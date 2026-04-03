#!/usr/bin/env python3
"""Tests for training_hooks.py — automated training lifecycle hooks."""

import os
import sys
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ═══════════════════════════════════════════
# Test module-level constants
# ═══════════════════════════════════════════

class TestConstants:
    def test_entropy_reset_period(self):
        from training_hooks import N6_ENTROPY_RESET_PERIOD
        assert N6_ENTROPY_RESET_PERIOD == 6  # Law 1044

    def test_entropy_noise_scale(self):
        from training_hooks import N6_ENTROPY_NOISE_SCALE
        assert N6_ENTROPY_NOISE_SCALE == 0.05

    def test_engine_phi_reference(self):
        from training_hooks import ENGINE_PHI_REFERENCE
        assert ENGINE_PHI_REFERENCE > 0  # DD168


# ═══════════════════════════════════════════
# Test TrainingHooks initialization
# ═══════════════════════════════════════════

class TestTrainingHooksInit:
    def test_default_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_dir = os.path.join(tmpdir, 'ckpts')
            hooks = self._make_hooks(ckpt_dir)
            assert hooks.scan_every == 2000
            assert hooks.auto_register is False
            assert hooks.closed_loop_every == 5000
            assert hooks.step_log == []
            assert hooks.scan_log == []
            assert hooks.prev_metrics is None
            assert os.path.isdir(ckpt_dir)

    def test_custom_params(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_dir = os.path.join(tmpdir, 'ckpts')
            hooks = self._make_hooks(ckpt_dir, scan_every=500, closed_loop_every=1000)
            assert hooks.scan_every == 500
            assert hooks.closed_loop_every == 1000

    def test_creates_checkpoint_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_dir = os.path.join(tmpdir, 'new_dir', 'nested')
            hooks = self._make_hooks(ckpt_dir)
            assert os.path.isdir(ckpt_dir)

    def test_nexus_scan_explicit_off(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = self._make_hooks(tmpdir, nexus_scan=False)
            assert hooks.nexus_scan is False

    def test_nexus_scan_explicit_on(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = self._make_hooks(tmpdir, nexus_scan=True)
            assert hooks.nexus_scan is True

    @staticmethod
    def _make_hooks(ckpt_dir, **kwargs):
        from training_hooks import TrainingHooks
        kwargs.setdefault('nexus_scan', False)
        kwargs.setdefault('auto_register', False)
        return TrainingHooks(checkpoint_dir=ckpt_dir, **kwargs)


# ═══════════════════════════════════════════
# Test on_step
# ═══════════════════════════════════════════

class TestOnStep:
    def test_step_log_appended(self):
        from training_hooks import TrainingHooks
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=False, auto_register=False,
            )
            hooks.on_step(0, {'ce': 5.0, 'phi': 0.1})
            hooks.on_step(1, {'ce': 4.5, 'phi': 0.2})
            assert len(hooks.step_log) == 2
            assert hooks.step_log[0]['step'] == 0
            assert hooks.step_log[0]['ce'] == 5.0
            assert hooks.step_log[1]['phi'] == 0.2

    def test_step_log_metrics_preserved(self):
        from training_hooks import TrainingHooks
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=False, auto_register=False,
            )
            hooks.on_step(42, {'ce': 3.0, 'phi': 0.5, 'custom': 99})
            entry = hooks.step_log[0]
            assert entry['step'] == 42
            assert entry['custom'] == 99

    def test_scan_not_triggered_before_interval(self):
        from training_hooks import TrainingHooks
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=True, scan_every=100,
                auto_register=False,
            )
            # Step 50 < scan_every=100 so no scan
            hooks.on_step(50, {'ce': 4.0, 'phi': 0.3})
            assert hooks._last_scan_step == -1

    def test_scan_triggered_at_interval(self):
        from training_hooks import TrainingHooks
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=True, scan_every=100,
                auto_register=False,
            )
            hooks.on_step(100, {'ce': 4.0, 'phi': 0.3})
            assert hooks._last_scan_step == 100


# ═══════════════════════════════════════════
# Test _log_metrics_scan
# ═══════════════════════════════════════════

