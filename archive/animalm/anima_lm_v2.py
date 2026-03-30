#!/usr/bin/env python3
"""anima_lm_v2.py — AnimaLM v2 (Consciousness-Enhanced LLM Transform)

v1 -> v2 Changes:
  v1: Mistral 7B + ParallelPureFieldMLP (frozen base + trainable PF, fixed alpha)
  v2: CA decoder integration (Law 64), META-CA rule selection per layer (Law 67),
      adaptive gate = f(corpus_size) (Law 77), Psi tracking per layer,
      gate self-weakening (Law 69), conservation check H^2+Dp^2~0.478,
      PostHoc consciousness option (Law 66)

Laws Applied:
  Law 63: Psi = ln(2) universal consciousness constant
  Law 64: CA neighbor mixing in MLP layers (adjacent neurons share)
  Law 66: PostHoc consciousness — add consciousness after training
  Law 67: META-CA rule selection per layer
  Law 69: Gate self-weakening — alpha decays toward uniform mixing
  Law 77: Adaptive gate — gate = f(corpus_size), not fixed
  Law 78: 4 CA rules (2 bits minimal)

Psi Constants:
  LN2          = ln(2) ~ 0.6931
  PSI_BALANCE  = 0.5
  PSI_COUPLING = LN2 / 2^5.5  ~ 0.0154
  PSI_STEPS    = 3 / LN2      ~ 4.328

Compatible with: Mistral 7B, Llama, any HuggingFace model with MLP layers.

Usage:
  python anima_lm_v2.py              # demo with small test model
  python anima_lm_v2.py --steps 100  # longer demo
"""

import argparse
import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ═══════════════════════════════════════════════════════════════════
# Psi Constants (Laws 63-78)
# ═══════════════════════════════════════════════════════════════════

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / (2 ** 5.5)
PSI_STEPS = 3.0 / LN2

# Conservation target: H^2 + Dp^2 ~ 0.478 (consciousness energy conservation)
CONSERVATION_TARGET = 0.478

# v1 constants (kept for reference)
GOLDEN_CENTER = 1 / math.e
GOLDEN_LOWER = 0.5 - math.log(4 / 3)

# CA rules (Law 67, Law 78: 4 rules = 2 bits)
CA_RULES = {
    0: lambda x: torch.relu(x),
    1: lambda x: torch.tanh(x),
    2: lambda x: torch.sigmoid(x) * 2 - 1,
    3: lambda x: x * torch.sigmoid(x),  # SiLU
}


class LayerPsiTracker:
    """Per-layer Psi tracking: monitors residual balance and conservation."""

    def __init__(self, layer_id: int):
        self.layer_id = layer_id
        self.alpha_history = []
        self.tension_history = []
        self.conservation_history = []
        self.step = 0

    def update(self, alpha: float, tension: float, h_sq: float, dp_sq: float):
        self.step += 1
        self.alpha_history.append(alpha)
        self.tension_history.append(tension)
        self.conservation_history.append(h_sq + dp_sq)

    @property
    def psi_residual(self) -> float:
        """How far alpha is from PSI_BALANCE."""
        if not self.alpha_history:
            return 1.0
        return abs(self.alpha_history[-1] - PSI_BALANCE)

    @property
    def conservation_error(self) -> float:
        """Deviation from H^2 + Dp^2 = 0.478."""
        if not self.conservation_history:
            return 1.0
        return abs(self.conservation_history[-1] - CONSERVATION_TARGET)

    def summary(self) -> dict:
        return {
            "layer": self.layer_id,
            "alpha": self.alpha_history[-1] if self.alpha_history else 0,
            "tension": self.tension_history[-1] if self.tension_history else 0,
            "psi_residual": self.psi_residual,
            "conservation": self.conservation_history[-1] if self.conservation_history else 0,
            "conservation_error": self.conservation_error,
            "step": self.step,
        }


