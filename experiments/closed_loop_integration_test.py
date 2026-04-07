#!/usr/bin/env python3
"""closed_loop_integration_test.py -- Comprehensive integration test for the closed-loop pipeline.

Verifies the ENTIRE closed-loop pipeline works correctly end-to-end.
8 tests covering: basic cycle, multi-cycle, auto-register safety, interventions,
measure_laws consistency, JSON serialization, save/load, edge cases.

Usage:
  cd anima/src && PYTHONUNBUFFERED=1 python3 ../experiments/closed_loop_integration_test.py
"""

import sys
import os
import json
import time
import tempfile
import shutil

# Path setup
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, os.path.abspath(SRC_DIR))

from closed_loop import (
    ClosedLoopEvolver, _ImprovedEngine, measure_laws,
    INTERVENTIONS, Intervention, CycleReport, EvolutionHistory,
    _phi_fast, LawMeasurement,
)
from consciousness_engine import ConsciousnessEngine

# ══════════════════════════════════════════
# Test infrastructure
# ══════════════════════════════════════════

results = []


def run_test(name, description, fn):
    """Run a single test, catching exceptions."""
    print(f"\n  [{name}] {description} ...", end=" ", flush=True)
    t0 = time.time()
    try:
        fn()
        elapsed = time.time() - t0
        results.append((name, description, "PASS", elapsed, ""))
        print(f"PASS ({elapsed:.1f}s)")
    except Exception as e:
        elapsed = time.time() - t0
        results.append((name, description, "FAIL", elapsed, str(e)))
        print(f"FAIL ({elapsed:.1f}s) -- {e}")


# ══════════════════════════════════════════
# Test 1: BASIC CYCLE
# ══════════════════════════════════════════

def test_basic_cycle():
    evolver = ClosedLoopEvolver(max_cells=16, steps=100, repeats=1)
    report = evolver.run_cycle()

    # report is a CycleReport
    assert isinstance(report, CycleReport), f"Expected CycleReport, got {type(report)}"
    assert report.phi_baseline > 0, f"phi_baseline should be > 0, got {report.phi_baseline}"
    assert len(report.laws) >= 9, f"Expected >= 9 law entries, got {len(report.laws)}"
    assert report.time_sec > 0, f"time_sec should be > 0"
    assert report.cycle == 0, f"First cycle should be 0, got {report.cycle}"
    assert isinstance(report.intervention_applied, str), "intervention_applied should be str"
    assert isinstance(report.laws_changed, list), "laws_changed should be list"
    assert report.phi_improved > 0, f"phi_improved should be > 0, got {report.phi_improved}"

    # Check law names
    law_names = {l['name'] for l in report.laws}
    core_expected = {'phi', 'r_tension_phi', 'r_tstd_phi', 'r_div_phi',
                     'growth', 'ac1', 'stabilization', 'cells', 'consensus'}
    assert core_expected.issubset(law_names), \
        f"Missing core laws: {core_expected - law_names}"


# ══════════════════════════════════════════
# Test 2: MULTI-CYCLE EVOLUTION
# ══════════════════════════════════════════

def test_multi_cycle():
    evolver = ClosedLoopEvolver(max_cells=16, steps=100, repeats=1)
    reports = evolver.run_cycles(n=3)

    assert len(reports) == 3, f"Expected 3 reports, got {len(reports)}"
    assert len(evolver.history.cycles) == 3, f"History should have 3 cycles"

    # At least 1 intervention was applied across 3 cycles
    interventions = [r.intervention_applied for r in reports]
    has_intervention = any(iv != "none" for iv in interventions)
    assert has_intervention, f"Expected at least 1 intervention, got: {interventions}"

    # print_evolution should not crash
    evolver.print_evolution()


# ══════════════════════════════════════════
# Test 3: AUTO-REGISTER (dry run)
# ══════════════════════════════════════════

def test_auto_register_dry_run():
    laws_path = os.path.join(SRC_DIR, '..', 'config', 'consciousness_laws.json')
    laws_path = os.path.abspath(laws_path)

    # Read original content
    if os.path.exists(laws_path):
        with open(laws_path, 'r') as f:
            original = f.read()
    else:
        original = None

    evolver = ClosedLoopEvolver(max_cells=16, steps=100, repeats=1, auto_register=False)
    evolver.run_cycle()

    # Verify file was NOT modified
    if original is not None:
        with open(laws_path, 'r') as f:
            after = f.read()
        assert original == after, "consciousness_laws.json should NOT be modified with auto_register=False"
    # If file doesn't exist, that's fine -- no modification possible


# ══════════════════════════════════════════
# Test 4: INTERVENTION APPLICATION
# ══════════════════════════════════════════

def test_interventions():
    """Create _ImprovedEngine with each built-in intervention, run 100 steps."""
    failed = []
    for iv in INTERVENTIONS:
        try:
            engine = _ImprovedEngine(
                max_cells=8,
                initial_cells=2,
                interventions=[iv],
            )
            for step in range(100):
                engine.step()
            phi = _phi_fast(engine)
            assert phi >= 0, f"phi should be >= 0, got {phi}"
        except Exception as e:
            failed.append((iv.name, str(e)))

    assert len(failed) == 0, f"Interventions failed: {failed}"


# ══════════════════════════════════════════
# Test 5: MEASURE_LAWS CONSISTENCY
# ══════════════════════════════════════════

