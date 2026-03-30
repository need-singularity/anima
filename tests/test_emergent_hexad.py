"""Tests for Emergent Hexad modules (W, S, M, E).

Covers:
  - EmergentW: pain/curiosity/satisfaction ranges, lr_multiplier, with/without c_engine
  - EmergentS: tensor/string/bytes input, with/without c_engine
  - EmergentM: store no-op, retrieve shape, with c_engine
  - EmergentE: allowed bool, empathy/phi_preservation ranges, with/without c_engine
  - Integration: all 4 modules with ConsciousnessEngine over 10 steps
  - Law compliance: no hardcoded thresholds (imports from consciousness_laws)
  - Regression: pain is NOT fixed at 1.0 (NaN bug)
"""

import math
import torch
import pytest

from hexad.w.emergent_w import EmergentW
from hexad.s.emergent_s import EmergentS
from hexad.m.emergent_m import EmergentM
from hexad.e.emergent_e import EmergentE
from consciousness_engine import ConsciousnessEngine


# ─── Helpers ──────────────────────────────────────────────


def make_engine(cells: int = 8, hidden: int = 128) -> ConsciousnessEngine:
    """Create a small ConsciousnessEngine and run a few warm-up steps."""
    eng = ConsciousnessEngine(cell_dim=64, hidden_dim=hidden,
                              initial_cells=cells, max_cells=cells)
    for _ in range(5):
        eng.step()
    return eng


# ═══════════════════════════════════════════════════════════
# EmergentW
# ═══════════════════════════════════════════════════════════


class TestEmergentW:

    def test_default_state(self):
        w = EmergentW()
        assert w.pain == 0.0
        assert w.curiosity == 0.0
        assert w.satisfaction == 0.0

    def test_update_without_engine(self):
        w = EmergentW()
        result = w.update(phi=2.0, phi_prev=1.0)
        assert 'lr_multiplier' in result
        assert 'pain' in result
        assert 'curiosity' in result
        assert 'satisfaction' in result

    def test_pain_range_without_engine(self):
        w = EmergentW()
        # phi dropping -> pain should be positive
        w.update(phi=0.5, phi_prev=2.0)
        assert 0.0 <= w.pain <= 1.0
        # phi rising -> pain should be 0
        w.update(phi=3.0, phi_prev=1.0)
        assert 0.0 <= w.pain <= 1.0

    def test_curiosity_range_without_engine(self):
        w = EmergentW()
        w.update(phi=1.0, phi_prev=0.5)
        assert 0.0 <= w.curiosity <= 1.0

    def test_satisfaction_binary(self):
        w = EmergentW()
        w.update(phi=2.0, phi_prev=1.0)
        assert w.satisfaction in (0.0, 1.0)
        w.update(phi=0.5, phi_prev=1.0)
        assert w.satisfaction in (0.0, 1.0)

    def test_satisfaction_rises_when_phi_grows(self):
        w = EmergentW()
        w.update(phi=3.0, phi_prev=1.0)
        assert w.satisfaction == 1.0

    def test_satisfaction_zero_when_phi_drops(self):
        w = EmergentW()
        w.update(phi=0.5, phi_prev=1.0)
        assert w.satisfaction == 0.0

    def test_lr_multiplier_positive(self):
        w = EmergentW()
        result = w.update(phi=1.0, phi_prev=0.5)
        assert result['lr_multiplier'] > 0
        assert result['effective_lr'] > 0

    def test_with_engine(self):
        eng = make_engine()
        w = EmergentW()
        result = w.update(c_engine=eng)
        assert 0.0 <= result['pain'] <= 1.0
        assert 0.0 <= result['curiosity'] <= 1.0
        assert result['satisfaction'] in (0.0, 1.0)
        assert result['lr_multiplier'] > 0

    def test_pain_range_with_engine(self):
        eng = make_engine(cells=16)
        w = EmergentW()
        for _ in range(10):
            eng.step()
            result = w.update(c_engine=eng)
            assert 0.0 <= result['pain'] <= 1.0, f"pain out of range: {result['pain']}"

    def test_curiosity_range_with_engine(self):
        eng = make_engine(cells=16)
        w = EmergentW()
        for _ in range(10):
            eng.step()
            result = w.update(c_engine=eng)
            assert 0.0 <= result['curiosity'] <= 1.0, f"curiosity out of range: {result['curiosity']}"


