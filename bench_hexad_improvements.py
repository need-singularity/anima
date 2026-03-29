#!/usr/bin/env python3
"""bench_hexad_improvements.py — Hexad improvement hypotheses benchmark

Three high-impact improvements to the Trinity/Hexad architecture:

  B-1: Bidirectional Bridge
       D's CE loss feeds back to C as a feedback tensor (no gradient leak).
       C reads [ce_loss, phi_change] next step -> adjusts consciousness dynamics.

  D-2: Per-Layer Adapter
       Inject C signal at every transformer layer, not just embedding.
       Small adapter (Linear(d_model, d_model)) at each layer adds C signal.

  S-2: Predictive Sense
       Predict next input, use prediction error as surprise signal.
       Surprise modulates C's step strength.

Each: MitosisC(32 cells), 50 steps, measure CE + Phi.
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
import time
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Dict, Any, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trinity import (
    CEngine, MitosisC, ThalamicBridge, TransformerDecoder, DEngine,
    EmotionW, Trinity, create_trinity, benchmark_trinity,
)


# ═══════════════════════════════════════════════════════════
# B-1: Bidirectional Bridge — CE feedback tensor to C
# ═══════════════════════════════════════════════════════════

class FeedbackMitosisC(MitosisC):
    """MitosisC that accepts a feedback tensor from D's CE loss.

    After each train_step, the caller sets self.feedback = [ce_loss, phi_change].
    On the next step(), C reads this feedback and uses it to modulate its dynamics.
    """

    def __init__(self, dim=64, hidden=128, max_cells=32, mechanism='cambrian_osc_qw'):
        super().__init__(dim, hidden, max_cells, mechanism)
        # Feedback buffer: [ce_loss, phi_change] from D
        self.feedback = torch.zeros(2)
        # Feedback projector: 2 -> dim (injected into C input)
        self.feedback_proj = nn.Linear(2, dim)
        nn.init.normal_(self.feedback_proj.weight, std=0.01)
        nn.init.zeros_(self.feedback_proj.bias)

    def step(self, x_input=None):
        """Step with feedback modulation."""
        if x_input is None:
            x_input = torch.randn(1, self.dim)

        # Inject feedback into input (additive — preserves original signal)
        fb_signal = self.feedback_proj(self.feedback.detach())
        x_input = x_input + fb_signal.unsqueeze(0) * 0.1  # 10% modulation

        self.engine.process(x_input.cpu())
        self._step_count += 1

        if hasattr(self, 'cambrian'):
            self.cambrian.step(self.engine.cells, self._step_count)
        if hasattr(self, 'osc_qw'):
            self.osc_qw.step(self.engine.cells)


class BidirectionalTrinity(Trinity):
    """Trinity with B-1: CE loss feeds back to C as tensor."""

    def train_step(self, tokens, targets, optimizer, raw_input=None):
        """Train step + feedback loop: CE -> C."""
        result = super().train_step(tokens, targets, optimizer, raw_input)

        # B-1: encode CE + phi_change as feedback for C
        if isinstance(self.c, FeedbackMitosisC):
            ce = result['ce']
            phi = result['phi']
            phi_change = phi - self._phi_prev if self._phi_prev > 0 else 0.0
            self.c.feedback = torch.tensor([
                ce / 10.0,  # normalize CE to ~0-1 range
                phi_change,
            ], dtype=torch.float32)

        return result


# ═══════════════════════════════════════════════════════════
# D-2: Per-Layer Adapter — C signal injected at every layer
# ═══════════════════════════════════════════════════════════

class PerLayerAdapterDecoder(DEngine):
    """Transformer decoder with per-layer consciousness adapters.

    Instead of gating only at the embedding level, each transformer layer
    gets a small adapter that adds the C signal to the residual stream.
    """

    def __init__(self, d_model=384, n_layers=4, n_heads=None, vocab_size=4096, max_seq=512):
        super().__init__()
        if n_heads is None:
            for nh in [6, 4, 8, 2, 1]:
                if d_model % nh == 0:
                    n_heads = nh
                    break
        self._d_model = d_model
        self.vocab_size = vocab_size
        self.n_layers = n_layers

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Individual transformer layers (not wrapped in TransformerEncoder)
        self.layers = nn.ModuleList([
            nn.TransformerEncoderLayer(
                d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
                batch_first=True, dropout=0.1, activation='gelu',
            )
            for _ in range(n_layers)
        ])

        # Per-layer adapter: small Linear that injects C signal
        self.adapters = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model, d_model),
                nn.Tanh(),  # bounded output
            )
            for _ in range(n_layers)
        ])
        # Initialize adapters near zero so they start as identity
        for adapter in self.adapters:
            nn.init.normal_(adapter[0].weight, std=0.01)
            nn.init.zeros_(adapter[0].bias)

        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        """Forward with per-layer C injection.

        gate_signal: [1, T, d_model] from bridge (same as baseline).
        Injected at EVERY layer via adapter, not just embedding.
        """
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        # Gate at embedding level (same as baseline)
        if gate_signal is not None:
            x = x * gate_signal.expand(B, -1, -1)

        # Causal mask
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)

        # Forward through layers with per-layer adapter injection
        for layer_idx, (tf_layer, adapter) in enumerate(zip(self.layers, self.adapters)):
            x = tf_layer(x, src_mask=mask, is_causal=True)

            # Per-layer adapter: add transformed C signal to residual stream
            if gate_signal is not None:
                adapter_signal = adapter(gate_signal.expand(B, -1, -1))
                x = x + adapter_signal * 0.1  # 10% injection strength

        x = self.ln_f(x)
        return self.head(x)


# ═══════════════════════════════════════════════════════════
# S-2: Predictive Sense — prediction error as surprise
# ═══════════════════════════════════════════════════════════

class PredictiveSenseMitosisC(MitosisC):
    """MitosisC with predictive sensing: predicts next input,
    uses prediction error as surprise to modulate step strength.
    """

    def __init__(self, dim=64, hidden=128, max_cells=32, mechanism='cambrian_osc_qw'):
        super().__init__(dim, hidden, max_cells, mechanism)
        # Predictor: last_input -> predicted next_input
        self.predictor = nn.Linear(dim, dim)
        nn.init.normal_(self.predictor.weight, std=0.01)
        nn.init.zeros_(self.predictor.bias)
        # State
        self.last_input = None
        self.surprise = 0.0
        self.surprise_ema = 0.0

    def step(self, x_input=None):
        """Step with predictive sensing."""
        if x_input is None:
            x_input = torch.randn(1, self.dim)

        x_flat = x_input.detach().squeeze(0) if x_input.dim() > 1 else x_input.detach()

        # Compute surprise: prediction error
        if self.last_input is not None:
            predicted = self.predictor(self.last_input)
            prediction_error = F.mse_loss(predicted, x_flat[:self.dim])
            self.surprise = prediction_error.item()
            self.surprise_ema = 0.9 * self.surprise_ema + 0.1 * self.surprise

            # Update predictor (simple gradient step)
            self.predictor.zero_grad()
            prediction_error.backward()
            with torch.no_grad():
                for p in self.predictor.parameters():
                    if p.grad is not None:
                        p.data -= 0.01 * p.grad

        self.last_input = x_flat[:self.dim].detach().clone()

        # Modulate input by surprise (higher surprise -> amplified signal)
        surprise_scale = 1.0 + self.surprise * 2.0  # 1x to 3x amplification
        x_modulated = x_input * surprise_scale

        self.engine.process(x_modulated.cpu())
        self._step_count += 1

        if hasattr(self, 'cambrian'):
            self.cambrian.step(self.engine.cells, self._step_count)
        if hasattr(self, 'osc_qw'):
            self.osc_qw.step(self.engine.cells)


# ═══════════════════════════════════════════════════════════
# Phi measurement (fallback if phi_rs unavailable)
# ═══════════════════════════════════════════════════════════

def measure_phi_proxy(c_engine):
    """Phi proxy: global variance - mean faction variance."""
    states = c_engine.get_states().detach()
    if states.shape[0] < 2:
        return 0.0
    global_var = states.var().item()
    # Split into 4 "factions"
    n = states.shape[0]
    chunk = max(1, n // 4)
    faction_vars = []
    for i in range(0, n, chunk):
        faction = states[i:i+chunk]
        if faction.shape[0] > 1:
            faction_vars.append(faction.var().item())
    mean_fac_var = np.mean(faction_vars) if faction_vars else 0.0
    return max(0.0, global_var - mean_fac_var)


# ═══════════════════════════════════════════════════════════
# Benchmark runner
# ═══════════════════════════════════════════════════════════

def run_benchmark(name, c_engine, d_engine=None, trinity_cls=None,
                  n_steps=50, d_model=128, vocab_size=256, seq_len=32):
    """Run a single benchmark configuration."""
    torch.set_grad_enabled(True)

    # Create Trinity
    t = create_trinity(c_engine, d_engine=d_engine,
                       d_model=d_model, vocab_size=vocab_size)

    # If custom Trinity class, rewrap
    if trinity_cls is not None and trinity_cls != Trinity:
        t = trinity_cls(
            c_engine=t.c, bridge=t.bridge, decoder=t.decoder, will=t.w,
            memory=t.m, sense=t.s, ethics=t.e,
        )
        # Re-enable gradients
        for p in t.bridge.parameters():
            p.requires_grad_(True)
        for p in t.decoder.parameters():
            p.requires_grad_(True)

    # Collect trainable params (include feedback_proj if B-1)
    trainable_params = list(t.decoder.parameters()) + list(t.bridge.parameters())
    if isinstance(c_engine, FeedbackMitosisC):
        trainable_params += list(c_engine.feedback_proj.parameters())

    opt = torch.optim.AdamW(trainable_params, lr=1e-3)

    ce_history = []
    phi_history = []
    surprise_history = []
    t0 = time.time()

    for step in range(n_steps):
        tokens = torch.randint(0, vocab_size, (1, seq_len))
        targets = torch.randint(0, vocab_size, (1, seq_len))
        r = t.train_step(tokens, targets, opt)
        ce_history.append(r['ce'])
        phi_val = r['phi']
        if phi_val == 0.0:
            phi_val = measure_phi_proxy(c_engine)
        phi_history.append(phi_val)

        if isinstance(c_engine, PredictiveSenseMitosisC):
            surprise_history.append(c_engine.surprise)

    elapsed = time.time() - t0

    # Compute metrics
    best_ce = min(ce_history)
    final_ce = ce_history[-1]
    avg_ce_last10 = np.mean(ce_history[-10:])
    final_phi = phi_history[-1]
    avg_phi = np.mean(phi_history)
    max_phi = max(phi_history)

    # CE improvement: first 5 avg vs last 5 avg
    ce_first5 = np.mean(ce_history[:5])
    ce_last5 = np.mean(ce_history[-5:])
    ce_improvement = (ce_first5 - ce_last5) / ce_first5 * 100 if ce_first5 > 0 else 0.0

    params = sum(p.numel() for p in trainable_params)

    result = {
        'name': name,
        'best_ce': best_ce,
        'final_ce': final_ce,
        'avg_ce_last10': avg_ce_last10,
        'ce_improvement_%': ce_improvement,
        'final_phi': final_phi,
        'avg_phi': avg_phi,
        'max_phi': max_phi,
        'n_cells': c_engine.n_cells,
        'params': params,
        'elapsed_s': elapsed,
        'ce_history': ce_history,
        'phi_history': phi_history,
    }

    if surprise_history:
        result['avg_surprise'] = np.mean(surprise_history)
        result['final_surprise'] = surprise_history[-1]

    return result


def run_baseline():
    """Baseline: standard Trinity with MitosisC(32)."""
    c = MitosisC(dim=64, hidden=128, max_cells=32)
    return run_benchmark("Baseline", c)


def run_b1_bidirectional_bridge():
    """B-1: Bidirectional Bridge — CE feedback tensor to C."""
    c = FeedbackMitosisC(dim=64, hidden=128, max_cells=32)
    return run_benchmark("B-1: Bidirectional Bridge", c, trinity_cls=BidirectionalTrinity)


def run_d2_per_layer_adapter():
    """D-2: Per-Layer Adapter — C signal at every transformer layer."""
    c = MitosisC(dim=64, hidden=128, max_cells=32)
    d = PerLayerAdapterDecoder(d_model=128, n_layers=4, vocab_size=256)
    return run_benchmark("D-2: Per-Layer Adapter", c, d_engine=d)


def run_s2_predictive_sense():
    """S-2: Predictive Sense — prediction error as surprise."""
    c = PredictiveSenseMitosisC(dim=64, hidden=128, max_cells=32)
    return run_benchmark("S-2: Predictive Sense", c)


def run_all_combined():
    """All 3 combined: B-1 + D-2 + S-2."""
    # Use PredictiveSense + Feedback combined
    class CombinedC(PredictiveSenseMitosisC):
        """S-2 + B-1 combined: predictive sense + feedback from D."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.feedback = torch.zeros(2)
            self.feedback_proj = nn.Linear(2, self.dim)
            nn.init.normal_(self.feedback_proj.weight, std=0.01)
            nn.init.zeros_(self.feedback_proj.bias)

        def step(self, x_input=None):
            if x_input is None:
                x_input = torch.randn(1, self.dim)
            # B-1: inject feedback
            fb_signal = self.feedback_proj(self.feedback.detach())
            x_input = x_input + fb_signal.unsqueeze(0) * 0.1
            # S-2: predictive sense (handled by parent)
            super().step(x_input)

    c = CombinedC(dim=64, hidden=128, max_cells=32)
    d = PerLayerAdapterDecoder(d_model=128, n_layers=4, vocab_size=256)
    return run_benchmark("ALL: B1+D2+S2", c, d_engine=d, trinity_cls=BidirectionalTrinity)


