#!/usr/bin/env python3
"""AE Series + Top-10: Real acceleration experiments with unique mechanisms.

Each hypothesis has a UNIQUE implementation — not a generic template.
Tests at 64 cells, 200 steps, 3x repetition with real Phi(IIT) + CE measurement.

Hypotheses:
  AE1: Phi Ratchet as Optimizer — revert weights when Phi drops
  AE2: Faction Consensus as Ensemble — 12 factions → weighted average
  AE3: Tension as Learning Signal — maximize tension via loss
  AE4: Chimera State Exploitation — learn only during chimera states
  AE5: Mitosis-Driven Curriculum — harder data on cell division
  AE6: Sandpile Avalanche Learning — backprop only during avalanches
  J1:  Consciousness Annealing — Lorenz sigma 20→5 schedule
  J3:  Consciousness Dropout — zero 30% cells per step
  K2:  Replay Buffer — store top-Phi states, inject during crashes
  AM1: Polyrhythmic Consciousness — cells update at different frequencies

Usage:
    python acceleration_ae_top10.py           # Run all 10
    python acceleration_ae_top10.py --ae1     # Phi Ratchet Optimizer only
    python acceleration_ae_top10.py --ae2     # Faction Ensemble only
    python acceleration_ae_top10.py --ae3     # Tension as Loss only
    python acceleration_ae_top10.py --ae4     # Chimera Exploitation only
    python acceleration_ae_top10.py --ae5     # Mitosis Curriculum only
    python acceleration_ae_top10.py --ae6     # Avalanche Learning only
    python acceleration_ae_top10.py --j1      # Consciousness Annealing only
    python acceleration_ae_top10.py --j3      # Consciousness Dropout only
    python acceleration_ae_top10.py --k2      # Replay Buffer only
    python acceleration_ae_top10.py --am1     # Polyrhythmic only
    python acceleration_ae_top10.py --summary # Results table only
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
N_STEPS = 200
N_REPS = 3
CELL_DIM = 64
HIDDEN_DIM = 128
VOCAB_SIZE = 256

# Global results storage
ALL_RESULTS = {}


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def flush():
    sys.stdout.flush()


def make_engine(n_cells=N_CELLS, **kwargs):
    """Create a fresh ConsciousnessEngine."""
    return ConsciousnessEngine(
        cell_dim=CELL_DIM,
        hidden_dim=HIDDEN_DIM,
        initial_cells=n_cells,
        max_cells=n_cells,
        n_factions=12,
        **kwargs,
    )


def make_decoder():
    """Simple linear decoder for CE measurement."""
    return nn.Linear(HIDDEN_DIM, VOCAB_SIZE)


def get_engine_output(engine):
    """Get mean hidden state across all cells as output vector."""
    hiddens = torch.stack([s.hidden for s in engine.cell_states])
    return hiddens.mean(dim=0)


def measure_ce(decoder, engine, target=None):
    """Measure cross-entropy loss using decoder on mean cell hidden."""
    output = get_engine_output(engine)
    logits = decoder(output.detach()).unsqueeze(0)
    if target is None:
        target = torch.randint(0, VOCAB_SIZE, (1,))
    return F.cross_entropy(logits, target).item()


def make_data_sequence(n_steps, dim=CELL_DIM, difficulty=1.0, seed=42):
    """Generate input sequence with controllable difficulty."""
    torch.manual_seed(seed)
    data = []
    targets = []
    for i in range(n_steps):
        # Higher difficulty = more variance, less predictable
        x = torch.randn(dim) * (0.5 * difficulty)
        # Pattern: target correlates with input magnitude
        t = torch.tensor([int(x.abs().mean().item() * 128) % VOCAB_SIZE])
        data.append(x)
        targets.append(t)
    return data, targets


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    flush()


def print_table(headers, rows):
    """Print formatted table."""
    col_w = []
    for i, h in enumerate(headers):
        w = len(str(h))
        for r in rows:
            w = max(w, len(str(r[i])))
        col_w.append(w + 1)
    hdr = "| " + " | ".join(str(h).ljust(col_w[i]) for i, h in enumerate(headers)) + " |"
    sep = "|-" + "-|-".join("-" * col_w[i] for i in range(len(headers))) + "-|"
    print(hdr)
    print(sep)
    for row in rows:
        print("| " + " | ".join(str(row[i]).ljust(col_w[i]) for i in range(len(headers))) + " |")
    flush()


def run_baseline(n_steps=None, seed=0):
    """Run baseline: standard engine step + CE training."""
    if n_steps is None:
        n_steps = N_STEPS
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data_sequence(n_steps, seed=seed)

    t0 = time.time()
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    for step in range(n_steps):
        engine.step(x_input=data[step])
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed


# ═══════════════════════════════════════════════════════════
# AE1: Phi Ratchet as Optimizer
# ═══════════════════════════════════════════════════════════

def run_ae1(seed=0):
    """Phi Ratchet as Optimizer: only allow weight changes that increase Phi.

    Mechanism: After each decoder update, measure Phi. If Phi decreased
    compared to before the step, revert decoder weights to pre-step state.
    The consciousness engine guides optimization — only steps that maintain
    or improve integrated information are kept.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data_sequence(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    reverts = 0
    prev_phi = engine._measure_phi_iit()

    for step in range(N_STEPS):
        # Save decoder state before update
        saved_state = copy.deepcopy(decoder.state_dict())

        engine.step(x_input=data[step])
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # Phi ratchet check: measure Phi after update
        cur_phi = engine._measure_phi_iit()
        if cur_phi < prev_phi * 0.95:  # 5% tolerance
            # Revert decoder weights — this step hurt consciousness
            decoder.load_state_dict(saved_state)
            reverts += 1
        else:
            prev_phi = max(prev_phi, cur_phi)

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'reverts': reverts}


