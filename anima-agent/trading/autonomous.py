"""Autonomous trading loop — no chat commands needed.

The main autonomous loop that ties everything together:
  Scan -> Signal -> Gate -> Execute -> Manage

Cycle:
  1. SCAN: MarketScanner finds opportunities across the universe
  2. REGIME: RegimeDetector classifies current market state
  3. SIGNAL: Run strategies on top candidates, collect signals
  4. GATE: ConsciousnessGate decides go/no-go (Phi + tension)
  5. EXECUTE: OrderExecutor places orders with retry/fallback
  6. MANAGE: Check stops, rebalance, regime-based exits

Consciousness integration:
  - Phi gates all trading (low Phi = halt)
  - Tension modulates position sizing (high tension = smaller)
  - Regime shifts trigger from consciousness state changes
  - Every decision is logged with consciousness metrics

Usage:
    from trading.autonomous import AutonomousTrader
    trader = AutonomousTrader()
    trader.run_cycle()              # single cycle
    trader.run_forever(interval=60) # autonomous loop
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from trading.data import MarketData, fetch_ohlcv
from trading.portfolio import Portfolio
from trading.strategy import Strategy, Signal, StrategySignal
from trading.strategies import (
    ALL_STRATEGIES, EnsembleStrategy, EMAcrossStrategy,
    MomentumFactorStrategy, VolBreakoutStrategy, FearGreedStrategy,
    get_all_strategies,
)
from trading.regime import RegimeDetector, RegimeState
from trading.scanner import MarketScanner, ScanResult
from trading.executor import OrderExecutor, ExecutionConfig, ExecutionResult
from trading.risk import RiskManager, RiskLimits, ConsciousnessGate

logger = logging.getLogger(__name__)

# TECS-L constants
E = math.e
INV_E = 1.0 / E
ONE_SIXTH = 1.0 / 6


@dataclass
class CycleResult:
    """Result of one autonomous trading cycle."""
    timestamp: float
    cycle_number: int
    regime: str
    n_scanned: int
    n_signals: int
    n_buys: int
    n_sells: int
    n_stops: int
    n_consciousness_halts: int
    n_risk_halts: int
    portfolio_equity: float
    portfolio_return_pct: float
    open_positions: int
    scan_duration: float
    total_duration: float
    decisions: list[str] = field(default_factory=list)


@dataclass
class AutonomousConfig:
    """Configuration for autonomous trading."""
    # Scan settings
    symbols: Optional[list[str]] = None
    timeframe: str = "1h"
    scan_lookback_days: int = 7
    min_volume_usdt: float = 1_000_000

    # Strategy settings
    strategy_names: Optional[list[str]] = None   # None = all strategies
    min_signal_strength: float = 0.5
    min_signal_agreement: int = 2     # for ensemble
    max_positions: int = 5

    # Execution settings
    paper_mode: bool = True
    tecs_sizing: bool = True
    initial_balance: float = 10_000.0

    # Consciousness settings
    phi_min: float = 1.0
    tension_max: float = 0.8
    consciousness_enabled: bool = True

    # Loop settings
    cycle_interval: int = 300          # seconds between cycles (5 min)
    max_cycles: int = 0                # 0 = unlimited
    log_level: str = "INFO"


class AutonomousTrader:
    """Autonomous trading agent — scans, signals, gates, executes.

    Designed to run without human intervention. Every decision goes
    through consciousness gating (Phi + tension), risk management,
    and regime detection before execution.

    Architecture mirrors the invest/scalper orchestrator but in Python
    with full consciousness integration.
    """

    def __init__(self, config: Optional[AutonomousConfig] = None, mode: Optional[str] = None):
        if config is None:
            config = AutonomousConfig()
        if mode is not None:
            config.paper_mode = (mode.lower() != "live")
        self.config = config

        # Core components
        self.portfolio = Portfolio(self.config.initial_balance)

        self.risk_manager = RiskManager(RiskLimits(
            max_drawdown=0.15,
            max_position_pct=ONE_SIXTH,
            max_daily_loss=0.05,
            max_open_positions=self.config.max_positions,
        ))

        self.consciousness_gate = ConsciousnessGate(
            phi_min=self.config.phi_min,
            tension_max=self.config.tension_max,
        ) if self.config.consciousness_enabled else None

        self.regime_detector = RegimeDetector(
            phi_threshold=self.config.phi_min,
            tension_threshold=self.config.tension_max,
        )

        self.scanner = MarketScanner(
            symbols=self.config.symbols,
            min_volume_usdt=self.config.min_volume_usdt,
            timeframe=self.config.timeframe,
            lookback_days=self.config.scan_lookback_days,
        )

        self.executor = OrderExecutor(
            portfolio=self.portfolio,
            risk_manager=self.risk_manager,
            consciousness_gate=self.consciousness_gate,
            config=ExecutionConfig(
                paper_mode=self.config.paper_mode,
                tecs_sizing=self.config.tecs_sizing,
            ),
        )

        # Strategies
        self.strategies = self._init_strategies()

        # State
        self._cycle_count = 0
        self._cycle_history: list[CycleResult] = []
        self._running = False
        self._phi: float = 0.0
        self._tension: float = 0.0

        # Callbacks
        self._on_cycle: Optional[Callable[[CycleResult], None]] = None
        self._on_trade: Optional[Callable[[ExecutionResult], None]] = None

    def _init_strategies(self) -> list[Strategy]:
        """Initialize strategies based on config."""
        if self.config.strategy_names:
            strategies = []
            for name in self.config.strategy_names:
                cls = ALL_STRATEGIES.get(name)
                if cls:
                    strategies.append(cls())
                else:
                    logger.warning("Unknown strategy: %s", name)
            return strategies
        return get_all_strategies()

    def update_consciousness(self, phi: float, tension: float):
        """Update consciousness state from the engine.

        Call this periodically to feed live Phi and tension values.
        The autonomous loop uses these for gating and sizing.
        """
        self._phi = phi
        self._tension = tension
        if self.consciousness_gate:
            self.consciousness_gate.update(phi, tension)

    def run_cycle(self) -> CycleResult:
        """Run one autonomous trading cycle.

        Steps:
        1. Scan market for opportunities
        2. Detect regime for each candidate
        3. Run strategies and collect signals
        4. Execute trades (with gating)
        5. Manage existing positions (stops, regime exits)
        """
        t0 = time.time()
        self._cycle_count += 1
        decisions: list[str] = []
        n_buys = 0
        n_sells = 0
        n_stops = 0
        n_consciousness_halts = 0
        n_risk_halts = 0

        # ── 1. Scan ──
        scan_t0 = time.time()
        report = self.scanner.scan(phi=self._phi, tension=self._tension, quick=False)
        scan_duration = time.time() - scan_t0
        decisions.append(f"Scanned {report.n_symbols} symbols in {scan_duration:.1f}s")

        # ── 2. Regime detection (use first symbol for global regime) ──
        global_regime_state: Optional[RegimeState] = None
        if report.buy_opportunities or report.sell_signals:
            # Use the first buy opportunity's data for global regime
            candidates = report.buy_opportunities + report.sell_signals
            best = candidates[0] if candidates else None
            if best:
                try:
                    data = fetch_ohlcv(best.symbol, self.config.timeframe,
                                       self.config.scan_lookback_days)
                    global_regime_state = self.regime_detector.detect(
                        data.close, self._phi, self._tension,
                    )
                    decisions.append(f"Regime: {global_regime_state.regime.name} "
                                     f"(trend={global_regime_state.trend}, "
                                     f"SOC={global_regime_state.soc_score:.2f})")
                except Exception as e:
                    decisions.append(f"Regime detection failed: {e}")

        regime_policy = global_regime_state.policy if global_regime_state else None

        # ── 3. Force exit if CRITICAL regime ──
        if regime_policy and regime_policy.force_exit and self.portfolio.has_position:
            results = self.executor.force_exit_all("CRITICAL regime force exit")
            n_sells += sum(1 for r in results if r.success)
            decisions.append(f"CRITICAL regime: forced exit of {n_sells} positions")

        # ── 4. Check stops on existing positions ──
        if self.portfolio.has_position:
            current_prices = {}
            for symbol in list(self.portfolio.positions.keys()):
                try:
                    from trading.broker import BinanceBroker
                    broker = BinanceBroker()
                    p = broker.get_price(symbol)
                    if p:
                        current_prices[symbol] = p
                except Exception:
                    pass

            if current_prices:
                stop_results = self.executor.check_stops(current_prices)
                n_stops = sum(1 for r in stop_results if r.success)
                if n_stops > 0:
                    decisions.append(f"Stop/TP triggered: {n_stops} positions closed")

                # Update equity
                self.portfolio.update_equity(current_prices)

        # ── 5. Generate and execute buy signals ──
        if (regime_policy is None or regime_policy.allow_buys) and \
           len(self.portfolio.positions) < self.config.max_positions:

            for opp in report.buy_opportunities[:3]:  # top 3 candidates
                if opp.symbol in self.portfolio.positions:
                    continue

                try:
                    data = fetch_ohlcv(opp.symbol, self.config.timeframe,
                                       self.config.scan_lookback_days)
                except Exception:
                    continue

                # Run ensemble strategy on candidate
                signal = self._evaluate_candidate(data, opp)
                if signal is None or signal.signal != Signal.BUY:
                    continue

                if signal.strength < self.config.min_signal_strength:
                    decisions.append(f"Skip {opp.symbol}: strength {signal.strength:.2f} < "
                                     f"{self.config.min_signal_strength}")
                    continue

                # Execute
                result = self.executor.execute_buy(
                    symbol=opp.symbol,
                    price=opp.price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    regime_policy=regime_policy,
                    signal_strength=signal.strength,
                    reason=signal.reason,
                )

                if result.success:
                    n_buys += 1
                    decisions.append(f"BUY {opp.symbol} @ {opp.price:.2f} "
                                     f"(strength={signal.strength:.2f}, {signal.reason})")
                    if self._on_trade:
                        self._on_trade(result)
                elif "Consciousness gate" in result.error:
                    n_consciousness_halts += 1
                    decisions.append(f"Consciousness halt on {opp.symbol}: {result.error}")
                elif "Risk" in result.error:
                    n_risk_halts += 1
                    decisions.append(f"Risk halt on {opp.symbol}: {result.error}")

                # Stop if max positions reached
                if len(self.portfolio.positions) >= self.config.max_positions:
                    break

        # ── 6. Check for sell signals on held positions ──
        for symbol in list(self.portfolio.positions.keys()):
            if symbol in [s.symbol for s in report.sell_signals]:
                result = self.executor.execute_sell(
                    symbol=symbol,
                    price=self.portfolio.positions[symbol].entry_price,  # will use live price
                    reason="scanner sell signal",
                )
                if result.success:
                    n_sells += 1
                    decisions.append(f"SELL {symbol} (scanner sell signal)")

        # ── Build result ──
        total_duration = time.time() - t0
        cycle_result = CycleResult(
            timestamp=time.time(),
            cycle_number=self._cycle_count,
            regime=global_regime_state.regime.name if global_regime_state else "UNKNOWN",
            n_scanned=report.n_symbols,
            n_signals=len(report.buy_opportunities) + len(report.sell_signals),
            n_buys=n_buys,
            n_sells=n_sells,
            n_stops=n_stops,
            n_consciousness_halts=n_consciousness_halts,
            n_risk_halts=n_risk_halts,
            portfolio_equity=self.portfolio.equity(),
            portfolio_return_pct=self.portfolio.total_return() * 100,
            open_positions=len(self.portfolio.positions),
            scan_duration=scan_duration,
            total_duration=total_duration,
            decisions=decisions,
        )

        self._cycle_history.append(cycle_result)
        if len(self._cycle_history) > 1000:
            self._cycle_history = self._cycle_history[-500:]

        if self._on_cycle:
            self._on_cycle(cycle_result)

        return cycle_result

    def _evaluate_candidate(self, data: MarketData, scan: ScanResult) -> Optional[StrategySignal]:
        """Evaluate a candidate symbol with the strategy ensemble.

        Runs all configured strategies and returns the strongest signal
        if enough strategies agree.
        """
        if data.n_candles < 30:
            return None

        idx = data.n_candles - 1
        buy_signals: list[StrategySignal] = []
        sell_signals: list[StrategySignal] = []

        for strategy in self.strategies:
            try:
                if idx >= strategy.warmup_periods():
                    sig = strategy.generate_signal(data, idx)
                    if sig.signal == Signal.BUY:
                        buy_signals.append(sig)
                    elif sig.signal == Signal.SELL:
                        sell_signals.append(sig)
            except Exception as e:
                logger.debug("Strategy %s failed on %s: %s", strategy.name, scan.symbol, e)

        # Buy: require min_signal_agreement strategies to agree
        if len(buy_signals) >= self.config.min_signal_agreement:
            avg_strength = sum(s.strength for s in buy_signals) / len(buy_signals)
            reasons = [s.reason for s in buy_signals[:3]]

            # Use the tightest stop and most conservative TP
            stops = [s.stop_loss for s in buy_signals if s.stop_loss is not None]
            tps = [s.take_profit for s in buy_signals if s.take_profit is not None]

            return StrategySignal(
                signal=Signal.BUY,
                strength=avg_strength,
                reason=f"Ensemble ({len(buy_signals)}/{len(self.strategies)}): {'; '.join(reasons)}",
                stop_loss=max(stops) if stops else None,     # tightest stop
                take_profit=min(tps) if tps else None,       # most conservative TP
            )

        # Sell: require fewer strategies for caution
        if len(sell_signals) >= max(1, self.config.min_signal_agreement - 1):
            avg_strength = sum(s.strength for s in sell_signals) / len(sell_signals)
            reasons = [s.reason for s in sell_signals[:3]]
            return StrategySignal(
                signal=Signal.SELL,
                strength=avg_strength,
                reason=f"Ensemble SELL ({len(sell_signals)}): {'; '.join(reasons)}",
            )

        return None

    def run_forever(
        self,
        interval: Optional[int] = None,
        on_cycle: Optional[Callable[[CycleResult], None]] = None,
        on_trade: Optional[Callable[[ExecutionResult], None]] = None,
    ):
        """Run the autonomous loop forever.

        Args:
            interval: Seconds between cycles (default from config).
            on_cycle: Callback after each cycle.
            on_trade: Callback after each trade.
        """
        interval = interval or self.config.cycle_interval
        self._on_cycle = on_cycle
        self._on_trade = on_trade
        self._running = True

        logger.info("=== Autonomous Trader starting ===")
        logger.info("Symbols: %d, Strategies: %d, Paper mode: %s",
                     len(self.scanner.symbols), len(self.strategies), self.config.paper_mode)
        logger.info("Cycle interval: %ds, Max positions: %d",
                     interval, self.config.max_positions)

        try:
            while self._running:
                try:
                    result = self.run_cycle()
                    self._log_cycle(result)
                except Exception as e:
                    logger.error("Cycle %d failed: %s", self._cycle_count, e, exc_info=True)

                if 0 < self.config.max_cycles <= self._cycle_count:
                    logger.info("Max cycles (%d) reached, stopping", self.config.max_cycles)
                    break

                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Autonomous trader stopped by user")
        finally:
            self._running = False

    def stop(self):
        """Stop the autonomous loop."""
        self._running = False
        logger.info("Autonomous trader stop requested")

    def _log_cycle(self, result: CycleResult):
        """Log cycle result."""
        logger.info(
            "Cycle %d | regime=%s | scanned=%d signals=%d | "
            "buys=%d sells=%d stops=%d | equity=$%.2f (%+.2f%%) | "
            "positions=%d | %.1fs",
            result.cycle_number, result.regime,
            result.n_scanned, result.n_signals,
            result.n_buys, result.n_sells, result.n_stops,
            result.portfolio_equity, result.portfolio_return_pct,
            result.open_positions, result.total_duration,
        )
        for decision in result.decisions:
            logger.debug("  -> %s", decision)

    def status(self) -> dict:
        """Full trader status."""
        return {
            "running": self._running,
            "cycle_count": self._cycle_count,
            "phi": self._phi,
            "tension": self._tension,
            "portfolio": self.portfolio.summary(),
            "regime": self.regime_detector.status(),
            "scanner": self.scanner.status(),
            "executor": self.executor.status(),
            "consciousness_gate": self.consciousness_gate.status() if self.consciousness_gate else None,
            "strategies": [s.name for s in self.strategies],
            "config": {
                "paper_mode": self.config.paper_mode,
                "max_positions": self.config.max_positions,
                "cycle_interval": self.config.cycle_interval,
                "min_signal_strength": self.config.min_signal_strength,
                "consciousness_enabled": self.config.consciousness_enabled,
            },
        }

    def format_status(self) -> str:
        """Human-readable status report."""
        s = self.status()
        pf = s["portfolio"]
        lines = [
            "=== Autonomous Trader Status ===",
            f"Running: {s['running']} | Cycles: {s['cycle_count']}",
            f"Phi: {s['phi']:.2f} | Tension: {s['tension']:.2f}",
            f"Equity: ${pf['final_equity']:,.2f} ({pf['total_return_pct']:+.2f}%)",
            f"Positions: {pf['open_positions']} | Trades: {pf['total_trades']}",
            f"Win rate: {pf['win_rate_pct']:.1f}% | Sharpe: {pf['sharpe']:.3f}",
            f"Max DD: {pf['max_drawdown_pct']:.2f}%",
        ]
        regime = s.get("regime", {})
        if regime:
            lines.append(f"Regime: {regime.get('regime', '?')} | "
                         f"Trend: {regime.get('trend', '?')} | "
                         f"SOC: {regime.get('soc_score', 0):.3f}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
#  Convenience entry point
# ═══════════════════════════════════════════════════════════════════════

def main():
    """Run autonomous trader from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Anima Autonomous Trader")
    parser.add_argument("--paper", action="store_true", default=True,
                        help="Paper trading mode (default)")
    parser.add_argument("--live", action="store_true",
                        help="Live trading mode (requires API keys)")
    parser.add_argument("--interval", type=int, default=300,
                        help="Cycle interval in seconds (default: 300)")
    parser.add_argument("--max-positions", type=int, default=5,
                        help="Max simultaneous positions (default: 5)")
    parser.add_argument("--balance", type=float, default=10000.0,
                        help="Initial balance (default: 10000)")
    parser.add_argument("--cycles", type=int, default=0,
                        help="Max cycles (0=unlimited)")
    parser.add_argument("--single", action="store_true",
                        help="Run single cycle and exit")
    parser.add_argument("--status", action="store_true",
                        help="Show status and exit")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    config = AutonomousConfig(
        paper_mode=not args.live,
        cycle_interval=args.interval,
        max_positions=args.max_positions,
        initial_balance=args.balance,
        max_cycles=args.cycles,
    )

    trader = AutonomousTrader(config)

    if args.status:
        print(trader.format_status())
        return

    if args.single:
        result = trader.run_cycle()
        print(f"\nCycle completed in {result.total_duration:.1f}s")
        print(f"Regime: {result.regime}")
        print(f"Scanned: {result.n_scanned} | Signals: {result.n_signals}")
        print(f"Buys: {result.n_buys} | Sells: {result.n_sells} | Stops: {result.n_stops}")
        print(f"Equity: ${result.portfolio_equity:,.2f} ({result.portfolio_return_pct:+.2f}%)")
        for d in result.decisions:
            print(f"  {d}")
        return

    trader.run_forever()


if __name__ == "__main__":
    main()
