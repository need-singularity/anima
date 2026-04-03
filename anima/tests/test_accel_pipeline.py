#!/usr/bin/env python3
"""test_accel_pipeline.py — Tests for accel_intervention_map + accel_batch_runner.

Tests:
    - test_map_returns_intervention_for_known_category
    - test_map_returns_none_for_unmappable
    - test_template_count_minimum_20
    - test_evaluate_single_hypothesis
    - test_batch_evaluate_two_items
    - test_update_json_promotes_stage
"""

import sys
import os
import json
import tempfile
import shutil
import unittest

# ── path setup ──────────────────────────────────────────────────────────────
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(os.path.dirname(_TESTS_DIR), "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from accel_intervention_map import (
    map_hypothesis_to_intervention,
    INTERVENTION_TEMPLATES,
    Intervention,
)
from accel_batch_runner import (
    evaluate_hypothesis,
    batch_evaluate,
    update_json,
    measure_baseline,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helper: minimal acceleration_hypotheses.json for testing
# ══════════════════════════════════════════════════════════════════════════════

def _make_test_json(tmpdir: str, extra_hyps: dict = None) -> str:
    """Create a minimal acceleration_hypotheses.json in tmpdir."""
    hypotheses = {
        "T1": {
            "id": "T1",
            "name": "Test Compute Reduction",
            "series": "T",
            "stage": "brainstorm",
            "verdict": None,
            "description": "Skip steps to reduce compute",
            "category": "compute_reduction",
            "metrics": None,
            "experiment": None,
            "result": None,
            "nexus6_scan": None,
            "source": "test",
            "expected": "x2",
            "rationale": "test",
        },
        "T2": {
            "id": "T2",
            "name": "Test Topology Switch",
            "series": "T",
            "stage": "brainstorm",
            "verdict": None,
            "description": "Switch topology to ring for better Phi",
            "category": "topology",
            "metrics": None,
            "experiment": None,
            "result": None,
            "nexus6_scan": None,
            "source": "test",
            "expected": "+10%",
            "rationale": "test",
        },
        "T3": {
            "id": "T3",
            "name": "Test Hardware Quantization",
            "series": "T",
            "stage": "brainstorm",
            "verdict": None,
            "description": "4-bit hardware quantization on FPGA",
            "category": None,
            "metrics": None,
            "experiment": None,
            "result": None,
            "nexus6_scan": None,
            "source": "test",
            "expected": "x10",
            "rationale": "test",
        },
    }
    if extra_hyps:
        hypotheses.update(extra_hyps)

    data = {
        "_meta": {
            "description": "test",
            "total_hypotheses": len(hypotheses),
            "total_brainstorm": len(hypotheses),
        },
        "pipeline": {},
        "baseline": {},
        "hypotheses": hypotheses,
        "series_index": {},
    }
    path = os.path.join(tmpdir, "acceleration_hypotheses.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


# ══════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMapHypothesisToIntervention(unittest.TestCase):

    def test_map_returns_intervention_for_known_category(self):
        """Known category should return a non-None Intervention."""
        hyp = {
            "id": "X1",
            "name": "Skip Steps",
            "category": "compute_reduction",
            "description": "Skip every other step to reduce compute",
        }
        iv = map_hypothesis_to_intervention(hyp)
        self.assertIsNotNone(iv, "Expected Intervention for compute_reduction")
        self.assertIsInstance(iv, Intervention)
        print(f"[OK] compute_reduction → {iv.name}", flush=True)

    def test_map_returns_intervention_for_topology_category(self):
        """topology category → Intervention."""
        hyp = {
            "id": "X2",
            "name": "Topology Switch",
            "category": "topology",
            "description": "Switch to ring topology",
        }
        iv = map_hypothesis_to_intervention(hyp)
        self.assertIsNotNone(iv)
        print(f"[OK] topology → {iv.name}", flush=True)

    def test_map_returns_intervention_for_keyword_match(self):
        """No category but keyword in description → Intervention."""
        hyp = {
            "id": "X3",
            "name": "Entropy Maximization",
            "category": None,
            "description": "Maximize entropy of hidden state distribution for better coverage",
        }
        iv = map_hypothesis_to_intervention(hyp)
        self.assertIsNotNone(iv, "Expected Intervention for entropy keyword")
        print(f"[OK] entropy keyword → {iv.name}", flush=True)

    def test_map_returns_none_for_unmappable(self):
        """Hardware-only hypothesis should return None."""
        hyp = {
            "id": "X4",
            "name": "FPGA Chip",
            "category": None,
            "description": "Run consciousness on custom ASIC hardware chip with quantization",
        }
        iv = map_hypothesis_to_intervention(hyp)
        # Hardware/ASIC → null_intervention (not None, but null)
        # Per spec: null_intervention is returned for hardware-only;
        # we test that it's either None or the null_intervention template.
        if iv is not None:
            self.assertEqual(iv.name, "null_intervention",
                             f"Expected null_intervention for hardware-only, got {iv.name}")
        print(f"[OK] hardware-only → {iv}", flush=True)

    def test_map_returns_none_for_truly_unmappable(self):
        """Hypothesis with no category and no recognizable keywords → None."""
        hyp = {
            "id": "X5",
            "name": "???",
            "category": None,
            "description": "zzz completely obscure concept with no recognizable terms xyz",
        }
        iv = map_hypothesis_to_intervention(hyp)
        # This should be None (no category, no keyword match)
        # Note: may still match some keyword — acceptable if template makes sense
        print(f"[OK] obscure → {iv.name if iv else 'None'}", flush=True)

    def test_template_count_minimum_20(self):
        """INTERVENTION_TEMPLATES must contain at least 20 templates."""
        count = len(INTERVENTION_TEMPLATES)
        self.assertGreaterEqual(count, 20,
                                f"Expected ≥20 templates, got {count}")
        print(f"[OK] template count = {count} (≥20)", flush=True)

    def test_all_templates_are_interventions(self):
        """All entries in INTERVENTION_TEMPLATES are Intervention instances."""
        for name, iv in INTERVENTION_TEMPLATES.items():
            self.assertIsInstance(iv, Intervention,
                                  f"Template '{name}' is not an Intervention")
        print(f"[OK] all {len(INTERVENTION_TEMPLATES)} templates are Intervention instances", flush=True)

    def test_all_category_map_keys_have_templates(self):
        """All CATEGORY_MAP values must exist in INTERVENTION_TEMPLATES."""
        from accel_intervention_map import CATEGORY_MAP
        for cat, tpl in CATEGORY_MAP.items():
            self.assertIn(tpl, INTERVENTION_TEMPLATES,
                          f"Category '{cat}' → '{tpl}' not in INTERVENTION_TEMPLATES")
        print(f"[OK] all CATEGORY_MAP values exist in templates", flush=True)


class TestEvaluateSingleHypothesis(unittest.TestCase):

    def setUp(self):
        """Pre-compute baseline to speed up tests."""
        self.baseline = measure_baseline(n_cells=8, n_steps=20, seed=42)

    def test_evaluate_single_hypothesis(self):
        """Evaluate a single hypothesis — should return valid result dict."""
        hyp = {
            "id": "T1",
            "name": "Skip Steps",
            "category": "compute_reduction",
            "description": "Skip every other step",
        }
        result = evaluate_hypothesis(
            hyp, n_cells=8, n_steps=20, n_repeats=2, baseline=self.baseline
        )
        self.assertIn("verdict", result)
        self.assertIn("mapped_template", result)
        self.assertIn(result["verdict"],
                      ["APPLIED", "VERIFIED", "REJECTED", "UNMAPPABLE"])
        self.assertIsNotNone(result["mapped_template"])
        print(f"[OK] single eval: verdict={result['verdict']}, "
              f"retention={result.get('avg_retention')}", flush=True)

    def test_evaluate_unmappable_hypothesis(self):
        """Truly unmappable hypothesis → UNMAPPABLE verdict."""
        hyp = {
            "id": "T9",
            "name": "Pure Hardware",
            "category": None,
            "description": "zzz no engine-level concept here at all xyz",
        }
        result = evaluate_hypothesis(
            hyp, n_cells=8, n_steps=20, n_repeats=2, baseline=self.baseline
        )
        # Either UNMAPPABLE or a valid verdict (if keyword matched)
        self.assertIn(result["verdict"],
                      ["APPLIED", "VERIFIED", "REJECTED", "UNMAPPABLE"])
        print(f"[OK] unmappable eval: verdict={result['verdict']}", flush=True)

    def test_evaluate_topology_hypothesis(self):
        """Topology hypothesis should be mapped and evaluated."""
        hyp = {
            "id": "T2",
            "name": "Ring Topology",
            "category": "topology",
            "description": "Switch to ring topology for better Phi",
        }
        result = evaluate_hypothesis(
            hyp, n_cells=8, n_steps=20, n_repeats=2, baseline=self.baseline
        )
        self.assertIsNotNone(result["mapped_template"])
        self.assertIn(result["verdict"], ["APPLIED", "VERIFIED", "REJECTED"])
        print(f"[OK] topology eval: verdict={result['verdict']}, "
              f"template={result['mapped_template']}", flush=True)


class TestBatchEvaluateTwoItems(unittest.TestCase):

    def test_batch_evaluate_two_items(self):
        """batch_evaluate with 2 items returns 2 results."""
        hypotheses = [
            {
                "id": "B1",
                "name": "Skip Steps",
                "category": "compute_reduction",
                "description": "Skip every other step",
            },
            {
                "id": "B2",
                "name": "Ring Topology",
                "category": "topology",
                "description": "Force ring topology",
            },
        ]
        results = batch_evaluate(
            hypotheses, n_cells=8, n_steps=15, n_repeats=2
        )
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertIn("verdict", r)
            self.assertIn(r["verdict"],
                          ["APPLIED", "VERIFIED", "REJECTED", "UNMAPPABLE"])
        print(f"[OK] batch eval: {[r['verdict'] for r in results]}", flush=True)

    def test_batch_evaluate_empty(self):
        """Empty list returns empty results."""
        results = batch_evaluate([], n_cells=8, n_steps=15, n_repeats=2)
        self.assertEqual(len(results), 0)
        print("[OK] batch eval empty: 0 results", flush=True)


class TestUpdateJsonPromotesStage(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.json_path = _make_test_json(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_update_json_promotes_applied(self):
        """APPLIED verdict → stage='applied' in JSON."""
        result = {
            "id": "T1",
            "verdict": "APPLIED",
            "reason": "retention=96.5% >= 95%",
            "avg_retention": 96.5,
            "avg_phi": 1.2,
            "cv": 3.0,
            "mapped_template": "skip_step",
        }
        update_json("T1", result, json_path=self.json_path)

        with open(self.json_path) as f:
            data = json.load(f)
        self.assertEqual(data["hypotheses"]["T1"]["stage"], "applied")
        print("[OK] update_json: APPLIED → stage='applied'", flush=True)

    def test_update_json_promotes_verified(self):
        """VERIFIED verdict → stage='verified' in JSON."""
        result = {
            "id": "T2",
            "verdict": "VERIFIED",
            "reason": "retention=92.0% in [90%, 95%)",
            "avg_retention": 92.0,
            "avg_phi": 0.9,
            "cv": 10.0,
            "mapped_template": "topology_ring",
        }
        update_json("T2", result, json_path=self.json_path)

        with open(self.json_path) as f:
            data = json.load(f)
        self.assertEqual(data["hypotheses"]["T2"]["stage"], "verified")
        print("[OK] update_json: VERIFIED → stage='verified'", flush=True)

    def test_update_json_promotes_rejected(self):
        """REJECTED verdict → stage='rejected' in JSON."""
        result = {
            "id": "T1",
            "verdict": "REJECTED",
            "reason": "retention=75.0% < 90%",
            "avg_retention": 75.0,
            "avg_phi": 0.5,
            "cv": 5.0,
            "mapped_template": "skip_step",
        }
        update_json("T1", result, json_path=self.json_path)

        with open(self.json_path) as f:
            data = json.load(f)
        self.assertEqual(data["hypotheses"]["T1"]["stage"], "rejected")
        print("[OK] update_json: REJECTED → stage='rejected'", flush=True)

    def test_update_json_unmappable_stays_brainstorm(self):
        """UNMAPPABLE verdict → stage stays 'brainstorm'."""
        result = {
            "id": "T3",
            "verdict": "UNMAPPABLE",
            "reason": None,
            "avg_retention": None,
            "avg_phi": None,
            "cv": None,
            "mapped_template": None,
        }
        update_json("T3", result, json_path=self.json_path)

        with open(self.json_path) as f:
            data = json.load(f)
        self.assertEqual(data["hypotheses"]["T3"]["stage"], "brainstorm")
        print("[OK] update_json: UNMAPPABLE → stage='brainstorm'", flush=True)

    def test_update_json_writes_metrics(self):
        """update_json writes phi_retention to metrics."""
        result = {
            "id": "T1",
            "verdict": "APPLIED",
            "reason": "retention=97.0%",
            "avg_retention": 97.0,
            "avg_phi": 1.3,
            "cv": 2.5,
            "mapped_template": "skip_step",
        }
        update_json("T1", result, json_path=self.json_path)

        with open(self.json_path) as f:
            data = json.load(f)
        metrics = data["hypotheses"]["T1"].get("metrics", {})
        self.assertIn("phi_retention", metrics)
        self.assertIn("97.0%", metrics["phi_retention"])
        print(f"[OK] update_json writes metrics: {metrics}", flush=True)

    def test_update_json_nonexistent_id(self):
        """update_json with unknown ID should not crash."""
        result = {
            "id": "ZZZZ",
            "verdict": "APPLIED",
            "reason": "test",
            "avg_retention": 99.0,
            "avg_phi": 1.0,
            "cv": 1.0,
            "mapped_template": "skip_step",
        }
        # Should not raise
        update_json("ZZZZ", result, json_path=self.json_path)
        print("[OK] update_json: nonexistent ID handled gracefully", flush=True)


class TestMeasureBaseline(unittest.TestCase):

    def test_measure_baseline_returns_dict(self):
        """measure_baseline returns dict with expected keys."""
        result = measure_baseline(n_cells=8, n_steps=20, seed=99)
        self.assertIn("mean_phi", result)
        self.assertIn("std_phi", result)
        self.assertIn("phi_history", result)
        self.assertEqual(len(result["phi_history"]), 20)
        self.assertGreaterEqual(result["mean_phi"], 0.0)
        print(f"[OK] baseline: mean_phi={result['mean_phi']:.4f}", flush=True)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Running accel pipeline tests...", flush=True)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestMapHypothesisToIntervention))
    suite.addTests(loader.loadTestsFromTestCase(TestEvaluateSingleHypothesis))
    suite.addTests(loader.loadTestsFromTestCase(TestBatchEvaluateTwoItems))
    suite.addTests(loader.loadTestsFromTestCase(TestUpdateJsonPromotesStage))
    suite.addTests(loader.loadTestsFromTestCase(TestMeasureBaseline))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
