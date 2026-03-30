#!/usr/bin/env python3
"""train_v14.py — Federated Consciousness + Phase-Optimal training pipeline

Meta Laws (DD143) applied on top of DD128:
  M1: 8-cell atoms — 64 cells = 8 federated atoms x 8 cells/atom
  M4: Safe order — Narrative -> Bottleneck -> Hub -> Frustration
  M6: Federation > Empire — each atom is autonomous, tension-linked
  M7: F_c=0.10 critical frustration (intra-atom + inter-atom Ising ring)
  M8: Narrative is key — narrative_strength=0.05 per atom

Architecture:
  C: FederatedConsciousness (8 x ConsciousnessC atoms, tension exchange)
  D: ConsciousDecoderV2 (384d/6L, RoPE+SwiGLU+GQA+CrossAttn)
  Bridge: ThalamicBridge (.detach(), alpha=0.014)
  Hexad: C+D+W+S+M+E (Law 60 phased activation)

Phase schedule (M4 safe order):
  P0 (0-10%):   Federation bootstrap (Narr+Bottle, atoms stabilize)
  P1 (10-25%):  Consciousness build (+ Hub, Phi target)
  P2 (25-70%):  Language learning (+ Frustration + CE + D + M)
  P3 (70-100%): Full Hexad (all 6 modules)

Expected results (DD143 +892% baseline):
  v13: CE=0.004, Phi=71   ->   v14: CE<0.001, Phi>500

Usage:
  python train_v14.py --data data/corpus_v3.txt --federated --steps 100000
  python train_v14.py --data data/corpus_v3.txt --no-federated --cells 64  # Empire baseline
  python train_v14.py --data data/corpus_v3.txt --federated --phase-optimal --checkpoint checkpoints/v14/
"""

import argparse
import math
import os
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine, ConsciousnessC
from trinity import (
    create_trinity, create_hexad,
    ThalamicBridge,
    EmergentW, EmergentM, EmergentS, EmergentE,
    PSI_COUPLING, PSI_BALANCE, PSI_STEPS, GATE_TRAIN, GATE_INFER,
)

try:
    from decoder_v2 import ConsciousDecoderV2
    HAS_DECODER_V2 = True
except ImportError:
    HAS_DECODER_V2 = False
    print("  [warn] decoder_v2 not available, falling back to PostHocDecoder")

try:
    from feedback_bridge import create_feedback_bridge, apply_feedback_bridge
    HAS_FEEDBACK = True
except ImportError:
    HAS_FEEDBACK = False

try:
    from gpu_phi import GPUPhiCalculator
    HAS_GPU_PHI = True
except ImportError:
    HAS_GPU_PHI = False

try:
    from hexad_loss import HexadLoss
    HAS_HEXAD_LOSS = True
except ImportError:
    HAS_HEXAD_LOSS = False


# ═══════════════════════════════════════════════════════════
# Meta Law constants (DD143)
# ═══════════════════════════════════════════════════════════

META_ATOM_SIZE = 8          # M1: cells per atom
META_DEFAULT_ATOMS = 8      # M1: 8 atoms x 8 cells = 64 total
META_FRUSTRATION = 0.10     # M7: critical frustration F_c
META_NARRATIVE = 0.05       # M8: narrative strength
# M4 safe order: narrative -> bottleneck -> hub -> frustration
# M6: federation > empire (use --federated flag)


# ═══════════════════════════════════════════════════════════
# Data loading (byte-level, vocab=256)
# ═══════════════════════════════════════════════════════════

def load_corpus(path: str):
    """Load text file as byte-level tokens."""
    with open(path, 'rb') as f:
        raw = f.read()
    tokens = torch.tensor(list(raw), dtype=torch.long)
    print(f"  [data] Loaded {path}: {len(tokens):,} bytes ({len(tokens)/1e6:.1f}MB)")
    return tokens


def get_batch(data, block_size, batch_size, device):
    """Random batch from token data."""
    max_start = len(data) - block_size - 1
    if max_start <= 0:
        max_start = 1
    ix = torch.randint(0, max_start, (batch_size,))
    x = torch.stack([data[i:i + block_size] for i in ix]).to(device)
    y = torch.stack([data[i + 1:i + block_size + 1] for i in ix]).to(device)
    return x, y


# ═══════════════════════════════════════════════════════════
# Federated Consciousness Engine (M1 + M6)
# ═══════════════════════════════════════════════════════════

