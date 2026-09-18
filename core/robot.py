"""
robot.py — AMR agent with full state machine, battery model, and task handling.

State machine
─────────────
  IDLE        → no task assigned, waiting
  NAVIGATING  → following a planned path toward pickup or dropoff
  PICKING_UP  → arrived at pickup, simulating pick duration
  DROPPING_OFF→ arrived at dropoff, simulating drop duration
  CHARGING    → at a charging station, recharging
  WAITING     → instructed to wait (conflict backoff)
  ERROR       → stuck / unreachable goal

Transitions are driven by the simulation engine each tick.
"""

from __future__ import annotations

import enum
import logging
from typing import List, Optional, Tuple, Dict, Any

from core.config import (
    BATTERY_CAPACITY, BATTERY_DRAIN_PER_MOVE, BATTERY_DRAIN_IDLE,
    BATTERY_CHARGE_RATE, LOW_BATTERY_THRESHOLD,
)

logger = logging.getLogger(__name__)

Cell = Tuple[int, int]
Path = List[Cell]


# ── State machine ──────────────────────────────────────────────────────────────

class RobotState(enum.Enum):
    IDLE         = "IDLE"
    NAVIGATING   = "NAVIGATING"
    PICKING_UP   = "PICKING_UP"
    DROPPING_OFF = "DROPPING_OFF"
    CHARGING     = "CHARGING"
    WAITING      = "WAITING"
    ERROR        = "ERROR"


# ── Task dataclass ─────────────────────────────────────────────────────────────

class Task:
    _id_counter = 0

    def __init__(self, pickup: Cell, dropoff: Cell, priority: int = 1) -> None:
        Task._id_counter += 1
        self.task_id  = Task._id_counter
        self.pickup   = pickup
        self.dropoff  = dropoff
        self.priority = priority          # higher = more urgent
        self.assigned_to: Optional[int] = None
        self.completed  : bool           = False
        self.created_tick: int           = 0

    def __repr__(self) -> str:
        return (f"Task(id={self.task_id}, "
                f"pickup={self.pickup}, dropoff={self.dropoff}, "
                f"priority={self.priority})")


# ── AMR Robot ─────────────────────────────────────────────────────────────────

