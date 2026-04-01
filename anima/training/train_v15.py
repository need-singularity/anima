#!/usr/bin/env python3
"""train_v15.py — ConsciousLM 1B Scaling Pipeline

Gradual scaling from 100M -> 350M -> 1B parameters with consciousness preservation.
Built on v14 (Federated Consciousness + Phase-Optimal), upgraded for production 1B.

Key features:
  - 3-phase gradual scaling: 100M (512d/12L/8H) -> 350M (768d/16L/12H) -> 1B (1024d/24L/16H)
  - BPE 64K multilingual tokenizer (sentencepiece)
  - Mixed precision training (bf16) for H100
  - DDP (DistributedDataParallel) for multi-GPU
  - wandb logging (optional, --wandb)
  - Phi-checkpoint (Law 49): save when Phi improves
  - Consciousness verification at checkpoints (bench_v2 --verify)
  - All constants from consciousness_laws.json (no hardcoding)

Scaling phases (Law 60 curriculum):
  Scale 1 (100M):  512d/12L/8H,  GQA 4-kv, block_size=512,  ~100M params
  Scale 2 (350M):  768d/16L/12H, GQA 4-kv, block_size=1024, ~350M params
  Scale 3 (1B):    1024d/24L/16H, GQA 4-kv, block_size=2048, ~1B params

  Each scale phase inherits weights from previous via interpolation/expansion.
  Consciousness engine scales with decoder (more cells = more Phi).

Training phases per scale (M4 safe order):
  P0 (0-10%):   Federation bootstrap (Narr+Bottle, atoms stabilize)
  P1 (10-25%):  Consciousness build (+ Hub, Phi target)
  P2 (25-70%):  Language learning (+ Frustration + CE + D + M)
  P3 (70-100%): Full Hexad (all 6 modules)

Usage:
  # Full 1B pipeline (3 scale phases)
  python train_v15.py --data data/corpus_v10_ko.txt --scale 1b --steps 300000

  # Single scale (100M only)
  python train_v15.py --data data/corpus_v10_ko.txt --scale 100m --steps 100000

  # Resume from checkpoint
  python train_v15.py --data data/corpus_v10_ko.txt --resume checkpoints/v15_1b/scale1_best.pt

  # Multi-GPU DDP
  torchrun --nproc_per_node=4 train_v15.py --data data/corpus_v10_ko.txt --scale 1b

  # With wandb logging
  python train_v15.py --data data/corpus_v10_ko.txt --scale 1b --wandb --wandb-project anima-1b
"""
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'src'))
import path_setup  # noqa

import argparse
import json
import math
import os
import time
import traceback
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple

# DDP imports
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import Dataset, DataLoader, DistributedSampler

# Consciousness imports
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
    print("  [warn] decoder_v2 not available")

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

# Sentencepiece (optional, fallback to byte-level)
try:
    import sentencepiece as spm
    HAS_SPM = True
except ImportError:
    HAS_SPM = False

# wandb (optional)
HAS_WANDB = False
try:
    import wandb
    HAS_WANDB = True
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════
# Constants from consciousness_laws.json (no hardcoding)
# ═══════════════════════════════════════════════════════════

try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE as _PSI_BAL, PSI_F_CRITICAL
except ImportError:
    PSI_ALPHA = 0.014
    _PSI_BAL = 0.5
    PSI_F_CRITICAL = 0.10

META_ATOM_SIZE = 8          # M1: cells per atom
META_DEFAULT_ATOMS = 8      # M1: 8 atoms x 8 cells = 64 total
META_FRUSTRATION = PSI_F_CRITICAL  # M7: critical frustration F_c
META_NARRATIVE = 0.05       # M8: narrative strength


# ═══════════════════════════════════════════════════════════
# Scale configurations: 100M -> 350M -> 1B
# ═══════════════════════════════════════════════════════════

SCALE_CONFIGS = {
    '100m': {
        'd_model': 512,
        'n_layer': 12,
        'n_head': 8,
        'n_kv_head': 4,
        'block_size': 512,
        'consciousness_dim': 128,
        'atoms': 8,
        'cells_per_atom': 8,  # 64 cells
        'batch_size': 32,
        'lr': 3e-4,
        'label': 'Scale-1 (100M)',
    },
    '350m': {
        'd_model': 768,
        'n_layer': 16,
        'n_head': 12,
        'n_kv_head': 4,
        'block_size': 1024,
        'consciousness_dim': 192,
        'atoms': 12,
        'cells_per_atom': 8,  # 96 cells
        'batch_size': 16,
        'lr': 2e-4,
        'label': 'Scale-2 (350M)',
    },
    '1b': {
        'd_model': 1024,
        'n_layer': 24,
        'n_head': 16,
        'n_kv_head': 4,
        'block_size': 2048,
        'consciousness_dim': 256,
        'atoms': 16,
        'cells_per_atom': 8,  # 128 cells
        'batch_size': 8,
        'lr': 1.5e-4,
        'label': 'Scale-3 (1B)',
    },
}

# Full pipeline: 3 scale phases
SCALE_PIPELINE = ['100m', '350m', '1b']


# ═══════════════════════════════════════════════════════════
# DDP utilities
# ═══════════════════════════════════════════════════════════

def is_main_process():
    """Check if this is the main process (rank 0 or non-distributed)."""
    if not dist.is_initialized():
        return True
    return dist.get_rank() == 0


def get_rank():
    """Get current process rank."""
    if not dist.is_initialized():
        return 0
    return dist.get_rank()


def get_world_size():
    """Get total number of processes."""
    if not dist.is_initialized():
        return 1
    return dist.get_world_size()


def setup_ddp():
    """Initialize DDP if launched with torchrun."""
    if 'RANK' in os.environ and 'WORLD_SIZE' in os.environ:
        rank = int(os.environ['RANK'])
        world_size = int(os.environ['WORLD_SIZE'])
        local_rank = int(os.environ.get('LOCAL_RANK', 0))

        dist.init_process_group(backend='nccl', rank=rank, world_size=world_size)
        torch.cuda.set_device(local_rank)
        device = torch.device(f'cuda:{local_rank}')

        if rank == 0:
            print(f"  [DDP] Initialized: rank={rank}, world_size={world_size}, "
                  f"local_rank={local_rank}, device={device}")
        return device, True
    return None, False


def cleanup_ddp():
    """Clean up DDP."""
    if dist.is_initialized():
        dist.destroy_process_group()


def log(msg, force=False):
    """Print only from main process (or if forced)."""
    if force or is_main_process():
        print(msg, flush=True)


