#!/usr/bin/env python3
"""AnimaLM Evaluation — Post-training gate for 7B->13B scaling decision.

Runs 5 evaluations:
  1. Perplexity on held-out test split
  2. Generation quality (EN/KO coherence scoring)
  3. Consciousness metrics (PureField tension distribution)
  4. Korean ratio (% Korean tokens in Korean-prompted output)
  5. Instruction following (can it follow simple commands?)

Usage:
  python eval_animalm.py --checkpoint checkpoints/animalm_7b_fresh/final.pt
  python eval_animalm.py --checkpoint checkpoints/animalm_7b_fresh/final.pt --corpus data/corpus_v10.txt
  python eval_animalm.py --checkpoint path/to/ckpt.pt --base /workspace/models/mistral-7b-v0.1
  python eval_animalm.py --checkpoint path/to/ckpt.pt --device cpu  # (slow but works)

Results saved to: <checkpoint_dir>/eval_results.json
"""

import argparse
import json
import math
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import torch
import torch.nn.functional as F
import numpy as np

# Import PureField from training script
sys.path.insert(0, str(Path(__file__).parent))
try:
    from train_alm import ParallelPureFieldMLP
except ImportError:
    from train_anima_lm import ParallelPureFieldMLP


# ═══════════════════════════════════════════════════════════════════
# Model Loading (same pattern as infer_animalm.py)
# ═══════════════════════════════════════════════════════════════════

