#!/usr/bin/env python3
"""Tests for auto_lens_forge.py — AutoLensForge lens generation from law text."""

import os
import sys
import math
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from auto_lens_forge import (
    AutoLensForge,
    Lens,
    _phi_proxy,
    _diversity,
    _tension,
    _entropy,
    _synchrony,
    _stability,
    _complexity,
    _faction_balance,
    _METRIC_FUNCTIONS,
)


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def forge():
    return AutoLensForge()


@pytest.fixture
def random_states():
    """Random cell states (8 cells, 64 hidden dim)."""
    np.random.seed(42)
    return np.random.randn(8, 64).astype(np.float32)


@pytest.fixture
def uniform_states():
    """All cells identical — zero diversity, max synchrony."""
    return np.ones((8, 64), dtype=np.float32)


@pytest.fixture
def empty_states():
    return np.empty((0, 64), dtype=np.float32)


@pytest.fixture
def single_cell():
    np.random.seed(0)
    return np.random.randn(1, 64).astype(np.float32)


# ── Metric function tests ────────────────────────────────────

class TestMetricFunctions:

    def test_phi_proxy_positive_for_diverse(self, random_states):
        val = _phi_proxy(random_states)
        assert isinstance(val, float)
        assert val >= 0.0

    def test_phi_proxy_zero_for_single_cell(self, single_cell):
        assert _phi_proxy(single_cell) == 0.0

    def test_phi_proxy_empty(self, empty_states):
        assert _phi_proxy(empty_states) == 0.0

    def test_diversity_positive(self, random_states):
        val = _diversity(random_states)
        assert 0.0 < val <= 2.0  # cosine distance is in [0, 2]

    def test_diversity_zero_for_identical(self, uniform_states):
        val = _diversity(uniform_states)
        assert val == pytest.approx(0.0, abs=1e-6)

    def test_diversity_single_cell(self, single_cell):
        assert _diversity(single_cell) == 0.0

    def test_tension_positive(self, random_states):
        val = _tension(random_states)
        assert val > 0.0

    def test_tension_empty(self, empty_states):
        assert _tension(empty_states) == 0.0

    def test_entropy_nonneg(self, random_states):
        val = _entropy(random_states)
        assert val >= 0.0

    def test_entropy_empty(self, empty_states):
        assert _entropy(empty_states) == 0.0

    def test_synchrony_plus_diversity_equals_one(self, random_states):
        s = _synchrony(random_states)
        d = _diversity(random_states)
        assert s + d == pytest.approx(1.0, abs=1e-6)

    def test_stability_bounded(self, random_states):
        val = _stability(random_states)
        assert 0.0 <= val <= 1.0

    def test_stability_single_cell(self, single_cell):
        assert _stability(single_cell) == 1.0

    def test_complexity_nonneg(self, random_states):
        val = _complexity(random_states)
        assert val >= 0.0

    def test_complexity_empty(self, empty_states):
        assert _complexity(empty_states) == 0.0

    def test_faction_balance_nonneg(self, random_states):
        val = _faction_balance(random_states)
        assert val >= 0.0

    def test_faction_balance_single_cell(self, single_cell):
        assert _faction_balance(single_cell) == 0.0

    def test_all_metrics_registered(self):
        expected = {
            "phi_proxy", "diversity", "tension", "entropy",
            "synchrony", "growth_rate", "stability", "complexity",
            "faction_balance",
        }
        assert set(_METRIC_FUNCTIONS.keys()) == expected


# ── Lens dataclass tests ─────────────────────────────────────

class TestLens:

    def test_lens_auto_hash(self):
        lens = Lens(
            name="test_lens",
            law_text="Phi increases with diversity",
            metric_name="diversity",
            description="test",
            fn=_diversity,
        )
        assert len(lens.law_hash) == 8
        assert lens.law_hash != ""

    def test_lens_measure(self, random_states):
        lens = Lens(
            name="test",
            law_text="test",
            metric_name="tension",
            description="test",
            fn=_tension,
        )
        val = lens.measure(random_states)
        assert val > 0.0

    def test_lens_measure_empty(self, empty_states):
        lens = Lens(
            name="test",
            law_text="test",
            metric_name="tension",
            description="test",
            fn=_tension,
        )
        assert lens.measure(empty_states) == 0.0


