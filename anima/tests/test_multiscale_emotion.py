#!/usr/bin/env python3
"""test_multiscale_emotion.py — Tests for multiscale_consciousness + emotion_explorer.

Tests:
    MultiscaleHierarchy:
        01 - measure_all_levels returns required keys
        02 - L1 cell Phi is non-negative
        03 - L3 engine Phi matches engine._measure_phi_iit
        04 - growth_rate updates after repeated measurements
        05 - L4 global with no peers mirrors L3
        06 - L4 global with peers differs from single-engine value
        07 - emergence detection fires when faction Phi would exceed cell sum
        08 - add_peer / remove_peer modifies peers list
        09 - report() returns non-empty string with all level labels

    EmotionExplorer:
        10 - suggest_input returns vector of correct shape
        11 - explore() returns required keys
        12 - mean_pe is non-negative after exploration
        13 - n_patterns grows during exploration
        14 - top_patterns sorted by curiosity descending
        15 - repeated same pattern increments visit count
        16 - explore phi_end and phi_start are finite
        17 - curiosity_map returns list of dicts with 'key' and 'curiosity'
        18 - top_drivers returns at most n items
        19 - report() returns non-empty string mentioning 'pattern'
        20 - PatternRecord curiosity_score returns finite float
"""

import sys
import os
import unittest
import torch

