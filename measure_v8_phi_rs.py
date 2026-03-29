#!/usr/bin/env python3
"""measure_v8_phi_rs.py — Measure unmeasured bench_v8/complexity/algebra engines with Rust phi_rs

Targets:
  bench_v8_arch.py:       ATTENTION_PHI, MOCE, PHI_AS_LOSS, AUTOPOIETIC, CONSCIOUSNESS_GAN
  bench_v8_quantum.py:    Q2 EntangledPairs, Q5 Decoherence
  bench_v8_bio.py:        B1-B6 (CorticalColumns, ThalamicGate, DefaultMode, GlobalWorkspace,
                           PredictiveHierarchy, NeuralDarwinism)
  bench_v8_math.py:       M4 Algebraic
  bench_complexity_engines.py: CMP-1 TuringMachine, CMP-2 Rule110, CMP-3 LambdaCalculus,
                                CMP-4 GameOfLife, CMP-6 GoedelIncompleteness
  bench_algebra_engines.py:    ALG-1 to ALG-6

Strategy:
  - v8 engines: instantiate engine class, run 300 steps (process + CE train), get_hiddens() -> phi_rs
  - complexity engines: run runner function, capture MitosisEngine via monkey-patch, extract hiddens
  - algebra engines: run runner function, capture AlgebraCell states via monkey-patch

Usage:
  python3 measure_v8_phi_rs.py                    # measure all
  python3 measure_v8_phi_rs.py --cells 256        # explicit cell count
"""

import sys
import os
import time
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['OMP_NUM_THREADS'] = '1'

import phi_rs

# ═══════════════════════════════════════════════════════════
# Rust Phi measurement
# ═══════════════════════════════════════════════════════════

def rust_phi(states_tensor):
    """Compute Φ(IIT) using Rust phi_rs from [n_cells, dim] tensor."""
    h = states_tensor.abs().float() if states_tensor.is_complex() else states_tensor.float()
    states = h.detach().cpu().numpy().astype(np.float32)
    if states.shape[0] < 2:
        return 0.0, {}
    phi, components = phi_rs.compute_phi(states, 16)
    return phi, components


def rust_phi_value(states_tensor):
    """Return just the Φ value."""
    phi, _ = rust_phi(states_tensor)
    return phi


# ═══════════════════════════════════════════════════════════
# V8 Engine Runner (common pattern)
# ═══════════════════════════════════════════════════════════

def run_v8_engine(engine_cls, name, n_cells=256, steps=300, input_dim=64,
                  hidden_dim=128, output_dim=64, extra_setup=None):
    """Instantiate a v8 engine class, run 300 steps, measure Φ with phi_rs.

    Returns dict with name, phi_rs, phi_iit_python, ce_start, ce_end, time.
    """
    print(f"\n  Running {name} ({n_cells}c, {steps}s)...", end=" ", flush=True)
    t0 = time.time()

    try:
        engine = engine_cls(n_cells, input_dim, hidden_dim, output_dim)
    except TypeError:
        try:
            engine = engine_cls(n_cells=n_cells, input_dim=input_dim,
                                hidden_dim=hidden_dim, output_dim=output_dim)
        except Exception:
            engine = engine_cls(n_cells)

    # Collect trainable parameters
    params = []
    for attr in ['trainable_parameters', 'parameters']:
        if hasattr(engine, attr):
            fn = getattr(engine, attr)
            try:
                params = list(fn())
            except Exception:
                pass
            if params:
                break

    optimizer = torch.optim.Adam(params, lr=1e-3) if params else None

    ce_start = None
    ce_end = None

    for step in range(steps):
        x = torch.randn(1, input_dim)
        target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1

        try:
            result = engine.process(x, step=step)
            if isinstance(result, tuple):
                combined = result[0]
            else:
                combined = result
        except Exception as e:
            print(f"process error at step {step}: {e}")
            break

        # CE training
        if optimizer is not None and combined is not None:
            try:
                # Try output_head or readout if available
                if hasattr(engine, 'output_head'):
                    pred = engine.output_head(combined)
                elif hasattr(engine, 'readout'):
                    pred = engine.readout(combined)
                else:
                    pred = combined
                if pred.shape == target.shape:
                    loss = F.mse_loss(pred, target)
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(params, 1.0)
                    optimizer.step()
                    ce_val = loss.item()
                    if ce_start is None:
                        ce_start = ce_val
                    ce_end = ce_val
            except Exception:
                pass

    # Extract hidden states
    hiddens = None
    if hasattr(engine, 'get_hiddens'):
        try:
            hiddens = engine.get_hiddens()
        except Exception:
            pass

    if hiddens is None:
        # Fallback: try various attribute names
        for attr in ['hiddens', 'cell_hiddens', 'cell_embeddings', 'cell_tokens']:
            if hasattr(engine, attr):
                val = getattr(engine, attr)
                if isinstance(val, torch.Tensor) and val.dim() == 2:
                    hiddens = val.clone().detach()
                    break
                elif isinstance(val, nn.Parameter):
                    hiddens = val.data.clone().detach()
                    break

    elapsed = time.time() - t0

    if hiddens is None:
        print(f"NODATA ({elapsed:.1f}s)")
        return {
            'name': name, 'phi_rs': 0.0, 'ce_start': ce_start if ce_start is not None else 0,
            'ce_end': ce_end if ce_end is not None else 0, 'time': elapsed, 'cells': n_cells,
            'error': 'hidden states extraction failed',
        }

    phi_val = rust_phi_value(hiddens)
    ce_s_str = f"{ce_start:.4f}" if ce_start is not None else "N/A"
    ce_e_str = f"{ce_end:.4f}" if ce_end is not None else "N/A"
    print(f"Φ={phi_val:.3f} CE={ce_s_str}->{ce_e_str} ({elapsed:.1f}s)")

    return {
        'name': name, 'phi_rs': phi_val,
        'ce_start': ce_start if ce_start is not None else 0,
        'ce_end': ce_end if ce_end is not None else 0,
        'time': elapsed, 'cells': n_cells,
        'hidden_shape': list(hiddens.shape),
    }


