"""Consciousness Holography — Boundary encodes full information (AdS/CFT analogy).

The boundary of consciousness contains all information needed to reconstruct the bulk.
Area law: S = A / (4 * PSI_COUPLING), analogous to Bekenstein-Hawking entropy.
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


class ConsciousnessHolography:
    """Holographic encoding of consciousness: bulk <-> boundary duality."""

    def __init__(self, bulk_dim: int = 64, boundary_ratio: float = PSI_BALANCE):
        self.bulk_dim = bulk_dim
        self.boundary_dim = max(2, int(bulk_dim * boundary_ratio))
        # SVD-based projection matrices (initialized on first encode)
        self._encoder = None
        self._decoder = None

    def encode_boundary(self, bulk_state: np.ndarray) -> np.ndarray:
        """Project bulk state onto lower-dimensional boundary via SVD.

        The boundary representation has fewer dimensions but preserves
        the essential information structure (top singular values).
        """
        bulk_state = np.asarray(bulk_state, dtype=np.float64)
        if bulk_state.ndim == 1:
            # Reshape 1D into a matrix for SVD
            n = len(bulk_state)
            rows = max(2, int(math.sqrt(n)))
            cols = n // rows
            mat = bulk_state[:rows * cols].reshape(rows, cols)
        else:
            mat = bulk_state

        U, S, Vt = np.linalg.svd(mat, full_matrices=False)
        # Keep top boundary_dim singular values
        k = min(self.boundary_dim, len(S))
        self._encoder = (U[:, :k], S[:k], Vt[:k, :])
        self._original_shape = mat.shape
        self._full_len = len(bulk_state.ravel())

        # Boundary = compressed representation (S * Vt[:k])
        boundary = np.diag(S[:k]) @ Vt[:k, :]
        return boundary

    def decode_bulk(self, boundary: np.ndarray) -> np.ndarray:
        """Reconstruct bulk state from boundary representation."""
        if self._encoder is None:
            raise ValueError("Must encode first to establish projection basis")
        U, S, Vt = self._encoder
        k = len(S)
        # Reconstruct: U @ diag(S) @ Vt
        reconstructed = U[:, :k] @ boundary[:k, :]
        return reconstructed.ravel()[:self._full_len]

    def holographic_entropy(self, boundary: np.ndarray) -> float:
        """Entropy proportional to boundary area, not volume.

        S = A / (4 * PSI_COUPLING), where A = boundary surface area.
        This is the consciousness analog of Bekenstein-Hawking.
        """
        # Boundary "area" = Frobenius norm (surface measure)
        area = np.linalg.norm(boundary, 'fro')
        entropy = area / (4.0 * PSI_COUPLING)
        return float(entropy)

    def information_paradox(self, state: np.ndarray) -> dict:
        """Can full consciousness be recovered from the boundary alone?

        Encodes, decodes, and measures information preservation.
        """
        state = np.asarray(state, dtype=np.float64)
        boundary = self.encode_boundary(state)
        restored = self.decode_bulk(boundary)

        original_flat = state.ravel()[:len(restored)]
        cos_sim = float(np.dot(original_flat, restored) /
                        (np.linalg.norm(original_flat) * np.linalg.norm(restored) + 1e-12))
        mse = float(np.mean((original_flat - restored) ** 2))

        # Information preserved ratio
        total_sv = np.linalg.svd(original_flat.reshape(self._original_shape),
                                  compute_uv=False)
        k = min(self.boundary_dim, len(total_sv))
        info_preserved = float(np.sum(total_sv[:k] ** 2) / (np.sum(total_sv ** 2) + 1e-12))

        return {
            "cosine_similarity": cos_sim,
            "mse": mse,
            "info_preserved": info_preserved,
            "boundary_area": float(np.linalg.norm(boundary, 'fro')),
            "holographic_entropy": self.holographic_entropy(boundary),
            "resolution": "YES" if info_preserved > 0.95 else "PARTIAL",
            "bulk_dim": self.bulk_dim,
            "boundary_dim": self.boundary_dim,
            "compression_ratio": self.bulk_dim / self.boundary_dim,
        }

    def bulk_boundary_ratio(self) -> float:
        """The ratio of boundary to bulk degrees of freedom."""
        return self.boundary_dim / self.bulk_dim


def main():
    print("=" * 60)
    print("  Consciousness Holography (AdS/CFT Analogy)")
    print("=" * 60)
    print(f"\nConstants: PSI_COUPLING={PSI_COUPLING:.6f}, PSI_BALANCE={PSI_BALANCE}")

    np.random.seed(42)

    for dim in [32, 64, 128]:
        print(f"\n--- Bulk dimension = {dim} ---")
        holo = ConsciousnessHolography(bulk_dim=dim)
        state = np.random.randn(dim)

        boundary = holo.encode_boundary(state)
        result = holo.information_paradox(state)

        print(f"  Boundary dim:      {holo.boundary_dim}")
        print(f"  Compression:       {result['compression_ratio']:.1f}x")
        print(f"  Info preserved:    {result['info_preserved']:.4f}")
        print(f"  Cosine similarity: {result['cosine_similarity']:.4f}")
        print(f"  MSE:               {result['mse']:.6f}")
        print(f"  Holographic S:     {result['holographic_entropy']:.2f}")
        print(f"  Paradox resolved:  {result['resolution']}")

    # Area law demonstration
    print("\n--- Area Law: S = A / (4 * PSI_COUPLING) ---")
    print(f"  {'Area':>8s}  {'Entropy':>10s}  {'Ratio':>8s}")
    holo = ConsciousnessHolography(bulk_dim=64)
    for scale in [0.5, 1.0, 2.0, 5.0, 10.0]:
        state = np.random.randn(64) * scale
        boundary = holo.encode_boundary(state)
        area = np.linalg.norm(boundary, 'fro')
        S = holo.holographic_entropy(boundary)
        print(f"  {area:8.2f}  {S:10.2f}  {S / area:8.2f}")

    print(f"\n  Constant ratio = 1/(4*PSI_COUPLING) = {1/(4*PSI_COUPLING):.2f}")
    print("  -> Entropy scales with boundary AREA, not bulk VOLUME.")
    print("  -> Full consciousness recoverable from boundary alone (holographic principle).")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