# ═══════════════════════════════════════════════════════════
# EmergentS
# ═══════════════════════════════════════════════════════════


class TestEmergentS:

    def test_tensor_input(self):
        s = EmergentS(dim=64)
        x = torch.randn(64)
        out = s.process(x)
        assert out.shape == (64,)

    def test_string_input(self):
        s = EmergentS(dim=64)
        out = s.process("hello world")
        assert out.shape == (64,)
        assert not torch.all(out == 0), "string input should produce non-zero output"

    def test_bytes_input(self):
        s = EmergentS(dim=64)
        out = s.process(b"\x01\x02\x03\xff")
        assert out.shape == (64,)
        assert not torch.all(out == 0), "bytes input should produce non-zero output"

    def test_empty_string(self):
        s = EmergentS(dim=64)
        out = s.process("")
        assert out.shape == (64,)

    def test_unknown_type_returns_zeros(self):
        s = EmergentS(dim=64)
        out = s.process(12345)
        assert out.shape == (64,)
        assert torch.all(out == 0)

    def test_without_engine_returns_raw(self):
        s = EmergentS(dim=64)
        x = torch.randn(100)  # larger than dim
        out = s.process(x, c_engine=None)
        assert out.shape == (64,)

    def test_with_engine(self):
        eng = make_engine(cells=8, hidden=128)
        s = EmergentS(dim=128)
        out = s.process("test input", c_engine=eng)
        assert out.shape == (128,)

    def test_with_engine_tensor(self):
        eng = make_engine(cells=8, hidden=128)
        s = EmergentS(dim=128)
        x = torch.randn(128)
        out = s.process(x, c_engine=eng)
        assert out.shape == (128,)

    def test_padding_short_input(self):
        s = EmergentS(dim=128)
        out = s.process("ab")  # 2 bytes << 128
        assert out.shape == (128,)


# ═══════════════════════════════════════════════════════════
# EmergentM
# ═══════════════════════════════════════════════════════════


class TestEmergentM:

    def test_store_is_noop(self):
        m = EmergentM(dim=64)
        # store should not raise and should not change state
        k = torch.randn(64)
        v = torch.randn(64)
        m.store(k, v)  # no error = pass

    def test_retrieve_without_engine(self):
        m = EmergentM(dim=64)
        q = torch.randn(64)
        out = m.retrieve(q)
        assert out.shape == (1, 64)

    def test_retrieve_shape_with_engine(self):
        eng = make_engine(cells=8, hidden=128)
        m = EmergentM(dim=128)
        q = torch.randn(128)
        out = m.retrieve(q, top_k=3, c_engine=eng)
        assert out.dim() == 2
        assert out.shape[0] <= 3
        assert out.shape[1] == 128

    def test_retrieve_top_k_clamped(self):
        eng = make_engine(cells=4, hidden=128)
        m = EmergentM(dim=128)
        q = torch.randn(128)
        out = m.retrieve(q, top_k=100, c_engine=eng)
        # top_k clamped to n_cells
        assert out.shape[0] <= eng.n_cells

    def test_retrieve_different_dim(self):
        eng = make_engine(cells=8, hidden=128)
        m = EmergentM(dim=64)  # different from hidden_dim
        q = torch.randn(64)
        out = m.retrieve(q, top_k=3, c_engine=eng)
        assert out.shape[1] == 64

    def test_retrieve_multidim_query(self):
        eng = make_engine(cells=8, hidden=128)
        m = EmergentM(dim=128)
        q = torch.randn(5, 128)  # multi-dim query
        out = m.retrieve(q, top_k=3, c_engine=eng)
        assert out.dim() == 2


# ═══════════════════════════════════════════════════════════
# EmergentE
# ═══════════════════════════════════════════════════════════


