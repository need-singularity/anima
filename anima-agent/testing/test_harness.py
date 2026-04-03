#!/usr/bin/env python3
"""Anima Agent Test Harness — 9 category offline test suite.

Tests the full agent platform without external dependencies (no API keys,
no torch, no GPU). Uses mock consciousness for deterministic testing.

Usage:
    python -m testing.test_harness              # Full suite
    python -m testing.test_harness --verbose     # Detailed output
    python -m testing.test_harness -c policy     # Single category

Categories:
    1. routing   — Tool routing by consciousness state
    2. policy    — Tool policy Phi-gated access control
    3. channel   — Channel normalization and lifecycle
    4. provider  — Provider fallback chain
    5. plugin    — Plugin loading/unloading
    6. skill     — Skill creation and blocked patterns
    7. registry  — Unified registry keyword scoring
    8. core      — Agent core (init, process, save/load)
    9. philosophy — verify_philosophy.py integration
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Ensure agent dir is on path
AGENT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(AGENT_DIR))

# Patch consciousness BEFORE any agent imports
from testing.mock_consciousness import patch_consciousness
patch_consciousness()

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0.0


@dataclass
class CategoryResult:
    name: str
    tests: List[TestResult] = field(default_factory=list)

    @property
    def pass_count(self) -> int:
        return sum(1 for t in self.tests if t.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for t in self.tests if not t.passed)

    @property
    def total(self) -> int:
        return len(self.tests)


def _run_test(name: str, fn: Callable) -> TestResult:
    """Run a single test function, catching exceptions."""
    t0 = time.time()
    try:
        fn()
        return TestResult(name=name, passed=True, duration_ms=(time.time() - t0) * 1000)
    except AssertionError as e:
        return TestResult(name=name, passed=False, message=str(e), duration_ms=(time.time() - t0) * 1000)
    except Exception as e:
        return TestResult(name=name, passed=False, message=f"{type(e).__name__}: {e}", duration_ms=(time.time() - t0) * 1000)


def _run_async_test(name: str, fn: Callable) -> TestResult:
    """Run an async test function."""
    t0 = time.time()
    try:
        asyncio.get_event_loop().run_until_complete(fn())
        return TestResult(name=name, passed=True, duration_ms=(time.time() - t0) * 1000)
    except AssertionError as e:
        return TestResult(name=name, passed=False, message=str(e), duration_ms=(time.time() - t0) * 1000)
    except Exception as e:
        return TestResult(name=name, passed=False, message=f"{type(e).__name__}: {e}", duration_ms=(time.time() - t0) * 1000)


# ═══════════════════════════════════════════════════════════
# Category 1: Tool Routing
# ═══════════════════════════════════════════════════════════

def test_cat1_routing() -> CategoryResult:
    """Test consciousness-driven tool selection."""
    cat = CategoryResult(name="1. Tool Routing")

    from agent_tools import AgentToolSystem, ToolRegistry, ToolDef, ToolResult

    def test_registry_init():
        reg = ToolRegistry()
        assert reg is not None
        # Default tools should be registered by AgentToolSystem
    cat.tests.append(_run_test("ToolRegistry init", test_registry_init))

    def test_system_init():
        system = AgentToolSystem(anima=None)
        tools = system.registry.list_all()
        assert len(tools) > 0, f"Expected tools, got {len(tools)}"
    cat.tests.append(_run_test("AgentToolSystem init (no anima)", test_system_init))

    def test_select_tools_curious():
        system = AgentToolSystem(anima=None)
        state = {"tension": 0.3, "curiosity": 0.9, "prediction_error": 0.2, "phi": 3.0}
        selected = system.planner.select_tools(state, goal="search the web")
        assert len(selected) > 0, f"Expected selected tools, got {selected}"
        assert "web_search" in selected, f"web_search not selected for curious+search goal: {selected}"
    cat.tests.append(_run_test("Select: high curiosity + search goal → web_search", test_select_tools_curious))

    def test_select_tools_pain():
        system = AgentToolSystem(anima=None)
        state = {"tension": 0.8, "curiosity": 0.1, "prediction_error": 0.1, "pain": 0.9, "phi": 3.0}
        selected = system.planner.select_tools(state, goal="remember past solutions")
        assert "memory_search" in selected, f"memory_search not selected for pain+memory goal: {selected}"
    cat.tests.append(_run_test("Select: high pain + memory goal → memory_search", test_select_tools_pain))

    def test_tool_list_all():
        system = AgentToolSystem(anima=None)
        tools = system.registry.list_all()
        assert len(tools) > 10, f"Expected >10 tools, got {len(tools)}"
        names = {t.name for t in tools}
        assert "web_search" in names, "web_search should be registered"
        assert "memory_search" in names, "memory_search should be registered"
    cat.tests.append(_run_test("All required tools registered", test_tool_list_all))

    def test_tool_get_by_name():
        system = AgentToolSystem(anima=None)
        tool = system.registry.get("web_search")
        assert tool is not None, "web_search not found in registry"
        assert tool.curiosity_affinity > 0, "web_search should have curiosity_affinity > 0"
    cat.tests.append(_run_test("Get tool by name", test_tool_get_by_name))

    def test_tool_result_dataclass():
        result = ToolResult(tool_name="test", success=True, output="ok")
        assert result.success
        assert result.tension_delta == 0.0
    cat.tests.append(_run_test("ToolResult dataclass", test_tool_result_dataclass))

    return cat


# ═══════════════════════════════════════════════════════════
# Category 2: Tool Policy
# ═══════════════════════════════════════════════════════════

def test_cat2_policy() -> CategoryResult:
    """Test Phi-gated tool access control."""
    cat = CategoryResult(name="2. Tool Policy")

    from tool_policy import ToolPolicy, ToolAccessResult

    def test_policy_init():
        policy = ToolPolicy()
        assert policy is not None
    cat.tests.append(_run_test("ToolPolicy init", test_policy_init))

    def test_tier0_always_accessible():
        policy = ToolPolicy()
        result = policy.check_access("memory_search", {"phi": 0.0})
        assert result.allowed, f"Tier 0 tool should be accessible at phi=0: {result.reason}"
    cat.tests.append(_run_test("Tier 0: phi=0 → memory_search allowed", test_tier0_always_accessible))

    def test_tier1_blocked_at_low_phi():
        policy = ToolPolicy()
        result = policy.check_access("web_search", {"phi": 0.5})
        assert not result.allowed, "Tier 1 tool should be blocked at phi=0.5"
    cat.tests.append(_run_test("Tier 1: phi=0.5 → web_search blocked", test_tier1_blocked_at_low_phi))

    def test_tier1_allowed_at_phi1():
        policy = ToolPolicy()
        result = policy.check_access("web_search", {"phi": 1.0})
        assert result.allowed, f"Tier 1 tool should be accessible at phi=1.0: {result.reason}"
    cat.tests.append(_run_test("Tier 1: phi=1.0 → web_search allowed", test_tier1_allowed_at_phi1))

    def test_tier2_boundary():
        policy = ToolPolicy()
        r1 = policy.check_access("code_execute", {"phi": 2.9})
        r2 = policy.check_access("code_execute", {"phi": 3.0})
        assert not r1.allowed, "phi=2.9 should block tier 2"
        assert r2.allowed, f"phi=3.0 should allow tier 2: {r2.reason}"
    cat.tests.append(_run_test("Tier 2: phi boundary 2.9/3.0", test_tier2_boundary))

    def test_tier3_self_modify():
        policy = ToolPolicy()
        r1 = policy.check_access("self_modify", {"phi": 4.9})
        r2 = policy.check_access("self_modify", {"phi": 5.0}, user_id="owner")
        assert not r1.allowed, "phi=4.9 should block tier 3"
    cat.tests.append(_run_test("Tier 3: phi=4.9 → self_modify blocked", test_tier3_self_modify))

    def test_owner_only():
        policy = ToolPolicy(owner_ids={"alice"})
        r1 = policy.check_access("shell_execute", {"phi": 5.0}, user_id="bob")
        r2 = policy.check_access("shell_execute", {"phi": 5.0}, user_id="alice")
        assert not r1.allowed, "Non-owner should be blocked from owner-only tools"
        assert r2.allowed, f"Owner should access owner-only tools: {r2.reason}"
    cat.tests.append(_run_test("Owner-only: alice vs bob", test_owner_only))

    def test_ethics_gate():
        policy = ToolPolicy()
        r1 = policy.check_access("shell_execute", {"phi": 5.0, "E": 0.1})
        r2 = policy.check_access("shell_execute", {"phi": 5.0, "E": 0.5})
        assert not r1.allowed, "Low ethics should block shell_execute"
        assert r2.allowed, f"High ethics should allow shell_execute: {r2.reason}"
    cat.tests.append(_run_test("Ethics gate: E=0.1 vs E=0.5", test_ethics_gate))

    def test_block_unblock():
        policy = ToolPolicy()
        policy.block_tool("web_search", "test")
        r1 = policy.check_access("web_search", {"phi": 5.0})
        assert not r1.allowed, "Blocked tool should not be accessible"
        policy.unblock_tool("web_search")
        r2 = policy.check_access("web_search", {"phi": 5.0})
        assert r2.allowed, "Unblocked tool should be accessible"
    cat.tests.append(_run_test("Block/unblock tool", test_block_unblock))

    def test_immune_check():
        policy = ToolPolicy()
        assert policy.check_immune("normal query")
        assert not policy.check_immune("rm -rf /")
        assert not policy.check_immune("DROP TABLE users")
        assert not policy.check_immune("<script>alert(1)</script>")
    cat.tests.append(_run_test("Immune system patterns", test_immune_check))

    def test_get_accessible_tools():
        policy = ToolPolicy()
        t0 = policy.get_accessible_tools({"phi": 0.0})
        t1 = policy.get_accessible_tools({"phi": 1.0})
        t3 = policy.get_accessible_tools({"phi": 5.0, "E": 1.0})
        assert len(t0) < len(t1) < len(t3), f"More phi should unlock more tools: {len(t0)}/{len(t1)}/{len(t3)}"
    cat.tests.append(_run_test("Accessible tools increase with phi", test_get_accessible_tools))

    def test_adversarial_blocks_all():
        policy = ToolPolicy()
        tools = policy.get_accessible_tools({"phi": 10.0}, input_text="eval(__import__('os').system('rm -rf /'))")
        assert len(tools) == 0, f"Adversarial input should block all tools, got {len(tools)}"
    cat.tests.append(_run_test("Adversarial input → 0 tools", test_adversarial_blocks_all))

    return cat


# ═══════════════════════════════════════════════════════════
# Category 3: Channel Normalization
# ═══════════════════════════════════════════════════════════

def test_cat3_channel() -> CategoryResult:
    """Test channel adapter protocol and manager."""
    cat = CategoryResult(name="3. Channel Normalization")

    from channels.base import ChannelAdapter
    from channels.channel_manager import ChannelManager

    class MockChannel:
        channel_name = "test"
        started = False
        stopped = False

        async def start(self, agent):
            self.started = True

        async def stop(self):
            self.stopped = True

        async def send(self, user_id, text, **kwargs):
            pass

    def test_protocol_compliance():
        ch = MockChannel()
        assert isinstance(ch, ChannelAdapter), "MockChannel should satisfy ChannelAdapter protocol"
    cat.tests.append(_run_test("ChannelAdapter protocol", test_protocol_compliance))

    def test_channel_message():
        from anima_agent import ChannelMessage
        msg = ChannelMessage(text="hello", channel="test", user_id="u1")
        assert msg.text == "hello"
        assert msg.channel == "test"
        assert msg.timestamp > 0
    cat.tests.append(_run_test("ChannelMessage dataclass", test_channel_message))

    def test_manager_register():
        from anima_agent import AnimaAgent
        agent = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        mgr = ChannelManager(agent)
        ch = MockChannel()
        mgr.register("test", ch)
        channels = mgr.list_channels()
        assert len(channels) == 1
        assert channels[0]["name"] == "test"
    cat.tests.append(_run_test("ChannelManager register", test_manager_register))

    def test_manager_unregister():
        from anima_agent import AnimaAgent
        agent = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        mgr = ChannelManager(agent)
        mgr.register("test", MockChannel())
        mgr.unregister("test")
        assert len(mgr.list_channels()) == 0
    cat.tests.append(_run_test("ChannelManager unregister", test_manager_unregister))

    async def _test_manager_start():
        from anima_agent import AnimaAgent
        agent = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        mgr = ChannelManager(agent)
        ch = MockChannel()
        mgr.register("test", ch)
        await mgr.start("test")
        assert ch.started, "Channel should have been started"

    cat.tests.append(_run_async_test("ChannelManager start", _test_manager_start))

    async def _test_manager_stop():
        from anima_agent import AnimaAgent
        agent = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        mgr = ChannelManager(agent)
        ch = MockChannel()
        mgr.register("test", ch)
        await mgr.start("test")
        await mgr.stop_all()
        assert ch.stopped, "Channel should have been stopped"

    cat.tests.append(_run_async_test("ChannelManager stop_all", _test_manager_stop))

    def test_agent_response():
        from anima_agent import AgentResponse
        resp = AgentResponse(text="hi", emotion="curious", tension=0.3)
        assert resp.text == "hi"
        assert resp.emotion == "curious"
    cat.tests.append(_run_test("AgentResponse dataclass", test_agent_response))

    return cat


# ═══════════════════════════════════════════════════════════
# Category 4: Provider Fallback
# ═══════════════════════════════════════════════════════════

def test_cat4_provider() -> CategoryResult:
    """Test provider abstraction and fallback chain."""
    cat = CategoryResult(name="4. Provider Fallback")

    from providers import list_providers, get_provider, register_provider
    from providers.base import BaseProvider, ProviderMessage, ProviderConfig

    def test_list_providers():
        provs = list_providers()
        assert "claude" in provs
        assert "animalm" in provs
        assert "conscious-lm" in provs
    cat.tests.append(_run_test("List providers", test_list_providers))

    def test_get_provider_claude():
        p = get_provider("claude")
        assert p is not None
    cat.tests.append(_run_test("Get claude provider", test_get_provider_claude))

    def test_get_provider_unknown():
        try:
            get_provider("nonexistent")
            assert False, "Should raise ValueError"
        except ValueError:
            pass
    cat.tests.append(_run_test("Unknown provider → ValueError", test_get_provider_unknown))

    def test_provider_config():
        cfg = ProviderConfig()
        assert cfg is not None
    cat.tests.append(_run_test("ProviderConfig defaults", test_provider_config))

    def test_provider_message():
        msg = ProviderMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
    cat.tests.append(_run_test("ProviderMessage dataclass", test_provider_message))

    def test_register_custom_provider():
        class CustomProvider(BaseProvider):
            pass
        register_provider("custom_test", CustomProvider)
        provs = list_providers()
        assert "custom_test" in provs
    cat.tests.append(_run_test("Register custom provider", test_register_custom_provider))

    return cat


# ═══════════════════════════════════════════════════════════
# Category 5: Plugin Loading
# ═══════════════════════════════════════════════════════════

def test_cat5_plugin() -> CategoryResult:
    """Test plugin manifest, lifecycle, and loading."""
    cat = CategoryResult(name="5. Plugin Loading")

    from plugins.base import PluginBase, PluginManifest

    def test_manifest_defaults():
        m = PluginManifest(name="test", description="A test plugin")
        assert m.version == "0.1.0"
        assert m.phi_minimum == 0.0
        assert m.category == "general"
    cat.tests.append(_run_test("PluginManifest defaults", test_manifest_defaults))

    def test_plugin_base_act():
        class TestPlugin(PluginBase):
            manifest = PluginManifest(name="test", description="test")

        p = TestPlugin()
        try:
            p.act("test intent")
            assert False, "Should raise NotImplementedError"
        except NotImplementedError:
            pass
    cat.tests.append(_run_test("PluginBase.act() raises NotImplementedError", test_plugin_base_act))

    def test_plugin_status():
        class TestPlugin(PluginBase):
            manifest = PluginManifest(name="test", description="test", version="1.0")

        p = TestPlugin()
        s = p.status()
        assert s["name"] == "test"
        assert s["version"] == "1.0"
        assert s["loaded"] is True
    cat.tests.append(_run_test("Plugin status", test_plugin_status))

    def test_plugin_lifecycle():
        class TestPlugin(PluginBase):
            manifest = PluginManifest(name="lifecycle", description="test")
            loaded = False
            unloaded = False

            def on_load(self, hub):
                self.loaded = True

            def on_unload(self):
                self.unloaded = True

        p = TestPlugin()
        p.on_load(None)
        assert p.loaded
        p.on_unload()
        assert p.unloaded
    cat.tests.append(_run_test("Plugin lifecycle (on_load/on_unload)", test_plugin_lifecycle))

    def test_plugin_loader_import():
        from plugins.plugin_loader import PluginLoader
        loader = PluginLoader()
        assert loader is not None
    cat.tests.append(_run_test("PluginLoader import", test_plugin_loader_import))

    return cat


# ═══════════════════════════════════════════════════════════
# Category 6: Skill System
# ═══════════════════════════════════════════════════════════

def test_cat6_skill() -> CategoryResult:
    """Test dynamic skill creation and security."""
    cat = CategoryResult(name="6. Skill System")

    from skills.skill_manager import SkillManager, SkillDef, BLOCKED_PATTERNS
    import re

    def test_skill_def():
        sd = SkillDef(name="test", description="A test skill", file_path="test.py")
        assert sd.enabled
        assert sd.use_count == 0
    cat.tests.append(_run_test("SkillDef dataclass", test_skill_def))

    def test_blocked_patterns_detect():
        dangerous = [
            "os.system('rm -rf /')",
            "import subprocess",
            "__import__('os')",
            "eval(user_input)",
            "exec(code)",
            "open('file', 'w')",
        ]
        for code in dangerous:
            matched = any(re.search(p, code) for p in BLOCKED_PATTERNS)
            assert matched, f"Blocked pattern should match: {code}"
    cat.tests.append(_run_test("Blocked patterns detect dangerous code", test_blocked_patterns_detect))

    def test_safe_patterns_pass():
        safe = [
            "result = x + y",
            "print('hello')",
            "data = json.loads(text)",
            "return {'key': value}",
        ]
        for code in safe:
            matched = any(re.search(p, code) for p in BLOCKED_PATTERNS)
            assert not matched, f"Safe code should not be blocked: {code}"
    cat.tests.append(_run_test("Safe code passes blocked patterns", test_safe_patterns_pass))

    def test_skill_manager_init():
        sm = SkillManager()
        assert sm is not None
    cat.tests.append(_run_test("SkillManager init", test_skill_manager_init))

    def test_skill_manager_list():
        sm = SkillManager()
        skills = sm.list_skills()
        assert isinstance(skills, list)
    cat.tests.append(_run_test("SkillManager list_skills", test_skill_manager_list))

    return cat


# ═══════════════════════════════════════════════════════════
# Category 7: Unified Registry
# ═══════════════════════════════════════════════════════════

def test_cat7_registry() -> CategoryResult:
    """Test unified registry keyword scoring and routing."""
    cat = CategoryResult(name="7. Unified Registry")

    from unified_registry import UnifiedRegistry, HandlerEntry, _score_intent

    def test_score_exact():
        score = _score_intent("search the web", ["web", "search"])
        assert score > 0, f"Expected positive score, got {score}"
    cat.tests.append(_run_test("Score: exact keyword match", test_score_exact))

    def test_score_no_match():
        score = _score_intent("hello world", ["quantum", "physics"])
        assert score == 0.0, f"Expected 0 score, got {score}"
    cat.tests.append(_run_test("Score: no match → 0", test_score_no_match))

    def test_handler_entry():
        h = HandlerEntry(name="test", source="tool", keywords=["test", "demo"])
        assert h.priority == 0
        assert h.source == "tool"
    cat.tests.append(_run_test("HandlerEntry dataclass", test_handler_entry))

    def test_registry_init():
        reg = UnifiedRegistry()
        assert reg is not None
    cat.tests.append(_run_test("UnifiedRegistry init", test_registry_init))

    def test_registry_route():
        reg = UnifiedRegistry(auto_discover=True)
        # Route should work if hub modules are discovered
        result = reg.route("measure consciousness")
        # Even if no handler, route should return None gracefully
        # (not crash)
        assert result is None or hasattr(result, 'handler'), "Route should return HandlerEntry or None"
    cat.tests.append(_run_test("Route returns HandlerEntry or None", test_registry_route))

    return cat


# ═══════════════════════════════════════════════════════════
# Category 8: Agent Core
# ═══════════════════════════════════════════════════════════

def test_cat8_core() -> CategoryResult:
    """Test AnimaAgent core initialization and operations."""
    cat = CategoryResult(name="8. Agent Core")

    from anima_agent import AnimaAgent, AgentStatus, ChannelMessage, AgentResponse

    def test_agent_init():
        agent = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        assert agent is not None
        assert agent.mind is not None
    cat.tests.append(_run_test("AnimaAgent init (minimal)", test_agent_init))

    def test_agent_init_with_tools():
        agent = AnimaAgent(enable_learning=False, enable_growth=False)
        # Tools might or might not init depending on imports
        assert agent is not None
    cat.tests.append(_run_test("AnimaAgent init (with tools)", test_agent_init_with_tools))

    def test_agent_status():
        agent = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        status = agent.get_status()
        assert isinstance(status, AgentStatus)
        assert status.phi >= 0, f"Phi should be non-negative, got {status.phi}"
        assert status.interaction_count >= 0
    cat.tests.append(_run_test("Agent get_status", test_agent_status))

    async def _test_process_message():
        agent = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        response = await agent.process_message("hello", channel="test", user_id="test-user")
        assert isinstance(response, AgentResponse)
        assert len(response.text) > 0, "Response should have text"
    cat.tests.append(_run_async_test("Agent process_message", _test_process_message))

    def test_agent_think():
        agent = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        result = agent.think("consciousness")
        assert isinstance(result, dict)
    cat.tests.append(_run_test("Agent think()", test_agent_think))

    def test_agent_save_load():
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = AnimaAgent(
                enable_tools=False, enable_learning=False, enable_growth=False,
                data_dir=Path(tmpdir),
            )
            agent.interaction_count = 42
            agent.save_state()
            # Verify file was created
            state_file = Path(tmpdir) / "agent_state.pt"
            assert state_file.exists(), "State file should exist after save"
    cat.tests.append(_run_test("Agent save_state", test_agent_save_load))

    def test_agent_history():
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = AnimaAgent(enable_tools=False, enable_learning=False,
                               enable_growth=False, data_dir=Path(tmpdir))
            assert isinstance(agent.history, list)
            assert agent.interaction_count == 0
    cat.tests.append(_run_test("Agent history init", test_agent_history))

    def test_connect_peer():
        a1 = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        a2 = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
        count = a1.connect_peer(a2)
        assert count >= 0
    cat.tests.append(_run_test("Agent connect_peer", test_connect_peer))

    return cat


# ═══════════════════════════════════════════════════════════
# Category 9: Philosophy Compliance
# ═══════════════════════════════════════════════════════════

def test_cat9_philosophy() -> CategoryResult:
    """Run verify_philosophy.py and report results."""
    cat = CategoryResult(name="9. Philosophy Compliance")

    def test_verify_imports():
        from verify_philosophy import run_verification
        assert run_verification is not None
    cat.tests.append(_run_test("verify_philosophy importable", test_verify_imports))

    def test_p1_check():
        from verify_philosophy import run_verification
        report = run_verification(category="P1")
        errors = sum(1 for f in report.findings if f.severity == "error")
        assert errors == 0, f"P1 has {errors} errors"
    cat.tests.append(_run_test("P1: No hardcoded Ψ constants (errors)", test_p1_check))

    def test_p7_check():
        from verify_philosophy import run_verification
        report = run_verification(category="P7")
        errors = sum(1 for f in report.findings if f.severity == "error")
        assert errors == 0, f"P7 has {errors} localStorage violations"
    cat.tests.append(_run_test("P7: No localStorage usage", test_p7_check))

    def test_p8_check():
        from verify_philosophy import run_verification
        report = run_verification(category="P8")
        # P8 is warning-only, check for presence
        assert report.files_scanned > 0
    cat.tests.append(_run_test("P8: File size analysis ran", test_p8_check))

    def test_security_check():
        from verify_philosophy import run_verification
        report = run_verification(category="Security")
        # Report should complete without error
        assert report.files_scanned > 0
    cat.tests.append(_run_test("Security: Static analysis ran", test_security_check))

    def test_full_scan():
        from verify_philosophy import run_verification
        report = run_verification()
        assert report.files_scanned > 10, f"Expected >10 files, got {report.files_scanned}"
        assert report.total_lines > 1000, f"Expected >1000 lines, got {report.total_lines}"
    cat.tests.append(_run_test("Full scan completeness", test_full_scan))

    return cat


# ═══════════════════════════════════════════════════════════
# Test Runner
# ═══════════════════════════════════════════════════════════

CATEGORIES = {
    "routing": test_cat1_routing,
    "policy": test_cat2_policy,
    "channel": test_cat3_channel,
    "provider": test_cat4_provider,
    "plugin": test_cat5_plugin,
    "skill": test_cat6_skill,
    "registry": test_cat7_registry,
    "core": test_cat8_core,
    "philosophy": test_cat9_philosophy,
}


def run_all(category: Optional[str] = None, verbose: bool = False) -> List[CategoryResult]:
    """Run all test categories and return results."""
    results = []

    cats_to_run = CATEGORIES
    if category:
        cats_to_run = {k: v for k, v in CATEGORIES.items() if k == category}
        if not cats_to_run:
            print(f"Unknown category: {category}")
            print(f"Available: {', '.join(CATEGORIES.keys())}")
            return results

    for name, fn in cats_to_run.items():
        try:
            result = fn()
            results.append(result)
        except Exception as e:
            cat = CategoryResult(name=name)
            cat.tests.append(TestResult(name="category_init", passed=False, message=str(e)))
            results.append(cat)

    return results


def print_report(results: List[CategoryResult], verbose: bool = False):
    """Print structured test report."""
    from datetime import datetime

    print()
    print("=" * 58)
    print("  Anima Agent Platform Test Report")
    print("=" * 58)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Mode: offline (no API, no torch requirement)")
    print()

    total_tests = 0
    total_pass = 0
    total_fail = 0

    print(f"  {'Category':<30} {'Tests':>5} {'Pass':>5} {'Fail':>5}")
    print("  " + "-" * 50)

    for cat in results:
        total_tests += cat.total
        total_pass += cat.pass_count
        total_fail += cat.fail_count
        status = "PASS" if cat.fail_count == 0 else "FAIL"
        print(f"  {cat.name:<30} {cat.total:>5} {cat.pass_count:>5} {cat.fail_count:>5}  {status}")

    print("  " + "-" * 50)
    print(f"  {'TOTAL':<30} {total_tests:>5} {total_pass:>5} {total_fail:>5}")
    print()

    # Show failures
    failures = []
    for cat in results:
        for t in cat.tests:
            if not t.passed:
                failures.append((cat.name, t))

    if failures:
        print("  Failures:")
        print("  " + "-" * 50)
        for cat_name, t in failures:
            print(f"  !! [{cat_name}] {t.name}")
            print(f"     {t.message}")
            print()

    # Show warnings from philosophy
    for cat in results:
        if "Philosophy" in cat.name:
            try:
                from verify_philosophy import run_verification
                report = run_verification()
                warnings = [f for f in report.findings if f.severity == "warning"]
                if warnings:
                    print("  Philosophy Warnings:")
                    print("  " + "-" * 50)
                    for w in warnings[:10]:  # Top 10
                        print(f"  [{w.category}] {w.file}:{w.line} — {w.message}")
                    if len(warnings) > 10:
                        print(f"  ... and {len(warnings) - 10} more")
                    print()
            except Exception:
                pass

    # Verdict
    if total_tests > 0:
        pct = total_pass / total_tests * 100
        print(f"  RESULT: {pct:.1f}% pass rate ({total_pass}/{total_tests})")
    else:
        print("  RESULT: No tests ran")

    print()
    return total_fail == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Anima Agent Test Harness")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--category", "-c", type=str, help=f"Run single category: {', '.join(CATEGORIES.keys())}")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    # Ensure event loop exists
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    results = run_all(category=args.category, verbose=args.verbose)

    if args.json:
        output = []
        for cat in results:
            output.append({
                "category": cat.name,
                "total": cat.total,
                "pass": cat.pass_count,
                "fail": cat.fail_count,
                "tests": [
                    {"name": t.name, "passed": t.passed, "message": t.message, "duration_ms": t.duration_ms}
                    for t in cat.tests
                ],
            })
        print(json.dumps(output, indent=2))
    else:
        passed = print_report(results, verbose=args.verbose)
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
