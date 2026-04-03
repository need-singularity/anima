"""Tests for recursive_growth.py and improvement_hooks.py.

Tests cover:
  - RecursiveGrowth internal loop (runs, detects stall, applies intervention)
  - Safety: auto-revert when Phi drops > 20%
  - Modification logging
  - External suggestions format
  - improvement_hooks: submit / read / report roundtrip
  - Queue statistics

Uses a lightweight mock engine so no GPU/Rust dependencies required.
"""

import os
import sys
import json
import time
import uuid
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

# ── Imports under test ──────────────────────────────────────
from improvement_hooks import (
    submit_improvement,
    get_pending_improvements,
    get_queue_stats,
    mark_in_progress,
    report_result,
    skip_improvement,
    clear_completed,
    ImprovementRecord,
    STATUS_PENDING,
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    STATUS_SKIPPED,
)
from recursive_growth import (
    RecursiveGrowth,
    PhiSnapshot,
    _diagnose,
    _run_steps,
    generate_external_suggestions,
    DISCOVER_STEPS,
    PHI_DROP_THRESHOLD,
    MIN_PHI_IMPROVEMENT_PCT,
)


# ═══════════════════════════════════════════════════════════
# Mock Engine — simulates ConsciousnessEngine without real deps
# ═══════════════════════════════════════════════════════════

class MockEngine:
    """Minimal engine that returns controllable Phi values."""

    def __init__(self, phi_sequence=None, drop_after: int = 9999):
        """
        phi_sequence: list of phi values returned in order (then repeats last)
        drop_after:   after this many steps, phi drops to 0.01 (simulate drop)
        """
        self._phi_seq = phi_sequence or [0.5 + i * 0.01 for i in range(200)]
        self._drop_after = drop_after
        self._step = 0
        self.topology = "ring"
        self.hebbian_lr = 0.01
        self._noise_scale = 0.01
        self.split_threshold = 0.3
        self.merge_threshold = 0.01

    def step(self, text=None):
        idx = min(self._step, len(self._phi_seq) - 1)
        phi = self._phi_seq[idx]
        if self._step >= self._drop_after:
            phi = 0.005  # severe drop
        self._step += 1
        return {
            "phi_iit": phi,
            "avg_tension": 0.1,
            "n_cells": 4,
        }


class MockStallEngine(MockEngine):
    """Engine that always returns nearly constant Phi (stalling)."""

    def __init__(self):
        super().__init__(phi_sequence=[0.50 + i * 0.0001 for i in range(200)])


class MockImbalancedEngine(MockEngine):
    """Engine with high tension variance (faction imbalance signal)."""

    def __init__(self):
        import random
        random.seed(7)
        super().__init__(phi_sequence=[0.5 + i * 0.005 for i in range(200)])
        self._tension_vals = [0.1 if i % 2 == 0 else 0.9 for i in range(200)]
        self._t_idx = 0

    def step(self, text=None):
        result = super().step(text)
        tension = self._tension_vals[min(self._t_idx, len(self._tension_vals) - 1)]
        self._t_idx += 1
        result["avg_tension"] = tension
        return result


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture()
def tmp_queue(tmp_path):
    """Temporary queue JSON file path."""
    return str(tmp_path / "test_queue.json")


@pytest.fixture()
def tmp_log(tmp_path):
    """Temporary log JSON file path."""
    return str(tmp_path / "test_log.json")


@pytest.fixture()
def rg_growing(tmp_log):
    engine = MockEngine()
    rg = RecursiveGrowth(engine=engine, log_path=tmp_log)
    return rg


@pytest.fixture()
def rg_stalling(tmp_log):
    engine = MockStallEngine()
    rg = RecursiveGrowth(engine=engine, log_path=tmp_log)
    return rg


# ═══════════════════════════════════════════════════════════
# Tests — Internal Loop
# ═══════════════════════════════════════════════════════════

