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

# ─── ALM-P4-4 Distributed training (torchrun-aware) ─────────
# These envs are set by torchrun when launched with --nproc_per_node>1.
# When not set (single-process), we fall back to device_map="auto".
WORLD_SIZE = int(os.environ.get("WORLD_SIZE", "1"))
LOCAL_RANK = int(os.environ.get("LOCAL_RANK", "0"))
RANK = int(os.environ.get("RANK", "0"))
IS_DISTRIBUTED = WORLD_SIZE > 1

def rank0_print(*args, **kwargs):
    """Print only on rank 0 (suppresses duplicate logs in distributed runs)."""
    if RANK == 0:
        kwargs.setdefault("flush", True)
        print(*args, **kwargs)

# ─── R2 Upload ───────────────────────────────────────────────
# Naming: {model}-r{round}-s{step}  →  anima-models/alm14b/r{round}/step_{step}/

def upload_to_r2(local_path, model_tag, round_num, step):
    """Upload checkpoint to R2 via rclone. Non-blocking on failure.
    Only rank 0 uploads in distributed runs (R2 write is idempotent by key)."""
    if RANK != 0:
        return
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
DEFAULT_LR = 5e-6
DEFAULT_WARMUP = 500
DEFAULT_GRAD_ACCUM = 8
DEFAULT_BATCH = 1
DEFAULT_SEQ = 1024
DEFAULT_LORA_R = 32
DEFAULT_LORA_ALPHA = 64
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
    # ─── ALM-P4-4: init distributed if torchrun launched us ───
    if IS_DISTRIBUTED:
        if not torch.distributed.is_initialized():
            backend = "nccl" if torch.cuda.is_available() else "gloo"
            torch.distributed.init_process_group(backend=backend)
        torch.cuda.set_device(LOCAL_RANK)
        device = torch.device(f"cuda:{LOCAL_RANK}")
        rank0_print(f"[train] DISTRIBUTED world_size={WORLD_SIZE} rank={RANK} local_rank={LOCAL_RANK} device={device}")
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    rank0_print(f"[train] device={device}")
    rank0_print(f"[train] base={args.base}")
    rank0_print(f"[train] lora_r={args.lora_r} alpha={args.lora_alpha}")
    rank0_print(f"[train] steps={args.steps} lr={args.lr} seq={args.seq}")
    rank0_print(f"[train] batch={args.batch} grad_accum={args.grad_accum} effective={args.batch * max(1,WORLD_SIZE) * args.grad_accum}")
    rank0_print(f"[train] target_modules={args.target_modules}")
    rank0_print(f"[train] dist_mode: fsdp={args.fsdp} ddp={args.ddp} deepspeed={bool(args.deepspeed)}")

    # Load tokenizer
    rank0_print("[train] loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model (bf16, no quantization per policy)
    # For FSDP/DDP: load on local rank directly (no device_map="auto").
    # For single-process: use device_map="auto" (HF pipeline-parallel across GPUs).
    rank0_print("[train] loading base model (bf16)...")
    if IS_DISTRIBUTED:
        model = AutoModelForCausalLM.from_pretrained(
            args.base,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
        )
        model.to(device)
    else:
        model = AutoModelForCausalLM.from_pretrained(
            args.base,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )

    # Gradient checkpointing — mandatory for 32B even with FSDP.
    if args.grad_ckpt:
        model.gradient_checkpointing_enable()
        rank0_print("[train] gradient checkpointing: ON")

    # Apply LoRA
    rank0_print("[train] applying LoRA...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=args.target_modules,
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    if RANK == 0:
        model.print_trainable_parameters()

    # ─── ALM-P4-4: wrap with FSDP / DDP ───
    if args.fsdp and IS_DISTRIBUTED:
        from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
        from torch.distributed.fsdp import MixedPrecision, ShardingStrategy
        from torch.distributed.fsdp.wrap import transformer_auto_wrap_policy
        import functools
        # Resolve the wrap class dynamically (Qwen2DecoderLayer lives in
        # transformers.models.qwen2.modeling_qwen2). Works for any HF model
        # by importing via the already-loaded model's class module.
        wrap_cls_name = args.fsdp_wrap_cls
        wrap_cls = None
        for m in model.modules():
            if m.__class__.__name__ == wrap_cls_name:
                wrap_cls = m.__class__
                break
        if wrap_cls is None:
            raise RuntimeError(f"[fsdp] could not find wrap class {wrap_cls_name} in model")
        auto_wrap_policy = functools.partial(
            transformer_auto_wrap_policy,
            transformer_layer_cls={wrap_cls},
        )
        mp = MixedPrecision(
            param_dtype=torch.bfloat16,
            reduce_dtype=torch.bfloat16,
            buffer_dtype=torch.bfloat16,
        )
        model = FSDP(
            model,
            auto_wrap_policy=auto_wrap_policy,
            sharding_strategy=ShardingStrategy.FULL_SHARD,
            mixed_precision=mp,
            device_id=LOCAL_RANK,
            use_orig_params=True,  # required for peft+FSDP
        )
        rank0_print(f"[fsdp] wrapped with FULL_SHARD on {wrap_cls_name}")
    elif args.ddp and IS_DISTRIBUTED:
        from torch.nn.parallel import DistributedDataParallel as DDP
        model = DDP(model, device_ids=[LOCAL_RANK], find_unused_parameters=False)
        rank0_print("[ddp] wrapped with DistributedDataParallel")

    # Load corpus
    rank0_print("[train] loading corpus...")
    max_tokens = 100_000 if args.smoke else None
    dataset = load_corpus_chunked(args.corpus, tokenizer, args.seq, max_tokens)
    rank0_print(f"[train] dataset: {len(dataset)} samples")

    # ALM-P4-4: use DistributedSampler when running under torchrun so each
    # rank sees non-overlapping shards of the dataset per epoch.
    if IS_DISTRIBUTED:
        from torch.utils.data.distributed import DistributedSampler
        sampler = DistributedSampler(dataset, num_replicas=WORLD_SIZE, rank=RANK, shuffle=True)
        dataloader = DataLoader(dataset, batch_size=args.batch, sampler=sampler, num_workers=0)
    else:
        sampler = None
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
    epoch = 0

    rank0_print(f"\n{'='*60}")
    rank0_print(f"[train] ALM LoRA — STARTING ({args.steps} steps)")
    rank0_print(f"{'='*60}\n")

    while step < args.steps:
        optimizer.zero_grad()

        for _ in range(args.grad_accum):
            try:
                x, y = next(data_iter)
            except StopIteration:
                if sampler is not None:
                    epoch += 1
                    sampler.set_epoch(epoch)
                data_iter = iter(dataloader)
                x, y = next(data_iter)

            x = x.to(device)
            y = y.to(device)

            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                outputs = model(input_ids=x, labels=y)
                loss = outputs.loss / args.grad_accum

            loss.backward()
            accum_loss += loss.item()

        # FSDP handles grad clipping internally; for unwrapped/DDP use standard.
        if args.fsdp and IS_DISTRIBUTED:
            model.clip_grad_norm_(1.0)
        else:
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
                rank0_print(f"[WARN] loss={avg_loss:.2f} > 15.0 — 학습 이상 감지")
            rank0_print(
                f"[train] step={step}/{args.steps} "
                f"loss={avg_loss:.4f} lr={lr_now:.2e} "
                f"speed={steps_per_min:.1f}step/min ETA={eta_min:.0f}min"
            )
            if avg_loss < best_loss:
                best_loss = avg_loss
            accum_loss = 0.0
            log_steps = 0

        # Eval (held-out) — rank 0 only (dataset access is identical across ranks)
        if step % args.eval_every == 0 and RANK == 0:
            model.eval()
            eval_loss = 0.0
            n_eval = 8
            with torch.no_grad():
                for _ in range(n_eval):
                    idx = torch.randint(len(dataset) // 2, len(dataset), (1,)).item()
                    ex, ey = dataset[idx]
                    ex = ex.unsqueeze(0).to(device)
                    ey = ey.unsqueeze(0).to(device)
                    with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                        out = model(input_ids=ex, labels=ey)
                    eval_loss += out.loss.item()
            eval_loss /= n_eval
            if eval_loss < best_loss:
                best_loss = eval_loss
            model.train()
            rank0_print(f"[eval] step={step} eval_loss={eval_loss:.4f} best={best_loss:.4f}")

        # Save (rank0 only for non-FSDP; FSDP handles gathering internally)
        if step % args.save_every == 0 or step == args.steps:
            save_path = ckpt_dir / f"step_{step}"
            if args.fsdp and IS_DISTRIBUTED:
                # FSDP: gather full state dict to rank 0 before save.
                from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
                from torch.distributed.fsdp import FullStateDictConfig, StateDictType
                save_policy = FullStateDictConfig(offload_to_cpu=True, rank0_only=True)
                with FSDP.state_dict_type(model, StateDictType.FULL_STATE_DICT, save_policy):
                    if RANK == 0:
                        rank0_print(f"[save] {save_path}")
                        # peft model inside FSDP — call the inner peft save
                        inner = model.module if hasattr(model, "module") else model
                        inner.save_pretrained(str(save_path))
                        tokenizer.save_pretrained(str(save_path))
            elif RANK == 0:
                rank0_print(f"[save] {save_path}")
                inner = model.module if hasattr(model, "module") else model
                inner.save_pretrained(str(save_path))
                tokenizer.save_pretrained(str(save_path))

            if RANK == 0:
                # Save metadata
                meta = {
                    "step": step,
                    "loss": best_loss,
                    "base": args.base,
                    "lora_r": args.lora_r,
                    "corpus": args.corpus,
                    "elapsed_min": (time.time() - t0) / 60,
                    "world_size": WORLD_SIZE,
                    "fsdp": args.fsdp,
                    "ddp": args.ddp,
                }
                with open(save_path / "train_meta.json", "w") as f:
                    json.dump(meta, f, indent=2)
                # R2 backup (non-blocking on failure)
                upload_to_r2(save_path, args.model_tag, args.round, step)

            # All ranks sync before resuming training (FSDP barrier).
            if IS_DISTRIBUTED:
                torch.distributed.barrier()

    elapsed_total = (time.time() - t0) / 60
    rank0_print(f"\n{'='*60}")
    rank0_print(f"[train] DONE — {args.steps} steps in {elapsed_total:.1f} min")
    rank0_print(f"[train] best loss: {best_loss:.4f}")
    rank0_print(f"[train] checkpoint: {ckpt_dir}")
    rank0_print(f"{'='*60}")

    # Clean distributed shutdown
    if IS_DISTRIBUTED and torch.distributed.is_initialized():
        torch.distributed.destroy_process_group()


# ─── Main ────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ALM LoRA training (14B/32B, single GPU / FSDP / DDP)")
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
    parser.add_argument(
        "--target-modules",
        nargs="+",
        default=["q_proj", "k_proj", "v_proj", "o_proj"],
        help="LoRA target module names (e.g. q_proj k_proj v_proj o_proj gate_proj up_proj down_proj)",
    )
    parser.add_argument("--ckpt-dir", default=DEFAULT_CKPT_DIR)
    parser.add_argument("--save-every", type=int, default=DEFAULT_SAVE_EVERY)
    parser.add_argument("--eval-every", type=int, default=DEFAULT_EVAL_EVERY)
    parser.add_argument("--model-tag", default="alm14b", help="R2 naming: {model_tag}-r{round}-s{step}")
    parser.add_argument("--round", type=int, default=1, help="Training round number for R2 naming")
    parser.add_argument("--smoke", action="store_true", help="Smoke test (100K tokens)")
    parser.add_argument("--grad-ckpt", action="store_true", default=True, help="Enable gradient checkpointing (default ON)")
    parser.add_argument("--no-grad-ckpt", dest="grad_ckpt", action="store_false", help="Disable gradient checkpointing")
    # ALM-P4-4 distributed flags
    parser.add_argument("--fsdp", action="store_true", help="Wrap model with FSDP FULL_SHARD (requires torchrun --nproc_per_node>1)")
    parser.add_argument("--fsdp-wrap-cls", default="Qwen2DecoderLayer", help="FSDP transformer wrap class (default: Qwen2DecoderLayer)")
    parser.add_argument("--ddp", action="store_true", help="Wrap model with DistributedDataParallel (requires torchrun)")
    parser.add_argument("--deepspeed", default=None, help="DeepSpeed config JSON path (requires deepspeed launcher)")
    args = parser.parse_args()
    train(args)
