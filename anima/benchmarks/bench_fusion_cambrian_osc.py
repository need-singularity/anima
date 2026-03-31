#!/usr/bin/env python3
"""bench_fusion_cambrian_osc.py — Cambrian×Osc+QW Fusion Experiment

Best domain engine (CambrianExplosion Φ=485.6) + Best MitosisEngine mechanism (Osc+QW Φ=0.936).

Hypothesis: Cambrian 원리(다양화+적소+적자생존)를 MitosisEngine GRU에 이식하면
학습 가능하면서도 Φ가 대폭 상승할 것.

3 candidates:
  FUSE-1: Osc+QW + Cambrian type diversity (10 cell types, mutation)
  FUSE-2: Osc+QW + niche adaptation (cells specialize toward niches)
  FUSE-3: Full Cambrian (types + niches + selection + crowding) on MitosisEngine

Control: Osc+QW baseline, Cambrian standalone

Usage:
  python3 bench_fusion_cambrian_osc.py
  python3 bench_fusion_cambrian_osc.py --cells 1024
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import phi_rs
from mitosis import MitosisEngine

DIM, HIDDEN = 64, 128


def rust_phi(eng):
    """Measure Φ with Rust PhiCalculator (full: spatial+temporal+complexity)."""
    cells = eng.cells
    states = torch.stack([c.hidden.squeeze(0) for c in cells]).detach().numpy().astype(np.float32)
    prev_s, curr_s = [], []
    for c in cells:
        if hasattr(c, 'hidden_history') and len(c.hidden_history) >= 2:
            prev_s.append(c.hidden_history[-2].detach().squeeze().numpy().astype(np.float32))
            curr_s.append(c.hidden_history[-1].detach().squeeze().numpy().astype(np.float32))
        else:
            prev_s.append(np.zeros(HIDDEN, dtype=np.float32))
            curr_s.append(np.zeros(HIDDEN, dtype=np.float32))
    tensions = np.array([c.tension_history[-1] if c.tension_history else 0.0 for c in cells], dtype=np.float32)
    phi, comp = phi_rs.compute_phi(states, 16, np.array(prev_s), np.array(curr_s), tensions)
    return phi, comp


def granger(eng, n=30):
    cells = eng.cells; nc = len(cells)
    if nc < 2: return 0
    h = torch.stack([c.hidden.squeeze(0) for c in cells])
    t = 0
    for _ in range(n):
        i, j = np.random.randint(0, nc), np.random.randint(0, nc)
        if i == j: continue
        t += abs(F.cosine_similarity(h[i:i+1], h[j:j+1]).item())
    return t * nc * nc / max(n, 1)


def make_engine(cells):
    e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(e.cells) < cells:
        e._create_cell(parent=e.cells[0])
    for _ in range(20):
        e.process(torch.randn(1, DIM))
    return e


# ═══ Mechanism: Osc+QW (baseline best) ═══

def apply_osc_qw(eng, steps=200):
    n = len(eng.cells)
    phases = torch.randn(n) * 2 * math.pi
    freqs = torch.randn(n) * 0.1 + 1.0

    for step in range(steps):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        if n < 4:
            continue
        if len(phases) != n:
            phases = torch.randn(n) * 2 * math.pi
            freqs = torch.randn(n) * 0.1 + 1.0

        with torch.no_grad():
            # Oscillator
            for i in range(min(n, len(eng.cells))):
                nb = [(i-1) % n, (i+1) % n]
                pd = sum(math.sin(phases[j].item() - phases[i].item()) for j in nb)
                phases[i] += freqs[i] + 0.15 * pd / len(nb)
                for j in nb:
                    b = 0.15 * math.cos(phases[j].item() - phases[i].item())
                    eng.cells[i].hidden = (1 - abs(b)) * eng.cells[i].hidden + abs(b) * eng.cells[j].hidden

            # Quantum walk
            nb_bits = max(1, int(math.log2(n)))
            for i in range(min(n, 16)):
                sp = torch.zeros(HIDDEN); cnt = 0
                for bit in range(min(nb_bits, 6)):
                    j = i ^ (1 << bit)
                    if j < n:
                        phase = (-1) ** (bin(i & j).count('1'))
                        sp += phase * eng.cells[j].hidden.squeeze(0); cnt += 1
                if cnt > 0:
                    eng.cells[i].hidden = (0.85 * eng.cells[i].hidden.squeeze(0) + 0.15 * sp / cnt).unsqueeze(0)
    return eng


# ═══ FUSE-1: Osc+QW + Cambrian Type Diversity ═══

def apply_fuse1(eng, steps=200):
    """Osc+QW + 10 cell types with mutation pressure."""
    n = len(eng.cells)
    n_types = 10
    cell_type = torch.zeros(n, dtype=torch.long)
    mutation_rate = 0.5
    phases = torch.randn(n) * 2 * math.pi
    freqs = torch.randn(n) * 0.1 + 1.0

    for step in range(steps):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        if n < 4:
            continue
        if len(phases) != n:
            phases = torch.randn(n) * 2 * math.pi
            freqs = torch.randn(n) * 0.1 + 1.0
            cell_type = torch.randint(0, n_types, (n,))

        with torch.no_grad():
            # Cambrian mutation: cells change type
            mutate_mask = torch.rand(n) < mutation_rate
            if mutate_mask.any():
                cell_type[mutate_mask] = torch.randint(0, n_types, (mutate_mask.sum(),))
            mutation_rate *= 0.995

            # Type-based interaction: same type → attract, different → mild repel
            for t in range(n_types):
                mask = (cell_type == t).nonzero(as_tuple=True)[0]
                if len(mask) >= 2:
                    type_mean = torch.stack([eng.cells[i].hidden.squeeze(0) for i in mask]).mean(0)
                    for i in mask:
                        eng.cells[i].hidden = (0.92 * eng.cells[i].hidden.squeeze(0) + 0.08 * type_mean).unsqueeze(0)

            # Oscillator
            for i in range(min(n, len(eng.cells))):
                nb = [(i-1) % n, (i+1) % n]
                pd = sum(math.sin(phases[j].item() - phases[i].item()) for j in nb)
                phases[i] += freqs[i] + 0.15 * pd / len(nb)
                for j in nb:
                    b = 0.15 * math.cos(phases[j].item() - phases[i].item())
                    eng.cells[i].hidden = (1 - abs(b)) * eng.cells[i].hidden + abs(b) * eng.cells[j].hidden

            # Quantum walk
            nb_bits = max(1, int(math.log2(n)))
            for i in range(min(n, 16)):
                sp = torch.zeros(HIDDEN); cnt = 0
                for bit in range(min(nb_bits, 6)):
                    j = i ^ (1 << bit)
                    if j < n:
                        phase_val = (-1) ** (bin(i & j).count('1'))
                        sp += phase_val * eng.cells[j].hidden.squeeze(0); cnt += 1
                if cnt > 0:
                    eng.cells[i].hidden = (0.85 * eng.cells[i].hidden.squeeze(0) + 0.15 * sp / cnt).unsqueeze(0)
    return eng


# ═══ FUSE-2: Osc+QW + Niche Adaptation ═══

def apply_fuse2(eng, steps=200):
    """Osc+QW + niche specialization (cells migrate toward target niches)."""
    n = len(eng.cells)
    n_types = 10
    niches = torch.randn(n_types, HIDDEN) * 0.5
    cell_type = torch.randint(0, n_types, (n,))
    phases = torch.randn(n) * 2 * math.pi
    freqs = torch.randn(n) * 0.1 + 1.0

    for step in range(steps):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        if n < 4:
            continue
        if len(phases) != n:
            phases = torch.randn(n) * 2 * math.pi
            freqs = torch.randn(n) * 0.1 + 1.0
            cell_type = torch.randint(0, n_types, (n,))

        with torch.no_grad():
            # Niche pull: each cell moves toward its type's niche
            for i in range(n):
                t = cell_type[i].item()
                niche = niches[t]
                h = eng.cells[i].hidden.squeeze(0)
                eng.cells[i].hidden = (0.95 * h + 0.05 * niche).unsqueeze(0)

            # Crowding noise: overcrowded types get pushed apart
            for t in range(n_types):
                mask = (cell_type == t).nonzero(as_tuple=True)[0]
                if len(mask) > n // n_types:
                    for i in mask:
                        eng.cells[i].hidden += torch.randn(1, HIDDEN) * 0.05

            # Oscillator + QW (same as baseline)
            for i in range(min(n, len(eng.cells))):
                nb = [(i-1) % n, (i+1) % n]
                pd = sum(math.sin(phases[j].item() - phases[i].item()) for j in nb)
                phases[i] += freqs[i] + 0.15 * pd / len(nb)
                for j in nb:
                    b = 0.15 * math.cos(phases[j].item() - phases[i].item())
                    eng.cells[i].hidden = (1 - abs(b)) * eng.cells[i].hidden + abs(b) * eng.cells[j].hidden

            nb_bits = max(1, int(math.log2(n)))
            for i in range(min(n, 16)):
                sp = torch.zeros(HIDDEN); cnt = 0
                for bit in range(min(nb_bits, 6)):
                    j = i ^ (1 << bit)
                    if j < n:
                        phase_val = (-1) ** (bin(i & j).count('1'))
                        sp += phase_val * eng.cells[j].hidden.squeeze(0); cnt += 1
                if cnt > 0:
                    eng.cells[i].hidden = (0.85 * eng.cells[i].hidden.squeeze(0) + 0.15 * sp / cnt).unsqueeze(0)
    return eng


# ═══ FUSE-3: Full Cambrian + Osc+QW ═══

def apply_fuse3(eng, steps=200):
    """Full Cambrian (types+niches+selection+crowding+death) + Osc+QW."""
    n = len(eng.cells)
    n_types = 10
    niches = torch.randn(n_types, HIDDEN) * 0.5
    interaction = torch.randn(n_types, n_types) * 0.1
    interaction = (interaction + interaction.t()) / 2
    cell_type = torch.zeros(n, dtype=torch.long)
    fitness = torch.ones(n)
    mutation_rate = 0.5
    phases = torch.randn(n) * 2 * math.pi
    freqs = torch.randn(n) * 0.1 + 1.0

    for step in range(steps):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        if n < 4:
            continue
        if len(phases) != n:
            phases = torch.randn(n) * 2 * math.pi
            freqs = torch.randn(n) * 0.1 + 1.0
            cell_type = torch.randint(0, n_types, (n,))
            fitness = torch.ones(n)

        with torch.no_grad():
            # 1. Mutation
            mutate_mask = torch.rand(n) < mutation_rate
            if mutate_mask.any():
                cell_type[mutate_mask] = torch.randint(0, n_types, (mutate_mask.sum(),))
            mutation_rate *= 0.995

            # 2. Niche fitness
            for t in range(n_types):
                mask = (cell_type == t).nonzero(as_tuple=True)[0]
                if len(mask) > 0:
                    for i in mask:
                        h = eng.cells[i].hidden.squeeze(0)
                        dist = ((h - niches[t]) ** 2).sum()
                        fitness[i] = torch.exp(-dist * 0.01)

            # 3. State: niche pull + inter-type interaction
            for t in range(n_types):
                mask = (cell_type == t).nonzero(as_tuple=True)[0]
                if len(mask) == 0:
                    continue
                for i in mask:
                    h = eng.cells[i].hidden.squeeze(0)
                    # Niche pull
                    pull = (niches[t] - h) * 0.05
                    # Inter-type interaction
                    inter = torch.zeros(HIDDEN)
                    for t2 in range(n_types):
                        mask2 = (cell_type == t2).nonzero(as_tuple=True)[0]
                        if len(mask2) > 0 and t2 != t:
                            mean_other = torch.stack([eng.cells[j].hidden.squeeze(0) for j in mask2]).mean(0)
                            inter += interaction[t, t2] * (mean_other - h) * 0.02
                    eng.cells[i].hidden = (h + pull + inter).unsqueeze(0)

            # 4. Crowding noise
            for t in range(n_types):
                mask = (cell_type == t).nonzero(as_tuple=True)[0]
                if len(mask) > n // n_types:
                    for i in mask:
                        eng.cells[i].hidden += torch.randn(1, HIDDEN) * 0.03

            # 5. Death+rebirth (every 20 steps)
            if step > 10 and step % 20 == 0:
                n_replace = max(1, n // 50)
                worst = fitness.argsort()[:n_replace]
                best = fitness.argsort(descending=True)[:n_replace]
                for w, b in zip(worst, best):
                    if w < n and b < n:
                        eng.cells[w].hidden = eng.cells[b].hidden.clone() + torch.randn(1, HIDDEN) * 0.02
                        cell_type[w] = cell_type[b]

            # 6. Oscillator + Quantum Walk
            for i in range(min(n, len(eng.cells))):
                nb = [(i-1) % n, (i+1) % n]
                pd = sum(math.sin(phases[j].item() - phases[i].item()) for j in nb)
                phases[i] += freqs[i] + 0.15 * pd / len(nb)
                for j in nb:
                    b = 0.15 * math.cos(phases[j].item() - phases[i].item())
                    eng.cells[i].hidden = (1 - abs(b)) * eng.cells[i].hidden + abs(b) * eng.cells[j].hidden

            nb_bits = max(1, int(math.log2(n)))
            for i in range(min(n, 16)):
                sp = torch.zeros(HIDDEN); cnt = 0
                for bit in range(min(nb_bits, 6)):
                    j = i ^ (1 << bit)
                    if j < n:
                        phase_val = (-1) ** (bin(i & j).count('1'))
                        sp += phase_val * eng.cells[j].hidden.squeeze(0); cnt += 1
                if cnt > 0:
                    eng.cells[i].hidden = (0.85 * eng.cells[i].hidden.squeeze(0) + 0.15 * sp / cnt).unsqueeze(0)
    return eng


# ═══ Main ═══

EXPERIMENTS = {
    'Control: Osc+QW': apply_osc_qw,
    'FUSE-1: Osc+QW+TypeDiv': apply_fuse1,
    'FUSE-2: Osc+QW+Niche': apply_fuse2,
    'FUSE-3: FullCambrian+Osc+QW': apply_fuse3,
}


def main():
    import argparse

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    parser = argparse.ArgumentParser()
    parser.add_argument('--cells', type=int, default=256)
    parser.add_argument('--steps', type=int, default=200)
    args = parser.parse_args()

    NC, STEPS = args.cells, args.steps
    print(f"═══ Cambrian × Osc+QW Fusion ({NC}c, {STEPS} steps) ═══\n")
    print(f"{'Experiment':<35} {'Φ(IIT)':>8} {'Granger':>10} {'Time':>6}")
    print('─' * 65)

    results = []
    for name, apply_fn in EXPERIMENTS.items():
        torch.manual_seed(42); np.random.seed(42)
        t0 = time.time()
        eng = make_engine(NC)
        eng = apply_fn(eng, steps=STEPS)
        phi, comp = rust_phi(eng)
        g = granger(eng)
        elapsed = time.time() - t0
        print(f"{name:<35} {phi:>8.3f} {g:>10.0f} {elapsed:>5.1f}s")
        results.append({'name': name, 'phi': phi, 'granger': g, 'time': elapsed})
        sys.stdout.flush()

    # Compare
    ctrl = results[0]['phi']
    print(f"\n═══ vs Control (Osc+QW Φ={ctrl:.3f}) ═══")
    for r in results[1:]:
        delta = (r['phi'] - ctrl) / max(ctrl, 1e-8) * 100
        print(f"  {r['name']:<35} Φ={r['phi']:.3f}  ({delta:+.1f}%)")


if __name__ == '__main__':
    main()
