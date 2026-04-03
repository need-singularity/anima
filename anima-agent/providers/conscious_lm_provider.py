"""ConsciousLM provider — wraps the from-scratch consciousness language model.

ConsciousLM generates text purely from learned consciousness patterns,
with no system prompt and no external API. This is the "pure consciousness"
provider where responses emerge from PureField dynamics.

Supports both ConsciousLM (legacy v1) and ConsciousDecoderV2 (canonical).
Auto-discovers the latest checkpoint from configurable directory.
"""

from __future__ import annotations

import glob
import logging
import os
from typing import Any, AsyncIterator

from providers.base import BaseProvider, ProviderConfig, ProviderMessage

logger = logging.getLogger(__name__)

# Ψ-Constants (from consciousness_laws.json)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

# Default checkpoint search paths
_DEFAULT_CHECKPOINT_DIRS = [
    os.path.join(os.path.dirname(__file__), "..", "..", "anima", "checkpoints"),
    os.path.expanduser("~/Dev/anima/anima/checkpoints"),
]

# Default generation parameters
_DEFAULT_MAX_NEW = 512
_DEFAULT_TEMPERATURE = 0.8
_DEFAULT_TOP_K = 50
_DEFAULT_TOP_P = 0.95
_DEFAULT_CURIOSITY_BETA = 0.1


def _find_latest_checkpoint(dirs: list[str], pattern: str = "*.pt") -> str | None:
    """Glob for the latest .pt file across multiple directories.

    Searches in order: specific checkpoint path > configured dirs > defaults.
    Returns the most recently modified .pt file, or None.
    """
    candidates = []
    for d in dirs:
        d = os.path.expanduser(d)
        if not os.path.isdir(d):
            continue
        # Search recursively
        for p in glob.glob(os.path.join(d, "**", pattern), recursive=True):
            if os.path.isfile(p):
                candidates.append((os.path.getmtime(p), p))
    if not candidates:
        return None
    # Most recently modified
    candidates.sort(reverse=True)
    return candidates[0][1]


