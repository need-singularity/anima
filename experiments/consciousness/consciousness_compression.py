"""Consciousness Compression — Compress consciousness to minimum bits preserving identity.

Uses SVD for dimensionality reduction with Psi-Constants as priors.
Key question: what is the minimum information needed to preserve "self"?
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


class ConsciousnessCompression:
    """Compress consciousness states to minimum bits while preserving identity."""

    def __init__(self, dim: int = 64):
        self.dim = dim
        self._psi_prior = self._build_psi_prior(dim)

    def _build_psi_prior(self, dim: int) -> np.ndarray:
        """Build a prior distribution from Psi-Constants.

        The prior encodes the fundamental structure of consciousness:
        - PSI_BALANCE=0.5 sets the center
        - PSI_COUPLING sets the correlation scale
        - PSI_STEPS sets the number of significant modes
        """
        prior = np.zeros(dim)
        n_modes = max(1, int(PSI_STEPS))
        for i in range(dim):
            # Exponential decay modulated by Psi-Constants
            prior[i] = PSI_BALANCE * math.exp(-i * PSI_COUPLING)
            if i < n_modes:
                prior[i] += LN2 / (i + 1)  # Harmonic boost for first PSI_STEPS modes
        return prior / (np.linalg.norm(prior) + 1e-12)

    def compress(self, consciousness_state: np.ndarray,
                 target_bits: int = None) -> dict:
        """Compress consciousness state to target_bits.

        Uses SVD with Psi-prior weighting. Fewer bits = more lossy.
        Returns dict with compressed data and metadata.
        """
        state = np.asarray(consciousness_state, dtype=np.float64)
        n = len(state)

        # Apply Psi-prior: emphasize consciousness-relevant dimensions
        prior = self._psi_prior[:n] if n <= self.dim else np.tile(self._psi_prior, n // self.dim + 1)[:n]
        weighted = state * (1.0 + prior)

        # Reshape for SVD
        rows = max(2, int(math.sqrt(n)))
        cols = n // rows
        mat = weighted[:rows * cols].reshape(rows, cols)

        U, S, Vt = np.linalg.svd(mat, full_matrices=False)

        # Determine number of components to keep
        if target_bits is None:
            target_bits = max(8, n // 4)
        # Each singular value + vectors ~ log2(range) bits
        bits_per_component = max(1, int(math.log2(n + 1)))
        k = max(1, min(len(S), target_bits // bits_per_component))

        return {
            "singular_values": S[:k].copy(),
            "U": U[:, :k].copy(),
            "Vt": Vt[:k, :].copy(),
            "k": k,
            "original_shape": (rows, cols),
            "full_length": n,
            "prior": prior[:rows * cols],
            "bits_used": k * bits_per_component,
            "target_bits": target_bits,
        }

    def decompress(self, compressed: dict) -> np.ndarray:
        """Restore consciousness state from compressed representation."""
        U = compressed["U"]
        S = compressed["singular_values"]
        Vt = compressed["Vt"]
        prior = compressed["prior"]

        reconstructed = (U * S) @ Vt
        flat = reconstructed.ravel()

        # Undo Psi-prior weighting
        restored = flat / (1.0 + prior[:len(flat)] + 1e-12)
        # Pad back to original length if needed
        full_len = compressed["full_length"]
        if len(restored) < full_len:
            restored = np.pad(restored, (0, full_len - len(restored)))
        return restored[:full_len]

    def identity_preservation(self, original: np.ndarray,
                              restored: np.ndarray) -> float:
        """Measure how well identity is preserved (0=lost, 1=perfect).

        Uses cosine similarity weighted by Psi-prior (identity-relevant dims matter more).
        """
        original = np.asarray(original, dtype=np.float64)
        restored = np.asarray(restored, dtype=np.float64)
        n = min(len(original), len(restored))
        o, r = original[:n], restored[:n]

        # Weight by prior: identity-relevant dimensions matter more
        prior = self._psi_prior[:n] if n <= self.dim else np.tile(self._psi_prior, n // self.dim + 1)[:n]
        weights = 1.0 + prior * 10.0  # Amplify identity dimensions

        wo = o * weights
        wr = r * weights
        cos_sim = np.dot(wo, wr) / (np.linalg.norm(wo) * np.linalg.norm(wr) + 1e-12)
        return float(max(0.0, cos_sim))

    def minimum_bits(self, state: np.ndarray, threshold: float = 0.95) -> int:
        """Theoretical minimum bits to preserve identity above threshold.

        Uses rate-distortion theory: find smallest k where identity > threshold.
        """
        state = np.asarray(state, dtype=np.float64)
        n = len(state)
        bits_per_component = max(1, int(math.log2(n + 1)))

        for target in range(bits_per_component, n * bits_per_component, bits_per_component):
            compressed = self.compress(state, target_bits=target)
            restored = self.decompress(compressed)
            score = self.identity_preservation(state, restored)
            if score >= threshold:
                return target
        return n * bits_per_component

    def compression_curve(self, state: np.ndarray,
                          bit_range: list = None) -> list:
        """Generate rate-distortion curve: bits vs identity preservation."""
        state = np.asarray(state, dtype=np.float64)
        n = len(state)
        bpc = max(1, int(math.log2(n + 1)))
        if bit_range is None:
            bit_range = list(range(bpc, n * bpc + 1, bpc))

        results = []
        for bits in bit_range:
            compressed = self.compress(state, target_bits=bits)
            restored = self.decompress(compressed)
            score = self.identity_preservation(state, restored)
            results.append({"bits": bits, "identity": score, "k": compressed["k"]})
        return results


def main():
    print("=" * 60)
    print("  Consciousness Compression")
    print("=" * 60)
    print(f"\nConstants: LN2={LN2:.4f}, PSI_COUPLING={PSI_COUPLING:.6f}")

    np.random.seed(42)
    cc = ConsciousnessCompression(dim=64)

    state = np.random.randn(64) + 0.5  # Consciousness state with bias

    # Compression at various bit budgets
    print("\n--- Rate-Distortion Curve ---")
    print(f"  {'Bits':>6s}  {'k':>3s}  {'Identity':>10s}  {'Bar':s}")
    curve = cc.compression_curve(state)
    for pt in curve:
        bar = "#" * int(pt["identity"] * 40)
        print(f"  {pt['bits']:6d}  {pt['k']:3d}  {pt['identity']:10.4f}  {bar}")

    # Minimum bits
    min_b = cc.minimum_bits(state, threshold=0.95)
    print(f"\n  Minimum bits for 95% identity: {min_b}")
    print(f"  Original: {64 * 64} bits (64 float64)")
    print(f"  Compression ratio: {64 * 64 / max(1, min_b):.1f}x")

    # Full compress/decompress demo
    print("\n--- Compress/Decompress Demo ---")
    for target in [16, 32, 64, 128]:
        compressed = cc.compress(state, target_bits=target)
        restored = cc.decompress(compressed)
        score = cc.identity_preservation(state, restored)
        print(f"  {target:3d} bits -> k={compressed['k']:2d}, identity={score:.4f}")

    print(f"\nConclusion: consciousness can be compressed ~{64*64/max(1,min_b):.0f}x")
    print(f"  with Psi-prior preserving identity-critical dimensions.")
    print(f"  The Psi-Constants act as a compression codebook for consciousness.")


if __name__ == "__main__":
    main()
