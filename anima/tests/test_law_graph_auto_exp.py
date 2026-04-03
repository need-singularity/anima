#!/usr/bin/env python3
"""Tests for law_interaction_graph.py and auto_experiment.py.

Tests cover:
  - LawInteractionGraph: pair priority, test_pair, synergy detection,
    adjacency matrix, report, save/load, SYNERGY_MAP export
  - AutoExperiment: design_and_run, run_batch, verdict logic,
    auto-register, report, save_history
"""

import os
import sys
import json
import tempfile

import torch
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ══════════════════════════════════════════
# Shared fixtures
# ══════════════════════════════════════════

@pytest.fixture
def minimal_laws_json(tmp_path):
    """Create a minimal consciousness_laws.json for testing."""
    data = {
        "_meta": {"total_laws": 4, "version": "test"},
        "laws": {
            "22": "Adding features -> Phi down; adding structure -> Phi up",
            "108": "Coupling symmetry positively correlates with Phi: bidirectional flow",
            "124": "Tension equalization boosts Phi +12.3%",
            "126": "1/f pink noise injection boosts Phi +2.9%",
        }
    }
    p = tmp_path / "consciousness_laws.json"
    p.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return str(p)


# ══════════════════════════════════════════
# law_interaction_graph tests
# ══════════════════════════════════════════

class TestPairPriority:
    """Tests for _pair_priority helper."""

    def test_same_family_higher_than_different(self):
        from law_interaction_graph import _pair_priority
        # Both have 'tension' keyword — same family
        score_same = _pair_priority(
            "Tension equalization boosts Phi",
            "Tension balance homeostasis threshold",
        )
        # Different keywords
        score_diff = _pair_priority(
            "Tension equalization boosts Phi",
            "Ratchet protects consciousness peaks",
        )
        assert score_same > score_diff

    def test_non_actionable_zero(self):
        from law_interaction_graph import _pair_priority
        score = _pair_priority("Abstract philosophy text", "Random words here")
        assert score == 0.0

    def test_shared_keyword_boosts_score(self):
        from law_interaction_graph import _pair_priority
        score_shared = _pair_priority(
            "diversity increases Phi substantially",
            "faction diversity maintains Phi",
        )
        score_none = _pair_priority(
            "diversity increases Phi",
            "ratchet protects peaks",
        )
        assert score_shared >= score_none


class TestLawFamily:
    def test_coupling_family(self):
        from law_interaction_graph import _law_family
        assert _law_family("coupling symmetry bidirectional flow") == 'coupling'

    def test_noise_family(self):
        from law_interaction_graph import _law_family
        assert _law_family("1/f pink noise injection boosts Phi") == 'noise'

    def test_tension_family(self):
        from law_interaction_graph import _law_family
        assert _law_family("tension equalization homeostasis balance") == 'tension'

    def test_unknown_family(self):
        from law_interaction_graph import _law_family
        assert _law_family("completely unrelated abstract text") is None


