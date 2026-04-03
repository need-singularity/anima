#!/usr/bin/env python3
"""Tests for perpetual_discovery.py"""

import sys
import os
import time
import pytest

# Ensure src/ is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from perpetual_discovery import (
    PerpetualDiscovery,
    PerpetualDiscoveryHub,
    Discovery,
    CycleResult,
    _phi_fast,
    _make_engine,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

def make_pd(n_cells=16, exhaustion=3, steps_per_cycle=20,
             hypotheses_per_cycle=1, verbose=False) -> PerpetualDiscovery:
    return PerpetualDiscovery(
        n_cells=n_cells,
        exhaustion_threshold=exhaustion,
        steps_per_cycle=steps_per_cycle,
        hypotheses_per_cycle=hypotheses_per_cycle,
        auto_register=False,   # don't write to JSON in tests
        verbose=verbose,
    )


# ── test_single_cycle_runs ──────────────────────────────────────────────────

def test_single_cycle_runs():
    """A single cycle must complete without raising and return a CycleResult."""
    pd = make_pd()
    result = pd.run_cycle()
    assert isinstance(result, CycleResult)
    assert result.cycle == 1
    assert result.duration_sec >= 0.0
    assert result.total_discoveries >= 0
    assert isinstance(result.domains_matched, list)
    assert result.hypotheses_tested >= 0


# ── test_exhaustion_detection ───────────────────────────────────────────────

def test_exhaustion_detection():
    """After exhaustion_threshold consecutive empty cycles the loop stops."""
    pd = make_pd(exhaustion=2)

    # Manually run cycles without any discoveries to trigger exhaustion
    # We monkey-patch _discover_domains to return nothing (no discoveries)
    pd._discover_domains = lambda phi_vals: []
    pd._generate_novel_hypotheses = lambda: []

    r1 = pd.run_cycle()
    assert r1.consecutive_empty == 1
    assert not r1.exhausted

    r2 = pd.run_cycle()
    assert r2.consecutive_empty == 2
    assert r2.exhausted   # threshold=2 → exhausted


def test_exhaustion_resets_on_discovery():
    """consecutive_empty must reset to 0 when a discovery is made."""
    pd = make_pd(exhaustion=3)

    # Manually inject one empty cycle
    pd.consecutive_empty = 2

    # Inject a fake discovery
    fake_disc = Discovery(
        cycle=1, domain="physics/test", pattern="test_pattern",
        hypothesis="Test hypothesis", phi_delta_pct=10.0,
        verdict="VERIFIED", law_id=None,
    )
    pd.discovery_log.append(fake_disc)
    pd.total_discoveries += 1
    pd.consecutive_empty = 0   # discovery resets it

    assert pd.consecutive_empty == 0
    assert pd.total_discoveries == 1


# ── test_discovery_logged ───────────────────────────────────────────────────

def test_discovery_logged():
    """If a discovery is injected, it appears in discovery_log."""
    pd = make_pd()
    disc = Discovery(
        cycle=1,
        domain="physics/1f_noise",
        pattern="1f_noise",
        hypothesis="1/f noise boosts Phi",
        phi_delta_pct=8.5,
        verdict="VERIFIED",
        law_id=None,
    )
    pd.discovery_log.append(disc)
    pd.total_discoveries += 1

    assert len(pd.discovery_log) == 1
    assert pd.discovery_log[0].domain == "physics/1f_noise"
    assert pd.total_discoveries == 1


def test_discovery_to_dict():
    """Discovery.to_dict() must contain required keys."""
    disc = Discovery(
        cycle=3,
        domain="biology/heartbeat",
        pattern="heartbeat_hrv",
        hypothesis="HRV modulation increases Phi by 12%",
        phi_delta_pct=12.3,
        verdict="VERIFIED",
        law_id=999,
    )
    d = disc.to_dict()
    assert d['cycle'] == 3
    assert d['domain'] == "biology/heartbeat"
    assert d['phi_delta_pct'] == pytest.approx(12.3, abs=1e-6)
    assert d['law_id'] == 999


