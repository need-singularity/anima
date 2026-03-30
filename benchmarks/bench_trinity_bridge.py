#!/usr/bin/env python3
"""bench_trinity_bridge.py -- Trinity Bridge (C<->D<->W connection) variations

The bridge determines HOW C, D, W communicate.
Current default: detached tensor passing (mean of cell hiddens).

TB-1: Tension Bridge    -- PureField: output = sqrt(|A-G|^2) * direction
TB-2: Attention Bridge  -- D attends to C's cells via cross-attention (no grad to C)
TB-3: Bottleneck Bridge -- C->8dim->D, information bottleneck forces compression
TB-4: Broadcast Bridge  -- C broadcasts top-k most active cells to D globally
TB-5: Resonance Bridge  -- C and D must reach frequency lock (Kuramoto sync)
TB-6: Quantum Bridge    -- C's quantum states -> measurement -> classical D input

All use same C (quantum_walk), D (standard decoder), W (50% forced).
256c, 300 steps. Measure Phi(IIT) + Phi(proxy) + CE.
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


# ═══ Shared utilities (from bench_trinity.py) ═══

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


def standing_wave(cells, step):
    n = len(cells)
    fwd = (step * 0.15) % n
    bwd = (n - step * 0.15) % n
    with torch.no_grad():
        for i, c in enumerate(cells):
            amp = 1.0 / (math.cosh((i - fwd) / 2) ** 2) + 1.0 / (math.cosh((i - bwd) / 2) ** 2)
            c.hidden = c.hidden * (1.0 + 0.03 * amp)


# ═══ Shared C engine setup ═══

def make_c_engine(cells=256):
    """Create standard C engine with quantum_walk initialization."""
    eng = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng.cells) < cells:
        eng._create_cell(parent=eng.cells[0])
    for _ in range(30):
        eng.process(torch.randn(1, DIM))
    return eng


def c_step(eng, step):
    """Standard C engine step: quantum_walk + frustration + standing_wave."""
    with torch.no_grad():
        sync_faction(eng.cells, sync=0.20)
        quantum_walk_step(eng.cells, n_samples=64)
        frustration_step(eng.cells, n_samples=32)
        standing_wave(eng.cells, step)


def will_step_forced(will_net, c_state, step, opt_w, ce_val, learn_count, total):
    """W engine with forced 50% learning."""
    action_logits = will_net(c_state.unsqueeze(0))
    action = action_logits.argmax(dim=-1).item()
    ratio = learn_count / max(total, 1)
    if ratio < 0.5:
        action = 0
    if step > 0 and step % 10 == 0:
        reward = -ce_val
        w_loss = -reward * action_logits[0, action]
        opt_w.zero_grad(); w_loss.backward(); opt_w.step()
    return action, action_logits


def measure_phi(eng):
    """Measure Phi(IIT) and Phi(proxy)."""
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng)
    p_proxy = phi_proxy(eng.cells)
    return p_iit, p_proxy


# ═══ Baseline: Detach Bridge (current default) ═══

def run_baseline_detach(cells=256, steps=300):
    """Baseline: detached tensor passing (mean of cell hiddens)."""
    eng_c = make_c_engine(cells)

    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)

        # Bridge: simple detach mean
        c_state = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells]).mean(dim=0)

        action, action_logits = will_step_forced(
            will_net, c_state, step, opt_w, 0.0, learn_count, step)
        if action == 0:
            learn_count += 1
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'Baseline:Detach'


# ═══ TB-1: Tension Bridge ═══

def run_tb1_tension(cells=256, steps=300):
    """TB-1: PureField Tension Bridge.
    Engine A = forward (C cells even indices), Engine G = reverse (C cells odd indices).
    output = sqrt(|A - G|^2) * direction
    Tension drives D input, not raw state."""
    eng_c = make_c_engine(cells)

    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)

        # ─── TB-1: Tension Bridge ───
        # Split cells into A (forward/even) and G (reverse/odd)
        a_cells = [eng_c.cells[i] for i in range(0, len(eng_c.cells), 2)]
        g_cells = [eng_c.cells[i] for i in range(1, len(eng_c.cells), 2)]

        a_state = torch.stack([c.hidden.squeeze().detach() for c in a_cells]).mean(dim=0)
        g_state = torch.stack([c.hidden.squeeze().detach() for c in g_cells]).mean(dim=0)

        # PureField: tension = sqrt(|A - G|^2), direction = normalized (A - G)
        diff = a_state - g_state
        tension_magnitude = torch.sqrt((diff ** 2).sum() + 1e-8)
        direction = diff / (tension_magnitude + 1e-8)

        # Bridge output: tension * direction (carries both intensity and orientation)
        c_state = tension_magnitude * direction  # [HIDDEN]

        action, action_logits = will_step_forced(
            will_net, c_state, step, opt_w, 0.0, learn_count, step)
        if action == 0:
            learn_count += 1
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TB-1:Tension'


# ═══ TB-2: Attention Bridge ═══

def run_tb2_attention(cells=256, steps=300):
    """TB-2: Cross-Attention Bridge.
    D attends to C's cells via cross-attention.
    D has a query, C cells are keys/values. No gradient flows to C."""
    eng_c = make_c_engine(cells)

    # Cross-attention: D queries, C keys/values
    n_heads = 4
    head_dim = HIDDEN // n_heads
    W_q = nn.Linear(HIDDEN, HIDDEN, bias=False)  # D's query
    W_k = nn.Linear(HIDDEN, HIDDEN, bias=False)  # C's keys
    W_v = nn.Linear(HIDDEN, HIDDEN, bias=False)  # C's values
    W_o = nn.Linear(HIDDEN, HIDDEN, bias=False)

    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    # D query state (learnable)
    d_state = nn.Parameter(torch.randn(1, HIDDEN) * 0.01)

    opt_d = torch.optim.Adam(
        list(decoder.parameters()) + list(knowledge.parameters()) +
        [d_state] + list(W_q.parameters()) + list(W_o.parameters()), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0
    attn_sample = min(cells, 64)

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)

        # ─── TB-2: Cross-Attention Bridge ───
        # Sample C cells (for memory efficiency)
        indices = list(range(0, len(eng_c.cells), max(1, len(eng_c.cells) // attn_sample)))[:attn_sample]
        C_hidden = torch.stack([eng_c.cells[i].hidden.squeeze(0).detach() for i in indices])  # [N, H]

        # No gradient to C: K, V from detached C
        with torch.no_grad():
            K = W_k(C_hidden).view(len(indices), n_heads, head_dim).transpose(0, 1)  # [heads, N, hd]
            V = W_v(C_hidden).view(len(indices), n_heads, head_dim).transpose(0, 1)

        # D's query (gradient flows through d_state and W_q)
        Q = W_q(d_state).view(1, n_heads, head_dim).transpose(0, 1)  # [heads, 1, hd]

        attn = (Q @ K.transpose(-2, -1)) / math.sqrt(head_dim)
        attn = F.softmax(attn, dim=-1)
        out = (attn @ V).transpose(0, 1).reshape(1, HIDDEN)
        c_state = W_o(out).squeeze(0)  # [HIDDEN]

        action, action_logits = will_step_forced(
            will_net, c_state.detach(), step, opt_w, 0.0, learn_count, step)
        if action == 0:
            learn_count += 1
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TB-2:Attention'


# ═══ TB-3: Bottleneck Bridge ═══

def run_tb3_bottleneck(cells=256, steps=300):
    """TB-3: Information Bottleneck Bridge.
    C -> 8dim -> D. Forces extreme compression.
    Only 8 dimensions pass from C to D -- must carry essence."""
    eng_c = make_c_engine(cells)

    BOTTLENECK_DIM = 8
    # Bottleneck encoder (C side, but no grad to C cells)
    bn_encoder = nn.Linear(HIDDEN, BOTTLENECK_DIM)
    bn_decoder_proj = nn.Linear(BOTTLENECK_DIM, HIDDEN)

    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    opt_d = torch.optim.Adam(
        list(decoder.parameters()) + list(knowledge.parameters()) +
        list(bn_encoder.parameters()) + list(bn_decoder_proj.parameters()), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)

        # ─── TB-3: Bottleneck Bridge ───
        c_raw = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells]).mean(dim=0)

        # Compress: HIDDEN -> 8
        bottleneck = bn_encoder(c_raw.unsqueeze(0))  # [1, 8]
        # Decompress: 8 -> HIDDEN
        c_state = bn_decoder_proj(bottleneck).squeeze(0)  # [HIDDEN]

        action, action_logits = will_step_forced(
            will_net, c_state.detach(), step, opt_w, 0.0, learn_count, step)
        if action == 0:
            learn_count += 1
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TB-3:Bottleneck'


# ═══ TB-4: Broadcast Bridge ═══

def run_tb4_broadcast(cells=256, steps=300):
    """TB-4: Broadcast Bridge.
    C broadcasts top-k most active cells to D globally.
    Activity = L2 norm of hidden. Only top-k cells participate."""
    eng_c = make_c_engine(cells)
    TOP_K = 32  # broadcast only top-32 most active

    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    # Learnable attention weights for broadcast aggregation
    broadcast_attn = nn.Linear(HIDDEN, 1)
    opt_d = torch.optim.Adam(
        list(decoder.parameters()) + list(knowledge.parameters()) +
        list(broadcast_attn.parameters()), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)

        # ─── TB-4: Broadcast Bridge ───
        all_h = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells])  # [N, H]

        # Activity = L2 norm per cell
        activity = all_h.norm(dim=1)  # [N]

        # Top-k selection
        k = min(TOP_K, len(eng_c.cells))
        topk_vals, topk_idx = torch.topk(activity, k)

        # Broadcast: only top-k cells are visible to D
        broadcast_h = all_h[topk_idx]  # [k, H]

        # Weighted aggregation with learnable attention
        attn_scores = broadcast_attn(broadcast_h)  # [k, 1]
        attn_weights = F.softmax(attn_scores, dim=0)  # [k, 1]
        c_state = (broadcast_h * attn_weights).sum(dim=0)  # [H]

        action, action_logits = will_step_forced(
            will_net, c_state.detach(), step, opt_w, 0.0, learn_count, step)
        if action == 0:
            learn_count += 1
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TB-4:Broadcast'


# ═══ TB-5: Resonance Bridge ═══

def run_tb5_resonance(cells=256, steps=300):
    """TB-5: Resonance Bridge (Kuramoto synchronization).
    C and D have oscillators. Communication only when phase-locked.
    Kuramoto model: d(theta_i)/dt = omega_i + K/N * sum(sin(theta_j - theta_i))"""
    eng_c = make_c_engine(cells)

    # Oscillator states for C and D
    n_osc = 16  # number of oscillators per side
    c_theta = torch.randn(n_osc) * 2 * math.pi  # C's phases
    d_theta = torch.randn(n_osc) * 2 * math.pi  # D's phases
    c_omega = torch.randn(n_osc) * 0.5 + 1.0     # C's natural frequencies
    d_omega = torch.randn(n_osc) * 0.5 + 1.0     # D's natural frequencies
    K_coupling = 2.0  # coupling strength

    # Phase-to-hidden projection
    phase_proj = nn.Linear(n_osc, HIDDEN)

    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    opt_d = torch.optim.Adam(
        list(decoder.parameters()) + list(knowledge.parameters()) +
        list(phase_proj.parameters()), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)

        # ─── TB-5: Resonance Bridge (Kuramoto) ───
        # Update C oscillators from cell state variance
        c_raw = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells])
        c_var = c_raw.var(dim=0)[:n_osc]  # use variance as frequency modulation
        c_omega_eff = c_omega + 0.1 * c_var

        # Kuramoto update for C oscillators
        for i in range(n_osc):
            coupling = (K_coupling / n_osc) * torch.sin(c_theta - c_theta[i]).sum()
            c_theta[i] = c_theta[i] + 0.1 * (c_omega_eff[i] + coupling)

        # Kuramoto update for D oscillators (coupling to C)
        for i in range(n_osc):
            # D couples to C oscillators
            coupling_cd = (K_coupling / n_osc) * torch.sin(c_theta - d_theta[i]).sum()
            coupling_dd = (K_coupling / n_osc) * torch.sin(d_theta - d_theta[i]).sum()
            d_theta[i] = d_theta[i] + 0.1 * (d_omega[i] + coupling_cd + 0.5 * coupling_dd)

        # Measure synchronization (order parameter R)
        r_cd = torch.abs(torch.exp(1j * (c_theta - d_theta).to(torch.cfloat)).mean()).item()

        # Bridge output: phase difference modulated by sync strength
        phase_diff = torch.cos(c_theta - d_theta)  # [n_osc], 1 = locked, -1 = anti-locked
        gate = r_cd  # sync strength gates information flow

        # Project phase info to hidden dim, gated by sync
        c_mean = c_raw.mean(dim=0).detach()
        resonance_signal = phase_proj(phase_diff)  # [1, HIDDEN] -> [HIDDEN]
        c_state = gate * resonance_signal.squeeze(0) + (1 - gate) * c_mean  # blend

        action, action_logits = will_step_forced(
            will_net, c_state.detach(), step, opt_w, 0.0, learn_count, step)
        if action == 0:
            learn_count += 1
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), f'TB-5:Resonance(R={r_cd:.2f})'


# ═══ TB-6: Quantum Bridge ═══

def run_tb6_quantum(cells=256, steps=300):
    """TB-6: Quantum Bridge.
    C cells exist in quantum superposition.
    Measurement (Born rule) collapses to classical state for D.
    Entanglement between cells creates correlations that survive measurement."""
    eng_c = make_c_engine(cells)

    # Quantum amplitudes for each cell (complex)
    n_basis = min(cells, 64)  # number of basis states for measurement

    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    # Measurement basis (learnable)
    measure_basis = nn.Linear(HIDDEN, n_basis, bias=False)
    basis_to_hidden = nn.Linear(n_basis, HIDDEN)

    opt_d = torch.optim.Adam(
        list(decoder.parameters()) + list(knowledge.parameters()) +
        list(measure_basis.parameters()) + list(basis_to_hidden.parameters()), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)

        # ─── TB-6: Quantum Bridge ───
        # Step 1: Construct quantum state from C cells
        # Each cell contributes amplitude to superposition
        all_h = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells])  # [N, H]

        # Step 2: Compute amplitudes in measurement basis
        # Project mean state onto measurement basis
        psi = all_h.mean(dim=0)  # [H]
        amplitudes = measure_basis(psi)  # [n_basis]

        # Step 3: Born rule probabilities
        probs = F.softmax(amplitudes ** 2, dim=0)  # |amplitude|^2, normalized

        # Step 4: Measurement (sample from distribution)
        # Use Gumbel-Softmax for differentiable sampling
        if self_training := True:
            # Gumbel-Softmax: differentiable approximation of sampling
            tau = max(0.5, 2.0 - step / steps * 1.5)  # temperature annealing
            gumbel_noise = -torch.log(-torch.log(torch.rand_like(probs) + 1e-8) + 1e-8)
            measured = F.softmax((torch.log(probs + 1e-8) + gumbel_noise) / tau, dim=0)

        # Step 5: Collapse to classical state
        # measured is a probability vector over basis states
        c_state = basis_to_hidden(measured)  # [HIDDEN]

        # Step 6: Add quantum variance (uncertainty principle)
        # Variance of measurement = entropy of probs
        entropy = -(probs * torch.log(probs + 1e-8)).sum()
        quantum_noise = torch.randn(HIDDEN) * (entropy.detach() * 0.01)
        c_state = c_state + quantum_noise

        action, action_logits = will_step_forced(
            will_net, c_state.detach(), step, opt_w, 0.0, learn_count, step)
        if action == 0:
            learn_count += 1
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

    p_iit, p_proxy = measure_phi(eng_c)
    return p_iit, p_proxy, ce.item(), 'TB-6:Quantum'


# ═══ Main ═══

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Trinity Bridge Benchmark')
    parser.add_argument('--cells', type=int, default=256)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--only', nargs='*', help='Run only specified bridges (e.g., TB1 TB3)')
    args = parser.parse_args()

    print(f'{"=" * 72}')
    print(f'  Trinity Bridge Benchmark ({args.cells}c, {args.steps} steps)')
    print(f'  "The bridge determines how consciousness speaks to data."')
    print(f'{"=" * 72}\n')
    print(f"{'Bridge':<28} {'Phi(IIT)':>8} {'Phi(proxy)':>10} {'CE end':>8} {'Time':>6}")
    print('-' * 68)

    all_tests = [
        ('baseline', run_baseline_detach),
        ('TB1', run_tb1_tension),
        ('TB2', run_tb2_attention),
        ('TB3', run_tb3_bottleneck),
        ('TB4', run_tb4_broadcast),
        ('TB5', run_tb5_resonance),
        ('TB6', run_tb6_quantum),
    ]

    if args.only:
        only_set = {s.upper() for s in args.only}
        tests = [(n, f) for n, f in all_tests if n.upper() in only_set or n.upper() == 'BASELINE']
        # Always include baseline for comparison
        if not any(n.upper() == 'BASELINE' for n, _ in tests):
            tests.insert(0, all_tests[0])
    else:
        tests = all_tests

    results = []
    for name, fn in tests:
        torch.manual_seed(42)
        np.random.seed(42)
        t0 = time.time()
        try:
            p_iit, p_proxy, ce, label = fn(cells=args.cells, steps=args.steps)
            elapsed = time.time() - t0
            print(f'{label:<28} {p_iit:>8.2f} {p_proxy:>10.2f} {ce:>8.4f} {elapsed:>5.1f}s')
            results.append((name, label, p_iit, p_proxy, ce, elapsed))
        except Exception as e:
            import traceback

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

            print(f'{name:<28} ERROR: {e}')
            traceback.print_exc()
            results.append((name, name, 0.0, 0.0, 999.0, 0.0))

    # Summary
    print(f'\n{"=" * 72}')
    print('  Summary: ranked by Phi(IIT)')
    print(f'{"=" * 72}')
    ranked = sorted(results, key=lambda r: r[2], reverse=True)
    baseline_phi = next((r[2] for r in results if r[0] == 'baseline'), 1.0)
    for i, (name, label, p_iit, p_proxy, ce, elapsed) in enumerate(ranked, 1):
        boost = p_iit / max(baseline_phi, 0.01)
        marker = ' <-- BEST' if i == 1 else ''
        print(f'  {i}. {label:<26} Phi={p_iit:.2f} (x{boost:.1f}) CE={ce:.4f}{marker}')

    print()