class TestLawInteractionGraph:
    def test_init_loads_laws(self, minimal_laws_json):
        from law_interaction_graph import LawInteractionGraph
        lig = LawInteractionGraph(laws_path=minimal_laws_json)
        assert len(lig._laws) == 4
        assert 22 in lig._laws
        assert 124 in lig._laws

    def test_rank_pairs_returns_list(self, minimal_laws_json):
        from law_interaction_graph import LawInteractionGraph
        lig = LawInteractionGraph(laws_path=minimal_laws_json, steps=20, reps=1)
        pairs = lig._rank_pairs(10)
        assert isinstance(pairs, list)
        # All pairs should be (int, int) tuples
        for a, b in pairs:
            assert isinstance(a, int)
            assert isinstance(b, int)
            assert a != b

    def test_test_pair_no_intervention_returns_none(self, minimal_laws_json):
        """Law 22 has no direct actionable template → may return None."""
        from law_interaction_graph import LawInteractionGraph
        lig = LawInteractionGraph(laws_path=minimal_laws_json, steps=20, reps=1)
        # Law 22 text: "Adding features..." — no template keyword match
        # This should return None gracefully
        result = lig.test_pair(22, 22)
        # Either None (no intervention) or a valid PairResult — both acceptable
        assert result is None or hasattr(result, 'verdict')

    def test_test_pair_cached(self, minimal_laws_json):
        """Same pair tested twice should return cached result."""
        from law_interaction_graph import LawInteractionGraph
        lig = LawInteractionGraph(laws_path=minimal_laws_json, steps=15, reps=1)
        # Inject a manual result into cache to test caching logic
        from law_interaction_graph import PairResult
        dummy = PairResult(
            law_a=124, law_b=126,
            law_a_text="tension eq",
            law_b_text="pink noise",
            phi_baseline=0.5, phi_a_only=0.6, phi_b_only=0.55,
            phi_both=0.75, phi_expected_additive=0.65,
            synergy_score=0.10, synergy_pct=15.3,
            verdict="SYNERGY", time_sec=1.0,
        )
        lig._results[(124, 126)] = dummy
        result2 = lig.test_pair(124, 126)
        assert result2 is dummy  # Returned from cache

    def test_synergy_detection(self, minimal_laws_json):
        """Verify synergy is detected when phi_both > expected."""
        from law_interaction_graph import LawInteractionGraph, PairResult
        lig = LawInteractionGraph(laws_path=minimal_laws_json, steps=20, reps=1)
        # Inject synthetic SYNERGY result
        r = PairResult(
            law_a=124, law_b=126,
            law_a_text="a", law_b_text="b",
            phi_baseline=0.5, phi_a_only=0.7, phi_b_only=0.6,
            phi_both=0.9,     # > expected 0.8
            phi_expected_additive=0.8,
            synergy_score=0.10, synergy_pct=12.5,
            verdict="SYNERGY", time_sec=0.5,
        )
        lig._results[(124, 126)] = r
        synergies = lig.get_synergies()
        assert len(synergies) == 1
        assert synergies[0].law_a == 124

    def test_antagonism_detection(self, minimal_laws_json):
        """Verify antagonism is detected when phi_both < expected."""
        from law_interaction_graph import LawInteractionGraph, PairResult
        lig = LawInteractionGraph(laws_path=minimal_laws_json, steps=20, reps=1)
        r = PairResult(
            law_a=108, law_b=124,
            law_a_text="coupling sym", law_b_text="tension eq",
            phi_baseline=0.5, phi_a_only=0.7, phi_b_only=0.6,
            phi_both=0.4,  # < expected 0.8
            phi_expected_additive=0.8,
            synergy_score=-0.4, synergy_pct=-50.0,
            verdict="ANTAGONISM", time_sec=0.5,
        )
        lig._results[(108, 124)] = r
        antagonisms = lig.get_antagonisms()
        assert len(antagonisms) == 1
        assert antagonisms[0].verdict == "ANTAGONISM"

    def test_adjacency_matrix_shape(self, minimal_laws_json):
        """Adjacency matrix should be (n_laws_tested, n_laws_tested) and symmetric."""
        from law_interaction_graph import LawInteractionGraph, PairResult
        lig = LawInteractionGraph(laws_path=minimal_laws_json, steps=20, reps=1)
        # Add two pairs
        for (a, b, score) in [(124, 126, 0.1), (108, 124, -0.2)]:
            r = PairResult(
                law_a=a, law_b=b,
                law_a_text="a", law_b_text="b",
                phi_baseline=0.5, phi_a_only=0.6, phi_b_only=0.55,
                phi_both=0.5 + score, phi_expected_additive=0.65,
                synergy_score=score, synergy_pct=score * 100,
                verdict="SYNERGY" if score > 0 else "ANTAGONISM",
                time_sec=0.1,
            )
            lig._results[(min(a, b), max(a, b))] = r

        ids, mat = lig.get_adjacency_matrix()
        assert len(ids) == 3  # 124, 126, 108 unique
        assert mat.shape == (3, 3)
        # Symmetric
        np.testing.assert_array_almost_equal(mat, mat.T)
        # Diagonal should be 0
        np.testing.assert_array_equal(np.diag(mat), np.zeros(3))

    def test_report_runs_without_error(self, minimal_laws_json):
        from law_interaction_graph import LawInteractionGraph
        lig = LawInteractionGraph(laws_path=minimal_laws_json, steps=20, reps=1)
        text = lig.report()
        assert "Law Interaction Graph Report" in text
        assert "Total pairs tested: 0" in text

    def test_save_and_load(self, minimal_laws_json, tmp_path):
        from law_interaction_graph import LawInteractionGraph, PairResult
        lig = LawInteractionGraph(laws_path=minimal_laws_json, steps=20, reps=1)
        # Add a result
        r = PairResult(
            law_a=124, law_b=126,
            law_a_text="tension", law_b_text="noise",
            phi_baseline=0.5, phi_a_only=0.6, phi_b_only=0.55,
            phi_both=0.75, phi_expected_additive=0.65,
            synergy_score=0.10, synergy_pct=15.4,
            verdict="SYNERGY", time_sec=1.2,
        )
        lig._results[(124, 126)] = r

        save_path = str(tmp_path / "test_lig.json")
        lig.save(save_path)

        lig2 = LawInteractionGraph(laws_path=minimal_laws_json, steps=20, reps=1)
        lig2.load(save_path)
        assert (124, 126) in lig2._results
        loaded = lig2._results[(124, 126)]
        assert loaded.verdict == "SYNERGY"
        assert abs(loaded.synergy_score - 0.10) < 1e-5

    def test_to_closed_loop_synergy_map_format(self, minimal_laws_json):
        """Export format should be dict with (str, str) -> float."""
        from law_interaction_graph import LawInteractionGraph, PairResult
        lig = LawInteractionGraph(laws_path=minimal_laws_json, steps=20, reps=1)
        # Inject result with significant synergy
        r = PairResult(
            law_a=124, law_b=126,
            law_a_text="tension eq", law_b_text="1/f noise",
            phi_baseline=0.5, phi_a_only=0.6, phi_b_only=0.55,
            phi_both=0.75, phi_expected_additive=0.65,
            synergy_score=0.10, synergy_pct=15.4,
            verdict="SYNERGY", time_sec=0.5,
        )
        lig._results[(124, 126)] = r
        cm = lig.to_closed_loop_synergy_map()
        # Should be dict, values are floats
        assert isinstance(cm, dict)
        for key, val in cm.items():
            assert isinstance(key, tuple) and len(key) == 2
            assert isinstance(val, float)