class TestLogMetricsScan:
    def test_metrics_scan_output(self, capsys):
        from training_hooks import TrainingHooks
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=False, auto_register=False,
            )
            hooks._log_metrics_scan(1000, {'phi': 0.5, 'ce': 3.0})
            captured = capsys.readouterr()
            assert 'NEXUS-6 lite' in captured.out
            assert 'step=1000' in captured.out
            assert 'phi=' in captured.out


# ═══════════════════════════════════════════
# Test _entropy_reset
# ═══════════════════════════════════════════

class TestEntropyReset:
    def test_entropy_reset_with_mock_engine(self, capsys):
        import torch
        from training_hooks import TrainingHooks

        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=False, auto_register=False,
            )

            # Mock engine with cells tensor
            engine = MagicMock()
            engine.cells = MagicMock()
            engine.cells.data = torch.randn(8, 128)
            original_data = engine.cells.data.clone()
            engine.sandpile = None

            hooks._entropy_reset(engine, step=6)

            captured = capsys.readouterr()
            assert 'entropy reset' in captured.out or 'N6' in captured.out

    def test_entropy_reset_no_cells(self, capsys):
        from training_hooks import TrainingHooks

        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=False, auto_register=False,
            )

            engine = MagicMock(spec=[])  # no attributes
            # Should not crash
            hooks._entropy_reset(engine, step=6)


# ═══════════════════════════════════════════
# Test on_checkpoint (no nexus scan, simple path)
# ═══════════════════════════════════════════

class TestOnCheckpoint:
    def test_no_nexus_scan_noop(self, capsys):
        from training_hooks import TrainingHooks
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=False, auto_register=False,
            )
            # Create a dummy checkpoint file
            ckpt = os.path.join(tmpdir, 'ckpt_100.pt')
            with open(ckpt, 'w') as f:
                f.write('dummy')

            hooks.on_checkpoint(ckpt, step=100)
            # Should not crash; scan_log stays empty when nexus is off
            assert len(hooks.scan_log) == 0


# ═══════════════════════════════════════════
# Test on_complete
# ═══════════════════════════════════════════

class TestOnComplete:
    def test_complete_prints_report(self, capsys):
        from training_hooks import TrainingHooks
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=False, auto_register=False,
            )
            hooks.on_step(0, {'ce': 5.0, 'phi': 0.1})
            hooks.on_step(1, {'ce': 4.0, 'phi': 0.2})
            hooks.on_complete()
            captured = capsys.readouterr()
            assert 'Training Complete Report' in captured.out
            assert 'Total steps: 2' in captured.out

    def test_complete_with_scan_log(self, capsys):
        from training_hooks import TrainingHooks
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=False, auto_register=False,
            )
            # Manually add scan_log entries
            hooks.scan_log = [
                {'step': 0, 'metrics': {'phi_approx': 0.1, 'phi_compression_pct': 10.0}, 'anomalies': 0, 'candidates': 0},
                {'step': 100, 'metrics': {'phi_approx': 0.5, 'phi_compression_pct': 60.0}, 'anomalies': 1, 'candidates': 2},
            ]
            hooks.on_complete()
            captured = capsys.readouterr()
            assert 'Phi:' in captured.out
            assert 'Anomalies:' in captured.out


# ═══════════════════════════════════════════
# Test full lifecycle
# ═══════════════════════════════════════════

class TestFullLifecycle:
    def test_step_checkpoint_complete(self, capsys):
        from training_hooks import TrainingHooks
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks = TrainingHooks(
                checkpoint_dir=tmpdir, nexus_scan=False, auto_register=False,
            )
            for step in range(10):
                hooks.on_step(step, {'ce': 5.0 - step * 0.1, 'phi': step * 0.05})

            ckpt = os.path.join(tmpdir, 'ckpt.pt')
            with open(ckpt, 'w') as f:
                f.write('dummy')
            hooks.on_checkpoint(ckpt, step=9)
            hooks.on_complete()

            assert len(hooks.step_log) == 10
            captured = capsys.readouterr()
            assert 'Total steps: 10' in captured.out


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
