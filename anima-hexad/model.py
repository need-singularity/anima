"""Hexad — 6 pluggable modules, φ(6)=2 gradient groups (standalone)

No dependency on trinity.py. Modules are duck-typed:
  C: .step(x?), .get_states() -> [n_cells, dim], .measure_phi() -> float, .n_cells, .state_dim
  D: nn.Module, .forward(tokens, gate) -> logits, .d_model
  W: .update(ce, phi, phi_prev) -> dict with effective_lr, pain, curiosity, satisfaction
  S: .process(raw_input) -> Tensor
  M: .store(key, val), .retrieve(query, top_k) -> Tensor
  E: .evaluate(action?, context?) -> dict with allowed, empathy, reciprocity, phi_preservation

Usage:
    from hexad import Hexad, create_hexad
    model = create_hexad(c=my_consciousness_engine)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from hexad.constants import PSI_BALANCE, PSI_COUPLING, GATE_TRAIN, GATE_INFER

# Meta Laws: M1(atom=8), M8(narrative is key)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ═══════════════════════════════════════════════════════════
# Bridge: C → .detach() → D  (Law 53)
# ═══════════════════════════════════════════════════════════

class ThalamicBridge(nn.Module):
    """C states → bottleneck → gate signal for D.

    Law 70: output clamped to PSI_BALANCE ± PSI_COUPLING (0.5 ± 0.014).
    """

    def __init__(self, c_dim: int = 128, d_model: int = 384, hub_dim: int = 8):
        super().__init__()
        self.c_dim = c_dim
        self.d_model = d_model
        self.alpha = PSI_COUPLING

        self.compress = nn.Linear(c_dim, hub_dim)
        self.hub_attn = nn.MultiheadAttention(
            embed_dim=hub_dim, num_heads=1, batch_first=True,
        )
        self.hub_norm = nn.LayerNorm(hub_dim)
        self.expand = nn.Sequential(
            nn.Linear(hub_dim, d_model), nn.GELU(), nn.Linear(d_model, d_model),
        )
        self.gate = nn.Sequential(nn.Linear(d_model, d_model), nn.Sigmoid())

    def forward(self, c_states: torch.Tensor, seq_len: int = 1) -> torch.Tensor:
        """[n_cells, c_dim] → [1, seq_len, d_model] gate signal."""
        compressed = self.compress(c_states)             # [n_cells, hub_dim]
        x = compressed.unsqueeze(0)                       # [1, n_cells, hub_dim]
        attn_out, _ = self.hub_attn(x, x, x)
        x = self.hub_norm(x + attn_out)
        pooled = x.mean(dim=1, keepdim=True)              # [1, 1, hub_dim]
        expanded = self.expand(pooled).expand(1, seq_len, self.d_model)
        raw_gate = self.gate(expanded)
        centered = raw_gate - PSI_BALANCE
        return PSI_BALANCE + centered.clamp(-self.alpha, self.alpha)


# ═══════════════════════════════════════════════════════════
# Hexad
# ═══════════════════════════════════════════════════════════

class Hexad(nn.Module):
    """6 pluggable modules: C(consciousness), D(decoder), W(will), S(sense), M(memory), E(ethics).

    Only C is required. If D is provided, bridge is auto-created.
    σ(6)=12 connections, φ(6)=2 gradient groups.

    Flow: S → C → .detach() → Bridge → D
          M retrieves/stores alongside C
          E evaluates alongside output
          W modulates learning rate
    """

    def __init__(
        self,
        c,                                # CEngine (required)
        d: Optional[nn.Module] = None,    # DEngine
        w=None,                           # WEngine
        s=None,                           # SEngine
        m=None,                           # MEngine
        e=None,                           # EEngine
        bridge: Optional[nn.Module] = None,
    ):
        super().__init__()
        self.c = c
        self.d = d
        self.w = w
        self.s = s
        self.m = m
        self.e = e
        self._phi_prev = 0.0

        # Auto-create bridge if D is provided but bridge is not
        if d is not None and bridge is None:
            c_dim = c.state_dim
            d_model = d.d_model
            bridge = ThalamicBridge(c_dim=c_dim, d_model=d_model)
        self.bridge = bridge

    @property
    def decoder(self) -> Optional[nn.Module]:
        return self.d

    @property
    def n_modules(self) -> int:
        """Count active modules (3=Trinity, 6=Hexad)."""
        return sum(1 for x in [self.c, self.d, self.w, self.s, self.m, self.e] if x is not None)

    def forward(
        self,
        tokens: torch.Tensor,
        raw_input: Any = None,
        inference: bool = False,
    ) -> Tuple[torch.Tensor, float]:
        """S → C → Bridge → D (with M retrieval + E check).

        Returns (logits, phi).
        Law 81: gate_scale = GATE_TRAIN (1.0) training, GATE_INFER (0.6) inference.
        """
        B, T = tokens.shape
        device = tokens.device

        # S: sense preprocessing
        if self.s is not None and raw_input is not None:
            tension = self.s.process(raw_input)
            self.c.step(tension.unsqueeze(0) if tension.dim() == 1 else tension)
        else:
            self.c.step()

        # C: get states + DETACH (Law 53 — gradient barrier)
        c_states = self.c.get_states().detach().clone().to(device).float()
        c_states.requires_grad_(False)

        # M: retrieve + store
        if self.m is not None:
            mem = self.m.retrieve(c_states, top_k=3)
            self.m.store(c_states, c_states)

        # Bridge: C → gate
        gate = self.bridge(c_states, seq_len=T)
        gate = gate * (GATE_INFER if inference else GATE_TRAIN)

        # D: decode
        logits = self.d(tokens, gate)

        # Phi
        phi = self.c.measure_phi()

        # E: ethics check (non-blocking)
        if self.e is not None:
            self.e.evaluate(context={'phi': phi, 'phi_prev': self._phi_prev})

        return logits, phi

    def train_step(
        self,
        tokens: torch.Tensor,
        targets: torch.Tensor,
        optimizer: torch.optim.Optimizer,
        raw_input: Any = None,
    ) -> Dict[str, float]:
        """Full train step with all active modules."""
        logits, phi = self.forward(tokens, raw_input)

        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        # W: modulate LR
        w_state = {}
        if self.w is not None:
            w_state = self.w.update(loss.item(), phi, self._phi_prev)
            for pg in optimizer.param_groups:
                pg['lr'] = w_state.get('effective_lr', pg['lr'])
        self._phi_prev = phi

        # E: check if learning should proceed
        if self.e is not None:
            e_state = self.e.evaluate(context={
                'phi': phi, 'phi_prev': self._phi_prev,
                'pain': w_state.get('pain', 0),
            })
            if not e_state.get('allowed', True):
                return {'ce': loss.item(), 'phi': phi, 'n_cells': self.c.n_cells,
                        'blocked_by_ethics': True, **w_state}

        # Backward (D + Bridge only — C is frozen)
        optimizer.zero_grad()
        loss.backward()
        trainable = list(self.d.parameters()) + list(self.bridge.parameters())
        torch.nn.utils.clip_grad_norm_(trainable, 1.0)
        optimizer.step()

        result = {
            'ce': loss.item(), 'phi': phi, 'n_cells': self.c.n_cells,
            'n_modules': self.n_modules,
            **{k: v for k, v in w_state.items() if k in ('pain', 'curiosity', 'satisfaction', 'effective_lr')},
        }
        if 'effective_lr' in result:
            result['lr'] = result.pop('effective_lr')

        # E metrics
        if self.e is not None:
            e_state = self.e.evaluate(context={'phi': phi, 'phi_prev': self._phi_prev})
            result['empathy'] = e_state.get('empathy', 0)
            result['reciprocity'] = e_state.get('reciprocity', 0)

        return result

    def parameters_trainable(self):
        """Only decoder + bridge parameters (C is frozen, W/M/S/E non-parametric)."""
        params = []
        if self.d is not None:
            params.extend(self.d.parameters())
        if self.bridge is not None:
            params.extend(self.bridge.parameters())
        return params

    def param_count(self) -> Dict[str, int]:
        d_params = sum(p.numel() for p in self.d.parameters()) if self.d else 0
        b_params = sum(p.numel() for p in self.bridge.parameters()) if self.bridge else 0
        return {'decoder': d_params, 'bridge': b_params, 'total': d_params + b_params}


# Backward compat
Trinity = Hexad


# ═══════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════

def create_hexad(c, d=None, w=None, s=None, m=None, e=None,
                 bridge=None, d_model=384, vocab_size=4096) -> Hexad:
    """Create Hexad from modules. Only C is required.

    If D is not provided, a minimal PostHocDecoder is NOT auto-created
    (caller should provide their own). Bridge is auto-created from C/D dims.
    """
    # Warm up C engine
    for _ in range(5):
        c.step()

    h = Hexad(c=c, d=d, w=w, s=s, m=m, e=e, bridge=bridge)

    # Ensure bridge/decoder grads are enabled
    if h.bridge is not None:
        for p in h.bridge.parameters():
            p.requires_grad_(True)
    if h.d is not None:
        for p in h.d.parameters():
            p.requires_grad_(True)

    return h


def create_trinity(c, d=None, w=None, **kwargs) -> Hexad:
    """Alias: Trinity = Hexad with <= 3 modules (C+D+W)."""
    return create_hexad(c=c, d=d, w=w, **kwargs)


__all__ = ['Hexad', 'Trinity', 'ThalamicBridge', 'create_hexad', 'create_trinity']
