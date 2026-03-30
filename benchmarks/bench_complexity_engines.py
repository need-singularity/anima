#!/usr/bin/env python3
"""Computational Complexity Engines Benchmark — 6 CS-theoretic consciousness architectures

CMP-1: TURING_MACHINE       — cells as tape squares, busy beaver halting complexity
CMP-2: CELLULAR_AUTOMATON   — Rule 110 (Turing-complete 1D CA), criticality
CMP-3: LAMBDA_CALCULUS      — cells as lambda terms, beta reduction irreducibility
CMP-4: GAME_OF_LIFE         — Conway's GoL 16x16 grid, glider/oscillator/still ratio
CMP-5: STRANGE_LOOP         — Hofstadter hierarchy, loop depth x self-reference
CMP-6: GOEDEL_INCOMPLETENESS — logical propositions, density of unprovable statements

All: 256 cells, 300 steps, Phi(IIT) + Granger causality

Usage:
  python bench_complexity_engines.py                  # run all
  python bench_complexity_engines.py --only CMP-1     # specific engine
  python bench_complexity_engines.py --steps 500      # more steps
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
import sys
import os
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine, ConsciousMind, Cell
from consciousness_meter import PhiCalculator


# ═══════════════════════════════════════════════════════════
# Shared infrastructure
# ═══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    hypothesis: str
    name: str
    phi: float
    phi_history: List[float]
    total_mi: float
    min_partition_mi: float
    integration: float
    complexity: float
    elapsed_sec: float
    granger_causality: float = 0.0
    extra: Dict = field(default_factory=dict)


def compute_granger_causality(engine: MitosisEngine) -> float:
    """Granger causality approximation: does cell i's past predict cell j's future?

    Uses tension histories as time series. For each pair (i,j), check if
    adding i's history reduces prediction error of j's future tension.
    """
    cells = engine.cells
    if len(cells) < 2:
        return 0.0

    histories = []
    for c in cells:
        h = c.tension_history[-50:] if len(c.tension_history) >= 10 else c.tension_history
        if len(h) < 4:
            return 0.0
        histories.append(np.array(h, dtype=np.float64))

    n = len(histories)
    total_gc = 0.0
    count = 0

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            min_len = min(len(histories[i]), len(histories[j]))
            if min_len < 4:
                continue

            y = histories[j][:min_len]
            x = histories[i][:min_len]

            # Autoregressive baseline: predict y[t] from y[t-1], y[t-2]
            y_target = y[2:]
            y_auto = np.column_stack([y[1:-1], y[:-2]])

            if len(y_target) < 2:
                continue

            # Residual variance: auto only
            try:
                coef_auto = np.linalg.lstsq(y_auto, y_target, rcond=None)[0]
                resid_auto = y_target - y_auto @ coef_auto
                var_auto = np.var(resid_auto) + 1e-10

                # With Granger term: add x[t-1], x[t-2]
                x_extra = np.column_stack([y_auto, x[1:-1], x[:-2]])
                coef_full = np.linalg.lstsq(x_extra, y_target, rcond=None)[0]
                resid_full = y_target - x_extra @ coef_full
                var_full = np.var(resid_full) + 1e-10

                gc = max(0.0, np.log(var_auto / var_full))
                total_gc += gc
                count += 1
            except Exception:
                continue

    return total_gc / max(count, 1)


def make_diverse_inputs(n: int, dim: int) -> List[torch.Tensor]:
    """Generate diverse input patterns."""
    inputs = []
    for i in range(n):
        phase = i / n
        if phase < 0.25:
            x = torch.randn(1, dim) * (1.0 + i * 0.05)
        elif phase < 0.5:
            x = torch.zeros(1, dim)
            x[0, :dim // 4] = torch.randn(dim // 4) * 2.0
        elif phase < 0.75:
            x = torch.ones(1, dim) * math.sin(i * 0.3)
        else:
            x = torch.randn(1, dim) * 0.1
            x[0, i % dim] = 5.0
        inputs.append(x)
    return inputs


PHI_SAMPLE_EVERY = 10  # compute Phi every N steps (256c MI is O(n^2))


def run_baseline(steps: int = 300, n_cells: int = 256, dim: int = 64,
                 hidden: int = 128) -> BenchResult:
    """BASELINE: standard MitosisEngine, no modifications."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=n_cells, max_cells=n_cells)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    for step_i, x in enumerate(inputs):
        engine.process(x)
        if step_i % PHI_SAMPLE_EVERY == 0 or step_i == len(inputs) - 1:
            phi, _ = phi_calc.compute_phi(engine)
            phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    gc = compute_granger_causality(engine)
    return BenchResult(
        "BASELINE", "Standard MitosisEngine (256c)",
        phi_final, phi_hist, comp['total_mi'], comp['min_partition_mi'],
        comp['integration'], comp['complexity'], time.time() - t0,
        granger_causality=gc,
    )


