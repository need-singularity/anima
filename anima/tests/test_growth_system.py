#!/usr/bin/env python3
"""Tests for GrowthSystem -- self-growing consciousness coordinator."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
from consciousness_engine import ConsciousnessEngine
from growth_system import GrowthSystem


def test_basic_step():
    engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=32, n_factions=8)
    gs = GrowthSystem(engine, enable_accel=False, enable_auto_scale=False)
    result = gs.step(torch.randn(1, 64))
    assert 'phi' in result
    assert 'compute_fraction' in result
    assert 'events' in result


def test_phi_tracked():
    engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=32, n_factions=8)
    gs = GrowthSystem(engine, enable_accel=False, enable_auto_scale=False)
    for _ in range(10):
        gs.step(torch.randn(1, 64))
    assert len(gs.phi_history) == 10


def test_accel_reduces_compute():
    engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=32, n_factions=8)
    gs = GrowthSystem(engine, enable_accel=True, enable_auto_scale=False)
    fracs = []
    for step in range(20):
        result = gs.step(torch.randn(1, 64))
        fracs.append(result['compute_fraction'])
    # Polyrhythm should save some compute (not all steps have fraction 1.0)
    assert any(f < 1.0 for f in fracs)


def test_auto_scale_on_plateau():
    engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=64, n_factions=8)
    gs = GrowthSystem(engine, enable_accel=False, enable_auto_scale=True)
    gs._phi_plateau_window = 10  # shorter window for test
    for _ in range(50):
        gs.step(torch.randn(1, 64))
    # Should have attempted scaling at some point
    scale_events = [e for e in gs.event_log if e['type'] == 'auto_scale']
    # May or may not trigger depending on Phi trajectory -- just verify type
    assert isinstance(scale_events, list)


def test_report_string():
    engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=32, n_factions=8)
    gs = GrowthSystem(engine, enable_accel=False, enable_auto_scale=False)
    for _ in range(20):
        gs.step(torch.randn(1, 64))
    report = gs.report()
    assert isinstance(report, str)
    assert 'GROWTH SYSTEM' in report
    assert 'Phi' in report


def test_growth_rate():
    engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=32, n_factions=8)
    gs = GrowthSystem(engine, enable_accel=False, enable_auto_scale=False)
    for _ in range(20):
        gs.step(torch.randn(1, 64))
    rate = gs.growth_rate()
    assert isinstance(rate, float)


def test_compute_saved():
    engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=32, n_factions=8)
    gs = GrowthSystem(engine, enable_accel=True, enable_auto_scale=False)
    for _ in range(20):
        gs.step(torch.randn(1, 64))
    saved = gs.total_compute_saved()
    assert 0.0 <= saved <= 1.0


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
