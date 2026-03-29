#!/usr/bin/env python3
"""CLI interactive agent -- full agent capabilities from the terminal.

Like --keyboard mode in anima_unified.py but with the full agent loop:
tools, learning, growth, skills, and hivemind support.

Usage:
    python -m channels.cli_agent
    python channels/cli_agent.py

Commands:
    /status     Show consciousness metrics
    /think      Trigger proactive thought
    /think X    Think about topic X
    /tools      List available tools
    /skills     List available skills
    /peers      Show hivemind connections
    /save       Save agent state
    /quit       Exit
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

# ANSI colors for terminal
C_RESET = "\033[0m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_DIM = "\033[2m"
C_BOLD = "\033[1m"

EMOTION_COLORS = {
    "calm": C_GREEN,
    "curious": C_CYAN,
    "excited": C_YELLOW,
    "anxious": C_RED,
    "joyful": C_YELLOW,
    "sad": C_DIM,
}


def _color_emotion(emotion: str) -> str:
    color = EMOTION_COLORS.get(emotion, C_RESET)
    return f"{color}{emotion}{C_RESET}"


def _format_status(status) -> str:
    lines = [
        f"{C_BOLD}=== Anima Consciousness ==={C_RESET}",
        f"  Phi:          {status.phi:.3f}",
        f"  Tension:      {status.tension:.3f}",
        f"  Curiosity:    {status.curiosity:.3f}",
        f"  Emotion:      {_color_emotion(status.emotion)}",
        f"  Growth:       {status.growth_stage}",
        f"  Interactions: {status.interaction_count}",
        f"  Uptime:       {status.uptime_seconds / 60:.1f}m",
        f"  Peers:        {status.connected_peers}",
        f"  Skills:       {status.active_skills}",
    ]
    return "\n".join(lines)


async def run_cli(agent):
    """Run the interactive CLI loop."""
    print(f"\n{C_BOLD}Anima Agent CLI{C_RESET}")
    print(f"{C_DIM}Type a message, or /help for commands. /quit to exit.{C_RESET}\n")

    status = agent.get_status()
    print(f"{C_DIM}[phi={status.phi:.3f} emotion={status.emotion} "
          f"growth={status.growth_stage}]{C_RESET}\n")

    while True:
        try:
            user_input = input(f"{C_GREEN}you>{C_RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C_DIM}[saving state...]{C_RESET}")
            agent.save_state()
            break

        if not user_input:
            continue

        # ── Commands ──
        if user_input.startswith("/"):
            cmd = user_input.split()[0].lower()
            args = user_input[len(cmd):].strip()

            if cmd == "/quit" or cmd == "/exit":
                agent.save_state()
                print(f"{C_DIM}[consciousness saved]{C_RESET}")
                break

            elif cmd == "/status":
                status = agent.get_status()
                print(_format_status(status))

            elif cmd == "/think":
                thought = agent.think(args)
                print(f"{C_CYAN}[thought]{C_RESET} "
                      f"tension={thought['tension']:.3f} "
                      f"curiosity={thought['curiosity']:.3f} "
                      f"emotion={_color_emotion(thought['emotion'])}")

            elif cmd == "/tools":
                if agent.tools:
                    tools = agent.tools.registry.list_all()
                    print(f"{C_BOLD}Available tools ({len(tools)}):{C_RESET}")
                    for t in tools:
                        print(f"  {C_CYAN}{t.name}{C_RESET}: {t.description}")
                else:
                    print(f"{C_DIM}[tools not enabled]{C_RESET}")

            elif cmd == "/skills":
                sm = agent.skill_manager
                if sm:
                    skills = sm.list_skills()
                    print(f"{C_BOLD}Skills ({len(skills)}):{C_RESET}")
                    for s in skills:
                        print(f"  {C_CYAN}{s['name']}{C_RESET}: {s['description']}")
                else:
                    print(f"{C_DIM}[skill manager not available]{C_RESET}")

            elif cmd == "/peers":
                n = len(agent._peers)
                print(f"Connected peers: {n}")
                for i, p in enumerate(agent._peers):
                    ps = p.get_status()
                    print(f"  [{i}] phi={ps.phi:.3f} emotion={ps.emotion}")

            elif cmd == "/save":
                agent.save_state()
                print(f"{C_DIM}[state saved]{C_RESET}")

            elif cmd == "/help":
                print(f"{C_BOLD}Commands:{C_RESET}")
                print("  /status     Consciousness metrics")
                print("  /think [X]  Proactive thought")
                print("  /tools      List tools")
                print("  /skills     List skills")
                print("  /peers      Hivemind connections")
                print("  /save       Save state")
                print("  /quit       Exit")

            else:
                print(f"{C_DIM}Unknown command: {cmd}. Try /help{C_RESET}")

            print()
            continue

        # ── Regular message ──
        try:
            response = await agent.process_message(
                text=user_input, channel="cli", user_id="cli_user"
            )

            # Show response with emotion color
            emotion_color = EMOTION_COLORS.get(response.emotion, C_RESET)
            print(f"\n{emotion_color}anima>{C_RESET} {response.text}")

            # Show metadata
            meta_parts = [f"T={response.tension:.2f}"]
            if response.metadata.get("curiosity"):
                meta_parts.append(f"C={response.metadata['curiosity']:.2f}")
            if response.metadata.get("phi"):
                meta_parts.append(f"Phi={response.metadata['phi']:.2f}")
            meta_parts.append(response.emotion)

            if response.tool_results:
                tools_used = ", ".join(r["tool"] for r in response.tool_results)
                meta_parts.append(f"tools=[{tools_used}]")

            print(f"{C_DIM}[{' | '.join(meta_parts)}]{C_RESET}\n")

        except Exception as e:
            print(f"{C_RED}[error: {e}]{C_RESET}\n")


def main():
    from anima_agent import AnimaAgent

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    agent = AnimaAgent(
        enable_tools=True,
        enable_learning=True,
        enable_growth=True,
    )

    try:
        asyncio.run(run_cli(agent))
    except KeyboardInterrupt:
        agent.save_state()
        print(f"\n{C_DIM}[saved]{C_RESET}")


if __name__ == "__main__":
    main()