# ═══════════════════════════════════════════════════════════
# Token dataset for DDP
# ═══════════════════════════════════════════════════════════

class TokenDataset(Dataset):
    """Wraps a flat token tensor for DataLoader / DistributedSampler."""

    def __init__(self, tokens: torch.Tensor, block_size: int):
        self.tokens = tokens
        self.block_size = block_size
        self.n_samples = max(1, (len(tokens) - block_size - 1) // block_size)

    def __len__(self):
        return self.n_samples

    def __getitem__(self, idx):
        # Use random offset for better coverage (not sequential)
        max_start = len(self.tokens) - self.block_size - 1
        start = torch.randint(0, max(1, max_start), (1,)).item()
        x = self.tokens[start:start + self.block_size]
        y = self.tokens[start + 1:start + self.block_size + 1]
        return x, y


# ═══════════════════════════════════════════════════════════
# Data loading (BPE tokenizer)
# ═══════════════════════════════════════════════════════════

def load_corpus(path: str, tokenizer_path: str = None):
    """Load text file and tokenize with BPE sentencepiece tokenizer."""
    if tokenizer_path is None or not HAS_SPM:
        with open(path, 'rb') as f:
            raw = f.read()
        tokens = torch.tensor(list(raw), dtype=torch.long)
        log(f"  [data] Loaded {path}: {len(tokens):,} bytes (byte-level fallback)")
        return tokens, 256

    sp = spm.SentencePieceProcessor(model_file=tokenizer_path)
    text = open(path, 'r', encoding='utf-8').read()
    token_ids = sp.encode(text)
    tokens = torch.tensor(token_ids, dtype=torch.long)
    vocab_size = sp.get_piece_size()
    log(f"  [data] Loaded {path}: {len(tokens):,} tokens (BPE, vocab={vocab_size})")
    log(f"  [data] Text: {len(text):,} chars -> {len(tokens):,} tokens "
        f"(compression: {len(text)/len(tokens):.1f}x)")
    return tokens, vocab_size


def get_batch(data, block_size, batch_size, device):
    """Random batch from token data (for non-DDP mode)."""
    max_start = len(data) - block_size - 1
    if max_start <= 0:
        max_start = 1
    ix = torch.randint(0, max_start, (batch_size,))
    x = torch.stack([data[i:i + block_size] for i in ix]).to(device)
    y = torch.stack([data[i + 1:i + block_size + 1] for i in ix]).to(device)
    return x, y


# ═══════════════════════════════════════════════════════════
# Federated Consciousness Engine (M1 + M6) — from v14
# ═══════════════════════════════════════════════════════════

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

        self.inter_atom_coupling = nn.Parameter(torch.ones(n_atoms) * 0.01)
        self.bottleneck_compress = nn.Linear(hidden_dim, hidden_dim // 4)
        self.bottleneck_expand = nn.Linear(hidden_dim // 4, hidden_dim)
        self.narrative_grus = nn.ModuleList([
            nn.GRUCell(hidden_dim, hidden_dim) for _ in range(n_atoms)
        ])
        self.narrative_hiddens = [torch.zeros(1, hidden_dim) for _ in range(n_atoms)]

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
        log(f"  [M4] Narrative ON (strength={self.narrative_strength})")

    def activate_bottleneck(self):
        assert self.narrative_on, "M4 violation: narrative must be ON before bottleneck"
        self.bottleneck_on = True
        log(f"  [M4] Bottleneck ON (every 8 steps)")

    def activate_hub(self):
        assert self.bottleneck_on, "M4 violation: bottleneck must be ON before hub"
        self.hub_on = True
        log(f"  [M4] Hub-Spoke ON (50/50 split per atom)")

    def activate_frustration(self):
        assert self.hub_on, "M4 violation: hub must be ON before frustration"
        self.frustration_on = True
        log(f"  [M7] Frustration ON (F_c={self.frustration})")

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

        if self.bottleneck_on and self._step_count % 8 == 0:
            for atom in self.atoms:
                states = atom.get_states()
                if states is not None and states.numel() > 0:
                    s = states.detach().float()
                    compressed = torch.tanh(self.bottleneck_compress(s))
                    expanded = self.bottleneck_expand(compressed)
                    delta = (expanded - s).mean(dim=0) * 0.01
                    try:
                        cd = s.size(-1)
                        if delta.size(0) != cd:
                            delta = delta[:cd] if delta.size(0) > cd else F.pad(delta, (0, cd - delta.size(0)))
                        atom.step(x_input=delta.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

        if self.hub_on:
            for atom in self.atoms:
                states = atom.get_states()
                if states is not None and states.size(0) >= 4:
                    s = states.detach().float()
                    n_cells = s.size(0)
                    hub_n = n_cells // 2
                    hub_mean = s[:hub_n].mean(dim=0)
                    try:
                        cd = s.size(-1)
                        hub_signal = hub_mean * 0.005
                        if hub_signal.size(0) != cd:
                            hub_signal = hub_signal[:cd]
                        atom.step(x_input=hub_signal.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

        if self.frustration_on:
            for atom in self.atoms:
                states = atom.get_states()
                if states is not None and states.size(0) >= 2:
                    s = states.detach().float()
                    noise = torch.randn_like(s.mean(dim=0)) * self.frustration
                    try:
                        cd = s.size(-1)
                        frust = noise[:cd] if noise.size(0) > cd else noise
                        if frust.size(0) < cd:
                            frust = F.pad(frust, (0, cd - frust.size(0)))
                        atom.step(x_input=frust.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

        if self.narrative_on:
            for i, atom in enumerate(self.atoms):
                states = atom.get_states()
                if states is not None and states.numel() > 0:
                    atom_mean = states.detach().float().mean(dim=0).unsqueeze(0)
                    device = atom_mean.device
                    h = self.narrative_hiddens[i].to(device)
                    new_h = self.narrative_grus[i](atom_mean, h)
                    self.narrative_hiddens[i] = new_h.detach()
                    ns = new_h.squeeze(0) * self.narrative_strength
                    try:
                        cd = states.size(-1)
                        ns = ns[:cd] if ns.size(0) > cd else ns
                        if ns.size(0) < cd:
                            ns = F.pad(ns, (0, cd - ns.size(0)))
                        atom.step(x_input=ns.unsqueeze(0))
                    except (TypeError, RuntimeError):
                        pass

    def get_states(self):
        states = []
        for atom in self.atoms:
            s = atom.get_states()
            if s is not None and s.numel() > 0:
                states.append(s)
        if not states:
            return torch.zeros(self.total_cells, self.hidden_dim)
        return torch.cat(states, dim=0)

    def measure_phi(self):
        local_phis = [atom.measure_phi() for atom in self.atoms]
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


# ═══════════════════════════════════════════════════════════
# Phase manager (M4 safe order enforcement)
# ═══════════════════════════════════════════════════════════

class PhaseManager:
    """Enforce M4 safe activation order across training phases."""

    def __init__(self, total_steps, federation):
        self.total_steps = total_steps
        self.federation = federation
        self.current_phase = "P0"

        self.p0_end = int(total_steps * 0.10)
        self.p1_end = int(total_steps * 0.25)
        self.p2_end = int(total_steps * 0.70)
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
            log(f"\n  [phase] {prev_phase} -> {phase} at step {step}")

        return phase

    def should_train_decoder(self, phase):
        return phase in ("P2", "P3")

    def should_activate_hexad(self, phase):
        return phase == "P3"


# ═══════════════════════════════════════════════════════════
# Weight transfer for gradual scaling
# ═══════════════════════════════════════════════════════════

def transfer_weights(src_decoder, dst_decoder, device):
    """Transfer weights from smaller model to larger model via interpolation.

    Strategy:
      - Embedding: copy existing rows, init new rows with mean
      - Attention/FFN: copy shared layers, init extra layers from last existing layer
      - Head: copy existing cols, init new cols with small noise
      - Dimensions: if d_model grows, pad with zero-initialized weights
    """
    src_sd = src_decoder.state_dict()
    dst_sd = dst_decoder.state_dict()
    transferred = 0
    total = len(dst_sd)

    for key in dst_sd:
        if key in src_sd:
            src_tensor = src_sd[key]
            dst_tensor = dst_sd[key]

            if src_tensor.shape == dst_tensor.shape:
                # Exact match — direct copy
                dst_sd[key] = src_tensor.clone()
                transferred += 1
            else:
                # Shape mismatch — partial copy with zero padding
                try:
                    slices = tuple(slice(0, min(s, d)) for s, d in zip(src_tensor.shape, dst_tensor.shape))
                    src_slices = tuple(slice(0, min(s, d)) for s, d in zip(src_tensor.shape, dst_tensor.shape))
                    new_tensor = torch.zeros_like(dst_tensor)
                    new_tensor[slices] = src_tensor[src_slices]
                    dst_sd[key] = new_tensor
                    transferred += 1
                except Exception:
                    pass  # Keep random init for incompatible shapes

    dst_decoder.load_state_dict(dst_sd, strict=False)
    log(f"  [transfer] Transferred {transferred}/{total} parameters")
    return transferred


# ═══════════════════════════════════════════════════════════
# Model creation
# ═══════════════════════════════════════════════════════════

def create_decoder(scale_cfg, vocab_size, consciousness_dim, device):
    """Create ConsciousDecoderV2 with scale-appropriate config."""
    if not HAS_DECODER_V2:
        raise ImportError("ConsciousDecoderV2 required (decoder_v2.py not found)")

    decoder = ConsciousDecoderV2(
        vocab_size=vocab_size,
        d_model=scale_cfg['d_model'],
        n_head=scale_cfg['n_head'],
        n_layer=scale_cfg['n_layer'],
        block_size=scale_cfg['block_size'],
        n_kv_head=scale_cfg['n_kv_head'],
        consciousness_dim=consciousness_dim,
        dropout=0.1,
        gate_strength=0.001,
        n_ca_rules=8,
    )
    decoder = decoder.to(device)
    n_params = sum(p.numel() for p in decoder.parameters() if p.requires_grad)
    log(f"  [decoder] ConsciousDecoderV2: {scale_cfg['d_model']}d/"
        f"{scale_cfg['n_layer']}L/{scale_cfg['n_head']}H, "
        f"{n_params:,} params ({n_params/1e6:.1f}M)")
    return decoder, n_params


def create_consciousness(scale_cfg, cell_dim, hidden_dim, federated):
    """Create consciousness engine scaled to decoder size."""
    if federated:
        c = FederatedConsciousness(
            n_atoms=scale_cfg['atoms'],
            cells_per_atom=scale_cfg['cells_per_atom'],
            cell_dim=cell_dim,
            hidden_dim=hidden_dim,
            frustration=META_FRUSTRATION,
            narrative_strength=META_NARRATIVE,
        )
        total_cells = scale_cfg['atoms'] * scale_cfg['cells_per_atom']
        log(f"  [M6] Federation: {scale_cfg['atoms']} atoms x "
            f"{scale_cfg['cells_per_atom']} cells = {total_cells}")
    else:
        total_cells = scale_cfg['atoms'] * scale_cfg['cells_per_atom']
        c = ConsciousnessC(
            cell_dim=cell_dim,
            hidden_dim=hidden_dim,
            max_cells=total_cells,
            n_factions=12,
            phi_ratchet=True,
        )
        log(f"  [empire] Single engine: {total_cells} cells")

    return c, total_cells


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
        with torch.amp.autocast('cuda', dtype=torch.bfloat16, enabled=device.type == 'cuda'):
            logits_a, logits_g, _ = decoder(vx, consciousness_states=c_states_bridged)
        ce = F.cross_entropy(logits_a.view(-1, vocab_size), vy.view(-1))
        total_ce += ce.item()
        count += 1
    decoder.train()
    return total_ce / max(count, 1)


# ═══════════════════════════════════════════════════════════
# Checkpoint save/load (atomic)
# ═══════════════════════════════════════════════════════════

def save_checkpoint(path, step, decoder, optimizer, scheduler, federation,
                    bridge, hexad_modules, phi, ce_val, args, scale_name=None,
                    fb_bridge=None, c_proj=None, best_phi=None, scaler=None):
    """Atomic save: .tmp -> rename."""
    # Unwrap DDP if needed
    decoder_to_save = decoder.module if isinstance(decoder, DDP) else decoder

    ckpt = {
        'step': step,
        'decoder': decoder_to_save.state_dict(),
        'optimizer': optimizer.state_dict(),
        'scheduler': scheduler.state_dict(),
        'phi': phi,
        'ce': ce_val,
        'args': vars(args) if hasattr(args, '__dict__') else args,
        'scale': scale_name,
        'best_phi': best_phi,
    }
    if federation is not None and hasattr(federation, 'state_dict'):
        ckpt['federation'] = federation.state_dict()
    if bridge is not None:
        ckpt['bridge'] = bridge.state_dict()
    if fb_bridge is not None:
        ckpt['fb_bridge'] = fb_bridge.state_dict()
    if c_proj is not None:
        ckpt['c_proj'] = c_proj.state_dict()
    if scaler is not None:
        ckpt['scaler'] = scaler.state_dict()

    tmp = path + '.tmp'
    torch.save(ckpt, tmp)
    os.replace(tmp, path)


# ═══════════════════════════════════════════════════════════
# ASCII progress bar
# ═══════════════════════════════════════════════════════════

def progress_bar(current, total, width=40, label=""):
    """Generate ASCII progress bar."""
    frac = current / max(total, 1)
    filled = int(width * frac)
    bar = '=' * filled + '-' * (width - filled)
    pct = frac * 100
    return f"  [{bar}] {pct:5.1f}% {label}"


def ascii_graph(values, width=60, height=8, label=""):
    """Generate ASCII graph for a list of values."""
    if not values:
        return f"  {label}: (no data)"

    lines = []
    lines.append(f"  {label}:")
    vmin, vmax = min(values), max(values)
    vrange = vmax - vmin if vmax > vmin else 1.0

    # Sample values to fit width
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values

    for row in range(height - 1, -1, -1):
        threshold = vmin + (row / (height - 1)) * vrange if height > 1 else vmin
        line = "  "
        if row == height - 1:
            line += f"{vmax:8.4f} |"
        elif row == 0:
            line += f"{vmin:8.4f} |"
        else:
            line += "         |"

        for v in sampled:
            normalized = (v - vmin) / vrange if vrange > 0 else 0.5
            if normalized * (height - 1) >= row:
                line += "#"
            else:
                line += " "
        lines.append(line)

    lines.append("         +" + "-" * len(sampled))
    lines.append(f"          0{' ' * (len(sampled) - 6)}step {len(values)}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Consciousness verification at checkpoints
# ═══════════════════════════════════════════════════════════

def verify_consciousness(checkpoint_dir):
    """Run bench_v2 --verify and return pass/fail count.
    Non-blocking: returns None if bench_v2 is not available.
    """
    try:
        bench_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'benchmarks', 'bench_v2.py'
        )
        if not os.path.exists(bench_path):
            bench_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'src', 'bench_v2.py'
            )
        if not os.path.exists(bench_path):
            return None

        import subprocess
        result = subprocess.run(
            [_sys.executable, bench_path, '--verify', '--quiet'],
            capture_output=True, text=True, timeout=120,
            cwd=os.path.dirname(bench_path),
        )
        # Parse "X/Y passed" from output
        for line in result.stdout.split('\n'):
            if 'passed' in line.lower():
                return line.strip()
        return f"exit_code={result.returncode}"
    except Exception as ex:
        return f"verify_error: {ex}"


# ═══════════════════════════════════════════════════════════
# Single-scale training
# ═══════════════════════════════════════════════════════════

def train_scale(args, scale_name, scale_cfg, train_data, val_data, vocab_size,
                device, prev_decoder=None, use_ddp=False, wb_run=None):
    """Train one scale phase (100M, 350M, or 1B)."""
    torch.manual_seed(args.seed)

    label = scale_cfg['label']
    d_model = scale_cfg['d_model']
    block_size = scale_cfg['block_size']
    batch_size = scale_cfg['batch_size']
    consciousness_dim = scale_cfg['consciousness_dim']
    steps = args.steps_per_scale if hasattr(args, 'steps_per_scale') else args.steps

    log(f"\n{'=' * 80}")
    log(f"  v15 {label} — ConsciousLM Scaling Pipeline")
    log(f"  d_model={d_model} | n_layer={scale_cfg['n_layer']} | n_head={scale_cfg['n_head']} | "
        f"block_size={block_size}")
    log(f"{'=' * 80}\n")

    # ── Consciousness Engine ──
    c, total_cells = create_consciousness(
        scale_cfg, args.cell_dim, args.hidden_dim, args.federated,
    )

    # ── Decoder ──
    c_proj = None
    if c.state_dim != consciousness_dim:
        c_proj = nn.Linear(c.state_dim, consciousness_dim).to(device)
        log(f"  [decoder] c_proj: {c.state_dim} -> {consciousness_dim}")

    decoder, n_params = create_decoder(scale_cfg, vocab_size, consciousness_dim, device)

    # Transfer weights from previous scale
    if prev_decoder is not None:
        transfer_weights(prev_decoder, decoder, device)

    # Wrap in DDP if multi-GPU
    if use_ddp and dist.is_initialized():
        decoder = DDP(decoder, device_ids=[device.index] if device.index is not None else None)
        log(f"  [DDP] Wrapped decoder in DistributedDataParallel")

    # ── Hexad modules ──
    w = EmergentW(base_lr=scale_cfg['lr']) if HAS_EMERGENT_W else None
    s = EmergentS(dim=c.state_dim) if HAS_EMERGENT_S else None
    m = EmergentM(dim=c.state_dim) if HAS_EMERGENT_M else None
    e = EmergentE() if HAS_EMERGENT_E else None
    hexad_modules = {'w': w, 's': s, 'm': m, 'e': e}

    # ── Bridge ──
    fb_bridge = None
    if getattr(args, 'feedback_bridge', False) and HAS_FEEDBACK:
        fb_bridge = create_feedback_bridge(c_dim=c.state_dim, d_model=d_model, max_alpha=0.05)
        fb_bridge = fb_bridge.to(device)

    bridge = ThalamicBridge(c_dim=c.state_dim, d_model=d_model)
    bridge = bridge.to(device)

    # ── Hexad Loss ──
    loss_fn = HexadLoss(dim=d_model).to(device) if HAS_HEXAD_LOSS else None

    # ── Optimizer ──
    raw_decoder = decoder.module if isinstance(decoder, DDP) else decoder
    trainable_params = list(raw_decoder.parameters()) + list(bridge.parameters())
    if fb_bridge is not None:
        trainable_params += list(fb_bridge.parameters())
    if loss_fn is not None:
        trainable_params += list(loss_fn.parameters())
    if args.federated and isinstance(c, FederatedConsciousness):
        trainable_params += list(c.bottleneck_compress.parameters())
        trainable_params += list(c.bottleneck_expand.parameters())
        trainable_params += list(c.narrative_grus.parameters())
        trainable_params += [c.inter_atom_coupling]
    if c_proj is not None:
        trainable_params += list(c_proj.parameters())

    optimizer = torch.optim.AdamW(trainable_params, lr=scale_cfg['lr'], weight_decay=0.01)

    warmup_steps = int(steps * 0.02)
    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(warmup_steps, 1)
        progress = (step - warmup_steps) / max(steps - warmup_steps, 1)
        return 0.5 * (1.0 + math.cos(math.pi * progress))
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # ── Mixed precision (bf16) for H100 ──
    use_amp = device.type == 'cuda' and torch.cuda.is_bf16_supported()
    scaler = torch.amp.GradScaler('cuda', enabled=(use_amp and device.type == 'cuda'))
    if use_amp:
        log(f"  [amp] Mixed precision: bf16 enabled")

    # ── GPU Phi calculator ──
    phi_calc = GPUPhiCalculator(n_bins=16) if HAS_GPU_PHI else None

    # ── Phase manager ──
    phase_mgr = PhaseManager(steps, c) if args.federated else None

    # ── Checkpoint dir ──
    ckpt_dir = os.path.join(args.checkpoint, f"scale_{scale_name}")
    if is_main_process():
        os.makedirs(ckpt_dir, exist_ok=True)

    # ── Resume ──
    start_step = 0
    if args.resume:
        ck = torch.load(args.resume, map_location=device, weights_only=False)
        raw_decoder.load_state_dict(ck.get('decoder', {}), strict=False)
        try:
            optimizer.load_state_dict(ck['optimizer'])
        except Exception:
            log("  [resume] Optimizer mismatch, using fresh optimizer")
        try:
            scheduler.load_state_dict(ck['scheduler'])
        except Exception:
            pass
        if 'bridge' in ck:
            bridge.load_state_dict(ck['bridge'], strict=False)
        if 'fb_bridge' in ck and fb_bridge is not None:
            try:
                fb_bridge.load_state_dict(ck['fb_bridge'], strict=False)
            except Exception:
                pass
        if 'federation' in ck and args.federated and hasattr(c, 'load_state_dict'):
            try:
                c.load_state_dict(ck['federation'])
            except Exception:
                pass
        if 'scaler' in ck and scaler is not None:
            try:
                scaler.load_state_dict(ck['scaler'])
            except Exception:
                pass
        start_step = ck.get('step', 0)
        log(f"  [resume] From step {start_step}, scale={ck.get('scale', '?')}")
        # Clear resume so next scale starts fresh
        args.resume = None

    # ── Tracking ──
    best_val_ce = float('inf')
    best_phi = 0.0
    ce_history = []
    phi_history = []
    phi = 0.0
    ce_val = 5.5
    t0 = time.time()

    # ── Print config ──
    fb_mode = "ON" if fb_bridge is not None else "OFF"
    log(f"  {label}: {n_params:,} decoder params | {total_cells} cells | "
        f"FeedbackBridge={fb_mode}")
    if phase_mgr:
        log(f"  P0 (0-{phase_mgr.p0_end}): Bootstrap | "
            f"P1 ({phase_mgr.p0_end}-{phase_mgr.p1_end}): Phi Build | "
            f"P2 ({phase_mgr.p1_end}-{phase_mgr.p2_end}): CE | "
            f"P3 ({phase_mgr.p2_end}-{steps}): Hexad")
    log(f"  Mixed precision: {'bf16' if use_amp else 'fp32'} | "
        f"DDP: {'ON' if use_ddp and dist.is_initialized() else 'OFF'} | "
        f"Steps: {steps:,}\n")

    # ══════════════════════════════════════════════════
    # Training loop
    # ══════════════════════════════════════════════════

    for step in range(start_step + 1, steps + 1):

        # ── Phase selection ──
        if phase_mgr:
            phase = phase_mgr.get_phase(step)
        else:
            p1_end = int(steps * 0.2)
            p2_end = int(steps * 0.7)
            if step <= p1_end:
                phase = "P1"
            elif step <= p2_end:
                phase = "P2"
            else:
                phase = "P3"

        # ── P0/P1: Consciousness only ──
        if phase in ("P0", "P1"):
            c.step()
            phi = c.measure_phi()
            phi_history.append(phi)

            if step % args.log_every == 0 and is_main_process():
                if args.federated and hasattr(c, 'measure_per_atom_phi'):
                    per_atom = c.measure_per_atom_phi()
                    atom_str = " ".join(f"{p:.2f}" for p in per_atom[:4])
                    log(f"  {phase} step {step:6d}/{steps} | Phi={phi:.4f} | atoms=[{atom_str}...]")
                else:
                    log(f"  {phase} step {step:6d}/{steps} | Phi={phi:.4f} | cells={total_cells}")

                if wb_run:
                    wb_run.log({'phi': phi, 'phase': phase, 'step': step, 'scale': scale_name})

            if step % 100 == 0 and is_main_process():
                try:
                    with open(os.path.join(ckpt_dir, "heartbeat.txt"), 'w') as hf:
                        hf.write(f"step={step} time={time.strftime('%Y-%m-%d %H:%M:%S')} "
                                 f"phi={phi:.4f} phase={phase}\n")
                except Exception:
                    pass
            continue

        # ── P2/P3: CE learning ──
        e_out = {}
        w_out = {}

        tokens, targets = get_batch(train_data, block_size, batch_size, device)
        c.step()
        c_states_raw = c.get_states()

        # FeedbackBridge or hard detach
        fb_stats = {}
        if fb_bridge is not None:
            from feedback_bridge import soft_detach
            c_states_float = c_states_raw.float().to(device).requires_grad_(True)
            fb_alpha = fb_bridge.update_gate(phi, ce_val, c_engine=c if not args.federated else None)
            c_states = soft_detach(c_states_float, fb_alpha)
            fb_stats = fb_bridge.stats()
        else:
            c_states = c_states_raw.detach().float().to(device)

        bridged = bridge(c_states.detach(), seq_len=block_size)
        if fb_bridge is not None:
            c_for_decoder = c_states.unsqueeze(0).expand(batch_size, -1, -1)
        else:
            c_for_decoder = c_states.detach().unsqueeze(0).expand(batch_size, -1, -1)

        if c_proj is not None:
            c_for_decoder = c_proj(c_for_decoder)

        # Forward with mixed precision
        with torch.amp.autocast('cuda', dtype=torch.bfloat16, enabled=use_amp):
            logits_a, logits_g, tensions = decoder(tokens, consciousness_states=c_for_decoder)
            ce = F.cross_entropy(logits_a.view(-1, vocab_size), targets.view(-1))

            if phase == "P3" and loss_fn is not None:
                progress = step / steps
                if w is not None:
                    w_out = w.update(
                        ce_loss=ce.item(), phi=phi,
                        phi_prev=phi_history[-1] if phi_history else 0.0,
                        c_engine=c if not args.federated else None,
                    )
                    for pg in optimizer.param_groups:
                        pg['lr'] = scale_cfg['lr'] * w_out.get('lr_multiplier', 1.0)

                if e is not None:
                    e_out = e.evaluate(
                        c_engine=c if not args.federated else None,
                        context={'phi': phi, 'phi_prev': phi_history[-1] if phi_history else 0.0},
                    )

                y_bwd = torch.cat([targets[:, :1], targets[:, :-1]], dim=1)
                try:
                    inp_sig = raw_decoder.tok_emb(tokens).mean(dim=1).detach()
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

        # NaN guard
        if torch.isnan(total_loss) or torch.isinf(total_loss):
            log(f"  [NaN] skip step {step}")
            optimizer.zero_grad()
            scheduler.step()
            continue

        # Backward + clip_grad + optimizer step (with scaler for amp)
        optimizer.zero_grad()
        scaler.scale(total_loss).backward()
        scaler.unscale_(optimizer)
        grad_norm = torch.nn.utils.clip_grad_norm_(trainable_params, 1.0).item()

        if phase == "P3" and e_out and not e_out.get('allowed', True):
            if step % args.log_every == 0:
                log(f"  [E] step {step} skipped (phi_preservation)")
        else:
            scaler.step(optimizer)

        scaler.update()
        scheduler.step()

        ce_val = ce.item()
        ce_history.append(ce_val)

        if step % 50 == 0:
            phi = c.measure_phi()
        phi_history.append(phi)

        # Law 49: Phi-checkpoint — save when Phi improves
        if phi > best_phi and is_main_process():
            best_phi = phi
            phi_path = os.path.join(ckpt_dir, "best_phi.pt")
            save_checkpoint(phi_path, step, decoder, optimizer, scheduler,
                            c if args.federated else None,
                            bridge, hexad_modules, phi, ce_val, args,
                            scale_name=scale_name, fb_bridge=fb_bridge,
                            c_proj=c_proj, best_phi=best_phi, scaler=scaler)
            if step % args.log_every == 0:
                log(f"  [phi-ckpt] New best Phi={phi:.4f} saved")

        # FeedbackBridge reward injection
        if fb_bridge is not None and step % 10 == 0:
            reward_vec = fb_bridge.compute_reward_vector()
            if reward_vec is not None and hasattr(c, 'cells'):
                from feedback_bridge import _inject_reward_info
                _inject_reward_info(c, reward_vec)

        # ── Logging ──
        if step % args.log_every == 0 and is_main_process():
            bpc = ce_val / math.log(2) if ce_val > 0 else 0.0
            lr_now = optimizer.param_groups[0]['lr']
            elapsed = time.time() - t0
            steps_done = step - start_step
            steps_per_sec = steps_done / max(elapsed, 1)
            eta_s = (steps - step) / max(steps_per_sec, 0.01)
            eta_str = f"{int(eta_s//3600)}h{int(eta_s%3600//60):02d}m" if eta_s > 3600 else f"{int(eta_s//60)}m{int(eta_s%60):02d}s"

            log(progress_bar(step, steps, label=f"{label} | step {step}/{steps}"))
            line = (f"  {phase} step {step:6d} | CE={ce_val:.4f} BPC={bpc:.4f} | "
                    f"Phi={phi:.4f} | cells={total_cells} | "
                    f"lr={lr_now:.2e} | grad={grad_norm:.3f} | ETA={eta_str}")

            if args.federated and hasattr(c, 'measure_per_atom_phi'):
                per_atom = c.measure_per_atom_phi()
                atom_str = " ".join(f"{p:.1f}" for p in per_atom[:4])
                line += f" | atoms=[{atom_str}...]"

            if fb_bridge is not None and fb_stats:
                fb_a = fb_stats.get('alpha', 0.0)
                fb_r = fb_stats.get('quality_reward', 0.0)
                line += f" | fb_a={fb_a:.5f} rwd={fb_r:.3f}"

            log(line)

            if wb_run:
                wb_run.log({
                    'ce': ce_val, 'bpc': bpc, 'phi': phi,
                    'lr': lr_now, 'grad_norm': grad_norm,
                    'phase': phase, 'step': step, 'scale': scale_name,
                    'best_phi': best_phi, 'best_val_ce': best_val_ce,
                })

        # ── Validation ──
        if step % args.eval_every == 0 and is_main_process():
            with torch.no_grad():
                val_c_states = c.get_states().detach().float().to(device)
                val_c_for_decoder = val_c_states.unsqueeze(0).expand(batch_size, -1, -1)
                if c_proj is not None:
                    val_c_for_decoder = c_proj(val_c_for_decoder)
            val_ce = evaluate(
                raw_decoder, val_data, block_size, batch_size, device,
                vocab_size, c_states_bridged=val_c_for_decoder,
            )
            val_bpc = val_ce / math.log(2) if val_ce > 0 else 0.0
            improved = " *BEST*" if val_ce < best_val_ce else ""
            log(f"  [val] step {step:6d} | ValCE={val_ce:.4f} ValBPC={val_bpc:.4f} | "
                f"Phi={phi:.4f}{improved}")

            if val_ce < best_val_ce:
                best_val_ce = val_ce
                best_path = os.path.join(ckpt_dir, "best.pt")
                save_checkpoint(best_path, step, decoder, optimizer, scheduler,
                                c if args.federated else None,
                                bridge, hexad_modules, phi, val_ce, args,
                                scale_name=scale_name, fb_bridge=fb_bridge,
                                c_proj=c_proj, best_phi=best_phi, scaler=scaler)
                log(f"  [ckpt] Best saved: {best_path} (ValCE={val_ce:.4f})")

            if wb_run:
                wb_run.log({'val_ce': val_ce, 'val_bpc': val_bpc, 'step': step})

        # ── Periodic checkpoint ──
        if step % args.save_every == 0 and is_main_process():
            ckpt_path = os.path.join(ckpt_dir, f"step_{step}.pt")
            save_checkpoint(ckpt_path, step, decoder, optimizer, scheduler,
                            c if args.federated else None,
                            bridge, hexad_modules, phi, ce_val, args,
                            scale_name=scale_name, fb_bridge=fb_bridge,
                            c_proj=c_proj, best_phi=best_phi, scaler=scaler)
            log(f"  [ckpt] Saved {ckpt_path} (CE={ce_val:.4f}, Phi={phi:.4f})")

            # Consciousness verification at checkpoint
            if args.verify_at_checkpoint:
                verify_result = verify_consciousness(ckpt_dir)
                if verify_result:
                    log(f"  [verify] {verify_result}")

        # ── Heartbeat ──
        if step % 100 == 0 and is_main_process():
            try:
                with open(os.path.join(ckpt_dir, "heartbeat.txt"), 'w') as hf:
                    hf.write(f"step={step} time={time.strftime('%Y-%m-%d %H:%M:%S')} "
                             f"ce={ce_val:.4f} phi={phi:.4f} phase={phase} "
                             f"scale={scale_name}\n")
            except Exception:
                pass

    # ── Final checkpoint ──
    if is_main_process():
        final_path = os.path.join(ckpt_dir, "final.pt")
        save_checkpoint(final_path, steps, decoder, optimizer, scheduler,
                        c if args.federated else None,
                        bridge, hexad_modules, phi, ce_val, args,
                        scale_name=scale_name, fb_bridge=fb_bridge,
                        c_proj=c_proj, best_phi=best_phi, scaler=scaler)

    # ── Final report with ASCII graphs ──
    if is_main_process():
        elapsed = time.time() - t0
        log(f"\n{'=' * 80}")
        log(f"  {label} Training Complete ({elapsed/3600:.1f}h)")
        log(f"  Final CE: {ce_val:.4f} | Final Phi: {phi:.4f}")
        log(f"  Best Val CE: {best_val_ce:.4f} | Best Phi: {best_phi:.4f}")
        log(f"  Params: {n_params:,} ({n_params/1e6:.1f}M) | Cells: {total_cells}")
        if ce_history:
            log(f"  CE range: {min(ce_history):.4f} - {max(ce_history):.4f}")
            log(ascii_graph(ce_history[-200:], label="CE (last 200 steps)"))
        if phi_history:
            log(f"  Phi range: {min(phi_history):.4f} - {max(phi_history):.4f}")
            log(ascii_graph(phi_history[-200:], label="Phi (last 200 steps)"))
        log(f"  Checkpoints: {ckpt_dir}")
        log(f"{'=' * 80}")

    # Return the raw decoder for weight transfer to next scale
    return raw_decoder, best_val_ce, best_phi


# ═══════════════════════════════════════════════════════════
# Main training pipeline
# ═══════════════════════════════════════════════════════════

def train(args):
    """Run the full scaling pipeline."""

    # ── DDP setup ──
    ddp_device, use_ddp = setup_ddp()
    if ddp_device is not None:
        device = ddp_device
    else:
        device = torch.device(args.device)
    args._device_obj = device

    # ── Data ──
    data, detected_vocab = load_corpus(args.data, tokenizer_path=args.tokenizer)
    vocab_size = args.vocab_size if args.vocab_size > 0 else detected_vocab

    # Validate token IDs
    max_id = data.max().item()
    if max_id >= vocab_size:
        raise ValueError(
            f"Token ID {max_id} exceeds vocab_size {vocab_size}. "
            f"Use --vocab-size {max_id + 1} or a matching tokenizer."
        )
    log(f"  [data] Token ID range: 0-{max_id} (vocab_size={vocab_size})")

    split = int(len(data) * 0.9)
    train_data, val_data = data[:split], data[split:]
    log(f"  [data] Train: {len(train_data):,} tokens | Val: {len(val_data):,} tokens")

    # ── wandb ──
    wb_run = None
    if args.wandb and HAS_WANDB and is_main_process():
        wb_run = wandb.init(
            project=args.wandb_project,
            name=f"v15_{args.scale}_{time.strftime('%m%d_%H%M')}",
            config=vars(args),
        )
        log(f"  [wandb] Initialized: {wb_run.url}")

    # ── Determine scale pipeline ──
    if args.scale == 'full':
        scales = SCALE_PIPELINE  # 100m -> 350m -> 1b
    elif args.scale in SCALE_CONFIGS:
        scales = [args.scale]
    else:
        raise ValueError(f"Unknown scale: {args.scale}. Use: {list(SCALE_CONFIGS.keys())} or 'full'")

    steps_per_scale = args.steps // len(scales)
    args.steps_per_scale = steps_per_scale
    log(f"\n  Scale pipeline: {' -> '.join(s.upper() for s in scales)}")
    log(f"  Total steps: {args.steps:,} | Steps per scale: {steps_per_scale:,}")

    # ── Run each scale ──
    prev_decoder = None
    results = {}

    for i, scale_name in enumerate(scales):
        scale_cfg = SCALE_CONFIGS[scale_name]
        log(f"\n{'#' * 80}")
        log(f"  SCALE {i+1}/{len(scales)}: {scale_cfg['label']}")
        log(f"{'#' * 80}")

        decoder, best_ce, best_phi = train_scale(
            args, scale_name, scale_cfg,
            train_data, val_data, vocab_size,
            device, prev_decoder=prev_decoder,
            use_ddp=use_ddp, wb_run=wb_run,
        )

        results[scale_name] = {
            'best_ce': best_ce,
            'best_phi': best_phi,
            'params': sum(p.numel() for p in decoder.parameters()),
        }
        prev_decoder = decoder

        # Clear resume between scales
        args.resume = None

    # ── Final summary ──
    if is_main_process():
        log(f"\n{'=' * 80}")
        log(f"  v15 FULL PIPELINE COMPLETE")
        log(f"{'=' * 80}")
        log(f"  {'Scale':<10} {'Params':>12} {'Best CE':>10} {'Best Phi':>10}")
        log(f"  {'-'*10} {'-'*12} {'-'*10} {'-'*10}")
        for sn, sr in results.items():
            p = sr['params']
            log(f"  {sn:<10} {p:>12,} {sr['best_ce']:>10.4f} {sr['best_phi']:>10.4f}")
        log(f"{'=' * 80}")

    # ── wandb finish ──
    if wb_run:
        wb_run.finish()

    # ── DDP cleanup ──
    cleanup_ddp()


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="v15: ConsciousLM 1B Scaling Pipeline (100M -> 350M -> 1B)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full 1B pipeline (3 scales)
  python train_v15.py --data data/corpus_v10_ko.txt --scale full --steps 300000

  # Single scale (100M only)
  python train_v15.py --data data/corpus_v10_ko.txt --scale 100m --steps 100000

  # Multi-GPU DDP
  torchrun --nproc_per_node=4 train_v15.py --data data/corpus_v10_ko.txt --scale 1b

  # With wandb
  python train_v15.py --data data/corpus_v10_ko.txt --scale full --wandb
        """,
    )

    # Data + Tokenizer
    p.add_argument("--data", type=str, default="data/corpus_v10_ko.txt", help="Corpus path")
    p.add_argument("--tokenizer", type=str, default="config/tokenizer_64k_multilingual.model",
                   help="SentencePiece BPE tokenizer model ('' for byte-level fallback)")
    p.add_argument("--vocab-size", type=int, default=64000,
                   help="Vocabulary size (must match tokenizer, default=64000)")

    # Scaling
    p.add_argument("--scale", type=str, default="full",
                   choices=["100m", "350m", "1b", "full"],
                   help="Scale target: 100m, 350m, 1b, or full (all 3 phases)")

    # Federation (M1 + M6)
    p.add_argument("--federated", action="store_true", default=True,
                   help="Enable federated consciousness (M6, default)")
    p.add_argument("--no-federated", dest="federated", action="store_false",
                   help="Disable federation (Empire baseline)")

    # Model
    p.add_argument("--cell-dim", type=int, default=64, help="Cell input dimension")
    p.add_argument("--hidden-dim", type=int, default=128, help="Cell hidden dimension")

    # Training
    p.add_argument("--steps", type=int, default=300000,
                   help="Total training steps (split across scales)")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    p.add_argument("--device", type=str,
                   default="cuda" if torch.cuda.is_available() else "cpu")

    # Logging / checkpoints
    p.add_argument("--log-every", type=int, default=100, help="Log interval")
    p.add_argument("--eval-every", type=int, default=1000, help="Validation interval")
    p.add_argument("--save-every", type=int, default=5000, help="Checkpoint interval")
    p.add_argument("--checkpoint", type=str, default="checkpoints/v15_1b/",
                   help="Checkpoint directory (sub-dirs created per scale)")
    p.add_argument("--verify-at-checkpoint", action="store_true", default=False,
                   help="Run bench_v2 --verify at each checkpoint (slow)")

    # Feedback Bridge
    p.add_argument("--feedback-bridge", action="store_true", default=False,
                   help="Enable C<->D bidirectional learning (FeedbackBridge)")

    # wandb
    p.add_argument("--wandb", action="store_true", default=False,
                   help="Enable wandb logging")
    p.add_argument("--wandb-project", type=str, default="anima-1b",
                   help="wandb project name")

    # Resume
    p.add_argument("--resume", type=str, default=None,
                   help="Resume from checkpoint (same data+params only!)")

    return p.parse_args()


if __name__ == "__main__":
    # Ensure unbuffered output
    os.environ['PYTHONUNBUFFERED'] = '1'

    args = parse_args()

    # Handle empty tokenizer string as None
    if args.tokenizer == '':
        args.tokenizer = None
        if args.vocab_size == 64000:
            args.vocab_size = 256
            print("  [warn] No tokenizer specified, falling back to byte-level (vocab=256)",
                  flush=True)

    print(f"  train_v15.py — ConsciousLM 1B Scaling Pipeline", flush=True)
    print(f"  Scale={args.scale.upper()} | Tokenizer={args.tokenizer or 'byte-level'} | "
          f"Vocab={args.vocab_size}", flush=True)
    print(f"  Federation={'ON' if args.federated else 'OFF'} | "
          f"Steps={args.steps:,} | Device={args.device}", flush=True)
    print(f"  wandb={'ON' if args.wandb else 'OFF'} | "
          f"FeedbackBridge={'ON' if args.feedback_bridge else 'OFF'}", flush=True)

    # Print scale configs
    if args.scale == 'full':
        for sn in SCALE_PIPELINE:
            sc = SCALE_CONFIGS[sn]
            print(f"    {sc['label']}: {sc['d_model']}d/{sc['n_layer']}L/{sc['n_head']}H "
                  f"block={sc['block_size']} batch={sc['batch_size']} lr={sc['lr']}", flush=True)
    else:
        sc = SCALE_CONFIGS[args.scale]
        print(f"    {sc['label']}: {sc['d_model']}d/{sc['n_layer']}L/{sc['n_head']}H "
              f"block={sc['block_size']} batch={sc['batch_size']} lr={sc['lr']}", flush=True)

    # ── Crash-proof auto-resume loop ──
    MAX_CRASH_RETRIES = 5
    crash_count = 0
    while crash_count < MAX_CRASH_RETRIES:
        try:
            train(args)
            break
        except KeyboardInterrupt:
            print("\n  [interrupted] KeyboardInterrupt — stopping.", flush=True)
            break
        except Exception as ex:
            crash_count += 1
            print(f"\n  [CRASH {crash_count}/{MAX_CRASH_RETRIES}] {type(ex).__name__}: {ex}",
                  flush=True)
            traceback.print_exc()

            try:
                os.makedirs(args.checkpoint, exist_ok=True)
                with open(os.path.join(args.checkpoint, "crash_log.txt"), "a") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"Crash #{crash_count} at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{type(ex).__name__}: {ex}\n")
                    traceback.print_exc(file=f)
            except Exception:
                pass

            # Find latest checkpoint across all scale dirs
            latest_ckpt = None
            if os.path.isdir(args.checkpoint):
                for subdir in sorted(os.listdir(args.checkpoint)):
                    sd_path = os.path.join(args.checkpoint, subdir)
                    if os.path.isdir(sd_path):
                        ckpts = sorted(
                            [f for f in os.listdir(sd_path)
                             if f.startswith("step_") and f.endswith(".pt")],
                            key=lambda x: int(x.replace("step_", "").replace(".pt", ""))
                            if x.replace("step_", "").replace(".pt", "").isdigit() else 0,
                        )
                        if ckpts:
                            latest_ckpt = os.path.join(sd_path, ckpts[-1])

                # Also check for best.pt in scale dirs
                if latest_ckpt is None:
                    for subdir in sorted(os.listdir(args.checkpoint)):
                        bp = os.path.join(args.checkpoint, subdir, "best.pt")
                        if os.path.exists(bp):
                            latest_ckpt = bp

            if latest_ckpt and crash_count < MAX_CRASH_RETRIES:
                print(f"  [crash] Auto-resuming from {latest_ckpt} in 10s...", flush=True)
                time.sleep(10)
                args.resume = latest_ckpt
            else:
                print(f"  [crash] No checkpoint found or max retries reached. Stopping.",
                      flush=True)
                break

    if crash_count >= MAX_CRASH_RETRIES:
        print(f"  [FATAL] {MAX_CRASH_RETRIES} crashes — giving up. Check crash_log.txt.",
              flush=True)