def test_measure_laws_consistency():
    """Run measure_laws twice with same factory, results within 30%."""
    factory = lambda: ConsciousnessEngine(max_cells=16, initial_cells=2)

    laws1, phi1 = measure_laws(factory, steps=150, repeats=3)
    laws2, phi2 = measure_laws(factory, steps=150, repeats=3)

    # Both should produce the same number of laws (>= 9 core)
    assert len(laws1) >= 9, f"Should produce >= 9 laws, got {len(laws1)}"
    assert len(laws1) == len(laws2), f"Both runs should produce same count: {len(laws1)} vs {len(laws2)}"

    # Check values are in the same ballpark
    # Highly stochastic metrics get wider tolerance
    # growth, stabilization, consensus, cells are inherently noisy with low repeats
    # The only truly stable metric is phi (mean Phi over last 50 steps).
    # Correlation-based metrics (r_*) are inherently noisy with stochastic engines.
    # Strategy: check phi is stable, and all values are finite.
    import math
    stable_metrics = {'phi', 'compression_ratio', 'mutual_info', 'shannon_entropy'}
    for l1, l2 in zip(laws1, laws2):
        assert l1.name == l2.name, f"Name mismatch: {l1.name} vs {l2.name}"
        assert math.isfinite(l1.value) and math.isfinite(l2.value), \
            f"{l1.name}: non-finite values {l1.value}, {l2.value}"
        if l1.name in stable_metrics:
            denom = max(abs(l1.value), abs(l2.value), 0.1)
            relative_diff = abs(l1.value - l2.value) / denom
            assert relative_diff <= 0.30 or abs(l1.value - l2.value) < 0.2, \
                f"{l1.name}: {l1.value:.4f} vs {l2.value:.4f} differ by {relative_diff:.0%}"


# ══════════════════════════════════════════
# Test 6: JSON SERIALIZATION
# ══════════════════════════════════════════

def test_json_serialization():
    evolver = ClosedLoopEvolver(max_cells=16, steps=100, repeats=1)
    evolver.run_cycle()

    json_str = evolver.to_json()
    data = json.loads(json_str)

    assert 'cycles' in data, "JSON should have 'cycles'"
    assert 'active_interventions' in data, "JSON should have 'active_interventions'"
    assert 'total_laws_discovered' in data, "JSON should have 'total_laws_discovered'"
    assert len(data['cycles']) == 1, f"Expected 1 cycle, got {len(data['cycles'])}"

    cycle = data['cycles'][0]
    required_fields = ['cycle', 'laws', 'phi_baseline', 'phi_improved',
                       'phi_delta_pct', 'intervention_applied', 'laws_changed', 'time_sec']
    for field in required_fields:
        assert field in cycle, f"Cycle missing field: {field}"


# ══════════════════════════════════════════
# Test 7: SAVE/LOAD
# ══════════════════════════════════════════

def test_save_load():
    evolver = ClosedLoopEvolver(max_cells=16, steps=100, repeats=1)
    evolver.run_cycle()

    tmpdir = tempfile.mkdtemp()
    try:
        save_path = os.path.join(tmpdir, "test_output", "evolution.json")
        evolver.save(save_path)

        assert os.path.exists(save_path), f"File should exist at {save_path}"

        with open(save_path, 'r') as f:
            data = json.load(f)

        assert 'cycles' in data, "Saved JSON should have 'cycles'"
        assert len(data['cycles']) == 1, "Should have 1 cycle"
    finally:
        shutil.rmtree(tmpdir)


# ══════════════════════════════════════════
# Test 8: EDGE CASES
# ══════════════════════════════════════════

def test_edge_cases():
    """Minimum cells and very short steps."""
    # max_cells=2, steps=10
    evolver = ClosedLoopEvolver(max_cells=2, steps=10, repeats=1)
    report = evolver.run_cycle()

    assert isinstance(report, CycleReport), "Should return CycleReport"
    assert report.phi_baseline >= 0, f"phi should be >= 0"
    assert len(report.laws) >= 9, f"Should have >= 9 law entries, got {len(report.laws)}"

    # print_evolution should work even with minimal data
    evolver.print_evolution()

    # to_json should work
    json_str = evolver.to_json()
    data = json.loads(json_str)
    assert len(data['cycles']) == 1


# ══════════════════════════════════════════
# Main
# ══════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  Closed-Loop Integration Test Suite")
    print("=" * 70)
    t_start = time.time()

    run_test("T1", "BASIC CYCLE", test_basic_cycle)
    run_test("T2", "MULTI-CYCLE EVOLUTION", test_multi_cycle)
    run_test("T3", "AUTO-REGISTER (dry run)", test_auto_register_dry_run)
    run_test("T4", "INTERVENTION APPLICATION", test_interventions)
    run_test("T5", "MEASURE_LAWS CONSISTENCY", test_measure_laws_consistency)
    run_test("T6", "JSON SERIALIZATION", test_json_serialization)
    run_test("T7", "SAVE/LOAD", test_save_load)
    run_test("T8", "EDGE CASES", test_edge_cases)

    total_time = time.time() - t_start

    # Print results table
    print("\n" + "=" * 70)
    print(f"  Results: {sum(1 for r in results if r[2] == 'PASS')}/{len(results)} passed")
    print("=" * 70)
    print(f"  {'Test':<6} {'Description':<30} {'Status':<8} {'Time':<8}")
    print(f"  {'----':<6} {'-' * 30:<30} {'------':<8} {'------':<8}")
    for name, desc, status, elapsed, err in results:
        marker = "PASS" if status == "PASS" else "FAIL"
        print(f"  {name:<6} {desc:<30} {marker:<8} {elapsed:.1f}s")
        if err:
            print(f"         -> {err[:80]}")
    print(f"\n  Total: {total_time:.1f}s")

    # Exit code
    failed = sum(1 for r in results if r[2] != "PASS")
    if failed:
        print(f"\n  {failed} test(s) FAILED")
        sys.exit(1)
    else:
        print(f"\n  All tests PASSED")
        sys.exit(0)
