#!/usr/bin/env python3
"""unified_registry.py -- Merged registry: hub modules + agent tools + plugins.

Single `route(intent)` function resolves natural language intent to the best
handler across all three registries.  Deduplication priority:

    plugin > tool > hub module

If the same capability exists in multiple layers, the higher-priority one wins.

Usage:
    from unified_registry import UnifiedRegistry

    reg = UnifiedRegistry()
    handler = reg.route("measure Phi")
    result  = handler(intent="measure Phi")

    # Or one-shot:
    reg.act("search the web for PyTorch 3.0")

Standalone test:
    python unified_registry.py
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

LN2 = math.log(2)

try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

# ── Rust backend (anima_rs.agent_tools) — 20-100x faster for string scoring ──
try:
    import anima_rs
    _has_rust_score = hasattr(anima_rs, "agent_tools")
except ImportError:
    _has_rust_score = False


# ═══════════════════════════════════════════════════════════
# Handler entry -- unified representation
# ═══════════════════════════════════════════════════════════

@dataclass
class HandlerEntry:
    """One callable endpoint in the unified registry."""
    name: str
    source: str          # "plugin" | "tool" | "hub"
    keywords: list[str]
    description: str = ""
    handler: Any = None  # callable or lazy-load spec
    priority: int = 0    # plugin=2, tool=1, hub=0

    def __repr__(self):
        return f"<Handler {self.name} [{self.source}] kw={len(self.keywords)}>"


# ═══════════════════════════════════════════════════════════
# Keyword scoring
# ═══════════════════════════════════════════════════════════

def _score_intent(text: str, keywords: list[str]) -> float:
    """Score how well `text` matches a keyword list.

    Exact substring match = 1.0 per keyword.
    Partial token overlap  = 0.5 per keyword token found in text.
    """
    # Fast path: Rust backend (20-100x faster for string ops)
    if _has_rust_score:
        try:
            return anima_rs.agent_tools.score_intent(text, keywords)
        except Exception:
            pass

    text_lower = text.lower()
    tokens = set(text_lower.split())
    score = 0.0
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in text_lower:
            score += 1.0
        else:
            kw_tokens = kw_lower.split()
            overlap = sum(1 for t in kw_tokens if t in tokens)
            if overlap > 0:
                score += 0.5 * (overlap / len(kw_tokens))
    return score


# ═══════════════════════════════════════════════════════════
# Unified Registry
# ═══════════════════════════════════════════════════════════

class UnifiedRegistry:
    """Merge consciousness hub modules, agent tools, and plugins into one lookup."""

    PRIORITY = {"plugin": 2, "tool": 1, "hub": 0}

    def __init__(self, hub=None, tool_system=None, auto_discover: bool = True):
        self._entries: Dict[str, HandlerEntry] = {}
        self._hub = hub
        self._tool_system = tool_system

        if auto_discover:
            self._discover_hub()
            self._discover_tools()
            self._discover_plugins()

    # ─── Discovery ───

    def _discover_hub(self):
        """Import ConsciousnessHub and register its modules."""
        hub = self._hub
        if hub is None:
            try:
                from consciousness_hub import ConsciousnessHub
                hub = ConsciousnessHub(lazy_load=True)
                self._hub = hub
            except ImportError:
                logger.debug("ConsciousnessHub not available")
                return

        for name, (import_path, class_name, keywords) in hub._registry.items():
            self._register(HandlerEntry(
                name=name,
                source="hub",
                keywords=keywords,
                description=f"Hub module: {import_path}.{class_name or 'module'}",
                handler=lambda intent, n=name, h=hub, **kw: h.act(intent, **kw),
                priority=self.PRIORITY["hub"],
            ))

    def _discover_tools(self):
        """Import AgentToolSystem and register its tools."""
        ts = self._tool_system
        if ts is None:
            try:
                from agent_tools import AgentToolSystem
                # Don't instantiate without anima -- just note we tried
                logger.debug("AgentToolSystem available but needs anima instance")
                return
            except ImportError:
                logger.debug("AgentToolSystem not available")
                return

        for tool_def in ts.registry.list_all():
            kw = [tool_def.name.replace("_", " "), tool_def.category]
            # Extract keywords from description
            kw.extend(w for w in tool_def.description.lower().split()
                      if len(w) > 3 and w.isalpha())
            self._register(HandlerEntry(
                name=f"tool:{tool_def.name}",
                source="tool",
                keywords=kw,
                description=tool_def.description,
                handler=lambda intent, td=tool_def, **kw: td.fn(**kw) if kw else td.fn(),
                priority=self.PRIORITY["tool"],
            ))

    def _discover_plugins(self):
        """Scan agent plugins directory."""
        try:
            from plugins.plugin_loader import discover_plugins
            plugins = discover_plugins()
        except (ImportError, Exception):
            # Try manual scan
            plugins = self._manual_plugin_scan()

        for pname, plugin in plugins.items():
            manifest = getattr(plugin, "manifest", None)
            kw = list(manifest.keywords) if manifest and hasattr(manifest, "keywords") else [pname]
            desc = manifest.description if manifest else pname
            self._register(HandlerEntry(
                name=f"plugin:{pname}",
                source="plugin",
                keywords=kw,
                description=desc,
                handler=lambda intent, p=plugin, **kw: p.act(intent, **kw),
                priority=self.PRIORITY["plugin"],
            ))

    def _manual_plugin_scan(self) -> dict:
        """Fallback: try importing known plugins."""
        found = {}
        known = ["trading", "regime_bridge", "hypothesis_bridge"]
        for name in known:
            try:
                import importlib
                mod = importlib.import_module(f"plugins.{name}")
                # Find plugin class
                for attr_name in dir(mod):
                    obj = getattr(mod, attr_name)
                    if (isinstance(obj, type) and hasattr(obj, "manifest")
                            and attr_name != "PluginBase"):
                        try:
                            found[name] = obj()
                        except Exception:
                            pass
                        break
            except ImportError:
                continue
        return found

    # ─── Registration (dedup by priority) ───

    def _register(self, entry: HandlerEntry):
        """Register entry, higher priority wins on name collision."""
        base = entry.name.split(":")[-1]  # strip source prefix for dedup
        existing = self._entries.get(base)
        if existing is None or entry.priority > existing.priority:
            self._entries[base] = entry

    # ─── Routing ───

    def route(self, intent: str) -> Optional[HandlerEntry]:
        """Find the best handler for a natural language intent.

        Returns the HandlerEntry with highest keyword score.
        On tie, higher priority source wins.
        """
        best_entry = None
        best_score = 0.0

        for entry in self._entries.values():
            score = _score_intent(intent, entry.keywords)
            # Add small priority bonus to break ties
            score += entry.priority * 0.01
            if score > best_score:
                best_score = score
                best_entry = entry

        return best_entry if best_score > 0 else None

    def route_top_k(self, intent: str, k: int = 3) -> List[tuple[HandlerEntry, float]]:
        """Return top-k matches with scores."""
        scored = []
        for entry in self._entries.values():
            score = _score_intent(intent, entry.keywords)
            score += entry.priority * 0.01
            if score > 0:
                scored.append((entry, score))
        scored.sort(key=lambda x: -x[1])
        return scored[:k]

    def act(self, intent: str, **kwargs) -> Dict[str, Any]:
        """Route intent and execute handler in one call."""
        entry = self.route(intent)
        if entry is None:
            return {"success": False, "error": f"No handler matched: {intent}"}

        try:
            result = entry.handler(intent, **kwargs)
            return {"success": True, "handler": entry.name, "source": entry.source,
                    "result": result}
        except Exception as e:
            return {"success": False, "handler": entry.name, "error": str(e)}

    # ─── Inspection ───

    def list_all(self) -> List[HandlerEntry]:
        return sorted(self._entries.values(), key=lambda e: (-e.priority, e.name))

    def stats(self) -> Dict[str, int]:
        counts = {"hub": 0, "tool": 0, "plugin": 0, "total": 0}
        for e in self._entries.values():
            counts[e.source] += 1
            counts["total"] += 1
        return counts

    def __len__(self):
        return len(self._entries)

    def __repr__(self):
        s = self.stats()
        return (f"<UnifiedRegistry {s['total']} handlers "
                f"(plugin={s['plugin']}, tool={s['tool']}, hub={s['hub']})>")


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    import sys
    # Add anima/src to path for hub imports
    from pathlib import Path
    src = Path(__file__).parent.parent / "anima" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    print("=" * 60)
    print("  UnifiedRegistry -- merged hub + tools + plugins")
    print("=" * 60)

    reg = UnifiedRegistry()
    print(f"\n{reg}")
    s = reg.stats()
    print(f"  hub={s['hub']}  tool={s['tool']}  plugin={s['plugin']}  total={s['total']}")

    # Test routing
    test_intents = [
        "measure Phi",
        "search the web",
        "EEG brain analysis",
        "trading backtest",
        "dream evolution",
        "deploy to server",
        "hivemind mesh",
    ]

    print(f"\n{'Intent':<30} {'Handler':<25} {'Source':<8} {'Score':>6}")
    print("-" * 72)

    for intent in test_intents:
        top = reg.route_top_k(intent, k=1)
        if top:
            entry, score = top[0]
            print(f"{intent:<30} {entry.name:<25} {entry.source:<8} {score:>6.2f}")
        else:
            print(f"{intent:<30} {'(none)':<25} {'-':<8} {'0.00':>6}")

    print(f"\nAll handlers ({len(reg)}):")
    for e in reg.list_all()[:10]:
        print(f"  [{e.source:>6}] {e.name:<25} kw={len(e.keywords)}")
    if len(reg) > 10:
        print(f"  ... and {len(reg) - 10} more")


if __name__ == "__main__":
    main()