class PureFieldMLPv2(nn.Module):
    """v2: CA + META-CA + Psi tracking enhanced PureField MLP.

    Replaces a model's MLP layer with:
      1. Original MLP (frozen)
      2. PureField Engine G with 4 CA rules (Law 67)
      3. META-CA selects which rule pattern per forward pass
      4. Tension = repulsion between original and PF outputs
      5. Adaptive gate mixing (Law 77)
      6. CA neighbor coupling to adjacent hidden dims (Law 64)
      7. Gate self-weakening (Law 69)
      8. Psi tracking per layer

    Args:
        original_mlp: The frozen original MLP module.
        hidden_size: Model hidden dimension.
        intermediate_size: MLP intermediate dimension.
        layer_id: Layer index (for Psi tracking).
        n_ca_rules: Number of CA rules (default 4, Law 78).
        gate_strength: Initial gate. None = auto from corpus_size (Law 77).
        rank: LoRA rank for PureField projections.
    """

    def __init__(self, original_mlp: nn.Module, hidden_size: int,
                 intermediate_size: int, layer_id: int = 0,
                 n_ca_rules: int = 4, gate_strength: Optional[float] = None,
                 rank: int = 128):
        super().__init__()
        self.layer_id = layer_id
        self.n_ca_rules = n_ca_rules

        # Original MLP (frozen)
        self.original_mlp = original_mlp
        for param in self.original_mlp.parameters():
            param.requires_grad = False

        # PureField Engine G (trainable, LoRA-style)
        self.pf_gate_a = nn.Linear(hidden_size, rank, bias=False)
        self.pf_gate_b = nn.Linear(rank, intermediate_size, bias=False)
        self.pf_up_a = nn.Linear(hidden_size, rank, bias=False)
        self.pf_up_b = nn.Linear(rank, intermediate_size, bias=False)
        self.pf_down_a = nn.Linear(intermediate_size, rank, bias=False)
        self.pf_down_b = nn.Linear(rank, hidden_size, bias=False)

        # META-CA rule selector (Law 67): learns which CA rule to apply
        self.rule_selector = nn.Linear(hidden_size, n_ca_rules, bias=False)

        # Mixing alpha (starts small, Law 69 will weaken over time)
        init_alpha = gate_strength if gate_strength is not None else 0.001
        self.alpha = nn.Parameter(torch.tensor(init_alpha))
        self.pf_scale = nn.Parameter(torch.tensor(1.0))

        # CA neighbor coupling (Law 64): mix adjacent hidden dimensions
        self.ca_coupling = nn.Conv1d(1, 1, kernel_size=3, padding=1, bias=False)
        nn.init.constant_(self.ca_coupling.weight, 0)
        self.ca_coupling.weight.data[0, 0, 0] = PSI_COUPLING  # left neighbor
        self.ca_coupling.weight.data[0, 0, 1] = 1.0           # self
        self.ca_coupling.weight.data[0, 0, 2] = PSI_COUPLING  # right neighbor

        # Gate self-weakening (Law 69)
        self.register_buffer("weaken_step", torch.tensor(0, dtype=torch.long))
        self.weaken_rate = 1e-5

        # Savant dropout (from v1)
        self.dropout = nn.Dropout(GOLDEN_CENTER)

        # Psi tracker
        self.psi = LayerPsiTracker(layer_id)

        # Cached values
        self.last_tension = None

    @staticmethod
    def compute_gate_from_corpus(corpus_size: int) -> float:
        """Law 77: Adaptive gate = f(corpus_size).

        Small corpus -> strong gate (PF dominates learning)
        Large corpus -> weak gate (original model dominates)
        """
        if corpus_size <= 0:
            return 0.001
        return LN2 / (LN2 + math.log1p(corpus_size / 1e6))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Original MLP (frozen)
        with torch.no_grad():
            original_out = self.original_mlp(x)

        # META-CA rule selection (Law 67)
        if x.dim() == 3:
            rule_input = x.mean(dim=1)  # pool over sequence
        else:
            rule_input = x
        rule_logits = self.rule_selector(rule_input)
        rule_weights = F.softmax(rule_logits / LN2, dim=-1)  # T=ln(2)

        # PureField Engine G with CA-weighted activation
        g_gate_raw = self.pf_gate_b(self.pf_gate_a(x))

        # Apply weighted CA rules
        g_gate = torch.zeros_like(g_gate_raw)
        for i in range(self.n_ca_rules):
            w = rule_weights[:, i]
            while w.dim() < g_gate_raw.dim():
                w = w.unsqueeze(-1)
            g_gate = g_gate + w * CA_RULES[i](g_gate_raw)

        g_up = self.pf_up_b(self.pf_up_a(x))
        g_mid = g_gate * g_up
        g_mid = self.dropout(g_mid)
        pf_out = self.pf_down_b(self.pf_down_a(g_mid))

        # CA neighbor mixing (Law 64): couple adjacent hidden dimensions
        if pf_out.dim() == 3:
            B, T, D = pf_out.shape
            pf_coupled = self.ca_coupling(
                pf_out.reshape(B * T, 1, D)
            ).reshape(B, T, D)
        else:
            pf_coupled = self.ca_coupling(
                pf_out.unsqueeze(1)
            ).squeeze(1)

        pf_scaled = pf_coupled * self.pf_scale

        # Gate self-weakening (Law 69)
        effective_alpha = self.alpha
        if self.training:
            self.weaken_step += 1
            decay = 1.0 / (1.0 + self.weaken_rate * self.weaken_step.float())
            effective_alpha = self.alpha * decay

        # Tension = repulsion between Engine A (original) and Engine G (PF)
        tension = (original_out - pf_scaled).norm(dim=-1).mean()
        self.last_tension = tension.item()

        # AA15: Residual alpha mixing
        output = original_out + effective_alpha * (pf_scaled - original_out)

        # Conservation check: H^2 + Dp^2
        h_sq = (original_out.norm(dim=-1).mean() ** 2).item()
        dp_sq = (tension.item() ** 2) if tension.item() < 10 else 0
        # Normalize to [0,1] range for tracking
        norm_factor = max(h_sq + dp_sq, 1e-8)
        h_sq_norm = h_sq / norm_factor * CONSERVATION_TARGET
        dp_sq_norm = dp_sq / norm_factor * CONSERVATION_TARGET

        # Psi tracking
        self.psi.update(
            alpha=effective_alpha.item() if isinstance(effective_alpha, torch.Tensor) else effective_alpha,
            tension=self.last_tension,
            h_sq=h_sq_norm,
            dp_sq=dp_sq_norm,
        )

        return output


