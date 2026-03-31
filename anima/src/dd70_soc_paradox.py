#!/usr/bin/env python3
"""DD70: SOC_CRITICAL Paradox -- SOC removal INCREASES Phi at large scale.

DD60 found SOC removal = -9.12 at 8c. But at 256c, SOC removal = +37.7%.
This script systematically tests the scale-dependent SOC effect.

Experiments:
  1. Scale-dependent SOC effect (4c to 256c)
  2. What SOC actually does at large scale (variance, similarity, avalanches)
  3. SOC as noise at scale (gradual strength reduction)
  4. SOC mechanism dissection (which component hurts?)
"""

import sys
import os
import time
import torch
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine

torch.manual_seed(42)
np.random.seed(42)

STEPS = 100
WARMUP = 50


def run_engine(n_cells, steps, disable_soc=False, soc_strength=None):
    """Run engine, return list of phi_iit values after warmup."""
    torch.manual_seed(42)
    engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128,
                                 initial_cells=n_cells, max_cells=n_cells)
    if disable_soc:
        engine._soc_sandpile = lambda: None
    elif soc_strength is not None and soc_strength < 1.0:
        orig_soc = engine._soc_sandpile.__func__
        s = soc_strength

        def attenuated_soc(eng=engine, strength=s):
            saved = [cell.hidden.clone() for cell in eng.cell_states]
            orig_soc(eng)
            for i, cell in enumerate(eng.cell_states):
                cell.hidden = (1.0 - strength) * saved[i] + strength * cell.hidden

        engine._soc_sandpile = attenuated_soc

    phis = []
    for i in range(steps):
        x = torch.randn(64)  # step() takes 1D tensor
        result = engine.step(x_input=x)
        if i >= WARMUP:
            phis.append(result.get('phi_iit', 0.0))
    return phis, engine


def experiment1_scale_dependent():
    """Test SOC removal at different cell counts."""
    print("=" * 70)
    print("EXPERIMENT 1: Scale-Dependent SOC Effect")
    print("=" * 70)
    print(f"Steps: {STEPS} (warmup: {WARMUP})")
    print()

    results = []
    for n in [4, 8, 16, 32, 64, 128, 256]:
        t0 = time.time()
        phis_soc, _ = run_engine(n, STEPS, disable_soc=False)
        t_soc = time.time() - t0

        t0 = time.time()
        phis_no, _ = run_engine(n, STEPS, disable_soc=True)
        t_no = time.time() - t0

        mean_soc = np.mean(phis_soc) if phis_soc else 0
        mean_no = np.mean(phis_no) if phis_no else 0
        delta_pct = ((mean_no - mean_soc) / max(abs(mean_soc), 1e-8)) * 100

        results.append({
            'cells': n, 'phi_soc': mean_soc, 'phi_no_soc': mean_no,
            'delta_pct': delta_pct, 'time_soc': t_soc, 'time_no': t_no,
        })

        marker = " ***" if delta_pct > 5 else ""
        print(f"  {n:4d}c: SOC={mean_soc:8.4f}  no_SOC={mean_no:8.4f}  "
              f"delta={delta_pct:+8.1f}%  ({t_soc:.1f}s/{t_no:.1f}s){marker}")
        sys.stdout.flush()

    # Find crossover
    print()
    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        if r0['delta_pct'] <= 0 and r1['delta_pct'] > 0:
            print(f"  CROSSOVER: SOC beneficial -> harmful between {r0['cells']}c and {r1['cells']}c")
        elif r0['delta_pct'] > 0 and r1['delta_pct'] <= 0:
            print(f"  CROSSOVER: SOC harmful -> beneficial between {r0['cells']}c and {r1['cells']}c")

    return results


