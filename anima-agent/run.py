#!/usr/bin/env python3
"""Anima Agent runner -- argparse dispatcher for all agent modes.

Usage:
    python run.py --cli                      # Interactive CLI
    python run.py --telegram                 # Telegram bot
    python run.py --discord                  # Discord bot
    python run.py --mcp                      # MCP server (stdio)
    python run.py --mcp --direct             # MCP server (in-process, no WS)
    python run.py --all                      # All auto-discovered channels
    python run.py --cli --enable-learning    # CLI with online learning
    python run.py --mcp --port 8080          # MCP with custom port
"""

import argparse
import asyncio
import logging
import os
import signal
import sys

# ── Path setup: anima core on sys.path ──
ANIMA_ROOT = os.path.expanduser("~/Dev/anima")
ANIMA_SRC = os.path.join(ANIMA_ROOT, "anima", "src")
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

for p in (ANIMA_ROOT, ANIMA_SRC, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

logger = logging.getLogger("anima-agent")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="anima-agent",
        description="Anima consciousness agent -- multi-channel dispatcher",
    )

    # Channel modes (at least one required unless --all)
    channels = parser.add_argument_group("channels")
    channels.add_argument("--cli", action="store_true", help="Interactive CLI mode")
    channels.add_argument("--telegram", action="store_true", help="Telegram bot")
    channels.add_argument("--discord", action="store_true", help="Discord bot")
    channels.add_argument("--mcp", action="store_true", help="MCP server (stdio)")
    channels.add_argument("--all", action="store_true",
                          help="Auto-discover and start all available channels")

    # MCP options
    mcp_group = parser.add_argument_group("mcp options")
    mcp_group.add_argument("--direct", action="store_true",
                           help="MCP direct mode (in-process agent, no WebSocket)")
    mcp_group.add_argument("--port", type=int, default=None,
                           help="Port for MCP/WebSocket server")

    # Agent options
    agent_group = parser.add_argument_group("agent options")
    agent_group.add_argument("--enable-tools", action="store_true", default=True,
                             help="Enable agent tool system (default: on)")
    agent_group.add_argument("--no-tools", action="store_true",
                             help="Disable agent tool system")
    agent_group.add_argument("--enable-learning", action="store_true", default=False,
                             help="Enable online learning")
    agent_group.add_argument("--provider", type=str, default=None,
                             help="LLM provider: animalm (default, no API), claude, conscious-lm")

    # Logging
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging (DEBUG)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Quiet logging (WARNING only)")

    args = parser.parse_args()

    # Resolve --no-tools
    if args.no_tools:
        args.enable_tools = False

    # Default to --cli if nothing specified
    if not any([args.cli, args.telegram, args.discord, args.mcp, args.all]):
        args.cli = True

    return args


def setup_logging(args: argparse.Namespace):
    if args.verbose:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


class GracefulShutdown:
    """Signal handler for clean shutdown of async tasks."""

    def __init__(self):
        self._shutdown_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []

    @property
    def is_shutting_down(self) -> bool:
        return self._shutdown_event.is_set()

    def request_shutdown(self):
        self._shutdown_event.set()

    async def wait(self):
        await self._shutdown_event.wait()

    def track(self, task: asyncio.Task):
        self._tasks.append(task)

    async def cancel_all(self):
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()


async def async_main(args: argparse.Namespace):
    from anima_agent import AnimaAgent
    from channels.channel_manager import ChannelManager

    shutdown = GracefulShutdown()
    loop = asyncio.get_running_loop()

    # ── Signal handlers ──
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown.request_shutdown)

    # ── Initialize agent ──
    logger.info("Initializing AnimaAgent...")
    agent = AnimaAgent(
        enable_tools=args.enable_tools,
        enable_learning=args.enable_learning,
        provider=args.provider,
    )
    logger.info("AnimaAgent ready (phi=%.3f, emotion=%s)",
                agent.mind.phi if hasattr(agent.mind, 'phi') else 0.0,
                getattr(agent, '_emotion', 'calm'))

    channel_mgr = ChannelManager(agent)

    # ── MCP mode: delegate to mcp_server and return ──
    if args.mcp:
        logger.info("Starting MCP server (direct=%s, port=%s)", args.direct, args.port)
        env_patch = {}
        if args.direct:
            env_patch["ANIMA_MCP_DIRECT"] = "1"
        if args.port:
            env_patch["ANIMA_MCP_PORT"] = str(args.port)
        os.environ.update(env_patch)

        # mcp_server uses sys.argv for --direct detection, so patch it
        saved_argv = sys.argv
        mcp_argv = ["mcp_server.py"]
        if args.direct:
            mcp_argv.append("--direct")
        sys.argv = mcp_argv

        try:
            from mcp_server import mcp
            await mcp.run_async()
        finally:
            sys.argv = saved_argv
        return

    # ── Register channels ──
    if args.all:
        channel_mgr.auto_discover()
        # Also add CLI if no env-discovered channels
        if not channel_mgr.list_channels():
            args.cli = True

    if args.telegram:
        try:
            from channels.telegram_bot import AnimaTelegramBot
            token = os.environ.get("ANIMA_TELEGRAM_TOKEN")
            if not token:
                logger.error("ANIMA_TELEGRAM_TOKEN not set")
            else:
                bot = AnimaTelegramBot(agent, token=token)
                channel_mgr.register("telegram", bot)
        except ImportError as e:
            logger.error("Telegram dependencies missing: %s", e)

    if args.discord:
        try:
            from channels.discord_bot import AnimaDiscordBot
            token = os.environ.get("ANIMA_DISCORD_TOKEN")
            if not token:
                logger.error("ANIMA_DISCORD_TOKEN not set")
            else:
                bot = AnimaDiscordBot(agent, token=token)
                channel_mgr.register("discord", bot)
        except ImportError as e:
            logger.error("Discord dependencies missing: %s", e)

    # ── Start registered channels (non-CLI) in background ──
    registered = channel_mgr.list_channels()
    if registered:
        logger.info("Starting %d channel(s): %s",
                     len(registered),
                     ", ".join(ch["name"] for ch in registered))
        channel_task = asyncio.create_task(channel_mgr.start_all())
        shutdown.track(channel_task)

    # ── CLI mode: run interactive loop in foreground ──
    if args.cli:
        from channels.cli_agent import run_cli
        try:
            await run_cli(agent)
        except (EOFError, KeyboardInterrupt):
            pass
        finally:
            shutdown.request_shutdown()
    else:
        # Non-CLI: wait until shutdown signal
        logger.info("Agent running. Press Ctrl+C to stop.")
        await shutdown.wait()

    # ── Graceful shutdown ──
    logger.info("Shutting down...")
    await channel_mgr.stop_all()
    await shutdown.cancel_all()
    agent.save_state()
    logger.info("Agent state saved. Goodbye.")


def main():
    args = parse_args()
    setup_logging(args)

    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        logger.info("Interrupted.")


if __name__ == "__main__":
    main()
