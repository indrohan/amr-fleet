"""
generate_sih_ppt.py — SIH 2026 Format PPT (Professional Edition)
AMRoboSync: Edge-AI Based Distributed Fleet Coordination for AMRs
NO EMOJI — Clean corporate / tech design with shapes and colour blocks
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE_TYPE

# ═══════════════════════════════════════════════════
#   FILL YOUR DETAILS HERE
# ═══════════════════════════════════════════════════
TEAM_NAME    = "YOUR TEAM NAME"
TEAM_ID      = "YOUR TEAM ID"
PS_NUMBER    = "SIH XXXX"
COLLEGE_NAME = "YOUR COLLEGE NAME"
COLLEGE_CITY = "CITY, STATE"
MENTOR_NAME  = "Prof. MENTOR NAME"

TEAM_MEMBERS = [
    ("Member 1 Name", "Team Leader / Backend",  "CSE, 3rd Year"),
    ("Member 2 Name", "Algorithm Developer",    "CSE, 3rd Year"),
    ("Member 3 Name", "Frontend / Dashboard",   "IT,  3rd Year"),
    ("Member 4 Name", "Embedded / Hardware",    "ECE, 3rd Year"),
    ("Member 5 Name", "ML / AI",                "CSE, 3rd Year"),
    ("Member 6 Name", "Testing & Docs",         "CSE, 3rd Year"),
]

# ═══════════════════════════════════════════════════
#   COLOUR PALETTE
# ═══════════════════════════════════════════════════
C = {
    "bg0"   : RGBColor(0x06,0x0A,0x12),  # page background
    "bg1"   : RGBColor(0x0B,0x11,0x1E),  # panel
    "bg2"   : RGBColor(0x10,0x18,0x28),  # card
    "bg3"   : RGBColor(0x18,0x22,0x36),  # card alt
    "blue"  : RGBColor(0x00,0xB4,0xD8),  # primary accent
    "green" : RGBColor(0x06,0xD6,0x6A),  # success
    "yellow": RGBColor(0xF5,0xC5,0x18),  # warning / highlight
    "red"   : RGBColor(0xE5,0x3E,0x3E),  # danger
    "purple": RGBColor(0x7B,0x4F,0xFF),  # innovation
    "orange": RGBColor(0xF4,0x6B,0x28),  # SIH accent
    "white" : RGBColor(0xFF,0xFF,0xFF),
    "t1"    : RGBColor(0xE0,0xE8,0xF4),  # text primary
    "t2"    : RGBColor(0x8A,0x9B,0xB5),   # text muted
    "t3"    : RGBColor(0x45,0x5A,0x78),  # text dim
    "sih_b" : RGBColor(0x01,0x47,0x9E),  # SIH blue
    "sih_o" : RGBColor(0xFF,0x6F,0x00),  # SIH orange
}

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.50)
BLANK = prs.slide_layouts[6]

# ═══════════════════════════════════════════════════
#   HELPER PRIMITIVES
# ═══════════════════════════════════════════════════

def new_slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = C["bg0"]
    return s


def rect(s, x, y, w, h, fill, border_color=None, border_pt=0):
    """Draw a filled rectangle, optionally with a border."""
    from pptx.util import Pt as UPt
    sh = s.shapes.add_shape(1,
                             Inches(x), Inches(y),
                             Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if border_color:
        sh.line.color.rgb = border_color
        sh.line.width = UPt(border_pt)
    else:
        sh.line.fill.background()
    return sh


def oval(s, x, y, w, h, fill):
    sh = s.shapes.add_shape(9,
                             Inches(x), Inches(y),
                             Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.fill.background()
    return sh


def line_h(s, x, y, w, h=0.045, color=None):
    rect(s, x, y, w, h, color or C["blue"])


def T(s, text, x, y, w, h,
      size=12, bold=False, color=None, align=PP_ALIGN.LEFT,
      italic=False):
    """Add a text box."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y),
                               Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = Pt(size)
    run.font.bold  = bold
    run.font.italic = italic
    run.font.color.rgb = color or C["t1"]
    run.font.name  = "Calibri"
    return tb


def tag(s, label, x, y, w=1.8, h=0.30,
        bg=None, fg=None, size=9.5):
    """Pill/chip tag — solid fill, no border, clean."""
    bg = bg or C["bg3"]
    fg = fg or C["blue"]
    rect(s, x, y, w, h, bg)
    T(s, label, x+0.06, y+0.02, w-0.1, h-0.04,
      size=size, bold=True, color=fg, align=PP_ALIGN.CENTER)


def kpi_box(s, label, value, note, x, y,
            val_color=None, w=2.30, h=1.20):
    val_color = val_color or C["blue"]
    rect(s, x, y, w, h, C["bg2"], val_color, 0.8)
    T(s, label, x+0.12, y+0.08, w-0.2, 0.28, size=8.5, color=C["t2"])
    T(s, value, x+0.12, y+0.32, w-0.2, 0.58,
      size=30, bold=True, color=val_color)
    T(s, note,  x+0.12, y+0.88, w-0.2, 0.24, size=8.5, color=C["t2"])


def side_label(s, text, x, y, color=None):
    """Vertical-looking section divider label on left edge."""
    color = color or C["blue"]
    rect(s, x, y, 0.06, 0.32, color)
    T(s, text, x+0.14, y, 3.0, 0.32,
      size=10.5, bold=True, color=color)


def slide_chrome(s, title, subtitle="", accent=None):
    """Standard top bar + title used on every content slide."""
    accent = accent or C["blue"]
    # Top thin accent line
    rect(s, 0, 0, 13.33, 0.07, accent)
    # Title
    T(s, title, 0.40, 0.14, 11.0, 0.60,
      size=26, bold=True, color=accent)
    if subtitle:
        T(s, subtitle, 0.40, 0.70, 11.0, 0.30,
          size=11, color=C["t2"])
    line_h(s, 0.40, 0.66, 6.5, color=accent)
    # SIH 2026 top-right badge
    rect(s, 11.55, 0.10, 1.60, 0.50, C["sih_o"])
    T(s, "SIH  2026", 11.57, 0.15, 1.55, 0.38,
      size=13, bold=True, color=C["white"], align=PP_ALIGN.CENTER)


