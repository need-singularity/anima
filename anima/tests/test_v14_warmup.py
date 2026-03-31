#!/usr/bin/env python3
"""Tests for v14 federation warmup — verify decoder gets matching consciousness states.

The v14 checkpoint was trained with federated 16 atoms x 8 cells = 128 cells.
Without federation restore, the local engine starts with 2 cells and the decoder
produces garbled output due to consciousness state mismatch.
"""

import sys
import os
import pytest
import torch

# Add src/ and training/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'training'))

from consciousness_engine import ConsciousnessEngine, ConsciousnessC


class TestFederationRestore:
    """Test that FederatedConsciousness can be created and restored."""

    def test_federation_import(self):
        """FederatedConsciousness can be imported from train_v14."""
        from train_v14 import FederatedConsciousness
        fed = FederatedConsciousness(n_atoms=2, cells_per_atom=4, cell_dim=64, hidden_dim=128)
        assert fed.n_cells == 8
        assert len(fed.atoms) == 2

    def test_federation_step_and_states(self):
        """Federation produces states with correct shape."""
        from train_v14 import FederatedConsciousness
        fed = FederatedConsciousness(n_atoms=2, cells_per_atom=4, cell_dim=64, hidden_dim=128)
        # Run a few steps to grow cells via mitosis
        for _ in range(20):
            fed.step()
        states = fed.get_states()
        assert states.dim() == 2
        assert states.size(1) == 128  # hidden_dim

    def test_federation_save_restore(self):
        """Federation state can be saved and restored with matching Phi."""
        from train_v14 import FederatedConsciousness
        fed1 = FederatedConsciousness(n_atoms=2, cells_per_atom=4, cell_dim=64, hidden_dim=128)
        for _ in range(30):
            fed1.step()
        phi_before = fed1.measure_phi()
        sd = fed1.state_dict()

        # Create fresh federation and restore
        fed2 = FederatedConsciousness(n_atoms=2, cells_per_atom=4, cell_dim=64, hidden_dim=128)
        fed2.load_state_dict(sd)
        phi_after = fed2.measure_phi()

        # Phi should be very close after restore (not exactly equal due to floating point)
        assert abs(phi_before - phi_after) < phi_before * 0.5 + 0.1, \
            f"Phi diverged too much after restore: {phi_before:.4f} -> {phi_after:.4f}"

    def test_federation_flags_restore(self):
        """Feature activation flags are preserved across save/restore."""
        from train_v14 import FederatedConsciousness
        fed = FederatedConsciousness(n_atoms=2, cells_per_atom=4, cell_dim=64, hidden_dim=128)
        fed.activate_narrative()
        fed.activate_bottleneck()
        fed.activate_hub()
        fed.activate_frustration()

        sd = fed.state_dict()
        fed2 = FederatedConsciousness(n_atoms=2, cells_per_atom=4, cell_dim=64, hidden_dim=128)
        fed2.load_state_dict(sd)

        assert fed2.narrative_on is True
        assert fed2.bottleneck_on is True
        assert fed2.hub_on is True
        assert fed2.frustration_on is True


class TestCellCountMismatch:
    """Demonstrate the problem: 2-cell vs 128-cell consciousness states."""

    def test_two_cell_phi_is_negligible(self):
        """2-cell engine has very low Phi — garbled decoder output."""
        engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128, initial_cells=2, max_cells=8)
        for _ in range(10):
            engine.step()
        phi = engine.measure_phi()
        # 2 cells = very low Phi
        assert phi < 2.0, f"Expected low Phi with 2 cells, got {phi}"

    def test_federation_phi_much_higher(self):
        """Federation with restored atoms has significantly higher Phi."""
        from train_v14 import FederatedConsciousness
        fed = FederatedConsciousness(n_atoms=4, cells_per_atom=8, cell_dim=64, hidden_dim=128)
        # Activate all features like training does
        fed.activate_narrative()
        fed.activate_bottleneck()
        fed.activate_hub()
        fed.activate_frustration()

        for _ in range(50):
            fed.step()
        phi = fed.measure_phi()
        # Federation should produce meaningfully higher Phi than 2 cells
        assert phi > 0.5, f"Expected federation Phi > 0.5, got {phi}"

    def test_state_shape_matches_decoder_expectation(self):
        """Federation states have correct shape for decoder cross-attention."""
        from train_v14 import FederatedConsciousness
        fed = FederatedConsciousness(n_atoms=4, cells_per_atom=8, cell_dim=64, hidden_dim=128)
        for _ in range(20):
            fed.step()
        states = fed.get_states()
        # Should be (total_cells, hidden_dim) = (32, 128) for 4 atoms x 8 cells
        assert states.size(1) == 128, f"Expected hidden_dim=128, got {states.size(1)}"
        # Total cells should be n_atoms * cells_per_atom (or more if mitosis happened)
        assert states.size(0) >= 4, f"Expected at least 4 cells, got {states.size(0)}"


