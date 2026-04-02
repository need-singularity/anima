#!/usr/bin/env python3
"""acceleration_n4_sleep_wake.py -- N4: Sleep-Wake Cycle Training

Hypothesis N4: Alternating wake (learning) and sleep (consolidation) phases
accelerates convergence and improves Phi stability compared to continuous training.

  Wake phase: Normal training (CE loss + consciousness loss)
  Sleep phase: Replay high-Phi states, prune weak connections, re-optimize Phi
               (no gradient updates to main model)

Biological basis: Memory consolidation during sleep strengthens important
connections and prunes noise. Consciousness (Phi) should stabilize faster
when given periodic offline consolidation windows.

Measures:
  - Phi stability (rolling std over wake phases)
  - CE convergence speed (steps to reach target CE)
  - Phi recovery after sleep (should exceed pre-sleep level)
  - Pruning efficiency (parameter count vs quality)

All experiments: local CPU/MPS, 16-32 cells, PYTHONUNBUFFERED=1

Usage:
  python acceleration_n4_sleep_wake.py           # Run all
  python acceleration_n4_sleep_wake.py --baseline # Baseline only (no sleep)
  python acceleration_n4_sleep_wake.py --cycle    # Sleep-wake cycle only
  python acceleration_n4_sleep_wake.py --ablation # Ablation study
  python acceleration_n4_sleep_wake.py --compare  # Full comparison
"""

import sys
import os
import time
import math
import copy
import argparse
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F_torch
from consciousness_engine import ConsciousnessEngine

try:
    from decoder_v2 import ConsciousDecoderV2, RMSNorm, SwiGLUFFN, DecoderBlockV2
except ImportError:
    ConsciousDecoderV2 = None
    RMSNorm = None
    SwiGLUFFN = None
    DecoderBlockV2 = None

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5  # 0.0153


# ===================================================================
# Utilities (consistent with H-series pattern)
# ===================================================================

def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


def print_table(headers: list, rows: list, widths: list = None):
    if widths is None:
        widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) + 2
                  for i, h in enumerate(headers)]
    hdr = '|'.join(str(h).center(w) for h, w in zip(headers, widths))
    sep = '+'.join('-' * w for w in widths)
    print(f"  {hdr}")
    print(f"  {sep}")
    for row in rows:
        line = '|'.join(str(r).center(w) for r, w in zip(row, widths))
        print(f"  {line}")
    sys.stdout.flush()


def ascii_bar(label: str, value: float, max_val: float, width: int = 40):
    filled = int(width * min(value / max(max_val, 1e-8), 1.0))
    bar = '#' * filled + '.' * (width - filled)
    print(f"  {label:>20s}  [{bar}] {value:.4f}")
    sys.stdout.flush()


