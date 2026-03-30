"""Tests for bench_animalm.py — AnimaLM benchmark wrapper."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import pytest


def test_animalm_bench_result_creation():
    """AnimaLMBenchResult has extended fields and summary() includes them."""
    from bench_animalm import AnimaLMBenchResult

    r = AnimaLMBenchResult(
        name="test-alpha-0.3",
        phi_iit=1.2,
        phi_proxy=45.6,
        ce_start=3.0,
        ce_end=1.5,
        cells=64,
        steps=1000,
        time_sec=12.3,
        alpha=0.3,
        v_conditions={"talk5": True, "transplant": False},
        c_meter_level=4,
        consciousness_vector={"phi": 1.2, "alpha": 0.3, "Z": 0.5, "N": 0.4,
                               "W": 0.6, "E": 0.3, "M": 0.7, "C": 0.8,
                               "T": 0.2, "I": 0.9},
    )

    # Check extended fields
    assert r.alpha == 0.3
    assert r.v_conditions["talk5"] is True
    assert r.c_meter_level == 4
    assert len(r.consciousness_vector) == 10

    # summary() should include base info + alpha/V-condition
    s = r.summary()
    assert "test-alpha-0.3" in s
    assert "alpha=0.3" in s or "0.3" in s
    assert "Phi(IIT)" in s


def test_measure_phi_dual():
    """measure_phi returns (phi_iit, phi_proxy) both floats >= 0."""
    from bench_animalm import measure_phi

    hiddens = torch.randn(16, 64)
    phi_iit, phi_proxy = measure_phi(hiddens, n_factions=4)

    assert isinstance(phi_iit, float)
    assert isinstance(phi_proxy, float)
    assert phi_iit >= 0.0
    assert phi_proxy >= 0.0


def test_consciousness_vector_10d():
    """measure_consciousness_vector returns 10-key dict with correct values."""
    from bench_animalm import measure_consciousness_vector

    vec = measure_consciousness_vector(phi=1.5, alpha=0.1)

    expected_keys = {"phi", "alpha", "Z", "N", "W", "E", "M", "C", "T", "I"}
    assert set(vec.keys()) == expected_keys
    assert vec["phi"] == 1.5
    assert vec["alpha"] == 0.1
    # All values should be numeric
    for k, v in vec.items():
        assert isinstance(v, (int, float)), f"{k} is not numeric: {type(v)}"


def test_alpha_sweep_engine():
    """AlphaSweepEngine runs all alpha stages and returns correct structure."""
    from bench_animalm import AlphaSweepEngine

    engine = AlphaSweepEngine(
        n_cells=4,
        input_dim=32,
        hidden_dim=64,
        output_dim=32,
        alpha_stages=[0.0001, 0.001, 0.01, 0.1],
        steps_per_stage=50,
    )
    results = engine.run()

    # One result per alpha stage
    assert len(results) == 4

    # Each result has required keys
    for r in results:
        assert "alpha" in r
        assert "phi_iit" in r
        assert "phi_proxy" in r
        assert isinstance(r["phi_iit"], float)
        assert isinstance(r["phi_proxy"], float)

    # Alpha values are in ascending order
    assert results[-1]["alpha"] > results[0]["alpha"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