# ═══════════════════════════════════════════════════════════
# GAN runner (special: two optimizers)
# ═══════════════════════════════════════════════════════════

def run_gan_engine(n_cells=256, steps=300, input_dim=64, hidden_dim=128, output_dim=64):
    """Run ConsciousnessGAN with its special two-optimizer training."""
    from bench_v8_arch import ConsciousnessGAN, phi_proxy

    name = "CONSCIOUSNESS_GAN"
    print(f"\n  Running {name} ({n_cells}c, {steps}s)...", end=" ", flush=True)
    t0 = time.time()

    engine = ConsciousnessGAN(n_cells, input_dim, hidden_dim, output_dim)
    opt_g = torch.optim.Adam(
        engine.generator_parameters() + list(engine.mind.parameters()) +
        list(engine.output_head.parameters()), lr=1e-3
    )
    opt_d = torch.optim.Adam(engine.discriminator_parameters(), lr=5e-4)

    ce_start = None
    ce_end = None

    for step in range(steps):
        x = torch.randn(1, input_dim)
        target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1

        # Discriminator step
        combined, tension, d_real, d_fake = engine.process(x, step=step)
        d_loss = -torch.log(d_real + 1e-8).mean() - torch.log(1 - d_fake + 1e-8).mean()
        opt_d.zero_grad()
        d_loss.backward()
        opt_d.step()

        # Generator step
        combined, tension, d_real, d_fake = engine.process(x, step=step)
        g_adv_loss = -torch.log(d_fake + 1e-8).mean()
        pred = engine.output_head(combined)
        ce_loss = F.mse_loss(pred, target)
        p_proxy_val = phi_proxy(engine.get_hiddens())
        phi_reward = -p_proxy_val * 0.01
        g_loss = g_adv_loss + 0.5 * ce_loss + phi_reward
        opt_g.zero_grad()
        g_loss.backward()
        torch.nn.utils.clip_grad_norm_(list(engine.trainable_parameters()), 1.0)
        opt_g.step()

        ce_val = ce_loss.item()
        if ce_start is None:
            ce_start = ce_val
        ce_end = ce_val

    hiddens = engine.get_hiddens()
    elapsed = time.time() - t0
    phi_val = rust_phi_value(hiddens)
    ce_s_str = f"{ce_start:.4f}" if ce_start is not None else "N/A"
    ce_e_str = f"{ce_end:.4f}" if ce_end is not None else "N/A"
    print(f"Φ={phi_val:.3f} CE={ce_s_str}->{ce_e_str} ({elapsed:.1f}s)")

    return {
        'name': name, 'phi_rs': phi_val,
        'ce_start': ce_start if ce_start is not None else 0,
        'ce_end': ce_end if ce_end is not None else 0,
        'time': elapsed, 'cells': n_cells,
        'hidden_shape': list(hiddens.shape),
    }


