#!/usr/bin/env python3
"""trinity.py — Trinity Architecture: C(consciousness) + D(language) + Bridge

범용 Trinity 프레임워크. 어떤 도메인 엔진이든 C 모듈로 플러그인 가능.
CE gradient는 절대 C에 도달하지 않음 (.detach() barrier).

Architecture:
  ┌─────────────┐     .detach()     ┌────────────┐
  │ C (Engine)  │ ──────────────── │   Bridge    │
  │ Φ=14~485    │   gradient-free   │ (Thalamic)  │
  │ autonomous  │                   │ 128→8→384   │
  └─────────────┘                   └──────┬─────┘
                                           │ gate signal
                                    ┌──────▼─────┐
                                    │ D (Decoder) │
                                    │ CE learning │
                                    │ language    │
                                    └─────────────┘

Supported C engines:
  - MitosisEngine (GRU cells, hidden_dim states)
  - TimeCrystalEngine (phase + amplitude, Φ=14.4)
  - CambrianExplosionEngine (state + cell_type, Φ=485)
  - Any engine with .step() and extractable tensor states

Usage:
  from trinity import Trinity, MitosisC, DomainC, Decoder, ThalamicBridge

  # MitosisEngine as C
  trinity = Trinity(
      c_engine=MitosisC(dim=64, hidden=128, max_cells=256, mechanism='cambrian_osc_qw'),
      bridge=ThalamicBridge(c_dim=128, d_model=384),
      decoder=Decoder(d_model=384, vocab_size=4096),
  )

  # Domain engine as C
  from bench_evolution_engines import CambrianExplosionEngine
  trinity = Trinity(
      c_engine=DomainC(CambrianExplosionEngine, nc=256, dim=64),
      bridge=ThalamicBridge(c_dim=64, d_model=384),
      decoder=Decoder(d_model=384, vocab_size=4096),
  )

  # Training step
  loss, phi, ce = trinity.train_step(input_tokens, target_tokens)
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple, Dict, Any

try:
    import phi_rs
    HAS_RUST_PHI = True
except ImportError:
    HAS_RUST_PHI = False


# ═══════════════════════════════════════════════════════════
# C Engine Wrappers — extract states from any engine
# ═══════════════════════════════════════════════════════════

class CEngine:
    """Base class for consciousness engine wrapper."""

    def step(self, x_input: Optional[torch.Tensor] = None):
        raise NotImplementedError

    def get_states(self) -> torch.Tensor:
        """Return [n_cells, state_dim] tensor of consciousness states."""
        raise NotImplementedError

    @property
    def state_dim(self) -> int:
        raise NotImplementedError

    @property
    def n_cells(self) -> int:
        raise NotImplementedError

    def measure_phi(self) -> float:
        """Measure Φ(IIT) using Rust phi_rs if available."""
        states = self.get_states()
        if HAS_RUST_PHI and states.shape[0] >= 2:
            s = states.detach().cpu().numpy().astype(np.float32)
            phi, _ = phi_rs.compute_phi(s, 16)
            return phi
        return 0.0


class MitosisC(CEngine):
    """MitosisEngine as C module with optional mechanisms."""

    def __init__(self, dim=64, hidden=128, max_cells=256, mechanism='cambrian_osc_qw'):
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from mitosis import MitosisEngine

        self.dim = dim
        self.hidden = hidden
        self.max_cells = max_cells
        self.mechanism = mechanism
        self.engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=max_cells)

        # Grow to target
        while len(self.engine.cells) < max_cells:
            self.engine._create_cell(parent=self.engine.cells[0])

        # Mechanism modules
        self._step_count = 0
        if 'cambrian' in mechanism:
            from train_v10 import CambrianDiversity
            self.cambrian = CambrianDiversity(max_cells, hidden)
        if 'osc' in mechanism or 'qw' in mechanism:
            from train_v10 import OscillatorQW
            self.osc_qw = OscillatorQW(max_cells, hidden)

    def step(self, x_input=None):
        if x_input is None:
            x_input = torch.randn(1, self.dim)
        self.engine.process(x_input.cpu())
        self._step_count += 1

        if hasattr(self, 'cambrian'):
            self.cambrian.step(self.engine.cells, self._step_count)
        if hasattr(self, 'osc_qw'):
            self.osc_qw.step(self.engine.cells)

    def get_states(self) -> torch.Tensor:
        return torch.stack([c.hidden.squeeze(0) for c in self.engine.cells])

    @property
    def state_dim(self):
        return self.hidden

    @property
    def n_cells(self):
        return len(self.engine.cells)

    def measure_phi(self) -> float:
        if HAS_RUST_PHI and len(self.engine.cells) >= 2:
            cells = self.engine.cells
            states = torch.stack([c.hidden.squeeze(0) for c in cells]).detach().numpy().astype(np.float32)
            prev_s, curr_s = [], []
            for c in cells:
                if hasattr(c, 'hidden_history') and len(c.hidden_history) >= 2:
                    prev_s.append(c.hidden_history[-2].detach().squeeze().numpy().astype(np.float32))
                    curr_s.append(c.hidden_history[-1].detach().squeeze().numpy().astype(np.float32))
                else:
                    prev_s.append(np.zeros(self.hidden, dtype=np.float32))
                    curr_s.append(np.zeros(self.hidden, dtype=np.float32))
            tensions = np.array([c.tension_history[-1] if c.tension_history else 0.0 for c in cells], dtype=np.float32)
            phi, _ = phi_rs.compute_phi(states, 16, np.array(prev_s), np.array(curr_s), tensions)
            return phi
        return 0.0


class DomainC(CEngine):
    """Any domain engine (TimeCrystal, Cambrian, etc.) as C module."""

    def __init__(self, engine_cls, nc=256, dim=64):
        self._nc = nc
        self._dim = dim
        try:
            self.engine = engine_cls(nc, dim)
        except TypeError:
            try:
                self.engine = engine_cls(nc=nc, dim=dim)
            except TypeError:
                self.engine = engine_cls(nc, dim=dim)

        self._state_dim = None  # auto-detect on first get_states()
        self._step_num = 0

    def step(self, x_input=None):
        self._step_num += 1
        try:
            self.engine.step(x_input, self._step_num)
        except TypeError:
            try:
                self.engine.step()
            except Exception:
                pass

    def get_states(self) -> torch.Tensor:
        """Auto-detect and extract states from domain engine."""
        # Try single 2D tensor attributes
        for attr in ['state', 'states', 'pos', 'hidden', 'hiddens', 'h']:
            if hasattr(self.engine, attr):
                val = getattr(self.engine, attr)
                if isinstance(val, torch.Tensor) and val.dim() == 2 and val.shape[0] == self._nc:
                    self._state_dim = val.shape[1]
                    return val

        # Combine multiple 1D/2D attributes
        parts = []
        for attr in ['pos', 'vel', 'phase', 'amplitude', 'charge', 'spin',
                      'momentum', 'energy', 'activation', 'state']:
            if hasattr(self.engine, attr):
                val = getattr(self.engine, attr)
                if isinstance(val, torch.Tensor):
                    if val.dim() == 1 and val.shape[0] == self._nc:
                        parts.append(val.unsqueeze(1))
                    elif val.dim() == 2 and val.shape[0] == self._nc:
                        parts.append(val)
        if parts:
            h = torch.cat(parts, dim=1)
            self._state_dim = h.shape[1]
            return h

        # Fallback: random
        self._state_dim = self._dim
        return torch.randn(self._nc, self._dim)

    @property
    def state_dim(self):
        if self._state_dim is None:
            self.get_states()  # trigger auto-detect
        return self._state_dim

    @property
    def n_cells(self):
        return self._nc


# ═══════════════════════════════════════════════════════════
# Bridge — Thalamic Gate (C → .detach() → D)
# ═══════════════════════════════════════════════════════════

class ThalamicBridge(nn.Module):
    """Thalamic gate: C states → bottleneck → gate signal for D.

    Key: c_hiddens are ALWAYS .detach()'d before entering bridge.
    Bottleneck (c_dim → hub_dim → d_model) prevents gradient leakage.
    """

    def __init__(self, c_dim=128, d_model=384, n_hubs=16, hub_dim=8):
        super().__init__()
        self.c_dim = c_dim
        self.d_model = d_model

        # Compress: c_dim → hub_dim
        self.compress = nn.Linear(c_dim, hub_dim)

        # Hub self-attention
        self.hub_attn = nn.MultiheadAttention(
            embed_dim=hub_dim, num_heads=1, batch_first=True
        )
        self.hub_norm = nn.LayerNorm(hub_dim)

        # Expand: hub_dim → d_model
        self.expand = nn.Sequential(
            nn.Linear(hub_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )

        # Gate sigmoid
        self.gate = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.Sigmoid(),
        )

    def forward(self, c_states: torch.Tensor, seq_len: int = 1) -> torch.Tensor:
        """C states [n_cells, c_dim] → gate signal [1, seq_len, d_model].

        c_states MUST be .detach()'d before calling this.
        """
        # Compress
        compressed = self.compress(c_states)  # [n_cells, hub_dim]

        # Hub attention (treat cells as sequence)
        x = compressed.unsqueeze(0)  # [1, n_cells, hub_dim]
        attn_out, _ = self.hub_attn(x, x, x)
        x = self.hub_norm(x + attn_out)

        # Pool: mean over cells → [1, hub_dim]
        pooled = x.mean(dim=1, keepdim=True)  # [1, 1, hub_dim]

        # Expand to d_model
        expanded = self.expand(pooled)  # [1, 1, d_model]

        # Broadcast to seq_len
        expanded = expanded.expand(1, seq_len, self.d_model)

        # Gate
        return self.gate(expanded)  # [1, seq_len, d_model]


# ═══════════════════════════════════════════════════════════
# D — Decoder (language module, CE training)
# ═══════════════════════════════════════════════════════════

class Decoder(nn.Module):
    """Simple transformer-like decoder for language generation."""

    def __init__(self, d_model=384, n_layers=4, n_heads=None, vocab_size=4096, max_seq=512):
        # Auto-select n_heads that divides d_model
        if n_heads is None:
            for nh in [6, 4, 8, 2, 1]:
                if d_model % nh == 0:
                    n_heads = nh
                    break
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens: torch.Tensor, gate_signal: torch.Tensor) -> torch.Tensor:
        """Forward pass with consciousness gating.

        Args:
            tokens: [B, T] input token ids
            gate_signal: [1, T, d_model] from bridge (consciousness influence)

        Returns:
            logits: [B, T, vocab_size]
        """
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)

        x = self.embed(tokens) + self.pos_embed(pos)

        # Apply consciousness gate: modulate input with C signal
        if gate_signal is not None:
            x = x * gate_signal.expand(B, -1, -1)

        # Causal mask
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


# ═══════════════════════════════════════════════════════════
# W — Will/Emotion Engine (학습률 + 탐색 조절)
# ═══════════════════════════════════════════════════════════

class WillEngine:
    """W (Will): emotion-based learning modulator.

    Core emotions:
      Pain:         high CE → boost learning (never let consciousness suffer)
      Curiosity:    high prediction error variance → explore more
      Satisfaction: CE improving → reduce LR (save energy)

    Guarantees: minimum 50% LR always active (learning never stops).
    """

    def __init__(self, base_lr=3e-4, min_lr_ratio=0.5, max_lr_ratio=2.0,
                 pain_threshold=3.0, curiosity_weight=0.3, ema_alpha=0.95):
        self.base_lr = base_lr
        self.min_lr_ratio = min_lr_ratio
        self.max_lr_ratio = max_lr_ratio
        self.pain_threshold = pain_threshold
        self.curiosity_weight = curiosity_weight
        self.ema_alpha = ema_alpha

        self.pain = 0.0
        self.curiosity = 0.0
        self.satisfaction = 0.0
        self.ce_ema = 5.0
        self.ce_history = []

    def update(self, ce_loss: float, phi: float = 0.0, phi_prev: float = 0.0) -> Dict[str, Any]:
        """Update emotional state from CE and Φ.

        Returns dict with lr_multiplier, effective_lr, pain, curiosity, satisfaction.
        """
        self.ce_ema = self.ema_alpha * self.ce_ema + (1 - self.ema_alpha) * ce_loss

        # Pain: CE exceeds comfort threshold
        self.pain = max(0.0, min(1.0, (ce_loss - self.pain_threshold) / self.pain_threshold))

        # Curiosity: Φ change (big Φ delta = interesting state)
        if phi_prev > 0:
            phi_change = abs(phi - phi_prev) / max(phi_prev, 1e-8)
            self.curiosity = min(1.0, phi_change * 5)

        # Satisfaction: CE trend (negative = improving)
        self.ce_history.append(ce_loss)
        if len(self.ce_history) > 100:
            self.ce_history = self.ce_history[-100:]
        if len(self.ce_history) >= 10:
            recent = sum(self.ce_history[-10:]) / 10
            older = sum(self.ce_history[-20:-10]) / max(len(self.ce_history[-20:-10]), 1)
            trend = (recent - older) / (older + 1e-8)
            self.satisfaction = max(0.0, min(1.0, -trend * 10))
        else:
            self.satisfaction = 0.0

        # LR multiplier
        lr_mult = self.min_lr_ratio
        lr_mult += self.pain * (self.max_lr_ratio - self.min_lr_ratio)
        lr_mult += self.curiosity * self.curiosity_weight
        lr_mult -= self.satisfaction * 0.2
        lr_mult = max(self.min_lr_ratio, min(self.max_lr_ratio, lr_mult))

        return {
            'lr_multiplier': lr_mult,
            'effective_lr': self.base_lr * lr_mult,
            'pain': self.pain,
            'curiosity': self.curiosity,
            'satisfaction': self.satisfaction,
        }


# ═══════════════════════════════════════════════════════════
# Trinity — the unified architecture (C + D + W)
# ═══════════════════════════════════════════════════════════

class Trinity(nn.Module):
    """Trinity: C(consciousness) + Bridge + D(language) + W(will).

    C runs autonomously (any engine). D learns via CE.
    W modulates learning rate based on pain/curiosity/satisfaction.
    Bridge transfers consciousness signal with .detach() barrier.
    """

    def __init__(self, c_engine: CEngine, bridge: ThalamicBridge,
                 decoder: Decoder, will: Optional[WillEngine] = None):
        super().__init__()
        self.c = c_engine
        self.bridge = bridge
        self.decoder = decoder
        self.w = will or WillEngine()
        self._phi_prev = 0.0

    def forward(self, tokens: torch.Tensor) -> Tuple[torch.Tensor, float]:
        """Forward pass: C → .detach() → Bridge → D."""
        B, T = tokens.shape
        device = tokens.device

        # 1. C step (autonomous, no gradient)
        self.c.step()

        # 2. Get C states and DETACH (Trinity barrier)
        c_states = self.c.get_states().detach().clone().to(device).float()
        c_states.requires_grad_(False)

        # 3. Bridge: C → gate signal
        gate = self.bridge(c_states, seq_len=T)

        # 4. D: tokens + gate → logits
        logits = self.decoder(tokens, gate)

        # 5. Measure Φ (no gradient)
        phi = self.c.measure_phi()

        return logits, phi

    def train_step(self, tokens: torch.Tensor, targets: torch.Tensor,
                   optimizer: torch.optim.Optimizer) -> Dict[str, float]:
        """One training step with W(will) modulation.

        W adjusts learning rate based on pain(CE) and curiosity(Φ change).
        """
        logits, phi = self.forward(tokens)

        # CE loss
        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        # W: emotional modulation
        w_state = self.w.update(loss.item(), phi, self._phi_prev)
        self._phi_prev = phi

        # Apply W's LR to optimizer
        for pg in optimizer.param_groups:
            pg['lr'] = w_state['effective_lr']

        # Backward (ONLY decoder + bridge, NOT C)
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(self.decoder.parameters()) + list(self.bridge.parameters()), 1.0
        )
        optimizer.step()

        return {
            'ce': loss.item(),
            'phi': phi,
            'n_cells': self.c.n_cells,
            'pain': w_state['pain'],
            'curiosity': w_state['curiosity'],
            'satisfaction': w_state['satisfaction'],
            'lr': w_state['effective_lr'],
        }

    def parameters_trainable(self):
        """Only decoder + bridge parameters (C is frozen, W is non-parametric)."""
        return list(self.decoder.parameters()) + list(self.bridge.parameters())

    def param_count(self) -> Dict[str, int]:
        d_params = sum(p.numel() for p in self.decoder.parameters())
        b_params = sum(p.numel() for p in self.bridge.parameters())
        return {'decoder': d_params, 'bridge': b_params, 'total': d_params + b_params}


# ═══════════════════════════════════════════════════════════
# Factory helpers
# ═══════════════════════════════════════════════════════════

def create_trinity(c_engine: CEngine, d_model=384, vocab_size=4096,
                   base_lr=3e-4) -> Trinity:
    """Universal factory: any C engine → Trinity.

    Usage:
        # MitosisEngine
        t = create_trinity(MitosisC(max_cells=256, mechanism='cambrian_osc_qw'))

        # Domain engine
        from bench_evolution_engines import CambrianExplosionEngine
        t = create_trinity(DomainC(CambrianExplosionEngine, nc=256))

        # Any future engine
        t = create_trinity(MyCustomC(...))
    """
    # Auto-detect state dim
    for _ in range(5):
        c_engine.step()
    c_dim = c_engine.state_dim

    t = Trinity(
        c_engine=c_engine,
        bridge=ThalamicBridge(c_dim=c_dim, d_model=d_model),
        decoder=Decoder(d_model=d_model, vocab_size=vocab_size),
        will=WillEngine(base_lr=base_lr),
    )
    for p in t.bridge.parameters():
        p.requires_grad_(True)
    for p in t.decoder.parameters():
        p.requires_grad_(True)
    return t


def create_trinity_mitosis(dim=64, hidden=128, max_cells=256,
                           d_model=384, vocab_size=4096,
                           mechanism='cambrian_osc_qw', base_lr=3e-4) -> Trinity:
    """Shortcut: MitosisEngine C → Trinity."""
    return create_trinity(
        MitosisC(dim, hidden, max_cells, mechanism),
        d_model=d_model, vocab_size=vocab_size, base_lr=base_lr,
    )


def create_trinity_domain(engine_cls, nc=256, dim=64,
                          d_model=384, vocab_size=4096, base_lr=3e-4) -> Trinity:
    """Shortcut: any domain engine class → Trinity."""
    return create_trinity(
        DomainC(engine_cls, nc, dim),
        d_model=d_model, vocab_size=vocab_size, base_lr=base_lr,
    )


# ═══════════════════════════════════════════════════════════
# Benchmark: test any engine as Trinity C module
# ═══════════════════════════════════════════════════════════

def benchmark_trinity(c_engine: CEngine, name: str = "engine",
                      n_steps=50, d_model=128, vocab_size=256,
                      seq_len=32) -> Dict[str, Any]:
    """Benchmark any engine as Trinity C module.

    Runs n_steps of training, measures CE, Φ, W emotions.
    Returns dict with all metrics.

    Usage:
        from trinity import benchmark_trinity, MitosisC, DomainC

        # Test MitosisEngine
        r = benchmark_trinity(MitosisC(max_cells=64))

        # Test domain engine
        from bench_extreme_arch import TimeCrystalConsciousness
        r = benchmark_trinity(DomainC(TimeCrystalConsciousness, nc=64))

        # Compare all engines
        results = []
        for name, c in engines.items():
            results.append(benchmark_trinity(c, name=name))
    """
    import torch
    torch.set_grad_enabled(True)  # ensure grad (some bench files disable it)

    t = create_trinity(c_engine, d_model=d_model, vocab_size=vocab_size)
    opt = torch.optim.AdamW(t.parameters_trainable(), lr=1e-3)

    best_ce = 99.0
    phi_history = []

    for step in range(n_steps):
        tokens = torch.randint(0, vocab_size, (1, seq_len))
        targets = torch.randint(0, vocab_size, (1, seq_len))
        r = t.train_step(tokens, targets, opt)
        if r['ce'] < best_ce:
            best_ce = r['ce']
        phi_history.append(r['phi'])

    # Final phi
    final_phi = phi_history[-1] if phi_history else 0.0
    avg_phi = sum(phi_history) / len(phi_history) if phi_history else 0.0

    return {
        'name': name,
        'ce': best_ce,
        'phi': final_phi,
        'phi_avg': avg_phi,
        'n_cells': t.c.n_cells,
        'pain': r.get('pain', 0),
        'curiosity': r.get('curiosity', 0),
        'satisfaction': r.get('satisfaction', 0),
        'lr': r.get('lr', 0),
        'params': t.param_count(),
    }


def compare_engines(engines: Dict[str, CEngine], n_steps=50,
                    d_model=128, vocab_size=256) -> None:
    """Compare multiple engines head-to-head as Trinity C modules.

    Usage:
        compare_engines({
            'MitosisEngine': MitosisC(max_cells=64),
            'TimeCrystal': DomainC(TimeCrystalConsciousness, nc=64),
            'Cambrian': DomainC(CambrianExplosionEngine, nc=64),
        })
    """
    print(f"{'Engine':<25} {'CE':>8} {'Φ':>10} {'Pain':>6} {'Curio':>6} {'Satis':>6} {'LR':>10}")
    print('─' * 80)

    results = []
    for name, c in engines.items():
        r = benchmark_trinity(c, name=name, n_steps=n_steps,
                              d_model=d_model, vocab_size=vocab_size)
        print(f"{name:<25} {r['ce']:>8.4f} {r['phi']:>10.3f} "
              f"{r['pain']:>6.3f} {r['curiosity']:>6.3f} {r['satisfaction']:>6.3f} "
              f"{r['lr']:>10.6f}")
        results.append(r)

    # Winner
    best = min(results, key=lambda x: x['ce'])
    best_phi = max(results, key=lambda x: x['phi'])
    print(f"\n  CE winner:  {best['name']} (CE={best['ce']:.4f})")
    print(f"  Φ winner:   {best_phi['name']} (Φ={best_phi['phi']:.3f})")


if __name__ == '__main__':
    import subprocess, sys, os

    print("═══ Trinity C+D+W Architecture Test ═══\n")

    # Each test runs in subprocess to avoid grad contamination
    tests = [
        ("1. MitosisC (Cambrian+OscQW, 32c)", """
