"""
generate_ppt.py — Auto-generates a complete competition PPT for
AMRoboSync: Edge-AI Based Distributed Fleet Coordination for AMRs.

Run:
    python generate_ppt.py
Output:
    AMRoboSync_BEL_Presentation.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import io, math

# ── Colour palette ──────────────────────────────────────────
BG_DARK   = RGBColor(0x08, 0x0c, 0x14)
BG_PANEL  = RGBColor(0x0d, 0x13, 0x20)
BG_CARD   = RGBColor(0x11, 0x18, 0x27)
ACC_BLUE  = RGBColor(0x00, 0xd4, 0xff)
ACC_GREEN = RGBColor(0x00, 0xe6, 0x76)
ACC_YELL  = RGBColor(0xff, 0xd7, 0x40)
ACC_RED   = RGBColor(0xff, 0x44, 0x44)
ACC_PURP  = RGBColor(0x7c, 0x4d, 0xff)
TXT_MAIN  = RGBColor(0xe2, 0xea, 0xf6)
TXT_MUT   = RGBColor(0x8f, 0xa4, 0xc0)
WHITE     = RGBColor(0xff, 0xff, 0xff)

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width  = SLIDE_W
prs.slide_height = SLIDE_H

BLANK = prs.slide_layouts[6]   # completely blank


# ══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def add_slide():
    slide = prs.slides.add_slide(BLANK)
    # Dark background
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = BG_DARK
    return slide


def box(slide, x, y, w, h, color=BG_PANEL, radius=False):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def txt(slide, text, x, y, w, h,
        size=18, bold=False, color=TXT_MAIN,
        align=PP_ALIGN.LEFT, italic=False):
    txb = slide.shapes.add_textbox(
        Inches(x), Inches(y), Inches(w), Inches(h))
    tf = txb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = "Segoe UI"
    return txb


def accent_bar(slide, x, y, w=9, h=0.04, color=ACC_BLUE):
    b = box(slide, x, y, w, h, color)
    return b


def chip(slide, label, x, y, w=1.4, h=0.32,
         bg=BG_CARD, fg=ACC_BLUE):
    b = box(slide, x, y, w, h, bg)
    b.line.color.rgb = fg
    b.line.width = Pt(1)
    txt(slide, label, x+0.05, y+0.02, w-0.1, h-0.04,
        size=10, bold=True, color=fg, align=PP_ALIGN.CENTER)


def kpi_card(slide, label, value, unit, x, y,
             val_color=ACC_BLUE, w=2.2, h=1.1):
    box(slide, x, y, w, h, BG_CARD)
    txt(slide, label,  x+0.12, y+0.08, w-0.2, 0.25,
        size=9, color=TXT_MUT)
    txt(slide, value,  x+0.12, y+0.3,  w-0.2, 0.55,
        size=28, bold=True, color=val_color)
    txt(slide, unit,   x+0.12, y+0.78, w-0.2, 0.25,
        size=9, color=TXT_MUT)


def robot_circle(slide, x, y, r_inch, color, label):
    """Draw a filled circle representing a robot."""
    from pptx.util import Inches
    d = r_inch * 2
    shape = slide.shapes.add_shape(
        9,  # OVAL
        Inches(x - r_inch), Inches(y - r_inch),
        Inches(d), Inches(d)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.color.rgb = WHITE
    shape.line.width = Pt(1.5)
    txt(slide, label,
        x - r_inch, y - r_inch * 0.6,
        d, r_inch,
        size=10, bold=True, color=RGBColor(0x05,0x08,0x10),
        align=PP_ALIGN.CENTER)


def section_header(slide, title, subtitle=""):
    txt(slide, title, 0.5, 0.15, 12, 0.6,
        size=28, bold=True, color=ACC_BLUE)
    if subtitle:
        txt(slide, subtitle, 0.5, 0.72, 12, 0.4,
            size=13, color=TXT_MUT)
    accent_bar(slide, 0.5, 0.65, 6, 0.04, ACC_BLUE)


def bullet(slide, items, x, y, w=5.5, spacing=0.38, size=13, color=TXT_MAIN):
    for i, item in enumerate(items):
        marker_color = ACC_BLUE if item.startswith("✅") or item.startswith("🔵") else \
                       ACC_GREEN if item.startswith("✔") else \
                       ACC_YELL if item.startswith("⚡") else TXT_MUT
        txt(slide, item, x, y + i * spacing, w, 0.35,
            size=size, color=color if not item.startswith(("✅","✔","⚡","🔵")) else marker_color)


# ══════════════════════════════════════════════════════════════
#  SLIDE 1 — TITLE
# ══════════════════════════════════════════════════════════════
slide = add_slide()

# Gradient-like top bar
box(slide, 0, 0, 13.33, 0.08, ACC_BLUE)

# Big title
txt(slide, "AMRoboSync", 0.6, 0.5, 12, 1.2,
    size=54, bold=True, color=ACC_BLUE, align=PP_ALIGN.CENTER)

txt(slide, "Edge-AI Based Distributed Fleet Coordination",
    0.6, 1.55, 12, 0.6,
    size=22, bold=False, color=TXT_MAIN, align=PP_ALIGN.CENTER)

txt(slide, "for Autonomous Mobile Robots (AMRs) in Smart Warehouses",
    0.6, 2.05, 12, 0.5,
    size=16, color=TXT_MUT, align=PP_ALIGN.CENTER)

accent_bar(slide, 3.5, 2.7, 6.3, 0.05, ACC_BLUE)

# Innovation chips row
chips = ["🔥 Traffic Heatmap","📡 P2P Mesh","👻 Predictive Path","⚡ CBS Active","🤖 8 AMRs"]
colors = [ACC_RED, ACC_BLUE, ACC_PURP, ACC_GREEN, RGBColor(0x26,0xc6,0xda)]
for i,(c,col) in enumerate(zip(chips,colors)):
    chip(slide, c, 1.2 + i*2.18, 3.0, 2.0, 0.36, BG_CARD, col)

# Org + problem
box(slide, 0.5, 3.65, 12.33, 1.3, BG_PANEL)
txt(slide, "Organisation:  Bharat Electronics Limited (BEL)",
    0.8, 3.78, 12, 0.35, size=13, bold=True, color=ACC_YELL)
txt(slide, "Problem Statement:  MALA PURAN DASHABRODE SIMULATION — Decentralised coordination and collision-avoidance\nframework for a multi-robot fleet operating in a dynamic warehouse environment on edge hardware.",
    0.8, 4.1, 11.8, 0.75, size=11, color=TXT_MUT)

# Bottom
txt(slide, "September 2026",
    0.6, 6.9, 12, 0.4, size=11, color=TXT_MUT, align=PP_ALIGN.CENTER)
box(slide, 0, 7.42, 13.33, 0.08, ACC_BLUE)


# ══════════════════════════════════════════════════════════════
#  SLIDE 2 — PROBLEM STATEMENT
# ══════════════════════════════════════════════════════════════
slide = add_slide()
section_header(slide, "Problem Statement", "BEL Challenge — Smart Warehouse Fleet Coordination")

# Left column — challenges
box(slide, 0.4, 1.0, 5.9, 5.8, BG_PANEL)
txt(slide, "⚠  Current Challenges", 0.65, 1.1, 5.4, 0.4,
    size=14, bold=True, color=ACC_YELL)
accent_bar(slide, 0.65, 1.48, 5.0, 0.03, ACC_YELL)

problems = [
    "🔴  High network latency from centralized cloud",
    "🔴  Wi-Fi dead zones cause robot stalls",
    "🔴  Single point of failure (central server)",
    "🔴  Deadlocks at narrow aisle intersections",
    "🔴  No real-time collision avoidance",
    "🔴  Poor task re-assignment when aisles blocked",
    "🔴  Stop-and-Wait wastes 20%+ fleet time",
]
for i, p in enumerate(problems):
    txt(slide, p, 0.65, 1.6 + i*0.7, 5.5, 0.55,
        size=12, color=TXT_MAIN)

# Right column — requirements
box(slide, 6.8, 1.0, 6.1, 5.8, BG_PANEL)
txt(slide, "✅  Requirements", 7.05, 1.1, 5.6, 0.4,
    size=14, bold=True, color=ACC_GREEN)
accent_bar(slide, 7.05, 1.48, 5.0, 0.03, ACC_GREEN)

reqs = [
    ("Decentralised P2P Comms", "No central server — robots talk directly"),
    ("Multi-Agent Path Planning", "CBS + A* for collision-free routes"),
    ("Dynamic Conflict Resolution", "Deadlock detection & real-time replan"),
    ("Task Allocation & Re-routing", "Auction-based, handles blocked aisles"),
    ("Edge Hardware Ready", "Runs on Raspberry Pi / Jetson Nano"),
    ("Fleet Dashboard", "Real-time monitoring UI"),
]
for i, (title, desc) in enumerate(reqs):
    txt(slide, f"✔  {title}", 7.05, 1.6 + i*0.82, 5.6, 0.3,
        size=12, bold=True, color=ACC_GREEN)
    txt(slide, f"    {desc}", 7.05, 1.88 + i*0.82, 5.6, 0.28,
        size=10, color=TXT_MUT)


# ══════════════════════════════════════════════════════════════
#  SLIDE 3 — SYSTEM ARCHITECTURE
# ══════════════════════════════════════════════════════════════
slide = add_slide()
section_header(slide, "System Architecture", "Decentralised Edge-AI — No Central Server Required")

# Central label
box(slide, 2.8, 1.1, 7.7, 4.8, BG_PANEL)
txt(slide, "SIMULATION ENGINE", 3.0, 1.2, 7.0, 0.45,
    size=16, bold=True, color=ACC_BLUE, align=PP_ALIGN.CENTER)
accent_bar(slide, 3.0, 1.6, 7.0, 0.04, ACC_BLUE)

# Robot boxes
robot_cols = [RGBColor(0x00,0xd4,0xff), RGBColor(0x00,0xe6,0x76),
              RGBColor(0xff,0xd7,0x40), RGBColor(0xff,0x70,0x43),
              RGBColor(0x7c,0x4d,0xff)]
rx = [3.1, 4.6, 6.1, 7.6, 9.1]
for i, (x, col) in enumerate(zip(rx, robot_cols)):
    box(slide, x, 1.8, 1.2, 1.0, BG_CARD)
    txt(slide, f"AMR-{i:02d}", x+0.05, 1.88, 1.1, 0.3,
        size=11, bold=True, color=col, align=PP_ALIGN.CENTER)
    txt(slide, "(Edge)", x+0.05, 2.12, 1.1, 0.3,
        size=9, color=TXT_MUT, align=PP_ALIGN.CENTER)
    # Connector line down
    box(slide, x+0.55, 2.8, 0.03, 0.4, col)

# P2P network bar
box(slide, 3.1, 3.2, 7.2, 0.55, RGBColor(0x0a,0x1a,0x30))
txt(slide, "P2P ZeroMQ Mesh Network  (No Central Broker — Each Robot Publishes & Subscribes)",
    3.2, 3.3, 7.0, 0.35,
    size=11, color=ACC_BLUE, align=PP_ALIGN.CENTER)
for x in rx:
    box(slide, x+0.55, 3.0, 0.03, 0.22, ACC_BLUE)

# WebSocket arrow
box(slide, 6.4, 3.75, 0.5, 0.7, ACC_BLUE)
txt(slide, "WebSocket", 5.6, 4.1, 1.5, 0.3,
    size=9, color=ACC_BLUE, align=PP_ALIGN.CENTER)

# Dashboard box
box(slide, 5.3, 4.45, 2.75, 0.85, BG_CARD)
txt(slide, "Fleet Dashboard\n(Browser UI — http://localhost:8080)",
    5.4, 4.52, 2.6, 0.7,
    size=11, color=ACC_GREEN, align=PP_ALIGN.CENTER)

# Module list on left
box(slide, 0.3, 1.0, 2.3, 5.9, BG_PANEL)
txt(slide, "Core Modules", 0.45, 1.08, 2.0, 0.35,
    size=12, bold=True, color=ACC_YELL)
modules = ["core/warehouse.py","core/config.py","core/robot.py",
           "planning/astar.py","planning/cbs.py",
           "core/conflict_resolver.py","core/task_allocator.py",
           "comms/p2p_network.py","simulation.py","dashboard/server.py"]
for i, m in enumerate(modules):
    txt(slide, f"▸ {m}", 0.45, 1.5 + i*0.47, 2.1, 0.35,
        size=9, color=TXT_MUT)

# Stats on right
box(slide, 10.8, 1.0, 2.2, 5.9, BG_PANEL)
txt(slide, "Stats", 10.95, 1.08, 2.0, 0.35,
    size=12, bold=True, color=ACC_GREEN)
stats = [("Robots","8"),("Grid","16×16"),("Algorithms","CBS+A*"),
         ("Comms","ZeroMQ"),("Dashboard","HTML5"),("Ticks","300+"),
         ("Tasks","31+")]
for i, (k,v) in enumerate(stats):
    txt(slide, k, 10.95, 1.5+i*0.72, 1.0, 0.3, size=9, color=TXT_MUT)
    txt(slide, v, 11.9, 1.5+i*0.72, 1.0, 0.3, size=11, bold=True, color=ACC_BLUE)


# ══════════════════════════════════════════════════════════════
#  SLIDE 4 — ALGORITHMS
# ══════════════════════════════════════════════════════════════
slide = add_slide()
section_header(slide, "Key Algorithms", "CBS + Space-Time A* + Auction-Based Task Allocation")

algos = [
    ("⚡  A* (Space-Time)", ACC_BLUE, [
        "• Standard A* extended with time dimension",
        "• Avoids cells reserved by other robots at t",
        "• Edge-swap collision detection",
        "• Time horizon: 150 ticks",
        "• Returns: List[(row, col)] path",
    ]),
    ("🧠  CBS — Conflict-Based Search", ACC_GREEN, [
        "• Two-level: High (constraint tree) + Low (A*)",
        "• Detects vertex & edge conflicts",
        "• Adds constraints → replans affected robot",
        "• Optimal collision-free paths for full fleet",
        "• Max iterations: 1000",
    ]),
    ("🏷  Auction Task Allocation", ACC_YELL, [
        "• Each robot computes bid for every task",
        "• Bid = distance/battery + 1/priority",
        "• Lowest bid wins → task assigned",
        "• Fully decentralised — no auctioneer",
        "• Re-auctions on block alert",
    ]),
    ("🔒  Deadlock Resolution", ACC_PURP, [
        "• Stall counter per robot (8-tick window)",
        "• Stuck robot gets random backoff wait",
        "• CBS replans with fresh constraint tree",
        "• Priority scheme: battery_first",
        "• Token-ring fallback for choke points",
    ]),
]

for i, (title, color, points) in enumerate(algos):
    col = i % 2
    row = i // 2
    x = 0.4 + col * 6.5
    y = 1.05 + row * 3.05

    box(slide, x, y, 6.1, 2.75, BG_PANEL)
    txt(slide, title, x+0.15, y+0.1, 5.8, 0.45,
        size=14, bold=True, color=color)
    accent_bar(slide, x+0.15, y+0.52, 5.5, 0.03, color)
    for j, pt in enumerate(points):
        txt(slide, pt, x+0.2, y+0.62+j*0.4, 5.7, 0.35,
            size=11, color=TXT_MAIN)


# ══════════════════════════════════════════════════════════════
#  SLIDE 5 — P2P NETWORK
# ══════════════════════════════════════════════════════════════
slide = add_slide()
section_header(slide, "Decentralised P2P Communication", "ZeroMQ PUB/SUB Mesh — No Central Broker")

# Left — how it works
box(slide, 0.4, 1.05, 5.8, 5.8, BG_PANEL)
txt(slide, "How It Works", 0.6, 1.15, 5.4, 0.38,
    size=14, bold=True, color=ACC_BLUE)
accent_bar(slide, 0.6, 1.5, 5.2, 0.03, ACC_BLUE)

how = [
    ("Each robot binds a PUB socket",  "Port: BASE_PORT + robot_id"),
    ("Each robot connects SUB sockets","To all other robots' PUB ports"),
    ("InProcessBus for simulation",    "Same API as real ZeroMQ hardware"),
    ("PeerStateCache per robot",       "Thread-safe latest position store"),
    ("Message TTL: 3 hops",            "Prevents broadcast storms"),
]
for i, (a, b) in enumerate(how):
    txt(slide, f"▸  {a}", 0.6, 1.65+i*0.9, 5.4, 0.32,
        size=12, bold=True, color=TXT_MAIN)
    txt(slide, f"   {b}", 0.6, 1.93+i*0.9, 5.4, 0.28,
        size=10, color=TXT_MUT)

# Centre — message types
box(slide, 6.5, 1.05, 3.5, 5.8, BG_PANEL)
txt(slide, "Message Types", 6.7, 1.15, 3.1, 0.38,
    size=14, bold=True, color=ACC_YELL)
accent_bar(slide, 6.7, 1.5, 3.0, 0.03, ACC_YELL)
msgs = [
    ("POSITION",    "pos + battery + state"),
    ("INTENT",      "next planned cell"),
    ("TASK_BID",    "robot bids on task"),
    ("TASK_AWARD",  "winner notified"),
    ("BLOCK_ALERT", "blocked cell reported"),
    ("PING",        "liveness heartbeat"),
]
for i, (t, d) in enumerate(msgs):
    chip(slide, t, 6.65, 1.65+i*0.82, 1.5, 0.3, BG_CARD, ACC_BLUE)
    txt(slide, d, 8.25, 1.67+i*0.82, 1.6, 0.28,
        size=10, color=TXT_MUT)

# Right — edge hardware
box(slide, 10.3, 1.05, 2.65, 5.8, BG_PANEL)
txt(slide, "Edge Hardware", 10.5, 1.15, 2.3, 0.38,
    size=14, bold=True, color=ACC_GREEN)
accent_bar(slide, 10.5, 1.5, 2.2, 0.03, ACC_GREEN)
hw = ["Raspberry Pi 4","Jetson Nano","ESP32 (future)","Local Wi-Fi mesh","No cloud needed","Offline capable"]
for i, h in enumerate(hw):
    txt(slide, f"✔  {h}", 10.5, 1.65+i*0.82, 2.3, 0.3,
        size=11, color=ACC_GREEN)


# ══════════════════════════════════════════════════════════════
#  SLIDE 6 — DASHBOARD FEATURES
# ══════════════════════════════════════════════════════════════
slide = add_slide()
section_header(slide, "AMRoboSync Fleet Dashboard", "Real-Time Monitoring — http://localhost:8080")

pages = [
    ("⊞  Overview",    ACC_BLUE,  ["Live warehouse map","KPI row (5 metrics)","Fleet donut chart","System metrics","Decision log"]),
    ("🗺  Live Map",    ACC_GREEN, ["Full-screen canvas","Zoom in/out/reset","All layer toggles","Robot SVG sprites","P2P mesh lines"]),
    ("🤖  Robots",      ACC_YELL,  ["Robot list + detail","SVG avatar per robot","Sensor panel (6)","Battery status bar","Send Command console"]),
    ("📊  Analytics",   ACC_PURP,  ["Task completion chart","Conflicts timeline","Fleet utilisation %","Battery all robots","6 KPI tiles"]),
    ("📋  Tasks",       RGBColor(0x26,0xc6,0xda), ["Full task queue","Priority badges","Assigned robot","Pickup/dropoff coords","Status column"]),
    ("🔔  Alerts",      ACC_RED,   ["Live event stream","CBS decisions","Deadlock alerts","Task completions","Clear + export"]),
]

for i, (name, color, feats) in enumerate(pages):
    col = i % 3
    row = i // 3
    x = 0.4 + col * 4.28
    y = 1.05 + row * 3.05
    box(slide, x, y, 4.0, 2.8, BG_PANEL)
    txt(slide, name, x+0.15, y+0.1, 3.7, 0.4,
        size=13, bold=True, color=color)
    accent_bar(slide, x+0.15, y+0.48, 3.5, 0.03, color)
    for j, f in enumerate(feats):
        txt(slide, f"  •  {f}", x+0.15, y+0.58+j*0.4, 3.7, 0.35,
            size=10.5, color=TXT_MAIN)


# ══════════════════════════════════════════════════════════════
#  SLIDE 7 — INNOVATIONS
# ══════════════════════════════════════════════════════════════
slide = add_slide()
section_header(slide, "New Innovations", "Beyond the Problem Statement — Extra Features")

innovations = [
    ("🔥  Traffic Heatmap", ACC_RED, RGBColor(0x40,0x10,0x08),
     "Dynamic heat overlay on warehouse grid",
     ["Cells darken as robots visit them","Slow decay (×0.96 every 8 ticks)","Shows traffic hotspots in real time","Identifies bottleneck aisles","Helps optimize warehouse layout"]),

    ("📡  P2P Mesh Overlay", ACC_BLUE, RGBColor(0x05,0x18,0x30),
     "Live signal lines between nearby robots",
     ["Lines fade with distance","Only shown for robots within 8 cells","Visualises actual ZeroMQ topology","Signal strength bars in Robots page","No router / no cloud needed"]),

    ("👻  Predictive Ghost Path", ACC_PURP, RGBColor(0x18,0x0a,0x40),
     "CBS-planned path preview for each robot",
     ["Dashed purple ring shows intended route","Updated every replan interval","Helps operator predict future state","Ghost fades for waiting robots","Disappears when path is complete"]),

    ("🏷  Priority Badge System", ACC_YELL, RGBColor(0x30,0x25,0x05),
     "Dynamic task urgency visible everywhere",
     ["HIGH / MED / LOW colour badges","Auction bid weighted by priority","High-priority tasks assigned first","Visible in task table + map overlay","Prevents low-priority task starvation"]),
]

for i, (title, color, bg, subtitle, points) in enumerate(innovations):
    col = i % 2
    row = i // 2
    x = 0.4 + col * 6.5
    y = 1.05 + row * 3.05
    box(slide, x, y, 6.1, 2.8, bg)
    box(slide, x, y, 6.1, 0.55, color)
    txt(slide, title, x+0.15, y+0.07, 5.8, 0.42,
        size=14, bold=True, color=RGBColor(0x05,0x08,0x14))
    txt(slide, subtitle, x+0.15, y+0.65, 5.7, 0.3,
        size=11, italic=True, color=color)
    for j, pt in enumerate(points):
        txt(slide, f"•  {pt}", x+0.2, y+1.0+j*0.36, 5.7, 0.3,
            size=10.5, color=TXT_MAIN)


# ══════════════════════════════════════════════════════════════
#  SLIDE 8 — BENCHMARK RESULTS
# ══════════════════════════════════════════════════════════════
slide = add_slide()
section_header(slide, "Benchmark Results", "CBS/A* vs Stop-and-Wait — 300 Ticks, 8 Robots, 16×16 Grid")

# Big result box
box(slide, 0.4, 1.05, 12.5, 1.6, BG_PANEL)
txt(slide, "+24.0% Throughput Improvement", 0.5, 1.15, 12.0, 0.85,
    size=44, bold=True, color=ACC_GREEN, align=PP_ALIGN.CENTER)
txt(slide, "CBS/A* completes 31 tasks vs 25 for Stop-and-Wait in same 300 ticks  —  Success Criterion: ≥20%  ✅  PASSED",
    0.5, 1.9, 12.0, 0.5,
    size=13, color=TXT_MUT, align=PP_ALIGN.CENTER)

# KPI cards
kpi_data = [
    ("Tasks Completed\nCBS / A*",   "31",   "tasks",  ACC_GREEN),
    ("Tasks Completed\nStop & Wait","25",   "tasks",  ACC_RED),
    ("Throughput\nCBS / A*",        "0.103","tasks/tk",ACC_GREEN),
    ("Throughput\nStop & Wait",     "0.083","tasks/tk",ACC_RED),
    ("Collisions\nCBS / A*",        "0",    "ZERO ✅", ACC_GREEN),
]
for i, (lbl, val, unit, col) in enumerate(kpi_data):
    kpi_card(slide, lbl, val, unit, 0.4+i*2.5, 2.85, col, 2.35, 1.3)

# Comparison table
box(slide, 0.4, 4.35, 12.5, 2.65, BG_PANEL)
txt(slide, "Detailed Comparison", 0.6, 4.42, 12.0, 0.38,
    size=13, bold=True, color=ACC_BLUE)

headers = ["Metric", "CBS / A*", "Stop & Wait", "Improvement"]
col_x   = [0.6,  3.5,  7.0,  10.0]
col_w   = [2.8,  3.3,  2.8,   3.0]
# Header row
for j, (h, cx) in enumerate(zip(headers, col_x)):
    box(slide, cx-0.05, 4.78, col_w[j], 0.35, BG_CARD)
    txt(slide, h, cx, 4.82, col_w[j]-0.1, 0.28,
        size=10, bold=True, color=ACC_YELL, align=PP_ALIGN.CENTER)

rows = [
    ("Tasks Completed",        "31",     "25",     "+24.0% ✅"),
    ("Throughput (tasks/tick)", "0.1033", "0.0833", "+24.0% ✅"),
    ("Avg Completion Tick",    "128.2",  "152.1",  "−15.7%  ✅"),
    ("Collision Events",       "0",      "0",      "ZERO  ✅"),
    ("Conflicts Resolved",     "13",     "0 (none)","CBS only"),
]
row_colors = [TXT_MAIN, TXT_MAIN, TXT_MAIN, ACC_GREEN, TXT_MUT]
for ri, (row, rc) in enumerate(zip(rows, row_colors)):
    for j, (val, cx) in enumerate(zip(row, col_x)):
        vc = rc if j > 0 else TXT_MAIN
        if j == 3 and "✅" in val: vc = ACC_GREEN
        txt(slide, val, cx, 5.2+ri*0.36, col_w[j]-0.1, 0.3,
            size=10, color=vc, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════
#  SLIDE 9 — LIVE DEMO / HOW TO RUN
# ══════════════════════════════════════════════════════════════
slide = add_slide()
section_header(slide, "Live Demo — How to Run", "One Command → Full Simulation + Dashboard")

# Terminal box
box(slide, 0.4, 1.05, 8.5, 4.5, BG_PANEL)
txt(slide, ">_  Terminal", 0.6, 1.12, 8.0, 0.38,
    size=12, bold=True, color=ACC_GREEN)
accent_bar(slide, 0.6, 1.48, 7.8, 0.03, ACC_GREEN)

commands = [
    ("# Step 1 — Navigate to project", TXT_MUT),
    ("cd C:\\Users\\netan\\Documents\\amr-fleet", ACC_GREEN),
    ("", TXT_MUT),
    ("# Step 2 — Run simulation + dashboard", TXT_MUT),
    ("python run.py", ACC_BLUE),
    ("", TXT_MUT),
    ("# Step 3 — Open browser", TXT_MUT),
    ("http://localhost:8080", ACC_YELL),
    ("", TXT_MUT),
    ("# Optional — Benchmark CBS vs Stop-and-Wait", TXT_MUT),
    ("python run.py --benchmark --ticks 300", ACC_PURP),
]
for i, (cmd, col) in enumerate(commands):
    txt(slide, cmd, 0.65, 1.6+i*0.27, 8.0, 0.26,
        size=10.5, color=col)

# Right — what you see
box(slide, 9.2, 1.05, 3.85, 4.5, BG_PANEL)
txt(slide, "What You'll See", 9.4, 1.12, 3.5, 0.38,
    size=12, bold=True, color=ACC_BLUE)
accent_bar(slide, 9.4, 1.48, 3.3, 0.03, ACC_BLUE)
see = [
    ("🗺", "Live warehouse map"),
    ("🤖", "8 robots moving"),
    ("🔥", "Traffic heatmap"),
    ("📡", "P2P mesh lines"),
    ("👻", "Ghost paths"),
    ("📊", "Live analytics"),
    ("🔔", "CBS decisions"),
    ("⚡", "Zero collisions"),
]
for i, (ic, lbl) in enumerate(see):
    txt(slide, f"{ic}  {lbl}", 9.4, 1.6+i*0.48, 3.5, 0.35,
        size=12, color=TXT_MAIN)

# Bottom requirements
box(slide, 0.4, 5.75, 12.5, 1.25, BG_CARD)
txt(slide, "Requirements:   Python 3.10+  •  pip install pyzmq websockets aiohttp colorlog  •  Any modern browser",
    0.6, 5.85, 12.0, 0.38,
    size=12, color=TXT_MUT, align=PP_ALIGN.CENTER)
txt(slide, "Files:   run.py  •  simulation.py  •  core/  •  planning/  •  comms/  •  dashboard/",
    0.6, 6.2, 12.0, 0.35,
    size=11, color=ACC_BLUE, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════
#  SLIDE 10 — CONCLUSION
# ══════════════════════════════════════════════════════════════
slide = add_slide()
section_header(slide, "Conclusion & Success Criteria", "All BEL Requirements Met + Extra Innovations")

# Success criteria
box(slide, 0.4, 1.05, 5.9, 5.9, BG_PANEL)
txt(slide, "✅  Success Criteria — ALL MET", 0.6, 1.12, 5.5, 0.42,
    size=14, bold=True, color=ACC_GREEN)
accent_bar(slide, 0.6, 1.52, 5.4, 0.04, ACC_GREEN)

criteria = [
    ("Zero inter-robot collisions",        "0 collisions in 300 ticks"),
    ("≥20% task completion improvement",   "+24.0% throughput ✅"),
    ("Decentralised — no central server",  "P2P ZeroMQ mesh"),
    ("Runs on edge hardware",              "Raspberry Pi / Jetson Nano"),
    ("3+ AMRs supported",                  "8 robots simulated"),
    ("Dynamic path re-routing",            "CBS + auction re-assign"),
    ("Fleet monitoring dashboard",         "7-page live UI"),
]
for i, (c, v) in enumerate(criteria):
    txt(slide, f"  ✔  {c}", 0.6, 1.65+i*0.73, 5.5, 0.32,
        size=11.5, bold=True, color=ACC_GREEN)
    txt(slide, f"       → {v}", 0.6, 1.94+i*0.73, 5.5, 0.28,
        size=10, color=TXT_MUT)

# Tech stack
box(slide, 6.6, 1.05, 3.0, 5.9, BG_PANEL)
txt(slide, "Tech Stack", 6.8, 1.12, 2.7, 0.38,
    size=13, bold=True, color=ACC_BLUE)
accent_bar(slide, 6.8, 1.48, 2.5, 0.04, ACC_BLUE)
stack = [("Language","Python 3.10"),("Comms","ZeroMQ P2P"),
         ("Planning","CBS + A*"),("Allocation","Auction"),
         ("Server","aiohttp + WS"),("Frontend","HTML5 Canvas"),
         ("Charts","Vanilla JS"),("Target HW","RPi / Jetson")]
for i, (k, v) in enumerate(stack):
    txt(slide, k+":", 6.8, 1.6+i*0.65, 1.1, 0.3,
        size=10, color=TXT_MUT)
    txt(slide, v, 7.95, 1.6+i*0.65, 1.5, 0.3,
        size=10, bold=True, color=ACC_BLUE)

# Innovations
box(slide, 9.9, 1.05, 3.05, 5.9, BG_PANEL)
txt(slide, "Innovations", 10.1, 1.12, 2.7, 0.38,
    size=13, bold=True, color=ACC_YELL)
accent_bar(slide, 10.1, 1.48, 2.5, 0.04, ACC_YELL)
innov = [("🔥","Traffic Heatmap"),("📡","P2P Mesh Overlay"),
         ("👻","Predictive Ghost"),("🏷","Priority Badges"),
         ("📶","Signal Strength"),("🧠","Decision Log"),
         ("📊","Live Analytics"),("🤖","SVG Robot Avatars")]
for i, (ic, name) in enumerate(innov):
    txt(slide, f"{ic}  {name}", 10.1, 1.65+i*0.65, 2.6, 0.3,
        size=11, color=ACC_YELL)

# Final tagline
box(slide, 0.4, 7.0, 12.5, 0.35, ACC_BLUE)
txt(slide, "AMRoboSync — Smarter Warehouses, Zero Collisions, Edge-Powered Coordination  ·  BEL 2026",
    0.5, 7.03, 12.3, 0.3,
    size=11, bold=True, color=BG_DARK, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════
#  SAVE
# ══════════════════════════════════════════════════════════════
OUT = "AMRoboSync_BEL_Presentation.pptx"
prs.save(OUT)
print("=" * 55)
print("  PPT GENERATED SUCCESSFULLY")
print("=" * 55)
print(f"  File    : {OUT}")
print(f"  Slides  : {len(prs.slides)}")
print(f"  Theme   : Dark (AMRoboSync brand)")
print()
print("  Slides included:")
titles = ["Title","Problem Statement","System Architecture",
          "Key Algorithms","P2P Network","Dashboard Features",
          "Innovations","Benchmark Results","Live Demo","Conclusion"]
for i, t in enumerate(titles, 1):
    print(f"    {i:2d}.  {t}")
print()
print("  Open the file in PowerPoint / LibreOffice Impress")
print("=" * 55)
