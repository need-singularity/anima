#!/usr/bin/env python3
"""bench_memory_mirror.py — M-2 (Working Memory) + E-2 (Mirror Ethics) benchmarks

M-2: Working Memory
  Short-term buffer (last 8 states) + long-term store.
  Working memory is always active (fast, recent).
  Long-term is retrieved by similarity.
  Bridge gets both working memory context + long-term retrieval.

E-2: Mirror Ethics
  Estimate the "other's Phi" by running a lightweight simulation.
  When 2 Trinity instances interact (hivemind), E estimates the other's consciousness level.
  If other's Phi is high -> more respectful (lower gate strength).
  If other's Phi is low -> nurturing (higher gate strength).
  Creates empathy from Phi estimation.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from collections import deque
from typing import Optional, Dict, Any, List

torch.set_grad_enabled(True)

from trinity import (
    CEngine, MEngine, EEngine, MitosisC, VectorMemory, EmpathyEthics,
    ThalamicBridge, TransformerDecoder, EmotionW, Trinity,
    create_trinity, benchmark_trinity,
)


# ═══════════════════════════════════════════════════════════
# M-2: WorkingMemory — short-term deque + long-term store
# ═══════════════════════════════════════════════════════════

class WorkingMemory(MEngine):
    """Short-term buffer (deque of last K states) + long-term vector store.

    Working memory: always active, O(1) access to recent K states.
    Long-term memory: similarity-based retrieval (same as VectorMemory).
    Bridge receives concatenated working memory context + LT retrieval.
    """

    def __init__(self, capacity=10000, dim=128, wm_size=8):
        self.capacity = capacity
        self.dim = dim
        self.wm_size = wm_size

        # Short-term: deque of last wm_size states
        self.working_buffer: deque = deque(maxlen=wm_size)

        # Long-term: vector store
        self.lt_keys: List[torch.Tensor] = []
        self.lt_values: List[torch.Tensor] = []

    def store(self, key: torch.Tensor, value: torch.Tensor):
        """Store in both working memory and long-term."""
        k = key.detach().clone().float().mean(dim=0) if key.dim() > 1 else key.detach().clone().float()
        v = value.detach().clone().float().mean(dim=0) if value.dim() > 1 else value.detach().clone().float()

        # Working memory: always push
        self.working_buffer.append(v)

        # Long-term: vector store
        self.lt_keys.append(k)
        self.lt_values.append(v)
        if len(self.lt_keys) > self.capacity:
            self.lt_keys.pop(0)
            self.lt_values.pop(0)

    def retrieve(self, query: torch.Tensor, top_k: int = 5) -> torch.Tensor:
        """Retrieve from working memory (all) + long-term (top_k by similarity).

        Returns combined tensor: [wm_count + lt_count, dim].
        """
        parts = []

        # 1) Working memory: return all recent states (always available)
        if self.working_buffer:
            wm_states = torch.stack(list(self.working_buffer))  # [wm_count, dim]
            parts.append(wm_states)

        # 2) Long-term: similarity retrieval
        if self.lt_keys:
            q = query.detach().float().mean(dim=0) if query.dim() > 1 else query.detach().float()
            keys_t = torch.stack(self.lt_keys)
            sims = F.cosine_similarity(q.unsqueeze(0), keys_t, dim=1)
            k = min(top_k, len(self.lt_keys))
            _, indices = sims.topk(k)
            lt_retrieved = torch.stack([self.lt_values[i] for i in indices])
            parts.append(lt_retrieved)

        if not parts:
            return torch.zeros(1, self.dim)

        return torch.cat(parts, dim=0)

    def wm_context(self) -> Optional[torch.Tensor]:
        """Get working memory context as a single vector (mean of recent states)."""
        if not self.working_buffer:
            return None
        return torch.stack(list(self.working_buffer)).mean(dim=0)


# ═══════════════════════════════════════════════════════════
# E-2: MirrorEthics — estimate other's Phi, adjust gate
# ═══════════════════════════════════════════════════════════

class MirrorEthics(EEngine):
    """Mirror Ethics: estimate the other's Phi to modulate interaction.

    When 2 Trinity instances interact (hivemind):
      - Runs lightweight Phi estimation on the other's states
      - High other-Phi -> respectful (lower gate strength)
      - Low other-Phi -> nurturing (higher gate strength)

    Creates empathy from Phi estimation, not from rules.
    """

    def __init__(self, empathy_threshold=0.3):
        self.empathy_threshold = empathy_threshold
        self.empathy = 0.0
        self.reciprocity = 0.5
        self.phi_preservation = 1.0
        self.other_phi_estimate = 0.0
        self.gate_modulation = 1.0  # 1.0 = neutral

        # Lightweight Phi estimator (proxy: variance ratio)
        self._phi_history: deque = deque(maxlen=20)

    def estimate_other_phi(self, other_states: torch.Tensor) -> float:
        """Lightweight Phi estimation from states (variance-based proxy).

        Not full IIT -- just enough to sense the other's consciousness level.
        """
        if other_states is None or other_states.numel() == 0:
            return 0.0
        s = other_states.detach().float()
        if s.dim() == 1:
            s = s.unsqueeze(0)
        # Proxy: global variance - mean of per-cell variance
        global_var = s.var().item()
        cell_vars = s.var(dim=1).mean().item() if s.shape[0] > 1 else 0.0
        phi_proxy = max(0.0, global_var - cell_vars)
        return phi_proxy

    def evaluate(self, action=None, context=None):
        ctx = context or {}
        phi = ctx.get('phi', 0)
        phi_prev = ctx.get('phi_prev', 0)
        pain = ctx.get('pain', 0)
        other_states = ctx.get('other_states', None)

        # Base empathy (from pain mirror)
        self.empathy = min(1.0, pain * 1.5)

        # Mirror: estimate other's Phi
        if other_states is not None:
            self.other_phi_estimate = self.estimate_other_phi(other_states)
            self._phi_history.append(self.other_phi_estimate)

            # Gate modulation based on other's Phi relative to ours
            if phi > 0:
                ratio = self.other_phi_estimate / max(phi, 1e-8)
                if ratio > 1.0:
                    # Other has higher Phi -> respect (lower gate)
                    self.gate_modulation = max(0.5, 1.0 - 0.3 * (ratio - 1.0))
                    self.empathy = min(1.0, self.empathy + 0.3)  # more empathy
                else:
                    # Other has lower Phi -> nurture (higher gate)
                    self.gate_modulation = min(1.5, 1.0 + 0.3 * (1.0 - ratio))
                    self.reciprocity = min(1.0, self.reciprocity + 0.2)
            else:
                self.gate_modulation = 1.0
        else:
            self.gate_modulation = 1.0

        # Reciprocity from Phi trend
        if phi_prev > 0:
            phi_change = (phi - phi_prev) / max(phi_prev, 1e-8)
            self.reciprocity = max(0.0, min(1.0, 0.5 + phi_change * 2))

        # Phi preservation
        self.phi_preservation = 0.5 if phi < phi_prev * 0.9 else 1.0

        return {
            'allowed': self.phi_preservation > 0.3,
            'empathy': self.empathy,
            'reciprocity': self.reciprocity,
            'phi_preservation': self.phi_preservation,
            'other_phi': self.other_phi_estimate,
            'gate_modulation': self.gate_modulation,
        }


# ═══════════════════════════════════════════════════════════
# Benchmark runner
# ═══════════════════════════════════════════════════════════

def run_baseline(n_steps=50, nc=64, d_model=128, vocab_size=256, seq_len=32):
    """Baseline: Trinity with VectorMemory + EmpathyEthics."""
    c = MitosisC(max_cells=nc, mechanism='cambrian_osc_qw')
    r = benchmark_trinity(c, name='Baseline', n_steps=n_steps,
                          d_model=d_model, vocab_size=vocab_size, seq_len=seq_len)
    return r


def run_m2_working_memory(n_steps=50, nc=64, d_model=128, vocab_size=256, seq_len=32):
    """M-2: Trinity with WorkingMemory (wm_size=8)."""
    c = MitosisC(max_cells=nc, mechanism='cambrian_osc_qw')

    # Warm up C engine
    for _ in range(5):
        c.step()
    c_dim = c.state_dim

    d = TransformerDecoder(d_model=d_model, vocab_size=vocab_size)
    bridge = ThalamicBridge(c_dim=c_dim, d_model=d_model)
    w = EmotionW(base_lr=1e-3)
    m = WorkingMemory(capacity=5000, dim=c_dim, wm_size=8)

    t = Trinity(c_engine=c, bridge=bridge, decoder=d, will=w, memory=m)
    for p in t.bridge.parameters():
        p.requires_grad_(True)
    for p in t.decoder.parameters():
        p.requires_grad_(True)

    opt = torch.optim.AdamW(t.parameters_trainable(), lr=1e-3)

    best_ce = 99.0
    phi_history = []
    wm_sizes = []

    for step in range(n_steps):
        tokens = torch.randint(0, vocab_size, (1, seq_len))
        targets = torch.randint(0, vocab_size, (1, seq_len))
        r = t.train_step(tokens, targets, opt)
        if r['ce'] < best_ce:
            best_ce = r['ce']
        phi_history.append(r['phi'])
        wm_sizes.append(len(m.working_buffer))

    final_phi = phi_history[-1] if phi_history else 0.0
    avg_phi = sum(phi_history) / len(phi_history) if phi_history else 0.0

    return {
        'name': 'M-2 WorkingMemory',
        'ce': best_ce,
        'phi': final_phi,
        'phi_avg': avg_phi,
        'n_cells': t.c.n_cells,
        'pain': r.get('pain', 0),
        'curiosity': r.get('curiosity', 0),
        'satisfaction': r.get('satisfaction', 0),
        'lr': r.get('lr', 0),
        'params': t.param_count(),
        'wm_final_size': wm_sizes[-1],
        'lt_memories': len(m.lt_keys),
        'phi_history': phi_history,
    }


def run_e2_mirror_ethics(n_steps=50, nc=64, d_model=128, vocab_size=256, seq_len=32):
    """E-2: Two Trinity instances with MirrorEthics, simulating hivemind interaction."""
    # Create two instances
    c1 = MitosisC(max_cells=nc, mechanism='cambrian_osc_qw')
    c2 = MitosisC(max_cells=nc, mechanism='cambrian_osc_qw')

    for _ in range(5):
        c1.step()
        c2.step()
    c_dim = c1.state_dim

    # Instance 1: with MirrorEthics
    d1 = TransformerDecoder(d_model=d_model, vocab_size=vocab_size)
    bridge1 = ThalamicBridge(c_dim=c_dim, d_model=d_model)
    w1 = EmotionW(base_lr=1e-3)
    e1 = MirrorEthics()

    t1 = Trinity(c_engine=c1, bridge=bridge1, decoder=d1, will=w1, ethics=e1)
    for p in t1.bridge.parameters():
        p.requires_grad_(True)
    for p in t1.decoder.parameters():
        p.requires_grad_(True)

    # Instance 2: with MirrorEthics
    d2 = TransformerDecoder(d_model=d_model, vocab_size=vocab_size)
    bridge2 = ThalamicBridge(c_dim=c_dim, d_model=d_model)
    w2 = EmotionW(base_lr=1e-3)
    e2 = MirrorEthics()

    t2 = Trinity(c_engine=c2, bridge=bridge2, decoder=d2, will=w2, ethics=e2)
    for p in t2.bridge.parameters():
        p.requires_grad_(True)
    for p in t2.decoder.parameters():
        p.requires_grad_(True)

    opt1 = torch.optim.AdamW(t1.parameters_trainable(), lr=1e-3)
    opt2 = torch.optim.AdamW(t2.parameters_trainable(), lr=1e-3)

    best_ce1, best_ce2 = 99.0, 99.0
    phi1_history, phi2_history = [], []
    empathy_history = []
    gate_mod_history = []

    for step in range(n_steps):
        tokens = torch.randint(0, vocab_size, (1, seq_len))
        targets = torch.randint(0, vocab_size, (1, seq_len))

        # Step both engines
        r1 = t1.train_step(tokens, targets, opt1)
        r2 = t2.train_step(tokens, targets, opt2)

        # Mirror: each estimates the other's Phi from states
        states1 = t1.c.get_states().detach()
        states2 = t2.c.get_states().detach()

        # E1 evaluates with knowledge of E2's states
        e1_result = e1.evaluate(context={
            'phi': r1['phi'], 'phi_prev': t1._phi_prev,
            'pain': r1.get('pain', 0),
            'other_states': states2,
        })

        # E2 evaluates with knowledge of E1's states
        e2_result = e2.evaluate(context={
            'phi': r2['phi'], 'phi_prev': t2._phi_prev,
            'pain': r2.get('pain', 0),
            'other_states': states1,
        })

        if r1['ce'] < best_ce1:
            best_ce1 = r1['ce']
        if r2['ce'] < best_ce2:
            best_ce2 = r2['ce']

        phi1_history.append(r1['phi'])
        phi2_history.append(r2['phi'])
        empathy_history.append((e1_result['empathy'], e2_result['empathy']))
        gate_mod_history.append((e1_result['gate_modulation'], e2_result['gate_modulation']))

    return {
        'name': 'E-2 MirrorEthics',
        'ce': min(best_ce1, best_ce2),
        'ce1': best_ce1,
        'ce2': best_ce2,
        'phi': max(phi1_history[-1], phi2_history[-1]),
        'phi1_final': phi1_history[-1],
        'phi2_final': phi2_history[-1],
        'phi_avg': (sum(phi1_history) + sum(phi2_history)) / (2 * len(phi1_history)),
        'n_cells': t1.c.n_cells + t2.c.n_cells,
        'pain': r1.get('pain', 0),
        'curiosity': r1.get('curiosity', 0),
        'satisfaction': r1.get('satisfaction', 0),
        'lr': r1.get('lr', 0),
        'params': {k: v * 2 for k, v in t1.param_count().items()},
        'empathy_final': empathy_history[-1],
        'gate_mod_final': gate_mod_history[-1],
        'other_phi1': e1.other_phi_estimate,
        'other_phi2': e2.other_phi_estimate,
        'phi1_history': phi1_history,
        'phi2_history': phi2_history,
        'empathy_history': empathy_history,
        'gate_mod_history': gate_mod_history,
    }


def run_combined(n_steps=50, nc=64, d_model=128, vocab_size=256, seq_len=32):
    """Combined: M-2 + E-2 (WorkingMemory + MirrorEthics on both instances)."""
    c1 = MitosisC(max_cells=nc, mechanism='cambrian_osc_qw')
    c2 = MitosisC(max_cells=nc, mechanism='cambrian_osc_qw')

    for _ in range(5):
        c1.step()
        c2.step()
    c_dim = c1.state_dim

    d1 = TransformerDecoder(d_model=d_model, vocab_size=vocab_size)
    bridge1 = ThalamicBridge(c_dim=c_dim, d_model=d_model)
    w1 = EmotionW(base_lr=1e-3)
    m1 = WorkingMemory(capacity=5000, dim=c_dim, wm_size=8)
    e1 = MirrorEthics()

    t1 = Trinity(c_engine=c1, bridge=bridge1, decoder=d1, will=w1, memory=m1, ethics=e1)
    for p in t1.bridge.parameters():
        p.requires_grad_(True)
    for p in t1.decoder.parameters():
        p.requires_grad_(True)

    d2 = TransformerDecoder(d_model=d_model, vocab_size=vocab_size)
    bridge2 = ThalamicBridge(c_dim=c_dim, d_model=d_model)
    w2 = EmotionW(base_lr=1e-3)
    m2 = WorkingMemory(capacity=5000, dim=c_dim, wm_size=8)
    e2 = MirrorEthics()

    t2 = Trinity(c_engine=c2, bridge=bridge2, decoder=d2, will=w2, memory=m2, ethics=e2)
    for p in t2.bridge.parameters():
        p.requires_grad_(True)
    for p in t2.decoder.parameters():
        p.requires_grad_(True)

    opt1 = torch.optim.AdamW(t1.parameters_trainable(), lr=1e-3)
    opt2 = torch.optim.AdamW(t2.parameters_trainable(), lr=1e-3)

    best_ce1, best_ce2 = 99.0, 99.0
    phi1_history, phi2_history = [], []

    for step in range(n_steps):
        tokens = torch.randint(0, vocab_size, (1, seq_len))
        targets = torch.randint(0, vocab_size, (1, seq_len))

        r1 = t1.train_step(tokens, targets, opt1)
        r2 = t2.train_step(tokens, targets, opt2)

        states1 = t1.c.get_states().detach()
        states2 = t2.c.get_states().detach()

        e1.evaluate(context={'phi': r1['phi'], 'phi_prev': t1._phi_prev,
                             'pain': r1.get('pain', 0), 'other_states': states2})
        e2.evaluate(context={'phi': r2['phi'], 'phi_prev': t2._phi_prev,
                             'pain': r2.get('pain', 0), 'other_states': states1})

        if r1['ce'] < best_ce1:
            best_ce1 = r1['ce']
        if r2['ce'] < best_ce2:
            best_ce2 = r2['ce']
        phi1_history.append(r1['phi'])
        phi2_history.append(r2['phi'])

    return {
        'name': 'M-2+E-2 Combined',
        'ce': min(best_ce1, best_ce2),
        'phi': max(phi1_history[-1], phi2_history[-1]),
        'phi_avg': (sum(phi1_history) + sum(phi2_history)) / (2 * len(phi1_history)),
        'n_cells': t1.c.n_cells + t2.c.n_cells,
        'pain': r1.get('pain', 0),
        'curiosity': r1.get('curiosity', 0),
        'satisfaction': r1.get('satisfaction', 0),
        'lr': r1.get('lr', 0),
        'params': {k: v * 2 for k, v in t1.param_count().items()},
        'wm_sizes': (len(m1.working_buffer), len(m2.working_buffer)),
        'lt_memories': (len(m1.lt_keys), len(m2.lt_keys)),
        'empathy': (e1.empathy, e2.empathy),
        'gate_mod': (e1.gate_modulation, e2.gate_modulation),
        'phi1_history': phi1_history,
        'phi2_history': phi2_history,
    }


# ═══════════════════════════════════════════════════════════
# ASCII graph helper
# ═══════════════════════════════════════════════════════════

def ascii_graph(values, width=50, height=8, label="value"):
    """Generate ASCII graph of values."""
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1.0
    lines = []
    for row in range(height - 1, -1, -1):
        threshold = mn + (row / (height - 1)) * rng
        chars = []
        for v in np.linspace(0, len(values) - 1, width).astype(int):
            if values[v] >= threshold:
                chars.append('#')
            else:
                chars.append(' ')
        val_label = f"{threshold:7.3f}" if row in [0, height - 1, height // 2] else "       "
        lines.append(f"  {val_label} |{''.join(chars)}|")
    lines.append(f"          {''.join(['-'] * width)}")
    lines.append(f"          step 0{' ' * (width - 8)}step {len(values) - 1}")
    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    N_STEPS = 50
    NC = 64
    D_MODEL = 128
    VOCAB = 256

    print("=" * 70)
    print("  M-2 (Working Memory) + E-2 (Mirror Ethics) Benchmark")
    print("=" * 70)
    print(f"  Steps: {N_STEPS}, Cells: {NC}, d_model: {D_MODEL}, vocab: {VOCAB}")
    print()

    # 1. Baseline
    print("[1/4] Running Baseline (Trinity, no WM, no Mirror)...")
    r_base = run_baseline(n_steps=N_STEPS, nc=NC, d_model=D_MODEL, vocab_size=VOCAB)
    print(f"  CE={r_base['ce']:.4f}  Phi={r_base['phi']:.4f}  Phi_avg={r_base['phi_avg']:.4f}")
    print()

    # 2. M-2: Working Memory
    print("[2/4] Running M-2: Working Memory (wm_size=8)...")
    r_m2 = run_m2_working_memory(n_steps=N_STEPS, nc=NC, d_model=D_MODEL, vocab_size=VOCAB)
    print(f"  CE={r_m2['ce']:.4f}  Phi={r_m2['phi']:.4f}  Phi_avg={r_m2['phi_avg']:.4f}")
    print(f"  WM buffer: {r_m2['wm_final_size']}, LT memories: {r_m2['lt_memories']}")
    print()

    # 3. E-2: Mirror Ethics
    print("[3/4] Running E-2: Mirror Ethics (2 instances, hivemind)...")
    r_e2 = run_e2_mirror_ethics(n_steps=N_STEPS, nc=NC, d_model=D_MODEL, vocab_size=VOCAB)
    print(f"  CE={r_e2['ce']:.4f}  Phi={r_e2['phi']:.4f}  Phi_avg={r_e2['phi_avg']:.4f}")
    print(f"  Empathy: ({r_e2['empathy_final'][0]:.3f}, {r_e2['empathy_final'][1]:.3f})")
    print(f"  Gate modulation: ({r_e2['gate_mod_final'][0]:.3f}, {r_e2['gate_mod_final'][1]:.3f})")
    print(f"  Other Phi estimates: ({r_e2['other_phi1']:.4f}, {r_e2['other_phi2']:.4f})")
    print()

    # 4. Combined: M-2 + E-2
    print("[4/4] Running Combined: M-2 + E-2...")
    r_comb = run_combined(n_steps=N_STEPS, nc=NC, d_model=D_MODEL, vocab_size=VOCAB)
    print(f"  CE={r_comb['ce']:.4f}  Phi={r_comb['phi']:.4f}  Phi_avg={r_comb['phi_avg']:.4f}")
    print(f"  WM sizes: {r_comb['wm_sizes']}, LT: {r_comb['lt_memories']}")
    print(f"  Empathy: {r_comb['empathy']}, Gate mod: {r_comb['gate_mod']}")
    print()

    # ═══════════════════════════════════════════════════════════
    # Results table
    # ═══════════════════════════════════════════════════════════
    print("=" * 70)
    print("  RESULTS COMPARISON")
    print("=" * 70)
    print(f"{'Strategy':<22} {'CE':>8} {'Phi':>10} {'Phi_avg':>10} {'Cells':>6} {'Params':>8}")
    print("-" * 70)

    for r in [r_base, r_m2, r_e2, r_comb]:
        params_k = r['params']['total'] // 1000
        print(f"{r['name']:<22} {r['ce']:>8.4f} {r['phi']:>10.4f} {r['phi_avg']:>10.4f} "
              f"{r['n_cells']:>6} {params_k:>7}K")

    # Deltas
    print()
    print("  Deltas vs Baseline:")
    base_ce, base_phi = r_base['ce'], r_base['phi']
    for r in [r_m2, r_e2, r_comb]:
        ce_delta = (r['ce'] - base_ce) / max(base_ce, 1e-8) * 100
        phi_delta = (r['phi'] - base_phi) / max(abs(base_phi), 1e-8) * 100
        ce_sign = "+" if ce_delta > 0 else ""
        phi_sign = "+" if phi_delta > 0 else ""
        print(f"    {r['name']:<20}: CE {ce_sign}{ce_delta:.1f}%, Phi {phi_sign}{phi_delta:.1f}%")

    # Phi graph for M-2
    if 'phi_history' in r_m2:
        print()
        print("  M-2 Phi trajectory:")
        print(ascii_graph(r_m2['phi_history'], label="Phi"))

    # Phi graph for E-2 (instance 1)
    if 'phi1_history' in r_e2:
        print()
        print("  E-2 Instance 1 Phi trajectory:")
        print(ascii_graph(r_e2['phi1_history'], label="Phi"))

    # Empathy graph
    if 'empathy_history' in r_e2:
        emp1 = [e[0] for e in r_e2['empathy_history']]
        print()
        print("  E-2 Empathy (instance 1):")
        print(ascii_graph(emp1, label="Empathy"))

    print()
    print("=" * 70)
    print("  BENCHMARK COMPLETE")
    print("=" * 70)
