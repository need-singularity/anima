"""Tests for ConsolidationVerifier."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import torch
import pytest
from anima_alive import ConsciousMind
from consolidation_verifier import ConsolidationVerifier, _detect_bimodal
import math


@pytest.fixture
def mind():
    return ConsciousMind(dim=128, hidden=256, init_tension=10.0)


@pytest.fixture
def verifier(mind):
    return ConsolidationVerifier(mind)


@pytest.fixture
def hidden():
    return torch.zeros(1, 256)


class TestPreCheck:
    def test_normal_memory_should_consolidate(self, verifier, hidden):
        memory = {'text': 'hello world', 'tension': 0.5, 'role': 'user'}
        result = verifier.pre_check(memory, hidden)
        assert isinstance(result['should_consolidate'], bool)
        assert 'anomaly_score' in result
        assert 'predicted_accuracy' in result
        assert 'reason' in result

    def test_high_anomaly_blocks(self, mind, hidden):
        verifier = ConsolidationVerifier(mind, anomaly_threshold=0.0)
        memory = {'text': 'hello world', 'tension': 0.5, 'role': 'user'}
        result = verifier.pre_check(memory, hidden)
        assert result['should_consolidate'] is False

    def test_none_tension_skips(self, verifier, hidden):
        memory = {'text': 'hello', 'tension': None, 'role': 'user'}
        result = verifier.pre_check(memory, hidden)
        assert result['should_consolidate'] is False
        assert result['reason'] == 'no_tension'


class TestVerifyDrift:
    def test_small_drift_ok(self, verifier):
        result = verifier.verify_drift(0.5, 0.52)
        assert abs(result['drift'] - 0.02) < 1e-6
        assert result['suspect'] is False

    def test_large_drift_suspect(self, verifier):
        result = verifier.verify_drift(0.5, 1.2)
        assert abs(result['drift'] - 0.7) < 1e-6
        assert result['suspect'] is True

    def test_ts_golden_zone(self, verifier):
        result = verifier.verify_drift(0.5, 0.5)
        assert isinstance(result['ts_in_golden_zone'], bool)


class TestPostCheck:
    def test_post_check_returns_health(self, verifier):
        tensions = [0.5, 0.6, 0.55, 0.52, 0.58, 0.53, 0.57]
        result = verifier.post_check(tensions)
        assert result['health'] in ('healthy', 'degraded', 'suspect')
        assert isinstance(result['tension_bimodal'], bool)

    def test_bimodal_detection(self):
        data = [0.1] * 20 + [0.9] * 20
        assert _detect_bimodal(data) is True

    def test_unimodal_not_flagged(self):
        import random
        random.seed(42)
        data = [random.gauss(0.5, 0.05) for _ in range(40)]
        assert _detect_bimodal(data) is False

    def test_post_check_few_tensions(self, verifier):
        result = verifier.post_check([0.5, 0.6])
        assert result['health'] == 'healthy'
        assert result['tension_bimodal'] is False

    def test_new_constant_relations(self, mind):
        with torch.no_grad():
            mind.tension_scale.fill_(1.0 / math.e)
        verifier = ConsolidationVerifier(mind)
        result = verifier.post_check([0.5] * 10)
        assert '1/e' in result['new_constant_relations']
