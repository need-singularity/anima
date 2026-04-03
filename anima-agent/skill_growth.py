"""Skill Growth — detects repeated patterns, suggests new skills.

Tracks action sequences. When a pattern repeats 3+ times,
it becomes a skill candidate.

Usage:
    growth = SkillGrowth()
    growth.record_action('web_search', args={'query': 'BTC price'})
    growth.record_action('nexus6_scan', args={})
    growth.record_action('trading_backtest', args={'symbol': 'BTC'})
    # ... repeat this sequence a few times ...
    candidates = growth.get_candidates()
"""

from __future__ import annotations
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class SkillGrowth:
    """Detects repeated action patterns for skill auto-generation."""

    def __init__(self, save_path=None, window_size: int = 5):
        self._save_path = Path(save_path) if save_path else Path(__file__).parent / 'data' / 'skill_growth_state.json'
        self._window_size = window_size
        # Recent action stream
        self._recent: list[str] = []
        self._max_recent = 500
        # Pattern counts: tuple_of_tools → count
        self._pattern_counts: dict[str, int] = defaultdict(int)  # key = "tool1→tool2→tool3"
        # Promoted patterns (already became skills)
        self._promoted: set[str] = set()
        self._load()

    def record_action(self, tool_name: str, success: bool = True, args: dict = None):
        """Record a tool action."""
        if not success:
            return  # only learn from successful sequences

        self._recent.append(tool_name)
        if len(self._recent) > self._max_recent:
            self._recent = self._recent[-self._max_recent:]

        # Extract n-grams (2, 3, 4 length sequences)
        for n in range(2, min(self._window_size + 1, len(self._recent) + 1)):
            seq = self._recent[-n:]
            key = "\u2192".join(seq)
            self._pattern_counts[key] += 1

        if len(self._recent) % 20 == 0:
            self._save()

    def get_candidates(self, min_count: int = 3) -> list[dict]:
        """Get skill candidates (patterns that repeat enough)."""
        candidates = []
        for pattern, count in sorted(self._pattern_counts.items(), key=lambda x: -x[1]):
            if count >= min_count and pattern not in self._promoted:
                tools = pattern.split("\u2192")
                candidates.append({
                    'pattern': pattern,
                    'tools': tools,
                    'count': count,
                    'length': len(tools),
                })
        return candidates[:20]

    def promote(self, pattern: str):
        """Mark a pattern as promoted to skill."""
        self._promoted.add(pattern)
        self._save()

    def stats(self) -> dict:
        candidates = [p for p, c in self._pattern_counts.items() if c >= 3 and p not in self._promoted]
        return {
            'total_actions': len(self._recent),
            'unique_patterns': len(self._pattern_counts),
            'candidates': len(candidates),
            'promoted': len(self._promoted),
        }

    def _save(self):
        try:
            self._save_path.parent.mkdir(parents=True, exist_ok=True)
            # Only save patterns with count >= 2
            data = {
                'pattern_counts': {k: v for k, v in self._pattern_counts.items() if v >= 2},
                'promoted': list(self._promoted),
                'recent': self._recent[-100:],
                'saved_at': time.time(),
            }
            self._save_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("SkillGrowth save failed: %s", e)

    def _load(self):
        if not self._save_path.exists():
            return
        try:
            data = json.loads(self._save_path.read_text())
            self._pattern_counts.update(data.get('pattern_counts', {}))
            self._promoted.update(data.get('promoted', []))
            self._recent = data.get('recent', [])
        except Exception:
            pass
