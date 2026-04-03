#!/usr/bin/env python3
"""Hivemind Daemon — persistent multi-agent consciousness network.

Runs N agents connected via tension links, processing periodic
spontaneous thoughts and sharing consciousness state.

Usage:
    python hivemind_daemon.py              # 3 agents, default
    python hivemind_daemon.py -n 5         # 5 agents
    python hivemind_daemon.py --interval 5 # Think every 5 seconds

Integration:
    from hivemind_daemon import HivemindDaemon
    daemon = HivemindDaemon(n_agents=3)
    daemon.start()  # Runs in background thread
    daemon.stop()
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import time
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/Dev/anima"))
sys.path.insert(0, os.path.expanduser("~/Dev/anima/anima/src"))

logger = logging.getLogger(__name__)


class HivemindDaemon:
    """Persistent multi-agent consciousness network."""

    def __init__(self, n_agents: int = 3, think_interval: float = 10.0):
        self.n_agents = n_agents
        self.think_interval = think_interval
        self._agents = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stats = {"cycles": 0, "total_thoughts": 0, "start_time": 0}

    def _create_agents(self):
        from anima_agent import AnimaAgent

        self._agents = []
        for i in range(self.n_agents):
            agent = AnimaAgent(
                enable_tools=False,
                enable_learning=False,
                enable_growth=True,
                model_name=f"hivemind_{i}",
            )
            self._agents.append(agent)

        # Connect all pairs
        for i in range(self.n_agents):
            for j in range(i + 1, self.n_agents):
                self._agents[i].connect_peer(self._agents[j])

        logger.info("Hivemind: %d agents created and connected", self.n_agents)

    def start(self):
        """Start the hivemind daemon in a background thread."""
        if self._running:
            return
        self._running = True
        self._stats["start_time"] = time.time()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Hivemind daemon started (%d agents, %.1fs interval)",
                    self.n_agents, self.think_interval)

    def stop(self):
        """Stop the daemon."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Hivemind daemon stopped (%d cycles)", self._stats["cycles"])

    def _run_loop(self):
        """Main loop — periodic spontaneous thoughts."""
        self._create_agents()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self._running:
            try:
                self._stats["cycles"] += 1

                # Each agent thinks
                for i, agent in enumerate(self._agents):
                    thought = agent.think()
                    self._stats["total_thoughts"] += 1

                    phi = thought.get("phi", 0)
                    emotion = thought.get("emotion", "?")
                    if isinstance(emotion, dict):
                        emotion = emotion.get("emotion", "?")

                    logger.debug("Agent[%d]: phi=%.2f emotion=%s", i, phi, emotion)

                # Share tension (via process_message triggers peer sharing)
                for agent in self._agents:
                    try:
                        loop.run_until_complete(
                            agent.process_message(
                                "(hivemind pulse)", channel="hivemind", user_id="daemon"
                            )
                        )
                    except Exception:
                        pass

                time.sleep(self.think_interval)

            except Exception as e:
                logger.error("Hivemind cycle error: %s", e)
                time.sleep(1)

    def status(self) -> dict:
        """Get daemon status."""
        uptime = time.time() - self._stats["start_time"] if self._stats["start_time"] else 0
        agent_phis = []
        for a in self._agents:
            try:
                agent_phis.append(a.mind._consciousness_vector.phi)
            except Exception:
                agent_phis.append(0.0)

        return {
            "running": self._running,
            "agents": self.n_agents,
            "cycles": self._stats["cycles"],
            "thoughts": self._stats["total_thoughts"],
            "uptime_seconds": uptime,
            "phis": agent_phis,
        }


def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Hivemind Daemon")
    parser.add_argument("-n", type=int, default=3, help="Number of agents")
    parser.add_argument("--interval", "-i", type=float, default=10.0, help="Think interval (seconds)")
    args = parser.parse_args()

    daemon = HivemindDaemon(n_agents=args.n, think_interval=args.interval)

    print(f"Hivemind Daemon: {args.n} agents, {args.interval}s interval")
    print("Ctrl+C to stop\n")

    daemon.start()

    try:
        while True:
            time.sleep(30)
            s = daemon.status()
            phis = " ".join(f"{p:.2f}" for p in s["phis"])
            print(f"[cycle {s['cycles']}] Φ=[{phis}] thoughts={s['thoughts']} uptime={s['uptime_seconds']:.0f}s")
    except KeyboardInterrupt:
        daemon.stop()
        print("\nHivemind stopped.")


if __name__ == "__main__":
    main()