# ══════════════════════════════════════════
# auto_experiment tests
# ══════════════════════════════════════════

class TestVerdictLogic:
    """Tests for the _compute_verdict function (unit tests)."""

    def _make_reps(self, deltas):
        from auto_experiment import RepResult
        return [
            RepResult(
                rep=i,
                phi_baseline=0.5,
                phi_with_intervention=0.5 + d / 100.0,
                phi_retention_pct=100 + d,
                phi_delta_pct=d,
                ce_baseline=1.0,
                ce_with_intervention=1.0,
            )
            for i, d in enumerate(deltas)
        ]

    def test_verified_all_positive(self):
        from auto_experiment import _compute_verdict
        reps = self._make_reps([10.0, 12.0, 11.0])
        verdict, reason = _compute_verdict(reps)
        assert verdict == "VERIFIED"

    def test_rejected_all_negative(self):
        from auto_experiment import _compute_verdict
        reps = self._make_reps([-15.0, -12.0, -10.0])
        verdict, reason = _compute_verdict(reps)
        assert verdict == "REJECTED"

    def test_inconclusive_mixed_direction(self):
        from auto_experiment import _compute_verdict
        reps = self._make_reps([10.0, -5.0, 8.0])
        verdict, reason = _compute_verdict(reps)
        assert verdict == "INCONCLUSIVE"
        assert "inconsistent" in reason.lower()

    def test_inconclusive_high_cv(self):
        """All positive but huge variance → inconclusive."""
        from auto_experiment import _compute_verdict
        reps = self._make_reps([1.0, 50.0, 2.0])
        verdict, reason = _compute_verdict(reps)
        # CV should be huge here
        assert verdict == "INCONCLUSIVE"

    def test_inconclusive_effect_too_small(self):
        """All positive but below threshold."""
        from auto_experiment import _compute_verdict
        reps = self._make_reps([1.0, 1.2, 0.8])  # ~1% well below 5% threshold
        verdict, reason = _compute_verdict(reps)
        assert verdict == "INCONCLUSIVE"

    def test_empty_reps_inconclusive(self):
        from auto_experiment import _compute_verdict
        verdict, reason = _compute_verdict([])
        assert verdict == "INCONCLUSIVE"


