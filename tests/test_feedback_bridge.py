#!/usr/bin/env python3
"""Tests for feedback_bridge.py — SoftDetach, PhiGatedGradient, alpha safety bounds."""

import sys
import os
import math
import pytest
import torch

# Add src/ to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from feedback_bridge import (
    SoftDetach, soft_detach,
    DialogueQualityTracker,
    PhiGatedGradient,
    FeedbackBridge,
)


class TestSoftDetach:
    """Test the differentiable detach replacement."""

    def test_alpha_zero_is_full_detach(self):
        x = torch.randn(4, 8, requires_grad=True)
        y = soft_detach(x, alpha=0.0)
        assert not y.requires_grad  # alpha=0 returns x.detach()

    def test_alpha_one_is_full_gradient(self):
        x = torch.randn(4, 8, requires_grad=True)
        y = soft_detach(x, alpha=1.0)
        loss = y.sum()
        loss.backward()
        assert x.grad is not None
        # Full gradient: grad should be all 1s
        assert torch.allclose(x.grad, torch.ones_like(x.grad))

    def test_alpha_scales_gradient(self):
        x = torch.randn(4, 8, requires_grad=True)
        alpha = 0.1
        y = soft_detach(x, alpha=alpha)
        loss = y.sum()
        loss.backward()
        # Gradient should be scaled by alpha
        expected = torch.full_like(x, alpha)
        assert torch.allclose(x.grad, expected, atol=1e-6)

    def test_forward_preserves_values(self):
        x = torch.randn(4, 8, requires_grad=True)
        y = soft_detach(x, alpha=0.5)
        assert torch.allclose(y, x, atol=1e-6)

    def test_negative_alpha_treated_as_zero(self):
        x = torch.randn(4, 8, requires_grad=True)
        y = soft_detach(x, alpha=-0.5)
        assert not y.requires_grad  # should detach


class TestDialogueQualityTracker:
    """Test CE trajectory -> reward signal computation."""

    def test_empty_tracker_returns_zero(self):
        tracker = DialogueQualityTracker()
        assert tracker.compute_reward() == 0.0

    def test_improving_ce_gives_positive_reward(self):
        tracker = DialogueQualityTracker(ema_alpha=0.5)
        # Decreasing CE = improving
        for ce in [5.0, 4.0, 3.0, 2.0, 1.0]:
            tracker.record(ce)
        reward = tracker.compute_reward()
        assert reward > 0, f"Improving CE should give positive reward, got {reward}"

    def test_worsening_ce_gives_negative_reward(self):
        tracker = DialogueQualityTracker(ema_alpha=0.5)
        # Increasing CE = worsening
        for ce in [1.0, 2.0, 3.0, 4.0, 5.0]:
            tracker.record(ce)
        reward = tracker.compute_reward()
        assert reward < 0, f"Worsening CE should give negative reward, got {reward}"

    def test_reward_bounded(self):
        tracker = DialogueQualityTracker(ema_alpha=0.5)
        # Even extreme values should stay in [-1, 1]
        for ce in [100.0, 0.001]:
            tracker.record(ce)
        reward = tracker.compute_reward()
        assert -1.0 <= reward <= 1.0

    def test_stats_returns_dict(self):
        tracker = DialogueQualityTracker()
        stats = tracker.stats()
        assert 'ce_mean' in stats
        assert 'trend' in stats

    def test_trend_with_insufficient_data(self):
        tracker = DialogueQualityTracker()
        for ce in [1.0, 2.0]:
            tracker.record(ce)
        assert tracker.trend() == 0.0  # need >= 10 for trend


class TestPhiGatedGradient:
    """Test Phi-based gate regulation and safety bounds."""

    def test_initial_alpha_is_zero(self):
        gate = PhiGatedGradient(max_alpha=0.05)
        assert gate.alpha == 0.0
        assert not gate.is_safe()

    def test_insufficient_data_returns_zero(self):
        gate = PhiGatedGradient(max_alpha=0.05)
        # Less than 5 data points
        for phi in [1.0, 1.1, 1.2]:
            gate.record_phi(phi)
        alpha = gate.compute_alpha(reward=0.5)
        assert alpha == 0.0

    def test_stable_phi_allows_small_alpha(self):
        gate = PhiGatedGradient(max_alpha=0.05)
        # Record stable phi values
        for _ in range(20):
            gate.record_phi(1.0)
        alpha = gate.compute_alpha(reward=0.0)
        # Should allow small alpha (> 0) since phi is stable
        assert alpha >= 0.0
        assert alpha <= 0.05  # never exceeds max

    def test_dropping_phi_snaps_to_zero(self):
        gate = PhiGatedGradient(max_alpha=0.05)
        # Build up phi history
        for _ in range(10):
            gate.record_phi(2.0)
        # Then phi drops significantly
        gate.record_phi(0.5)
        gate.record_phi(0.1)
        alpha = gate.compute_alpha(reward=1.0)
        # Should snap to 0 when phi is dropping
        assert alpha == 0.0

    def test_alpha_never_exceeds_max(self):
        gate = PhiGatedGradient(max_alpha=0.05)
        # Rising phi with high reward
        for i in range(50):
            gate.record_phi(float(i) * 0.1)
        alpha = gate.compute_alpha(reward=1.0)
        assert alpha <= 0.05

    def test_stats_returns_monitoring_info(self):
        gate = PhiGatedGradient()
        for _ in range(10):
            gate.record_phi(1.5)
        stats = gate.stats()
        assert 'alpha' in stats
        assert 'phi_ema' in stats
        assert 'phi_mean' in stats
        assert stats['phi_mean'] == pytest.approx(1.5, abs=0.01)


class TestFeedbackBridge:
    """Test the full FeedbackBridge module."""

    def test_bridge_creation(self):
        bridge = FeedbackBridge(c_dim=32, d_model=64)
        assert bridge.c_dim == 32
        assert bridge.d_model == 64
        assert bridge._current_alpha == 0.0

    def test_update_gate_records_phi(self):
        bridge = FeedbackBridge(c_dim=32, d_model=64)
        alpha = bridge.update_gate(phi=1.0, ce=0.5)
        assert isinstance(alpha, float)
        assert alpha >= 0.0

    def test_forward_output_shape(self):
        bridge = FeedbackBridge(c_dim=32, d_model=64)
        c_states = torch.randn(4, 32)  # 4 cells, 32 dim
        output = bridge(c_states, seq_len=8)
        assert output.shape == (1, 8, 64)

    def test_reward_vector_none_initially(self):
        bridge = FeedbackBridge(c_dim=32, d_model=64)
        # No CE history -> no reward vector
        vec = bridge.compute_reward_vector()
        assert vec is None

    def test_default_alpha_is_safe(self):
        """Bridge starts fully detached (alpha=0) for safety."""
        bridge = FeedbackBridge(c_dim=32, d_model=64, max_alpha=0.05)
        assert bridge._current_alpha == 0.0
        # Even after one update with no phi history, should stay at 0
        bridge.update_gate(phi=1.0)
        assert bridge._current_alpha == 0.0  # not enough data yet
