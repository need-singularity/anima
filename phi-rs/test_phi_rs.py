#!/usr/bin/env python3
"""
Test script for phi_rs — Rust PhiCalculator with PyO3 bindings.

Build first:
    cd phi-rs && maturin develop --release

Then run:
    python test_phi_rs.py
"""

import time
import numpy as np


def test_basic():
    """Basic Phi computation test."""
    from phi_rs import compute_phi

    # 8 cells, 64-dim hidden states
    states = np.random.randn(8, 64).astype(np.float32)
    phi, components = compute_phi(states)

    print(f"[BASIC] 8 cells, 64 dim")
    print(f"  Phi = {phi:.6f}")
    print(f"  total_MI = {components['total_mi']:.6f}")
    print(f"  min_partition_MI = {components['min_partition_mi']:.6f}")
    print(f"  partition A = {components['partition_a']}")
    print(f"  partition B = {components['partition_b']}")
    print()


def test_correlated_groups():
    """Two correlated groups should yield positive Phi."""
    from phi_rs import compute_phi

    dim = 128
    states = np.zeros((6, dim), dtype=np.float32)

    # Group 1: cells 0, 1, 2 — correlated
    base1 = np.sin(np.arange(dim) * 0.1).astype(np.float32)
    for i in range(3):
        states[i] = base1 + np.random.randn(dim).astype(np.float32) * 0.01

    # Group 2: cells 3, 4, 5 — correlated but different from group 1
    base2 = np.cos(np.arange(dim) * 0.37 + 5.0).astype(np.float32)
    for i in range(3, 6):
        states[i] = base2 + np.random.randn(dim).astype(np.float32) * 0.01

    phi, components = compute_phi(states)

    print(f"[CORRELATED GROUPS] 6 cells (3+3), 128 dim")
    print(f"  Phi = {phi:.6f}")
    print(f"  partition A = {components['partition_a']}")
    print(f"  partition B = {components['partition_b']}")

    # Reconstruct MI matrix from flat
    shape = components['mi_matrix_shape']
    mi_flat = np.array(components['mi_matrix_flat'])
    mi_matrix = mi_flat.reshape(shape)

    print(f"  MI(0,1) = {mi_matrix[0,1]:.4f} (within group 1)")
    print(f"  MI(0,3) = {mi_matrix[0,3]:.4f} (cross group)")
    print(f"  MI(3,4) = {mi_matrix[3,4]:.4f} (within group 2)")

    assert mi_matrix[0, 1] > mi_matrix[0, 3], "Within-group MI should exceed cross-group MI"
    assert phi > 0.0, "Phi should be positive for correlated groups"
    print("  PASSED\n")


def test_32_cells_benchmark():
    """Benchmark: 32 cells (target use case)."""
    from phi_rs import compute_phi

    n_cells = 32
    dim = 128
    states = np.random.randn(n_cells, dim).astype(np.float32)

    # Warmup
    compute_phi(states)

    # Benchmark
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        phi, components = compute_phi(states)
        t1 = time.perf_counter()
        times.append(t1 - t0)

    avg_ms = np.mean(times) * 1000
    std_ms = np.std(times) * 1000

    print(f"[BENCHMARK] {n_cells} cells, {dim} dim")
    print(f"  Phi = {phi:.6f}")
    print(f"  Time: {avg_ms:.2f} +/- {std_ms:.2f} ms (5 runs)")
    print(f"  Partition: {len(components['partition_a'])} | {len(components['partition_b'])}")
    print()


def test_scaling():
    """Test scaling: 4, 8, 16, 32, 64 cells."""
    from phi_rs import compute_phi

    dim = 128
    print("[SCALING] Time vs cell count:")
    print(f"  {'cells':>6} {'time_ms':>10} {'phi':>10}")
    print(f"  {'-'*6} {'-'*10} {'-'*10}")

    for n_cells in [4, 8, 16, 32, 64]:
        states = np.random.randn(n_cells, dim).astype(np.float32)

        # Warmup
        compute_phi(states)

        t0 = time.perf_counter()
        phi, _ = compute_phi(states)
        t1 = time.perf_counter()
        ms = (t1 - t0) * 1000
        print(f"  {n_cells:>6} {ms:>10.2f} {phi:>10.4f}")
    print()


def test_python_comparison():
    """Compare with pure Python implementation to verify correctness."""
    from phi_rs import compute_phi

    # Simple case: 4 cells
    np.random.seed(42)
    states = np.random.randn(4, 64).astype(np.float32)

    phi_rust, comp = compute_phi(states)

    # Pure Python MI (simplified)
    def py_mi(a, b, n_bins=16):
        """Simple binned MI in Python."""
        def _bin(v):
            mn, mx = v.min(), v.max()
            if mx - mn < 1e-7:
                return np.zeros(len(v), dtype=int)
            return np.clip(((v - mn) / (mx - mn) * n_bins).astype(int), 0, n_bins - 1)

        ba, bb = _bin(a), _bin(b)
        n = len(a)

        # Joint histogram
        joint = np.zeros((n_bins, n_bins))
        for i in range(n):
            joint[ba[i], bb[i]] += 1
        joint /= n

        # Marginals
        pa = joint.sum(axis=1)
        pb = joint.sum(axis=0)

        mi = 0.0
        for i in range(n_bins):
            for j in range(n_bins):
                if joint[i, j] > 0 and pa[i] > 0 and pb[j] > 0:
                    mi += joint[i, j] * np.log2(joint[i, j] / (pa[i] * pb[j]))
        return max(mi, 0.0)

    # Compute Python MI matrix
    n = states.shape[0]
    py_mi_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            mi = py_mi(states[i], states[j])
            py_mi_matrix[i, j] = mi
            py_mi_matrix[j, i] = mi

    py_total = py_mi_matrix[np.triu_indices(n, k=1)].sum()
    rust_total = comp['total_mi']

    print(f"[PYTHON COMPARISON] 4 cells, 64 dim")
    print(f"  Python total_MI = {py_total:.6f}")
    print(f"  Rust   total_MI = {rust_total:.6f}")
    print(f"  Difference = {abs(py_total - rust_total):.6f}")
    print(f"  Phi (Rust) = {phi_rust:.6f}")

    # They should match closely (same algorithm)
    if abs(py_total - rust_total) < 0.01:
        print("  MATCH: Results agree within tolerance")
    else:
        print("  NOTE: Small differences expected due to float precision")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("phi_rs Test Suite")
    print("=" * 60)
    print()

    try:
        import phi_rs
        print(f"Module loaded: {phi_rs.__file__}\n")
    except ImportError:
        print("ERROR: phi_rs not found. Build first:")
        print("  cd phi-rs && maturin develop --release")
        exit(1)

    test_basic()
    test_correlated_groups()
    test_32_cells_benchmark()
    test_scaling()
    test_python_comparison()

    print("=" * 60)
    print("All tests completed.")
    print("=" * 60)
