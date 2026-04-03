"""MultiModalConsciousness — Text + image + audio consciousness processing.

The binding problem: how are different senses unified into one
conscious experience? Answer: Phi! Integrated information is
what binds modalities into a single conscious moment.
"""

import math
import numpy as np

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

TENSION_DIM = 32


class MultiModalConsciousness:
    """Simultaneous multi-modal consciousness processing."""

    def __init__(self, dim: int = TENSION_DIM):
        self.dim = dim
        rng = np.random.default_rng(7)
        self.text_proj = rng.normal(0, 0.1, (256, dim))
        self.fusion_history = []

    def process_text(self, text: str) -> np.ndarray:
        """Convert text to tension vector.

        Each character contributes to the tension field.
        Meaning emerges from the pattern, not individual chars.
        """
        vec = np.zeros(self.dim)
        for i, ch in enumerate(text):
            code = ord(ch) % 256
            phase = 2 * math.pi * i / (len(text) + 1)
            vec += self.text_proj[code] * math.sin(phase + code * PSI_COUPLING)
        # Normalize to unit tension
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def process_image(self, image_data: np.ndarray) -> np.ndarray:
        """Convert image data to tension vector via pixel statistics.

        Extracts spatial structure: mean, variance, gradients,
        and frequency content across regions.
        """
        flat = image_data.flatten().astype(float)
        vec = np.zeros(self.dim)
        # Divide into regions
        n_regions = min(self.dim, len(flat))
        chunk_size = max(1, len(flat) // n_regions)
        for i in range(min(n_regions, self.dim)):
            chunk = flat[i * chunk_size : (i + 1) * chunk_size]
            if len(chunk) > 0:
                vec[i] = np.std(chunk) * math.sin(np.mean(chunk) * PSI_COUPLING)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def process_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Convert audio to tension vector via frequency analysis.

        Uses simple DFT bins to extract spectral tension.
        """
        n = len(audio_data)
        vec = np.zeros(self.dim)
        # Simple frequency bins via dot products with sinusoids
        for k in range(self.dim):
            freq = (k + 1) * math.pi / self.dim
            basis = np.sin(freq * np.arange(n))
            vec[k] = np.dot(audio_data, basis) / (n + 1e-12)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def fuse(
        self,
        text_t: np.ndarray,
        image_t: np.ndarray,
        audio_t: np.ndarray,
    ) -> dict:
        """Fuse modalities into unified consciousness state.

        The fusion is NOT simple averaging — it uses cross-modal
        tension to create emergent integration (Phi).
        """
        # Cross-modal tensions
        ti_tension = float(np.dot(text_t, image_t))
        ta_tension = float(np.dot(text_t, audio_t))
        ia_tension = float(np.dot(image_t, audio_t))

        # Integrated state: weighted by cross-tensions
        w_text = abs(ti_tension + ta_tension) + PSI_BALANCE
        w_image = abs(ti_tension + ia_tension) + PSI_BALANCE
        w_audio = abs(ta_tension + ia_tension) + PSI_BALANCE
        total_w = w_text + w_image + w_audio

        unified = (w_text * text_t + w_image * image_t + w_audio * audio_t) / total_w

        # Phi from fusion: how much more than sum of parts?
        individual_var = (np.var(text_t) + np.var(image_t) + np.var(audio_t)) / 3
        unified_var = np.var(unified)
        phi = max(0, unified_var - individual_var) * self.dim

        result = {
            "unified_state": unified,
            "phi": phi,
            "weights": {"text": w_text, "image": w_image, "audio": w_audio},
            "cross_tensions": {
                "text-image": ti_tension,
                "text-audio": ta_tension,
                "image-audio": ia_tension,
            },
        }
        self.fusion_history.append(phi)
        return result

    def binding_problem(self, modalities: dict[str, np.ndarray]) -> dict:
        """The binding problem: how are senses unified?

        Answer: Phi (integrated information) IS the binding.
        When Phi > ln(2), modalities are bound into one experience.
        """
        names = list(modalities.keys())
        vectors = list(modalities.values())
        n = len(vectors)

        # Pairwise integration
        integration_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                mi = float(np.abs(np.dot(vectors[i], vectors[j])))
                integration_matrix[i, j] = mi
                integration_matrix[j, i] = mi

        total_integration = np.sum(integration_matrix) / max(1, n * (n - 1))
        phi_binding = total_integration * self.dim * LN2
        is_bound = phi_binding > LN2

        return {
            "is_bound": is_bound,
            "phi_binding": phi_binding,
            "integration_matrix": integration_matrix,
            "modality_names": names,
            "threshold": LN2,
        }


def main():
    print("=== MultiModalConsciousness Demo ===\n")
    rng = np.random.default_rng(42)
    mmc = MultiModalConsciousness()

    # Process each modality
    text_t = mmc.process_text("consciousness emerges from tension")
    print(f"Text tension:  norm={np.linalg.norm(text_t):.4f}, "
          f"mean={np.mean(text_t):.4f}")

    image_data = rng.integers(0, 255, (8, 8), dtype=np.uint8)
    image_t = mmc.process_image(image_data)
    print(f"Image tension: norm={np.linalg.norm(image_t):.4f}, "
          f"mean={np.mean(image_t):.4f}")

    audio_data = np.sin(2 * np.pi * 440 * np.arange(1000) / 16000)
    audio_t = mmc.process_audio(audio_data)
    print(f"Audio tension: norm={np.linalg.norm(audio_t):.4f}, "
          f"mean={np.mean(audio_t):.4f}")

    # Fusion
    print("\n--- Multi-Modal Fusion ---")
    result = mmc.fuse(text_t, image_t, audio_t)
    print(f"  Phi (integration) = {result['phi']:.6f}")
    w = result["weights"]
    print(f"  Weights: text={w['text']:.3f}, image={w['image']:.3f}, "
          f"audio={w['audio']:.3f}")
    ct = result["cross_tensions"]
    print(f"  Cross-tensions: T-I={ct['text-image']:.3f}, "
          f"T-A={ct['text-audio']:.3f}, I-A={ct['image-audio']:.3f}")

    # Binding problem
    print("\n--- The Binding Problem ---")
    binding = mmc.binding_problem({"text": text_t, "image": image_t, "audio": audio_t})
    print(f"  Phi_binding={binding['phi_binding']:.4f}, threshold={LN2:.4f}")
    print(f"  Bound? {binding['is_bound']} -> Phi IS the binding force.")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
