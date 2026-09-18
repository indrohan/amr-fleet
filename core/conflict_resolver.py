"""
conflict_resolver.py — Real-time conflict detection, deadlock resolution,
and collision avoidance for the AMR fleet.

Strategies (applied in priority order each tick)
─────────────────────────────────────────────────
1. Next-cell conflict  : Two robots intend to move into the same cell.
   → Lower-priority robot is issued a wait; higher-priority moves.

2. Edge (swap) conflict : Robots A→B and B→A would swap positions.
   → Lower-priority robot waits; higher-priority moves.

3. Deadlock detection   : Any robot that hasn't moved for
   DEADLOCK_DETECTION_WINDOW ticks while in NAVIGATING/WAITING state
   is considered deadlocked.
   → Robot with lowest priority in the stuck group backs off
     (random wait + path replan from CBS).

Priority scheme (configurable via config.PRIORITY_SCHEME)
──────────────────────────────────────────────────────────
  "id_order"      : lower robot_id wins
  "battery_first" : robot with MORE battery wins (preserve low-battery path)
  "task_urgency"  : robot carrying higher-priority task wins
"""

from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional, Set, Tuple

from core.config import (
    DEADLOCK_DETECTION_WINDOW, BACKOFF_MIN_TICKS, BACKOFF_MAX_TICKS,
    PRIORITY_SCHEME,
)
from core.robot import Robot, RobotState

logger = logging.getLogger(__name__)

Cell = Tuple[int, int]


# ── Priority helpers ──────────────────────────────────────────────────────────

def _priority(robot: Robot) -> float:
    """
    Return a scalar priority for the robot.
    Higher value = higher priority = gets the right of way.
    """
    if PRIORITY_SCHEME == "battery_first":
        return robot.battery
    elif PRIORITY_SCHEME == "task_urgency":
        if robot.current_task:
            return float(robot.current_task.priority)
        return 0.0
    else:  # "id_order" — lower id wins, so invert
        return -float(robot.robot_id)


def _higher_priority(a: Robot, b: Robot) -> Robot:
    return a if _priority(a) >= _priority(b) else b


def _lower_priority(a: Robot, b: Robot) -> Robot:
    return b if _priority(a) >= _priority(b) else a


# ── Conflict Resolver ────────────────────────────────────────────────────────

