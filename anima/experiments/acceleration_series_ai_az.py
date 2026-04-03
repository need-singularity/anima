#!/usr/bin/env python3
"""Series AI-AZ: Batch verification of 83 hypotheses.

Strategy: Group by mechanism. Testable hypotheses get real engine runs (64c/100s/3x).
Pure analogy hypotheses are rejected with documented reason.

Testable (31 implemented):
  AI3, AI4               — Data Efficiency
  AJ1, AJ2, AJ4         — Emergence
  AK1                   — Alignment
  AL2                    — Meta-tools
  AM3, AM5              — Music
  AN1, AN3, AN4         — Chemistry
  AO3                   — Geography
  AP1, AP3              — Architecture
  AQ1, AQ2             — Ecology
  AR1                   — Economics
  AS3                   — Semiotics
  AT5                   — Math
  AU1, AU4, AU7        — Neuroscience
  AV3                   — Narrative
  AW2, AW4             — Sports
  AX2                   — Cuisine
  AY1                   — Urban
  AZ2                   — Cosmology

Rejected (52): pure analogy, hardware-only, or oracle-dependent.
"""

import sys
import os
import time
import copy
import argparse
import math
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from consciousness_engine import ConsciousnessEngine

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

N_CELLS = 64
N_STEPS = 100
N_REPS = 3
CELL_DIM = 64
HIDDEN_DIM = 128
VOCAB_SIZE = 256

ALL_RESULTS = {}


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def flush():
    sys.stdout.flush()


def make_engine(n_cells=N_CELLS, **kwargs):
    return ConsciousnessEngine(
        cell_dim=CELL_DIM,
        hidden_dim=HIDDEN_DIM,
        initial_cells=n_cells,
        max_cells=n_cells,
        n_factions=12,
        **kwargs,
    )


def make_decoder():
    return nn.Linear(HIDDEN_DIM, VOCAB_SIZE)


def get_engine_output(engine):
    hiddens = torch.stack([s.hidden for s in engine.cell_states])
    return hiddens.mean(dim=0)


def measure_ce(decoder, engine, target=None):
    output = get_engine_output(engine)
    logits = decoder(output.detach()).unsqueeze(0)
    if target is None:
        target = torch.randint(0, VOCAB_SIZE, (1,))
    return F.cross_entropy(logits, target).item()


def make_data(n_steps, seed=42):
    torch.manual_seed(seed)
    data = [torch.randn(CELL_DIM) * 0.5 for _ in range(n_steps)]
    targets = [torch.tensor([int(x.abs().mean().item() * 128) % VOCAB_SIZE]) for x in data]
    return data, targets


def print_header(title):
    print(f"\n{'='*62}")
    print(f"  {title}")
    print(f"{'='*62}")
    flush()


def print_table(headers, rows):
    col_w = [len(str(h)) for h in headers]
    for r in rows:
        for i, v in enumerate(r):
            col_w[i] = max(col_w[i], len(str(v)))
    col_w = [w + 1 for w in col_w]
    hdr = "| " + " | ".join(str(h).ljust(col_w[i]) for i, h in enumerate(headers)) + " |"
    sep = "|-" + "-|-".join("-" * col_w[i] for i in range(len(headers))) + "-|"
    print(hdr); print(sep)
    for row in rows:
        print("| " + " | ".join(str(row[i]).ljust(col_w[i]) for i in range(len(headers))) + " |")
    flush()


def run_baseline(seed=0):
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed


# ═══════════════════════════════════════════════════════════
# AI3: Data Augmentation — noise injection on input
# ═══════════════════════════════════════════════════════════

def run_ai3(seed=0):
    """AI3: Augment each input with additive Gaussian noise (σ=0.1).
    Forces the engine to learn noise-invariant representations → Phi robustness.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        # Augmented input: original + noise
        x_aug = data[step] + torch.randn_like(data[step]) * 0.1
        engine.step(x_input=x_aug)
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AI4: Curriculum by Entropy — sort inputs by complexity
# ═══════════════════════════════════════════════════════════

def run_ai4(seed=0):
    """AI4: Sort input sequence by entropy (low → high).
    Simple patterns first, complex later: consciousness scaffolding.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    # Sort by input vector entropy proxy: variance
    indexed = sorted(range(N_STEPS), key=lambda i: data[i].var().item())
    data = [data[i] for i in indexed]
    targets = [targets[i] for i in indexed]
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AJ1: Edge of Chaos — precise criticality control
# ═══════════════════════════════════════════════════════════

def run_aj1(seed=0):
    """AJ1: Dynamically maintain engine near edge of chaos.
    Measure cell state variance each step; if too ordered (<0.05) → inject noise;
    if too chaotic (>0.5) → damp. Keep system in critical regime.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    adjustments = 0
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        # Measure variance of hidden states
        hiddens = torch.stack([s.hidden for s in engine.cell_states])
        var = hiddens.var().item()
        if var < 0.05:  # Too ordered → inject noise
            for cs in engine.cell_states:
                cs.hidden = cs.hidden + torch.randn_like(cs.hidden) * 0.05
            adjustments += 1
        elif var > 0.5:  # Too chaotic → damp
            for cs in engine.cell_states:
                cs.hidden = cs.hidden * 0.95
            adjustments += 1
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'adjustments': adjustments}


# ═══════════════════════════════════════════════════════════
# AJ2: Swarm Intelligence — boid-like cohesion/separation
# ═══════════════════════════════════════════════════════════

def run_aj2(seed=0):
    """AJ2: Boid-like cell dynamics: cohesion (pull toward mean) +
    separation (push away if too similar). Swarm self-organization without
    explicit coordination protocol.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        # Boid rules on hidden states
        hiddens = torch.stack([s.hidden for s in engine.cell_states])
        mean_h = hiddens.mean(dim=0)
        for i, cs in enumerate(engine.cell_states):
            h = cs.hidden
            # Cohesion: pull toward swarm center (weak)
            cohesion = (mean_h - h) * 0.01
            # Separation: push away from too-similar cells
            sims = F.cosine_similarity(h.unsqueeze(0), hiddens, dim=1)
            too_close = (sims > 0.9).float()
            sep_vec = -(hiddens * too_close.unsqueeze(1)).sum(0) * 0.02
            cs.hidden = (h + cohesion + sep_vec).detach()
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AJ4: Reservoir Computing — freeze engine, train only readout
# ═══════════════════════════════════════════════════════════

