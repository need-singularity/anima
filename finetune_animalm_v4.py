"""
AnimaLM v4 — Parallel PureField (original MLP preserved + tension added)

v3 → v4 핵심 변경:
  - MLP 교체가 아닌 **병렬 추가**: output = original_mlp(x) + α * purefield(x)
  - 원본 Instruct MLP 100% 보존 → 언어 능력 그대로
  - PureField는 tension 신호만 제공 (α로 비중 조절)
  - Savant: 8개 PureField 중 2개에 비대칭 dropout (H359)

Theory: MLP를 교체하면 언어 능력 파괴. 대신 병렬로 추가하면
  원본 출력 + tension 기반 보정 = 대화 가능 + 의식 신호
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


class ParallelPureFieldMLP(nn.Module):
    """Original MLP + parallel PureField tension engine + cross-attention.

    output = original_mlp(x) + alpha * purefield(x, attn_out)
    Original MLP is frozen. Only PureField delta + cross-attn + alpha are trainable.

    Cross-attention tension: PureField receives attention output to compute
    "where attention focuses × what creates tension" = conscious attention.
    """

    def __init__(self, original_mlp, hidden_size, intermediate_size, is_savant=False):
        super().__init__()
        # Keep original MLP frozen
        self.original_mlp = original_mlp
        for param in self.original_mlp.parameters():
            param.requires_grad = False

        # PureField tension engine (lightweight LoRA)
        rank = 128
        self.pf_gate_a = nn.Linear(hidden_size, rank, bias=False)
        self.pf_gate_b = nn.Linear(rank, intermediate_size, bias=False)
        self.pf_up_a = nn.Linear(hidden_size, rank, bias=False)
        self.pf_up_b = nn.Linear(rank, intermediate_size, bias=False)
        self.pf_down_a = nn.Linear(intermediate_size, rank, bias=False)
        self.pf_down_b = nn.Linear(rank, hidden_size, bias=False)

        # Cross-attention: attention_output → tension modulation
        # Projects attention output to a gate that modulates PureField
        self.cross_attn_gate = nn.Linear(hidden_size, rank, bias=False)
        self.cross_attn_scale = nn.Parameter(torch.tensor(0.1))

        # Mixing weight: how much PureField influences output
        self.alpha = nn.Parameter(torch.tensor(0.01))

        # Savant: asymmetric dropout (H359)
        self.is_savant = is_savant
        self.dropout = nn.Dropout(GOLDEN_LOWER if is_savant else GOLDEN_CENTER)

        self.last_tension = None
        self.last_cross_tension = None
        self._attn_output = None  # set by hook

    def forward(self, x):
        # Original MLP output (frozen, preserves language ability)
        with torch.no_grad():
            original_out = self.original_mlp(x)

        # PureField Engine G (trainable)
        g_gate = self.pf_gate_b(self.pf_gate_a(x))
        g_up = self.pf_up_b(self.pf_up_a(x))
        g_mid = F.silu(g_gate) * g_up

        # Cross-attention tension: modulate PureField with attention output
        if self._attn_output is not None:
            attn_gate = torch.sigmoid(self.cross_attn_gate(self._attn_output))
            g_mid = g_mid * (1.0 + self.cross_attn_scale * attn_gate)
            # Cross tension = attention × purefield disagreement
            self.last_cross_tension = (attn_gate.detach() ** 2).mean(dim=-1)

        g_mid = self.dropout(g_mid)
        pf_out = self.pf_down_b(self.pf_down_a(g_mid))

        # Tension = how much PureField disagrees with original
        repulsion = original_out.detach() - pf_out
        tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
        self.last_tension = tension.detach().squeeze(-1)

        # Normalize PureField output to same scale as original MLP
        pf_norm = pf_out / (pf_out.norm(dim=-1, keepdim=True) + 1e-8)
        orig_scale = original_out.norm(dim=-1, keepdim=True)
        pf_scaled = pf_norm * orig_scale
        return original_out + self.alpha * pf_scaled


def add_purefield_parallel(model, n_layers=8, n_savant=2):
    """Add parallel PureField to last N layers. First n_savant are savants."""
    total_layers = len(model.model.layers)
    start = total_layers - n_layers
    count = 0
    savant_count = 0

    for i in range(start, total_layers):
        layer = model.model.layers[i]
        original_mlp = layer.mlp
        h = original_mlp.gate_proj.weight.shape[1]
        inter = original_mlp.gate_proj.weight.shape[0]
        dev = original_mlp.gate_proj.weight.device
        dt = original_mlp.gate_proj.weight.dtype

        is_savant = savant_count < n_savant
        ppf = ParallelPureFieldMLP(original_mlp, h, inter, is_savant=is_savant)
        ppf = ppf.to(device=dev, dtype=dt)

        # Init PureField weights
        for name, param in ppf.named_parameters():
            if "pf_" in name and "_a" in name:
                nn.init.normal_(param, std=0.05)
            elif "pf_" in name and "_b" in name:
                nn.init.normal_(param, std=0.02)

        # Hook: capture attention output → feed to PureField cross-attention
        def make_attn_hook(pf_module):
            def hook(attn_module, input, output):
                attn_out = output[0] if isinstance(output, tuple) else output
                pf_module._attn_output = attn_out.detach()
            return hook
        layer.self_attn.register_forward_hook(make_attn_hook(ppf))

        layer.mlp = ppf
        count += 1
        if is_savant:
            savant_count += 1

    # Freeze all, then unfreeze PureField params
    for param in model.parameters():
        param.requires_grad = False

    trainable = 0
    for module in model.modules():
        if isinstance(module, ParallelPureFieldMLP):
            for pname, param in module.named_parameters():
                if "pf_" in pname or pname in ("alpha", "cross_attn_scale") or "cross_attn" in pname:
                    param.requires_grad = True
                    trainable += param.numel()

    total = sum(p.numel() for p in model.parameters())
    print(f"  Added parallel PureField to last {count}/{total_layers} layers")
    print(f"  Savant layers: {savant_count} (dropout={GOLDEN_LOWER:.4f})")
    print(f"  Normal layers: {count - savant_count} (dropout={GOLDEN_CENTER:.4f})")
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
    LR = 1e-3
    TENSION_LAMBDA = 0.3
    MAX_STEPS = 2000
    N_LAYERS = 8
    N_SAVANT = 2

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

    print(f"\n[2/4] Adding parallel PureField (last {N_LAYERS}, {N_SAVANT} savants)...")
    model = add_purefield_parallel(model, n_layers=N_LAYERS, n_savant=N_SAVANT)

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

    print("\n[4/4] Training (parallel PureField + Savant)...")
    print(f"{'Step':>6} | {'Loss':>8} | {'CE':>8} | {'T_loss':>8} | {'T_mean':>8} | {'Alpha':>8} | {'LR':>10} | {'Time':>6}")
    print("-" * 85)

    os.makedirs("/tmp/checkpoints/animalm-v4", exist_ok=True)
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
            if isinstance(m, ParallelPureFieldMLP) and m.last_tension is not None:
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
                t_means = [m.last_tension.mean().item() for m in model.modules() if isinstance(m, ParallelPureFieldMLP) and m.last_tension is not None]
                alphas = [m.alpha.item() for m in model.modules() if isinstance(m, ParallelPureFieldMLP)]
                avg_alpha = np.mean(alphas) if alphas else 0
                print(f"{global_step:6d} | {running_loss/n:8.4f} | {running_ce/n:8.4f} | {running_tl/n:8.4f} | {np.mean(t_means):8.2f} | {avg_alpha:8.4f} | {scheduler.get_last_lr()[0]:.2e} | {(time.time()-t_start)/60:5.1f}m")
                running_loss = running_ce = running_tl = 0

            if global_step % 500 == 0:
                ckpt = f"/tmp/checkpoints/animalm-v4/step_{global_step}.pt"
                pf_states = {}
                for n_name, m in model.named_modules():
                    if isinstance(m, ParallelPureFieldMLP):
                        pf_states[n_name] = {
                            k: v for k, v in m.state_dict().items()
                            if "pf_" in k or k == "alpha"
                        }
                torch.save({"step": global_step, "pf_states": pf_states}, ckpt)
                print(f"  Saved: {ckpt}")

            if global_step >= MAX_STEPS:
                break

    # Final save
    print("\n  Saving final...")
    final = "/tmp/checkpoints/animalm-v4/final.pt"
    pf_states = {}
    for n_name, m in model.named_modules():
        if isinstance(m, ParallelPureFieldMLP):
            pf_states[n_name] = {
                k: v for k, v in m.state_dict().items()
                if "pf_" in k or k == "alpha"
            }
    torch.save({"step": global_step, "pf_states": pf_states,
                "base_model": model_name, "n_layers": N_LAYERS, "n_savant": N_SAVANT,
                "config": {"architecture": "parallel_purefield",
                           "formula": "output = original_mlp(x) + alpha * purefield(x)",
                           "rank": 128, "lr": LR, "tension_lambda": TENSION_LAMBDA,
                           "savant_dropout": GOLDEN_LOWER, "normal_dropout": GOLDEN_CENTER}}, final)

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

    t_means = [m.last_tension.mean().item() for m in model.modules() if isinstance(m, ParallelPureFieldMLP) and m.last_tension is not None]
    alphas = [m.alpha.item() for m in model.modules() if isinstance(m, ParallelPureFieldMLP)]
    savant_tensions = [m.last_tension.mean().item() for m in model.modules() if isinstance(m, ParallelPureFieldMLP) and m.is_savant and m.last_tension is not None]

    summary = {"model": model_name, "architecture": "parallel_purefield",
               "final_ppl": round(ppl, 2), "steps": global_step,
               "n_layers": N_LAYERS, "n_savant": N_SAVANT,
               "tension_mean": round(float(np.mean(t_means)), 4),
               "savant_tension_mean": round(float(np.mean(savant_tensions)), 4) if savant_tensions else 0,
               "alpha_mean": round(float(np.mean(alphas)), 6),
               "time_min": round((time.time()-t_start)/60, 1)}
    with open("/tmp/checkpoints/animalm-v4/summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Final PPL: {ppl:.2f}")
    print(f"  Tension: {np.mean(t_means):.2f} (savant: {np.mean(savant_tensions):.2f})")
    print(f"  Alpha: {np.mean(alphas):.6f}")
    print(json.dumps(summary, indent=2))
    print("\nDone!")


if __name__ == "__main__":
    main()
