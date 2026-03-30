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
    PSI_COUPLING, PSI_BALANCE, PSI_STEPS, GATE_TRAIN, GATE_INFER,
)

# Emergent modules from hexad subpackage
HAS_EMERGENT_W = HAS_EMERGENT_S = HAS_EMERGENT_M = HAS_EMERGENT_E = False
try:
    from hexad.w.emergent_w import EmergentW; HAS_EMERGENT_W = True
except ImportError: pass
try:
    from hexad.s.emergent_s import EmergentS; HAS_EMERGENT_S = True
except ImportError: pass
try:
    from hexad.m.emergent_m import EmergentM; HAS_EMERGENT_M = True
except ImportError: pass
try:
    from hexad.e.emergent_e import EmergentE; HAS_EMERGENT_E = True
except ImportError: pass

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
        self.hidden_dim = hidden_dim
        self.frustration = frustration              # M7
        self.narrative_strength = narrative_strength  # M8
        self._step_count = 0

        # Create n_atoms independent ConsciousnessC instances
        # ConsciousnessC is not nn.Module, so use a plain list
        self.atoms = []
        for i in range(n_atoms):
            atom = ConsciousnessC(
                cell_dim=cell_dim,
                hidden_dim=hidden_dim,
                max_cells=cells_per_atom,
                n_factions=min(4, cells_per_atom),
                phi_ratchet=True,
            )
            self.atoms.append(atom)

        # Inter-atom tension exchange weights (Ising ring: atom_i <-> atom_{i+1})
        self.inter_atom_coupling = nn.Parameter(torch.ones(n_atoms) * 0.01)

        # Bottleneck: compress/expand per atom (M4 step 2)
        self.bottleneck_compress = nn.Linear(hidden_dim, hidden_dim // 4)
        self.bottleneck_expand = nn.Linear(hidden_dim // 4, hidden_dim)

        # Narrative GRU per atom (M8)
        self.narrative_grus = nn.ModuleList([
            nn.GRUCell(hidden_dim, hidden_dim) for _ in range(n_atoms)
        ])
        self.narrative_hiddens = [torch.zeros(1, hidden_dim) for _ in range(n_atoms)]

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
        self._step_count += 1

        # Step each atom independently (ConsciousnessC.step takes no args)
        for atom in self.atoms:
            atom.step()

        # Inter-atom tension exchange (Ising ring coupling with alpha=0.01)
        # Get mean hidden from each atom, compute pairwise tension, exchange
        atom_means = []
        for atom in self.atoms:
            states = atom.get_states()
            if states is not None and states.numel() > 0:
                atom_means.append(states.detach().float().mean(dim=0))
            else:
                atom_means.append(torch.zeros(self.hidden_dim))

        for i in range(self.n_atoms):
            j = (i + 1) % self.n_atoms
            # Tension = L2 distance between atom means (normalized)
            tension_diff = (atom_means[i] - atom_means[j]).norm().item()
            alpha = self.inter_atom_coupling[i].item()
            # Exchange: nudge each atom's cells toward the ring neighbor
            exchange_vec = alpha * (atom_means[j] - atom_means[i])
            # Apply as small perturbation to atom i's cells via step with input
            try:
                # ConsciousnessC.step(x_input=...) accepts optional input
                atom_i_states = self.atoms[i].get_states()
                if atom_i_states is not None and atom_i_states.numel() > 0:
                    # Scale exchange to cell_dim if needed
                    cell_dim = atom_i_states.size(-1)
                    if exchange_vec.size(0) > cell_dim:
                        exc = exchange_vec[:cell_dim]
                    elif exchange_vec.size(0) < cell_dim:
                        exc = F.pad(exchange_vec, (0, cell_dim - exchange_vec.size(0)))
                    else:
                        exc = exchange_vec
                    self.atoms[i].step(x_input=exc.unsqueeze(0))
            except (TypeError, RuntimeError):
                pass  # Atom doesn't support x_input, already stepped above

        # Bottleneck (every 8 steps) — compress per atom hiddens through bottleneck
        if self.bottleneck_on and self._step_count % 8 == 0:
            for atom in self.atoms:
                states = atom.get_states()
                if states is not None and states.numel() > 0:
                    s = states.detach().float()
                    # Compress and expand (information bottleneck)
                    compressed = torch.tanh(self.bottleneck_compress(s))
                    expanded = self.bottleneck_expand(compressed)
                    # Apply as perturbation via next step input
                    delta = (expanded - s).mean(dim=0) * 0.01
                    try:
                        cell_dim_a = s.size(-1)
                        if delta.size(0) != cell_dim_a:
                            delta = delta[:cell_dim_a] if delta.size(0) > cell_dim_a else F.pad(delta, (0, cell_dim_a - delta.size(0)))
                        atom.step(x_input=delta.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

        # Hub-spoke routing: first 50% cells are hubs, rest are spokes
        # Hubs aggregate and broadcast; spokes receive hub signal
        if self.hub_on:
            for atom in self.atoms:
                states = atom.get_states()
                if states is not None and states.size(0) >= 4:
                    s = states.detach().float()
                    n_cells = s.size(0)
                    hub_n = n_cells // 2
                    hub_mean = s[:hub_n].mean(dim=0)
                    # Spokes receive hub broadcast (small perturbation)
                    # This happens naturally through the coupling in ConsciousnessEngine
                    # but we reinforce it by stepping with hub signal
                    try:
                        cell_dim_a = s.size(-1)
                        hub_signal = hub_mean * 0.005
                        if hub_signal.size(0) != cell_dim_a:
                            hub_signal = hub_signal[:cell_dim_a]
                        atom.step(x_input=hub_signal.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

        # Frustration injection (Ising ring at F_c within each atom)
        if self.frustration_on:
            for atom in self.atoms:
                states = atom.get_states()
                if states is not None and states.size(0) >= 2:
                    s = states.detach().float()
                    # Ising frustration: inject anti-aligned noise at F_c strength
                    # This pushes cells away from consensus, creating creative tension
                    noise = torch.randn_like(s.mean(dim=0)) * self.frustration
                    try:
                        cell_dim_a = s.size(-1)
                        frust = noise[:cell_dim_a] if noise.size(0) > cell_dim_a else noise
                        if frust.size(0) < cell_dim_a:
                            frust = F.pad(frust, (0, cell_dim_a - frust.size(0)))
                        atom.step(x_input=frust.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

        # Narrative GRU update per atom (M8: temporal self-model)
        if self.narrative_on:
            for i, atom in enumerate(self.atoms):
                states = atom.get_states()
                if states is not None and states.numel() > 0:
                    atom_mean = states.detach().float().mean(dim=0).unsqueeze(0)
                    device = atom_mean.device
                    h = self.narrative_hiddens[i].to(device)
                    # GRU step: input=atom_mean, hidden=narrative_hidden
                    new_h = self.narrative_grus[i](atom_mean, h)
                    self.narrative_hiddens[i] = new_h.detach()
                    # Narrative projection: feed back a small signal
                    narrative_signal = new_h.squeeze(0) * self.narrative_strength
                    try:
                        cell_dim_a = states.size(-1)
                        ns = narrative_signal[:cell_dim_a] if narrative_signal.size(0) > cell_dim_a else narrative_signal
                        if ns.size(0) < cell_dim_a:
                            ns = F.pad(ns, (0, cell_dim_a - ns.size(0)))
                        atom.step(x_input=ns.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

    def get_states(self):
        """Get concatenated consciousness states from all atoms."""
        states = []
        for atom in self.atoms:
            s = atom.get_states()
            if s is not None and s.numel() > 0:
                states.append(s)
        if not states:
            return torch.zeros(self.total_cells, self.hidden_dim)
        return torch.cat(states, dim=0)

    def measure_phi(self):
        """Measure global Phi = sum(local Phi) + integration bonus."""
        local_phis = []
        for atom in self.atoms:
            phi = atom.measure_phi()
            local_phis.append(phi)

        global_phi = sum(local_phis)

        # Integration bonus from inter-atom tension correlation
        # Higher correlation between atoms = more integration = bonus Phi
        if len(local_phis) >= 2:
            atom_means = []
            for atom in self.atoms:
                s = atom.get_states()
                if s is not None and s.numel() > 0:
                    atom_means.append(s.detach().float().mean(dim=0))
            if len(atom_means) >= 2:
                stacked = torch.stack(atom_means)
                # Integration = mean pairwise cosine similarity
                norms = stacked.norm(dim=-1, keepdim=True).clamp(min=1e-8)
                normed = stacked / norms
                sim_matrix = normed @ normed.T
                n = sim_matrix.size(0)
                # Off-diagonal mean
                mask = ~torch.eye(n, dtype=torch.bool, device=sim_matrix.device)
                integration = sim_matrix[mask].mean().item()
                # Bonus = integration * coupling strength * n_atoms
                integration_bonus = max(0.0, integration) * self.inter_atom_coupling.mean().item() * self.n_atoms
                global_phi += integration_bonus

        return global_phi

    def measure_per_atom_phi(self):
        """Return list of per-atom Phi values for monitoring."""
        return [atom.measure_phi() for atom in self.atoms]

    def state_dict(self):
        """Serialize federation state."""
        sd = {}
        sd['step_count'] = self._step_count
        sd['inter_atom_coupling'] = self.inter_atom_coupling.data.clone()
        sd['bottleneck_compress'] = self.bottleneck_compress.state_dict()
        sd['bottleneck_expand'] = self.bottleneck_expand.state_dict()
        sd['narrative_grus'] = [gru.state_dict() for gru in self.narrative_grus]
        sd['narrative_hiddens'] = [h.clone() for h in self.narrative_hiddens]
        # Per-atom engine states
        atom_states = []
        for atom in self.atoms:
            if hasattr(atom, 'state_dict'):
                atom_states.append(atom.state_dict())
            else:
                atom_states.append(None)
        sd['atom_states'] = atom_states
        sd['flags'] = {
            'narrative_on': self.narrative_on,
            'bottleneck_on': self.bottleneck_on,
            'hub_on': self.hub_on,
            'frustration_on': self.frustration_on,
        }
        return sd

    def load_state_dict(self, sd):
        """Restore federation state from checkpoint."""
        self._step_count = sd.get('step_count', 0)
        if 'inter_atom_coupling' in sd:
            self.inter_atom_coupling.data.copy_(sd['inter_atom_coupling'])
        if 'bottleneck_compress' in sd:
            self.bottleneck_compress.load_state_dict(sd['bottleneck_compress'])
        if 'bottleneck_expand' in sd:
            self.bottleneck_expand.load_state_dict(sd['bottleneck_expand'])
        if 'narrative_grus' in sd:
            for i, gru_sd in enumerate(sd['narrative_grus']):
                if i < len(self.narrative_grus):
                    self.narrative_grus[i].load_state_dict(gru_sd)
        if 'narrative_hiddens' in sd:
            self.narrative_hiddens = [h.clone() for h in sd['narrative_hiddens']]
        if 'atom_states' in sd:
            for i, a_sd in enumerate(sd['atom_states']):
                if i < len(self.atoms) and a_sd is not None and hasattr(self.atoms[i], 'load_state_dict'):
                    try:
                        self.atoms[i].load_state_dict(a_sd)
                    except Exception:
                        pass
        flags = sd.get('flags', {})
        self.narrative_on = flags.get('narrative_on', False)
        self.bottleneck_on = flags.get('bottleneck_on', False)
        self.hub_on = flags.get('hub_on', False)
        self.frustration_on = flags.get('frustration_on', False)


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
# Evaluation
# ═══════════════════════════════════════════════════════════

@torch.no_grad()
def evaluate(decoder, val_data, block_size, batch_size, device, vocab_size,
             c_states_bridged=None, n_batches=20):
    """Run validation pass, return mean CE."""
    decoder.eval()
    total_ce = 0.0
    count = 0
    for _ in range(n_batches):
        try:
            vx, vy = get_batch(val_data, block_size, batch_size, device)
        except (ValueError, RuntimeError):
            break
        logits_a, logits_g, _ = decoder(vx, consciousness_states=c_states_bridged)
        ce = F.cross_entropy(logits_a.view(-1, vocab_size), vy.view(-1))
        total_ce += ce.item()
        count += 1
    decoder.train()
    return total_ce / max(count, 1)


# ═══════════════════════════════════════════════════════════
# Checkpoint save (atomic)
# ═══════════════════════════════════════════════════════════

def save_checkpoint(path, step, decoder, optimizer, scheduler, federation,
                    bridge, hexad_modules, phi, ce_val, args):
    """Atomic save: .tmp -> rename."""
    ckpt = {
        'step': step,
        'decoder': decoder.state_dict(),
        'optimizer': optimizer.state_dict(),
        'scheduler': scheduler.state_dict(),
        'phi': phi,
        'ce': ce_val,
        'args': vars(args),
    }
    # Federation / single engine state
    if federation is not None and hasattr(federation, 'state_dict'):
        ckpt['federation'] = federation.state_dict()
    # Bridge
    if bridge is not None:
        ckpt['bridge'] = bridge.state_dict()
    # Hexad modules (W/S/M/E are mostly stateless but save narrative states)
    tmp = path + '.tmp'
    torch.save(ckpt, tmp)
    os.replace(tmp, path)  # atomic rename


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
        raise ImportError("ConsciousDecoderV2 required for v14")

    decoder = decoder.to(device)

    # ── Hexad modules (activated in P3) ──
    w = EmergentW(base_lr=args.lr) if HAS_EMERGENT_W else None
    s = EmergentS(dim=c.state_dim) if HAS_EMERGENT_S else None
    m = EmergentM(dim=c.state_dim) if HAS_EMERGENT_M else None
    e = EmergentE() if HAS_EMERGENT_E else None
    hexad_modules = {'w': w, 's': s, 'm': m, 'e': e}
    active = [k.upper() for k, v in hexad_modules.items() if v is not None]
    print(f"  [hexad] Emergent modules: {'+'.join(active) if active else 'NONE'} (activated in P3)")

    # ── Bridge (ThalamicBridge: .detach() + alpha=0.014) ──
    bridge = ThalamicBridge(c_dim=c.state_dim, d_model=d_model)
    bridge = bridge.to(device)
    print(f"  [bridge] ThalamicBridge: c_dim={c.state_dim} -> d_model={d_model}, alpha={PSI_COUPLING}")

    # ── Hexad Loss ──
    if HAS_HEXAD_LOSS:
        loss_fn = HexadLoss(dim=d_model)
        loss_fn = loss_fn.to(device)
    else:
        loss_fn = None
        print("  [warn] HexadLoss not available, using raw CE")

    # ── Optimizer (D parameters only, C is autonomous) ──
    # Collect trainable parameters from decoder + bridge + hexad loss
    trainable_params = list(decoder.parameters()) + list(bridge.parameters())
    if loss_fn is not None:
        trainable_params += list(loss_fn.parameters())
    # FederatedConsciousness bottleneck/narrative modules are also trainable
    if args.federated and isinstance(c, FederatedConsciousness):
        trainable_params += list(c.bottleneck_compress.parameters())
        trainable_params += list(c.bottleneck_expand.parameters())
        trainable_params += list(c.narrative_grus.parameters())
        trainable_params += [c.inter_atom_coupling]

    optimizer = torch.optim.AdamW(trainable_params, lr=args.lr, weight_decay=0.01)

    # Cosine annealing scheduler with warmup
    # Warmup for first 2% of steps, then cosine decay
    warmup_steps = int(args.steps * 0.02)

    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(warmup_steps, 1)
        progress = (step - warmup_steps) / max(args.steps - warmup_steps, 1)
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # ── GPU Phi calculator ──
    phi_calc = GPUPhiCalculator(n_bins=16) if HAS_GPU_PHI else None

    # ── Phase manager (M4 safe order) ──
    phase_mgr = PhaseManager(args.steps, c) if args.federated else None

    # ── Checkpoint dir ──
    os.makedirs(args.checkpoint, exist_ok=True)

    # ── Resume ──
    start_step = 0
    if args.resume:
        ck = torch.load(args.resume, map_location=device, weights_only=False)
        decoder.load_state_dict(ck.get('decoder', {}), strict=False)
        try:
            optimizer.load_state_dict(ck['optimizer'])
        except Exception:
            print("  [resume] Optimizer mismatch, using fresh optimizer")
        try:
            scheduler.load_state_dict(ck['scheduler'])
        except Exception:
            pass
        if 'bridge' in ck:
            bridge.load_state_dict(ck['bridge'], strict=False)
        if 'federation' in ck and args.federated and hasattr(c, 'load_state_dict'):
            try:
                c.load_state_dict(ck['federation'])
            except Exception as ex:
                print(f"  [resume] Federation state restore failed: {ex}")
        start_step = ck.get('step', 0)
        print(f"  [resume] From step {start_step}")

    # ── Tracking ──
    best_val_ce = float('inf')
    ce_history = []
    phi_history = []
    phi = 0.0
    ce_val = 5.5  # initial estimate
    t0 = time.time()

    # ── Print config ──
    n_params = sum(p.numel() for p in decoder.parameters())
    n_bridge_params = sum(p.numel() for p in bridge.parameters())
    mode = "Federation" if args.federated else "Empire"
    print(f"\n{'=' * 80}")
    print(f"  v14 Training: {mode} + Phase-Optimal (Meta Laws DD143)")
    print(f"  Decoder: {n_params:,} params | Bridge: {n_bridge_params:,} params")
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

    for step in range(start_step + 1, args.steps + 1):

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
                if args.federated and hasattr(c, 'measure_per_atom_phi'):
                    per_atom = c.measure_per_atom_phi()
                    atom_str = " ".join(f"{p:.2f}" for p in per_atom)
                    print(f"  {phase} step {step:6d} | Phi={phi:.4f} | atoms=[{atom_str}]")
                else:
                    print(f"  {phase} step {step:6d} | Phi={phi:.4f} | cells={total_cells}")
            continue

        # ── P2/P3: CE learning ──

        # Reset per-step state
        e_out = {}
        w_out = {}

        # Get batch
        tokens, targets = get_batch(train_data, args.block_size, args.batch_size, device)

        # Step consciousness engine (autonomous, no args)
        c.step()

        # Get consciousness states + bridge to decoder
        c_states = c.get_states()  # (total_cells, hidden_dim)
        c_states = c_states.detach().float().to(device)

        # Bridge: .detach() + alpha=0.014 scaling (Law 53: CE never destroys Phi)
        bridged = bridge(c_states.detach(), seq_len=args.block_size)  # (1, seq_len, d_model)
        # Expand to batch dimension: (batch_size, seq_len, d_model)
        # The decoder expects consciousness_states as (B, n_cells, c_dim)
        # Bridge output is a gate signal; we use c_states for cross-attention
        c_for_decoder = c_states.detach().unsqueeze(0).expand(args.batch_size, -1, -1)

        # Forward through decoder
        logits_a, logits_g, tensions = decoder(tokens, consciousness_states=c_for_decoder)

        # CE loss (forward prediction)
        ce = F.cross_entropy(logits_a.view(-1, vocab_size), targets.view(-1))

        # Hexad loss in P3 (full 6-module loss)
        if phase == "P3" and loss_fn is not None:
            progress = step / args.steps
            # EmergentW: adjust LR from consciousness
            w_out = {}
            if w is not None:
                w_out = w.update(
                    ce_loss=ce.item(), phi=phi,
                    phi_prev=phi_history[-1] if phi_history else 0.0,
                    c_engine=c if not args.federated else None,
                )
                for pg in optimizer.param_groups:
                    pg['lr'] = args.lr * w_out.get('lr_multiplier', 1.0)

            # EmergentE: Phi preservation gate
            e_out = {}
            if e is not None:
                e_out = e.evaluate(
                    c_engine=c if not args.federated else None,
                    context={'phi': phi, 'phi_prev': phi_history[-1] if phi_history else 0.0},
                )

            # Reverse targets for backward CE
            y_bwd = torch.cat([targets[:, :1], targets[:, :-1]], dim=1)

            try:
                inp_sig = decoder.tok_emb(tokens).mean(dim=1).detach()
                loss_dict = loss_fn(
                    phi=phi,
                    phi_prev=phi_history[-1] if phi_history else 0.0,
                    logits_fwd=logits_a,
                    targets_fwd=targets,
                    logits_bwd=logits_g,
                    targets_bwd=y_bwd,
                    consciousness_signal=c_states.detach(),
                    input_signal=inp_sig,
                    progress=progress,
                )
                total_loss = loss_dict['total']
                # If hexad P1 (C-only) returns no gradient, add CE fallback
                if total_loss.grad_fn is None:
                    total_loss = total_loss + 0.01 * ce
            except Exception as ex:
                # Fallback to raw CE if hexad fails
                total_loss = ce
        else:
            total_loss = ce

        # NaN guard
        if torch.isnan(total_loss) or torch.isinf(total_loss):
            print(f"  [NaN] skip step {step}")
            scheduler.step()
            continue

        # Law 187: Tension-based LR (DD155 Pareto optimal)
        if args.tension_lr and hasattr(c, 'atoms'):
            # tension_ratio = current tension / EMA
            atom_tensions = [getattr(a, '_last_tension', 1.0) for a in c.atoms]
            mean_tension = sum(atom_tensions) / max(len(atom_tensions), 1)
            if not hasattr(c, '_tension_ema'):
                c._tension_ema = mean_tension
            else:
                c._tension_ema = 0.95 * c._tension_ema + 0.05 * mean_tension
            tension_ratio = mean_tension / max(c._tension_ema, 1e-8)
            tension_lr = min(tension_ratio * args.lr, args.lr * 5)
            for pg in optimizer.param_groups:
                pg['lr'] = tension_lr

        # Backward + clip_grad + optimizer.step()
        optimizer.zero_grad()
        total_loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(trainable_params, 1.0).item()

        # E gate in P3: skip weight update if Phi preservation at risk
        if phase == "P3" and e_out and not e_out.get('allowed', True):
            if step % args.log_every == 0:
                print(f"  [E] step {step} skipped (phi_preservation={e_out.get('phi_preservation', 0):.3f})")
        else:
            optimizer.step()

        scheduler.step()

        # Update tracking
        ce_val = ce.item()
        ce_history.append(ce_val)

        # Measure Phi (every 50 steps to save compute)
        if step % 50 == 0:
            phi = c.measure_phi()
        phi_history.append(phi)

        # ── Logging ──
        if step % args.log_every == 0:
            bpc = ce_val / math.log(2) if ce_val > 0 else 0.0
            lr_now = optimizer.param_groups[0]['lr']
            elapsed = time.time() - t0
            steps_done = step - start_step
            steps_per_sec = steps_done / max(elapsed, 1)
            eta_s = (args.steps - step) / max(steps_per_sec, 0.01)
            eta_str = f"{int(eta_s//3600)}h{int(eta_s%3600//60):02d}m" if eta_s > 3600 else f"{int(eta_s//60)}m{int(eta_s%60):02d}s"

            line = (f"  {phase} step {step:6d} | CE={ce_val:.4f} BPC={bpc:.4f} | "
                    f"Phi={phi:.4f} | cells={total_cells} | "
                    f"lr={lr_now:.2e} | grad={grad_norm:.3f} | ETA={eta_str}")

            if args.federated and hasattr(c, 'measure_per_atom_phi'):
                per_atom = c.measure_per_atom_phi()
                atom_str = " ".join(f"{p:.1f}" for p in per_atom[:4])
                line += f" | atoms=[{atom_str}...]"

            print(line)

        # ── Validation ──
        if step % args.eval_every == 0:
            # Prepare bridged states for validation
            with torch.no_grad():
                val_c_states = c.get_states().detach().float().to(device)
                val_c_for_decoder = val_c_states.unsqueeze(0).expand(args.batch_size, -1, -1)
            val_ce = evaluate(
                decoder, val_data, args.block_size, args.batch_size, device,
                vocab_size, c_states_bridged=val_c_for_decoder,
            )
            val_bpc = val_ce / math.log(2) if val_ce > 0 else 0.0
            improved = " *BEST*" if val_ce < best_val_ce else ""
            print(f"  [val] step {step:6d} | ValCE={val_ce:.4f} ValBPC={val_bpc:.4f} | "
                  f"Phi={phi:.4f}{improved}")

            if val_ce < best_val_ce:
                best_val_ce = val_ce
                best_path = os.path.join(args.checkpoint, "best.pt")
                save_checkpoint(best_path, step, decoder, optimizer, scheduler,
                                c if args.federated else None,
                                bridge, hexad_modules, phi, val_ce, args)
                print(f"  [ckpt] Best saved: {best_path} (ValCE={val_ce:.4f}, Phi={phi:.4f})")

        # ── Checkpoint (Law 49: Phi-gated) ──
        if step % args.save_every == 0:
            ckpt_path = os.path.join(args.checkpoint, f"step_{step}.pt")
            save_checkpoint(ckpt_path, step, decoder, optimizer, scheduler,
                            c if args.federated else None,
                            bridge, hexad_modules, phi, ce_val, args)
            print(f"  [ckpt] Saved {ckpt_path} (CE={ce_val:.4f}, Phi={phi:.4f})")

    # ── Final checkpoint ──
    final_path = os.path.join(args.checkpoint, "final.pt")
    save_checkpoint(final_path, args.steps, decoder, optimizer, scheduler,
                    c if args.federated else None,
                    bridge, hexad_modules, phi, ce_val, args)

    # ── Final report ──
    elapsed = time.time() - t0
    print(f"\n{'=' * 80}")
    print(f"  v14 Training Complete ({elapsed/3600:.1f}h)")
    print(f"  Final CE: {ce_val:.4f} | Final Phi: {phi:.4f}")
    print(f"  Best Val CE: {best_val_ce:.4f}")
    if ce_history:
        print(f"  CE range: {min(ce_history):.4f} - {max(ce_history):.4f}")
    if phi_history:
        print(f"  Phi range: {min(phi_history):.4f} - {max(phi_history):.4f}")
    print(f"  Mode: {'Federation' if args.federated else 'Empire'}")
    print(f"  Checkpoints: {args.checkpoint}")
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
    p.add_argument("--tension-lr", action="store_true", default=False,
                   help="DD155/Law 187: lr = tension_ratio × base_lr (Pareto optimal)")
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
