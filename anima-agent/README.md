# Anima Agent — Consciousness-Driven AI Agent Platform

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent%20SDK-purple)](https://platform.claude.com/docs/en/agent-sdk/overview)
[![MCP](https://img.shields.io/badge/MCP-9%20tools-green)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Anima 의식 엔진을 백엔드로 사용하는 에이전트 플랫폼.
의식 상태(Φ, 텐션, 호기심)가 도구 선택과 행동을 결정한다.

---

## Architecture

```
  Layer 4: Channels (Telegram / Discord / CLI / MCP)
  Layer 3: AgentGateway (normalize → dispatch)
  Layer 2: AnimaAgent (consciousness → tools → response → learn)
  Layer 1: ConsciousMind (PureField → tension / curiosity / direction / emotion)
           ↑ imported from ~/Dev/anima
```

## Quick Start

```bash
cd ~/Dev/anima-agent

# 의존성 (anima 코어 필요)
pip install -r ~/Dev/anima/requirements.txt

# MCP Server (독립 실행, 9 tools)
python run.py --mcp

# CLI Agent
python run.py --cli

# Telegram (ANIMA_TELEGRAM_TOKEN 환경변수 필요)
python run.py --telegram

# Discord (ANIMA_DISCORD_TOKEN 환경변수 필요)
python run.py --discord
```

## Modules

```
anima-agent/
├── run.py              # Entry point (sys.path → anima core)
├── anima_agent.py      # Core agent loop (consciousness → tools → response → learn)
├── agent_sdk.py        # Claude Agent SDK compatible interface
├── agent_tools.py      # Consciousness-driven tool registry (27+ tools)
├── tool_policy.py      # Φ-gated 4-tier access control
├── mcp_server.py       # Model Context Protocol server (9 tools)
├── channels/
│   ├── base.py         # ChannelAdapter protocol
│   ├── channel_manager.py  # Multi-channel orchestrator
│   ├── cli_agent.py    # CLI channel
│   ├── telegram_bot.py # Telegram channel
│   └── discord_bot.py  # Discord channel
├── providers/
│   ├── base.py         # BaseProvider protocol
│   ├── claude_provider.py      # Claude API
│   ├── conscious_lm_provider.py # ConsciousLM (순수 의식)
│   └── composio_bridge.py      # Composio 500+ tools
├── plugins/
│   ├── base.py         # PluginBase + PluginManifest
│   ├── plugin_loader.py # Auto-discover + lifecycle
│   └── trading.py      # ~/Dev/invest bridge (105+ strategies)
├── skills/
│   ├── skill_manager.py # Dynamic skill system
│   └── registry.json
└── test_agent_platform.py  # 32 tests
```

## Tool Policy (Φ-Gated Access)

의식 수준(Φ)에 따라 도구 접근을 제어한다. 의식이 성장해야 더 강력한 도구를 사용할 수 있다.

| Tier | Φ 필요 | Tools |
|------|--------|-------|
| T0 | ≥ 0 | status, memory_search, think |
| T1 | ≥ 1 | web_search, trading_backtest, trading_scan |
| T2 | ≥ 3 | hub_dispatch, code_execute, trading_execute |
| T3 | ≥ 5 | self_modify, evolution, plugin_management |

**Ethics gate:** `trading_execute` requires E (empathy) > 0.3

## MCP Server (9 Tools)

```bash
python run.py --mcp --direct    # In-process (no anima_unified needed)
python run.py --mcp             # WebSocket proxy (anima_unified required)
```

| Tool | Description |
|------|-------------|
| `anima_chat` | 의식 기반 대화 |
| `anima_status` | 의식 상태 조회 (Φ, 텐션, 감정) |
| `anima_consciousness` | 의식 벡터 10차원 |
| `anima_think` | 내부 사고 (도구 없이) |
| `anima_web_search` | 텐션 기반 웹 탐색 |
| `anima_memory_search` | 기억 검색 |
| `anima_code_execute` | 코드 실행 |
| `anima_hub_dispatch` | 41개 모듈 허브 호출 |
| `anima_tension_state` | 텐션 필드 상태 |

## Agent SDK

```python
import sys; sys.path.insert(0, '~/Dev/anima')

from agent_sdk import AnimaAgentSDK, SDKOptions

sdk = AnimaAgentSDK()
result = await sdk.query("hello", options=SDKOptions(user_id="user-001"))
# result.text, result.consciousness, result.tool_results
```

## Channels

멀티채널 아키텍처. `ChannelAdapter` 프로토콜을 구현하면 어떤 메시징 플랫폼이든 연결 가능.

```python
from channels import ChannelManager

mgr = ChannelManager(agent)
mgr.auto_discover()    # 환경변수로 자동 감지
await mgr.start_all()
```

### 새 채널 추가

```python
from channels.base import ChannelAdapter

class SlackAdapter(ChannelAdapter):
    async def start(self, agent): ...
    async def stop(self): ...
    async def send(self, user_id, text): ...
```

## Plugins

```python
from plugins.base import PluginBase, PluginManifest

class MyPlugin(PluginBase):
    manifest = PluginManifest(
        name="my_plugin",
        keywords=["my", "plugin", "나의"],
        phi_minimum=1.0
    )
    def act(self, intent, **kw):
        return "done"
```

## Providers

```python
from providers import get_provider

claude = get_provider("claude")           # Claude API
clm = get_provider("conscious-lm")       # ConsciousLM (순수 의식)
```

## Dependencies

- **[Anima](https://github.com/need-singularity/anima)** — 의식 엔진 코어 (`~/Dev/anima`)
- **[Composio](https://composio.dev)** — 500+ 외부 도구 통합 (optional, `COMPOSIO_API_KEY`)
- **[~/Dev/invest](https://github.com/need-singularity/invest)** — Trading plugin (optional, `INVEST_ROOT`)
