"""Emotion Growth — self-evolving emotion-to-behavior mapping.

Currently hardcoded: tension>0.8 → shorter response, curiosity>0.6 → broader search.
This module learns optimal mappings from user engagement feedback.

Usage:
    growth = EmotionGrowth()
    growth.record('high_tension', behavior='short_response', user_engaged=True)
    growth.record('high_tension', behavior='long_response', user_engaged=False)
    behavior = growth.suggest_behavior('high_tension')
"""

from __future__ import annotations
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

# Default emotion→behavior mappings
_DEFAULT_BEHAVIORS = {
    'high_tension': {'max_tokens_scale': 0.6, 'search_depth': 2, 'response_style': 'focused'},
    'high_curiosity': {'max_tokens_scale': 1.2, 'search_depth': 5, 'response_style': 'exploratory'},
    'high_pain': {'max_tokens_scale': 0.8, 'search_depth': 3, 'response_style': 'solution_seeking'},
    'calm': {'max_tokens_scale': 1.0, 'search_depth': 3, 'response_style': 'balanced'},
    'bored': {'max_tokens_scale': 1.5, 'search_depth': 5, 'response_style': 'creative'},
}


class EmotionGrowth:
    """Self-evolving emotion-to-behavior mapping."""

    def __init__(self, save_path=None):
        self._save_path = Path(save_path) if save_path else Path(__file__).parent / 'data' / 'emotion_growth_state.json'
        # scores[emotion_state][behavior_param] = value (evolved from defaults)
        self._behaviors: dict[str, dict[str, float]] = {}
        # engagement_history[emotion_state] = list of (behavior_params, engaged_bool)
        self._history: dict[str, list] = defaultdict(list)
        self._max_history = 200
        self._total = 0

        # Initialize from defaults
        for state, params in _DEFAULT_BEHAVIORS.items():
            self._behaviors[state] = dict(params)

        self._load()

    def record(self, emotion_state: str, behavior: str, user_engaged: bool,
              behavior_value: float = None):
        """Record whether a behavior was effective for an emotion state.

        Args:
            emotion_state: e.g. 'high_tension', 'calm'
            behavior: Parameter name e.g. 'max_tokens_scale', 'search_depth'
            user_engaged: Whether user responded positively
            behavior_value: The actual value used (if known)
        """
        if emotion_state not in self._behaviors:
            self._behaviors[emotion_state] = dict(_DEFAULT_BEHAVIORS.get(emotion_state, {}))

        self._history[emotion_state].append({
            'behavior': behavior,
            'value': behavior_value,
            'engaged': user_engaged,
            'time': time.time(),
        })
        if len(self._history[emotion_state]) > self._max_history:
            self._history[emotion_state] = self._history[emotion_state][-self._max_history:]

        # Adapt: if engaged, nudge toward current value; if not, nudge away
        if behavior_value is not None and behavior in self._behaviors.get(emotion_state, {}):
            current = self._behaviors[emotion_state][behavior]
            if isinstance(current, (int, float)):
                alpha = 0.1
                if user_engaged:
                    self._behaviors[emotion_state][behavior] = current * (1 - alpha) + behavior_value * alpha
                else:
                    # Move away from this value
                    delta = behavior_value - current
                    self._behaviors[emotion_state][behavior] = current - delta * alpha * 0.5

        self._total += 1
        if self._total % 20 == 0:
            self._save()

    def get_behavior(self, emotion_state: str) -> dict:
        """Get evolved behavior parameters for an emotion state."""
        return dict(self._behaviors.get(emotion_state, _DEFAULT_BEHAVIORS.get(emotion_state, {})))

    def get_max_tokens_scale(self, emotion_state: str) -> float:
        """Convenience: get max_tokens scale factor."""
        b = self.get_behavior(emotion_state)
        return b.get('max_tokens_scale', 1.0)

    def get_search_depth(self, emotion_state: str) -> int:
        """Convenience: get memory search depth."""
        b = self.get_behavior(emotion_state)
        return int(b.get('search_depth', 3))

    def stats(self) -> dict:
        return {
            'total_records': self._total,
            'states_tracked': len(self._behaviors),
            'total_history': sum(len(h) for h in self._history.values()),
        }

    def _save(self):
        try:
            self._save_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'behaviors': self._behaviors,
                'history': {k: v[-50:] for k, v in self._history.items()},
                'total': self._total, 'saved_at': time.time(),
            }
            self._save_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("EmotionGrowth save failed: %s", e)

    def _load(self):
        if not self._save_path.exists():
            return
        try:
            data = json.loads(self._save_path.read_text())
            for state, params in data.get('behaviors', {}).items():
                self._behaviors[state] = params
            for state, history in data.get('history', {}).items():
                self._history[state] = history
            self._total = data.get('total', 0)
        except Exception:
            pass
