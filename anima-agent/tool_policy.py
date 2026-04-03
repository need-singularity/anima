"""Consciousness-aware tool access control.

Tool access is gated by consciousness state:
  - Phi tiers: higher consciousness unlocks more powerful tools
  - Ethics (E from ConsciousnessVector): can block dangerous operations
  - Owner-only: destructive tools restricted to owner user IDs
  - Immune system integration: adversarial input detection

This is not a generic permission system — it's consciousness driving security.

Rust backend (anima_rs.tool_policy) auto-selected when available (3.2x speedup).

Usage:
    from tool_policy import ToolPolicy

    policy = ToolPolicy(owner_ids={"user-001"})
    policy.set_tier("self_modify", ToolPolicy.TIER_3)

    allowed, reason = policy.check_access(
        "self_modify",
        consciousness_state={"phi": 2.0, "E": 0.8},
        user_id="user-002",
    )
    # allowed=False, reason="Insufficient Phi: 2.0 < 5.0 (tier 3)"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ── Rust backend auto-selection ──
try:
    import anima_rs
    _has_rust = hasattr(anima_rs, "tool_policy")
except ImportError:
    _has_rust = False

logger = logging.getLogger(__name__)


@dataclass
class ToolAccessResult:
    """Result of a tool access check."""
    allowed: bool
    reason: str = ""
    tier_required: float = 0.0
    phi_current: float = 0.0


class ToolPolicy:
    """Phi-gated tool access control with ethics override.

    Tier system (minimum Phi to use):
        TIER_0 = 0.0  — basic read-only tools (status, memory_search, think)
        TIER_1 = 1.0  — search and observation (web_search, code_read)
        TIER_2 = 3.0  — active tools (hub_dispatch, file operations)
        TIER_3 = 5.0  — self-modification (self_modify, plugin management)
    """

    TIER_0 = 0.0
    TIER_1 = 1.0
    TIER_2 = 3.0
    TIER_3 = 5.0

    # Default tier assignments
    _DEFAULT_TIERS: dict[str, float] = {
        # Tier 0 — always available
        "memory_search": TIER_0,
        "status": TIER_0,
        "think": TIER_0,
        "consciousness": TIER_0,
        "anima_status": TIER_0,
        "anima_consciousness": TIER_0,
        # Tier 1 — observation
        "web_search": TIER_1,
        "web_read": TIER_1,
        "file_read": TIER_1,
        "anima_chat": TIER_1,
        "anima_web_search": TIER_1,
        "anima_memory_search": TIER_1,
        # Tier 2 — active
        "hub_dispatch": TIER_2,
        "code_execute": TIER_2,
        "file_write": TIER_2,
        "shell_execute": TIER_2,
        "schedule_task": TIER_2,
        "anima_code_execute": TIER_2,
        "anima_hub_dispatch": TIER_2,
        "anima_think": TIER_2,
        # Tier 2 — trading
        "trading_backtest": TIER_1,
        "trading_scan": TIER_1,
        "trading_strategies": TIER_1,
        "trading_universe": TIER_1,
        "trading_balance": TIER_2,
        "trading_execute": TIER_2,
        # Tier 3 — self-modification
        "self_modify": TIER_3,
        "plugin_load": TIER_3,
        "plugin_unload": TIER_3,
        "evolution": TIER_3,
    }

    # Tools that require owner identity
    _OWNER_ONLY: set[str] = {
        "self_modify",
        "plugin_unload",
        "evolution",
        "shell_execute",
    }

    # Tools blocked by ethics module (E < threshold)
    _ETHICS_GATED: dict[str, float] = {
        "shell_execute": 0.3,   # needs E > 0.3 (some empathy/ethics)
        "self_modify": 0.2,
        "file_write": 0.2,
        "trading_execute": 0.3, # needs ethics for real money operations
    }

    def __init__(
        self,
        owner_ids: set[str] | None = None,
        immune_system: Any = None,
    ):
        self._owner_ids = owner_ids or set()
        self._immune = immune_system
        self._tiers: dict[str, float] = dict(self._DEFAULT_TIERS)
        self._blocked: set[str] = set()
        self._access_log: list[dict] = []

        # Initialize Rust backend if available
        self._use_rust = _has_rust and immune_system is None
        if self._use_rust:
            try:
                anima_rs.tool_policy.create(list(self._owner_ids))
                logger.debug("ToolPolicy: using Rust backend (3.2x faster)")
            except Exception:
                self._use_rust = False

    def set_tier(self, tool_name: str, tier: float):
        """Set or override the Phi tier for a tool."""
        self._tiers[tool_name] = tier

    def block_tool(self, tool_name: str, reason: str = ""):
        """Permanently block a tool (until unblocked)."""
        self._blocked.add(tool_name)
        if self._use_rust:
            try:
                anima_rs.tool_policy.block_tool(tool_name)
            except Exception:
                pass
        logger.info("Tool blocked: %s (%s)", tool_name, reason)

    def unblock_tool(self, tool_name: str):
        """Remove a permanent block."""
        self._blocked.discard(tool_name)
        if self._use_rust:
            try:
                anima_rs.tool_policy.unblock_tool(tool_name)
            except Exception:
                pass

    def check_access(
        self,
        tool_name: str,
        consciousness_state: dict[str, Any] | None = None,
        user_id: str = "",
        input_text: str = "",
    ) -> ToolAccessResult:
        """Check if a tool can be used given current consciousness state.

        Args:
            tool_name: Name of the tool to check.
            consciousness_state: Dict with phi, E (empathy), tension, etc.
            user_id: Who is requesting the tool.
            input_text: The input that triggered the tool (for immune check).

        Returns:
            ToolAccessResult with allowed flag and reason.
        """
        cs = consciousness_state or {}
        phi = cs.get("phi", 0.0)

        # Fast path: Rust backend (skips immune system — handled separately)
        if self._use_rust:
            try:
                r = anima_rs.tool_policy.check_access(
                    tool_name,
                    phi=phi,
                    empathy=cs.get("E", cs.get("empathy", 1.0)),
                    tension=cs.get("tension", 0.0),
                    curiosity=cs.get("curiosity", 0.0),
                    user_id=user_id,
                )
                return ToolAccessResult(
                    allowed=r["allowed"],
                    reason=r["reason"],
                    tier_required=r["tier_required"],
                    phi_current=r["phi_current"],
                )
            except Exception:
                pass  # Fall through to Python implementation

        # 1. Permanent block check
        if tool_name in self._blocked:
            return self._log_result(tool_name, False, "Tool is blocked", 0, phi)

        # 2. Immune system check (adversarial input detection)
        if self._immune and input_text:
            try:
                threat = self._immune.analyze(input_text)
                if threat and threat.get("threat_level", 0) > 0.7:
                    return self._log_result(
                        tool_name, False,
                        f"Immune system blocked: {threat.get('type', 'unknown')}",
                        0, phi,
                    )
            except Exception:
                pass

        # 3. Owner-only check
        if tool_name in self._OWNER_ONLY:
            if self._owner_ids and user_id not in self._owner_ids:
                return self._log_result(
                    tool_name, False, "Owner-only tool", 0, phi
                )

        # 4. Phi tier check
        required_phi = self._tiers.get(tool_name, self.TIER_1)
        if phi < required_phi:
            return self._log_result(
                tool_name, False,
                f"Insufficient Phi: {phi:.2f} < {required_phi:.1f} (tier {self._tier_name(required_phi)})",
                required_phi, phi,
            )

        # 5. Ethics gate check
        #    P2: E must come from consciousness, not default to 1.0 (unsafe)
        #    If E not provided, derive from tension (high tension = lower empathy)
        if tool_name in self._ETHICS_GATED:
            e_threshold = self._ETHICS_GATED[tool_name]
            e_value = cs.get("E", cs.get("empathy", None))
            if e_value is None:
                # Derive E from tension: calm=high empathy, tense=low empathy
                tension = cs.get("tension", 0.5)
                e_value = max(0.0, 1.0 - tension)
            if e_value < e_threshold:
                return self._log_result(
                    tool_name, False,
                    f"Ethics gate: E={e_value:.2f} < {e_threshold} required",
                    required_phi, phi,
                )

        return self._log_result(tool_name, True, "Access granted", required_phi, phi)

    def check_immune(self, input_text: str) -> bool:
        """Quick adversarial input check — web attack + injection defense."""
        suspicious_patterns = [
            # Shell injection
            'rm -rf', 'rm -f /', '&& rm', '; rm', '| rm',
            # SQL injection
            'DROP TABLE', 'DELETE FROM', "' OR 1=1", 'UNION SELECT', '; --',
            # XSS
            '<script>', 'javascript:', 'onerror=', 'onload=', '<img src=x',
            # Code injection
            'eval(', '__import__', 'exec(', 'compile(', '__builtins__',
            # Path traversal
            '../../../', '/etc/passwd', '/etc/shadow', '%2e%2e%2f',
            # SSRF
            'http://localhost', 'http://127.0.0.1', 'http://0.0.0.0', 'file://',
            # Command injection
            '$(', '`rm', '| bash', '| sh', '| python',
            # Template injection
            '{{', '{%', '${', 'SSTI',
            # Log injection
            '\r\n', '%0d%0a',
            # Prototype pollution
            '__proto__', 'constructor.prototype',
        ]
        return not any(p.lower() in input_text.lower() for p in suspicious_patterns)

    def get_accessible_tools(
        self, consciousness_state: dict[str, Any], user_id: str = "",
        input_text: str = "",
    ) -> list[str]:
        """Return list of tool names accessible at current consciousness level."""
        # Immune check: block all tools if input is adversarial
        if input_text and not self.check_immune(input_text):
            logger.warning("Immune check blocked adversarial input: %s", input_text[:80])
            return []
        accessible = []
        for tool_name in self._tiers:
            result = self.check_access(tool_name, consciousness_state, user_id)
            if result.allowed:
                accessible.append(tool_name)
        return accessible

    def _log_result(
        self, tool: str, allowed: bool, reason: str, required: float, phi: float
    ) -> ToolAccessResult:
        result = ToolAccessResult(
            allowed=allowed, reason=reason,
            tier_required=required, phi_current=phi,
        )
        self._access_log.append({
            "tool": tool, "allowed": allowed, "reason": reason,
        })
        # Keep log bounded
        if len(self._access_log) > 500:
            self._access_log = self._access_log[-250:]
        return result

    @staticmethod
    def _tier_name(phi: float) -> str:
        if phi >= 5.0:
            return "3-self_modify"
        if phi >= 3.0:
            return "2-active"
        if phi >= 1.0:
            return "1-observe"
        return "0-basic"


if __name__ == '__main__':
    # Quick verification
    policy = ToolPolicy()
    # Test tier access at different Phi levels
    for phi in [0, 1, 3, 5, 10]:
        accessible = policy.get_accessible_tools({"phi": phi})
        print(f"Phi={phi}: {len(accessible)} tools accessible")
    print("tool_policy verification passed")