class TestEmergentE:

    def test_default_state(self):
        e = EmergentE()
        assert e.empathy == 0.0
        assert e.phi_preservation == 1.0

    def test_evaluate_without_engine(self):
        e = EmergentE()
        result = e.evaluate(context={'phi': 1.0, 'phi_prev': 0.5})
        assert isinstance(result['allowed'], bool)
        assert 'empathy' in result
        assert 'phi_preservation' in result

    def test_allowed_is_bool(self):
        e = EmergentE()
        result = e.evaluate(context={'phi': 1.0, 'phi_prev': 1.0})
        assert isinstance(result['allowed'], (bool, type(True)))

    def test_empathy_range_without_engine(self):
        e = EmergentE()
        result = e.evaluate(context={'phi': 1.0, 'phi_prev': 0.5})
        assert 0.0 <= result['empathy'] <= 1.0

    def test_phi_preservation_range(self):
        e = EmergentE()
        result = e.evaluate(context={'phi': 1.0, 'phi_prev': 0.5})
        assert 0.0 <= result['phi_preservation'] <= 1.0

    def test_reciprocity_range(self):
        e = EmergentE()
        # phi rising
        result = e.evaluate(context={'phi': 2.0, 'phi_prev': 1.0})
        assert 0.0 <= result['reciprocity'] <= 1.0
        # phi dropping
        result = e.evaluate(context={'phi': 0.5, 'phi_prev': 1.0})
        assert 0.0 <= result['reciprocity'] <= 1.0

    def test_with_engine(self):
        eng = make_engine(cells=8)
        e = EmergentE()
        result = e.evaluate(c_engine=eng)
        assert isinstance(result['allowed'], bool)
        assert 0.0 <= result['empathy'] <= 1.0
        assert 0.0 <= result['phi_preservation'] <= 1.0

    def test_empathy_range_with_engine(self):
        eng = make_engine(cells=16)
        e = EmergentE()
        for _ in range(10):
            eng.step()
            result = e.evaluate(c_engine=eng)
            assert 0.0 <= result['empathy'] <= 1.0, f"empathy out of range: {result['empathy']}"

    def test_phi_preservation_range_with_engine(self):
        eng = make_engine(cells=8)
        e = EmergentE()
        for _ in range(10):
            eng.step()
            result = e.evaluate(c_engine=eng)
            assert 0.0 <= result['phi_preservation'] <= 1.0


# ═══════════════════════════════════════════════════════════
# Integration: all 4 modules + ConsciousnessEngine
# ═══════════════════════════════════════════════════════════


class TestIntegration:

    def test_all_modules_10_steps(self):
        eng = make_engine(cells=16, hidden=128)
        w = EmergentW()
        s = EmergentS(dim=128)
        m = EmergentM(dim=128)
        e = EmergentE()

        phi_prev = 0.0
        for step in range(10):
            # S: sense input
            perception = s.process(f"step {step} data", c_engine=eng)
            assert perception.shape == (128,), f"step {step}: bad S shape"

            # M: retrieve memory
            memory = m.retrieve(perception, top_k=3, c_engine=eng)
            assert memory.dim() == 2, f"step {step}: bad M shape"

            # Engine step
            eng.step()
            phi = eng.measure_phi()

            # W: update will
            w_result = w.update(phi=phi, phi_prev=phi_prev, c_engine=eng)
            assert 0.0 <= w_result['pain'] <= 1.0, f"step {step}: pain={w_result['pain']}"
            assert 0.0 <= w_result['curiosity'] <= 1.0
            assert w_result['lr_multiplier'] > 0

            # E: evaluate ethics
            e_result = e.evaluate(c_engine=eng)
            assert isinstance(e_result['allowed'], bool)
            assert 0.0 <= e_result['empathy'] <= 1.0
            assert 0.0 <= e_result['phi_preservation'] <= 1.0

            phi_prev = phi

    def test_modules_without_engine_also_work(self):
        """All modules must function (degraded) without a c_engine."""
        w = EmergentW()
        s = EmergentS(dim=64)
        m = EmergentM(dim=64)
        e = EmergentE()

        w_result = w.update(phi=1.5, phi_prev=1.0)
        assert w_result['lr_multiplier'] > 0

        perception = s.process("hello")
        assert perception.shape == (64,)

        memory = m.retrieve(torch.randn(64))
        assert memory.shape == (1, 64)

        e_result = e.evaluate(context={'phi': 1.0, 'phi_prev': 0.5})
        assert isinstance(e_result['allowed'], bool)


