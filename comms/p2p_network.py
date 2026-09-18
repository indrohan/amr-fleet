"""
p2p_network.py — Decentralised peer-to-peer communication layer.

Design
------
Each robot runs its own *PeerNode*.  A PeerNode binds a ZeroMQ PUB
socket on a unique port (BASE_PUB_PORT + robot_id) and connects a SUB
socket to every other robot's PUB port.  There is **no central broker**.

Message format (JSON envelope):
  {
    "type"      : str,        # e.g. "POSITION", "INTENT", "TASK_BID",
                              #      "TASK_AWARD", "BLOCK_ALERT", "PING"
    "sender_id" : int,
    "tick"      : int,
    "payload"   : dict
  }

Message types
─────────────
  POSITION    : broadcast current (row, col) and battery every tick
  INTENT      : broadcast next planned cell (for pre-emptive conflict check)
  TASK_BID    : robot bids on an unassigned task (auction-based allocation)
  TASK_AWARD  : highest-bidder robot is awarded a task
  BLOCK_ALERT : robot reports a blocked aisle / obstacle it discovered
  PING        : heartbeat (used for liveness detection)

In simulation mode (no real ZeroMQ hardware), the network can be run in
*in-process* mode where messages pass through Python queues — keeping
the simulation fast and deterministic while preserving the exact same
API as the ZeroMQ version.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Message helpers ────────────────────────────────────────────────────────────

def make_message(msg_type: str, sender_id: int,
                 tick: int, payload: Dict) -> Dict:
    return {
        "type"      : msg_type,
        "sender_id" : sender_id,
        "tick"      : tick,
        "payload"   : payload,
    }


# ── In-process bus (simulation mode) ─────────────────────────────────────────

class InProcessBus:
    """
    A shared message bus for in-process simulation.
    Replaces real ZeroMQ sockets so the simulation runs without
    needing open ports or network hardware.
    """
    _instance: Optional["InProcessBus"] = None

    def __new__(cls) -> "InProcessBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers: Dict[int, queue.Queue] = {}
            cls._instance._lock = threading.Lock()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def register(self, robot_id: int) -> queue.Queue:
        with self._lock:
            q: queue.Queue = queue.Queue(maxsize=256)
            self._subscribers[robot_id] = q
            return q

    def publish(self, sender_id: int, message: Dict) -> None:
        """Deliver message to every subscriber except the sender."""
        raw = json.dumps(message)
        with self._lock:
            for rid, q in self._subscribers.items():
                if rid != sender_id:
                    try:
                        q.put_nowait(raw)
                    except queue.Full:
                        pass  # drop if queue full (simulates packet loss)

    def unregister(self, robot_id: int) -> None:
        with self._lock:
            self._subscribers.pop(robot_id, None)


# ── PeerNode ──────────────────────────────────────────────────────────────────

class PeerNode:
    """
    Communication endpoint for one AMR.

    In simulation mode (use_zmq=False) messages route through the
    shared InProcessBus.  When use_zmq=True the node binds real ZeroMQ
    sockets for deployment on actual edge hardware.
    """

    def __init__(self,
                 robot_id: int,
                 num_robots: int,
                 use_zmq: bool = False) -> None:
        self.robot_id   = robot_id
        self.num_robots = num_robots
        self.use_zmq    = use_zmq

        self._handlers: Dict[str, List[Callable]] = {}
        self._running   = False
        self._rx_thread: Optional[threading.Thread] = None

        # Latency / packet-loss stats
        self.msgs_sent     = 0
        self.msgs_received = 0

        if use_zmq:
            self._init_zmq()
        else:
            self._bus = InProcessBus()
            self._rx_queue = self._bus.register(robot_id)

    # ── ZeroMQ setup (real hardware mode) ─────────────────────────────────────

    def _init_zmq(self) -> None:
        try:
            import zmq
            from core.config import BASE_PUB_PORT
            ctx = zmq.Context.instance()

            # PUB socket — bind
            self._pub = ctx.socket(zmq.PUB)
            self._pub.bind(f"tcp://*:{BASE_PUB_PORT + self.robot_id}")

            # SUB socket — connect to all peers
            self._sub = ctx.socket(zmq.SUB)
            self._sub.setsockopt(zmq.SUBSCRIBE, b"")
            for i in range(self.num_robots):
                if i != self.robot_id:
                    self._sub.connect(
                        f"tcp://localhost:{BASE_PUB_PORT + i}")
            time.sleep(0.05)   # allow ZMQ connections to settle
        except ImportError:
            logger.warning("pyzmq not installed — falling back to in-process bus.")
            self.use_zmq   = False
            self._bus      = InProcessBus()
            self._rx_queue = self._bus.register(self.robot_id)

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._running  = True
        self._rx_thread = threading.Thread(
            target=self._receive_loop,
            name=f"rx-robot-{self.robot_id}",
            daemon=True,
        )
        self._rx_thread.start()

    def stop(self) -> None:
        self._running = False
        if not self.use_zmq:
            self._bus.unregister(self.robot_id)

    # ── Send ───────────────────────────────────────────────────────────────────

    def send(self, msg_type: str, tick: int, payload: Dict) -> None:
        msg = make_message(msg_type, self.robot_id, tick, payload)
        self.msgs_sent += 1

        if self.use_zmq:
            self._pub.send_string(json.dumps(msg))
        else:
            self._bus.publish(self.robot_id, msg)

    def broadcast_position(self, tick: int, row: int, col: int,
                           battery: float, state: str) -> None:
        self.send("POSITION", tick, {
            "row": row, "col": col,
            "battery": battery, "state": state,
        })

    def broadcast_intent(self, tick: int,
                         next_row: int, next_col: int) -> None:
        self.send("INTENT", tick, {
            "next_row": next_row, "next_col": next_col,
        })

    def send_task_bid(self, tick: int, task_id: int, bid_value: float) -> None:
        self.send("TASK_BID", tick, {
            "task_id": task_id, "bid": bid_value,
        })

    def send_task_award(self, tick: int, task_id: int,
                        winner_id: int) -> None:
        self.send("TASK_AWARD", tick, {
            "task_id": task_id, "winner_id": winner_id,
        })

    def send_block_alert(self, tick: int, row: int, col: int) -> None:
        self.send("BLOCK_ALERT", tick, {"row": row, "col": col})

    # ── Receive loop ───────────────────────────────────────────────────────────

    def _receive_loop(self) -> None:
        while self._running:
            try:
                if self.use_zmq:
                    # Non-blocking poll every 5 ms
                    if self._sub.poll(timeout=5):
                        raw = self._sub.recv_string()
                        self._dispatch(raw)
                else:
                    raw = self._rx_queue.get(timeout=0.005)
                    self._dispatch(raw)
            except Exception:
                pass

    def _dispatch(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
            self.msgs_received += 1
            msg_type = msg.get("type", "")
            for handler in self._handlers.get(msg_type, []):
                handler(msg)
            for handler in self._handlers.get("*", []):
                handler(msg)
        except json.JSONDecodeError:
            pass

    # ── Handler registration ───────────────────────────────────────────────────

    def on(self, msg_type: str, handler: Callable) -> None:
        """Register a callback for a specific message type (or '*' for all)."""
        self._handlers.setdefault(msg_type, []).append(handler)

    # ── Peer state cache ───────────────────────────────────────────────────────
    # Each robot maintains a local snapshot of all peers (updated via POSITION msgs)

    def build_peer_cache(self) -> "PeerStateCache":
        cache = PeerStateCache(self.robot_id)
        self.on("POSITION", cache.update)
        return cache


class PeerStateCache:
    """
    Thread-safe cache of the latest known state of every peer robot.
    Updated automatically as POSITION messages arrive.
    """

    def __init__(self, owner_id: int) -> None:
        self.owner_id = owner_id
        self._cache: Dict[int, Dict] = {}
        self._lock  = threading.Lock()

    def update(self, msg: Dict) -> None:
        sid = msg["sender_id"]
        with self._lock:
            self._cache[sid] = {
                "row"    : msg["payload"]["row"],
                "col"    : msg["payload"]["col"],
                "battery": msg["payload"]["battery"],
                "state"  : msg["payload"]["state"],
                "tick"   : msg["tick"],
            }

    def get_all(self) -> Dict[int, Dict]:
        with self._lock:
            return dict(self._cache)

    def get(self, robot_id: int) -> Optional[Dict]:
        with self._lock:
            return self._cache.get(robot_id)
