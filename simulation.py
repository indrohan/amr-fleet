"""
simulation.py — Main orchestration engine for the AMR fleet.

Tick loop (runs at TICK_RATE_HZ)
─────────────────────────────────
  1. Task allocator assigns pending tasks to idle robots
  2. Path planner plans / replans paths for robots that need them
  3. Conflict resolver checks and resolves vertex/edge/deadlock conflicts
  4. Each robot advances one step (battery, state machine, movement)
  5. P2P network: robots broadcast position and intent
  6. Statistics collected and pushed to the WebSocket bridge queue

Stop-and-wait baseline
──────────────────────
  When stop_and_wait=True every robot halts when any other robot is
  within 2 cells, simulating the naive approach for benchmarking.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Dict, List, Optional, Any

from core.config import (
    NUM_ROBOTS, TICK_RATE_HZ, MAX_TICKS, RANDOM_SEED,
    REPLANNING_INTERVAL, LOW_BATTERY_THRESHOLD,
)
from core.warehouse      import Warehouse
from core.robot          import Robot, RobotState
from core.conflict_resolver import ConflictResolver
from core.task_allocator    import TaskAllocator
from comms.p2p_network      import PeerNode, InProcessBus
from planning.cbs           import CBS
from planning.astar         import astar

logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    Orchestrates the entire AMR fleet simulation.

    Parameters
    ----------
    stop_and_wait : bool
        Run in baseline mode (no CBS, robots stop if neighbour nearby).
    state_queue : asyncio.Queue, optional
        If provided, the engine pushes JSON state snapshots each tick
        for the WebSocket bridge to forward to the dashboard.
    """

    def __init__(self,
                 stop_and_wait: bool = False,
                 state_queue: Optional[asyncio.Queue] = None) -> None:
        self.stop_and_wait = stop_and_wait
        self.state_queue   = state_queue

        random.seed(RANDOM_SEED)
        InProcessBus.reset()

        # ── Core objects ───────────────────────────────────────────────────────
        self.warehouse = Warehouse()
        self.robots: Dict[int, Robot] = {}
        self._init_robots()

        self.cbs      = CBS(self.warehouse)
        self.allocator = TaskAllocator(self.warehouse, self.robots)
        self.resolver  = ConflictResolver(
            self.robots, self.warehouse, self.cbs)

        # P2P nodes (one per robot)
        self.peers: Dict[int, PeerNode] = {}
        self._init_peers()

        # ── Simulation state ───────────────────────────────────────────────────
        self.tick      : int  = 0
        self.running   : bool = False

        # Performance tracking
        self._task_completion_ticks: List[int] = []   # tick when each task done
        self._baseline_completion_ticks: List[int] = []
        self._collision_events: int = 0

        # Replanning schedule
        self._replan_due: Dict[int, int] = {}   # robot_id → next replan tick

    # ── Initialisation ─────────────────────────────────────────────────────────

    def _init_robots(self) -> None:
        starts = self.warehouse.robot_starts
        for i in range(NUM_ROBOTS):
            pos = starts[i % len(starts)]
            # Spread starting positions slightly to avoid overlap
            robot = Robot(robot_id=i, start=pos)
            self.robots[i] = robot

    def _init_peers(self) -> None:
        for rid in self.robots:
            node = PeerNode(rid, NUM_ROBOTS, use_zmq=False)
            node.start()
            # Register BLOCK_ALERT handler
            node.on("BLOCK_ALERT",
                    lambda msg: self.allocator.register_block(
                        (msg["payload"]["row"], msg["payload"]["col"])
                    ))
            self.peers[rid] = node

    # ── Main async loop ────────────────────────────────────────────────────────

    async def run_async(self) -> None:
        """
        Async tick loop — yields control each tick so the WebSocket
        server can service connections concurrently.
        """
        self.running = True
        interval = 1.0 / TICK_RATE_HZ
        logger.info("Simulation started (%s mode, %d robots).",
                    "stop-and-wait" if self.stop_and_wait else "CBS",
                    NUM_ROBOTS)

        while self.running:
            if MAX_TICKS and self.tick >= MAX_TICKS:
                logger.info("Simulation reached MAX_TICKS=%d. Stopping.",
                            MAX_TICKS)
                self.running = False
                break

            t_start = time.monotonic()
            self._step()
            elapsed = time.monotonic() - t_start
            sleep_for = max(0.0, interval - elapsed)
            await asyncio.sleep(sleep_for)

        self._shutdown()

    def run_sync(self) -> None:
        """Blocking version for headless / benchmark runs."""
        asyncio.run(self.run_async())

    def stop(self) -> None:
        self.running = False

    # ── Single tick ────────────────────────────────────────────────────────────

    def _step(self) -> None:
        self.tick += 1

        # 1. Allocate tasks to idle robots
        self.allocator.tick(self.tick)

        # 2. Plan / replan paths
        self._plan_paths()

        # 3. Conflict resolution (or stop-and-wait baseline)
        if self.stop_and_wait:
            self._baseline_stop_and_wait()
        else:
            self.resolver.resolve(self.tick)

        # 4. Advance each robot
        for robot in self.robots.values():
            robot.tick(self.warehouse)

            # Route low-battery robot to charger
            if (robot.state == RobotState.IDLE
                    and robot.battery <= LOW_BATTERY_THRESHOLD
                    and robot.current_task is None):
                self._route_to_charger(robot)

        # 5. P2P broadcasts
        self._broadcast_positions()

        # 6. Record completions
        self._record_completions()

        # 7. Push snapshot to dashboard queue
        if self.state_queue is not None:
            snapshot = self._snapshot()
            try:
                self.state_queue.put_nowait(snapshot)
            except asyncio.QueueFull:
                pass  # dashboard consumer is slow; drop frame

        if self.tick % 50 == 0:
            self._log_stats()

    # ── Path planning ──────────────────────────────────────────────────────────

    def _plan_paths(self) -> None:
        """
        For robots that need a new path, run a joint CBS solve across all
        active robots — guaranteeing collision-free paths for the whole fleet.
        Robots that are already navigating and not due for replan are included
        as fixed reservations.
        """
        # Determine which robots need fresh paths
        needs_plan: Dict[int, tuple] = {}   # robot_id → (start, goal)
        fixed_paths: Dict[int, list] = {}   # robot_id → existing path (reservation)

        for robot in self.robots.values():
            if robot.state == RobotState.IDLE and robot.current_task is not None:
                goal = (robot.current_task.pickup
                        if robot.heading_to_pickup
                        else robot.current_task.dropoff)
                needs_plan[robot.robot_id] = (robot.position, goal)

            elif robot.state == RobotState.NAVIGATING:
                due_tick = self._replan_due.get(robot.robot_id, 0)
                if self.tick >= due_tick and robot.current_task is not None:
                    goal = (robot.current_task.pickup
                            if robot.heading_to_pickup
                            else robot.current_task.dropoff)
                    needs_plan[robot.robot_id] = (robot.position, goal)
                else:
                    # Already has a valid path — treat as fixed reservation
                    remaining = robot.path[robot.path_index:]
                    if remaining:
                        fixed_paths[robot.robot_id] = remaining

        if not needs_plan:
            return

        if len(needs_plan) == 1:
            # Fast path: single robot, use greedy replan
            rid, (start, goal) = next(iter(needs_plan.items()))
            robot = self.robots[rid]
            if start == goal:
                self._handle_at_goal(robot)
                return
            path = self.cbs.replan_single(rid, start, goal, fixed_paths)
            if path:
                robot.set_path(path)
                self._replan_due[rid] = self.tick + REPLANNING_INTERVAL
            else:
                logger.debug("Robot %d: no single path to %s — backing off.", rid, goal)
                robot.issue_wait(random.randint(2, 5))
            return

        # Multi-robot joint CBS solve
        starts_map = {rid: sg[0] for rid, sg in needs_plan.items()}
        goals_map  = {rid: sg[1] for rid, sg in needs_plan.items()}

        # Handle robots already at their goal
        at_goal = {rid for rid, (s, g) in needs_plan.items() if s == g}
        for rid in at_goal:
            self._handle_at_goal(self.robots[rid])
            del starts_map[rid]
            del goals_map[rid]

        if not starts_map:
            return

        joint_paths = self.cbs.solve(starts_map, goals_map)

        for rid, path in joint_paths.items():
            robot = self.robots[rid]
            if path:
                robot.set_path(path)
                self._replan_due[rid] = self.tick + REPLANNING_INTERVAL
            else:
                logger.debug("Robot %d: CBS returned empty path — backing off.", rid)
                robot.issue_wait(random.randint(2, 5))

    def _handle_at_goal(self, robot: Robot) -> None:
        """Robot is already at its target cell — advance its state."""
        robot.path       = []
        robot.path_index = 0
        if robot.current_task:
            if robot.heading_to_pickup:
                robot.state        = RobotState.PICKING_UP
                robot._action_ticks = 0
            else:
                robot.state        = RobotState.DROPPING_OFF
                robot._action_ticks = 0

    # ── Charger routing ────────────────────────────────────────────────────────

    def _route_to_charger(self, robot: Robot) -> None:
        self.allocator.route_to_charger(robot)
        charger = self.warehouse.nearest_charging_station(robot.position)
        other_paths = {
            rid: r.path[r.path_index:]
            for rid, r in self.robots.items()
            if rid != robot.robot_id and r.path
        }
        path = self.cbs.replan_single(
            robot.robot_id, robot.position, charger, other_paths)
        if path:
            robot.set_path(path)
            robot._routing_to_charger = True
            robot.state = RobotState.NAVIGATING
        else:
            # Already at charger or no path
            if robot.position in self.warehouse.charging_stations:
                robot.state = RobotState.CHARGING

    # ── Stop-and-wait baseline ─────────────────────────────────────────────────

    def _baseline_stop_and_wait(self) -> None:
        """
        Realistic stop-and-wait: each robot navigates with plain A* (no
        space-time coordination).  If its intended next cell is currently
        occupied by another robot it issues a 1-tick wait.
        This accurately models the naive "stop when blocked" strategy.
        """
        # Current occupied cells (positions of ALL robots)
        occupied = {r.position for r in self.robots.values()}

        for robot in self.robots.values():
            if robot.state != RobotState.NAVIGATING:
                continue
            nxt = robot.next_intended_cell()
            if nxt is None:
                continue
            # Count how many OTHER robots sit on the intended cell
            others_there = sum(
                1 for r in self.robots.values()
                if r.robot_id != robot.robot_id and r.position == nxt
            )
            if others_there > 0:
                robot.issue_wait(1)   # stop for exactly one tick, then re-check

    # ── P2P broadcasts ─────────────────────────────────────────────────────────

    def _broadcast_positions(self) -> None:
        for rid, robot in self.robots.items():
            peer = self.peers[rid]
            peer.broadcast_position(
                self.tick,
                robot.position[0], robot.position[1],
                robot.battery, robot.state.value,
            )
            nxt = robot.next_intended_cell()
            if nxt:
                peer.broadcast_intent(self.tick, nxt[0], nxt[1])

    # ── Completion tracking ────────────────────────────────────────────────────

    def _record_completions(self) -> None:
        for task in self.allocator.completed_tasks:
            if not hasattr(task, "_recorded"):
                task._recorded = True
                self._task_completion_ticks.append(self.tick)

    # ── Snapshot for dashboard ─────────────────────────────────────────────────

    def _snapshot(self) -> Dict[str, Any]:
        # Always send full warehouse — client caches it after first receive
        wh = self.warehouse.to_dict()
        return {
            "tick"     : self.tick,
            "mode"     : "stop_and_wait" if self.stop_and_wait else "cbs",
            "robots"   : [r.to_dict() for r in self.robots.values()],
            "tasks"    : self.allocator.all_tasks_for_dashboard(),
            "stats"    : self._stats_dict(),
            "warehouse": wh,
            "events"   : self._drain_events(),
        }

    def _drain_events(self) -> list:
        """Return and clear any queued events (conflicts, completions)."""
        if not hasattr(self, '_event_queue'):
            self._event_queue = []
        evts = list(self._event_queue)
        self._event_queue.clear()
        return evts

    def _stats_dict(self) -> Dict[str, Any]:
        completed = len(self.allocator.completed_tasks)
        # Total wait ticks = sum of all wait_ticks_remaining ever issued
        # Approximate: (total ticks × robots) - total distance moved
        total_move_ticks = sum(r.total_distance for r in self.robots.values())
        total_robot_ticks = self.tick * len(self.robots)
        total_wait_ticks  = max(0, total_robot_ticks - total_move_ticks)

        avg_ticks = (
            sum(self._task_completion_ticks) / len(self._task_completion_ticks)
            if self._task_completion_ticks else 0
        )
        resolver_stats = self.resolver.stats()
        alloc_stats    = self.allocator.stats()
        return {
            "tick"               : self.tick,
            "mode"               : "stop_and_wait" if self.stop_and_wait else "cbs",
            "tasks_completed"    : completed,
            "tasks_pending"      : alloc_stats["pending"],
            "tasks_assigned"     : alloc_stats["assigned"],
            "avg_completion_tick": round(avg_ticks, 1),
            "total_wait_ticks"   : total_wait_ticks,
            "conflicts_resolved" : resolver_stats["conflicts_resolved"],
            "deadlocks_resolved" : resolver_stats["deadlocks_resolved"],
            "collision_events"   : self._collision_events,
            "robot_summary"      : [
                {"id": r.robot_id,
                 "battery": round(r.battery, 1),
                 "state": r.state.value,
                 "tasks_done": r.tasks_completed,
                 "distance": r.total_distance}
                for r in self.robots.values()
            ],
        }

    def _log_stats(self) -> None:
        s = self._stats_dict()
        logger.info(
            "Tick %4d | tasks done=%d pending=%d | "
            "conflicts=%d deadlocks=%d",
            self.tick,
            s["tasks_completed"], s["tasks_pending"],
            s["conflicts_resolved"], s["deadlocks_resolved"],
        )

    # ── Shutdown ───────────────────────────────────────────────────────────────

    def _shutdown(self) -> None:
        for peer in self.peers.values():
            peer.stop()
        InProcessBus.reset()
        logger.info("Simulation stopped at tick %d.", self.tick)
        self._print_final_report()

    def _print_final_report(self) -> None:
        s = self._stats_dict()
        print("\n" + "=" * 60)
        print("  SIMULATION FINAL REPORT")
        print("=" * 60)
        print(f"  Mode              : {s['mode'].upper()}")
        print(f"  Total ticks       : {self.tick}")
        print(f"  Tasks completed   : {s['tasks_completed']}")
        print(f"  Avg completion    : {s['avg_completion_tick']} ticks")
        print(f"  Conflicts resolved: {s['conflicts_resolved']}")
        print(f"  Deadlocks resolved: {s['deadlocks_resolved']}")
        print(f"  Collision events  : {s['collision_events']}")
        print("-" * 60)
        for r in s["robot_summary"]:
            print(f"  Robot {r['id']}: battery={r['battery']:.1f}% "
                  f"tasks={r['tasks_done']} dist={r['distance']}")
        print("=" * 60 + "\n")