class ConflictResolver:
    """
    Runs each simulation tick *before* robots commit their moves.

    Usage
    ─────
    resolver = ConflictResolver(robots, warehouse, cbs_solver)
    resolver.resolve(tick)   # mutates robot states / paths as needed
    """

    def __init__(self, robots: Dict[int, Robot], warehouse, cbs_solver) -> None:
        self.robots     = robots
        self.warehouse  = warehouse
        self.cbs        = cbs_solver

        # Per-robot: ticks since last position change
        self._stall_counter: Dict[int, int]  = {rid: 0 for rid in robots}
        self._last_pos     : Dict[int, Cell] = {
            rid: r.position for rid, r in robots.items()
        }

        # Statistics
        self.total_conflicts_resolved: int = 0
        self.total_deadlocks_resolved: int = 0

    # ── Main entry point ──────────────────────────────────────────────────────

    def resolve(self, tick: int) -> None:
        """Call once per tick before robot.tick() is called."""
        self._update_stall_counters()
        self._resolve_next_cell_conflicts(tick)
        self._resolve_edge_swap_conflicts(tick)
        self._resolve_deadlocks(tick)

    # ── Stall tracking ────────────────────────────────────────────────────────

    def _update_stall_counters(self) -> None:
        for rid, robot in self.robots.items():
            if robot.position == self._last_pos[rid]:
                self._stall_counter[rid] += 1
            else:
                self._stall_counter[rid] = 0
            self._last_pos[rid] = robot.position

    # ── 1. Next-cell conflicts ─────────────────────────────────────────────────

    def _resolve_next_cell_conflicts(self, tick: int) -> None:
        """
        Detect robots intending to move to the same cell next tick.
        All but the highest-priority one are issued a wait.
        """
        # Map: target_cell → list of robots wanting it
        intentions: Dict[Cell, List[Robot]] = {}
        for robot in self.robots.values():
            if robot.state != RobotState.NAVIGATING:
                continue
            nxt = robot.next_intended_cell()
            if nxt is None:
                continue
            intentions.setdefault(nxt, []).append(robot)

        for cell, contenders in intentions.items():
            if len(contenders) < 2:
                continue

            # Sort by priority descending; highest gets to move
            contenders.sort(key=_priority, reverse=True)
            winner = contenders[0]
            for loser in contenders[1:]:
                backoff = random.randint(BACKOFF_MIN_TICKS, BACKOFF_MAX_TICKS)
                logger.debug(
                    "Tick %d: vertex conflict at %s → Robot %d waits %d ticks "
                    "(Robot %d moves)",
                    tick, cell, loser.robot_id, backoff, winner.robot_id,
                )
                loser.issue_wait(backoff)
                self.total_conflicts_resolved += 1

    # ── 2. Edge swap conflicts ────────────────────────────────────────────────

    def _resolve_edge_swap_conflicts(self, tick: int) -> None:
        """
        Detect A→B and B→A swaps. Lower-priority robot waits.
        """
        navigating = [
            r for r in self.robots.values()
            if r.state == RobotState.NAVIGATING
               and r.next_intended_cell() is not None
        ]

        checked: Set[Tuple[int, int]] = set()
        for i in range(len(navigating)):
            for j in range(i + 1, len(navigating)):
                ra, rb = navigating[i], navigating[j]
                pair = (min(ra.robot_id, rb.robot_id),
                        max(ra.robot_id, rb.robot_id))
                if pair in checked:
                    continue
                checked.add(pair)

                a_next = ra.next_intended_cell()
                b_next = rb.next_intended_cell()

                if a_next == rb.position and b_next == ra.position:
                    loser  = _lower_priority(ra, rb)
                    winner = _higher_priority(ra, rb)
                    backoff = random.randint(BACKOFF_MIN_TICKS,
                                            BACKOFF_MAX_TICKS)
                    logger.debug(
                        "Tick %d: swap conflict (%s↔%s) → Robot %d waits %d ticks",
                        tick, ra.position, rb.position,
                        loser.robot_id, backoff,
                    )
                    loser.issue_wait(backoff)
                    self.total_conflicts_resolved += 1

    # ── 3. Deadlock detection and resolution ──────────────────────────────────

    def _resolve_deadlocks(self, tick: int) -> None:
        """
        Identify robots stuck for ≥ DEADLOCK_DETECTION_WINDOW ticks
        and force a replan via CBS.
        """
        stuck: List[Robot] = [
            r for r in self.robots.values()
            if self._stall_counter[r.robot_id] >= DEADLOCK_DETECTION_WINDOW
            and r.state in (RobotState.NAVIGATING, RobotState.WAITING)
            and r.current_task is not None
        ]

        if not stuck:
            return

        # Sort by priority ascending — lowest priority replans first
        stuck.sort(key=_priority)

        for robot in stuck:
            self._break_deadlock(robot, tick)

    def _break_deadlock(self, robot: Robot, tick: int) -> None:
        """
        Force a robot out of deadlock:
        1. Issue a random backoff wait.
        2. Replan its path using CBS, treating all other robots'
           current paths as reservations.
        """
        backoff = random.randint(BACKOFF_MIN_TICKS * 2,
                                 BACKOFF_MAX_TICKS * 2)
        robot.issue_wait(backoff)
        self._stall_counter[robot.robot_id] = 0
        self.total_deadlocks_resolved += 1

        # Determine goal for replanning
        if robot.current_task:
            goal = (robot.current_task.pickup
                    if robot.heading_to_pickup
                    else robot.current_task.dropoff)
        else:
            return

        # Build other robots' current paths as reservations
        other_paths = {
            rid: r.path[r.path_index:]
            for rid, r in self.robots.items()
            if rid != robot.robot_id and r.path
        }

        new_path = self.cbs.replan_single(
            robot.robot_id,
            robot.position,
            goal,
            other_paths,
        )

        if new_path:
            robot.set_path(new_path)
            logger.info(
                "Tick %d: Deadlock resolved for Robot %d — new path length %d",
                tick, robot.robot_id, len(new_path),
            )
        else:
            logger.warning(
                "Tick %d: Robot %d deadlocked with no replan path. "
                "Releasing task.",
                tick, robot.robot_id,
            )
            robot.release_task()

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> Dict:
        return {
            "conflicts_resolved": self.total_conflicts_resolved,
            "deadlocks_resolved": self.total_deadlocks_resolved,
        }
