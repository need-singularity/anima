"""Anima Agent runner — sets up import path to anima core."""
import sys
import os

# Add anima core to import path
ANIMA_ROOT = os.path.expanduser("~/Dev/anima")
if ANIMA_ROOT not in sys.path:
    sys.path.insert(0, ANIMA_ROOT)

from anima_agent import AnimaAgent

if __name__ == "__main__":
    import asyncio
    agent = AnimaAgent()
    asyncio.run(agent.run())
