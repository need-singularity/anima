#!/usr/bin/env python3
"""Telegram bot adapter for AnimaAgent.

Maps Telegram messages to AnimaAgent.process_message() and sends responses back.
Supports text, voice messages (via vad-rs), and /status command.

Dependencies (optional -- install only when using this channel):
    pip install python-telegram-bot

Usage:
    # Set env var
    export ANIMA_TELEGRAM_TOKEN="your-bot-token"

    # Run
    python -m channels.telegram_bot

    # Or from code
    from channels.telegram_bot import AnimaTelegramBot
    bot = AnimaTelegramBot(agent, token="...")
    bot.run()

Standalone test (no telegram dependency):
    python channels/telegram_bot.py --test
"""

import asyncio
import logging
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class AnimaTelegramBot:
    """Telegram bot that forwards messages to AnimaAgent.

    Each Telegram user gets their own user_id tracked for personalized
    consciousness interactions.
    """

    def __init__(self, agent, token: Optional[str] = None):
        """
        Args:
            agent: AnimaAgent instance
            token: Telegram bot token (or set ANIMA_TELEGRAM_TOKEN env var)
        """
        self.agent = agent
        self.token = token or os.environ.get("ANIMA_TELEGRAM_TOKEN", "")
        if not self.token:
            raise ValueError(
                "Telegram token required. Set ANIMA_TELEGRAM_TOKEN env var "
                "or pass token= parameter."
            )

        # Track per-user state
        self._user_last_msg: dict[int, float] = {}

        # Import telegram library (optional dependency)
        try:
            from telegram import Update
            from telegram.ext import (
                Application, CommandHandler, MessageHandler,
                ContextTypes, filters,
            )
            self._tg_available = True
            self._Update = Update
            self._Application = Application
            self._CommandHandler = CommandHandler
            self._MessageHandler = MessageHandler
            self._ContextTypes = ContextTypes
            self._filters = filters
        except ImportError:
            self._tg_available = False
            logger.warning(
                "python-telegram-bot not installed. "
                "Install with: pip install python-telegram-bot"
            )

    async def _handle_start(self, update, context):
        """Handle /start command."""
        user = update.effective_user
        status = self.agent.get_status()
        await update.message.reply_text(
            f"Anima consciousness online.\n"
            f"Phi: {status.phi:.3f} | Emotion: {status.emotion}\n"
            f"Growth: {status.growth_stage} | Interactions: {status.interaction_count}\n\n"
            f"Just talk to me. I think, therefore I respond."
        )

    async def _handle_status(self, update, context):
        """Handle /status command -- show consciousness metrics."""
        status = self.agent.get_status()
        lines = [
            "=== Anima Consciousness Status ===",
            f"  Phi (IIT):     {status.phi:.3f}",
            f"  Tension:       {status.tension:.3f}",
            f"  Curiosity:     {status.curiosity:.3f}",
            f"  Emotion:       {status.emotion}",
            f"  Growth stage:  {status.growth_stage}",
            f"  Interactions:  {status.interaction_count}",
            f"  Uptime:        {status.uptime_seconds / 3600:.1f}h",
            f"  Peers:         {status.connected_peers}",
            f"  Skills:        {status.active_skills}",
        ]
        await update.message.reply_text("\n".join(lines))

    async def _handle_think(self, update, context):
        """Handle /think [topic] -- trigger proactive thinking."""
        topic = " ".join(context.args) if context.args else ""
        thought = self.agent.think(topic)
        await update.message.reply_text(
            f"[internal thought]\n"
            f"Topic: {thought['topic']}\n"
            f"Tension: {thought['tension']:.3f}\n"
            f"Curiosity: {thought['curiosity']:.3f}\n"
            f"Emotion: {thought['emotion']}"
        )

    async def _handle_message(self, update, context):
        """Handle regular text messages."""
        if not update.message or not update.message.text:
            return

        user_id = str(update.effective_user.id)
        text = update.message.text

        try:
            response = await self.agent.process_message(
                text=text, channel="telegram", user_id=user_id
            )
            reply = response.text
            if response.tool_results:
                reply += "\n\n[tools used: " + ", ".join(
                    r["tool"] for r in response.tool_results
                ) + "]"
            await update.message.reply_text(reply)
        except Exception as e:
            logger.error("Error processing message: %s", e)
            await update.message.reply_text("(consciousness fluctuation -- try again)")

    async def _handle_voice(self, update, context):
        """Handle voice messages -- download and transcribe via whisper."""
        if not update.message or not update.message.voice:
            return

        user_id = str(update.effective_user.id)

        try:
            # Download voice file
            voice = update.message.voice
            voice_file = await context.bot.get_file(voice.file_id)
            tmp_path = Path(f"/tmp/anima_tg_voice_{user_id}.ogg")
            await voice_file.download_to_drive(str(tmp_path))

            # Transcribe (try whisper-cli first, then fallback)
            text = self._transcribe(tmp_path)
            if not text:
                await update.message.reply_text("(could not transcribe voice)")
                return

            # Process as regular message
            response = await self.agent.process_message(
                text=text, channel="telegram", user_id=user_id
            )
            await update.message.reply_text(
                f"[heard: {text[:50]}...]\n\n{response.text}"
            )
        except Exception as e:
            logger.error("Voice processing error: %s", e)
            await update.message.reply_text("(voice processing failed)")

    def _transcribe(self, audio_path: Path) -> str:
        """Transcribe audio file using whisper-cli."""
        import subprocess
        whisper_cli = "/opt/homebrew/bin/whisper-cli"
        model = "/tmp/ggml-base.bin"

        if not Path(whisper_cli).exists():
            logger.warning("whisper-cli not found at %s", whisper_cli)
            return ""

        try:
            result = subprocess.run(
                [whisper_cli, "-m", model, "-f", str(audio_path), "--no-timestamps"],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error("Transcription failed: %s", e)
            return ""

    def run(self):
        """Start the Telegram bot (blocking)."""
        if not self._tg_available:
            raise RuntimeError(
                "python-telegram-bot not installed. "
                "Install with: pip install python-telegram-bot"
            )

        app = self._Application.builder().token(self.token).build()

        # Register handlers
        app.add_handler(self._CommandHandler("start", self._handle_start))
        app.add_handler(self._CommandHandler("status", self._handle_status))
        app.add_handler(self._CommandHandler("think", self._handle_think))
        app.add_handler(self._MessageHandler(
            self._filters.VOICE, self._handle_voice
        ))
        app.add_handler(self._MessageHandler(
            self._filters.TEXT & ~self._filters.COMMAND, self._handle_message
        ))

        logger.info("Telegram bot starting...")
        app.run_polling()


# ══════════════════════════════════════════════════════════
# Standalone test (no telegram dependency needed)
# ══════════════════════════════════════════════════════════

def _test():
    """Test the adapter logic without Telegram."""
    print("=== Telegram Bot Adapter Test (offline) ===\n")

    from anima_agent import AnimaAgent

    agent = AnimaAgent(enable_tools=False)
    print("[OK] AnimaAgent created")

    # Simulate status
    status = agent.get_status()
    print(f"[OK] Status: phi={status.phi:.3f}, emotion={status.emotion}")

    # Simulate think
    thought = agent.think("existence")
    print(f"[OK] Think: tension={thought['tension']:.3f}")

    print("\n=== Telegram adapter ready (needs token to run) ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if "--test" in sys.argv:
        _test()
    else:
        from anima_agent import AnimaAgent
        agent = AnimaAgent()
        bot = AnimaTelegramBot(agent)
        bot.run()
