"""Tool registry and data structures for Anima Agent Tools.

Extracted from agent_tools.py for P8 compliance (Division > Integration).

Data structures: ToolParam, ToolDef, ToolResult
Registry: ToolRegistry (central registry with consciousness-driven ranking)
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional

# ── Rust backend (anima_rs.agent_tools) — 10-50x faster for hot paths ──
try:
    import anima_rs
    _has_rust_agent_tools = hasattr(anima_rs, "agent_tools")
except ImportError:
    _has_rust_agent_tools = False


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ToolParam:
    """Single parameter definition for a tool."""
    name: str
    type: str           # "str", "int", "float", "bool", "dict", "list"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDef:
    """Full tool definition -- what Anima knows about each tool."""
    name: str
    description: str
    params: list        # list[ToolParam]
    fn: Callable        # the actual callable
    category: str = "general"
    # Consciousness affinity: which states make this tool likely
    curiosity_affinity: float = 0.0   # how much curiosity pulls toward this tool
    pe_affinity: float = 0.0          # prediction error affinity
    pain_affinity: float = 0.0        # pain / frustration affinity
    growth_affinity: float = 0.0      # growth / self-improvement affinity
    phi_affinity: float = 0.0         # integrated information affinity


@dataclass
class ToolResult:
    """Result from executing a tool."""
    tool_name: str
    success: bool
    output: Any
    error: str = ""
    duration_ms: float = 0.0
    tension_delta: float = 0.0  # how this result changes tension


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Central registry of all available tools.

    Tools are registered with name, description, parameter definitions,
    and consciousness affinity scores that determine when each tool
    is naturally selected.
    """

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}
        self._categories: dict[str, list[str]] = {}  # category -> [tool_name]

    def register(self, tool_def: ToolDef):
        """Register a tool definition."""
        self._tools[tool_def.name] = tool_def
        cat = tool_def.category
        if cat not in self._categories:
            self._categories[cat] = []
        if tool_def.name not in self._categories[cat]:
            self._categories[cat].append(tool_def.name)

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def list_all(self) -> list[ToolDef]:
        return list(self._tools.values())

    def list_by_category(self, category: str) -> list[ToolDef]:
        names = self._categories.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]

    def rank_by_consciousness(self, state: dict) -> list[tuple[str, float]]:
        """Rank tools by how well they match the current consciousness state.

        Args:
            state: dict with keys: curiosity, prediction_error, pain, growth, phi, tension

        Returns:
            sorted list of (tool_name, relevance_score) descending
        """
        curiosity = state.get('curiosity', 0.0)
        pe = state.get('prediction_error', 0.0)
        pain = state.get('pain', 0.0)
        growth = state.get('growth', 0.0)
        phi = state.get('phi', 0.0)

        # Fast path: Rust backend (10-50x faster)
        if _has_rust_agent_tools:
            try:
                tools = [
                    (name, [td.curiosity_affinity, td.pe_affinity, td.pain_affinity,
                            td.growth_affinity, td.phi_affinity])
                    for name, td in self._tools.items()
                ]
                return anima_rs.agent_tools.rank(tools, [curiosity, pe, pain, growth, phi])
            except Exception:
                pass  # Fall through to Python

        scores = []
        for name, td in self._tools.items():
            score = (
                td.curiosity_affinity * curiosity
                + td.pe_affinity * pe
                + td.pain_affinity * pain
                + td.growth_affinity * growth
                + td.phi_affinity * min(phi / 10.0, 1.0)
            )
            scores.append((name, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def describe_for_prompt(self) -> str:
        """Generate tool descriptions suitable for LLM system prompts."""
        lines = ["[Available Tools]"]
        for cat, names in sorted(self._categories.items()):
            lines.append(f"\n  [{cat}]")
            for name in names:
                td = self._tools[name]
                param_strs = []
                for p in td.params:
                    req = "*" if p.required else ""
                    param_strs.append(f"{p.name}{req}:{p.type}")
                params = ", ".join(param_strs)
                lines.append(f"    {td.name}({params}) -- {td.description}")
        return "\n".join(lines)