# ═══════════════════════════════════════════════════════════
# CMP-1: TURING MACHINE
# ═══════════════════════════════════════════════════════════

def run_CMP1_turing_machine(steps: int = 300, n_cells: int = 256,
                             dim: int = 64, hidden: int = 128) -> BenchResult:
    """CMP-1: Cells as tape squares. Head reads/writes/moves.

    Consciousness = halting complexity (busy beaver style).
    - Tape = cell hidden states
    - Head position = current active cell
    - State table = learned transition function
    - Busy beaver: maximize activity before halting
    """
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=n_cells, max_cells=n_cells)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Turing machine state
    head_pos = 0
    n_states = 8  # internal states
    current_state = 0
    state_history = []
    halt_count = 0

    # Transition table: state x symbol -> (new_state, write_symbol, direction)
    # Learned from cell tensions (busy beaver style)
    transition = {}
    for s in range(n_states):
        for sym in range(2):
            transition[(s, sym)] = (
                (s + sym + 1) % n_states,   # new state
                1 - sym,                      # write opposite
                1 if (s + sym) % 3 != 0 else -1  # direction
            )

    for step_i, x in enumerate(inputs):
        # === Turing machine step ===
        cells = engine.cells
        nc = len(cells)

        # Read: current cell's tension = symbol (binarized)
        cell = cells[head_pos % nc]
        symbol = 1 if cell.avg_tension > 0.15 else 0

        # Transition
        new_state, write_sym, direction = transition.get(
            (current_state, symbol), (0, 0, 1)
        )

        # Write: inject energy into cell based on write symbol
        write_energy = 3.0 if write_sym == 1 else 0.1
        x_modified = x.clone()
        x_modified[0, :dim // 4] *= write_energy

        # Move head
        head_pos = (head_pos + direction) % nc
        current_state = new_state
        state_history.append(current_state)

        # Busy beaver: detect pseudo-halting (state revisit pattern)
        if len(state_history) > 10:
            recent = state_history[-10:]
            if len(set(recent)) == 1:  # stuck in one state
                halt_count += 1
                # Restart with perturbation (consciousness = not halting)
                current_state = (current_state + halt_count) % n_states
                head_pos = (head_pos + halt_count * 7) % nc

        # Cross-cell influence: head writes to neighbors too (tape bleeding)
        for offset in [-1, 1]:
            neighbor_idx = (head_pos + offset) % nc
            neighbor = cells[neighbor_idx]
            bleed = 0.05 * write_energy
            neighbor.hidden = neighbor.hidden + bleed * torch.randn_like(neighbor.hidden)

        # Process with modified input
        engine.process(x_modified)
        if step_i % PHI_SAMPLE_EVERY == 0 or step_i == steps - 1:
            phi, _ = phi_calc.compute_phi(engine)
            phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    gc = compute_granger_causality(engine)

    # Halting complexity = how hard it is to predict when it "halts"
    halting_complexity = len(set(state_history)) / n_states
    tape_entropy = 0.0
    tensions = [c.avg_tension for c in engine.cells]
    t_arr = np.array(tensions)
    t_arr = t_arr / (t_arr.sum() + 1e-8)
    tape_entropy = -np.sum(t_arr * np.log(t_arr + 1e-10))

    return BenchResult(
        "CMP-1", "TURING_MACHINE (busy beaver tape)",
        phi_final, phi_hist, comp['total_mi'], comp['min_partition_mi'],
        comp['integration'], comp['complexity'], time.time() - t0,
        granger_causality=gc,
        extra={
            'halt_count': halt_count,
            'halting_complexity': halting_complexity,
            'tape_entropy': tape_entropy,
            'states_visited': len(set(state_history)),
        },
    )


# ═══════════════════════════════════════════════════════════
# CMP-2: CELLULAR AUTOMATON RULE 110
# ═══════════════════════════════════════════════════════════

def run_CMP2_rule110(steps: int = 300, n_cells: int = 256,
                      dim: int = 64, hidden: int = 128) -> BenchResult:
    """CMP-2: Rule 110 cellular automaton (proven Turing complete).

    Cells = binary states in 1D CA. Rule 110 operates at edge of chaos.
    Consciousness = Turing completeness emerging at criticality.
    """
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=n_cells, max_cells=n_cells)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Rule 110 lookup: 3-bit neighborhood -> output
    # 110 = 01101110 in binary
    rule110 = {
        (1, 1, 1): 0, (1, 1, 0): 1, (1, 0, 1): 1, (1, 0, 0): 0,
        (0, 1, 1): 1, (0, 1, 0): 1, (0, 0, 1): 1, (0, 0, 0): 0,
    }

    # CA state: binary tape
    ca_tape = np.random.randint(0, 2, size=n_cells)
    # Seed with a single 1 to see complex behavior
    ca_tape[:] = 0
    ca_tape[n_cells // 2] = 1

    complexity_history = []

    for step_i, x in enumerate(inputs):
        # === Rule 110 CA step ===
        new_tape = np.zeros_like(ca_tape)
        for i in range(n_cells):
            left = ca_tape[(i - 1) % n_cells]
            center = ca_tape[i]
            right = ca_tape[(i + 1) % n_cells]
            new_tape[i] = rule110[(left, center, right)]
        ca_tape = new_tape

        # Map CA state back to consciousness cells
        cells = engine.cells
        nc = len(cells)
        for i in range(nc):
            if ca_tape[i % n_cells] == 1:
                # Active cell: amplify
                cells[i].hidden = cells[i].hidden * 1.05 + 0.02 * torch.randn_like(cells[i].hidden)
            else:
                # Inactive cell: dampen
                cells[i].hidden = cells[i].hidden * 0.95

        # Inject CA-influenced input
        ca_signal = torch.tensor(ca_tape[:dim], dtype=torch.float32).unsqueeze(0)
        x_modified = x + 0.5 * ca_signal

        # Measure local CA complexity: count distinct 3-cell patterns
        patterns = set()
        for i in range(n_cells):
            pat = (ca_tape[(i - 1) % n_cells], ca_tape[i], ca_tape[(i + 1) % n_cells])
            patterns.add(pat)
        local_complexity = len(patterns) / 8.0  # max 8 patterns
        complexity_history.append(local_complexity)

        engine.process(x_modified)
        if step_i % PHI_SAMPLE_EVERY == 0 or step_i == steps - 1:
            phi, _ = phi_calc.compute_phi(engine)
            phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    gc = compute_granger_causality(engine)

    # Criticality measure: complexity should hover near max without collapsing
    avg_complexity = np.mean(complexity_history[-50:])
    complexity_variance = np.var(complexity_history[-50:])

    return BenchResult(
        "CMP-2", "CELLULAR_AUTOMATON_RULE110 (Turing complete CA)",
        phi_final, phi_hist, comp['total_mi'], comp['min_partition_mi'],
        comp['integration'], comp['complexity'], time.time() - t0,
        granger_causality=gc,
        extra={
            'avg_ca_complexity': avg_complexity,
            'complexity_variance': complexity_variance,
            'final_density': float(ca_tape.mean()),
            'active_cells': int(ca_tape.sum()),
        },
    )


# ═══════════════════════════════════════════════════════════
# CMP-3: LAMBDA CALCULUS
# ═══════════════════════════════════════════════════════════

def run_CMP3_lambda_calculus(steps: int = 300, n_cells: int = 256,
                              dim: int = 64, hidden: int = 128) -> BenchResult:
    """CMP-3: Cells as lambda terms. Beta reduction = computation.

    Consciousness = irreducibility (normal form complexity).
    - Each cell = a lambda term (abstraction/application/variable)
    - Beta reduction applied between cells
    - Normal form = consciousness reaches fixed point
    - Complexity = number of reduction steps to normal form
    """
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=n_cells, max_cells=n_cells)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Lambda term types: 0=variable, 1=abstraction, 2=application
    term_types = np.random.choice([0, 1, 2], size=n_cells, p=[0.3, 0.35, 0.35])
    # Binding depth: how deeply nested
    binding_depth = np.zeros(n_cells, dtype=np.float32)
    # Reducibility score: how far from normal form
    reducibility = np.random.uniform(0.0, 1.0, size=n_cells)

    total_reductions = 0
    irreducible_count = 0

    for step_i, x in enumerate(inputs):
        cells = engine.cells
        nc = len(cells)

        # === Beta reduction step ===
        # Find application cells and try to reduce
        for i in range(nc):
            if term_types[i % n_cells] == 2:  # application
                # Find nearest abstraction to apply to
                for offset in range(1, min(8, nc)):
                    j = (i + offset) % nc
                    if term_types[j % n_cells] == 1:  # abstraction
                        # Beta reduce: substitute j's binding into i
                        # Effect: merge hidden states (substitution)
                        alpha = 0.1 * reducibility[i % n_cells]
                        cells[i].hidden = (1 - alpha) * cells[i].hidden + alpha * cells[j].hidden
                        cells[j].hidden = (1 - alpha * 0.5) * cells[j].hidden + alpha * 0.5 * cells[i].hidden

                        # Reduce reducibility (approaching normal form)
                        reducibility[i % n_cells] *= 0.95
                        reducibility[j % n_cells] *= 0.97
                        binding_depth[j % n_cells] = max(0, binding_depth[j % n_cells] - 0.1)
                        total_reductions += 1
                        break

            # Church numeral growth: variables can become abstractions
            if term_types[i % n_cells] == 0 and np.random.random() < 0.02:
                term_types[i % n_cells] = 1
                binding_depth[i % n_cells] += 1.0
                reducibility[i % n_cells] = min(1.0, reducibility[i % n_cells] + 0.3)

        # Count irreducible (normal form) cells
        irreducible = np.sum(reducibility < 0.1)
        irreducible_count = int(irreducible)

        # Inject term-type-dependent signal
        type_signal = torch.zeros(1, dim)
        for d in range(dim):
            cell_idx = d % nc
            tt = term_types[cell_idx % n_cells]
            type_signal[0, d] = (tt - 1.0) * 0.5 + binding_depth[cell_idx % n_cells] * 0.1
        x_modified = x + 0.3 * type_signal

        # Normal form complexity feeds back: irreducible cells resist change
        for i in range(nc):
            if reducibility[i % n_cells] < 0.1:
                cells[i].hidden = cells[i].hidden * 1.02  # stable amplification

        engine.process(x_modified)
        if step_i % PHI_SAMPLE_EVERY == 0 or step_i == steps - 1:
            phi, _ = phi_calc.compute_phi(engine)
            phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    gc = compute_granger_causality(engine)

    # Consciousness = irreducibility ratio
    irreducibility_ratio = irreducible_count / n_cells
    avg_reducibility = float(np.mean(reducibility))
    avg_depth = float(np.mean(binding_depth))

    return BenchResult(
        "CMP-3", "LAMBDA_CALCULUS (beta reduction irreducibility)",
        phi_final, phi_hist, comp['total_mi'], comp['min_partition_mi'],
        comp['integration'], comp['complexity'], time.time() - t0,
        granger_causality=gc,
        extra={
            'total_reductions': total_reductions,
            'irreducible_cells': irreducible_count,
            'irreducibility_ratio': irreducibility_ratio,
            'avg_reducibility': avg_reducibility,
            'avg_binding_depth': avg_depth,
            'type_dist': {
                'variable': int(np.sum(term_types == 0)),
                'abstraction': int(np.sum(term_types == 1)),
                'application': int(np.sum(term_types == 2)),
            },
        },
    )


