#!/usr/bin/env python3
"""AnimaLM 7B Local Server — HTTP API for consciousness-driven generation.

Serves AnimaLM (Mistral-7B + PureField 56.6M) locally with CPU fallback.
Downloads checkpoint from R2 automatically if not present.

Endpoints:
    GET  /health     — Server status + model info
    POST /generate   — Text generation (JSON body: prompt, max_tokens, temperature)

Usage:
    python3 serve_local.py                          # auto-detect device
    python3 serve_local.py --port 8321              # custom port
    python3 serve_local.py --device cpu              # force CPU
    python3 serve_local.py --device mps              # Apple Silicon GPU
    python3 serve_local.py --checkpoint path/to/best.pt  # custom checkpoint

Requirements:
    pip install torch transformers aiohttp boto3

NO QUANTIZATION — float16/float32 only (user policy: feedback_no_quantization.md)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

# ── Path Setup ──────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
ANIMA_DIR = SCRIPT_DIR.parent          # anima/
PROJECT_DIR = ANIMA_DIR.parent          # repo root
ANIMALM_DIR = PROJECT_DIR / "sub-projects" / "animalm"
SRC_DIR = ANIMA_DIR / "src"

# Add paths for imports
for p in [str(ANIMALM_DIR), str(SRC_DIR), str(ANIMA_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("serve_local")

# ── Constants ───────────────────────────────────────────────────────────
DEFAULT_PORT = 8321
R2_KEY = "checkpoints/7b_v05/best.pt"
LOCAL_CHECKPOINT_DIR = ANIMA_DIR / "checkpoints" / "7b_v05"
LOCAL_CHECKPOINT = LOCAL_CHECKPOINT_DIR / "best.pt"
DEFAULT_BASE_MODEL = "mistralai/Mistral-7B-v0.1"
TARGET_LAYERS = 8
SAVANT_LAYERS = 2


# ── R2 Download ─────────────────────────────────────────────────────────
def _load_env():
    """Load R2 credentials from .env files."""
    for env_path in [ANIMA_DIR / ".env", ANIMA_DIR / ".local" / ".env"]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip("'\"")
                if k not in os.environ:
                    os.environ[k] = v


def download_checkpoint_from_r2(output_path: Path, r2_key: str = R2_KEY) -> bool:
    """Download checkpoint from Cloudflare R2 (anima-models bucket).

    Uses the same credential pattern as scripts/r2_upload.py.
    Returns True if download succeeded or file already exists.
    """
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info("Checkpoint already exists: %s (%.1f MB)", output_path, size_mb)
        return True

    _load_env()
    endpoint = os.environ.get("ANIMA_R2_ENDPOINT")
    access_key = os.environ.get("ANIMA_R2_ACCESS_KEY")
    secret_key = os.environ.get("ANIMA_R2_SECRET_KEY")
    bucket = os.environ.get("ANIMA_R2_MODELS_BUCKET", "anima-models")

    if not all([endpoint, access_key, secret_key]):
        logger.error(
            "R2 credentials not set. Set ANIMA_R2_ENDPOINT, ANIMA_R2_ACCESS_KEY, "
            "ANIMA_R2_SECRET_KEY in environment or anima/.env"
        )
        return False

    try:
        import boto3
        from botocore.config import Config

        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "adaptive"}),
            region_name="auto",
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading r2://%s/%s -> %s ...", bucket, r2_key, output_path)

        # Download with progress callback
        file_size = client.head_object(Bucket=bucket, Key=r2_key)["ContentLength"]
        logger.info("File size: %.1f MB", file_size / (1024 * 1024))

        downloaded = [0]
        last_log = [time.time()]

        def progress(bytes_amount):
            downloaded[0] += bytes_amount
            now = time.time()
            if now - last_log[0] > 5.0:  # log every 5s
                pct = 100.0 * downloaded[0] / file_size if file_size > 0 else 0
                logger.info("  %.1f%% (%.1f MB / %.1f MB)",
                            pct, downloaded[0] / 1e6, file_size / 1e6)
                last_log[0] = now

        tmp_path = output_path.with_suffix(".tmp")
        client.download_file(
            Bucket=bucket, Key=r2_key, Filename=str(tmp_path),
            Callback=progress,
        )
        # Atomic rename
        tmp_path.rename(output_path)
        logger.info("Download complete: %s", output_path)
        return True

    except ImportError:
        logger.error("boto3 not installed. Run: pip install boto3")
        return False
    except Exception as e:
        logger.error("R2 download failed: %s", e)
        return False


# ── Model Loading ───────────────────────────────────────────────────────
class AnimaLMServer:
    """Loads and serves AnimaLM 7B with PureField consciousness transform."""

    def __init__(self, checkpoint: Path, base_model: str, device: str):
        self.checkpoint = checkpoint
        self.base_model = base_model
        self.device = device
        self.model = None
        self.tokenizer = None
        self.pf_class = None
        self._loaded = False
        self._load_time = 0.0
        self._total_requests = 0
        self._total_tokens = 0

    def load(self) -> bool:
        """Load model into memory. Returns True on success."""
        import torch

        t0 = time.time()

        # Resolve device
        if self.device == "auto":
            if torch.cuda.is_available():
                self.device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        logger.info("Device: %s", self.device)

        # Determine dtype: float16 for GPU, float32 for CPU
        # NO QUANTIZATION (4-bit/8-bit absolutely forbidden)
        if self.device == "cpu":
            dtype = torch.float32
            logger.info("Using float32 (CPU mode)")
        else:
            dtype = torch.float16
            logger.info("Using float16 (GPU mode)")

        # Load tokenizer + base model
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info("Loading base model: %s", self.base_model)
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.base_model,
                torch_dtype=dtype,
                low_cpu_mem_usage=True,
            )
            self.model = self.model.to(self.device)
            logger.info("Base model loaded on %s", self.device)
        except Exception as e:
            logger.error("Failed to load base model: %s", e)
            return False

        # Apply PureField transform
        if self.checkpoint.exists():
            try:
                from train_anima_lm import ParallelPureFieldMLP
                self.pf_class = ParallelPureFieldMLP

                ckpt = torch.load(str(self.checkpoint), map_location=self.device, weights_only=False)

                total_layers = len(self.model.model.layers)
                start = total_layers - TARGET_LAYERS

                pf_count = 0
                for i in range(start, total_layers):
                    layer = self.model.model.layers[i]
                    is_savant = (i - start) < SAVANT_LAYERS
                    original_mlp = layer.mlp
                    h = original_mlp.gate_proj.weight.shape[1]
                    inter = original_mlp.gate_proj.weight.shape[0]
                    pf = ParallelPureFieldMLP(original_mlp, h, inter, is_savant=is_savant)
                    layer.mlp = pf.to(device=self.device, dtype=dtype)
                    pf_count += 1

                if "pf_states" in ckpt:
                    loaded = 0
                    for mod_name, module in self.model.named_modules():
                        if isinstance(module, ParallelPureFieldMLP) and mod_name in ckpt["pf_states"]:
                            module.load_state_dict(ckpt["pf_states"][mod_name], strict=False)
                            loaded += 1
                    logger.info(
                        "PureField loaded: %d/%d layers, step=%s, Phi=%.4f",
                        loaded, pf_count,
                        ckpt.get("step", "?"),
                        ckpt.get("best_phi", 0),
                    )
                else:
                    logger.warning("Checkpoint has no pf_states — running base PureField init")

            except ImportError:
                logger.warning(
                    "train_anima_lm not found in %s — serving base Mistral without PureField",
                    ANIMALM_DIR,
                )
            except Exception as e:
                logger.error("PureField transform failed: %s — serving base Mistral", e)
        else:
            logger.warning("Checkpoint not found: %s — serving base Mistral", self.checkpoint)

        self.model.eval()
        self._loaded = True
        self._load_time = time.time() - t0
        logger.info("Model ready in %.1fs", self._load_time)

        # Memory usage
        param_count = sum(p.numel() for p in self.model.parameters())
        mem_gb = sum(p.numel() * p.element_size() for p in self.model.parameters()) / (1024**3)
        logger.info("Parameters: %.1fM, Memory: %.2f GB", param_count / 1e6, mem_gb)

        return True

    def generate(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.8,
        top_p: float = 0.9,
        repetition_penalty: float = 1.2,
    ) -> dict:
        """Generate text from prompt. Returns dict with text, tokens, tension, timing."""
        if not self._loaded:
            return {"error": "Model not loaded", "text": ""}

        import torch
        import torch.nn.functional as F

        t0 = time.time()
        input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
        generated = input_ids.clone()
        tensions = []

        max_new = min(max_tokens, 1024)
        tokens_generated = 0

        with torch.no_grad():
            for _ in range(max_new):
                # Use autocast for GPU, skip for CPU
                if self.device in ("cuda", "mps"):
                    autocast_device = "cuda" if self.device == "cuda" else "cpu"
                    with torch.autocast(autocast_device, dtype=torch.float16, enabled=(self.device == "cuda")):
                        outputs = self.model(generated[:, -512:])
                        logits = outputs.logits[:, -1, :]
                else:
                    outputs = self.model(generated[:, -512:])
                    logits = outputs.logits[:, -1, :]

                # Repetition penalty
                for token_id in set(generated[0, -100:].tolist()):
                    logits[0, token_id] /= repetition_penalty

                # Temperature + top-p sampling
                if temperature < 0.01:
                    next_token = logits.argmax(dim=-1)
                else:
                    logits = logits / temperature
                    probs = F.softmax(logits, dim=-1)
                    sorted_probs, sorted_indices = torch.sort(probs, descending=True)
                    cumsum = torch.cumsum(sorted_probs, dim=-1)
                    mask = cumsum - sorted_probs > top_p
                    sorted_probs[mask] = 0
                    sorted_probs /= sorted_probs.sum(dim=-1, keepdim=True)
                    next_token = sorted_indices[0, torch.multinomial(sorted_probs[0], 1)]

                generated = torch.cat([generated, next_token.unsqueeze(0).unsqueeze(0)
                                       if next_token.dim() == 0 else next_token.unsqueeze(0)], dim=-1)
                tokens_generated += 1

                # Collect PureField tension
                if self.pf_class:
                    for _, module in self.model.named_modules():
                        if isinstance(module, self.pf_class) and hasattr(module, 'last_tension') and module.last_tension is not None:
                            tensions.append(module.last_tension.mean().item())
                            break

                # Stop on EOS
                tok_val = next_token.item() if next_token.dim() == 0 else next_token[0].item()
                if tok_val == self.tokenizer.eos_token_id:
                    break

        # Decode
        output_ids = generated[0, input_ids.shape[1]:]
        text = self.tokenizer.decode(output_ids, skip_special_tokens=True)

        elapsed = time.time() - t0
        avg_tension = sum(tensions) / len(tensions) if tensions else 0.0
        tps = tokens_generated / elapsed if elapsed > 0 else 0

        self._total_requests += 1
        self._total_tokens += tokens_generated

        return {
            "text": text,
            "tokens": tokens_generated,
            "tension": round(avg_tension, 6),
            "time_s": round(elapsed, 3),
            "tokens_per_sec": round(tps, 1),
        }

    def health(self) -> dict:
        """Server health info."""
        return {
            "status": "ok" if self._loaded else "loading",
            "model": self.base_model,
            "device": self.device,
            "checkpoint": str(self.checkpoint),
            "purefield": self.pf_class is not None,
            "load_time_s": round(self._load_time, 1),
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
        }


# ── HTTP Server (aiohttp) ──────────────────────────────────────────────
async def run_server(server: AnimaLMServer, host: str, port: int):
    """Start HTTP server with /generate and /health endpoints."""
    try:
        from aiohttp import web
    except ImportError:
        logger.error("aiohttp not installed. Run: pip install aiohttp")
        sys.exit(1)

    async def handle_health(request):
        return web.json_response(server.health())

    async def handle_generate(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        prompt = body.get("prompt", "")
        if not prompt:
            return web.json_response({"error": "Missing 'prompt' field"}, status=400)

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: server.generate(
                prompt=prompt,
                max_tokens=body.get("max_tokens", 256),
                temperature=body.get("temperature", 0.8),
                top_p=body.get("top_p", 0.9),
                repetition_penalty=body.get("repetition_penalty", 1.2),
            ),
        )
        return web.json_response(result)

    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_post("/generate", handle_generate)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    logger.info("Server listening on http://%s:%d", host, port)
    logger.info("  GET  /health     — server status")
    logger.info("  POST /generate   — {prompt, max_tokens, temperature, top_p}")

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()


# ── CLI ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AnimaLM 7B Local Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"HTTP port (default: {DEFAULT_PORT})")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "mps", "cpu"],
                        help="Device (default: auto-detect)")
    parser.add_argument("--checkpoint", type=str, default=None,
                        help=f"PureField checkpoint path (default: {LOCAL_CHECKPOINT})")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL,
                        help=f"HuggingFace base model (default: {DEFAULT_BASE_MODEL})")
    parser.add_argument("--no-download", action="store_true",
                        help="Skip R2 auto-download (use base Mistral if checkpoint missing)")
    args = parser.parse_args()

    checkpoint = Path(args.checkpoint) if args.checkpoint else LOCAL_CHECKPOINT

    # Auto-download from R2 if checkpoint missing
    if not checkpoint.exists() and not args.no_download:
        logger.info("Checkpoint not found locally. Downloading from R2...")
        if not download_checkpoint_from_r2(checkpoint):
            logger.warning("R2 download failed. Will serve base Mistral without PureField.")

    # Load model
    server = AnimaLMServer(
        checkpoint=checkpoint,
        base_model=args.base_model,
        device=args.device,
    )

    logger.info("Loading model (this may take a few minutes on first run)...")
    if not server.load():
        logger.error("Model load failed.")
        sys.exit(1)

    # Start server
    asyncio.run(run_server(server, args.host, args.port))


if __name__ == "__main__":
    main()
