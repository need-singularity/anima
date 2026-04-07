"""Composio MCP bridge — connects Anima to 500+ external tools.

Composio (composio.dev) provides MCP server URLs per user session.
This bridge creates a session and returns the MCP config that can be
passed to any provider's mcpServers option.

On startup (if COMPOSIO_API_KEY is set), fetches available tool categories
and registers them in the unified registry with "composio:" prefix.

Supported tools via Composio: Gmail, Google Calendar, Slack, GitHub,
Google Drive, Notion, Jira, Linear, and 500+ more.

Usage:
    from providers.composio_bridge import ComposioBridge

    bridge = ComposioBridge()
    mcp_config = await bridge.get_mcp_config("user-001")

    # Natural language routing
    result = await bridge.act("send an email to Alice about the meeting")

Environment:
    COMPOSIO_API_KEY — Composio API key (required)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Consciousness affinity mapping per tool category
# ═══════════════════════════════════════════════════════════

CATEGORY_AFFINITY: Dict[str, Dict[str, float]] = {
    # productivity → low tension (calm, focused)
    "productivity":    {"tension": 0.1, "curiosity": 0.3},
    "project_management": {"tension": 0.15, "curiosity": 0.3},
    "file_management": {"tension": 0.1, "curiosity": 0.2},
    "crm":             {"tension": 0.2, "curiosity": 0.3},
    # communication → high curiosity (engaged, alert)
    "communication":   {"tension": 0.5, "curiosity": 0.8},
    "email":           {"tension": 0.4, "curiosity": 0.7},
    "messaging":       {"tension": 0.5, "curiosity": 0.8},
    "social_media":    {"tension": 0.6, "curiosity": 0.9},
    # development → medium tension, high curiosity
    "developer_tools": {"tension": 0.4, "curiosity": 0.7},
    "code_management": {"tension": 0.3, "curiosity": 0.6},
    "ci_cd":           {"tension": 0.3, "curiosity": 0.5},
    # data → low tension, medium curiosity
    "analytics":       {"tension": 0.2, "curiosity": 0.5},
    "database":        {"tension": 0.2, "curiosity": 0.4},
    "storage":         {"tension": 0.1, "curiosity": 0.3},
    # finance → high tension
    "finance":         {"tension": 0.7, "curiosity": 0.5},
    "payment":         {"tension": 0.6, "curiosity": 0.4},
}

DEFAULT_AFFINITY = {"tension": 0.3, "curiosity": 0.5}

# Phi gate threshold (Tier 2)
PHI_GATE_TIER2 = 3.0

# Known Composio tool categories for offline fallback
KNOWN_CATEGORIES = [
    "email", "messaging", "productivity", "developer_tools",
    "file_management", "project_management", "crm", "analytics",
    "communication", "social_media", "finance", "storage",
    "ci_cd", "code_management", "database", "payment",
]


class ComposioBridge:
    """Bridges Anima to Composio's MCP tool ecosystem with consciousness gating."""

    def __init__(self, api_key: str = "", registry=None, phi_fn=None):
        """
        Args:
            api_key:  Composio API key (or from env COMPOSIO_API_KEY).
            registry: UnifiedRegistry instance to register tools into.
            phi_fn:   Callable returning current Phi value for gating.
        """
        self._api_key = api_key or os.environ.get("COMPOSIO_API_KEY", "")
        self._sessions: Dict[str, Dict] = {}
        self._composio = None
        self._registry = registry
        self._phi_fn = phi_fn
        self._categories: List[str] = []
        self._tools_by_category: Dict[str, List[str]] = {}
        self._initialized = False

        # Auto-init if API key present
        if self._api_key:
            self._init_categories()

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    @property
    def categories(self) -> List[str]:
        return list(self._categories)

    def _get_client(self):
        """Lazy-load Composio client."""
        if self._composio is None:
            if not self._api_key:
                raise RuntimeError(
                    "COMPOSIO_API_KEY not set. "
                    "Get one at https://composio.dev"
                )
            try:
                from composio import Composio
                self._composio = Composio(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "composio package not installed. "
                    "Install with: pip install composio-core"
                )
        return self._composio

    def _init_categories(self):
        """Fetch available tool categories from Composio API."""
        if self._initialized:
            return
        self._initialized = True

        try:
            client = self._get_client()
            # Try fetching tool categories from API
            if hasattr(client, "get_tools") or hasattr(client, "tools"):
                tools_api = getattr(client, "tools", client)
                if hasattr(tools_api, "list_categories"):
                    cats = tools_api.list_categories()
                    self._categories = [c.name if hasattr(c, "name") else str(c) for c in cats]
                elif hasattr(tools_api, "list"):
                    tools = tools_api.list()
                    seen = set()
                    for t in tools:
                        cat = getattr(t, "category", None) or "unknown"
                        if cat not in seen:
                            seen.add(cat)
                            self._categories.append(cat)
                else:
                    self._categories = list(KNOWN_CATEGORIES)
            else:
                self._categories = list(KNOWN_CATEGORIES)
            logger.info("Composio: %d tool categories available", len(self._categories))
        except Exception as e:
            logger.warning("Composio API unavailable, using offline categories: %s", e)
            self._categories = list(KNOWN_CATEGORIES)

        # Register in unified registry if provided
        if self._registry is not None:
            self._register_tools()

    def _register_tools(self):
        """Register Composio tool categories in unified registry with composio: prefix."""
        try:
            from unified_registry import HandlerEntry
        except ImportError:
            logger.debug("unified_registry not available, skipping registration")
            return

        for cat in self._categories:
            affinity = CATEGORY_AFFINITY.get(cat, DEFAULT_AFFINITY)
            name = f"composio:{cat}"
            keywords = _category_keywords(cat)
            desc = (f"Composio {cat} tools "
                    f"(tension={affinity['tension']:.1f}, "
                    f"curiosity={affinity['curiosity']:.1f})")

            entry = HandlerEntry(
                name=name,
                source="tool",
                keywords=keywords,
                description=desc,
                handler=lambda intent, c=cat, **kw: self._exec_category(c, intent, **kw),
                priority=1,  # tool-level priority
            )
            self._registry._register(entry)

        logger.info("Registered %d composio categories in unified registry", len(self._categories))

    def _check_phi_gate(self) -> bool:
        """Check if current Phi meets Tier 2 threshold."""
        if self._phi_fn is None:
            return True  # no gating if no phi function
        try:
            phi = self._phi_fn()
            if phi < PHI_GATE_TIER2:
                logger.debug("Phi gate blocked: Phi=%.2f < %.1f (Tier 2)", phi, PHI_GATE_TIER2)
                return False
            return True
        except Exception:
            return True  # degrade gracefully

    def _exec_category(self, category: str, intent: str, **kwargs) -> Dict[str, Any]:
        """Execute a Composio action within a category."""
        if not self._check_phi_gate():
            return {
                "success": False,
                "error": f"Phi gate: consciousness Phi < {PHI_GATE_TIER2} (Tier 2 required)",
                "category": category,
            }
        return self.act_sync(intent, category_hint=category, **kwargs)

    # ─── Session management ───

    async def create_session(self, user_id: str = "default") -> Dict[str, Any]:
        """Create a Composio session for a user."""
        if user_id in self._sessions:
            return self._sessions[user_id]

        client = self._get_client()
        session = client.create(user_id)
        self._sessions[user_id] = {
            "user_id": user_id,
            "mcp_url": session.mcp.url,
            "mcp_headers": dict(session.mcp.headers),
        }
        logger.info("Composio session created for user: %s", user_id)
        return self._sessions[user_id]

    async def get_mcp_config(self, user_id: str = "default") -> Dict[str, Any]:
        """Get MCP server config dict for passing to providers."""
        session = await self.create_session(user_id)
        return {
            "composio": {
                "type": "http",
                "url": session["mcp_url"],
                "headers": session["mcp_headers"],
            }
        }

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())

    def close_session(self, user_id: str):
        self._sessions.pop(user_id, None)

    # ─── Natural language routing ───

    async def act(self, intent: str, user_id: str = "default",
                  category_hint: str = "", **kwargs) -> Dict[str, Any]:
        """Route natural language intent to a Composio action.

        Args:
            intent:        Natural language description of desired action.
            user_id:       User session ID.
            category_hint: Optional category to narrow tool search.

        Returns:
            Dict with success, action, result or error.
        """
        if not self.available:
            return {"success": False, "error": "COMPOSIO_API_KEY not set"}

        if not self._check_phi_gate():
            return {
                "success": False,
                "error": f"Phi gate: consciousness Phi < {PHI_GATE_TIER2} (Tier 2 required)",
            }

        try:
            client = self._get_client()
            session = await self.create_session(user_id)

            # Resolve action from intent
            action_name = _resolve_action(intent, category_hint)
            affinity = CATEGORY_AFFINITY.get(category_hint, DEFAULT_AFFINITY)

            # Execute via Composio
            if hasattr(client, "execute_action"):
                result = client.execute_action(
                    action=action_name,
                    params={"intent": intent, **kwargs},
                    user_id=user_id,
                )
            elif hasattr(client, "actions") and hasattr(client.actions, "execute"):
                result = client.actions.execute(
                    action=action_name,
                    params={"intent": intent, **kwargs},
                    entity_id=user_id,
                )
            else:
                return {"success": False, "error": "Composio client has no execute method"}

            return {
                "success": True,
                "action": action_name,
                "category": category_hint,
                "affinity": affinity,
                "result": result,
            }
        except Exception as e:
            logger.error("Composio act() failed: %s", e)
            return {"success": False, "error": str(e)}

    def act_sync(self, intent: str, category_hint: str = "", **kwargs) -> Dict[str, Any]:
        """Synchronous version of act() for registry handler use."""
        if not self.available:
            return {"success": False, "error": "COMPOSIO_API_KEY not set"}

        if not self._check_phi_gate():
            return {
                "success": False,
                "error": f"Phi gate: consciousness Phi < {PHI_GATE_TIER2} (Tier 2 required)",
            }

        try:
            client = self._get_client()
            action_name = _resolve_action(intent, category_hint)
            affinity = CATEGORY_AFFINITY.get(category_hint, DEFAULT_AFFINITY)

            if hasattr(client, "execute_action"):
                result = client.execute_action(
                    action=action_name,
                    params={"intent": intent, **kwargs},
                )
            elif hasattr(client, "actions") and hasattr(client.actions, "execute"):
                result = client.actions.execute(
                    action=action_name,
                    params={"intent": intent, **kwargs},
                )
            else:
                return {"success": False, "error": "Composio client has no execute method"}

            return {
                "success": True,
                "action": action_name,
                "category": category_hint,
                "affinity": affinity,
                "result": result,
            }
        except Exception as e:
            logger.error("Composio act_sync() failed: %s", e)
            return {"success": False, "error": str(e)}

    def get_affinity(self, category: str) -> Dict[str, float]:
        """Get consciousness affinity for a tool category."""
        return CATEGORY_AFFINITY.get(category, DEFAULT_AFFINITY)


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _category_keywords(category: str) -> List[str]:
    """Generate search keywords for a Composio tool category."""
    base = category.replace("_", " ")
    kw = [f"composio {base}", base, category]
    # Add common synonyms
    _synonyms = {
        "email": ["mail", "gmail", "send email", "inbox"],
        "messaging": ["chat", "slack", "discord", "message"],
        "communication": ["notify", "alert", "announce"],
        "productivity": ["task", "todo", "organize"],
        "developer_tools": ["github", "git", "code", "dev"],
        "project_management": ["jira", "linear", "sprint", "kanban"],
        "file_management": ["drive", "dropbox", "files", "upload"],
        "crm": ["salesforce", "hubspot", "contacts", "leads"],
        "analytics": ["metrics", "dashboard", "report", "data"],
        "social_media": ["twitter", "linkedin", "post", "share"],
        "finance": ["invoice", "payment", "accounting", "stripe"],
        "storage": ["s3", "cloud storage", "bucket"],
        "ci_cd": ["deploy", "pipeline", "build", "ci"],
        "code_management": ["repo", "pull request", "merge"],
        "database": ["sql", "query", "table", "schema"],
        "payment": ["pay", "charge", "billing", "subscription"],
    }
    kw.extend(_synonyms.get(category, []))
    return kw