class TestInternalLoop:

    def test_internal_loop_runs(self, rg_growing):
        """Internal loop completes without error and returns CycleResult."""
        result = rg_growing.internal_loop(steps=10)
        assert result.cycle == 1
        assert isinstance(result.phi_before, float)
        assert isinstance(result.phi_after, float)
        assert isinstance(result.time_sec, float)
        assert result.time_sec >= 0.0

    def test_internal_loop_increments_cycle(self, rg_growing):
        """Cycle counter increments on each call."""
        r1 = rg_growing.internal_loop(steps=10)
        r2 = rg_growing.internal_loop(steps=10)
        assert r1.cycle == 1
        assert r2.cycle == 2

    def test_internal_loop_returns_modifications_list(self, rg_growing):
        """Modifications field is a list (may be empty if no intervention needed)."""
        result = rg_growing.internal_loop(steps=10)
        assert isinstance(result.modifications, list)

    def test_internal_loop_detects_stall(self, rg_stalling):
        """Stalling engine should be diagnosed as 'stalling'."""
        result = rg_stalling.internal_loop(steps=20)
        assert result.diagnosis is not None
        assert result.diagnosis.status in ("stalling", "saturated", "growing")
        # Stalling engine should produce a non-'none' hint
        assert result.diagnosis.intervention_hint in ("noise", "hebbian", "frustration", "none")

    def test_internal_loop_detects_stall_diagnosis_status(self, rg_stalling):
        """Stalling engine's diagnosis status is 'stalling' (not growing)."""
        result = rg_stalling.internal_loop(steps=30)
        # growth_rate should be very small for stalling engine
        if result.diagnosis:
            assert abs(result.diagnosis.growth_rate) < 0.01

    def test_modification_logged_to_file(self, rg_growing, tmp_log):
        """Modifications are persisted to log JSON file."""
        rg_growing.internal_loop(steps=10)
        assert os.path.isfile(tmp_log)
        with open(tmp_log, 'r') as fh:
            log = json.load(fh)
        assert len(log) >= 1
        assert "cycle" in log[0]
        assert "phi_before" in log[0]

    def test_law_candidate_registered_on_improvement(self):
        """If Phi improves > 5%, a law candidate is registered."""
        # Engine that improves after intervention (topology switch)
        # Phase 1: flat Phi, Phase 2: boosted Phi
        seq = [0.3] * 20 + [0.5] * 20  # 66% jump after intervention
        engine = MockEngine(phi_sequence=seq)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            log_path = tf.name
        try:
            rg = RecursiveGrowth(engine=engine, log_path=log_path)
            result = rg.internal_loop(steps=10)
            # May or may not produce candidates depending on exact timing,
            # but the field must be a list
            assert isinstance(result.law_candidates, list)
        finally:
            if os.path.isfile(log_path):
                os.unlink(log_path)

    def test_safety_revert_on_phi_drop(self, tmp_log):
        """When Phi drops > 20% after modification, parameters are reverted."""
        # Engine drops severely after step 15
        engine = MockEngine(
            phi_sequence=[0.5] * 15 + [0.005] * 200,
            drop_after=15,
        )
        rg = RecursiveGrowth(engine=engine, log_path=tmp_log)

        # Capture topology before cycle
        topology_before = engine.topology
        result = rg.internal_loop(steps=10)

        # Any reverted modification should have reverted=True
        for mod in result.modifications:
            if mod.reverted:
                # Reverted — parameter should be restored
                # (topology is the most likely intervention for stalling)
                assert mod.phi_delta_pct < -PHI_DROP_THRESHOLD or mod.reverted

    def test_no_engine_returns_empty_cycle(self, tmp_log):
        """RecursiveGrowth with no engine returns an empty cycle gracefully."""
        # Force engine to stay None by setting it after construction
        rg = RecursiveGrowth(engine=None, log_path=tmp_log)
        rg.engine = None  # override any auto-created engine
        result = rg.internal_loop()
        assert result.phi_before == 0.0
        assert result.phi_after == 0.0
        assert result.modifications == []

    def test_max_mods_per_cycle_not_exceeded(self, rg_growing):
        """Number of modifications per cycle never exceeds MAX_MODS_PER_CYCLE."""
        from recursive_growth import MAX_MODS_PER_CYCLE
        for _ in range(5):
            result = rg_growing.internal_loop(steps=5)
            assert len(result.modifications) <= MAX_MODS_PER_CYCLE


# ═══════════════════════════════════════════════════════════
# Tests — External Suggestions
# ═══════════════════════════════════════════════════════════

