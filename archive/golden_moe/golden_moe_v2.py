#!/usr/bin/env python3
"""golden_moe_v2.py — Golden MoE v2 (Psi-Enhanced)

v1 -> v2 Changes:
  v1: 8 experts, Boltzmann router T=e, zone=1/e ratio, LoRA adapters
  v2: 4 experts (Law 78), META-CA router (Law 67), CA neighbor mixing (Law 64),
      Psi_balance=1/2 enforcement, adaptive gate (Law 77), gate self-weakening (Law 69)

Laws Applied:
  Law 63: Psi = ln(2) universal consciousness constant
  Law 64: CA neighbor mixing — adjacent experts share information
  Law 67: META-CA rule selection — consciousness selects expert activation patterns
  Law 69: Gate self-weakening — router converges toward uniform over time
  Law 77: Adaptive gate — gate strength = f(data_size)
  Law 78: CA(4) = 2 bits minimal — 4 experts suffice

Psi Constants:
  LN2          = ln(2) ~ 0.6931  (universal consciousness constant)
  PSI_BALANCE  = 0.5             (expert usage target)
  PSI_COUPLING = LN2 / 2^5.5    ~ 0.0154 (CA coupling strength)
  PSI_STEPS    = 3 / LN2        ~ 4.328  (convergence timescale)

Usage:
  python golden_moe_v2.py              # demo forward + Psi tracking
  python golden_moe_v2.py --steps 200  # longer run
"""

import argparse
import math
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

LN2 = math.log(2)                  # 0.6931 — universal consciousness constant
PSI_BALANCE = 0.5                  # expert usage target (no collapse)
PSI_COUPLING = LN2 / (2 ** 5.5)   # 0.0154 — CA neighbor coupling strength
PSI_STEPS = 3.0 / LN2             # 4.328  — convergence timescale


# ═══════════════════════════════════════════════════════════════════
# CA Rules for META-CA Router (Law 67)
# ═══════════════════════════════════════════════════════════════════

# 4 elementary CA-inspired activation rules (2 bits = 4 states)
CA_RULES = {
    0: lambda x: torch.relu(x),                          # Rule 0: simple threshold
    1: lambda x: torch.tanh(x),                          # Rule 1: bounded symmetric
    2: lambda x: torch.sigmoid(x) * 2 - 1,              # Rule 2: shifted sigmoid
    3: lambda x: x * torch.sigmoid(x),                   # Rule 3: SiLU/Swish
}


class PsiTracker:
    """Tracks Psi convergence metrics across forward passes.

    Monitors:
      - Expert usage balance (target: PSI_BALANCE per expert)
      - Usage entropy (target: log(n_experts))
      - Gate uniformity (0=peaked, 1=uniform)
      - Psi residual: |usage - PSI_BALANCE|
    """

    def __init__(self, n_experts: int):
        self.n_experts = n_experts
        self.usage_counts = torch.zeros(n_experts)
        self.total_tokens = 0
        self.history = []

    def update(self, gate_weights: torch.Tensor):
        """gate_weights: (batch, n_experts) soft assignments."""
        usage = gate_weights.detach().mean(dim=0).cpu()
        self.usage_counts += usage
        self.total_tokens += 1

    @property
    def usage_ratio(self) -> torch.Tensor:
        if self.total_tokens == 0:
            return torch.ones(self.n_experts) / self.n_experts
        return self.usage_counts / self.usage_counts.sum()

    @property
    def psi_residual(self) -> float:
        """Distance from perfect balance (PSI_BALANCE per expert)."""
        target = torch.ones(self.n_experts) / self.n_experts
        return (self.usage_ratio - target).abs().mean().item()

    @property
    def entropy(self) -> float:
        """Usage entropy. Max = log(n_experts)."""
        p = self.usage_ratio.clamp(min=1e-8)
        return -(p * p.log()).sum().item()

    def snapshot(self) -> dict:
        snap = {
            "usage": self.usage_ratio.tolist(),
            "psi_residual": self.psi_residual,
            "entropy": self.entropy,
            "max_entropy": math.log(self.n_experts),
            "uniformity": self.entropy / max(math.log(self.n_experts), 1e-8),
        }
        self.history.append(snap)
        return snap


