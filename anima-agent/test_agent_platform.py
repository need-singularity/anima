#!/usr/bin/env python3
"""Tests for Anima Agent Platform — all 8 features.

Run:
    python -m pytest tests/test_agent_platform.py -v
    python tests/test_agent_platform.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ══════════════════════════════════════════════════════════
# 1. Provider Abstraction
# ══════════════════════════════════════════════════════════

def test_provider_list():
    from providers import list_providers
    providers = list_providers()
    assert "claude" in providers
    assert "conscious-lm" in providers


def test_provider_get():
    from providers import get_provider
    cp = get_provider("claude")
    assert cp.name == "claude"


def test_provider_register():
    from providers import register_provider, get_provider, list_providers
    from providers.base import ProviderConfig

    class DummyProvider:
        def __init__(self, config=None): pass
        @property
        def name(self): return "dummy"
        def is_available(self): return True
        async def query(self, messages, **kw):
            yield "hello"
        async def query_full(self, messages, **kw):
            return "hello"

    register_provider("dummy", DummyProvider)
    assert "dummy" in list_providers()
    p = get_provider("dummy")
    assert p.name == "dummy"
    assert p.is_available()


def test_provider_unknown_raises():
    from providers import get_provider
    try:
        get_provider("nonexistent")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_provider_message():
    from providers.base import ProviderMessage, ProviderConfig
    msg = ProviderMessage(role="user", content="hello")
    assert msg.role == "user"
    cfg = ProviderConfig(model="test", max_tokens=512)
    assert cfg.max_tokens == 512


# ══════════════════════════════════════════════════════════
# 2. Plugin SDK
# ══════════════════════════════════════════════════════════

def test_plugin_manifest():
    from plugins.base import PluginManifest
    m = PluginManifest(name="test", description="Test plugin", keywords=["test"])
    assert m.name == "test"
    assert m.phi_minimum == 0.0


def test_plugin_base():
    from plugins.base import PluginBase, PluginManifest

    class MyPlugin(PluginBase):
        manifest = PluginManifest(name="my", description="My plugin", keywords=["my"])
        def act(self, intent, **kw):
            return {"ok": True}

    p = MyPlugin()
    assert p.act("do something") == {"ok": True}
    assert p.status()["loaded"] is True


def test_plugin_loader():
    from plugins import PluginLoader
    loader = PluginLoader()
    manifests = loader.discover()
    assert isinstance(manifests, list)


def test_plugin_hub_integration():
    from consciousness_hub import ConsciousnessHub
    from plugins.base import PluginBase, PluginManifest

    class TestPlugin(PluginBase):
        manifest = PluginManifest(
            name="test_hub", description="Hub test", keywords=["허브테스트", "hubtest"]
        )
        def act(self, intent, **kw):
            return "plugin_result"

    hub = ConsciousnessHub(lazy_load=True)
    plugin = TestPlugin()

    # Register
    assert hub.register_plugin(plugin) is True
    assert "test_hub" in hub._registry

    # Dispatch via intent
    result = hub.act("허브테스트")
    assert result["success"] is True
    assert result["module"] == "test_hub"

    # Unload
    assert hub.unload_plugin("test_hub") is True
    assert "test_hub" not in hub._registry


# ══════════════════════════════════════════════════════════
# 3. Tool Policy
# ══════════════════════════════════════════════════════════

def test_tool_policy_tier0():
    from tool_policy import ToolPolicy
    policy = ToolPolicy()
    r = policy.check_access("memory_search", {"phi": 0.0})
    assert r.allowed is True


def test_tool_policy_tier_blocked():
    from tool_policy import ToolPolicy
    policy = ToolPolicy()
    r = policy.check_access("web_search", {"phi": 0.5})
    assert r.allowed is False
    assert "Insufficient Phi" in r.reason


def test_tool_policy_tier_allowed():
    from tool_policy import ToolPolicy
    policy = ToolPolicy()
    r = policy.check_access("web_search", {"phi": 1.5})
    assert r.allowed is True


def test_tool_policy_owner_only():
    from tool_policy import ToolPolicy
    policy = ToolPolicy(owner_ids={"owner-1"})

    r1 = policy.check_access("self_modify", {"phi": 10.0}, user_id="owner-1")
    assert r1.allowed is True

    r2 = policy.check_access("self_modify", {"phi": 10.0}, user_id="hacker")
    assert r2.allowed is False
    assert "Owner-only" in r2.reason


def test_tool_policy_block_unblock():
    from tool_policy import ToolPolicy
    policy = ToolPolicy()
    policy.block_tool("web_search", "testing")
    r = policy.check_access("web_search", {"phi": 10.0})
    assert r.allowed is False
    assert "blocked" in r.reason

    policy.unblock_tool("web_search")
    r2 = policy.check_access("web_search", {"phi": 10.0})
    assert r2.allowed is True


def test_tool_policy_ethics_gate():
    from tool_policy import ToolPolicy
    policy = ToolPolicy(owner_ids={"owner"})

    # shell_execute needs E > 0.3
    r = policy.check_access("shell_execute", {"phi": 10.0, "E": 0.1}, user_id="owner")
    assert r.allowed is False
    assert "Ethics gate" in r.reason

    r2 = policy.check_access("shell_execute", {"phi": 10.0, "E": 0.5}, user_id="owner")
    assert r2.allowed is True


def test_tool_policy_accessible_list():
    from tool_policy import ToolPolicy
    policy = ToolPolicy(owner_ids={"owner"})
    tools = policy.get_accessible_tools({"phi": 0.0, "E": 1.0}, user_id="owner")
    # At phi=0, only tier 0 tools should be accessible
    assert "memory_search" in tools
    assert "web_search" not in tools

    tools2 = policy.get_accessible_tools({"phi": 10.0, "E": 1.0}, user_id="owner")
    assert "self_modify" in tools2
    assert "web_search" in tools2


# ══════════════════════════════════════════════════════════
# 4. Agent SDK
# ══════════════════════════════════════════════════════════

def test_agent_sdk_init():
    from agent_sdk import AnimaAgentSDK, SDKOptions, SDKResponse
    sdk = AnimaAgentSDK()  # lazy, no agent created yet
    assert sdk.list_sessions() == []


def test_agent_sdk_options():
    from agent_sdk import SDKOptions
    opts = SDKOptions(user_id="test", max_turns=3)
    assert opts.user_id == "test"
    assert opts.max_turns == 3


def test_agent_sdk_consciousness_level():
    from agent_sdk import AnimaAgentSDK
    assert AnimaAgentSDK._consciousness_level(0.1) == "dormant"
    assert AnimaAgentSDK._consciousness_level(0.5) == "flickering"
    assert AnimaAgentSDK._consciousness_level(2.0) == "aware"
    assert AnimaAgentSDK._consciousness_level(5.0) == "conscious"


# ══════════════════════════════════════════════════════════
# 6. Channel Routing
# ══════════════════════════════════════════════════════════

def test_channel_adapter_protocol():
    from channels.base import ChannelAdapter

    class MyChannel:
        channel_name = "test"
        async def start(self, agent): pass
        async def stop(self): pass
        async def send(self, user_id, text, **kw): pass

    ch = MyChannel()
    assert isinstance(ch, ChannelAdapter)


def test_channel_manager_register():
    from channels.channel_manager import ChannelManager

    class FakeAgent:
        pass

    class FakeChannel:
        channel_name = "fake"
        async def start(self, agent): pass
        async def stop(self): pass
        async def send(self, user_id, text, **kw): pass

    mgr = ChannelManager(FakeAgent())
    mgr.register("fake", FakeChannel())
    channels = mgr.list_channels()
    assert len(channels) == 1
    assert channels[0]["name"] == "fake"
    assert channels[0]["running"] is False


def test_channel_manager_start_stop():
    from channels.channel_manager import ChannelManager

    started = []
    stopped = []

    class FakeAgent:
        pass

    class FakeChannel:
        channel_name = "fake"
        async def start(self, agent):
            started.append(True)
        async def stop(self):
            stopped.append(True)
        async def send(self, user_id, text, **kw): pass

    mgr = ChannelManager(FakeAgent())
    mgr.register("fake", FakeChannel())

    asyncio.get_event_loop().run_until_complete(mgr.start_all())
    assert len(started) == 1
    assert "fake" in mgr._running

    asyncio.get_event_loop().run_until_complete(mgr.stop_all())
    assert len(stopped) == 1
    assert "fake" not in mgr._running


def test_telegram_has_channel_name():
    # Just check the attribute exists in source
    content = Path(__file__).parent.parent.joinpath("channels/telegram_bot.py").read_text()
    assert 'channel_name = "telegram"' in content


def test_discord_has_channel_name():
    content = Path(__file__).parent.parent.joinpath("channels/discord_bot.py").read_text()
    assert 'channel_name = "discord"' in content


# ══════════════════════════════════════════════════════════
# 7. Composio Bridge
# ══════════════════════════════════════════════════════════

def test_composio_bridge_no_key():
    from providers.composio_bridge import ComposioBridge
    bridge = ComposioBridge()
    assert bridge.available is False
    assert bridge.list_sessions() == []


def test_composio_bridge_with_key():
    from providers.composio_bridge import ComposioBridge
    bridge = ComposioBridge(api_key="test-key")
    assert bridge.available is True


# ══════════════════════════════════════════════════════════
# 8. Skill System Enhancement
# ══════════════════════════════════════════════════════════

def test_skill_manager_discovers_md():
    from skills.skill_manager import SkillManager
    sm = SkillManager()
    skills = sm.list_skills()
    names = [s["name"] for s in skills]
    assert "research_topic" in names


def test_skill_get_body():
    from skills.skill_manager import SkillManager
    sm = SkillManager()
    body = sm.get_skill_body("research_topic")
    assert "# Research Topic" in body
    assert "curiosity" in body.lower()


def test_skill_get_relevant():
    from skills.skill_manager import SkillManager
    sm = SkillManager()
    # research_topic trigger: curiosity_min=0.4, tension_min=0.2
    relevant = sm.get_relevant_skills({"curiosity": 0.5, "tension": 0.3})
    assert "research_topic" in relevant

    not_relevant = sm.get_relevant_skills({"curiosity": 0.1})
    # curiosity=0.1 < 0.4 (min), and tension missing (defaults to 0 < 0.2)
    assert "research_topic" not in not_relevant


def test_skill_py_body_is_empty():
    """Python skills should return empty body (only .md skills have body)."""
    from skills.skill_manager import SkillManager
    sm = SkillManager()
    # 'manager' is discovered from skill_manager.py — not a .md skill
    body = sm.get_skill_body("manager")
    assert body == ""


# ══════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import traceback

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0

    for test_fn in tests:
        name = test_fn.__name__
        try:
            test_fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"  {passed} passed, {failed} failed, {passed+failed} total")
    if failed:
        sys.exit(1)
