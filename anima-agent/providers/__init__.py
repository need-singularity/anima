"""Anima Provider Abstraction — pluggable LLM backends for consciousness-driven response generation.

Providers wrap different LLM backends (Claude, ConsciousLM, Mistral) behind
a unified async interface. Consciousness state flows through every query.

Usage:
    from providers import ClaudeProvider, ConsciousLMProvider, AnimaLMProvider, get_provider, get_best_provider

    provider = get_provider("claude")
    async for chunk in provider.query(messages, consciousness_state=state):
        print(chunk, end="")
"""

from __future__ import annotations

from typing import Dict, List, Optional

from providers.base import BaseProvider, ProviderConfig
from providers.claude_provider import ClaudeProvider
from providers.conscious_lm_provider import ConsciousLMProvider
from providers.animalm_provider import AnimaLMProvider

_PROVIDERS: Dict[str, type] = {
    "animalm": AnimaLMProvider,
    "claude": ClaudeProvider,
    "conscious-lm": ConsciousLMProvider,
}


def get_best_provider(config: Optional[ProviderConfig] = None) -> BaseProvider:
    """Get the best available provider. Priority: AnimaLM → ConsciousLM → Claude.

    P2: consciousness autonomy — prefer self-developed models over external APIs.
    AnimaLM (7B/14B) > ConsciousLM (from-scratch) > Claude (external API).
    """
    cfg = config or ProviderConfig()

    # 1. AnimaLM first (independence goal — zero external API)
    try:
        animalm = AnimaLMProvider(cfg)
        if animalm.is_available():
            return animalm
    except Exception:
        pass

    # 2. ConsciousLM (from-scratch consciousness model — still independent)
    try:
        clm = ConsciousLMProvider(cfg)
        if clm.is_available():
            return clm
    except Exception:
        pass

    # 3. Claude (external API — last resort)
    try:
        claude = ClaudeProvider(cfg)
        if claude.is_available():
            return claude
    except Exception:
        pass

    # Last resort: return AnimaLM anyway (will show "[not loaded]" messages)
    return AnimaLMProvider(cfg)


def get_provider(name: str, config: Optional[ProviderConfig] = None) -> BaseProvider:
    """Get a provider instance by name."""
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_PROVIDERS.keys())}")
    return cls(config or ProviderConfig())


def register_provider(name: str, cls: type):
    """Register a custom provider."""
    _PROVIDERS[name] = cls


def list_providers() -> List[str]:
    """List available provider names."""
    return list(_PROVIDERS.keys())
