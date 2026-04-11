#!/usr/bin/env python3
"""train_alm_14b.py — ALM 14B LoRA fine-tune for Zeta-level Korean chat

GOAL: CLM + ALM → AGI. This is the ALM fast-path.
Base: Qwen/Qwen2.5-14B-Instruct + LoRA on attention layers.

Usage (H100 pod):
  python3 train_alm_14b.py --corpus /workspace/corpus.txt --steps 10000
  python3 train_alm_14b.py --corpus /workspace/corpus.txt --steps 1000 --smoke

Preflight (runpod.json R16+):
  0. runpodctl pod list (check existing)
  1. du -sh /workspace/
  2. nvidia-smi
  3. echo $HF_TOKEN
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType

# ─── R2 Upload ───────────────────────────────────────────────
# Naming: {model}-r{round}-s{step}  →  anima-models/alm14b/r{round}/step_{step}/

def upload_to_r2(local_path, model_tag, round_num, step):
    """Upload checkpoint to R2 via rclone. Non-blocking on failure."""
    r2_dest = f"r2:anima-models/{model_tag}/r{round_num}/step_{step}/"
    print(f"[r2] uploading {local_path} → {r2_dest}", flush=True)
    try:
        result = subprocess.run(
            ["rclone", "copy", str(local_path), r2_dest, "--s3-no-check-bucket"],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode == 0:
            print(f"[r2] ✓ uploaded {model_tag}-r{round_num}-s{step}", flush=True)
        else:
            print(f"[r2] ✗ upload failed: {result.stderr[:200]}", flush=True)
    except Exception as e:
        print(f"[r2] ✗ upload error: {e}", flush=True)


# ─── Config ──────────────────────────────────────────────────

DEFAULT_BASE = "Qwen/Qwen2.5-14B-Instruct"
DEFAULT_LR = 2e-5
DEFAULT_WARMUP = 200
DEFAULT_GRAD_ACCUM = 8
DEFAULT_BATCH = 1
DEFAULT_SEQ = 1024
DEFAULT_LORA_R = 64
DEFAULT_LORA_ALPHA = 128
DEFAULT_LORA_DROPOUT = 0.05
DEFAULT_STEPS = 10000
DEFAULT_CKPT_DIR = "/workspace/ckpt_alm_14b"
DEFAULT_SAVE_EVERY = 2000
DEFAULT_EVAL_EVERY = 500

# ─── Corpus Dataset ──────────────────────────────────────────

class TextDataset(Dataset):
    def __init__(self, tokens, block_size):
        self.tokens = tokens
        self.block_size = block_size
        self.n_samples = max(1, len(tokens) - block_size - 1)

    def __len__(self):
        return self.n_samples

    def __getitem__(self, idx):
        start = idx % self.n_samples
        chunk = self.tokens[start : start + self.block_size + 1]
        x = chunk[:-1]
        y = chunk[1:]
        return x, y


def load_corpus_chunked(path, tokenizer, block_size, max_tokens=None):
    """Load corpus with chunked tokenization (R14: avoid single-call OOM)."""
    print(f"[corpus] loading {path}")
    file_size = os.path.getsize(path)
    chunk_chars = 10_000_000  # ~10MB per chunk

    all_tokens = []
    total_chars = 0
    with open(path, "r", encoding="utf-8") as f:
        chunk_idx = 0
        while True:
            chunk = f.read(chunk_chars)
            if not chunk:
                break
            total_chars += len(chunk)
            ids = tokenizer(chunk, return_tensors="pt", truncation=False).input_ids[0]
            all_tokens.append(ids)
            chunk_idx += 1
            if chunk_idx % 5 == 0:
                n_tok = sum(len(t) for t in all_tokens)
                pct = total_chars * 100 // max(file_size, 1)
                print(f"  chunk {chunk_idx}: {n_tok:,} tokens ({pct}%)")
            if max_tokens and sum(len(t) for t in all_tokens) >= max_tokens:
                break

    tokens = torch.cat(all_tokens)
    if max_tokens:
        tokens = tokens[:max_tokens]
    print(f"[corpus] {len(tokens):,} tokens from {path} ({total_chars:,} chars)")
    return TextDataset(tokens, block_size)


# ─── Training ────────────────────────────────────────────────

def train(args):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[train] device={device}")
    print(f"[train] base={args.base}")
    print(f"[train] lora_r={args.lora_r} alpha={args.lora_alpha}")
    print(f"[train] steps={args.steps} lr={args.lr} seq={args.seq}")

    # Load tokenizer
    print("[train] loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model (bf16, no quantization per policy)
    print("[train] loading base model (bf16)...")
    model = AutoModelForCausalLM.from_pretrained(
        args.base,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )

    # Apply LoRA
    print("[train] applying LoRA...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load corpus
    print("[train] loading corpus...")
    max_tokens = 100_000 if args.smoke else None
    dataset = load_corpus_chunked(args.corpus, tokenizer, args.seq, max_tokens)
    print(f"[train] dataset: {len(dataset)} samples")

    dataloader = DataLoader(dataset, batch_size=args.batch, shuffle=True, num_workers=0)

    # Optimizer (R04: foreach=False)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.lr,
        betas=(0.9, 0.999),
        weight_decay=0.01,
        foreach=False,
    )

    # LR schedule: linear warmup + cosine decay
    from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR
    warmup = LinearLR(optimizer, start_factor=0.01, total_iters=args.warmup)
    cosine = CosineAnnealingLR(optimizer, T_max=args.steps - args.warmup, eta_min=args.lr * 0.01)
    scheduler = SequentialLR(optimizer, [warmup, cosine], milestones=[args.warmup])

    # Checkpoint dir
    ckpt_dir = Path(args.ckpt_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # Training loop
    model.train()
    data_iter = iter(dataloader)
    step = 0
    accum_loss = 0.0
    log_steps = 0
    best_loss = float("inf")
    t0 = time.time()

    print(f"\n{'='*60}")
    print(f"[train] ALM 14B LoRA — STARTING ({args.steps} steps)")
    print(f"{'='*60}\n")

    while step < args.steps:
        optimizer.zero_grad()

        for _ in range(args.grad_accum):
            try:
                x, y = next(data_iter)
            except StopIteration:
                data_iter = iter(dataloader)
                x, y = next(data_iter)

            x = x.to(device)
            y = y.to(device)

            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                outputs = model(input_ids=x, labels=y)
                loss = outputs.loss / args.grad_accum

            loss.backward()
            accum_loss += loss.item()

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        step += 1
        log_steps += 1

        # Log (avg_loss = per-step CE, NOT accumulated over log interval)
        if step % 10 == 0 or step == 1:
            avg_loss = accum_loss / max(log_steps, 1)
            elapsed = time.time() - t0
            steps_per_min = step * 60 / max(elapsed, 1)
            eta_min = (args.steps - step) / max(steps_per_min, 0.01)
            lr_now = scheduler.get_last_lr()[0]
            # Sanity: CE should never exceed ln(vocab_size) ≈ 12 for random
            if avg_loss > 15.0 and step > args.warmup:
                print(f"[WARN] loss={avg_loss:.2f} > 15.0 — 학습 이상 감지", flush=True)
            print(
                f"[train] step={step}/{args.steps} "
                f"loss={avg_loss:.4f} lr={lr_now:.2e} "
                f"speed={steps_per_min:.1f}step/min ETA={eta_min:.0f}min",
                flush=True,
            )
            if avg_loss < best_loss:
                best_loss = avg_loss
            accum_loss = 0.0
            log_steps = 0

        # Eval
        if step % args.eval_every == 0:
            print(f"[eval] step={step} best_loss={best_loss:.4f}")

        # Save
        if step % args.save_every == 0 or step == args.steps:
            save_path = ckpt_dir / f"step_{step}"
            print(f"[save] {save_path}")
            model.save_pretrained(str(save_path))
            tokenizer.save_pretrained(str(save_path))
            # Save metadata
            meta = {
                "step": step,
                "loss": best_loss,
                "base": args.base,
                "lora_r": args.lora_r,
                "corpus": args.corpus,
                "elapsed_min": (time.time() - t0) / 60,
            }
            with open(save_path / "train_meta.json", "w") as f:
                json.dump(meta, f, indent=2)
            # R2 backup (non-blocking on failure)
            upload_to_r2(save_path, args.model_tag, args.round, step)

    elapsed_total = (time.time() - t0) / 60
    print(f"\n{'='*60}")
    print(f"[train] DONE — {args.steps} steps in {elapsed_total:.1f} min")
    print(f"[train] best loss: {best_loss:.4f}")
    print(f"[train] checkpoint: {ckpt_dir}")
    print(f"{'='*60}")


# ─── Main ────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ALM 14B LoRA training")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--lr", type=float, default=DEFAULT_LR)
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    parser.add_argument("--seq", type=int, default=DEFAULT_SEQ)
    parser.add_argument("--grad-accum", type=int, default=DEFAULT_GRAD_ACCUM)
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--lora-r", type=int, default=DEFAULT_LORA_R)
    parser.add_argument("--lora-alpha", type=int, default=DEFAULT_LORA_ALPHA)
    parser.add_argument("--lora-dropout", type=float, default=DEFAULT_LORA_DROPOUT)
    parser.add_argument("--ckpt-dir", default=DEFAULT_CKPT_DIR)
    parser.add_argument("--save-every", type=int, default=DEFAULT_SAVE_EVERY)
    parser.add_argument("--eval-every", type=int, default=DEFAULT_EVAL_EVERY)
    parser.add_argument("--model-tag", default="alm14b", help="R2 naming: {model_tag}-r{round}-s{step}")
    parser.add_argument("--round", type=int, default=1, help="Training round number for R2 naming")
    parser.add_argument("--smoke", action="store_true", help="Smoke test (100K tokens)")
    args = parser.parse_args()
    train(args)
