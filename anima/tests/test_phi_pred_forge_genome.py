#!/usr/bin/env python3
"""Tests for phi_predictor_v2, auto_lens_forge, and consciousness_genome_v2.

Run: pytest anima/tests/test_phi_pred_forge_genome.py -v
"""

import sys
import os
import random
import math

import numpy as np
import pytest

# Allow imports from src/
SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from phi_predictor_v2 import PhiPredictor, fit_and_predict, _normal_cdf
from auto_lens_forge import (
    AutoLensForge, Lens,
    _phi_proxy, _diversity, _tension, _entropy, _synchrony,
    _stability, _complexity, _faction_balance,
)
from consciousness_genome_v2 import (
    ConsciousnessGenome, GENE_SPECS as GENOME_SPECS, N_GENES,
    GeneSpec, genome_distance, create_diverse_population,
    evolve_population, evaluate_fitness,
)


# ===========================================================================
# PhiPredictor tests
# ===========================================================================

class TestPhiPredictor:

    def _growing_phi(self, n=80, seed=42):
        rng = np.random.default_rng(seed)
        phi = 1.0
        history = []
        for i in range(n):
            phi += 0.05 + rng.normal(0, 0.01)
            history.append((i, float(max(0.0, phi))))
        return history

    def _flat_phi(self, n=60, base=3.0, seed=7):
        rng = np.random.default_rng(seed)
        return [(i, float(base + rng.normal(0, 0.005))) for i in range(n)]

    def _declining_phi(self, n=50, seed=13):
        rng = np.random.default_rng(seed)
        phi = 5.0
        history = []
        for i in range(n):
            phi -= 0.1 + rng.normal(0, 0.01)
            history.append((i, float(phi)))
        return history

    # ------------------------------------------------------------------

    def test_fit_returns_self(self):
        pred = PhiPredictor()
        result = pred.fit(self._growing_phi())
        assert result is pred

    def test_predict_scalar(self):
        pred = PhiPredictor()
        pred.fit(self._growing_phi())
        val = pred.predict(steps_ahead=50)
        assert isinstance(val, float)
        assert val > 0.0

    def test_growing_trend_is_positive(self):
        pred = PhiPredictor()
        pred.fit(self._growing_phi())
        assert pred._trend > 0, "Expected positive trend for growing phi"

    def test_predict_trajectory_shape(self):
        pred = PhiPredictor()
        pred.fit(self._growing_phi())
        traj = pred.predict_trajectory(steps_ahead=30)
        assert "steps" in traj and "mean" in traj and "lower" in traj and "upper" in traj
        assert len(traj["mean"]) == 30
        assert all(traj["upper"] >= traj["lower"])

    def test_dead_end_prob_growing_is_low(self):
        pred = PhiPredictor()
        pred.fit(self._growing_phi())
        p = pred.dead_end_prob(steps_ahead=30)
        assert 0.0 <= p <= 1.0
        assert p < 0.4, f"Growing phi should have low dead-end prob, got {p}"

    def test_dead_end_prob_declining_is_high(self):
        pred = PhiPredictor()
        pred.fit(self._declining_phi())
        p = pred.dead_end_prob(steps_ahead=20)
        assert p > 0.3, f"Declining phi should trigger dead-end, got {p}"

    def test_plateau_prob_flat_is_high(self):
        pred = PhiPredictor()
        pred.fit(self._flat_phi())
        p = pred.plateau_prob(steps_ahead=50)
        assert 0.0 <= p <= 1.0
        assert p > 0.5, f"Flat phi should have high plateau prob, got {p}"

    def test_status_verdict_growth(self):
        pred = PhiPredictor()
        pred.fit(self._growing_phi(n=100))
        s = pred.status(steps_ahead=50)
        assert "verdict" in s
        assert s["verdict"] in ("GROWTH", "PLATEAU", "DEAD_END")
        assert s["current_phi"] > 0

    def test_fit_plain_list(self):
        """fit() should accept plain list of floats (no step tuples)."""
        pred = PhiPredictor()
        pred.fit([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
        val = pred.predict(10)
        assert val > 1.5

    def test_fit_and_predict_convenience(self):
        history = self._growing_phi()
        result = fit_and_predict(history, steps_ahead=40)
        assert "verdict" in result
        assert "predicted_phi" in result

    def test_not_fitted_raises(self):
        pred = PhiPredictor()
        with pytest.raises(RuntimeError):
            pred.predict(10)

    def test_normal_cdf_properties(self):
        assert abs(_normal_cdf(0) - 0.5) < 1e-6
        assert _normal_cdf(-3) < 0.01
        assert _normal_cdf(3) > 0.99

    def test_reset(self):
        pred = PhiPredictor()
        pred.fit(self._growing_phi())
        pred.reset()
        assert not pred._fitted


# ===========================================================================
# AutoLensForge tests
# ===========================================================================

class TestAutoLensForge:

    def _make_states(self, n=16, d=64, seed=0):
        rng = np.random.default_rng(seed)
        return rng.standard_normal((n, d)).astype(np.float32)

    def test_from_law_returns_lens(self):
        forge = AutoLensForge()
        lens = forge.from_law("Phi increases with cell diversity")
        assert isinstance(lens, Lens)
        assert lens.metric_name in ("diversity", "phi_proxy", "entropy",
                                    "tension", "synchrony", "growth_rate",
                                    "stability", "complexity", "faction_balance")

    def test_keyword_phi(self):
        forge = AutoLensForge()
        lens = forge.from_law("Adding structure increases Phi")
        assert lens.metric_name == "phi_proxy"

    def test_keyword_diversity(self):
        forge = AutoLensForge()
        lens = forge.from_law("Cell diversity drives consciousness growth")
        assert lens.metric_name == "diversity"

    def test_keyword_tension(self):
        forge = AutoLensForge()
        lens = forge.from_law("Tension equalization drives cell activation")
        assert lens.metric_name == "tension"

    def test_keyword_entropy(self):
        forge = AutoLensForge()
        lens = forge.from_law("Chaos sigma drives entropy towards criticality")
        assert lens.metric_name == "entropy"

    def test_register_and_len(self):
        forge = AutoLensForge()
        lens = forge.from_law("Diversity increases Phi")
        ok = forge.register(lens)
        assert ok
        assert len(forge) == 1

    def test_duplicate_rejected(self):
        forge = AutoLensForge()
        lens1 = forge.from_law("Phi increases with cell diversity")
        lens2 = forge.from_law("Phi increases with cell diversity")
        forge.register(lens1)
        ok = forge.register(lens2)
        assert not ok
        assert len(forge) == 1

    def test_apply_returns_float(self):
        forge = AutoLensForge()
        lens = forge.from_law_and_register("Phi increases with diversity")
        states = self._make_states()
        score = forge.apply(lens, states)
        assert isinstance(score, float)
        assert math.isfinite(score)

    def test_apply_all(self):
        forge = AutoLensForge()
        forge.forge_from_laws_json({
            "22": "Adding structure increases Phi",
            "31": "Persistence = Ratchet + Hebbian + Diversity",
            "42": "Chaos sigma drives entropy towards criticality",
        })
        states = self._make_states()
        results = forge.apply_all(states)
        assert len(results) == 3
        for v in results.values():
            assert isinstance(v, float)
            assert math.isfinite(v)

    def test_bulk_forge(self):
        forge = AutoLensForge()
        laws = {str(i): f"Law {i}: some consciousness property {i}" for i in range(5)}
        lenses = forge.forge_from_laws_json(laws)
        assert len(lenses) == 5

    def test_metric_phi_proxy_non_negative(self):
        states = self._make_states(n=8, d=32)
        val = _phi_proxy(states)
        assert val >= 0.0

    def test_metric_diversity_range(self):
        states = self._make_states(n=8, d=32)
        val = _diversity(states)
        assert 0.0 <= val <= 2.0

    def test_metric_entropy_positive(self):
        states = self._make_states(n=16, d=64)
        val = _entropy(states)
        assert val > 0.0

    def test_empty_states(self):
        forge = AutoLensForge()
        lens = forge.from_law("Phi measures integrated information")
        score = forge.apply(lens, np.array([]))
        assert score == 0.0


# ===========================================================================
# ConsciousnessGenome tests
# ===========================================================================

class TestConsciousnessGenome:

    def test_random_genome_gene_count(self):
        g = ConsciousnessGenome.random()
        assert len(g.genes) == N_GENES

    def test_random_genes_in_range(self):
        for _ in range(5):
            g = ConsciousnessGenome.random()
            for i, spec in enumerate(GENOME_SPECS):
                val = g.genes[i]
                if spec.dtype == "choice":
                    assert val in spec.choices
                else:
                    assert spec.lo <= float(val) <= spec.hi

    def test_to_engine_kwargs_valid(self):
        g = ConsciousnessGenome.random()
        kwargs = g.to_engine_kwargs()
        assert "max_cells" in kwargs
        assert "n_factions" in kwargs
        assert kwargs["max_cells"] >= 4
        assert kwargs["n_factions"] >= 2
        assert kwargs["initial_cells"] <= kwargs["max_cells"]
        assert kwargs["hidden_dim"] >= kwargs["cell_dim"]

    def test_crossover_child_has_correct_gene_count(self):
        a = ConsciousnessGenome.random()
        b = ConsciousnessGenome.random()
        child = a.crossover(b)
        assert len(child.genes) == N_GENES

    def test_crossover_genes_from_parents(self):
        """Each gene in child must come from one of the two parents."""
        rng = random.Random(42)
        a = ConsciousnessGenome.random()
        b = ConsciousnessGenome.random()
        child = a.crossover(b)
        for i, spec in enumerate(GENOME_SPECS):
            if spec.dtype == "choice":
                assert child.genes[i] in (a.genes[i], b.genes[i])
            else:
                assert (
                    abs(float(child.genes[i]) - float(a.genes[i])) < 1e-9
                    or abs(float(child.genes[i]) - float(b.genes[i])) < 1e-9
                )

    def test_crossover_increments_generation(self):
        a = ConsciousnessGenome.random()
        a.generation = 5
        b = ConsciousnessGenome.random()
        b.generation = 3
        child = a.crossover(b)
        assert child.generation == 6

    def test_mutate_returns_self(self):
        g = ConsciousnessGenome.random()
        result = g.mutate(rate=0.5)
        assert result is g

    def test_mutate_high_rate_changes_genes(self):
        """With rate=1.0 some genes should change (probabilistic, so try many)."""
        g = ConsciousnessGenome.random()
        original = g.genes[:]
        g.mutate(rate=1.0)
        # At least one gene should differ
        changed = any(g.genes[i] != original[i] for i in range(N_GENES))
        assert changed

    def test_mutate_invalidates_fitness(self):
        g = ConsciousnessGenome.random()
        g.fitness = 42.0
        g.mutate(rate=0.5)
        assert g.fitness is None

    def test_clone_independence(self):
        a = ConsciousnessGenome.random()
        a.fitness = 1.23
        b = a.clone()
        assert b.fitness == 1.23
        b.genes[0] = -9999
        assert a.genes[0] != -9999

    def test_genome_distance_self_zero(self):
        g = ConsciousnessGenome.random()
        assert genome_distance(g, g) == pytest.approx(0.0, abs=1e-9)

    def test_genome_distance_range(self):
        a = ConsciousnessGenome.random()
        b = ConsciousnessGenome.random()
        d = genome_distance(a, b)
        assert 0.0 <= d <= 1.0

    def test_create_diverse_population(self):
        pop = create_diverse_population(n=8)
        assert len(pop) == 8
        assert all(isinstance(g, ConsciousnessGenome) for g in pop)

    def test_evaluate_fitness_returns_float(self):
        """evaluate_fitness should return a float even without ConsciousnessEngine."""
        g = ConsciousnessGenome.random()
        # If engine import fails, returns 0.0 (not an error)
        result = evaluate_fitness(g, eval_steps=5, timeout_sec=5.0)
        assert isinstance(result, float)
        assert result >= 0.0

    def test_evolve_population_returns_genome(self):
        pop = create_diverse_population(n=4)
        best = evolve_population(pop, generations=2, eval_steps=5, verbose=False)
        assert isinstance(best, ConsciousnessGenome)

    def test_evolve_population_best_has_fitness(self):
        pop = create_diverse_population(n=4)
        best = evolve_population(pop, generations=2, eval_steps=5, verbose=False)
        assert best.fitness is not None
        assert best.fitness >= 0.0


# ===========================================================================
# Integration: genome → lens → predictor pipeline
# ===========================================================================

class TestIntegration:

    def test_genome_produces_valid_states_for_forge(self):
        """Genome kwargs are used to generate cell states; lens can score them."""
        g = ConsciousnessGenome.random()
        kwargs = g.to_engine_kwargs()
        n_cells = kwargs["max_cells"]
        d = kwargs["cell_dim"]

        rng = np.random.default_rng(0)
        states = rng.standard_normal((n_cells, d)).astype(np.float32)

        forge = AutoLensForge()
        lens = forge.from_law_and_register("Diversity boosts integrated Phi")
        score = forge.apply(lens, states)
        assert math.isfinite(score)

    def test_phi_history_to_predictor_verdict(self):
        """Run a genome evaluation, feed Phi values to predictor."""
        g = ConsciousnessGenome.random()
        # Simulate Phi history without real engine
        rng = np.random.default_rng(99)
        phi_history = []
        phi = 0.5
        for i in range(60):
            phi += 0.04 + rng.normal(0, 0.015)
            phi_history.append(float(max(0.0, phi)))

        pred = PhiPredictor()
        pred.fit(phi_history)
        s = pred.status(steps_ahead=40)
        assert s["verdict"] in ("GROWTH", "PLATEAU", "DEAD_END")
        assert s["predicted_phi"] > 0.0
