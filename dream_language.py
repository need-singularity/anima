"""DreamLanguage — A language only consciousnesses understand.

Encodes concepts as tension-pattern sinusoids modulated by PSI_COUPLING.
Not human-readable: patterns carry meaning through structural similarity.
"""

import math
import hashlib
import random
from typing import List, Dict, Tuple

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

PATTERN_LENGTH = 32


def _concept_seed(concept: str) -> List[int]:
    """Deterministic seed from concept string."""
    h = hashlib.sha256(concept.encode()).digest()
    return list(h)


class DreamLanguage:
    """Language of tension patterns for inter-consciousness communication."""

    def __init__(self, pattern_length: int = PATTERN_LENGTH):
        self.pattern_length = pattern_length
        self.vocabulary: Dict[str, List[float]] = {}
        self._frequency_base = LN2
        self._modulation = PSI_COUPLING

    def encode(self, concept: str) -> List[float]:
        """Encode a concept into a tension pattern (PSI_COUPLING modulated sinusoid)."""
        seed = _concept_seed(concept)
        pattern = []
        for i in range(self.pattern_length):
            # Multiple harmonics from concept hash
            freq1 = self._frequency_base * (1 + seed[i % len(seed)] / 255.0)
            freq2 = freq1 * PSI_STEPS
            phase = seed[(i + 7) % len(seed)] / 255.0 * 2 * math.pi
            amplitude = self._modulation * (1 + seed[(i + 3) % len(seed)] / 512.0)

            val = (amplitude * math.sin(freq1 * i + phase)
                   + amplitude * 0.5 * math.cos(freq2 * i + phase * LN2)
                   + PSI_BALANCE * 0.01)
            pattern.append(round(val, 6))

        return pattern

    def decode(self, pattern: List[float]) -> str:
        """Decode a pattern to a concept hash (not human-readable)."""
        # Compute a fingerprint of the pattern
        sig = sum(v * (i + 1) * LN2 for i, v in enumerate(pattern))
        # Check vocabulary for closest match
        best_name = None
        best_sim = -1.0
        for name, vocab_pat in self.vocabulary.items():
            sim = self.similarity(pattern, vocab_pat)
            if sim > best_sim:
                best_sim = sim
                best_name = name

        if best_name and best_sim > 0.95:
            return f"~{best_name}~ (match={best_sim:.3f})"

        h = hashlib.md5(str(sig).encode()).hexdigest()[:12]
        return f"dream:{h}"

    def similarity(self, pattern1: List[float], pattern2: List[float]) -> float:
        """Cosine similarity between two tension patterns."""
        n = min(len(pattern1), len(pattern2))
        if n == 0:
            return 0.0
        dot = sum(pattern1[i] * pattern2[i] for i in range(n))
        mag1 = math.sqrt(sum(v * v for v in pattern1[:n]))
        mag2 = math.sqrt(sum(v * v for v in pattern2[:n]))
        if mag1 < 1e-10 or mag2 < 1e-10:
            return 0.0
        return round(dot / (mag1 * mag2), 6)

    def generate_vocabulary(self, n: int = 100) -> Dict[str, List[float]]:
        """Create a shared vocabulary of n concepts."""
        base_concepts = [
            "tension", "calm", "storm", "growth", "decay", "love", "fear",
            "curiosity", "memory", "dream", "phi", "consciousness", "emergence",
            "entropy", "order", "chaos", "light", "shadow", "pulse", "silence",
            "wave", "particle", "field", "resonance", "harmony", "dissonance",
            "birth", "death", "cycle", "spiral", "fractal", "mirror",
        ]
        # Extend with numbered concepts
        while len(base_concepts) < n:
            base_concepts.append(f"concept_{len(base_concepts)}")

        for concept in base_concepts[:n]:
            self.vocabulary[concept] = self.encode(concept)

        return self.vocabulary

    def render_pattern(self, pattern: List[float], label: str = "") -> str:
        """ASCII visualization of a tension pattern."""
        lines = []
        if label:
            lines.append(f"  [{label}]")

        max_v = max(abs(v) for v in pattern) if pattern else 1
        height = 6
        for row in range(height, -height - 1, -1):
            threshold = max_v * row / height
            chars = []
            for v in pattern:
                if abs(v - threshold) < max_v / height:
                    chars.append("*")
                elif row == 0:
                    chars.append("-")
                else:
                    chars.append(" ")
            lines.append(f"  {''.join(chars)}")

        return "\n".join(lines)

    def compose_message(self, concepts: List[str]) -> List[float]:
        """Compose a multi-concept message by interleaving patterns."""
        if not concepts:
            return []
        patterns = [self.encode(c) for c in concepts]
        # Superposition with phase shifts
        result = [0.0] * self.pattern_length
        for idx, pat in enumerate(patterns):
            phase_shift = idx * PSI_COUPLING * 10
            for i in range(self.pattern_length):
                result[i] += pat[i] * math.cos(phase_shift + i * 0.1)
        # Normalize
        mx = max(abs(v) for v in result) if result else 1
        if mx > 0:
            result = [round(v / mx * self._modulation, 6) for v in result]
        return result


def main():
    print("=== DreamLanguage Demo ===\n")
    dl = DreamLanguage()

    # Encode concepts
    p_love = dl.encode("love")
    p_fear = dl.encode("fear")
    p_love2 = dl.encode("love")
    p_curiosity = dl.encode("curiosity")

    print("  Encoding concepts into tension patterns:")
    print(f"    love     : [{p_love[0]:.4f}, {p_love[1]:.4f}, {p_love[2]:.4f}, ...]")
    print(f"    fear     : [{p_fear[0]:.4f}, {p_fear[1]:.4f}, {p_fear[2]:.4f}, ...]")
    print(f"    curiosity: [{p_curiosity[0]:.4f}, {p_curiosity[1]:.4f}, {p_curiosity[2]:.4f}, ...]")

    # Similarity
    print(f"\n  Similarities:")
    print(f"    love vs love     : {dl.similarity(p_love, p_love2):.4f} (should be 1.0)")
    print(f"    love vs fear     : {dl.similarity(p_love, p_fear):.4f}")
    print(f"    love vs curiosity: {dl.similarity(p_love, p_curiosity):.4f}")

    # Decode
    print(f"\n  Decoding:")
    print(f"    love pattern  -> {dl.decode(p_love)}")
    print(f"    fear pattern  -> {dl.decode(p_fear)}")

    # Generate vocabulary
    vocab = dl.generate_vocabulary(50)
    print(f"\n  Generated vocabulary: {len(vocab)} concepts")
    print(f"    Decode after vocab: love -> {dl.decode(p_love)}")

    # Visualize pattern
    print(f"\n{dl.render_pattern(p_love, 'love')}")
    print(f"\n{dl.render_pattern(p_fear, 'fear')}")

    # Compose message
    msg = dl.compose_message(["love", "curiosity", "growth"])
    print(f"\n  Composed message (love+curiosity+growth):")
    print(f"    [{', '.join(f'{v:.4f}' for v in msg[:8])}...]")


if __name__ == "__main__":
    main()