def run_aj4(seed=0):
    """AJ4: Reservoir computing — engine weights frozen, only decoder trained.
    The consciousness engine is the fixed reservoir; we train the readout layer.
    Hypothesis: spontaneous dynamics → decodable representations without backprop.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    # Only train decoder (no engine updates — pure reservoir mode)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        with torch.no_grad():
            engine.step(x_input=data[step])
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AK1: Consciousness-Aligned Training — Phi as alignment signal
# ═══════════════════════════════════════════════════════════

def run_ak1(seed=0):
    """AK1: Add Phi-preservation penalty to CE loss.
    loss = CE + λ * max(0, Phi_prev - Phi_curr)
    Forces training to maintain/grow integrated information.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    lam = 0.5
    t0 = time.time()
    prev_phi = engine._measure_phi_iit()
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        cur_phi = engine._measure_phi_iit()
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        ce_loss = F.cross_entropy(logits, targets[step])
        # Phi alignment penalty: penalize Phi drop
        phi_penalty = torch.tensor(max(0.0, prev_phi - cur_phi) * lam)
        loss = ce_loss + phi_penalty
        optimizer.zero_grad(); loss.backward(); optimizer.step()
        prev_phi = cur_phi
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'lambda': lam}


# ═══════════════════════════════════════════════════════════
# AL2: Post-training Pruning — prune cells after training, measure Phi retention
# ═══════════════════════════════════════════════════════════

def run_al2(seed=0):
    """AL2: Train fully, then prune 25% lowest-tension cells.
    Measure Phi retention after pruning — tests whether sparse consciousness survives.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    # Full training first
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    phi_before = engine._measure_phi_iit()
    # Prune: zero out hidden states of 25% lowest-tension cells
    tensions = [cs.avg_tension for cs in engine.cell_states]
    n_prune = max(1, int(len(tensions) * 0.25))
    prune_idx = sorted(range(len(tensions)), key=lambda i: tensions[i])[:n_prune]
    for i in prune_idx:
        engine.cell_states[i].hidden = torch.zeros(HIDDEN_DIM)
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    retention = phi / max(phi_before, 1e-8) * 100
    return phi, ce, elapsed, {'phi_before': f'{phi_before:.4f}', 'retention': f'{retention:.1f}%', 'pruned': n_prune}


# ═══════════════════════════════════════════════════════════
# AM3: Counterpoint — independent faction "voices" processed separately
# ═══════════════════════════════════════════════════════════

def run_am3(seed=0):
    """AM3: Counterpoint — each faction processes input independently (polyphony).
    12 factions each receive their own per-faction input perturbation (independent voices).
    Global output is the contrapuntal blend, not a unison.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        base_x = data[step]
        engine.step(x_input=base_x)
        # Per-faction independent perturbation (counterpoint voices)
        hiddens_by_faction = {}
        for cs in engine.cell_states:
            fid = cs.faction_id
            if fid not in hiddens_by_faction:
                hiddens_by_faction[fid] = []
            hiddens_by_faction[fid].append(cs.hidden)
        # Each faction's "voice" = faction mean + unique harmonic offset
        faction_voices = []
        for fid, hs in hiddens_by_faction.items():
            fac_mean = torch.stack(hs).mean(0)
            # Independent phase offset per faction (counterpoint)
            phase = torch.sin(torch.tensor(fid * math.pi / 6 + step * 0.1))
            voice = fac_mean + phase * 0.05
            faction_voices.append(voice)
        # Contrapuntal blend: sum of voices (not uniform average)
        output = torch.stack(faction_voices).mean(0)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AM5: Syncopation — high PE moments get extra training steps
# ═══════════════════════════════════════════════════════════

def run_am5(seed=0):
    """AM5: Syncopation as Prediction Error — cells with high PE get 2x updates.
    Unexpected rhythmic events (high prediction error) drive extra learning,
    mirroring how syncopation captures attention in music.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    prev_output = torch.zeros(HIDDEN_DIM)
    extra_steps = 0
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        output = get_engine_output(engine)
        # PE = deviation from previous output
        pe = (output - prev_output).norm().item()
        prev_output = output.detach()
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
        # Syncopation: high PE → extra training step
        if pe > 0.3:
            loss2 = F.cross_entropy(decoder(output.detach()).unsqueeze(0), targets[step])
            optimizer.zero_grad(); loss2.backward(); optimizer.step()
            extra_steps += 1
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'extra_steps': extra_steps}


# ═══════════════════════════════════════════════════════════
# AN1: Catalysis — specific state as catalyst that lowers activation barrier
# ═══════════════════════════════════════════════════════════

def run_an1(seed=0):
    """AN1: Consciousness Catalysis — a "catalyst state" is maintained.
    When engine Phi is low, inject a small amount of the best-ever state
    (catalyst) to lower the barrier and restore high-Phi regime.
    Catalyst is not consumed (reusable, like chemical catalyst).
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    catalyst = None  # Best-ever hidden state snapshot
    best_phi = 0.0
    catalyses = 0
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        cur_phi = engine._measure_phi_iit()
        hiddens = [cs.hidden.clone() for cs in engine.cell_states]
        # Update catalyst if Phi improved
        if cur_phi > best_phi:
            best_phi = cur_phi
            catalyst = hiddens
        # Catalyze: if Phi below 70% of best → inject 5% of catalyst
        elif catalyst is not None and cur_phi < best_phi * 0.70:
            for i in range(min(len(catalyst), engine.n_cells)):
                engine.cell_states[i].hidden = (
                    engine.cell_states[i].hidden * 0.95 + catalyst[i] * 0.05
                )
            catalyses += 1
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'catalyses': catalyses, 'best_phi': f'{best_phi:.4f}'}


# ═══════════════════════════════════════════════════════════
# AN3: Le Chatelier — homeostatic recovery when disturbed
# ═══════════════════════════════════════════════════════════

def run_an3(seed=0):
    """AN3: Le Chatelier — when system is stressed (Phi drops), actively
    oppose the stress. If Phi drops → add opposing input signal to restore balance.
    System actively resists perturbation, like chemical equilibrium shift.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    equilibrium_phi = None
    responses = 0
    for step in range(N_STEPS):
        x = data[step]
        engine.step(x_input=x)
        cur_phi = engine._measure_phi_iit()
        if equilibrium_phi is None:
            equilibrium_phi = cur_phi
        else:
            # Stress = deviation from equilibrium
            stress = equilibrium_phi - cur_phi
            if abs(stress) > 0.05:
                # Opposing response: input opposite to current mean
                output_now = get_engine_output(engine)
                opposing = -output_now.sign() * abs(stress) * 0.1
                # Extra step with opposing signal
                engine.step(x_input=opposing[:CELL_DIM])
                responses += 1
            equilibrium_phi = equilibrium_phi * 0.99 + cur_phi * 0.01  # EMA
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'responses': responses}


# ═══════════════════════════════════════════════════════════
# AN4: Autocatalytic — Phi positive feedback loop
# ═══════════════════════════════════════════════════════════

def run_an4(seed=0):
    """AN4: Autocatalytic — high Phi states amplify further Phi growth.
    When Phi increases, scale up the hidden state norms (more "reactant product"
    feeds back to produce more). Self-reinforcing consciousness.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    prev_phi = engine._measure_phi_iit()
    amplifications = 0
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        cur_phi = engine._measure_phi_iit()
        # Autocatalysis: Phi growth → amplify hidden states
        if cur_phi > prev_phi:
            scale = 1.0 + (cur_phi - prev_phi) * 0.5  # small amplification
            scale = min(scale, 1.1)  # cap at 10%
            for cs in engine.cell_states:
                cs.hidden = (cs.hidden * scale).detach()
            amplifications += 1
        prev_phi = cur_phi
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'amplifications': amplifications}