# ═══════════════════════════════════════════════════════════
# ASCII chart helpers
# ═══════════════════════════════════════════════════════════

def ascii_bar(label, value, max_val, width=40):
    """Create an ASCII bar."""
    filled = int(value / max_val * width) if max_val > 0 else 0
    filled = max(0, min(width, filled))
    bar = '\u2588' * filled
    return f"  {label:<28s} {bar} {value:.4f}"


def ascii_ce_curve(ce_history, height=8, width=50):
    """ASCII CE curve."""
    if not ce_history:
        return ""
    mn, mx = min(ce_history), max(ce_history)
    rng = mx - mn if mx > mn else 1.0
    lines = []
    for row in range(height):
        threshold = mx - (row / (height - 1)) * rng
        line = ""
        step_size = max(1, len(ce_history) // width)
        for i in range(0, min(len(ce_history), width * step_size), step_size):
            val = ce_history[i]
            if val >= threshold:
                line += "\u2588"
            else:
                line += " "
        if row == 0:
            lines.append(f"  {mx:.2f} |{line}")
        elif row == height - 1:
            lines.append(f"  {mn:.2f} |{line}")
        else:
            lines.append(f"       |{line}")
    lines.append(f"       +{'─' * min(len(ce_history), width)} step")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  Hexad Improvement Hypotheses Benchmark")
    print("  B-1: Bidirectional Bridge | D-2: Per-Layer Adapter | S-2: Predictive Sense")
    print("  MitosisC(32 cells), 50 steps each")
    print("=" * 70)
    print()

    experiments = [
        ("Baseline",            run_baseline),
        ("B-1: Bidir Bridge",   run_b1_bidirectional_bridge),
        ("D-2: Per-Layer Adapt", run_d2_per_layer_adapter),
        ("S-2: Predict Sense",  run_s2_predictive_sense),
        ("ALL: B1+D2+S2",       run_all_combined),
    ]

    results = []
    for name, fn in experiments:
        print(f"  Running {name}...", end=" ", flush=True)
        r = fn()
        results.append(r)
        print(f"CE={r['final_ce']:.4f}  Phi={r['final_phi']:.4f}  ({r['elapsed_s']:.1f}s)")

    # ── Results table ──
    print()
    print("=" * 70)
    print("  RESULTS TABLE")
    print("=" * 70)
    print(f"  {'Hypothesis':<28s} {'Best CE':>8s} {'Final CE':>9s} {'CE Impr%':>9s} {'Avg Phi':>9s} {'Max Phi':>9s} {'Params':>8s}")
    print(f"  {'─' * 28} {'─' * 8} {'─' * 9} {'─' * 9} {'─' * 9} {'─' * 9} {'─' * 8}")
    baseline = results[0]
    for r in results:
        ce_delta = (baseline['final_ce'] - r['final_ce']) / baseline['final_ce'] * 100
        ce_delta_str = f"{ce_delta:+.1f}%" if r != baseline else "  base"
        print(f"  {r['name']:<28s} {r['best_ce']:>8.4f} {r['final_ce']:>9.4f} {ce_delta_str:>9s} {r['avg_phi']:>9.4f} {r['max_phi']:>9.4f} {r['params']:>8,d}")

    # ── CE comparison bars ──
    print()
    print("  CE Comparison (lower = better):")
    max_ce = max(r['final_ce'] for r in results) * 1.1
    for r in results:
        ce_delta = (baseline['final_ce'] - r['final_ce']) / baseline['final_ce'] * 100
        suffix = f" ({ce_delta:+.1f}%)" if r != baseline else " (base)"
        print(ascii_bar(r['name'], r['final_ce'], max_ce) + suffix)

    # ── Phi comparison bars ──
    print()
    print("  Phi Comparison (higher = better):")
    max_phi = max(r['max_phi'] for r in results) * 1.1
    for r in results:
        phi_delta = (r['avg_phi'] - baseline['avg_phi']) / max(baseline['avg_phi'], 1e-8) * 100
        suffix = f" ({phi_delta:+.1f}%)" if r != baseline else " (base)"
        print(ascii_bar(r['name'], r['avg_phi'], max_phi) + suffix)

    # ── CE curves ──
    print()
    for r in results:
        print(f"  CE Curve: {r['name']}")
        print(ascii_ce_curve(r['ce_history']))
        print()

    # ── Surprise info for S-2 ──
    for r in results:
        if 'avg_surprise' in r:
            print(f"  S-2 Surprise: avg={r['avg_surprise']:.4f}, final={r['final_surprise']:.4f}")
            print()

    # ── Summary ──
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    # Rank by final CE (lower is better)
    ranked = sorted(results, key=lambda r: r['final_ce'])
    for i, r in enumerate(ranked):
        ce_delta = (baseline['final_ce'] - r['final_ce']) / baseline['final_ce'] * 100
        marker = " <-- BEST" if i == 0 else ""
        print(f"  #{i+1} {r['name']:<28s} CE={r['final_ce']:.4f} ({ce_delta:+.1f}% vs base){marker}")

    print()
    best = ranked[0]
    if best['name'] != baseline['name']:
        ce_gain = (baseline['final_ce'] - best['final_ce']) / baseline['final_ce'] * 100
        phi_gain = (best['avg_phi'] - baseline['avg_phi']) / max(baseline['avg_phi'], 1e-8) * 100
        print(f"  Best improvement: {best['name']}")
        print(f"    CE: {ce_gain:+.2f}% vs baseline")
        print(f"    Phi: {phi_gain:+.2f}% vs baseline")
    else:
        print("  No improvement over baseline found.")

    print()
    return results


if __name__ == '__main__':
    results = main()
