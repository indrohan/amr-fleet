"""
astar.py — A* single-agent pathfinding on the warehouse grid.

Returns a list of (row, col) cells from start (exclusive) to goal
(inclusive), or an empty list if no path exists.

Space-time variant
------------------
When `reserved_cells` is provided (a set of (row, col, time_step)
tuples), the planner avoids cells already claimed by other robots at
each time step — this is the foundation for the CBS low-level solver.
"""

from __future__ import annotations
import heapq
from typing import List, Tuple, Set, Optional, Dict

from core.warehouse import Warehouse

Cell      = Tuple[int, int]
STCell    = Tuple[int, int, int]   # (row, col, t)
Path      = List[Cell]


# ── Heuristic ──────────────────────────────────────────────────────────────────

def _manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ── Standard A* ───────────────────────────────────────────────────────────────

def astar(warehouse: Warehouse,
          start: Cell,
          goal: Cell,
          reserved: Optional[Set[STCell]] = None,
          max_time: int = 200) -> Path:
    """
    A* (space-time aware when `reserved` is given).

    Parameters
    ----------
    warehouse : Warehouse
        The map to plan on.
    start : (row, col)
        Robot's current cell (NOT included in returned path).
    goal : (row, col)
        Target cell (included in returned path).
    reserved : set of (row, col, t), optional
        Space-time reservations from other robots.
    max_time : int
        Maximum number of time steps to search.

    Returns
    -------
    List of (row, col) from start+1 step to goal, or [] if unreachable.
    """
    if start == goal:
        return []

    if reserved is None:
        reserved = set()

    # Each node: (f, g, (row, col, t), parent)
    # We track time so we can check space-time reservations.
    open_heap: List[Tuple[int, int, STCell]] = []
    start_st: STCell = (start[0], start[1], 0)
    heapq.heappush(open_heap, (0, 0, start_st))

    came_from: Dict[STCell, Optional[STCell]] = {start_st: None}
    g_score:   Dict[STCell, int]              = {start_st: 0}

    while open_heap:
        f, g, current = heapq.heappop(open_heap)
        cr, cc, ct = current

        # Goal check — accept as soon as we reach goal cell at any time
        if (cr, cc) == goal:
            return _reconstruct(came_from, current)

        if ct >= max_time:
            continue

        nt = ct + 1

        # ── Expand neighbours (move + wait-in-place) ───────────────────────────
        moves: List[Cell] = warehouse.neighbors(cr, cc)
        moves.append((cr, cc))   # wait action

        for nr, nc in moves:
            nst: STCell = (nr, nc, nt)

            # Space-time reservation check
            if nst in reserved:
                continue
            # Edge-swap collision: if another robot is moving the opposite way
            swap: STCell = (cr, cc, nt)   # other robot would occupy our cell
            if (nr, nc, ct) in reserved and swap in reserved:
                continue

            new_g = g + 1
            if new_g < g_score.get(nst, float("inf")):
                g_score[nst]  = new_g
                came_from[nst] = current
                h = _manhattan((nr, nc), goal)
                heapq.heappush(open_heap, (new_g + h, new_g, nst))

    return []   # no path found


# ── Path reconstruction ────────────────────────────────────────────────────────

def _reconstruct(came_from: Dict[STCell, Optional[STCell]],
                 node: STCell) -> Path:
    path: Path = []
    current: Optional[STCell] = node
    while current is not None:
        r, c, _ = current
        path.append((r, c))
        current = came_from[current]
    path.reverse()
    return path[1:]   # drop the start cell itself


# ── Utility: build reservation table from existing paths ──────────────────────

def build_reservation_table(paths: Dict[int, Path],
                             exclude_id: int = -1) -> Set[STCell]:
    """
    Convert a dict of {robot_id: path} into a set of (row, col, t)
    reservations, skipping `exclude_id`.
    """
    reserved: Set[STCell] = set()
    for rid, path in paths.items():
        if rid == exclude_id:
            continue
        for t, (r, c) in enumerate(path):
            reserved.add((r, c, t))
        # Hold goal position indefinitely after path ends
        if path:
            lr, lc = path[-1]
            for extra_t in range(len(path), len(path) + 20):
                reserved.add((lr, lc, extra_t))
    return reserved


# ── Path cost helper ──────────────────────────────────────────────────────────

def path_cost(path: Path) -> int:
    """Sum-of-costs metric (number of moves)."""
    return len(path)