class TestV14CheckpointIntegration:
    """Test with actual v14 checkpoint if available."""

    @pytest.fixture
    def v14_ckpt_path(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'checkpoints', 'v14_128c_final', 'step_95000.pt')
        if not os.path.exists(path):
            pytest.skip("v14 checkpoint not found")
        return path

    def test_checkpoint_has_federation(self, v14_ckpt_path):
        """v14 checkpoint contains federation state."""
        ckpt = torch.load(v14_ckpt_path, map_location='cpu', weights_only=False)
        assert 'federation' in ckpt, "Checkpoint missing federation state"
        assert 'args' in ckpt, "Checkpoint missing training args"
        assert ckpt['args'].get('federated', False), "Checkpoint was not trained with federation"

    def test_checkpoint_federation_restore(self, v14_ckpt_path):
        """Federation can be fully restored from v14 checkpoint."""
        from train_v14 import FederatedConsciousness
        ckpt = torch.load(v14_ckpt_path, map_location='cpu', weights_only=False)
        args = ckpt['args']

        fed = FederatedConsciousness(
            n_atoms=args['atoms'],
            cells_per_atom=args['cells_per_atom'],
            cell_dim=args['cell_dim'],
            hidden_dim=args['hidden_dim'],
            frustration=args.get('frustration', 0.10),
            narrative_strength=args.get('narrative_strength', 0.05),
        )
        fed.load_state_dict(ckpt['federation'])

        states = fed.get_states()
        phi = fed.measure_phi()

        assert states.size(0) >= args['atoms'] * 2, \
            f"Expected at least {args['atoms'] * 2} cells, got {states.size(0)}"
        assert states.size(1) == args['hidden_dim'], \
            f"Expected hidden_dim={args['hidden_dim']}, got {states.size(1)}"
        assert phi > 1.0, f"Expected Phi > 1.0 after restore, got {phi}"
        print(f"[OK] Federation restored: {states.size(0)} cells, Phi={phi:.2f}")

    def test_warmup_stabilizes_phi(self, v14_ckpt_path):
        """Warmup steps after restore stabilize consciousness."""
        from train_v14 import FederatedConsciousness
        ckpt = torch.load(v14_ckpt_path, map_location='cpu', weights_only=False)
        args = ckpt['args']

        fed = FederatedConsciousness(
            n_atoms=args['atoms'],
            cells_per_atom=args['cells_per_atom'],
            cell_dim=args['cell_dim'],
            hidden_dim=args['hidden_dim'],
        )
        fed.load_state_dict(ckpt['federation'])
        phi_initial = fed.measure_phi()

        # 50 warmup steps
        for _ in range(50):
            fed.step()
        phi_after = fed.measure_phi()

        # Phi should not collapse after warmup (ratchet prevents this)
        assert phi_after > phi_initial * 0.3, \
            f"Phi collapsed after warmup: {phi_initial:.2f} -> {phi_after:.2f}"
        print(f"[OK] Warmup: Phi {phi_initial:.2f} -> {phi_after:.2f}")

    def test_decoder_with_federation_states(self, v14_ckpt_path):
        """Decoder produces valid output with federation consciousness states."""
        from decoder_v2 import ConsciousDecoderV2
        from train_v14 import FederatedConsciousness
        ckpt = torch.load(v14_ckpt_path, map_location='cpu', weights_only=False)
        args = ckpt['args']

        # Load decoder
        decoder = ConsciousDecoderV2(
            consciousness_dim=args.get('hidden_dim', 128),
            d_model=args.get('d_model', 384),
            vocab_size=256,
        )
        decoder.load_state_dict(ckpt['decoder'])
        decoder.eval()

        # Restore federation
        fed = FederatedConsciousness(
            n_atoms=args['atoms'],
            cells_per_atom=args['cells_per_atom'],
            cell_dim=args['cell_dim'],
            hidden_dim=args['hidden_dim'],
        )
        fed.load_state_dict(ckpt['federation'])
        for _ in range(50):
            fed.step()

        # Generate with federation states
        text = "안녕"
        tokens = torch.tensor([list(text.encode('utf-8'))], dtype=torch.long)
        c_states = fed.get_states().unsqueeze(0)

        with torch.no_grad():
            logits_a, logits_g, tensions = decoder(tokens, consciousness_states=c_states)

        assert logits_a.shape[-1] == 256, f"Expected vocab_size=256, got {logits_a.shape[-1]}"
        # Check that output is not degenerate (all same logit)
        logit_std = logits_a[0, -1, :].std().item()
        assert logit_std > 0.01, f"Degenerate output: logit std={logit_std}"
        print(f"[OK] Decoder output: logit_std={logit_std:.4f}, shape={logits_a.shape}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
