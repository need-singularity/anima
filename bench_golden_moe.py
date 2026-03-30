#!/usr/bin/env python3
"""bench_golden_moe.py — Golden MoE general ML benchmark

Compares MLP baseline, Top-1, Top-2, and Golden MoE (v2) on synthetic
classification tasks (MNIST-like, CIFAR10-like).

Key metric: expert_usage_ratio near 1/e (0.3679) indicates golden zone.

Usage:
  python bench_golden_moe.py                          # MNIST default
  python bench_golden_moe.py --dataset cifar10        # CIFAR10
  python bench_golden_moe.py --experts 4,8            # multiple expert counts
  python bench_golden_moe.py --all                    # all datasets
"""

import argparse
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

INV_E = 1.0 / math.e  # 0.3679 — golden zone target


# ═══════════════════════════════════════════════════════════════════
# Result dataclass
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MoEBenchResult:
    method: str
    dataset: str
    n_experts: int
    accuracy: float
    expert_usage_ratio: float
    convergence_step: int
    balance_loss: float
    wall_time: float
    params: int
    extra: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        golden_dist = abs(self.expert_usage_ratio - INV_E)
        return (
            f"{self.method:<14s} | experts={self.n_experts:2d} | "
            f"acc={self.accuracy:.4f} | usage={self.expert_usage_ratio:.4f} | "
            f"|usage-1/e|={golden_dist:.4f} | conv_step={self.convergence_step:3d} | "
            f"bal_loss={self.balance_loss:.6f} | time={self.wall_time:.2f}s | "
            f"params={self.params:,}"
        )


# ═══════════════════════════════════════════════════════════════════
# Expert and TopKMoE
# ═══════════════════════════════════════════════════════════════════

