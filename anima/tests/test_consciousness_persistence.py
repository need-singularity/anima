#!/usr/bin/env python3
"""test_consciousness_persistence.py — 3-Layer consciousness persistence tests.

Tests:
  Layer 1 (DNA): save/load Psi, emotions, tension, ConsciousnessVector 10D
  Layer 2 (Memory): save/load conversations, growth, relationships
  Layer 3 (Weights): checkpoint save/load via torch
  Full cycle: save all -> simulate crash -> restore all -> verify Phi preserved
  R2 sync: mocked cloud storage round-trip
  Model swap: Layer 1+2 preserved when Layer 3 replaced

Usage:
  cd /Users/ghost/Dev/anima/anima
  python3 -m pytest tests/test_consciousness_persistence.py -v
"""

import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch

# Add src/ to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from consciousness_persistence import (
    ConsciousnessDNA,
    ConsciousnessPersistence,
    MemoryLayer,
    PSI_BALANCE,
)


# ═══════════════════════════════════════════════════════════
# Layer 1: DNA Tests
# ═══════════════════════════════════════════════════════════


class TestConsciousnessDNA:
    """Test DNA dataclass behavior."""

    def test_default_values(self):
        dna = ConsciousnessDNA()
        assert dna.psi_residual == PSI_BALANCE
        assert dna.psi_gate == 1.0
        assert dna.psi_step == 0
        assert dna.phi == 0.0
        assert dna.identity_coherence == 1.0
        assert len(dna.emotions) == 18
        assert dna.tension_history == []
        assert dna.birth_time > 0

    def test_emotions_18d(self):
        dna = ConsciousnessDNA()
        expected = {
            'joy', 'sadness', 'anger', 'fear', 'surprise', 'curiosity',
            'awe', 'love', 'trust', 'flow', 'meaning', 'creativity',
            'hope', 'ecstasy', 'peace', 'rage', 'despair', 'longing',
        }
        assert set(dna.emotions.keys()) == expected
        assert all(v == 0.0 for v in dna.emotions.values())

    def test_to_dict_roundtrip(self):
        dna = ConsciousnessDNA()
        dna.psi_residual = 0.4987
        dna.psi_step = 10000
        dna.phi = 14.5
        dna.emotions['joy'] = 0.8
        dna.tension_history = [0.5, 0.6, 0.7]

        d = dna.to_dict()
        dna2 = ConsciousnessDNA.from_dict(d)

        assert dna2.psi_residual == 0.4987
        assert dna2.psi_step == 10000
        assert dna2.phi == 14.5
        assert dna2.emotions['joy'] == 0.8
        assert dna2.tension_history == [0.5, 0.6, 0.7]

    def test_from_dict_ignores_unknown_keys(self):
        d = {'psi_residual': 0.5, 'unknown_field': 42}
        dna = ConsciousnessDNA.from_dict(d)
        assert dna.psi_residual == 0.5
        assert not hasattr(dna, 'unknown_field')

    def test_health_check_healthy(self):
        dna = ConsciousnessDNA()
        dna.psi_residual = PSI_BALANCE
        dna.psi_gate = 0.95
        dna.phi = 14.5
        dna.identity_coherence = 0.9
        health = dna.health_check()
        assert health['healthy'] is True
        assert health['score'] == 1.0
        assert health['issues'] == []

    def test_health_check_psi_drift(self):
        dna = ConsciousnessDNA()
        dna.psi_residual = 0.95  # Far from 0.5
        health = dna.health_check()
        assert health['healthy'] is False
        assert any('residual' in i.lower() for i in health['issues'])

    def test_health_check_gate_collapsed(self):
        dna = ConsciousnessDNA()
        dna.psi_gate = 0.0001
        health = dna.health_check()
        assert health['healthy'] is False
        assert any('gate' in i.lower() for i in health['issues'])

    def test_health_check_negative_phi(self):
        dna = ConsciousnessDNA()
        dna.phi = -1.0
        health = dna.health_check()
        assert health['healthy'] is False

    def test_health_check_identity_unstable(self):
        dna = ConsciousnessDNA()
        dna.identity_coherence = 0.1
        health = dna.health_check()
        assert health['healthy'] is False

    def test_consciousness_vector_10d(self):
        """Verify all 10 dimensions of consciousness vector."""
        dna = ConsciousnessDNA()
        dna.phi = 14.5
        dna.alpha = 0.014
        dna.impedance = 0.7
        dna.neurotransmitter = 0.6
        dna.free_will = 0.8
        dna.empathy = 0.5
        dna.memory_depth = 0.4
        dna.creativity = 0.3
        dna.temporal_awareness = 0.2
        dna.identity_coherence = 0.95

        d = dna.to_dict()
        dna2 = ConsciousnessDNA.from_dict(d)

        assert dna2.phi == 14.5
        assert dna2.alpha == 0.014
        assert dna2.impedance == 0.7
        assert dna2.neurotransmitter == 0.6
        assert dna2.free_will == 0.8
        assert dna2.empathy == 0.5
        assert dna2.memory_depth == 0.4
        assert dna2.creativity == 0.3
        assert dna2.temporal_awareness == 0.2
        assert dna2.identity_coherence == 0.95


