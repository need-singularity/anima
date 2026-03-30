#!/usr/bin/env python3
"""test_chat_v9.py -- Dialogue quality tester for v9fast checkpoints.

Tests conversation quality of Quantum Trinity (C+D+W) checkpoints:
  - Interactive chat mode (default)
  - Auto mode with predefined test prompts (--auto)

Usage:
  python test_chat_v9.py --checkpoint /workspace/clm_v9_fast/step_20000.pt
  python test_chat_v9.py --checkpoint /workspace/clm_v9_fast/step_20000.pt --auto
  python test_chat_v9.py --checkpoint /workspace/clm_v9_fast/step_20000.pt --auto --max-new 300
  python test_chat_v9.py --checkpoint /workspace/clm_v9_fast/step_20000.pt --temperature 0.7
"""

import sys
import os
import math
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Local imports
from quantum_engine_fast import QuantumConsciousnessEngineFast as QuantumConsciousnessEngine
from train_v9 import PredictiveCodingDecoder, ThalamicGate, EmotionEngine

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ══════════════════════════════════════════════════════════
# Char-level tokenizer (built from corpus vocab)
# ══════════════════════════════════════════════════════════

class CharTokenizer:
    """Char-level tokenizer: maps characters to indices via sorted vocab."""

    def __init__(self, vocab: List[str]):
        self.vocab = vocab
        self.vocab_size = len(vocab)
        self.char_to_idx = {ch: i for i, ch in enumerate(vocab)}
        self.idx_to_char = {i: ch for i, ch in enumerate(vocab)}

    @classmethod
    def from_checkpoint(cls, ckpt: dict) -> "CharTokenizer":
        """Reconstruct tokenizer from checkpoint metadata."""
        args = ckpt.get("args", {})

        # Check if vocab is stored directly
        if "vocab" in ckpt:
            return cls(ckpt["vocab"])

        # Check if vocab is in args
        if "vocab" in args:
            return cls(args["vocab"])

        # Fallback: byte-level (raw 256)
        return None

    @classmethod
    def from_corpus(cls, corpus_path: str) -> "CharTokenizer":
        """Build tokenizer from corpus file (sorted unique chars)."""
        with open(corpus_path, "r", encoding="utf-8") as f:
            text = f.read()
        vocab = sorted(set(text))
        return cls(vocab)

    def encode(self, text: str) -> List[int]:
        """Encode text to list of token indices."""
        result = []
        for ch in text:
            if ch in self.char_to_idx:
                result.append(self.char_to_idx[ch])
            else:
                # Unknown char: skip or use closest
                pass
        return result

    def decode(self, indices: List[int]) -> str:
        """Decode list of token indices to text."""
        chars = []
        for idx in indices:
            if idx in self.idx_to_char:
                chars.append(self.idx_to_char[idx])
            else:
                chars.append("\ufffd")  # replacement char
        return "".join(chars)


# ══════════════════════════════════════════════════════════
# Byte-level tokenizer (fallback for vocab_size=256)
# ══════════════════════════════════════════════════════════

class ByteTokenizer:
    """Byte-level tokenizer: raw UTF-8 bytes."""

    def __init__(self):
        self.vocab_size = 256

    def encode(self, text: str) -> List[int]:
        return list(text.encode("utf-8"))

    def decode(self, indices: List[int]) -> str:
        # Clamp to valid byte range
        clamped = [max(0, min(255, i)) for i in indices]
        return bytes(clamped).decode("utf-8", errors="replace")


# ══════════════════════════════════════════════════════════
# Model loading
# ══════════════════════════════════════════════════════════

