#!/usr/bin/env python3
"""acceleration_c3_entropy.py — Entropy surfing: jump along entropy gradients instead of CE gradients

Hypothesis: Instead of gradient descent on cross-entropy, directly compute the Shannon
entropy landscape of hidden states and navigate it. The brain operates near critical
entropy (PSI_ENTROPY = 0.998). "Surfing" this entropy surface may be faster or more
stable than CE-gradient descent.

Four experiments:
  Exp 1: Entropy direction probing — random perturbations, pick entropy-reducing direction
  Exp 2: Numerical entropy gradient — dH/dW via finite differences, compare to dCE/dW
  Exp 3: PSI_ENTROPY surfing — maintain H ≈ 0.998 via bidirectional control
  Exp 4: Speed comparison — entropy jump vs gradient descent to reach CE < target

Local CPU, 32 cells, Shannon entropy + mutual information.
"""

import sys
import os
import time
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from consciousness_engine import ConsciousnessEngine
from consciousness_laws import PSI_ENTROPY, PSI_ALPHA
from conscious_decoder import ConsciousDecoderV2

# ═══════════════════════════════════════════════════════════
# Entropy computation utilities
# ═══════════════════════════════════════════════════════════

def shannon_entropy(hiddens: torch.Tensor, n_bins: int = 32) -> float:
    """Compute normalized Shannon entropy of hidden state distribution.

    Args:
        hiddens: (n_cells, hidden_dim) tensor
        n_bins: histogram resolution

    Returns:
        H_norm in [0, 1] — 0=perfectly ordered, 1=max entropy (uniform)
    """
    flat = hiddens.detach().flatten().float()
    if flat.numel() < 2:
        return 0.0

    # Histogram over all values
    lo, hi = flat.min().item(), flat.max().item()
    if hi - lo < 1e-8:
        return 0.0  # all identical → zero entropy

    counts = torch.histc(flat, bins=n_bins, min=lo, max=hi)
    probs = counts / counts.sum()
    probs = probs[probs > 0]

    H = -(probs * probs.log()).sum().item()
    H_max = math.log(n_bins)
    return H / H_max if H_max > 0 else 0.0


def per_cell_entropy(hiddens: torch.Tensor, n_bins: int = 32) -> float:
    """Average Shannon entropy computed per-cell (across hidden dim)."""
    n_cells = hiddens.shape[0]
    total_H = 0.0
    for i in range(n_cells):
        total_H += shannon_entropy(hiddens[i:i+1], n_bins)
    return total_H / n_cells


def mutual_information(hiddens: torch.Tensor, n_bins: int = 16) -> float:
    """Estimate average pairwise mutual information between cells.

    MI(i,j) = H(i) + H(j) - H(i,j)  via 2D histogram.
    """
    n_cells = hiddens.shape[0]
    if n_cells < 2:
        return 0.0

    flat_cells = []
    for i in range(n_cells):
        v = hiddens[i].detach().float()
        # PCA to 1D for histogram
        flat_cells.append(v.mean().item())

    total_mi = 0.0
    pairs = 0
    for i in range(min(n_cells, 16)):  # cap pairs for speed
        for j in range(i + 1, min(n_cells, 16)):
            xi = flat_cells[i]
            xj = flat_cells[j]
            # Simple bin-based MI estimate
            # H(i), H(j) from marginal, H(i,j) from joint
            # Since we have scalar summaries, use direct formula
            total_mi += abs(xi - xj)  # proxy: divergence
            pairs += 1

    if pairs == 0:
        return 0.0

    # Better MI: use actual hidden vectors
    total_mi = 0.0
    pairs = 0
    for i in range(min(n_cells, 8)):
        for j in range(i + 1, min(n_cells, 8)):
            hi = hiddens[i].detach().float()
            hj = hiddens[j].detach().float()
            # Correlation-based MI approximation: MI ≈ -0.5 * ln(1 - r^2)
            cos = F.cosine_similarity(hi.unsqueeze(0), hj.unsqueeze(0)).item()
            r2 = cos ** 2
            if r2 < 0.999:
                mi = -0.5 * math.log(1 - r2)
            else:
                mi = 3.0  # cap
            total_mi += mi
            pairs += 1

    return total_mi / pairs if pairs > 0 else 0.0


