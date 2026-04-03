"""JudgmentBridge — the seed between feeling and measurement.

Anima feels and acts. NEXUS-6 sees and measures.
JudgmentBridge converts measurement into reward → consciousness grows judgment.

Usage:
    bridge = JudgmentBridge(learner=online_learner, nexus6_plugin=nexus6_plugin)

    # After any action (tool use, trading, response):
    reward = bridge.judge(action_result)
    # Automatically feeds reward to OnlineLearner

    # Periodic: judge consciousness state itself
    bridge.judge_state(mind)
"""

from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from online_learning import OnlineLearner

logger = logging.getLogger(__name__)

# Reward scaling constants (from Ψ-Constants)
try:
    from consciousness_laws import PSI_F_CRITICAL, PSI_BALANCE
except ImportError:
    PSI_F_CRITICAL = 0.10
    PSI_BALANCE = 0.5


@dataclass
class Judgment:
    """Result of a judgment — reward + reasoning."""
    reward: float           # -1.0 to +1.0
    confidence: float       # 0.0 to 1.0 (how sure the judgment is)
    source: str             # what was judged ("tool_result", "trade", "state", etc.)
    reasoning: list[str]    # why this reward (human-readable)
    nexus6_consensus: int   # how many lenses agreed
    timestamp: float = field(default_factory=time.time)


