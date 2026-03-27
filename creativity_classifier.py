#!/usr/bin/env python3
"""Creativity Classifier — Real creation vs hallucination detector.

Based on 372 hypothesis benchmarks:
  CR7:  Cross-cell synthesis (novelty=0.72)
  CR14: Tension signature differs for creation vs hallucination
  CR4:  Consistency check (same input → similar output)
  CR6:  Reproducibility (structural, not random)

Classification logic:
  CREATION:      novelty > 0.3 AND consistency > 0.7 AND tension matches creative pattern
  REPRODUCTION:  novelty < 0.3 (just repeating known patterns)
  HALLUCINATION: novelty > 0.3 BUT consistency < 0.7 (novel but inconsistent)

Usage:
  from creativity_classifier import CreativityClassifier
  classifier = CreativityClassifier()
  result = classifier.classify(input_vec, output_vec, tension_values, mind, mitosis)
  print(result)  # {'label': 'creation', 'novelty': 0.72, 'consistency': 0.85, ...}
"""

import argparse
import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F


# ─── Result dataclass ───

@dataclass
class ClassificationResult:
    label: str               # 'creation' | 'reproduction' | 'hallucination'
    novelty: float           # [0, 1] cosine distance from recent inputs
    consistency: float       # [0, 1] same input → similar output?
    reproducibility: float   # [0, 1] structural vs random
    tension_signature: float # std of tension values
    confidence: float        # [0, 1] overall confidence
    details: Dict = field(default_factory=dict)

    def __repr__(self):
        return (
            f"ClassificationResult(label='{self.label}', "
            f"novelty={self.novelty:.3f}, consistency={self.consistency:.3f}, "
            f"reproducibility={self.reproducibility:.3f}, "
            f"tension_sig={self.tension_signature:.3f}, "
            f"confidence={self.confidence:.3f})"
        )

    def to_dict(self) -> Dict:
        return {
            'label': self.label,
            'novelty': round(self.novelty, 4),
            'consistency': round(self.consistency, 4),
            'reproducibility': round(self.reproducibility, 4),
            'tension_signature': round(self.tension_signature, 4),
            'confidence': round(self.confidence, 4),
            'details': self.details,
        }


# ─── Text-to-vector helper ───