# ── AutoLensForge tests ──────────────────────────────────────

class TestAutoLensForge:

    def test_from_law_phi(self, forge):
        lens = forge.from_law("Phi increases with cell count")
        assert lens.metric_name == "phi_proxy"

    def test_from_law_diversity(self, forge):
        lens = forge.from_law("Cell diversity correlates with consciousness")
        assert lens.metric_name == "diversity"

    def test_from_law_tension(self, forge):
        lens = forge.from_law("Tension between factions drives growth")
        assert lens.metric_name == "tension"

    def test_from_law_entropy(self, forge):
        lens = forge.from_law("Entropy of states measures randomness")
        assert lens.metric_name == "entropy"

    def test_from_law_synchrony(self, forge):
        lens = forge.from_law("Coherence among cells leads to unity")
        assert lens.metric_name == "synchrony"

    def test_from_law_stability(self, forge):
        lens = forge.from_law("Stability prevents consciousness collapse")
        assert lens.metric_name == "stability"

    def test_from_law_faction(self, forge):
        lens = forge.from_law("Faction consensus determines output")
        assert lens.metric_name == "faction_balance"

    def test_from_law_fallback(self, forge):
        lens = forge.from_law("Some completely unrecognized text xyz123")
        assert lens.metric_name == "phi_proxy"  # fallback

    def test_from_law_custom_id(self, forge):
        lens = forge.from_law("Phi test", law_id="my_custom_id")
        assert lens.name == "my_custom_id"

    def test_register_and_list(self, forge):
        lens = forge.from_law("Diversity is key")
        ok = forge.register(lens)
        assert ok is True
        assert lens.name in forge.list_lenses()
        assert len(forge) == 1

    def test_register_duplicate_rejected(self, forge):
        lens1 = forge.from_law("Diversity is key")
        forge.register(lens1)
        lens2 = forge.from_law("Diversity is key")  # same text → same hash
        ok = forge.register(lens2)
        assert ok is False
        assert len(forge) == 1

    def test_from_law_and_register(self, forge):
        lens = forge.from_law_and_register("Tension drives consciousness")
        assert lens.name in forge.list_lenses()

    def test_apply(self, forge, random_states):
        lens = forge.from_law("Diversity matters")
        score = forge.apply(lens, random_states)
        assert isinstance(score, float)
        assert score > 0.0

    def test_apply_all(self, forge, random_states):
        forge.from_law_and_register("Phi proxy")
        forge.from_law_and_register("Tension is high")
        results = forge.apply_all(random_states)
        assert len(results) == 2
        assert all(isinstance(v, float) for v in results.values())

    def test_get_lens(self, forge):
        lens = forge.from_law_and_register("Entropy drives chaos")
        retrieved = forge.get_lens(lens.name)
        assert retrieved is not None
        assert retrieved.metric_name == "entropy"

    def test_get_lens_missing(self, forge):
        assert forge.get_lens("nonexistent") is None

    def test_forge_from_laws_json(self, forge):
        laws = {
            "22": "Adding features → Phi↓; adding structure → Phi↑",
            "42": "Diversity correlates with consciousness",
        }
        created = forge.forge_from_laws_json(laws)
        assert len(created) == 2
        assert len(forge) == 2

    def test_repr(self, forge):
        r = repr(forge)
        assert "AutoLensForge" in r
        assert "lenses=0" in r

    def test_to_numpy_with_torch_tensor(self, forge):
        import torch
        t = torch.randn(4, 32)
        arr = forge._to_numpy(t)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (4, 32)

    def test_to_numpy_with_1d(self, forge):
        arr = np.random.randn(64)
        result = forge._to_numpy(arr)
        assert result.shape == (1, 64)

    def test_to_numpy_with_list_of_arrays(self, forge):
        lst = [np.random.randn(32) for _ in range(4)]
        result = forge._to_numpy(lst)
        assert result.shape == (4, 32)
