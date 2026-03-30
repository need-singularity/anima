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


if __name__ == "__main__":
    test_topk_moe_forward()
    print("PASS: test_topk_moe_forward")
    test_run_comparison_mnist()
    print("PASS: test_run_comparison_mnist")
    print("All tests passed!")