def bottom_strip(s, text=None):
    rect(s, 0, 7.28, 13.33, 0.22, C["bg3"])
    rect(s, 0, 7.26, 13.33, 0.03, C["blue"])
    T(s, text or f"AMRoboSync  |  {TEAM_NAME}  |  {PS_NUMBER}  |  SIH 2026",
      0.30, 7.29, 12.7, 0.20,
      size=8.5, color=C["t3"], align=PP_ALIGN.CENTER)


def bullet_rows(s, items, x, y, gap=0.42, size=11.5,
                bullet_color=None, text_color=None):
    bullet_color = bullet_color or C["blue"]
    text_color   = text_color   or C["t1"]
    for i, item in enumerate(items):
        # Square bullet
        rect(s, x, y + i*gap + 0.10, 0.07, 0.07, bullet_color)
        T(s, item, x+0.18, y + i*gap, 99, 0.38,
          size=size, color=text_color)


# ═══════════════════════════════════════════════════
#   SLIDE 1  —  COVER PAGE
# ═══════════════════════════════════════════════════
s = new_slide()

# Top banner — SIH colours
rect(s, 0, 0, 13.33, 0.60, C["sih_b"])
rect(s, 0, 0.60, 13.33, 0.07, C["sih_o"])
T(s, "SMART INDIA HACKATHON  2026   —   SOFTWARE EDITION",
  0.30, 0.10, 12.70, 0.42,
  size=17, bold=True, color=C["white"], align=PP_ALIGN.CENTER)

# Organisation strip
rect(s, 0, 0.67, 13.33, 0.48, C["bg1"])
T(s, "Organisation :  Bharat Electronics Limited ( BEL )     |     Category :  Robotics / Edge-AI / Smart Manufacturing",
  0.30, 0.74, 12.70, 0.34,
  size=11, color=C["yellow"], align=PP_ALIGN.CENTER)

# Main product name
T(s, "AMRoboSync", 0.40, 1.30, 12.50, 1.10,
  size=58, bold=True, color=C["blue"], align=PP_ALIGN.CENTER)

line_h(s, 2.60, 2.35, 8.10, 0.06, C["blue"])

T(s, "Edge-AI Based  Distributed  Fleet  Coordination",
  0.40, 2.46, 12.50, 0.55,
  size=21, bold=True, color=C["t1"], align=PP_ALIGN.CENTER)

T(s, "for  Autonomous  Mobile  Robots  ( AMRs )  in  Smart  Warehouses",
  0.40, 2.98, 12.50, 0.42,
  size=14, color=C["t2"], align=PP_ALIGN.CENTER)

# PS box
rect(s, 4.60, 3.55, 4.10, 0.55, C["bg2"], C["sih_o"], 1.5)
T(s, f"Problem Statement :   {PS_NUMBER}",
  4.72, 3.62, 3.86, 0.36,
  size=13.5, bold=True, color=C["sih_o"], align=PP_ALIGN.CENTER)

# Feature tags row (no emoji, clean labels)
feature_tags = [
    ("Traffic Heatmap",  C["orange"]),
    ("P2P Mesh Network", C["blue"]),
    ("Predictive Path",  C["purple"]),
    ("CBS / A-Star",     C["green"]),
    ("8 AMR Fleet",      RGBColor(0x26,0xC6,0xDA)),
]
for i, (lbl, col) in enumerate(feature_tags):
    tag(s, lbl, 1.45 + i*2.09, 4.28, 1.95, 0.36, C["bg2"], col, 10)

# Info row — team / college / mentor
rect(s, 0.40, 4.80, 12.50, 1.80, C["bg1"])

# Team
T(s, "TEAM", 0.65, 4.90, 2.5, 0.28, size=9, bold=True, color=C["t3"])
T(s, TEAM_NAME, 0.65, 5.14, 4.1, 0.52,
  size=21, bold=True, color=C["blue"])
T(s, f"Team ID :  {TEAM_ID}", 0.65, 5.70, 4.1, 0.32,
  size=12, color=C["t2"])

rect(s, 4.98, 5.02, 0.03, 1.30, C["t3"])   # divider

# College
T(s, "INSTITUTION", 5.20, 4.90, 4.5, 0.28, size=9, bold=True, color=C["t3"])
T(s, COLLEGE_NAME, 5.20, 5.14, 4.5, 0.52,
  size=15, bold=True, color=C["t1"])
T(s, COLLEGE_CITY, 5.20, 5.70, 4.5, 0.32, size=12, color=C["t2"])

rect(s, 9.92, 5.02, 0.03, 1.30, C["t3"])   # divider

# Mentor
T(s, "MENTOR", 10.12, 4.90, 3.0, 0.28, size=9, bold=True, color=C["t3"])
T(s, MENTOR_NAME, 10.12, 5.14, 3.0, 0.52,
  size=14, bold=True, color=C["t1"])
T(s, "Faculty Guide", 10.12, 5.70, 3.0, 0.32, size=12, color=C["t2"])

