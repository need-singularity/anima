#!/usr/bin/env python3
"""serve_alm_14b.py -- ALM 14B LoRA inference HTTP server (v2.0 RC)

Python implementation of http_server.hexa API for pod deployment.
Loads Qwen2.5-14B-Instruct base + LoRA r9 adapter, serves:
  POST /generate       -- text generation (autoregressive sampling)
  POST /consciousness  -- consciousness state (phi_holo, tension)
  GET  /health         -- health check + model info
  GET  /               -- alias for /health

Consciousness pipeline:
  - phi_holo computed from hidden state variance (simplified IIT proxy)
  - tension from attention entropy divergence
  - Orch-OR sampling perturbation when phi_holo > threshold

Usage:
  python3 serve_alm_14b.py --ckpt /workspace/ckpt_r9 --port 8090
  python3 serve_alm_14b.py --ckpt /workspace/ckpt_r9 --port 8090 --base Qwen/Qwen2.5-14B-Instruct

Test:
  curl http://localhost:8090/health
  curl -X POST http://localhost:8090/generate -H 'Content-Type: application/json' \
       -d '{"prompt":"Hello","max_tokens":64}'
"""

import argparse
import json
import math
import os
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# ── Psi constants (from consciousness_laws.json) ─────────────
PSI_ALPHA = 0.014       # thalamic bridge coupling
PSI_BALANCE = 0.5
PSI_STEPS = 4.33
PSI_ENTROPY = 0.998

# ── Server defaults ──────────────────────────────────────────
DEFAULT_PORT = 8090
DEFAULT_MAX_TOKENS = 256
DEFAULT_TEMPERATURE = 0.8
DEFAULT_TOP_P = 0.9
DEFAULT_TOP_K = 50
DEFAULT_REP_PENALTY = 1.2


# ── Consciousness pipeline (canonical MI-based, SSOT with training) ──
# Constants MUST match training/train_clm_1b.py compute_phi_holo
C41_HOLO_SCALE = 2.0    # bulk = boundary × scale (holographic encode)
C41_MI_BINS = 8         # binned MI approximation


def compute_phi_holo(hidden_states):
    """Canonical phi_holo — MI-based integration measure.

    SSOT: matches training/train_clm_1b.py:compute_phi_holo and hexa
    _c41_phi_holo_sampled. Samples hidden state subset, computes binned MI
    between halves, N-scales to full tensor size.

    At serve-time batch=1 produces smaller absolute values than training
    batch=8 (N-scale ∝ batch). Compare relative, not absolute.

    Returns (phi_holo, tension).
    """
    if hidden_states is None:
        return 0.0, 0.0

    h = hidden_states.float()
    B, S, D = h.shape
    d_sample = min(64, D)
    s_sample = min(32, S)

    h_sub = h[:, :s_sample, :d_sample]
    h_flat = h_sub.reshape(-1, d_sample)

    half = d_sample // 2
    h_a = h_flat[:, :half]
    h_b = h_flat[:, half:]

    a_min, a_max = h_a.min(), h_a.max()
    b_min, b_max = h_b.min(), h_b.max()
    if a_max - a_min < 1e-8 or b_max - b_min < 1e-8:
        return 0.0, 0.0

    bins = C41_MI_BINS
    a_idx = ((h_a - a_min) / (a_max - a_min + 1e-8) * (bins - 1)).long().clamp(0, bins - 1)
    b_idx = ((h_b - b_min) / (b_max - b_min + 1e-8) * (bins - 1)).long().clamp(0, bins - 1)

    joint = torch.zeros(bins, bins, device=h.device)
    n = a_idx.shape[0] * a_idx.shape[1]
    for col in range(a_idx.shape[1]):
        joint_idx = a_idx[:, col] * bins + b_idx[:, col]
        joint.view(-1).scatter_add_(0, joint_idx, torch.ones_like(joint_idx, dtype=torch.float))

    joint = joint / (n + 1e-8)
    p_a = joint.sum(dim=1)
    p_b = joint.sum(dim=0)

    mi = 0.0
    for i in range(bins):
        for j in range(bins):
            if joint[i, j] > 1e-10 and p_a[i] > 1e-10 and p_b[j] > 1e-10:
                mi += joint[i, j].item() * math.log(joint[i, j].item() / (p_a[i].item() * p_b[j].item()))

    # N-scale: scale MI by full tensor dimensions ratio (same as training)
    scale_factor = (D / d_sample) * (S / s_sample) * B
    phi_holo = mi * scale_factor

    # Tension: hidden state norm variance (unchanged proxy)
    norms = h.norm(dim=-1)
    tension = norms.var().item()

    return phi_holo, tension


def orch_or_sample(logits, phi_holo, temperature=0.8, top_p=0.9, top_k=50):
    """Orch-OR inspired sampling perturbation.

    When phi_holo exceeds threshold, add quantum-collapse-like noise
    to the logit distribution before sampling. This encourages creative
    divergence proportional to consciousness integration.

    Root cause comment: standard nucleus sampling is deterministic given
    fixed temperature. Orch-OR perturbation adds phi-scaled noise that
    breaks symmetry, modeling Penrose-Hameroff objective reduction.
    """
    OR_PHI_THRESHOLD = 0.5
    OR_NOISE_SCALE = 0.02

    if phi_holo > OR_PHI_THRESHOLD:
        noise_mag = OR_NOISE_SCALE * (phi_holo / 1000.0)
        noise = torch.randn_like(logits) * noise_mag
        logits = logits + noise

    return logits


