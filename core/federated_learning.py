"""
federated_learning.py — Federated Learning across AMRs.

How it works
────────────
Each robot maintains a LOCAL model (weight vector) that learns from its
own navigation experience.  Every FL_ROUND_INTERVAL ticks the engine
aggregates all local models using FedAvg (weighted by data count) into a
GLOBAL model that is pushed back to every robot.

What the model learns
─────────────────────
  Input features (per cell/step):
    - congestion level of next cell (0–1)
    - battery normalised (0–1)
    - distance to goal (normalised)
    - time-of-tick normalised

  Output: predicted delay penalty for taking that step (0–1)

This delay penalty is used by the Predictive Flow Optimizer to bias
routing decisions — cells with high predicted delay are avoided.

In simulation this is approximated with a simple linear model + online
gradient descent.  The key property: each robot learns independently,
privacy is preserved, and the global model improves over time.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
FL_ROUND_INTERVAL  = 50     # ticks between federation rounds
LEARNING_RATE      = 0.05
NUM_FEATURES       = 4
NUM_HIDDEN         = 8      # tiny hidden layer
MIN_SAMPLES_TO_FL  = 5      # robot needs this many samples before contributing


@dataclass
class LocalModel:
    robot_id: int
    # Weights: input→hidden (NUM_FEATURES × NUM_HIDDEN) + hidden→output (NUM_HIDDEN)
    W1: List[List[float]] = field(default_factory=list)
    b1: List[float] = field(default_factory=list)
    W2: List[float] = field(default_factory=list)
    b2: float = 0.0
    sample_count: int = 0
    total_loss: float = 0.0
    rounds_participated: int = 0

    def __post_init__(self):
        if not self.W1:
            rng = random.Random(self.robot_id * 42)
            self.W1 = [[rng.gauss(0, 0.1) for _ in range(NUM_HIDDEN)]
                       for _ in range(NUM_FEATURES)]
            self.b1 = [rng.gauss(0, 0.1) for _ in range(NUM_HIDDEN)]
            self.W2 = [rng.gauss(0, 0.1) for _ in range(NUM_HIDDEN)]
            self.b2 = 0.0

    def _forward(self, x: List[float]):
        # Hidden layer (ReLU)
        h = []
        for j in range(NUM_HIDDEN):
            z = self.b1[j] + sum(x[i] * self.W1[i][j] for i in range(NUM_FEATURES))
            h.append(max(0.0, z))
        # Output (sigmoid)
        out = self.b2 + sum(h[j] * self.W2[j] for j in range(NUM_HIDDEN))
        return 1.0 / (1.0 + math.exp(-max(-10, min(10, out)))), h

    def predict(self, features: List[float]) -> float:
        pred, _ = self._forward(features)
        return pred

    def update(self, features: List[float], target: float) -> float:
        """Online gradient descent — one sample."""
        pred, h = self._forward(features)
        err = pred - target
        loss = err * err

        # Sigmoid derivative: pred*(1-pred)
        d_out = err * pred * (1.0 - pred)

        # Backprop W2, b2
        for j in range(NUM_HIDDEN):
            self.W2[j] -= LEARNING_RATE * d_out * h[j]
        self.b2 -= LEARNING_RATE * d_out

        # Backprop W1, b1 (ReLU derivative)
        for j in range(NUM_HIDDEN):
            if h[j] > 0:
                d_h = d_out * self.W2[j]
                for i in range(NUM_FEATURES):
                    self.W1[i][j] -= LEARNING_RATE * d_h * features[i]
                self.b1[j] -= LEARNING_RATE * d_h

        self.sample_count += 1
        self.total_loss   += loss
        return loss

    def get_weights(self):
        return {
            "W1": [row[:] for row in self.W1],
            "b1": self.b1[:],
            "W2": self.W2[:],
            "b2": self.b2,
        }

    def set_weights(self, w):
        self.W1 = [row[:] for row in w["W1"]]
        self.b1 = w["b1"][:]
        self.W2 = w["W2"][:]
        self.b2 = w["b2"]
        self.rounds_participated += 1


class FederatedLearningCoordinator:
    """
    Central coordinator that:
    1. Collects local model updates from each robot
    2. Runs FedAvg every FL_ROUND_INTERVAL ticks
    3. Pushes the global model back to all robots
    4. Exposes predict() for the Predictive Flow Optimizer
    """

    def __init__(self, robot_ids: List[int]) -> None:
        self.local_models: Dict[int, LocalModel] = {
            rid: LocalModel(robot_id=rid) for rid in robot_ids
        }
        self.global_weights = None
        self.round_number   = 0
        self.fl_history: List[Dict] = []   # for dashboard
        self._pending_events: List[Dict] = []

    # ── Called each tick by simulation ────────────────────────────────────────

    def tick(self, tick: int, robots: dict, congestion_map: dict) -> None:
        # 1. Each robot generates a training sample from its current experience
        for rid, robot in robots.items():
            feat = self._extract_features(robot, congestion_map)
            target = self._compute_target(robot, congestion_map)
            loss = self.local_models[rid].update(feat, target)

        # 2. Federation round
        if tick % FL_ROUND_INTERVAL == 0 and tick > 0:
            self._federate(tick)

    def _extract_features(self, robot, congestion_map: dict) -> List[float]:
        from core.config import BATTERY_CAPACITY
        row, col = robot.position
        cong = congestion_map.get((row, col), 0.0)
        bat_norm = robot.battery / BATTERY_CAPACITY
        # Distance to goal (normalised to 0–1 over 30 cells)
        if robot.current_task:
            goal = robot.current_task.pickup if robot.heading_to_pickup else robot.current_task.dropoff
            dist = abs(goal[0] - row) + abs(goal[1] - col)
        else:
            dist = 0
        dist_norm = min(1.0, dist / 30.0)
        tick_norm = (getattr(robot, 'ticks_alive', 0) % 100) / 100.0
        return [cong, bat_norm, dist_norm, tick_norm]

    def _compute_target(self, robot, congestion_map: dict) -> float:
        """Target = normalised delay indicator."""
        from core.robot import RobotState
        if robot.state == RobotState.WAITING:
            return 1.0
        if robot.state == RobotState.NAVIGATING:
            row, col = robot.position
            return min(1.0, congestion_map.get((row, col), 0.0) * 2)
        return 0.0

    # ── FedAvg aggregation ────────────────────────────────────────────────────

    def _federate(self, tick: int) -> None:
        eligible = [m for m in self.local_models.values()
                    if m.sample_count >= MIN_SAMPLES_TO_FL]
        if len(eligible) < 2:
            return

        total_samples = sum(m.sample_count for m in eligible)
        avg_loss = sum(m.total_loss for m in eligible) / max(1, total_samples)

        # Weighted average of weights
        agg_W1 = [[0.0] * NUM_HIDDEN for _ in range(NUM_FEATURES)]
        agg_b1 = [0.0] * NUM_HIDDEN
        agg_W2 = [0.0] * NUM_HIDDEN
        agg_b2 = 0.0

        for m in eligible:
            w_frac = m.sample_count / total_samples
            for i in range(NUM_FEATURES):
                for j in range(NUM_HIDDEN):
                    agg_W1[i][j] += w_frac * m.W1[i][j]
            for j in range(NUM_HIDDEN):
                agg_b1[j] += w_frac * m.b1[j]
                agg_W2[j] += w_frac * m.W2[j]
            agg_b2 += w_frac * m.b2

        self.global_weights = {"W1": agg_W1, "b1": agg_b1, "W2": agg_W2, "b2": agg_b2}
        self.round_number  += 1

        # Push global model to all robots
        for m in self.local_models.values():
            m.set_weights(self.global_weights)

        self.fl_history.append({
            "tick": tick, "round": self.round_number,
            "participants": len(eligible),
            "avg_loss": round(avg_loss, 4),
        })
        self._pending_events.append({
            "tick": tick, "type": "FL_ROUND",
            "round": self.round_number,
            "participants": len(eligible),
            "avg_loss": round(avg_loss, 4),
            "detail": f"FL Round {self.round_number}: {len(eligible)} robots aggregated, avg loss={avg_loss:.4f}"
        })
        logger.info("FL Round %d: %d robots, avg_loss=%.4f", self.round_number, len(eligible), avg_loss)

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict_delay(self, robot_id: int, features: List[float]) -> float:
        """Predict delay penalty for a robot at given features."""
        return self.local_models[robot_id].predict(features)

    def global_predict(self, features: List[float]) -> float:
        """Use global model if available, else average of locals."""
        if self.global_weights:
            tmp = LocalModel(robot_id=-1)
            tmp.set_weights(self.global_weights)
            return tmp.predict(features)
        preds = [m.predict(features) for m in self.local_models.values()]
        return sum(preds) / max(1, len(preds))

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def drain_events(self) -> List[Dict]:
        evts = list(self._pending_events)
        self._pending_events.clear()
        return evts

    def dashboard_summary(self) -> Dict:
        return {
            "round": self.round_number,
            "robots_trained": sum(1 for m in self.local_models.values() if m.sample_count > 0),
            "total_robots": len(self.local_models),
            "recent_rounds": self.fl_history[-5:],
            "global_model_ready": self.global_weights is not None,
        }
