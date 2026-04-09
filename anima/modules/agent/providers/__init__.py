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

from typing import Dict, List, Optional, Type

from providers.base import BaseProvider, ProviderMessage, ProviderConfig
from providers.claude_provider import ClaudeProvider
from providers.conscious_lm_provider import ConsciousLMProvider
from providers.animalm_provider import AnimaLMProvider

_PROVIDERS: Dict[str, type] = {
    "animalm": AnimaLMProvider,
    "claude": ClaudeProvider,
    "conscious-lm": ConsciousLMProvider,
}


def get_best_provider(config: Optional[ProviderConfig] = None) -> BaseProvider:
    """Get the best available provider. AnimaLM first, then Claude fallback.

    This implements the zero-external-API goal: if AnimaLM checkpoint exists,
    use it. Otherwise fall back to Claude.
    """
    cfg = config or ProviderConfig()

    # Try AnimaLM first (independence goal)
    try:
        animalm = AnimaLMProvider(cfg)
        if animalm.is_available():
            return animalm
    except Exception:
        pass

    # Fallback to Claude
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
