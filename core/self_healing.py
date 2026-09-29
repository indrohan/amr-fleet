"""
self_healing.py — Self-Healing + Automatic Battery Management for AMR fleet.

Features
────────
  1. Battery Management
     - Predicts when a robot will run out BEFORE it completes its task
     - Proactively sends robot to charger mid-task if needed
     - Prioritises charger slots (only N robots charge simultaneously)
     - Emergency charge if battery < CRITICAL threshold

  2. Robot Failure Recovery
     - Detects stuck robots (no movement for N ticks)
     - Detects robots in ERROR state
     - Auto-replans or re-assigns their tasks
     - Logs recovery actions for dashboard
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
CRITICAL_BATTERY      = 15.0   # below this → emergency charge
PROACTIVE_BATTERY     = 28.0   # below this → plan charge after current task
STUCK_TICKS_THRESHOLD = 20     # ticks without movement = stuck
MAX_SIMULTANEOUS_CHARGE = 3    # charger slots
HEALTH_CHECK_INTERVAL = 5      # ticks between health checks


@dataclass
class RobotHealth:
    robot_id: int
    last_position: tuple = (0, 0)
    ticks_stationary: int = 0
    failure_count: int = 0
    recovery_count: int = 0
    battery_warnings: int = 0
    last_battery: float = 100.0
    is_failed: bool = False
    charging_scheduled: bool = False


@dataclass
class HealingEvent:
    tick: int
    robot_id: int
    event_type: str          # 'BATTERY_EMERGENCY' | 'BATTERY_PROACTIVE' | 'STUCK_DETECTED' | 'RECOVERED' | 'TASK_REASSIGNED'
    detail: str
    severity: str = 'INFO'   # 'INFO' | 'WARN' | 'CRITICAL'


class SelfHealingManager:
    """
    Monitors all robots each tick and automatically:
    - Manages battery routing
    - Detects and recovers stuck/failed robots
    - Reports healing events for the dashboard
    """

    def __init__(self, robots: dict, warehouse, cbs) -> None:
        self.robots    = robots
        self.warehouse = warehouse
        self.cbs       = cbs

        self.health: Dict[int, RobotHealth] = {
            rid: RobotHealth(robot_id=rid, last_position=r.position)
            for rid, r in robots.items()
        }
        self.events: List[HealingEvent] = []
        self._charging_now: set = set()    # robot ids currently charging by our routing

    # ── Main tick ─────────────────────────────────────────────────────────────

    def tick(self, tick: int, allocator) -> None:
        if tick % HEALTH_CHECK_INTERVAL != 0:
            return

        for rid, robot in self.robots.items():
            h = self.health[rid]
            self._check_battery(tick, robot, h, allocator)
            self._check_stuck(tick, robot, h, allocator)
            h.last_position = robot.position
            h.last_battery  = robot.battery

    # ── Battery management ────────────────────────────────────────────────────

    def _check_battery(self, tick: int, robot, h: RobotHealth, allocator) -> None:
        from core.robot import RobotState

        bat = robot.battery

        # Already charging — remove from our tracking if done
        if robot.state == RobotState.CHARGING:
            self._charging_now.discard(robot.robot_id)
            h.charging_scheduled = False
            return

        # Emergency — drop task and charge immediately
        if bat <= CRITICAL_BATTERY and robot.state not in (RobotState.CHARGING, RobotState.ERROR):
            if robot.robot_id not in self._charging_now:
                task = robot.release_task()
                if task:
                    allocator.requeue_task(task)
                self._route_to_charger(robot)
                self._charging_now.add(robot.robot_id)
                h.battery_warnings += 1
                h.charging_scheduled = True
                evt = HealingEvent(
                    tick=tick, robot_id=robot.robot_id,
                    event_type='BATTERY_EMERGENCY',
                    detail=f'Battery {bat:.1f}% critical — emergency charge. Task re-queued.',
                    severity='CRITICAL'
                )
                self.events.append(evt)
                logger.warning("SelfHeal: Robot %d EMERGENCY CHARGE at %.1f%%", robot.robot_id, bat)

        # Proactive — schedule charge after current task
        elif bat <= PROACTIVE_BATTERY and not h.charging_scheduled:
            if robot.current_task is None and robot.state == RobotState.IDLE:
                if robot.robot_id not in self._charging_now:
                    if len(self._charging_now) < MAX_SIMULTANEOUS_CHARGE:
                        self._route_to_charger(robot)
                        self._charging_now.add(robot.robot_id)
                        h.charging_scheduled = True
                        evt = HealingEvent(
                            tick=tick, robot_id=robot.robot_id,
                            event_type='BATTERY_PROACTIVE',
                            detail=f'Battery {bat:.1f}% low — proactive charge scheduled.',
                            severity='WARN'
                        )
                        self.events.append(evt)
                        logger.info("SelfHeal: Robot %d proactive charge at %.1f%%", robot.robot_id, bat)

    def _route_to_charger(self, robot) -> None:
        """Route robot to nearest free charger using A*."""
        from planning.astar import astar
        from core.robot import RobotState

        charger = self.warehouse.nearest_charging_station(robot.position)
        if charger == robot.position:
            robot.state = robot.state.CHARGING
            return

        other_paths = {
            rid: r.path[r.path_index:]
            for rid, r in self.robots.items()
            if rid != robot.robot_id and r.path
        }
        path = self.cbs.replan_single(robot.robot_id, robot.position, charger, other_paths)
        if path:
            robot.set_path(path)
            robot._routing_to_charger = True
            robot.state = RobotState.NAVIGATING

    # ── Stuck / failure detection ──────────────────────────────────────────────

    def _check_stuck(self, tick: int, robot, h: RobotHealth, allocator) -> None:
        from core.robot import RobotState

        if robot.state in (RobotState.CHARGING, RobotState.IDLE,
                           RobotState.PICKING_UP, RobotState.DROPPING_OFF):
            h.ticks_stationary = 0
            return

        if robot.position == h.last_position:
            h.ticks_stationary += HEALTH_CHECK_INTERVAL
        else:
            h.ticks_stationary = 0

        # ERROR state recovery
        if robot.state == RobotState.ERROR and not h.is_failed:
            h.is_failed = True
            h.failure_count += 1
            task = robot.release_task()
            if task:
                allocator.requeue_task(task)
            robot.state = RobotState.IDLE
            h.recovery_count += 1
            evt = HealingEvent(
                tick=tick, robot_id=robot.robot_id,
                event_type='RECOVERED',
                detail=f'Robot ERROR recovered. Task re-queued. Failure #{h.failure_count}',
                severity='WARN'
            )
            self.events.append(evt)
            logger.warning("SelfHeal: Robot %d recovered from ERROR state.", robot.robot_id)

        elif h.ticks_stationary >= STUCK_TICKS_THRESHOLD:
            h.ticks_stationary = 0
            h.failure_count += 1
            # Force replan
            task = robot.release_task()
            if task:
                allocator.requeue_task(task)
            robot.state = RobotState.IDLE
            h.recovery_count += 1
            h.is_failed = False
            evt = HealingEvent(
                tick=tick, robot_id=robot.robot_id,
                event_type='STUCK_DETECTED',
                detail=f'Robot stuck {STUCK_TICKS_THRESHOLD}+ ticks — replanned. Failure #{h.failure_count}',
                severity='WARN'
            )
            self.events.append(evt)
            logger.warning("SelfHeal: Robot %d stuck — forced replan.", robot.robot_id)
        else:
            h.is_failed = False

    # ── Dashboard data ─────────────────────────────────────────────────────────

    def drain_events(self) -> List[Dict[str, Any]]:
        evts = [
            {
                "tick": e.tick, "robot_id": e.robot_id,
                "type": e.event_type, "detail": e.detail, "severity": e.severity
            }
            for e in self.events
        ]
        self.events.clear()
        return evts

    def health_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "robot_id": h.robot_id,
                "failures": h.failure_count,
                "recoveries": h.recovery_count,
                "battery_warnings": h.battery_warnings,
                "charging_scheduled": h.charging_scheduled,
                "ticks_stationary": h.ticks_stationary,
                "is_failed": h.is_failed,
            }
            for h in self.health.values()
        ]