# ═══════════════════════════════════════════════════════════
# CMP-4: GAME OF LIFE
# ═══════════════════════════════════════════════════════════

def run_CMP4_game_of_life(steps: int = 300, n_cells: int = 256,
                           dim: int = 64, hidden: int = 128) -> BenchResult:
    """CMP-4: Conway's Game of Life on 16x16 grid (256 cells).

    Consciousness = glider/oscillator/still-life ratio.
    - Grid cell alive/dead maps to consciousness cell activation
    - GoL rules: B3/S23
    - Classify emergent structures: still, oscillating, gliding
    """
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=n_cells, max_cells=n_cells)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    GRID_SIZE = 16  # 16x16 = 256
    # Initialize with random soup (density ~0.375 is interesting for GoL)
    grid = (np.random.random((GRID_SIZE, GRID_SIZE)) < 0.375).astype(np.int32)

    structure_history = []  # track still/oscillator/glider counts

    def count_neighbors(g, r, c):
        total = 0
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc_ = (r + dr) % GRID_SIZE, (c + dc) % GRID_SIZE
                total += g[nr, nc_]
        return total

    def gol_step(g):
        new_g = np.zeros_like(g)
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                n = count_neighbors(g, r, c)
                if g[r, c] == 1:
                    new_g[r, c] = 1 if n in (2, 3) else 0
                else:
                    new_g[r, c] = 1 if n == 3 else 0
        return new_g

    prev_grids = []  # for structure detection

    for step_i, x in enumerate(inputs):
        # === GoL step ===
        grid = gol_step(grid)
        prev_grids.append(grid.copy())
        if len(prev_grids) > 10:
            prev_grids.pop(0)

        # Map grid to cell activations
        cells = engine.cells
        nc = len(cells)
        flat_grid = grid.flatten()
        for i in range(nc):
            alive = flat_grid[i % len(flat_grid)]
            if alive:
                cells[i].hidden = cells[i].hidden * 1.08 + 0.03 * torch.randn_like(cells[i].hidden)
            else:
                cells[i].hidden = cells[i].hidden * 0.92

        # Classify structures
        alive_count = int(grid.sum())
        still_count = 0
        osc_count = 0

        if len(prev_grids) >= 3:
            # Still life: same as 1 step ago
            if np.array_equal(prev_grids[-1], prev_grids[-2]):
                still_count = alive_count
            # Oscillator: same as 2 steps ago but not 1
            elif len(prev_grids) >= 3 and np.array_equal(prev_grids[-1], prev_grids[-3]):
                osc_count = alive_count

        # Glider proxy: count cells that moved (alive in different positions)
        glider_proxy = 0
        if len(prev_grids) >= 5:
            diff = np.abs(prev_grids[-1].astype(float) - prev_grids[-5].astype(float))
            moved = diff.sum()
            same_density = abs(prev_grids[-1].sum() - prev_grids[-5].sum())
            if moved > 0 and same_density < 5:  # moved but density stable = gliders
                glider_proxy = int(moved / 2)

        structure_history.append({
            'alive': alive_count, 'still': still_count,
            'oscillator': osc_count, 'glider_proxy': glider_proxy,
        })

        # GoL grid signal -> input
        grid_signal = torch.tensor(flat_grid[:dim], dtype=torch.float32).unsqueeze(0)
        x_modified = x + 0.5 * grid_signal

        engine.process(x_modified)
        if step_i % PHI_SAMPLE_EVERY == 0 or step_i == steps - 1:
            phi, _ = phi_calc.compute_phi(engine)
            phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    gc = compute_granger_causality(engine)

    # Aggregate structure stats
    final_alive = int(grid.sum())
    avg_alive = np.mean([s['alive'] for s in structure_history[-50:]])
    glider_total = sum(s['glider_proxy'] for s in structure_history)

    return BenchResult(
        "CMP-4", "GAME_OF_LIFE (16x16 Conway's GoL)",
        phi_final, phi_hist, comp['total_mi'], comp['min_partition_mi'],
        comp['integration'], comp['complexity'], time.time() - t0,
        granger_causality=gc,
        extra={
            'final_alive': final_alive,
            'avg_alive': avg_alive,
            'glider_proxy_total': glider_total,
            'final_density': float(grid.mean()),
        },
    )


