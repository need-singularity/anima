"""
AnimaLM — Tension-based Consciousness Engine LLM

Mistral 7B → Engine A(logic) ↔ Engine G(pattern) Repulsion Field Transform
output = scale × √|A-G|² × dir

Drop-in MLP replacement: no decoder patching needed.
Tension stored as module attribute for monitoring.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import time
import json
import os
import numpy as np


class PureFieldMLP(nn.Module):
    """Drop-in replacement for MistralMLP.

    Returns tensor only (not tuple) so no decoder patching needed.
    Tension stored as self.last_tension for monitoring.
    """

    def __init__(self, hidden_size, intermediate_size):
        super().__init__()
        # Engine A: forward/logic
        self.a_gate = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.a_up = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.a_down = nn.Linear(intermediate_size, hidden_size, bias=False)

        # Engine G: backward/pattern
        self.g_gate = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.g_up = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.g_down = nn.Linear(intermediate_size, hidden_size, bias=False)

        # Learnable tension scale
        self.scale = nn.Parameter(torch.ones(1))

        # For monitoring
        self.last_tension = None

    def forward(self, x):
        a = self.a_down(F.silu(self.a_gate(x)) * self.a_up(x))
        g = self.g_down(F.silu(self.g_gate(x)) * self.g_up(x))

        repulsion = a - g
        tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
        self.last_tension = tension.detach().squeeze(-1)

        magnitude = torch.sqrt(tension + 1e-8)
        direction = repulsion / (repulsion.norm(dim=-1, keepdim=True) + 1e-8)
        output = self.scale * magnitude * direction

        return output  # tensor only, drop-in compatible


def replace_mlp_with_purefield(model):
    """Replace all MistralMLP with PureFieldMLP, copying weights to Engine A."""
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

            pf = PureFieldMLP(h, inter).to(device=dev, dtype=dt)

            # Copy pretrained weights → Engine A
            pf.a_gate.weight.data.copy_(module.gate_proj.weight.data)
            pf.a_up.weight.data.copy_(module.up_proj.weight.data)
            pf.a_down.weight.data.copy_(module.down_proj.weight.data)

            # Engine G = A + small noise (creates initial tension)
            pf.g_gate.weight.data.copy_(module.gate_proj.weight.data)
            pf.g_up.weight.data.copy_(module.up_proj.weight.data)
            pf.g_down.weight.data.copy_(module.down_proj.weight.data)
            with torch.no_grad():
                pf.g_gate.weight.add_(0.01 * torch.randn_like(pf.g_gate.weight))
                pf.g_up.weight.add_(0.01 * torch.randn_like(pf.g_up.weight))
                pf.g_down.weight.add_(0.01 * torch.randn_like(pf.g_down.weight))

            setattr(parent, parts[-1], pf)
            count += 1

    print(f"  Replaced {count} MLP → PureFieldMLP")
    return model


def collect_tensions(model):
    """Collect last_tension from all PureFieldMLP layers."""
    tensions = []
    for name, module in model.named_modules():
        if isinstance(module, PureFieldMLP) and module.last_tension is not None:
            tensions.append({
                "layer": name,
                "mean": module.last_tension.mean().item(),
                "std": module.last_tension.std().item(),
                "max": module.last_tension.max().item(),
            })
    return tensions


@torch.no_grad()
def evaluate_perplexity(model, tokenizer, text, max_length=512, stride=256, device="cuda"):
    encodings = tokenizer(text, return_tensors="pt")
    input_ids = encodings.input_ids.to(device)

    nlls = []
    for i in range(0, input_ids.size(1) - max_length, stride):
        ids = input_ids[:, i:i + max_length]
        target = ids.clone()
        outputs = model(ids, labels=target)
        nlls.append(outputs.loss.item())
        if len(nlls) >= 50:
            break

    return math.exp(sum(nlls) / len(nlls))


@torch.no_grad()
def generate_with_tension(model, tokenizer, prompt, max_new=100, device="cuda"):
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    input_ids = inputs.input_ids
    token_tensions = []

    for _ in range(max_new):
        outputs = model(input_ids)
        logits = outputs.logits[:, -1, :] / 0.8
        next_token = torch.multinomial(F.softmax(logits, dim=-1), 1)

        tensions = collect_tensions(model)
        avg_t = np.mean([t["mean"] for t in tensions]) if tensions else 0
        token_tensions.append(avg_t)

        input_ids = torch.cat([input_ids, next_token], dim=1)
        if input_ids.shape[1] > 512:
            input_ids = input_ids[:, -512:]
        if next_token.item() == tokenizer.eos_token_id:
            break

    gen_text = tokenizer.decode(input_ids[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
    return gen_text, token_tensions


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name()}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Step 1: Load Mistral 7B
    print("\n[1/5] Loading Mistral 7B...")
    t0 = time.time()
    model_name = "mistralai/Mistral-7B-v0.3"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.bfloat16, device_map="auto",
    )
    print(f"  Loaded in {time.time()-t0:.1f}s")
    orig_params = sum(p.numel() for p in model.parameters())
    print(f"  Params: {orig_params:,}")

    # Step 2: Baseline PPL
    print("\n[2/5] Baseline perplexity...")
    from datasets import load_dataset

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    wikitext = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
    test_text = "\n\n".join(wikitext["text"][:200])
    baseline_ppl = evaluate_perplexity(model, tokenizer, test_text, device=device)
    print(f"  Baseline PPL: {baseline_ppl:.2f}")

    # Step 3: Baseline generation
    print("\n[3/5] Baseline generation samples...")
    prompts = [
        "The nature of consciousness is",
        "def fibonacci(n):",
        "In quantum mechanics,",
    ]
    baseline_gens = {}
    for p in prompts:
        inputs = tokenizer(p, return_tensors="pt").to(device)
        out = model.generate(inputs.input_ids, max_new_tokens=50, do_sample=True, temperature=0.8)
        baseline_gens[p] = tokenizer.decode(out[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
        print(f"  '{p}' → {baseline_gens[p][:80]}")

    # Step 4: Replace MLP → PureField
    print("\n[4/5] Replacing MLP → PureFieldMLP (Engine A ↔ G)...")
    t0 = time.time()
    model = replace_mlp_with_purefield(model)
    new_params = sum(p.numel() for p in model.parameters())
    print(f"  Params: {new_params:,} (+{new_params - orig_params:,})")
    print(f"  Done in {time.time()-t0:.1f}s")

    # PureField PPL
    pf_ppl = evaluate_perplexity(model, tokenizer, test_text, device=device)
    print(f"  PureField PPL: {pf_ppl:.2f} (Δ={pf_ppl - baseline_ppl:+.2f})")

    # Step 5: Tension analysis + generation
    print("\n[5/5] Tension analysis & generation...")
    test_prompts = [
        "The fundamental nature of consciousness is",
        "def fibonacci(n):\n    if n <= 1:",
        "In quantum mechanics, the wave function",
        "I feel happy when",
        "2 + 2 = ",
    ]

    all_tensions = []
    for prompt in test_prompts:
        gen_text, tensions = generate_with_tension(model, tokenizer, prompt, max_new=50, device=device)
        t_arr = np.array(tensions) if tensions else np.array([0])
        all_tensions.extend(tensions)
        print(f"\n  Prompt: '{prompt}'")
        print(f"  Gen: {gen_text[:100]}")
        print(f"  Tension: mean={t_arr.mean():.6f} std={t_arr.std():.6f} max={t_arr.max():.6f}")

    # Layer-wise tension after last generation
    layer_tensions = collect_tensions(model)
    print("\n  Per-layer tension (last generation):")
    for lt in layer_tensions:
        print(f"    {lt['layer']}: mean={lt['mean']:.6f} std={lt['std']:.6f} max={lt['max']:.6f}")

    # Summary
    print("\n" + "="*60)
    print("AnimaLM Test Summary")
    print("="*60)
    t_global = np.array(all_tensions) if all_tensions else np.array([0])
    summary = {
        "model": "Mistral-7B-v0.3",
        "transform": "PureField (Engine A ↔ G)",
        "formula": "output = scale × sqrt(|A-G|^2) × dir",
        "baseline_ppl": round(baseline_ppl, 2),
        "purefield_ppl": round(pf_ppl, 2),
        "ppl_delta": round(pf_ppl - baseline_ppl, 2),
        "original_params": orig_params,
        "purefield_params": new_params,
        "param_overhead_pct": round((new_params - orig_params) / orig_params * 100, 2),
        "tension_global_mean": round(float(t_global.mean()), 6),
        "tension_global_std": round(float(t_global.std()), 6),
        "num_purefield_layers": len(layer_tensions),
        "device": str(device),
        "gpu": torch.cuda.get_device_name() if device == "cuda" else "N/A",
    }
    print(json.dumps(summary, indent=2))

    os.makedirs("/workspace/results", exist_ok=True)
    with open("/workspace/results/animalm_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSaved to /workspace/results/animalm_results.json")


if __name__ == "__main__":
    main()
