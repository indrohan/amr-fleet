"""
config.py — All tuneable simulation parameters in one place.
Edge-AI AMR Fleet Coordination | BEL Problem Statement
"""

# ── Warehouse grid ─────────────────────────────────────────────────────────────
GRID_ROWS = 16          # number of rows
GRID_COLS = 16          # number of columns
CELL_SIZE_M = 1.0       # each cell represents 1 metre

# ── Fleet ──────────────────────────────────────────────────────────────────────
NUM_ROBOTS = 8          # total AMRs in simulation
ROBOT_SPEED = 1.0       # cells per simulation tick
BATTERY_CAPACITY = 100.0          # % full charge
BATTERY_DRAIN_PER_MOVE = 0.3      # % per cell moved
BATTERY_DRAIN_IDLE = 0.02         # % per tick while waiting
BATTERY_CHARGE_RATE = 2.0         # % per tick while at charging station
LOW_BATTERY_THRESHOLD = 15.0      # robot seeks charging below this %

# ── Task generation ────────────────────────────────────────────────────────────
NUM_INITIAL_TASKS = 15            # tasks pre-loaded at start
TASK_GENERATION_INTERVAL = 30     # ticks between random new tasks
MAX_PENDING_TASKS = 20            # cap on task queue depth

# ── Path planning ──────────────────────────────────────────────────────────────
CBS_MAX_ITERATIONS = 1000         # CBS solver iteration cap
CBS_TIME_HORIZON = 150            # ticks to plan ahead (> longest possible path)
ASTAR_DIAGONAL = False            # allow diagonal moves
REPLANNING_INTERVAL = 15          # ticks between forced replans

# ── Conflict resolution ────────────────────────────────────────────────────────
DEADLOCK_DETECTION_WINDOW = 8     # ticks without progress = suspect deadlock
BACKOFF_MIN_TICKS = 2
BACKOFF_MAX_TICKS = 6
PRIORITY_SCHEME = "battery_first" # options: "id_order", "battery_first", "task_urgency"

# ── P2P Communication ──────────────────────────────────────────────────────────
BASE_PUB_PORT = 5550              # robot i publishes on 5550+i
BROADCAST_INTERVAL = 1            # ticks between position broadcasts
MSG_TTL = 3                       # max hops for a routed message

# ── Simulation timing ──────────────────────────────────────────────────────────
TICK_RATE_HZ = 4                  # simulation steps per second (realtime)
MAX_TICKS = 2000                  # stop after this many ticks (0 = infinite)
RANDOM_SEED = 42

# ── Conflict scenario tuning ───────────────────────────────────────────────────
# Tighter cross-aisles create more choke-point conflicts
CROSS_AISLE_SPACING = 6           # every N columns is a cross-aisle (lower = tighter)

# ── Dashboard / WebSocket ──────────────────────────────────────────────────────
WS_HOST = "localhost"
WS_PORT = 8765
HTTP_HOST = "localhost"
HTTP_PORT = 8080

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_DIR = "logs"
LOG_LEVEL = "INFO"                # DEBUG | INFO | WARNING