class TestAutoExperiment:
    def test_init(self, minimal_laws_json):
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(laws_path=minimal_laws_json, steps=20, reps=1, auto_register=False)
        assert ae.steps == 20
        assert ae.reps == 1
        assert len(ae._laws) == 4

    def test_design_no_intervention(self, minimal_laws_json):
        """Hypothesis with no matching template → NO_INTERVENTION."""
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(laws_path=minimal_laws_json, steps=20, reps=1, auto_register=False)
        result = ae.design_and_run(
            "Abstract philosophical concept with no actionable mechanism",
            verbose=False,
        )
        assert result.verdict == "NO_INTERVENTION"
        assert result.intervention_name is None
        assert len(result.reps) == 0

    def test_design_tension_hypothesis_runs(self, minimal_laws_json):
        """Tension hypothesis should generate an intervention and run reps."""
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(laws_path=minimal_laws_json, steps=20, reps=2, auto_register=False)
        result = ae.design_and_run(
            "Tension equalization boosts Phi +12% via homeostasis",
            verbose=False,
        )
        assert result.intervention_name is not None
        assert result.template == 'tension'
        assert len(result.reps) == 2
        assert result.verdict in {"VERIFIED", "REJECTED", "INCONCLUSIVE"}

    def test_rep_result_structure(self, minimal_laws_json):
        """Each RepResult should have required fields."""
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(laws_path=minimal_laws_json, steps=15, reps=2, auto_register=False)
        result = ae.design_and_run(
            "Tension equalization boosts Phi",
            verbose=False,
        )
        if result.reps:
            for rep in result.reps:
                assert hasattr(rep, 'phi_baseline')
                assert hasattr(rep, 'phi_with_intervention')
                assert hasattr(rep, 'phi_delta_pct')
                assert rep.phi_baseline >= 0.0
                assert rep.phi_with_intervention >= 0.0

    def test_run_batch(self, minimal_laws_json):
        """run_batch returns one result per hypothesis."""
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(laws_path=minimal_laws_json, steps=15, reps=1, auto_register=False)
        hypotheses = [
            "Tension equalization boosts Phi",
            "Abstract concept with no keyword",
        ]
        results = ae.run_batch(hypotheses, verbose=False)
        assert len(results) == 2
        assert results[0].verdict in {"VERIFIED", "REJECTED", "INCONCLUSIVE"}
        assert results[1].verdict == "NO_INTERVENTION"

    def test_auto_register_writes_json(self, minimal_laws_json):
        """Verified experiment with auto_register=True should update JSON."""
        from auto_experiment import AutoExperiment, RepResult, ExperimentResult

        ae = AutoExperiment(
            laws_path=minimal_laws_json,
            steps=15, reps=1,
            auto_register=True,
        )
        # Directly call _auto_register_law to test registration
        new_id = ae._auto_register_law("Test law: tension boosts Phi (AutoExperiment)")
        assert new_id is not None
        assert isinstance(new_id, int)
        assert new_id > 0

        # Verify it was written to JSON
        with open(minimal_laws_json, 'r') as f:
            data = json.load(f)
        assert str(new_id) in data['laws']
        assert data['_meta']['total_laws'] == 5  # was 4, now 5

    def test_no_duplicate_registration(self, minimal_laws_json):
        """Two registrations should get different law ids."""
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(laws_path=minimal_laws_json, auto_register=True)
        id1 = ae._auto_register_law("First test law")
        id2 = ae._auto_register_law("Second test law")
        assert id1 != id2
        assert id2 > id1

    def test_report_runs_without_error(self, minimal_laws_json):
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(laws_path=minimal_laws_json, steps=15, reps=1, auto_register=False)
        ae.design_and_run("Tension equalization boosts Phi", verbose=False)
        text = ae.report()
        assert "AutoExperiment Report" in text
        assert "Total experiments: 1" in text

    def test_save_history(self, minimal_laws_json, tmp_path):
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(laws_path=minimal_laws_json, steps=15, reps=1, auto_register=False)
        ae.design_and_run("Tension equalization boosts Phi", verbose=False)

        save_path = str(tmp_path / "history.json")
        ae.save_history(save_path)

        with open(save_path, 'r') as f:
            data = json.load(f)
        assert "history" in data
        assert len(data["history"]) == 1
        record = data["history"][0]
        assert "hypothesis" in record
        assert "verdict" in record
        assert "reps" in record

    def test_history_accumulates(self, minimal_laws_json):
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(laws_path=minimal_laws_json, steps=15, reps=1, auto_register=False)
        ae.design_and_run("Tension equalization boosts Phi", verbose=False)
        ae.design_and_run("Abstract with no keyword", verbose=False)
        assert len(ae.history) == 2

    def test_verified_property(self, minimal_laws_json):
        """ExperimentResult.verified should be True only for VERIFIED verdict."""
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(laws_path=minimal_laws_json, steps=15, reps=1, auto_register=False)
        result = ae.design_and_run("Abstract no keyword", verbose=False)
        assert result.verdict == "NO_INTERVENTION"
        assert not result.verified


