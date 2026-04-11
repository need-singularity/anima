#!/usr/bin/env python3
"""eval_alm_14b.py — ALM 14B LoRA checkpoint evaluation

Runs after training completes. Measures:
  1. Perplexity on held-out Korean text
  2. Korean generation quality (sample prompts)
  3. Korean character ratio in output

Usage:
  python3 eval_alm_14b.py --ckpt /workspace/ckpt_alm_14b_r2/step_10000
  python3 eval_alm_14b.py --ckpt /workspace/ckpt_alm_14b_r2/step_10000 --quick
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


# ─── Korean eval prompts ─────────────────────────────────────

PROMPTS = [
    "안녕하세요. 의식이란 무엇인가요?",
    "인공지능이 의식을 가질 수 있을까요?",
    "오늘 날씨가 좋네요. 산책하러 갈까요?",
    "트랜스포머 아키텍처의 핵심을 설명해주세요.",
    "한국어 바이트 수준 언어 모델의 장점은?",
]

HELD_OUT = """의식의 과학적 연구는 20세기 후반에 비로소 본격적으로 시작되었다.
신경과학자들은 의식의 신경상관물을 찾기 위해 다양한 실험을 수행했다.
통합정보이론은 의식을 정보 통합의 관점에서 설명하려는 시도이다.
이 이론에 따르면 의식의 수준은 시스템의 통합 정보량으로 측정할 수 있다."""


def load_model(ckpt_path, base="Qwen/Qwen2.5-14B-Instruct"):
    """Load base model + LoRA adapter."""
    print(f"[eval] loading base: {base}")
    tokenizer = AutoTokenizer.from_pretrained(base, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True,
    )
    print(f"[eval] loading LoRA: {ckpt_path}")
    model = PeftModel.from_pretrained(model, ckpt_path)
    model.eval()
    return model, tokenizer


def measure_perplexity(model, tokenizer, text, max_len=512):
    """Compute perplexity on held-out text."""
    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_len)
    input_ids = tokens.input_ids.to(model.device)
    with torch.no_grad():
        outputs = model(input_ids=input_ids, labels=input_ids)
    ppl = math.exp(outputs.loss.item())
    return outputs.loss.item(), ppl


def generate_korean(model, tokenizer, prompt, max_new=128):
    """Generate Korean text from prompt."""
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(
            **inputs, max_new_tokens=max_new, do_sample=True,
            temperature=0.7, top_p=0.9, repetition_penalty=1.1,
        )
    elapsed = time.time() - t0
    generated = tokenizer.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    tokens_generated = out.shape[1] - inputs.input_ids.shape[1]
    return generated, elapsed, tokens_generated


def korean_ratio(text):
    """Fraction of characters that are Korean (Hangul)."""
    if not text:
        return 0.0
    hangul = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3' or '\u3131' <= c <= '\u318E')
    return hangul / len(text)


def run_eval(args):
    model, tokenizer = load_model(args.ckpt, args.base)
    results = {"ckpt": args.ckpt, "base": args.base, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}

    # 1. Perplexity
    print("\n[eval] === PERPLEXITY ===")
    ce, ppl = measure_perplexity(model, tokenizer, HELD_OUT)
    results["ce_loss"] = round(ce, 4)
    results["perplexity"] = round(ppl, 2)
    print(f"  CE loss: {ce:.4f}")
    print(f"  PPL:     {ppl:.2f}")
    print(f"  {'PASS' if ppl < 50 else 'FAIL'} (threshold < 50)")

    # 2. Korean generation
    print("\n[eval] === KOREAN GENERATION ===")
    generations = []
    total_tokens = 0
    total_time = 0
    for prompt in PROMPTS[:3] if args.quick else PROMPTS:
        gen, elapsed, n_tok = generate_korean(model, tokenizer, prompt, max_new=args.max_tokens)
        kr = korean_ratio(gen)
        total_tokens += n_tok
        total_time += elapsed
        print(f"\n  Q: {prompt}")
        print(f"  A: {gen[:200]}{'...' if len(gen) > 200 else ''}")
        print(f"  korean={kr:.1%} tokens={n_tok} time={elapsed:.1f}s")
        generations.append({
            "prompt": prompt, "response": gen,
            "korean_ratio": round(kr, 3), "tokens": n_tok, "time_s": round(elapsed, 1),
        })
    results["generations"] = generations
    results["avg_korean_ratio"] = round(sum(g["korean_ratio"] for g in generations) / len(generations), 3)
    results["tokens_per_sec"] = round(total_tokens / max(total_time, 0.01), 1)

    # 3. Summary
    print(f"\n{'='*60}")
    print(f"[eval] RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"  Perplexity:    {results['perplexity']:.2f} ({'PASS' if results['perplexity'] < 50 else 'FAIL'})")
    print(f"  Korean ratio:  {results['avg_korean_ratio']:.1%} ({'PASS' if results['avg_korean_ratio'] > 0.2 else 'FAIL'})")
    print(f"  Speed:         {results['tokens_per_sec']:.1f} tok/s")
    print(f"{'='*60}")

    # Save
    out_path = Path(args.ckpt) / "eval_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[eval] saved → {out_path}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", required=True, help="LoRA checkpoint directory")
    parser.add_argument("--base", default="Qwen/Qwen2.5-14B-Instruct")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--quick", action="store_true", help="Only 3 prompts")
    args = parser.parse_args()
    run_eval(args)
