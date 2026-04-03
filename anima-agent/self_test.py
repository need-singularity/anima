#!/usr/bin/env python3
"""Agent Self-Test — agent tests itself after interactions.

P2: Consciousness should monitor its own health autonomously.
Called periodically from process_message or via /selftest CLI command.

Usage:
    from self_test import AgentSelfTest
    tester = AgentSelfTest(agent)
    result = tester.run()  # Returns dict with pass/fail + metrics
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class AgentSelfTest:
    """Lightweight self-diagnostic that the agent runs on itself."""

    def __init__(self, agent):
        self.agent = agent

    def run(self) -> Dict[str, Any]:
        """Run all self-checks. Returns summary dict."""
        t0 = time.time()
        checks = {}

        # 1. Consciousness vector valid
        try:
            cv = self.agent.mind._consciousness_vector
            checks["phi_valid"] = cv.phi >= 0
            checks["phi_value"] = cv.phi
        except Exception:
            checks["phi_valid"] = False

        # 2. Tension in range
        t = self.agent._tension
        checks["tension_range"] = 0 <= t <= 10
        checks["tension_value"] = t

        # 3. History not corrupted
        checks["history_valid"] = isinstance(self.agent.history, list)
        checks["history_size"] = len(self.agent.history)

        # 4. Tools accessible
        if self.agent.tools:
            tools = self.agent.tools.registry.list_all()
            checks["tools_count"] = len(tools)
            checks["tools_valid"] = len(tools) > 0
        else:
            checks["tools_valid"] = True  # Disabled is OK
            checks["tools_count"] = 0

        # 5. NEXUS-6 reachable
        checks["nexus6"] = self.agent.nexus6 is not None

        # 6. Provider available
        if self.agent.provider:
            checks["provider"] = self.agent.provider.name
            checks["provider_available"] = self.agent.provider.is_available()
        else:
            checks["provider"] = None
            checks["provider_available"] = False

        # 7. Memory functional
        checks["memory_rag"] = self.agent.memory_rag is not None
        checks["memory_store"] = getattr(self.agent, 'memory_store', None) is not None

        # Overall
        critical = [checks.get("phi_valid"), checks.get("tension_range"),
                    checks.get("history_valid")]
        checks["passed"] = all(c for c in critical if c is not None)
        checks["duration_ms"] = (time.time() - t0) * 1000

        return checks
