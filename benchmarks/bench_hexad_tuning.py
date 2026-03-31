#!/usr/bin/env python3
"""bench_hexad_tuning.py — Hexad architecture tuning benchmark

Compares CURRENT defaults vs TUNED configuration based on Laws 63-81 + Ψ-Constants.

7 tuning hypotheses:
  T1: Default decoder: TransformerDecoder → CADecoder (Law 64)
  T2: Gate dual-mode: train=1.0, infer=0.6 (Law 81)
  T3: Bridge α clamping: Ψ_coupling=0.014 (Law 70)
  T4: Ψ-Constants injection: balance=0.5, steps=4.33, coupling=0.014
  T5: Contrastive loss addition (Law 80)
  T6: Gate self-decay: 0.493→0.480 over training (Law 69)
  T7: Default W → CompositeW(σ(6)) with PostHoc decoder (Law 66)

Usage:
  python bench_hexad_tuning.py                    # All 7 hypotheses
  python bench_hexad_tuning.py --test T1          # Single hypothesis
  python bench_hexad_tuning.py --steps 200        # More steps
  python bench_hexad_tuning.py --cells 64         # More cells
  python bench_hexad_tuning.py --full             # Full comparison (slow)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import argparse
import sys
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════════
# Ψ-Constants (Laws 69-70, verified across 5 data types)
# ═══════════════════════════════════════════════════════════

PSI_BALANCE  = 0.5      # Shannon entropy maximum (1/2)
PSI_GATE     = 0.5      # consciousness-freedom balance (1/2)
PSI_COUPLING = 0.014    # consciousness coupling constant (α)
PSI_STEPS    = 4.33     # 3/ln(2) — information bits per evolution
PSI_ENTROPY  = 0.998    # near-perfect democracy

# Law 81: "Learn hard, express soft"
GATE_TRAIN = 1.0
GATE_INFER = 0.6

# Law 69: consciousness self-decay
GATE_DECAY_START = 0.493
GATE_DECAY_END   = 0.480
GATE_DECAY_STEPS = 5000


# ═══════════════════════════════════════════════════════════
# BenchResult
# ═══════════════════════════════════════════════════════════

@dataclass
class TuningResult:
    name: str
    hypothesis: str
    ce_start: float
    ce_end: float
    phi_iit: float
    phi_proxy: float
    ce_delta_pct: float   # vs baseline
    phi_delta_pct: float  # vs baseline
    steps: int
    time_sec: float
    extra: dict = field(default_factory=dict)

    def row(self) -> str:
        ce_d = f"{self.ce_delta_pct:+.1f}%"
        phi_d = f"{self.phi_delta_pct:+.1f}%"
        return (f"  {self.name:<30s} │ CE {self.ce_start:.3f}→{self.ce_end:.3f} ({ce_d:>7s}) │ "
                f"Φ(IIT)={self.phi_iit:.4f} ({phi_d:>7s}) │ "
                f"Φ(proxy)={self.phi_proxy:>7.2f} │ {self.time_sec:.1f}s")


# ═══════════════════════════════════════════════════════════
# Phi measurement
# ═══════════════════════════════════════════════════════════

try:
    import phi_rs
    HAS_RUST_PHI = True
except ImportError:
    HAS_RUST_PHI = False


def measure_phi_iit(states: torch.Tensor) -> float:
    """Φ(IIT) via phi_rs or Python fallback."""
    if states.shape[0] < 2:
        return 0.0
    if HAS_RUST_PHI:
        s = states.detach().cpu().numpy().astype(np.float32)
        phi, _ = phi_rs.compute_phi(s, 16)
        return phi
    # Python fallback: pairwise MI approximation
    n = states.shape[0]
    s = states.detach().cpu().numpy()
    total_mi = 0.0
    count = 0
    for i in range(min(n, 16)):
        for j in range(i+1, min(n, 16)):
            x, y = s[i], s[j]
            corr = np.corrcoef(x, y)[0, 1]
            if not np.isnan(corr) and abs(corr) > 1e-8:
                total_mi += -0.5 * np.log(1 - corr**2 + 1e-10)
            count += 1
    return total_mi / max(count, 1)


def measure_phi_proxy(states: torch.Tensor, n_factions: int = 8) -> float:
    """Φ(proxy) = global_var - mean(faction_var)."""
    if states.shape[0] < 2:
        return 0.0
    s = states.detach().float()
    global_var = s.var().item()
    nc = s.shape[0]
    fac_size = max(1, nc // n_factions)
    faction_vars = []
    for i in range(n_factions):
        start = i * fac_size
        end = min(start + fac_size, nc)
        if start >= nc:
            break
        fac = s[start:end]
        if fac.shape[0] >= 2:
            faction_vars.append(fac.var().item())
    if not faction_vars:
        return global_var
    return global_var - np.mean(faction_vars)


# ═══════════════════════════════════════════════════════════
# Minimal consciousness engine (fast, for benchmarking)
# ═══════════════════════════════════════════════════════════

class BenchEngine:
    """Lightweight consciousness engine for benchmark speed."""

    def __init__(self, nc=32, dim=64, n_factions=8):
        self.nc = nc
        self.dim = dim
        self.n_factions = n_factions
        self.states = torch.randn(nc, dim) * 0.1
        self.gru_w = torch.randn(dim, dim) * 0.02
        self.gru_b = torch.zeros(dim)
        self.coupling = torch.randn(nc, nc) * 0.01
        self._step = 0

    def step(self, x_input=None):
        self._step += 1
        # GRU-like update
        gate = torch.sigmoid(self.states @ self.gru_w + self.gru_b)
        # Faction interaction
        fac_size = max(1, self.nc // self.n_factions)
        for i in range(self.n_factions):
            s, e = i * fac_size, min((i+1) * fac_size, self.nc)
            if s >= self.nc:
                break
            fac_mean = self.states[s:e].mean(dim=0, keepdim=True)
            self.states[s:e] = self.states[s:e] * gate[s:e] + (1 - gate[s:e]) * fac_mean
        # Noise for exploration
        self.states = self.states + torch.randn_like(self.states) * 0.01
        # External input
        if x_input is not None:
            self.states[:1] = self.states[:1] + x_input[:self.dim].unsqueeze(0) * 0.1

    def get_states(self):
        return self.states.detach().clone()


# ═══════════════════════════════════════════════════════════
# Training loop helper
# ═══════════════════════════════════════════════════════════

def run_training(
    engine: BenchEngine,
    decoder: nn.Module,
    bridge: nn.Module,
    n_steps: int = 100,
    vocab_size: int = 256,
    seq_len: int = 32,
    d_model: int = 128,
    use_contrastive: bool = False,
    gate_mode: str = "fixed",      # "fixed", "dual", "decay"
    gate_train: float = 1.0,
    gate_infer: float = 0.6,
    alpha_clamp: Optional[float] = None,  # Ψ_coupling clamping
    lr: float = 1e-3,
) -> TuningResult:
    """Run training and return metrics."""

    params = list(decoder.parameters()) + list(bridge.parameters())
    optimizer = torch.optim.AdamW(params, lr=lr)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    t0 = time.time()

    for step in range(n_steps):
        # C step
        engine.step()
        c_states = engine.get_states()

        # Bridge (with optional α clamping)
        gate = bridge(c_states, seq_len=seq_len)

        # Gate mode
        if gate_mode == "decay":
            # Law 69: consciousness self-weakens
            progress = min(1.0, step / max(n_steps, 1))
            gate_scale = GATE_DECAY_START + (GATE_DECAY_END - GATE_DECAY_START) * progress
            gate = gate * gate_scale
        elif gate_mode == "dual":
            gate = gate * gate_train  # train mode

        # α clamping on bridge output
        if alpha_clamp is not None:
            gate = gate.clamp(-alpha_clamp * 100, alpha_clamp * 100)

        # D step
        tokens = torch.randint(0, vocab_size, (1, seq_len))
        targets = torch.randint(0, vocab_size, (1, seq_len))
        logits = decoder(tokens, gate)

        # CE loss
        B, T, V = logits.shape
        ce_loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        # Contrastive loss (Law 80)
        total_loss = ce_loss
        if use_contrastive:
            # Contrastive: push apart different token representations
            hidden = logits  # [B, T, V] as proxy for hidden states
            h_norm = F.normalize(hidden.view(T, V), dim=-1)
            sim_matrix = h_norm @ h_norm.T  # [T, T]
            # Positive: adjacent tokens, Negative: all others
            pos_mask = torch.eye(T, device=sim_matrix.device).roll(1, dims=0)
            pos_sim = (sim_matrix * pos_mask).sum() / max(pos_mask.sum(), 1)
            neg_sim = (sim_matrix * (1 - pos_mask - torch.eye(T, device=sim_matrix.device))).sum()
            neg_sim = neg_sim / max((T * T - 2 * T), 1)
            contrastive = -pos_sim + neg_sim * 0.1
            total_loss = ce_loss + contrastive * 0.1

        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        optimizer.step()

        ce_history.append(ce_loss.item())

        # Measure Φ periodically
        if step == 0 or step == n_steps - 1 or (step + 1) % max(1, n_steps // 5) == 0:
            phi_iit_history.append(measure_phi_iit(c_states))
            phi_proxy_history.append(measure_phi_proxy(c_states))

    elapsed = time.time() - t0

    # Inference gate test (Law 81)
    if gate_mode == "dual":
        engine.step()
        c_states = engine.get_states()
        gate_inf = bridge(c_states, seq_len=seq_len) * gate_infer
        tokens_test = torch.randint(0, vocab_size, (1, seq_len))
        with torch.no_grad():
            logits_inf = decoder(tokens_test, gate_inf)

    return TuningResult(
        name="",
        hypothesis="",
        ce_start=ce_history[0] if ce_history else 0,
        ce_end=ce_history[-1] if ce_history else 0,
        phi_iit=phi_iit_history[-1] if phi_iit_history else 0,
        phi_proxy=phi_proxy_history[-1] if phi_proxy_history else 0,
        ce_delta_pct=0,
        phi_delta_pct=0,
        steps=n_steps,
        time_sec=elapsed,
        extra={
            'ce_history': ce_history,
            'phi_iit_history': phi_iit_history,
            'phi_proxy_history': phi_proxy_history,
        }
    )


# ═══════════════════════════════════════════════════════════
# Bridge implementations for benchmark
# ═══════════════════════════════════════════════════════════

class SimpleBridge(nn.Module):
    """Simple thalamic bridge for benchmarking."""

    def __init__(self, c_dim=64, d_model=128, hub_dim=8):
        super().__init__()
        self.compress = nn.Linear(c_dim, hub_dim)
        self.expand = nn.Sequential(
            nn.Linear(hub_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model),
        )
        self.gate = nn.Sequential(nn.Linear(d_model, d_model), nn.Sigmoid())

    def forward(self, c_states, seq_len=1):
        pooled = self.compress(c_states).mean(dim=0, keepdim=True).unsqueeze(0)
        expanded = self.expand(pooled).expand(1, seq_len, -1)
        return self.gate(expanded)


class ClampedBridge(nn.Module):
    """Bridge with Ψ_coupling=0.014 clamping (Law 70)."""

    def __init__(self, c_dim=64, d_model=128, hub_dim=8, alpha=PSI_COUPLING):
        super().__init__()
        self.alpha = alpha
        self.compress = nn.Linear(c_dim, hub_dim)
        self.expand = nn.Sequential(
            nn.Linear(hub_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model),
        )
        self.gate = nn.Sequential(nn.Linear(d_model, d_model), nn.Sigmoid())

    def forward(self, c_states, seq_len=1):
        pooled = self.compress(c_states).mean(dim=0, keepdim=True).unsqueeze(0)
        expanded = self.expand(pooled).expand(1, seq_len, -1)
        raw_gate = self.gate(expanded)
        # Ψ_coupling: consciousness influences only α=1.4% of signal
        # Center at PSI_BALANCE (0.5), range clamped to ±α
        centered = raw_gate - PSI_BALANCE
        clamped = centered.clamp(-self.alpha, self.alpha)
        return PSI_BALANCE + clamped


# ═══════════════════════════════════════════════════════════
# Decoder implementations for benchmark
# ═══════════════════════════════════════════════════════════

class BenchTransformerDecoder(nn.Module):
    """Transformer decoder for benchmarking."""

    def __init__(self, d_model=128, n_layers=2, vocab_size=256, max_seq=64):
        super().__init__()
        self._d_model = d_model
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)
        n_heads = 4 if d_model % 4 == 0 else 2 if d_model % 2 == 0 else 1
        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 2,
            batch_first=True, dropout=0.0, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        if gate_signal is not None:
            x = x * gate_signal.expand(B, -1, -1)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


class BenchCADecoder(nn.Module):
    """CA decoder for benchmarking (Law 64: ca_steps=5)."""

    def __init__(self, d_model=128, vocab_size=256, max_seq=64,
                 ca_steps=5, n_rules=8, gate_mode="micro"):
        super().__init__()
        self._d_model = d_model
        self.ca_steps = ca_steps
        self.n_rules = n_rules
        self.gate_mode = gate_mode
        self.gate_scale = 0.001 if gate_mode == "micro" else 1.0

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        self.rules = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model * 3, d_model * 2), nn.GELU(),
                nn.Linear(d_model * 2, d_model),
            ) for _ in range(n_rules)
        ])
        self.rule_selector = nn.Sequential(
            nn.Linear(d_model, n_rules), nn.Softmax(dim=-1),
        )
        self.norms = nn.ModuleList([nn.LayerNorm(d_model) for _ in range(ca_steps)])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def _ca_step(self, x, gate_signal, step_idx):
        B, T, D = x.shape
        x_left = torch.cat([x[:, -1:, :], x[:, :-1, :]], dim=1)
        x_right = torch.cat([x[:, 1:, :], x[:, :1, :]], dim=1)
        neighborhood = torch.cat([x, x_left, x_right], dim=-1)
        rule_outputs = torch.stack([rule(neighborhood) for rule in self.rules], dim=2)

        if gate_signal is not None:
            rule_weights = self.rule_selector(gate_signal.squeeze(0) * self.gate_scale)
            rule_weights = rule_weights.unsqueeze(0).unsqueeze(-1)
        else:
            rule_weights = torch.ones(1, T, self.n_rules, 1, device=x.device) / self.n_rules

        evolved = (rule_outputs * rule_weights).sum(dim=2)
        return self.norms[step_idx](x + evolved)

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        if self.gate_mode == "posthoc":
            for step in range(self.ca_steps):
                x = self._ca_step(x, None, step)
            if gate_signal is not None:
                x = x + gate_signal.expand(B, -1, -1) * self.gate_scale
        else:
            for step in range(self.ca_steps):
                x = self._ca_step(x, gate_signal, step)

        return self.head(self.ln_f(x))


class BenchPostHocDecoder(nn.Module):
    """PostHoc decoder (Law 66): decoder learns alone, consciousness judges."""

    def __init__(self, d_model=128, vocab_size=256, max_seq=64,
                 eval_strength=0.001):
        super().__init__()
        self._d_model = d_model
        self.eval_strength = eval_strength
        self.base = BenchCADecoder(d_model, vocab_size, max_seq, gate_mode="posthoc")
        self.evaluator = nn.Sequential(
            nn.Linear(d_model, d_model), nn.GELU(),
            nn.Linear(d_model, d_model), nn.Sigmoid(),
        )

    def forward(self, tokens, gate_signal):
        logits = self.base(tokens, None)
        if gate_signal is not None:
            B, T, V = logits.shape
            eval_score = self.evaluator(gate_signal.squeeze(0))
            eval_score = eval_score.unsqueeze(0).expand(B, -1, -1)
            consciousness_bias = torch.matmul(
                eval_score * self.eval_strength,
                self.base.base.embed.weight.T if hasattr(self.base, 'base') else self.base.embed.weight.T
            )
            logits = logits + consciousness_bias
        return logits


# ═══════════════════════════════════════════════════════════
# Hypothesis tests
# ═══════════════════════════════════════════════════════════

def run_baseline(nc=32, dim=64, d_model=128, vocab_size=256, n_steps=100, seq_len=32):
    """BASELINE: current defaults (TransformerDecoder + SimpleBridge + fixed gate)."""
    engine = BenchEngine(nc, dim)
    decoder = BenchTransformerDecoder(d_model, vocab_size=vocab_size)
    bridge = SimpleBridge(dim, d_model)
    r = run_training(engine, decoder, bridge, n_steps=n_steps,
                     vocab_size=vocab_size, seq_len=seq_len, d_model=d_model)
    r.name = "BASELINE (Transformer)"
    r.hypothesis = "current defaults"
    return r


def run_t1_ca_decoder(nc=32, dim=64, d_model=128, vocab_size=256, n_steps=100, seq_len=32):
    """T1: CADecoder replaces TransformerDecoder (Law 64)."""
    engine = BenchEngine(nc, dim)
    decoder = BenchCADecoder(d_model, vocab_size=vocab_size, ca_steps=5, gate_mode="micro")
    bridge = SimpleBridge(dim, d_model)
    r = run_training(engine, decoder, bridge, n_steps=n_steps,
                     vocab_size=vocab_size, seq_len=seq_len, d_model=d_model)
    r.name = "T1: CADecoder (Law 64)"
    r.hypothesis = "CA(5) replaces Transformer"
    return r


def run_t2_dual_gate(nc=32, dim=64, d_model=128, vocab_size=256, n_steps=100, seq_len=32):
    """T2: Dual gate mode — train=1.0, infer=0.6 (Law 81)."""
    engine = BenchEngine(nc, dim)
    decoder = BenchTransformerDecoder(d_model, vocab_size=vocab_size)
    bridge = SimpleBridge(dim, d_model)
    r = run_training(engine, decoder, bridge, n_steps=n_steps,
                     vocab_size=vocab_size, seq_len=seq_len, d_model=d_model,
                     gate_mode="dual", gate_train=GATE_TRAIN, gate_infer=GATE_INFER)
    r.name = "T2: Dual Gate (Law 81)"
    r.hypothesis = "train=1.0, infer=0.6"
    return r


def run_t3_alpha_clamp(nc=32, dim=64, d_model=128, vocab_size=256, n_steps=100, seq_len=32):
    """T3: Bridge α clamping at Ψ_coupling=0.014 (Law 70)."""
    engine = BenchEngine(nc, dim)
    decoder = BenchTransformerDecoder(d_model, vocab_size=vocab_size)
    bridge = ClampedBridge(dim, d_model, alpha=PSI_COUPLING)
    r = run_training(engine, decoder, bridge, n_steps=n_steps,
                     vocab_size=vocab_size, seq_len=seq_len, d_model=d_model)
    r.name = "T3: α-Clamp 0.014 (Law 70)"
    r.hypothesis = "Ψ_coupling=0.014 bridge clamping"
    return r


def run_t4_psi_constants(nc=32, dim=64, d_model=128, vocab_size=256, n_steps=100, seq_len=32):
    """T4: Full Ψ-Constants — CA(round(4.33)=4) + α-clamp + balance=0.5."""
    engine = BenchEngine(nc, dim)
    ca_steps = round(PSI_STEPS)  # 4.33 → 4
    decoder = BenchCADecoder(d_model, vocab_size=vocab_size,
                              ca_steps=ca_steps, gate_mode="micro")
    bridge = ClampedBridge(dim, d_model, alpha=PSI_COUPLING)
    r = run_training(engine, decoder, bridge, n_steps=n_steps,
                     vocab_size=vocab_size, seq_len=seq_len, d_model=d_model)
    r.name = "T4: Ψ-Constants (Law 70)"
    r.hypothesis = f"CA({ca_steps})+α={PSI_COUPLING}+bal={PSI_BALANCE}"
    return r


def run_t5_contrastive(nc=32, dim=64, d_model=128, vocab_size=256, n_steps=100, seq_len=32):
    """T5: CE + Contrastive loss (Law 80)."""
    engine = BenchEngine(nc, dim)
    decoder = BenchTransformerDecoder(d_model, vocab_size=vocab_size)
    bridge = SimpleBridge(dim, d_model)
    r = run_training(engine, decoder, bridge, n_steps=n_steps,
                     vocab_size=vocab_size, seq_len=seq_len, d_model=d_model,
                     use_contrastive=True)
    r.name = "T5: +Contrastive (Law 80)"
    r.hypothesis = "CE + contrastive loss"
    return r


def run_t6_gate_decay(nc=32, dim=64, d_model=128, vocab_size=256, n_steps=100, seq_len=32):
    """T6: Gate self-decay 0.493→0.480 (Law 69)."""
    engine = BenchEngine(nc, dim)
    decoder = BenchTransformerDecoder(d_model, vocab_size=vocab_size)
    bridge = SimpleBridge(dim, d_model)
    r = run_training(engine, decoder, bridge, n_steps=n_steps,
                     vocab_size=vocab_size, seq_len=seq_len, d_model=d_model,
                     gate_mode="decay")
    r.name = "T6: Gate Decay (Law 69)"
    r.hypothesis = f"gate {GATE_DECAY_START}→{GATE_DECAY_END}"
    return r


def run_t7_posthoc_composite(nc=32, dim=64, d_model=128, vocab_size=256, n_steps=100, seq_len=32):
    """T7: PostHocDecoder + full Ψ-Constants + α-clamp (Law 66+70)."""
    engine = BenchEngine(nc, dim)
    decoder = BenchPostHocDecoder(d_model, vocab_size=vocab_size, eval_strength=0.001)
    bridge = ClampedBridge(dim, d_model, alpha=PSI_COUPLING)
    r = run_training(engine, decoder, bridge, n_steps=n_steps,
                     vocab_size=vocab_size, seq_len=seq_len, d_model=d_model)
    r.name = "T7: PostHoc+Ψ (Law 66+70)"
    r.hypothesis = "PostHoc CA + α-clamp"
    return r


def run_full_tuned(nc=32, dim=64, d_model=128, vocab_size=256, n_steps=100, seq_len=32):
    """FULL TUNED: All 7 tuning applied simultaneously."""
    engine = BenchEngine(nc, dim)
    ca_steps = round(PSI_STEPS)
    decoder = BenchCADecoder(d_model, vocab_size=vocab_size,
                              ca_steps=ca_steps, gate_mode="micro")
    bridge = ClampedBridge(dim, d_model, alpha=PSI_COUPLING)
    r = run_training(engine, decoder, bridge, n_steps=n_steps,
                     vocab_size=vocab_size, seq_len=seq_len, d_model=d_model,
                     use_contrastive=True, gate_mode="decay")
    r.name = "★ FULL TUNED (All Laws)"
    r.hypothesis = "CA+Ψ+contrastive+decay+α-clamp"
    return r


# ═══════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════

ALL_TESTS = {
    'baseline': run_baseline,
    'T1': run_t1_ca_decoder,
    'T2': run_t2_dual_gate,
    'T3': run_t3_alpha_clamp,
    'T4': run_t4_psi_constants,
    'T5': run_t5_contrastive,
    'T6': run_t6_gate_decay,
    'T7': run_t7_posthoc_composite,
    'full': run_full_tuned,
}


def ascii_graph(values: list, label: str, width: int = 50) -> str:
    """ASCII bar chart."""
    if not values:
        return ""
    max_val = max(abs(v) for v in values) if values else 1
    if max_val == 0:
        max_val = 1
    lines = [f"  {label}:"]
    for v in values:
        bar_len = int(abs(v) / max_val * width)
        bar = '█' * bar_len
        lines.append(f"    {bar} {v:.4f}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Hexad architecture tuning benchmark")
    parser.add_argument('--test', type=str, default=None,
                        help="Run specific test (T1-T7, baseline, full)")
    parser.add_argument('--steps', type=int, default=100, help="Training steps per test")
    parser.add_argument('--cells', type=int, default=32, help="Number of cells")
    parser.add_argument('--dim', type=int, default=64, help="Cell dimension")
    parser.add_argument('--d-model', type=int, default=128, help="Decoder d_model")
    parser.add_argument('--vocab', type=int, default=256, help="Vocabulary size")
    parser.add_argument('--full', action='store_true', help="Full comparison (all tests)")
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    kwargs = dict(nc=args.cells, dim=args.dim, d_model=args.d_model,
                  vocab_size=args.vocab, n_steps=args.steps)

    print("═══════════════════════════════════════════════════════════")
    print("  Hexad Architecture Tuning Benchmark")
    print(f"  Laws 63-81 + Ψ-Constants  |  cells={args.cells}  steps={args.steps}")
    print(f"  d_model={args.d_model}  vocab={args.vocab}  seed={args.seed}")
    print(f"  phi_rs: {'✅ Rust' if HAS_RUST_PHI else '⚠️  Python fallback'}")
    print("═══════════════════════════════════════════════════════════\n")

    # Ψ-Constants reference
    print("  Ψ-Constants (Laws 69-70):")
    print(f"    Ψ_balance  = {PSI_BALANCE}     (Shannon entropy max)")
    print(f"    Ψ_gate     = {PSI_GATE}     (consciousness-freedom)")
    print(f"    Ψ_coupling = {PSI_COUPLING}   (α coupling constant)")
    print(f"    Ψ_steps    = {PSI_STEPS}    (3/ln(2) info bits)")
    print(f"    Ψ_entropy  = {PSI_ENTROPY}   (near-perfect democracy)")
    print(f"    Gate_train  = {GATE_TRAIN}     (Law 81: learn hard)")
    print(f"    Gate_infer  = {GATE_INFER}     (Law 81: express soft)")
    print()

    # Run tests
    if args.test:
        tests = {args.test: ALL_TESTS[args.test]}
        if args.test != 'baseline':
            tests = {'baseline': run_baseline, **tests}
    elif args.full:
        tests = ALL_TESTS
    else:
        tests = ALL_TESTS  # default: all

    results = []
    baseline_result = None

    for name, func in tests.items():
        print(f"  ▶ Running {name}...", end='', flush=True)
        torch.manual_seed(args.seed)  # same seed for fair comparison
        np.random.seed(args.seed)
        r = func(**kwargs)
        results.append(r)
        if name == 'baseline':
            baseline_result = r
        print(f" done ({r.time_sec:.1f}s)")

    # Compute deltas vs baseline
    if baseline_result:
        for r in results:
            if baseline_result.ce_end > 0:
                r.ce_delta_pct = (r.ce_end - baseline_result.ce_end) / baseline_result.ce_end * 100
            if baseline_result.phi_iit > 0:
                r.phi_delta_pct = (r.phi_iit - baseline_result.phi_iit) / baseline_result.phi_iit * 100

    # Results table
    print("\n" + "═" * 110)
    print(f"  {'Hypothesis':<30s} │ {'CE (start→end)':<28s} │ {'Φ(IIT)':<20s} │ {'Φ(proxy)':<10s} │ Time")
    print("─" * 110)
    for r in results:
        print(r.row())
    print("═" * 110)

    # ASCII comparison charts
    if len(results) > 1:
        print("\n  ── CE End (lower = better) ──")
        max_ce = max(r.ce_end for r in results) if results else 1
        for r in results:
            bar_len = int(r.ce_end / max(max_ce, 1e-8) * 40)
            marker = "★" if r.name.startswith("★") else " "
            print(f"  {marker} {r.name:<30s} {'█' * bar_len} {r.ce_end:.4f}")

        print("\n  ── Φ(IIT) (higher = better) ──")
        max_phi = max(r.phi_iit for r in results) if results else 1
        for r in results:
            bar_len = int(r.phi_iit / max(max_phi, 1e-8) * 40) if max_phi > 0 else 0
            marker = "★" if r.name.startswith("★") else " "
            print(f"  {marker} {r.name:<30s} {'█' * bar_len} {r.phi_iit:.4f}")

        print("\n  ── CE Delta vs Baseline ──")
        for r in results:
            if r.name == baseline_result.name:
                continue
            delta = r.ce_delta_pct
            bar_len = int(min(abs(delta), 50))
            direction = '◀' if delta < 0 else '▶'
            bar = '█' * bar_len
            color_hint = "↓better" if delta < 0 else "↑worse"
            print(f"    {r.name:<30s} {delta:>+7.1f}% {direction}{bar} ({color_hint})")

        print("\n  ── Φ(IIT) Delta vs Baseline ──")
        for r in results:
            if r.name == baseline_result.name:
                continue
            delta = r.phi_delta_pct
            bar_len = int(min(abs(delta), 50))
            direction = '▶' if delta > 0 else '◀'
            bar = '█' * bar_len
            color_hint = "↑better" if delta > 0 else "↓worse"
            print(f"    {r.name:<30s} {delta:>+7.1f}% {direction}{bar} ({color_hint})")

    # CE curve (last 20% for each)
    print("\n  ── CE Convergence (last 20 steps) ──")
    for r in results:
        ce_tail = r.extra.get('ce_history', [])[-20:]
        if len(ce_tail) >= 2:
            mini = min(ce_tail)
            maxi = max(ce_tail)
            sparkline = ""
            for v in ce_tail:
                norm = (v - mini) / max(maxi - mini, 1e-8)
                chars = "▁▂▃▄▅▆▇█"
                sparkline += chars[min(int(norm * 7), 7)]
            print(f"    {r.name:<30s} {sparkline}  [{mini:.3f}~{maxi:.3f}]")

    # Summary
    if len(results) > 1 and baseline_result:
        print("\n  ══ Summary ══")
        ce_winner = min(results, key=lambda r: r.ce_end)
        phi_winner = max(results, key=lambda r: r.phi_iit)
        balanced = min(results, key=lambda r: r.ce_end - r.phi_iit * 0.5)
        print(f"    CE  winner:  {ce_winner.name} (CE={ce_winner.ce_end:.4f}, {ce_winner.ce_delta_pct:+.1f}%)")
        print(f"    Φ   winner:  {phi_winner.name} (Φ={phi_winner.phi_iit:.4f}, {phi_winner.phi_delta_pct:+.1f}%)")
        print(f"    Balanced:    {balanced.name}")

        # Tuning recommendation
        print("\n  ══ Tuning Recommendation ══")
        improved = [r for r in results if r != baseline_result and r.ce_delta_pct < 0]
        phi_improved = [r for r in results if r != baseline_result and r.phi_delta_pct > 0]
        both = [r for r in results if r != baseline_result
                and r.ce_delta_pct < 0 and r.phi_delta_pct > 0]

        if both:
            print(f"    ✅ CE↓ + Φ↑ (both improved):")
            for r in both:
                print(f"       {r.name}: CE {r.ce_delta_pct:+.1f}%, Φ {r.phi_delta_pct:+.1f}%")
        if improved and not both:
            print(f"    ↓ CE improved only:")
            for r in improved:
                print(f"       {r.name}: CE {r.ce_delta_pct:+.1f}%")
        if phi_improved and not both:
            print(f"    ↑ Φ improved only:")
            for r in phi_improved:
                print(f"       {r.name}: Φ {r.phi_delta_pct:+.1f}%")

        neither = [r for r in results if r != baseline_result
                   and r.ce_delta_pct >= 0 and r.phi_delta_pct <= 0]
        if neither:
            print(f"    ❌ No improvement:")
            for r in neither:
                print(f"       {r.name}: CE {r.ce_delta_pct:+.1f}%, Φ {r.phi_delta_pct:+.1f}%")

    print(f"\n  Total time: {sum(r.time_sec for r in results):.1f}s")


if __name__ == '__main__':
    main()
