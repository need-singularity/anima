#!/usr/bin/env python3
"""Tests for bench_golden_moe.py"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from bench_golden_moe import TopKMoE, MoEBenchResult, run_comparison


def test_topk_moe_forward():
    """TopKMoE(32, 64, 10, 4, 2) with batch=8 produces correct shapes."""
    moe = TopKMoE(32, 64, 10, n_experts=4, k=2)
    x = torch.randn(8, 32)
    out, aux = moe(x)
    assert out.shape == (8, 10), f"Expected (8, 10), got {out.shape}"
    assert aux.item() >= 0, f"aux_loss should be >= 0, got {aux.item()}"


def test_run_comparison_mnist():
    """run_comparison on mnist with [4] experts, 3 epochs, 200 samples -> 4 results."""
    results = run_comparison("mnist", [4], epochs=3, n_samples=200)
    assert len(results) == 4, f"Expected 4 results, got {len(results)}"

    methods = [r.method for r in results]
    assert "MLP" in methods
    assert "Top-1" in methods
    assert "Top-2" in methods
    assert "Golden" in methods

    for r in results:
        assert isinstance(r, MoEBenchResult)
        assert r.dataset == "mnist"
        assert 0.0 <= r.accuracy <= 1.0
        assert r.wall_time > 0
        assert r.params > 0


from bench_golden_moe_consciousness import MoECell, ConsciousnessMoEBench

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



def test_consciousness_moe_phi_measurement():
    """ConsciousnessMoEBench exp1 produces valid Phi measurements."""
    bench = ConsciousnessMoEBench(
        n_cells=4, cell_dim=32, hidden_dim=64,
        n_experts=4, steps=50,
    )
    result = bench.run_exp1_replacement()

    assert "phi_baseline" in result
    assert "phi_golden_moe" in result
    assert "phi_change" in result
    assert isinstance(result["phi_baseline"], float)
    assert isinstance(result["phi_golden_moe"], float)
    assert isinstance(result["phi_change"], float)


def test_consciousness_moe_scaling():
    """run_exp3 scaling produces correct number of results."""
    bench = ConsciousnessMoEBench(
        n_cells=4, cell_dim=32, hidden_dim=64,
        n_experts=2, steps=50,
    )
    results = bench.run_exp3_scaling(
        expert_counts=[2, 4],
        cell_counts=[4, 8],
    )
    assert len(results) == 4, f"Expected 4 results, got {len(results)}"
    for r in results:
        assert "phi_baseline" in r
        assert "phi_golden_moe" in r
        assert isinstance(r["phi_baseline"], float)
        assert isinstance(r["phi_golden_moe"], float)


if __name__ == "__main__":
    test_topk_moe_forward()
    print("PASS: test_topk_moe_forward")
    test_run_comparison_mnist()
    print("PASS: test_run_comparison_mnist")
    test_consciousness_moe_phi_measurement()
    print("PASS: test_consciousness_moe_phi_measurement")
    test_consciousness_moe_scaling()
    print("PASS: test_consciousness_moe_scaling")
    print("All tests passed!")