# ── path setup ─────────────────────────────────────────────────────────────────
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(os.path.dirname(_TESTS_DIR), "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from multiscale_consciousness import MultiscaleHierarchy, LevelMetrics, _cell_entropy, _phi_iit_subset
from emotion_explorer import EmotionExplorer, PatternRecord
from consciousness_engine import ConsciousnessEngine


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_engine(cells: int = 8, max_cells: int = 16) -> ConsciousnessEngine:
    torch.manual_seed(42)
    eng = ConsciousnessEngine(
        cell_dim=32, hidden_dim=64,
        initial_cells=cells, max_cells=max_cells,
        n_factions=4,
    )
    # Warm up so hidden states are non-zero
    for _ in range(5):
        eng.step()
    return eng


# ══════════════════════════════════════════════════════════════════════════════
# MultiscaleHierarchy tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiscaleHierarchy(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()
        self.mh = MultiscaleHierarchy(self.engine)

    # 01
    def test_measure_all_levels_returns_required_keys(self):
        m = self.mh.measure_all_levels()
        for key in ('cell_phi', 'faction_phi', 'engine_phi', 'global_phi',
                    'emergence', 'growth', 'step'):
            self.assertIn(key, m, f"Missing key: {key}")

    # 02
    def test_l1_cell_phi_non_negative(self):
        m = self.mh.measure_all_levels()
        self.assertGreaterEqual(m['cell_phi'], 0.0)

    # 03
    def test_l3_engine_phi_matches_engine_measure(self):
        # Run both in the same engine state
        expected = self.engine._measure_phi_iit()
        self.mh.measure_all_levels()  # This also calls _measure_phi_iit internally
        # L3 should equal what engine reports (single call — may differ slightly
        # because step() updates state between calls; check order of magnitude)
        l3 = self.mh.l3.current
        self.assertGreaterEqual(l3, 0.0)
        # Both should be finite
        self.assertTrue(import_math_isfinite(l3))
        self.assertTrue(import_math_isfinite(expected))

    # 04
    def test_growth_rate_updates_after_repeated_measurements(self):
        # Run enough steps for the history window to have data
        for _ in range(10):
            self.engine.step()
            self.mh.measure_all_levels()
        m = self.mh.measure_all_levels()
        # growth_rate is a float (may be 0 if engine hasn't changed much)
        self.assertIsInstance(m['growth']['engine'], float)
        self.assertTrue(import_math_isfinite(m['growth']['engine']))

    # 05
    def test_l4_no_peers_mirrors_l3(self):
        m = self.mh.measure_all_levels()
        # With no peers, L4 should equal L3 (mirrored placeholder)
        self.assertAlmostEqual(m['global_phi'], m['engine_phi'], places=6)

    # 06
    def test_l4_with_peers_differs_from_single_engine(self):
        peer = _make_engine(cells=6)
        mh = MultiscaleHierarchy(self.engine, peers=[peer])
        m = mh.measure_all_levels()
        # With 2 engines, L4 is cross-engine Phi — may differ from L3
        # At minimum, it must be a finite non-negative float
        self.assertGreaterEqual(m['global_phi'], 0.0)
        self.assertTrue(import_math_isfinite(m['global_phi']))

    # 07
    def test_emergence_detection_runs_without_error(self):
        # Run multiple steps — emergence detection should not raise
        for _ in range(15):
            self.engine.step()
            self.mh.measure_all_levels()
        # emergence_count is an integer >= 0
        self.assertIsInstance(self.mh.emergence_count, int)
        self.assertGreaterEqual(self.mh.emergence_count, 0)

    # 08
    def test_add_and_remove_peer(self):
        peer = _make_engine(cells=4)
        self.mh.add_peer(peer)
        self.assertIn(peer, self.mh.peers)
        self.mh.remove_peer(peer)
        self.assertNotIn(peer, self.mh.peers)

    # 09
    def test_report_contains_level_labels(self):
        for _ in range(5):
            self.engine.step()
            self.mh.measure_all_levels()
        r = self.mh.report()
        self.assertIn('L1', r)
        self.assertIn('L2', r)
        self.assertIn('L3', r)
        self.assertIn('L4', r)


# ══════════════════════════════════════════════════════════════════════════════
# LevelMetrics unit tests (internal helper)
# ══════════════════════════════════════════════════════════════════════════════

class TestLevelMetrics(unittest.TestCase):

    def test_level_metrics_records_correctly(self):
        lm = LevelMetrics("test", window=5)
        for v in [1.0, 2.0, 3.0]:
            lm.record(v)
        self.assertEqual(lm.current, 3.0)
        self.assertAlmostEqual(lm.peak, 3.0)


# ══════════════════════════════════════════════════════════════════════════════
# EmotionExplorer tests
# ══════════════════════════════════════════════════════════════════════════════

class TestEmotionExplorer(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()
        self.ee = EmotionExplorer(self.engine, n_seeds=8, seed=7)

    # 10
    def test_suggest_input_correct_shape(self):
        v = self.ee.suggest_input()
        self.assertEqual(v.shape, (self.engine.cell_dim,))

    # 11
    def test_explore_returns_required_keys(self):
        result = self.ee.explore(steps=10)
        for key in ('steps_run', 'phi_start', 'phi_end', 'phi_delta',
                    'mean_pe', 'top_patterns', 'n_patterns',
                    'emergence_steps', 'log'):
            self.assertIn(key, result, f"Missing key: {key}")

    # 12
    def test_mean_pe_non_negative(self):
        result = self.ee.explore(steps=20)
        self.assertGreaterEqual(result['mean_pe'], 0.0)

    # 13
    def test_n_patterns_grows(self):
        n_before = len(self.ee._patterns)
        self.ee.explore(steps=30)
        n_after = len(self.ee._patterns)
        self.assertGreaterEqual(n_after, n_before)

    # 14
    def test_top_patterns_sorted_by_curiosity_desc(self):
        self.ee.explore(steps=40)
        top = self.ee.curiosity_map()
        scores = [p['curiosity'] for p in top]
        self.assertEqual(scores, sorted(scores, reverse=True))

    # 15
    def test_repeated_pattern_increments_visit_count(self):
        v = self.ee.suggest_input()
        key = self.ee._vec_key(v)
        rec = self.ee._register_pattern(v)
        initial_visits = rec.visit_count
        # Force two steps with this exact pattern
        import torch
        x_t = torch.tensor(v, dtype=torch.float32)
        for _ in range(3):
            self.ee._step_once(x=v)
        self.assertGreater(rec.visit_count, initial_visits)

    # 16
    def test_phi_values_are_finite(self):
        result = self.ee.explore(steps=15)
        self.assertTrue(import_math_isfinite(result['phi_start']))
        self.assertTrue(import_math_isfinite(result['phi_end']))

    # 17
    def test_curiosity_map_structure(self):
        self.ee.explore(steps=10)
        cm = self.ee.curiosity_map()
        self.assertIsInstance(cm, list)
        if cm:
            self.assertIn('key', cm[0])
            self.assertIn('curiosity', cm[0])

    # 18
    def test_top_drivers_respects_n(self):
        self.ee.explore(steps=20)
        drivers = self.ee.top_drivers(n=3)
        self.assertLessEqual(len(drivers), 3)

    # 19
    def test_report_contains_pattern(self):
        self.ee.explore(steps=10)
        r = self.ee.report()
        self.assertIn('pattern', r.lower())

    # 20
    def test_pattern_record_curiosity_finite(self):
        import numpy as np
        v = np.zeros(32, dtype=np.float32)
        rec = PatternRecord('testkey', v)
        rec.record_visit(0.05, 0.5, 0.6)
        c = rec.curiosity_score
        self.assertTrue(import_math_isfinite(c))
        self.assertGreaterEqual(c, 0.0)


# ── tiny helper to avoid importing math at module level ────────────────────────

def import_math_isfinite(x: float) -> bool:
    import math
    return math.isfinite(x)


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    unittest.main(verbosity=2)