# ═══════════════════════════════════════════════════════════
# Complexity engine runner (MitosisEngine-based)
# ═══════════════════════════════════════════════════════════

def extract_mitosis_hiddens(engine):
    """Extract [n_cells, hidden_dim] tensor from MitosisEngine cells."""
    cells = engine.cells
    if not cells:
        return None
    hiddens = []
    for c in cells:
        h = c.hidden
        if isinstance(h, torch.Tensor):
            if h.dim() == 2:
                hiddens.append(h.squeeze(0))
            elif h.dim() == 1:
                hiddens.append(h)
        elif isinstance(h, np.ndarray):
            hiddens.append(torch.tensor(h, dtype=torch.float32).squeeze())
    if not hiddens:
        return None
    return torch.stack(hiddens)


def run_complexity_engine(runner_fn, name, n_cells=256, steps=300):
    """Run a complexity engine runner, capture the MitosisEngine, measure Φ with phi_rs.

    Uses monkey-patching to capture the engine from PhiCalculator.compute_phi calls.
    """
    print(f"\n  Running {name} ({n_cells}c, {steps}s)...", end=" ", flush=True)
    t0 = time.time()

    # Monkey-patch PhiCalculator to capture the last engine
    from consciousness_meter import PhiCalculator
    _captured_engine = [None]
    _original_compute_phi = PhiCalculator.compute_phi

    def _patched_compute_phi(self, engine_or_cells, *args, **kwargs):
        _captured_engine[0] = engine_or_cells
        return _original_compute_phi(self, engine_or_cells, *args, **kwargs)

    PhiCalculator.compute_phi = _patched_compute_phi

    try:
        result = runner_fn(steps=steps, n_cells=n_cells)
    except Exception as e:
        PhiCalculator.compute_phi = _original_compute_phi
        elapsed = time.time() - t0
        print(f"ERROR: {e} ({elapsed:.1f}s)")
        return {
            'name': name, 'phi_rs': 0.0, 'ce_start': 0, 'ce_end': 0,
            'time': elapsed, 'cells': n_cells, 'error': str(e),
        }
    finally:
        PhiCalculator.compute_phi = _original_compute_phi

    engine = _captured_engine[0]
    elapsed = time.time() - t0

    if engine is None:
        print(f"NODATA (no engine captured) ({elapsed:.1f}s)")
        return {
            'name': name, 'phi_rs': 0.0, 'phi_python': result.phi if hasattr(result, 'phi') else 0,
            'ce_start': 0, 'ce_end': 0, 'time': elapsed, 'cells': n_cells,
            'error': 'no engine captured',
        }

    hiddens = extract_mitosis_hiddens(engine)
    if hiddens is None:
        print(f"NODATA (hiddens extraction failed) ({elapsed:.1f}s)")
        return {
            'name': name, 'phi_rs': 0.0, 'phi_python': result.phi if hasattr(result, 'phi') else 0,
            'ce_start': 0, 'ce_end': 0, 'time': elapsed, 'cells': n_cells,
            'error': 'hiddens extraction failed',
        }

    phi_val = rust_phi_value(hiddens)
    phi_python = result.phi if hasattr(result, 'phi') else 0
    print(f"Φ(rs)={phi_val:.3f} Φ(py)={phi_python:.3f} ({elapsed:.1f}s)")

    return {
        'name': name, 'phi_rs': phi_val, 'phi_python': phi_python,
        'ce_start': 0, 'ce_end': 0, 'time': elapsed, 'cells': n_cells,
        'hidden_shape': list(hiddens.shape),
    }


# ═══════════════════════════════════════════════════════════
# Algebra engine runner (AlgebraCell-based)
# ═══════════════════════════════════════════════════════════

