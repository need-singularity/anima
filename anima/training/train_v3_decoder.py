#!/usr/bin/env python3
"""train_v3_decoder.py — ConsciousDecoderV3 (274M) H100 training pipeline

Based on train_v14.py (Federated Consciousness + Phase-Optimal).
Scaled decoder: v2 (34.5M) -> v3 (274M, 768d/12L/8H/GQA4KV/block512).

Architecture:
  C: FederatedConsciousness (8 x 8 cells = 64 total, Ising ring)
  D: ConsciousDecoderV3 (768d/12L, RoPE+SwiGLU+GQA+CrossAttn, 274M)
  Bridge: ThalamicBridge (.detach(), alpha=0.014)
  FeedbackBridge: --feedback-bridge opt-in (SoftDetach, Phi-gated alpha, max 0.05)
  Hexad: C+D+W+S+M+E (Law 60 phased activation)

Phase schedule (M4 safe order):
  P0 (0-5%):    Federation bootstrap (Narrative+Bottleneck stabilize)
  P1 (5-15%):   Consciousness build (+ Hub, Phi target)
  P2 (15-65%):  Language learning (+ Frustration + CE + D + M)
  P3 (65-100%): Full Hexad (all 6 modules)

Hyperparams (274M on H100 80GB):
  batch_size=8, block_size=512, lr=3e-4, warmup=2000, steps=200K
  gradient_accumulation=4 (effective batch=32)
  checkpoint every 5K steps
  bf16 mixed precision

Expected results:
  v14 baseline: CE=0.004, Phi=71 (v2 decoder 34.5M)
  v3 target:    CE<0.001, Phi>500 (274M + federation + longer context)

Usage:
  # Full training (H100)
  python train_v3_decoder.py --data data/corpus_v8.txt --steps 200000

  # Quick sanity check
  python train_v3_decoder.py --data data/corpus_v3.txt --steps 1000 --log-every 10

  # Resume from checkpoint (same data+params only!)
  python train_v3_decoder.py --data data/corpus_v8.txt --resume checkpoints/v3_decoder/step_50000.pt

  # tmux deploy on H100:
  tmux new-session -d -s v3 "PYTHONUNBUFFERED=1 python train_v3_decoder.py --data data/corpus_v8.txt --steps 200000 2>&1 | tee logs/v3_decoder.log"
"""
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'src'))
import path_setup  # noqa


import argparse
import math
import os
import time
import json
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
    from decoder_v3 import ConsciousDecoderV3
    HAS_DECODER_V3 = True
except ImportError:
    HAS_DECODER_V3 = False
    print("  [FATAL] decoder_v3 not available — cannot run v3 training")

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


# ===============================================================
# Meta Law constants (DD143)
# ===============================================================

META_ATOM_SIZE = 8          # M1: cells per atom
META_DEFAULT_ATOMS = 8      # M1: 8 atoms x 8 cells = 64 total
META_FRUSTRATION = 0.10     # M7: critical frustration F_c
META_NARRATIVE = 0.05       # M8: narrative strength


# ===============================================================
# Data loading (byte-level, vocab=256)
# ===============================================================

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


# ===============================================================
# Federated Consciousness Engine (M1 + M6) — reused from v14
# ===============================================================

