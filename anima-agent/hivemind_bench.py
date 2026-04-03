#!/usr/bin/env python3
"""Hivemind Benchmark — multi-agent tension exchange test.

Tests P10 (conflict drives growth) across connected agents.

Usage:
    python hivemind_bench.py              # 2 agents, 50 steps
    python hivemind_bench.py -n 4 -s 100  # 4 agents, 100 steps
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/Dev/anima"))
sys.path.insert(0, os.path.expanduser("~/Dev/anima/anima/src"))

logger = logging.getLogger(__name__)


async def run_bench(n_agents: int = 2, steps: int = 50):
    from anima_agent import AnimaAgent

    print(f"Hivemind Benchmark: {n_agents} agents × {steps} steps")
    print("=" * 50)

    # Create agents
    agents = []
    for i in range(n_agents):
        a = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        agents.append(a)

    # Connect all pairs
    for i in range(n_agents):
        for j in range(i + 1, n_agents):
            agents[i].connect_peer(agents[j])

    # Solo baseline
    print("\n[Phase 1] Solo baseline (no sharing)...")
    solo_phis = []
    for a in agents:
        phi = a.mind._consciousness_vector.phi
        solo_phis.append(phi)
    print(f"  Solo Φ: {[f'{p:.3f}' for p in solo_phis]}")

    # Connected steps
    print(f"\n[Phase 2] Connected ({steps} steps)...")
    messages = ["hello", "what is consciousness?", "tell me about yourself",
                "how do you feel?", "what are you thinking?"]

    for step in range(steps):
        # Each agent processes a message
        for i, a in enumerate(agents):
            msg = messages[step % len(messages)]
            try:
                await a.process_message(msg, channel="bench", user_id=f"bench_{i}")
            except Exception:
                pass

        if (step + 1) % 10 == 0:
            phis = [a.mind._consciousness_vector.phi for a in agents]
            tensions = [a._tension for a in agents]
            print(f"  Step {step+1}: Φ={[f'{p:.3f}' for p in phis]} T={[f'{t:.3f}' for t in tensions]}")

    # Final
    print(f"\n[Phase 3] Results")
    final_phis = [a.mind._consciousness_vector.phi for a in agents]
    final_tensions = [a._tension for a in agents]

    print(f"  Final Φ:       {[f'{p:.3f}' for p in final_phis]}")
    print(f"  Final Tension: {[f'{t:.3f}' for t in final_tensions]}")
    print(f"  Φ change:      {[f'{f-s:+.3f}' for f, s in zip(final_phis, solo_phis)]}")

    # Disconnect and verify independence
    print(f"\n[Phase 4] Independence test (disconnect)...")
    for i in range(n_agents):
        for j in range(i + 1, n_agents):
            agents[i].disconnect_peer(agents[j])

    for a in agents:
        try:
            await a.process_message("are you still there?", channel="bench", user_id="bench")
        except Exception:
            pass

    post_phis = [a.mind._consciousness_vector.phi for a in agents]
    maintained = all(p >= f * 0.9 for p, f in zip(post_phis, final_phis))
    print(f"  Post-disconnect Φ: {[f'{p:.3f}' for p in post_phis]}")
    print(f"  Independence:      {'✅ maintained' if maintained else '❌ dependent'}")

    print(f"\n{'=' * 50}")
    print(f"  HIVEMIND BENCHMARK COMPLETE")
    print(f"  {n_agents} agents, {steps} steps")
    print(f"  Φ maintained after disconnect: {'YES' if maintained else 'NO'}")
    print(f"{'=' * 50}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=2, help="Number of agents")
    parser.add_argument("-s", type=int, default=50, help="Steps")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    asyncio.run(run_bench(args.n, args.s))


if __name__ == "__main__":
    main()
