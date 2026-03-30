"""ConsolidationVerifier — pre_check, verify_drift, post_check with bimodal detection.

Verifies whether a memory should be consolidated into the model,
checks drift during consolidation, and assesses model health afterward.
"""

import math
import torch
from anima_alive import text_to_vector

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ─── Constants from logout project ───

KNOWN_CONSTANTS = {
    '1/e': 1.0 / math.e,       # 0.3679
    'ln(4/3)': math.log(4/3),   # 0.2877
    '1/3': 1/3,                  # 0.3333
    '1/2': 0.5,                  # 0.5000
}

CORRECT_MEAN = 201.3
WRONG_MEAN = 120.3


def predict_accuracy(tension: float) -> float:
    """Logistic model: higher tension -> higher accuracy.

    Based on logout/calc/tension_calculator.py calibration values.
    """
    overall_mean = CORRECT_MEAN * 0.975 + WRONG_MEAN * 0.025
    z = (tension - overall_mean) / 90.0
    logit = 3.5 + 0.5 * z
    logit = max(-20.0, min(20.0, logit))
    return 1.0 / (1.0 + math.exp(-logit))


def _detect_bimodal(arr: list) -> bool:
    """Histogram valley method: 2+ peaks with valley < 50% of smaller peak."""
    if len(arr) < 10:
        return False

    n_bins = max(5, len(arr) // 4)
    lo, hi = min(arr), max(arr)
    if hi - lo < 1e-9:
        return False

    bin_width = (hi - lo) / n_bins
    counts = [0] * n_bins
    for v in arr:
        idx = int((v - lo) / bin_width)
        idx = min(idx, n_bins - 1)
        counts[idx] += 1

    # Find peaks (local maxima with minimum height)
    min_count = max(1, len(arr) * 0.05)  # peak must have >= 5% of data
    peaks = []
    for i in range(len(counts)):
        left = counts[i - 1] if i > 0 else 0
        right = counts[i + 1] if i < len(counts) - 1 else 0
        if counts[i] >= left and counts[i] >= right and counts[i] >= min_count:
            peaks.append(i)

    if len(peaks) < 2:
        return False

    # Check if any pair of peaks has a valley between them < 30% of smaller peak
    # Peaks must be separated by at least 2 bins (meaningful distance)
    for pi in range(len(peaks) - 1):
        p1, p2 = peaks[pi], peaks[pi + 1]
        if p2 - p1 < 3:
            continue
        valley = min(counts[p1 + 1:p2])
        smaller_peak = min(counts[p1], counts[p2])
        if smaller_peak > 0 and valley < 0.3 * smaller_peak:
            return True

    return False


class ConsolidationVerifier:
    """Verifies memory consolidation safety and model health."""

    def __init__(self, mind, anomaly_threshold=None, drift_threshold=0.3,
                 golden_zone=(0.2123, 0.5)):
        self.mind = mind
        self.anomaly_threshold = anomaly_threshold if anomaly_threshold is not None else 2.0
        self.drift_threshold = drift_threshold
        self.golden_lower, self.golden_upper = golden_zone

    def _compute_anomaly_score(self, text_vec, hidden):
        """Compute anomaly as squared difference between engine_a and engine_g."""
        with torch.no_grad():
            combined = torch.cat([text_vec, hidden], dim=-1)
            a = self.mind.engine_a(combined)
            g = self.mind.engine_g(combined)
            return (a - g).pow(2).mean().item()

    def pre_check(self, memory: dict, hidden: torch.Tensor) -> dict:
        """Should we consolidate this memory?

        Args:
            memory: {'text': str, 'tension': float|None, 'role': str}
            hidden: (1, hidden_dim) tensor

        Returns dict with should_consolidate, anomaly_score,
        predicted_accuracy, reason.
        """
        tension = memory.get('tension')

        # No tension means LLM-API model, skip consolidation
        if tension is None:
            return {
                'should_consolidate': False,
                'anomaly_score': 0.0,
                'predicted_accuracy': 0.0,
                'reason': 'no_tension',
            }

        # Compute anomaly score
        text = memory.get('text', '')
        text_vec = text_to_vector(text, dim=self.mind.dim)
        anomaly_score = self._compute_anomaly_score(text_vec, hidden)

        if anomaly_score > self.anomaly_threshold:
            return {
                'should_consolidate': False,
                'anomaly_score': anomaly_score,
                'predicted_accuracy': predict_accuracy(tension),
                'reason': 'anomaly',
            }

        # Predict accuracy from tension
        pred_acc = predict_accuracy(tension)
        if pred_acc <= 0.5:
            return {
                'should_consolidate': False,
                'anomaly_score': anomaly_score,
                'predicted_accuracy': pred_acc,
                'reason': 'low_accuracy',
            }

        return {
            'should_consolidate': True,
            'anomaly_score': anomaly_score,
            'predicted_accuracy': pred_acc,
            'reason': 'ok',
        }

    def verify_drift(self, t_before: float, t_after: float) -> dict:
        """Check tension drift during consolidation."""
        drift = abs(t_after - t_before)
        # H404: tension_scale removed; report N/A for legacy fields
        ts_value = getattr(self.mind, 'tension_scale', None)
        ts_val = ts_value.item() if ts_value is not None else 0.0
        return {
            'drift': drift,
            'significant': drift > self.drift_threshold * 0.5,
            'suspect': drift > self.drift_threshold,
            'ts_value': ts_val,
            'ts_in_golden_zone': self.golden_lower <= ts_val <= self.golden_upper if ts_val > 0 else False,
        }

    def post_check(self, recent_tensions: list) -> dict:
        """Assess model health after consolidation."""
        # H404: tension_scale removed; use 0.0 as fallback
        ts_param = getattr(self.mind, 'tension_scale', None)
        ts_value = ts_param.item() if ts_param is not None else 0.0

        # Check constant relations (within 5%)
        new_constant_relations = {}
        for name, val in KNOWN_CONSTANTS.items():
            if val > 0 and abs(ts_value - val) / val < 0.05:
                new_constant_relations[name] = val

        # Too few tensions to assess
        if len(recent_tensions) < 5:
            return {
                'health': 'healthy',
                'tension_bimodal': False,
                'new_constant_relations': new_constant_relations,
            }

        # Bimodal detection (H-CX-70 Loop 2 warning)
        bimodal = _detect_bimodal(recent_tensions)

        if bimodal:
            return {
                'health': 'suspect',
                'tension_bimodal': True,
                'new_constant_relations': new_constant_relations,
            }

        # CV check
        mean_t = sum(recent_tensions) / len(recent_tensions)
        if mean_t > 1e-9:
            var_t = sum((x - mean_t) ** 2 for x in recent_tensions) / len(recent_tensions)
            cv = math.sqrt(var_t) / mean_t
        else:
            cv = 0.0

        if cv > 1.0:
            return {
                'health': 'degraded',
                'tension_bimodal': False,
                'new_constant_relations': new_constant_relations,
            }

        return {
            'health': 'healthy',
            'tension_bimodal': False,
            'new_constant_relations': new_constant_relations,
        }