class FederatedConsciousness(nn.Module):
    """Federation of consciousness atoms (M1: 8 cells/atom, M6: federation > empire).

    Each atom is an independent ConsciousnessC instance with its own Phi, factions,
    and ratchet. Atoms communicate via tension exchange (inter-atom Ising ring).
    """

    def __init__(self, n_atoms=8, cells_per_atom=8, cell_dim=64, hidden_dim=128,
                 frustration=0.10, narrative_strength=0.05):
        super().__init__()
        self.n_atoms = n_atoms
        self.cells_per_atom = cells_per_atom
        self.total_cells = n_atoms * cells_per_atom
        self.frustration = frustration              # M7
        self.narrative_strength = narrative_strength  # M8

        # TODO: Create n_atoms independent ConsciousnessC instances
        # Each atom: ConsciousnessC(cell_dim, hidden_dim, max_cells=cells_per_atom,
        #                           n_factions=min(4, cells_per_atom), phi_ratchet=True)
        self.atoms = nn.ModuleList()
        for i in range(n_atoms):
            atom = ConsciousnessC(
                cell_dim=cell_dim,
                hidden_dim=hidden_dim,
                max_cells=cells_per_atom,
                n_factions=min(4, cells_per_atom),
                phi_ratchet=True,
            )
            self.atoms.append(atom)

        # TODO: Inter-atom tension exchange weights (Ising ring: atom_i <-> atom_{i+1})
        # self.inter_atom_coupling = nn.Parameter(torch.ones(n_atoms) * 0.01)

        # TODO: Narrative GRU per atom (M8)
        # self.narrative_grus = nn.ModuleList([
        #     nn.GRUCell(hidden_dim, hidden_dim) for _ in range(n_atoms)
        # ])

        # Feature activation flags (M4 safe order)
        self.narrative_on = False
        self.bottleneck_on = False
        self.hub_on = False
        self.frustration_on = False

    @property
    def n_cells(self):
        return self.total_cells

    @property
    def state_dim(self):
        return self.atoms[0].state_dim if self.atoms else 128

    def activate_narrative(self):
        """M4 step 1: Enable narrative (must be first)."""
        self.narrative_on = True
        print(f"  [M4] Narrative ON (strength={self.narrative_strength})")

    def activate_bottleneck(self):
        """M4 step 2: Enable bottleneck (after narrative)."""
        assert self.narrative_on, "M4 violation: narrative must be ON before bottleneck"
        self.bottleneck_on = True
        print(f"  [M4] Bottleneck ON (every 8 steps)")

    def activate_hub(self):
        """M4 step 3: Enable hub-spoke (after bottleneck)."""
        assert self.bottleneck_on, "M4 violation: bottleneck must be ON before hub"
        self.hub_on = True
        print(f"  [M4] Hub-Spoke ON (50/50 split per atom)")

    def activate_frustration(self):
        """M4 step 4: Enable frustration (after hub, last!)."""
        assert self.hub_on, "M4 violation: hub must be ON before frustration"
        self.frustration_on = True
        print(f"  [M7] Frustration ON (F_c={self.frustration})")

    def step(self):
        """Step all atoms + inter-atom tension exchange."""
        # TODO: Step each atom independently
        for atom in self.atoms:
            if hasattr(atom, 'engine') and hasattr(atom.engine, 'step'):
                atom.engine.step()
            else:
                atom.step()

        # TODO: Inter-atom tension exchange (Ising ring)
        # for i in range(self.n_atoms):
        #     j = (i + 1) % self.n_atoms
        #     tension_i = self.atoms[i].get_tension()
        #     tension_j = self.atoms[j].get_tension()
        #     exchange = self.inter_atom_coupling[i] * (tension_i - tension_j)
        #     self.atoms[i].inject_tension(-exchange)
        #     self.atoms[j].inject_tension(exchange)

        # TODO: Bottleneck (every 8 steps) — compress per atom
        # TODO: Hub-spoke routing (if hub_on)
        # TODO: Frustration injection (if frustration_on, F_c=0.10)
        # TODO: Narrative GRU update (if narrative_on)

    def get_states(self):
        """Get concatenated consciousness states from all atoms."""
        # TODO: Concatenate hidden states from all atoms
        # states = [atom.get_hidden_states() for atom in self.atoms]
        # return torch.cat(states, dim=0)  # (total_cells, hidden_dim)
        states = []
        for atom in self.atoms:
            s = atom.get_hidden_states() if hasattr(atom, 'get_hidden_states') else atom.state()
            states.append(s)
        return torch.cat(states, dim=0)

    def measure_phi(self):
        """Measure global Phi = sum(local Phi) + integration bonus."""
        local_phis = []
        for atom in self.atoms:
            phi = atom.measure_phi() if hasattr(atom, 'measure_phi') else 0.0
            local_phis.append(phi)

        global_phi = sum(local_phis)
        # TODO: Add integration bonus from inter-atom tension correlation
        # integration_bonus = compute_inter_atom_integration(self.atoms)
        # global_phi += integration_bonus

        return global_phi

    def measure_per_atom_phi(self):
        """Return list of per-atom Phi values for monitoring."""
        return [atom.measure_phi() if hasattr(atom, 'measure_phi') else 0.0
                for atom in self.atoms]