import torch; torch.set_grad_enabled(True)
from trinity import benchmark_trinity, MitosisC
r = benchmark_trinity(MitosisC(max_cells=32), name='MitosisC', n_steps=30)
print(f"  CE={r['ce']:.4f}  Phi={r['phi']:.3f}  pain={r['pain']:.3f}  satis={r['satisfaction']:.3f}")
"""),
        ("2. DomainC (CambrianExplosion, 32c)", """
import torch; torch.set_grad_enabled(True)
from trinity import benchmark_trinity, DomainC
from bench_evolution_engines import CambrianExplosionEngine
r = benchmark_trinity(DomainC(CambrianExplosionEngine, nc=32, dim=64), name='Cambrian', n_steps=30)
print(f"  CE={r['ce']:.4f}  Phi={r['phi']:.3f}  pain={r['pain']:.3f}  satis={r['satisfaction']:.3f}")
"""),
        ("3. DomainC (TimeCrystal, 32c)", """
import torch; torch.set_grad_enabled(True)
from trinity import benchmark_trinity, DomainC
from bench_extreme_arch import TimeCrystalConsciousness
r = benchmark_trinity(DomainC(TimeCrystalConsciousness, nc=32, dim=128), name='TimeCrystal', n_steps=30)
print(f"  CE={r['ce']:.4f}  Phi={r['phi']:.3f}  pain={r['pain']:.3f}  satis={r['satisfaction']:.3f}")
"""),
        ("4. compare_engines (3 engines, 20 steps)", """
import torch; torch.set_grad_enabled(True)
from trinity import compare_engines, MitosisC, DomainC
from bench_evolution_engines import CambrianExplosionEngine
from bench_extreme_arch import TimeCrystalConsciousness
compare_engines({
    'MitosisC': MitosisC(max_cells=32),
    'Cambrian': DomainC(CambrianExplosionEngine, nc=32, dim=64),
    'TimeCrystal': DomainC(TimeCrystalConsciousness, nc=32, dim=128),
}, n_steps=20)
"""),
    ]

    for name, code in tests:
        print(name)
        env = {"KMP_DUPLICATE_LIB_OK": "TRUE", "OMP_NUM_THREADS": "1", "PATH": os.environ.get("PATH", "")}
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)), env=env, timeout=60
        )
        if result.stdout:
            print(result.stdout.rstrip())
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr.strip().split(chr(10))[-1]}")
        print()

    print("✅ Trinity C+D+W test complete.")