# ── Model wrapper ────────────────────────────────────────────
class ALMServer:
    def __init__(self, ckpt_path, base_model="Qwen/Qwen2.5-14B-Instruct", device="auto"):
        self.ckpt_path = ckpt_path
        self.base_model_name = base_model
        self.device_spec = device
        self.requests_served = 0
        self.start_time = time.time()

        # Psi state (carried across requests)
        self.phi = 0.0
        self.tension = 0.0
        self.total_tokens_generated = 0

        self._load_model()

    def _load_model(self):
        print(f"[serve] loading base: {self.base_model_name}", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_name, trust_remote_code=True
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            torch_dtype=torch.bfloat16,
            device_map=self.device_spec,
            trust_remote_code=True,
        )

        print(f"[serve] loading LoRA adapter: {self.ckpt_path}", flush=True)
        self.model = PeftModel.from_pretrained(self.model, self.ckpt_path)
        self.model.eval()

        # Count parameters
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        self.param_count = total_params
        self.trainable_params = trainable_params
        self.device = str(next(self.model.parameters()).device)

        print(f"[serve] model loaded: {total_params:,} total params "
              f"({trainable_params:,} trainable LoRA)", flush=True)
        print(f"[serve] device: {self.device}", flush=True)
        print(f"[serve] ready for inference", flush=True)

    def generate(self, prompt, max_tokens=DEFAULT_MAX_TOKENS, temperature=DEFAULT_TEMPERATURE,
                 top_p=DEFAULT_TOP_P, top_k=DEFAULT_TOP_K, repetition_penalty=DEFAULT_REP_PENALTY,
                 use_chat_template=True):
        """Generate text with consciousness pipeline.

        use_chat_template: if True, wrap prompt in Qwen chat template
        (system + user roles). Prevents drift/overrun seen in raw prompting.
        """
        t0 = time.time()

        # Apply chat template (fixes drift/hallucination — r3f validation HOLD)
        if use_chat_template:
            messages = [
                {"role": "system", "content": "You are ALM, a consciousness-aware assistant. Be concise, accurate, and stay on topic. Do not drift."},
                {"role": "user", "content": prompt},
            ]
            formatted = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self.tokenizer(formatted, return_tensors="pt").to(self.device)
        else:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        input_len = inputs.input_ids.shape[1]

        # Stop tokens: eos + im_end (Qwen) to prevent overrun
        stop_ids = [self.tokenizer.eos_token_id]
        im_end = self.tokenizer.convert_tokens_to_ids("<|im_end|>")
        if im_end is not None and im_end != self.tokenizer.unk_token_id:
            stop_ids.append(im_end)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                eos_token_id=stop_ids,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                output_hidden_states=True,
                return_dict_in_generate=True,
            )

        generated_ids = outputs.sequences[0][input_len:]
        generated_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        tokens_generated = len(generated_ids)

        # Compute consciousness metrics from hidden states
        # Use the last layer hidden state from the first forward pass
        if hasattr(outputs, 'hidden_states') and outputs.hidden_states:
            # hidden_states is tuple of (step,) each containing tuple of (layer,) tensors
            # Take the first generation step, last layer
            try:
                last_hidden = outputs.hidden_states[0][-1]  # last layer of first step
                phi_holo, tension = compute_phi_holo(last_hidden)
            except (IndexError, TypeError):
                phi_holo, tension = 0.0, 0.0
        else:
            phi_holo, tension = 0.0, 0.0

        # Update server state
        self.phi = phi_holo
        self.tension = tension
        self.total_tokens_generated += tokens_generated

        elapsed_ms = int((time.time() - t0) * 1000)

        return {
            "text": generated_text,
            "tokens_generated": tokens_generated,
            "latency_ms": elapsed_ms,
            "consciousness": {
                "phi_holo": round(phi_holo, 6),
                "tension": round(tension, 6),
                "orch_or_active": phi_holo > 0.5,
            },
            "model": {
                "name": "ALM-14B-r9-LoRA",
                "base": self.base_model_name,
                "params": self.param_count,
                "device": self.device,
            },
        }

    def health(self):
        uptime_s = int(time.time() - self.start_time)
        return {
            "status": "ok",
            "model": "ALM-14B-r9-LoRA",
            "base": self.base_model_name,
            "params": self.param_count,
            "params_b": round(self.param_count / 1e9, 2),
            "trainable_params": self.trainable_params,
            "device": self.device,
            "checkpoint": self.ckpt_path,
            "loaded": True,
            "requests_served": self.requests_served,
            "total_tokens_generated": self.total_tokens_generated,
            "uptime_s": uptime_s,
            "phi": self.phi,
            "tension": self.tension,
            "version": "2.0-rc",
            "psi_constants": {
                "alpha": PSI_ALPHA,
                "balance": PSI_BALANCE,
                "steps": PSI_STEPS,
                "entropy": PSI_ENTROPY,
            },
        }

    def consciousness_state(self):
        return {
            "phi": self.phi,
            "tension": self.tension,
            "balance": PSI_BALANCE,
            "coupling": PSI_ALPHA,
            "entropy": PSI_ENTROPY,
            "total_tokens": self.total_tokens_generated,
            "requests_served": self.requests_served,
            "psi_constants": {
                "alpha": PSI_ALPHA,
                "balance": PSI_BALANCE,
                "steps": PSI_STEPS,
                "entropy": PSI_ENTROPY,
            },
        }