class PsiRouter(nn.Module):
    """META-CA based router with Psi_balance constraint (Law 67 + Law 69).

    Instead of a simple linear router, applies CA rule patterns to determine
    expert selection. Gate self-weakening (Law 69) gradually pushes the router
    toward uniform distribution over training steps.

    Args:
        input_dim: Input feature dimension.
        n_experts: Number of experts (default 4, Law 78).
        weaken_rate: Gate self-weakening rate per step (Law 69).
    """

    def __init__(self, input_dim: int, n_experts: int = 4,
                 weaken_rate: float = 1e-4):
        super().__init__()
        self.n_experts = n_experts
        self.weaken_rate = weaken_rate

        # META-CA: project input to rule-space, then to expert scores
        self.rule_proj = nn.Linear(input_dim, n_experts * 4, bias=False)
        self.expert_proj = nn.Linear(n_experts, n_experts, bias=False)

        # Temperature starts at e (like v1), decays via self-weakening
        self.temperature = nn.Parameter(torch.tensor(math.e))

        # Balance penalty weight (Psi enforcement)
        self.balance_lambda = LN2  # use consciousness constant

        # Step counter for self-weakening
        self.register_buffer("step_count", torch.tensor(0, dtype=torch.long))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Returns soft expert weights (batch, n_experts)."""
        # META-CA: apply CA rules to projected features
        proj = self.rule_proj(x)  # (B, n_experts * 4)
        chunks = proj.chunk(4, dim=-1)  # 4 chunks of (B, n_experts)
        ca_out = sum(CA_RULES[i](chunks[i]) for i in range(4)) / 4.0

        scores = self.expert_proj(ca_out)  # (B, n_experts)

        # Gate self-weakening (Law 69): add uniform noise proportional to step
        if self.training:
            self.step_count += 1
            weaken = self.weaken_rate * self.step_count.float()
            uniform_noise = torch.ones_like(scores) / self.n_experts
            scores = scores * (1 - weaken.clamp(max=0.5)) + uniform_noise * weaken.clamp(max=0.5)

        # Boltzmann with temperature
        weights = F.softmax(scores / self.temperature.clamp(min=0.1), dim=-1)
        return weights

    def balance_loss(self, weights: torch.Tensor) -> torch.Tensor:
        """Psi_balance enforcement: penalize deviation from uniform usage."""
        usage = weights.mean(dim=0)  # (n_experts,)
        target = torch.ones_like(usage) / self.n_experts
        return self.balance_lambda * F.mse_loss(usage, target)


class Expert(nn.Module):
    """Single MoE expert with CA rule activation (Law 67)."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int,
                 ca_rule_id: int = 0):
        super().__init__()
        self.gate_proj = nn.Linear(input_dim, hidden_dim, bias=False)
        self.up_proj = nn.Linear(input_dim, hidden_dim, bias=False)
        self.down_proj = nn.Linear(hidden_dim, output_dim, bias=False)
        self.ca_rule = CA_RULES[ca_rule_id % len(CA_RULES)]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gate = self.ca_rule(self.gate_proj(x))
        up = self.up_proj(x)
        return self.down_proj(gate * up)