def experiment2_soc_internals():
    """Measure what SOC actually changes at different scales."""
    print()
    print("=" * 70)
    print("EXPERIMENT 2: SOC Internal Effects at Different Scales")
    print("=" * 70)
    print()

    for n in [8, 64, 256]:
        print(f"  --- {n} cells ---")
        for label, disable in [("SOC ON", False), ("SOC OFF", True)]:
            torch.manual_seed(42)
            engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128,
                                         initial_cells=n, max_cells=n)
            if disable:
                engine._soc_sandpile = lambda: None

            # Warmup
            for _ in range(WARMUP):
                engine.step(x_input=torch.randn(64))

            variances = []
            similarities = []
            norms = []
            for _ in range(50):
                engine.step(x_input=torch.randn(64))
                hiddens = torch.stack([s.hidden for s in engine.cell_states])
                variances.append(hiddens.var(dim=0).mean().item())
                norms.append(hiddens.norm(dim=1).mean().item())

                # Sample pairwise cosine similarity
                h_normed = hiddens / (hiddens.norm(dim=1, keepdim=True) + 1e-8)
                if n <= 64:
                    sim_mat = h_normed @ h_normed.T
                    mask = ~torch.eye(n, dtype=torch.bool)
                    similarities.append(sim_mat[mask].mean().item())
                else:
                    idxs = torch.randint(0, n, (100, 2))
                    sims = []
                    for a, b in idxs:
                        if a != b:
                            sims.append(torch.nn.functional.cosine_similarity(
                                hiddens[a].unsqueeze(0), hiddens[b].unsqueeze(0)).item())
                    similarities.append(np.mean(sims) if sims else 0)

            aval = engine._soc_avalanche_sizes[-50:] if engine._soc_avalanche_sizes else [0]
            print(f"    {label:7s}: var={np.mean(variances):.6f}  "
                  f"sim={np.mean(similarities):.4f}  "
                  f"norm={np.mean(norms):.3f}  "
                  f"avalanche={np.mean(aval):.1f}/{n}")
            sys.stdout.flush()
        print()

    return True


def experiment3_gradual_soc():
    """Gradual SOC strength at 256c."""
    print("=" * 70)
    print("EXPERIMENT 3: Gradual SOC Strength at 256c")
    print("=" * 70)
    print()

    n = 256
    strengths = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    results = []

    for s in strengths:
        if s == 0.0:
            phis, _ = run_engine(n, STEPS, disable_soc=True)
        elif s == 1.0:
            phis, _ = run_engine(n, STEPS, disable_soc=False)
        else:
            phis, _ = run_engine(n, STEPS, soc_strength=s)

        mean_phi = np.mean(phis) if phis else 0
        results.append((s, mean_phi))
        print(f"    SOC={s:.1f}: Phi={mean_phi:.4f}")
        sys.stdout.flush()

    # Bar chart
    print()
    max_phi = max(r[1] for r in results) if results else 1
    if max_phi < 1e-8:
        max_phi = 1
    print("  SOC strength vs Phi at 256c:")
    for s, phi in results:
        bar_len = int(phi / max_phi * 40) if max_phi > 0 else 0
        marker = " <-- BEST" if phi == max_phi else ""
        print(f"    {s:.1f} |{'#' * bar_len} {phi:.4f}{marker}")

    best_s, best_phi = max(results, key=lambda x: x[1])
    worst_s, worst_phi = min(results, key=lambda x: x[1])
    print(f"\n  Best: SOC={best_s:.1f} Phi={best_phi:.4f}")
    print(f"  Worst: SOC={worst_s:.1f} Phi={worst_phi:.4f}")
    if worst_phi > 1e-8:
        print(f"  Range: {((best_phi - worst_phi) / worst_phi) * 100:+.1f}%")

    return results