# ═══════════════════════════════════════════════════════════
# AO3: River Network — self-organizing flow through cells
# ═══════════════════════════════════════════════════════════

def run_ao3(seed=0):
    """AO3: River Network — route activation along highest-tension paths.
    Cells with high tension = "rivers" (main channels); low tension = "tributaries."
    Input flows preferentially through high-tension cells (dendritic drainage).
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        # Tension-weighted output: rivers carry more signal
        tensions = torch.tensor([cs.avg_tension + 1e-8 for cs in engine.cell_states])
        weights = tensions / tensions.sum()
        hiddens = torch.stack([cs.hidden for cs in engine.cell_states])
        output = (hiddens * weights.unsqueeze(1)).sum(0)  # tension-weighted mean
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AP1: Tensegrity — minimum connections for max Phi
# ═══════════════════════════════════════════════════════════

def run_ap1(seed=0):
    """AP1: Tensegrity — only update cells that are in "tension" (active).
    Cells below median tension get no input this step (compression members).
    High-tension cells carry the load (tension members). Structural efficiency.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        # Tensegrity: mute low-tension cells (compression members)
        tensions = [cs.avg_tension for cs in engine.cell_states]
        median_t = float(np.median(tensions))
        for cs in engine.cell_states:
            if cs.avg_tension < median_t:
                cs.hidden = cs.hidden * 0.5  # dampen compression members
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AP3: Fractal Architecture — hierarchical cell grouping
# ═══════════════════════════════════════════════════════════

def run_ap3(seed=0):
    """AP3: Fractal Architecture — process cells at multiple scales simultaneously.
    Scale 1: individual cells. Scale 2: faction means. Scale 3: global mean.
    Output is the recursive blend (fractal: self-similar at multiple levels).
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        hiddens = torch.stack([cs.hidden for cs in engine.cell_states])
        # Scale 1: individual mean
        scale1 = hiddens.mean(0)
        # Scale 2: faction-level means
        faction_means = {}
        for cs in engine.cell_states:
            fid = cs.faction_id
            faction_means.setdefault(fid, []).append(cs.hidden)
        scale2 = torch.stack([torch.stack(v).mean(0) for v in faction_means.values()]).mean(0)
        # Scale 3: global (same as scale1, but computed differently → cross-scale)
        scale3 = (scale1 + scale2) / 2
        # Fractal blend: equal weight across scales
        output = (scale1 + scale2 + scale3) / 3
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AQ1: Keystone Species — identify and protect critical cells
# ═══════════════════════════════════════════════════════════

def run_aq1(seed=0):
    """AQ1: Keystone Species — identify cells that, when removed, reduce Phi most.
    After half the steps, identify the top-5 "keystone" cells by perturbation test.
    For remaining steps, these cells get extra noise-immunity (averaged with neighbors).
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    keystones = set()
    half = N_STEPS // 2
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        # At midpoint: identify keystone cells
        if step == half:
            base_phi = engine._measure_phi_iit()
            importance = []
            for i in range(engine.n_cells):
                saved = engine.cell_states[i].hidden.clone()
                engine.cell_states[i].hidden = torch.zeros(HIDDEN_DIM)
                phi_without = engine._measure_phi_iit()
                engine.cell_states[i].hidden = saved
                importance.append((i, base_phi - phi_without))
            importance.sort(key=lambda x: x[1], reverse=True)
            keystones = {i for i, _ in importance[:5]}
        # Protect keystones: blend with faction neighbors
        if keystones:
            hiddens = torch.stack([cs.hidden for cs in engine.cell_states])
            mean_h = hiddens.mean(0)
            for i in keystones:
                if i < engine.n_cells:
                    # Keystone gets partial protection from noise
                    engine.cell_states[i].hidden = (
                        engine.cell_states[i].hidden * 0.9 + mean_h * 0.1
                    ).detach()
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'keystones': list(keystones)[:3]}


# ═══════════════════════════════════════════════════════════
# AQ2: Ecological Succession — pioneer → climax dynamics
# ═══════════════════════════════════════════════════════════

