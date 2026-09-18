"""
cbs.py — Conflict-Based Search (CBS) for multi-agent path planning.

CBS is a two-level algorithm:
  High level : searches a constraint tree (CT) where each node holds a
               set of constraints and an assignment of paths.
  Low level  : re-runs A* for a single agent given its constraints.

A *constraint* is (robot_id, row, col, time_step) meaning that robot
must not occupy (row, col) at time_step.

An *edge constraint* is (robot_id, from_cell, to_cell, time_step)
preventing a swap collision.

Reference: Sharon et al., "Conflict-based search for optimal
multi-agent pathfinding", AIJ 2015.
"""

from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from core.warehouse import Warehouse
from core.config   import CBS_MAX_ITERATIONS, CBS_TIME_HORIZON
from planning.astar import astar, path_cost, STCell

Cell      = Tuple[int, int]
Path      = List[Cell]
Constraint = Tuple   # (robot_id, row, col, t)  OR  (robot_id, r1,c1,r2,c2, t)


# ── Conflict detection ─────────────────────────────────────────────────────────

@dataclass
class Conflict:
    """Describes a collision between two robots."""
    type: str         # "vertex" or "edge"
    robot_a: int
    robot_b: int
    cell_a: Cell
    cell_b: Cell      # same as cell_a for vertex conflicts
    time: int


def _pad_path(path: Path, length: int) -> Path:
    """Extend path by holding the last position."""
    if not path:
        return path
    return path + [path[-1]] * max(0, length - len(path))


def find_first_conflict(paths: Dict[int, Path]) -> Optional[Conflict]:
    """Return the first vertex or edge conflict in the current set of paths."""
    if not paths:
        return None

    max_t = max(len(p) for p in paths.values())
    robot_ids = list(paths.keys())

    padded = {rid: _pad_path(paths[rid], max_t) for rid in robot_ids}

    for t in range(max_t):
        # Vertex conflicts
        positions: Dict[Cell, int] = {}
        for rid in robot_ids:
            if t < len(padded[rid]):
                pos = padded[rid][t]
                if pos in positions:
                    return Conflict("vertex", positions[pos], rid,
                                    pos, pos, t)
                positions[pos] = rid

        # Edge (swap) conflicts
        if t + 1 < max_t:
            for i in range(len(robot_ids)):
                for j in range(i + 1, len(robot_ids)):
                    ra, rb = robot_ids[i], robot_ids[j]
                    if t < len(padded[ra]) and t + 1 < len(padded[ra]) \
                       and t < len(padded[rb]) and t + 1 < len(padded[rb]):
                        a_from, a_to = padded[ra][t], padded[ra][t + 1]
                        b_from, b_to = padded[rb][t], padded[rb][t + 1]
                        if a_from == b_to and a_to == b_from:
                            return Conflict("edge", ra, rb,
                                            a_from, a_to, t + 1)
    return None


# ── CT node ────────────────────────────────────────────────────────────────────

@dataclass(order=True)
class CTNode:
    """A node in the Constraint Tree."""
    cost: int
    constraints: Set[Constraint] = field(compare=False, default_factory=set)
    paths: Dict[int, Path]       = field(compare=False, default_factory=dict)


# ── CBS solver ────────────────────────────────────────────────────────────────

class CBS:
    """
    Conflict-Based Search solver.

    Usage
    -----
    solver = CBS(warehouse)
    paths  = solver.solve(starts, goals)
    # paths is {robot_id: [list of (row,col) steps]}
    """

    def __init__(self, warehouse: Warehouse) -> None:
        self.warehouse = warehouse

    def _low_level(self,
                   robot_id: int,
                   start: Cell,
                   goal: Cell,
                   constraints: Set[Constraint]) -> Path:
        """Run space-time A* respecting this robot's constraints."""
        # Build reservation table from constraints for this robot
        reserved: Set[STCell] = set()
        for c in constraints:
            if c[0] == robot_id:
                if len(c) == 4:
                    # vertex constraint: (rid, r, col, t)
                    _, r, col, t = c
                    reserved.add((r, col, t))
                elif len(c) == 6:
                    # edge constraint: (rid, r1, c1, r2, c2, t)
                    _, r1, c1, r2, c2, t = c
                    reserved.add((r2, c2, t))  # forbid arriving at r2,c2 at t

        return astar(self.warehouse, start, goal,
                     reserved=reserved,
                     max_time=CBS_TIME_HORIZON)

    def solve(self,
              starts: Dict[int, Cell],
              goals:  Dict[int, Cell]) -> Dict[int, Path]:
        """
        Find collision-free paths for all robots.

        Parameters
        ----------
        starts : {robot_id: (row, col)}
        goals  : {robot_id: (row, col)}

        Returns
        -------
        {robot_id: path}  where path is a list of (row, col) steps.
        Empty path means the robot is already at its goal.
        """
        robot_ids = list(starts.keys())

        # ── Root node ──────────────────────────────────────────────────────────
        root_constraints: Set[Constraint] = set()
        root_paths: Dict[int, Path] = {}

        for rid in robot_ids:
            p = self._low_level(rid, starts[rid], goals[rid],
                                root_constraints)
            root_paths[rid] = p

        root = CTNode(
            cost=sum(path_cost(p) for p in root_paths.values()),
            constraints=root_constraints,
            paths=root_paths,
        )

        open_list: List[CTNode] = [root]
        heapq.heapify(open_list)
        iterations = 0

        while open_list and iterations < CBS_MAX_ITERATIONS:
            iterations += 1
            node = heapq.heappop(open_list)

            conflict = find_first_conflict(node.paths)
            if conflict is None:
                # Solution found!
                return node.paths

            # ── Branch on conflict ─────────────────────────────────────────────
            for affected_rid in (conflict.robot_a, conflict.robot_b):
                new_constraints = set(node.constraints)

                if conflict.type == "vertex":
                    r, c = conflict.cell_a
                    new_constraints.add(
                        (affected_rid, r, c, conflict.time)
                    )
                else:  # edge
                    # Prevent the robot from making the swap move
                    if affected_rid == conflict.robot_a:
                        fr, fc = conflict.cell_a
                        tr, tc = conflict.cell_b
                    else:
                        fr, fc = conflict.cell_b
                        tr, tc = conflict.cell_a
                    new_constraints.add(
                        (affected_rid, fr, fc, tr, tc, conflict.time)
                    )

                new_paths = dict(node.paths)
                new_path  = self._low_level(affected_rid,
                                            starts[affected_rid],
                                            goals[affected_rid],
                                            new_constraints)
                if new_path is not None:
                    new_paths[affected_rid] = new_path
                    child = CTNode(
                        cost=sum(path_cost(p) for p in new_paths.values()),
                        constraints=new_constraints,
                        paths=new_paths,
                    )
                    heapq.heappush(open_list, child)

        # CBS did not converge — return best effort paths from root
        return root_paths

    def replan_single(self,
                      robot_id: int,
                      start: Cell,
                      goal: Cell,
                      other_paths: Dict[int, Path]) -> Path:
        """
        Quickly replan a single robot's path given other robots' paths as
        reservations (used by the conflict resolver for fast local replanning).
        """
        reserved: Set[STCell] = set()
        for rid, path in other_paths.items():
            if rid == robot_id:
                continue
            for t, (r, c) in enumerate(path):
                reserved.add((r, c, t))
            if path:
                lr, lc = path[-1]
                for et in range(len(path), len(path) + 20):
                    reserved.add((lr, lc, et))

        return astar(self.warehouse, start, goal,
                     reserved=reserved,
                     max_time=CBS_TIME_HORIZON)