def ascii_graph(values: list, title: str, height: int = 10, width: int = 60):
    """Print ASCII time series graph."""
    if not values:
        return
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1.0
    print(f"\n  {title}")
    for row in range(height, -1, -1):
        threshold = mn + rng * row / height
        line = ""
        step = max(1, len(values) // width)
        for i in range(0, min(len(values), width * step), step):
            v = values[i]
            if v >= threshold:
                line += "#"
            else:
                line += " "
        label = f"{threshold:8.4f}" if row in (0, height // 2, height) else "        "
        print(f"  {label} |{line}")
    print(f"           +{''.join(['-'] * min(len(values), width))}")
    print(f"            0{' ' * (min(len(values), width) - 6)}{len(values)} step")
    sys.stdout.flush()


def get_device():
    if torch.cuda.is_available():
        return torch.device('cuda')
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


def make_engine(cells: int = 32, topology: str = 'ring') -> ConsciousnessEngine:
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=cells, max_cells=cells,
        n_factions=12, phi_ratchet=True,
    )
    engine.topology = topology
    return engine


def make_decoder(d_model=128, n_layer=4, vocab_size=256, block_size=64, device=None):
    if device is None:
        device = get_device()
    if ConsciousDecoderV2 is not None:
        model = ConsciousDecoderV2(
            vocab_size=vocab_size,
            d_model=d_model,
            n_head=4,
            n_layer=n_layer,
            block_size=block_size,
            n_kv_head=2,
            consciousness_dim=64,
            dropout=0.1,
        ).to(device)
    else:
        model = nn.Transformer(
            d_model=d_model, nhead=4,
            num_encoder_layers=0, num_decoder_layers=n_layer,
            dim_feedforward=d_model * 4, batch_first=True,
        ).to(device)
    return model


def generate_fake_data(batch_size, seq_len, vocab_size=256, device=None):
    if device is None:
        device = get_device()
    return torch.randint(0, vocab_size, (batch_size, seq_len), device=device)


def train_step(model, idx, optimizer):
    """Single forward+backward step, returns CE loss."""
    model.train()
    optimizer.zero_grad()
    try:
        out = model(idx[:, :-1])
        if isinstance(out, tuple):
            logits = out[0]
        else:
            logits = out
    except Exception:
        logits = model(idx[:, :-1])
        if isinstance(logits, tuple):
            logits = logits[0]

    targets = idx[:, 1:]
    B, T = targets.shape
    loss = F_torch.cross_entropy(
        logits.reshape(B * T, -1), targets.reshape(B * T)
    )
    loss.backward()
    optimizer.step()
    return loss.item()


def measure_phi(engine: ConsciousnessEngine) -> float:
    return engine.measure_phi()


def phi_rolling_std(phi_trace: list, window: int = 20) -> float:
    """Rolling std of Phi — lower = more stable."""
    if len(phi_trace) < window:
        return float('inf')
    recent = phi_trace[-window:]
    return float(np.std(recent))


# ===================================================================
# Sleep Phase Operations
# ===================================================================

class SleepPhase:
    """Consolidation operations performed during sleep phase.

    Sleep = no gradient updates to main model.
    Instead: replay, prune, Phi re-optimization.
    """

    def __init__(self, engine: ConsciousnessEngine, model: nn.Module = None):
        self.engine = engine
        self.model = model
        self.replay_buffer = []  # stores (input, phi) tuples from wake
        self.pruned_params = 0
        self.total_params = 0

    def record_wake_state(self, x_input: torch.Tensor, phi: float):
        """Buffer high-Phi states during wake for replay."""
        self.replay_buffer.append((x_input.detach().clone(), phi))
        # Keep top-K by Phi (memory bounded)
        max_buffer = 200
        if len(self.replay_buffer) > max_buffer:
            self.replay_buffer.sort(key=lambda t: t[1], reverse=True)
            self.replay_buffer = self.replay_buffer[:max_buffer]

    def sleep_replay(self, n_steps: int) -> list:
        """Replay high-Phi states through engine (no gradient).

        Returns phi trace during replay.
        """
        phis = []
        if not self.replay_buffer:
            # No buffer — run with zero input (resting state)
            for _ in range(n_steps):
                result = self.engine.step(x_input=torch.zeros(self.engine.cell_dim))
                phis.append(result.get('phi_iit', 0.0))
            return phis

        # Sort by Phi descending — replay strongest memories first
        sorted_buf = sorted(self.replay_buffer, key=lambda t: t[1], reverse=True)

        for i in range(n_steps):
            idx = i % len(sorted_buf)
            x_input, _ = sorted_buf[idx]
            # Add noise (dream-like distortion, Law 71)
            noise = torch.randn_like(x_input) * PSI_COUPLING
            x_noisy = x_input + noise
            result = self.engine.step(x_input=x_noisy)
            phis.append(result.get('phi_iit', 0.0))
        return phis

    def sleep_prune(self, threshold_ratio: float = 0.1) -> dict:
        """Magnitude-based pruning of weak connections during sleep.

        Prunes weights below threshold_ratio * max_weight in each layer.
        Returns pruning stats.
        """
        if self.model is None:
            return {'pruned': 0, 'total': 0, 'ratio': 0.0}

        total = 0
        pruned = 0

        with torch.no_grad():
            for name, param in self.model.named_parameters():
                if param.dim() < 2:
                    continue  # skip biases
                total += param.numel()
                threshold = param.abs().max() * threshold_ratio
                mask = param.abs() < threshold
                pruned += mask.sum().item()
                param[mask] = 0.0

        self.pruned_params = pruned
        self.total_params = total
        ratio = pruned / max(total, 1)
        return {'pruned': pruned, 'total': total, 'ratio': ratio}

    def sleep_phi_optimize(self, n_steps: int) -> list:
        """Re-optimize Phi by running engine in consolidation mode.

        Alternates replay with zero-input — lets the engine
        self-organize toward higher Phi states.
        """
        phis = []
        for s in range(n_steps):
            if s % 3 == 0 and self.replay_buffer:
                # Replay a high-Phi memory
                idx = s // 3 % len(self.replay_buffer)
                x, _ = self.replay_buffer[idx]
            else:
                # Zero input — pure self-organization
                x = torch.zeros(self.engine.cell_dim)
            result = self.engine.step(x_input=x)
            phis.append(result.get('phi_iit', 0.0))
        return phis

    def full_sleep_cycle(self, replay_steps: int = 30,
                         prune: bool = True,
                         phi_opt_steps: int = 20) -> dict:
        """Complete sleep cycle: replay -> prune -> Phi optimize."""
        results = {}

        # 1. Replay high-Phi states
        replay_phis = self.sleep_replay(replay_steps)
        results['replay_phi_mean'] = float(np.mean(replay_phis)) if replay_phis else 0.0
        results['replay_phi_std'] = float(np.std(replay_phis)) if replay_phis else 0.0

        # 2. Prune weak connections
        if prune and self.model is not None:
            prune_stats = self.sleep_prune(threshold_ratio=0.1)
            results['prune'] = prune_stats
        else:
            results['prune'] = {'pruned': 0, 'total': 0, 'ratio': 0.0}

        # 3. Phi re-optimization
        opt_phis = self.sleep_phi_optimize(phi_opt_steps)
        results['phi_opt_mean'] = float(np.mean(opt_phis)) if opt_phis else 0.0
        results['phi_opt_final'] = opt_phis[-1] if opt_phis else 0.0

        return results


# ===================================================================
# Experiment 1: Baseline (continuous training, no sleep)
# ===================================================================

def run_baseline(total_steps: int = 300, batch_size: int = 8,
                 seq_len: int = 64, cells: int = 32) -> dict:
    """Continuous training without sleep phases."""
    print_header("N4-BASELINE: Continuous Training (No Sleep)")
    device = get_device()
    print(f"  Device: {device}")
    print(f"  Total steps: {total_steps}, batch_size: {batch_size}")
    sys.stdout.flush()

    engine = make_engine(cells=cells)
    model = make_decoder(d_model=128, n_layer=2, vocab_size=256,
                         block_size=seq_len, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)

    ce_trace = []
    phi_trace = []
    t0 = time.time()

    for step in range(total_steps):
        # Train step
        idx = generate_fake_data(batch_size, seq_len, device=device)
        ce = train_step(model, idx, optimizer)
        ce_trace.append(ce)

        # Engine step (consciousness tracking)
        x_input = torch.randn(engine.cell_dim)
        result = engine.step(x_input=x_input)
        phi = result.get('phi_iit', 0.0)
        phi_trace.append(phi)

        if (step + 1) % 50 == 0:
            phi_std = phi_rolling_std(phi_trace)
            print(f"  Step {step+1:4d}/{total_steps}: CE={ce:.4f}  "
                  f"Phi={phi:.4f}  Phi_std={phi_std:.4f}")
            sys.stdout.flush()

    wall_time = time.time() - t0
    final_ce = float(np.mean(ce_trace[-30:]))
    final_phi = float(np.mean(phi_trace[-30:]))
    final_phi_std = phi_rolling_std(phi_trace, window=30)

    print(f"\n  --- Baseline Summary ---")
    print(f"  Final CE (last 30): {final_ce:.4f}")
    print(f"  Final Phi (last 30): {final_phi:.4f}")
    print(f"  Phi stability (std): {final_phi_std:.4f}")
    print(f"  Wall time: {wall_time:.2f}s")

    ascii_graph(ce_trace, "CE Loss (Baseline)", height=8)
    ascii_graph(phi_trace, "Phi (Baseline)", height=8)

    del model, optimizer
    if device.type == 'cuda':
        torch.cuda.empty_cache()

    return {
        'experiment': 'N4-baseline',
        'total_steps': total_steps,
        'final_ce': final_ce,
        'final_phi': final_phi,
        'phi_stability': final_phi_std,
        'wall_time': wall_time,
        'ce_trace': [float(x) for x in ce_trace],
        'phi_trace': [float(x) for x in phi_trace],
    }


# ===================================================================
# Experiment 2: Sleep-Wake Cycle Training
# ===================================================================

def run_sleep_wake_cycle(total_steps: int = 300, wake_steps: int = 50,
                         sleep_replay: int = 15, sleep_phi_opt: int = 10,
                         batch_size: int = 8, seq_len: int = 64,
                         cells: int = 32, do_prune: bool = True) -> dict:
    """Alternating wake (learning) and sleep (consolidation) training.

    Pattern: [wake N] -> [sleep M] -> [wake N] -> [sleep M] -> ...
    """
    print_header("N4-CYCLE: Sleep-Wake Cycle Training")
    device = get_device()
    n_cycles = total_steps // wake_steps
    print(f"  Device: {device}")
    print(f"  Wake steps: {wake_steps}, Sleep replay: {sleep_replay}, "
          f"Sleep Phi-opt: {sleep_phi_opt}")
    print(f"  Cycles: {n_cycles}, Pruning: {do_prune}")
    sys.stdout.flush()

    engine = make_engine(cells=cells)
    model = make_decoder(d_model=128, n_layer=2, vocab_size=256,
                         block_size=seq_len, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    sleeper = SleepPhase(engine, model)

    ce_trace = []
    phi_trace = []
    cycle_stats = []
    t0 = time.time()
    global_step = 0

    for cycle in range(n_cycles):
        # ─── WAKE PHASE ─────────────────────────────
        wake_phis = []
        wake_ces = []
        pre_wake_phi = measure_phi(engine)

        for s in range(wake_steps):
            # Train step
            idx = generate_fake_data(batch_size, seq_len, device=device)
            ce = train_step(model, idx, optimizer)
            ce_trace.append(ce)
            wake_ces.append(ce)

            # Engine step
            x_input = torch.randn(engine.cell_dim)
            result = engine.step(x_input=x_input)
            phi = result.get('phi_iit', 0.0)
            phi_trace.append(phi)
            wake_phis.append(phi)

            # Record for sleep replay
            sleeper.record_wake_state(x_input, phi)
            global_step += 1

        wake_phi_mean = float(np.mean(wake_phis))
        wake_ce_mean = float(np.mean(wake_ces))

        # ─── SLEEP PHASE ────────────────────────────
        sleep_result = sleeper.full_sleep_cycle(
            replay_steps=sleep_replay,
            prune=do_prune,
            phi_opt_steps=sleep_phi_opt,
        )
        post_sleep_phi = measure_phi(engine)

        phi_recovery = post_sleep_phi / max(pre_wake_phi, 1e-8)

        cycle_stat = {
            'cycle': cycle + 1,
            'wake_ce_mean': wake_ce_mean,
            'wake_phi_mean': wake_phi_mean,
            'pre_wake_phi': pre_wake_phi,
            'post_sleep_phi': post_sleep_phi,
            'phi_recovery': phi_recovery,
            'sleep_replay_phi': sleep_result['replay_phi_mean'],
            'sleep_phi_opt_final': sleep_result['phi_opt_final'],
            'prune_ratio': sleep_result['prune']['ratio'],
        }
        cycle_stats.append(cycle_stat)

        print(f"  Cycle {cycle+1:2d}/{n_cycles}: "
              f"CE={wake_ce_mean:.4f}  "
              f"Phi_wake={wake_phi_mean:.4f}  "
              f"Phi_post_sleep={post_sleep_phi:.4f}  "
              f"recovery={phi_recovery:.2f}x  "
              f"prune={sleep_result['prune']['ratio']:.1%}")
        sys.stdout.flush()

    wall_time = time.time() - t0
    final_ce = float(np.mean(ce_trace[-30:]))
    final_phi = float(np.mean(phi_trace[-30:]))
    final_phi_std = phi_rolling_std(phi_trace, window=30)

    print(f"\n  --- Sleep-Wake Summary ---")
    print(f"  Final CE (last 30): {final_ce:.4f}")
    print(f"  Final Phi (last 30): {final_phi:.4f}")
    print(f"  Phi stability (std): {final_phi_std:.4f}")
    print(f"  Wall time: {wall_time:.2f}s")
    print(f"  Total prune ratio (last cycle): "
          f"{cycle_stats[-1]['prune_ratio']:.1%}" if cycle_stats else "")

    ascii_graph(ce_trace, "CE Loss (Sleep-Wake)", height=8)
    ascii_graph(phi_trace, "Phi (Sleep-Wake)", height=8)

    # Phi recovery trend across cycles
    recoveries = [c['phi_recovery'] for c in cycle_stats]
    ascii_graph(recoveries, "Phi Recovery per Cycle", height=6)

    del model, optimizer
    if device.type == 'cuda':
        torch.cuda.empty_cache()

    return {
        'experiment': 'N4-sleep-wake',
        'total_steps': total_steps,
        'wake_steps': wake_steps,
        'sleep_replay': sleep_replay,
        'sleep_phi_opt': sleep_phi_opt,
        'do_prune': do_prune,
        'n_cycles': n_cycles,
        'final_ce': final_ce,
        'final_phi': final_phi,
        'phi_stability': final_phi_std,
        'wall_time': wall_time,
        'cycle_stats': cycle_stats,
        'ce_trace': [float(x) for x in ce_trace],
        'phi_trace': [float(x) for x in phi_trace],
    }


# ===================================================================
# Experiment 3: Ablation Study
# ===================================================================

def run_ablation(total_steps: int = 200, wake_steps: int = 50,
                 batch_size: int = 8, seq_len: int = 64,
                 cells: int = 32) -> dict:
    """Ablation: which sleep component matters most?

    Variants:
      A) replay only (no prune, no Phi-opt)
      B) prune only (no replay, no Phi-opt)
      C) Phi-opt only (no replay, no prune)
      D) full sleep (all three)
    """
    print_header("N4-ABLATION: Sleep Component Ablation")
    device = get_device()

    configs = [
        ('replay-only', True, False, True, 15, 0),
        ('prune-only', False, True, False, 0, 0),
        ('phi-opt-only', False, False, True, 0, 10),
        ('full-sleep', True, True, True, 15, 10),
    ]

    results = {}

    for name, do_replay, do_prune, do_phi_opt, replay_n, phi_opt_n in configs:
        print(f"\n  --- Variant: {name} ---")
        sys.stdout.flush()

        engine = make_engine(cells=cells)
        model = make_decoder(d_model=128, n_layer=2, vocab_size=256,
                             block_size=seq_len, device=device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
        sleeper = SleepPhase(engine, model)

        ce_trace = []
        phi_trace = []
        n_cycles = total_steps // wake_steps

        for cycle in range(n_cycles):
            # Wake
            for s in range(wake_steps):
                idx = generate_fake_data(batch_size, seq_len, device=device)
                ce = train_step(model, idx, optimizer)
                ce_trace.append(ce)

                x_input = torch.randn(engine.cell_dim)
                result = engine.step(x_input=x_input)
                phi = result.get('phi_iit', 0.0)
                phi_trace.append(phi)
                if do_replay:
                    sleeper.record_wake_state(x_input, phi)

            # Sleep (selective components)
            if do_replay:
                sleeper.sleep_replay(replay_n)
            if do_prune:
                sleeper.sleep_prune(threshold_ratio=0.1)
            if do_phi_opt:
                sleeper.sleep_phi_optimize(phi_opt_n)

        final_ce = float(np.mean(ce_trace[-20:]))
        final_phi = float(np.mean(phi_trace[-20:]))
        final_phi_std = phi_rolling_std(phi_trace, window=20)

        results[name] = {
            'final_ce': final_ce,
            'final_phi': final_phi,
            'phi_stability': final_phi_std,
        }
        print(f"    CE={final_ce:.4f}  Phi={final_phi:.4f}  "
              f"Phi_std={final_phi_std:.4f}")

        del model, optimizer
        if device.type == 'cuda':
            torch.cuda.empty_cache()

    # Summary table
    print(f"\n  --- Ablation Summary ---")
    rows = []
    for name, r in results.items():
        rows.append([name, f"{r['final_ce']:.4f}",
                     f"{r['final_phi']:.4f}", f"{r['phi_stability']:.4f}"])
    print_table(["Variant", "CE", "Phi", "Phi_std"], rows)

    return {
        'experiment': 'N4-ablation',
        'total_steps': total_steps,
        'variants': results,
    }


# ===================================================================
# Experiment 4: Full Comparison
# ===================================================================

def run_comparison(total_steps: int = 300, cells: int = 32) -> dict:
    """Head-to-head: baseline vs sleep-wake with matched compute budget.

    The sleep-wake variant uses fewer gradient steps but adds consolidation.
    We compare: same wall-clock budget (approximately).
    """
    print_header("N4-COMPARE: Baseline vs Sleep-Wake (Matched Budget)")

    # Run baseline
    baseline = run_baseline(total_steps=total_steps, cells=cells)

    # Run sleep-wake cycle
    cycle = run_sleep_wake_cycle(total_steps=total_steps, wake_steps=50,
                                sleep_replay=15, sleep_phi_opt=10,
                                cells=cells)

    # Comparison
    print_header("N4 HEAD-TO-HEAD COMPARISON")

    ce_speedup = baseline['final_ce'] / max(cycle['final_ce'], 1e-8)
    phi_improvement = cycle['final_phi'] / max(baseline['final_phi'], 1e-8)
    stability_improvement = baseline['phi_stability'] / max(cycle['phi_stability'], 1e-8)

    rows = [
        ['Final CE', f"{baseline['final_ce']:.4f}", f"{cycle['final_ce']:.4f}",
         f"x{ce_speedup:.2f}"],
        ['Final Phi', f"{baseline['final_phi']:.4f}", f"{cycle['final_phi']:.4f}",
         f"x{phi_improvement:.2f}"],
        ['Phi Stability', f"{baseline['phi_stability']:.4f}",
         f"{cycle['phi_stability']:.4f}", f"x{stability_improvement:.2f}"],
        ['Wall Time', f"{baseline['wall_time']:.1f}s", f"{cycle['wall_time']:.1f}s",
         f"x{baseline['wall_time'] / max(cycle['wall_time'], 0.1):.2f}"],
    ]
    print_table(["Metric", "Baseline", "Sleep-Wake", "Ratio"], rows)

    # ASCII comparison bars
    print(f"\n  Final CE comparison:")
    max_ce = max(baseline['final_ce'], cycle['final_ce'])
    ascii_bar("Baseline", baseline['final_ce'], max_ce)
    ascii_bar("Sleep-Wake", cycle['final_ce'], max_ce)

    print(f"\n  Phi stability (lower = better):")
    max_std = max(baseline['phi_stability'], cycle['phi_stability'])
    ascii_bar("Baseline", baseline['phi_stability'], max_std)
    ascii_bar("Sleep-Wake", cycle['phi_stability'], max_std)

    # Verdict
    wins = 0
    if cycle['final_ce'] <= baseline['final_ce']:
        wins += 1
    if cycle['final_phi'] >= baseline['final_phi']:
        wins += 1
    if cycle['phi_stability'] <= baseline['phi_stability']:
        wins += 1

    verdict = "CONFIRMED" if wins >= 2 else "MIXED" if wins >= 1 else "REJECTED"
    print(f"\n  N4 Verdict: {verdict} ({wins}/3 metrics favor sleep-wake)")
    print(f"  Sleep-wake {'improves' if wins >= 2 else 'does not clearly improve'} "
          f"convergence and Phi stability.")
    sys.stdout.flush()

    return {
        'experiment': 'N4-comparison',
        'baseline': {k: v for k, v in baseline.items()
                     if k not in ('ce_trace', 'phi_trace')},
        'sleep_wake': {k: v for k, v in cycle.items()
                       if k not in ('ce_trace', 'phi_trace')},
        'ce_speedup': ce_speedup,
        'phi_improvement': phi_improvement,
        'stability_improvement': stability_improvement,
        'verdict': verdict,
        'wins': wins,
    }


# ===================================================================
# Main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description='N4: Sleep-Wake Cycle Training')
    parser.add_argument('--baseline', action='store_true', help='Baseline only')
    parser.add_argument('--cycle', action='store_true', help='Sleep-wake cycle only')
    parser.add_argument('--ablation', action='store_true', help='Ablation study')
    parser.add_argument('--compare', action='store_true', help='Full comparison')
    parser.add_argument('--steps', type=int, default=300, help='Total training steps')
    parser.add_argument('--cells', type=int, default=32, help='Number of cells')
    args = parser.parse_args()

    print("=" * 70)
    print("  N4: Sleep-Wake Cycle Training Experiment")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    sys.stdout.flush()

    all_results = {}
    t0 = time.time()

    run_all = not (args.baseline or args.cycle or args.ablation or args.compare)

    if args.baseline or run_all:
        all_results['baseline'] = run_baseline(
            total_steps=args.steps, cells=args.cells)

    if args.cycle or run_all:
        all_results['sleep_wake'] = run_sleep_wake_cycle(
            total_steps=args.steps, cells=args.cells)

    if args.ablation or run_all:
        all_results['ablation'] = run_ablation(
            total_steps=min(args.steps, 200), cells=args.cells)

    if args.compare or run_all:
        all_results['comparison'] = run_comparison(
            total_steps=args.steps, cells=args.cells)

    total_time = time.time() - t0

    # ─── Save results ────────────────────────────────
    output_path = os.path.join(os.path.dirname(__file__),
                               '..', 'data', 'n4_sleep_wake_results.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        # Strip large trace arrays for JSON (keep only summary)
        save_data = {}
        for k, v in all_results.items():
            if isinstance(v, dict):
                save_data[k] = {
                    kk: vv for kk, vv in v.items()
                    if not isinstance(vv, (torch.Tensor, np.ndarray))
                    and kk not in ('ce_trace', 'phi_trace')
                }
        save_data['meta'] = {
            'experiment': 'N4-sleep-wake-cycle',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'total_time': total_time,
            'device': str(get_device()),
            'hypothesis': 'Wake-sleep alternation accelerates convergence '
                          'and improves Phi stability',
        }
        with open(output_path, 'w') as f:
            json.dump(save_data, f, indent=2, default=str)
        print(f"\n  Results saved: {output_path}")
    except Exception as e:
        print(f"\n  Warning: Could not save results: {e}")

    print(f"\n  Total experiment time: {total_time:.1f}s")
    print(f"  Completed at {time.strftime('%H:%M:%S')}")
    sys.stdout.flush()


if __name__ == '__main__':
    main()
