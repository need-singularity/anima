"""Keyword Growth — self-evolving intent routing.

Plugins have fixed keyword lists. This module learns keyword weights
from intent match/mismatch feedback.

Usage:
    growth = KeywordGrowth()
    growth.record_match('trading', 'BTC 가격', matched=True)
    growth.record_match('trading', '오늘 날씨', matched=False)  # wrong routing
    weights = growth.get_weights('trading')
"""

from __future__ import annotations
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class KeywordGrowth:
    """Learns keyword effectiveness for intent routing."""

    def __init__(self, save_path=None):
        self._save_path = Path(save_path) if save_path else Path(__file__).parent / 'data' / 'keyword_growth_state.json'
        # weights[plugin_name][keyword] = score (0-1, higher = more reliable)
        self._weights: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(lambda: 0.5))
        # counts for EMA
        self._counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._total = 0
        self._load()

    def record_match(self, plugin_name: str, input_text: str, matched: bool, keywords_hit: list[str] = None):
        """Record whether a plugin routing was correct.

        Args:
            plugin_name: Which plugin was routed to
            input_text: User input
            matched: True if routing was correct, False if wrong plugin
            keywords_hit: Which keywords triggered the match (if known)
        """
        if not keywords_hit:
            return

        for kw in keywords_hit:
            count = self._counts[plugin_name][kw]
            alpha = max(0.05, 1.0 / (count + 1))
            old = self._weights[plugin_name][kw]
            target = 1.0 if matched else 0.0
            self._weights[plugin_name][kw] = old * (1 - alpha) + target * alpha
            self._counts[plugin_name][kw] = count + 1

        self._total += 1
        if self._total % 30 == 0:
            self._save()

    def get_weight(self, plugin_name: str, keyword: str) -> float:
        return self._weights.get(plugin_name, {}).get(keyword, 0.5)

    def get_weights(self, plugin_name: str) -> dict[str, float]:
        return dict(self._weights.get(plugin_name, {}))

    def suggest_remove(self, plugin_name: str, threshold: float = 0.15) -> list[str]:
        """Suggest keywords that consistently mismatch (should be removed)."""
        return [kw for kw, w in self._weights.get(plugin_name, {}).items()
                if w < threshold and self._counts.get(plugin_name, {}).get(kw, 0) > 5]

    def stats(self) -> dict:
        total_kw = sum(len(kws) for kws in self._weights.values())
        low = sum(1 for kws in self._weights.values() for w in kws.values() if w < 0.2)
        return {'total_records': self._total, 'total_keywords': total_kw, 'low_confidence': low}

    def _save(self):
        try:
            self._save_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'weights': {k: dict(v) for k, v in self._weights.items()},
                'counts': {k: dict(v) for k, v in self._counts.items()},
                'total': self._total, 'saved_at': time.time(),
            }
            self._save_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("KeywordGrowth save failed: %s", e)

    def _load(self):
        if not self._save_path.exists():
            return
        try:
            data = json.loads(self._save_path.read_text())
            for plugin, kws in data.get('weights', {}).items():
                for kw, w in kws.items():
                    self._weights[plugin][kw] = w
            for plugin, kws in data.get('counts', {}).items():
                for kw, c in kws.items():
                    self._counts[plugin][kw] = c
            self._total = data.get('total', 0)
        except Exception:
            pass