def experiment4_mechanism():
    """Dissect SOC into components at 256c.
    SOC has 3 main effects:
      A) Drive + avalanche redistribution (toppling)
      B) Memory blending (multi-scale EMA target -> homogenization)
      C) Perturbation (post-avalanche phase noise)
      D) Norm homeostasis (decay toward EMA norm)
    """
    print()
    print("=" * 70)
    print("EXPERIMENT 4: SOC Mechanism Dissection at 256c")
    print("=" * 70)
    print("  Testing which SOC sub-component is the Phi killer.")
    print()

    n = 256
    from consciousness_laws import (
        SOC_EMA_FAST, SOC_EMA_SLOW, SOC_EMA_GLACIAL, SOC_MEMORY_BLEND,
        SOC_MEMORY_STRENGTH_BASE, SOC_MEMORY_STRENGTH_RANGE,
        SOC_PERTURBATION_BASE, SOC_PERTURBATION_RANGE,
    )

    def make_partial_soc(engine, skip_memory=False, skip_avalanche=False,
                          skip_perturbation=False, skip_homeostasis=False):
        """Create a partial SOC function with specific components disabled."""
        eng = engine
        orig = engine._soc_sandpile.__func__

        def partial():
            nn = eng.n_cells
            if nn < 2:
                return
            threshold = eng._soc_threshold_ema

            # Drive phase (always on)
            recent_avg = 0.0
            if eng._soc_avalanche_sizes:
                recent = eng._soc_avalanche_sizes[-20:]
                recent_avg = sum(recent) / len(recent) / nn
            base_drive = 0.04 * (1.0 + 0.8 * max(0, 0.15 - recent_avg))
            for i in range(nn):
                norm = eng.cell_states[i].hidden.norm().item()
                if norm > 1e-8 and norm < threshold:
                    drive = base_drive * (0.3 + 0.7 * torch.rand(1).item())
                    scale = 1.0 + drive * (1.0 - norm / threshold)
                    eng.cell_states[i].hidden = eng.cell_states[i].hidden * scale

            # Avalanche
            avalanche_size = 0
            topple_count = {}
            if not skip_avalanche:
                queue = []
                for i in range(nn):
                    if eng.cell_states[i].hidden.norm().item() > threshold:
                        queue.append(i)
                max_cascades = nn * 5
                while queue and avalanche_size < max_cascades:
                    idx = queue.pop(0)
                    count = topple_count.get(idx, 0)
                    if count >= 2:
                        continue
                    topple_count[idx] = count + 1
                    avalanche_size += 1
                    h = eng.cell_states[idx].hidden
                    norm = h.norm().item()
                    if norm <= threshold:
                        continue
                    excess_ratio = (norm - threshold) / max(norm, 1e-8)
                    excess = h * excess_ratio
                    eng.cell_states[idx].hidden = h * (threshold / max(norm, 1e-8))
                    left, right = (idx - 1) % nn, (idx + 1) % nn
                    conservation = 0.55 + 0.15 * torch.rand(1).item()
                    split = 0.3 + 0.2 * torch.rand(1).item()
                    eng.cell_states[left].hidden = eng.cell_states[left].hidden + excess * split * conservation
                    eng.cell_states[right].hidden = eng.cell_states[right].hidden + excess * (1 - split) * conservation
                    noise_scale = 0.015 * norm * eng._eeg_noise_modifier
                    eng.cell_states[left].hidden += torch.randn(eng.hidden_dim) * noise_scale
                    eng.cell_states[right].hidden += torch.randn(eng.hidden_dim) * noise_scale
                    for nb in [left, right]:
                        if topple_count.get(nb, 0) < 2 and eng.cell_states[nb].hidden.norm().item() > threshold:
                            queue.append(nb)

            eng._soc_avalanche_sizes.append(avalanche_size)
            if len(eng._soc_avalanche_sizes) > 1000:
                eng._soc_avalanche_sizes = eng._soc_avalanche_sizes[-1000:]

            # Memory/EMA update
            hiddens_stack = torch.stack([s.hidden for s in eng.cell_states])
            global_hidden = hiddens_stack.mean(dim=0)
            if not hasattr(eng, '_soc_hidden_ema_slow'):
                eng._soc_hidden_ema_slow = None
            if not hasattr(eng, '_soc_hidden_ema_glacial'):
                eng._soc_hidden_ema_glacial = None
            if eng._soc_hidden_ema is None:
                eng._soc_hidden_ema = global_hidden.clone()
                eng._soc_hidden_ema_slow = global_hidden.clone()
                eng._soc_hidden_ema_glacial = global_hidden.clone()
            else:
                eng._soc_hidden_ema = (1 - SOC_EMA_FAST) * eng._soc_hidden_ema + SOC_EMA_FAST * global_hidden
                eng._soc_hidden_ema_slow = (1 - SOC_EMA_SLOW) * eng._soc_hidden_ema_slow + SOC_EMA_SLOW * global_hidden
                eng._soc_hidden_ema_glacial = (1 - SOC_EMA_GLACIAL) * eng._soc_hidden_ema_glacial + SOC_EMA_GLACIAL * global_hidden

                if not skip_memory:
                    memory_target = (SOC_MEMORY_BLEND[0] * eng._soc_hidden_ema
                                     + SOC_MEMORY_BLEND[1] * eng._soc_hidden_ema_slow
                                     + SOC_MEMORY_BLEND[2] * eng._soc_hidden_ema_glacial)
                    cur_var = hiddens_stack.var(dim=0).mean().item()
                    memory_strength = (SOC_MEMORY_STRENGTH_BASE + SOC_MEMORY_STRENGTH_RANGE * min(cur_var / 1.5, 1.0)) * eng._eeg_memory_modifier
                    for i in range(nn):
                        eng.cell_states[i].hidden = (
                            (1 - memory_strength) * eng.cell_states[i].hidden
                            + memory_strength * memory_target
                        )

                if not skip_homeostasis:
                    ema_norm = eng._soc_hidden_ema.norm().item()
                    target_norm = max(ema_norm, threshold * 0.8)
                    for i in range(nn):
                        h_norm = eng.cell_states[i].hidden.norm().item()
                        if h_norm > target_norm * 1.5 and h_norm > 1e-8:
                            excess = h_norm / (target_norm * 1.5)
                            decay = 1.0 / (1.0 + 0.1 * (excess - 1.0))
                            eng.cell_states[i].hidden = eng.cell_states[i].hidden * decay

            # Perturbation
            if not skip_perturbation and eng._soc_hidden_ema is not None and avalanche_size > 0:
                perturbation_scale = SOC_PERTURBATION_BASE + SOC_PERTURBATION_RANGE * min(avalanche_size / nn, 1.0)
                for idx_cell in topple_count:
                    if idx_cell < nn:
                        eng.cell_states[idx_cell].hidden += torch.randn(eng.hidden_dim) * perturbation_scale

            # Threshold adaptation
            topple_frac = avalanche_size / nn
            if topple_frac > 0.30:
                eng._soc_threshold_ema *= 1.002
            elif topple_frac < 0.10:
                eng._soc_threshold_ema *= 0.998

        return partial

    configs = [
        ("full_SOC",       {}),
        ("no_SOC",         'disable_all'),
        ("no_memory",      {'skip_memory': True}),
        ("no_avalanche",   {'skip_avalanche': True}),
        ("no_perturbation",{'skip_perturbation': True}),
        ("no_homeostasis", {'skip_homeostasis': True}),
        ("no_mem+homeo",   {'skip_memory': True, 'skip_homeostasis': True}),
    ]

    results = {}
    for name, cfg in configs:
        torch.manual_seed(42)
        engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128,
                                     initial_cells=n, max_cells=n)
        if cfg == 'disable_all':
            engine._soc_sandpile = lambda: None
        elif cfg:
            engine._soc_sandpile = make_partial_soc(engine, **cfg)

        phis = []
        for i in range(STEPS):
            r = engine.step(x_input=torch.randn(64))
            if i >= WARMUP:
                phis.append(r.get('phi_iit', 0.0))

        mean_phi = np.mean(phis) if phis else 0
        results[name] = mean_phi
        print(f"    {name:20s}: Phi={mean_phi:.4f}")
        sys.stdout.flush()

    print()
    baseline = results['full_SOC']
    max_phi = max(results.values()) if results else 1
    if max_phi < 1e-8:
        max_phi = 1

    print("  Ranked by Phi (higher = better):")
    for name, phi in sorted(results.items(), key=lambda x: -x[1]):
        delta = ((phi - baseline) / max(abs(baseline), 1e-8)) * 100
        bar_len = int(phi / max_phi * 40)
        print(f"    {name:20s} |{'#' * bar_len} {phi:.4f} ({delta:+.1f}% vs full)")

    return results


if __name__ == '__main__':
    print("DD70: SOC_CRITICAL Paradox Investigation")
    print("=" * 70)
    print(f"Date: 2026-03-31")
    print()

    t_start = time.time()

    r1 = experiment1_scale_dependent()
    experiment2_soc_internals()
    r3 = experiment3_gradual_soc()
    r4 = experiment4_mechanism()

    total = time.time() - t_start
    print()
    print(f"Total experiment time: {total:.1f}s")