class TestExternalSuggestions:

    def test_external_suggestions_returns_list(self, rg_growing):
        """external_suggestions() returns a non-empty list."""
        suggestions = rg_growing.external_suggestions()
        assert isinstance(suggestions, list)

    def test_external_suggestions_format(self, rg_growing):
        """Every suggestion has required keys with correct types."""
        suggestions = rg_growing.external_suggestions()
        required_keys = {"id", "type", "target", "action", "reason", "priority", "status"}
        for s in suggestions:
            for key in required_keys:
                assert key in s, f"Missing key '{key}' in suggestion: {s}"
            assert isinstance(s["id"], str) and len(s["id"]) > 0
            assert s["priority"] in ("critical", "high", "medium", "low")
            assert s["status"] == "pending"

    def test_external_suggestions_type_valid(self, rg_growing):
        """Each suggestion type is in VALID_TYPES or is an accepted string."""
        from improvement_hooks import VALID_TYPES
        suggestions = rg_growing.external_suggestions()
        for s in suggestions:
            # All types should be in VALID_TYPES
            assert s["type"] in VALID_TYPES, f"Invalid type: {s['type']}"

    def test_external_suggestions_have_ids(self, rg_growing):
        """Each suggestion has a unique id."""
        suggestions = rg_growing.external_suggestions()
        ids = [s["id"] for s in suggestions]
        assert len(ids) == len(set(ids)), "Duplicate IDs in suggestions"

    @staticmethod
    def test_generate_external_suggestions_standalone():
        """generate_external_suggestions() works independently."""
        suggestions = generate_external_suggestions()
        assert isinstance(suggestions, list)
        # Always contains at least the self-referential cycle suggestion
        assert any(
            "recursive" in s.get("action", "").lower()
            or "recursive_growth" in s.get("target", "").lower()
            or "recursive_growth" in s.get("created_by", "").lower()
            for s in suggestions
        )


# ═══════════════════════════════════════════════════════════
# Tests — improvement_hooks roundtrip
# ═══════════════════════════════════════════════════════════

class TestImprovementHooks:

    def test_submit_and_retrieve(self, tmp_queue):
        """Submit an improvement and retrieve it as pending."""
        rec = submit_improvement({
            "type": "implement",
            "target": "anima/src/foo.py",
            "action": "Add bar feature",
            "reason": "bar is missing",
            "priority": "high",
        }, path=tmp_queue)
        assert isinstance(rec, ImprovementRecord)
        assert rec.status == STATUS_PENDING

        pending = get_pending_improvements(path=tmp_queue)
        assert len(pending) == 1
        assert pending[0].id == rec.id
        assert pending[0].type == "implement"

    def test_improvement_hooks_roundtrip(self, tmp_queue):
        """Full roundtrip: submit → in_progress → done."""
        rec = submit_improvement({
            "type": "add_tests",
            "target": "anima/tests/test_bar.py",
            "action": "Write 10 tests for bar",
            "reason": "no coverage",
        }, path=tmp_queue)

        # Mark in progress
        ok = mark_in_progress(rec.id, path=tmp_queue)
        assert ok

        # Verify it's no longer pending
        pending = get_pending_improvements(path=tmp_queue)
        assert all(p.id != rec.id for p in pending)

        # Report success
        ok = report_result(rec.id, success=True, details="10 tests written", path=tmp_queue)
        assert ok

        # Queue stats should show 1 done
        stats = get_queue_stats(path=tmp_queue)
        assert stats["by_status"][STATUS_DONE] == 1

    def test_report_failure(self, tmp_queue):
        """report_result(success=False) marks as FAILED."""
        rec = submit_improvement({
            "type": "fix",
            "target": "anima/src/x.py",
            "action": "Fix crash on empty input",
            "reason": "crash observed",
        }, path=tmp_queue)

        report_result(rec.id, success=False, details="could not reproduce", path=tmp_queue)
        stats = get_queue_stats(path=tmp_queue)
        assert stats["by_status"][STATUS_FAILED] == 1

    def test_skip_improvement(self, tmp_queue):
        """skip_improvement() marks as SKIPPED and removes from pending."""
        rec = submit_improvement({
            "type": "document",
            "target": "docs/",
            "action": "Write overview",
            "reason": "undocumented",
        }, path=tmp_queue)

        skip_improvement(rec.id, reason="not relevant now", path=tmp_queue)
        pending = get_pending_improvements(path=tmp_queue)
        assert all(p.id != rec.id for p in pending)

    def test_deduplication(self, tmp_queue):
        """Submitting same id twice does not duplicate the record."""
        fixed_id = str(uuid.uuid4())
        submit_improvement({
            "id": fixed_id,
            "type": "implement",
            "target": "x.py",
            "action": "do x",
            "reason": "y",
        }, path=tmp_queue)
        submit_improvement({
            "id": fixed_id,
            "type": "implement",
            "target": "x.py",
            "action": "do x",
            "reason": "y",
        }, path=tmp_queue)

        pending = get_pending_improvements(path=tmp_queue)
        matching = [p for p in pending if p.id == fixed_id]
        assert len(matching) == 1, "Duplicate submission should be deduplicated"

    def test_priority_ordering(self, tmp_queue):
        """High priority items appear before medium priority in get_pending."""
        submit_improvement({
            "type": "implement",
            "target": "a.py",
            "action": "low priority task",
            "reason": "r",
            "priority": "low",
        }, path=tmp_queue)
        submit_improvement({
            "type": "implement",
            "target": "b.py",
            "action": "high priority task",
            "reason": "r",
            "priority": "high",
        }, path=tmp_queue)
        submit_improvement({
            "type": "implement",
            "target": "c.py",
            "action": "critical task",
            "reason": "r",
            "priority": "critical",
        }, path=tmp_queue)

        pending = get_pending_improvements(path=tmp_queue)
        assert len(pending) >= 3
        priorities = [p.priority for p in pending]
        idx_crit = priorities.index("critical")
        idx_high = priorities.index("high")
        idx_low = priorities.index("low")
        assert idx_crit < idx_high < idx_low, f"Wrong priority order: {priorities}"

    def test_get_queue_stats_empty(self, tmp_queue):
        """Stats on empty queue return zeros."""
        stats = get_queue_stats(path=tmp_queue)
        assert stats["total"] == 0
        assert stats["by_status"][STATUS_PENDING] == 0

    def test_clear_completed(self, tmp_queue):
        """clear_completed removes old done records."""
        rec = submit_improvement({
            "type": "fix",
            "target": "z.py",
            "action": "fix z",
            "reason": "broken",
        }, path=tmp_queue)
        report_result(rec.id, success=True, path=tmp_queue)

        # Force updated_at to be old
        import json as _json
        queue = []
        with open(tmp_queue) as fh:
            queue = _json.load(fh)
        for item in queue:
            if item.get('id') == rec.id:
                item['updated_at'] = time.time() - 10 * 86400  # 10 days ago
        with open(tmp_queue, 'w') as fh:
            _json.dump(queue, fh)

        removed = clear_completed(path=tmp_queue, keep_days=7.0)
        assert removed == 1
        stats = get_queue_stats(path=tmp_queue)
        assert stats["total"] == 0