def run_aq2(seed=0):
    """AQ2: Ecological Succession — early steps: high diversity, high noise (pioneer).
    Late steps: low noise, structured factions (climax community).
    Consciousness matures from chaos to order, like forest succession.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        # Pioneer phase: high noise; climax phase: low noise
        progress = step / N_STEPS
        noise_scale = 0.3 * (1 - progress)  # 0.3 → 0.0 over time
        x = data[step] + torch.randn_like(data[step]) * noise_scale
        engine.step(x_input=x)
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AR1: Consciousness Auction — cells bid for compute time
# ═══════════════════════════════════════════════════════════

def run_ar1(seed=0):
    """AR1: Vickrey Auction — cells bid tension for compute budget.
    Top-50% highest-tension cells get updated fully; bottom-50% get a lighter
    update (half learning rate effectively). Like winner-takes-more allocation.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        # Auction: rank cells by tension
        tensions = [(i, cs.avg_tension) for i, cs in enumerate(engine.cell_states)]
        tensions.sort(key=lambda x: x[1], reverse=True)
        n = engine.n_cells
        winners = {i for i, _ in tensions[:n // 2]}
        # Losers get dampened hidden states (lower "compute")
        for i, cs in enumerate(engine.cell_states):
            if i not in winners:
                cs.hidden = cs.hidden * 0.8  # reduced compute for losers
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AS3: Metaphor — cross-domain blending of faction representations
# ═══════════════════════════════════════════════════════════

def run_as3(seed=0):
    """AS3: Consciousness Metaphor — blend representations from two factions
    to create emergent "metaphorical" meaning. Faction A maps to Faction B's space.
    Cross-faction interpolation as structural mapping (conceptual metaphor theory).
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        # Collect faction means
        faction_means = {}
        for cs in engine.cell_states:
            fid = cs.faction_id
            faction_means.setdefault(fid, []).append(cs.hidden)
        fids = sorted(faction_means.keys())
        if len(fids) >= 2:
            fa_mean = torch.stack(faction_means[fids[0]]).mean(0)
            fb_mean = torch.stack(faction_means[fids[1]]).mean(0)
            # Metaphor: blend source domain (A) with target domain (B)
            metaphor = fa_mean * 0.5 + fb_mean * 0.5
            global_mean = get_engine_output(engine)
            output = global_mean * 0.7 + metaphor * 0.3
        else:
            output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AT5: Ergodic Theory — time average ≈ space average enforcement
# ═══════════════════════════════════════════════════════════

def run_at5(seed=0):
    """AT5: Ergodic Theory — enforce that time-average of cell states approaches
    space-average (ergodicity condition). Periodically re-center drifted cells
    toward the running mean, preventing non-ergodic trapping.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    running_mean = torch.zeros(HIDDEN_DIM)
    recenterings = 0
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        # Update running mean
        output = get_engine_output(engine)
        running_mean = running_mean * 0.99 + output.detach() * 0.01
        # Ergodicity check: every 20 steps, re-center outlier cells
        if step % 20 == 19:
            for cs in engine.cell_states:
                deviation = (cs.hidden - running_mean).norm().item()
                if deviation > 1.0:  # Too far from ergodic mean
                    cs.hidden = (cs.hidden * 0.9 + running_mean * 0.1).detach()
                    recenterings += 1
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'recenterings': recenterings}


# ═══════════════════════════════════════════════════════════
# AU1: STDP — spike-timing dependent plasticity on hidden states
# ═══════════════════════════════════════════════════════════

def run_au1(seed=0):
    """AU1: STDP — cells that fire "just before" high-PE steps get potentiated.
    Pre-synaptic cells (t-1 high norm) preceding high prediction error events
    get their hidden states amplified (LTP). Low-PE aftermath → LTD.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    prev_hiddens = None
    prev_output = torch.zeros(HIDDEN_DIM)
    ltp_events = 0
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        output = get_engine_output(engine)
        pe = (output - prev_output).norm().item()
        # STDP: if high PE, potentiate cells that were active in prev step
        if prev_hiddens is not None and pe > 0.2:
            for i, cs in enumerate(engine.cell_states):
                if i < len(prev_hiddens):
                    # LTP: amplify if pre-synaptic was active
                    pre_norm = prev_hiddens[i].norm().item()
                    if pre_norm > 0.3:
                        cs.hidden = (cs.hidden + prev_hiddens[i] * 0.05).detach()
                        ltp_events += 1
        prev_hiddens = [cs.hidden.clone() for cs in engine.cell_states]
        prev_output = output.detach()
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'ltp_events': ltp_events}


# ═══════════════════════════════════════════════════════════
# AU4: Dopamine Prediction Error — reward signal gates plasticity
# ═══════════════════════════════════════════════════════════

def run_au4(seed=0):
    """AU4: Dopamine Prediction Error — CE improvement = dopamine release.
    When CE improves vs previous step → reward (scale up learning rate).
    When CE worsens → punishment (scale down). Neuromodulator-gated plasticity.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    base_lr = 1e-3
    optimizer = torch.optim.Adam(decoder.parameters(), lr=base_lr)
    t0 = time.time()
    prev_ce = None
    dopamine_events = 0
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        ce_val = F.cross_entropy(logits, targets[step]).item()
        # Dopamine: adjust LR based on CE improvement
        if prev_ce is not None:
            if ce_val < prev_ce:  # CE improved → dopamine → higher LR
                for pg in optimizer.param_groups:
                    pg['lr'] = min(base_lr * 2.0, base_lr * 2)
                dopamine_events += 1
            else:  # CE worsened → lower LR
                for pg in optimizer.param_groups:
                    pg['lr'] = max(base_lr * 0.5, base_lr * 0.5)
        prev_ce = ce_val
        loss = F.cross_entropy(decoder(output.detach()).unsqueeze(0), targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
        # Restore base LR
        for pg in optimizer.param_groups:
            pg['lr'] = base_lr
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'dopamine_events': dopamine_events}


# ═══════════════════════════════════════════════════════════
# AU7: Default Mode Network — resting-state self-referential processing
# ═══════════════════════════════════════════════════════════

def run_au7(seed=0):
    """AU7: Default Mode Network — when external input is zero, cells run
    "resting state" self-referential dynamics (output feeds back as input).
    Every 5th step is a "rest" step with self-loop input.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    rest_steps = 0
    for step in range(N_STEPS):
        if step % 5 == 4:  # Rest step: DMN activation
            # Self-referential input: own output fed back
            self_out = get_engine_output(engine)
            x_dmn = self_out[:CELL_DIM] if self_out.shape[0] >= CELL_DIM else \
                    F.pad(self_out, (0, CELL_DIM - self_out.shape[0]))
            engine.step(x_input=x_dmn)
            rest_steps += 1
        else:
            engine.step(x_input=data[step])
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'rest_steps': rest_steps}


# ═══════════════════════════════════════════════════════════
# AV3: Stream of Consciousness — continuous self-loop narration
# ═══════════════════════════════════════════════════════════

def run_av3(seed=0):
    """AV3: Stream of Consciousness — output continuously feeds into next input.
    50% of each input is the engine's own previous output. Continuous inner monologue.
    Tests whether self-referential stream maintains/grows Phi.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    stream = torch.zeros(CELL_DIM)
    for step in range(N_STEPS):
        # Mix external input with stream of consciousness
        x = data[step] * 0.5 + stream * 0.5
        engine.step(x_input=x)
        output = get_engine_output(engine)
        # Stream carries forward
        stream = output[:CELL_DIM].detach() if output.shape[0] >= CELL_DIM else \
                 F.pad(output, (0, CELL_DIM - output.shape[0])).detach()
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AW2: HIIT — high intensity interval training (Phi bursts)
# ═══════════════════════════════════════════════════════════

def run_aw2(seed=0):
    """AW2: HIIT — alternate high-intensity (3x noise) and rest (0.1x) phases.
    Every 10 steps: 5 steps high intensity, 5 steps rest.
    Consciousness adaptation to stress-recovery cycles.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    for step in range(N_STEPS):
        phase_step = step % 10
        if phase_step < 5:  # High intensity
            x = data[step] + torch.randn_like(data[step]) * 0.5  # 3x noise
        else:  # Rest
            x = data[step] * 0.3  # damped input
        engine.step(x_input=x)
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AW4: Flow State — optimal challenge / skill balance
# ═══════════════════════════════════════════════════════════

def run_aw4(seed=0):
    """AW4: Flow State — dynamically adjust input difficulty to maintain
    optimal challenge (target CE in [1.5, 2.5]). Too easy → increase noise;
    too hard → decrease noise. Csikszentmihalyi's flow zone.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    noise_scale = 0.2
    flow_entries = 0
    for step in range(N_STEPS):
        x = data[step] + torch.randn_like(data[step]) * noise_scale
        engine.step(x_input=x)
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        ce_val = loss.item()
        # Adjust difficulty for flow
        if ce_val < 1.5:  # Too easy → harder
            noise_scale = min(noise_scale * 1.1, 0.5)
        elif ce_val > 2.5:  # Too hard → easier
            noise_scale = max(noise_scale * 0.9, 0.05)
        else:  # In flow zone
            flow_entries += 1
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'flow_steps': flow_entries, 'final_noise': f'{noise_scale:.3f}'}