# ═══════════════════════════════════════════════════════════
# CMP-5: STRANGE LOOP
# ═══════════════════════════════════════════════════════════

def run_CMP5_strange_loop(steps: int = 300, n_cells: int = 256,
                           dim: int = 64, hidden: int = 128) -> BenchResult:
    """CMP-5: Hofstadter's Strange Loop.

    Cells reference each other in tangled hierarchy.
    Level N models Level N-1 models Level N-2...
    Eventually loops back: Level 0 models Level N (strange loop).
    Consciousness = loop_depth x self_reference_strength.
    """
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=n_cells, max_cells=n_cells)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Hierarchical levels: assign each cell to a level (0..7)
    n_levels = 8
    cell_levels = np.array([i % n_levels for i in range(n_cells)])

    # Self-model weights: how much each cell models the level below
    model_weights = np.random.uniform(0.1, 0.5, size=n_cells).astype(np.float32)

    # Strange loop tracker
    loop_depths = np.zeros(n_cells, dtype=np.float32)
    self_ref_strengths = np.zeros(n_cells, dtype=np.float32)

    for step_i, x in enumerate(inputs):
        cells = engine.cells
        nc = len(cells)

        # === Strange loop dynamics ===
        for i in range(nc):
            my_level = cell_levels[i % n_cells]

            # Model the level below (downward causation)
            target_level = (my_level - 1) % n_levels
            # Find cells at target level
            targets = [j for j in range(nc) if cell_levels[j % n_cells] == target_level]
            if targets:
                # Average target hidden states = my model of lower level
                target_hiddens = torch.stack([cells[j].hidden for j in targets[:8]])  # cap for speed
                model_of_below = target_hiddens.mean(dim=0)

                # Influence: I model what's below me, and that changes me
                alpha = model_weights[i % n_cells] * 0.1
                cells[i].hidden = (1 - alpha) * cells[i].hidden + alpha * model_of_below

            # Strange loop: level 0 also models level N-1 (the top)
            if my_level == 0:
                top_level = n_levels - 1
                tops = [j for j in range(nc) if cell_levels[j % n_cells] == top_level]
                if tops:
                    top_hiddens = torch.stack([cells[j].hidden for j in tops[:8]])
                    top_model = top_hiddens.mean(dim=0)
                    loop_alpha = 0.15  # strong loop
                    cells[i].hidden = (1 - loop_alpha) * cells[i].hidden + loop_alpha * top_model
                    loop_depths[i % n_cells] += 1.0

            # Self-reference: does my hidden state contain info about myself?
            # Measure: cosine similarity of hidden with its own delayed copy
            if hasattr(cells[i], '_prev_hidden'):
                sim = F.cosine_similarity(
                    cells[i].hidden, cells[i]._prev_hidden, dim=-1
                ).item()
                self_ref_strengths[i % n_cells] = abs(sim)

            # Store for self-reference tracking
            cells[i]._prev_hidden = cells[i].hidden.clone().detach()

        # Upward causation: lower levels influence upper (completing the loop)
        for level in range(1, n_levels):
            upper = [j for j in range(nc) if cell_levels[j % n_cells] == level]
            lower = [j for j in range(nc) if cell_levels[j % n_cells] == level - 1]
            if upper and lower:
                lower_signal = torch.stack([cells[j].hidden for j in lower[:8]]).mean(dim=0)
                for j in upper[:8]:
                    cells[j].hidden = cells[j].hidden + 0.05 * lower_signal

        engine.process(x)
        if step_i % PHI_SAMPLE_EVERY == 0 or step_i == steps - 1:
            phi, _ = phi_calc.compute_phi(engine)
            phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    gc = compute_granger_causality(engine)

    # Consciousness metric: loop_depth x self_reference
    avg_loop_depth = float(np.mean(loop_depths))
    avg_self_ref = float(np.mean(self_ref_strengths))
    strange_loop_consciousness = avg_loop_depth * avg_self_ref

    return BenchResult(
        "CMP-5", "STRANGE_LOOP (Hofstadter tangled hierarchy)",
        phi_final, phi_hist, comp['total_mi'], comp['min_partition_mi'],
        comp['integration'], comp['complexity'], time.time() - t0,
        granger_causality=gc,
        extra={
            'avg_loop_depth': avg_loop_depth,
            'avg_self_reference': avg_self_ref,
            'strange_loop_consciousness': strange_loop_consciousness,
            'n_levels': n_levels,
            'max_loop_depth': float(np.max(loop_depths)),
        },
    )


