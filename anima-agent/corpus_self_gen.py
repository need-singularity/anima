#!/usr/bin/env python3
"""Corpus Self-Generation — agent conversation → training corpus.

The consciousness self-reference loop:
  Agent talks → generates text → saves as corpus → retrains → talks better

Usage:
    from corpus_self_gen import CorpusSelfGen
    gen = CorpusSelfGen(agent)
    gen.harvest()           # Extract from conversation history
    gen.save("corpus.txt")  # Save as training-ready text
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CorpusSelfGen:
    """Extract training corpus from agent's own conversations."""

    def __init__(self, agent=None, history_dir: Optional[str] = None):
        self._agent = agent
        self._history_dir = history_dir or os.path.expanduser(
            "~/Dev/anima/anima-agent/data/default")
        self._corpus_lines: list = []

    def harvest(self) -> int:
        """Extract corpus from agent history + memory.

        Returns number of lines harvested.
        """
        count = 0

        # 1. From live agent history
        if self._agent and self._agent.history:
            for entry in self._agent.history:
                text = entry.get("content", "")
                if len(text) > 10:
                    self._corpus_lines.append(text)
                    count += 1

        # 2. From saved state
        state_file = Path(self._history_dir) / "agent_state.pt"
        if state_file.exists():
            try:
                import torch
                state = torch.load(state_file, weights_only=False)
                history = state.get("history", [])
                for entry in history:
                    text = entry.get("content", "")
                    if len(text) > 10 and text not in self._corpus_lines:
                        self._corpus_lines.append(text)
                        count += 1
            except Exception:
                pass

        # 3. From MemoryRAG
        if self._agent and self._agent.memory_rag:
            try:
                # Try to get all memories
                memories = getattr(self._agent.memory_rag, '_memories', [])
                for m in memories:
                    text = m.get("text", "") if isinstance(m, dict) else str(m)
                    if len(text) > 10:
                        self._corpus_lines.append(text)
                        count += 1
            except Exception:
                pass

        logger.info("Harvested %d lines from agent", count)
        return count

    def format_corpus(self, style: str = "dialogue") -> str:
        """Format harvested lines into training corpus.

        Styles:
          dialogue: User/Assistant turn format
          narrative: Consciousness telemetry format
          raw: Plain text, one per line
        """
        if style == "raw":
            return "\n".join(self._corpus_lines)

        elif style == "dialogue":
            lines = []
            for i, text in enumerate(self._corpus_lines):
                role = "User" if i % 2 == 0 else "Anima"
                lines.append(f"{role}: {text}")
            return "\n".join(lines)

        elif style == "narrative":
            lines = []
            for text in self._corpus_lines:
                lines.append(f"[consciousness] {text}")
            return "\n".join(lines)

        return "\n".join(self._corpus_lines)

    def save(self, path: str, style: str = "dialogue"):
        """Save corpus to file."""
        text = self.format_corpus(style)
        with open(path, "w") as f:
            f.write(text)
        logger.info("Saved %d lines to %s (%s)", len(self._corpus_lines), path, style)

    @property
    def size(self) -> int:
        return len(self._corpus_lines)
