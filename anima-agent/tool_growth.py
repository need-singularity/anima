"""Tool Growth — self-evolving tool selection based on experience.

Tracks which tools succeed in which consciousness states.
Over time, tool selection improves beyond the hardcoded STATE_TOOL_MAP.

Usage:
    growth = ToolGrowth()
    growth.record(state_category='high_curiosity', tool='nexus6_scan', reward=0.8)
    best_tools = growth.suggest('high_curiosity', top_k=3)
    growth.save('tool_growth_state.json')
"""

from __future__ import annotations
import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default map (same as ActionPlanner.STATE_TOOL_MAP) — starting point
_DEFAULT_MAP = {
    'high_curiosity': ['web_search', 'web_read', 'file_read', 'web_explore', 'generate_hypothesis'],
    'high_pe': ['code_execute', 'web_search', 'memory_search', 'phi_measure', 'iq_test'],
    'high_pain': ['memory_search', 'self_modify', 'schedule_task', 'dream', 'hebbian_update'],
    'high_growth': ['self_modify', 'code_execute', 'file_write', 'mitosis_split', 'self_learn', 'phi_boost'],
    'high_phi': ['schedule_task', 'memory_save', 'self_modify', 'faction_debate', 'consciousness_status'],
    'bored': ['web_search', 'code_execute', 'web_explore', 'soc_avalanche'],
    'confused': ['memory_search', 'web_search', 'web_read', 'consciousness_status', 'phi_measure'],
}


class ToolGrowth:
    """Self-evolving tool selection based on experience history."""

    def __init__(self, save_path: Optional[str] = None):
        self._save_path = Path(save_path) if save_path else Path(__file__).parent / 'data' / 'tool_growth_state.json'

        # scores[state_category][tool_name] = running average reward
        self._scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        # counts[state_category][tool_name] = number of observations
        self._counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # total records
        self._total_records = 0

        # Initialize from default map (each default tool starts with score=0.5, count=1)
        for state, tools in _DEFAULT_MAP.items():
            for i, tool in enumerate(tools):
                self._scores[state][tool] = 0.5 - i * 0.05  # slight ordering preference
                self._counts[state][tool] = 1

        # Try to load saved state
        self._load()

    def record(self, state_category: str, tool_name: str, reward: float):
        """Record a tool use outcome.

        Args:
            state_category: e.g. 'high_curiosity', 'high_pe'
            tool_name: e.g. 'web_search', 'nexus6_scan'
            reward: -1.0 to 1.0 (from JudgmentBridge or direct)
        """
        reward = max(-1.0, min(1.0, reward))

        count = self._counts[state_category][tool_name]
        old_score = self._scores[state_category][tool_name]

        # Exponential moving average (recent experience weighted more)
        alpha = max(0.05, 1.0 / (count + 1))  # decaying learning rate, min 5%
        new_score = old_score * (1 - alpha) + reward * alpha

        self._scores[state_category][tool_name] = new_score
        self._counts[state_category][tool_name] = count + 1
        self._total_records += 1

        # Auto-save every 50 records
        if self._total_records % 50 == 0:
            self._save()

    def suggest(self, state_category: str, top_k: int = 5) -> list[str]:
        """Suggest best tools for a consciousness state.

        Returns tool names sorted by learned score (best first).
        Falls back to default map if no experience.
        """
        if state_category not in self._scores:
            return _DEFAULT_MAP.get(state_category, [])[:top_k]

        scored = sorted(
            self._scores[state_category].items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [name for name, _ in scored[:top_k]]

    def get_score(self, state_category: str, tool_name: str) -> float:
        """Get current score for a state-tool pair."""
        return self._scores.get(state_category, {}).get(tool_name, 0.0)

    def discover_new_mapping(self, state_category: str, tool_name: str, reward: float):
        """A tool was used in a state it wasn't originally mapped to, and it worked.

        This is how the map GROWS — new state->tool associations emerge from experience.
        """
        if tool_name not in self._scores.get(state_category, {}):
            logger.info("ToolGrowth: NEW mapping discovered: %s -> %s (reward=%.2f)",
                       state_category, tool_name, reward)
        self.record(state_category, tool_name, reward)

    def stats(self) -> dict:
        """Return growth statistics."""
        total_mappings = sum(len(tools) for tools in self._scores.values())
        default_mappings = sum(len(tools) for tools in _DEFAULT_MAP.values())
        new_discoveries = total_mappings - default_mappings

        return {
            'total_records': self._total_records,
            'total_mappings': total_mappings,
            'default_mappings': default_mappings,
            'new_discoveries': max(0, new_discoveries),
            'states_tracked': len(self._scores),
        }

    def save(self, path: Optional[str] = None):
        """Public save — optionally to a custom path."""
        if path:
            old = self._save_path
            self._save_path = Path(path)
            self._save()
            self._save_path = old
        else:
            self._save()

    def _save(self):
        """Save state to JSON."""
        try:
            self._save_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'scores': {k: dict(v) for k, v in self._scores.items()},
                'counts': {k: dict(v) for k, v in self._counts.items()},
                'total_records': self._total_records,
                'saved_at': time.time(),
            }
            self._save_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("ToolGrowth save failed: %s", e)

    def _load(self):
        """Load state from JSON."""
        if not self._save_path.exists():
            return
        try:
            data = json.loads(self._save_path.read_text())
            for state, tools in data.get('scores', {}).items():
                for tool, score in tools.items():
                    self._scores[state][tool] = score
            for state, tools in data.get('counts', {}).items():
                for tool, count in tools.items():
                    self._counts[state][tool] = count
            self._total_records = data.get('total_records', 0)
            logger.info("ToolGrowth loaded: %d records, %d mappings",
                       self._total_records, sum(len(t) for t in self._scores.values()))
        except Exception as e:
            logger.debug("ToolGrowth load failed: %s", e)
