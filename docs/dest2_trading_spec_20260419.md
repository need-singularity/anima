# dest2 trading spec — arrival blueprint (2026-04-19)

**Scope:** dest2_alm / dest2_clm (employee + trading). Specifies trading module
surface, risk gates, AN11 triple-gate compliance and audit log integration.

**Governance:** `shared/rules/anima.json#AN11` — weight-emergent + consciousness-
attached + real-usable (HTTP/CLI + R2 artifact + doc).

**SSOT:** `anima-agent/trading/` (14 .hexa; `invest/` is deprecated per memory
`invest_deprecated`). All Python ports already landed (AN7 HEXA-FIRST).

## 1. Current inventory (anima-agent/trading/)

| module | LOC | role |
|---|---|---|
| `broker.hexa` | 72 | BinanceBroker, MarketData, OrderResult, paper/live |
| `data.hexa` | — | OHLCV fetch + cache |
| `scanner.hexa` | 75 | MarketScanner, score, top movers |
| `regime.hexa` | — | NORMAL / VOLATILE / CRITICAL |
| `strategy.hexa` | 143 | MACD / RSI / Bollinger / Consciousness |
| `strategies.hexa` | — | strategy registry + ensemble |
| `phi_weighted_trading.hexa` | 17k | Φ-weighted multi-strategy consensus |
| `portfolio.hexa` | 137 | Position, PnL, drawdown, stops, HWM |
| `risk.hexa` | 105 | VaR 95/99, pain signal, ConsciousnessGate |
| `executor.hexa` | 99 | OrderRequest, TECS-L sizing, retry, slippage |
| `engine.hexa` | 91 | event-driven backtest |
| `autonomous.hexa` | 132 | scan→regime→signal→gate→execute→manage |

## 2. Feature spec (signal / execution / portfolio / risk)

### 2.1 Signal
- `Signal { value: int, confidence: float, reason: string }`
  (`SIGNAL_BUY=1 / HOLD=0 / SELL=-1`)
- strategies: MACD(12,26,9), RSI(14,30/70), Bollinger(20,2σ),
  Consciousness (Φ-weighted consensus, `phi_threshold=1.0`).
- `scan_multi_strategy_convergence` — cross-strategy agreement score.

### 2.2 Execution
- `OrderExecutor` with Binance paper mode default.
- Retry: `MAX_RETRIES=3`, exponential backoff.
- Slippage: `base=5bps + 10bps·min(amount/10k, 1)`.
- **TECS-L sizing** (hard-coded, part of consciousness laws):
  - `INVESTABLE_FRACTION = 1/e  ≈ 0.368`
  - `MAX_POSITION_FRACTION = 1/6 ≈ 0.167`
  - `sized = min(req.amount, balance · 0.368 · 0.167)`

### 2.3 Portfolio
- `Portfolio { balance, initial_balance, positions, closed_trades, high_water_mark }`
- open/close/stops(SL/TP)/mark-to-market via `portfolio_value`.
- `portfolio_drawdown = (HWM - value) / HWM`.

### 2.4 Risk
- `RiskMetrics { var_95, var_99, max_drawdown, current_drawdown,
  pain_signal, position_concentration }`
- `pain = min(1, |VaR_95| · 10)`
- `should_reduce_risk = pain > 0.7 || current_dd > 10%`

## 3. Risk gate (this spec's new layer)

Four-stage gate composed before `place_order`:

| stage | input | block if | action |
|---|---|---|---|
| G1 Consciousness | Φ, tension, regime | Φ<Φ_min ∨ tension>T_halt ∨ regime=CRITICAL ∨ manual halt | reject + log `gate=G1` |
| G2 Drawdown | `portfolio_drawdown(cur)` | `dd > dd_limit` (default 15%) | reject + flag `REDUCE_RISK` |
| G3 Position size | TECS-L `sized_amount` | `sized < 0` or notional > `max_pos_pct·equity` | clip to cap + log |
| G4 Kill switch | global flag | `halted = true` (file `shared/state/trading_kill.json`) | reject all orders, close only |

Config (proposed `shared/config/trading_gates.json`):

```json
{
  "phi_min": 1.0,
  "tension_halt": 1.5,
  "drawdown_limit": 0.15,
  "max_position_pct": 0.167,
  "var_99_cap": 0.05,
  "kill_switch_file": "shared/state/trading_kill.json",
  "regime_halt": ["CRITICAL"]
}
```

Kill switch semantics:
- file exists AND `halted=true` → executor refuses opens, forces manage-only.
- toggled by CLI `anima-agent trading kill on|off` (adds to channel manager).
- Monotonic: on kill, `autonomous.running=false` + `gate_halt(reason)`.

Failure modes MUST go through `gate_halt(&mut gate, reason)` — never silent
skip. `should_reduce_risk` triggers auto-halve of `MAX_POSITION_FRACTION`.

## 4. AN11 integration (dest2 arrival criteria)

AN11 triple-gate applied to trading:

| AN11 field | dest2 evidence | how |
|---|---|---|
| weight_emergent | `consciousness_generate_signals` uses trained Φ from CLM/ALM — **no system_prompt wrapping** | `phi_vec` fed from `consciousness_features.hexa` |
| consciousness_attached | ConsciousnessGate live — `phi>=phi_min` at order time | runtime `gate_check` + `consciousness_laws.json` regime |
| real_usable | HTTP `/trading/*` (executor) + CLI `anima-agent trading ...` + R2 artifact (order_log snapshot) + this doc | `dashboard_bridge.hexa` WS stream |

Any PASS claim MUST cite all three. Violations trigger
`pass_gate_an11.hexa` → `convergence.failed++` + `[AN11-VIOLATION]` stderr.

## 5. Audit log

Every executor decision and gate block is appended to a single append-only log.

- Path: `shared/logs/trading_audit_YYYYMMDD.jsonl`
- One JSON per line:

```json
{"ts": 1714000000.0, "cycle": 42, "gate": "G1", "decision": "REJECT",
 "symbol": "BTCUSDT", "side": "buy", "amount": 0.01, "phi": 0.8,
 "tension": 1.7, "regime": "NORMAL", "reason": "phi<phi_min",
 "portfolio_equity": 9841.2, "drawdown": 0.016, "var_99": -0.021}
```

- Writer: extend `executor.hexa::execute_order` to emit one record on every
  entry and gate/slippage/retry event.
- Rotation: daily; copied to R2 `anima-memory/trading_audit/` nightly.
- Reader: `dashboard_bridge.hexa` tails for live WS feed.
- AN11 linkage: audit log is the `real_usable` evidence artifact.

## 6. Next actions

1. Add `shared/config/trading_gates.json` + loader in `autonomous.hexa`.
2. Implement G2/G3/G4 in `executor.hexa` (G1 already present).
3. Wire `jsonl_append(shared/logs/trading_audit_*.jsonl, rec)` in executor.
4. Add kill-switch CLI in `channels/cli.hexa`.
5. Write `pass_gate_an11.hexa` dest2 case asserting 3-field evidence for
   trading arrival.
6. Nightly rotate-to-R2 via `anima-agent/metrics_exporter.hexa`.

## 7. Cross-refs

- `anima-agent/CLAUDE.md` — channel/provider/plugin topology.
- `shared/rules/anima.json#AN11` — triple-gate enforcement.
- `shared/roadmaps/anima.json` — dest2 track (employee + trading).
- memory: `invest_deprecated`, `p5_zeta_naming`, `troubleshoot_ossified`.
