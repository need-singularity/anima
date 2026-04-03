#!/usr/bin/env python3
"""Tests for auto_discovery_loop.py"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from auto_discovery_loop import detect_anomalies, discover_laws, generate_improvements, RecursiveLoop


def test_detect_anomalies_low_phi():
    metrics = {'phi_compression_pct': 20, 'chaos_score': 0.5}
    anomalies = detect_anomalies(metrics)
    assert any(a['type'] == 'LOW_PHI_COMPRESSION' for a in anomalies)


def test_detect_anomalies_chaos_extreme():
    metrics = {'phi_compression_pct': 50, 'chaos_score': 0.995}
    anomalies = detect_anomalies(metrics)
    assert any(a['type'] == 'CHAOS_EXTREME' for a in anomalies)


def test_detect_anomalies_phi_drop():
    prev = {'phi_approx': 1.0, 'phi_compression_pct': 50}
    curr = {'phi_approx': 0.5, 'phi_compression_pct': 50, 'chaos_score': 0.5}
    anomalies = detect_anomalies(curr, prev)
    assert any(a['type'] == 'PHI_DROP' for a in anomalies)


def test_detect_anomalies_no_issues():
    metrics = {'phi_compression_pct': 80, 'chaos_score': 0.5}
    anomalies = detect_anomalies(metrics)
    assert len(anomalies) == 0


def test_discover_laws_attractor_six():
    metrics = {'attractor_count': 6, 'step': 100, 'phi_approx': 0.5}
    candidates = discover_laws(metrics)
    assert any('n=6' in c['formula'] for c in candidates)


def test_discover_laws_phi_improvement():
    prev = {'phi_compression_pct': 30, 'step': 100}
    curr = {'phi_compression_pct': 40, 'step': 200, 'phi_approx': 0.5,
            'attractor_count': 3, 'chaos_score': 0.5, 'hurst_exponent': 0.7}
    candidates = discover_laws(curr, prev)
    assert any('compression improves' in c['formula'] for c in candidates)


def test_discover_laws_consciousness_dilution():
    metrics = {'phi_approx': 0.01, 'step': 50, 'attractor_count': 3,
               'chaos_score': 0.5, 'hurst_exponent': 0.7}
    candidates = discover_laws(metrics)
    assert any('dilution' in c['formula'] for c in candidates)


def test_generate_improvements():
    candidates = [
        {'formula': 'test', 'improvement': 'increase_alpha'},
        {'formula': 'test2', 'improvement': 'reduce_chaos'},
    ]
    improvements = generate_improvements(candidates)
    types = [i['type'] for i in improvements]
    assert 'IMPROVE_ALPHA' in types
    assert 'REDUCE_CHAOS' in types


def test_generate_improvements_no_improvement_key():
    candidates = [{'formula': 'test', 'confidence': 'HIGH'}]
    improvements = generate_improvements(candidates)
    assert len(improvements) == 0


def test_recursive_loop_init():
    loop = RecursiveLoop()
    assert loop.state['generation'] == 0 or loop.state['generation'] >= 0
    assert 'total_scans' in loop.state
    assert 'active_rules' in loop.state


def test_recursive_loop_evolve_rules_no_crash():
    loop = RecursiveLoop()
    # Should not crash even with minimal state
    loop.evolve_rules()


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