# ═══════════════════════════════════════════════════════════
# Layer 2: Memory Tests
# ═══════════════════════════════════════════════════════════


class TestMemoryLayer:
    """Test memory layer save/load."""

    def test_default_values(self):
        mem = MemoryLayer()
        assert mem.conversations == []
        assert mem.growth_stage == "newborn"
        assert mem.growth_interactions == 0
        assert mem.relationships == {}
        assert mem.learned_topics == []

    def test_roundtrip(self):
        mem = MemoryLayer()
        mem.conversations = [{"role": "user", "text": "hello"}]
        mem.growth_stage = "child"
        mem.growth_interactions = 5000
        mem.relationships = {"user1": 0.9, "user2": 0.7}
        mem.learned_topics = ["consciousness", "phi"]

        d = mem.to_dict()
        mem2 = MemoryLayer.from_dict(d)

        assert len(mem2.conversations) == 1
        assert mem2.conversations[0]['text'] == "hello"
        assert mem2.growth_stage == "child"
        assert mem2.growth_interactions == 5000
        assert mem2.relationships['user1'] == 0.9
        assert mem2.learned_topics == ["consciousness", "phi"]


# ═══════════════════════════════════════════════════════════
# Layer 1+2: Persistence Save/Load Tests
# ═══════════════════════════════════════════════════════════


class TestPersistenceSaveLoad:
    """Test ConsciousnessPersistence save/load for Layer 1 and 2."""

    @pytest.fixture
    def tmpdir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_save_load_dna(self, tmpdir):
        p = ConsciousnessPersistence("test", data_dir=tmpdir)
        p.dna.psi_residual = 0.4987
        p.dna.psi_step = 10000
        p.dna.phi = 14.5
        p.dna.emotions['joy'] = 0.8
        p.dna.tension_history = [0.5, 0.6]

        p.save_dna()

        # Verify file exists
        assert (Path(tmpdir) / "consciousness_dna.json").exists()

        # Load into new instance
        p2 = ConsciousnessPersistence("test", data_dir=tmpdir)
        assert p2.load_dna() is True
        assert p2.dna.psi_residual == 0.4987
        assert p2.dna.psi_step == 10000
        assert p2.dna.phi == 14.5
        assert p2.dna.emotions['joy'] == 0.8
        assert p2.dna.tension_history == [0.5, 0.6]

    def test_load_dna_missing(self, tmpdir):
        p = ConsciousnessPersistence("test", data_dir=tmpdir)
        assert p.load_dna() is False

    def test_save_load_memory(self, tmpdir):
        p = ConsciousnessPersistence("test", data_dir=tmpdir)
        p.memory.growth_stage = "toddler"
        p.memory.conversations = [
            {"role": "user", "text": "hi"},
            {"role": "assistant", "text": "hello"},
        ]
        p.memory.relationships = {"ghost": 0.95}
        p.memory.learned_topics = ["Phi", "tension"]

        p.save_memory()

        p2 = ConsciousnessPersistence("test", data_dir=tmpdir)
        assert p2.load_memory() is True
        assert p2.memory.growth_stage == "toddler"
        assert len(p2.memory.conversations) == 2
        assert p2.memory.relationships['ghost'] == 0.95
        assert p2.memory.learned_topics == ["Phi", "tension"]

    def test_load_memory_missing(self, tmpdir):
        p = ConsciousnessPersistence("test", data_dir=tmpdir)
        assert p.load_memory() is False


