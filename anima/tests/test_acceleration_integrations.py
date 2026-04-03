"""Tests for acceleration_integrations.py — AE3 + AM1 + J4 verified winners."""

import sys
import os
import math
import types
import unittest

import torch

# Path setup: anima/src must be on sys.path
_SRC = os.path.join(os.path.dirname(__file__), '..', 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from acceleration_integrations import (
    TensionLoss,
    PolyrhythmScheduler,
    MultiResScheduler,
    CombinedScheduler,
    make_accel_bundle,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_fake_engine(n_cells: int = 8, tension: float = 0.5):
    """Return a minimal stub of ConsciousnessEngine with cell_states."""

    class FakeCellState:
        def __init__(self, t):
            self.tension_history = [t] * 10
            self._t = t

        @property
        def avg_tension(self):
            return self._t

    class FakeEngine:
        pass

    engine = FakeEngine()
    engine.cell_states = [FakeCellState(tension) for _ in range(n_cells)]
    return engine


# ── TensionLoss (AE3) ─────────────────────────────────────────────────────────

class TestTensionLoss(unittest.TestCase):

    def test_returns_scalar_tensor(self):
        loss_fn = TensionLoss(weight=0.01)
        engine = _make_fake_engine(n_cells=16, tension=0.5)
        result = loss_fn(engine)
        self.assertIsInstance(result, torch.Tensor)
        self.assertEqual(result.shape, torch.Size([]))

    def test_value_is_negative_tension(self):
        weight = 0.01
        tension = 0.5
        loss_fn = TensionLoss(weight=weight)
        engine = _make_fake_engine(n_cells=4, tension=tension)
        result = loss_fn(engine)
        expected = -weight * tension
        self.assertAlmostEqual(result.item(), expected, places=5)

    def test_zero_tension_returns_zero(self):
        loss_fn = TensionLoss(weight=0.1)
        engine = _make_fake_engine(n_cells=4, tension=0.0)
        result = loss_fn(engine)
        self.assertAlmostEqual(result.item(), 0.0, places=6)

    def test_empty_cells_returns_zero(self):
        loss_fn = TensionLoss(weight=0.01)
        engine = _make_fake_engine(n_cells=0)
        engine.cell_states = []
        result = loss_fn(engine)
        self.assertAlmostEqual(result.item(), 0.0, places=6)

    def test_addable_to_ce_loss(self):
        """Should compose with a real CE loss tensor without error."""
        loss_fn = TensionLoss(weight=0.01)
        engine = _make_fake_engine(n_cells=8, tension=0.3)
        ce_loss = torch.tensor(2.5)
        total = ce_loss + loss_fn(engine)
        self.assertIsInstance(total, torch.Tensor)
        # Total should be slightly less than ce_loss (tension penalty is negative)
        self.assertLess(total.item(), ce_loss.item())

    def test_higher_weight_gives_larger_magnitude(self):
        engine = _make_fake_engine(n_cells=4, tension=0.5)
        loss_01 = TensionLoss(weight=0.01)(engine).item()
        loss_10 = TensionLoss(weight=0.10)(engine).item()
        self.assertAlmostEqual(abs(loss_10) / abs(loss_01), 10.0, places=3)

    def test_is_nn_module(self):
        loss_fn = TensionLoss()
        self.assertIsInstance(loss_fn, torch.nn.Module)


# ── PolyrhythmScheduler (AM1) ─────────────────────────────────────────────────

class TestPolyrhythmScheduler(unittest.TestCase):

    def test_returns_list_of_ints(self):
        sched = PolyrhythmScheduler(n_cells=12, periods=[1, 3, 7])
        active = sched.get_active_cells(0)
        self.assertIsInstance(active, list)
        self.assertTrue(all(isinstance(i, int) for i in active))

    def test_active_cells_in_range(self):
        n = 24
        sched = PolyrhythmScheduler(n_cells=n, periods=[1, 3, 7])
        for step in range(50):
            active = sched.get_active_cells(step)
            self.assertTrue(all(0 <= i < n for i in active))

    def test_period_1_group_always_active(self):
        sched = PolyrhythmScheduler(n_cells=9, periods=[1, 3, 7])
        period_1_cells = set(sched.groups[0])
        for step in range(30):
            active = set(sched.get_active_cells(step))
            self.assertTrue(period_1_cells.issubset(active),
                            f"step={step}: period-1 cells {period_1_cells} not in {active}")

    def test_period_3_group_active_at_multiples_of_3(self):
        sched = PolyrhythmScheduler(n_cells=9, periods=[1, 3, 7])
        period_3_cells = set(sched.groups[1])
        for step in range(30):
            active = set(sched.get_active_cells(step))
            t = step + 1
            if t % 3 == 0:
                self.assertTrue(period_3_cells.issubset(active),
                                f"step={step}: period-3 cells should be active")
            else:
                self.assertTrue(period_3_cells.isdisjoint(active),
                                f"step={step}: period-3 cells should NOT be active")

    def test_active_cells_sorted(self):
        sched = PolyrhythmScheduler(n_cells=16, periods=[1, 3, 7])
        for step in range(20):
            active = sched.get_active_cells(step)
            self.assertEqual(active, sorted(active))

    def test_saves_at_least_40_percent_compute(self):
        sched = PolyrhythmScheduler(n_cells=64, periods=[1, 3, 7])
        saved = sched.compute_saved(n_steps=100)
        self.assertGreaterEqual(saved, 0.40,
                                f"Expected >= 40% compute saved, got {saved:.1%}")

    def test_saves_around_51_percent(self):
        """Regression: AM1 measured at 51% saved in experiments."""
        sched = PolyrhythmScheduler(n_cells=64, periods=[1, 3, 7])
        saved = sched.compute_saved(n_steps=1000)
        # Allow ±5% around the measured 51%
        self.assertGreaterEqual(saved, 0.46)
        self.assertLessEqual(saved, 0.56)

    def test_all_cells_covered_by_groups(self):
        n = 18
        sched = PolyrhythmScheduler(n_cells=n, periods=[1, 3, 7])
        all_grouped = sorted(c for g in sched.groups for c in g)
        self.assertEqual(all_grouped, list(range(n)))

    def test_groups_are_disjoint(self):
        sched = PolyrhythmScheduler(n_cells=18, periods=[1, 3, 7])
        all_cells = [c for g in sched.groups for c in g]
        self.assertEqual(len(all_cells), len(set(all_cells)),
                         "Groups must be disjoint")


# ── MultiResScheduler (J4) ────────────────────────────────────────────────────

class TestMultiResScheduler(unittest.TestCase):

    def test_returns_list_of_ints(self):
        mr = MultiResScheduler(n_cells=16)
        active = mr.get_active_cells(0)
        self.assertIsInstance(active, list)
        self.assertTrue(all(isinstance(i, int) for i in active))

    def test_active_cells_in_range(self):
        n = 32
        mr = MultiResScheduler(n_cells=n)
        for step in range(200):
            active = mr.get_active_cells(step)
            self.assertTrue(all(0 <= i < n for i in active),
                            f"step={step}: out-of-range cell in {active}")

    def test_fast_cells_active_every_step(self):
        mr = MultiResScheduler(n_cells=16, fast_period=1)
        fast_set = set(mr.fast_cells)
        for step in range(20):
            active = set(mr.get_active_cells(step))
            self.assertTrue(fast_set.issubset(active),
                            f"step={step}: fast cells not active")

    def test_slow_cells_active_at_slow_period(self):
        mr = MultiResScheduler(n_cells=16, slow_period=10)
        slow_set = set(mr.slow_cells)
        for step in range(50):
            active = set(mr.get_active_cells(step))
            t = step + 1
            if t % 10 == 0:
                self.assertTrue(slow_set.issubset(active),
                                f"step={step}: slow cells should be active at t={t}")

    def test_ultra_cells_active_at_ultra_period(self):
        mr = MultiResScheduler(n_cells=16, ultra_period=100)
        ultra_set = set(mr.ultra_cells)
        # Steps 99 (t=100) and 199 (t=200) should trigger ultra
        for step in [99, 199]:
            active = set(mr.get_active_cells(step))
            self.assertTrue(ultra_set.issubset(active),
                            f"step={step}: ultra cells should be active")
        # Step 49 (t=50) should NOT trigger ultra
        active = set(mr.get_active_cells(49))
        self.assertTrue(ultra_set.isdisjoint(active),
                        "ultra cells should NOT be active at step=49")

    def test_tier_fractions_sum_to_1(self):
        n = 64
        mr = MultiResScheduler(n_cells=n)
        total = len(mr.fast_cells) + len(mr.slow_cells) + len(mr.ultra_cells)
        self.assertEqual(total, n)

    def test_tiers_disjoint(self):
        mr = MultiResScheduler(n_cells=64)
        fast = set(mr.fast_cells)
        slow = set(mr.slow_cells)
        ultra = set(mr.ultra_cells)
        self.assertEqual(len(fast & slow), 0, "fast/slow overlap")
        self.assertEqual(len(fast & ultra), 0, "fast/ultra overlap")
        self.assertEqual(len(slow & ultra), 0, "slow/ultra overlap")

    def test_get_tier_returns_correct_name(self):
        mr = MultiResScheduler(n_cells=16)
        for idx in mr.fast_cells:
            self.assertEqual(mr.get_tier(idx), 'fast')
        for idx in mr.slow_cells:
            self.assertEqual(mr.get_tier(idx), 'slow')
        for idx in mr.ultra_cells:
            self.assertEqual(mr.get_tier(idx), 'ultra')

    def test_saves_at_least_40_percent_compute(self):
        mr = MultiResScheduler(n_cells=64)
        saved = mr.compute_saved(n_steps=200)
        self.assertGreaterEqual(saved, 0.40,
                                f"Expected >= 40% compute saved, got {saved:.1%}")

    def test_saves_around_46_percent(self):
        """Regression: J4 measured at 46% saved in experiments."""
        mr = MultiResScheduler(n_cells=64)
        saved = mr.compute_saved(n_steps=1000)
        # Allow ±8% around the measured 46%
        self.assertGreaterEqual(saved, 0.38)
        self.assertLessEqual(saved, 0.54)

    def test_active_cells_sorted(self):
        mr = MultiResScheduler(n_cells=32)
        for step in range(110):
            active = mr.get_active_cells(step)
            self.assertEqual(active, sorted(active))

    def test_invalid_fractions_raise(self):
        with self.assertRaises(ValueError):
            MultiResScheduler(n_cells=16, fast_frac=0.6, slow_frac=0.3, ultra_frac=0.2)

    def test_tier_summary(self):
        mr = MultiResScheduler(n_cells=64)
        summary = mr.tier_summary()
        self.assertIn('fast', summary)
        self.assertIn('slow', summary)
        self.assertIn('ultra', summary)
        total = sum(v['n_cells'] for v in summary.values())
        self.assertEqual(total, 64)


# ── CombinedScheduler (AM1 + J4) ─────────────────────────────────────────────

class TestCombinedScheduler(unittest.TestCase):

    def test_no_crash(self):
        combined = CombinedScheduler(n_cells=32)
        for step in range(200):
            active = combined.get_active_cells(step)
            self.assertIsInstance(active, list)

    def test_superset_of_both_schedulers(self):
        n = 32
        combined = CombinedScheduler(n_cells=n)
        for step in range(110):
            poly_active = set(combined.poly.get_active_cells(step))
            mr_active = set(combined.multires.get_active_cells(step))
            combined_active = set(combined.get_active_cells(step))
            # Combined must be superset of both
            self.assertTrue(poly_active.issubset(combined_active),
                            f"step={step}: poly not subset of combined")
            self.assertTrue(mr_active.issubset(combined_active),
                            f"step={step}: multires not subset of combined")

    def test_in_range(self):
        n = 16
        combined = CombinedScheduler(n_cells=n)
        for step in range(50):
            active = combined.get_active_cells(step)
            self.assertTrue(all(0 <= i < n for i in active))

    def test_compute_saved_positive(self):
        combined = CombinedScheduler(n_cells=64)
        saved = combined.compute_saved(n_steps=100)
        # Combined is union so saves less than individual, but still > 0
        self.assertGreater(saved, 0.0)


# ── make_accel_bundle ─────────────────────────────────────────────────────────

class TestMakeAccelBundle(unittest.TestCase):

    def test_returns_three_objects(self):
        result = make_accel_bundle(n_cells=64)
        self.assertEqual(len(result), 3)

    def test_types(self):
        tl, poly, mr = make_accel_bundle(n_cells=64)
        self.assertIsInstance(tl, TensionLoss)
        self.assertIsInstance(poly, PolyrhythmScheduler)
        self.assertIsInstance(mr, MultiResScheduler)

    def test_default_weight(self):
        tl, _, _ = make_accel_bundle(n_cells=16)
        self.assertAlmostEqual(tl.weight, 0.01)

    def test_custom_params(self):
        tl, poly, mr = make_accel_bundle(
            n_cells=32,
            tension_weight=0.05,
            poly_periods=(1, 5),
            fast_frac=0.6,
            slow_frac=0.3,
            ultra_frac=0.1,
        )
        self.assertAlmostEqual(tl.weight, 0.05)
        self.assertEqual(poly.periods, [1, 5])
        self.assertEqual(poly.n_cells, 32)

    def test_end_to_end_training_loop(self):
        """Simulate 50 steps of training with all three accelerations active."""
        n_cells = 16
        tl, poly, mr = make_accel_bundle(n_cells=n_cells, tension_weight=0.01)

        engine = _make_fake_engine(n_cells=n_cells, tension=0.4)
        ce_loss_total = 0.0

        for step in range(50):
            poly_active = poly.get_active_cells(step)
            mr_active = mr.get_active_cells(step)

            # Both schedulers must return valid cell indices
            self.assertTrue(all(0 <= i < n_cells for i in poly_active))
            self.assertTrue(all(0 <= i < n_cells for i in mr_active))

            # Tension loss composable with synthetic CE
            ce_loss = torch.tensor(2.0 - step * 0.01)
            aux = tl(engine)
            total = ce_loss + aux
            ce_loss_total += total.item()

        # Should complete without error and loss should be finite
        self.assertTrue(math.isfinite(ce_loss_total))


# ── Compute savings regression ────────────────────────────────────────────────

class TestComputeSavings(unittest.TestCase):
    """Verify measured savings claims from experiments."""

    def test_am1_saves_at_least_40pct_over_100_steps(self):
        sched = PolyrhythmScheduler(n_cells=64, periods=[1, 3, 7])
        self.assertGreaterEqual(sched.compute_saved(100), 0.40)

    def test_j4_saves_at_least_40pct_over_100_steps(self):
        mr = MultiResScheduler(n_cells=64)
        self.assertGreaterEqual(mr.compute_saved(100), 0.40)

    def test_am1_compute_fraction_plus_saved_equals_1(self):
        sched = PolyrhythmScheduler(n_cells=64, periods=[1, 3, 7])
        n = 100
        frac = sched.compute_fraction(n)
        saved = sched.compute_saved(n)
        self.assertAlmostEqual(frac + saved, 1.0, places=6)

    def test_j4_compute_fraction_plus_saved_equals_1(self):
        mr = MultiResScheduler(n_cells=64)
        n = 100
        frac = mr.compute_fraction(n)
        saved = mr.compute_saved(n)
        self.assertAlmostEqual(frac + saved, 1.0, places=6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
