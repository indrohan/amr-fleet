"""
smart_task_allocator.py — Smart Task Allocation with Accept/Reject logic.

Each AMR evaluates incoming tasks using a multi-factor cost function:
  cost = w1*distance + w2*(1/battery) + w3*load_factor + w4*deadline_urgency

If cost > REJECTION_THRESHOLD the robot rejects the task and it goes to
the next best robot.  This prevents over-loading robots that are far away,
low on battery, or already carrying heavy payloads.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
W_DISTANCE   = 0.35
W_BATTERY    = 0.30
W_LOAD       = 0.20
W_DEADLINE   = 0.15
REJECTION_THRESHOLD = 0.78     # 0–1 normalised cost; above this → reject
MAX_REJECTION_ROUNDS = 3       # after 3 rejections force assign to best robot

Cell = Tuple[int, int]


@dataclass
class TaskBid:
    robot_id:   int
    task_id:    int
    cost:       float
    accepted:   bool
    reason:     str
    components: Dict[str, float]


class SmartTaskAllocator:
    """
    Wraps the base TaskAllocator and adds cost-based accept/reject.

    Usage:  call evaluate_assignment(robot, task) before assigning.
    The simulation calls this instead of direct assignment.
    """

    def __init__(self, robots: dict, warehouse) -> None:
        self.robots    = robots
        self.warehouse = warehouse
        self._bid_log:  List[Dict[str, Any]] = []
        self._pending_events: List[Dict[str, Any]] = []

        # Stats
        self.total_bids      = 0
        self.total_accepts   = 0
        self.total_rejects   = 0
        self.reassignments   = 0

    # ── Cost function ─────────────────────────────────────────────────────────

    def compute_cost(self, robot, task) -> Tuple[float, Dict[str, float]]:
        """
        Returns normalised cost [0,1] and component breakdown.
        Lower cost = better fit.
        """
        from core.config import BATTERY_CAPACITY

        # Distance component: Manhattan to pickup / max expected dist (30)
        dist = abs(task.pickup[0] - robot.position[0]) + abs(task.pickup[1] - robot.position[1])
        dist_norm = min(1.0, dist / 30.0)

        # Battery component: low battery = high cost
        bat_norm  = 1.0 - (robot.battery / BATTERY_CAPACITY)   # 0=full, 1=empty

        # Load factor: tasks already queued by this robot
        load = robot.tasks_completed   # proxy: use current task count
        load_norm = min(1.0, load / 20.0)

        # Deadline urgency: higher priority task → lower cost penalty
        deadline_norm = 1.0 - (min(task.priority, 3) / 3.0)

        total = (W_DISTANCE * dist_norm
                 + W_BATTERY  * bat_norm
                 + W_LOAD     * load_norm
                 + W_DEADLINE * deadline_norm)

        return total, {
            "distance":  round(dist_norm, 3),
            "battery":   round(bat_norm, 3),
            "load":      round(load_norm, 3),
            "deadline":  round(deadline_norm, 3),
        }

    def evaluate_assignment(self, robot, task, tick: int) -> TaskBid:
        """Returns a TaskBid — accepted or rejected with reason."""
        cost, components = self.compute_cost(robot, task)
        self.total_bids += 1

        if cost <= REJECTION_THRESHOLD:
            accepted = True
            reason   = f"Accepted — cost {cost:.3f} ≤ threshold {REJECTION_THRESHOLD}"
            self.total_accepts += 1
        else:
            accepted = False
            reason   = (f"Rejected — cost {cost:.3f} > threshold {REJECTION_THRESHOLD} "
                        f"(dist={components['distance']:.2f} bat={components['battery']:.2f})")
            self.total_rejects += 1

        bid = TaskBid(
            robot_id=robot.robot_id, task_id=task.task_id,
            cost=cost, accepted=accepted, reason=reason, components=components
        )
        self._bid_log.append({
            "tick": tick, "robot_id": robot.robot_id, "task_id": task.task_id,
            "cost": round(cost, 3), "accepted": accepted, "reason": reason,
            **{f"c_{k}": v for k, v in components.items()}
        })
        self._pending_events.append({
            "tick": tick, "type": "TASK_BID",
            "robot_id": robot.robot_id, "task_id": task.task_id,
            "cost": round(cost, 3), "accepted": accepted, "reason": reason,
            "detail": f"AMR-{robot.robot_id:02d} {'✓ ACCEPT' if accepted else '✗ REJECT'} Task#{task.task_id} cost={cost:.3f}"
        })
        return bid

    def best_robot_for_task(self, task, candidates: list, tick: int) -> Optional[object]:
        """
        Evaluate all candidates and return the one with the lowest accepted cost.
        If all reject, force assign to the lowest cost robot.
        """
        bids = [(self.evaluate_assignment(r, task, tick), r) for r in candidates]
        accepted = [(b, r) for b, r in bids if b.accepted]

        if accepted:
            best_bid, best_robot = min(accepted, key=lambda x: x[0].cost)
            logger.info("SmartAlloc: Task %d → Robot %d (cost=%.3f, ACCEPTED)",
                        task.task_id, best_robot.robot_id, best_bid.cost)
            return best_robot

        # All rejected — force assign to lowest cost
        if bids:
            best_bid, best_robot = min(bids, key=lambda x: x[0].cost)
            self.reassignments += 1
            logger.info("SmartAlloc: Task %d force-assigned to Robot %d (cost=%.3f, all rejected)",
                        task.task_id, best_robot.robot_id, best_bid.cost)
            self._pending_events.append({
                "tick": tick, "type": "FORCE_ASSIGN",
                "robot_id": best_robot.robot_id, "task_id": task.task_id,
                "detail": f"Task#{task.task_id} force-assigned to AMR-{best_robot.robot_id:02d} after all rejects"
            })
            return best_robot
        return None

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def drain_events(self) -> List[Dict[str, Any]]:
        evts = list(self._pending_events)
        self._pending_events.clear()
        return evts

    def recent_bids(self, n: int = 20) -> List[Dict[str, Any]]:
        return self._bid_log[-n:]

    def stats(self) -> Dict[str, Any]:
        accept_rate = (self.total_accepts / max(1, self.total_bids)) * 100
        return {
            "total_bids":    self.total_bids,
            "total_accepts": self.total_accepts,
            "total_rejects": self.total_rejects,
            "reassignments": self.reassignments,
            "accept_rate":   round(accept_rate, 1),
        }