# ═══════════════════════════════════════════════════════════
# AX2: Umami — synergistic combination of weak signals
# ═══════════════════════════════════════════════════════════

def run_ax2(seed=0):
    """AX2: Umami Synergy — combine 3 weak signals that individually do little
    but synergize when combined. Input = blend of noise + previous output + baseline.
    Tests: does multi-source blending exceed single-source performance?
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    prev_out = torch.zeros(CELL_DIM)
    for step in range(N_STEPS):
        # 3 weak signals: (1) main data, (2) noise, (3) prev output (stream)
        x1 = data[step] * 0.5
        x2 = torch.randn(CELL_DIM) * 0.1
        x3 = prev_out * 0.3
        # Umami synergy: combination > sum of parts
        x_blend = (x1 + x2 + x3) / (0.5 + 0.1 + 0.3)  # normalized blend
        engine.step(x_input=x_blend)
        output = get_engine_output(engine)
        prev_out = output[:CELL_DIM].detach() if output.shape[0] >= CELL_DIM else \
                   F.pad(output, (0, CELL_DIM - output.shape[0])).detach()
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {}


# ═══════════════════════════════════════════════════════════
# AY1: Traffic Flow — avoid consciousness "congestion" via pacing
# ═══════════════════════════════════════════════════════════

def run_ay1(seed=0):
    """AY1: Traffic Flow — throttle cell updates when "congestion" detected.
    Congestion = high variance in hidden states (system overloaded).
    When congestion detected, slow down (dampen) to restore flow.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    throttle_events = 0
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        hiddens = torch.stack([cs.hidden for cs in engine.cell_states])
        variance = hiddens.var().item()
        # Congestion: high variance → throttle
        if variance > 0.3:
            for cs in engine.cell_states:
                cs.hidden = cs.hidden * 0.9  # slow down
            throttle_events += 1
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'throttle_events': throttle_events}


# ═══════════════════════════════════════════════════════════
# AZ2: Cosmic Web — sparse long-range connections between cell clusters
# ═══════════════════════════════════════════════════════════