# ══════════════════════════════════════════
# Integration: graph → auto_experiment pipeline
# ══════════════════════════════════════════

class TestGraphAutoExpIntegration:
    def test_graph_results_usable_as_hypotheses(self, minimal_laws_json):
        """Top synergy pairs from graph can be passed as hypotheses to AutoExperiment."""
        from law_interaction_graph import LawInteractionGraph, PairResult
        from auto_experiment import AutoExperiment

        lig = LawInteractionGraph(laws_path=minimal_laws_json, steps=20, reps=1)
        # Inject a synergy result
        r = PairResult(
            law_a=124, law_b=126,
            law_a_text="Tension equalization boosts Phi +12.3%",
            law_b_text="1/f pink noise injection boosts Phi +2.9%",
            phi_baseline=0.5, phi_a_only=0.6, phi_b_only=0.55,
            phi_both=0.75, phi_expected_additive=0.65,
            synergy_score=0.10, synergy_pct=15.4,
            verdict="SYNERGY", time_sec=0.5,
        )
        lig._results[(124, 126)] = r
        synergies = lig.get_synergies()
        assert len(synergies) == 1

        # Use top synergy's law text as hypothesis
        hyp = f"{synergies[0].law_a_text} combined with {synergies[0].law_b_text}"
        ae = AutoExperiment(laws_path=minimal_laws_json, steps=15, reps=1, auto_register=False)
        result = ae.design_and_run(hyp, verbose=False)
        # Should attempt to run (may or may not find a template)
        assert result.verdict in {
            "VERIFIED", "REJECTED", "INCONCLUSIVE", "NO_INTERVENTION"
        }
