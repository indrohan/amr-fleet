# Edge-AI Based Distributed Fleet Coordination for AMRs in Smart Warehouses

**Organization:** Bharat Electronics Limited  
**Problem Statement:** Decentralized coordination and collision-avoidance for a multi-robot fleet operating in a dynamic warehouse environment.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    SIMULATION ENGINE                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  AMR-1   │  │  AMR-2   │  │  AMR-3   │  │  AMR-N │  │
│  │ (Edge)   │  │ (Edge)   │  │ (Edge)   │  │ (Edge) │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
│       │              │              │             │       │
│       └──────────────┴──────────────┴─────────────┘      │
│                  P2P ZeroMQ Mesh Network                  │
│                  (No Central Server)                      │
└─────────────────────┬───────────────────────────────────-┘
                      │ WebSocket
              ┌───────▼────────┐
              │ Fleet Dashboard │
              │  (Browser UI)  │
              └────────────────┘
```
## 🎥 Live Dashboard Demo

The following videos demonstrate the real-time AMR Fleet Coordination System, including fleet monitoring, live map visualization, robot status, task coordination, and dashboard operation.

### 🖥️ AMR Fleet Dashboard

[▶️ Watch Dashboard Demo](./demo/AMR_Fleet_Dashboard_Demo.mp4)

### 🗺️ Live Map Visualization

[▶️ Watch Live Map Demo](./demo/AMR_Fleet_Dashboard_Demo_live_map.mp4)

### 🤖 Robot List & Fleet Monitoring

[▶️ Watch Robot List Demo](./demo/AMR_Fleet_Dashboard_Demo_ROBOT_LIST.mp4)

## Components

| Module | Description |
|---|---|
| `core/warehouse.py` | Grid warehouse map with obstacles, aisles, charging stations |
| `core/config.py` | All tuneable simulation parameters |
| `planning/astar.py` | A* single-agent pathfinding |
| `planning/cbs.py` | Conflict-Based Search for multi-agent planning |
| `core/robot.py` | AMR state machine (IDLE → NAVIGATING → CHARGING → ERROR) |
| `comms/p2p_network.py` | ZeroMQ PUB/SUB peer-to-peer mesh |
| `core/conflict_resolver.py` | Deadlock detection & resolution |
| `core/task_allocator.py` | Dynamic task assignment & re-routing |
| `simulation.py` | Main orchestration loop |
| `dashboard/server.py` | WebSocket bridge + HTTP server |
| `dashboard/static/index.html` | Fleet monitoring UI |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full simulation + dashboard
python run.py

# 3. Open your browser to:
#    http://localhost:8080
```

## Key Algorithms

- **A\*** for single-robot path planning on a weighted grid  
- **CBS (Conflict-Based Search)** for collision-free multi-agent paths  
- **SIPP (Safe Interval Path Planning)** concepts for time-expanded conflict detection  
- **Auction-based Task Allocation** — robots bid on tasks based on proximity and battery  
- **Deadlock Resolution** — token ring priority + random backoff for choke points  

## Success Criteria

- ✅ Zero inter-robot collisions  
- ✅ ≥20% reduction in total task completion time vs stop-and-wait  
- ✅ Fully decentralized — no single point of failure  
- ✅ Runs on edge hardware (Raspberry Pi / Jetson Nano class)  
