"""
run.py — Entry point for the AMR Fleet Coordination simulation.

Usage
─────
  # Full simulation + live dashboard
  python run.py

  # Benchmark: run CBS vs stop-and-wait, no dashboard
  python run.py --benchmark

  # Headless (no dashboard)
  python run.py --headless

  # Custom tick cap
  python run.py --ticks 500
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

# Ensure project root is on the path when run from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _setup_logging(level: str = "INFO") -> None:
    import colorlog
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s "
        "%(cyan)s%(name)s%(reset)s — %(message)s",
        log_colors={
            "DEBUG"   : "white",
            "INFO"    : "green",
            "WARNING" : "yellow",
            "ERROR"   : "red",
            "CRITICAL": "bold_red",
        },
    ))
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    # File handler
    os.makedirs("logs", exist_ok=True)
    fh = logging.FileHandler("logs/simulation.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
    ))
    root.addHandler(fh)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Edge-AI AMR Fleet Coordination Simulation")
    parser.add_argument("--headless",   action="store_true",
                        help="Run without dashboard (no HTTP/WS servers)")
    parser.add_argument("--benchmark",  action="store_true",
                        help="Run CBS then stop-and-wait and compare")
    parser.add_argument("--ticks",      type=int, default=0,
                        help="Override MAX_TICKS (0 = use config default)")
    parser.add_argument("--log-level",  default="INFO",
                        help="Logging level: DEBUG|INFO|WARNING")
    parser.add_argument("--saw",        action="store_true",
                        help="Run in stop-and-wait mode (for manual comparison)")
    return parser.parse_args()


# ── Dashboard mode ─────────────────────────────────────────────────────────────

async def _run_with_dashboard(stop_and_wait: bool, ticks: int) -> None:
    import core.config as cfg
    if ticks:
        cfg.MAX_TICKS = ticks

    state_queue: asyncio.Queue = asyncio.Queue(maxsize=50)

    from simulation        import SimulationEngine
    from dashboard.server  import start_servers

    engine = SimulationEngine(
        stop_and_wait=stop_and_wait,
        state_queue=state_queue,
    )
    await start_servers(state_queue, engine.run_async())


# ── Headless mode ──────────────────────────────────────────────────────────────

async def _run_headless(stop_and_wait: bool, ticks: int) -> None:
    import core.config as cfg
    if ticks:
        cfg.MAX_TICKS = ticks
    if cfg.MAX_TICKS == 0:
        cfg.MAX_TICKS = 300   # sensible default for headless

    from simulation import SimulationEngine
    engine = SimulationEngine(stop_and_wait=stop_and_wait, state_queue=None)
    await engine.run_async()


# ── Benchmark mode ─────────────────────────────────────────────────────────────

async def _run_benchmark(ticks: int) -> None:
    import core.config as cfg
    cfg.MAX_TICKS = ticks if ticks else 300

    from simulation import SimulationEngine

    print("\n" + "═"*60)
    print("  BENCHMARK: CBS/A* vs Stop-and-Wait")
    print("═"*60)

    # --- CBS run ---
    print("\n▶  Running CBS/A* …")
    from comms.p2p_network import InProcessBus
    InProcessBus.reset()
    cbs_engine = SimulationEngine(stop_and_wait=False, state_queue=None)
    await cbs_engine.run_async()
    cbs_done = len(cbs_engine.allocator.completed_tasks)
    cbs_avg  = (sum(cbs_engine._task_completion_ticks) /
                max(1, len(cbs_engine._task_completion_ticks)))

    # --- Stop-and-wait run ---
    print("\n▶  Running Stop-and-Wait …")
    InProcessBus.reset()
    saw_engine = SimulationEngine(stop_and_wait=True, state_queue=None)
    await saw_engine.run_async()
    saw_done = len(saw_engine.allocator.completed_tasks)
    saw_avg  = (sum(saw_engine._task_completion_ticks) /
                max(1, len(saw_engine._task_completion_ticks)))

    # --- Report ---
    cbs_throughput = cbs_done / cfg.MAX_TICKS
    saw_throughput = saw_done / cfg.MAX_TICKS
    throughput_improvement = ((cbs_throughput - saw_throughput) /
                              max(0.001, saw_throughput)) * 100

    cbs_wait = cbs_engine._stats_dict().get("total_wait_ticks", 0)
    saw_wait = saw_engine._stats_dict().get("total_wait_ticks", 0)
    wait_reduction = ((saw_wait - cbs_wait) / max(1, saw_wait)) * 100

    print("\n" + "═"*60)
    print("  BENCHMARK RESULTS")
    print("═"*60)
    print(f"  {'Metric':<35} {'CBS/A*':>8} {'Stop&Wait':>10}")
    print(f"  {'-'*55}")
    print(f"  {'Tasks completed':<35} {cbs_done:>8} {saw_done:>10}")
    print(f"  {'Throughput (tasks/tick)':<35} {cbs_throughput:>8.4f} {saw_throughput:>10.4f}")
    print(f"  {'Total fleet wait-ticks':<35} {cbs_wait:>8} {saw_wait:>10}")
    print(f"  {'Avg completion tick':<35} {cbs_avg:>8.1f} {saw_avg:>10.1f}")
    print()
    print(f"  Throughput improvement     : {throughput_improvement:+.1f}%")
    print(f"  Fleet idle-time reduction  : {wait_reduction:+.1f}%")

    # Primary criterion: throughput OR idle-time reduction ≥ 20%
    passes = throughput_improvement >= 20 or wait_reduction >= 20
    goal = "✅ PASS" if passes else "❌ FAIL (target ≥20%)"
    print(f"\n  Success criterion (≥20% improvement): {goal}")
    print("═"*60 + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    # Try colorlog; fall back to plain if not installed
    try:
        _setup_logging(args.log_level)
    except ImportError:
        logging.basicConfig(
            level=getattr(logging, args.log_level.upper(), logging.INFO),
            format="%(levelname)-8s %(name)s — %(message)s",
        )

    if args.benchmark:
        asyncio.run(_run_benchmark(args.ticks))
    elif args.headless or args.saw:
        asyncio.run(_run_headless(args.saw, args.ticks))
    else:
        try:
            asyncio.run(_run_with_dashboard(False, args.ticks))
        except KeyboardInterrupt:
            print("\nSimulation interrupted by user.")


if __name__ == "__main__":
    main()