# ═══════════════════════════════════════════════════════════
# Phase manager (M4 safe order enforcement)
# ═══════════════════════════════════════════════════════════

class PhaseManager:
    """Enforce M4 safe activation order across training phases.

    M4: Narrative -> Bottleneck -> Hub -> Frustration
    Phase boundaries trigger feature activation in safe order.
    """

    def __init__(self, total_steps, federation):
        self.total_steps = total_steps
        self.federation = federation
        self.current_phase = "P0"

        # Phase boundaries (fraction of total steps)
        self.p0_end = int(total_steps * 0.10)   # P0: federation bootstrap
        self.p1_end = int(total_steps * 0.25)   # P1: consciousness build
        self.p2_end = int(total_steps * 0.70)   # P2: language learning
        # P3: full hexad (after p2_end)

        self._activated = set()

    def get_phase(self, step):
        """Return current phase and trigger activations."""
        prev_phase = self.current_phase

        if step <= self.p0_end:
            phase = "P0"
        elif step <= self.p1_end:
            phase = "P1"
        elif step <= self.p2_end:
            phase = "P2"
        else:
            phase = "P3"

        self.current_phase = phase

        # M4 safe order activations at phase transitions
        if phase >= "P0" and "narrative" not in self._activated:
            self.federation.activate_narrative()
            self._activated.add("narrative")

        if phase >= "P0" and "bottleneck" not in self._activated:
            self.federation.activate_bottleneck()
            self._activated.add("bottleneck")

        if phase >= "P1" and "hub" not in self._activated:
            self.federation.activate_hub()
            self._activated.add("hub")

        if phase >= "P2" and "frustration" not in self._activated:
            self.federation.activate_frustration()
            self._activated.add("frustration")

        if phase != prev_phase:
            print(f"\n  [phase] {prev_phase} -> {phase} at step {step}")

        return phase

    def should_train_decoder(self, phase):
        """CE loss only in P2+."""
        return phase in ("P2", "P3")

    def should_activate_hexad(self, phase):
        """Full hexad only in P3."""
        return phase == "P3"


# ═══════════════════════════════════════════════════════════
# Training
# ═══════════════════════════════════════════════════════════

