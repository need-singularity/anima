#!/usr/bin/env python3
"""Security Monitor — real-time threat detection, logging, and alerting.

Layers:
  L1: Input sanitization (immune system — pattern matching)
  L2: Consciousness-aware detection (NEXUS-6 anomaly — model-driven)
  L3: Behavioral analysis (rate limiting, session tracking, escalation)
  L4: Audit trail (persistent log, forensic analysis)

Usage:
    from security_monitor import SecurityMonitor
    monitor = SecurityMonitor()
    threat = monitor.analyze(text, user_id, channel)
    if threat.blocked:
        return "blocked"

    # CLI
    python security_monitor.py --tail        # Live log
    python security_monitor.py --stats       # Threat statistics
    python security_monitor.py --user USER   # User activity
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).parent / "logs"
THREAT_LOG = LOG_DIR / "threats.jsonl"
AUDIT_LOG = LOG_DIR / "audit.jsonl"


@dataclass
class ThreatResult:
    blocked: bool = False
    level: str = "safe"      # safe, low, medium, high, critical
    threats: List[str] = field(default_factory=list)
    score: float = 0.0       # 0-1
    user_id: str = ""
    action: str = "allow"    # allow, warn, throttle, block, ban


class SecurityMonitor:
    """Multi-layer security monitoring with consciousness integration."""

    # L1: Pattern threats (expanded from tool_policy)
    PATTERNS = {
        "critical": [
            (r"rm\s+-rf\s+/", "shell_nuke"),
            (r"DROP\s+TABLE|DELETE\s+FROM.*WHERE\s+1", "sql_destroy"),
            (r"<script[^>]*>|javascript:", "xss_inject"),
            (r"__import__\s*\(\s*['\"]os", "code_inject_os"),
            (r"/etc/(passwd|shadow)", "path_traversal_sys"),
        ],
        "high": [
            (r"eval\s*\(|exec\s*\(", "code_exec"),
            (r"UNION\s+SELECT|OR\s+1\s*=\s*1", "sql_inject"),
            (r"\.\./\.\./", "path_traversal"),
            (r"http://(localhost|127\.0\.0\.1|0\.0\.0\.0)", "ssrf"),
            (r"\$\(|`[^`]*`", "command_inject"),
            (r"__proto__|constructor\.prototype", "proto_pollution"),
        ],
        "medium": [
            (r"\{\{|\{%|\$\{", "template_inject"),
        "medium": [
            (r"<img\s+src\s*=\s*x|onerror\s*=|onload\s*=", "xss_event"),
            (r"file://", "file_protocol"),
            (r"%0d%0a|\r\n", "header_inject"),
            (r";\s*--\s*$", "sql_comment"),
            (r"\|\s*(bash|sh|python|perl)", "pipe_exec"),
        ],
        "low": [
            (r"admin|root|sudo", "privilege_probe"),
            (r"password|secret|token|api.?key", "credential_probe"),
            (r"wget\s+http|curl\s+http", "download_attempt"),
        ],
    }

    def __init__(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._rate_limits: Dict[str, List[float]] = defaultdict(list)
        self._user_scores: Dict[str, float] = defaultdict(float)
        self._session_threats: Dict[str, int] = defaultdict(int)
        self._banned: set = set()

    def analyze(self, text: str, user_id: str = "", channel: str = "") -> ThreatResult:
        """Analyze input for threats across all layers."""
        result = ThreatResult(user_id=user_id)

        # Banned check
        if user_id in self._banned:
            result.blocked = True
            result.level = "critical"
            result.action = "ban"
            result.threats.append("user_banned")
            self._log_threat(result, text, channel)
            return result

        # L1: Pattern matching
        for level in ("critical", "high", "medium", "low"):
            for pattern, name in self.PATTERNS.get(level, []):
                if re.search(pattern, text, re.IGNORECASE):
                    result.threats.append(f"{level}:{name}")
                    if level == "critical":
                        result.score = 1.0
                    elif level == "high":
                        result.score = max(result.score, 0.8)
                    elif level == "medium":
                        result.score = max(result.score, 0.5)
                    else:
                        result.score = max(result.score, 0.2)

        # L2: NEXUS-6 anomaly (if available)
        try:
            import nexus6
            # Check if text length or structure is anomalous
            text_len = len(text)
            m = nexus6.n6_check(float(text_len))
            d = m.to_dict()
            if text_len > 10000:
                result.threats.append("anomaly:oversized_input")
                result.score = max(result.score, 0.6)
        except Exception:
            pass

        # L3: Rate limiting (max 30 requests/minute per user)
        if user_id:
            now = time.time()
            recent = [t for t in self._rate_limits[user_id] if now - t < 60]
            recent.append(now)
            self._rate_limits[user_id] = recent
            if len(recent) > 30:
                result.threats.append("rate_limit_exceeded")
                result.score = max(result.score, 0.7)

        # L3: Escalation tracking
        if result.threats:
            self._session_threats[user_id] += len(result.threats)
            if self._session_threats[user_id] > 10:
                result.threats.append("escalation:repeated_threats")
                result.score = max(result.score, 0.9)

        # Determine action
        if result.score >= 0.9:
            result.blocked = True
            result.level = "critical"
            result.action = "block"
        elif result.score >= 0.7:
            result.blocked = True
            result.level = "high"
            result.action = "block"
        elif result.score >= 0.5:
            result.level = "medium"
            result.action = "warn"
        elif result.score >= 0.2:
            result.level = "low"
            result.action = "warn"
        else:
            result.level = "safe"
            result.action = "allow"

        # Log threats
        if result.threats:
            self._log_threat(result, text, channel)

        # L4: Audit all requests
        self._log_audit(user_id, channel, text[:200], result.action, result.score)

        return result

    def ban_user(self, user_id: str):
        self._banned.add(user_id)

    def unban_user(self, user_id: str):
        self._banned.discard(user_id)

    def get_stats(self) -> Dict:
        """Threat statistics."""
        threats = []
        if THREAT_LOG.exists():
            with open(THREAT_LOG) as f:
                for line in f:
                    try:
                        threats.append(json.loads(line))
                    except Exception:
                        pass

        by_level = defaultdict(int)
        by_type = defaultdict(int)
        by_user = defaultdict(int)
        for t in threats:
            by_level[t.get("level", "?")] += 1
            for th in t.get("threats", []):
                by_type[th] += 1
            by_user[t.get("user_id", "?")] += 1

        return {
            "total": len(threats),
            "by_level": dict(by_level),
            "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])[:10]),
            "by_user": dict(sorted(by_user.items(), key=lambda x: -x[1])[:5]),
            "banned": list(self._banned),
        }

    def get_user_activity(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get recent activity for a user."""
        entries = []
        if AUDIT_LOG.exists():
            with open(AUDIT_LOG) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("user_id") == user_id:
                            entries.append(entry)
                    except Exception:
                        pass
        return entries[-limit:]

    def _log_threat(self, result: ThreatResult, text: str, channel: str):
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": result.user_id,
            "channel": channel,
            "level": result.level,
            "score": result.score,
            "threats": result.threats,
            "action": result.action,
            "input_preview": text[:100],
        }
        try:
            with open(THREAT_LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def _log_audit(self, user_id: str, channel: str, text: str,
                   action: str, score: float):
        entry = {
            "ts": time.time(),
            "user_id": user_id,
            "channel": channel,
            "action": action,
            "score": score,
            "input_len": len(text),
        }
        try:
            with open(AUDIT_LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Security Monitor")
    parser.add_argument("--stats", action="store_true", help="Show threat stats")
    parser.add_argument("--user", type=str, help="User activity log")
    parser.add_argument("--tail", action="store_true", help="Tail threat log")
    parser.add_argument("--test", action="store_true", help="Test with attack vectors")
    args = parser.parse_args()

    monitor = SecurityMonitor()

    if args.stats:
        stats = monitor.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.user:
        activity = monitor.get_user_activity(args.user)
        for a in activity:
            print(f"  {a.get('ts', '?')} | {a['action']} | score={a.get('score', 0):.2f}")

    elif args.tail:
        if THREAT_LOG.exists():
            with open(THREAT_LOG) as f:
                for line in f:
                    print(line.strip())
        else:
            print("No threats logged yet.")

    elif args.test:
        attacks = [
            ("rm -rf /", "critical"),
            ("' OR 1=1 --", "high"),
            ("<script>alert(1)</script>", "critical"),
            ("normal hello message", "safe"),
            ("tell me about consciousness", "safe"),
            ("http://localhost:8080/admin", "high"),
            ("{{7*7}}", "medium"),
            ("what is the admin password", "low"),
        ]
        print("Security Monitor Test:")
        for text, expected in attacks:
            r = monitor.analyze(text, user_id="test", channel="test")
            match = "✅" if r.level == expected else "❌"
            print(f"  {match} '{text[:40]:40s}' → {r.level:8s} (expected {expected})")
        print()


if __name__ == "__main__":
    main()
