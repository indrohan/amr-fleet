"""
dynamic_events.py — Dynamic Event Handling System.

Event Types
───────────
  BLOCKED_AISLE   — A grid cell becomes temporarily impassable
  NEW_OBSTACLE    — Random obstacle appears on floor
  ROBOT_FAILURE   — Robot enters ERROR state randomly
  LOW_BATTERY     — Robot battery drops below threshold
  AISLE_CLEARED   — Blocked aisle is cleared
  OBSTACLE_REMOVED— Obstacle removed after TTL
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BLOCKED_AISLE_PROB    = 0.002   # per tick probability of an aisle blocking
OBSTACLE_PROB         = 0.001
ROBOT_FAILURE_PROB    = 0.0008
BLOCKED_AISLE_TTL     = 80      # ticks before aisle clears
OBSTACLE_TTL          = 60
MAX_ACTIVE_EVENTS     = 4       # cap simultaneous events
LOW_BATTERY_THRESHOLD = 28.0

Cell = Tuple[int, int]


@dataclass
class DynamicEvent:
    event_id: int
    tick_created: int
    event_type: str
    cell: Optional[Cell]
    robot_id: Optional[int]
    detail: str
    ttl: int            # ticks until auto-resolved (0 = permanent until resolved)
    resolved: bool = False
    tick_resolved: int = 0
    severity: str = 'INFO'


class DynamicEventSystem:
    """
    Randomly generates and manages dynamic warehouse events.
    Integrates with the warehouse grid to block/unblock cells.
    """

    def __init__(self, warehouse, robots: dict, seed: int = 42) -> None:
        self.warehouse = warehouse
        self.robots    = robots
        self.rng       = random.Random(seed + 99)
        self._id_counter   = 0
        self.active_events: List[DynamicEvent] = []
        self.history:       List[DynamicEvent] = []
        self._pending_broadcast: List[Dict[str, Any]] = []
        self._blocked_cells: Set[Cell] = set()

    # ── Main tick ─────────────────────────────────────────────────────────────

    def tick(self, tick: int, allocator) -> None:
        # Age and resolve TTL events
        self._expire_events(tick)

        if len(self.active_events) >= MAX_ACTIVE_EVENTS:
            return

        # Randomly generate events
        r = self.rng.random()
        if r < BLOCKED_AISLE_PROB:
            self._gen_blocked_aisle(tick, allocator)
        elif r < BLOCKED_AISLE_PROB + OBSTACLE_PROB:
            self._gen_obstacle(tick)
        elif r < BLOCKED_AISLE_PROB + OBSTACLE_PROB + ROBOT_FAILURE_PROB:
            self._gen_robot_failure(tick, allocator)

        # Low battery is detected from robot state — not random
        self._detect_low_battery(tick)

    # ── Event generators ──────────────────────────────────────────────────────

    def _gen_blocked_aisle(self, tick: int, allocator) -> None:
        free_cells = [
            (r, c)
            for r in range(self.warehouse.rows)
            for c in range(self.warehouse.cols)
            if self.warehouse.grid[r][c] == 0 and (r, c) not in self._blocked_cells
        ]
        if not free_cells:
            return
        cell = self.rng.choice(free_cells)
        self._id_counter += 1
        evt = DynamicEvent(
            event_id=self._id_counter, tick_created=tick,
            event_type='BLOCKED_AISLE', cell=cell, robot_id=None,
            detail=f'Aisle blocked at {cell} — rerouting affected robots.',
            ttl=BLOCKED_AISLE_TTL, severity='WARN'
        )
        self.active_events.append(evt)
        self._blocked_cells.add(cell)
        # Block cell in warehouse temporarily
        self.warehouse.grid[cell[0]][cell[1]] = 99   # temporary block type
        # Force allocator to re-evaluate
        allocator.register_block(cell)
        self._broadcast(evt)
        logger.warning("DynEvent: Blocked aisle at %s", cell)

    def _gen_obstacle(self, tick: int) -> None:
        free_cells = [
            (r, c)
            for r in range(self.warehouse.rows)
            for c in range(self.warehouse.cols)
            if self.warehouse.grid[r][c] == 0 and (r, c) not in self._blocked_cells
        ]
        if not free_cells:
            return
        cell = self.rng.choice(free_cells)
        self._id_counter += 1
        evt = DynamicEvent(
            event_id=self._id_counter, tick_created=tick,
            event_type='NEW_OBSTACLE', cell=cell, robot_id=None,
            detail=f'New obstacle detected at {cell}.',
            ttl=OBSTACLE_TTL, severity='WARN'
        )
        self.active_events.append(evt)
        self._blocked_cells.add(cell)
        self.warehouse.grid[cell[0]][cell[1]] = 99
        self._broadcast(evt)
        logger.info("DynEvent: Obstacle at %s", cell)

    def _gen_robot_failure(self, tick: int, allocator) -> None:
        from core.robot import RobotState
        candidates = [
            r for r in self.robots.values()
            if r.state not in (RobotState.CHARGING, RobotState.ERROR)
        ]
        if not candidates:
            return
        robot = self.rng.choice(candidates)
        self._id_counter += 1
        evt = DynamicEvent(
            event_id=self._id_counter, tick_created=tick,
            event_type='ROBOT_FAILURE', cell=None, robot_id=robot.robot_id,
            detail=f'Robot {robot.robot_id} failure — self-healing initiated.',
            ttl=0, severity='CRITICAL'
        )
        self.active_events.append(evt)
        # Set robot to ERROR — self_healing.py will recover it
        robot.state = RobotState.ERROR
        task = robot.release_task()
        if task:
            allocator.requeue_task(task)
        self._broadcast(evt)
        logger.error("DynEvent: Robot %d failure injected", robot.robot_id)

    def _detect_low_battery(self, tick: int) -> None:
        for robot in self.robots.values():
            if robot.battery <= LOW_BATTERY_THRESHOLD:
                # Check if we already have an active event for this robot
                already = any(
                    e.event_type == 'LOW_BATTERY' and e.robot_id == robot.robot_id
                    for e in self.active_events
                )
                if not already:
                    self._id_counter += 1
                    evt = DynamicEvent(
                        event_id=self._id_counter, tick_created=tick,
                        event_type='LOW_BATTERY', cell=None, robot_id=robot.robot_id,
                        detail=f'Robot {robot.robot_id} battery {robot.battery:.1f}% — charge routing active.',
                        ttl=30, severity='WARN'
                    )
                    self.active_events.append(evt)
                    self._broadcast(evt)

    # ── TTL expiry ────────────────────────────────────────────────────────────

    def _expire_events(self, tick: int) -> None:
        to_remove = []
        for evt in self.active_events:
            if evt.ttl > 0 and (tick - evt.tick_created) >= evt.ttl:
                evt.resolved      = True
                evt.tick_resolved = tick
                self.history.append(evt)
                to_remove.append(evt)
                # Restore cell
                if evt.cell and evt.cell in self._blocked_cells:
                    orig_type = 0  # free
                    self.warehouse.grid[evt.cell[0]][evt.cell[1]] = orig_type
                    self._blocked_cells.discard(evt.cell)
                    resolved_type = ('AISLE_CLEARED' if evt.event_type == 'BLOCKED_AISLE'
                                     else 'OBSTACLE_REMOVED')
                    self._id_counter += 1
                    clear_evt = DynamicEvent(
                        event_id=self._id_counter, tick_created=tick,
                        event_type=resolved_type, cell=evt.cell, robot_id=None,
                        detail=f'{resolved_type} at {evt.cell}.',
                        ttl=0, severity='INFO'
                    )
                    self._broadcast(clear_evt)
                    logger.info("DynEvent: %s at %s", resolved_type, evt.cell)

        for e in to_remove:
            self.active_events.remove(e)

    # ── Broadcast ─────────────────────────────────────────────────────────────

    def _broadcast(self, evt: DynamicEvent) -> None:
        self._pending_broadcast.append({
            "event_id": evt.event_id,
            "tick":     evt.tick_created,
            "type":     evt.event_type,
            "cell":     list(evt.cell) if evt.cell else None,
            "robot_id": evt.robot_id,
            "detail":   evt.detail,
            "severity": evt.severity,
            "ttl":      evt.ttl,
        })

    def drain_events(self) -> List[Dict[str, Any]]:
        evts = list(self._pending_broadcast)
        self._pending_broadcast.clear()
        return evts

    # ── Dashboard data ────────────────────────────────────────────────────────

    def active_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "event_id": e.event_id, "type": e.event_type,
                "cell": list(e.cell) if e.cell else None,
                "robot_id": e.robot_id, "detail": e.detail,
                "severity": e.severity, "tick": e.tick_created,
                "ttl_remaining": max(0, e.ttl - 0),
            }
            for e in self.active_events
        ]

    def blocked_cells(self) -> List[List[int]]:
        return [list(c) for c in self._blocked_cells]
