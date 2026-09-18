"""
warehouse.py — Grid-based warehouse map.

Cell types
----------
  0  : free aisle
  1  : permanent obstacle / shelf unit
  2  : charging station
  3  : pickup point  (set dynamically by task allocator)
  4  : dropoff point (set dynamically by task allocator)

Coordinates are (row, col) with (0,0) at the top-left.
"""

from __future__ import annotations
import random
from typing import List, Tuple, Set, Dict, Optional
from core.config import GRID_ROWS, GRID_COLS, RANDOM_SEED

# ── Cell-type constants ────────────────────────────────────────────────────────
FREE     = 0
OBSTACLE = 1
CHARGING = 2
PICKUP   = 3
DROPOFF  = 4

Cell = Tuple[int, int]   # (row, col)


class Warehouse:
    """
    Represents the physical warehouse as a 2-D grid.

    The layout is generated once from a fixed seed so every run
    uses the same map unless explicitly regenerated.
    """

    def __init__(self,
                 rows: int = GRID_ROWS,
                 cols: int = GRID_COLS,
                 seed: int = RANDOM_SEED) -> None:
        self.rows = rows
        self.cols = cols
        self.seed = seed

        # grid[r][c] → cell type
        self.grid: List[List[int]] = [[FREE] * cols for _ in range(rows)]

        # Special locations
        self.charging_stations: List[Cell] = []
        self.pickup_points: List[Cell]     = []
        self.dropoff_points: List[Cell]    = []
        self.robot_starts: List[Cell]      = []

        self._build_layout()

    # ── Layout construction ────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        """
        Builds a realistic warehouse layout:
        - Horizontal shelf rows with clear aisles between them
        - Vertical cross-aisles every N columns
        - Charging stations along the south wall
        - Pickup points on the west side, dropoff on the east side
        - Robot starting positions near charging stations
        """
        rng = random.Random(self.seed)

        # ── Shelf rows ─────────────────────────────────────────────────────────
        # Shelves occupy alternating rows starting at row 2, skipping every 4th
        # row (the aisle).  Also leave col 0 and col-1 as border aisles.
        shelf_rows = [r for r in range(2, self.rows - 3, 4)]
        aisle_cols = {0, 1, self.cols - 1, self.cols - 2}      # always clear
        cross_aisle_cols = set(range(0, self.cols, 5))          # vertical aisles

        for r in shelf_rows:
            for c in range(self.cols):
                if c not in aisle_cols and c not in cross_aisle_cols:
                    self.grid[r][c]     = OBSTACLE
                    self.grid[r + 1][c] = OBSTACLE   # shelves are 2 cells deep

        # ── Charging stations (south wall) ─────────────────────────────────────
        charge_row = self.rows - 1
        charge_cols = [1, self.cols // 2 - 1, self.cols - 2]
        for c in charge_cols:
            self.grid[charge_row][c] = CHARGING
            self.charging_stations.append((charge_row, c))

        # ── Pickup points (west aisle, scattered) ──────────────────────────────
        for r in range(1, self.rows - 2, 3):
            if self.grid[r][1] == FREE:
                self.grid[r][1] = PICKUP
                self.pickup_points.append((r, 1))

        # ── Dropoff points (east aisle, scattered) ─────────────────────────────
        for r in range(2, self.rows - 2, 3):
            if self.grid[r][self.cols - 2] == FREE:
                self.grid[r][self.cols - 2] = DROPOFF
                self.dropoff_points.append((r, self.cols - 2))

        # ── Robot starting positions (near charging) ───────────────────────────
        starts = [
            (self.rows - 2, 1),
            (self.rows - 2, self.cols // 2 - 1),
            (self.rows - 2, self.cols - 2),
            (self.rows - 3, 1),
            (self.rows - 3, self.cols // 2 - 1),
            (self.rows - 3, self.cols - 2),
            (self.rows - 4, 1),
            (self.rows - 4, self.cols // 2 - 1),
        ]
        for s in starts:
            r, c = s
            if self.in_bounds(r, c) and self.grid[r][c] == FREE:
                self.robot_starts.append(s)

    # ── Query helpers ──────────────────────────────────────────────────────────

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_passable(self, r: int, c: int) -> bool:
        """True if a robot can move onto this cell."""
        if not self.in_bounds(r, c):
            return False
        return self.grid[r][c] != OBSTACLE

    def neighbors(self, r: int, c: int) -> List[Cell]:
        """4-connected passable neighbors."""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        result = []
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if self.is_passable(nr, nc):
                result.append((nr, nc))
        return result

    def cell_type(self, r: int, c: int) -> int:
        return self.grid[r][c]

    def nearest_charging_station(self, pos: Cell) -> Cell:
        """Return the closest charging station to pos."""
        return min(self.charging_stations,
                   key=lambda cs: abs(cs[0] - pos[0]) + abs(cs[1] - pos[1]))

    def free_cells(self) -> List[Cell]:
        """All traversable non-obstacle cells."""
        return [(r, c)
                for r in range(self.rows)
                for c in range(self.cols)
                if self.is_passable(r, c)]

    def to_dict(self) -> Dict:
        """Serialise for dashboard transmission."""
        return {
            "rows": self.rows,
            "cols": self.cols,
            "grid": self.grid,
            "charging_stations": list(self.charging_stations),
            "pickup_points":     list(self.pickup_points),
            "dropoff_points":    list(self.dropoff_points),
        }

    def __repr__(self) -> str:
        symbols = {FREE: "·", OBSTACLE: "█", CHARGING: "⚡", PICKUP: "P", DROPOFF: "D"}
        lines = []
        for row in self.grid:
            lines.append(" ".join(symbols.get(c, "?") for c in row))
        return "\n".join(lines)