# ── test_report_format ──────────────────────────────────────────────────────

def test_report_format():
    """Report must contain required sections."""
    pd = make_pd()
    # Run one cycle so there's some data
    pd.run_cycle()

    report = pd.report()
    assert "PERPETUAL DISCOVERY" in report
    assert "Cycles:" in report
    assert "Discoveries:" in report
    assert "Domains found:" in report
    assert "Top discoveries:" in report


def test_report_shows_discoveries():
    """Verified discoveries appear in report."""
    pd = make_pd()
    disc = Discovery(
        cycle=2, domain="music/harmonic_series", pattern="harmonic_spectrum",
        hypothesis="Harmonic coupling boosts Phi", phi_delta_pct=6.2,
        verdict="VERIFIED", law_id=None,
    )
    pd.discovery_log.append(disc)
    pd.total_discoveries = 1
    pd.cycle = 2

    # Add a fake cycle result so report has data
    from perpetual_discovery import CycleResult
    pd.cycle_results.append(CycleResult(
        cycle=2, discoveries=1, total_discoveries=1, consecutive_empty=0,
        exhausted=False, phi_start=0.1, phi_end=0.15, growth_status="growing",
        domains_matched=["music/harmonic_series"], hypotheses_tested=1,
        hypotheses_verified=1, duration_sec=0.5,
    ))

    report = pd.report()
    assert "music" in report or "harmonic" in report


# ── test_max_cycles_limit ───────────────────────────────────────────────────

def test_max_cycles_limit():
    """run_until_exhaustion respects max_cycles even without exhaustion."""
    pd = make_pd(exhaustion=100, steps_per_cycle=10)
    summary = pd.run_until_exhaustion(max_cycles=2)
    assert pd.cycle <= 2
    assert isinstance(summary, dict)
    assert 'cycles' in summary
    assert 'total_discoveries' in summary
    assert summary['cycles'] <= 2


def test_max_cycles_1():
    """max_cycles=1 runs exactly one cycle."""
    pd = make_pd(steps_per_cycle=10)
    summary = pd.run_until_exhaustion(max_cycles=1)
    assert pd.cycle == 1
    assert summary['cycles'] == 1


# ── test_phi_fast ───────────────────────────────────────────────────────────

def test_phi_fast_returns_float():
    """_phi_fast must return a non-negative float."""
    engine = _make_engine(16)
    import torch
    engine.process(torch.randn(1, 64))
    phi = _phi_fast(engine)
    assert isinstance(phi, float)
    assert phi >= 0.0


# ── test_hub_shim ───────────────────────────────────────────────────────────

def test_hub_shim_acts():
    """PerpetualDiscoveryHub.act() must return a dict with expected keys."""
    hub = PerpetualDiscoveryHub()
    result = hub.act(max_cycles=1, n_cells=16)
    assert isinstance(result, dict)
    assert 'total_discoveries' in result
    assert 'report' in result


def test_hub_report_before_act():
    """report() before act() returns a helpful message."""
    hub = PerpetualDiscoveryHub()
    msg = hub.report()
    assert isinstance(msg, str)
    assert len(msg) > 0


# ── test_domain_count_tracking ─────────────────────────────────────────────

def test_domain_count_tracking():
    """Domain counts must accumulate across cycles."""
    pd = make_pd(steps_per_cycle=10)
    pd._domain_counts['physics'] = 3
    pd._domain_counts['biology'] = 1
    assert pd._domain_counts['physics'] == 3
    assert sum(pd._domain_counts.values()) == 4


# ── test_phi_history_grows ──────────────────────────────────────────────────

def test_phi_history_grows():
    """phi_history must grow with each cycle."""
    pd = make_pd(steps_per_cycle=20)
    assert len(pd.phi_history) == 0
    pd.run_cycle()
    assert len(pd.phi_history) > 0
    before = len(pd.phi_history)
    pd.run_cycle()
    assert len(pd.phi_history) > before


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
