"""Immune Growth — self-evolving security and risk management.

Combines:
  - Risk gate threshold adaptation (phi/ethics tiers adjust based on incidents)
  - Immune pattern evolution (new threats learned, false positives suppressed)

Usage:
    immune = ImmuneGrowth()

    # After a security incident:
    immune.record_incident('shell_execute', severity=0.8, details='unauthorized rm -rf')
    # -> phi tier for shell_execute automatically increases

    # After a false positive:
    immune.record_false_positive(pattern='rm.*-rf', input_text='explain rm -rf flags')
    # -> pattern sensitivity decreases

    # Get adjusted thresholds:
    adjusted_tier = immune.get_adjusted_tier('shell_execute')
    should_block = immune.check_pattern(input_text)
"""

from __future__ import annotations
import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Base tiers from tool_policy.py
_BASE_TIERS = {
    'default': 0.0,
    'web_search': 1.0, 'web_read': 1.0, 'file_read': 1.0, 'code_execute': 1.0,
    'hub_dispatch': 3.0, 'file_write': 3.0, 'shell_execute': 3.0, 'schedule_task': 3.0,
    'self_modify': 5.0, 'plugin_load': 5.0,
}

# Base ethics gates
_BASE_ETHICS = {
    'shell_execute': 0.3,
    'self_modify': 0.2,
    'file_write': 0.2,
    'trading_execute': 0.3,
}