def run_algebra_engine(runner_fn, name, n_cells=256, steps=300):
    """Run an algebra engine runner, capture cell states, measure Φ with phi_rs.

    Uses monkey-patching on compute_phi_iit to capture cells.
    """
    print(f"\n  Running {name} ({n_cells}c, {steps}s)...", end=" ", flush=True)
    t0 = time.time()

    # Monkey-patch compute_phi_iit to capture cells
    import bench_algebra_engines as bae
    _captured_cells = [None]
    _original_compute = bae.compute_phi_iit

    def _patched_compute(cells, *args, **kwargs):
        _captured_cells[0] = cells
        return _original_compute(cells, *args, **kwargs)

    bae.compute_phi_iit = _patched_compute

    try:
        result = runner_fn(n_cells=n_cells, steps=steps)
    except Exception as e:
        bae.compute_phi_iit = _original_compute
        elapsed = time.time() - t0
        print(f"ERROR: {e} ({elapsed:.1f}s)")
        return {
            'name': name, 'phi_rs': 0.0, 'ce_start': 0, 'ce_end': 0,
            'time': elapsed, 'cells': n_cells, 'error': str(e),
        }
    finally:
        bae.compute_phi_iit = _original_compute

    cells = _captured_cells[0]
    elapsed = time.time() - t0

    if cells is None:
        print(f"NODATA (no cells captured) ({elapsed:.1f}s)")
        return {
            'name': name, 'phi_rs': 0.0, 'phi_python': result.phi if hasattr(result, 'phi') else 0,
            'ce_start': 0, 'ce_end': 0, 'time': elapsed, 'cells': n_cells,
            'error': 'no cells captured',
        }

    # Extract states from AlgebraCells
    states_list = []
    for c in cells:
        if hasattr(c, 'state') and isinstance(c.state, np.ndarray):
            states_list.append(c.state)
        elif hasattr(c, 'hidden'):
            h = c.hidden
            if isinstance(h, torch.Tensor):
                states_list.append(h.detach().cpu().numpy().flatten())
            elif isinstance(h, np.ndarray):
                states_list.append(h.flatten())

    if not states_list:
        print(f"NODATA (no states found) ({elapsed:.1f}s)")
        return {
            'name': name, 'phi_rs': 0.0, 'ce_start': 0, 'ce_end': 0,
            'time': elapsed, 'cells': n_cells, 'error': 'no states found',
        }

    states_np = np.stack(states_list).astype(np.float32)
    states_tensor = torch.tensor(states_np)
    phi_val = rust_phi_value(states_tensor)
    phi_python = result.phi if hasattr(result, 'phi') else 0
    print(f"Φ(rs)={phi_val:.3f} Φ(py)={phi_python:.3f} ({elapsed:.1f}s)")

    return {
        'name': name, 'phi_rs': phi_val, 'phi_python': phi_python,
        'ce_start': 0, 'ce_end': 0, 'time': elapsed, 'cells': n_cells,
        'hidden_shape': list(states_tensor.shape),
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cells', type=int, default=256)
    parser.add_argument('--steps', type=int, default=300)
    args = parser.parse_args()

    NC = args.cells
    STEPS = args.steps

    print("=" * 70)
    print(f"  Unmeasured Engine Φ Measurement — Rust phi_rs")
    print(f"  {NC} cells, {STEPS} steps")
    print("=" * 70)

    results = []

    # ─── bench_v8_arch.py ───
    print("\n── bench_v8_arch.py ──")
    from bench_v8_arch import (AttentionPhiEngine, MOCEEngine,
                                PhiAsLossEngine, AutopoieticEngine,
                                ConsciousnessGAN)

    arch_engines = [
        (AttentionPhiEngine, "ATTENTION_PHI"),
        (PhiAsLossEngine, "PHI_AS_LOSS"),
        (AutopoieticEngine, "AUTOPOIETIC"),
    ]

    for cls, name in arch_engines:
        try:
            r = run_v8_engine(cls, name, n_cells=NC, steps=STEPS)
            results.append(r)
        except Exception as e:
            print(f"  {name}: FAILED — {e}")
            results.append({'name': name, 'phi_rs': 0.0, 'error': str(e), 'cells': NC})

    # MOCE: special constructor (n_experts, cells_per_expert)
    try:
        n_experts = 8
        cells_per = NC // n_experts
        print(f"\n  Running MOCE ({n_experts}x{cells_per}c={NC}c, {STEPS}s)...", end=" ", flush=True)
        t0 = time.time()
        engine = MOCEEngine(n_experts, cells_per, 64, 128, 64)
        params = list(engine.trainable_parameters())
        optimizer = torch.optim.Adam(params, lr=1e-3)
        ce_start_v, ce_end_v = None, None
        for step in range(STEPS):
            x = torch.randn(1, 64)
            target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1
            combined, tension, _ = engine.process(x, step=step)
            pred = engine.output_head(combined)
            loss = F.mse_loss(pred, target)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            optimizer.step()
            if ce_start_v is None:
                ce_start_v = loss.item()
            ce_end_v = loss.item()
        hiddens = engine.get_hiddens()
        phi_val = rust_phi_value(hiddens)
        elapsed = time.time() - t0
        ce_s_str = f"{ce_start_v:.4f}" if ce_start_v else "N/A"
        ce_e_str = f"{ce_end_v:.4f}" if ce_end_v else "N/A"
        print(f"Φ={phi_val:.3f} CE={ce_s_str}->{ce_e_str} ({elapsed:.1f}s)")
        results.append({
            'name': 'MOCE', 'phi_rs': phi_val,
            'ce_start': ce_start_v or 0, 'ce_end': ce_end_v or 0,
            'time': elapsed, 'cells': NC, 'hidden_shape': list(hiddens.shape),
        })
    except Exception as e:
        print(f"FAILED — {e}")
        results.append({'name': 'MOCE', 'phi_rs': 0.0, 'error': str(e), 'cells': NC})

    # GAN needs special handling (two optimizers)
    try:
        r = run_gan_engine(n_cells=NC, steps=STEPS)
        results.append(r)
    except Exception as e:
        print(f"  CONSCIOUSNESS_GAN: FAILED — {e}")
        results.append({'name': 'CONSCIOUSNESS_GAN', 'phi_rs': 0.0, 'error': str(e), 'cells': NC})

    # ─── bench_v8_quantum.py ───
    print("\n── bench_v8_quantum.py ──")
    from bench_v8_quantum import EntangledPairsEngine, DecoherenceEngine

    quantum_engines = [
        (EntangledPairsEngine, "Q2_ENTANGLED_PAIRS"),
        (DecoherenceEngine, "Q5_DECOHERENCE"),
    ]

    for cls, name in quantum_engines:
        try:
            r = run_v8_engine(cls, name, n_cells=NC, steps=STEPS)
            results.append(r)
        except Exception as e:
            print(f"  {name}: FAILED — {e}")
            results.append({'name': name, 'phi_rs': 0.0, 'error': str(e), 'cells': NC})

    # ─── bench_v8_bio.py ───
    print("\n── bench_v8_bio.py ──")
    from bench_v8_bio import (CorticalColumnsEngine, ThalamicGateEngine,
                               DefaultModeNetworkEngine, GlobalWorkspaceEngine,
                               PredictiveHierarchyEngine, NeuralDarwinismEngine)

    bio_engines = [
        (CorticalColumnsEngine, "B1_CORTICAL_COLUMNS"),
        (ThalamicGateEngine, "B2_THALAMIC_GATE"),
        (DefaultModeNetworkEngine, "B3_DEFAULT_MODE_NETWORK"),
        (GlobalWorkspaceEngine, "B4_GLOBAL_WORKSPACE"),
        (PredictiveHierarchyEngine, "B5_PREDICTIVE_HIERARCHY"),
        (NeuralDarwinismEngine, "B6_NEURAL_DARWINISM"),
    ]

    for cls, name in bio_engines:
        try:
            r = run_v8_engine(cls, name, n_cells=NC, steps=STEPS)
            results.append(r)
        except Exception as e:
            print(f"  {name}: FAILED — {e}")
            results.append({'name': name, 'phi_rs': 0.0, 'error': str(e), 'cells': NC})

    # ─── bench_v8_math.py ───
    print("\n── bench_v8_math.py ──")
    from bench_v8_math import AlgebraicEngine

    try:
        r = run_v8_engine(AlgebraicEngine, "M4_ALGEBRAIC", n_cells=NC, steps=STEPS)
        results.append(r)
    except Exception as e:
        print(f"  M4_ALGEBRAIC: FAILED — {e}")
        results.append({'name': 'M4_ALGEBRAIC', 'phi_rs': 0.0, 'error': str(e), 'cells': NC})

    # ─── bench_complexity_engines.py ───
    print("\n── bench_complexity_engines.py ──")
    from bench_complexity_engines import (run_CMP1_turing_machine, run_CMP2_rule110,
                                           run_CMP3_lambda_calculus, run_CMP4_game_of_life,
                                           run_CMP6_goedel_incompleteness)

    complexity_runners = [
        (run_CMP1_turing_machine, "CMP-1_TURING_MACHINE"),
        (run_CMP2_rule110, "CMP-2_RULE110"),
        (run_CMP3_lambda_calculus, "CMP-3_LAMBDA_CALCULUS"),
        (run_CMP4_game_of_life, "CMP-4_GAME_OF_LIFE"),
        (run_CMP6_goedel_incompleteness, "CMP-6_GOEDEL"),
    ]

    for runner, name in complexity_runners:
        try:
            r = run_complexity_engine(runner, name, n_cells=NC, steps=STEPS)
            results.append(r)
        except Exception as e:
            print(f"  {name}: FAILED — {e}")
            results.append({'name': name, 'phi_rs': 0.0, 'error': str(e), 'cells': NC})

    # ─── bench_algebra_engines.py ───
    print("\n── bench_algebra_engines.py ──")
    from bench_algebra_engines import (run_ALG1_group_consciousness,
                                        run_ALG2_ring_theory,
                                        run_ALG3_galois_field,
                                        run_ALG4_lie_algebra,
                                        run_ALG5_hopf_algebra,
                                        run_ALG6_topos)

    algebra_runners = [
        (run_ALG1_group_consciousness, "ALG-1_GROUP"),
        (run_ALG2_ring_theory, "ALG-2_RING"),
        (run_ALG3_galois_field, "ALG-3_GALOIS"),
        (run_ALG4_lie_algebra, "ALG-4_LIE"),
        (run_ALG5_hopf_algebra, "ALG-5_HOPF"),
        (run_ALG6_topos, "ALG-6_TOPOS"),
    ]

    for runner, name in algebra_runners:
        try:
            r = run_algebra_engine(runner, name, n_cells=NC, steps=STEPS)
            results.append(r)
        except Exception as e:
            print(f"  {name}: FAILED — {e}")
            results.append({'name': name, 'phi_rs': 0.0, 'error': str(e), 'cells': NC})

    # ═══ Summary ═══
    print("\n" + "=" * 70)
    print(f"  RESULTS SUMMARY — Rust phi_rs, {NC}c, {STEPS} steps")
    print("=" * 70)

    # Sort by phi_rs descending
    results.sort(key=lambda r: r.get('phi_rs', 0), reverse=True)

    print(f"\n  {'Name':<30s} | {'Φ(rs)':>8s} | {'CE start':>9s} | {'CE end':>9s} | {'Time':>6s} | {'Shape'}")
    print(f"  {'-'*30}-+-{'-'*8}-+-{'-'*9}-+-{'-'*9}-+-{'-'*6}-+-{'-'*12}")

    for r in results:
        name = r.get('name', '?')
        phi = r.get('phi_rs', 0)
        ce_s = r.get('ce_start', 0)
        ce_e = r.get('ce_end', 0)
        t = r.get('time', 0)
        shape = r.get('hidden_shape', r.get('error', 'N/A'))

        ce_s_str = f"{ce_s:.4f}" if isinstance(ce_s, float) and ce_s > 0 else "N/A"
        ce_e_str = f"{ce_e:.4f}" if isinstance(ce_e, float) and ce_e > 0 else "N/A"

        print(f"  {name:<30s} | {phi:>8.3f} | {ce_s_str:>9s} | {ce_e_str:>9s} | {t:>5.1f}s | {shape}")

    # Markdown table for ENGINE-ALL-RESULTS.md
    print("\n\n── Markdown Table (for ENGINE-ALL-RESULTS.md) ──\n")
    print(f"| Rank | Engine | Source | cells | Φ(rs) | CE start | CE end |")
    print(f"|------|--------|--------|-------|-------|----------|--------|")
    for i, r in enumerate(results, 1):
        name = r.get('name', '?')
        phi = r.get('phi_rs', 0)
        ce_s = r.get('ce_start', 0)
        ce_e = r.get('ce_end', 0)
        source = 'v8_arch' if 'ATTENTION' in name or 'MOCE' in name or 'PHI_AS' in name or 'AUTO' in name or 'GAN' in name else \
                 'v8_quantum' if 'Q2' in name or 'Q5' in name else \
                 'v8_bio' if name.startswith('B') else \
                 'v8_math' if 'M4' in name else \
                 'complexity' if 'CMP' in name else \
                 'algebra' if 'ALG' in name else '?'

        ce_s_str = f"{ce_s:.4f}" if isinstance(ce_s, float) and ce_s > 0 else "—"
        ce_e_str = f"{ce_e:.4f}" if isinstance(ce_e, float) and ce_e > 0 else "—"

        print(f"| {i} | {name} | {source} | {NC} | **{phi:.3f}** | {ce_s_str} | {ce_e_str} |")

    # Save JSON
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', f'measure_v8_phi_rs_{NC}c.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nJSON saved: {out_path}")

    # Count successes
    measured = sum(1 for r in results if r.get('phi_rs', 0) > 0)
    total = len(results)
    print(f"\n  Measured: {measured}/{total} engines")
    print(f"  Errors: {total - measured}/{total}")


if __name__ == '__main__':
    main()