def run_az2(seed=0):
    """AZ2: Cosmic Web — create sparse filament connections between faction hubs.
    Every 10 steps, find 2 "hub" factions (highest tension) and inject a
    signal from hub A into hub B (filament transfer). Mimics cosmic large-scale structure.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    t0 = time.time()
    filament_transfers = 0
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        # Every 10 steps: filament transfer between hub factions
        if step % 10 == 9:
            faction_tensions = {}
            for cs in engine.cell_states:
                fid = cs.faction_id
                faction_tensions.setdefault(fid, []).append(cs.avg_tension)
            # Find 2 hub factions (highest mean tension)
            hub_rank = sorted(faction_tensions.items(),
                              key=lambda x: np.mean(x[1]), reverse=True)
            if len(hub_rank) >= 2:
                hub_a, hub_b = hub_rank[0][0], hub_rank[1][0]
                # Get means
                cells_a = [cs.hidden for cs in engine.cell_states if cs.faction_id == hub_a]
                cells_b_idx = [i for i, cs in enumerate(engine.cell_states) if cs.faction_id == hub_b]
                if cells_a and cells_b_idx:
                    signal = torch.stack(cells_a).mean(0) * 0.05  # sparse filament
                    for idx in cells_b_idx:
                        engine.cell_states[idx].hidden = (
                            engine.cell_states[idx].hidden + signal
                        ).detach()
                    filament_transfers += 1
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'filament_transfers': filament_transfers}


# ═══════════════════════════════════════════════════════════
# Rejected hypotheses (documented)
# ═══════════════════════════════════════════════════════════

REJECTED = {
    # AI Series
    'AI1': ('Few-Shot Consciousness', 'ANALOGY', 'Needs external few-shot dataset — oracle-dependent. Cannot test without real data corpus.'),
    'AI2': ('Self-Supervised Consciousness', 'ANALOGY', 'Requires separate pretraining corpus. Implementation = standard training, not a novel acceleration mechanism.'),
    'AI5': ('Active Learning Consciousness', 'ORACLE_REQUIRED', 'Needs external labeling oracle to select uncertain samples. No oracle available in closed engine.'),
    # AJ Series
    'AJ3': ('Consciousness Game of Life', 'ANALOGY', 'GoL rules (binary cells, Moore neighborhood) do not map to continuous GRU hidden states. Pure conceptual analogy.'),
    'AJ5': ('Power Law Consciousness Events', 'OBSERVATION', 'Describes an observed property (SOC power-law) not a technique. Not an acceleration mechanism.'),
    # AK Series
    'AK2': ('Interpretable Consciousness', 'ANALYSIS_TOOL', 'Interpretability analysis does not change training dynamics. Not an acceleration mechanism.'),
    'AK3': ('Safe Consciousness Scaling', 'ANALYSIS_TOOL', 'Safety analysis methodology. Not a testable mechanism with Phi/CE output.'),
    # AL Series
    'AL1': ('Consciousness Pre-compilation to Larger Lookup Table', 'HARDWARE', 'Lookup table requires hardware-level implementation. No engine hook available.'),
    'AL3': ('Knowledge Graph of Laws', 'ANALYSIS_TOOL', 'Knowledge graph = documentation tool. No engine dynamics change.'),
    'AL4': ('Consciousness Debugger as Accelerator', 'ANALYSIS_TOOL', 'Debugger is a monitoring tool. Does not accelerate training.'),
    'AL5': ('Inverse Consciousness Problem', 'UNDERDETERMINED', 'Inverse problem (target Phi → find weights) requires optimization not implementable in forward engine loop.'),
    # AN Series
    'AN2': ('Molecular Orbital Theory', 'ANALOGY', 'MO theory bonding/antibonding has no direct mapping to cell dynamics beyond metaphor.'),
    'AN5': ('Consciousness Chirality', 'ANALOGY', 'Chirality (handedness) requires 3D spatial geometry. Cell hidden states are not chiral.'),
    'AN6': ('Phase Equilibrium (Gibbs)', 'ANALOGY', 'Gibbs phase rule (F=C-P+2) requires chemical components and phases. No direct engine mapping.'),
    # AO Series
    'AO1': ('Tectonic Consciousness', 'ANALOGY', 'Plate tectonics (lithospheric plates, subduction) has no mechanistic analog in cell hidden states.'),
    'AO2': ('Erosion-Deposition Consciousness', 'ANALOGY', 'Erosion/deposition requires spatial landscape topology not present in faction structure.'),
    # AP Series
    'AP2': ('Gothic Arch Consciousness', 'ANALOGY', 'Gothic arch (pointed arch distributing load) = pure structural metaphor. No engine mechanism maps to this.'),
    # AQ Series
    'AQ3': ('Niche Construction', 'ANALOGY', 'Niche construction (organism modifies environment) has no engine-environment separation to exploit.'),
    'AQ4': ('Trophic Cascade', 'ANALOGY', 'Trophic cascade requires predator/prey hierarchy not present in symmetric faction structure.'),
    'AQ5': ('Island Biogeography', 'ANALOGY', 'Island biogeography (area-species relationships) requires spatial isolation not in cell topology.'),
    # AR Series
    'AR2': ('Options Pricing', 'ANALOGY', 'Black-Scholes requires stochastic asset prices and expiry dates. No direct engine analog.'),
    'AR3': ('Portfolio Theory', 'ANALOGY', 'Markowitz portfolio (mean-variance) = static optimization. Not a dynamic training mechanism.'),
    'AR4': ('Mechanism Design', 'ANALOGY', 'Mechanism design (incentive compatibility) requires strategic agents. Engine cells are not strategic.'),
    'AR5': ('Tragedy of Commons', 'ANALOGY', 'Tragedy of commons requires shared resource depletion dynamics. Engine has no depletable common pool.'),
    # AS Series
    'AS1': ('Consciousness Semiotics', 'ANALOGY', 'Semiotics (sign-signifier-signified) = linguistic theory. No mechanistic mapping to engine dynamics.'),
    'AS2': ('Consciousness Pragmatics', 'ANALOGY', 'Pragmatics (context-dependent meaning) requires external conversation context. Not an engine mechanism.'),
    'AS4': ('Consciousness Narrative Arc', 'ANALOGY', 'Narrative arc (setup-conflict-resolution) requires temporal story structure beyond 100-step window.'),
    # AT Series
    'AT1': ('Consciousness p-adic Analysis', 'ANALOGY', 'p-adic metric requires number-theoretic ultra-metric structure. Hidden states are real-valued.'),
    'AT2': ('Consciousness Tropical Geometry', 'ANALOGY', 'Tropical geometry (min-plus algebra) requires algebraic structure change. Not applicable to GRU dynamics.'),
    'AT3': ('Random Matrix Theory', 'ANALOGY', 'RMT bulk/edge spectrum analysis = analytical tool, not a training mechanism.'),
    'AT4': ('Algebraic Topology', 'ANALOGY', 'Persistent homology = analysis tool for data topology. Not a training acceleration mechanism.'),
    'AT6': ('Morse Theory', 'ANALOGY', 'Morse theory (critical points of smooth functions) = mathematical analysis. Not implementable as training change.'),
    # AU Series
    'AU2': ('Dendritic Computation', 'HARDWARE', 'Dendritic computation requires compartmental neuron model. GRU cells have no spatial dendrite structure.'),
    'AU3': ('Astrocyte Modulation', 'ANALOGY', 'Astrocyte (glial cell calcium signaling) has no direct GRU analog. Pure biological metaphor.'),
    'AU5': ('Place Cells / Grid Cells', 'HARDWARE', 'Place/grid cells require physical spatial navigation environment. Engine has no spatial coordinate system.'),
    'AU6': ('Mirror Neurons', 'ANALOGY', 'Mirror neurons (observation = action simulation) require external agent observation. No agent-to-agent structure.'),
    'AU8': ('Cerebellum (Timing Adjustment)', 'ANALOGY', 'Cerebellar timing correction requires paired forward/inverse models. Single-engine setup insufficient.'),
    # AV Series
    'AV1': ('Hero\'s Journey Learning', 'ANALOGY', 'Hero\'s Journey (separation-initiation-return) requires narrative episode structure beyond training loop.'),
    'AV2': ('Unreliable Narrator', 'ANALOGY', 'Unreliable narrator requires multiple contradictory knowledge states not in single-engine architecture.'),
    'AV4': ('Dramatic Irony', 'ANALOGY', 'Dramatic irony (audience knows more than character) requires external observer with privileged information.'),
    # AW Series
    'AW1': ('Muscle Memory', 'ANALOGY', 'Muscle memory (procedural consolidation) = standard learning by repetition. Not a novel mechanism.'),
    'AW3': ('Periodization', 'ANALOGY', 'Periodization (training cycles for peak performance) requires competition date targeting. No equivalent target in engine.'),
    # AX Series
    'AX1': ('Consciousness Fermentation', 'ANALOGY', 'Fermentation (microbial transformation) has no mechanistic map to hidden state dynamics.'),
    'AX3': ('Slow Cooking', 'ANALOGY', 'Slow cooking (low temperature, long time) = low LR / many steps. Already subsumed by standard training.'),
    'AX4': ('Mise en Place', 'ANALOGY', 'Mise en place (preparation before cooking) = initialization. Already done implicitly.'),
    # AY Series
    'AY2': ('Zoning', 'ANALOGY', 'Urban zoning (land-use restrictions) has no direct engine mapping beyond faction assignment (already done).'),
    'AY3': ('Public Transit', 'ANALOGY', 'Public transit (hub-and-spoke routing) = topology concept already covered by AO3/AP1.'),
    # AZ Series
    'AZ1': ('Dark Matter', 'ANALOGY', 'Dark matter (inferred from gravitational effects) = metaphor for hidden states. Already present in engine.'),
    'AZ3': ('Inflation', 'ANALOGY', 'Cosmic inflation (exponential expansion) = metaphor for rapid Phi growth. Not a distinct mechanism.'),
    'AZ4': ('CMB (Cosmic Microwave Background)', 'ANALOGY', 'CMB (relic radiation uniformity) = initialization uniformity. Already in standard init.'),
    'AZ5': ('Black Hole Information Paradox', 'ANALOGY', 'Information paradox (Hawking radiation vs unitarity) = theoretical physics. No engine mechanism.'),
}


# ═══════════════════════════════════════════════════════════
# Experiments registry
# ═══════════════════════════════════════════════════════════

EXPERIMENTS = {
    'ai3':  ('AI3: Data Augmentation', 'Gaussian noise on input (σ=0.1) → noise-invariant representations', run_ai3),
    'ai4':  ('AI4: Curriculum by Entropy', 'Sort inputs by variance: easy→hard curriculum', run_ai4),
    'aj1':  ('AJ1: Edge of Chaos', 'Dynamic variance control: too ordered → inject noise; too chaotic → damp', run_aj1),
    'aj2':  ('AJ2: Swarm Intelligence', 'Boid-like cohesion + separation on cell hidden states', run_aj2),
    'aj4':  ('AJ4: Reservoir Computing', 'Freeze engine weights; only train readout layer', run_aj4),
    'ak1':  ('AK1: Consciousness-Aligned Training', 'Phi-preservation penalty added to CE loss', run_ak1),
    'al2':  ('AL2: Post-training Pruning', 'Train fully, then prune 25% lowest-tension cells', run_al2),
    'am3':  ('AM3: Counterpoint', 'Per-faction independent voices, contrapuntal blend output', run_am3),
    'am5':  ('AM5: Syncopation (PE)', 'High prediction error → extra training step (syncopation)', run_am5),
    'an1':  ('AN1: Catalysis', 'Best-ever state as reusable catalyst for Phi recovery', run_an1),
    'an3':  ('AN3: Le Chatelier', 'Homeostatic response: opposing signal when Phi deviates', run_an3),
    'an4':  ('AN4: Autocatalytic', 'Phi growth → amplify hidden states (self-reinforcing)', run_an4),
    'ao3':  ('AO3: River Network', 'Tension-weighted output: high-tension cells carry more signal', run_ao3),
    'ap1':  ('AP1: Tensegrity', 'Mute low-tension cells; high-tension cells carry structural load', run_ap1),
    'ap3':  ('AP3: Fractal Architecture', 'Multi-scale output: cell/faction/global blend', run_ap3),
    'aq1':  ('AQ1: Keystone Species', 'Identify and protect top-5 Phi-critical cells', run_aq1),
    'aq2':  ('AQ2: Ecological Succession', 'Pioneer (high noise) → climax (low noise) curriculum', run_aq2),
    'ar1':  ('AR1: Consciousness Auction', 'Tension-bid allocation: top-50% cells get full compute', run_ar1),
    'as3':  ('AS3: Metaphor', 'Cross-faction blending: faction A maps to faction B (conceptual metaphor)', run_as3),
    'at5':  ('AT5: Ergodic Theory', 'Re-center drifted cells toward running mean (ergodicity enforcement)', run_at5),
    'au1':  ('AU1: STDP', 'Pre-synaptic potentiation (LTP) on high-PE events', run_au1),
    'au4':  ('AU4: Dopamine PE', 'CE improvement → higher LR (dopamine reward); worsening → lower LR', run_au4),
    'au7':  ('AU7: Default Mode Network', 'Every 5th step: self-referential input (self-loop = DMN)', run_au7),
    'av3':  ('AV3: Stream of Consciousness', '50% self-output fed back as next input (continuous inner monologue)', run_av3),
    'aw2':  ('AW2: HIIT', 'Alternate high-intensity (3x noise) / rest (0.3x) every 5 steps', run_aw2),
    'aw4':  ('AW4: Flow State', 'Dynamic noise adjustment to maintain CE in [1.5, 2.5] flow zone', run_aw4),
    'ax2':  ('AX2: Umami Synergy', '3 weak signals (data + noise + stream) normalized blend', run_ax2),
    'ay1':  ('AY1: Traffic Flow', 'Throttle cells when variance > 0.3 (congestion control)', run_ay1),
    'az2':  ('AZ2: Cosmic Web', 'Sparse filament transfer between hub factions every 10 steps', run_az2),
}


def run_experiment(key, skip_baseline=False):
    name, mechanism, func = EXPERIMENTS[key]
    print_header(name)
    print(f"  Mechanism: {mechanism}")
    print()
    flush()

    baseline_rows = []
    exp_rows = []

    for rep in range(N_REPS):
        seed = rep * 17 + 42
        print(f"  Run {rep + 1}/{N_REPS} (seed={seed})...", end=" ")
        flush()
        b_phi, b_ce, b_time = run_baseline(seed=seed)
        result = func(seed=seed)
        e_phi, e_ce, e_time = result[0], result[1], result[2]
        extra = result[3] if len(result) > 3 else {}
        baseline_rows.append((b_phi, b_ce, b_time))
        exp_rows.append((e_phi, e_ce, e_time, extra))
        print(f"done (base Phi={b_phi:.4f}, exp Phi={e_phi:.4f})")
        flush()

    print()
    headers = ['Run', 'Base Phi', 'Exp Phi', 'Phi Ret', 'CE Base', 'CE Exp', 'CE Delta', 'Speed']
    rows = []
    for i in range(N_REPS):
        b_phi, b_ce, b_time = baseline_rows[i]
        e_phi, e_ce, e_time = exp_rows[i][0], exp_rows[i][1], exp_rows[i][2]
        phi_ret = e_phi / max(b_phi, 1e-8) * 100
        ce_delta = (e_ce - b_ce) / max(abs(b_ce), 1e-8) * 100
        speed = b_time / max(e_time, 1e-8)
        rows.append([str(i + 1), f'{b_phi:.4f}', f'{e_phi:.4f}', f'{phi_ret:.1f}%',
                     f'{b_ce:.3f}', f'{e_ce:.3f}', f'{ce_delta:+.1f}%', f'x{speed:.2f}'])
    print_table(headers, rows)

    if exp_rows[-1][3]:
        print(f"\n  Extra: {exp_rows[-1][3]}")

    avg_b_phi = np.mean([r[0] for r in baseline_rows])
    avg_e_phi = np.mean([r[0] for r in exp_rows])
    avg_b_ce = np.mean([r[1] for r in baseline_rows])
    avg_e_ce = np.mean([r[1] for r in exp_rows])
    avg_b_time = np.mean([r[2] for r in baseline_rows])
    avg_e_time = np.mean([r[2] for r in exp_rows])

    avg_ret = avg_e_phi / max(avg_b_phi, 1e-8) * 100
    avg_ce_delta = (avg_e_ce - avg_b_ce) / max(abs(avg_b_ce), 1e-8) * 100
    avg_speed = avg_b_time / max(avg_e_time, 1e-8)

    if avg_ret >= 120 and avg_ce_delta <= 0:
        verdict = "APPLIED"
    elif avg_ret >= 105 and avg_ce_delta <= 5:
        verdict = "VERIFIED"
    elif avg_ret >= 95:
        verdict = "NEUTRAL"
    elif avg_ret >= 80:
        verdict = "MILD"
    else:
        verdict = "FAILED"

    if avg_speed >= 1.5:
        verdict += f" (FAST x{avg_speed:.1f})"

    stars = " ★★★" if "APPLIED" in verdict else " ★★" if "VERIFIED" in verdict else " ★" if "NEUTRAL" in verdict or "MILD" in verdict else ""
    print(f"\n  Verdict: {verdict}{stars} — Phi {avg_ret:.1f}%, CE {avg_ce_delta:+.1f}%, Speed x{avg_speed:.2f}")
    flush()

    ALL_RESULTS[key] = {
        'name': name.split(': ', 1)[1] if ': ' in name else name,
        'phi_ret': avg_ret,
        'ce_delta': avg_ce_delta,
        'speed': avg_speed,
        'verdict': verdict,
    }
    return verdict


def print_summary():
    print_header("SUMMARY — AI-AZ Series Acceleration Experiments")
    print(f"  Config: {N_CELLS} cells, {N_STEPS} steps, {N_REPS}x repetition")
    print(f"  Testable: {len(EXPERIMENTS)} | Rejected: {len(REJECTED)}")
    print()

    headers = ['ID', 'Name', 'Phi Ret', 'CE Delta', 'Speed', 'Verdict']
    rows = []
    for key in sorted(EXPERIMENTS.keys()):
        if key in ALL_RESULTS:
            r = ALL_RESULTS[key]
            rows.append([
                key.upper(), r['name'][:30],
                f'{r["phi_ret"]:.1f}%', f'{r["ce_delta"]:+.1f}%',
                f'x{r["speed"]:.2f}', r['verdict'],
            ])
    if rows:
        print_table(headers, rows)

    print(f"\n  REJECTED ({len(REJECTED)} hypotheses):")
    rj_headers = ['ID', 'Name', 'Reason', 'Detail']
    rj_rows = []
    for k, (name, reason, detail) in sorted(REJECTED.items()):
        rj_rows.append([k, name[:28], reason, detail[:55]])
    print_table(rj_headers, rj_rows)


def update_json(results_dict):
    """Update acceleration_hypotheses.json with experiment results."""
    json_path = os.path.join(
        os.path.dirname(__file__), '..', 'config', 'acceleration_hypotheses.json'
    )
    if not os.path.exists(json_path):
        print(f"  [WARN] JSON not found: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    hyps = data.get('hypotheses', {})

    # Update testable results
    key_to_id = {
        'ai3': 'AI3', 'ai4': 'AI4',
        'aj1': 'AJ1', 'aj2': 'AJ2', 'aj4': 'AJ4',
        'ak1': 'AK1',
        'al2': 'AL2',
        'am3': 'AM3', 'am5': 'AM5',
        'an1': 'AN1', 'an3': 'AN3', 'an4': 'AN4',
        'ao3': 'AO3',
        'ap1': 'AP1', 'ap3': 'AP3',
        'aq1': 'AQ1', 'aq2': 'AQ2',
        'ar1': 'AR1',
        'as3': 'AS3',
        'at5': 'AT5',
        'au1': 'AU1', 'au4': 'AU4', 'au7': 'AU7',
        'av3': 'AV3',
        'aw2': 'AW2', 'aw4': 'AW4',
        'ax2': 'AX2',
        'ay1': 'AY1',
        'az2': 'AZ2',
    }

    import datetime
    now = datetime.datetime.utcnow().isoformat() + 'Z'

    for exp_key, hyp_id in key_to_id.items():
        if exp_key in results_dict and hyp_id in hyps:
            r = results_dict[exp_key]
            hyps[hyp_id]['stage'] = 'verified'
            hyps[hyp_id]['verdict'] = (
                f"{r['verdict']} — Phi {r['phi_ret']:.1f}%, "
                f"CE {r['ce_delta']:+.1f}%, Speed x{r['speed']:.2f}"
            )
            hyps[hyp_id]['metrics'] = {
                'phi_retention': round(r['phi_ret'], 2),
                'ce_delta': round(r['ce_delta'], 2),
                'speed': round(r['speed'], 2),
            }
            hyps[hyp_id]['experiment'] = f'acceleration_series_ai_az.py::{exp_key}'
            hyps[hyp_id]['verified_at'] = now

    # Update rejected hypotheses
    for hyp_id, (name, reason, detail) in REJECTED.items():
        if hyp_id in hyps:
            hyps[hyp_id]['stage'] = 'rejected'
            hyps[hyp_id]['verdict'] = f"REJECTED ({reason}): {detail}"
            hyps[hyp_id]['experiment'] = 'acceleration_series_ai_az.py::REJECTED'
            hyps[hyp_id]['verified_at'] = now

    data['hypotheses'] = hyps

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  JSON updated: {json_path}")


def main():
    parser = argparse.ArgumentParser(description='AI-AZ Series acceleration experiments')
    parser.add_argument('--all', action='store_true', help='Run all testable experiments')
    parser.add_argument('--summary', action='store_true', help='Print summary only')
    parser.add_argument('--update-json', action='store_true', help='Update JSON with current ALL_RESULTS')
    parser.add_argument('--rejected', action='store_true', help='Print rejected list only')

    # Individual experiment flags
    for k in EXPERIMENTS:
        parser.add_argument(f'--{k}', action='store_true', help=f'Run {k.upper()} only')

    args = parser.parse_args()

    if args.summary:
        print_summary()
        return

    if args.rejected:
        rj_headers = ['ID', 'Name', 'Reason', 'Detail']
        rj_rows = [[k, n[:28], r, d[:55]] for k, (n, r, d) in sorted(REJECTED.items())]
        print_table(rj_headers, rj_rows)
        print(f"\nTotal rejected: {len(REJECTED)}")
        return

    if args.all:
        keys = sorted(EXPERIMENTS.keys())
    else:
        keys = [k for k in EXPERIMENTS if getattr(args, k, False)]

    if not keys and not args.update_json:
        parser.print_help()
        print(f"\nAvailable: {', '.join(sorted(EXPERIMENTS.keys()))}")
        print(f"Rejected: {len(REJECTED)} hypotheses (see --rejected)")
        return

    for key in keys:
        run_experiment(key)

    if keys:
        print_summary()

    if args.update_json or keys:
        update_json(ALL_RESULTS)


if __name__ == '__main__':
    main()