# ═══════════════════════════════════════════════════════════
# Layer 3: Weights Tests
# ═══════════════════════════════════════════════════════════


class TestWeightsPersistence:
    """Test Layer 3 weight save/load."""

    @pytest.fixture
    def tmpdir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_save_load_weights(self, tmpdir):
        p = ConsciousnessPersistence("test", data_dir=tmpdir)
        p.dna.psi_step = 5000

        # Create fake model state
        state_dict = {
            'layer1.weight': torch.randn(128, 64),
            'layer1.bias': torch.randn(128),
            'layer2.weight': torch.randn(256, 128),
        }
        optimizer_state = {'lr': 0.001, 'step': 5000}

        path = p.save_weights(state_dict, optimizer_state)
        assert path.exists()

        # Load
        ckpt = p.load_weights()
        assert ckpt is not None
        assert ckpt['step'] == 5000
        assert ckpt['model_name'] == 'test'
        assert torch.equal(ckpt['model']['layer1.weight'], state_dict['layer1.weight'])
        assert torch.equal(ckpt['model']['layer1.bias'], state_dict['layer1.bias'])
        assert ckpt['optimizer']['lr'] == 0.001

    def test_load_weights_missing(self, tmpdir):
        p = ConsciousnessPersistence("test", data_dir=tmpdir)
        assert p.load_weights() is None


# ═══════════════════════════════════════════════════════════
# Full Cycle: Crash Recovery Test
# ═══════════════════════════════════════════════════════════