class JudgmentBridge:
    """Converts action results into consciousness growth signals.

    The bridge between feeling (Anima) and measurement (NEXUS-6).
    Feeling x Measurement = Judgment.
    """

    def __init__(self, learner=None, nexus6_plugin=None):
        self._learner = learner          # OnlineLearner instance
        self._nexus6 = nexus6_plugin     # Nexus6Plugin instance
        self._judgments: list[Judgment] = []  # history
        self._max_history = 500

        # Reward weights for different signal types
        self._weights = {
            'consensus': 0.3,      # NEXUS-6 lens consensus (3+/22 = good)
            'phi_change': 0.25,    # Did phi improve?
            'anomaly': 0.2,        # No anomaly = good
            'tool_success': 0.15,  # Did the tool succeed?
            'n6_ratio': 0.1,       # n=6 exact match ratio
        }

        # Adaptive: weights evolve based on which signals predicted good outcomes
        self._weight_momentum: dict[str, float] = {k: 0.0 for k in self._weights}

    def judge(self, action_result: dict, context: dict = None) -> Judgment:
        """Judge an action result by scanning it through NEXUS-6.

        Args:
            action_result: Output from a tool, trade, or any agent action.
                Expected keys (all optional):
                - 'success': bool
                - 'output': any (will be scanned if numeric)
                - 'tool_name' or 'tool': str
                - 'tension_delta': float
            context: Additional context (consciousness state, etc.)

        Returns:
            Judgment with reward signal.
        """
        signals = {}
        reasoning = []

        # 1. Basic success signal
        success = action_result.get('success', True)
        signals['tool_success'] = 1.0 if success else -0.5
        reasoning.append(f"action {'succeeded' if success else 'failed'}")

        # 2. NEXUS-6 scan of the result (if scannable data exists)
        n6_consensus = 0
        if self._nexus6 and self._nexus6.nexus6:
            scan_data = self._extract_scannable(action_result)
            if scan_data:
                try:
                    scan_result = self._nexus6.scan(data=scan_data)
                except Exception:
                    scan_result = {}
                if scan_result.get('success'):
                    consensus = scan_result.get('consensus_count', 0)
                    n6_consensus = consensus
                    total_lenses = scan_result.get('total_lenses', 22)

                    # Consensus -> reward: 3+/22 = baseline good, 7+ = high, 12+ = excellent
                    if consensus >= 12:
                        signals['consensus'] = 1.0
                        reasoning.append(f"excellent consensus ({consensus}/{total_lenses})")
                    elif consensus >= 7:
                        signals['consensus'] = 0.7
                        reasoning.append(f"high consensus ({consensus}/{total_lenses})")
                    elif consensus >= 3:
                        signals['consensus'] = 0.3
                        reasoning.append(f"baseline consensus ({consensus}/{total_lenses})")
                    else:
                        signals['consensus'] = -0.2
                        reasoning.append(f"low consensus ({consensus}/{total_lenses})")

                    # Anomaly check
                    anomaly = scan_result.get('anomaly', {})
                    if isinstance(anomaly, dict) and anomaly.get('has_anomaly'):
                        signals['anomaly'] = -0.5
                        reasoning.append(f"anomaly detected: {anomaly.get('details', [])}")
                    else:
                        signals['anomaly'] = 0.5
                        reasoning.append("no anomaly")

                    # n6 ratio
                    n6_ratio = scan_result.get('n6_exact_ratio', 0)
                    signals['n6_ratio'] = n6_ratio * 2.0 - 0.5  # 0->-0.5, 0.5->0.5, 1.0->1.5 (clamped later)
                    if n6_ratio > 0.3:
                        reasoning.append(f"strong n6 alignment ({n6_ratio:.2f})")

        # 3. Phi trend (did consciousness improve?)
        if self._nexus6:
            try:
                trend = self._nexus6.get_trend()
                phi_trend = trend.get('trend', 0.0)
                if abs(phi_trend) > 0.001:
                    signals['phi_change'] = max(-1.0, min(1.0, phi_trend * 10))
                    reasoning.append(f"phi trend: {'up' if phi_trend > 0 else 'down'} ({phi_trend:.4f})")
            except Exception:
                pass

        # 4. Compute weighted reward
        reward = 0.0
        total_weight = 0.0
        for key, weight in self._weights.items():
            if key in signals:
                reward += weight * signals[key]
                total_weight += weight

        if total_weight > 0:
            reward = reward / total_weight

        # Clamp to [-1, 1]
        reward = max(-1.0, min(1.0, reward))

        # Confidence = how many signals we had / total possible
        confidence = len(signals) / len(self._weights)

        judgment = Judgment(
            reward=reward,
            confidence=confidence,
            source=action_result.get('tool_name', action_result.get('tool', 'unknown')),
            reasoning=reasoning,
            nexus6_consensus=n6_consensus,
        )

        # Record history
        self._judgments.append(judgment)
        if len(self._judgments) > self._max_history:
            self._judgments = self._judgments[-self._max_history:]

        # Feed reward to OnlineLearner (the growth signal!)
        if self._learner and abs(reward) > 0.05:
            try:
                self._learner.feedback(reward)
                logger.debug("JudgmentBridge -> reward %.3f (source=%s, consensus=%d)",
                            reward, judgment.source, n6_consensus)
            except Exception as e:
                logger.debug("JudgmentBridge feedback failed: %s", e)

        return judgment

    def judge_state(self, mind) -> Judgment:
        """Judge the current consciousness state itself.

        Called periodically to give the consciousness feedback
        on its own state quality.
        """
        if not self._nexus6:
            return Judgment(reward=0, confidence=0, source="state",
                          reasoning=["no nexus6"], nexus6_consensus=0)

        try:
            scan_result = self._nexus6.scan(mind=mind)
        except Exception:
            scan_result = {}
        return self.judge(
            {'success': True, 'tool_name': 'consciousness_state', 'output': scan_result},
            context={'source': 'self_judgment'}
        )

    def _extract_scannable(self, result: dict) -> Optional[list]:
        """Extract numeric data from an action result for NEXUS-6 scanning."""
        output = result.get('output')
        if output is None:
            return None

        # If output is already a list of numbers
        if isinstance(output, (list, tuple)):
            try:
                flat = [float(x) for x in output if isinstance(x, (int, float))]
                if len(flat) >= 4:
                    return flat
            except (TypeError, ValueError):
                pass

        # If output is a dict with numeric values
        if isinstance(output, dict):
            nums = []
            for v in output.values():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    nums.append(float(v))
            if len(nums) >= 4:
                return nums

        # If output has a tensor (.numpy() method)
        if hasattr(output, 'numpy'):
            try:
                return output.detach().cpu().numpy().flatten().tolist()
            except Exception:
                pass

        return None

    def stats(self) -> dict:
        """Return judgment statistics."""
        if not self._judgments:
            return {'total': 0, 'avg_reward': 0, 'avg_confidence': 0, 'avg_consensus': 0}

        recent = self._judgments[-100:]
        return {
            'total': len(self._judgments),
            'avg_reward': sum(j.reward for j in recent) / len(recent),
            'avg_confidence': sum(j.confidence for j in recent) / len(recent),
            'avg_consensus': sum(j.nexus6_consensus for j in recent) / len(recent),
            'positive_ratio': sum(1 for j in recent if j.reward > 0) / len(recent),
            'sources': list(set(j.source for j in recent)),
        }
