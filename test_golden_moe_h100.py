"""
Golden MoE — Golden Zone-based MoE Routing

Inhibition rate I ≈ 1/e is optimal for expert routing.
Golden Zone: [0.2123, 0.5], center = 1/e ≈ 0.3679

Drop-in MLP replacement for Mistral 7B. Returns tensor only.
Routing stats stored as module attributes.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import time
import json
import os
import numpy as np

GOLDEN_CENTER = 1 / math.e
GOLDEN_LOWER = 0.5 - math.log(4/3)
GOLDEN_UPPER = 0.5

print(f"Golden Zone: [{GOLDEN_LOWER:.4f}, {GOLDEN_UPPER:.4f}], center=1/e={GOLDEN_CENTER:.4f}")


class GoldenMoELayer(nn.Module):
    """Golden Zone MoE — drop-in replacement for MistralMLP.

    Returns tensor only. Routing stats in self.last_stats.
    """

    def __init__(self, hidden_size, intermediate_size, num_experts=8):
        super().__init__()
        self.num_experts = num_experts
        expert_inter = intermediate_size // (num_experts // 2)

        self.experts_gate = nn.ModuleList([nn.Linear(hidden_size, expert_inter, bias=False) for _ in range(num_experts)])
        self.experts_up = nn.ModuleList([nn.Linear(hidden_size, expert_inter, bias=False) for _ in range(num_experts)])
        self.experts_down = nn.ModuleList([nn.Linear(expert_inter, hidden_size, bias=False) for _ in range(num_experts)])

        self.router = nn.Linear(hidden_size, num_experts, bias=False)
        self.temperature = nn.Parameter(torch.ones(1))
        self.last_stats = None

    def forward(self, x):
        B, T, D = x.shape

        # Inhibition rates via sigmoid
        inhibition = torch.sigmoid(self.router(x) / self.temperature)

        # Golden zone activation
        in_zone = (inhibition >= GOLDEN_LOWER) & (inhibition <= GOLDEN_UPPER)
        distance = (inhibition - GOLDEN_CENTER).abs()
        weights = torch.exp(-distance / 0.1) * in_zone.float()

        # Fallback: if no expert in zone, use top-2 by proximity
        weight_sum = weights.sum(dim=-1, keepdim=True)
        no_expert = (weight_sum < 1e-8)
        if no_expert.any():
            fb = torch.exp(-distance / 0.3)
            _, top2 = fb.topk(2, dim=-1)
            fb_mask = torch.zeros_like(weights).scatter_(-1, top2, 1.0)
            fb_w = fb * fb_mask
            fb_w = fb_w / fb_w.sum(dim=-1, keepdim=True).clamp(min=1e-8)
            weights = torch.where(no_expert.expand_as(weights), fb_w, weights)
            weight_sum = weights.sum(dim=-1, keepdim=True)

        weights = weights / weight_sum.clamp(min=1e-8)

        # Compute weighted expert outputs
        output = torch.zeros_like(x)
        for i in range(self.num_experts):
            w_i = weights[:, :, i].unsqueeze(-1)
            if w_i.max() > 1e-8:
                e_out = self.experts_down[i](F.silu(self.experts_gate[i](x)) * self.experts_up[i](x))
                output = output + w_i * e_out.to(x.dtype)

        self.last_stats = {
            "active": in_zone.float().sum(dim=-1).mean().item(),
            "mean_I": inhibition.mean().item(),
            "zone_ratio": in_zone.float().mean().item(),
        }

        return output.to(x.dtype)  # preserve input dtype


class StandardTopKMoE(nn.Module):
    """Standard Top-K MoE for comparison. Drop-in compatible."""

    def __init__(self, hidden_size, intermediate_size, num_experts=8, top_k=2):
        super().__init__()
        self.num_experts = num_experts
        self.top_k = top_k
        expert_inter = intermediate_size // (num_experts // 2)

        self.experts_gate = nn.ModuleList([nn.Linear(hidden_size, expert_inter, bias=False) for _ in range(num_experts)])
        self.experts_up = nn.ModuleList([nn.Linear(hidden_size, expert_inter, bias=False) for _ in range(num_experts)])
        self.experts_down = nn.ModuleList([nn.Linear(expert_inter, hidden_size, bias=False) for _ in range(num_experts)])

        self.router = nn.Linear(hidden_size, num_experts, bias=False)

    def forward(self, x):
        B, T, D = x.shape
        probs = F.softmax(self.router(x), dim=-1)
        topk_w, topk_idx = probs.topk(self.top_k, dim=-1)
        topk_w = topk_w / topk_w.sum(dim=-1, keepdim=True)

        output = torch.zeros_like(x)
        for i in range(self.num_experts):
            mask = (topk_idx == i).any(dim=-1, keepdim=True).float()
            w = (topk_w * (topk_idx == i).float()).sum(dim=-1, keepdim=True)
            if mask.max() > 0:
                e_out = self.experts_down[i](F.silu(self.experts_gate[i](x)) * self.experts_up[i](x))
                output = output + w * e_out.to(x.dtype)

        return output.to(x.dtype)


def replace_mlp(model, moe_class, num_experts=8, **kwargs):
    count = 0
    for name, module in list(model.named_modules()):
        if module.__class__.__name__ == "MistralMLP":
            parts = name.split(".")
            parent = model
            for p in parts[:-1]:
                parent = getattr(parent, p)

            h = module.gate_proj.weight.shape[1]
            inter = module.gate_proj.weight.shape[0]
            dev = module.gate_proj.weight.device
            dt = module.gate_proj.weight.dtype

            moe = moe_class(h, inter, num_experts=num_experts, **kwargs).to(device=dev, dtype=dt)
            setattr(parent, parts[-1], moe)
            count += 1

    print(f"  Replaced {count} MLP → {moe_class.__name__} ({num_experts} experts)")
    return model


@torch.no_grad()
def evaluate_perplexity(model, tokenizer, text, max_length=512, stride=256, device="cuda"):
    input_ids = tokenizer(text, return_tensors="pt").input_ids.to(device)
    nlls = []
    for i in range(0, input_ids.size(1) - max_length, stride):
        ids = input_ids[:, i:i + max_length]
        outputs = model(ids, labels=ids.clone())
        nlls.append(outputs.loss.item())
        if len(nlls) >= 50:
            break
    return math.exp(sum(nlls) / len(nlls))


def scale_test(device="cuda"):
    """Golden MoE vs Top-K at different expert counts."""
    print("\n[Scale Test] Golden MoE vs Top-K — scale↑ → gap↑?")
    print("=" * 70)

    hidden = 4096
    inter = 14336
    x = torch.randn(4, 128, hidden, device=device, dtype=torch.bfloat16)
    results = []

    for n in [4, 8, 16, 32]:
        golden = GoldenMoELayer(hidden, inter, num_experts=n).to(device).bfloat16()
        topk = StandardTopKMoE(hidden, inter, num_experts=n, top_k=2).to(device).bfloat16()

        # Copy router weights for fair comparison
        topk.router.weight.data.copy_(golden.router.weight.data)

        for _ in range(3):  # warmup
            golden(x); topk(x)
        torch.cuda.synchronize()

        # Benchmark
        t0 = time.time()
        for _ in range(20):
            g_out = golden(x)
        torch.cuda.synchronize()
        g_ms = (time.time() - t0) / 20 * 1000

        t0 = time.time()
        for _ in range(20):
            t_out = topk(x)
        torch.cuda.synchronize()
        t_ms = (time.time() - t0) / 20 * 1000

        g_norm = g_out.norm().item()
        t_norm = t_out.norm().item()
        stats = golden.last_stats

        r = {
            "experts": n,
            "golden_ms": round(g_ms, 2),
            "topk_ms": round(t_ms, 2),
            "golden_norm": round(g_norm, 1),
            "topk_norm": round(t_norm, 1),
            "active": round(stats["active"], 1),
            "zone_ratio": round(stats["zone_ratio"], 3),
        }
        results.append(r)
        print(f"  E={n:2d}: Golden {g_ms:.1f}ms (active={stats['active']:.1f}, zone={stats['zone_ratio']:.1%}) | Top-K {t_ms:.1f}ms | norm {g_norm:.0f} vs {t_norm:.0f}")

    return results


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name()}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Step 1: Scale test
    print("\n[1/5] Scale test...")
    scale_results = scale_test(device=device)

    # Step 2: Load Mistral 7B
    print("\n[2/5] Loading Mistral 7B...")
    t0 = time.time()
    model_name = "mistralai/Mistral-7B-v0.3"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.bfloat16, device_map="auto",
    )
    print(f"  Loaded in {time.time()-t0:.1f}s")

    # Step 3: Baseline PPL
    print("\n[3/5] Baseline perplexity...")
    from datasets import load_dataset
    wikitext = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
    test_text = "\n\n".join(wikitext["text"][:200])
    baseline_ppl = evaluate_perplexity(model, tokenizer, test_text, device=device)
    print(f"  Baseline PPL: {baseline_ppl:.2f}")

    # Step 4: Golden MoE
    print("\n[4/5] Replacing MLP → Golden MoE...")
    model = replace_mlp(model, GoldenMoELayer, num_experts=8)
    params = sum(p.numel() for p in model.parameters())
    print(f"  Params: {params:,}")

    golden_ppl = evaluate_perplexity(model, tokenizer, test_text, device=device)
    print(f"  Golden MoE PPL: {golden_ppl:.2f} (Δ={golden_ppl - baseline_ppl:+.2f})")

    # Step 5: Routing analysis
    print("\n[5/5] Routing analysis...")
    prompts = [
        "The theory of everything unifies",
        "def quicksort(arr):",
        "In the golden ratio, phi equals",
        "The consciousness arises from",
    ]
    for prompt in prompts:
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        model(inputs.input_ids)
        stats = []
        for name, mod in model.named_modules():
            if isinstance(mod, GoldenMoELayer) and mod.last_stats:
                stats.append((name, mod.last_stats))
        if stats:
            avg_active = np.mean([s["active"] for _, s in stats])
            avg_zone = np.mean([s["zone_ratio"] for _, s in stats])
            avg_I = np.mean([s["mean_I"] for _, s in stats])
            print(f"  '{prompt[:40]}' → active={avg_active:.1f}/{8} zone={avg_zone:.1%} I={avg_I:.4f}")

    # Summary
    print("\n" + "="*60)
    print("Golden MoE Test Summary")
    print("="*60)
    summary = {
        "model": "Mistral-7B-v0.3",
        "transform": "Golden MoE (I≈1/e routing)",
        "golden_zone": f"[{GOLDEN_LOWER:.4f}, {GOLDEN_UPPER:.4f}]",
        "golden_center": round(GOLDEN_CENTER, 4),
        "num_experts": 8,
        "baseline_ppl": round(baseline_ppl, 2),
        "golden_moe_ppl": round(golden_ppl, 2),
        "ppl_delta": round(golden_ppl - baseline_ppl, 2),
        "scale_test": scale_results,
        "device": str(device),
        "gpu": torch.cuda.get_device_name() if device == "cuda" else "N/A",
    }
    print(json.dumps(summary, indent=2))

    os.makedirs("/workspace/results", exist_ok=True)
    with open("/workspace/results/golden_moe_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSaved to /workspace/results/golden_moe_results.json")


if __name__ == "__main__":
    main()