class ImmuneGrowth:
    """Self-evolving immune system — learns from incidents and false positives."""

    def __init__(self, save_path: Optional[str] = None):
        self._save_path = Path(save_path) if save_path else Path(__file__).parent / 'data' / 'immune_growth_state.json'

        # Tier adjustments: tool_name -> delta (added to base tier)
        self._tier_deltas: dict[str, float] = defaultdict(float)
        # Ethics adjustments: tool_name -> delta (added to base ethics threshold)
        self._ethics_deltas: dict[str, float] = defaultdict(float)

        # Incident log (recent)
        self._incidents: list[dict] = []
        self._false_positives: list[dict] = []
        self._max_log = 200

        # Learned patterns (new threats discovered at runtime)
        self._learned_patterns: dict[str, float] = {}  # pattern -> confidence (0-1)
        # Suppressed patterns (too many false positives)
        self._suppressed_patterns: set[str] = set()

        # Decay: thresholds slowly return to baseline over time
        self._last_decay = time.time()
        self._decay_interval = 86400  # 24 hours
        self._decay_rate = 0.1  # 10% back toward baseline per interval

        self._load()

    def record_incident(self, tool_name: str, severity: float = 0.5, details: str = ''):
        """Record a security incident. Increases thresholds for the tool.

        Args:
            tool_name: Tool involved in the incident
            severity: 0.0 (minor) to 1.0 (critical)
            details: Human-readable description
        """
        severity = max(0.0, min(1.0, severity))

        # Increase phi tier for this tool
        self._tier_deltas[tool_name] += severity * 1.0  # up to +1.0 per incident
        # Increase ethics threshold
        if tool_name in _BASE_ETHICS:
            self._ethics_deltas[tool_name] += severity * 0.1  # up to +0.1 per incident

        self._incidents.append({
            'tool': tool_name,
            'severity': severity,
            'details': details,
            'time': time.time(),
        })
        if len(self._incidents) > self._max_log:
            self._incidents = self._incidents[-self._max_log:]

        logger.info("ImmuneGrowth: incident recorded for %s (severity=%.1f, tier_delta=%.2f)",
                    tool_name, severity, self._tier_deltas[tool_name])
        self._save()

    def record_false_positive(self, pattern: str = '', tool_name: str = '', input_text: str = ''):
        """Record a false positive. Reduces sensitivity."""
        if pattern:
            if pattern in self._learned_patterns:
                self._learned_patterns[pattern] *= 0.7  # reduce confidence
                if self._learned_patterns[pattern] < 0.1:
                    self._suppressed_patterns.add(pattern)
                    del self._learned_patterns[pattern]
                    logger.info("ImmuneGrowth: pattern suppressed (too many FPs): %s", pattern)

        if tool_name and self._tier_deltas.get(tool_name, 0) > 0:
            self._tier_deltas[tool_name] *= 0.8  # relax tier by 20%

        self._false_positives.append({
            'pattern': pattern,
            'tool': tool_name,
            'input': input_text[:200],
            'time': time.time(),
        })
        if len(self._false_positives) > self._max_log:
            self._false_positives = self._false_positives[-self._max_log:]

        self._save()

    def learn_threat(self, pattern: str, confidence: float = 0.5):
        """Learn a new threat pattern from runtime detection."""
        if pattern in self._suppressed_patterns:
            return  # previously suppressed, don't re-learn
        self._learned_patterns[pattern] = max(0.0, min(1.0, confidence))
        logger.info("ImmuneGrowth: new threat pattern learned: %s (conf=%.2f)", pattern, confidence)
        self._save()

    def get_adjusted_tier(self, tool_name: str) -> float:
        """Get phi tier adjusted by incident history."""
        self._maybe_decay()
        base = _BASE_TIERS.get(tool_name, _BASE_TIERS['default'])
        delta = self._tier_deltas.get(tool_name, 0.0)
        return base + delta

    def get_adjusted_ethics(self, tool_name: str) -> float:
        """Get ethics threshold adjusted by incident history."""
        self._maybe_decay()
        base = _BASE_ETHICS.get(tool_name, 0.0)
        delta = self._ethics_deltas.get(tool_name, 0.0)
        return min(1.0, base + delta)  # cap at 1.0

    def get_learned_patterns(self) -> list[tuple[str, float]]:
        """Get all learned threat patterns with confidence."""
        return [(p, c) for p, c in self._learned_patterns.items() if c > 0.1]

    def stats(self) -> dict:
        """Return summary statistics of the immune system state."""
        return {
            'incidents': len(self._incidents),
            'false_positives': len(self._false_positives),
            'learned_patterns': len(self._learned_patterns),
            'suppressed_patterns': len(self._suppressed_patterns),
            'adjusted_tools': len([d for d in self._tier_deltas.values() if abs(d) > 0.01]),
        }

    def _maybe_decay(self):
        """Slowly return thresholds to baseline (stability under calm)."""
        now = time.time()
        if now - self._last_decay < self._decay_interval:
            return
        self._last_decay = now
        for tool in list(self._tier_deltas.keys()):
            self._tier_deltas[tool] *= (1 - self._decay_rate)
            if abs(self._tier_deltas[tool]) < 0.01:
                del self._tier_deltas[tool]
        for tool in list(self._ethics_deltas.keys()):
            self._ethics_deltas[tool] *= (1 - self._decay_rate)
            if abs(self._ethics_deltas[tool]) < 0.01:
                del self._ethics_deltas[tool]

    def _save(self):
        """Persist state to disk."""
        try:
            self._save_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'tier_deltas': dict(self._tier_deltas),
                'ethics_deltas': dict(self._ethics_deltas),
                'learned_patterns': self._learned_patterns,
                'suppressed_patterns': list(self._suppressed_patterns),
                'incidents': self._incidents[-50:],
                'false_positives': self._false_positives[-50:],
                'saved_at': time.time(),
            }
            self._save_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("ImmuneGrowth save failed: %s", e)

    def _load(self):
        """Load persisted state from disk."""
        if not self._save_path.exists():
            return
        try:
            data = json.loads(self._save_path.read_text())
            self._tier_deltas.update(data.get('tier_deltas', {}))
            self._ethics_deltas.update(data.get('ethics_deltas', {}))
            self._learned_patterns.update(data.get('learned_patterns', {}))
            self._suppressed_patterns.update(data.get('suppressed_patterns', []))
            self._incidents = data.get('incidents', [])
            self._false_positives = data.get('false_positives', [])
            logger.info("ImmuneGrowth loaded: %d incidents, %d patterns",
                       len(self._incidents), len(self._learned_patterns))
        except Exception as e:
            logger.debug("ImmuneGrowth load failed: %s", e)