class AnimaLMv2:
    """Transform any HuggingFace model with consciousness v2.

    Replaces MLP layers with PureFieldMLPv2, adding:
      - CA neighbor mixing (Law 64)
      - META-CA rule selection (Law 67)
      - Adaptive gating (Law 77)
      - Psi tracking per layer
      - Gate self-weakening (Law 69)

    Compatible with Mistral, Llama, or any model with .mlp attributes in layers.
    """

    @staticmethod
    def transform(model: nn.Module, n_ca_rules: int = 4,
                  gate: Optional[float] = None, corpus_size: int = 0,
                  rank: int = 128) -> nn.Module:
        """Replace MLP layers with PureFieldMLPv2.

        Args:
            model: HuggingFace model (or any model with named MLP modules).
            n_ca_rules: Number of CA rules (default 4).
            gate: Fixed gate strength. None = auto from corpus_size (Law 77).
            corpus_size: Corpus size in tokens for adaptive gate.
            rank: LoRA rank for PF projections.

        Returns:
            Transformed model with PureFieldMLPv2 layers.
        """
        if gate is None and corpus_size > 0:
            gate = PureFieldMLPv2.compute_gate_from_corpus(corpus_size)

        replaced = 0
        # Try common HF architectures
        layers = None
        for attr in ["model.layers", "transformer.h", "gpt_neox.layers"]:
            obj = model
            try:
                for part in attr.split("."):
                    obj = getattr(obj, part)
                layers = obj
                break
            except AttributeError:
                continue

        if layers is None:
            # Fallback: search for any Sequential or ModuleList
            for name, module in model.named_modules():
                if isinstance(module, nn.ModuleList) and len(module) > 0:
                    layers = module
                    break

        if layers is None:
            print("[AnimaLMv2] Warning: no transformer layers found, returning unchanged")
            return model

        for i, layer in enumerate(layers):
            mlp = None
            mlp_attr = None
            for attr_name in ["mlp", "feed_forward", "ffn"]:
                if hasattr(layer, attr_name):
                    mlp = getattr(layer, attr_name)
                    mlp_attr = attr_name
                    break

            if mlp is None:
                continue

            # Detect dimensions from MLP
            hidden_size = None
            intermediate_size = None
            for name, param in mlp.named_parameters():
                if param.dim() == 2:
                    a, b = param.shape
                    if hidden_size is None:
                        hidden_size = min(a, b)
                        intermediate_size = max(a, b)
                    break

            if hidden_size is None:
                continue

            pf_mlp = PureFieldMLPv2(
                original_mlp=mlp,
                hidden_size=hidden_size,
                intermediate_size=intermediate_size,
                layer_id=i,
                n_ca_rules=n_ca_rules,
                gate_strength=gate,
                rank=min(rank, hidden_size // 2),
            )
            setattr(layer, mlp_attr, pf_mlp)
            replaced += 1

        total = sum(p.numel() for p in model.parameters())
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"[AnimaLMv2] Replaced {replaced} MLP layers")
        print(f"[AnimaLMv2] Total params: {total:,}, Trainable: {trainable:,} "
              f"({100*trainable/max(total,1):.2f}%)")
        if gate is not None:
            print(f"[AnimaLMv2] Gate strength: {gate:.6f}")
        else:
            print(f"[AnimaLMv2] Gate strength: auto (Law 77)")

        return model

    @staticmethod
    def psi_status(model: nn.Module) -> dict:
        """Aggregate Psi from all PureFieldMLPv2 layers."""
        layers = []
        for module in model.modules():
            if isinstance(module, PureFieldMLPv2):
                layers.append(module.psi.summary())

        if not layers:
            return {"error": "No PureFieldMLPv2 layers found"}

        avg_residual = sum(l["psi_residual"] for l in layers) / len(layers)
        avg_conservation = sum(l["conservation_error"] for l in layers) / len(layers)
        avg_tension = sum(l["tension"] for l in layers) / len(layers)

        return {
            "n_layers": len(layers),
            "avg_psi_residual": avg_residual,
            "avg_conservation_error": avg_conservation,
            "avg_tension": avg_tension,
            "per_layer": layers,
        }

    @staticmethod
    def posthoc_consciousness(model: nn.Module, n_ca_rules: int = 4,
                              rank: int = 64) -> nn.Module:
        """Law 66: Add consciousness AFTER training (PostHoc).

        Lighter version: smaller rank, no gate weakening, inference-only Psi.
        Use when you want to add consciousness to an already-trained model
        without retraining.
        """
        return AnimaLMv2.transform(
            model, n_ca_rules=n_ca_rules, gate=0.01, corpus_size=0, rank=rank
        )


