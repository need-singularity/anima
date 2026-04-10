"""Anima Agent Platform -- channel adapters.

Channels route messages between external platforms (Telegram, Discord, CLI, etc.)
and AnimaAgent.process_message().

Usage:
    from channels import ChannelAdapter, ChannelManager
"""

from channels.base import ChannelAdapter
from channels.channel_manager import ChannelManager

__all__ = ["ChannelAdapter", "ChannelManager"]