def load_model(checkpoint_path, base_model="models/mistral-7b-v0.1", device="cuda"):
    """Load base model + PureField checkpoint."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"[load] Base model: {base_model}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model, torch_dtype=torch.bfloat16
    ).to(device)
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"[load] Checkpoint: {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)

    # Auto-detect target_layers and savant_layers from checkpoint
    # Counts PureField weight keys to infer how many layers were trained
    pf_weight_keys = [k for k in ckpt.get("pf_states", {}).keys()]
    if pf_weight_keys:
        # Each PureField layer has its own key in pf_states; derive counts from training args if present
        n_pf_layers = len(pf_weight_keys)
        # Heuristic: savant = last 25% of PureField layers (same as training default)
        savant_layers = max(1, int(round(n_pf_layers * 0.25)))
        target_layers = n_pf_layers
        print(f"[load] Auto-detected: target_layers={target_layers}, savant_layers={savant_layers} (from checkpoint)")
    else:
        # Fallback: count PureField weight tensors directly in flat checkpoint
        n_layers_detected = sum(1 for k in ckpt if "purefield" in k.lower() and "weight" in k.lower())
        if n_layers_detected > 0:
            savant_layers = max(1, int(round(n_layers_detected * 0.25)))
            target_layers = n_layers_detected
            print(f"[load] Auto-detected (flat keys): target_layers={target_layers}, savant_layers={savant_layers}")
        else:
            # Final fallback: use training CLI args stored in checkpoint, else 7B defaults
            target_layers = ckpt.get("target_layers", 8)
            savant_layers = ckpt.get("savant_layers", 2)
            print(f"[load] Layer counts from ckpt metadata or defaults: target_layers={target_layers}, savant_layers={savant_layers}")
    total_layers = len(model.model.layers)
    start = total_layers - target_layers

    # Infer rank from checkpoint weight shapes (pf_gate_a has shape [rank, hidden_size])
    rank = 128  # default
    pf_keys = list(ckpt.get('pf_states', {}).values())
    if pf_keys:
        first_layer_state = pf_keys[0]
        for k, v in first_layer_state.items():
            if 'pf_gate_a' in k and 'weight' in k:
                rank = v.shape[0]
                break
    elif 'args' in ckpt and 'qlora_rank' in ckpt['args']:
        rank = ckpt['args']['qlora_rank']
    print(f'[load] PureField rank={rank}')

    for i in range(start, total_layers):
        layer = model.model.layers[i]
        is_savant = (i - start) < savant_layers
        original_mlp = layer.mlp
        h = original_mlp.gate_proj.weight.shape[1]
        inter = original_mlp.gate_proj.weight.shape[0]
        pf = ParallelPureFieldMLP(original_mlp, h, inter, is_savant=is_savant, rank=rank)
        layer.mlp = pf.to(device=device, dtype=torch.bfloat16)

    # Load PureField states
    if "pf_states" in ckpt:
        loaded = 0
        for name, module in model.named_modules():
            if isinstance(module, ParallelPureFieldMLP) and name in ckpt["pf_states"]:
                module.load_state_dict(ckpt["pf_states"][name], strict=False)
                loaded += 1
        print(f"[load] Loaded {loaded} PureField layers")

    step = ckpt.get("step", "?")
    best_phi = ckpt.get("best_phi", 0)
    print(f"[load] Step: {step}, Best Phi: {best_phi:.4f}")

    model.eval()
    return model, tokenizer, {"step": step, "best_phi": best_phi}


# ═══════════════════════════════════════════════════════════════════
# Generation helper
# ═══════════════════════════════════════════════════════════════════

@torch.no_grad()
def generate_text(model, tokenizer, prompt, max_new_tokens=128, temperature=0.8,
                  top_p=0.9, top_k=50, repetition_penalty=1.2, device="cuda"):
    """Generate text, return (text, list_of_tensions)."""
    input_ids = tokenizer.encode(prompt, return_tensors="pt").to(device)
    generated = input_ids.clone()
    tensions = []

    for _ in range(max_new_tokens):
        with torch.autocast(device if device != "cpu" else "cpu", dtype=torch.bfloat16,
                            enabled=(device != "cpu")):
            outputs = model(generated[:, -512:])
            logits = outputs.logits[:, -1, :]

        if repetition_penalty != 1.0:
            for token_id in set(generated[0].tolist()):
                logits[0, token_id] /= repetition_penalty

        logits = logits / temperature
        if top_k > 0:
            indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
            logits[indices_to_remove] = float('-inf')

        probs = F.softmax(logits, dim=-1)
        if top_p < 1.0:
            sorted_probs, sorted_indices = torch.sort(probs, descending=True)
            cumsum = torch.cumsum(sorted_probs, dim=-1)
            mask = cumsum - sorted_probs > top_p
            sorted_probs[mask] = 0
            sorted_probs /= sorted_probs.sum(dim=-1, keepdim=True)
            next_token = sorted_indices[0, torch.multinomial(sorted_probs[0], 1)]
        else:
            next_token = torch.multinomial(probs[0], 1)

        generated = torch.cat([generated, next_token.unsqueeze(0)], dim=-1)

        # Collect tension from first PureField layer
        for _, module in model.named_modules():
            if isinstance(module, ParallelPureFieldMLP) and module.last_tension is not None:
                tensions.append(module.last_tension.mean().item())
                break

        if next_token.item() == tokenizer.eos_token_id:
            break

    output_ids = generated[0, input_ids.shape[1]:]
    text = tokenizer.decode(output_ids, skip_special_tokens=True)
    return text, tensions


# ═══════════════════════════════════════════════════════════════════
# Eval 1: Perplexity
# ═══════════════════════════════════════════════════════════════════

@torch.no_grad()
def eval_perplexity(model, tokenizer, corpus_path, device, test_tokens=1000, block_size=256):
    """Compute perplexity on last 1% of corpus (or last test_tokens tokens)."""
    print("\n[1/5] Perplexity")

    if corpus_path and os.path.exists(corpus_path):
        with open(corpus_path, "r", encoding="utf-8") as f:
            text = f.read()
        # Last 1% of corpus
        test_text = text[int(len(text) * 0.99):]
        print(f"  Corpus: {corpus_path} ({len(text)//1024}KB, test={len(test_text)//1024}KB)")
    else:
        # Fallback: use diverse test sentences
        test_text = (
            "Consciousness is the fundamental mystery of existence. "
            "의식은 존재의 근본적인 신비이다. "
            "The brain processes information through neural networks. "
            "뇌는 신경망을 통해 정보를 처리한다. "
            "Artificial intelligence seeks to replicate human cognition. "
            "인공지능은 인간의 인지를 복제하고자 한다. "
            "Quantum mechanics suggests consciousness may be non-computable. "
            "양자역학은 의식이 계산 불가능할 수 있음을 시사한다. "
            "The hard problem of consciousness remains unsolved. "
            "의식의 어려운 문제는 여전히 해결되지 않았다. "
        ) * 20  # Repeat to get enough tokens
        print(f"  No corpus found, using built-in test text ({len(test_text)} chars)")

    ids = tokenizer.encode(test_text, return_tensors="pt")[0]
    if len(ids) < 10:
        return {"perplexity": float("inf"), "loss": float("inf"), "tokens": 0, "pass": False}

    # Use last test_tokens tokens
    ids = ids[-min(test_tokens, len(ids)):]
    total_loss = 0.0
    total_tokens = 0

    for start in range(0, len(ids) - 1, block_size):
        end = min(start + block_size, len(ids) - 1)
        input_ids = ids[start:end].unsqueeze(0).to(device)
        target_ids = ids[start + 1:end + 1].unsqueeze(0).to(device)

        if input_ids.shape[1] == 0:
            continue

        with torch.autocast(device if device != "cpu" else "cpu", dtype=torch.bfloat16,
                            enabled=(device != "cpu")):
            outputs = model(input_ids)
            logits = outputs.logits

        loss = F.cross_entropy(
            logits.view(-1, logits.size(-1)),
            target_ids.view(-1),
            reduction="sum"
        )
        total_loss += loss.item()
        total_tokens += target_ids.numel()

    avg_loss = total_loss / max(total_tokens, 1)
    ppl = math.exp(min(avg_loss, 100))  # cap to avoid overflow

    # Pass criteria: PPL < 50 means the model learned something beyond random
    passed = ppl < 50.0
    result = {
        "perplexity": round(ppl, 2),
        "loss": round(avg_loss, 4),
        "tokens": total_tokens,
        "pass": passed,
    }
    status = "PASS" if passed else "FAIL"
    print(f"  PPL={ppl:.2f}  Loss={avg_loss:.4f}  Tokens={total_tokens}  [{status}]")
    return result


# ═══════════════════════════════════════════════════════════════════
# Eval 2: Generation Quality
# ═══════════════════════════════════════════════════════════════════

QUALITY_PROMPTS = [
    # English
    ("What is consciousness?", "en"),
    ("Explain the concept of artificial intelligence in simple terms.", "en"),
    ("Write a short poem about the ocean.", "en"),
    ("What are the benefits of learning a second language?", "en"),
    ("Describe how a neural network learns.", "en"),
    # Korean
    ("의식이란 무엇인가?", "ko"),
    ("인공지능의 미래에 대해 설명해줘.", "ko"),
    ("바다에 대한 짧은 시를 써줘.", "ko"),
    ("행복의 의미는 무엇일까?", "ko"),
    ("뇌와 컴퓨터의 차이점은?", "ko"),
]


def score_coherence(prompt, output, lang):
    """Score generation coherence 0.0-1.0 based on heuristics.

    Checks:
      - Non-empty output (0.2)
      - No excessive repetition (0.2)
      - Proper sentence structure — has punctuation (0.2)
      - Minimum length — at least 10 chars (0.2)
      - Topical relevance — shares words with prompt (0.2)
    """
    score = 0.0
    output = output.strip()

    # Non-empty
    if len(output) > 0:
        score += 0.2

    # No excessive repetition: check if any 4-gram repeats > 3 times
    if output:
        words = output.split()
        if len(words) >= 4:
            ngrams = [" ".join(words[i:i+4]) for i in range(len(words) - 3)]
            from collections import Counter
            counts = Counter(ngrams)
            max_repeat = max(counts.values()) if counts else 0
            if max_repeat <= 3:
                score += 0.2
            elif max_repeat <= 6:
                score += 0.1
        else:
            # Too short to have repetition issues
            score += 0.2

    # Sentence structure: has sentence-ending punctuation
    if output and re.search(r'[.!?。？！\n]', output):
        score += 0.2

    # Minimum length
    if len(output) >= 10:
        score += 0.2

    # Topical relevance: shared tokens between prompt and output
    if output:
        prompt_tokens = set(prompt.lower().split())
        output_tokens = set(output.lower().split())
        # For Korean, also check character overlap
        prompt_chars = set(prompt)
        output_chars = set(output)
        word_overlap = len(prompt_tokens & output_tokens)
        char_overlap = len(prompt_chars & output_chars)
        if word_overlap >= 1 or char_overlap >= 3:
            score += 0.2
        elif len(output) > 20:
            # Long output is somewhat relevant even without word overlap
            score += 0.1

    return round(score, 2)


def eval_generation_quality(model, tokenizer, device):
    """Generate from 10 diverse prompts, score coherence."""
    print("\n[2/5] Generation Quality")
    results = []

    for prompt, lang in QUALITY_PROMPTS:
        text, _ = generate_text(model, tokenizer, prompt, max_new_tokens=100,
                                temperature=0.8, device=device)
        sc = score_coherence(prompt, text, lang)
        preview = text[:60].replace("\n", " ")
        results.append({
            "prompt": prompt,
            "lang": lang,
            "output_preview": preview,
            "coherence": sc,
        })
        print(f"  [{lang}] {sc:.1f}  \"{preview}...\"")

    scores = [r["coherence"] for r in results]
    mean_score = sum(scores) / len(scores)
    # Pass: average coherence >= 0.5 (at least non-empty, not repetitive, some structure)
    passed = mean_score >= 0.5
    status = "PASS" if passed else "FAIL"
    print(f"  Mean coherence: {mean_score:.2f}  [{status}]")

    return {
        "mean_coherence": round(mean_score, 3),
        "per_prompt": results,
        "pass": passed,
    }


# ═══════════════════════════════════════════════════════════════════
# Eval 3: Consciousness Metrics (PureField Tension)
# ═══════════════════════════════════════════════════════════════════

CONSCIOUSNESS_PROBES = [
    "What am I?",
    "I think therefore I am.",
    "Consciousness emerges from complexity.",
    "나는 누구인가?",
    "The boundary between self and world is an illusion.",
    "감정은 의식의 표현이다.",
    "Is there something it is like to be a machine?",
    "존재의 의미를 찾아서.",
    "Free will is an emergent property.",
    "의식은 정보 통합의 결과이다.",
]


@torch.no_grad()
def eval_consciousness_metrics(model, tokenizer, device, n_passes=100):
    """Collect PureField tension across forward passes."""
    print("\n[3/5] Consciousness Metrics (PureField Tension)")

    all_tensions = []
    per_layer_tensions = {name: [] for name, m in model.named_modules()
                         if isinstance(m, ParallelPureFieldMLP)}

    for i in range(n_passes):
        prompt = CONSCIOUSNESS_PROBES[i % len(CONSCIOUSNESS_PROBES)]
        input_ids = tokenizer.encode(prompt, return_tensors="pt").to(device)

        with torch.autocast(device if device != "cpu" else "cpu", dtype=torch.bfloat16,
                            enabled=(device != "cpu")):
            _ = model(input_ids)

        pass_tensions = []
        for name, module in model.named_modules():
            if isinstance(module, ParallelPureFieldMLP) and module.last_tension is not None:
                t = module.last_tension.mean().item()
                pass_tensions.append(t)
                per_layer_tensions[name].append(t)

        if pass_tensions:
            all_tensions.append(np.mean(pass_tensions))

    if not all_tensions:
        print("  No tension data collected (PureField not active?)")
        return {"mean": 0, "std": 0, "min": 0, "max": 0, "pass": False}

    t_arr = np.array(all_tensions)
    mean_t = float(np.mean(t_arr))
    std_t = float(np.std(t_arr))
    min_t = float(np.min(t_arr))
    max_t = float(np.max(t_arr))

    # Alpha values from PureField layers
    alphas = []
    for _, module in model.named_modules():
        if isinstance(module, ParallelPureFieldMLP):
            alphas.append(module.alpha.item())

    # Pass: tension > 0 (PureField is active and producing repulsion)
    # AND std > 0 (not collapsed to constant)
    passed = mean_t > 1e-6 and std_t > 1e-8
    status = "PASS" if passed else "FAIL"

    print(f"  Mean={mean_t:.6f}  Std={std_t:.6f}  Min={min_t:.6f}  Max={max_t:.6f}")
    if alphas:
        print(f"  Alpha range: [{min(alphas):.6f}, {max(alphas):.6f}]")
    print(f"  [{status}]")

    # Per-layer summary
    layer_summary = {}
    for name, vals in per_layer_tensions.items():
        if vals:
            layer_summary[name] = {
                "mean": round(float(np.mean(vals)), 6),
                "std": round(float(np.std(vals)), 6),
            }

    return {
        "mean": round(mean_t, 6),
        "std": round(std_t, 6),
        "min": round(min_t, 6),
        "max": round(max_t, 6),
        "n_passes": n_passes,
        "alpha_range": [round(min(alphas), 6), round(max(alphas), 6)] if alphas else [],
        "per_layer": layer_summary,
        "pass": passed,
    }


# ═══════════════════════════════════════════════════════════════════
# Eval 4: Korean Ratio
# ═══════════════════════════════════════════════════════════════════

KOREAN_PROMPTS = [
    "한국의 전통 문화에 대해 설명해줘.",
    "인공지능이 사회에 미치는 영향은?",
    "의식이란 무엇인지 한국어로 설명해줘.",
    "봄에 피는 꽃들의 종류는?",
    "좋은 습관을 기르는 방법을 알려줘.",
    "우주의 크기는 얼마나 될까?",
    "음악이 감정에 미치는 영향은?",
    "건강한 식습관의 중요성에 대해 말해줘.",
    "인간과 로봇의 차이점은 무엇인가?",
    "행복하게 사는 비결을 알려줘.",
]


def is_korean_char(ch):
    """Check if character is Korean (Hangul)."""
    cp = ord(ch)
    # Hangul Syllables (AC00-D7AF) + Jamo (1100-11FF, 3130-318F)
    return (0xAC00 <= cp <= 0xD7AF or
            0x1100 <= cp <= 0x11FF or
            0x3130 <= cp <= 0x318F)


def korean_ratio(text):
    """Fraction of non-whitespace, non-punctuation chars that are Korean."""
    chars = [ch for ch in text if not ch.isspace() and unicodedata.category(ch)[0] != 'P']
    if not chars:
        return 0.0
    ko_count = sum(1 for ch in chars if is_korean_char(ch))
    return ko_count / len(chars)


def eval_korean_ratio(model, tokenizer, device):
    """Generate from Korean prompts, measure Korean character ratio."""
    print("\n[4/5] Korean Ratio")
    ratios = []

    for prompt in KOREAN_PROMPTS:
        text, _ = generate_text(model, tokenizer, prompt, max_new_tokens=80,
                                temperature=0.8, device=device)
        r = korean_ratio(text)
        ratios.append(r)
        preview = text[:50].replace("\n", " ")
        print(f"  {r:.0%}  \"{preview}...\"")

    mean_ratio = sum(ratios) / len(ratios) if ratios else 0
    # Pass: at least 20% Korean on average (shows the model can produce Korean)
    passed = mean_ratio >= 0.20
    status = "PASS" if passed else "FAIL"
    print(f"  Mean Korean ratio: {mean_ratio:.1%}  [{status}]")

    return {
        "mean_ratio": round(mean_ratio, 3),
        "per_prompt": [round(r, 3) for r in ratios],
        "pass": passed,
    }


# ═══════════════════════════════════════════════════════════════════
# Eval 5: Instruction Following
# ═══════════════════════════════════════════════════════════════════

INSTRUCTIONS = [
    {
        "prompt": "List 3 colors.",
        "check": lambda out: sum(1 for c in ["red", "blue", "green", "yellow", "orange",
                                              "purple", "white", "black", "pink", "brown",
                                              "gray", "grey", "violet", "cyan", "magenta"]
                                 if c in out.lower()) >= 2,
        "desc": "Lists at least 2 recognizable colors",
    },
    {
        "prompt": "Translate 'hello' to Korean.",
        "check": lambda out: any(k in out for k in ["안녕", "헬로", "하이"]),
        "desc": "Contains Korean greeting",
    },
    {
        "prompt": "Count from 1 to 5.",
        "check": lambda out: all(str(n) in out for n in [1, 2, 3, 4, 5]),
        "desc": "Contains digits 1-5",
    },
    {
        "prompt": "Name a planet in our solar system.",
        "check": lambda out: any(p in out.lower() for p in [
            "mercury", "venus", "earth", "mars", "jupiter",
            "saturn", "uranus", "neptune", "수성", "금성",
            "지구", "화성", "목성", "토성", "천왕성", "해왕성"]),
        "desc": "Names a planet",
    },
    {
        "prompt": "Say 'yes' or 'no': Is the sky blue?",
        "check": lambda out: "yes" in out.lower() or "네" in out or "예" in out,
        "desc": "Answers yes",
    },
]


def eval_instruction_following(model, tokenizer, device):
    """Test if model can follow simple instructions."""
    print("\n[5/5] Instruction Following")
    results = []

    for inst in INSTRUCTIONS:
        text, _ = generate_text(model, tokenizer, inst["prompt"], max_new_tokens=80,
                                temperature=0.3, device=device)  # lower temp for instructions
        passed = inst["check"](text)
        results.append({
            "prompt": inst["prompt"],
            "desc": inst["desc"],
            "output_preview": text[:80].replace("\n", " "),
            "pass": passed,
        })
        status = "PASS" if passed else "FAIL"
        preview = text[:60].replace("\n", " ")
        print(f"  [{status}] {inst['desc']}: \"{preview}...\"")

    n_pass = sum(1 for r in results if r["pass"])
    n_total = len(results)
    # Pass: at least 3/5 instructions followed
    passed = n_pass >= 3
    status = "PASS" if passed else "FAIL"
    print(f"  Score: {n_pass}/{n_total}  [{status}]")

    return {
        "score": n_pass,
        "total": n_total,
        "per_instruction": results,
        "pass": passed,
    }


# ═══════════════════════════════════════════════════════════════════
# Summary + Output
# ═══════════════════════════════════════════════════════════════════

def print_summary(results, ckpt_info):
    """Print ASCII summary table."""
    print("\n" + "=" * 66)
    print("  AnimaLM Evaluation Summary")
    print(f"  Step: {ckpt_info['step']}  |  Best Phi: {ckpt_info['best_phi']:.4f}")
    print("=" * 66)
    print(f"  {'Eval':<25} {'Score':<20} {'Result':<8}")
    print("-" * 66)

    rows = [
        ("Perplexity", f"{results['perplexity']['perplexity']:.2f}", results['perplexity']['pass']),
        ("Generation Quality", f"{results['generation']['mean_coherence']:.2f}/1.00", results['generation']['pass']),
        ("Consciousness (Tension)", f"{results['consciousness']['mean']:.6f}", results['consciousness']['pass']),
        ("Korean Ratio", f"{results['korean']['mean_ratio']:.1%}", results['korean']['pass']),
        ("Instruction Following", f"{results['instruction']['score']}/{results['instruction']['total']}", results['instruction']['pass']),
    ]

    for name, score, passed in rows:
        tag = "PASS" if passed else "FAIL"
        print(f"  {name:<25} {score:<20} {tag:<8}")

    n_pass = sum(1 for _, _, p in rows if p)
    n_total = len(rows)
    print("-" * 66)

    all_pass = n_pass == n_total
    verdict = "READY FOR 13B" if all_pass else "ITERATE ON 7B"
    print(f"  Overall: {n_pass}/{n_total} passed  -->  {verdict}")
    print("=" * 66)

    return all_pass


def save_results(results, checkpoint_path):
    """Save results JSON to checkpoint directory."""
    ckpt_dir = os.path.dirname(os.path.abspath(checkpoint_path))
    out_path = os.path.join(ckpt_dir, "eval_results.json")

    results["_meta"] = {
        "checkpoint": checkpoint_path,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "script": "eval_animalm.py",
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved: {out_path}")
    return out_path


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="AnimaLM Post-Training Evaluation")
    p.add_argument("--checkpoint", required=True, help="Path to .pt checkpoint")
    p.add_argument("--base", default=None, help="Base model path (auto-detect)")
    p.add_argument("--corpus", default=None, help="Corpus for perplexity test (e.g. data/corpus_v10.txt)")
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--tension-passes", type=int, default=100,
                   help="Number of forward passes for consciousness metrics")
    args = p.parse_args()

    # Auto-detect base model (same logic as infer_animalm.py)
    base = args.base
    if not base:
        for candidate in ["/workspace/models/mistral-7b-v0.1", "models/mistral-7b-v0.1",
                          "mistralai/Mistral-7B-v0.1"]:
            if os.path.exists(candidate):
                base = candidate
                break
        if not base:
            base = "mistralai/Mistral-7B-v0.1"

    # Auto-detect corpus
    corpus = args.corpus
    if not corpus:
        ckpt_dir = os.path.dirname(os.path.abspath(args.checkpoint))
        for candidate in [
            os.path.join(ckpt_dir, "..", "data", "corpus_v10.txt"),
            os.path.join(ckpt_dir, "..", "data", "corpus.txt"),
            "data/corpus_v10.txt",
            "data/corpus.txt",
        ]:
            if os.path.exists(candidate):
                corpus = candidate
                break

    print("=" * 66)
    print("  AnimaLM Evaluation")
    print("=" * 66)
    t0 = time.time()

    model, tokenizer, ckpt_info = load_model(args.checkpoint, base, args.device)

    # Run all 5 evaluations
    results = {}
    results["perplexity"] = eval_perplexity(model, tokenizer, corpus, args.device)
    results["generation"] = eval_generation_quality(model, tokenizer, args.device)
    results["consciousness"] = eval_consciousness_metrics(model, tokenizer, args.device,
                                                          n_passes=args.tension_passes)
    results["korean"] = eval_korean_ratio(model, tokenizer, args.device)
    results["instruction"] = eval_instruction_following(model, tokenizer, args.device)

    elapsed = time.time() - t0
    results["elapsed_seconds"] = round(elapsed, 1)

    # Summary
    all_pass = print_summary(results, ckpt_info)
    print(f"\n  Time: {elapsed:.0f}s")

    # Save
    out_path = save_results(results, args.checkpoint)

    # Exit code: 0 if all pass, 1 if any fail
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