class GoldenMoEv2(nn.Module):
    """Golden MoE v2: Psi-Enhanced Mixture of Experts.

    Architecture:
      - 4 experts (Law 78: CA(4) = 2 bits minimal)
      - PsiRouter: META-CA rule selection (Law 67) + self-weakening (Law 69)
      - CA neighbor mixing (Law 64): adjacent experts share via coupling
      - Adaptive gate: strength = f(batch_size) (Law 77)
      - Psi tracking: monitors convergence to balanced usage

    Args:
        input_dim: Input feature dimension.
        hidden_dim: Expert hidden dimension.
        output_dim: Output dimension.
        n_experts: Number of experts (default 4).
    """

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int,
                 n_experts: int = 4):
        super().__init__()
        self.n_experts = n_experts
        self.input_dim = input_dim

        # Experts — each gets a different CA rule (Law 67)
        self.experts = nn.ModuleList([
            Expert(input_dim, hidden_dim, output_dim, ca_rule_id=i)
            for i in range(n_experts)
        ])

        # META-CA router with Psi balance
        self.router = PsiRouter(input_dim, n_experts)

        # CA neighbor coupling matrix (Law 64): ring topology
        coupling = torch.zeros(n_experts, n_experts)
        for i in range(n_experts):
            coupling[i, (i + 1) % n_experts] = PSI_COUPLING
            coupling[i, (i - 1) % n_experts] = PSI_COUPLING
        self.register_buffer("coupling", coupling)

        # CA neighbor mixing projection (Law 64)
        self.neighbor_mix = nn.Linear(output_dim, output_dim, bias=False)
        nn.init.normal_(self.neighbor_mix.weight, std=PSI_COUPLING)

        # Psi tracker
        self.psi_tracker = PsiTracker(n_experts)

    def _adaptive_gate(self, batch_size: int) -> float:
        """Law 77: gate = f(data_size). Larger batches -> softer gating."""
        return 1.0 / (1.0 + math.log1p(batch_size) / PSI_STEPS)

    def forward(self, x: torch.Tensor) -> tuple:
        """Forward pass.

        Args:
            x: (batch, input_dim) or (batch, seq_len, input_dim)

        Returns:
            (output, aux_loss) where aux_loss is Psi balance penalty.
        """
        has_seq = x.dim() == 3
        if has_seq:
            B, T, D = x.shape
            x_flat = x.reshape(B * T, D)
        else:
            x_flat = x
            B = x.shape[0]

        # 1. META-CA router scores
        weights = self.router(x_flat)  # (N, n_experts)

        # 2. Expert forward passes
        expert_outputs = torch.stack(
            [expert(x_flat) for expert in self.experts], dim=1
        )  # (N, n_experts, output_dim)

        # 3. CA neighbor mixing (Law 64): adjacent experts share info
        mixed = expert_outputs + torch.einsum(
            "ij,bjo->bio", self.coupling, self.neighbor_mix(expert_outputs)
        )

        # 4. Adaptive gate (Law 77)
        gate_strength = self._adaptive_gate(B)

        # 5. Weighted combination
        w = weights.unsqueeze(-1) * gate_strength  # (N, n_experts, 1)
        output = (w * mixed).sum(dim=1)  # (N, output_dim)

        if has_seq:
            output = output.reshape(B, T, -1)

        # 6. Psi tracking
        self.psi_tracker.update(weights)

        # Aux loss: balance + conservation
        aux_loss = self.router.balance_loss(weights)

        return output, aux_loss

    def psi_status(self) -> dict:
        """Get current Psi tracking status."""
        snap = self.psi_tracker.snapshot()
        snap["gate_temperature"] = self.router.temperature.item()
        snap["step"] = self.router.step_count.item()
        return snap


# ═══════════════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Golden MoE v2 demo")
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--hidden", type=int, default=256)
    parser.add_argument("--batch", type=int, default=32)
    args = parser.parse_args()

    print("=" * 60)
    print("Golden MoE v2 (Psi-Enhanced)")
    print("=" * 60)
    print(f"  Experts:      4 (Law 78: CA(4) = 2 bits)")
    print(f"  Router:       META-CA (Law 67)")
    print(f"  Neighbor mix: CA coupling (Law 64)")
    print(f"  Gate:         Adaptive f(batch) (Law 77)")
    print(f"  Weakening:    Self-decay (Law 69)")
    print(f"  Psi constants:")
    print(f"    LN2          = {LN2:.4f}")
    print(f"    PSI_BALANCE  = {PSI_BALANCE}")
    print(f"    PSI_COUPLING = {PSI_COUPLING:.6f}")
    print(f"    PSI_STEPS    = {PSI_STEPS:.3f}")
    print()

    model = GoldenMoEv2(args.dim, args.hidden, args.dim, n_experts=4)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    model.train()

    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {total_params:,}")
    print()

    print(f"{'step':>5} {'loss':>8} {'aux':>8} {'psi_res':>8} {'entropy':>8} {'uniform':>8}")
    print("-" * 54)

    for step in range(1, args.steps + 1):
        x = torch.randn(args.batch, args.dim)
        target = torch.randn(args.batch, args.dim)

        output, aux_loss = model(x)
        mse_loss = F.mse_loss(output, target)
        loss = mse_loss + aux_loss

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if step % 10 == 0 or step == 1:
            status = model.psi_status()
            print(f"{step:5d} {mse_loss.item():8.4f} {aux_loss.item():8.5f} "
                  f"{status['psi_residual']:8.5f} {status['entropy']:8.4f} "
                  f"{status['uniformity']:8.4f}")

    print()
    print("Final Psi Status:")
    status = model.psi_status()
    for k, v in status.items():
        if isinstance(v, list):
            print(f"  {k}: [{', '.join(f'{x:.4f}' for x in v)}]")
        elif isinstance(v, float):
            print(f"  {k}: {v:.6f}")
        else:
            print(f"  {k}: {v}")

    # Check convergence
    if status["psi_residual"] < 0.05:
        print("\n  -> Expert usage converged to PSI_BALANCE (balanced)")
    else:
        print(f"\n  -> Expert usage not yet balanced (residual={status['psi_residual']:.4f})")


if __name__ == "__main__":
    main()