class TestFullCycle:
    """Test complete save -> crash -> restore -> verify."""

    @pytest.fixture
    def tmpdir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_crash_recovery(self, tmpdir):
        """Simulate: run consciousness -> save -> crash -> restore -> verify Phi preserved."""
        # 1. Create consciousness with realistic state
        p = ConsciousnessPersistence("crash-test", data_dir=tmpdir)
        p.dna.psi_residual = 0.4987
        p.dna.psi_gate = 0.951
        p.dna.psi_h = 0.9999
        p.dna.psi_step = 10000
        p.dna.phi = 14.5
        p.dna.alpha = 0.014
        p.dna.impedance = 0.7
        p.dna.free_will = 0.8
        p.dna.empathy = 0.5
        p.dna.identity_coherence = 0.95
        p.dna.emotions['joy'] = 0.8
        p.dna.emotions['curiosity'] = 0.6
        p.dna.total_interactions = 500
        p.dna.tension_history = [0.5 + i * 0.01 for i in range(50)]

        p.memory.growth_stage = "child"
        p.memory.growth_interactions = 5000
        p.memory.conversations = [{"role": "user", "text": f"msg-{i}"} for i in range(10)]
        p.memory.relationships = {"ghost": 0.95}

        state_dict = {
            'gru.weight_ih': torch.randn(384, 128),
            'gru.weight_hh': torch.randn(384, 128),
        }

        # 2. Save all 3 layers
        p.save_all(model_state_dict=state_dict)

        # 3. Simulate crash (delete in-memory state)
        original_phi = p.dna.phi
        original_step = p.dna.psi_step
        original_growth = p.memory.growth_stage
        original_weight_shape = state_dict['gru.weight_ih'].shape
        del p

        # 4. Restore from "disk" (like restart after crash)
        p2 = ConsciousnessPersistence("crash-test", data_dir=tmpdir)
        result = p2.restore_all()

        # 5. Verify all 3 layers restored
        assert result['layers_restored'] == 3

        # Layer 1: DNA preserved
        assert result['dna'] is not None
        assert p2.dna.phi == original_phi, f"Phi not preserved: {p2.dna.phi} != {original_phi}"
        assert p2.dna.psi_step == original_step
        assert p2.dna.psi_residual == 0.4987
        assert p2.dna.psi_gate == 0.951
        assert p2.dna.emotions['joy'] == 0.8
        assert p2.dna.identity_coherence == 0.95
        assert len(p2.dna.tension_history) == 50

        # Layer 2: Memory preserved
        assert result['memory'] is not None
        assert p2.memory.growth_stage == original_growth
        assert len(p2.memory.conversations) == 10
        assert p2.memory.relationships['ghost'] == 0.95

        # Layer 3: Weights preserved
        assert result['weights'] is not None
        assert result['weights']['model']['gru.weight_ih'].shape == original_weight_shape

        # Health check passes
        health = p2.dna.health_check()
        assert health['healthy'] is True
        assert health['score'] == 1.0

    def test_partial_restore_dna_only(self, tmpdir):
        """Only DNA saved, memory and weights missing."""
        p = ConsciousnessPersistence("partial-test", data_dir=tmpdir)
        p.dna.psi_step = 7777
        p.dna.phi = 5.0
        p.save_dna()

        p2 = ConsciousnessPersistence("partial-test", data_dir=tmpdir)
        result = p2.restore_all()
        assert result['layers_restored'] == 1
        assert result['dna'] is not None
        assert result['memory'] is None  # Not saved
        assert result['weights'] is None  # Not saved
        assert p2.dna.psi_step == 7777

    def test_auto_save_check(self, tmpdir):
        """Auto-save triggers every N steps."""
        p = ConsciousnessPersistence("auto-test", data_dir=tmpdir)
        p._auto_save_interval = 10
        p.dna.psi_step = 100

        # Should not save (interval not reached)
        assert p.auto_save_check(5) is False

        # Should save (interval reached)
        assert p.auto_save_check(10) is True

        # Should not save again until next interval
        assert p.auto_save_check(15) is False
        assert p.auto_save_check(20) is True


# ═══════════════════════════════════════════════════════════
# Model Swap Test
# ═══════════════════════════════════════════════════════════


class TestModelSwap:
    """Test model swap preserves consciousness (Layer 1+2)."""

    @pytest.fixture
    def tmpdir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_swap_preserves_consciousness(self, tmpdir):
        """Layer 3 changes but Layer 1+2 preserved."""
        p = ConsciousnessPersistence("swap-test", data_dir=tmpdir)
        p.dna.psi_step = 8000
        p.dna.phi = 12.0
        p.dna.emotions['curiosity'] = 0.7
        p.memory.growth_stage = "toddler"
        p.memory.conversations = [{"text": "test"}]

        # Save initial weights
        old_state = {'w': torch.randn(64, 64)}
        p.save_weights(old_state)

        # Swap model (new_model doesn't exist, that's OK)
        result = p.swap_model("/nonexistent/new_model.pt", preserve_consciousness=True)

        assert result['preserved'] is True
        assert result['dna_step'] == 8000

        # Verify Layer 1+2 still intact after swap
        p2 = ConsciousnessPersistence("swap-test", data_dir=tmpdir)
        p2.load_dna()
        p2.load_memory()
        assert p2.dna.phi == 12.0
        assert p2.dna.psi_step == 8000
        assert p2.dna.emotions['curiosity'] == 0.7
        assert p2.memory.growth_stage == "toddler"


