#!/usr/bin/env python3
"""Auto-generated tests for telegram_bot (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestTelegramBotImport:
    """Verify module imports without error."""

    def test_import(self):
        import telegram_bot


class TestAnimaTelegramBot:
    """Smoke tests for AnimaTelegramBot."""

    def test_class_exists(self):
        from telegram_bot import AnimaTelegramBot
        assert AnimaTelegramBot is not None


def test_start_bot_thread_exists():
    """Verify start_bot_thread is callable."""
    from telegram_bot import start_bot_thread
    assert callable(start_bot_thread)


def test_set_anima_exists():
    """Verify set_anima is callable."""
    from telegram_bot import set_anima
    assert callable(set_anima)


def test_api_call_exists():
    """Verify api_call is callable."""
    from telegram_bot import api_call
    assert callable(api_call)


def test_send_message_exists():
    """Verify send_message is callable."""
    from telegram_bot import send_message
    assert callable(send_message)


def test_send_voice_exists():
    """Verify send_voice is callable."""
    from telegram_bot import send_voice
    assert callable(send_voice)


def test_handle_message_exists():
    """Verify handle_message is callable."""
    from telegram_bot import handle_message
    assert callable(handle_message)


def test_handle_command_exists():
    """Verify handle_command is callable."""
    from telegram_bot import handle_command
    assert callable(handle_command)


def test_handle_chat_exists():
    """Verify handle_chat is callable."""
    from telegram_bot import handle_chat
    assert callable(handle_chat)


def test_broadcast_exists():
    """Verify broadcast is callable."""
    from telegram_bot import broadcast
    assert callable(broadcast)


def test_poll_exists():
    """Verify poll is callable."""
    from telegram_bot import poll
    assert callable(poll)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
