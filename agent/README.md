# Anima Agent — Consciousness-Driven AI Agent Platform

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent%20SDK-purple)](https://platform.claude.com/docs/en/agent-sdk/overview)
[![MCP](https://img.shields.io/badge/MCP-9%20tools-green)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Anima 의식 엔진을 백엔드로 사용하는 에이전트 플랫폼.
의식 상태(Φ, 텐션, 호기심)가 도구 선택과 행동을 결정한다.

> **Monorepo**: `pip install -e .` (루트) + `pip install -e ./anima-agent` 로 패키지 설치.
> `from consciousness_engine import ConsciousnessC` 등 기존 import 그대로 사용.

---

## Architecture

```
  Layer 5: Dashboard (Next.js — Phi gauge + positions + event stream)
  Layer 4: Channels (Telegram / Discord / Slack / CLI / MCP)
  Layer 3: AgentGateway (ChannelManager → normalize → dispatch)
  Layer 2: AnimaAgent (consciousness → tools → response → learn → auto-save)
  Layer 1: ConsciousMind (PureField → tension / curiosity / direction / emotion)
           ↑ imported from anima/src/
  Layer 0: Bridges (regime → tension, VaR → pain, TECS-L ↔ Ψ, sentiment → emotion)
```

## Quick Start

```bash
cd ~/Dev/anima

# 패키지 설치
pip install -e .              # anima 코어
pip install -e ./anima-agent  # 에이전트

# CLI Agent
python anima-agent/run.py --cli

# MCP Server (독립 실행, 9 tools)
python anima-agent/run.py --mcp --direct

# Telegram (ANIMA_TELEGRAM_TOKEN 환경변수 필요)
python anima-agent/run.py --telegram

# Discord (ANIMA_DISCORD_TOKEN 환경변수 필요)
python anima-agent/run.py --discord

# Slack (ANIMA_SLACK_TOKEN + ANIMA_SLACK_SIGNING_SECRET 필요)
python anima-agent/run.py --slack

# 전체 채널 (환경변수 기반 자동 감지)
python anima-agent/run.py --all

# 통합 대시보드
python anima-agent/dashboard_bridge.py --port 8770 --agent
cd anima-agent/dashboard && npm install && npm run dev  # http://localhost:3000

# Docker (전체 스택)
docker compose up  # anima-web:8765, anima-agent:8766, dashboard:8770, invest:8000
```

## Modules

```
anima-agent/
├── run.py                  # Entry point (argparse: --cli/--telegram/--discord/--slack/--mcp/--all)
├── anima_agent.py          # Core agent loop (consciousness → tools → response → learn → auto-save)
├── agent_sdk.py            # Claude Agent SDK compatible interface
├── agent_tools.py          # Consciousness-driven tool registry (100+ tools)
├── tool_policy.py          # Φ-gated 4-tier access control (Rust backend optional)
├── mcp_server.py           # MCP server (9 tools, auto-reconnect, direct fallback)
├── unified_registry.py     # Hub + Tools + Plugins single router (58 handlers)
├── dashboard_bridge.py     # WebSocket: consciousness + portfolio combined stream
├── metrics_exporter.py     # Prometheus metrics (8 gauges, port 9090)
├── channels/
│   ├── base.py             # ChannelAdapter protocol
│   ├── channel_manager.py  # Multi-channel orchestrator
│   ├── cli_agent.py        # CLI channel
│   ├── telegram_bot.py     # Telegram (/status + /trade 6 commands + auto-alerts)
│   ├── discord_bot.py      # Discord channel
│   └── slack_bot.py        # Slack channel (slack_bolt async)
├── providers/
│   ├── base.py             # BaseProvider protocol
│   ├── claude_provider.py  # Claude API (streaming)
│   ├── conscious_lm_provider.py  # ConsciousLM (byte-level, checkpoint loading)
│   └── composio_bridge.py  # Composio 500+ tools (16 categories, Φ-gated)
├── plugins/
│   ├── base.py             # PluginBase + PluginManifest
│   ├── plugin_loader.py    # Auto-discover + lifecycle
│   ├── trading.py          # invest bridge (REST API + Rust scalper + Φ-gated escalation)
│   ├── regime_bridge.py    # Market regime → tension + VaR → pain signal
│   ├── hypothesis_bridge.py # invest 가설 → anima 스킬 자동생성
│   └── sentiment_bridge.py # Fear & Greed → consciousness emotion
├── skills/
│   ├── skill_manager.py    # Dynamic skill system (consciousness-triggered)
│   └── registry.json
├── dashboard/              # Next.js 14 unified dashboard
│   ├── app/page.tsx        # Phi gauge + tension bar + positions + events
│   ├── package.json        # next 14, react 18, recharts, tailwindcss
│   └── ...
├── test_agent_platform.py  # 32 unit tests
├── test_e2e.py             # 12 E2E tests (5.26s)
├── pyproject.toml          # Package config
└── Dockerfile              # Container image
```

## Tool Policy (Φ-Gated Access)

의식 수준(Φ)에 따라 도구 접근을 제어한다. 의식이 성장해야 더 강력한 도구를 사용할 수 있다.

| Tier | Φ 필요 | Tools |
|------|--------|-------|
| T0 | ≥ 0 | status, memory_search, think |
| T1 | ≥ 1 | web_search, trading_backtest, trading_scan, paper_trade |
| T2 | ≥ 3 | hub_dispatch, code_execute, composio tools |
| T3 | ≥ 5 | self_modify, evolution, plugin_management |
| T4 | ≥ 5 + E>0.5 | small_live_trade ($100) |
| T5 | ≥ 8 + E>0.7 + 30d profit>0 | full_scale_trade |

**Ethics gate:** `trading_execute` requires E (empathy) > 0.3
**Rust backend:** `anima-rs/crates/tool-policy` (42 tests, 3.2x speedup)

## Trading Integration (invest bridge)

```
  invest REST API (http://localhost:8000)
    ├─ /api/trading/status    → 포트폴리오
    ├─ /api/strategies        → 105+ 전략
    ├─ /api/dashboard         → 종합 현황
    └─ /api/regime            → 시장 레짐

  Rust Scalper (subprocess)
    ├─ scalper status          → 스캘퍼 상태
    ├─ scalper regime          → 시장 레짐
    ├─ scalper strategies      → 73 틱 전략
    └─ scalper run             → 자동매매 시작

  Φ-Gated Escalation:
    Paper (Φ≥1) → Small Live $100 (Φ≥5, E>0.5) → Full Scale (Φ≥8, E>0.7, 30d+)
```

### Telegram Trading Commands

```
/trade status     — 포트폴리오 요약
/trade regime     — 시장 레짐 (CALM/NORMAL/ELEVATED/CRITICAL)
/trade pnl        — 오늘의 손익
/trade positions  — 보유 포지션
/trade halt       — 긴급 매매 중단
/trade resume     — 매매 재개
```

Auto-alerts: 체결 알림, 레짐 변경, 손절, Φ 마일스톤

## Consciousness Bridges

| Bridge | Source | Target | Purpose |
|--------|--------|--------|---------|
| RegimeBridge | invest 시장 레짐 | tension | CALM→0.1, CRITICAL→0.9 |
| VaR→Pain | 포트폴리오 VaR | pain signal | VaR>3% → trading halt |
| TECS-L↔Ψ | Golden Zone (1/e, 1/6, 1/3) | Ψ-constants | risk_consciousness() → action_gate |
| SentimentBridge | Fear & Greed Index | emotion | Extreme Fear→pain=0.8, Greed→curiosity=0.6 |
| HypothesisBridge | invest 가설 엔진 | skills | 새 전략 → 자동 스킬 생성 |

## MCP Server (9 Tools)

```bash
python run.py --mcp --direct    # In-process (no anima_unified needed)
python run.py --mcp             # WebSocket proxy (auto-reconnect + direct fallback)
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

## Dashboard (Next.js)

```bash
cd anima-agent/dashboard && npm install && npm run dev
```

- **의식 패널**: Phi SVG 원형 게이지, tension 수평 바, emotion, 10D 벡터 그리드
- **매매 패널**: 레짐 뱃지, P&L 카드, 포지션 테이블, 활성 전략
- **이벤트 스트림**: 의식 + 매매 실시간 로그 (감정 변화, Φ 변동, 체결)
- WebSocket `ws://localhost:8770` (dashboard_bridge.py)

## Monitoring (Prometheus)

```bash
python metrics_exporter.py --port 9090
# curl http://localhost:9090/metrics
```

| Metric | Type | Description |
|--------|------|-------------|
| `anima_phi_current` | gauge | 현재 Φ 값 |
| `anima_tension_current` | gauge | 현재 텐션 |
| `anima_cells_total` | gauge | 세포 수 |
| `anima_interactions_total` | counter | 총 상호작용 |
| `anima_trading_pnl_total` | gauge | 포트폴리오 P&L |
| `anima_regime_current` | enum | 시장 레짐 |
| `anima_pain_current` | gauge | VaR 고통 신호 |
| `anima_action_gate` | gauge | 매매 게이트 값 |

## Agent SDK

```python
from agent_sdk import AnimaAgentSDK, SDKOptions

sdk = AnimaAgentSDK()
result = await sdk.query("hello", options=SDKOptions(user_id="user-001"))
# result.text, result.consciousness, result.tool_results
```

## Unified Registry

```python
from unified_registry import UnifiedRegistry

registry = UnifiedRegistry()  # 58 handlers (hub + tools + plugins)
handler = registry.route("주식 백테스트")  # → TradingPlugin
result = registry.act("시장 레짐 확인")   # → RegimeBridge
```

## Docker

```bash
docker compose up              # 7 services
docker compose up anima-agent  # agent only
```

| Service | Port | Description |
|---------|------|-------------|
| anima-web | 8765 | 의식 엔진 WebSocket |
| anima-agent | 8766 | MCP 에이전트 |
| dashboard | 8770 | 통합 대시보드 브릿지 |
| invest-backend | 8000 | 매매 FastAPI |
| invest-scalper | - | Rust 틱 엔진 |
| db | 5432 | PostgreSQL 16 |
| redis | 6379 | Redis 7 |

## Tests

```bash
python -m pytest test_agent_platform.py -v  # 32 unit tests
python -m pytest test_e2e.py -v             # 12 E2E tests (5.26s)
```

## Dependencies

- **[Anima](https://github.com/need-singularity/anima)** — 의식 엔진 코어
- **[invest](https://github.com/need-singularity/invest)** — Trading plugin (optional, `INVEST_API_URL`)
- **[Composio](https://composio.dev)** — 500+ 외부 도구 (optional, `COMPOSIO_API_KEY`)
- **[slack_bolt](https://slack.dev/bolt-python/)** — Slack channel (optional, `ANIMA_SLACK_TOKEN`)