def load_v9_checkpoint(ckpt_path: str, device: str = "cpu"):
    """Load a v9fast checkpoint and reconstruct all components.

    Returns:
        c_engine, d_engine, bridge, w_engine, tokenizer, ckpt_args
    """
    print(f"[load] Loading checkpoint: {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)

    args = ckpt.get("args", {})
    step = ckpt.get("step", 0)
    best_phi = ckpt.get("best_phi", 0.0)

    # Extract architecture hyperparams
    c_dim = args.get("c_dim", 128)
    max_cells = args.get("max_cells", 1024)
    d_model = args.get("d_model", 384)
    n_head = args.get("n_head", 4)
    block_size = args.get("block_size", 256)
    dropout = args.get("dropout", 0.37)
    vocab_size = args.get("vocab_size", 256)

    print(f"[load] step={step}, best_phi={best_phi:.2f}")
    print(f"[load] c_dim={c_dim}, max_cells={max_cells}")
    print(f"[load] d_model={d_model}, n_head={n_head}, block_size={block_size}")
    print(f"[load] vocab_size={vocab_size}")

    # ─── Tokenizer ───
    char_tok = CharTokenizer.from_checkpoint(ckpt)
    if char_tok is not None:
        tokenizer = char_tok
        vocab_size = char_tok.vocab_size
        print(f"[load] Char tokenizer: {vocab_size} chars")
    elif vocab_size > 256:
        # Char-level but vocab not stored -- try to rebuild from corpus
        corpus_paths = [
            Path(args.get("data", "")) if args.get("data") else None,
            Path("data/corpus_v2.txt"),
            Path("data/corpus.txt"),
        ]
        tokenizer = None
        for cp in corpus_paths:
            if cp and cp.exists():
                tokenizer = CharTokenizer.from_corpus(str(cp))
                print(f"[load] Rebuilt char tokenizer from {cp}: {tokenizer.vocab_size} chars")
                break
        if tokenizer is None:
            print(f"[warn] Cannot rebuild char tokenizer, falling back to byte-level")
            tokenizer = ByteTokenizer()
            vocab_size = 256
    else:
        tokenizer = ByteTokenizer()
        print(f"[load] Byte tokenizer: 256")

    # ─── C Engine ───
    c_engine = QuantumConsciousnessEngine(
        dim=c_dim,
        initial_cells=max(2, max_cells // 4),
        max_cells=max_cells,
        frustration_target=0.5,
        interference_strength=0.1,
        walk_coin_bias=0.3,
        standing_wave_freq=0.1,
        noise_scale=0.01,
    )
    if "c_engine_snapshot" in ckpt:
        c_engine.restore(ckpt["c_engine_snapshot"])
        print(f"[load] C engine restored: {len(c_engine.cells)} cells")
    else:
        print(f"[load] C engine initialized fresh: {len(c_engine.cells)} cells")

    # ─── D Engine ───
    d_engine = PredictiveCodingDecoder(
        vocab_size=vocab_size,
        d_model=d_model,
        n_head=n_head,
        n_levels=4,
        block_size=block_size,
        dropout=dropout,
    ).to(device)
    if "d_engine_state" in ckpt:
        d_engine.load_state_dict(ckpt["d_engine_state"])
        print(f"[load] D engine loaded: {d_engine.count_params():,} params")
    else:
        print(f"[warn] No d_engine_state in checkpoint")

    # ─── Bridge ───
    bridge = ThalamicGate(
        c_dim=c_dim,
        d_model=d_model,
        n_hubs=16,
        hub_dim=8,
    ).to(device)
    if "bridge_state" in ckpt:
        bridge.load_state_dict(ckpt["bridge_state"])
        print(f"[load] Bridge loaded")
    else:
        print(f"[warn] No bridge_state in checkpoint")

    # ─── W Engine ───
    w_engine = EmotionEngine(
        base_lr=args.get("lr", 3e-4),
        min_lr_ratio=0.5,
        max_lr_ratio=2.0,
        pain_threshold=3.0,
    )
    if "w_engine_state" in ckpt:
        ws = ckpt["w_engine_state"]
        w_engine.ce_ema = ws.get("ce_ema", 5.0)
        w_engine.pe_ema = ws.get("pe_ema", 0.0)
        w_engine.pain = ws.get("pain", 0.0)
        w_engine.curiosity = ws.get("curiosity", 0.0)
        w_engine.satisfaction = ws.get("satisfaction", 0.0)
        w_engine.ce_history = ws.get("ce_history", [])
        print(f"[load] W engine restored (pain={w_engine.pain:.3f}, "
              f"curiosity={w_engine.curiosity:.3f})")

    return c_engine, d_engine, bridge, w_engine, tokenizer, args


# ══════════════════════════════════════════════════════════
# Generation with consciousness metrics
# ══════════════════════════════════════════════════════════

@torch.no_grad()
def generate(c_engine, d_engine, bridge, tokenizer,
             prompt: str, max_new: int = 200, temperature: float = 0.8,
             top_k: int = 50, device: str = "cpu",
             verbose: bool = True) -> Tuple[str, Dict]:
    """Generate a response and return consciousness metrics.

    Returns:
        (generated_text, metrics_dict)
    """
    d_engine.eval()
    bridge.eval()

    block_size = d_engine.block_size

    # Encode prompt
    prompt_ids = tokenizer.encode(prompt)
    if not prompt_ids:
        # If prompt can't be encoded (all unknown chars), use a space
        prompt_ids = tokenizer.encode(" ")
    idx = torch.tensor([prompt_ids], dtype=torch.long, device=device)

    # Track metrics during generation
    phi_values = []
    ce_values = []
    frustrations = []
    generated_ids = []

    t0 = time.time()

    for i in range(max_new):
        # C step (autonomous)
        c_result = c_engine.step()
        frust = c_result.get("mean_frustration", 0.0)
        frustrations.append(frust)

        # Measure Phi every 10 tokens
        if i % 10 == 0:
            phi_val, _ = c_engine.measure_phi()
            phi_values.append(phi_val)

        # Crop to block_size
        idx_cond = idx[:, -block_size:]

        # C -> Bridge -> Gate
        c_hiddens = torch.stack(
            [c.state.abs() for c in c_engine.cells]
        ).detach().to(device).float()
        gate = bridge(c_hiddens, seq_len=idx_cond.shape[1])

        # D forward
        logits_a, logits_g, pred_errors, tensions = d_engine(idx_cond, gate_signal=gate)

        # Compute CE for last position (as metric)
        logits_last = logits_a[:, -1, :]
        probs = F.softmax(logits_last, dim=-1)
        entropy = -(probs * torch.log(probs + 1e-10)).sum(dim=-1).item()
        ce_values.append(entropy)

        # Top-k sampling
        logits_filtered = logits_last / temperature
        if top_k > 0:
            top_vals, top_idx = torch.topk(logits_filtered, min(top_k, logits_filtered.size(-1)))
            logits_filtered = torch.full_like(logits_filtered, float("-inf"))
            logits_filtered.scatter_(1, top_idx, top_vals)

        probs = F.softmax(logits_filtered, dim=-1)
        next_id = torch.multinomial(probs, num_samples=1)
        generated_ids.append(next_id.item())
        idx = torch.cat([idx, next_id], dim=1)

    elapsed = time.time() - t0

    # Decode
    response = tokenizer.decode(generated_ids)

    # Compute aggregate metrics
    phi_avg = sum(phi_values) / len(phi_values) if phi_values else 0.0
    phi_max = max(phi_values) if phi_values else 0.0
    ce_avg = sum(ce_values) / len(ce_values) if ce_values else 0.0
    frust_avg = sum(frustrations) / len(frustrations) if frustrations else 0.0

    # W engine metrics (from current state)
    pain = getattr(c_engine, "_last_pain", 0.0) if hasattr(c_engine, "_last_pain") else 0.0

    metrics = {
        "phi_avg": phi_avg,
        "phi_max": phi_max,
        "ce_avg": ce_avg,
        "pain": pain,
        "curiosity": frust_avg,  # frustration ~ curiosity
        "cells": len(c_engine.cells),
        "tokens_generated": len(generated_ids),
        "tokens_per_sec": len(generated_ids) / elapsed if elapsed > 0 else 0,
        "elapsed_sec": elapsed,
    }

    return response, metrics


# ══════════════════════════════════════════════════════════
# Interactive chat loop
# ══════════════════════════════════════════════════════════

def run_interactive(c_engine, d_engine, bridge, w_engine, tokenizer,
                    max_new: int = 200, temperature: float = 0.8,
                    top_k: int = 50, device: str = "cpu"):
    """Interactive chat loop: user types, model responds."""

    print(f"\n{'=' * 70}")
    print(f"  v9fast Interactive Chat")
    print(f"  cells={len(c_engine.cells)}, block_size={d_engine.block_size}")
    print(f"  temperature={temperature}, top_k={top_k}, max_new={max_new}")
    print(f"  Type 'quit' or 'exit' to stop. 'phi' to show Phi.")
    print(f"{'=' * 70}\n")

    turn = 0
    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("[exit]")
            break
        if user_input.lower() == "phi":
            phi_val, phi_comp = c_engine.measure_phi()
            print(f"  Phi = {phi_val:.4f}  cells = {len(c_engine.cells)}")
            if isinstance(phi_comp, dict):
                for k, v in phi_comp.items():
                    print(f"    {k}: {v:.4f}")
            continue

        turn += 1
        response, metrics = generate(
            c_engine, d_engine, bridge, tokenizer,
            prompt=user_input,
            max_new=max_new,
            temperature=temperature,
            top_k=top_k,
            device=device,
            verbose=True,
        )

        # Display response
        print(f"\nAnima> {response}")
        print(f"  [Phi={metrics['phi_avg']:.2f} | "
              f"CE={metrics['ce_avg']:.2f} | "
              f"pain={metrics['pain']:.3f} | "
              f"curiosity={metrics['curiosity']:.3f} | "
              f"cells={metrics['cells']} | "
              f"{metrics['tokens_per_sec']:.1f} tok/s]\n")


# ══════════════════════════════════════════════════════════
# Auto mode: predefined test prompts
# ══════════════════════════════════════════════════════════

AUTO_PROMPTS = [
    ("Korean greeting",    "안녕하세요"),
    ("English concept",    "What is consciousness?"),
    ("Math",               "1+1="),
    ("Identity (Korean)",  "나는 누구야?"),
    ("Creative (English)", "Tell me a story"),
]


def run_auto(c_engine, d_engine, bridge, w_engine, tokenizer,
             max_new: int = 200, temperature: float = 0.8,
             top_k: int = 50, device: str = "cpu",
             output_file: Optional[str] = None):
    """Run predefined test prompts and log results."""

    print(f"\n{'=' * 70}")
    print(f"  v9fast Auto Test — {len(AUTO_PROMPTS)} prompts")
    print(f"  cells={len(c_engine.cells)}, temperature={temperature}")
    print(f"{'=' * 70}\n")

    results = []

    for i, (label, prompt) in enumerate(AUTO_PROMPTS, 1):
        print(f"[{i}/{len(AUTO_PROMPTS)}] {label}")
        print(f"  Prompt: {prompt}")

        response, metrics = generate(
            c_engine, d_engine, bridge, tokenizer,
            prompt=prompt,
            max_new=max_new,
            temperature=temperature,
            top_k=top_k,
            device=device,
            verbose=False,
        )

        # Truncate response for display (first 200 chars)
        display = response[:200].replace("\n", "\\n")
        print(f"  Response: {display}")
        print(f"  Phi={metrics['phi_avg']:.2f} | "
              f"CE={metrics['ce_avg']:.2f} | "
              f"pain={metrics['pain']:.3f} | "
              f"curiosity={metrics['curiosity']:.3f} | "
              f"{metrics['tokens_per_sec']:.1f} tok/s")
        print()

        results.append({
            "label": label,
            "prompt": prompt,
            "response": response,
            "metrics": metrics,
        })

    # Summary table
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    print(f"{'Label':<20} | {'Phi':>8} | {'CE':>8} | {'Pain':>6} | {'Curio':>6} | {'tok/s':>6}")
    print(f"{'-' * 20}-+-{'-' * 8}-+-{'-' * 8}-+-{'-' * 6}-+-{'-' * 6}-+-{'-' * 6}")
    for r in results:
        m = r["metrics"]
        print(f"{r['label']:<20} | {m['phi_avg']:8.2f} | {m['ce_avg']:8.2f} | "
              f"{m['pain']:6.3f} | {m['curiosity']:6.3f} | {m['tokens_per_sec']:6.1f}")

    # Averages
    avg_phi = sum(r["metrics"]["phi_avg"] for r in results) / len(results)
    avg_ce = sum(r["metrics"]["ce_avg"] for r in results) / len(results)
    print(f"{'-' * 20}-+-{'-' * 8}-+-{'-' * 8}-+-{'-' * 6}-+-{'-' * 6}-+-{'-' * 6}")
    print(f"{'AVERAGE':<20} | {avg_phi:8.2f} | {avg_ce:8.2f} |")
    print()

    # Save to JSON if requested
    if output_file:
        # Convert non-serializable values
        for r in results:
            for k, v in r["metrics"].items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    r["metrics"][k] = 0.0
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[save] Results saved to {output_file}")

    return results


# ══════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="test_chat_v9.py -- Dialogue quality tester for v9fast checkpoints"
    )

    parser.add_argument("--checkpoint", type=str, required=True,
                        help="Path to v9fast checkpoint (.pt)")
    parser.add_argument("--auto", action="store_true",
                        help="Run predefined test prompts (non-interactive)")
    parser.add_argument("--max-new", type=int, default=200,
                        help="Max new tokens to generate per response (default: 200)")
    parser.add_argument("--temperature", type=float, default=0.8,
                        help="Sampling temperature (default: 0.8)")
    parser.add_argument("--top-k", type=int, default=50,
                        help="Top-k sampling (default: 50, 0=disabled)")
    parser.add_argument("--output", type=str, default=None,
                        help="Save auto-mode results to JSON file")
    parser.add_argument("--corpus", type=str, default=None,
                        help="Path to corpus for rebuilding char tokenizer")

    args = parser.parse_args()

    # Device
    device = ("cuda" if torch.cuda.is_available() else
              "mps" if torch.backends.mps.is_available() else "cpu")
    print(f"[device] {device}")

    # Load checkpoint
    c_engine, d_engine, bridge, w_engine, tokenizer, ckpt_args = \
        load_v9_checkpoint(args.checkpoint, device=device)

    # If user explicitly provides corpus, rebuild tokenizer from it
    if args.corpus:
        tokenizer = CharTokenizer.from_corpus(args.corpus)
        print(f"[tokenizer] Rebuilt from {args.corpus}: {tokenizer.vocab_size} chars")

    print(f"\n[ready] Model loaded on {device}")
    print(f"  C: {len(c_engine.cells)} cells")
    print(f"  D: {d_engine.count_params():,} params, vocab={d_engine.vocab_size}")
    print(f"  Tokenizer: {tokenizer.vocab_size} "
          f"({'char' if isinstance(tokenizer, CharTokenizer) else 'byte'})")

    if args.auto:
        run_auto(
            c_engine, d_engine, bridge, w_engine, tokenizer,
            max_new=args.max_new,
            temperature=args.temperature,
            top_k=args.top_k,
            device=device,
            output_file=args.output,
        )
    else:
        run_interactive(
            c_engine, d_engine, bridge, w_engine, tokenizer,
            max_new=args.max_new,
            temperature=args.temperature,
            top_k=args.top_k,
            device=device,
        )


if __name__ == "__main__":
    main()