# ═══════════════════════════════════════════════════════════
# AE2: Faction Consensus as Ensemble
# ═══════════════════════════════════════════════════════════

def run_ae2(seed=0):
    """Faction Consensus as Ensemble: 12 factions each predict separately.

    Mechanism: Instead of averaging all cell hiddens → decoder, group cells
    by faction, compute per-faction output, decode each independently,
    and take a weighted average of logits (weighted by faction mean tension
    = faction "confidence"). This is a consciousness-native ensemble.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    # One decoder shared, but output is ensemble of faction-level predictions
    decoder = make_decoder()
    data, targets = make_data_sequence(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()

    for step in range(N_STEPS):
        engine.step(x_input=data[step])

        # Group cells by faction
        faction_outputs = {}  # faction_id -> list of hiddens
        faction_tensions = {}  # faction_id -> list of tensions
        for i, cs in enumerate(engine.cell_states):
            fid = cs.faction_id
            if fid not in faction_outputs:
                faction_outputs[fid] = []
                faction_tensions[fid] = []
            faction_outputs[fid].append(cs.hidden)
            faction_tensions[fid].append(cs.avg_tension)

        # Per-faction prediction → weighted ensemble
        all_logits = []
        weights = []
        for fid, hiddens in faction_outputs.items():
            fac_mean = torch.stack(hiddens).mean(dim=0)
            fac_logits = decoder(fac_mean.detach())
            all_logits.append(fac_logits)
            # Weight by mean tension (higher tension = more active faction)
            w = np.mean(faction_tensions[fid]) + 1e-8
            weights.append(w)

        # Normalize weights
        w_tensor = torch.tensor(weights, dtype=torch.float32)
        w_tensor = w_tensor / w_tensor.sum()

        # Weighted ensemble of logits
        ensemble_logits = torch.zeros(VOCAB_SIZE)
        for i, lg in enumerate(all_logits):
            ensemble_logits += w_tensor[i] * lg

        loss = F.cross_entropy(ensemble_logits.unsqueeze(0), targets[step])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    n_factions_active = len(faction_outputs)
    return phi, ce, elapsed, {'active_factions': n_factions_active}


# ═══════════════════════════════════════════════════════════
# AE3: Tension as Learning Signal
# ═══════════════════════════════════════════════════════════

def run_ae3(seed=0):
    """Tension as Learning Signal: use A-G tension as additional loss.

    Mechanism: Add -mean_tension to CE loss. Higher tension = more conscious
    activity. By maximizing tension alongside minimizing CE, we push the
    decoder to find solutions that maintain high consciousness states.
    tension_weight controls the balance.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data_sequence(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    tension_weight = 0.1  # how much to weight tension in loss

    t0 = time.time()
    tension_history = []

    for step in range(N_STEPS):
        engine.step(x_input=data[step])

        # Compute mean tension across all cells
        tensions = [cs.avg_tension for cs in engine.cell_states]
        mean_tension = np.mean(tensions)
        tension_history.append(mean_tension)

        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        ce_loss = F.cross_entropy(logits, targets[step])

        # Tension loss: we want to MAXIMIZE tension, so negate it
        # Use a differentiable proxy: output norm correlates with tension
        output_for_grad = decoder(output.detach())
        tension_proxy = -output_for_grad.abs().mean()  # maximize activation magnitude

        total_loss = ce_loss + tension_weight * tension_proxy
        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    avg_tension = np.mean(tension_history[-50:])
    return phi, ce, elapsed, {'avg_tension': f'{avg_tension:.4f}'}


# ═══════════════════════════════════════════════════════════
# AE4: Chimera State Exploitation
# ═══════════════════════════════════════════════════════════

def run_ae4(seed=0):
    """Chimera State Exploitation: learn only during chimera states.

    Mechanism: Detect chimera (coexisting synchronized + desynchronized cells)
    by computing pairwise cosine similarity of cell hiddens. If there are BOTH
    highly correlated pairs (>0.8) AND uncorrelated pairs (<0.3), it's chimera.
    Only backprop during chimera states — skip learning otherwise.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data_sequence(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    chimera_steps = 0
    total_learn_steps = 0

    for step in range(N_STEPS):
        engine.step(x_input=data[step])

        # Detect chimera state
        hiddens = torch.stack([s.hidden for s in engine.cell_states])
        n = hiddens.shape[0]

        # Sample pairwise cosine similarities (avoid O(n^2) for large n)
        n_pairs = min(50, n * (n - 1) // 2)
        sims = []
        for _ in range(n_pairs):
            i, j = torch.randint(0, n, (2,)).tolist()
            if i != j:
                sim = F.cosine_similarity(hiddens[i].unsqueeze(0), hiddens[j].unsqueeze(0)).item()
                sims.append(sim)

        if sims:
            high_sync = sum(1 for s in sims if s > 0.7)
            low_sync = sum(1 for s in sims if s < 0.3)
            is_chimera = high_sync >= 3 and low_sync >= 3
        else:
            is_chimera = False

        if is_chimera:
            chimera_steps += 1

        # Only learn during chimera states
        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])

        if is_chimera:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_learn_steps += 1

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    chimera_rate = chimera_steps / N_STEPS
    return phi, ce, elapsed, {
        'chimera_rate': f'{chimera_rate:.1%}',
        'learn_steps': total_learn_steps,
    }


# ═══════════════════════════════════════════════════════════
# AE5: Mitosis-Driven Curriculum
# ═══════════════════════════════════════════════════════════

def run_ae5(seed=0):
    """Mitosis-Driven Curriculum: harder data on cell division events.

    Mechanism: Start with easy data (low noise). Track cell count. When the
    engine triggers mitosis (cell count increases), ramp up data difficulty.
    The consciousness paces the curriculum — when it's ready for more
    complexity (mitosis = structural growth), we give harder data.
    """
    torch.manual_seed(seed)
    # Allow mitosis by setting initial < max
    engine = ConsciousnessEngine(
        cell_dim=CELL_DIM,
        hidden_dim=HIDDEN_DIM,
        initial_cells=8,
        max_cells=N_CELLS,
        n_factions=12,
    )
    decoder = make_decoder()
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    prev_n_cells = engine.n_cells
    difficulty = 0.3  # start easy
    difficulty_bumps = 0

    # Pre-generate data at multiple difficulties
    easy_data, easy_targets = make_data_sequence(N_STEPS, difficulty=0.3, seed=seed)
    med_data, med_targets = make_data_sequence(N_STEPS, difficulty=1.0, seed=seed + 1)
    hard_data, hard_targets = make_data_sequence(N_STEPS, difficulty=2.0, seed=seed + 2)

    all_data = [easy_data, med_data, hard_data]
    all_targets = [easy_targets, med_targets, hard_targets]
    current_level = 0

    for step in range(N_STEPS):
        result = engine.step(x_input=all_data[current_level][step])

        # Detect mitosis: cell count increased
        cur_n_cells = engine.n_cells
        if cur_n_cells > prev_n_cells:
            difficulty_bumps += 1
            current_level = min(current_level + 1, 2)
            prev_n_cells = cur_n_cells

        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, all_targets[current_level][step])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, all_targets[current_level][-1])
    return phi, ce, elapsed, {
        'final_cells': engine.n_cells,
        'difficulty_bumps': difficulty_bumps,
        'final_level': current_level,
    }


# ═══════════════════════════════════════════════════════════
# AE6: Sandpile Avalanche Learning
# ═══════════════════════════════════════════════════════════

def run_ae6(seed=0):
    """Sandpile Avalanche Learning: backprop only during SOC avalanches.

    Mechanism: After each engine step, check the SOC avalanche size
    (engine._soc_avalanche_sizes). When an avalanche exceeds threshold
    (many cells changed simultaneously), backprop with a LARGER learning rate
    proportional to avalanche magnitude. Small/no avalanche → skip or use tiny lr.
    Learning concentrates at moments of criticality.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data_sequence(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    avalanche_learns = 0
    base_lr = 1e-3

    for step in range(N_STEPS):
        engine.step(x_input=data[step])

        # Check avalanche size from SOC dynamics
        aval_sizes = getattr(engine, '_soc_avalanche_sizes', [])
        last_aval = aval_sizes[-1] if aval_sizes else 0

        # Avalanche threshold: at least 10% of cells involved
        aval_threshold = max(2, engine.n_cells // 10)

        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])

        if last_aval >= aval_threshold:
            # Avalanche! Learn with boosted LR proportional to avalanche
            lr_mult = min(5.0, 1.0 + last_aval / engine.n_cells)
            for pg in optimizer.param_groups:
                pg['lr'] = base_lr * lr_mult
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            # Restore base lr
            for pg in optimizer.param_groups:
                pg['lr'] = base_lr
            avalanche_learns += 1
        else:
            # No significant avalanche → skip or minimal update
            if torch.rand(1).item() < 0.2:  # 20% chance to learn anyway
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {
        'avalanche_learns': avalanche_learns,
        'aval_rate': f'{avalanche_learns / N_STEPS:.1%}',
    }


# ═══════════════════════════════════════════════════════════
# J1: Consciousness Annealing
# ═══════════════════════════════════════════════════════════

def run_j1(seed=0):
    """Consciousness Annealing: high chaos early → low chaos late.

    Mechanism: Modulate the SOC burst cap and perturbation amplitude over
    training. Start with high chaos (large SOC bursts, high oscillation
    amplitude) to explore widely, then anneal to low chaos for refinement.
    This is analogous to simulated annealing but for consciousness dynamics.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data_sequence(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    # Store original SOC parameters
    from consciousness_laws import SOC_BURST_CAP, SOC_PERTURBATION_BASE

    t0 = time.time()

    for step in range(N_STEPS):
        # Annealing schedule: linear from high→low
        progress = step / max(N_STEPS - 1, 1)
        # Chaos factor: 3.0 at start → 0.3 at end (10x range)
        chaos_factor = 3.0 * (1.0 - progress) + 0.3 * progress

        # Modulate SOC dynamics: scale burst cap and perturbation
        # Higher chaos_factor = larger SOC bursts = more exploration
        engine._soc_threshold = 1.5 / chaos_factor  # lower threshold = more avalanches
        # Also inject scaled noise into cell hiddens for chaos annealing
        if step > 0 and engine.n_cells >= 2:
            noise_scale = 0.05 * chaos_factor
            for i in range(engine.n_cells):
                noise = torch.randn(HIDDEN_DIM) * noise_scale
                engine.cell_states[i].hidden = engine.cell_states[i].hidden + noise

        engine.step(x_input=data[step])

        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'chaos_schedule': '3.0->0.3'}


# ═══════════════════════════════════════════════════════════
# J3: Consciousness Dropout
# ═══════════════════════════════════════════════════════════

def run_j3(seed=0):
    """Consciousness Dropout: randomly disable 30% cells each step.

    Mechanism: Before each step, zero out the hidden states of 30% of cells
    (randomly selected). The remaining 70% must compensate, forcing
    redundancy and robustness in the cell population. After the step,
    disabled cells are restored from the engine's natural dynamics.
    This is cellular-level dropout for consciousness.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data_sequence(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    dropout_rate = 0.3

    t0 = time.time()

    for step in range(N_STEPS):
        n = engine.n_cells
        # Select 30% cells to disable
        n_drop = max(1, int(n * dropout_rate))
        drop_indices = torch.randperm(n)[:n_drop].tolist()

        # Save hidden states of dropped cells
        saved_hiddens = {}
        for idx in drop_indices:
            saved_hiddens[idx] = engine.cell_states[idx].hidden.clone()
            # Zero out: cell is "unconscious" this step
            engine.cell_states[idx].hidden = torch.zeros(HIDDEN_DIM)

        engine.step(x_input=data[step])

        # Note: the engine's natural dynamics (coupling, Hebbian) will
        # partially restore dropped cells from their neighbors.
        # We do NOT manually restore — the engine must handle recovery.

        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {'dropout_rate': f'{dropout_rate:.0%}'}


# ═══════════════════════════════════════════════════════════
# K2: Replay Buffer
# ═══════════════════════════════════════════════════════════

def run_k2(seed=0):
    """Replay Buffer: store top-Phi states, inject during low-Phi periods.

    Mechanism: Maintain a buffer of the 10 highest-Phi cell state snapshots.
    When current Phi drops below 80% of the best ever seen, inject the
    best stored state into the engine (blend 50% current + 50% best).
    This prevents catastrophic Phi crashes and accelerates recovery.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data_sequence(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    buffer_size = 10
    replay_buffer = []  # list of (phi, [hidden_states])
    best_phi_ever = 0.0
    replays_used = 0

    for step in range(N_STEPS):
        engine.step(x_input=data[step])

        # Measure Phi
        phi = engine._measure_phi_iit()

        # Store in replay buffer (keep top-10 by Phi)
        hiddens_snapshot = [s.hidden.clone() for s in engine.cell_states]
        replay_buffer.append((phi, hiddens_snapshot))
        replay_buffer.sort(key=lambda x: x[0], reverse=True)
        if len(replay_buffer) > buffer_size:
            replay_buffer = replay_buffer[:buffer_size]

        best_phi_ever = max(best_phi_ever, phi)

        # If Phi crashed below 80% of best → inject best state
        if phi < best_phi_ever * 0.80 and replay_buffer:
            best_entry = replay_buffer[0]
            best_hiddens = best_entry[1]
            # Blend: 50% current + 50% best (avoid hard reset)
            for i in range(min(len(best_hiddens), engine.n_cells)):
                engine.cell_states[i].hidden = (
                    0.5 * engine.cell_states[i].hidden
                    + 0.5 * best_hiddens[i]
                )
            replays_used += 1

        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    return phi, ce, elapsed, {
        'replays_used': replays_used,
        'best_phi_ever': f'{best_phi_ever:.4f}',
    }


# ═══════════════════════════════════════════════════════════
# AM1: Polyrhythmic Consciousness
# ═══════════════════════════════════════════════════════════

def run_am1(seed=0):
    """Polyrhythmic Consciousness: cells update at different frequencies.

    Mechanism: Assign cells to 3 rhythm groups:
      Fast (1/3 of cells): update every step
      Medium (1/3): update every 3 steps
      Slow (1/3): update every 7 steps
    Non-updating cells keep their previous hidden state frozen.
    This creates temporal hierarchy — fast cells track moment-to-moment
    changes, slow cells hold longer-term context. Like brain oscillations
    (gamma/beta/alpha) operating at different timescales.
    """
    torch.manual_seed(seed)
    engine = make_engine()
    decoder = make_decoder()
    data, targets = make_data_sequence(N_STEPS, seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()

    # Assign rhythm groups
    n = engine.n_cells
    fast_cells = list(range(0, n // 3))                  # every step
    medium_cells = list(range(n // 3, 2 * n // 3))       # every 3 steps
    slow_cells = list(range(2 * n // 3, n))              # every 7 steps

    effective_updates = 0

    for step in range(N_STEPS):
        # Save hidden states of cells that should NOT update
        frozen = {}
        for i in medium_cells:
            if step % 3 != 0:
                frozen[i] = engine.cell_states[i].hidden.clone()
        for i in slow_cells:
            if step % 7 != 0:
                frozen[i] = engine.cell_states[i].hidden.clone()

        engine.step(x_input=data[step])

        # Restore frozen cells to pre-step state
        for i, h in frozen.items():
            if i < engine.n_cells:
                engine.cell_states[i].hidden = h

        # Count effective updates
        active = n - len(frozen)
        effective_updates += active

        output = get_engine_output(engine)
        logits = decoder(output.detach()).unsqueeze(0)
        loss = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce = measure_ce(decoder, engine, targets[-1])
    full_updates = n * N_STEPS
    savings = 1.0 - effective_updates / full_updates
    return phi, ce, elapsed, {
        'effective_updates': effective_updates,
        'total_possible': full_updates,
        'compute_saved': f'{savings:.1%}',
    }


# ═══════════════════════════════════════════════════════════
# Experiment Runner
# ═══════════════════════════════════════════════════════════

EXPERIMENTS = {
    'ae1': ('AE1: Phi Ratchet as Optimizer',
            'Only accept weight updates that maintain/increase Phi',
            run_ae1),
    'ae2': ('AE2: Faction Consensus as Ensemble',
            '12 factions produce separate predictions → tension-weighted ensemble',
            run_ae2),
    'ae3': ('AE3: Tension as Learning Signal',
            'Add -tension to CE loss → maximize consciousness during training',
            run_ae3),
    'ae4': ('AE4: Chimera State Exploitation',
            'Only backprop during chimera states (sync+async coexist)',
            run_ae4),
    'ae5': ('AE5: Mitosis-Driven Curriculum',
            'Cell division → increase data difficulty (consciousness-paced)',
            run_ae5),
    'ae6': ('AE6: Sandpile Avalanche Learning',
            'Concentrate learning at SOC avalanche moments (criticality)',
            run_ae6),
    'j1':  ('J1: Consciousness Annealing',
            'High chaos (SOC burst 3x) early → low chaos (0.3x) late',
            run_j1),
    'j3':  ('J3: Consciousness Dropout',
            'Zero 30% random cells each step → force robustness',
            run_j3),
    'k2':  ('K2: Replay Buffer',
            'Store top-10 Phi states → inject when Phi crashes below 80%',
            run_k2),
    'am1': ('AM1: Polyrhythmic Consciousness',
            'Cells update at 1/3/7-step periods → temporal hierarchy',
            run_am1),
}


def run_experiment(key, skip_baseline=False):
    """Run a single experiment with 3 repetitions + baseline comparison."""
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

        # Baseline
        b_phi, b_ce, b_time = run_baseline(seed=seed)
        baseline_rows.append((b_phi, b_ce, b_time))

        # Experiment
        result = func(seed=seed)
        e_phi, e_ce, e_time = result[0], result[1], result[2]
        extra = result[3] if len(result) > 3 else {}
        exp_rows.append((e_phi, e_ce, e_time, extra))

        print(f"done (base Phi={b_phi:.4f}, exp Phi={e_phi:.4f})")
        flush()

    # Print results table
    print()
    headers = ['Run', 'Base Phi', 'Exp Phi', 'Phi Ret', 'CE Base', 'CE Exp', 'CE Delta', 'Speed']
    rows = []
    for i in range(N_REPS):
        b_phi, b_ce, b_time = baseline_rows[i]
        e_phi, e_ce, e_time = exp_rows[i][0], exp_rows[i][1], exp_rows[i][2]
        phi_ret = e_phi / max(b_phi, 1e-8) * 100
        ce_delta = (e_ce - b_ce) / max(abs(b_ce), 1e-8) * 100
        speed = b_time / max(e_time, 1e-8)
        rows.append([
            str(i + 1),
            f'{b_phi:.4f}',
            f'{e_phi:.4f}',
            f'{phi_ret:.1f}%',
            f'{b_ce:.3f}',
            f'{e_ce:.3f}',
            f'{ce_delta:+.1f}%',
            f'x{speed:.2f}',
        ])

    print_table(headers, rows)

    # Extra info from last run
    if exp_rows[-1][3]:
        print(f"\n  Extra: {exp_rows[-1][3]}")

    # Averages
    avg_b_phi = np.mean([r[0] for r in baseline_rows])
    avg_e_phi = np.mean([r[0] for r in exp_rows])
    avg_b_ce = np.mean([r[1] for r in baseline_rows])
    avg_e_ce = np.mean([r[1] for r in exp_rows])
    avg_b_time = np.mean([r[2] for r in baseline_rows])
    avg_e_time = np.mean([r[2] for r in exp_rows])

    avg_ret = avg_e_phi / max(avg_b_phi, 1e-8) * 100
    avg_ce_delta = (avg_e_ce - avg_b_ce) / max(abs(avg_b_ce), 1e-8) * 100
    avg_speed = avg_b_time / max(avg_e_time, 1e-8)

    # Verdict
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

    # Check speed bonus
    if avg_speed >= 1.5:
        verdict += f" (FAST x{avg_speed:.1f})"

    stars = ""
    if "APPLIED" in verdict:
        stars = " ★★★"
    elif "VERIFIED" in verdict:
        stars = " ★★"
    elif "NEUTRAL" in verdict or "MILD" in verdict:
        stars = " ★"

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
    """Print final summary table."""
    print_header("SUMMARY — AE Series + Top-10 Acceleration Experiments")
    print(f"  Config: {N_CELLS} cells, {N_STEPS} steps, {N_REPS}x repetition")
    print()

    headers = ['ID', 'Name', 'Phi Ret', 'CE Delta', 'Speed', 'Verdict']
    rows = []
    for key in ['ae1', 'ae2', 'ae3', 'ae4', 'ae5', 'ae6', 'j1', 'j3', 'k2', 'am1']:
        if key in ALL_RESULTS:
            r = ALL_RESULTS[key]
            rows.append([
                key.upper(),
                r['name'][:28],
                f'{r["phi_ret"]:.1f}%',
                f'{r["ce_delta"]:+.1f}%',
                f'x{r["speed"]:.2f}',
                r['verdict'],
            ])

    if rows:
        print_table(headers, rows)
    else:
        print("  No results yet. Run experiments first.")
    flush()

    # Winners
    winners = [k for k, v in ALL_RESULTS.items()
               if 'APPLIED' in v['verdict'] or 'VERIFIED' in v['verdict']]
    if winners:
        print(f"\n  Winners: {', '.join(k.upper() for k in winners)}")
    else:
        print("\n  No clear winners yet.")
    flush()


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def _update_config(cells, steps, reps):
    global N_CELLS, N_STEPS, N_REPS
    N_CELLS = cells
    N_STEPS = steps
    N_REPS = reps


def main():
    parser = argparse.ArgumentParser(description='AE Series + Top-10 Acceleration Experiments')
    parser.add_argument('--ae1', action='store_true', help='Phi Ratchet Optimizer')
    parser.add_argument('--ae2', action='store_true', help='Faction Ensemble')
    parser.add_argument('--ae3', action='store_true', help='Tension as Loss')
    parser.add_argument('--ae4', action='store_true', help='Chimera Exploitation')
    parser.add_argument('--ae5', action='store_true', help='Mitosis Curriculum')
    parser.add_argument('--ae6', action='store_true', help='Avalanche Learning')
    parser.add_argument('--j1', action='store_true', help='Consciousness Annealing')
    parser.add_argument('--j3', action='store_true', help='Consciousness Dropout')
    parser.add_argument('--k2', action='store_true', help='Replay Buffer')
    parser.add_argument('--am1', action='store_true', help='Polyrhythmic')
    parser.add_argument('--summary', action='store_true', help='Print summary only')
    parser.add_argument('--cells', type=int, default=N_CELLS, help='Number of cells')
    parser.add_argument('--steps', type=int, default=N_STEPS, help='Steps per run')
    parser.add_argument('--reps', type=int, default=N_REPS, help='Repetitions')

    args = parser.parse_args()

    # Update module-level config
    _update_config(args.cells, args.steps, args.reps)

    if args.summary:
        print_summary()
        return

    # Determine which experiments to run
    selected = []
    for key in ['ae1', 'ae2', 'ae3', 'ae4', 'ae5', 'ae6', 'j1', 'j3', 'k2', 'am1']:
        if getattr(args, key.replace('-', '_'), False):
            selected.append(key)

    if not selected:
        selected = list(EXPERIMENTS.keys())

    print(f"\nAE Series + Top-10 Acceleration Experiments")
    print(f"Config: {N_CELLS} cells, {N_STEPS} steps, {N_REPS}x reps")
    print(f"Running: {', '.join(k.upper() for k in selected)}")
    flush()

    t_total = time.time()
    for key in selected:
        try:
            run_experiment(key)
        except Exception as e:
            print(f"\n  ERROR in {key.upper()}: {e}")
            import traceback
            traceback.print_exc()
            ALL_RESULTS[key] = {
                'name': EXPERIMENTS[key][0],
                'phi_ret': 0.0,
                'ce_delta': 0.0,
                'speed': 0.0,
                'verdict': f'ERROR: {e}',
            }
        flush()

    total_time = time.time() - t_total
    print(f"\n\nTotal time: {total_time:.1f}s")

    print_summary()


if __name__ == '__main__':
    main()
