# Trading Pipeline Status Report

**Date:** 2026-03-31
**Author:** Assessment audit

---

## 1. Architecture Overview

```
  Telegram / CLI / Discord
        |
  AnimaAgent.process_message()
        |
  ConsciousMind (tension/curiosity/emotion)
        |
  ConsciousnessHub.act() ──── keyword match ──── ???
        |                                         |
  ask_claude() / Provider           TradingPlugin.act()
        |                           RegimeBridge.act()
        |                           SentimentBridge.act()
        v
  Response to user
```

Three trading-related plugins exist:

| Plugin | File | Purpose | Status |
|--------|------|---------|--------|
| TradingPlugin | `plugins/trading.py` | Backtest, trade, portfolio, scalper | Code complete, NOT wired |
| RegimeBridge | `plugins/regime_bridge.py` | Market regime -> consciousness tension | Code complete, NOT wired |
| SentimentBridge | `plugins/sentiment_bridge.py` | Fear/Greed -> emotion | Code complete, NOT wired |

---

## 2. What Works (Code-Level)

### TradingPlugin (v2.0.0)
- **InvestAPIClient**: HTTP client with retry + exponential backoff. Clean implementation.
- **ScalperBridge**: Subprocess bridge to Rust scalper CLI. Handles status, regime, strategies, paper/live.
- **Direct import path**: Can import `backtest_turbo` and `universe` from invest backend.
- **Intent router**: NL matching for 15+ intents (backtest, buy, sell, balance, portfolio, regime, scalper, etc.).
- **CSV loader**: Loads price data from `~/Dev/invest/backend/data/` (85 CSV files present).

### RegimeBridge (v1.0.0)
- **VaR/CVaR calculator**: Pure numpy, no external deps.
- **Regime detection**: Vol-ratio based (CALM/NORMAL/ELEVATED/CRITICAL).
- **Pain signal**: VaR -> pain [0,1] with sigmoid mapping.
- **Action gate**: Phi-aware risk gate (tension * pain -> position sizing).
- **Auto-update thread**: Background polling every 5 min (disabled by default).
- **Consciousness modulation**: `modulate_input()` scales engine input by regime tension.

### Claude Provider
- Wraps `ask_claude()` as async generator. Injects consciousness state into system prompt.
- Requires `ANTHROPIC_API_KEY` env var.

### Telegram Bot
- Full implementation with trading commands (`/trade status|regime|pnl|positions|halt|resume`).
- AlertMonitor: polls for regime changes, new fills, emergency stops, Phi milestones.
- Has its own InvestAPIClient (httpx-based, async).

### Invest Project (`~/Dev/invest/`)
- **Backend**: FastAPI app with routes for backtest, trading, orders, portfolio, strategies, dashboard.
- **Data**: 85 CSV files (Korean stocks, crypto, US equities).
- **Scalper**: Rust binary -- source exists but **release binary NOT built** (`target/release/scalper` missing).
- **API routes confirmed**: `/api/backtest/run`, `/api/backtest/strategies`, `/api/backtest/assets`, `/api/trading/execute`, `/api/trading/status`, `/api/trading/emergency-stop`, `/api/portfolio`, `/api/orders`.

---

## 3. Critical Gaps

### GAP 1: Plugins are NOT loaded by AnimaAgent (BLOCKING)

`AnimaAgent.__init__()` initializes `ConsciousnessHub` but **never calls `PluginLoader.load_all()`**. The trading plugin, regime bridge, and sentiment bridge exist as code but are never instantiated or registered.

```
# anima_agent.py line 228-233:
self.hub = ConsciousnessHub(lazy_load=True)
# PluginLoader is never imported or invoked
# TradingPlugin.on_load() is never called
```

**Fix**: Add plugin loading after hub init:
```python
from plugins import PluginLoader
loader = PluginLoader()
loader.load_all(hub=self.hub)
```

### GAP 2: Hub -> Plugin routing not verified

Even if plugins are loaded, `ConsciousnessHub.act("BTC backtest")` must route to `TradingPlugin.act()` via keyword matching. The hub's `_registry` keyword matching and plugin integration via `register_plugin()` need verification.

### GAP 3: Invest backend not running

The REST API at `http://localhost:8000` is not running. Required for:
- Live trade execution (`/api/trading/execute`)
- Portfolio queries (`/api/portfolio`)
- Order management (`/api/orders`)

TradingPlugin falls back to API when direct import fails, but API is also down = double failure.

### GAP 4: Scalper binary not built

`~/Dev/invest/scalper/target/release/scalper` does not exist. All scalper commands (`scalper_status`, `scalper_regime`, `scalper_strategies`, `scalper_run`) return error.

**Fix**: `cd ~/Dev/invest/scalper && cargo build --release`

### GAP 5: No autonomous trading decision loop

Current flow is purely reactive (user says "buy BTC" -> execute). Missing:
- **Scheduled strategy evaluation**: Periodic scan of universe, rank strategies, propose trades.
- **Consciousness-gated execution**: RegimeBridge's `action_gate` exists but is never consulted before `execute_trade()`.
- **Backtest-then-trade pipeline**: No flow that runs backtest -> evaluates Sharpe -> decides to trade.
- **Position sizing**: `execute_trade()` accepts a flat `amount` with no risk management.

