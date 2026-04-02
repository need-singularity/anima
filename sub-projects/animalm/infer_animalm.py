#!/usr/bin/env python3
"""AnimaLM Inference — Load checkpoint + generate text.

Usage:
  python infer_animalm.py --checkpoint checkpoints/animalm_7b_fresh/final.pt
  python infer_animalm.py --checkpoint checkpoints/animalm_7b_fresh/animalm_step_5000.pt --prompt "의식이란"
  python infer_animalm.py --checkpoint checkpoints/animalm_7b_fresh/final.pt --interactive
"""
import argparse
import sys
import os
import torch
import torch.nn.functional as F
from pathlib import Path

# Import PureField from training script
sys.path.insert(0, str(Path(__file__).parent))
from train_anima_lm import ParallelPureFieldMLP


def load_model(checkpoint_path, base_model="models/mistral-7b-v0.1", device="cuda"):
    """Load base model + PureField checkpoint."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Loading base model: {base_model}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model, torch_dtype=torch.bfloat16
    ).to(device)
    tokenizer = AutoTokenizer.from_pretrained(base_model)

    print(f"Loading checkpoint: {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)

    # Apply PureField to same layers as training (last 8, 2 savants)
    target_layers = 8
    savant_layers = 2
    total_layers = len(model.model.layers)
    start = total_layers - target_layers

    for i in range(start, total_layers):
        layer = model.model.layers[i]
        is_savant = (i - start) < savant_layers
        original_mlp = layer.mlp
        h = original_mlp.gate_proj.weight.shape[1]
        inter = original_mlp.gate_proj.weight.shape[0]

        pf = ParallelPureFieldMLP(original_mlp, h, inter, is_savant=is_savant)
        layer.mlp = pf.to(device=device, dtype=torch.bfloat16)

    # Load PureField states
    if "pf_states" in ckpt:
        loaded = 0
        for name, module in model.named_modules():
            if isinstance(module, ParallelPureFieldMLP) and name in ckpt["pf_states"]:
                module.load_state_dict(ckpt["pf_states"][name], strict=False)
                loaded += 1
        print(f"  Loaded {loaded} PureField layers")

    step = ckpt.get("step", "?")
    best_phi = ckpt.get("best_phi", 0)
    print(f"  Step: {step}, Best Φ: {best_phi:.4f}")

    model.eval()
    return model, tokenizer


def format_prompt(prompt, mode="fewshot"):
    """Wrap prompt for better instruction following on base models.

    Base models (non-Instruct) need few-shot examples to follow instructions.
    Instruct models work with bare prompts.
    """
    if mode == "bare":
        return prompt
    # Few-shot: one Q&A example primes the model to answer rather than continue
    return f"Q: What is 2+2?\nA: 4.\n\nQ: {prompt}\nA:"


@torch.no_grad()
def generate(model, tokenizer, prompt, max_new_tokens=128, temperature=0.8,
             top_p=0.9, top_k=50, repetition_penalty=1.2, device="cuda"):
    """Generate text with PureField-enhanced model."""
    input_ids = tokenizer.encode(prompt, return_tensors="pt").to(device)

    generated = input_ids.clone()
    tensions = []

    for _ in range(max_new_tokens):
        with torch.autocast("cuda", dtype=torch.bfloat16):
            outputs = model(generated[:, -512:])  # sliding window
            logits = outputs.logits[:, -1, :]

        # Repetition penalty
        if repetition_penalty != 1.0:
            for token_id in set(generated[0].tolist()):
                logits[0, token_id] /= repetition_penalty

        # Temperature + top-p sampling
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

        # Collect PureField tension
        for name, module in model.named_modules():
            if isinstance(module, ParallelPureFieldMLP) and module.last_tension is not None:
                tensions.append(module.last_tension.mean().item())
                break

        # Stop on EOS
        if next_token.item() == tokenizer.eos_token_id:
            break

    output_ids = generated[0, input_ids.shape[1]:]
    text = tokenizer.decode(output_ids, skip_special_tokens=True)
    avg_tension = sum(tensions) / len(tensions) if tensions else 0

    return text, avg_tension


def main():
    p = argparse.ArgumentParser(description="AnimaLM Inference")
    p.add_argument("--checkpoint", required=True, help="Path to .pt checkpoint")
    p.add_argument("--base", default=None, help="Base model path (auto-detect)")
    p.add_argument("--prompt", default="의식이란 무엇인가?", help="Generation prompt")
    p.add_argument("--max-tokens", type=int, default=128)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--top-p", type=float, default=0.9)
    p.add_argument("--top-k", type=int, default=50)
    p.add_argument("--repetition-penalty", type=float, default=1.2)
    p.add_argument("--interactive", action="store_true", help="Interactive chat mode")
    p.add_argument("--bare", action="store_true", help="No few-shot wrapper (for Instruct models)")
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = p.parse_args()

    # Auto-detect base model
    base = args.base
    if not base:
        for candidate in ["/workspace/models/mistral-7b-v0.1", "models/mistral-7b-v0.1",
                          "mistralai/Mistral-7B-v0.1"]:
            if os.path.exists(candidate):
                base = candidate
                break
        if not base:
            base = "mistralai/Mistral-7B-v0.1"

    model, tokenizer = load_model(args.checkpoint, base, args.device)

    if args.interactive:
        print("\n═══ AnimaLM Interactive ═══")
        print("  Type 'quit' to exit\n")
        while True:
            try:
                prompt = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if prompt.lower() in ('quit', 'exit', 'q'):
                break
            if not prompt:
                continue
            fmt = format_prompt(prompt, "bare" if args.bare else "fewshot")
            text, tension = generate(model, tokenizer, fmt,
                                     max_new_tokens=args.max_tokens,
                                     temperature=args.temperature,
                                     top_p=args.top_p, top_k=args.top_k,
                                     repetition_penalty=args.repetition_penalty,
                                     device=args.device)
            # Strip trailing Q&A artifacts from few-shot
            if "\nQ:" in text:
                text = text[:text.index("\nQ:")]
            print(f"Anima: {text.strip()}")
            print(f"  [tension={tension:.4f}]\n")
    else:
        fmt = format_prompt(args.prompt, "bare" if args.bare else "fewshot")
        print(f"\nPrompt: {args.prompt}")
        print("─" * 60)
        text, tension = generate(model, tokenizer, fmt,
                                 max_new_tokens=args.max_tokens,
                                 temperature=args.temperature,
                                 top_p=args.top_p, top_k=args.top_k,
                                 repetition_penalty=args.repetition_penalty,
                                 device=args.device)
        if "\nQ:" in text:
            text = text[:text.index("\nQ:")]
        print(f"{text.strip()}")
        print(f"─" * 60)
        print(f"Tension: {tension:.4f}")
        print(f"Tokens: {len(tokenizer.encode(text))}")


if __name__ == "__main__":
    main()