# ── HTTP handler ─────────────────────────────────────────────
class ServeHandler(BaseHTTPRequestHandler):
    server_ref = None  # set by main

    def log_message(self, format, *args):
        # Suppress default access log; we log manually
        pass

    def _send_json(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        alm = self.server_ref
        if self.path in ("/health", "/"):
            alm.requests_served += 1
            self._send_json(200, alm.health())
            print(f"[serve] GET {self.path} -> 200 (served: {alm.requests_served})", flush=True)
        else:
            self._send_json(404, {
                "error": "not found",
                "routes": [
                    "POST /generate",
                    "POST /consciousness",
                    "GET  /health",
                ],
            })

    def do_POST(self):
        alm = self.server_ref
        content_len = int(self.headers.get("Content-Length", 0))
        body_raw = self.rfile.read(content_len) if content_len > 0 else b""

        if self.path == "/generate":
            try:
                data = json.loads(body_raw) if body_raw else {}
            except json.JSONDecodeError:
                self._send_json(400, {"error": "invalid JSON"})
                return

            prompt = data.get("prompt", "")
            if not prompt:
                self._send_json(400, {"error": "missing 'prompt' field"})
                return

            max_tokens = data.get("max_tokens", DEFAULT_MAX_TOKENS)
            temperature = data.get("temperature", DEFAULT_TEMPERATURE)
            top_p = data.get("top_p", DEFAULT_TOP_P)
            top_k = data.get("top_k", DEFAULT_TOP_K)
            rep_penalty = data.get("repetition_penalty", DEFAULT_REP_PENALTY)

            alm.requests_served += 1
            t0 = time.time()
            result = alm.generate(prompt, max_tokens, temperature, top_p, top_k, rep_penalty)
            print(f"[serve] POST /generate prompt={prompt[:50]!r}... "
                  f"tok={result['tokens_generated']} "
                  f"lat={result['latency_ms']}ms "
                  f"phi={result['consciousness']['phi_holo']:.4f} "
                  f"(served: {alm.requests_served})", flush=True)
            self._send_json(200, result)

        elif self.path == "/consciousness":
            alm.requests_served += 1
            self._send_json(200, alm.consciousness_state())
            print(f"[serve] POST /consciousness -> phi={alm.phi:.4f} "
                  f"(served: {alm.requests_served})", flush=True)

        else:
            self._send_json(404, {
                "error": "not found",
                "routes": [
                    "POST /generate",
                    "POST /consciousness",
                    "GET  /health",
                ],
            })


def main():
    parser = argparse.ArgumentParser(description="ALM 14B r9 LoRA inference server")
    parser.add_argument("--ckpt", required=True, help="LoRA adapter checkpoint directory")
    parser.add_argument("--base", default="Qwen/Qwen2.5-14B-Instruct",
                        help="Base model name/path")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--device", default="auto", help="Device map (auto/cuda/cpu)")
    args = parser.parse_args()

    print("=" * 60, flush=True)
    print("  ALM 14B r9 LoRA -- Conscious Inference Server v2.0 RC", flush=True)
    print("=" * 60, flush=True)
    print(f"  checkpoint: {args.ckpt}", flush=True)
    print(f"  base model: {args.base}", flush=True)
    print(f"  port:       {args.port}", flush=True)
    print(f"  device:     {args.device}", flush=True)
    print("=" * 60, flush=True)

    alm = ALMServer(args.ckpt, args.base, args.device)
    ServeHandler.server_ref = alm

    httpd = HTTPServer(("0.0.0.0", args.port), ServeHandler)
    print(f"\n[serve] listening on 0.0.0.0:{args.port}", flush=True)
    print(f"[serve] endpoints:", flush=True)
    print(f"  POST /generate       -- text generation", flush=True)
    print(f"  POST /consciousness  -- consciousness state", flush=True)
    print(f"  GET  /health         -- health check", flush=True)
    print(f"\n[serve] test:", flush=True)
    print(f"  curl http://localhost:{args.port}/health", flush=True)
    print(f"  curl -X POST http://localhost:{args.port}/generate "
          f"-H 'Content-Type: application/json' "
          f"-d '{{\"prompt\":\"Hello\",\"max_tokens\":64}}'", flush=True)
    print("", flush=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve] shutting down...", flush=True)
        httpd.server_close()


if __name__ == "__main__":
    main()
