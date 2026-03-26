"""
Golden MoE Fine-tuning — Router + 2 experts only, memory-optimized

Key optimizations:
  - Only router + temperature + 2 experts trainable
  - 8-bit Adam
  - Gradient checkpointing
  - batch=1, grad_accum=16
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import time
import json
import os
import numpy as np
from torch.utils.data import DataLoader, Dataset, RandomSampler

GOLDEN_CENTER = 1 / math.e
GOLDEN_LOWER = 0.5 - math.log(4/3)
GOLDEN_UPPER = 0.5


class GoldenMoELayer(nn.Module):
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
        input_dtype = x.dtype

        inhibition = torch.sigmoid(self.router(x) / self.temperature)
        in_zone = (inhibition >= GOLDEN_LOWER) & (inhibition <= GOLDEN_UPPER)
        distance = (inhibition - GOLDEN_CENTER).abs()
        weights = torch.exp(-distance / 0.1) * in_zone.float()

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

        output = torch.zeros_like(x)
        for i in range(self.num_experts):
            w_i = weights[:, :, i].unsqueeze(-1)
            if w_i.max() > 1e-8:
                e_out = self.experts_down[i](F.silu(self.experts_gate[i](x)) * self.experts_up[i](x))
                output = output + w_i * e_out.to(input_dtype)

        self.last_stats = {
            "active": in_zone.float().sum(dim=-1).mean().item(),
            "mean_I": inhibition.mean().item(),
            "zone_ratio": in_zone.float().mean().item(),
            "inhibition": inhibition.detach(),
        }
        return output.to(input_dtype)


def replace_and_freeze(model, num_experts=8):
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

            moe = GoldenMoELayer(h, inter, num_experts=num_experts).to(device=dev, dtype=dt)

            # Init expert 0 from pretrained
            e_inter = moe.experts_gate[0].weight.shape[0]
            moe.experts_gate[0].weight.data.copy_(module.gate_proj.weight.data[:e_inter])
            moe.experts_up[0].weight.data.copy_(module.up_proj.weight.data[:e_inter])
            moe.experts_down[0].weight.data.copy_(module.down_proj.weight.data[:, :e_inter])

            setattr(parent, parts[-1], moe)
            count += 1

    # Freeze all
    for param in model.parameters():
        param.requires_grad = False

    # Unfreeze only router + temperature + experts 0,1
    trainable = 0
    for module in model.modules():
        if isinstance(module, GoldenMoELayer):
            module.router.weight.requires_grad = True
            trainable += module.router.weight.numel()
            module.temperature.requires_grad = True
            trainable += 1
            for i in range(min(2, module.num_experts)):
                for param in [module.experts_gate[i].weight, module.experts_up[i].weight, module.experts_down[i].weight]:
                    param.requires_grad = True
                    trainable += param.numel()

    total = sum(p.numel() for p in model.parameters())
    print(f"  Replaced {count} MLP → GoldenMoE ({num_experts} experts)")
    print(f"  Total: {total:,}, Trainable: {trainable:,} ({trainable/total*100:.2f}%)")
    return model


class TextDataset(Dataset):
    def __init__(self, tokens, block_size=512):
        self.tokens = tokens
        self.block_size = block_size
    def __len__(self):
        return max(0, len(self.tokens) - self.block_size - 1)
    def __getitem__(self, idx):
        chunk = self.tokens[idx:idx + self.block_size + 1]
        return chunk[:-1], chunk[1:]


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from datasets import load_dataset

    device = "cuda"
    print(f"GPU: {torch.cuda.get_device_name()}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    NUM_EXPERTS = 8
    BATCH_SIZE = 1
    GRAD_ACCUM = 16
    BLOCK_SIZE = 512
    LR = 3e-5
    BALANCE_LAMBDA = 0.01
    MAX_STEPS = 2000

    print("\n[1/4] Loading Mistral 7B...")
    t0 = time.time()
    model_name = "mistralai/Mistral-7B-v0.3"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.bfloat16, device_map="auto",
    )
    model.gradient_checkpointing_enable()
    print(f"  Loaded in {time.time()-t0:.1f}s")

    print("\n[2/4] Replacing MLP → Golden MoE...")
    model = replace_and_freeze(model, num_experts=NUM_EXPERTS)

    print("\n[3/4] Preparing data...")
    dataset = load_dataset("wikitext", "wikitext-103-raw-v1", split="train")
    text = "\n\n".join([t for t in dataset["text"] if len(t) > 100])
    tokens = tokenizer(text, return_tensors="pt", truncation=False).input_ids[0]
    tokens = tokens[:20_000_000]
    print(f"  Tokens: {len(tokens):,}")

    train_dataset = TextDataset(tokens, block_size=BLOCK_SIZE)
    sampler = RandomSampler(train_dataset, replacement=True, num_samples=(MAX_STEPS * GRAD_ACCUM + 100) * BATCH_SIZE)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=sampler, num_workers=2, pin_memory=True)

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    try:
        import bitsandbytes as bnb
        optimizer = bnb.optim.Adam8bit(trainable_params, lr=LR, weight_decay=0.01)
        print("  Using 8-bit Adam")
    except ImportError:
        optimizer = torch.optim.AdamW(trainable_params, lr=LR, weight_decay=0.01)
        print("  Using AdamW")

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=MAX_STEPS)
    print(f"  Target: {MAX_STEPS} steps, Effective batch: {BATCH_SIZE * GRAD_ACCUM}")

    print("\n[4/4] Training...")
    print(f"{'Step':>6} | {'Loss':>8} | {'CE':>8} | {'Bal':>8} | {'Active':>6} | {'Zone%':>6} | {'I':>6} | {'Time':>6}")
    print("-" * 78)

    os.makedirs("/workspace/checkpoints/golden_moe", exist_ok=True)
    model.train()
    global_step = 0
    running_loss = running_ce = running_bal = 0
    t_start = time.time()

    for batch_idx, (input_ids, labels) in enumerate(train_loader):
        input_ids = input_ids.to(device)
        labels = labels.to(device)

        outputs = model(input_ids=input_ids, labels=labels)
        ce_loss = outputs.loss

        # Balance loss: push inhibition toward golden center
        bal_losses = []
        for m in model.modules():
            if isinstance(m, GoldenMoELayer) and m.last_stats and m.last_stats.get("inhibition") is not None:
                bal_losses.append(((m.last_stats["inhibition"] - GOLDEN_CENTER) ** 2).mean())
        bal_loss = torch.stack(bal_losses).mean() if bal_losses else torch.tensor(0.0, device=device)

        loss = (ce_loss + BALANCE_LAMBDA * bal_loss) / GRAD_ACCUM
        loss.backward()

        running_loss += loss.item() * GRAD_ACCUM
        running_ce += ce_loss.item()
        running_bal += bal_loss.item()

        if (batch_idx + 1) % GRAD_ACCUM == 0:
            torch.nn.utils.clip_grad_norm_(trainable_params, 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            global_step += 1

            if global_step % 10 == 0:
                n = 10 * GRAD_ACCUM
                stats = [m.last_stats for m in model.modules() if isinstance(m, GoldenMoELayer) and m.last_stats]
                avg_a = np.mean([s["active"] for s in stats]) if stats else 0
                avg_z = np.mean([s["zone_ratio"] for s in stats]) if stats else 0
                avg_I = np.mean([s["mean_I"] for s in stats]) if stats else 0
                print(f"{global_step:6d} | {running_loss/n:8.4f} | {running_ce/n:8.4f} | {running_bal/n:8.4f} | {avg_a:6.1f} | {avg_z*100:5.1f}% | {avg_I:6.4f} | {(time.time()-t_start)/60:5.1f}m")
                running_loss = running_ce = running_bal = 0

            if global_step % 500 == 0:
                ckpt = f"/workspace/checkpoints/golden_moe/step_{global_step}.pt"
                states = {n: m.state_dict() for n, m in model.named_modules() if isinstance(m, GoldenMoELayer)}
                torch.save({"step": global_step, "moe_states": states}, ckpt)
                print(f"  Saved: {ckpt}")

            if global_step >= MAX_STEPS:
                break

    # Final save
    final = "/workspace/checkpoints/golden_moe/final.pt"
    states = {n: m.state_dict() for n, m in model.named_modules() if isinstance(m, GoldenMoELayer)}
    torch.save({"step": global_step, "moe_states": states, "base_model": model_name,
                "num_experts": NUM_EXPERTS, "golden_zone": [GOLDEN_LOWER, GOLDEN_UPPER]}, final)

    # Eval
    model.eval()
    wt2 = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
    test_text = "\n\n".join(wt2["text"][:200])
    ids = tokenizer(test_text, return_tensors="pt").input_ids.to(device)
    nlls = []
    with torch.no_grad():
        for i in range(0, ids.size(1) - 512, 256):
            out = model(ids[:, i:i+512], labels=ids[:, i:i+512].clone())
            nlls.append(out.loss.item())
            if len(nlls) >= 50: break
    ppl = math.exp(sum(nlls) / len(nlls))

    stats = [m.last_stats for m in model.modules() if isinstance(m, GoldenMoELayer) and m.last_stats]
    summary = {"model": model_name, "final_ppl": round(ppl, 2), "steps": global_step,
               "num_experts": NUM_EXPERTS,
               "avg_active": round(np.mean([s["active"] for s in stats]), 1) if stats else 0,
               "avg_zone_ratio": round(np.mean([s["zone_ratio"] for s in stats]), 3) if stats else 0,
               "time_min": round((time.time()-t_start)/60, 1)}
    with open("/workspace/checkpoints/golden_moe/summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Final PPL: {ppl:.2f}")
    print(json.dumps(summary, indent=2))
    print("\nDone!")


if __name__ == "__main__":
    main()
