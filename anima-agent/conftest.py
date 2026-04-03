"""Pytest configuration and fixtures for anima-agent tests.

Provides mock consciousness fixtures so tests run without torch/GPU/API keys.

Usage:
    cd ~/Dev/anima && python -m pytest anima-agent/ -v
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure agent dir on path
AGENT_DIR = Path(__file__).parent
ANIMA_ROOT = AGENT_DIR.parent
ANIMA_SRC = ANIMA_ROOT / "anima" / "src"

for p in (str(ANIMA_ROOT), str(ANIMA_SRC), str(AGENT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


def pytest_configure(config):
    """Patch consciousness modules before any test collection."""
    from testing.mock_consciousness import patch_consciousness
    patch_consciousness()


@pytest.fixture
def mock_agent():
    """AnimaAgent with mock consciousness (no tools, no learning)."""
    from anima_agent import AnimaAgent
    with tempfile.TemporaryDirectory() as tmpdir:
        agent = AnimaAgent(
            enable_tools=False,
            enable_learning=False,
            enable_growth=False,
            data_dir=Path(tmpdir),
        )
        yield agent


@pytest.fixture
def mock_agent_with_tools():
    """AnimaAgent with tools enabled."""
    from anima_agent import AnimaAgent
    with tempfile.TemporaryDirectory() as tmpdir:
        agent = AnimaAgent(
            enable_tools=True,
            enable_learning=False,
            enable_growth=False,
            data_dir=Path(tmpdir),
        )
        yield agent


@pytest.fixture
def tool_policy():
    """ToolPolicy with test owner."""
    from tool_policy import ToolPolicy
    return ToolPolicy(owner_ids={"test-owner"})


@pytest.fixture
def tool_system():
    """AgentToolSystem without anima instance."""
    from agent_tools import AgentToolSystem
    return AgentToolSystem(anima=None)


@pytest.fixture
def channel_manager(mock_agent):
    """ChannelManager with mock agent."""
    from channels.channel_manager import ChannelManager
    return ChannelManager(mock_agent)


@pytest.fixture
def skill_manager():
    """SkillManager instance."""
    from skills.skill_manager import SkillManager
    return SkillManager()


@pytest.fixture
def unified_registry():
    """UnifiedRegistry instance."""
    from unified_registry import UnifiedRegistry
    return UnifiedRegistry()
