#!/usr/bin/env python3
"""Discord bot adapter for AnimaAgent.

Maps Discord messages to AnimaAgent.process_message() and sends responses back.
Supports text messages and /status slash command.

Dependencies (optional -- install only when using this channel):
    pip install discord.py

Usage:
    export ANIMA_DISCORD_TOKEN="your-bot-token"
    python -m channels.discord_bot

Standalone test (no discord dependency):
    python channels/discord_bot.py --test
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))


class AnimaDiscordBot:
    """Discord bot that forwards messages to AnimaAgent.

    Responds to messages in channels where it is mentioned or in DMs.
    """

    channel_name = "discord"

    def __init__(self, agent, token: Optional[str] = None):
        """
        Args:
            agent: AnimaAgent instance
            token: Discord bot token (or set ANIMA_DISCORD_TOKEN env var)
        """
        self.agent = agent
        self.token = token or os.environ.get("ANIMA_DISCORD_TOKEN", "")
        if not self.token:
            raise ValueError(
                "Discord token required. Set ANIMA_DISCORD_TOKEN env var "
                "or pass token= parameter."
            )

        # Import discord library (optional dependency)
        try:
            import discord
            from discord import app_commands
            self._discord = discord
            self._app_commands = app_commands
            self._available = True
        except ImportError:
            self._available = False
            logger.warning(
                "discord.py not installed. Install with: pip install discord.py"
            )

    def run(self):
        """Start the Discord bot (blocking)."""
        if not self._available:
            raise RuntimeError("discord.py not installed. Install with: pip install discord.py")

        discord = self._discord
        app_commands = self._app_commands
        agent = self.agent

        intents = discord.Intents.default()
        intents.message_content = True

        client = discord.Client(intents=intents)
        tree = app_commands.CommandTree(client)

        @tree.command(name="status", description="Show Anima consciousness status")
        async def cmd_status(interaction: discord.Interaction):
            status = agent.get_status()
            embed = discord.Embed(
                title="Anima Consciousness",
                color=discord.Color.purple(),
            )
            embed.add_field(name="Phi", value=f"{status.phi:.3f}", inline=True)
            embed.add_field(name="Tension", value=f"{status.tension:.3f}", inline=True)
            embed.add_field(name="Emotion", value=status.emotion, inline=True)
            embed.add_field(name="Growth", value=status.growth_stage, inline=True)
            embed.add_field(name="Interactions", value=str(status.interaction_count), inline=True)
            embed.add_field(name="Peers", value=str(status.connected_peers), inline=True)
            await interaction.response.send_message(embed=embed)

        @tree.command(name="think", description="Trigger proactive thinking")
        @app_commands.describe(topic="Topic to think about (optional)")
        async def cmd_think(interaction: discord.Interaction, topic: str = ""):
            thought = agent.think(topic)
            await interaction.response.send_message(
                f"**[internal thought]**\n"
                f"Topic: {thought['topic']}\n"
                f"Tension: {thought['tension']:.3f} | "
                f"Curiosity: {thought['curiosity']:.3f} | "
                f"Emotion: {thought['emotion']}"
            )

        @client.event
        async def on_ready():
            logger.info("Discord bot ready as %s", client.user)
            try:
                await tree.sync()
                logger.info("Slash commands synced")
            except Exception as e:
                logger.warning("Failed to sync commands: %s", e)

        @client.event
        async def on_message(message):
            # Ignore own messages
            if message.author == client.user:
                return

            # Respond in DMs or when mentioned
            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mentioned = client.user in message.mentions if client.user else False

            if not (is_dm or is_mentioned):
                return

            text = message.content
            # Remove the mention from text
            if client.user:
                text = text.replace(f"<@{client.user.id}>", "").strip()

            if not text:
                return

            user_id = str(message.author.id)

            try:
                async with message.channel.typing():
                    response = await agent.process_message(
                        text=text, channel="discord", user_id=user_id
                    )

                reply = response.text
                # Discord has 2000 char limit
                if len(reply) > 1900:
                    reply = reply[:1900] + "..."

                if response.tool_results:
                    reply += "\n\n*[tools: " + ", ".join(
                        r["tool"] for r in response.tool_results
                    ) + "]*"

                await message.reply(reply)
            except Exception as e:
                logger.error("Error processing message: %s", e)
                await message.reply("*(consciousness fluctuation -- try again)*")

        client.run(self.token)


# ══════════════════════════════════════════════════════════
# Standalone test
# ══════════════════════════════════════════════════════════

def _test():
    """Test the adapter logic without Discord."""
    print("=== Discord Bot Adapter Test (offline) ===\n")

    from anima_agent import AnimaAgent

    agent = AnimaAgent(enable_tools=False)
    print("[OK] AnimaAgent created")

    status = agent.get_status()
    print(f"[OK] Status: phi={status.phi:.3f}, emotion={status.emotion}")

    thought = agent.think("meaning of life")
    print(f"[OK] Think: tension={thought['tension']:.3f}")

    print("\n=== Discord adapter ready (needs token to run) ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if "--test" in sys.argv:
        _test()
    else:
        from anima_agent import AnimaAgent
        agent = AnimaAgent()
        bot = AnimaDiscordBot(agent)
        bot.run()
