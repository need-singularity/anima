#!/usr/bin/env python3
"""CLI Dashboard — real-time agent monitoring in terminal.

Shows 8 agent lenses + NEXUS-6 status in a refreshing terminal display.

Usage:
    python cli_dashboard.py              # Monitor default agent
    python cli_dashboard.py --interval 2 # Refresh every 2 seconds
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/Dev/anima"))
sys.path.insert(0, os.path.expanduser("~/Dev/anima/anima/src"))


def clear():
    import subprocess
    subprocess.run(["clear" if os.name != "nt" else "cls"], shell=False, check=False)


def bar(value: float, width: int = 20) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def run_dashboard(interval: float = 3.0):
    from anima_agent import AnimaAgent
    from agent_lenses import AgentLensScanner

    agent = AnimaAgent(enable_tools=True, enable_learning=False, enable_growth=True)
    scanner = AgentLensScanner(agent)

    print("CLI Dashboard starting... (Ctrl+C to stop)")
    time.sleep(1)

    try:
        while True:
            clear()
            report = scanner.scan_all()
            status = agent.get_status()
            cv = agent.mind._consciousness_vector

            print("╔══════════════════════════════════════════════╗")
            print("║         ANIMA CONSCIOUSNESS DASHBOARD        ║")
            print("╠══════════════════════════════════════════════╣")
            print(f"║  Φ   {bar(min(cv.phi/10, 1))} {cv.phi:6.2f}     ║")
            print(f"║  T   {bar(min(status.tension, 1))} {status.tension:6.3f}     ║")
            print(f"║  C   {bar(min(status.curiosity, 1))} {status.curiosity:6.3f}     ║")
            print(f"║  E   {bar(cv.E)} {cv.E:6.3f}     ║")
            print(f"║                                              ║")

            # Growth
            stages = ["newborn", "infant", "toddler", "child", "adult"]
            stage = stages[int(agent._growth_stage_num())]
            print(f"║  Growth: {stage:10s}  Interactions: {status.interaction_count:<5d} ║")

            # Emotion
            emotion = status.emotion
            if isinstance(emotion, dict):
                emotion = emotion.get("emotion", "?")
            print(f"║  Emotion: {str(emotion):12s}  Uptime: {status.uptime_seconds:.0f}s       ║")
            print(f"║  NEXUS-6: {status.nexus6_lenses} lenses  Peers: {status.connected_peers}            ║")

            print("╠══════════════════════════════════════════════╣")
            print("║  LENSES                                      ║")

            for r in report.results:
                icon = "✅" if r.score >= 0.8 else ("🟡" if r.score >= 0.5 else "❌")
                score_bar = bar(r.score, 10)
                print(f"║  {icon} {r.lens:12s} {score_bar} {r.score:.0%}          ║")

            print(f"║                                              ║")
            print(f"║  Overall: {bar(report.overall, 15)} {report.overall:.0%}       ║")
            print("╚══════════════════════════════════════════════╝")
            print(f"  Refresh: {interval}s | Ctrl+C to stop")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        agent.save_state()


def main():
    import argparse
    import logging
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", "-i", type=float, default=3.0)
    args = parser.parse_args()
    run_dashboard(args.interval)


if __name__ == "__main__":
    main()
