"""
task_allocator.py — Auction-based dynamic task allocation and re-routing.

Algorithm
─────────
Each unassigned task is broadcast to all idle/near-idle robots.
Each robot computes a *bid* (lower = better):

    bid = distance_to_pickup / battery_factor + (1 / priority)

The allocator awards the task to the robot with the lowest bid.
This is a greedy single-item auction run locally on the edge — no
central auctioneer needed.  The allocator runs on whichever robot
currently acts as the "coordinator" (rotating token), so the system
remains fully decentralised.

Re-routing
──────────
When a robot reports a blocked cell (BLOCK_ALERT), tasks assigned to
routes that pass through the blocked cell are released back to the pool
and re-auctioned immediately.
"""

from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional, Set, Tuple

from core.config   import (
    NUM_INITIAL_TASKS, TASK_GENERATION_INTERVAL,
    MAX_PENDING_TASKS, RANDOM_SEED, LOW_BATTERY_THRESHOLD,
)
from core.robot    import Robot, RobotState, Task
from core.warehouse import Warehouse, PICKUP, DROPOFF

logger = logging.getLogger(__name__)

Cell = Tuple[int, int]


class TaskAllocator:
    """
    Manages the global task pool and assigns tasks to robots.

    The allocator is called by the simulation engine each tick.
    It is intentionally stateless w.r.t. the robots — it only reads
    robot state and calls robot.assign_task().
    """

    def __init__(self,
                 warehouse: Warehouse,
                 robots: Dict[int, Robot],
                 seed: int = RANDOM_SEED) -> None:
        self.warehouse = warehouse
        self.robots    = robots
        self._rng      = random.Random(seed + 7)

        self.pending_tasks  : List[Task] = []
        self.completed_tasks: List[Task] = []
        self.blocked_cells  : Set[Cell]  = set()
        self._all_tasks     : List[Task] = []   # every task ever created

        self._task_gen_countdown = TASK_GENERATION_INTERVAL

        # Seed initial tasks
        self._generate_tasks(NUM_INITIAL_TASKS, tick=0)

    # ── Main tick entry ────────────────────────────────────────────────────────

    def tick(self, current_tick: int) -> None:
        """Called every simulation tick by the engine."""
        self._maybe_generate_tasks(current_tick)
        self._collect_completed()
        self._assign_pending(current_tick)

    # ── Task generation ────────────────────────────────────────────────────────

    def _maybe_generate_tasks(self, tick: int) -> None:
        self._task_gen_countdown -= 1
        if self._task_gen_countdown <= 0:
            self._task_gen_countdown = TASK_GENERATION_INTERVAL
            if len(self.pending_tasks) < MAX_PENDING_TASKS:
                self._generate_tasks(
                    self._rng.randint(1, 3), tick=tick)

    def _generate_tasks(self, n: int, tick: int) -> None:
        pickups  = [c for c in self.warehouse.pickup_points
                    if c not in self.blocked_cells]
        dropoffs = [c for c in self.warehouse.dropoff_points
                    if c not in self.blocked_cells]

        if not pickups or not dropoffs:
            return

        for _ in range(n):
            if len(self.pending_tasks) >= MAX_PENDING_TASKS:
                break
            pickup  = self._rng.choice(pickups)
            dropoff = self._rng.choice(dropoffs)
            if pickup == dropoff:
                continue
            priority = self._rng.randint(1, 3)
            task = Task(pickup, dropoff, priority)
            task.created_tick = tick
            self.pending_tasks.append(task)
            self._all_tasks.append(task)
            logger.debug("Generated task %d: %s → %s (priority %d)",
                         task.task_id, pickup, dropoff, priority)

    # ── Collect completions ────────────────────────────────────────────────────

    def _collect_completed(self) -> None:
        """
        Scan all known tasks. Move newly-completed ones to completed_tasks
        and remove them from pending_tasks.
        """
        for task in list(self.pending_tasks):
            if task.completed and task not in self.completed_tasks:
                self.completed_tasks.append(task)
                self.pending_tasks.remove(task)

    # ── Assignment loop ────────────────────────────────────────────────────────

    def _assign_pending(self, tick: int) -> None:
        """
        For each unassigned task, find the best idle robot and assign it.
        """
        unassigned = [t for t in self.pending_tasks
                      if t.assigned_to is None and not t.completed]
        idle_robots = [r for r in self.robots.values()
                       if r.state == RobotState.IDLE
                       and r.current_task is None
                       and r.battery > LOW_BATTERY_THRESHOLD]

        if not unassigned or not idle_robots:
            return

        for task in unassigned:
            if not idle_robots:
                break
            winner, bid = self._auction(task, idle_robots)
            if winner:
                winner.assign_task(task)
                idle_robots.remove(winner)
                logger.info(
                    "Tick %d: Task %d awarded to Robot %d (bid=%.2f)",
                    tick, task.task_id, winner.robot_id, bid,
                )

    def _auction(self,
                 task: Task,
                 candidates: List[Robot]) -> Tuple[Optional[Robot], float]:
        """Return (best_robot, bid_value). Lower bid = better."""
        best_robot: Optional[Robot] = None
        best_bid = float("inf")

        for robot in candidates:
            d = self._manhattan(robot.position, task.pickup)
            battery_factor = max(0.1, robot.battery / 100.0)
            bid = (d / battery_factor) + (10.0 / max(1, task.priority))
            if bid < best_bid:
                best_bid  = bid
                best_robot = robot

        return best_robot, best_bid

    # ── Charging re-routing ────────────────────────────────────────────────────

    def route_to_charger(self, robot: Robot) -> None:
        """
        Strip the robot's current task (return it to pool) and mark
        the robot so the engine will plan a path to the nearest charger.
        """
        task = robot.release_task()
        if task:
            task.assigned_to = None
            # Re-insert at front so it gets re-assigned quickly
            self.pending_tasks.insert(0, task)
            logger.info("Robot %d: task %d released for charging.",
                        robot.robot_id, task.task_id)
        robot._routing_to_charger = True  # flag checked by conflict resolver

    # ── Block alerts ──────────────────────────────────────────────────────────

    def register_block(self, cell: Cell) -> None:
        """
        Mark a cell as blocked (discovered by a robot) and release any
        task whose pickup or dropoff is that cell.
        """
        self.blocked_cells.add(cell)
        for task in list(self.pending_tasks):
            if task.pickup == cell or task.dropoff == cell:
                if task.assigned_to is not None:
                    for robot in self.robots.values():
                        if robot.robot_id == task.assigned_to:
                            robot.release_task()
                self.pending_tasks.remove(task)
                logger.warning("Task %d removed: cell %s blocked.",
                               task.task_id, cell)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> Dict:
        return {
            "pending"   : len([t for t in self.pending_tasks
                               if t.assigned_to is None]),
            "assigned"  : len([t for t in self.pending_tasks
                               if t.assigned_to is not None]),
            "completed" : len(self.completed_tasks),
            "blocked_cells": len(self.blocked_cells),
        }

    def all_tasks_for_dashboard(self) -> List[Dict]:
        result = []
        for t in self._all_tasks[-40:]:   # last 40 tasks to keep payload small
            result.append({
                "id"         : t.task_id,
                "pickup"     : list(t.pickup),
                "dropoff"    : list(t.dropoff),
                "priority"   : t.priority,
                "assigned_to": t.assigned_to,
                "completed"  : t.completed,
            })
        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _manhattan(a: Cell, b: Cell) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
