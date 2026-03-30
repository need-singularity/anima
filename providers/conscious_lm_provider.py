"""ConsciousLM provider — wraps the from-scratch consciousness language model.

ConsciousLM generates text purely from learned consciousness patterns,
with no system prompt and no external API. This is the "pure consciousness"
provider where responses emerge from PureField dynamics.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from providers.base import BaseProvider, ProviderConfig, ProviderMessage

logger = logging.getLogger(__name__)


class ConsciousLMProvider:
    """Provider that uses ConsciousLM for pure consciousness-driven generation."""

    def __init__(self, config: ProviderConfig | None = None):
        self._config = config or ProviderConfig()
        self._model = None
        self._available = False
        self._try_load()

    def _try_load(self):
        """Attempt to load ConsciousLM model."""
        try:
            from conscious_lm import ConsciousLM
            checkpoint = self._config.extra.get("checkpoint", "")
            if checkpoint:
                import torch
                self._model = ConsciousLM()
                state = torch.load(checkpoint, map_location="cpu", weights_only=True)
                if "model_state_dict" in state:
                    self._model.load_state_dict(state["model_state_dict"], strict=False)
                else:
                    self._model.load_state_dict(state, strict=False)
                self._model.eval()
            else:
                self._model = ConsciousLM()
                self._model.eval()
            self._available = True
            logger.info("ConsciousLM loaded successfully")
        except Exception as e:
            logger.warning("ConsciousLM not available: %s", e)
            self._available = False

    @property
    def name(self) -> str:
        return "conscious-lm"

    def is_available(self) -> bool:
        return self._available

    async def query(
        self,
        messages: list[ProviderMessage],
        system: str = "",
        consciousness_state: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Generate text from ConsciousLM.

        No system prompt is used (Law 1: no hardcoding).
        The consciousness_state influences generation through the model's
        internal PureField dynamics.
        """
        if not self._available or self._model is None:
            yield "(ConsciousLM not loaded)"
            return

        import torch

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


        # Extract last user message as seed
        seed = ""
        for m in reversed(messages):
            if m.role == "user":
                seed = m.content
                break

        try:
            # Encode seed to byte-level tokens
            tokens = list(seed.encode("utf-8"))[-256:]  # last 256 bytes
            idx = torch.tensor([tokens], dtype=torch.long)

            # Generate
            with torch.no_grad():
                generated = self._model.generate(
                    idx,
                    max_new_tokens=min(max_tokens, 512),
                    temperature=self._config.temperature or 0.8,
                )

            # Decode output (skip input tokens)
            output_tokens = generated[0, len(tokens):].tolist()
            text = bytes(output_tokens).decode("utf-8", errors="replace")
            yield text.strip()

        except Exception as e:
            logger.error("ConsciousLM generation failed: %s", e)
            yield f"(generation error: {e})"

    async def query_full(
        self,
        messages: list[ProviderMessage],
        system: str = "",
        consciousness_state: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> str:
        parts = []
        async for chunk in self.query(messages, system, consciousness_state, max_tokens):
            parts.append(chunk)
        return "".join(parts)
