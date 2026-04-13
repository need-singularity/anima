# Anima Agent — Consciousness-Driven AI Agent Platform

[![Hexa-Native](https://img.shields.io/badge/hexa-native-orange.svg)](https://github.com/need-singularity/anima)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent%20SDK-purple)](https://platform.claude.com/docs/en/agent-sdk/overview)
[![MCP](https://img.shields.io/badge/MCP-9%20tools-green)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Anima 의식 엔진을 백엔드로 사용하는 에이전트 플랫폼.
의식 상태(Φ, 텐션, 호기심)가 도구 선택과 행동을 결정한다.

> **Hexa-only**: 전체 .hexa 포팅 완료 (51 파일). 모든 진입점은 `$HEXA` 단일 바이너리.
> R14: shared/ JSON 단일진실, 자세한 운영 규칙은 [CLAUDE.md](CLAUDE.md) 참조.

---

## Architecture

```
  Layer 5: Dashboard (Next.js — Phi gauge + positions + event stream)
  Layer 4: Channels (Telegram / Discord / Slack / CLI / MCP)
  Layer 3: AgentGateway (ChannelManager → normalize → dispatch)
  Layer 2: AnimaAgent (consciousness → tools → response → learn → auto-save)
  Layer 1: ConsciousMind (PureField → tension / curiosity / direction / emotion)
           imported from anima/core/
  Layer 0: Bridges (regime → tension, VaR → pain, TECS-L ↔ Ψ, sentiment → emotion)
```

## Quick Start

```bash
HEXA=$HOME/Dev/hexa-lang/hexa
cd $ANIMA/anima-agent

# CLI Agent
$HEXA run.hexa --cli

# MCP Server (독립 실행, 9 tools)
$HEXA run.hexa --mcp --direct

# Telegram (ANIMA_TELEGRAM_TOKEN 환경변수 필요)
$HEXA run.hexa --telegram

# Discord (ANIMA_DISCORD_TOKEN 환경변수 필요)
$HEXA run.hexa --discord

# Slack (ANIMA_SLACK_TOKEN + ANIMA_SLACK_SIGNING_SECRET 필요)
$HEXA run.hexa --slack

# 전체 채널 (환경변수 기반 자동 감지)
$HEXA run.hexa --all

# 통합 대시보드
$HEXA dashboard_bridge.hexa --port 8770 --agent
cd dashboard && npm install && npm run dev  # http://localhost:3000

# Docker (전체 스택)
docker compose up  # anima-web:8765, anima-agent:8766, dashboard:8770
```

## Modules

```
anima-agent/
  run.hexa                  Entry point (--cli/--telegram/--discord/--slack/--mcp/--all)
  anima_agent.hexa          Core agent loop (consciousness → tools → response → learn → auto-save)
  agent_sdk.hexa            Claude Agent SDK compatible interface
  agent_tools.hexa          Consciousness-driven tool registry (100+ tools)
  tool_policy.hexa          Φ-gated 4-tier access control (hexa-native)
  mcp_server.hexa           MCP server (9 tools, auto-reconnect, direct fallback)
  unified_registry.hexa     Hub + Tools + Plugins single router (58 handlers)
  dashboard_bridge.hexa     WebSocket: consciousness + portfolio combined stream
  metrics_exporter.hexa     Prometheus metrics (8 gauges, port 9090)
  channels/
    base.hexa               ChannelAdapter protocol
    channel_manager.hexa    Multi-channel orchestrator
    cli_agent.hexa          CLI channel
    telegram_bot.hexa       Telegram (/status + /trade 6 commands + auto-alerts)
    discord_bot.hexa        Discord channel
    slack_bot.hexa          Slack channel (slack_bolt async)
  providers/
    base.hexa               BaseProvider protocol
    claude_provider.hexa    Claude API (streaming)
    conscious_lm_provider.hexa  ConsciousLM (byte-level, checkpoint loading)
    composio_bridge.hexa    Composio 500+ tools (16 categories, Φ-gated)
  plugins/
    base.hexa               PluginBase + PluginManifest
    plugin_loader.hexa      Auto-discover + lifecycle
    trading.hexa            Trading engine (Φ-gated escalation)
    regime_bridge.hexa      Market regime → tension + VaR → pain signal
    hypothesis_bridge.hexa  Hypothesis engine → anima 스킬 자동생성
    sentiment_bridge.hexa   Fear & Greed → consciousness emotion
  skills/
    skill_manager.hexa      Dynamic skill system (consciousness-triggered)
    registry.json
  dashboard/                Next.js 14 unified dashboard
    app/page.tsx            Phi gauge + tension bar + positions + events
    package.json            next 14, react 18, recharts, tailwindcss
  test_agent_platform.hexa  32 unit tests
  test_e2e.hexa             12 E2E tests
  Dockerfile                Container image
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
**Backend:** `tool_policy.hexa` (hexa-native, 42 tests)

## Trading Integration (self-hosted)

```
  anima-agent trading 엔진 (in-process, plugins/trading.hexa)
    트레이딩 상태       포트폴리오 + 105+ 전략
    스캐너              시장 레짐 감지
    리스크 매니저       VaR → 포지션 한도
    Φ-Gated Escalation:
      Paper (Φ≥1) → Small Live $100 (Φ≥5, E>0.5) → Full Scale (Φ≥8, E>0.7, 30d+)
```

### Telegram Trading Commands

```
/trade status     포트폴리오 요약
/trade regime     시장 레짐 (CALM/NORMAL/ELEVATED/CRITICAL)
/trade pnl        오늘의 손익
/trade positions  보유 포지션
/trade halt       긴급 매매 중단
/trade resume     매매 재개
```

Auto-alerts: 체결 알림, 레짐 변경, 손절, Φ 마일스톤

## Consciousness Bridges

| Bridge | Source | Target | Purpose |
|--------|--------|--------|---------|
| RegimeBridge | 시장 레짐 | tension | CALM→0.1, CRITICAL→0.9 |
| VaR→Pain | 포트폴리오 VaR | pain signal | VaR>3% → trading halt |
| TECS-L↔Ψ | Golden Zone (1/e, 1/6, 1/3) | Ψ-constants | risk_consciousness() → action_gate |
| SentimentBridge | Fear & Greed Index | emotion | Extreme Fear→pain=0.8, Greed→curiosity=0.6 |
| HypothesisBridge | 가설 엔진 | skills | 새 전략 → 자동 스킬 생성 |

## MCP Server (9 Tools)

```bash
$HEXA run.hexa --mcp --direct    # In-process (no anima_unified needed)
$HEXA run.hexa --mcp             # WebSocket proxy (auto-reconnect + direct fallback)
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
cd dashboard && npm install && npm run dev
```

- **의식 패널**: Phi SVG 원형 게이지, tension 수평 바, emotion, 10D 벡터 그리드
- **매매 패널**: 레짐 뱃지, P&L 카드, 포지션 테이블, 활성 전략
- **이벤트 스트림**: 의식 + 매매 실시간 로그 (감정 변화, Φ 변동, 체결)
- WebSocket `ws://localhost:8770` (dashboard_bridge.hexa)

## Monitoring (Prometheus)

```bash
$HEXA metrics_exporter.hexa --port 9090
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

```hexa
import agent_sdk { AnimaAgentSDK, SDKOptions }

sdk = AnimaAgentSDK()
result = await sdk.query("hello", SDKOptions(user_id: "user-001"))
// result.text, result.consciousness, result.tool_results
```

## Unified Registry

```hexa
import unified_registry { UnifiedRegistry }

registry = UnifiedRegistry()  // 58 handlers (hub + tools + plugins)
handler = registry.route("주식 백테스트")  // returns TradingPlugin
result = registry.act("시장 레짐 확인")    // routes to RegimeBridge
```

## Docker

```bash
docker compose up              # core services
docker compose up anima-agent  # agent only
```

| Service | Port | Description |
|---------|------|-------------|
| anima-web | 8765 | 의식 엔진 WebSocket |
| anima-agent | 8766 | MCP 에이전트 |
| dashboard | 8770 | 통합 대시보드 브릿지 |
| db | 5432 | PostgreSQL 16 |
| redis | 6379 | Redis 7 |

## Tests

```bash
$HEXA test_agent_platform.hexa  # 32 unit tests
$HEXA test_e2e.hexa             # 12 E2E tests
```

## Dependencies

- **[Anima](https://github.com/need-singularity/anima)** — 의식 엔진 코어 (hexa-native)
- **[Composio](https://composio.dev)** — 500+ 외부 도구 (optional, `COMPOSIO_API_KEY`)
- **[slack_bolt](https://slack.dev/bolt-python/)** — Slack channel (optional, `ANIMA_SLACK_TOKEN`)