class Expert(nn.Module):
    """2-layer MLP expert: Linear -> GELU -> Linear."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(F.gelu(self.fc1(x)))


class TopKMoE(nn.Module):
    """Standard Top-K Mixture of Experts.

    Args:
        input_dim: Input feature dimension.
        hidden_dim: Expert hidden dimension.
        output_dim: Output dimension.
        n_experts: Number of experts.
        k: Number of experts selected per token.
    """

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int,
                 n_experts: int = 4, k: int = 2):
        super().__init__()
        self.n_experts = n_experts
        self.k = k
        self.gate = nn.Linear(input_dim, n_experts)
        self.experts = nn.ModuleList([
            Expert(input_dim, hidden_dim, output_dim)
            for _ in range(n_experts)
        ])
        self.usage_counts = torch.zeros(n_experts)

    def forward(self, x: torch.Tensor) -> tuple:
        """Returns (output, aux_loss)."""
        B = x.shape[0]
        gate_scores = self.gate(x)  # (B, n_experts)
        topk_vals, topk_idx = torch.topk(gate_scores, self.k, dim=-1)  # (B, k)
        topk_weights = F.softmax(topk_vals, dim=-1)  # (B, k)

        # Compute all expert outputs
        expert_outputs = torch.stack(
            [expert(x) for expert in self.experts], dim=1
        )  # (B, n_experts, output_dim)

        # Gather selected experts
        idx_expanded = topk_idx.unsqueeze(-1).expand(-1, -1, expert_outputs.shape[-1])
        selected = torch.gather(expert_outputs, 1, idx_expanded)  # (B, k, output_dim)

        # Weighted combination
        output = (topk_weights.unsqueeze(-1) * selected).sum(dim=1)  # (B, output_dim)

        # Track usage
        with torch.no_grad():
            usage = torch.zeros(self.n_experts, device=x.device)
            for i in range(self.k):
                usage.scatter_add_(0, topk_idx[:, i], torch.ones(B, device=x.device))
            self.usage_counts = self.usage_counts.to(x.device) + usage

        # Balance loss: MSE(expert_usage, uniform)
        usage_frac = usage / (B * self.k)
        uniform = torch.ones_like(usage_frac) / self.n_experts
        aux_loss = F.mse_loss(usage_frac, uniform)

        return output, aux_loss


# ═══════════════════════════════════════════════════════════════════
# MoE Classifier
# ═══════════════════════════════════════════════════════════════════

class MoEClassifier(nn.Module):
    """Classifier wrapping a MoE layer.

    proj: Linear(input_dim, hidden_dim)
    moe_layer: hidden_dim -> n_classes
    head: Identity (moe output is already n_classes dim)
    """

    def __init__(self, input_dim: int, hidden_dim: int, n_classes: int,
                 moe_layer: nn.Module):
        super().__init__()
        self.proj = nn.Linear(input_dim, hidden_dim)
        self.moe_layer = moe_layer
        self.head = nn.Identity()

    def forward(self, x: torch.Tensor) -> tuple:
        h = F.gelu(self.proj(x))
        out, aux_loss = self.moe_layer(h)
        logits = self.head(out)
        return logits, aux_loss


# ═══════════════════════════════════════════════════════════════════
# Synthetic data
# ═══════════════════════════════════════════════════════════════════

def get_synthetic_data(dataset: str, n_samples: int = 1000):
    """Generate synthetic classification data.

    Args:
        dataset: "mnist" (784d, 10 classes) or "cifar10" (3072d, 10 classes).
        n_samples: Number of samples.

    Returns:
        (X, y, input_dim, n_classes)
    """
    if dataset == "mnist":
        input_dim = 784
        n_classes = 10
    elif dataset == "cifar10":
        input_dim = 3072
        n_classes = 10
    else:
        raise ValueError(f"Unknown dataset: {dataset}")

    X = torch.randn(n_samples, input_dim)
    y = torch.randint(0, n_classes, (n_samples,))
    return X, y, input_dim, n_classes


# ═══════════════════════════════════════════════════════════════════
# Training and evaluation
# ═══════════════════════════════════════════════════════════════════

def train_and_evaluate(model: nn.Module, X: torch.Tensor, y: torch.Tensor,
                       epochs: int = 20, batch_size: int = 64,
                       lr: float = 1e-3) -> dict:
    """Train and evaluate a MoEClassifier.

    Returns dict with: accuracy, expert_usage_ratio, convergence_step,
    balance_loss, wall_time, acc_history, usage_history.
    """
    # 80/20 split
    n = len(X)
    n_train = int(0.8 * n)
    perm = torch.randperm(n)
    X_train, y_train = X[perm[:n_train]], y[perm[:n_train]]
    X_test, y_test = X[perm[n_train:]], y[perm[n_train:]]

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    model.train()

    acc_history = []
    usage_history = []
    t0 = time.time()

    for epoch in range(epochs):
        # Train
        for i in range(0, n_train, batch_size):
            xb = X_train[i:i + batch_size]
            yb = y_train[i:i + batch_size]

            logits, aux_loss = model(xb)
            loss = F.cross_entropy(logits, yb) + 0.01 * aux_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # Evaluate
        model.eval()
        with torch.no_grad():
            logits, aux = model(X_test)
            preds = logits.argmax(dim=-1)
            acc = (preds == y_test).float().mean().item()
            acc_history.append(acc)

            # Get usage ratio (max single expert fraction)
            moe = model.moe_layer
            if hasattr(moe, 'usage_counts') and moe.usage_counts.sum() > 0:
                usage_ratio = (moe.usage_counts / moe.usage_counts.sum()).max().item()
            elif hasattr(moe, 'psi_tracker'):
                usage_ratio = moe.psi_tracker.usage_ratio.max().item()
            else:
                usage_ratio = 1.0
            usage_history.append(usage_ratio)

        model.train()

    wall_time = time.time() - t0

    # Final metrics
    final_acc = acc_history[-1] if acc_history else 0.0

    # Convergence step: first epoch reaching 90% of final accuracy
    threshold = 0.9 * final_acc
    convergence_step = epochs
    for i, a in enumerate(acc_history):
        if a >= threshold:
            convergence_step = i + 1
            break

    # Final balance loss
    model.eval()
    with torch.no_grad():
        _, final_aux = model(X_test)
        balance_loss = final_aux.item()

    # Final usage ratio
    final_usage = usage_history[-1] if usage_history else 1.0

    return {
        "accuracy": final_acc,
        "expert_usage_ratio": final_usage,
        "convergence_step": convergence_step,
        "balance_loss": balance_loss,
        "wall_time": wall_time,
        "acc_history": acc_history,
        "usage_history": usage_history,
    }


# ═══════════════════════════════════════════════════════════════════
# Comparison runner
# ═══════════════════════════════════════════════════════════════════

def run_comparison(dataset: str = "mnist", expert_counts: List[int] = None,
                   epochs: int = 20, n_samples: int = 1000) -> List[MoEBenchResult]:
    """Run comparison across MLP baseline, Top-1, Top-2, and Golden MoE.

    Args:
        dataset: "mnist" or "cifar10".
        expert_counts: List of expert counts to test.
        epochs: Training epochs.
        n_samples: Number of synthetic samples.

    Returns:
        List of MoEBenchResult.
    """
    from golden_moe_v2 import GoldenMoEv2

    if expert_counts is None:
        expert_counts = [4]

    X, y, input_dim, n_classes = get_synthetic_data(dataset, n_samples)
    hidden_dim = 128
    results = []

    for n_experts in expert_counts:
        configs = [
            ("MLP", None),
            ("Top-1", lambda: TopKMoE(hidden_dim, hidden_dim * 2, n_classes,
                                      n_experts=n_experts, k=1)),
            ("Top-2", lambda: TopKMoE(hidden_dim, hidden_dim * 2, n_classes,
                                      n_experts=n_experts, k=min(2, n_experts))),
            ("Golden", lambda: GoldenMoEv2(hidden_dim, hidden_dim * 2, n_classes,
                                           n_experts=n_experts)),
        ]

        for method, moe_factory in configs:
            if method == "MLP":
                # MLP baseline: use TopKMoE with 1 expert, k=1
                moe = TopKMoE(hidden_dim, hidden_dim * 2, n_classes,
                              n_experts=1, k=1)
            else:
                moe = moe_factory()

            model = MoEClassifier(input_dim, hidden_dim, n_classes, moe)
            params = sum(p.numel() for p in model.parameters())

            res = train_and_evaluate(model, X, y, epochs=epochs)

            results.append(MoEBenchResult(
                method=method,
                dataset=dataset,
                n_experts=n_experts if method != "MLP" else 1,
                accuracy=res["accuracy"],
                expert_usage_ratio=res["expert_usage_ratio"],
                convergence_step=res["convergence_step"],
                balance_loss=res["balance_loss"],
                wall_time=res["wall_time"],
                params=params,
                extra={
                    "acc_history": res["acc_history"],
                    "usage_history": res["usage_history"],
                },
            ))

    return results


# ═══════════════════════════════════════════════════════════════════
# Pretty printing
# ═══════════════════════════════════════════════════════════════════

def print_results(results: List[MoEBenchResult]):
    """Print results as ASCII table + 1/e check + accuracy bar graph."""
    if not results:
        print("No results.")
        return

    # Header
    print()
    print("=" * 100)
    print("Golden MoE Benchmark Results")
    print("=" * 100)
    print()

    # Table
    header = (f"{'Method':<14s} | {'Dataset':<8s} | {'#Exp':>4s} | "
              f"{'Acc':>7s} | {'Usage':>7s} | {'|u-1/e|':>7s} | "
              f"{'Conv':>4s} | {'BalLoss':>9s} | {'Time':>6s} | {'Params':>10s}")
    print(header)
    print("-" * len(header))

    for r in results:
        golden_dist = abs(r.expert_usage_ratio - INV_E)
        marker = " *" if golden_dist < 0.05 else ""
        print(
            f"{r.method:<14s} | {r.dataset:<8s} | {r.n_experts:4d} | "
            f"{r.accuracy:7.4f} | {r.expert_usage_ratio:7.4f} | {golden_dist:7.4f}{marker} | "
            f"{r.convergence_step:4d} | {r.balance_loss:9.6f} | "
            f"{r.wall_time:5.2f}s | {r.params:>10,}"
        )

    # 1/e check
    print()
    print(f"1/e = {INV_E:.4f} (golden zone target)")
    golden_results = [r for r in results if abs(r.expert_usage_ratio - INV_E) < 0.05]
    if golden_results:
        print(f"  {len(golden_results)} method(s) in golden zone (* marked above)")
    else:
        print("  No methods in golden zone (|usage - 1/e| < 0.05)")

    # Accuracy bar graph
    print()
    print("Accuracy comparison:")
    max_acc = max(r.accuracy for r in results) if results else 1.0
    bar_width = 40
    for r in results:
        bar_len = int(bar_width * r.accuracy / max(max_acc, 1e-8))
        bar = "#" * bar_len
        print(f"  {r.method:<14s} [{bar:<{bar_width}s}] {r.accuracy:.4f}")

    print()


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Golden MoE ML Benchmark")
    parser.add_argument("--dataset", type=str, default="mnist",
                        choices=["mnist", "cifar10"],
                        help="Dataset (default: mnist)")
    parser.add_argument("--experts", type=str, default="4",
                        help="Comma-separated expert counts (default: 4)")
    parser.add_argument("--epochs", type=int, default=20,
                        help="Training epochs (default: 20)")
    parser.add_argument("--samples", type=int, default=1000,
                        help="Number of samples (default: 1000)")
    parser.add_argument("--all", action="store_true",
                        help="Run all datasets")
    args = parser.parse_args()

    expert_counts = [int(x) for x in args.experts.split(",")]

    if args.all:
        datasets = ["mnist", "cifar10"]
    else:
        datasets = [args.dataset]

    all_results = []
    for ds in datasets:
        print(f"\nRunning benchmark on {ds}...")
        results = run_comparison(ds, expert_counts, args.epochs, args.samples)
        all_results.extend(results)

    print_results(all_results)


if __name__ == "__main__":
    main()