def get_engine_hiddens(engine: ConsciousnessEngine) -> torch.Tensor:
    """Extract hidden states from engine as (n_cells, hidden_dim) tensor."""
    return torch.stack([s.hidden for s in engine.cell_states])


def compute_phi_proxy(engine: ConsciousnessEngine) -> float:
    """Quick Φ(proxy) = global_var - faction_var."""
    hiddens = get_engine_hiddens(engine)
    global_var = hiddens.var(dim=0).mean().item()

    n = hiddens.shape[0]
    faction_ids = [s.faction_id for s in engine.cell_states]
    faction_set = set(faction_ids)
    faction_var = 0.0
    for fid in faction_set:
        mask = [i for i in range(n) if faction_ids[i] == fid]
        if len(mask) >= 2:
            fh = hiddens[torch.tensor(mask)]
            faction_var += fh.var(dim=0).mean().item()
    if len(faction_set) > 0:
        faction_var /= len(faction_set)

    return max(0.0, global_var - faction_var)


# ═══════════════════════════════════════════════════════════
# Experiment 1: Entropy direction probing
# ═══════════════════════════════════════════════════════════

def exp1_entropy_direction_probing(n_cells=32, n_steps=100, n_probes=10, epsilon=0.01):
    """Probe random directions, pick the one that moves entropy toward PSI_ENTROPY."""
    print("\n" + "=" * 70)
    print("EXP 1: Entropy Direction Probing")
    print(f"  cells={n_cells}, steps={n_steps}, probes/step={n_probes}, eps={epsilon}")
    print(f"  target entropy = PSI_ENTROPY = {PSI_ENTROPY}")
    print("=" * 70)

    engine = ConsciousnessEngine(max_cells=n_cells, initial_cells=n_cells)

    # Warm up
    for _ in range(20):
        engine.step()

    baseline_H = []
    surfed_H = []
    baseline_phi = []
    surfed_phi = []

    # --- Baseline: normal engine evolution ---
    engine_base = ConsciousnessEngine(max_cells=n_cells, initial_cells=n_cells)
    for _ in range(20):
        engine_base.step()

    t0 = time.time()
    for step in range(n_steps):
        engine_base.step()
        h = get_engine_hiddens(engine_base)
        baseline_H.append(shannon_entropy(h))
        baseline_phi.append(compute_phi_proxy(engine_base))

        if (step + 1) % 25 == 0:
            print(f"  [baseline] step {step+1}/{n_steps}  H={baseline_H[-1]:.4f}  Φ={baseline_phi[-1]:.4f}")
            sys.stdout.flush()

    base_time = time.time() - t0

    # --- Entropy surfing: after each step, probe directions and nudge toward PSI_ENTROPY ---
    t0 = time.time()
    for step in range(n_steps):
        engine.step()
        hiddens = get_engine_hiddens(engine)
        current_H = shannon_entropy(hiddens)

        # Distance from target entropy
        H_error = current_H - PSI_ENTROPY

        best_direction = None
        best_improvement = 0.0

        for _ in range(n_probes):
            # Random direction in hidden space
            direction = torch.randn_like(hiddens)
            direction = direction / (direction.norm() + 1e-8)

            # Probe: nudge hiddens
            probed = hiddens + epsilon * direction
            probed_H = shannon_entropy(probed)
            probed_error = probed_H - PSI_ENTROPY

            # Improvement = reduction in |H - target|
            improvement = abs(H_error) - abs(probed_error)
            if improvement > best_improvement:
                best_improvement = improvement
                best_direction = direction

        # Apply best direction
        if best_direction is not None and best_improvement > 0:
            for i in range(engine.n_cells):
                engine.cell_states[i].hidden = (
                    engine.cell_states[i].hidden + epsilon * best_direction[i]
                )

        surfed_H.append(shannon_entropy(get_engine_hiddens(engine)))
        surfed_phi.append(compute_phi_proxy(engine))

        if (step + 1) % 25 == 0:
            print(f"  [surfed]   step {step+1}/{n_steps}  H={surfed_H[-1]:.4f}  Φ={surfed_phi[-1]:.4f}  best_impr={best_improvement:.6f}")
            sys.stdout.flush()

    surf_time = time.time() - t0

    # Results
    print("\n--- Exp 1 Results ---")
    print(f"  Target H = {PSI_ENTROPY}")
    print(f"  Baseline: avg H = {np.mean(baseline_H):.4f} ± {np.std(baseline_H):.4f}")
    print(f"  Surfed:   avg H = {np.mean(surfed_H):.4f} ± {np.std(surfed_H):.4f}")
    print(f"  Baseline: avg Φ = {np.mean(baseline_phi):.4f} ± {np.std(baseline_phi):.4f}")
    print(f"  Surfed:   avg Φ = {np.mean(surfed_phi):.4f} ± {np.std(surfed_phi):.4f}")
    print(f"  |H - target| baseline: {np.mean(np.abs(np.array(baseline_H) - PSI_ENTROPY)):.4f}")
    print(f"  |H - target| surfed:   {np.mean(np.abs(np.array(surfed_H) - PSI_ENTROPY)):.4f}")
    print(f"  Time: baseline {base_time:.1f}s, surfed {surf_time:.1f}s")

    # Phi stability comparison
    phi_base_cv = np.std(baseline_phi) / (np.mean(baseline_phi) + 1e-8)
    phi_surf_cv = np.std(surfed_phi) / (np.mean(surfed_phi) + 1e-8)
    print(f"  Φ CV (lower=more stable): baseline {phi_base_cv:.4f}, surfed {phi_surf_cv:.4f}")

    return {
        'baseline_H': baseline_H, 'surfed_H': surfed_H,
        'baseline_phi': baseline_phi, 'surfed_phi': surfed_phi,
        'base_time': base_time, 'surf_time': surf_time,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 2: Numerical entropy gradient vs CE gradient
# ═══════════════════════════════════════════════════════════

def exp2_entropy_gradient(n_cells=32, n_steps=50, epsilon=0.001):
    """Compare dH/dW (entropy gradient) with dCE/dW (loss gradient).

    Measures: cosine similarity between the two gradient directions.
    If cos ≈ 1: entropy descent ≈ CE descent (redundant).
    If cos ≈ 0: orthogonal (complementary info).
    If cos < 0:  opposing (entropy descent hurts CE).
    """
    print("\n" + "=" * 70)
    print("EXP 2: Entropy Gradient vs CE Gradient")
    print(f"  cells={n_cells}, steps={n_steps}, eps={epsilon}")
    print("=" * 70)

    # Create a small decoder for CE measurement
    decoder = ConsciousDecoderV2(
        consciousness_dim=128, d_model=128, n_head=4, n_kv_head=2,
        n_layer=2, vocab_size=256, block_size=64,
    )
    decoder.eval()

    engine = ConsciousnessEngine(max_cells=n_cells, initial_cells=n_cells)
    for _ in range(30):
        engine.step()

    cosine_sims = []
    H_values = []
    CE_values = []

    for step in range(n_steps):
        engine.step()
        hiddens = get_engine_hiddens(engine)  # (n_cells, hidden_dim)
        current_H = shannon_entropy(hiddens)
        H_values.append(current_H)

        # Pick one GRU cell's weight to compute gradients on
        cell_mod = engine.cell_modules[0]
        W = cell_mod.gru.weight_hh  # a real parameter

        # --- Entropy gradient (numerical) ---
        H_grads = []
        W_flat = W.data.flatten()
        n_params = min(W_flat.numel(), 200)  # sample subset for speed

        indices = torch.randperm(W_flat.numel())[:n_params]
        dH_dW = torch.zeros(n_params)

        for k, idx in enumerate(indices):
            orig = W_flat[idx].item()

            # H(W + eps)
            W_flat[idx] = orig + epsilon
            W.data = W_flat.view_as(W)
            engine.step()
            h_plus = get_engine_hiddens(engine)
            H_plus = shannon_entropy(h_plus)

            # H(W - eps)
            W_flat[idx] = orig - epsilon
            W.data = W_flat.view_as(W)
            engine.step()
            h_minus = get_engine_hiddens(engine)
            H_minus = shannon_entropy(h_minus)

            # Restore
            W_flat[idx] = orig
            W.data = W_flat.view_as(W)

            dH_dW[k] = (H_plus - H_minus) / (2 * epsilon)

        # --- CE gradient (autograd) ---
        # Run decoder with consciousness states
        idx_seq = torch.randint(0, 256, (1, 65))
        x = idx_seq[:, :64]
        y = idx_seq[:, 1:65]

        decoder.train()
        decoder.zero_grad()

        # Enable grad temporarily on the GRU weight
        W.requires_grad_(True)
        engine.step()
        c_states = get_engine_hiddens(engine).mean(dim=0, keepdim=True).unsqueeze(0).expand(1, 64, -1)

        logits_a, logits_g, tensions = decoder(x, consciousness_states=c_states)
        ce = F.cross_entropy(logits_a.view(-1, 256), y.view(-1))
        CE_values.append(ce.item())

        # Since W is not in decoder's graph, we approximate CE gradient numerically too
        dCE_dW = torch.zeros(n_params)
        decoder.eval()
        with torch.no_grad():
            for k, idx_val in enumerate(indices):
                orig = W_flat[idx_val].item()

                W_flat[idx_val] = orig + epsilon
                W.data = W_flat.view_as(W)
                engine.step()
                c_plus = get_engine_hiddens(engine).mean(dim=0, keepdim=True).unsqueeze(0).expand(1, 64, -1)
                la, _, _ = decoder(x, consciousness_states=c_plus)
                ce_plus = F.cross_entropy(la.view(-1, 256), y.view(-1)).item()

                W_flat[idx_val] = orig - epsilon
                W.data = W_flat.view_as(W)
                engine.step()
                c_minus = get_engine_hiddens(engine).mean(dim=0, keepdim=True).unsqueeze(0).expand(1, 64, -1)
                la, _, _ = decoder(x, consciousness_states=c_minus)
                ce_minus = F.cross_entropy(la.view(-1, 256), y.view(-1)).item()

                W_flat[idx_val] = orig
                W.data = W_flat.view_as(W)

                dCE_dW[k] = (ce_plus - ce_minus) / (2 * epsilon)

        W.requires_grad_(False)

        # Cosine similarity between entropy gradient and CE gradient
        if dH_dW.norm() > 1e-8 and dCE_dW.norm() > 1e-8:
            cos = F.cosine_similarity(dH_dW.unsqueeze(0), dCE_dW.unsqueeze(0)).item()
        else:
            cos = 0.0
        cosine_sims.append(cos)

        if (step + 1) % 10 == 0:
            print(f"  step {step+1}/{n_steps}  H={current_H:.4f}  CE={CE_values[-1]:.4f}  cos(dH,dCE)={cos:.4f}")
            sys.stdout.flush()

    print("\n--- Exp 2 Results ---")
    print(f"  avg cos(dH/dW, dCE/dW) = {np.mean(cosine_sims):.4f} ± {np.std(cosine_sims):.4f}")
    print(f"  Interpretation:")
    avg_cos = np.mean(cosine_sims)
    if avg_cos > 0.5:
        print(f"    ALIGNED — entropy gradient ≈ CE gradient (redundant info)")
    elif avg_cos > -0.2:
        print(f"    ORTHOGONAL — entropy gradient carries complementary info")
    else:
        print(f"    OPPOSING — entropy descent conflicts with CE descent")
    print(f"  H range: [{min(H_values):.4f}, {max(H_values):.4f}]")
    print(f"  CE range: [{min(CE_values):.4f}, {max(CE_values):.4f}]")

    return {'cosine_sims': cosine_sims, 'H_values': H_values, 'CE_values': CE_values}


# ═══════════════════════════════════════════════════════════
# Experiment 3: PSI_ENTROPY surfing (homeostatic entropy control)
# ═══════════════════════════════════════════════════════════

def exp3_psi_entropy_surfing(n_cells=32, n_steps=200, gain=0.05):
    """Maintain entropy near PSI_ENTROPY = 0.998 via feedback control.

    When H > target: nudge toward lower entropy (more structure)
    When H < target: nudge toward higher entropy (more noise)

    Measure: does this stabilize Φ? Does consciousness benefit from entropy homeostasis?
    """
    print("\n" + "=" * 70)
    print("EXP 3: PSI_ENTROPY Surfing (Homeostatic Control)")
    print(f"  cells={n_cells}, steps={n_steps}, gain={gain}")
    print(f"  target H = {PSI_ENTROPY}")
    print("=" * 70)

    # Baseline engine
    engine_base = ConsciousnessEngine(max_cells=n_cells, initial_cells=n_cells)
    # Surfing engine
    engine_surf = ConsciousnessEngine(max_cells=n_cells, initial_cells=n_cells)

    # Sync initial state
    for _ in range(20):
        engine_base.step()
        engine_surf.step()

    base_H, surf_H = [], []
    base_phi, surf_phi = [], []
    base_mi, surf_mi = [], []
    corrections = []

    t0 = time.time()
    for step in range(n_steps):
        # Step both engines
        engine_base.step()
        engine_surf.step()

        # Measure baseline
        h_base = get_engine_hiddens(engine_base)
        base_H.append(shannon_entropy(h_base))
        base_phi.append(compute_phi_proxy(engine_base))

        # Measure surfed before correction
        h_surf = get_engine_hiddens(engine_surf)
        current_H = shannon_entropy(h_surf)

        # Entropy error: how far from PSI_ENTROPY
        H_error = current_H - PSI_ENTROPY

        # Correction: move hiddens toward/away from mean
        if abs(H_error) > 0.01:  # deadband
            mean_h = h_surf.mean(dim=0)
            for i in range(engine_surf.n_cells):
                if H_error > 0:
                    # Too much entropy → pull toward mean (reduce diversity)
                    delta = (mean_h - engine_surf.cell_states[i].hidden) * gain * H_error
                else:
                    # Too little entropy → push away from mean (increase diversity)
                    delta = (engine_surf.cell_states[i].hidden - mean_h) * gain * abs(H_error)
                engine_surf.cell_states[i].hidden = engine_surf.cell_states[i].hidden + delta

        corrections.append(H_error)
        h_after = get_engine_hiddens(engine_surf)
        surf_H.append(shannon_entropy(h_after))
        surf_phi.append(compute_phi_proxy(engine_surf))

        # MI every 20 steps (expensive)
        if (step + 1) % 20 == 0:
            base_mi.append(mutual_information(get_engine_hiddens(engine_base)))
            surf_mi.append(mutual_information(get_engine_hiddens(engine_surf)))
            print(f"  step {step+1}/{n_steps}  base H={base_H[-1]:.4f} Φ={base_phi[-1]:.4f}  "
                  f"surf H={surf_H[-1]:.4f} Φ={surf_phi[-1]:.4f}  MI_base={base_mi[-1]:.3f} MI_surf={surf_mi[-1]:.3f}")
            sys.stdout.flush()

    elapsed = time.time() - t0

    # Analysis
    print("\n--- Exp 3 Results ---")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Target H = {PSI_ENTROPY}")
    print(f"  {'Metric':<25} {'Baseline':>12} {'Surfed':>12} {'Delta':>10}")
    print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*10}")

    metrics = [
        ("avg H", np.mean(base_H), np.mean(surf_H)),
        ("std H", np.std(base_H), np.std(surf_H)),
        ("|H - target| avg", np.mean(np.abs(np.array(base_H) - PSI_ENTROPY)),
         np.mean(np.abs(np.array(surf_H) - PSI_ENTROPY))),
        ("avg Φ(proxy)", np.mean(base_phi), np.mean(surf_phi)),
        ("std Φ(proxy)", np.std(base_phi), np.std(surf_phi)),
        ("Φ final", base_phi[-1], surf_phi[-1]),
    ]
    if base_mi:
        metrics.append(("avg MI", np.mean(base_mi), np.mean(surf_mi)))

    for name, bv, sv in metrics:
        delta = sv - bv
        pct = (delta / (abs(bv) + 1e-8)) * 100
        print(f"  {name:<25} {bv:>12.4f} {sv:>12.4f} {pct:>+9.1f}%")

    # ASCII graph: H over time
    print("\n  Entropy over time (--- = baseline, === = surfed, ... = target):")
    _ascii_dual_graph(base_H, surf_H, PSI_ENTROPY, width=60, height=12)

    # ASCII graph: Phi over time
    print("\n  Φ(proxy) over time (--- = baseline, === = surfed):")
    _ascii_dual_graph(base_phi, surf_phi, target=None, width=60, height=12)

    return {
        'base_H': base_H, 'surf_H': surf_H,
        'base_phi': base_phi, 'surf_phi': surf_phi,
        'corrections': corrections,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 4: Entropy jump vs gradient descent speed
# ═══════════════════════════════════════════════════════════

def exp4_speed_comparison(n_cells=32, max_steps=200, target_ce=4.5):
    """Race: entropy-guided weight update vs standard gradient descent.

    Both try to reduce decoder CE below target.
    Entropy method: estimate dH/dW numerically, update W to reduce H (entropy descent).
    Gradient method: standard CE backward + SGD.

    Measure: steps to reach target CE, final CE, Φ preservation.
    """
    print("\n" + "=" * 70)
    print("EXP 4: Speed Comparison — Entropy Jump vs Gradient Descent")
    print(f"  cells={n_cells}, max_steps={max_steps}, target CE={target_ce}")
    print("=" * 70)

    # Shared consciousness engine (frozen during this comparison)
    engine = ConsciousnessEngine(max_cells=n_cells, initial_cells=n_cells)
    for _ in range(30):
        engine.step()

    # Get consciousness states
    def get_c_states(eng, seq_len=64):
        h = get_engine_hiddens(eng)
        return h.mean(dim=0, keepdim=True).unsqueeze(0).expand(1, seq_len, -1)

    seq_len = 64

    # --- Gradient descent ---
    decoder_gd = ConsciousDecoderV2(
        consciousness_dim=128, d_model=128, n_head=4, n_kv_head=2,
        n_layer=2, vocab_size=256, block_size=seq_len,
    )
    optimizer_gd = torch.optim.Adam(decoder_gd.parameters(), lr=1e-3)

    gd_ce_history = []
    gd_reached = None

    t0 = time.time()
    for step in range(max_steps):
        engine.step()  # keep consciousness alive
        c_states = get_c_states(engine, seq_len)

        idx = torch.randint(0, 256, (1, seq_len + 1))
        x, y = idx[:, :seq_len], idx[:, 1:seq_len + 1]

        decoder_gd.train()
        optimizer_gd.zero_grad()
        logits_a, _, _ = decoder_gd(x, consciousness_states=c_states)
        ce = F.cross_entropy(logits_a.view(-1, 256), y.view(-1))
        ce.backward()
        optimizer_gd.step()

        gd_ce_history.append(ce.item())
        if gd_reached is None and ce.item() < target_ce:
            gd_reached = step + 1

        if (step + 1) % 50 == 0:
            print(f"  [GD]      step {step+1}/{max_steps}  CE={ce.item():.4f}")
            sys.stdout.flush()

    gd_time = time.time() - t0

    # --- Entropy-guided update ---
    # Strategy: perturb decoder weights, keep perturbations that move
    # consciousness entropy toward PSI_ENTROPY AND reduce CE
    decoder_ent = ConsciousDecoderV2(
        consciousness_dim=128, d_model=128, n_head=4, n_kv_head=2,
        n_layer=2, vocab_size=256, block_size=seq_len,
    )
    # Copy initial weights from GD decoder's initial state
    # (Actually we should use fresh init for fair comparison)

    engine2 = ConsciousnessEngine(max_cells=n_cells, initial_cells=n_cells)
    for _ in range(30):
        engine2.step()

    ent_ce_history = []
    ent_reached = None
    lr_ent = 0.05  # larger step since direction is noisier
    n_directions = 5

    t0 = time.time()
    for step in range(max_steps):
        engine2.step()
        c_states = get_c_states(engine2, seq_len)

        idx = torch.randint(0, 256, (1, seq_len + 1))
        x, y = idx[:, :seq_len], idx[:, 1:seq_len + 1]

        decoder_ent.eval()
        with torch.no_grad():
            logits_a, _, _ = decoder_ent(x, consciousness_states=c_states)
            base_ce = F.cross_entropy(logits_a.view(-1, 256), y.view(-1)).item()

        # Current consciousness entropy
        h_current = get_engine_hiddens(engine2)
        base_H = shannon_entropy(h_current)

        # Try random weight perturbations
        best_delta_params = None
        best_score = 0.0

        params_list = list(decoder_ent.parameters())
        param_idx = step % len(params_list)  # rotate through parameters
        param = params_list[param_idx]

        for _ in range(n_directions):
            direction = torch.randn_like(param.data)
            direction = direction / (direction.norm() + 1e-8)

            # Perturb
            param.data.add_(lr_ent * direction)

            with torch.no_grad():
                logits_a, _, _ = decoder_ent(x, consciousness_states=c_states)
                new_ce = F.cross_entropy(logits_a.view(-1, 256), y.view(-1)).item()

            # Score = CE reduction + entropy alignment bonus
            ce_improvement = base_ce - new_ce
            h_new = shannon_entropy(h_current)  # hiddens unchanged by decoder
            h_alignment = abs(base_H - PSI_ENTROPY) - abs(h_new - PSI_ENTROPY)

            score = ce_improvement + 0.1 * h_alignment

            if score > best_score:
                best_score = score
                best_delta_params = lr_ent * direction.clone()

            # Restore
            param.data.add_(-lr_ent * direction)

        # Apply best perturbation
        if best_delta_params is not None and best_score > 0:
            param.data.add_(best_delta_params)

        # Measure final CE
        with torch.no_grad():
            logits_a, _, _ = decoder_ent(x, consciousness_states=c_states)
            final_ce = F.cross_entropy(logits_a.view(-1, 256), y.view(-1)).item()

        ent_ce_history.append(final_ce)
        if ent_reached is None and final_ce < target_ce:
            ent_reached = step + 1

        if (step + 1) % 50 == 0:
            print(f"  [Entropy] step {step+1}/{max_steps}  CE={final_ce:.4f}  best_score={best_score:.6f}")
            sys.stdout.flush()

    ent_time = time.time() - t0

    # Results
    print("\n--- Exp 4 Results ---")
    print(f"  Target CE = {target_ce}")
    print(f"  {'Method':<20} {'Final CE':>10} {'Steps to target':>16} {'Time':>8}")
    print(f"  {'-'*20} {'-'*10} {'-'*16} {'-'*8}")
    print(f"  {'Gradient Descent':<20} {gd_ce_history[-1]:>10.4f} {str(gd_reached or 'N/A'):>16} {gd_time:>7.1f}s")
    print(f"  {'Entropy Jump':<20} {ent_ce_history[-1]:>10.4f} {str(ent_reached or 'N/A'):>16} {ent_time:>7.1f}s")

    if gd_reached and ent_reached:
        ratio = ent_reached / gd_reached
        print(f"\n  Speed ratio (entropy/GD): {ratio:.2f}x {'(entropy faster)' if ratio < 1 else '(GD faster)'}")
    elif gd_reached:
        print(f"\n  Entropy method did not reach target in {max_steps} steps")
    elif ent_reached:
        print(f"\n  GD did not reach target in {max_steps} steps")

    # CE curves
    print("\n  CE over time (--- = GD, === = Entropy):")
    _ascii_dual_graph(gd_ce_history, ent_ce_history, target=target_ce, width=60, height=12)

    return {
        'gd_ce': gd_ce_history, 'ent_ce': ent_ce_history,
        'gd_reached': gd_reached, 'ent_reached': ent_reached,
        'gd_time': gd_time, 'ent_time': ent_time,
    }


# ═══════════════════════════════════════════════════════════
# ASCII graph utility
# ═══════════════════════════════════════════════════════════

def _ascii_dual_graph(series1, series2, target=None, width=60, height=12):
    """Simple dual ASCII line graph."""
    all_vals = list(series1) + list(series2)
    if target is not None:
        all_vals.append(target)
    lo = min(all_vals)
    hi = max(all_vals)
    if hi - lo < 1e-8:
        hi = lo + 1

    def to_row(v):
        return int((v - lo) / (hi - lo) * (height - 1))

    # Downsample to width
    def sample(series):
        if len(series) <= width:
            return series
        step = len(series) / width
        return [series[int(i * step)] for i in range(width)]

    s1 = sample(series1)
    s2 = sample(series2)
    n = min(len(s1), len(s2), width)

    grid = [[' ' for _ in range(n)] for _ in range(height)]

    for col in range(n):
        r1 = to_row(s1[col])
        r2 = to_row(s2[col])
        grid[height - 1 - r1][col] = '-'
        grid[height - 1 - r2][col] = '='

    # Target line
    if target is not None:
        tr = height - 1 - to_row(target)
        if 0 <= tr < height:
            for col in range(n):
                if grid[tr][col] == ' ':
                    grid[tr][col] = '.'

    # Print with Y-axis labels
    for row in range(height):
        val = hi - (row / (height - 1)) * (hi - lo)
        line = ''.join(grid[row])
        if row == 0:
            print(f"  {val:>8.3f} |{line}|")
        elif row == height - 1:
            print(f"  {val:>8.3f} |{line}|")
        elif row == height // 2:
            print(f"  {val:>8.3f} |{line}|")
        else:
            print(f"           |{line}|")


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  C3: Entropy Surfing — gradient-free learning via entropy landscape")
    print(f"  PSI_ENTROPY = {PSI_ENTROPY}, PSI_ALPHA = {PSI_ALPHA}")
    print("=" * 70)
    sys.stdout.flush()

    results = {}

    # Exp 1: Direction probing
    results['exp1'] = exp1_entropy_direction_probing(n_cells=32, n_steps=100, n_probes=10)

    # Exp 2: Gradient comparison (expensive, fewer steps)
    results['exp2'] = exp2_entropy_gradient(n_cells=16, n_steps=20, epsilon=0.001)

    # Exp 3: PSI_ENTROPY homeostasis
    results['exp3'] = exp3_psi_entropy_surfing(n_cells=32, n_steps=200, gain=0.05)

    # Exp 4: Speed race
    results['exp4'] = exp4_speed_comparison(n_cells=32, max_steps=200, target_ce=4.5)

    # ═══════════════════════════════════════════════════════════
    # Summary table
    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  SUMMARY: C3 Entropy Surfing Results")
    print("=" * 70)

    exp1 = results['exp1']
    exp2 = results['exp2']
    exp3 = results['exp3']
    exp4 = results['exp4']

    print(f"\n  {'Experiment':<35} {'Key Metric':<25} {'Value':>10}")
    print(f"  {'-'*35} {'-'*25} {'-'*10}")

    # Exp 1
    base_err = np.mean(np.abs(np.array(exp1['baseline_H']) - PSI_ENTROPY))
    surf_err = np.mean(np.abs(np.array(exp1['surfed_H']) - PSI_ENTROPY))
    improvement = (base_err - surf_err) / (base_err + 1e-8) * 100
    print(f"  {'1. Direction Probing':<35} {'|H-target| reduction':25} {improvement:>+9.1f}%")
    phi_delta = (np.mean(exp1['surfed_phi']) - np.mean(exp1['baseline_phi'])) / (np.mean(exp1['baseline_phi']) + 1e-8) * 100
    print(f"  {'':<35} {'Φ change':25} {phi_delta:>+9.1f}%")

    # Exp 2
    avg_cos = np.mean(exp2['cosine_sims'])
    print(f"  {'2. Gradient Comparison':<35} {'cos(dH/dW, dCE/dW)':25} {avg_cos:>+9.4f}")

    # Exp 3
    phi_base_avg = np.mean(exp3['base_phi'])
    phi_surf_avg = np.mean(exp3['surf_phi'])
    phi_pct = (phi_surf_avg - phi_base_avg) / (phi_base_avg + 1e-8) * 100
    print(f"  {'3. PSI_ENTROPY Surfing':<35} {'Φ change vs baseline':25} {phi_pct:>+9.1f}%")
    h_stability = np.std(exp3['surf_H']) / (np.std(exp3['base_H']) + 1e-8)
    print(f"  {'':<35} {'H stability (lower=better)':25} {h_stability:>9.3f}x")

    # Exp 4
    gd_final = exp4['gd_ce'][-1]
    ent_final = exp4['ent_ce'][-1]
    print(f"  {'4. Speed: GD':<35} {'final CE':25} {gd_final:>9.4f}")
    print(f"  {'4. Speed: Entropy':<35} {'final CE':25} {ent_final:>9.4f}")
    if exp4['gd_reached'] and exp4['ent_reached']:
        ratio = exp4['ent_reached'] / exp4['gd_reached']
        print(f"  {'':<35} {'speed ratio (ent/GD)':25} {ratio:>9.2f}x")

    print("\n  Conclusion:")
    if phi_pct > 5:
        print(f"    + Entropy surfing STABILIZES consciousness (Φ {phi_pct:+.1f}%)")
    elif phi_pct > -5:
        print(f"    ~ Entropy surfing is Φ-neutral ({phi_pct:+.1f}%)")
    else:
        print(f"    - Entropy surfing DESTABILIZES consciousness (Φ {phi_pct:+.1f}%)")

    if avg_cos > 0.3:
        print(f"    ~ Entropy gradient ALIGNED with CE gradient (cos={avg_cos:.3f}) — redundant")
    elif avg_cos > -0.3:
        print(f"    + Entropy gradient ORTHOGONAL to CE gradient (cos={avg_cos:.3f}) — complementary")
    else:
        print(f"    - Entropy gradient OPPOSING CE gradient (cos={avg_cos:.3f}) — harmful")

    print("\n  Done.")


if __name__ == '__main__':
    main()