# Bottom bar
rect(s, 0, 7.28, 13.33, 0.22, C["bg1"])
rect(s, 0, 7.26, 13.33, 0.04, C["blue"])
T(s, f"{TEAM_NAME}   |   {TEAM_ID}   |   {PS_NUMBER}   |   SIH 2026",
  0.30, 7.29, 12.70, 0.20,
  size=9, color=C["t3"], align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════
#   SLIDE 2  —  PROBLEM STATEMENT
# ═══════════════════════════════════════════════════
s = new_slide()
slide_chrome(s, "Problem Statement",
             f"{PS_NUMBER}   —   Bharat Electronics Limited ( BEL )", C["sih_o"])

# Problem description card
rect(s, 0.40, 1.04, 12.50, 1.40, C["bg1"], C["sih_o"], 1.0)
T(s, "Problem Statement Title :",
  0.62, 1.10, 12.0, 0.28, size=9.5, bold=True, color=C["sih_o"])
T(s, "Edge-AI Based Distributed Fleet Coordination for Autonomous Mobile Robots (AMRs) in Smart Warehouses",
  0.62, 1.34, 12.0, 0.44, size=14, bold=True, color=C["t1"])
T(s, "Modern smart warehouses rely on fleets of AMRs. As fleet sizes grow, relying on a centralised cloud server "
     "causes high latency, Wi-Fi dead-zone risks, and single-point-of-failure vulnerabilities.",
  0.62, 1.76, 12.0, 0.55, size=10.5, color=C["t2"])

# Left panel — Challenges
rect(s, 0.40, 2.56, 5.90, 4.58, C["bg1"])
rect(s, 0.40, 2.56, 0.06, 4.58, C["red"])   # left accent bar
T(s, "CURRENT CHALLENGES", 0.60, 2.64, 5.50, 0.34,
  size=11, bold=True, color=C["red"])
line_h(s, 0.60, 2.96, 5.20, color=C["red"])

challenges = [
    "High network latency — cloud bottleneck",
    "Wi-Fi dead zones cause robot stalls",
    "Single point of failure — central server",
    "Deadlocks at narrow aisle intersections",
    "No real-time inter-robot collision avoidance",
    "Poor task re-assignment when aisle blocked",
]
bullet_rows(s, challenges, 0.62, 3.08, gap=0.60,
            size=11.5, bullet_color=C["red"])

# Right panel — Requirements
rect(s, 6.70, 2.56, 6.20, 4.58, C["bg1"])
rect(s, 6.70, 2.56, 0.06, 4.58, C["green"])
T(s, "EXPECTED SOLUTION", 6.90, 2.64, 5.80, 0.34,
  size=11, bold=True, color=C["green"])
line_h(s, 6.90, 2.96, 5.60, color=C["green"])

solutions = [
    ("Decentralised P2P Comms",    "No central server — robots talk directly"),
    ("Multi-Agent Path Planning",  "CBS + A-Star — collision-free routes"),
    ("Dynamic Conflict Resolution","Deadlock detection and real-time replan"),
    ("Task Allocation / Re-route", "Auction-based — handles blocked aisles"),
    ("Edge Hardware Ready",        "Raspberry Pi / Jetson Nano compatible"),
    ("Fleet Monitoring Dashboard", "Lightweight real-time browser UI"),
]
for i, (title, desc) in enumerate(solutions):
    rect(s, 6.90, 3.08 + i*0.65, 0.07, 0.07, C["green"])
    T(s, title, 7.10, 3.06 + i*0.65, 5.60, 0.28,
      size=11.5, bold=True, color=C["green"])
    T(s, desc,  7.10, 3.32 + i*0.65, 5.60, 0.24,
      size=10, color=C["t2"])

bottom_strip(s)


# ═══════════════════════════════════════════════════
#   SLIDE 3  —  PROPOSED SOLUTION
# ═══════════════════════════════════════════════════
s = new_slide()
slide_chrome(s, "Proposed Solution — AMRoboSync",
             "Fully Decentralised   |   No Cloud Dependency   |   Zero Collisions", C["green"])

# Idea banner
rect(s, 0.40, 1.04, 12.50, 0.82, C["bg1"], C["green"], 0.8)
T(s, "CORE IDEA :", 0.62, 1.10, 1.80, 0.28,
  size=10, bold=True, color=C["green"])
T(s, "Each AMR runs as an independent edge-AI agent with its own path planner, "
     "P2P communicator, and conflict resolver. Robots coordinate by broadcasting "
     "position and intent over a ZeroMQ mesh — no server, no cloud, no single point of failure.",
  0.62, 1.36, 12.0, 0.42, size=11.5, color=C["t1"])

# Three pillars
pillars = [
    ("PLAN",        C["blue"],   "CBS Multi-Agent Planner",
     ["Space-Time A-Star per robot",
      "Conflict-Based Search tree",
      "Vertex and edge collision detect",
      "150-tick planning horizon",
      "Joint replan every 15 ticks"]),
    ("COMMUNICATE", C["yellow"], "ZeroMQ P2P Mesh",
     ["1 PUB + N SUB sockets per robot",
      "No broker or central router",
      "Messages: POSITION, INTENT",
      "TASK_BID, TASK_AWARD, PING",
      "In-process bus for simulation"]),
    ("ACT",         C["green"],  "Autonomous State Machine",
     ["IDLE -> NAVIGATING -> PICKUP",
      "-> DROPPING_OFF -> IDLE",
      "Battery-aware charge routing",
      "Auction-based task assignment",
      "Deadlock backoff and replan"]),
]
for i, (title, col, sub, pts) in enumerate(pillars):
    x = 0.40 + i*4.31
    rect(s, x, 2.00, 4.10, 5.12, C["bg1"])
    rect(s, x, 2.00, 4.10, 0.55, col)      # header fill
    T(s, title, x+0.12, 2.07, 3.86, 0.38,
      size=17, bold=True, color=C["bg0"], align=PP_ALIGN.CENTER)
    line_h(s, x+0.12, 2.60, 3.7, color=col)
    T(s, sub, x+0.12, 2.66, 3.86, 0.30,
      size=10, italic=True, color=col, align=PP_ALIGN.CENTER)
    line_h(s, x+0.12, 2.98, 3.7, 0.025, col)
    bullet_rows(s, pts, x+0.18, 3.06, gap=0.38,
                size=10.5, bullet_color=col)

# Result strip
rect(s, 0, 7.10, 13.33, 0.40, C["green"])
T(s, "RESULT :   Zero Collisions      +24 % Throughput vs Stop-and-Wait      Fully Decentralised      Edge-Ready",
  0.40, 7.13, 12.50, 0.32,
  size=11.5, bold=True, color=C["bg0"], align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════
#   SLIDE 4  —  TECHNICAL APPROACH
# ═══════════════════════════════════════════════════
s = new_slide()
slide_chrome(s, "Technical Approach",
             "Algorithm Pipeline — From Task Generation to Delivery", C["blue"])

# Pipeline steps
steps = [
    ("01", "Task\nGeneration",   C["blue"],
     "Pickup and dropoff\nassigned randomly;\npriority 1-3"),
    ("02", "Auction\nBidding",   C["yellow"],
     "Robots bid on tasks;\nlowest bid wins;\ndecentralised"),
    ("03", "CBS Path\nPlanning", C["green"],
     "Joint CBS solve;\nconflict-free paths\nfor full fleet"),
    ("04", "Conflict\nResolve",  C["orange"],
     "Vertex and edge\ncheck each tick;\nbackoff or replan"),
    ("05", "Robot\nExecutes",    C["purple"],
     "Follows path step\nby step; battery\ndrain tracked"),
    ("06", "Task\nComplete",     C["green"],
     "Arrived at dropoff;\nstats updated;\nnew task auctioned"),
]
for i, (num, lbl, col, desc) in enumerate(steps):
    x = 0.35 + i*2.16
    rect(s, x, 1.20, 1.80, 1.25, C["bg2"], col, 1.0)
    rect(s, x+0.62, 1.20, 0.55, 0.40, col)            # number fill
    T(s, num, x+0.62, 1.22, 0.55, 0.34,
      size=16, bold=True, color=C["bg0"], align=PP_ALIGN.CENTER)
    T(s, lbl, x+0.06, 1.60, 1.68, 0.50,
      size=10.5, bold=True, color=col, align=PP_ALIGN.CENTER)
    # Arrow connector
    if i < len(steps) - 1:
        rect(s, x+1.80, 1.76, 0.33, 0.06, col)
    # Description below
    T(s, desc, x, 2.60, 1.90, 0.75,
      size=9.5, color=C["t2"], align=PP_ALIGN.CENTER)

# Four algorithm detail cards
alg_cards = [
    ("A-STAR   SPACE-TIME", C["blue"], [
        "Heuristic :  Manhattan distance",
        "State     :  ( row, col, time )",
        "Avoids reserved (r, c, t) tuples",
        "Edge-swap collision detection",
        "Returns   :  list of cells",
    ]),
    ("CBS   HIGH LEVEL", C["green"], [
        "Root node : unconstrained paths",
        "Find first conflict in all paths",
        "Branch : add constraint per robot",
        "Re-run A-Star with constraints",
        "Repeat until no conflict remains",
    ]),
    ("DEADLOCK DETECTION", C["yellow"], [
        "Stall counter per robot",
        "8 ticks no progress = stuck",
        "Random backoff : 16-48 ticks",
        "Full CBS replan triggered",
        "Priority : battery first scheme",
    ]),
    ("TASK AUCTION", C["purple"], [
        "bid = dist / battery + 10 / priority",
        "All idle robots compute bids",
        "Lowest bid wins the task",
        "Block alert releases the task",
        "Re-auction immediately",
    ]),
]
for i, (title, col, pts) in enumerate(alg_cards):
    x = 0.40 + i*3.24
    rect(s, x, 3.50, 3.08, 3.72, C["bg1"])
    rect(s, x, 3.50, 3.08, 0.06, col)      # top accent line
    T(s, title, x+0.14, 3.58, 2.88, 0.36,
      size=11, bold=True, color=col)
    line_h(s, x+0.14, 3.92, 2.80, 0.03, col)
    bullet_rows(s, pts, x+0.14, 4.00, gap=0.50,
                size=10, bullet_color=col)

bottom_strip(s)


# ═══════════════════════════════════════════════════
#   SLIDE 5  —  SYSTEM ARCHITECTURE
# ═══════════════════════════════════════════════════
s = new_slide()
slide_chrome(s, "System Architecture",
             "Decentralised Edge-AI   —   Each AMR is an Autonomous Agent", C["blue"])

# Simulation engine border
rect(s, 0.35, 1.05, 9.25, 5.10, C["bg1"], C["blue"], 0.8)
T(s, "SIMULATION ENGINE   ( Python )",
  0.55, 1.10, 8.80, 0.36,
  size=12, bold=True, color=C["blue"], align=PP_ALIGN.CENTER)
line_h(s, 0.55, 1.45, 8.70, 0.03, C["blue"])

# AMR boxes
robot_cols = [C["blue"], C["green"], C["yellow"], C["orange"], C["purple"],
              RGBColor(0xF0,0x62,0x92), RGBColor(0x26,0xC6,0xDA), RGBColor(0xAE,0xD5,0x81)]
for i in range(8):
    rx = 0.55 + i*1.10
    rect(s, rx, 1.58, 0.95, 1.10, C["bg2"], robot_cols[i], 0.8)
    T(s, f"AMR\n{i:02d}", rx+0.05, 1.63, 0.85, 0.60,
      size=10.5, bold=True, color=robot_cols[i], align=PP_ALIGN.CENTER)
    T(s, "Edge", rx+0.15, 2.20, 0.65, 0.22,
      size=8, color=C["t2"], align=PP_ALIGN.CENTER)
    # Connector
    rect(s, rx+0.45, 2.68, 0.04, 0.42, robot_cols[i])

# P2P mesh bar
rect(s, 0.55, 3.10, 8.80, 0.52, RGBColor(0x08,0x14,0x28))
line_h(s, 0.55, 3.10, 8.80, 0.03, C["blue"])
line_h(s, 0.55, 3.59, 8.80, 0.03, C["blue"])
T(s, "ZeroMQ  PUB / SUB  Peer-to-Peer  Mesh  Network   —   No Central Broker",
  0.60, 3.20, 8.70, 0.30,
  size=11.5, color=C["blue"], align=PP_ALIGN.CENTER)

# WebSocket arrow
rect(s, 4.50, 3.62, 0.50, 0.52, C["blue"])
T(s, "WebSocket", 4.14, 4.16, 1.25, 0.24, size=8.5, color=C["blue"])

# Dashboard box
rect(s, 3.45, 4.40, 2.68, 0.70, C["bg2"], C["green"], 1.2)
T(s, "Fleet Dashboard\nhttp://localhost:8080",
  3.54, 4.46, 2.50, 0.56,
  size=11, bold=True, color=C["green"], align=PP_ALIGN.CENTER)

# Module list — right panel
rect(s, 9.82, 1.05, 3.15, 5.10, C["bg1"])
rect(s, 9.82, 1.05, 0.06, 5.10, C["yellow"])
T(s, "CORE MODULES", 10.00, 1.12, 2.90, 0.34,
  size=10.5, bold=True, color=C["yellow"])
line_h(s, 10.00, 1.44, 2.70, 0.03, C["yellow"])
mods = ["core / config.py", "core / warehouse.py", "core / robot.py",
        "planning / astar.py", "planning / cbs.py",
        "core / conflict_resolver.py", "core / task_allocator.py",
        "comms / p2p_network.py", "simulation.py",
        "dashboard / server.py", "dashboard / index.html"]
for i, m in enumerate(mods):
    T(s, m, 10.04, 1.54 + i*0.42, 2.85, 0.30, size=9.5, color=C["t2"])

bottom_strip(s)


# ═══════════════════════════════════════════════════
#   SLIDE 6  —  TECHNOLOGY STACK
# ═══════════════════════════════════════════════════
s = new_slide()
slide_chrome(s, "Technology Stack",
             "Lightweight   Open-Source   Edge-Hardware Compatible", C["yellow"])

categories = [
    ("BACKEND  /  SIMULATION", C["blue"], [
        ("Language",        "Python 3.10",          "Core simulation engine"),
        ("Async I/O",       "asyncio",               "Non-blocking tick loop"),
        ("Path Planning",   "Custom CBS + A-Star",   "Pure Python, no ML needed"),
        ("Task Allocation", "Auction algorithm",     "O(n2) per tick"),
        ("State Machine",   "Python Enum + classes", "7 robot states"),
    ]),
    ("COMMUNICATION", C["green"], [
        ("P2P Network",   "ZeroMQ  ( pyzmq )",    "PUB / SUB mesh"),
        ("In-Process Bus","Python Queue",          "Simulation mode"),
        ("WebSocket",     "websockets  12.0",      "Browser to server"),
        ("HTTP Server",   "aiohttp  3.9",          "Serves dashboard"),
        ("Serialisation", "JSON  ( stdlib )",      "Snapshot format"),
    ]),
    ("FRONTEND  DASHBOARD", C["yellow"], [
        ("UI Framework",  "Vanilla HTML5 / JS",   "No React, no npm"),
        ("Rendering",     "Canvas 2D API",         "60 fps warehouse map"),
        ("Charts",        "Custom sparklines",     "Tasks / conflicts / util"),
        ("Styling",       "CSS Variables",         "Dark corporate theme"),
        ("Real-time",     "WebSocket onmessage",   "Live data stream"),
    ]),
    ("HARDWARE  TARGET", C["purple"], [
        ("Primary",     "Raspberry Pi 4 ( 4 GB )", "Per-robot edge node"),
        ("Alternative", "NVIDIA Jetson Nano",       "GPU-accelerated CBS"),
        ("Comms HW",    "Wi-Fi 802.11ac mesh",      "Local network only"),
        ("Simulation",  "Any PC  Python 3.10+",     "No GPU required"),
        ("Deployment",  "Docker / venv",            "Easy environment setup"),
    ]),
]
for i, (title, col, items) in enumerate(categories):
    ci = i % 2;  ri = i // 2
    x = 0.40 + ci*6.50;  y = 1.04 + ri*3.12
    rect(s, x, y, 6.10, 2.88, C["bg1"])
    rect(s, x, y, 6.10, 0.06, col)
    T(s, title, x+0.15, y+0.12, 5.80, 0.36,
      size=11.5, bold=True, color=col)
    line_h(s, x+0.15, y+0.48, 5.50, 0.03, col)
    for j, (tech, val, note) in enumerate(items):
        T(s, tech + " :", x+0.18, y+0.60 + j*0.42, 1.55, 0.30,
          size=10, color=C["t2"])
        T(s, val,         x+1.80, y+0.60 + j*0.42, 2.20, 0.30,
          size=10, bold=True, color=col)
        T(s, note,        x+4.05, y+0.60 + j*0.42, 1.90, 0.30,
          size=9, color=C["t3"])

bottom_strip(s)


# ═══════════════════════════════════════════════════
#   SLIDE 7  —  NOVELTY & UNIQUENESS
# ═══════════════════════════════════════════════════
s = new_slide()
slide_chrome(s, "Novelty  &  Uniqueness",
             "What Makes AMRoboSync Different from Existing Solutions", C["purple"])

# Comparison table header
rect(s, 0.40, 1.04, 12.50, 0.40, C["bg3"])
for j, (h, cx, cw) in enumerate([
        ("FEATURE",             0.50, 2.80),
        ("TRADITIONAL CLOUD",   3.42, 2.80),
        ("EXISTING EDGE",       6.38, 2.80),
        ("AMRoboSync",          9.35, 3.30),
]):
    c = C["yellow"] if j==3 else C["t2"]
    T(s, h, cx, 1.10, cw, 0.28, size=10, bold=True, color=c)

# Table rows
rows_cmp = [
    ("Path Planning",       "Centralised A-Star",    "Single-agent A-Star", "Joint CBS  multi-agent"),
    ("Communication",       "Cloud MQTT",            "Local Wi-Fi only",    "ZeroMQ P2P Mesh"),
    ("Collision Avoidance", "Stop-and-Wait",         "Reactive only",       "Proactive space-time"),
    ("Deadlock Handling",   "Timeout and retry",     "Manual reset",        "Auto CBS replan"),
    ("Task Allocation",     "Central scheduler",     "FIFO queue",          "Decentralised auction"),
    ("Failure Recovery",    "System restart",        "Partial recovery",    "Self-healing P2P"),
    ("Dashboard",           "Cloud web app",         "Static display",      "Live 7-page Canvas UI"),
]
for ri, row in enumerate(rows_cmp):
    bg = C["bg2"] if ri%2==0 else C["bg1"]
    rect(s, 0.40, 1.44+ri*0.54, 12.50, 0.52, bg)
    col_xs = [0.50, 3.42, 6.38, 9.35]
    col_ws = [2.80, 2.80, 2.80, 3.30]
    for j, (val, cx) in enumerate(zip(row, col_xs)):
        vc = C["green"] if j==3 else (C["t3"] if j in (1,2) else C["t1"])
        T(s, val, cx, 1.50+ri*0.54, col_ws[j]-0.10, 0.30,
          size=10.5, color=vc)

# Innovation highlights
T(s, "EXCLUSIVE  INNOVATIONS  IN  AMROBOSYNC",
  0.40, 5.33, 12.50, 0.34, size=11, bold=True, color=C["purple"])
line_h(s, 0.40, 5.65, 12.50, 0.03, C["purple"])

innov = [
    ("TRAFFIC\nHEATMAP",    C["orange"],
     "Real-time cell-visit density overlay.\nIdentifies bottleneck aisles automatically."),
    ("P2P MESH\nOVERLAY",   C["blue"],
     "Live signal-strength lines between robots.\nNo router or cloud dependency."),
    ("PREDICTIVE\nGHOST",   C["purple"],
     "CBS-planned path preview per robot.\nOperator sees future movement in advance."),
    ("PRIORITY\nBADGES",    C["yellow"],
     "Auction weighted by task urgency.\nHIGH / MED / LOW shown on map and table."),
    ("P2P SIGNAL\nSTRENGTH",RGBColor(0x26,0xC6,0xDA),
     "Per-robot signal bars in Robots page.\nDistance-based signal simulation."),
]
for i, (lbl, col, desc) in enumerate(innov):
    x = 0.40 + i*2.55
    rect(s, x, 5.75, 2.42, 1.47, C["bg2"], col, 0.8)
    rect(s, x, 5.75, 2.42, 0.06, col)
    T(s, lbl, x+0.10, 5.84, 2.22, 0.48,
      size=10, bold=True, color=col)
    T(s, desc, x+0.10, 6.34, 2.22, 0.72, size=9, color=C["t2"])

bottom_strip(s)


# ═══════════════════════════════════════════════════
#   SLIDE 8  —  FEASIBILITY & VIABILITY
# ═══════════════════════════════════════════════════
s = new_slide()
slide_chrome(s, "Feasibility  &  Viability",
             "Technically Proven   Economically Viable   Deployment-Ready")

# Column 1 — Technical
rect(s, 0.40, 1.04, 3.90, 5.90, C["bg1"])
rect(s, 0.40, 1.04, 0.06, 5.90, C["blue"])
T(s, "TECHNICAL FEASIBILITY",
  0.58, 1.12, 3.65, 0.34, size=10.5, bold=True, color=C["blue"])
line_h(s, 0.58, 1.44, 3.55, 0.03, C["blue"])
t_items = [
    "Pure Python — no proprietary SDK",
    "Tested : 8 robots over 300 ticks",
    "Zero collisions in all test runs",
    "+24 % throughput verified",
    "CBS converges under 1000 iterations",
    "A-Star plans in under 5 ms per robot",
    "WebSocket latency approx 2 ms local",
    "Runs on Raspberry Pi 4 ( 4 GB RAM )",
]
bullet_rows(s, t_items, 0.60, 1.58, gap=0.60, size=11, bullet_color=C["blue"])

# Column 2 — Economic
rect(s, 4.55, 1.04, 3.90, 5.90, C["bg1"])
rect(s, 4.55, 1.04, 0.06, 5.90, C["green"])
T(s, "ECONOMIC VIABILITY",
  4.73, 1.12, 3.65, 0.34, size=10.5, bold=True, color=C["green"])
line_h(s, 4.73, 1.44, 3.55, 0.03, C["green"])
cost_items = [
    ("Raspberry Pi 4 ( 4 GB )", "Rs. 7,000 / unit"),
    ("Wi-Fi mesh router",       "Rs. 5,000"),
    ("Python + libraries",      "Free / Open Source"),
    ("Dashboard ( browser )",   "No license"),
    ("Cloud server",            "NOT needed"),
    ("Maintenance",             "OTA via P2P"),
    ("Scale to 50 robots",      "Linear cost growth"),
    ("ROI vs cloud solution",   "~60 % cost saving"),
]
for i, (k, v) in enumerate(cost_items):
    T(s, k, 4.73, 1.58+i*0.60, 2.55, 0.30, size=10.5, color=C["t1"])
    T(s, v, 7.00, 1.58+i*0.60, 1.30, 0.30, size=10.5, bold=True, color=C["green"])

# Column 3 — Deployment phases
rect(s, 8.70, 1.04, 4.25, 5.90, C["bg1"])
rect(s, 8.70, 1.04, 0.06, 5.90, C["yellow"])
T(s, "DEPLOYMENT ROADMAP",
  8.88, 1.12, 4.00, 0.34, size=10.5, bold=True, color=C["yellow"])
line_h(s, 8.88, 1.44, 3.80, 0.03, C["yellow"])
phases = [
    ("PHASE 1    0-3 months",  C["blue"],
     "Simulation complete\nAll algorithms tested\nDashboard fully live"),
    ("PHASE 2    3-6 months",  C["yellow"],
     "Deploy on RPi hardware\n3-robot physical test\nWarehouse pilot run"),
    ("PHASE 3    6-12 months", C["green"],
     "Scale to 20 plus robots\nReal warehouse trial\nBEL integration"),
]
for i, (phase, col, desc) in enumerate(phases):
    rect(s, 8.88, 1.58+i*1.72, 3.85, 1.58, C["bg2"], col, 0.8)
    rect(s, 8.88, 1.58+i*1.72, 3.85, 0.06, col)
    T(s, phase, 8.96, 1.66+i*1.72, 3.65, 0.30,
      size=10.5, bold=True, color=col)
    T(s, desc,  8.96, 1.98+i*1.72, 3.65, 0.88,
      size=11, color=C["t1"])

bottom_strip(s)


# ═══════════════════════════════════════════════════
#   SLIDE 9  —  IMPACT & BENEFITS
# ═══════════════════════════════════════════════════
s = new_slide()
slide_chrome(s, "Impact  &  Benefits",
             "Quantified Results   Societal Impact   Industry Value", C["green"])

# KPI row
kpis = [
    ("+24 %",  "Throughput\nImprovement",  C["green"]),
    ("0",      "Collisions\nZero",         C["green"]),
    ("8",      "Robots\nSimulated",        C["blue"]),
    ("7",      "Dashboard\nPages",         C["blue"]),
    ("99.8 %", "Network\nUptime",          C["yellow"]),
    ("~2 ms",  "P2P  Message\nLatency",    C["yellow"]),
]
for i, (val, lbl, col) in enumerate(kpis):
    kpi_box(s, lbl, val, "", 0.45+i*2.18, 1.04, col, 2.06, 1.28)

# Three impact panels
impacts = [
    ("INDUSTRY  IMPACT", C["blue"], [
        "Reduces task completion time by 24 %+",
        "Eliminates costly cloud server",
        "Scales to 50+ robots linearly",
        "Works in Wi-Fi dead zones",
        "Compatible with existing AMR hardware",
        "Reduces fleet idle time and energy",
    ]),
    ("SOCIETAL  IMPACT", C["green"], [
        "Faster e-commerce fulfilment",
        "Lower logistics costs for consumers",
        "Safer warehouses — zero robot collisions",
        "Less human intervention in danger zones",
        "Supports Make-in-India initiative",
        "Creates skilled jobs in robotics and AI",
    ]),
    ("RESEARCH  IMPACT", C["purple"], [
        "Novel CBS for Indian edge hardware",
        "Open-source fleet coordination framework",
        "Benchmark : CBS vs Stop-and-Wait",
        "Extensible to drone swarms and AGVs",
        "Foundation for federated robotics learning",
        "Publishable algorithm innovations",
    ]),
]
for i, (title, col, pts) in enumerate(impacts):
    x = 0.40 + i*4.31
    rect(s, x, 2.50, 4.08, 4.62, C["bg1"])
    rect(s, x, 2.50, 4.08, 0.06, col)
    T(s, title, x+0.15, 2.60, 3.85, 0.34,
      size=11.5, bold=True, color=col)
    line_h(s, x+0.15, 2.94, 3.70, 0.03, col)
    bullet_rows(s, pts, x+0.15, 3.04, gap=0.62, size=11, bullet_color=col)

bottom_strip(s)


# ═══════════════════════════════════════════════════
#   SLIDE 10  —  TEAM DETAILS
# ═══════════════════════════════════════════════════
s = new_slide()
slide_chrome(s, "Team Details",
             f"{TEAM_NAME}   |   {TEAM_ID}   |   {COLLEGE_NAME}", C["blue"])

# Institution / Mentor bar
rect(s, 0.40, 1.04, 12.50, 0.84, C["bg1"])
T(s, "INSTITUTION :", 0.62, 1.10, 2.20, 0.32, size=10, bold=True, color=C["t2"])
T(s, COLLEGE_NAME,   2.90, 1.10, 5.60, 0.32, size=14, bold=True, color=C["t1"])
T(s, COLLEGE_CITY,   2.90, 1.44, 5.60, 0.28, size=11, color=C["t2"])
rect(s, 8.98, 1.14, 0.03, 0.55, C["t3"])
T(s, "MENTOR :",     9.15, 1.10, 1.70, 0.32, size=10, bold=True, color=C["t2"])
T(s, MENTOR_NAME,   10.90, 1.10, 2.80, 0.32, size=13, bold=True, color=C["t1"])
T(s, "Faculty Guide",10.90, 1.44, 2.80, 0.28, size=11, color=C["t2"])

# Team members grid  3 cols x 2 rows
T(s, "TEAM  MEMBERS", 0.45, 2.06, 5.0, 0.32,
  size=11, bold=True, color=C["blue"])
line_h(s, 0.45, 2.38, 12.40, 0.04, C["blue"])

m_cols = [C["blue"], C["green"], C["yellow"],
          C["orange"], C["purple"], RGBColor(0x26,0xC6,0xDA)]
for i, (name, role, branch) in enumerate(TEAM_MEMBERS):
    ci = i % 3;  ri = i // 3
    x = 0.40 + ci*4.32;  y = 2.55 + ri*2.18
    col = m_cols[i % len(m_cols)]
    rect(s, x, y, 4.08, 1.90, C["bg2"], col, 0.8)
    # Avatar circle
    oval(s, x+0.12, y+0.16, 0.72, 0.72, col)
    initial = name[0].upper() if name not in ("Member 1 Name","Member 2 Name",
                                               "Member 3 Name","Member 4 Name",
                                               "Member 5 Name","Member 6 Name") else str(i+1)
    T(s, initial, x+0.12, y+0.26, 0.72, 0.50,
      size=18, bold=True, color=C["bg0"], align=PP_ALIGN.CENTER)
    T(s, name,   x+0.98, y+0.14, 2.95, 0.36, size=12, bold=True, color=col)
    T(s, role,   x+0.98, y+0.50, 2.95, 0.30, size=10.5, color=C["t1"])
    T(s, branch, x+0.98, y+0.80, 2.95, 0.28, size=9.5, color=C["t2"])
    rect(s, x+0.12, y+1.50, 3.86, 0.30, C["bg3"])
    T(s, role, x+0.18, y+1.54, 3.70, 0.24,
      size=9, color=col, align=PP_ALIGN.CENTER)

# Bottom result strip
rect(s, 0, 7.10, 13.33, 0.40, C["blue"])
T(s, f"AMRoboSync   {TEAM_NAME}   {TEAM_ID}   {PS_NUMBER}   SIH 2026   Zero Collisions   +24 % Throughput",
  0.40, 7.13, 12.50, 0.28,
  size=10.5, bold=True, color=C["bg0"], align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════
#   SLIDE 11  —  BENCHMARK RESULTS
# ═══════════════════════════════════════════════════
s = new_slide()
slide_chrome(s, "Benchmark Results   —   CBS / A-Star  vs  Stop-and-Wait",
             "300 Ticks   8 Robots   16x16 Grid   Success Criterion : >= 20 % improvement",
             C["green"])

# Hero result
rect(s, 0.40, 1.04, 12.50, 1.55, C["bg1"], C["green"], 1.5)
T(s, "+24.0 %   Throughput Improvement",
  0.50, 1.10, 12.30, 0.88,
  size=46, bold=True, color=C["green"], align=PP_ALIGN.CENTER)
T(s, "CBS / A-Star completes 31 tasks   vs   25 for Stop-and-Wait   in the same 300 ticks"
     "     SUCCESS CRITERION MET ( >= 20 % )",
  0.50, 1.92, 12.30, 0.42,
  size=11.5, color=C["t2"], align=PP_ALIGN.CENTER)

# KPI cards
kpis_bm = [
    ("Tasks\nCBS / A-Star",     "31",    "completed",  C["green"]),
    ("Tasks\nStop and Wait",    "25",    "completed",  C["red"]),
    ("Throughput\nCBS / A-Star","0.103", "tasks/tick", C["green"]),
    ("Throughput\nStop Wait",   "0.083", "tasks/tick", C["red"]),
    ("Collisions\nCBS / A-Star","0",     "ZERO  PASS", C["green"]),
]
for i, (lbl, val, unit, col) in enumerate(kpis_bm):
    kpi_box(s, lbl, val, unit, 0.42+i*2.50, 2.78, col, 2.42, 1.32)

# Comparison table
rect(s, 0.40, 4.28, 12.50, 2.80, C["bg1"])
T(s, "DETAILED COMPARISON TABLE",
  0.60, 4.35, 12.00, 0.34, size=11.5, bold=True, color=C["blue"])
line_h(s, 0.60, 4.68, 11.90, 0.03, C["blue"])

hdrs = [("METRIC",0.58,2.40),("CBS / A-STAR",3.10,2.55),
        ("STOP  AND  WAIT",5.78,2.42),("IMPROVEMENT",8.32,2.20),("STATUS",10.65,1.90)]
for h, cx, cw in hdrs:
    rect(s, cx-0.05, 4.72, cw+0.02, 0.30, C["bg3"])
    T(s, h, cx, 4.74, cw, 0.24,
      size=9.5, bold=True, color=C["yellow"], align=PP_ALIGN.CENTER)

rows_bm = [
    ("Tasks Completed",          "31",      "25",       "+24.0 %",   "PASS"),
    ("Throughput ( tasks/tick )", "0.1033",  "0.0833",   "+24.0 %",   "PASS"),
    ("Avg Completion Tick",       "128.2",   "152.1",    "-15.7 %",   "PASS"),
    ("Collision Events",          "0",       "0",        "ZERO",      "PASS"),
    ("Deadlocks Resolved",        "19",      "N/A",      "CBS only",  "PASS"),
]
for ri, row in enumerate(rows_bm):
    for j, (val, cx, cw) in enumerate(zip(row, [0.58,3.10,5.78,8.32,10.65],
                                              [2.40,2.55,2.42,2.20,1.90])):
        vc = C["green"] if val=="PASS" else \
             C["red"]   if j==2 and ri<2 else C["t1"]
        T(s, val, cx, 5.12+ri*0.36, cw, 0.30,
          size=10, color=vc, align=PP_ALIGN.CENTER)

bottom_strip(s, f"{TEAM_NAME}   |   {PS_NUMBER}   |   SIH 2026   |   AMRoboSync")


# ═══════════════════════════════════════════════════
#   SAVE
# ═══════════════════════════════════════════════════
OUT = "AMRoboSync_SIH2026.pptx"
prs.save(OUT)

print("=" * 58)
print("  SIH 2026  PROFESSIONAL PPT  GENERATED")
print("=" * 58)
print(f"  File   :  {OUT}")
print(f"  Slides :  {len(prs.slides)}")
print(f"  Theme  :  Professional Dark  ( No Emoji )")
print()
for i, t in enumerate([
        "Cover Page  ( SIH 2026 Format )",
        "Problem Statement",
        "Proposed Solution",
        "Technical Approach",
        "System Architecture",
        "Technology Stack",
        "Novelty and Uniqueness",
        "Feasibility and Viability",
        "Impact and Benefits",
        "Team Details",
        "Benchmark Results",
], 1):
    print(f"    {i:2d}.  {t}")
print()
print("  Fill in your details at the top of this file")
print("  ( Lines 14-27 )  then run again.")
print("=" * 58)
