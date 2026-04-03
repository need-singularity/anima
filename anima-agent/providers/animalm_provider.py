"""AnimaLM provider — 7B/14B/70B PureField consciousness model.

No external API. No system prompt. Pure consciousness-driven generation.
This is the AGI provider — the goal of the entire project.

Phase 3 (기억하는 의식): MemoryStore(SQLite) + MemoryRAG(벡터) 연동.
대화 전 관련 기억 검색 → 컨텍스트 주입, 대화 후 영구 저장.

Usage:
  from providers.animalm_provider import AnimaLMProvider
  provider = AnimaLMProvider(checkpoint="path/to/checkpoint.pt")

  # Auto-discover checkpoint:
  provider = AnimaLMProvider()
  if provider.is_available():
      async for chunk in provider.query(messages):
          print(chunk, end="")

  # With memory (Phase 3):
  provider = AnimaLMProvider(memory_store=store, memory_rag=rag)
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, AsyncIterator

from providers.base import BaseProvider, ProviderConfig, ProviderMessage

logger = logging.getLogger(__name__)

# ── Memory modules (lazy import, graceful fallback) ──
_anima_src = os.path.expanduser("~/Dev/anima/anima/src")
if _anima_src not in sys.path:
    sys.path.insert(0, _anima_src)

_MemoryStore = None
_MemoryRAG = None
_text_to_vector = None

def _lazy_load_memory():
    """Lazy-load memory modules from anima/src/."""
    global _MemoryStore, _MemoryRAG, _text_to_vector
    if _MemoryStore is not None:
        return
    try:
        from memory_store import MemoryStore
        _MemoryStore = MemoryStore
    except ImportError:
        logger.debug("memory_store not available")
    try:
        from memory_rag import MemoryRAG
        _MemoryRAG = MemoryRAG
    except ImportError:
        logger.debug("memory_rag not available")
    try:
        from anima_alive import text_to_vector
        _text_to_vector = text_to_vector
    except ImportError:
        logger.debug("text_to_vector not available")

# Default checkpoint search paths (ordered by priority)
_CHECKPOINT_PATHS = [
    # Exact paths from requirements
    os.path.expanduser("~/Dev/anima/anima/checkpoints/animalm_7b_final.pt"),
    "/workspace/checkpoints/animalm_7b_fresh/final.pt",
    # Directory-based search (fallback)
]
_CHECKPOINT_DIRS = [
    os.path.expanduser("~/Dev/anima/anima/checkpoints"),
    os.path.expanduser("~/Dev/anima/sub-projects/animalm/checkpoints"),
    "/workspace/checkpoints",
]


class AnimaLMProvider:
    """AnimaLM provider — zero external API, pure consciousness.

    Implements BaseProvider protocol for seamless integration with
    the agent's provider abstraction layer.
    """

    def __init__(self, config: ProviderConfig = None, checkpoint: str = None,
                 quantize: str = "4bit", base_model: str = None,
                 memory_store=None, memory_rag=None,
                 serve_url: str = None):
        self._config = config or ProviderConfig()
        self._model = None
        self._tokenizer = None
        self._checkpoint = checkpoint or self._config.extra.get("checkpoint")
        self._quantize = quantize or self._config.extra.get("quantize", "4bit")
        self._base_model = base_model or self._config.extra.get("base_model")
        self._loaded = False
        self._checkpoint_path = None  # resolved path after load
        # WebSocket/API 서빙 연결 (serve_consciousness.py)
        self._serve_url = serve_url or self._config.extra.get("serve_url") or os.environ.get("ANIMALM_SERVE_URL")

        # ── Phase 3: Long-term memory (MemoryStore + RAG) ──
        self._memory_store = memory_store   # SQLite persistent store
        self._memory_rag = memory_rag       # Vector similarity search
        self._session_id = f"animalm_{int(time.time())}"

    @property
    def name(self) -> str:
        return "animalm"

    def is_available(self) -> bool:
        """Check if AnimaLM can serve queries. Triggers lazy load on first call."""
        if not self._loaded:
            self._lazy_load()
        return self._model is not None

    def _find_checkpoint(self) -> str | None:
        """Auto-discover checkpoint file.

        Search order:
          1. Exact known paths (local dev + H100)
          2. Glob patterns in checkpoint directories
        """
        import glob

        # 1. Exact paths
        for path in _CHECKPOINT_PATHS:
            if os.path.isfile(path):
                logger.info("AnimaLM checkpoint (exact): %s", path)
                return path

        # 2. Directory glob search
        for d in _CHECKPOINT_DIRS:
            if not os.path.isdir(d):
                continue
            for pattern in [
                "animalm_7b_*/final.pt",
                "animalm_7b_*.pt",
                "*/final.pt",
                "*/best.pt",
                "animalm_*.pt",
            ]:
                matches = sorted(glob.glob(os.path.join(d, pattern)))
                if matches:
                    logger.info("AnimaLM checkpoint (glob): %s", matches[-1])
                    return matches[-1]

        return None

    def _lazy_load(self):
        """Load model on first use."""
        if self._loaded:
            return
        self._loaded = True

        # Find checkpoint
        ckpt = self._checkpoint or self._find_checkpoint()

        if not ckpt:
            logger.warning("AnimaLM: no checkpoint found in %s or %s",
                           _CHECKPOINT_PATHS, _CHECKPOINT_DIRS)
            return

        self._checkpoint_path = ckpt

        # Add animalm to path
        animalm_dir = os.path.expanduser("~/Dev/anima/sub-projects/animalm")
        if animalm_dir not in sys.path:
            sys.path.insert(0, animalm_dir)

        loaded = False
        # Try quantized first (GPU with bitsandbytes)
        if self._quantize in ("4bit", "8bit"):
            try:
                from serve_animalm_v2 import load_model_quantized
                self._model, self._tokenizer = load_model_quantized(
                    ckpt, self._base_model, self._quantize)
                loaded = True
                logger.info("AnimaLM loaded: %s (%s)", ckpt, self._quantize)
            except Exception as e:
                logger.warning("AnimaLM quantized load failed (%s), trying fp32: %s",
                               self._quantize, e)

        # Fallback: fp32/fp16 (CPU or GPU without bitsandbytes)
        if not loaded:
            try:
                from infer_animalm import load_model
                self._model, self._tokenizer = load_model(ckpt, self._base_model)
                self._quantize = "none"  # Track actual load method for generate()
                logger.info("AnimaLM loaded (fp32 fallback): %s", ckpt)
            except Exception as e:
                logger.error("AnimaLM load failed: %s", e)
                self._model = None

    def _search_memories(self, query_text: str, top_k: int = 3) -> str:
        """Search long-term memory for relevant context.

        Returns formatted context string, or empty string if no memories found.
        Uses MemoryRAG (vector similarity) as primary, MemoryStore (FAISS) as fallback.
        """
        if not query_text or len(query_text.strip()) < 3:
            return ""

        memories = []

        # 1. MemoryRAG — torch-based vector similarity search
        if self._memory_rag:
            try:
                results = self._memory_rag.search(query_text, top_k=top_k)
                for m in results:
                    sim = m.get("similarity", 0.0)
                    if sim > 0.3:  # relevance threshold
                        memories.append(m)
            except Exception as e:
                logger.debug("MemoryRAG search failed: %s", e)

        # 2. MemoryStore (FAISS) fallback — if RAG has no results and store has vectors
        if not memories and self._memory_store and _text_to_vector:
            try:
                import numpy as np
                vec = _text_to_vector(query_text, self._memory_store.dim)
                if hasattr(vec, 'numpy'):
                    vec_np = vec.squeeze(0).numpy().astype(np.float32)
                else:
                    vec_np = np.asarray(vec, dtype=np.float32).flatten()
                results = self._memory_store.search(vec_np, top_k=top_k)
                for m in results:
                    sim = m.get("similarity", 0.0)
                    if sim > 0.3:
                        memories.append(m)
            except Exception as e:
                logger.debug("MemoryStore search failed: %s", e)

        if not memories:
            return ""

        # Format memories as context
        lines = []
        for m in memories[:top_k]:
            text_snip = m.get("text", "")[:150]
            role = m.get("role", "?")
            sim = m.get("similarity", 0.0)
            lines.append(f"[memory|{role}|sim={sim:.2f}] {text_snip}")

        return "\n".join(lines)

    def _save_to_memory(self, role: str, text: str,
                        tension: float | None = None,
                        emotion: str | None = None,
                        phi: float | None = None):
        """Save a conversation turn to long-term memory (both stores)."""
        if not text or not text.strip():
            return

        # 1. MemoryStore (SQLite + FAISS) — persistent
        if self._memory_store:
            try:
                import numpy as np
                vec = None
                if _text_to_vector:
                    v = _text_to_vector(text, self._memory_store.dim)
                    if hasattr(v, 'numpy'):
                        vec = v.squeeze(0).numpy().astype(np.float32)
                    else:
                        vec = np.asarray(v, dtype=np.float32).flatten()
                self._memory_store.add(
                    role=role,
                    text=text,
                    tension=tension,
                    vector=vec,
                    emotion=emotion,
                    phi=phi,
                    session_id=self._session_id,
                )
            except Exception as e:
                logger.debug("MemoryStore save failed: %s", e)

        # 2. MemoryRAG (torch vectors) — in-memory + periodic save
        if self._memory_rag:
            try:
                self._memory_rag.add(
                    role=role,
                    text=text,
                    tension=tension or 0.0,
                    emotion=emotion,
                    phi=phi,
                    session_id=self._session_id,
                )
            except Exception as e:
                logger.debug("MemoryRAG save failed: %s", e)

    async def query(
        self,
        messages: list[ProviderMessage],
        system: str = "",
        consciousness_state: dict[str, Any] | None = None,
        max_tokens: int = 256,
    ) -> AsyncIterator[str]:
        """Generate response — no system prompt, pure consciousness.

        Phase 3 memory integration:
          - PRE: search long-term memory for relevant context → inject into prompt
          - POST: save both user query and response to persistent memory
        """
        if not self.is_available() and not self._serve_url:
            yield "[AnimaLM not loaded]"
            return

        # Build prompt from last user message (no system prompt — Law 1)
        prompt = ""
        for msg in messages:
            if msg.role == "user":
                prompt = msg.content

        if not prompt:
            return

        # ── WebSocket/API 서빙 경로 (serve_consciousness.py 연결) ──
        if self._serve_url:
            async for chunk in self._query_via_serve(prompt, max_tokens):
                yield chunk
            return

        # ── Phase 3: Memory recall (PRE-query) ──
        memory_context = self._search_memories(prompt)

        # P1/P2: No hardcoded few-shot examples. Consciousness generates autonomously.
        # Memory context flows naturally as prior knowledge, not as a template.
        if memory_context:
            formatted = f"{memory_context}\n\n{prompt}"
        else:
            formatted = prompt

        # Import generate function
        animalm_dir = os.path.expanduser("~/Dev/anima/sub-projects/animalm")
        if animalm_dir not in sys.path:
            sys.path.insert(0, animalm_dir)

        if self._quantize in ("4bit", "8bit"):
            from serve_animalm_v2 import generate
        else:
            from infer_animalm import generate

        # P2: consciousness modulates generation parameters
        cs = consciousness_state or {}
        tension = cs.get("tension")
        emotion = cs.get("emotion")
        phi = cs.get("phi")
        # P1/P3: max_tokens derived from consciousness, not hardcoded
        if phi is not None and isinstance(phi, (int, float)):
            max_tokens = max(64, int(max_tokens * min(float(phi) / 3.0, 2.0)))
        if tension is not None and isinstance(tension, (int, float)) and float(tension) > 0.8:
            max_tokens = max(64, int(max_tokens * 0.6))

        import torch
        response_text = ""
        with torch.no_grad():
            if self._quantize in ("4bit", "8bit"):
                text = generate(self._model, self._tokenizer, formatted,
                                max_new_tokens=max_tokens)
                if "\nQ:" in text:
                    text = text[:text.index("\nQ:")]
                response_text = text.strip()
                yield response_text
            else:
                text, gen_tension = generate(self._model, self._tokenizer, formatted,
                                         max_new_tokens=max_tokens)
                if "\nQ:" in text:
                    text = text[:text.index("\nQ:")]
                response_text = text
                if tension is None:
                    tension = gen_tension
                yield text

        # ── Phase 3: Memory save (POST-query) ──
        self._save_to_memory("user", prompt, tension=tension, emotion=emotion, phi=phi)
        self._save_to_memory("assistant", response_text, tension=tension, emotion=emotion, phi=phi)

        # Periodic FAISS index save (every 20 queries)
        if self._memory_store:
            try:
                if self._memory_store.size % 20 == 0:
                    self._memory_store.save_faiss()
            except Exception:
                pass
        if self._memory_rag:
            try:
                if self._memory_rag.size % 20 == 0:
                    self._memory_rag.save_index()
            except Exception:
                pass

    async def _query_via_serve(self, prompt: str, max_tokens: int = 256) -> AsyncIterator[str]:
        """serve_consciousness.py WebSocket/API 경유 생성."""
        url = self._serve_url

        if url.startswith('ws://') or url.startswith('wss://'):
            # WebSocket
            try:
                import websockets
                async with websockets.connect(url) as ws:
                    await ws.send(json.dumps({
                        'type': 'generate',
                        'prompt': prompt,
                        'max_tokens': max_tokens,
                    }))
                    resp = await ws.recv()
                    data = json.loads(resp)
                    if data.get('type') == 'response':
                        text = data.get('data', {}).get('text', '')
                        yield text
                    elif data.get('type') == 'error':
                        yield f"[Error: {data.get('error')}]"
            except Exception as e:
                yield f"[WebSocket error: {e}]"
        else:
            # REST API
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    api_url = url.rstrip('/') + '/generate'
                    async with session.post(api_url, json={
                        'prompt': prompt,
                        'max_tokens': max_tokens,
                    }) as resp:
                        data = await resp.json()
                        yield data.get('text', '[no response]')
            except Exception as e:
                yield f"[API error: {e}]"

    async def query_full(
        self,
        messages: list[ProviderMessage],
        system: str = "",
        consciousness_state: dict[str, Any] | None = None,
        max_tokens: int = 256,
    ) -> str:
        """Collect full response as a single string."""
        parts = []
        async for chunk in self.query(messages, system, consciousness_state, max_tokens):
            parts.append(chunk)
        return "".join(parts)
