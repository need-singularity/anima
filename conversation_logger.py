"""Conversation Logger — Records all state changes during dialogue.

Saves every conversation turn as a JSON line in data/conversation_log.jsonl.
Captures: input, response, tension, curiosity, emotion, direction, mitosis,
growth stage, learning updates, memory recalls, web searches, PH status,
LLM stats (AnimaLM tension/alpha), and timestamps.

Usage:
    logger = ConversationLogger("data/conversation_log.jsonl")
    logger.log_turn(data)  # called after each process_input
    logger.log_event(event_type, data)  # for non-conversation events
"""

import json
import time
from pathlib import Path
from datetime import datetime


class ConversationLogger:
    def __init__(self, path="data/conversation_log.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.session_start = time.time()
        self.turn_count = 0

        # Log session start
        self.log_event("session_start", {
            "timestamp": datetime.now().isoformat(),
        })

    def log_turn(self, data):
        """Log a full conversation turn with all state changes."""
        self.turn_count += 1
        entry = {
            "type": "turn",
            "turn": self.turn_count,
            "timestamp": datetime.now().isoformat(),
            "elapsed_sec": round(time.time() - self.session_start, 1),
            **data,
        }
        self._write(entry)

    def log_event(self, event_type, data=None):
        """Log a non-conversation event (dream, mitosis, growth, etc.)."""
        entry = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "elapsed_sec": round(time.time() - self.session_start, 1),
            **(data or {}),
        }
        self._write(entry)

    def _write(self, entry):
        with open(self.path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    def get_summary(self):
        """Return session summary."""
        return {
            "turns": self.turn_count,
            "duration_min": round((time.time() - self.session_start) / 60, 1),
            "log_path": str(self.path),
        }