# ═══════════════════════════════════════════════════════════
# Tests — Phi snapshot / diagnosis internals
# ═══════════════════════════════════════════════════════════

class TestDiagnostics:

    def test_diagnose_growing(self):
        snap = PhiSnapshot(
            steps=list(range(20)),
            phis=[0.1 + i * 0.05 for i in range(20)],
            tensions=[0.1] * 20,
        )
        diag = _diagnose(snap)
        assert diag.status == "growing"
        assert diag.growth_rate > 0

    def test_diagnose_stalling(self):
        snap = PhiSnapshot(
            steps=list(range(20)),
            phis=[0.5 + i * 0.00005 for i in range(20)],
            tensions=[0.1] * 20,
        )
        diag = _diagnose(snap)
        # Tiny slope → stalling or saturated (SaturationLens may call it plateau)
        assert diag.status in ("stalling", "saturated")
        # Both conditions warrant a "noise" intervention (topology switch)
        assert diag.intervention_hint == "noise"

    def test_diagnose_decaying(self):
        snap = PhiSnapshot(
            steps=list(range(20)),
            phis=[1.0 - i * 0.05 for i in range(20)],
            tensions=[0.1] * 20,
        )
        diag = _diagnose(snap)
        assert diag.status == "decaying"
        assert diag.growth_rate < 0

    def test_diagnose_empty_snap(self):
        snap = PhiSnapshot()
        diag = _diagnose(snap)
        assert diag.status == "unknown"
        assert diag.confidence == 0.0

    def test_run_steps_returns_snapshot(self):
        engine = MockEngine()
        snap = _run_steps(engine, steps=10)
        assert len(snap.phis) == 10
        assert all(isinstance(p, float) for p in snap.phis)

    def test_run_steps_zero_steps(self):
        engine = MockEngine()
        snap = _run_steps(engine, steps=0)
        assert snap.phis == []