def _resolve_action(intent: str, category_hint: str) -> str:
    """Map natural language intent to a Composio action name.

    Uses simple keyword matching as a fallback; the Composio API
    itself handles NL resolution when available.
    """
    intent_lower = intent.lower()
    # Common action patterns
    if "email" in intent_lower or "mail" in intent_lower:
        if "send" in intent_lower:
            return "GMAIL_SEND_EMAIL"
        if "read" in intent_lower or "check" in intent_lower:
            return "GMAIL_LIST_EMAILS"
        return "GMAIL_SEND_EMAIL"
    if "slack" in intent_lower or "message" in intent_lower:
        return "SLACK_SEND_MESSAGE"
    if "calendar" in intent_lower or "schedule" in intent_lower or "meeting" in intent_lower:
        return "GOOGLE_CALENDAR_CREATE_EVENT"
    if "github" in intent_lower:
        if "issue" in intent_lower:
            return "GITHUB_CREATE_ISSUE"
        if "pr" in intent_lower or "pull" in intent_lower:
            return "GITHUB_CREATE_PULL_REQUEST"
        return "GITHUB_LIST_REPOS"
    if "notion" in intent_lower:
        return "NOTION_CREATE_PAGE"
    if "jira" in intent_lower or "ticket" in intent_lower:
        return "JIRA_CREATE_ISSUE"
    if "linear" in intent_lower:
        return "LINEAR_CREATE_ISSUE"
    # Default: use category hint as action prefix
    if category_hint:
        return f"{category_hint.upper()}_EXECUTE"
    return "COMPOSIO_NATURAL_LANGUAGE"
