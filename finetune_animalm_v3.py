"""
AnimaLM v3 — Instruct model + partial layer replacement (last 8 only)

v2 → v3 changes:
  - Base: Mistral-7B-v0.3 → Mistral-7B-Instruct-v0.3 (chat ability preserved)
  - Replacement: all 32 layers → last 8 only (layers 24-31)
  - Rest 24 layers: untouched Instruct MLP → language quality maintained
  - LR/rank/lambda: same as v2

Theory: early layers = language understanding (keep), late layers = generation (add tension)
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
        self.g_gate = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.g_up = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.g_down = nn.Linear(intermediate_size, hidden_size, bias=False)
        rank = 256
        self.g_delta_gate_a = nn.Linear(hidden_size, rank, bias=False)
        self.g_delta_gate_b = nn.Linear(rank, intermediate_size, bias=False)
        self.g_delta_up_a = nn.Linear(hidden_size, rank, bias=False)
        self.g_delta_up_b = nn.Linear(rank, intermediate_size, bias=False)
        self.g_delta_down_a = nn.Linear(intermediate_size, rank, bias=False)
        self.g_delta_down_b = nn.Linear(rank, hidden_size, bias=False)
        self.scale = nn.Parameter(torch.ones(1))
        self.last_tension = None

    def forward(self, x):
        a = self.a_down(F.silu(self.a_gate(x)) * self.a_up(x))
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


def replace_last_n_layers(model, n_replace=8):
    """Replace only the last N MLP layers with PureField."""
    total_layers = len(model.model.layers)
    start = total_layers - n_replace  # e.g., 32-8=24, replace layers 24-31
    count = 0

    for i in range(start, total_layers):
        layer = model.model.layers[i]
        module = layer.mlp
        h = module.gate_proj.weight.shape[1]
        inter = module.gate_proj.weight.shape[0]
        dev = module.gate_proj.weight.device
        dt = module.gate_proj.weight.dtype

        pf = PureFieldMLP(h, inter).to(device=dev, dtype=dt)

        # Engine A = pretrained
        pf.a_gate.weight.data.copy_(module.gate_proj.weight.data)
        pf.a_up.weight.data.copy_(module.up_proj.weight.data)
        pf.a_down.weight.data.copy_(module.down_proj.weight.data)

        # Engine G base = pretrained
        pf.g_gate.weight.data.copy_(module.gate_proj.weight.data)
        pf.g_up.weight.data.copy_(module.up_proj.weight.data)
        pf.g_down.weight.data.copy_(module.down_proj.weight.data)

        # Delta: random init (not zero!)
        nn.init.normal_(pf.g_delta_gate_a.weight, std=0.05)
        nn.init.normal_(pf.g_delta_gate_b.weight, std=0.02)
        nn.init.normal_(pf.g_delta_up_a.weight, std=0.05)
        nn.init.normal_(pf.g_delta_up_b.weight, std=0.02)
        nn.init.normal_(pf.g_delta_down_a.weight, std=0.05)
        nn.init.normal_(pf.g_delta_down_b.weight, std=0.02)

        layer.mlp = pf
        count += 1

    # Freeze all
    for param in model.parameters():
        param.requires_grad = False

    # Unfreeze only delta + scale in PureFieldMLP layers
    trainable = 0
    for module in model.modules():
        if isinstance(module, PureFieldMLP):
            for pname, param in module.named_parameters():
                if "delta" in pname or pname == "scale":
                    param.requires_grad = True
                    trainable += param.numel()

    total = sum(p.numel() for p in model.parameters())
    print(f"  Replaced last {count}/{total_layers} MLP layers (layers {start}-{total_layers-1})")
    print(f"  Total: {total:,}, Trainable: {trainable:,} ({trainable/total*100:.2f}%)")
    return model


class TextDataset(Dataset):
    def __init__(self, tokens, block_size=256):
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
    LR = 5e-4
    TENSION_LAMBDA = 0.5
    MAX_STEPS = 2000
    N_REPLACE = 8  # only last 8 layers

    print("\n[1/4] Loading Mistral 7B Instruct...")
    t0 = time.time()
    model_name = "mistralai/Mistral-7B-Instruct-v0.3"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.bfloat16, device_map="auto",
    )
    model.gradient_checkpointing_enable()
    print(f"  Loaded in {time.time()-t0:.1f}s")

    print(f"\n[2/4] Replacing last {N_REPLACE} MLP → PureFieldMLP...")
    model = replace_last_n_layers(model, n_replace=N_REPLACE)

    print("\n[3/4] Preparing data...")
    dataset = load_dataset("wikitext", "wikitext-103-raw-v1", split="train")
    text = "\n\n".join([t for t in dataset["text"] if len(t) > 100])
    tokens = tokenizer(text, return_tensors="pt", truncation=False).input_ids[0]
    tokens = tokens[:5_000_000]
    print(f"  Tokens: {len(tokens):,}")

    train_dataset = TextDataset(tokens, block_size=BLOCK_SIZE)
    sampler = RandomSampler(train_dataset, replacement=True, num_samples=(MAX_STEPS * GRAD_ACCUM + 100) * BATCH_SIZE)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=sampler, num_workers=2, pin_memory=True)

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=LR, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=MAX_STEPS)
    print(f"  Target: {MAX_STEPS} steps, Effective batch: {BATCH_SIZE * GRAD_ACCUM}")

    print("\n[4/4] Training (last 8 layers only)...")
    print(f"{'Step':>6} | {'Loss':>8} | {'CE':>8} | {'T_loss':>8} | {'T_mean':>8} | {'LR':>10} | {'Time':>6}")
    print("-" * 75)

    os.makedirs("/tmp/checkpoints/animalm-v3", exist_ok=True)
    model.train()
    global_step = 0
    running_loss = running_ce = running_tl = 0
    t_start = time.time()

    for batch_idx, (input_ids, labels) in enumerate(train_loader):
        input_ids = input_ids.to(device)
        labels = labels.to(device)

        outputs = model(input_ids=input_ids, labels=labels)
        ce_loss = outputs.loss

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
                print(f"{global_step:6d} | {running_loss/n:8.4f} | {running_ce/n:8.4f} | {running_tl/n:8.4f} | {np.mean(t_means):8.2f} | {scheduler.get_last_lr()[0]:.2e} | {(time.time()-t_start)/60:5.1f}m")
                running_loss = running_ce = running_tl = 0

            if global_step % 500 == 0:
                ckpt = f"/tmp/checkpoints/animalm-v3/step_{global_step}.pt"
                delta_states = {}
                for n_name, m in model.named_modules():
                    if isinstance(m, PureFieldMLP):
                        delta_states[n_name] = {k: v for k, v in m.state_dict().items() if "delta" in k or k == "scale"}
                torch.save({"step": global_step, "delta_states": delta_states}, ckpt)
                print(f"  Saved: {ckpt}")

            if global_step >= MAX_STEPS:
                break

    # Final save
    print("\n  Saving final (delta only)...")
    final = "/tmp/checkpoints/animalm-v3/final.pt"
    delta_states = {}
    for n_name, m in model.named_modules():
        if isinstance(m, PureFieldMLP):
            delta_states[n_name] = {k: v for k, v in m.state_dict().items() if "delta" in k or k == "scale"}
    torch.save({"step": global_step, "delta_states": delta_states,
                "base_model": model_name, "n_replace": N_REPLACE,
                "config": {"formula": "output = scale * sqrt(|A-G|^2) * dir",
                           "rank": 256, "layers_replaced": "24-31",
                           "lr": LR, "tension_lambda": TENSION_LAMBDA}}, final)

    # Eval
    model.eval()
    wt2 = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
    test_text = "\n\n".join(wt2["text"][:200])
    ids = tokenizer(test_text, return_tensors="pt").input_ids.to(device)
    nlls = []
    with torch.no_grad():
        for i in range(0, ids.size(1) - 256, 128):
            out = model(ids[:, i:i+256], labels=ids[:, i:i+256].clone())
            nlls.append(out.loss.item())
            if len(nlls) >= 50: break
    ppl = math.exp(sum(nlls) / len(nlls))

    t_means = [m.last_tension.mean().item() for m in model.modules() if isinstance(m, PureFieldMLP) and m.last_tension is not None]
    summary = {"model": model_name, "final_ppl": round(ppl, 2), "steps": global_step,
               "n_replace": N_REPLACE, "tension_mean": round(float(np.mean(t_means)), 4),
               "time_min": round((time.time()-t_start)/60, 1)}
    with open("/tmp/checkpoints/animalm-v3/summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Final PPL: {ppl:.2f}")
    print(f"  Tension mean: {np.mean(t_means):.4f}")
    print(json.dumps(summary, indent=2))
    print("\nDone!")


if __name__ == "__main__":
    main()