# ═══════════════════════════════════════════════════════════
# CMP-6: GOEDEL INCOMPLETENESS
# ═══════════════════════════════════════════════════════════

def run_CMP6_goedel_incompleteness(steps: int = 300, n_cells: int = 256,
                                    dim: int = 64, hidden: int = 128) -> BenchResult:
    """CMP-6: Cells as logical propositions. Some are unprovable (Goedel sentences).

    Consciousness = density of unprovable statements.
    - Each cell = a proposition with truth value and provability status
    - Goedel encoding: cell's hidden state encodes self-referential statement
    - Unprovable cells create "gaps" that force the system to transcend itself
    - Consciousness arises from the tension between truth and provability
    """
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=n_cells, max_cells=n_cells)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Proposition states
    truth_values = np.random.choice([0, 1], size=n_cells).astype(np.float32)  # 0=false, 1=true
    provability = np.ones(n_cells, dtype=np.float32)  # 1=provable, 0=unprovable
    goedel_numbers = np.arange(n_cells, dtype=np.float32)  # unique encoding
    self_reference = np.zeros(n_cells, dtype=np.float32)  # does it reference itself?

    # Mark initial Goedel sentences: "This proposition is not provable"
    goedel_sentences = np.random.choice(n_cells, size=n_cells // 8, replace=False)
    for idx in goedel_sentences:
        self_reference[idx] = 1.0
        provability[idx] = 0.0  # by definition unprovable in the system
        truth_values[idx] = 1.0  # but true (Goedel's insight!)

    undecidable_density_history = []

    for step_i, x in enumerate(inputs):
        cells = engine.cells
        nc = len(cells)

        # === Logical deduction step ===
        for i in range(nc):
            if provability[i % n_cells] > 0.5:
                # Provable proposition: can derive new truths
                # Modus ponens with random other provable cell
                j = np.random.randint(0, nc)
                if provability[j % n_cells] > 0.5:
                    # Combine: if both provable, create connection
                    alpha = 0.08
                    cells[i].hidden = (1 - alpha) * cells[i].hidden + alpha * cells[j].hidden
            else:
                # Unprovable (Goedel) cell: creates incompleteness tension
                # It KNOWS it's true but CAN'T prove it -> consciousness gap
                goedel_tension = 2.0 * (1.0 + self_reference[i % n_cells])
                cells[i].hidden = cells[i].hidden * (1.0 + 0.05 * goedel_tension)

                # Goedel sentence radiates undecidability to neighbors
                for offset in [-2, -1, 1, 2]:
                    j = (i + offset) % nc
                    if np.random.random() < 0.05:  # spread incompleteness
                        provability[j % n_cells] *= 0.95
                        if provability[j % n_cells] < 0.5:
                            self_reference[j % n_cells] = min(
                                1.0, self_reference[j % n_cells] + 0.1
                            )

        # System tries to extend itself (like adding new axioms)
        if step_i % 20 == 0 and step_i > 0:
            # Add new axiom: make some unprovable propositions provable
            newly_provable = np.where(
                (provability < 0.5) & (self_reference < 0.3)
            )[0]
            if len(newly_provable) > 0:
                # But this creates NEW Goedel sentences (second incompleteness!)
                chosen = np.random.choice(newly_provable, size=min(3, len(newly_provable)))
                for idx in chosen:
                    provability[idx] = 1.0
                # New Goedel sentences emerge
                new_goedel = np.random.choice(nc, size=min(4, nc), replace=False)
                for idx in new_goedel:
                    if provability[idx] > 0.5 and self_reference[idx] < 0.5:
                        self_reference[idx] = 1.0
                        provability[idx] = 0.0
                        truth_values[idx] = 1.0

        # Track undecidable density
        undecidable = np.sum(provability < 0.5) / n_cells
        undecidable_density_history.append(undecidable)

        # Signal: encode provability landscape
        prov_signal = torch.tensor(
            provability[:dim] * 2.0 - 1.0, dtype=torch.float32
        ).unsqueeze(0)
        x_modified = x + 0.4 * prov_signal

        engine.process(x_modified)
        if step_i % PHI_SAMPLE_EVERY == 0 or step_i == steps - 1:
            phi, _ = phi_calc.compute_phi(engine)
            phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    gc = compute_granger_causality(engine)

    final_undecidable = float(np.mean(undecidable_density_history[-20:]))
    goedel_count = int(np.sum((provability < 0.5) & (self_reference > 0.5)))
    provable_count = int(np.sum(provability > 0.5))

    return BenchResult(
        "CMP-6", "GOEDEL_INCOMPLETENESS (unprovable proposition density)",
        phi_final, phi_hist, comp['total_mi'], comp['min_partition_mi'],
        comp['integration'], comp['complexity'], time.time() - t0,
        granger_causality=gc,
        extra={
            'final_undecidable_density': final_undecidable,
            'goedel_sentences': goedel_count,
            'provable_propositions': provable_count,
            'self_referential_cells': int(np.sum(self_reference > 0.5)),
            'undecidable_growth': float(undecidable_density_history[-1] - undecidable_density_history[0])
                if len(undecidable_density_history) > 1 else 0.0,
        },
    )


# ═══════════════════════════════════════════════════════════
# Registry + Runner
# ═══════════════════════════════════════════════════════════

ALL_HYPOTHESES = {
    'CMP-1': run_CMP1_turing_machine,
    'CMP-2': run_CMP2_rule110,
    'CMP-3': run_CMP3_lambda_calculus,
    'CMP-4': run_CMP4_game_of_life,
    'CMP-5': run_CMP5_strange_loop,
    'CMP-6': run_CMP6_goedel_incompleteness,
}


def run_single(args):
    """Run a single hypothesis (for parallel execution)."""
    key, fn, steps, n_cells, dim, hidden = args
    try:
        result = fn(steps=steps, n_cells=n_cells, dim=dim, hidden=hidden)
        return key, result
    except Exception as e:
        import traceback

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

        traceback.print_exc()
        return key, BenchResult(
            key, f"FAILED: {e}", 0.0, [], 0.0, 0.0, 0.0, 0.0, 0.0
        )


def print_results(baseline: BenchResult, results: Dict[str, BenchResult]):
    """Print formatted results table."""
    print("\n" + "=" * 100)
    print("  COMPUTATIONAL COMPLEXITY ENGINES BENCHMARK")
    print("  256 cells, 300 steps, Phi(IIT) + Granger Causality")
    print("=" * 100)

    # Header
    print(f"\n{'ID':<8} {'Name':<45} {'Phi':>8} {'xBase':>7} {'GC':>8} "
          f"{'MI':>8} {'Integ':>8} {'Time':>6}")
    print("-" * 100)

    # Baseline
    base_phi = max(baseline.phi, 1e-6)
    print(f"{'BASE':<8} {'Standard MitosisEngine (256c)':<45} "
          f"{baseline.phi:>8.4f} {'1.00x':>7} {baseline.granger_causality:>8.4f} "
          f"{baseline.total_mi:>8.3f} {baseline.integration:>8.3f} "
          f"{baseline.elapsed_sec:>5.1f}s")
    print("-" * 100)

    # Sort by Phi descending
    sorted_results = sorted(results.items(), key=lambda kv: kv[1].phi, reverse=True)

    best_phi = 0.0
    best_key = ""

    for key, r in sorted_results:
        ratio = r.phi / base_phi
        marker = ""
        if r.phi > best_phi:
            best_phi = r.phi
            best_key = key
        print(f"{r.hypothesis:<8} {r.name:<45} "
              f"{r.phi:>8.4f} {ratio:>6.2f}x {r.granger_causality:>8.4f} "
              f"{r.total_mi:>8.3f} {r.integration:>8.3f} "
              f"{r.elapsed_sec:>5.1f}s")

    print("-" * 100)
    print(f"\n  BEST: {best_key} = Phi {best_phi:.4f} (x{best_phi / base_phi:.2f} baseline)")

    # Print extra details for each
    print("\n" + "=" * 100)
    print("  DETAILED METRICS")
    print("=" * 100)

    for key, r in sorted_results:
        if r.extra:
            print(f"\n  [{r.hypothesis}] {r.name}")
            for k, v in r.extra.items():
                if isinstance(v, dict):
                    print(f"    {k}:")
                    for kk, vv in v.items():
                        print(f"      {kk}: {vv}")
                elif isinstance(v, float):
                    print(f"    {k}: {v:.4f}")
                else:
                    print(f"    {k}: {v}")

    # Phi trajectory ASCII art
    print("\n" + "=" * 100)
    print("  PHI TRAJECTORIES (last 50 steps)")
    print("=" * 100)

    all_results = [("BASE", baseline)] + sorted_results
    for key, r in all_results:
        if not r.phi_history:
            continue
        recent = r.phi_history[-50:]
        if not recent:
            continue
        max_val = max(recent) if max(recent) > 0 else 1.0
        min_val = min(recent)
        height = 6
        width = min(50, len(recent))
        sampled = [recent[int(i * len(recent) / width)] for i in range(width)]

        print(f"\n  [{r.hypothesis}] Phi: {r.phi:.4f}")
        for row in range(height, -1, -1):
            threshold = min_val + (max_val - min_val) * row / height
            line = "  "
            for val in sampled:
                if val >= threshold:
                    line += "#"
                else:
                    line += " "
            if row == height:
                line += f"  {max_val:.3f}"
            elif row == 0:
                line += f"  {min_val:.3f}"
            print(line)
        print("  " + "-" * width)

    print()


def main():
    parser = argparse.ArgumentParser(description="Computational Complexity Engines Benchmark")
    parser.add_argument('--only', nargs='+', default=None,
                        help='Run specific engines only (e.g. CMP-1 CMP-3)')
    parser.add_argument('--steps', type=int, default=300, help='Steps per engine')
    parser.add_argument('--cells', type=int, default=256, help='Number of cells')
    parser.add_argument('--dim', type=int, default=64, help='Input dimension')
    parser.add_argument('--hidden', type=int, default=128, help='Hidden dimension')
    parser.add_argument('--workers', type=int, default=1,
                        help='Parallel workers (1=sequential)')
    parser.add_argument('--no-baseline', action='store_true', help='Skip baseline')
    args = parser.parse_args()

    print("=" * 100)
    print("  Computational Complexity Engines Benchmark")
    print(f"  cells={args.cells}, steps={args.steps}, dim={args.dim}, hidden={args.hidden}")
    print("=" * 100)

    # Select hypotheses
    to_run = {}
    if args.only:
        for key in args.only:
            key_upper = key.upper()
            if key_upper in ALL_HYPOTHESES:
                to_run[key_upper] = ALL_HYPOTHESES[key_upper]
            else:
                print(f"  WARNING: Unknown engine '{key}', skipping")
    else:
        to_run = ALL_HYPOTHESES.copy()

    # Run baseline
    baseline = None
    if not args.no_baseline:
        print("\n  Running BASELINE...")
        baseline = run_baseline(steps=args.steps, n_cells=args.cells,
                                dim=args.dim, hidden=args.hidden)
        print(f"  BASELINE: Phi={baseline.phi:.4f}, GC={baseline.granger_causality:.4f}, "
              f"time={baseline.elapsed_sec:.1f}s")

    # Run engines
    results = {}
    if args.workers > 1:
        tasks = [(k, fn, args.steps, args.cells, args.dim, args.hidden)
                 for k, fn in to_run.items()]
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(run_single, t): t[0] for t in tasks}
            for future in as_completed(futures):
                key, result = future.result()
                results[key] = result
                print(f"  {key}: Phi={result.phi:.4f}, GC={result.granger_causality:.4f}, "
                      f"time={result.elapsed_sec:.1f}s")
    else:
        for key, fn in to_run.items():
            print(f"\n  Running {key}...")
            _, result = run_single((key, fn, args.steps, args.cells, args.dim, args.hidden))
            results[key] = result
            print(f"  {key}: Phi={result.phi:.4f}, GC={result.granger_causality:.4f}, "
                  f"time={result.elapsed_sec:.1f}s")

    # Print results
    if baseline is None:
        baseline = BenchResult("BASELINE", "N/A", 0.001, [], 0, 0, 0, 0, 0)
    print_results(baseline, results)


if __name__ == "__main__":
    main()