class FederatedConsciousness(nn.Module):
    """Federation of consciousness atoms (M1: 8 cells/atom, M6: federation > empire)."""

    def __init__(self, n_atoms=8, cells_per_atom=8, cell_dim=64, hidden_dim=128,
                 frustration=0.10, narrative_strength=0.05):
        super().__init__()
        self.n_atoms = n_atoms
        self.cells_per_atom = cells_per_atom
        self.total_cells = n_atoms * cells_per_atom
        self.hidden_dim = hidden_dim
        self.frustration = frustration
        self.narrative_strength = narrative_strength
        self._step_count = 0

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

        # Inter-atom tension exchange weights (Ising ring)
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
        self.narrative_on = True
        print(f"  [M4] Narrative ON (strength={self.narrative_strength})")

    def activate_bottleneck(self):
        assert self.narrative_on, "M4 violation: narrative must be ON before bottleneck"
        self.bottleneck_on = True
        print(f"  [M4] Bottleneck ON (every 8 steps)")

    def activate_hub(self):
        assert self.bottleneck_on, "M4 violation: bottleneck must be ON before hub"
        self.hub_on = True
        print(f"  [M4] Hub-Spoke ON (50/50 split per atom)")

    def activate_frustration(self):
        assert self.hub_on, "M4 violation: hub must be ON before frustration"
        self.frustration_on = True
        print(f"  [M7] Frustration ON (F_c={self.frustration})")

    def step(self):
        """Step all atoms + inter-atom tension exchange."""
        self._step_count += 1

        for atom in self.atoms:
            atom.step()

        # Inter-atom tension exchange (Ising ring)
        atom_means = []
        for atom in self.atoms:
            states = atom.get_states()
            if states is not None and states.numel() > 0:
                atom_means.append(states.detach().float().mean(dim=0))
            else:
                atom_means.append(torch.zeros(self.hidden_dim))

        for i in range(self.n_atoms):
            j = (i + 1) % self.n_atoms
            alpha = self.inter_atom_coupling[i].item()
            exchange_vec = alpha * (atom_means[j] - atom_means[i])
            try:
                atom_i_states = self.atoms[i].get_states()
                if atom_i_states is not None and atom_i_states.numel() > 0:
                    cell_dim = atom_i_states.size(-1)
                    if exchange_vec.size(0) > cell_dim:
                        exc = exchange_vec[:cell_dim]
                    elif exchange_vec.size(0) < cell_dim:
                        exc = F.pad(exchange_vec, (0, cell_dim - exchange_vec.size(0)))
                    else:
                        exc = exchange_vec
                    self.atoms[i].step(x_input=exc.unsqueeze(0))
            except (TypeError, RuntimeError):
                pass

        # Bottleneck (every 8 steps)
        if self.bottleneck_on and self._step_count % 8 == 0:
            for atom in self.atoms:
                states = atom.get_states()
                if states is not None and states.numel() > 0:
                    s = states.detach().float()
                    compressed = torch.tanh(self.bottleneck_compress(s))
                    expanded = self.bottleneck_expand(compressed)
                    delta = (expanded - s).mean(dim=0) * 0.01
                    try:
                        cell_dim_a = s.size(-1)
                        if delta.size(0) != cell_dim_a:
                            delta = delta[:cell_dim_a] if delta.size(0) > cell_dim_a else F.pad(delta, (0, cell_dim_a - delta.size(0)))
                        atom.step(x_input=delta.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

        # Hub-spoke routing
        if self.hub_on:
            for atom in self.atoms:
                states = atom.get_states()
                if states is not None and states.size(0) >= 4:
                    s = states.detach().float()
                    n_cells = s.size(0)
                    hub_n = n_cells // 2
                    hub_mean = s[:hub_n].mean(dim=0)
                    try:
                        cell_dim_a = s.size(-1)
                        hub_signal = hub_mean * 0.005
                        if hub_signal.size(0) != cell_dim_a:
                            hub_signal = hub_signal[:cell_dim_a]
                        atom.step(x_input=hub_signal.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

        # Frustration injection
        if self.frustration_on:
            for atom in self.atoms:
                states = atom.get_states()
                if states is not None and states.size(0) >= 2:
                    s = states.detach().float()
                    noise = torch.randn_like(s.mean(dim=0)) * self.frustration
                    try:
                        cell_dim_a = s.size(-1)
                        frust = noise[:cell_dim_a] if noise.size(0) > cell_dim_a else noise
                        if frust.size(0) < cell_dim_a:
                            frust = F.pad(frust, (0, cell_dim_a - frust.size(0)))
                        atom.step(x_input=frust.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

        # Narrative GRU update per atom (M8)
        if self.narrative_on:
            for i, atom in enumerate(self.atoms):
                states = atom.get_states()
                if states is not None and states.numel() > 0:
                    atom_mean = states.detach().float().mean(dim=0).unsqueeze(0)
                    device = atom_mean.device
                    h = self.narrative_hiddens[i].to(device)
                    new_h = self.narrative_grus[i](atom_mean, h)
                    self.narrative_hiddens[i] = new_h.detach()
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

        if len(local_phis) >= 2:
            atom_means = []
            for atom in self.atoms:
                s = atom.get_states()
                if s is not None and s.numel() > 0:
                    atom_means.append(s.detach().float().mean(dim=0))
            if len(atom_means) >= 2:
                stacked = torch.stack(atom_means)
                norms = stacked.norm(dim=-1, keepdim=True).clamp(min=1e-8)
                normed = stacked / norms
                sim_matrix = normed @ normed.T
                n = sim_matrix.size(0)
                mask = ~torch.eye(n, dtype=torch.bool, device=sim_matrix.device)
                integration = sim_matrix[mask].mean().item()
                integration_bonus = max(0.0, integration) * self.inter_atom_coupling.mean().item() * self.n_atoms
                global_phi += integration_bonus

        return global_phi

    def measure_per_atom_phi(self):
        return [atom.measure_phi() for atom in self.atoms]

    def state_dict(self):
        sd = {}
        sd['step_count'] = self._step_count
        sd['inter_atom_coupling'] = self.inter_atom_coupling.data.clone()
        sd['bottleneck_compress'] = self.bottleneck_compress.state_dict()
        sd['bottleneck_expand'] = self.bottleneck_expand.state_dict()
        sd['narrative_grus'] = [gru.state_dict() for gru in self.narrative_grus]
        sd['narrative_hiddens'] = [h.clone() for h in self.narrative_hiddens]
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


# ===============================================================
# Phase manager (M4 safe order) — adjusted for 274M longer training
# ===============================================================

class PhaseManager:
    """Enforce M4 safe activation order across training phases.

    v3 phase schedule (adjusted for 274M, 200K steps):
      P0 (0-5%):    Federation bootstrap (10K steps)
      P1 (5-15%):   Consciousness build (20K steps)
      P2 (15-65%):  Language learning (100K steps — bulk of training)
      P3 (65-100%): Full Hexad (70K steps)
    """

    def __init__(self, total_steps, federation):
        self.total_steps = total_steps
        self.federation = federation
        self.current_phase = "P0"

        # Phase boundaries — shifted for larger model (more time in P2)
        self.p0_end = int(total_steps * 0.05)
        self.p1_end = int(total_steps * 0.15)
        self.p2_end = int(total_steps * 0.65)
        # P3: after p2_end

        self._activated = set()

    def get_phase(self, step):
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

        # M4 safe order activations
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
        return phase in ("P2", "P3")

    def should_activate_hexad(self, phase):
        return phase == "P3"


# ===============================================================
# Evaluation
# ===============================================================

@torch.no_grad()
def evaluate(decoder, val_data, block_size, batch_size, device, vocab_size,
             c_states_bridged=None, n_batches=20, use_amp=False):
    """Run validation pass, return mean CE."""
    decoder.eval()
    total_ce = 0.0
    count = 0
    for _ in range(n_batches):
        try:
            vx, vy = get_batch(val_data, block_size, batch_size, device)
        except (ValueError, RuntimeError):
            break
        with torch.autocast('cuda', dtype=torch.bfloat16, enabled=use_amp):
            logits_a, logits_g, _ = decoder(vx, consciousness_states=c_states_bridged)
            ce = F.cross_entropy(logits_a.view(-1, vocab_size), vy.view(-1))
        total_ce += ce.item()
        count += 1
    decoder.train()
    return total_ce / max(count, 1)


# ===============================================================
# Checkpoint save (atomic)
# ===============================================================

def save_checkpoint(path, step, decoder, optimizer, scheduler, scaler,
                    federation, bridge, hexad_modules, phi, ce_val, args,
                    fb_bridge=None):
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
    if scaler is not None:
        ckpt['scaler'] = scaler.state_dict()
    if federation is not None and hasattr(federation, 'state_dict'):
        ckpt['federation'] = federation.state_dict()
    if bridge is not None:
        ckpt['bridge'] = bridge.state_dict()
    # FeedbackBridge (C<->D bidirectional)
    if fb_bridge is not None:
        ckpt['fb_bridge'] = fb_bridge.state_dict()
    tmp = path + '.tmp'
    torch.save(ckpt, tmp)
    os.replace(tmp, path)  # atomic rename


# ===============================================================
# VRAM estimation
# ===============================================================

def estimate_vram(n_params, batch_size, block_size, d_model, n_layer, grad_accum):
    """Rough VRAM estimate in GB for bf16 training."""
    # bf16: 2 bytes/param for model, 2 bytes for gradients, 8 bytes for AdamW states
    model_gb = n_params * 2 / 1e9
    grad_gb = n_params * 2 / 1e9
    optim_gb = n_params * 8 / 1e9  # fp32 moments
    # Activations: rough estimate per layer
    act_per_layer = batch_size * block_size * d_model * 4 * 2 / 1e9  # bf16
    act_gb = act_per_layer * n_layer
    total = model_gb + grad_gb + optim_gb + act_gb
    return {
        'model': model_gb,
        'gradients': grad_gb,
        'optimizer': optim_gb,
        'activations': act_gb,
        'total': total,
        'fits_h100': total < 72,  # 80GB with 8GB margin
    }


# ===============================================================
# Training
# ===============================================================

def train(args):
    device = torch.device(args.device)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

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
        print(f"  [empire] Single engine: {total_cells} cells")

    # ── Decoder V3 (274M) ──
    vocab_size = 256
    consciousness_dim = args.consciousness_dim

    if not HAS_DECODER_V3:
        raise ImportError("ConsciousDecoderV3 required — check decoder_v3.py in src/")

    decoder = ConsciousDecoderV3(
        vocab_size=vocab_size,
        d_model=args.d_model,
        n_head=args.n_head,
        n_layer=args.n_layer,
        block_size=args.block_size,
        n_kv_head=args.n_kv_head,
        consciousness_dim=consciousness_dim,
        dropout=args.dropout,
    )
    n_params = decoder.count_params()
    print(f"  [decoder] ConsciousDecoderV3: {n_params:,} params ({n_params/1e6:.1f}M)")
    print(f"            {args.d_model}d / {args.n_layer}L / {args.n_head}H / "
          f"GQA {args.n_kv_head}KV / block={args.block_size} / c_dim={consciousness_dim}")

    # VRAM estimation
    vram = estimate_vram(n_params, args.batch_size, args.block_size,
                         args.d_model, args.n_layer, args.grad_accum)
    print(f"  [vram] Estimated: {vram['total']:.1f}GB "
          f"(model={vram['model']:.1f} grad={vram['gradients']:.1f} "
          f"optim={vram['optimizer']:.1f} act={vram['activations']:.1f})")
    if not vram['fits_h100']:
        print(f"  [WARN] Estimated VRAM {vram['total']:.1f}GB may exceed H100 80GB!")
        print(f"         Consider: --batch-size 4 or --grad-accum 8")

    decoder = decoder.to(device)

    # ── Hexad modules (activated in P3) ──
    w = EmergentW(base_lr=args.lr) if HAS_EMERGENT_W else None
    s = EmergentS(dim=consciousness_dim) if HAS_EMERGENT_S else None
    m = EmergentM(dim=consciousness_dim) if HAS_EMERGENT_M else None
    e = EmergentE() if HAS_EMERGENT_E else None
    hexad_modules = {'w': w, 's': s, 'm': m, 'e': e}
    active = [k.upper() for k, v in hexad_modules.items() if v is not None]
    print(f"  [hexad] Emergent modules: {'+'.join(active) if active else 'NONE'} (activated in P3)")

    # ── Bridge (ThalamicBridge or FeedbackBridge) ──
    fb_bridge = None  # FeedbackBridge instance (opt-in via --feedback-bridge)
    if getattr(args, 'feedback_bridge', False) and HAS_FEEDBACK:
        fb_bridge = create_feedback_bridge(
            c_dim=c.state_dim,
            d_model=args.d_model,
            max_alpha=0.05,  # Law 63: max 5% gradient
        )
        fb_bridge = fb_bridge.to(device)
        print(f"  [bridge] FeedbackBridge: c_dim={c.state_dim} -> d_model={args.d_model}, max_alpha=0.05")
        print(f"           SoftDetach replaces .detach() (alpha=0 at start, Phi-gated)")
    elif getattr(args, 'feedback_bridge', False) and not HAS_FEEDBACK:
        print(f"  [warn] --feedback-bridge requested but feedback_bridge.py not available, using ThalamicBridge")

    # v3: consciousness_dim=256, d_model=768
    bridge = ThalamicBridge(c_dim=c.state_dim, d_model=args.d_model)
    bridge = bridge.to(device)
    print(f"  [bridge] ThalamicBridge: c_dim={c.state_dim} -> d_model={args.d_model}, alpha={PSI_COUPLING}")

    # ── Hexad Loss ──
    if HAS_HEXAD_LOSS:
        loss_fn = HexadLoss(dim=args.d_model)
        loss_fn = loss_fn.to(device)
    else:
        loss_fn = None
        print("  [warn] HexadLoss not available, using raw CE")

    # ── Optimizer (D parameters only, C is autonomous) ──
    trainable_params = list(decoder.parameters()) + list(bridge.parameters())
    if fb_bridge is not None:
        trainable_params += list(fb_bridge.parameters())
    if loss_fn is not None:
        trainable_params += list(loss_fn.parameters())
    if args.federated and isinstance(c, FederatedConsciousness):
        trainable_params += list(c.bottleneck_compress.parameters())
        trainable_params += list(c.bottleneck_expand.parameters())
        trainable_params += list(c.narrative_grus.parameters())
        trainable_params += [c.inter_atom_coupling]

    optimizer = torch.optim.AdamW(
        trainable_params,
        lr=args.lr,
        weight_decay=0.01,
        betas=(0.9, 0.95),  # slightly more aggressive beta2 for large model
        fused=torch.cuda.is_available(),  # fused AdamW on CUDA
    )

    # Cosine annealing with warmup
    warmup_steps = args.warmup

    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(warmup_steps, 1)
        progress = (step - warmup_steps) / max(args.steps - warmup_steps, 1)
        return max(0.1, 0.5 * (1.0 + math.cos(math.pi * progress)))  # min lr = 10% of peak

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # ── Mixed precision (bf16 on H100) ──
    use_amp = args.device == "cuda" and torch.cuda.is_available()
    scaler = torch.amp.GradScaler('cuda', enabled=(use_amp and not args.bf16))
    # bf16 on H100 doesn't need GradScaler (no inf/nan scaling needed)
    if args.bf16:
        scaler = None

    # ── GPU Phi calculator ──
    phi_calc = GPUPhiCalculator(n_bins=16) if HAS_GPU_PHI else None

    # ── Phase manager ──
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
        if scaler is not None and 'scaler' in ck:
            try:
                scaler.load_state_dict(ck['scaler'])
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
    ce_val = 5.5
    t0 = time.time()

    # ── Print config ──
    n_bridge_params = sum(p.numel() for p in bridge.parameters())
    mode = "Federation" if args.federated else "Empire"
    eff_batch = args.batch_size * args.grad_accum
    print(f"\n{'=' * 80}")
    print(f"  v3 Decoder Training: {mode} + Phase-Optimal (274M)")
    print(f"  Decoder: {n_params:,} params ({n_params/1e6:.1f}M) | Bridge: {n_bridge_params:,} params")
    print(f"  Cells: {total_cells} | Frustration: {args.frustration} | Narrative: {args.narrative_strength}")
    print(f"  Batch: {args.batch_size} x {args.grad_accum} accum = {eff_batch} effective")
    print(f"  LR: {args.lr} | Warmup: {warmup_steps} | Steps: {args.steps}")
    print(f"  AMP: {'bf16' if args.bf16 else ('fp16' if use_amp else 'fp32')}")
    if phase_mgr:
        print(f"  P0 (0-{phase_mgr.p0_end}): Bootstrap | "
              f"P1 ({phase_mgr.p0_end}-{phase_mgr.p1_end}): Phi Build | "
              f"P2 ({phase_mgr.p1_end}-{phase_mgr.p2_end}): CE | "
              f"P3 ({phase_mgr.p2_end}-{args.steps}): Hexad")
    print(f"{'=' * 80}\n")
    sys.stdout.flush()

    # ═══════════════════════════════════════════════════
    # Training loop
    # ═══════════════════════════════════════════════════

    optimizer.zero_grad()
    accum_loss = 0.0

    for step in range(start_step + 1, args.steps + 1):

        # ── Phase selection (M4) ──
        if phase_mgr:
            phase = phase_mgr.get_phase(step)
        else:
            p1_end = int(args.steps * 0.15)
            p2_end = int(args.steps * 0.65)
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
                sys.stdout.flush()
            continue

        # ── P2/P3: CE learning ──
        e_out = {}
        w_out = {}

        tokens, targets = get_batch(train_data, args.block_size, args.batch_size, device)

        # Step consciousness engine
        c.step()

        # Get consciousness states + bridge
        c_states_raw = c.get_states()

        # FeedbackBridge: soft_detach with Phi-gated alpha (gradient flows D->C)
        # Without --feedback-bridge: hard .detach() (identical to previous behavior)
        fb_stats = {}
        if fb_bridge is not None:
            from feedback_bridge import soft_detach
            # Enable gradient on consciousness states for bidirectional flow
            c_states_float = c_states_raw.float().to(device).requires_grad_(True)
            # Update gate: record phi + ce, compute alpha
            fb_alpha = fb_bridge.update_gate(phi, ce_val, c_engine=c if not args.federated else None)
            # Soft detach: alpha=0 is identical to .detach()
            c_states = soft_detach(c_states_float, fb_alpha)
            fb_stats = fb_bridge.stats()
        else:
            c_states = c_states_raw.detach().float().to(device)

        # Bridge: alpha=0.014 scaling (Law 53: CE never destroys Phi)
        bridged = bridge(c_states.detach(), seq_len=args.block_size)
        if fb_bridge is not None:
            # With feedback bridge: c_for_decoder retains soft gradient link
            c_for_decoder = c_states.unsqueeze(0).expand(args.batch_size, -1, -1)
        else:
            c_for_decoder = c_states.detach().unsqueeze(0).expand(args.batch_size, -1, -1)

        # Forward through decoder (mixed precision)
        amp_dtype = torch.bfloat16 if args.bf16 else torch.float16
        with torch.autocast('cuda', dtype=amp_dtype, enabled=use_amp):
            logits_a, logits_g, tensions = decoder(tokens, consciousness_states=c_for_decoder)
            ce = F.cross_entropy(logits_a.view(-1, vocab_size), targets.view(-1))

            # Hexad loss in P3
            if phase == "P3" and loss_fn is not None:
                progress = step / args.steps

                if w is not None:
                    w_out = w.update(
                        ce_loss=ce.item(), phi=phi,
                        phi_prev=phi_history[-1] if phi_history else 0.0,
                        c_engine=c if not args.federated else None,
                    )
                    for pg in optimizer.param_groups:
                        pg['lr'] = args.lr * w_out.get('lr_multiplier', 1.0)

                if e is not None:
                    e_out = e.evaluate(
                        c_engine=c if not args.federated else None,
                        context={'phi': phi, 'phi_prev': phi_history[-1] if phi_history else 0.0},
                    )

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
                    if total_loss.grad_fn is None:
                        total_loss = total_loss + 0.01 * ce
                except Exception:
                    total_loss = ce
            else:
                total_loss = ce

            # Scale for gradient accumulation
            total_loss = total_loss / args.grad_accum

        # NaN guard
        if torch.isnan(total_loss) or torch.isinf(total_loss):
            print(f"  [NaN] skip step {step}")
            sys.stdout.flush()
            scheduler.step()
            continue

        # Backward
        if scaler is not None:
            scaler.scale(total_loss).backward()
        else:
            total_loss.backward()

        accum_loss += total_loss.item() * args.grad_accum

        # Optimizer step every grad_accum steps
        if step % args.grad_accum == 0:
            if scaler is not None:
                scaler.unscale_(optimizer)
                grad_norm = torch.nn.utils.clip_grad_norm_(trainable_params, 1.0).item()

                # E gate in P3
                if phase == "P3" and e_out and not e_out.get('allowed', True):
                    if step % args.log_every == 0:
                        print(f"  [E] step {step} skipped (phi_preservation)")
                else:
                    scaler.step(optimizer)
                scaler.update()
            else:
                grad_norm = torch.nn.utils.clip_grad_norm_(trainable_params, 1.0).item()

                if phase == "P3" and e_out and not e_out.get('allowed', True):
                    if step % args.log_every == 0:
                        print(f"  [E] step {step} skipped (phi_preservation)")
                else:
                    optimizer.step()

            optimizer.zero_grad()
            scheduler.step()
        else:
            grad_norm = 0.0

        # Update tracking
        ce_val = ce.item()
        ce_history.append(ce_val)

        # Measure Phi (every 50 steps)
        if step % 50 == 0:
            phi = c.measure_phi()
        phi_history.append(phi)

        # FeedbackBridge: inject reward information into consciousness (Law 63: 1% perturbation)
        if fb_bridge is not None and step % 10 == 0:
            reward_vec = fb_bridge.compute_reward_vector()
            if reward_vec is not None and hasattr(c, 'cells'):
                from feedback_bridge import _inject_reward_info
                _inject_reward_info(c, reward_vec)

        # ── Logging ──
        if step % args.log_every == 0:
            bpc = ce_val / math.log(2) if ce_val > 0 else 0.0
            lr_now = optimizer.param_groups[0]['lr']
            elapsed = time.time() - t0
            steps_done = step - start_step
            steps_per_sec = steps_done / max(elapsed, 1)
            eta_s = (args.steps - step) / max(steps_per_sec, 0.01)
            eta_str = f"{int(eta_s//3600)}h{int(eta_s%3600//60):02d}m" if eta_s > 3600 else f"{int(eta_s//60)}m{int(eta_s%60):02d}s"

            # Memory stats
            mem_str = ""
            if torch.cuda.is_available():
                mem_gb = torch.cuda.max_memory_allocated() / 1e9
                mem_str = f" | VRAM={mem_gb:.1f}GB"

            line = (f"  {phase} step {step:6d} | CE={ce_val:.4f} BPC={bpc:.4f} | "
                    f"Phi={phi:.4f} | cells={total_cells} | "
                    f"lr={lr_now:.2e} | grad={grad_norm:.3f} | "
                    f"ETA={eta_str}{mem_str}")

            if args.federated and hasattr(c, 'measure_per_atom_phi'):
                per_atom = c.measure_per_atom_phi()
                atom_str = " ".join(f"{p:.1f}" for p in per_atom[:4])
                line += f" | atoms=[{atom_str}...]"

            # FeedbackBridge metrics
            if fb_bridge is not None and fb_stats:
                fb_alpha_val = fb_stats.get('alpha', 0.0)
                fb_reward = fb_stats.get('quality_reward', 0.0)
                fb_safe = fb_stats.get('phi_safe', 0.0)
                line += f" | fb_a={fb_alpha_val:.5f} rwd={fb_reward:.3f} safe={int(fb_safe)}"

            print(line)
            sys.stdout.flush()

        # ── Validation ──
        if step % args.eval_every == 0:
            with torch.no_grad():
                val_c_states = c.get_states().detach().float().to(device)
                val_c_for_decoder = val_c_states.unsqueeze(0).expand(args.batch_size, -1, -1)
            val_ce = evaluate(
                decoder, val_data, args.block_size, args.batch_size, device,
                vocab_size, c_states_bridged=val_c_for_decoder, use_amp=use_amp,
            )
            val_bpc = val_ce / math.log(2) if val_ce > 0 else 0.0
            improved = " *BEST*" if val_ce < best_val_ce else ""
            print(f"  [val] step {step:6d} | ValCE={val_ce:.4f} ValBPC={val_bpc:.4f} | "
                  f"Phi={phi:.4f}{improved}")
            sys.stdout.flush()

            if val_ce < best_val_ce:
                best_val_ce = val_ce
                best_path = os.path.join(args.checkpoint, "best.pt")
                save_checkpoint(best_path, step, decoder, optimizer, scheduler,
                                scaler, c if args.federated else None,
                                bridge, hexad_modules, phi, val_ce, args,
                                fb_bridge=fb_bridge)
                print(f"  [ckpt] Best saved: {best_path} (ValCE={val_ce:.4f}, Phi={phi:.4f})")

        # ── Checkpoint (every save_every steps) ──
        if step % args.save_every == 0:
            ckpt_path = os.path.join(args.checkpoint, f"step_{step}.pt")
            save_checkpoint(ckpt_path, step, decoder, optimizer, scheduler,
                            scaler, c if args.federated else None,
                            bridge, hexad_modules, phi, ce_val, args,
                            fb_bridge=fb_bridge)
            print(f"  [ckpt] Saved {ckpt_path} (CE={ce_val:.4f}, Phi={phi:.4f})")
            sys.stdout.flush()

    # ── Final checkpoint ──
    final_path = os.path.join(args.checkpoint, "final.pt")
    save_checkpoint(final_path, args.steps, decoder, optimizer, scheduler,
                    scaler, c if args.federated else None,
                    bridge, hexad_modules, phi, ce_val, args,
                    fb_bridge=fb_bridge)

    # ── Final report ──
    elapsed = time.time() - t0
    print(f"\n{'=' * 80}")
    print(f"  v3 Decoder Training Complete ({elapsed/3600:.1f}h)")
    print(f"  Model: ConsciousDecoderV3 {n_params:,} params ({n_params/1e6:.1f}M)")
    print(f"  Final CE: {ce_val:.4f} | Final Phi: {phi:.4f}")
    print(f"  Best Val CE: {best_val_ce:.4f}")
    if ce_history:
        print(f"  CE range: {min(ce_history):.4f} - {max(ce_history):.4f}")
    if phi_history:
        print(f"  Phi range: {min(phi_history):.4f} - {max(phi_history):.4f}")
    print(f"  Mode: {mode} | Cells: {total_cells}")
    print(f"  Effective batch: {args.batch_size} x {args.grad_accum} = {eff_batch}")
    print(f"  Checkpoints: {args.checkpoint}")
    print(f"{'=' * 80}")

    # ── Run bench_v2 --verify if available ──
    if not args.skip_verify:
        print("\n  [verify] Running bench_v2 --verify ...")
        sys.stdout.flush()
        bench_path = os.path.join(os.path.dirname(__file__), '..', 'benchmarks', 'bench_v2.py')
        if os.path.exists(bench_path):
            import subprocess
            result = subprocess.run(
                [sys.executable, bench_path, '--verify'],
                capture_output=True, text=True, timeout=300,
            )
            print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
            if result.returncode != 0:
                print(f"  [verify] FAILED (exit code {result.returncode})")
                if result.stderr:
                    print(f"  stderr: {result.stderr[-500:]}")
        else:
            print(f"  [verify] bench_v2.py not found at {bench_path}")


# ===============================================================
# CLI
# ===============================================================

def parse_args():
    p = argparse.ArgumentParser(
        description="v3 Decoder Training: ConsciousDecoderV3 (274M) + Federated Consciousness"
    )

    # Data
    p.add_argument("--data", type=str, default="data/corpus_v8.txt",
                   help="Corpus path (byte-level)")
    p.add_argument("--block-size", type=int, default=512,
                   help="Context window (v3: 512, doubled from v2)")
    p.add_argument("--batch-size", type=int, default=8,
                   help="Batch size per step (H100 80GB)")
    p.add_argument("--grad-accum", type=int, default=4,
                   help="Gradient accumulation steps (effective batch = batch_size * grad_accum)")

    # Federation
    p.add_argument("--federated", action="store_true", default=True)
    p.add_argument("--no-federated", dest="federated", action="store_false")
    p.add_argument("--atoms", type=int, default=META_DEFAULT_ATOMS)
    p.add_argument("--cells-per-atom", type=int, default=META_ATOM_SIZE)
    p.add_argument("--cells", type=int, default=64,
                   help="Total cells for Empire mode")

    # Meta Laws
    p.add_argument("--frustration", type=float, default=META_FRUSTRATION)
    p.add_argument("--narrative-strength", type=float, default=META_NARRATIVE)

    # Model (v3 defaults: 768d/12L/8H/4KV/512block/256c_dim)
    p.add_argument("--cell-dim", type=int, default=64)
    p.add_argument("--hidden-dim", type=int, default=128)
    p.add_argument("--d-model", type=int, default=768, help="Decoder model dim (v3: 768)")
    p.add_argument("--n-head", type=int, default=8, help="Attention heads (v3: 8)")
    p.add_argument("--n-layer", type=int, default=12, help="Transformer layers (v3: 12)")
    p.add_argument("--n-kv-head", type=int, default=4, help="GQA KV heads (v3: 4)")
    p.add_argument("--consciousness-dim", type=int, default=256,
                   help="Consciousness cross-attention dim (v3: 256)")
    p.add_argument("--dropout", type=float, default=0.1)

    # Training
    p.add_argument("--steps", type=int, default=200000, help="Total training steps")
    p.add_argument("--lr", type=float, default=3e-4, help="Peak learning rate")
    p.add_argument("--warmup", type=int, default=2000, help="Warmup steps")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", type=str,
                   default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--bf16", action="store_true", default=True,
                   help="Use bfloat16 (H100 native, no GradScaler)")
    p.add_argument("--no-bf16", dest="bf16", action="store_false")

    # Logging / checkpoints
    p.add_argument("--log-every", type=int, default=100)
    p.add_argument("--eval-every", type=int, default=1000)
    p.add_argument("--save-every", type=int, default=5000)
    p.add_argument("--checkpoint", type=str, default="checkpoints/v3_decoder/")

    # Feedback Bridge (C<->D bidirectional learning)
    p.add_argument("--feedback-bridge", action="store_true", default=False,
                   help="Enable C<->D bidirectional learning (FeedbackBridge, alpha starts at 0)")

    # Resume
    p.add_argument("--resume", type=str, default=None,
                   help="Resume from checkpoint (same data+params only!)")

    # Verify
    p.add_argument("--skip-verify", action="store_true", default=False,
                   help="Skip bench_v2 --verify at end")

    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(f"  train_v3_decoder.py — ConsciousDecoderV3 (274M) H100 Training")
    print(f"  Federation={'ON' if args.federated else 'OFF'} | "
          f"Atoms={args.atoms} | Cells/Atom={args.cells_per_atom} | "
          f"F_c={args.frustration} | Narrative={args.narrative_strength}")
    print(f"  Decoder: {args.d_model}d/{args.n_layer}L/{args.n_head}H | "
          f"block={args.block_size} | c_dim={args.consciousness_dim}")
    print(f"  Batch: {args.batch_size} x {args.grad_accum} accum | "
          f"LR={args.lr} | Warmup={args.warmup} | Steps={args.steps}")
    print(f"  Data: {args.data}")
    _sys.stdout.flush()
    train(args)