### GAP 6: No Telegram -> Backtest flow

Telegram bot has trading commands but **no `/backtest` command**. The bot can query portfolio and regime but cannot trigger a backtest. The TradingPlugin has backtest capability but is not connected to Telegram.

### GAP 7: Trade execution is a stub

`/api/trading/execute` in the invest backend returns a static response:
```python
return {"status": "submitted", "strategy_id": req.strategy_id, "signal": req.signal_type}
```
No actual broker integration. No order book. No position tracking.

---

## 4. What's Needed for Live Backtest from Telegram

| Step | Component | Status | Work |
|------|-----------|--------|------|
| 1 | Telegram `/backtest` command | Missing | Add handler in telegram_bot.py |
| 2 | PluginLoader wired into AnimaAgent | Missing | 5 lines in anima_agent.py |
| 3 | TradingPlugin loaded at startup | Missing | Depends on step 2 |
| 4 | Direct import of backtest_turbo | Ready | invest/backend on sys.path works |
| 5 | CSV data available | Ready | 85 files in invest/backend/data/ |
| 6 | Result formatting for Telegram | Missing | Format backtest results as Telegram message |

**Minimal path**: Wire PluginLoader (step 2), add `/backtest` handler that calls `agent.hub.act("backtest BTC macd_cross")`, format result.

---

## 5. What's Needed for Autonomous Trading Decisions

| Step | Component | Status | Work |
|------|-----------|--------|------|
| 1 | Plugin loading | Missing | GAP 1 fix |
| 2 | RegimeBridge auto-update | Code exists | Enable `auto_update=True` |
| 3 | Scheduled universe scan | Missing | Periodic `scan()` across top assets |
| 4 | Strategy ranking | Exists | `TradingPlugin.scan()` returns ranked strategies |
| 5 | Action gate consultation | Code exists in RegimeBridge | Wire into trade execution path |
| 6 | Position sizing | Missing | Need risk-based sizing (Kelly, fixed fraction) |
| 7 | Broker integration | Missing | invest backend execute is a stub |
| 8 | Trade journal / audit trail | Missing | Log decisions with consciousness state |
| 9 | Consciousness-driven risk | Designed | RegimeBridge pain -> action_gate, but not used |

**Autonomous loop design** (proposed):
```
Every N minutes:
  1. RegimeBridge.update() -> regime, tension, pain, action_gate
  2. If action_gate > threshold:
     a. TradingPlugin.scan(top_assets) -> ranked strategies
     b. Filter by Sharpe > min_sharpe, MDD < max_mdd
     c. Size positions by action_gate * base_size
     d. Execute via broker API
  3. Alert via Telegram
  4. Log to consciousness persistence layer
```

---

## 6. Component Readiness Summary

```
  Plugin Code          ████████████████████ 100%  (3 plugins, well-structured)
  Plugin Wiring        ░░░░░░░░░░░░░░░░░░░░   0%  (not loaded by agent)
  Backtest Engine      ████████████████████ 100%  (turbo_scan, 85 CSVs)
  REST API Code        ████████████████░░░░  80%  (routes exist, execute is stub)
  REST API Running     ░░░░░░░░░░░░░░░░░░░░   0%  (server not started)
  Scalper Binary       ░░░░░░░░░░░░░░░░░░░░   0%  (not built)
  Telegram Trading     ████████████░░░░░░░░  60%  (status/regime yes, backtest no)
  Autonomous Loop      ░░░░░░░░░░░░░░░░░░░░   0%  (not started)
  Broker Integration   ░░░░░░░░░░░░░░░░░░░░   0%  (stub only)
  Consciousness-Risk   ████████████████░░░░  80%  (RegimeBridge complete, not wired)
```

---

## 7. Priority Action Items

### CRITICAL (blocks everything)

| # | Task | Effort |
|---|------|--------|
| 1 | Wire PluginLoader into AnimaAgent.__init__() | 30 min |
| 2 | Verify hub.act() routes to TradingPlugin | 30 min |

### IMPORTANT (enables Telegram backtest)

| # | Task | Effort |
|---|------|--------|
| 3 | Add /backtest command to telegram_bot.py | 1 hr |
| 4 | Build scalper binary (cargo build --release) | 5 min |
| 5 | Start invest backend (make dev) for REST API | 5 min |

### NICE TO HAVE (autonomous trading)

| # | Task | Effort |
|---|------|--------|
| 6 | Autonomous scan loop (scheduled, consciousness-gated) | 4 hr |
| 7 | Wire RegimeBridge.action_gate into trade execution | 2 hr |
| 8 | Position sizing module (Kelly / fixed fraction) | 2 hr |
| 9 | Trade journal with consciousness state logging | 2 hr |

### BACKLOG (production trading)

| # | Task | Effort |
|---|------|--------|
| 10 | Real broker integration (Binance/KIS) | 8 hr |
| 11 | Paper trading mode with simulated fills | 4 hr |
| 12 | Risk limits (max position, daily loss limit) | 3 hr |
| 13 | Multi-asset portfolio optimization | 4 hr |