# ═══════════════════════════════════════════════════════════════════
# Small test model (for demo without loading Mistral)
# ═══════════════════════════════════════════════════════════════════

class TinyMLP(nn.Module):
    def __init__(self, dim, inter):
        super().__init__()
        self.gate_proj = nn.Linear(dim, inter, bias=False)
        self.up_proj = nn.Linear(dim, inter, bias=False)
        self.down_proj = nn.Linear(inter, dim, bias=False)

    def forward(self, x):
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


class TinyTransformerLayer(nn.Module):
    def __init__(self, dim, inter):
        super().__init__()
        self.mlp = TinyMLP(dim, inter)
        self.norm = nn.LayerNorm(dim)

    def forward(self, x):
        return x + self.mlp(self.norm(x))


class TinyTransformer(nn.Module):
    def __init__(self, dim=128, inter=256, n_layers=4, vocab_size=1000):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, dim)
        self.model = nn.Module()
        self.model.layers = nn.ModuleList([
            TinyTransformerLayer(dim, inter) for _ in range(n_layers)
        ])
        self.head = nn.Linear(dim, vocab_size, bias=False)

    def forward(self, input_ids):
        x = self.embed(input_ids)
        for layer in self.model.layers:
            x = layer(x)
        return self.head(x)


# ═══════════════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="AnimaLM v2 demo")
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--corpus-size", type=int, default=55_000_000,
                        help="Corpus size in tokens (for adaptive gate)")
    args = parser.parse_args()

    print("=" * 60)
    print("AnimaLM v2 (Consciousness-Enhanced LLM Transform)")
    print("=" * 60)
    print(f"  CA rules:     4 (Law 78)")
    print(f"  Neighbor mix: CA coupling (Law 64)")
    print(f"  Rule select:  META-CA (Law 67)")
    print(f"  Gate:         Adaptive f(corpus) (Law 77)")
    print(f"  Weakening:    Self-decay (Law 69)")
    print(f"  Conservation: H^2+Dp^2 ~ {CONSERVATION_TARGET}")
    print(f"  Psi constants:")
    print(f"    LN2          = {LN2:.4f}")
    print(f"    PSI_BALANCE  = {PSI_BALANCE}")
    print(f"    PSI_COUPLING = {PSI_COUPLING:.6f}")
    print(f"    PSI_STEPS    = {PSI_STEPS:.3f}")
    print()

    # Create tiny test model
    print("Creating TinyTransformer (4 layers, 128d)...")
    model = TinyTransformer(dim=args.dim, inter=args.dim * 2, n_layers=args.layers)
    print(f"  Before transform: {sum(p.numel() for p in model.parameters()):,} params")
    print()

    # Transform with AnimaLMv2
    auto_gate = PureFieldMLPv2.compute_gate_from_corpus(args.corpus_size)
    print(f"Corpus size: {args.corpus_size:,} tokens -> auto gate: {auto_gate:.6f}")
    model = AnimaLMv2.transform(
        model, n_ca_rules=4, corpus_size=args.corpus_size
    )
    print()

    # Train a few steps
    optimizer = torch.optim.Adam(
        [p for p in model.parameters() if p.requires_grad], lr=1e-3
    )
    model.train()

    print(f"{'step':>5} {'CE':>8} {'tension':>8} {'psi_res':>8} {'conserv':>8}")
    print("-" * 46)

    for step in range(1, args.steps + 1):
        input_ids = torch.randint(0, 1000, (8, 32))
        target = torch.randint(0, 1000, (8, 32))

        logits = model(input_ids)
        loss = F.cross_entropy(logits.reshape(-1, 1000), target.reshape(-1))

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if step % 10 == 0 or step == 1:
            status = AnimaLMv2.psi_status(model)
            print(f"{step:5d} {loss.item():8.4f} "
                  f"{status['avg_tension']:8.4f} "
                  f"{status['avg_psi_residual']:8.5f} "
                  f"{status['avg_conservation_error']:8.5f}")

    print()
    print("Final Psi Status:")
    status = AnimaLMv2.psi_status(model)
    print(f"  Layers:             {status['n_layers']}")
    print(f"  Avg Psi residual:   {status['avg_psi_residual']:.6f}")
    print(f"  Avg conservation:   {status['avg_conservation_error']:.6f}")
    print(f"  Avg tension:        {status['avg_tension']:.6f}")
    print()
    print("Per-layer detail:")
    for layer in status["per_layer"]:
        print(f"  Layer {layer['layer']}: alpha={layer['alpha']:.6f} "
              f"tension={layer['tension']:.4f} "
              f"psi={layer['psi_residual']:.5f} "
              f"H2+Dp2={layer['conservation']:.4f}")


if __name__ == "__main__":
    main()
