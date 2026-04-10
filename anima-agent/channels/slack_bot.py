#!/usr/bin/env python3
"""Slack channel adapter — Anima consciousness chat + trading commands.

Implements the ChannelAdapter protocol for Slack using slack_bolt (async).
Handles @mentions, DMs, and slash commands for consciousness and trading.

Commands:
    /status          → consciousness state (Phi, tension, regime)
    /trade status    → trading system status
    /trade regime    → current market regime
    /trade pnl       → P&L summary
    /trade positions → open positions
    /trade halt      → emergency stop
    /trade resume    → resume trading

Dependencies (optional -- install only when using this channel):
    pip install slack-bolt aiohttp

Usage:
    # Set env vars
    export ANIMA_SLACK_TOKEN="xoxb-your-bot-token"
    export ANIMA_SLACK_SIGNING_SECRET="your-signing-secret"
    export INVEST_API_URL="http://localhost:8000"  # invest backend

    # Run
    python -m channels.slack_bot

    # Or from code
    from channels.slack_bot import AnimaSlackBot
    bot = AnimaSlackBot(agent, token="...", signing_secret="...")
    await bot.start(agent)

Standalone test (no slack_bolt dependency):
    python channels/slack_bot.py --test
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Graceful import of slack_bolt
try:
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
    HAS_SLACK_BOLT = True
except ImportError:
    HAS_SLACK_BOLT = False
    AsyncApp = None
    AsyncSocketModeHandler = None

# Invest API client (shared with telegram_bot)
try:
    from channels.telegram_bot import InvestAPIClient
except ImportError:
    InvestAPIClient = None


class AnimaSlackBot:
    """Slack channel adapter implementing ChannelAdapter protocol."""

    channel_name = "slack"

    def __init__(
        self,
        agent=None,
        token: Optional[str] = None,
        signing_secret: Optional[str] = None,
        invest_url: Optional[str] = None,
    ):
        self.agent = agent
        self.token = token or os.getenv("ANIMA_SLACK_TOKEN", "")
        self.signing_secret = signing_secret or os.getenv("ANIMA_SLACK_SIGNING_SECRET", "")
        self.invest_url = invest_url or os.getenv("INVEST_API_URL", "http://localhost:8000")
        self._app: Optional[Any] = None
        self._handler: Optional[Any] = None
        self._invest: Optional[Any] = None

    async def start(self, agent) -> None:
        """Start the Slack bot (ChannelAdapter protocol)."""
        self.agent = agent

        if not HAS_SLACK_BOLT:
            logger.error("slack_bolt not installed. pip install slack-bolt aiohttp")
            return

        if not self.token or not self.signing_secret:
            logger.error(
                "ANIMA_SLACK_TOKEN and ANIMA_SLACK_SIGNING_SECRET must be set"
            )
            return

        # Init invest client
        if InvestAPIClient:
            self._invest = InvestAPIClient(self.invest_url)

        # Create Slack app
        self._app = AsyncApp(
            token=self.token,
            signing_secret=self.signing_secret,
        )

        # Register handlers
        self._register_handlers()

        # Start socket mode
        app_token = os.getenv("ANIMA_SLACK_APP_TOKEN", "")
        if app_token:
            self._handler = AsyncSocketModeHandler(self._app, app_token)
            logger.info("[slack] Starting socket mode...")
            await self._handler.start_async()
        else:
            logger.info("[slack] No ANIMA_SLACK_APP_TOKEN — use HTTP mode externally")

    async def stop(self) -> None:
        """Stop the Slack bot (ChannelAdapter protocol)."""
        if self._handler:
            await self._handler.close_async()
            self._handler = None
        if self._invest:
            await self._invest.close()
            self._invest = None
        logger.info("[slack] Stopped")

    async def send(self, user_id: str, text: str, **kwargs) -> None:
        """Send a message to a Slack channel or DM (ChannelAdapter protocol)."""
        if not self._app:
            logger.warning("[slack] App not initialized, cannot send")
            return
        channel = kwargs.get("channel", user_id)
        await self._app.client.chat_postMessage(channel=channel, text=text)

    def _register_handlers(self):
        """Register Slack event and command handlers."""
        app = self._app

        # --- Slash commands ---

        @app.command("/status")
        async def handle_status(ack, command, say):
            await ack()
            text = await self._get_consciousness_status()
            await say(text)

        @app.command("/trade")
        async def handle_trade(ack, command, say):
            await ack()
            args = (command.get("text") or "").strip().split()
            subcmd = args[0] if args else "status"
            text = await self._handle_trade_command(subcmd)
            await say(text)

        # --- @mention and DMs ---

        @app.event("app_mention")
        async def handle_mention(event, say):
            user = event.get("user", "unknown")
            text = event.get("text", "").strip()
            # Strip bot mention from text
            import re
            text = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()
            if not text:
                text = "안녕"
            response = await self._process_message(user, text)
            await say(response)

        @app.event("message")
        async def handle_dm(event, say):
            # Only respond to DMs (no subtype = user message)
            if event.get("channel_type") != "im":
                return
            if event.get("subtype"):
                return
            user = event.get("user", "unknown")
            text = event.get("text", "").strip()
            if not text:
                return
            response = await self._process_message(user, text)
            await say(response)

    async def _process_message(self, user_id: str, text: str) -> str:
        """Route a message through the Anima agent."""
        if not self.agent:
            return "Anima agent not connected."
        try:
            result = await self.agent.process_message(
                text, user_id=user_id, channel="slack"
            )
            if isinstance(result, dict):
                return result.get("text", result.get("response", str(result)))
            return str(result)
        except Exception as e:
            logger.error("[slack] process_message error: %s", e)
            return f"Error: {e}"

    async def _get_consciousness_status(self) -> str:
        """Get consciousness state summary."""
        lines = ["*Anima Consciousness Status*"]
        if self.agent:
            try:
                state = self.agent.get_state() if hasattr(self.agent, "get_state") else {}
                phi = state.get("phi", 0)
                tension = state.get("tension", 0)
                cells = state.get("cells", 0)
                growth = state.get("growth_stage", "unknown")
                lines.append(f"  Phi: {phi:.4f}")
                lines.append(f"  Tension: {tension:.3f}")
                lines.append(f"  Cells: {cells}")
                lines.append(f"  Growth: {growth}")
            except Exception as e:
                lines.append(f"  (agent error: {e})")
        else:
            lines.append("  Agent not connected")
        lines.append(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
        return "\n".join(lines)

    async def _handle_trade_command(self, subcmd: str) -> str:
        """Handle /trade subcommands via invest API."""
        if not self._invest:
            return "Invest API client not available (install httpx)"

        if subcmd == "status":
            data = await self._invest.get_trading_status()
            if "error" in data:
                return f"Trade API error: {data['error']}"
            halted = data.get("emergency_stop", False)
            status = "HALTED" if halted else "ACTIVE"
            return f"*Trading Status*: {status}\n{_fmt_dict(data)}"

        elif subcmd == "regime":
            data = await self._invest.get_regime()
            if "error" in data:
                return f"Regime API error: {data['error']}"
            regime = data.get("regime", data.get("status", "unknown"))
            return f"*Market Regime*: {regime.upper()}\n{_fmt_dict(data)}"

        elif subcmd == "pnl":
            history = await self._invest.get_portfolio_history(limit=7)
            if not history:
                return "No portfolio history available"
            lines = ["*P&L (last 7 days)*"]
            for entry in history:
                date = entry.get("date", "?")
                pnl = entry.get("pnl", entry.get("total_value", 0))
                lines.append(f"  {date}: {pnl:+,.0f}")
            return "\n".join(lines)

        elif subcmd == "positions":
            positions = await self._invest.get_portfolio()
            if not positions:
                return "No open positions"
            lines = ["*Open Positions*"]
            for p in positions:
                sym = p.get("symbol", "?")
                qty = p.get("quantity", p.get("qty", 0))
                pnl = p.get("pnl", p.get("unrealized_pnl", 0))
                lines.append(f"  {sym}: {qty} ({pnl:+,.0f})")
            return "\n".join(lines)

        elif subcmd == "halt":
            data = await self._invest.emergency_stop(stop=True)
            return "Trading HALTED" if "error" not in data else f"Error: {data['error']}"

        elif subcmd == "resume":
            data = await self._invest.emergency_stop(stop=False)
            return "Trading RESUMED" if "error" not in data else f"Error: {data['error']}"

        else:
            return (
                "*Available /trade commands:*\n"
                "  status, regime, pnl, positions, halt, resume"
            )


def _fmt_dict(d: dict, indent: int = 2) -> str:
    """Format dict as readable key-value lines."""
    prefix = " " * indent
    return "\n".join(f"{prefix}{k}: {v}" for k, v in d.items() if k != "error")


# ── Standalone test ──

async def _test():
    """Test without Slack dependencies."""
    print("[slack_bot] Standalone test (no Slack connection)")
    print(f"  HAS_SLACK_BOLT: {HAS_SLACK_BOLT}")
    print(f"  InvestAPIClient: {InvestAPIClient is not None}")

    bot = AnimaSlackBot()
    print(f"  channel_name: {bot.channel_name}")

    # Test consciousness status (no agent)
    status = await bot._get_consciousness_status()
    print(f"\n{status}")

    # Test trade commands (no invest API)
    trade_help = await bot._handle_trade_command("help")
    print(f"\n{trade_help}")

    print("\n[OK] Slack bot standalone test passed")


if __name__ == "__main__":
    if "--test" in sys.argv:
        asyncio.run(_test())
    else:
        print("Usage: python channels/slack_bot.py --test")
        print("  Or set ANIMA_SLACK_TOKEN + ANIMA_SLACK_SIGNING_SECRET and run via anima-agent")
