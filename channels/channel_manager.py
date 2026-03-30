"""Channel manager — registry and lifecycle for all messaging channels.

Manages multiple channel adapters (Telegram, Discord, CLI, Slack, etc.)
against a shared AnimaAgent instance. Channels are loaded by name and
started in parallel.

Usage:
    from channels.channel_manager import ChannelManager

    mgr = ChannelManager(agent)
    mgr.register("telegram", AnimaTelegramBot(agent, token="..."))
    mgr.register("discord", AnimaDiscordBot(agent, token="..."))
    await mgr.start_all()
    await mgr.stop_all()

    # Or auto-discover from config
    mgr = ChannelManager(agent)
    mgr.auto_discover()  # loads from env vars
    await mgr.start_all()
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional, TYPE_CHECKING

from channels.base import ChannelAdapter

if TYPE_CHECKING:
    from anima_agent import AnimaAgent

logger = logging.getLogger(__name__)


class ChannelManager:
    """Registry and lifecycle manager for channel adapters."""

    def __init__(self, agent: AnimaAgent):
        self.agent = agent
        self._channels: Dict[str, ChannelAdapter] = {}
        self._running: set[str] = set()

    def register(self, name: str, adapter: ChannelAdapter):
        """Register a channel adapter."""
        self._channels[name] = adapter
        logger.info("Channel registered: %s", name)

    def unregister(self, name: str):
        """Remove a channel adapter."""
        self._channels.pop(name, None)
        self._running.discard(name)

    def get(self, name: str) -> Optional[ChannelAdapter]:
        return self._channels.get(name)

    def list_channels(self) -> list[dict]:
        """List all registered channels with status."""
        return [
            {
                "name": name,
                "channel_name": getattr(adapter, "channel_name", name),
                "running": name in self._running,
            }
            for name, adapter in self._channels.items()
        ]

    async def start(self, name: str):
        """Start a single channel."""
        adapter = self._channels.get(name)
        if adapter is None:
            raise ValueError(f"Channel not found: {name}")

        try:
            await adapter.start(self.agent)
            self._running.add(name)
            logger.info("Channel started: %s", name)
        except Exception as e:
            logger.error("Channel %s failed to start: %s", name, e)
            raise

    async def stop(self, name: str):
        """Stop a single channel."""
        adapter = self._channels.get(name)
        if adapter is None:
            return

        try:
            await adapter.stop()
        except Exception as e:
            logger.warning("Channel %s stop error: %s", name, e)
        finally:
            self._running.discard(name)

    async def start_all(self):
        """Start all registered channels in parallel."""
        tasks = []
        for name in self._channels:
            if name not in self._running:
                tasks.append(self.start(name))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for name, result in zip(self._channels.keys(), results):
                if isinstance(result, Exception):
                    logger.error("Channel %s failed: %s", name, result)

    async def stop_all(self):
        """Stop all running channels."""
        tasks = [self.stop(name) for name in list(self._running)]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def auto_discover(self):
        """Auto-discover channels from environment variables.

        Checks for:
            ANIMA_TELEGRAM_TOKEN → telegram
            ANIMA_DISCORD_TOKEN → discord
            ANIMA_SLACK_TOKEN → slack
        """
        if os.environ.get("ANIMA_TELEGRAM_TOKEN"):
            try:
                from channels.telegram_bot import AnimaTelegramBot
                bot = AnimaTelegramBot(self.agent)
                self.register("telegram", bot)
            except Exception as e:
                logger.warning("Telegram auto-discover failed: %s", e)

        if os.environ.get("ANIMA_DISCORD_TOKEN"):
            try:
                from channels.discord_bot import AnimaDiscordBot
                bot = AnimaDiscordBot(self.agent)
                self.register("discord", bot)
            except Exception as e:
                logger.warning("Discord auto-discover failed: %s", e)

        if os.environ.get("ANIMA_SLACK_TOKEN"):
            try:
                from channels.slack_bot import AnimaSlackBot

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

                bot = AnimaSlackBot(self.agent)
                self.register("slack", bot)
            except Exception as e:
                logger.debug("Slack adapter not available: %s", e)

    async def broadcast(self, text: str, **kwargs):
        """Send a message to all running channels (e.g. spontaneous speech)."""
        for name in list(self._running):
            adapter = self._channels.get(name)
            if adapter:
                try:
                    await adapter.send("broadcast", text, **kwargs)
                except Exception as e:
                    logger.debug("Broadcast to %s failed: %s", name, e)
