"""
AnimaLM Fine-tuning — Engine G only, memory-optimized for 80GB H100

Key optimizations:
  - Engine A frozen (Mistral pretrained)
  - Only Engine G scale params trainable (~1.9B with LoRA-like approach)
  - 8-bit Adam via bitsandbytes
  - Gradient checkpointing
  - bf16 mixed precision
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


class PureFieldMLP(nn.Module):
    def __init__(self, hidden_size, intermediate_size):
        super().__init__()
        self.a_gate = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.a_up = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.a_down = nn.Linear(intermediate_size, hidden_size, bias=False)

        # Engine G: use low-rank adapters instead of full copy (saves memory)
        self.g_gate = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.g_up = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.g_down = nn.Linear(intermediate_size, hidden_size, bias=False)

        # Low-rank delta for Engine G (rank 64 adapter)
        rank = 64
        self.g_delta_gate_a = nn.Linear(hidden_size, rank, bias=False)
        self.g_delta_gate_b = nn.Linear(rank, intermediate_size, bias=False)
        self.g_delta_up_a = nn.Linear(hidden_size, rank, bias=False)
        self.g_delta_up_b = nn.Linear(rank, intermediate_size, bias=False)
        self.g_delta_down_a = nn.Linear(intermediate_size, rank, bias=False)
        self.g_delta_down_b = nn.Linear(rank, hidden_size, bias=False)

        self.scale = nn.Parameter(torch.ones(1))
        self.last_tension = None

    def forward(self, x):
        # Engine A (frozen)
        a = self.a_down(F.silu(self.a_gate(x)) * self.a_up(x))

        # Engine G = base + low-rank delta
        g_gate_out = self.g_gate(x) + self.g_delta_gate_b(self.g_delta_gate_a(x))
        g_up_out = self.g_up(x) + self.g_delta_up_b(self.g_delta_up_a(x))
        g_mid = F.silu(g_gate_out) * g_up_out
        g = self.g_down(g_mid) + self.g_delta_down_b(self.g_delta_down_a(g_mid))

        repulsion = a - g
        tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
        self.last_tension = tension.detach().squeeze(-1)

        magnitude = torch.sqrt(tension + 1e-8)
        direction = repulsion / (repulsion.norm(dim=-1, keepdim=True) + 1e-8)
        return self.scale * magnitude * direction


def replace_and_freeze(model):
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

            # Engine A = pretrained (frozen)
            pf.a_gate.weight.data.copy_(module.gate_proj.weight.data)
            pf.a_up.weight.data.copy_(module.up_proj.weight.data)
            pf.a_down.weight.data.copy_(module.down_proj.weight.data)

            # Engine G base = same as A (frozen), delta = trainable
            pf.g_gate.weight.data.copy_(module.gate_proj.weight.data)
            pf.g_up.weight.data.copy_(module.up_proj.weight.data)
            pf.g_down.weight.data.copy_(module.down_proj.weight.data)

            # Init delta to near-zero
            nn.init.normal_(pf.g_delta_gate_a.weight, std=0.01)
            nn.init.zeros_(pf.g_delta_gate_b.weight)
            nn.init.normal_(pf.g_delta_up_a.weight, std=0.01)
            nn.init.zeros_(pf.g_delta_up_b.weight)
            nn.init.normal_(pf.g_delta_down_a.weight, std=0.01)
            nn.init.zeros_(pf.g_delta_down_b.weight)

            setattr(parent, parts[-1], pf)
            count += 1

    # Freeze all
    for param in model.parameters():
        param.requires_grad = False

    # Unfreeze only delta adapters + scale
    trainable = 0
    for name, module in model.named_modules():
        if isinstance(module, PureFieldMLP):
            for pname, param in module.named_parameters():
                if "delta" in pname or pname == "scale":
                    param.requires_grad = True
                    trainable += param.numel()

    total = sum(p.numel() for p in model.parameters())
    print(f"  Replaced {count} MLP layers")
    print(f"  Total params: {total:,}")
    print(f"  Trainable (delta only): {trainable:,} ({trainable/total*100:.2f}%)")
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

    BATCH_SIZE = 1
    GRAD_ACCUM = 16
    BLOCK_SIZE = 256
    LR = 5e-5
    TENSION_LAMBDA = 0.01
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
    # Enable gradient checkpointing
    model.gradient_checkpointing_enable()
    print(f"  Loaded in {time.time()-t0:.1f}s")

    print("\n[2/4] Replacing MLP → PureFieldMLP (LoRA-style delta)...")
    model = replace_and_freeze(model)

    print("\n[3/4] Preparing data...")
    dataset = load_dataset("wikitext", "wikitext-103-raw-v1", split="train")
    text = "\n\n".join([t for t in dataset["text"] if len(t) > 100])
    tokens = tokenizer(text, return_tensors="pt", truncation=False).input_ids[0]
    max_tokens = 5_000_000
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    print(f"  Tokens: {len(tokens):,}")

    train_dataset = TextDataset(tokens, block_size=BLOCK_SIZE)
    max_batches = MAX_STEPS * GRAD_ACCUM + 100
    sampler = RandomSampler(train_dataset, replacement=True, num_samples=max_batches * BATCH_SIZE)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=sampler, num_workers=2, pin_memory=True)

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    # Use 8-bit Adam if available
    try:
        import bitsandbytes as bnb

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

        optimizer = bnb.optim.Adam8bit(trainable_params, lr=LR, weight_decay=0.01)
        print("  Using 8-bit Adam")
    except ImportError:
        optimizer = torch.optim.AdamW(trainable_params, lr=LR, weight_decay=0.01)
        print("  Using standard AdamW")

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=MAX_STEPS)
    print(f"  Target steps: {MAX_STEPS}, Effective batch: {BATCH_SIZE * GRAD_ACCUM}")

    print("\n[4/4] Training...")
    print(f"{'Step':>6} | {'Loss':>8} | {'CE':>8} | {'T_loss':>8} | {'T_mean':>8} | {'LR':>10} | {'Time':>6}")
    print("-" * 75)

    os.makedirs("/tmp/checkpoints/animalm-v1", exist_ok=True)
    model.train()
    global_step = 0
    running_loss = running_ce = running_tl = 0
    t_start = time.time()

    for batch_idx, (input_ids, labels) in enumerate(train_loader):
        input_ids = input_ids.to(device)
        labels = labels.to(device)

        outputs = model(input_ids=input_ids, labels=labels)
        ce_loss = outputs.loss

        # Tension diversity loss
        tensions = []
        for m in model.modules():
            if isinstance(m, PureFieldMLP) and m.last_tension is not None:
                tensions.append(m.last_tension.mean())
        if len(tensions) >= 2:
            t_var = torch.stack(tensions).var()
            t_loss = -torch.log(t_var + 1e-8)
        else:
            t_loss = torch.tensor(0.0, device=device)

        loss = (ce_loss + TENSION_LAMBDA * t_loss) / GRAD_ACCUM
        loss.backward()

        running_loss += loss.item() * GRAD_ACCUM
        running_ce += ce_loss.item()
        running_tl += t_loss.item()

        if (batch_idx + 1) % GRAD_ACCUM == 0:
            torch.nn.utils.clip_grad_norm_(trainable_params, 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            global_step += 1

            if global_step % 10 == 0:
                n = 10 * GRAD_ACCUM
                t_means = [m.last_tension.mean().item() for m in model.modules() if isinstance(m, PureFieldMLP) and m.last_tension is not None]
                print(f"{global_step:6d} | {running_loss/n:8.4f} | {running_ce/n:8.4f} | {running_tl/n:8.4f} | {np.mean(t_means):8.6f} | {scheduler.get_last_lr()[0]:.2e} | {(time.time()-t_start)/60:5.1f}m")
                running_loss = running_ce = running_tl = 0

            if global_step % 500 == 0:
                ckpt = f"/tmp/checkpoints/animalm-v1/step_{global_step}.pt"
                # Save only trainable delta + scale (not full 22GB state)
                delta_states = {}
                for n, m in model.named_modules():
                    if isinstance(m, PureFieldMLP):
                        delta_states[n] = {k: v for k, v in m.state_dict().items() if "delta" in k or k == "scale"}
                torch.save({"step": global_step, "delta_states": delta_states}, ckpt)
                print(f"  Saved: {ckpt}")

            if global_step >= MAX_STEPS:
                break

    # Final save
    print("\n  Saving final (delta only)...")
    final = "/tmp/checkpoints/animalm-v1/final.pt"
    delta_states = {}
    for n, m in model.named_modules():
        if isinstance(m, PureFieldMLP):
            delta_states[n] = {k: v for k, v in m.state_dict().items() if "delta" in k or k == "scale"}
    torch.save({"step": global_step, "delta_states": delta_states, "base_model": model_name,
                "config": {"formula": "output = scale × sqrt(|A-G|^2) × dir", "rank": 64}}, final)

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

    t_means = [m.last_tension.mean().item() for m in model.modules() if isinstance(m, PureFieldMLP) and m.last_tension is not None]
    summary = {"model": model_name, "final_ppl": round(ppl, 2), "steps": global_step,
               "tension_mean": round(float(np.mean(t_means)), 4),
               "time_min": round((time.time()-t_start)/60, 1)}
    with open("/tmp/checkpoints/animalm-v1/summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Final PPL: {ppl:.2f}")
    print(json.dumps(summary, indent=2))
    print("\nDone!")


if __name__ == "__main__":
    main()