class Robot:
    """
    Represents one Autonomous Mobile Robot on the warehouse floor.

    Each robot maintains:
    - Its position and planned path
    - Battery level and charging logic
    - Current task and phase (going to pickup vs. dropoff)
    - Statistics for dashboard reporting
    """

    PICK_DURATION = 2    # ticks to simulate picking up a load
    DROP_DURATION = 2    # ticks to simulate dropping off a load

    def __init__(self, robot_id: int, start: Cell) -> None:
        self.robot_id   : int        = robot_id
        self.position   : Cell       = start
        self.state      : RobotState = RobotState.IDLE
        self.battery    : float      = BATTERY_CAPACITY

        # Path following
        self.path       : Path              = []
        self.path_index : int               = 0

        # Task
        self.current_task     : Optional[Task] = None
        self.heading_to_pickup: bool            = True   # False = heading to dropoff

        # Backoff / wait
        self.wait_ticks_remaining: int = 0

        # Action counters for dwell at pickup/dropoff
        self._action_ticks: int = 0

        # Statistics
        self.tasks_completed : int   = 0
        self.total_distance  : int   = 0   # cells moved
        self.collision_count : int   = 0   # incremented externally
        self.ticks_alive     : int   = 0

        # For dashboard — last broadcast
        self._last_broadcast_tick: int = -1

    # ── Path interface ─────────────────────────────────────────────────────────

    def set_path(self, path: Path) -> None:
        """Assign a new planned path (list of cells EXCLUDING current position)."""
        self.path       = list(path)
        self.path_index = 0
        if path:
            self.state = RobotState.NAVIGATING

    def next_intended_cell(self) -> Optional[Cell]:
        """The next cell this robot wants to move to this tick."""
        if self.state != RobotState.NAVIGATING:
            return None
        if self.path_index < len(self.path):
            return self.path[self.path_index]
        return None

    def has_path(self) -> bool:
        return bool(self.path) and self.path_index < len(self.path)

    # ── Tick update ────────────────────────────────────────────────────────────

    def tick(self, warehouse) -> None:
        """
        Advance robot by one simulation tick.
        Movement is only committed here; collision checks happen in the engine.
        """
        self.ticks_alive += 1
        self._drain_battery()

        if self.state == RobotState.WAITING:
            self._handle_wait()

        elif self.state == RobotState.NAVIGATING:
            self._handle_navigate(warehouse)

        elif self.state == RobotState.PICKING_UP:
            self._handle_action(RobotState.NAVIGATING)

        elif self.state == RobotState.DROPPING_OFF:
            self._handle_action_dropoff()

        elif self.state == RobotState.CHARGING:
            self._handle_charge(warehouse)

        elif self.state == RobotState.IDLE:
            pass   # waiting for task allocation

        # Check if battery is critically low and no charging path set
        if (self.battery <= LOW_BATTERY_THRESHOLD
                and self.state not in (RobotState.CHARGING, RobotState.ERROR)):
            if self.state != RobotState.NAVIGATING or not self._is_going_to_charge():
                logger.debug("Robot %d: low battery (%.1f%%), requesting charge",
                             self.robot_id, self.battery)
                self.state = RobotState.IDLE   # signal engine to reroute to charger

    # ── Internal state handlers ────────────────────────────────────────────────

    def _handle_navigate(self, warehouse) -> None:
        if not self.has_path():
            # Reached end of path — decide what to do next
            if self.current_task:
                if self.heading_to_pickup:
                    # Arrived at pickup
                    self.state      = RobotState.PICKING_UP
                    self._action_ticks = 0
                else:
                    # Arrived at dropoff
                    self.state      = RobotState.DROPPING_OFF
                    self._action_ticks = 0
            else:
                self.state = RobotState.IDLE
            return

        # Move one step
        next_cell = self.path[self.path_index]
        self.position   = next_cell
        self.path_index += 1
        self.total_distance += 1
        self._drain_move()

    def _handle_wait(self) -> None:
        self.wait_ticks_remaining -= 1
        if self.wait_ticks_remaining <= 0:
            self.wait_ticks_remaining = 0
            # Resume: if we have a task go back to navigating, else idle
            self.state = (RobotState.NAVIGATING
                          if self.has_path()
                          else RobotState.IDLE)

    def _handle_action(self, next_state: RobotState) -> None:
        """Generic dwell for PICKING_UP."""
        self._action_ticks += 1
        if self._action_ticks >= self.PICK_DURATION:
            self._action_ticks = 0
            self.heading_to_pickup = False
            self.path       = []
            self.path_index = 0
            self.state      = RobotState.IDLE   # signal engine to plan dropoff leg

    def _handle_action_dropoff(self) -> None:
        """Dwell for DROPPING_OFF then mark task complete."""
        self._action_ticks += 1
        if self._action_ticks >= self.DROP_DURATION:
            self._action_ticks = 0
            self._complete_task()

    def _handle_charge(self, warehouse) -> None:
        self.battery = min(BATTERY_CAPACITY,
                           self.battery + BATTERY_CHARGE_RATE)
        if self.battery >= BATTERY_CAPACITY:
            self.battery = BATTERY_CAPACITY
            self.state   = RobotState.IDLE
            logger.info("Robot %d: fully charged.", self.robot_id)

    def _is_going_to_charge(self) -> bool:
        """True if the robot's current path ends at a charging station cell
        — checked by looking at state flag set by the engine."""
        return getattr(self, "_routing_to_charger", False)

    # ── Task management ────────────────────────────────────────────────────────

    def assign_task(self, task: Task) -> None:
        self.current_task      = task
        self.heading_to_pickup = True
        self.path              = []
        self.path_index        = 0
        self.state             = RobotState.IDLE   # engine will plan the path
        task.assigned_to       = self.robot_id
        logger.info("Robot %d assigned task %d (pickup=%s, dropoff=%s)",
                    self.robot_id, task.task_id, task.pickup, task.dropoff)

    def _complete_task(self) -> None:
        if self.current_task:
            self.current_task.completed = True
            self.tasks_completed += 1
            logger.info("Robot %d completed task %d.",
                        self.robot_id, self.current_task.task_id)
        self.current_task      = None
        self.heading_to_pickup = True
        self.path              = []
        self.path_index        = 0
        self.state             = RobotState.IDLE

    def release_task(self) -> Optional[Task]:
        """Drop current task back to pool (e.g. for re-routing)."""
        task               = self.current_task
        self.current_task  = None
        self.path          = []
        self.path_index    = 0
        self.state         = RobotState.IDLE
        if task:
            task.assigned_to = None
        return task

    # ── Battery helpers ────────────────────────────────────────────────────────

    def _drain_battery(self) -> None:
        if self.state not in (RobotState.CHARGING,):
            self.battery = max(0.0, self.battery - BATTERY_DRAIN_IDLE)

    def _drain_move(self) -> None:
        self.battery = max(0.0, self.battery - BATTERY_DRAIN_PER_MOVE)

    def issue_wait(self, ticks: int) -> None:
        """External call from conflict resolver to pause this robot."""
        self.wait_ticks_remaining = ticks
        self.state = RobotState.WAITING

    # ── Serialisation for dashboard ────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id"            : self.robot_id,
            "pos"           : list(self.position),
            "state"         : self.state.value,
            "battery"       : round(self.battery, 1),
            "task_id"       : self.current_task.task_id if self.current_task else None,
            "tasks_done"    : self.tasks_completed,
            "distance"      : self.total_distance,
            "path_remaining": len(self.path) - self.path_index,
            "heading_pickup": self.heading_to_pickup,
        }