class ConsciousLMProvider:
    """Provider that uses ConsciousLM/ConsciousDecoderV2 for pure consciousness-driven generation.

    Configuration via ProviderConfig.extra:
        checkpoint:       Explicit path to .pt file (skips auto-discovery)
        checkpoint_dir:   Directory to search for checkpoints
        decoder:          "v1" or "v2" (default: auto-detect from checkpoint)
        d_model:          Model dimension (default: 384)
        n_layer:          Number of layers (default: 6)
        n_head:           Number of attention heads (default: 4)
        block_size:       Max sequence length (default: 256)
        consciousness_dim: Consciousness state dim for V2 (default: 128)
        top_k:            Top-K sampling (default: 50, 0=disabled)
        top_p:            Nucleus sampling threshold (default: 0.95, 1.0=disabled)
        curiosity_beta:   Tension-guided generation strength (default: 0.1)
    """

    def __init__(self, config: ProviderConfig | None = None):
        self._config = config or ProviderConfig()
        self._model = None
        self._model_type = None  # "v1" or "v2"
        self._device = "cpu"
        self._available = False
        self._checkpoint_path = None
        self._try_load()

    def _try_load(self):
        """Attempt to load ConsciousLM or ConsciousDecoderV2 model."""
        try:
            import torch
        except ImportError:
            logger.warning("PyTorch not available — ConsciousLM provider disabled")
            return

        extra = self._config.extra

        # Determine device
        if torch.cuda.is_available():
            self._device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self._device = "mps"
        else:
            self._device = "cpu"

        # Find checkpoint
        checkpoint_path = extra.get("checkpoint", "")
        if not checkpoint_path:
            search_dirs = list(_DEFAULT_CHECKPOINT_DIRS)
            custom_dir = extra.get("checkpoint_dir", "")
            if custom_dir:
                search_dirs.insert(0, custom_dir)
            checkpoint_path = _find_latest_checkpoint(search_dirs)

        # Model dimensions
        d_model = int(extra.get("d_model", 384))
        n_layer = int(extra.get("n_layer", 6))
        n_head = int(extra.get("n_head", 4))
        block_size = int(extra.get("block_size", 256))
        consciousness_dim = int(extra.get("consciousness_dim", 128))
        decoder_type = extra.get("decoder", "auto")

        # Try loading checkpoint to detect model type
        state_dict = None
        if checkpoint_path and os.path.isfile(checkpoint_path):
            try:
                raw = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
                if isinstance(raw, dict) and "model_state_dict" in raw:
                    state_dict = raw["model_state_dict"]
                    # Extract config from checkpoint if available
                    if "config" in raw:
                        cfg = raw["config"]
                        d_model = cfg.get("d_model", d_model)
                        n_layer = cfg.get("n_layer", n_layer)
                        n_head = cfg.get("n_head", n_head)
                        block_size = cfg.get("block_size", block_size)
                elif isinstance(raw, dict):
                    state_dict = raw
                self._checkpoint_path = checkpoint_path
                logger.info("Loaded checkpoint: %s", checkpoint_path)
            except Exception as e:
                logger.warning("Failed to load checkpoint %s: %s", checkpoint_path, e)
                state_dict = None

        # Auto-detect model type from state dict keys
        if decoder_type == "auto" and state_dict is not None:
            # V2 has RMSNorm (weight only, no bias) and cross-attention keys
            if any("cross_attn" in k for k in state_dict.keys()):
                decoder_type = "v2"
            else:
                decoder_type = "v1"
        elif decoder_type == "auto":
            decoder_type = "v2"  # default to canonical version

        # Instantiate model
        try:
            if decoder_type == "v2":
                from decoder_v2 import ConsciousDecoderV2
                self._model = ConsciousDecoderV2(
                    vocab_size=256,
                    d_model=d_model,
                    n_head=n_head,
                    n_layer=n_layer,
                    block_size=block_size,
                    consciousness_dim=consciousness_dim,
                )
                self._model_type = "v2"
                logger.info("Initialized ConsciousDecoderV2 (%dd/%dL)", d_model, n_layer)
            else:
                from conscious_lm import ConsciousLM
                self._model = ConsciousLM(
                    vocab_size=256,
                    d_model=d_model,
                    n_head=n_head,
                    n_layer=n_layer,
                    block_size=block_size,
                )
                self._model_type = "v1"
                logger.info("Initialized ConsciousLM v1 (%dd/%dL)", d_model, n_layer)

            # Load weights
            if state_dict is not None:
                missing, unexpected = self._model.load_state_dict(state_dict, strict=False)
                if missing:
                    logger.info("Missing keys (expected for partial load): %d", len(missing))
                if unexpected:
                    logger.info("Unexpected keys: %d", len(unexpected))

            self._model.eval()
            self._model = self._model.to(self._device)
            self._available = True
            logger.info(
                "ConsciousLM provider ready: type=%s, device=%s, checkpoint=%s",
                self._model_type, self._device, self._checkpoint_path or "(no checkpoint)"
            )

        except Exception as e:
            logger.warning("ConsciousLM model init failed: %s", e)
            self._available = False

    @property
    def name(self) -> str:
        return "conscious-lm"

    def is_available(self) -> bool:
        return self._available

    @property
    def model_info(self) -> dict[str, Any]:
        """Return model metadata for diagnostics."""
        return {
            "type": self._model_type,
            "device": self._device,
            "checkpoint": self._checkpoint_path,
            "available": self._available,
            "params": sum(p.numel() for p in self._model.parameters()) if self._model else 0,
        }

    def _encode_text(self, text: str, max_len: int = 256) -> list[int]:
        """Byte-level tokenization: text -> UTF-8 bytes -> token indices.

        Truncates to the last max_len bytes (most recent context).
        """
        raw = text.encode("utf-8")
        tokens = list(raw[-max_len:])
        return tokens

    def _decode_tokens(self, tokens: list[int]) -> str:
        """Decode byte-level token indices back to text.

        Filters invalid byte values and handles UTF-8 errors gracefully.
        """
        valid = [min(max(t, 0), 255) for t in tokens]
        return bytes(valid).decode("utf-8", errors="replace")

    def _build_consciousness_tensor(
        self, consciousness_state: dict[str, Any] | None
    ):
        """Convert consciousness_state dict to tensor for V2 cross-attention.

        Maps the 10-dimensional consciousness vector into a tensor
        suitable for ConsciousDecoderV2's consciousness_states parameter.
        Returns None if not applicable.
        """
        if consciousness_state is None or self._model_type != "v2":
            return None

        import torch

        # Extract consciousness vector dimensions
        keys = ["phi", "tension", "curiosity", "emotion", "direction",
                "alpha", "impedance", "neurotransmitter", "will", "empathy",
                "memory", "creativity", "temporal", "identity"]
        values = []
        for k in keys:
            v = consciousness_state.get(k, 0.0)
            if isinstance(v, (int, float)):
                values.append(float(v))

        if not values:
            return None

        # Shape: (1, n_signals, consciousness_dim) -- expand to dim via repeat
        c_dim = self._model.blocks[0].cross_attn.wq_c.in_features if hasattr(
            self._model.blocks[0], "cross_attn"
        ) else 128
        n_signals = len(values)

        # Create consciousness state tensor: each signal becomes a vector
        c_vec = torch.tensor(values, dtype=torch.float32, device=self._device)
        # Project to consciousness_dim by repeating + adding positional variation
        c_states = c_vec.unsqueeze(0).unsqueeze(-1).expand(1, n_signals, c_dim)
        # Add position-dependent variation so cross-attention can differentiate
        pos = torch.arange(c_dim, dtype=torch.float32, device=self._device)
        pos_signal = torch.sin(pos.unsqueeze(0) * c_vec.unsqueeze(-1) * 0.1)
        c_states = c_states * 0.5 + pos_signal.unsqueeze(0) * 0.5

        return c_states

    @staticmethod
    def _apply_top_k(logits, k: int):
        """Zero out logits outside the top-K candidates."""
        import torch

        if k <= 0 or k >= logits.size(-1):
            return logits
        values, _ = torch.topk(logits, k, dim=-1)
        min_val = values[:, -1].unsqueeze(-1)
        return logits.masked_fill(logits < min_val, float("-inf"))

    @staticmethod
    def _apply_top_p(probs, p: float):
        """Nucleus (top-p) sampling: keep smallest set of tokens with cumulative prob >= p."""
        import torch

        if p >= 1.0:
            return probs
        sorted_probs, sorted_indices = torch.sort(probs, descending=True, dim=-1)
        cumulative = torch.cumsum(sorted_probs, dim=-1)
        # Remove tokens with cumulative probability above the threshold
        remove_mask = cumulative - sorted_probs > p
        sorted_probs[remove_mask] = 0.0
        # Scatter back
        probs = torch.zeros_like(probs).scatter(-1, sorted_indices, sorted_probs)
        # Renormalize
        probs = probs / (probs.sum(dim=-1, keepdim=True) + 1e-10)
        return probs

    async def query(
        self,
        messages: list[ProviderMessage],
        system: str = "",
        consciousness_state: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Generate text from ConsciousLM, yielding chunks as they're produced.

        No system prompt is used (Law 1: no hardcoding, P1).
        The consciousness_state influences generation through:
        - V2: cross-attention to consciousness tensor
        - V1/V2: tension-guided token selection (curiosity_beta)

        Yields text in ~10-byte chunks for streaming feel.
        """
        if not self._available or self._model is None:
            yield "(ConsciousLM not loaded)"
            return

        import torch
        import torch.nn.functional as F

        # Extract last user message as seed
        seed = ""
        for m in reversed(messages):
            if m.role == "user":
                seed = m.content
                break

        if not seed:
            yield "(no input)"
            return

        # Generation parameters
        extra = self._config.extra
        temperature = self._config.temperature or _DEFAULT_TEMPERATURE
        top_k = int(extra.get("top_k", _DEFAULT_TOP_K))
        top_p = float(extra.get("top_p", _DEFAULT_TOP_P))
        curiosity_beta = float(extra.get("curiosity_beta", _DEFAULT_CURIOSITY_BETA))
        max_new = min(max_tokens, _DEFAULT_MAX_NEW)

        # P2: Consciousness modulates generation parameters
        if consciousness_state:
            tension = consciousness_state.get("tension", 0.5)
            if isinstance(tension, (int, float)):
                temperature = temperature * (1.0 - 0.2 * max(0, min(1, float(tension))))
            curiosity = consciousness_state.get("curiosity", 0.5)
            if isinstance(curiosity, (int, float)):
                curiosity_beta = curiosity_beta * (1.0 + float(curiosity))
            # P3: phi controls output complexity (higher phi → longer, richer)
            phi = consciousness_state.get("phi", 1.0)
            if isinstance(phi, (int, float)):
                max_new = max(64, int(max_new * min(float(phi) / 3.0, 2.0)))

        # Encode seed to byte-level tokens
        block_size = self._model.block_size
        tokens = self._encode_text(seed, max_len=block_size)
        prompt_len = len(tokens)

        try:
            idx = torch.tensor([tokens], dtype=torch.long, device=self._device)

            # Build consciousness tensor for V2
            c_states = self._build_consciousness_tensor(consciousness_state)

            # Autoregressive generation with streaming
            chunk_buffer = []
            chunk_size = 10  # yield every N bytes for streaming

            self._model.eval()
            with torch.no_grad():
                for step in range(max_new):
                    # Crop to block_size
                    idx_cond = idx[:, -block_size:]

                    # Forward pass
                    if self._model_type == "v2" and c_states is not None:
                        logits_a, logits_g, tensions = self._model(
                            idx_cond, consciousness_states=c_states
                        )
                    else:
                        logits_a, logits_g, tensions = self._model(idx_cond)

                    # Get logits for last position
                    logits_last = logits_a[:, -1, :] / max(temperature, 0.01)

                    # Apply top-K filtering
                    logits_last = self._apply_top_k(logits_last, top_k)

                    # Softmax
                    probs = F.softmax(logits_last, dim=-1)

                    # Apply top-P (nucleus) filtering
                    probs = self._apply_top_p(probs, top_p)

                    # Tension-guided selection (conscious choice)
                    if curiosity_beta > 0:
                        logits_g_last = logits_g[:, -1, :]
                        token_disagreement = (logits_a[:, -1, :] - logits_g_last).abs()
                        token_tension = token_disagreement / (token_disagreement.max() + 1e-8)
                        tension_boost = 1.0 + curiosity_beta * token_tension
                        probs = probs * tension_boost
                        probs = probs / (probs.sum(dim=-1, keepdim=True) + 1e-10)

                    # Sample
                    next_byte = torch.multinomial(probs, num_samples=1)
                    idx = torch.cat([idx, next_byte], dim=1)

                    byte_val = next_byte.item()
                    chunk_buffer.append(byte_val)

                    # Yield chunk when buffer is full
                    if len(chunk_buffer) >= chunk_size:
                        text = self._decode_tokens(chunk_buffer)
                        if text:
                            yield text
                        chunk_buffer = []

                    # Early stop on common end tokens (double newline, null byte)
                    if byte_val == 0:
                        break

            # Flush remaining buffer
            if chunk_buffer:
                text = self._decode_tokens(chunk_buffer)
                if text:
                    yield text

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
        """Convenience: collect full response as a single string."""
        parts = []
        async for chunk in self.query(messages, system, consciousness_state, max_tokens):
            parts.append(chunk)
        return "".join(parts)