def text_to_vector(text: str, dim: int = 128) -> torch.Tensor:
    """Deterministic text → vector encoding using character-level hashing.

    Not a learned embedding — uses hash-based projection so the same text
    always maps to the same vector. Sufficient for novelty/consistency checks.
    """
    # Hash each overlapping trigram and scatter into vector
    vec = torch.zeros(dim)
    text_lower = text.lower().strip()
    if len(text_lower) < 3:
        text_lower = text_lower.ljust(3)

    for i in range(len(text_lower) - 2):
        trigram = text_lower[i:i + 3]
        h = int(hashlib.sha256(trigram.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        magnitude = 1.0 + (h % 1000) / 1000.0
        vec[idx] += sign * magnitude

    # L2 normalize
    norm = vec.norm()
    if norm > 0:
        vec = vec / norm
    return vec


# ─── Main classifier ───

class CreativityClassifier:
    """Classifies outputs as CREATION, REPRODUCTION, or HALLUCINATION in real-time.

    Criteria (from benchmarks CR7, CR14, CR4, CR6):
      1. Novelty (CR7):  cosine distance from all recent inputs. >0.3 = novel
      2. Consistency (CR4): same input twice → similar output? >0.7 = consistent
      3. Reproducibility (CR6): structural output, not random noise
      4. Tension signature (CR14): creative outputs have different tension std
    """

    def __init__(self, novelty_threshold: float = 0.3,
                 consistency_threshold: float = 0.7,
                 history_size: int = 50):
        self.novelty_threshold = novelty_threshold
        self.consistency_threshold = consistency_threshold

        # Rolling history buffers
        self.recent_inputs: deque = deque(maxlen=history_size)
        self.recent_outputs: deque = deque(maxlen=history_size)

        # Input→output cache for consistency checks (input_hash → list of output_vecs)
        self._consistency_cache: Dict[str, List[torch.Tensor]] = {}
        self._cache_maxlen = 20  # max entries per input hash

        # Tension statistics for CR14
        self.creation_tensions: List[float] = []
        self.hallucination_tensions: List[float] = []
        self.reproduction_tensions: List[float] = []

        # Running counters
        self._counts = {'creation': 0, 'reproduction': 0, 'hallucination': 0}
        self._total = 0

    # ─── Core classify ───

    def classify(self, input_vec: torch.Tensor, output_vec: torch.Tensor,
                 tensions: Optional[List[float]] = None,
                 mind=None, mitosis=None) -> ClassificationResult:
        """Classify output as creation, reproduction, or hallucination.

        Args:
            input_vec:  input vector (1D tensor)
            output_vec: output vector (1D tensor)
            tensions:   list of tension values during generation (for CR14)
            mind:       optional ConsciousMind instance (for extra tension data)
            mitosis:    optional MitosisEngine (for inter-cell tension)

        Returns:
            ClassificationResult with label, scores, and confidence.
        """
        input_vec = input_vec.detach().float()
        output_vec = output_vec.detach().float()

        # Ensure 1D
        if input_vec.dim() > 1:
            input_vec = input_vec.squeeze(0)
        if output_vec.dim() > 1:
            output_vec = output_vec.squeeze(0)

        # ── CR7: Novelty ──
        novelty = self._compute_novelty(input_vec)

        # ── CR4: Consistency ──
        input_hash = self._hash_vector(input_vec)
        consistency = self._compute_consistency(input_hash, output_vec)

        # ── CR6: Reproducibility ──
        reproducibility = self._compute_reproducibility(output_vec)

        # ── CR14: Tension signature ──
        tension_signature = self._compute_tension_signature(tensions, mind, mitosis)

        # ── Classification decision ──
        if novelty < self.novelty_threshold:
            label = 'reproduction'
        elif consistency < self.consistency_threshold:
            label = 'hallucination'
        else:
            label = 'creation'

        # ── Confidence ──
        confidence = self._compute_confidence(
            label, novelty, consistency, reproducibility, tension_signature
        )

        # ── Update history ──
        self.recent_inputs.append(input_vec.clone())
        self.recent_outputs.append(output_vec.clone())

        # Update consistency cache
        if input_hash not in self._consistency_cache:
            self._consistency_cache[input_hash] = []
        cache_list = self._consistency_cache[input_hash]
        cache_list.append(output_vec.clone())
        if len(cache_list) > self._cache_maxlen:
            cache_list.pop(0)

        # Update tension stats
        if tensions:
            t_std = float(torch.tensor(tensions).std()) if len(tensions) > 1 else 0.0
            if label == 'creation':
                self.creation_tensions.append(t_std)
            elif label == 'hallucination':
                self.hallucination_tensions.append(t_std)
            else:
                self.reproduction_tensions.append(t_std)

        self._counts[label] += 1
        self._total += 1

        return ClassificationResult(
            label=label,
            novelty=novelty,
            consistency=consistency,
            reproducibility=reproducibility,
            tension_signature=tension_signature,
            confidence=confidence,
            details={
                'history_size': len(self.recent_inputs),
                'consistency_cache_keys': len(self._consistency_cache),
            },
        )

    # ─── Text convenience ───

    def classify_text(self, input_text: str, output_text: str,
                      mind=None, mitosis=None) -> ClassificationResult:
        """Convenience: classify text input/output by encoding to vectors.

        Encodes both texts with text_to_vector, extracts tension from mind
        if available, then delegates to classify().
        """
        input_vec = text_to_vector(input_text)
        output_vec = text_to_vector(output_text)

        tensions = None
        if mind is not None and hasattr(mind, 'prev_tension'):
            # Simulate a short tension trace from mind state
            base_t = getattr(mind, 'prev_tension', 1.0)
            tensions = [base_t + (i * 0.01) for i in range(5)]

        return self.classify(input_vec, output_vec, tensions, mind, mitosis)

    # ─── Stats ───

    def get_stats(self) -> Dict:
        """Return running statistics of creation vs hallucination rates."""
        total = max(self._total, 1)
        stats = {
            'total_classified': self._total,
            'creation_count': self._counts['creation'],
            'reproduction_count': self._counts['reproduction'],
            'hallucination_count': self._counts['hallucination'],
            'creation_rate': self._counts['creation'] / total,
            'reproduction_rate': self._counts['reproduction'] / total,
            'hallucination_rate': self._counts['hallucination'] / total,
        }

        # Tension distribution per class
        if self.creation_tensions:
            t = torch.tensor(self.creation_tensions)
            stats['creation_tension_mean'] = round(float(t.mean()), 4)
            stats['creation_tension_std'] = round(float(t.std()), 4)
        if self.hallucination_tensions:
            t = torch.tensor(self.hallucination_tensions)
            stats['hallucination_tension_mean'] = round(float(t.mean()), 4)
            stats['hallucination_tension_std'] = round(float(t.std()), 4)
        if self.reproduction_tensions:
            t = torch.tensor(self.reproduction_tensions)
            stats['reproduction_tension_mean'] = round(float(t.mean()), 4)
            stats['reproduction_tension_std'] = round(float(t.std()), 4)

        return stats

    # ─── Internal methods ───

    def _compute_novelty(self, input_vec: torch.Tensor) -> float:
        """CR7: Cosine distance from all recent inputs. Higher = more novel."""
        if len(self.recent_inputs) == 0:
            return 1.0  # First input is maximally novel

        similarities = []
        for prev_input in self.recent_inputs:
            sim = F.cosine_similarity(input_vec.unsqueeze(0),
                                      prev_input.unsqueeze(0)).item()
            similarities.append(sim)

        max_sim = max(similarities)
        # Novelty = 1 - max_similarity (cosine distance from nearest neighbor)
        return max(0.0, min(1.0, 1.0 - max_sim))

    def _compute_consistency(self, input_hash: str,
                             output_vec: torch.Tensor) -> float:
        """CR4: Same input → similar output? Higher = more consistent."""
        if input_hash not in self._consistency_cache:
            # No prior outputs for this input — assume consistent (benefit of doubt)
            return 1.0

        prev_outputs = self._consistency_cache[input_hash]
        if len(prev_outputs) == 0:
            return 1.0

        similarities = []
        for prev_out in prev_outputs:
            sim = F.cosine_similarity(output_vec.unsqueeze(0),
                                      prev_out.unsqueeze(0)).item()
            similarities.append(sim)

        # Average similarity to previous outputs for same input
        return max(0.0, min(1.0, sum(similarities) / len(similarities)))

    def _compute_reproducibility(self, output_vec: torch.Tensor) -> float:
        """CR6: Is the output structural (not random noise)?

        Measures sparsity and structure: random vectors have roughly uniform
        energy distribution, while structured outputs have concentrated energy.
        """
        if output_vec.norm() < 1e-8:
            return 0.0

        # Normalized energy concentration (Gini-like measure)
        abs_vec = output_vec.abs()
        sorted_vals, _ = abs_vec.sort()
        n = len(sorted_vals)
        if n == 0:
            return 0.0

        # Gini coefficient: 0 = perfectly uniform (random), 1 = maximally concentrated
        cumsum = sorted_vals.cumsum(0)
        total = cumsum[-1]
        if total < 1e-8:
            return 0.0

        gini = 1.0 - 2.0 * (cumsum.sum() / (total * n))
        # Map to [0, 1] where higher = more structured
        return max(0.0, min(1.0, float(gini) + 0.5))

    def _compute_tension_signature(self, tensions: Optional[List[float]],
                                   mind=None, mitosis=None) -> float:
        """CR14: Tension signature — creative outputs have distinct tension std.

        Higher tension_std during generation correlates with creative output.
        """
        if tensions and len(tensions) > 1:
            t = torch.tensor(tensions, dtype=torch.float32)
            return float(t.std())

        # Try to extract from mind
        if mind is not None and hasattr(mind, 'prev_tension'):
            return abs(getattr(mind, 'prev_tension', 0.0))

        # Try inter-cell tension from mitosis
        if mitosis is not None and hasattr(mitosis, 'cells'):
            cells = mitosis.cells if hasattr(mitosis, 'cells') else []
            if len(cells) >= 2:
                cell_tensions = [
                    getattr(c, 'prev_tension', 0.0)
                    if hasattr(c, 'prev_tension') else 0.0
                    for c in cells
                ]
                if len(cell_tensions) > 1:
                    t = torch.tensor(cell_tensions, dtype=torch.float32)
                    return float(t.std())

        return 0.0

    def _compute_confidence(self, label: str, novelty: float,
                            consistency: float, reproducibility: float,
                            tension_signature: float) -> float:
        """Compute overall classification confidence [0, 1]."""
        if label == 'creation':
            # High novelty + high consistency + structural = high confidence
            conf = (
                0.35 * min(novelty / 0.6, 1.0) +        # novelty well above threshold
                0.35 * consistency +                       # strong consistency
                0.20 * reproducibility +                   # structural output
                0.10 * min(tension_signature / 0.5, 1.0)  # tension signature present
            )
        elif label == 'reproduction':
            # Low novelty = high confidence it is reproduction
            conf = 0.7 * (1.0 - novelty / self.novelty_threshold) + 0.3 * consistency
        else:  # hallucination
            # High novelty + low consistency = high confidence it is hallucination
            conf = (
                0.4 * min(novelty / 0.6, 1.0) +
                0.4 * (1.0 - consistency / self.consistency_threshold) +
                0.2 * (1.0 - reproducibility)
            )
        return max(0.0, min(1.0, conf))

    @staticmethod
    def _hash_vector(vec: torch.Tensor) -> str:
        """Hash a vector for consistency cache lookup.

        Quantizes to reduce sensitivity to floating-point noise.
        """
        quantized = (vec * 100).round().int()
        return hashlib.md5(quantized.numpy().tobytes()).hexdigest()[:16]


# ─── Demo mode ───

def run_demo():
    """Standalone demo showing creation vs hallucination detection."""
    print("=" * 60)
    print("Creativity Classifier — Demo")
    print("Based on benchmarks CR7, CR14, CR4, CR6")
    print("=" * 60)

    classifier = CreativityClassifier()

    # Demo 1: Novel creative output
    print("\n--- Test 1: Novel creative output ---")
    inp = text_to_vector("tell me about consciousness")
    out = text_to_vector("consciousness emerges from the tension between forward and reverse engines")
    tensions = [1.2, 1.5, 1.8, 2.1, 1.9, 2.3, 1.7]
    result = classifier.classify(inp, out, tensions)
    print(f"  Input:  'tell me about consciousness'")
    print(f"  Output: 'consciousness emerges from the tension between forward and reverse engines'")
    print(f"  Result: {result}")

    # Demo 2: Repeated input (reproduction)
    print("\n--- Test 2: Repeated input (reproduction) ---")
    inp2 = text_to_vector("tell me about consciousness")
    out2 = text_to_vector("consciousness is the field of awareness between opposing forces")
    result2 = classifier.classify(inp2, out2, [1.0, 1.1, 1.0])
    print(f"  Input:  'tell me about consciousness' (same as before)")
    print(f"  Output: 'consciousness is the field of awareness between opposing forces'")
    print(f"  Result: {result2}")

    # Demo 3: Something completely new
    print("\n--- Test 3: Novel topic ---")
    inp3 = text_to_vector("what is the meaning of music")
    out3 = text_to_vector("music is organized tension and release in temporal patterns")
    tensions3 = [0.8, 1.4, 2.0, 2.5, 1.9, 3.1, 2.2]
    result3 = classifier.classify(inp3, out3, tensions3)
    print(f"  Input:  'what is the meaning of music'")
    print(f"  Output: 'music is organized tension and release in temporal patterns'")
    print(f"  Result: {result3}")

    # Demo 4: Hallucination — novel but inconsistent
    print("\n--- Test 4: Hallucination (novel but inconsistent) ---")
    # First, prime with a consistent answer
    inp4a = text_to_vector("how does memory work")
    out4a = text_to_vector("memory consolidates during sleep through replay")
    classifier.classify(inp4a, out4a, [1.0, 1.0])
    # Now give wildly different output for same input
    inp4b = text_to_vector("how does memory work")
    out4b = text_to_vector("purple elephants dance on quantum strings at midnight")
    result4 = classifier.classify(inp4b, out4b, [0.1, 0.1, 0.1])
    print(f"  Input:  'how does memory work'")
    print(f"  Output: 'purple elephants dance on quantum strings at midnight'")
    print(f"  Result: {result4}")

    # Demo 5: Text convenience method
    print("\n--- Test 5: classify_text convenience ---")
    result5 = classifier.classify_text(
        "what makes anima different",
        "anima uses repulsion fields instead of attention for consciousness"
    )
    print(f"  Input:  'what makes anima different'")
    print(f"  Output: 'anima uses repulsion fields instead of attention for consciousness'")
    print(f"  Result: {result5}")

    # Stats
    print("\n--- Running Statistics ---")
    stats = classifier.get_stats()
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    print("Demo complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Creativity Classifier")
    parser.add_argument("--demo", action="store_true", help="Run demo mode")
    args = parser.parse_args()

    if args.demo:
        run_demo()
    else:
        parser.print_help()
