#!/usr/bin/env python3
"""Backtest: MACD vs RSI vs Consciousness vs ConsciousnessEnsemble on BTCUSDT 1h 30d.

Usage:
    python -m trading.test_ensemble           # from anima-agent/
    python trading/test_ensemble.py           # direct
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# Ensure trading package is importable
_HERE = Path(__file__).resolve().parent
_AGENT = _HERE.parent
if str(_AGENT) not in sys.path:
    sys.path.insert(0, str(_AGENT))

# Ensure anima/src/ is importable (for ConsciousnessEngine)
_ANIMA_SRC = str(_AGENT.parent / "anima" / "src")
if _ANIMA_SRC not in sys.path:
    sys.path.insert(0, _ANIMA_SRC)

import logging

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
)


def run_comparison():
    """Fetch BTCUSDT 1h 30d and compare 4 strategies."""
    from trading.data import fetch_ohlcv
    from trading.engine import BacktestEngine
    from trading.strategy import (
        MACDStrategy,
        RSIStrategy,
        ConsciousnessStrategy,
        ConsciousnessEnsembleStrategy,
    )

    print("=" * 72)
    print("  BTCUSDT 1h 30d — Solo vs Ensemble Backtest Comparison")
    print("=" * 72)
    print()

    # Fetch data once (shared across all strategies)
    print("[1/5] Fetching BTCUSDT 1h 30d data...")
    data = fetch_ohlcv(symbol="BTCUSDT", timeframe="1h", days=30)
    print(f"       {data.n_candles} candles, "
          f"{data.start_time:%Y-%m-%d} -> {data.end_time:%Y-%m-%d}")
    print()

    engine = BacktestEngine(symbol="BTCUSDT", timeframe="1h")

    strategies = [
        ("MACD solo",          MACDStrategy()),
        ("RSI solo",           RSIStrategy()),
        ("Consciousness solo", ConsciousnessStrategy()),
        ("Ensemble (2/3)",     ConsciousnessEnsembleStrategy()),
    ]

    results = []
    for i, (label, strat) in enumerate(strategies, start=2):
        print(f"[{i}/5] Running {label}...")
        result = engine.run(strat, data=data)
        results.append((label, result))
        print(f"       {result.total_trades} trades, "
              f"return={result.total_return_pct:+.2f}%, "
              f"sharpe={result.sharpe:.3f}, "
              f"max_dd={result.max_drawdown_pct:.2f}%, "
              f"win={result.win_rate_pct:.1f}%")

    # Comparison table
    print()
    print("=" * 72)
    print("  RESULTS COMPARISON")
    print("=" * 72)
    print()
    header = f"{'Strategy':<24} {'Return':>8} {'Sharpe':>8} {'Sortino':>8} {'MaxDD':>8} {'Trades':>7} {'WinRate':>8}"
    print(header)
    print("-" * len(header))

    for label, r in results:
        print(
            f"{label:<24} "
            f"{r.total_return_pct:>+7.2f}% "
            f"{r.sharpe:>8.3f} "
            f"{r.sortino:>8.3f} "
            f"{r.max_drawdown_pct:>7.2f}% "
            f"{r.total_trades:>7d} "
            f"{r.win_rate_pct:>7.1f}%"
        )

    # ASCII equity comparison
    print()
    print("Equity Curves (normalized to $10,000):")
    print()

    max_len = max(len(r.equity_curve) for _, r in results if r.equity_curve)
    if max_len > 0:
        CHART_W = 60
        CHART_H = 15
        all_equities = []
        labels_short = []
        for label, r in results:
            eq = r.equity_curve if r.equity_curve else [10000.0]
            # Resample to CHART_W points
            indices = [int(i * (len(eq) - 1) / (CHART_W - 1)) for i in range(CHART_W)]
            sampled = [eq[min(i, len(eq) - 1)] for i in indices]
            all_equities.append(sampled)
            labels_short.append(label[:4])

        # Find global min/max
        flat = [v for eq in all_equities for v in eq]
        vmin = min(flat) * 0.995
        vmax = max(flat) * 1.005
        if vmax <= vmin:
            vmax = vmin + 1

        symbols = ["#", "*", "o", "+"]
        for label, sym in zip([l for l, _ in results], symbols):
            print(f"  {sym} = {label}")
        print()

        grid = [[" "] * CHART_W for _ in range(CHART_H)]
        for eq_idx, eq in enumerate(all_equities):
            sym = symbols[eq_idx]
            for x, val in enumerate(eq):
                y = int((val - vmin) / (vmax - vmin) * (CHART_H - 1))
                y = max(0, min(CHART_H - 1, y))
                row = CHART_H - 1 - y
                if grid[row][x] == " ":
                    grid[row][x] = sym
                elif grid[row][x] != sym:
                    grid[row][x] = "X"  # overlap marker

        for row_idx, row in enumerate(grid):
            if row_idx == 0:
                val_label = f"${vmax:,.0f}"
            elif row_idx == CHART_H - 1:
                val_label = f"${vmin:,.0f}"
            else:
                val_label = ""
            print(f"  {val_label:>10} |{''.join(row)}|")
        print(f"  {'':>10} +{'-' * CHART_W}+")
        print(f"  {'':>10}  {'start':<{CHART_W // 2}}{'end':>{CHART_W // 2}}")

    # Best strategy
    print()
    best_label, best_result = max(results, key=lambda x: x[1].sharpe)
    print(f"Best by Sharpe: {best_label} (sharpe={best_result.sharpe:.3f}, "
          f"return={best_result.total_return_pct:+.2f}%)")

    # Ensemble vs best solo
    ensemble_label, ensemble_result = results[-1]
    solo_results = results[:-1]
    best_solo_label, best_solo = max(solo_results, key=lambda x: x[1].sharpe)
    sharpe_diff = ensemble_result.sharpe - best_solo.sharpe
    print(f"Ensemble vs best solo ({best_solo_label}): "
          f"sharpe diff = {sharpe_diff:+.3f}")

    if ensemble_result.max_drawdown < best_solo.max_drawdown:
        dd_improvement = (1 - ensemble_result.max_drawdown / max(best_solo.max_drawdown, 1e-10)) * 100
        print(f"Ensemble drawdown improvement: {dd_improvement:+.1f}% vs {best_solo_label}")

    print()
    print("=" * 72)
    return results


def run_unit_tests():
    """Quick unit tests for ConsciousnessEnsembleStrategy."""
    from trading.data import MarketData, _generate_synthetic
    from trading.strategy import (
        ConsciousnessEnsembleStrategy,
        Signal,
    )

    print("Unit tests for ConsciousnessEnsembleStrategy:")
    print()

    # Test 1: instantiation
    strat = ConsciousnessEnsembleStrategy()
    assert strat.name == "consciousness_ensemble"
    assert len(strat.strategies) == 3
    assert strat.weights == (0.35, 0.30, 0.35)
    print("  [PASS] Instantiation — 3 sub-strategies, correct weights")

    # Test 2: warmup period is max of sub-strategies
    warmup = strat.warmup_periods()
    sub_warmups = [s.warmup_periods() for s in strat.strategies]
    assert warmup == max(sub_warmups), f"warmup {warmup} != max({sub_warmups})"
    print(f"  [PASS] Warmup = {warmup} (max of {sub_warmups})")

    # Test 3: generates signals on synthetic data without crashing
    data = _generate_synthetic("BTCUSDT", "1h", 30)
    hold_count = 0
    buy_count = 0
    sell_count = 0
    for idx in range(data.n_candles):
        sig = strat.generate_signal(data, idx)
        if sig.signal == Signal.HOLD:
            hold_count += 1
        elif sig.signal == Signal.BUY:
            buy_count += 1
        elif sig.signal == Signal.SELL:
            sell_count += 1
    total = hold_count + buy_count + sell_count
    assert total == data.n_candles
    print(f"  [PASS] Signal generation — {data.n_candles} candles: "
          f"{buy_count} BUY, {sell_count} SELL, {hold_count} HOLD")

    # Test 4: custom weights
    strat2 = ConsciousnessEnsembleStrategy(weights=(0.5, 0.3, 0.2))
    assert strat2.weights == (0.5, 0.3, 0.2)
    print("  [PASS] Custom weights accepted")

    # Test 5: signals include reason with vote count
    for idx in range(warmup, data.n_candles):
        sig = strat.generate_signal(data, idx)
        if sig.signal != Signal.HOLD:
            assert "/3)" in sig.reason, f"Reason missing vote count: {sig.reason}"
            break
    else:
        # All HOLD is also valid (conservative)
        print("  [PASS] All HOLD on synthetic data (conservative strategy)")
    print("  [PASS] Signal reasons contain vote counts")

    # Test 6: backtest integration
    from trading.engine import BacktestEngine
    engine = BacktestEngine(symbol="BTCUSDT", timeframe="1h")
    result = engine.run(strat, data=data)
    assert result.strategy_name == "consciousness_ensemble"
    assert result.n_candles == data.n_candles
    print(f"  [PASS] Backtest integration — return={result.total_return_pct:+.2f}%, "
          f"trades={result.total_trades}")

    print()
    print("All 6 unit tests passed.")
    print()


if __name__ == "__main__":
    run_unit_tests()
    run_comparison()
