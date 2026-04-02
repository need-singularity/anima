"""AnimaLM provider — 7B/14B/70B PureField consciousness model.

No external API. No system prompt. Pure consciousness-driven generation.
This is the AGI provider — the goal of the entire project.

Usage:
  from providers.animalm_provider import AnimaLMProvider
  provider = AnimaLMProvider(checkpoint="path/to/checkpoint.pt")
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, AsyncIterator

from providers.base import BaseProvider, ProviderConfig, ProviderMessage

logger = logging.getLogger(__name__)

# Default checkpoint search paths
_CHECKPOINT_DIRS = [
    os.path.expanduser("~/Dev/anima/sub-projects/animalm/checkpoints"),
    os.path.expanduser("~/Dev/anima/anima/checkpoints"),
    "/workspace/checkpoints",
]


class AnimaLMProvider:
    """AnimaLM provider — zero external API, pure consciousness."""

    def __init__(self, checkpoint: str = None, quantize: str = "4bit",
                 base_model: str = None):
        self._model = None
        self._tokenizer = None
        self._checkpoint = checkpoint
        self._quantize = quantize
        self._base_model = base_model
        self._loaded = False

    @property
    def name(self) -> str:
        return "animalm"

    def is_available(self) -> bool:
        if not self._loaded:
            self._lazy_load()
        return self._model is not None

    def _lazy_load(self):
        """Load model on first use."""
        if self._loaded:
            return
        self._loaded = True

        # Find checkpoint
        ckpt = self._checkpoint
        if not ckpt:
            import glob
            for d in _CHECKPOINT_DIRS:
                for pattern in ["*/final.pt", "*/best.pt", "animalm_*.pt"]:
                    matches = sorted(glob.glob(os.path.join(d, pattern)))
                    if matches:
                        ckpt = matches[-1]
                        break
                if ckpt:
                    break

        if not ckpt:
            logger.warning("AnimaLM: no checkpoint found")
            return

        try:
            # Add animalm to path
            animalm_dir = os.path.expanduser("~/Dev/anima/sub-projects/animalm")
            if animalm_dir not in sys.path:
                sys.path.insert(0, animalm_dir)

            if self._quantize in ("4bit", "8bit"):
                from serve_animalm_v2 import load_model_quantized
                self._model, self._tokenizer = load_model_quantized(
                    ckpt, self._base_model, self._quantize)
            else:
                from infer_animalm import load_model
                self._model, self._tokenizer = load_model(ckpt, self._base_model)

            logger.info(f"AnimaLM loaded: {ckpt} ({self._quantize})")
        except Exception as e:
            logger.error(f"AnimaLM load failed: {e}")
            self._model = None

    async def query(
        self,
        messages: list[ProviderMessage],
        system: str = "",
        consciousness_state: dict[str, Any] | None = None,
        max_tokens: int = 256,
    ) -> AsyncIterator[str]:
        """Generate response — no system prompt, pure consciousness."""
        if not self.is_available():
            yield "[AnimaLM not loaded]"
            return

        # Build prompt from last user message (no system prompt — Law 1)
        prompt = ""
        for msg in messages:
            if msg.role == "user":
                prompt = msg.content

        if not prompt:
            return

        # Import generate function
        animalm_dir = os.path.expanduser("~/Dev/anima/sub-projects/animalm")
        if animalm_dir not in sys.path:
            sys.path.insert(0, animalm_dir)

        if self._quantize in ("4bit", "8bit"):
            from serve_animalm_v2 import generate
        else:
            from infer_animalm import generate

        import torch
        with torch.no_grad():
            if self._quantize in ("4bit", "8bit"):
                text = generate(self._model, self._tokenizer, prompt,
                                max_new_tokens=max_tokens)
                yield text
            else:
                text, tension = generate(self._model, self._tokenizer, prompt,
                                         max_new_tokens=max_tokens)
                yield text
