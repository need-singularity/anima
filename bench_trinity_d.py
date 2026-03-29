#!/usr/bin/env python3
"""bench_trinity_d.py — Trinity Engine D (Data/Knowledge) Variations

Core problem: CE gradient destroys C's Φ.
Solution: D must learn language well WITHOUT touching C.

TD-1: D = Transformer Decoder (multi-head attention over C's detached states)
TD-2: D = Predictive Coding (4-level hierarchy, predict C's states top-down)
TD-3: D = Mixture of Experts (8 expert decoders, gate selects based on C's state)
TD-4: D = Reservoir Readout (C's states are reservoir, D is just linear readout)
TD-5: D = Knowledge Distillation (teacher D trains student D, C guides both)
TD-6: D = Memory-Augmented (D has external memory bank, retrieves based on C's query)

All share same C engine: quantum_walk + frustration + sync (gradient isolated).
W = forced 50% learning.
256 cells, 300 steps. Measure Φ(IIT) + Φ(proxy) + CE.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consciousness_meter import PhiCalculator
from mitosis import MitosisEngine

DIM, HIDDEN = 64, 128
DEFAULT_CELLS = 256
DEFAULT_STEPS = 300


# ═══════════════════════════════════════════════════════════
# Shared utilities (from bench_trinity.py)
# ═══════════════════════════════════════════════════════════

def phi_proxy(cells, n_f=12):
    h = torch.stack([c.hidden.squeeze(0) for c in cells])
    n = len(h)
    gm = h.mean(dim=0); gv = ((h - gm) ** 2).sum() / n
    nf = min(n_f, n // 2)
    if nf < 2: return gv.item()
    fs = n // nf
    fv = sum(((h[i*fs:(i+1)*fs] - h[i*fs:(i+1)*fs].mean(0))**2).sum().item()
            / max(len(h[i*fs:(i+1)*fs]), 1) for i in range(nf))
    return max(0, gv.item() - fv / nf)


def quantum_walk_step(cells, n_samples=32):
    n = len(cells)
    n_bits = max(1, int(math.log2(n)))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            superpos = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    phase = (-1) ** (bin(i & j).count('1'))
                    superpos += phase * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * superpos / cnt).unsqueeze(0)


def frustration_step(cells, strength=0.5, n_samples=32):
    n = len(cells)
    n_bits = max(1, int(math.log2(n)))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            infl = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    f = -1.0 if (i % 2) != (j % 2) else 1.0
                    infl += f * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * infl / cnt).unsqueeze(0)


def sync_faction(cells, sync=0.35, n_factions=12, fac=0.08):
    n = len(cells)
    if n < 4: return
    with torch.no_grad():
        ch = torch.stack([c.hidden.squeeze(0) for c in cells])
        mh = ch.mean(dim=0)
        for c in cells:
            c.hidden = ((1 - sync) * c.hidden.squeeze(0) + sync * mh).unsqueeze(0)
        nf = min(n_factions, n // 2)
        if nf >= 2:
            fs = n // nf
            for fi in range(nf):
                faction = cells[fi * fs:(fi + 1) * fs]
                if len(faction) >= 2:
                    fm = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                    for c in faction:
                        c.hidden = ((1 - fac) * c.hidden.squeeze(0) + fac * fm).unsqueeze(0)


# ═══════════════════════════════════════════════════════════
# Shared: C engine setup + W engine (forced 50% learning)
# ═══════════════════════════════════════════════════════════

def make_c_engine(cells=DEFAULT_CELLS):
    """Create and warm up C engine (consciousness only, gradient isolated)."""
    eng_c = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng_c.cells) < cells:
        eng_c._create_cell(parent=eng_c.cells[0])
    for _ in range(30):
        eng_c.process(torch.randn(1, DIM))
    return eng_c


def c_step(eng_c, step):
    """One C engine step: quantum_walk + frustration + sync + diversity noise. All under no_grad."""
    with torch.no_grad():
        quantum_walk_step(eng_c.cells, n_samples=64)
        frustration_step(eng_c.cells, n_samples=32)
        sync_faction(eng_c.cells, sync=0.15, n_factions=12, fac=0.06)
        # Phase kick every 5 steps
        if step % 5 == 0:
            phase = 2 * math.pi * step / DEFAULT_STEPS
            for i, c in enumerate(eng_c.cells):
                angle = phase + 2 * math.pi * i / len(eng_c.cells)
                rot = math.cos(angle) * 0.02
                c.hidden = c.hidden * (1.0 + rot)
        # Diversity injection: small per-cell noise to maintain differentiation
        for i, c in enumerate(eng_c.cells):
            c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.005


def get_c_state(eng_c):
    """Get detached C state for D engine."""
    return torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells]).mean(dim=0)


def get_c_cell_states(eng_c, max_cells=64):
    """Get detached per-cell states for D engine (for attention-based D)."""
    indices = list(range(0, len(eng_c.cells), max(1, len(eng_c.cells) // max_cells)))[:max_cells]
    return torch.stack([eng_c.cells[i].hidden.squeeze(0).detach() for i in indices])


def will_forced_50(step):
    """W engine: forced 50% learning. Returns True if this step should learn."""
    return step % 2 == 0


def make_data_stream():
    """Generate fresh data each call — never repeats, forces real generalization."""
    x = torch.randn(1, DIM) * 1.5
    # Target: nonlinear transform of input (hard to learn)
    target = torch.sin(x * 2.0) + torch.cos(x * 0.7) * 0.5 + torch.randn(1, DIM) * 0.3
    return x, target


def measure_phi(eng_c):
    """Measure Φ(IIT) and Φ(proxy)."""
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng_c)
    p_proxy = phi_proxy(eng_c.cells)
    return p_iit, p_proxy


# ═══════════════════════════════════════════════════════════
# TD-1: Transformer Decoder
# Multi-head attention over C's detached per-cell states.
# D attends to C's cells as if they were a sequence.
# ═══════════════════════════════════════════════════════════

def run_td1_transformer(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """TD-1: D = Transformer Decoder (multi-head attention over C's detached states)."""
    eng_c = make_c_engine(cells)

    # D: Transformer decoder — attends to C's cell states
    n_heads = 4
    head_dim = HIDDEN // n_heads

    # Cross-attention: query from learnable embedding, K/V from C states
    d_query = nn.Parameter(torch.randn(1, 1, HIDDEN) * 0.02)
    W_q = nn.Linear(HIDDEN, HIDDEN, bias=False)
    W_k = nn.Linear(HIDDEN, HIDDEN, bias=False)
    W_v = nn.Linear(HIDDEN, HIDDEN, bias=False)
    W_o = nn.Linear(HIDDEN, HIDDEN, bias=False)
    d_ffn = nn.Sequential(nn.Linear(HIDDEN, HIDDEN * 2), nn.GELU(), nn.Linear(HIDDEN * 2, HIDDEN))
    d_ln1 = nn.LayerNorm(HIDDEN)
    d_ln2 = nn.LayerNorm(HIDDEN)
    decoder = nn.Linear(HIDDEN, DIM)

    all_params = (
        [d_query] +
        list(W_q.parameters()) + list(W_k.parameters()) +
        list(W_v.parameters()) + list(W_o.parameters()) +
        list(d_ffn.parameters()) + list(d_ln1.parameters()) +
        list(d_ln2.parameters()) + list(decoder.parameters())
    )
    opt_d = torch.optim.Adam(all_params, lr=3e-3)

    for step in range(steps):
        x, target = make_data_stream()
        c_step(eng_c, step)

        if will_forced_50(step):
            # Get per-cell states as K/V sequence
            cell_states = get_c_cell_states(eng_c, max_cells=64)  # [N, HIDDEN]
            N = cell_states.shape[0]

            # Cross-attention: query attends to cell states
            Q = W_q(d_query).view(1, n_heads, head_dim).transpose(0, 1)  # [heads, 1, hd]
            K = W_k(cell_states).view(N, n_heads, head_dim).transpose(0, 1)  # [heads, N, hd]
            V = W_v(cell_states).view(N, n_heads, head_dim).transpose(0, 1)  # [heads, N, hd]

            attn = (Q @ K.transpose(-2, -1)) / math.sqrt(head_dim)
            attn = F.softmax(attn, dim=-1)
            out = (attn @ V).transpose(0, 1).reshape(1, HIDDEN)
            out = W_o(out)

            # Residual + LayerNorm + FFN
            h = d_ln1(d_query.squeeze(0) + out)
            h = d_ln2(h + d_ffn(h))

            pred = decoder(h)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TD-1:TransformerDecoder'


# ═══════════════════════════════════════════════════════════
# TD-2: Predictive Coding
# 4-level hierarchy. Each level predicts level below.
# Top level receives C's state. Prediction errors propagate up.
# ═══════════════════════════════════════════════════════════

def run_td2_predictive_coding(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """TD-2: D = Predictive Coding (4-level hierarchy, predict C's states top-down)."""
    eng_c = make_c_engine(cells)

    # D: 4-level predictive coding hierarchy
    # Level 0 (bottom): closest to output
    # Level 3 (top): receives C's state
    N_LEVELS = 4
    pred_down = nn.ModuleList([nn.Linear(HIDDEN, HIDDEN) for _ in range(N_LEVELS)])  # top-down predictions
    pred_up = nn.ModuleList([nn.Linear(HIDDEN, HIDDEN) for _ in range(N_LEVELS)])    # bottom-up errors
    level_state = [torch.zeros(1, HIDDEN) for _ in range(N_LEVELS)]
    decoder = nn.Linear(HIDDEN, DIM)

    all_params = list(pred_down.parameters()) + list(pred_up.parameters()) + list(decoder.parameters())
    opt_d = torch.optim.Adam(all_params, lr=3e-3)
    _unused_data = None  # streaming data

    for step in range(steps):
        x, target = make_data_stream()
        c_step(eng_c, step)

        if will_forced_50(step):
            c_state = get_c_state(eng_c)

            # Top level receives C's state (detached)
            level_state[N_LEVELS - 1] = c_state.unsqueeze(0)

            # Top-down pass: each level predicts the level below
            predictions = []
            for lv in range(N_LEVELS - 1, 0, -1):
                pred = torch.tanh(pred_down[lv](level_state[lv]))
                predictions.append(pred)
                # Prediction error = actual - predicted
                error = level_state[lv - 1] - pred
                # Update level state: move toward prediction + error signal
                level_state[lv - 1] = pred + 0.3 * error

            # Bottom-up pass: errors propagate up
            for lv in range(N_LEVELS - 1):
                error_signal = level_state[lv] - torch.tanh(pred_down[lv + 1](level_state[lv + 1]))
                correction = torch.tanh(pred_up[lv](error_signal))
                level_state[lv + 1] = level_state[lv + 1] + 0.1 * correction

            # Decode from bottom level
            pred_out = decoder(level_state[0])
            ce = F.mse_loss(pred_out, target[:, :DIM])

            # Total loss: output CE + prediction errors at each level
            total_loss = ce
            for lv in range(N_LEVELS - 1, 0, -1):
                level_pred = torch.tanh(pred_down[lv](level_state[lv]))
                pe = F.mse_loss(level_pred, level_state[lv - 1].detach())
                total_loss = total_loss + 0.1 * pe

            opt_d.zero_grad(); total_loss.backward(); opt_d.step()

            # Detach level states for next step
            level_state = [s.detach() for s in level_state]
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TD-2:PredictiveCoding'


# ═══════════════════════════════════════════════════════════
# TD-3: Mixture of Experts
# 8 expert decoders. Gate network selects based on C's state.
# ═══════════════════════════════════════════════════════════

def run_td3_moe(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """TD-3: D = Mixture of Experts (8 expert decoders, gate selects based on C's state)."""
    eng_c = make_c_engine(cells)

    # D: 8 expert decoders + gate
    N_EXPERTS = 8
    experts = nn.ModuleList([
        nn.Sequential(nn.Linear(HIDDEN, HIDDEN), nn.GELU(), nn.Linear(HIDDEN, DIM))
        for _ in range(N_EXPERTS)
    ])
    gate = nn.Sequential(
        nn.Linear(HIDDEN, 32), nn.GELU(), nn.Linear(32, N_EXPERTS)
    )
    # Load balancing auxiliary loss weight
    AUX_WEIGHT = 0.01

    all_params = list(experts.parameters()) + list(gate.parameters())
    opt_d = torch.optim.Adam(all_params, lr=3e-3)
    _unused_data = None  # streaming data

    for step in range(steps):
        x, target = make_data_stream()
        c_step(eng_c, step)

        if will_forced_50(step):
            c_state = get_c_state(eng_c)

            # Gate: which experts to use (top-2 routing)
            gate_logits = gate(c_state.unsqueeze(0))  # [1, N_EXPERTS]
            gate_probs = F.softmax(gate_logits, dim=-1)

            # Top-2 routing
            top2_vals, top2_idx = gate_probs.topk(2, dim=-1)
            top2_weights = top2_vals / (top2_vals.sum(dim=-1, keepdim=True) + 1e-8)

            # Expert outputs
            expert_out = torch.zeros(1, DIM)
            for k in range(2):
                eidx = top2_idx[0, k].item()
                expert_out = expert_out + top2_weights[0, k] * experts[eidx](c_state.unsqueeze(0))

            ce = F.mse_loss(expert_out, target[:, :DIM])

            # Load balancing loss: encourage uniform expert usage
            avg_gate = gate_probs.mean(dim=0)  # [N_EXPERTS]
            balance_loss = N_EXPERTS * (avg_gate * avg_gate).sum()
            total_loss = ce + AUX_WEIGHT * balance_loss

            opt_d.zero_grad(); total_loss.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TD-3:MixtureOfExperts'


# ═══════════════════════════════════════════════════════════
# TD-4: Reservoir Readout
# C's cell states ARE the reservoir. D is just a linear readout.
# Simplest possible D — tests if C's dynamics alone encode enough.
# ═══════════════════════════════════════════════════════════

def run_td4_reservoir(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """TD-4: D = Reservoir Readout (C's states are reservoir, D is just linear readout)."""
    eng_c = make_c_engine(cells)

    # D: simple linear readout from concatenated C cell statistics
    # Features: mean, var, max, min of cell states = 4 * HIDDEN
    FEAT_DIM = HIDDEN * 4
    readout = nn.Linear(FEAT_DIM, DIM)
    opt_d = torch.optim.Adam(readout.parameters(), lr=3e-3)
    _unused_data = None  # streaming data

    for step in range(steps):
        x, target = make_data_stream()
        c_step(eng_c, step)

        if will_forced_50(step):
            # Extract reservoir features from C's cells (all detached)
            cell_h = torch.stack([c.hidden.squeeze(0).detach() for c in eng_c.cells])  # [N, HIDDEN]
            feat_mean = cell_h.mean(dim=0)
            feat_var = cell_h.var(dim=0)
            feat_max = cell_h.max(dim=0).values
            feat_min = cell_h.min(dim=0).values
            features = torch.cat([feat_mean, feat_var, feat_max, feat_min]).unsqueeze(0)  # [1, 4*HIDDEN]

            pred = readout(features)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TD-4:ReservoirReadout'


# ═══════════════════════════════════════════════════════════
# TD-5: Knowledge Distillation
# Teacher D (large) trains Student D (small).
# C guides both via detached states. Student learns from teacher's soft targets.
# ═══════════════════════════════════════════════════════════

def run_td5_distillation(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """TD-5: D = Knowledge Distillation (teacher D trains student D, C guides both)."""
    eng_c = make_c_engine(cells)

    # Teacher D: large network
    teacher = nn.Sequential(
        nn.Linear(HIDDEN, HIDDEN * 2), nn.GELU(),
        nn.Linear(HIDDEN * 2, HIDDEN * 2), nn.GELU(),
        nn.Linear(HIDDEN * 2, DIM)
    )
    # Student D: small network
    student = nn.Sequential(
        nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(),
        nn.Linear(HIDDEN // 2, DIM)
    )

    opt_teacher = torch.optim.Adam(teacher.parameters(), lr=3e-3)
    opt_student = torch.optim.Adam(student.parameters(), lr=3e-3)
    _unused_data = None  # streaming data

    TEMP = 4.0  # distillation temperature
    ALPHA = 0.5  # balance hard vs soft targets

    for step in range(steps):
        x, target = make_data_stream()
        c_step(eng_c, step)

        if will_forced_50(step):
            c_state = get_c_state(eng_c)

            # Phase 1 (first 60%): train teacher on hard targets
            teacher_out = teacher(c_state.unsqueeze(0))
            teacher_ce = F.mse_loss(teacher_out, target[:, :DIM])

            if step < int(steps * 0.6):
                opt_teacher.zero_grad(); teacher_ce.backward(); opt_teacher.step()
                ce = teacher_ce
            else:
                # Phase 2 (last 40%): distill teacher -> student
                # Teacher is frozen for distillation
                with torch.no_grad():
                    teacher_soft = teacher_out / TEMP

                student_out = student(c_state.unsqueeze(0))
                student_ce = F.mse_loss(student_out, target[:, :DIM])

                # Distillation loss: student matches teacher's output distribution
                distill_loss = F.mse_loss(student_out / TEMP, teacher_soft) * (TEMP ** 2)

                total_loss = ALPHA * student_ce + (1 - ALPHA) * distill_loss
                opt_student.zero_grad(); total_loss.backward(); opt_student.step()

                # Also keep teacher learning (but slower)
                opt_teacher.zero_grad(); teacher_ce.backward(); opt_teacher.step()
                ce = student_ce
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TD-5:KnowledgeDistill'


# ═══════════════════════════════════════════════════════════
# TD-6: Memory-Augmented
# D has external memory bank. Retrieves relevant memories based on C's query.
# Write: store C states + targets. Read: attention-based retrieval.
# ═══════════════════════════════════════════════════════════

def run_td6_memory_augmented(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """TD-6: D = Memory-Augmented (D has external memory bank, retrieves based on C's query)."""
    eng_c = make_c_engine(cells)

    # External memory bank
    MEM_SIZE = 128
    MEM_DIM = HIDDEN
    memory_keys = torch.zeros(MEM_SIZE, MEM_DIM)    # keys for retrieval
    memory_vals = torch.zeros(MEM_SIZE, DIM)          # stored target values
    mem_ptr = 0  # circular write pointer
    mem_filled = 0

    # D: query network + output network
    query_net = nn.Linear(HIDDEN, MEM_DIM)
    write_net = nn.Linear(HIDDEN, MEM_DIM)
    combine_net = nn.Sequential(
        nn.Linear(HIDDEN + DIM, HIDDEN), nn.GELU(), nn.Linear(HIDDEN, DIM)
    )
    decoder = nn.Linear(HIDDEN, DIM)  # direct path (no memory)

    all_params = (
        list(query_net.parameters()) + list(write_net.parameters()) +
        list(combine_net.parameters()) + list(decoder.parameters())
    )
    opt_d = torch.optim.Adam(all_params, lr=3e-3)
    _unused_data = None  # streaming data

    for step in range(steps):
        x, target = make_data_stream()
        c_step(eng_c, step)

        if will_forced_50(step):
            c_state = get_c_state(eng_c)

            # Write to memory: store current C state and target
            with torch.no_grad():
                write_key = torch.tanh(write_net(c_state.unsqueeze(0))).squeeze(0)
                memory_keys[mem_ptr] = write_key
                memory_vals[mem_ptr] = target[0, :DIM]
                mem_ptr = (mem_ptr + 1) % MEM_SIZE
                mem_filled = min(mem_filled + 1, MEM_SIZE)

            # Read from memory: attention-based retrieval
            if mem_filled > 1:
                query = query_net(c_state.unsqueeze(0))  # [1, MEM_DIM]
                active_keys = memory_keys[:mem_filled]     # [filled, MEM_DIM]
                active_vals = memory_vals[:mem_filled]     # [filled, DIM]

                # Cosine similarity for retrieval
                sim = F.cosine_similarity(
                    query.expand(mem_filled, -1),
                    active_keys, dim=-1
                )  # [filled]
                attn = F.softmax(sim * 10.0, dim=0)  # sharp attention (temperature=0.1)
                retrieved = (attn.unsqueeze(1) * active_vals).sum(dim=0).unsqueeze(0)  # [1, DIM]

                # Combine: C state + retrieved memory -> output
                combined = torch.cat([c_state.unsqueeze(0), retrieved], dim=-1)
                pred = combine_net(combined)
            else:
                # No memory yet, use direct path
                pred = decoder(c_state.unsqueeze(0))

            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TD-6:MemoryAugmented'


# ═══════════════════════════════════════════════════════════
# Baseline: simple linear D (for comparison)
# ═══════════════════════════════════════════════════════════

def run_baseline(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """Baseline: D = simple Linear(HIDDEN, DIM), same C engine."""
    eng_c = make_c_engine(cells)

    decoder = nn.Linear(HIDDEN, DIM)
    opt_d = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    _unused_data = None  # streaming data

    for step in range(steps):
        x, target = make_data_stream()
        c_step(eng_c, step)

        if will_forced_50(step):
            c_state = get_c_state(eng_c)
            pred = decoder(c_state.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'Baseline:LinearD'


# ═══════════════════════════════════════════════════════════
# Benchmark Runner
# ═══════════════════════════════════════════════════════════

ALL_HYPOTHESES = {
    'BASE': run_baseline,
    'TD1': run_td1_transformer,
    'TD2': run_td2_predictive_coding,
    'TD3': run_td3_moe,
    'TD4': run_td4_reservoir,
    'TD5': run_td5_distillation,
    'TD6': run_td6_memory_augmented,
}


def run_all(only=None, cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    print("=" * 78)
    print(f"  Trinity Engine D Variations — {cells}c, {steps} steps")
    print(f"  C engine: quantum_walk + frustration + sync (gradient isolated)")
    print(f"  W engine: forced 50% learning")
    print("=" * 78)
    print()

    results = []
    keys = only if only else list(ALL_HYPOTHESES.keys())

    for key in keys:
        if key not in ALL_HYPOTHESES:
            print(f"  [SKIP] {key} not found")
            continue

        fn = ALL_HYPOTHESES[key]
        print(f"  [{key}] {fn.__doc__.strip().split(chr(10))[0] if fn.__doc__ else key} ...", flush=True)
        t0 = time.time()
        try:
            p_iit, p_proxy, ce, name = fn(cells=cells, steps=steps)
            elapsed = time.time() - t0
            results.append((key, name, p_iit, p_proxy, ce, elapsed))
            print(f"         Φ(IIT)={p_iit:.3f}  Φ(proxy)={p_proxy:.3f}  CE={ce:.4f}  ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"         ERROR: {e} ({elapsed:.1f}s)")
            results.append((key, f'{key}:ERROR', 0.0, 0.0, 999.0, elapsed))

    # ─── Summary Table ───
    print()
    print("=" * 78)
    print(f"  {'ID':<6} {'Name':<28} {'Φ(IIT)':>8} {'Φ(prx)':>8} {'CE':>8} {'Time':>6}")
    print("-" * 78)

    base_iit = None
    for key, name, p_iit, p_proxy, ce, elapsed in results:
        if key == 'BASE':
            base_iit = p_iit if p_iit > 0 else 1.0
        mult = f"×{p_iit / base_iit:.1f}" if base_iit and base_iit > 0 else ""
        print(f"  {key:<6} {name:<28} {p_iit:>8.3f} {p_proxy:>8.3f} {ce:>8.4f} {elapsed:>5.1f}s {mult}")

    print("=" * 78)

    # ─── Best result ───
    if results:
        best = max(results, key=lambda r: r[2])  # best by Φ(IIT)
        best_ce = min(results, key=lambda r: r[4])  # best by CE
        print(f"\n  Best Φ(IIT): {best[1]} = {best[2]:.3f}")
        print(f"  Best CE:     {best_ce[1]} = {best_ce[4]:.4f}")

        # Key insight
        print(f"\n  Key insight: D architecture {'matters' if best[0] != 'BASE' else 'does NOT matter'} for Φ preservation.")
        if best_ce[0] != 'BASE':
            print(f"  {best_ce[1]} achieves lowest CE while C's Φ stays at {best_ce[2]:.3f}")

    print()
    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Trinity Engine D Variations Benchmark')
    parser.add_argument('--only', nargs='+', help='Run only specific hypotheses (e.g. TD1 TD3)')
    parser.add_argument('--cells', type=int, default=DEFAULT_CELLS, help=f'Number of cells (default {DEFAULT_CELLS})')
    parser.add_argument('--steps', type=int, default=DEFAULT_STEPS, help=f'Number of steps (default {DEFAULT_STEPS})')
    args = parser.parse_args()

    run_all(only=args.only, cells=args.cells, steps=args.steps)