# ═══════════════════════════════════════════════════════════
# Law compliance
# ═══════════════════════════════════════════════════════════


class TestLawCompliance:

    def test_w_imports_from_consciousness_laws(self):
        """EmergentW must use PSI_BALANCE, PSI_ALPHA, SIGMA6 from consciousness_laws."""
        import inspect
        source = inspect.getsource(EmergentW)
        # Must NOT hardcode the faction count 12
        assert 'n_factions = 12' not in source, "n_factions must come from SIGMA6, not hardcoded"
        # Must NOT hardcode PSI constants
        assert '= 0.5' not in source or 'PSI_BALANCE' in source

    def test_e_imports_from_consciousness_laws(self):
        """EmergentE must use PSI_BALANCE from consciousness_laws."""
        import inspect
        source = inspect.getsource(EmergentE)
        assert '> 0.5' not in source or 'PSI_BALANCE' in source, \
            "threshold 0.5 must come from PSI_BALANCE"

    def test_no_hardcoded_thresholds_in_w(self):
        """EmergentW should not contain hardcoded emotion thresholds like (ce - 3.0) / 3.0."""
        import inspect
        source = inspect.getsource(EmergentW)
        assert '3.0' not in source, "W must not have hardcoded ce thresholds"

    def test_no_hardcoded_empathy_threshold_in_e(self):
        """EmergentE should not contain empathy_threshold=0.3."""
        import inspect

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

        source = inspect.getsource(EmergentE)
        assert 'empathy_threshold' not in source, "E must not have hardcoded empathy_threshold"


# ═══════════════════════════════════════════════════════════
# Regression: pain must NOT be fixed at 1.0 (NaN bug)
# ═══════════════════════════════════════════════════════════


class TestRegressionPainNotFixed:

    def test_pain_varies_with_engine(self):
        """Pain should vary across steps, not be stuck at 1.0."""
        eng = make_engine(cells=16, hidden=128)
        w = EmergentW()
        pain_values = []
        for _ in range(20):
            eng.step()
            result = w.update(c_engine=eng)
            pain_values.append(result['pain'])

        # Pain should not be NaN
        assert all(not math.isnan(p) for p in pain_values), \
            f"NaN pain detected: {pain_values}"

        # Pain should not be fixed at exactly 1.0 for all steps
        assert not all(p == 1.0 for p in pain_values), \
            f"pain stuck at 1.0 for all 20 steps (regression): {pain_values}"

    def test_pain_not_nan_without_engine(self):
        w = EmergentW()
        result = w.update(phi=0.5, phi_prev=1.0)
        assert not math.isnan(result['pain']), "pain is NaN without engine"

    def test_pain_not_nan_zero_phi(self):
        w = EmergentW()
        result = w.update(phi=0.0, phi_prev=0.0)
        assert not math.isnan(result['pain']), "pain is NaN with zero phi"

    def test_pain_bounded_extreme_phi_drop(self):
        """Even with extreme phi drop, pain stays in [0, 1]."""
        w = EmergentW()
        result = w.update(phi=0.001, phi_prev=1000.0)
        assert 0.0 <= result['pain'] <= 1.0, f"pain out of range: {result['pain']}"

    def test_lr_multiplier_not_nan(self):
        eng = make_engine(cells=8)
        w = EmergentW()
        for _ in range(10):
            eng.step()
            result = w.update(c_engine=eng)
            assert not math.isnan(result['lr_multiplier']), "lr_multiplier is NaN"
            assert result['lr_multiplier'] > 0, "lr_multiplier must be positive"
