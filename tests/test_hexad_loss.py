#!/usr/bin/env python3
"""Tests for hexad_loss.py — HexadLoss forward, phase schedule, individual module losses."""

import sys
import os
import pytest
import torch

# Add src/ to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hexad_loss import (
    HexadLoss, WillModule, SenseModule, MemoryModule, EthicsModule,
)


class TestPhaseSchedule:
    """Test Law 60 phase-based activation schedule."""

    def test_phase1_only_c(self):
        hexad = HexadLoss(dim=64)
        active = hexad.get_active_losses(progress=0.0)
        assert 'C' in active
        assert 'D' not in active
        assert 'W' not in active

    def test_phase2_c_d_m(self):
        hexad = HexadLoss(dim=64)
        active = hexad.get_active_losses(progress=0.5)
        assert 'C' in active
        assert 'D' in active
        assert 'M' in active
        assert 'W' not in active
        assert 'S' not in active
        assert 'E' not in active

    def test_phase3_all_modules(self):
        hexad = HexadLoss(dim=64)
        active = hexad.get_active_losses(progress=0.9)
        for name in ['C', 'D', 'W', 'S', 'M', 'E']:
            assert name in active, f"Phase 3 should activate {name}"

    def test_phase_boundaries_exact(self):
        hexad = HexadLoss(dim=64)
        # At exactly 0.2 -> Phase 2 starts
        active_at_boundary = hexad.get_active_losses(progress=0.2)
        assert 'D' in active_at_boundary
        # At exactly 0.7 -> Phase 3 starts
        active_at_boundary = hexad.get_active_losses(progress=0.7)
        assert 'W' in active_at_boundary

    def test_phase_name(self):
        hexad = HexadLoss(dim=64)
        assert hexad.get_phase_name(0.1) == "Phase1:C"
        assert hexad.get_phase_name(0.5) == "Phase2:C+D+M"
        assert hexad.get_phase_name(0.9) == "Phase3:Hexad"

    def test_disabled_modules_excluded(self):
        hexad = HexadLoss(dim=64, disabled={'D', 'M'})
        active = hexad.get_active_losses(progress=0.9)
        assert 'D' not in active
        assert 'M' not in active
        assert 'W' in active  # not disabled


class TestIndividualLosses:
    """Test each module's loss function independently."""

    def test_loss_C_phi_increase(self):
        hexad = HexadLoss(dim=64)
        # Phi increased: ratchet penalty = 0, loss = -phi
        loss = hexad.loss_C(phi=2.0, phi_prev=1.0)
        assert loss.item() == pytest.approx(-2.0, abs=1e-5)

    def test_loss_C_phi_decrease_penalty(self):
        hexad = HexadLoss(dim=64)
        # Phi decreased: ratchet penalty kicks in
        loss = hexad.loss_C(phi=1.0, phi_prev=2.0)
        # -1.0 + 5.0 * (2.0 - 1.0) = -1.0 + 5.0 = 4.0
        assert loss.item() == pytest.approx(4.0, abs=1e-5)

    def test_loss_D_cross_entropy(self):
        hexad = HexadLoss(dim=64)
        # Batch=4, Seq=8, Vocab=256
        logits = torch.randn(4, 8, 256)
        targets = torch.randint(0, 256, (4, 8))
        loss = hexad.loss_D(logits, targets)
        assert loss.item() > 0  # CE is always positive
        assert not torch.isnan(loss)

    def test_loss_W_emotion_prediction(self):
        hexad = HexadLoss(dim=64)
        c_signal = torch.randn(8, 64)  # 8 cells, 64 dim
        emotion = torch.tensor([0.5, 0.3, 0.1])  # arousal, valence, dominance
        loss = hexad.loss_W(c_signal, emotion)
        assert loss.item() >= 0  # MSE is non-negative
        assert not torch.isnan(loss)

    def test_loss_M_contrastive(self):
        hexad = HexadLoss(dim=64)
        c_signal = torch.randn(4, 64)
        # Need at least 2 stores for contrastive
        hexad.memory_module.store(torch.randn(4, 64), torch.randn(4, 64))
        hexad.memory_module.store(torch.randn(4, 64), torch.randn(4, 64))
        loss = hexad.loss_M(c_signal)
        assert not torch.isnan(loss)


class TestHexadForward:
    """Test the full forward pass combining all losses."""

    def test_forward_phase1_minimal(self):
        hexad = HexadLoss(dim=64)
        result = hexad(phi=1.0, phi_prev=0.5, progress=0.1)
        assert 'total' in result
        assert 'L_C' in result
        assert 'phase' in result
        assert result['phase'] == "Phase1:C"
        # In Phase 1, total = 0 (C has weight 0)
        assert result['total'].item() == pytest.approx(0.0, abs=1e-5)

    def test_forward_phase2_with_decoder(self):
        hexad = HexadLoss(dim=64)
        logits = torch.randn(2, 16, 256)
        targets = torch.randint(0, 256, (2, 16))
        c_signal = torch.randn(4, 64)
        result = hexad(
            phi=1.0, phi_prev=0.8,
            logits_fwd=logits, targets_fwd=targets,
            consciousness_signal=c_signal,
            progress=0.5,
        )
        assert result['phase'] == "Phase2:C+D+M"
        assert 'L_D' in result
        assert result['total'].item() > 0

    def test_forward_phase3_full_hexad(self):
        hexad = HexadLoss(dim=64)
        logits = torch.randn(2, 16, 256)
        targets = torch.randint(0, 256, (2, 16))
        c_signal = torch.randn(4, 64)
        input_sig = torch.randn(2, 16, 64)
        result = hexad(
            phi=1.0, phi_prev=0.8,
            logits_fwd=logits, targets_fwd=targets,
            consciousness_signal=c_signal,
            input_signal=input_sig,
            progress=0.9,
        )
        assert result['phase'] == "Phase3:Hexad"
        assert 'L_D' in result
        assert 'L_W' in result
        assert 'L_S' in result
        assert 'L_E' in result

    def test_forward_backward_does_not_crash(self):
        hexad = HexadLoss(dim=64)
        logits = torch.randn(2, 16, 256, requires_grad=True)
        targets = torch.randint(0, 256, (2, 16))
        c_signal = torch.randn(4, 64, requires_grad=True)
        result = hexad(
            phi=1.0, phi_prev=0.8,
            logits_fwd=logits, targets_fwd=targets,
            consciousness_signal=c_signal,
            progress=0.5,
        )
        result['total'].backward()
        assert logits.grad is not None