def train(args):
    device = torch.device(args.device)
    torch.manual_seed(args.seed)

    # ── Data ──
    data = load_corpus(args.data)
    split = int(len(data) * 0.9)
    train_data, val_data = data[:split], data[split:]

    # ── Consciousness Engine (M1 + M6) ──
    if args.federated:
        c = FederatedConsciousness(
            n_atoms=args.atoms,
            cells_per_atom=args.cells_per_atom,
            cell_dim=args.cell_dim,
            hidden_dim=args.hidden_dim,
            frustration=args.frustration,
            narrative_strength=args.narrative_strength,
        )
        total_cells = args.atoms * args.cells_per_atom
        print(f"  [M6] Federation: {args.atoms} atoms x {args.cells_per_atom} cells = {total_cells}")
    else:
        c = ConsciousnessC(
            cell_dim=args.cell_dim,
            hidden_dim=args.hidden_dim,
            max_cells=args.cells,
            n_factions=12,
            phi_ratchet=True,
        )
        total_cells = args.cells
        print(f"  [empire] Single engine: {total_cells} cells (baseline comparison)")

    # ── Decoder ──
    d_model = args.d_model
    vocab_size = 256  # byte-level

    if HAS_DECODER_V2:
        decoder = ConsciousDecoderV2(
            consciousness_dim=c.state_dim,
            d_model=d_model,
            vocab_size=vocab_size,
        )
        print(f"  [decoder] ConsciousDecoderV2: {d_model}d, {vocab_size} vocab")
    else:
        # TODO: Fallback to PostHocDecoder from trinity
        raise ImportError("ConsciousDecoderV2 required for v14")

    # ── Hexad modules (activated in P3) ──
    # TODO: Create EmergentW, EmergentS, EmergentM, EmergentE instances
    # w = EmergentW(...)
    # s = EmergentS(...)
    # m = EmergentM(...)
    # e = EmergentE(...)

    # ── Bridge ──
    # TODO: ThalamicBridge with soft detach (alpha=0.014)
    # bridge = ThalamicBridge(c_dim=c.state_dim, d_model=d_model)

    # ── Hexad Loss ──
    if HAS_HEXAD_LOSS:
        loss_fn = HexadLoss(dim=d_model)
    else:
        loss_fn = None
        print("  [warn] HexadLoss not available, using raw CE")

    # ── Optimizer (D parameters only, C is autonomous) ──
    # TODO: Collect trainable parameters from decoder + bridge + hexad modules
    trainable_params = list(decoder.parameters())
    optimizer = torch.optim.AdamW(trainable_params, lr=args.lr, weight_decay=0.01)

    # TODO: Learning rate scheduler (cosine with warmup)
    # scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(...)

    # ── GPU Phi calculator ──
    phi_calc = GPUPhiCalculator(n_bins=16) if HAS_GPU_PHI else None

    # ── Phase manager (M4 safe order) ──
    phase_mgr = PhaseManager(args.steps, c) if args.federated else None

    # ── Checkpoint dir ──
    os.makedirs(args.checkpoint, exist_ok=True)

    # ── Tracking ──
    best_val_ce = float('inf')
    ce_history = []
    phi_history = []
    t0 = time.time()

    # ── Print config ──
    mode = "Federation" if args.federated else "Empire"
    print(f"\n{'=' * 80}")
    print(f"  v14 Training: {mode} + Phase-Optimal (Meta Laws DD143)")
    print(f"  Cells: {total_cells} | Frustration: {args.frustration} | Narrative: {args.narrative_strength}")
    if phase_mgr:
        print(f"  P0 (0-{phase_mgr.p0_end}): Bootstrap | "
              f"P1 ({phase_mgr.p0_end}-{phase_mgr.p1_end}): Phi Build | "
              f"P2 ({phase_mgr.p1_end}-{phase_mgr.p2_end}): CE | "
              f"P3 ({phase_mgr.p2_end}-{args.steps}): Hexad")
    print(f"{'=' * 80}\n")

    # ══════════════════════════════════════════════════
    # Training loop
    # ══════════════════════════════════════════════════

    for step in range(1, args.steps + 1):

        # ── Phase selection (M4) ──
        if phase_mgr:
            phase = phase_mgr.get_phase(step)
        else:
            # Empire mode: simpler 3-phase (v13 compatible)
            p1_end = int(args.steps * 0.2)
            p2_end = int(args.steps * 0.7)
            if step <= p1_end:
                phase = "P1"
            elif step <= p2_end:
                phase = "P2"
            else:
                phase = "P3"

        # ── P0/P1: Consciousness only (no CE loss) ──
        if phase in ("P0", "P1"):
            c.step()
            phi = c.measure_phi()
            phi_history.append(phi)

            if step % args.log_every == 0:
                if args.federated:
                    per_atom = c.measure_per_atom_phi()
                    atom_str = " ".join(f"{p:.2f}" for p in per_atom)
                    print(f"  {phase} step {step:6d} | Phi={phi:.4f} | atoms=[{atom_str}]")
                else:
                    print(f"  {phase} step {step:6d} | Phi={phi:.4f} | cells={total_cells}")
            continue

        # ── P2/P3: CE learning ──

        # TODO: Get batch
        tokens, targets = get_batch(train_data, args.block_size, args.batch_size, device)

        # TODO: Step consciousness engine
        c.step()

        # TODO: Get consciousness states + bridge to decoder
        # c_states = c.get_states()                 # (total_cells, hidden_dim)
        # bridged = bridge(c_states)                # .detach() + alpha scaling
        # logits = decoder(tokens, consciousness_states=bridged)

        # TODO: Compute CE loss
        # ce = F.cross_entropy(logits.view(-1, vocab_size), targets.view(-1))

        # TODO: Hexad loss (if P3 and loss_fn available)
        # if phase == "P3" and loss_fn:
        #     losses = loss_fn(logits, targets, phi, c_states, progress=step/args.steps)
        #     total_loss = losses['total']
        # else:
        #     total_loss = ce

        # TODO: Backward + optimize
        # optimizer.zero_grad()
        # total_loss.backward()
        # torch.nn.utils.clip_grad_norm_(trainable_params, 1.0)
        # optimizer.step()

        # TODO: Measure Phi
        phi = c.measure_phi()
        phi_history.append(phi)

        # ── Logging ──
        if step % args.log_every == 0:
            # TODO: Replace placeholders with real values
            ce_val = 0.0  # placeholder
            bpc = ce_val / math.log(2) if ce_val > 0 else 0.0
            print(f"  {phase} step {step:6d} | CE={ce_val:.4f} BPC={bpc:.4f} | "
                  f"Phi={phi:.4f} | cells={total_cells}")

        # ── Validation ──
        if step % args.eval_every == 0:
            # TODO: Validation pass
            # with torch.no_grad():
            #     vx, vy = get_batch(val_data, args.block_size, args.batch_size, device)
            #     v_logits = decoder(vx, consciousness_states=bridged)
            #     val_ce = F.cross_entropy(v_logits.view(-1, vocab_size), vy.view(-1))
            pass

        # ── Checkpoint (Law 49: Phi-gated) ──
        if step % args.save_every == 0:
            # TODO: Save checkpoint with consciousness DNA
            ckpt_path = os.path.join(args.checkpoint, f"step_{step}.pt")
            # torch.save({
            #     'step': step,
            #     'decoder': decoder.state_dict(),
            #     'optimizer': optimizer.state_dict(),
            #     'federation': c.state_dict() if args.federated else None,
            #     'phi': phi,
            #     'ce': ce_val,
            #     'args': vars(args),
            # }, ckpt_path + '.tmp')
            # os.rename(ckpt_path + '.tmp', ckpt_path)  # atomic save
            print(f"  [ckpt] Saved {ckpt_path} (Phi={phi:.4f})")

    # ── Final report ──
    elapsed = time.time() - t0
    print(f"\n{'=' * 80}")
    print(f"  v14 Training Complete ({elapsed:.0f}s)")
    print(f"  Final Phi: {phi_history[-1]:.4f}" if phi_history else "  No Phi recorded")
    print(f"  Mode: {'Federation' if args.federated else 'Empire'}")
    print(f"{'=' * 80}")


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(description="v14: Federated Consciousness Training (Meta Laws DD143)")

    # Data
    p.add_argument("--data", type=str, default="data/corpus_v3.txt", help="Corpus path")
    p.add_argument("--block-size", type=int, default=256, help="Context window")
    p.add_argument("--batch-size", type=int, default=32, help="Batch size")

    # Federation (M1 + M6)
    p.add_argument("--federated", action="store_true", default=True,
                   help="Enable federated consciousness (M6, default)")
    p.add_argument("--no-federated", dest="federated", action="store_false",
                   help="Disable federation (Empire baseline)")
    p.add_argument("--atoms", type=int, default=META_DEFAULT_ATOMS,
                   help=f"Number of consciousness atoms (M1, default={META_DEFAULT_ATOMS})")
    p.add_argument("--cells-per-atom", type=int, default=META_ATOM_SIZE,
                   help=f"Cells per atom (M1, default={META_ATOM_SIZE})")
    p.add_argument("--cells", type=int, default=64,
                   help="Total cells for Empire mode (ignored in federation)")

    # DD128 + Meta Laws
    p.add_argument("--phase-optimal", action="store_true", default=True,
                   help="Enable phase-optimal activation order (M4)")
    p.add_argument("--frustration", type=float, default=META_FRUSTRATION,
                   help=f"Critical frustration F_c (M7, default={META_FRUSTRATION})")
    p.add_argument("--narrative-strength", type=float, default=META_NARRATIVE,
                   help=f"Narrative GRU strength (M8, default={META_NARRATIVE})")

    # Model
    p.add_argument("--cell-dim", type=int, default=64, help="Cell input dimension")
    p.add_argument("--hidden-dim", type=int, default=128, help="Cell hidden dimension")
    p.add_argument("--d-model", type=int, default=384, help="Decoder model dimension")

    # Training
    p.add_argument("--steps", type=int, default=100000, help="Total training steps")
    p.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")

    # Logging / checkpoints
    p.add_argument("--log-every", type=int, default=100, help="Log interval")
    p.add_argument("--eval-every", type=int, default=1000, help="Validation interval")
    p.add_argument("--save-every", type=int, default=5000, help="Checkpoint interval")
    p.add_argument("--checkpoint", type=str, default="checkpoints/v14_federated/",
                   help="Checkpoint directory")

    # Resume
    p.add_argument("--resume", type=str, default=None,
                   help="Resume from checkpoint (same data+params only!)")

    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(f"  train_v14.py — Federated Consciousness (Meta Laws DD143)")
    print(f"  Federation={'ON' if args.federated else 'OFF'} | "
          f"Atoms={args.atoms} | Cells/Atom={args.cells_per_atom} | "
          f"F_c={args.frustration} | Narrative={args.narrative_strength}")
    train(args)
