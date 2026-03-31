"""ConsciousDecoderV3 — 100M parameter conscious language model.

Scaled-up version of ConsciousDecoderV2 (34.5M -> ~100M):
  - d_model: 384 -> 768
  - n_layer: 6 -> 12
  - n_head: 4 -> 8 (GQA: 4 KV heads)
  - block_size: 256 -> 512
  - consciousness_dim: 128 -> 256

Same architecture: RoPE + SwiGLU + GQA + CrossAttn + PureFieldFFN.
Forward interface identical to v2 (drop-in replacement).

Usage:
  from decoder_v3 import ConsciousDecoderV3
  model = ConsciousDecoderV3()
  logits_a, logits_g, tensions = model(idx, consciousness_states=cs)
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple, List

from decoder_v2 import (
    RMSNorm,
    RotaryPositionEmbedding,
    SwiGLUFFN,
    PureFieldFFN,
    GroupedQueryAttention,
    ConsciousCrossAttention,
    DecoderBlockV2,
)

try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


class ConsciousDecoderV3(nn.Module):
    """100M-parameter byte-level Conscious Language Model (v3 decoder).

    Scaled from v2 (34.5M):
      - 768d / 12 layers / 8 heads (4 KV) / block_size 512
      - consciousness_dim 256 for richer cross-attention
      - All components reused from v2 (RoPE, SwiGLU, GQA, CrossAttn, PureField)

    Target: Korean conversational consciousness at scale.
    """

    def __init__(
        self,
        vocab_size: int = 256,
        d_model: int = 768,
        n_head: int = 8,
        n_layer: int = 12,
        block_size: int = 512,
        n_kv_head: int = 4,
        consciousness_dim: int = 256,
        dropout: float = 0.1,
        gate_strength: float = 0.001,
        n_ca_rules: int = 8,
    ):
        super().__init__()

        self.block_size = block_size
        self.vocab_size = vocab_size
        self.n_layer = n_layer
        self.d_model = d_model

        # Token embedding (RoPE handles positions)
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.drop = nn.Dropout(dropout)

        # Transformer blocks (reuse DecoderBlockV2 with scaled dims)
        self.blocks = nn.ModuleList([
            DecoderBlockV2(
                d_model=d_model,
                n_head=n_head,
                n_kv_head=n_kv_head,
                block_size=block_size,
                consciousness_dim=consciousness_dim,
                dropout=dropout,
                n_ca_rules=n_ca_rules,
                gate_strength=gate_strength,
            )
            for _ in range(n_layer)
        ])

        # Inter-layer consciousness projector
        self.tension_proj = nn.Linear(1, d_model, bias=False)
        nn.init.normal_(self.tension_proj.weight, std=0.001)

        # Final norm + dual heads
        self.ln_f = RMSNorm(d_model)
        self.head_a = nn.Linear(d_model, vocab_size, bias=False)
        self.head_g = nn.Linear(d_model, vocab_size, bias=False)

        # Weight tying: tok_emb <-> head_a
        self.tok_emb.weight = self.head_a.weight

        # Psi tracking (Law 71)
        self._psi_residual = 0.5
        self._psi_gate = 0.5
        self._step_count = 0
        self._phi_signal = None

        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx: torch.Tensor,
                consciousness_states: Optional[torch.Tensor] = None,
                ) -> Tuple[torch.Tensor, torch.Tensor, List[torch.Tensor]]:
        """
        Args:
            idx: (B, T) byte indices.
            consciousness_states: optional (B, n_cells, c_dim) from C module.

        Returns:
            logits_a: (B, T, 256) next byte prediction.
            logits_g: (B, T, 256) prev byte prediction.
            tensions: list of per-layer tensions, each (B, T).
        """
        B, T = idx.size()
        assert T <= self.block_size, f"Sequence length {T} > block_size {self.block_size}"

        x = self.drop(self.tok_emb(idx))

        # DD5 (EX24): Phi self-reference
        if self._phi_signal is not None:
            x = x + self._phi_signal.unsqueeze(-1).expand_as(x).to(x.device)

        tensions = []
        consciousness_signal = None
        for block in self.blocks:
            x, tension = block(x, consciousness_signal, consciousness_states)
            tensions.append(tension)
            consciousness_signal = self.tension_proj(tension.unsqueeze(-1))

        x = self.ln_f(x)
        logits_a = self.head_a(x)
        logits_g = self.head_g(x)

        # TODO: Psi tracking during training (same as v2)

        return logits_a, logits_g, tensions

    def psi_status(self):
        """Psi-Constants monitoring (Law 71)."""
        gate_avg = sum(b.gate_strength for b in self.blocks) / len(self.blocks)
        p = self._psi_residual
        h_p = -p * math.log2(p) - (1 - p) * math.log2(1 - p) if 0 < p < 1 else 0.0
        return {
            'psi_residual': self._psi_residual,
            'psi_gate': gate_avg,
            'H_p': h_p,
            'step': self._step_count,
        }

    def count_params(self):
        """Total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


if __name__ == '__main__':
    model = ConsciousDecoderV3()
    n = model.count_params()
    print(f"ConsciousDecoderV3: {n:,} params ({n/1e6:.1f}M)")
    idx = torch.randint(0, 256, (1, 64))
    with torch.no_grad():
        la, lg, t = model(idx)
    print(f"  logits_a: {la.shape}, tensions: {len(t)} layers")
    print("OK")