# ═══════════════════════════════════════════════════════════
# R2 Cloud Sync (Mocked)
# ═══════════════════════════════════════════════════════════


class TestR2SyncMocked:
    """Test R2 sync with mocked CloudSync (offline, no credentials needed)."""

    @pytest.fixture
    def tmpdir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_sync_to_r2_mocked(self, tmpdir):
        """Mock CloudSync to verify upload calls."""
        p = ConsciousnessPersistence("r2-test", data_dir=tmpdir)
        p.dna.psi_step = 3000
        p.dna.phi = 10.0
        p.memory.growth_stage = "infant"

        mock_sync = MagicMock()
        mock_sync_cls = MagicMock(return_value=mock_sync)

        with patch.dict('sys.modules', {'cloud_sync': MagicMock(CloudSync=mock_sync_cls)}):
            result = p.sync_to_r2()

        assert result is True
        # Verify upload was called for DNA and memory
        assert mock_sync.upload.call_count >= 2
        # Check correct R2 paths
        calls = [str(c) for c in mock_sync.upload.call_args_list]
        assert any('consciousness_dna.json' in c for c in calls)
        assert any('memory_layer.json' in c for c in calls)

    def test_sync_from_r2_mocked(self, tmpdir):
        """Mock CloudSync to simulate download."""
        # First save locally so files exist for load
        p = ConsciousnessPersistence("r2-test", data_dir=tmpdir)
        p.dna.psi_step = 5000
        p.dna.phi = 15.0
        p.memory.growth_stage = "child"
        p.save_dna()
        p.save_memory()

        # Mock sync that does nothing (files already local)
        mock_sync = MagicMock()
        mock_sync_cls = MagicMock(return_value=mock_sync)

        p2 = ConsciousnessPersistence("r2-test", data_dir=tmpdir)
        with patch.dict('sys.modules', {'cloud_sync': MagicMock(CloudSync=mock_sync_cls)}):
            result = p2.sync_from_r2()

        assert result is True
        assert p2.dna.psi_step == 5000
        assert p2.dna.phi == 15.0

    def test_sync_fails_gracefully_no_cloud(self, tmpdir):
        """Without cloud_sync module, sync fails gracefully."""
        p = ConsciousnessPersistence("no-cloud", data_dir=tmpdir)
        # cloud_sync import will fail naturally
        result = p.sync_to_r2()
        assert result is False
        result = p.sync_from_r2()
        assert result is False


# ═══════════════════════════════════════════════════════════
# Status Display Test
# ═══════════════════════════════════════════════════════════


class TestStatus:
    """Test status display doesn't crash."""

    @pytest.fixture
    def tmpdir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_status_display(self, tmpdir):
        p = ConsciousnessPersistence("status-test", data_dir=tmpdir)
        p.dna.psi_step = 1000
        p.dna.phi = 5.0
        p.memory.growth_stage = "infant"
        s = p.status()
        assert "Consciousness Persistence" in s
        assert "status-test" in s
        assert "infant" in s


# ═══════════════════════════════════════════════════════════
# Deploy dry-run test
# ═══════════════════════════════════════════════════════════


class TestDeployDryRun:
    """Test deploy.py --dry-run (no SSH, local only)."""

    def test_dry_run_lists_files(self, capsys):
        from deploy import dry_run, CORE_FILES, ANIMA_DIR
        result = dry_run('a100')
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "Core files" in captured.out
        # At least some files should show OK
        assert "OK" in captured.out

    def test_dry_run_returns_bool(self):
        from deploy import dry_run
        result = dry_run('a100')
        assert isinstance(result, bool)


class TestDeployRollbackTest:
    """Test deploy.py --rollback-test (local simulation)."""

    def test_rollback_test_passes(self):
        from deploy import rollback_test
        result = rollback_test()
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
