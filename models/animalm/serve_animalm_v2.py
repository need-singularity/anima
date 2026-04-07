#!/usr/bin/env python3
"""AnimaLM Serving — 4-bit quantized for RTX 5070 (12GB VRAM).

Usage:
  python serve_animalm_v2.py --checkpoint checkpoints/animalm_7b_fresh/final.pt --port 8080
  python serve_animalm_v2.py --checkpoint checkpoints/animalm_14b/final.pt --quantize 4bit
"""
import argparse
import json
import sys
import os
import torch
import torch.nn.functional as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from train_anima_lm import ParallelPureFieldMLP


def _detect_device(requested):
    """Auto-detect best device: cuda > mps > cpu."""
    if requested == "auto":
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    return requested


def load_model_quantized(checkpoint_path, base_model=None, quantize="4bit", device="cuda"):
    """Load base model with quantization + PureField checkpoint."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = _detect_device(device)

    # bitsandbytes quantization requires CUDA
    if quantize in ("4bit", "8bit") and device != "cuda":
        print(f"  WARNING: {quantize} quantization requires CUDA, falling back to float16")
        quantize = "float16" if device == "mps" else "bf16"

    if not base_model:
        for candidate in ["/workspace/models/mistral-7b-v0.1", "/workspace/models/qwen2.5-14b",
                          "models/mistral-7b-v0.1", "models/qwen2.5-14b"]:
            if os.path.exists(candidate):
                base_model = candidate
                break
        if not base_model:
            # Fall back to HuggingFace Hub ID (will download if not cached)
            base_model = "mistralai/Mistral-7B-v0.1"
            print(f"  No local model found, using HF Hub: {base_model}")

    print(f"Loading {base_model} ({quantize}) on {device}...")

    if quantize == "4bit":
        from transformers import BitsAndBytesConfig
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            base_model, quantization_config=quant_config, device_map="auto"
        )
    elif quantize == "8bit":
        from transformers import BitsAndBytesConfig
        model = AutoModelForCausalLM.from_pretrained(
            base_model, load_in_8bit=True, device_map="auto"
        )
    elif quantize == "float16":
        model = AutoModelForCausalLM.from_pretrained(
            base_model, torch_dtype=torch.float16
        ).to(device)
    else:  # bf16
        model = AutoModelForCausalLM.from_pretrained(
            base_model, torch_dtype=torch.bfloat16
        ).to(device)

    tokenizer = AutoTokenizer.from_pretrained(base_model)

    # Determine dtype for PureField weights
    pf_dtype = torch.float16 if device == "mps" else torch.bfloat16

    # Load PureField
    print(f"Loading checkpoint: {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

    target_layers = ckpt.get("args", {}).get("target_layers", 8)
    savant_layers = ckpt.get("args", {}).get("savant_layers", 2)
    rank = ckpt.get("args", {}).get("qlora_rank", 128)

    total_layers = len(model.model.layers)
    start = total_layers - target_layers

    for i in range(start, total_layers):
        layer = model.model.layers[i]
        original_mlp = layer.mlp
        h = original_mlp.gate_proj.weight.shape[1]
        inter = original_mlp.gate_proj.weight.shape[0]
        is_savant = (i - start) < savant_layers
        pf = ParallelPureFieldMLP(original_mlp, h, inter, is_savant=is_savant, rank=rank)
        # PureField weights in appropriate dtype (not quantized)
        for name, p in pf.named_parameters():
            if "original_mlp" not in name:
                p.data = p.data.to(device=device, dtype=pf_dtype)
        layer.mlp = pf

    if "pf_states" in ckpt:
        loaded = 0
        for name, module in model.named_modules():
            if isinstance(module, ParallelPureFieldMLP) and name in ckpt["pf_states"]:
                module.load_state_dict(ckpt["pf_states"][name], strict=False)
                loaded += 1
        print(f"  Loaded {loaded} PureField layers")

    step = ckpt.get("step", "?")
    print(f"  Step: {step}, Quantization: {quantize}, Device: {device}")

    # Memory report
    if torch.cuda.is_available():
        vram_used = torch.cuda.memory_allocated() / 1024**3
        vram_total = torch.cuda.get_device_properties(0).total_mem / 1024**3
        print(f"  VRAM: {vram_used:.1f}/{vram_total:.1f} GB")
    elif device == "mps":
        # MPS shares unified memory with CPU
        try:
            allocated = torch.mps.current_allocated_memory() / 1024**3
            print(f"  MPS memory allocated: {allocated:.1f} GB (unified memory)")
        except AttributeError:
            print("  MPS: unified memory (no per-device stats available)")

    model.eval()
    return model, tokenizer


@torch.no_grad()
def generate(model, tokenizer, prompt, max_new_tokens=256, temperature=0.8,
             top_p=0.9, top_k=50, repetition_penalty=1.2):
    """Generate text."""
    input_ids = tokenizer.encode(prompt, return_tensors="pt").to(model.device)
    generated = input_ids.clone()

    # Determine autocast device type
    device_type = "cuda" if model.device.type == "cuda" else ("mps" if model.device.type == "mps" else "cpu")
    ac_dtype = torch.float16 if device_type == "mps" else torch.bfloat16

    for _ in range(max_new_tokens):
        with torch.autocast(device_type, dtype=ac_dtype) if device_type != "cpu" else torch.no_grad():
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
        if next_token.item() == tokenizer.eos_token_id:
            break

    output_ids = generated[0, input_ids.shape[1]:]
    return tokenizer.decode(output_ids, skip_special_tokens=True)


def serve_http(model, tokenizer, port=8080):
    """Simple HTTP API for chat."""
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            prompt = body.get("prompt", body.get("text", ""))
            max_tokens = body.get("max_tokens", 256)
            temp = body.get("temperature", 0.8)

            # Few-shot wrapper for base models (improves instruction following)
            bare = body.get("bare", False)
            if not bare:
                prompt = f"Q: What is 2+2?\nA: 4.\n\nQ: {prompt}\nA:"
            response = generate(model, tokenizer, prompt,
                                max_new_tokens=max_tokens, temperature=temp)
            # Strip trailing Q&A artifacts
            if "\nQ:" in response:
                response = response[:response.index("\nQ:")]
            response = response.strip()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"response": response}, ensure_ascii=False).encode())

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "model": "AnimaLM"}).encode())

        def log_message(self, format, *args):
            pass  # suppress logs

    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"\nServing on http://0.0.0.0:{port}")
    print("  POST /  {\"prompt\": \"...\", \"max_tokens\": 256}")
    server.serve_forever()


def main():
    p = argparse.ArgumentParser(description="AnimaLM Serving (4-bit quantized)")
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--base", default=None)
    p.add_argument("--quantize", default="4bit", choices=["4bit", "8bit", "bf16", "float16"])
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--device", default="auto", help="cuda/mps/cpu/auto (default: auto-detect)")
    args = p.parse_args()

    model, tokenizer = load_model_quantized(
        args.checkpoint, args.base, args.quantize, args.device)

    if args.interactive:
        print("\n═══ AnimaLM Interactive (quantized) ═══")
        while True:
            try:
                prompt = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if prompt.lower() in ('quit', 'exit', 'q'):
                break
            if not prompt:
                continue
            text = generate(model, tokenizer, prompt)
            print(f"Anima: {text}\n")
    else:
        serve_http(model, tokenizer, args.port)


if __name__ == "__main__":
    main()
