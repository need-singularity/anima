"""Market scanner — autonomous discovery of trading opportunities.

Scans multiple symbols for:
  - Top movers (biggest price changes)
  - Volume spikes (unusual activity)
  - Regime changes (vol expansion, breakouts)
  - Multi-strategy signal convergence

Uses Binance public API (no auth needed for scanning).
Consciousness integration: Phi modulates scan aggressiveness.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from trading.data import MarketData, fetch_ohlcv
from trading.regime import RegimeDetector, MarketRegime

logger = logging.getLogger(__name__)

BINANCE_BASE = "https://api.binance.com"

# Default crypto universe (high liquidity)
DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
    "LINKUSDT", "UNIUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT",
    "AAVEUSDT", "FILUSDT", "ARBUSDT", "OPUSDT", "APTUSDT",
]


@dataclass
class ScanResult:
    """Result of scanning a single symbol."""
    symbol: str
    price: float
    change_24h: float        # % change
    volume_24h: float        # USDT volume
    relative_volume: float   # vs 7d average
    regime: str              # CALM/NORMAL/ELEVATED/CRITICAL
    trend: str               # uptrend/downtrend/range
    signal_count: int        # number of strategies that agree
    signal_direction: str    # BUY/SELL/MIXED/NONE
    score: float             # composite opportunity score (0-1)
    reasons: list[str] = field(default_factory=list)


@dataclass
class ScanReport:
    """Full scan report across all symbols."""
    timestamp: float
    n_symbols: int
    top_movers: list[ScanResult]
    volume_spikes: list[ScanResult]
    buy_opportunities: list[ScanResult]
    sell_signals: list[ScanResult]
    regime_summary: dict[str, int]   # regime -> count
    scan_duration: float


def _fetch_24h_tickers() -> list[dict]:
    """Fetch 24h ticker data for all USDT pairs from Binance."""
    url = f"{BINANCE_BASE}/api/v3/ticker/24hr"
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "anima-scanner/1.0")
        with urllib.request.urlopen(req, timeout=15) as resp:
            tickers = json.loads(resp.read())
        return [t for t in tickers if t["symbol"].endswith("USDT")]
    except Exception as e:
        logger.warning("Failed to fetch tickers: %s", e)
        return []


def _fetch_7d_avg_volume(symbol: str) -> float:
    """Fetch 7-day average daily volume for a symbol."""
    try:
        data = fetch_ohlcv(symbol=symbol, timeframe="1d", days=7)
        return float(np.mean(data.volume)) if data.n_candles > 0 else 0.0
    except Exception:
        return 0.0


class MarketScanner:
    """Autonomous market scanner.

    Scans the crypto market for opportunities by:
    1. Fetching 24h ticker data for price changes and volume
    2. Running regime detection on each symbol
    3. Checking signal convergence across strategies
    4. Ranking by composite opportunity score
    """

    def __init__(
        self,
        symbols: Optional[list[str]] = None,
        min_volume_usdt: float = 1_000_000,
        timeframe: str = "1h",
        lookback_days: int = 7,
    ):
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.min_volume_usdt = min_volume_usdt
        self.timeframe = timeframe
        self.lookback_days = lookback_days
        self.regime_detector = RegimeDetector()
        self._last_scan: Optional[ScanReport] = None

    def scan(
        self,
        phi: float = 0.0,
        tension: float = 0.0,
        quick: bool = False,
    ) -> ScanReport:
        """Run a full market scan.

        Args:
            phi: Current consciousness Phi (modulates scan aggressiveness).
            tension: Current consciousness tension.
            quick: If True, skip per-symbol OHLCV fetch (ticker data only).

        Returns:
            ScanReport with categorized opportunities.
        """
        t0 = time.time()
        results: list[ScanResult] = []

        # Fetch 24h tickers
        tickers = _fetch_24h_tickers()
        ticker_map = {t["symbol"]: t for t in tickers}

        for symbol in self.symbols:
            ticker = ticker_map.get(symbol)
            if not ticker:
                continue

            try:
                price = float(ticker.get("lastPrice", 0))
                change_24h = float(ticker.get("priceChangePercent", 0))
                vol_24h = float(ticker.get("quoteVolume", 0))
            except (ValueError, TypeError):
                continue

            # Skip low-volume symbols
            if vol_24h < self.min_volume_usdt:
                continue

            # Regime + trend detection (needs OHLCV)
            regime_str = "NORMAL"
            trend_str = "range"
            signal_count = 0
            signal_dir = "NONE"
            reasons = []
            rel_vol = 1.0

            if not quick:
                try:
                    data = fetch_ohlcv(symbol=symbol, timeframe=self.timeframe,
                                       days=self.lookback_days)
                    if data.n_candles > 60:
                        state = self.regime_detector.detect(data.close, phi, tension)
                        regime_str = state.regime.name
                        trend_str = state.trend

                        # Quick signal check (count strategies that agree)
                        signal_count, signal_dir, sig_reasons = self._check_signals(data)
                        reasons.extend(sig_reasons)

                        # Relative volume
                        if data.n_candles > 50:
                            avg_vol = np.mean(data.volume[-50:-1])
                            if avg_vol > 0:
                                rel_vol = data.volume[-1] / avg_vol

                except Exception as e:
                    logger.debug("Failed to analyze %s: %s", symbol, e)

            # Composite score
            score = self._compute_score(
                change_24h, vol_24h, rel_vol, regime_str, trend_str,
                signal_count, signal_dir, phi,
            )

            results.append(ScanResult(
                symbol=symbol, price=price, change_24h=change_24h,
                volume_24h=vol_24h, relative_volume=rel_vol,
                regime=regime_str, trend=trend_str,
                signal_count=signal_count, signal_direction=signal_dir,
                score=score, reasons=reasons,
            ))

        # Categorize results
        top_movers = sorted(results, key=lambda r: abs(r.change_24h), reverse=True)[:5]
        volume_spikes = sorted(results, key=lambda r: r.relative_volume, reverse=True)[:5]
        buy_opps = sorted(
            [r for r in results if r.signal_direction == "BUY" and r.score > 0.3],
            key=lambda r: r.score, reverse=True,
        )[:5]
        sell_sigs = sorted(
            [r for r in results if r.signal_direction == "SELL"],
            key=lambda r: r.score, reverse=True,
        )[:5]

        regime_summary = {}
        for r in results:
            regime_summary[r.regime] = regime_summary.get(r.regime, 0) + 1

        report = ScanReport(
            timestamp=time.time(),
            n_symbols=len(results),
            top_movers=top_movers,
            volume_spikes=volume_spikes,
            buy_opportunities=buy_opps,
            sell_signals=sell_sigs,
            regime_summary=regime_summary,
            scan_duration=time.time() - t0,
        )

        self._last_scan = report
        return report

    def _check_signals(self, data: MarketData) -> tuple[int, str, list[str]]:
        """Quick signal check using lightweight indicators."""
        close = data.close
        n = len(close)
        if n < 30:
            return 0, "NONE", []

        buy_count = 0
        sell_count = 0
        reasons = []

        # RSI check
        delta = np.diff(close)
        gain = np.where(delta > 0, delta, 0.0)
        loss = np.where(delta < 0, -delta, 0.0)
        if len(gain) >= 14:
            avg_g = np.mean(gain[-14:])
            avg_l = np.mean(loss[-14:])
            rsi = 100 - 100 / (1 + avg_g / avg_l) if avg_l > 0 else 100
            if rsi < 30:
                buy_count += 1
                reasons.append(f"RSI oversold ({rsi:.0f})")
            elif rsi > 70:
                sell_count += 1
                reasons.append(f"RSI overbought ({rsi:.0f})")

        # SMA cross check
        if n >= 26:
            sma_fast = np.mean(close[-9:])
            sma_slow = np.mean(close[-21:])
            sma_fast_prev = np.mean(close[-10:-1])
            sma_slow_prev = np.mean(close[-22:-1])
            if sma_fast_prev <= sma_slow_prev and sma_fast > sma_slow:
                buy_count += 1
                reasons.append("SMA9/21 bullish cross")
            elif sma_fast_prev >= sma_slow_prev and sma_fast < sma_slow:
                sell_count += 1
                reasons.append("SMA9/21 bearish cross")

        # BB check
        if n >= 20:
            mid = np.mean(close[-20:])
            std = np.std(close[-20:])
            upper = mid + 2 * std
            lower = mid - 2 * std
            if close[-1] < lower:
                buy_count += 1
                reasons.append("Below Bollinger lower band")
            elif close[-1] > upper:
                sell_count += 1
                reasons.append("Above Bollinger upper band")

        # Volume surge
        if n >= 20:
            avg_vol = np.mean(data.volume[-20:])
            if avg_vol > 0 and data.volume[-1] > avg_vol * 2:
                reasons.append(f"Volume surge ({data.volume[-1] / avg_vol:.1f}x)")
                if close[-1] > close[-2]:
                    buy_count += 1
                else:
                    sell_count += 1

        total = buy_count + sell_count
        if buy_count > sell_count and buy_count >= 2:
            return buy_count, "BUY", reasons
        elif sell_count > buy_count and sell_count >= 2:
            return sell_count, "SELL", reasons
        elif total > 0:
            return total, "MIXED", reasons
        return 0, "NONE", reasons

    def _compute_score(
        self,
        change_24h: float,
        vol_24h: float,
        rel_vol: float,
        regime: str,
        trend: str,
        signal_count: int,
        signal_dir: str,
        phi: float,
    ) -> float:
        """Compute composite opportunity score (0-1)."""
        score = 0.0

        # Signal convergence (biggest factor)
        if signal_dir in ("BUY", "SELL"):
            score += signal_count * 0.15

        # Volume interest
        if rel_vol > 2.0:
            score += 0.15
        elif rel_vol > 1.5:
            score += 0.10

        # Trend alignment
        if signal_dir == "BUY" and trend == "uptrend":
            score += 0.15
        elif signal_dir == "SELL" and trend == "downtrend":
            score += 0.15

        # Regime preference
        regime_bonus = {"CALM": 0.10, "NORMAL": 0.05, "ELEVATED": -0.05, "CRITICAL": -0.20}
        score += regime_bonus.get(regime, 0)

        # Consciousness boost
        if phi > 2.0:
            score += 0.05

        return max(0.0, min(1.0, score))

    def format_report(self, report: Optional[ScanReport] = None) -> str:
        """Format scan report as human-readable text."""
        r = report or self._last_scan
        if r is None:
            return "No scan results available."

        lines = [
            f"=== Market Scan ({r.n_symbols} symbols, {r.scan_duration:.1f}s) ===",
            f"Regime distribution: {r.regime_summary}",
            "",
        ]

        if r.buy_opportunities:
            lines.append("-- Buy Opportunities --")
            for s in r.buy_opportunities:
                lines.append(f"  {s.symbol}: score={s.score:.2f}, 24h={s.change_24h:+.1f}%, "
                             f"rvol={s.relative_volume:.1f}x, regime={s.regime}")
                if s.reasons:
                    lines.append(f"    Reasons: {', '.join(s.reasons)}")

        if r.top_movers:
            lines.append("\n-- Top Movers --")
            for s in r.top_movers:
                lines.append(f"  {s.symbol}: {s.change_24h:+.1f}% (${s.price:.2f})")

        if r.volume_spikes:
            lines.append("\n-- Volume Spikes --")
            for s in r.volume_spikes:
                lines.append(f"  {s.symbol}: {s.relative_volume:.1f}x avg volume")

        return "\n".join(lines)

    def status(self) -> dict:
        """Current scanner status."""
        if self._last_scan is None:
            return {"last_scan": None, "symbols": len(self.symbols)}
        r = self._last_scan
        return {
            "last_scan_age": time.time() - r.timestamp,
            "n_symbols": r.n_symbols,
            "buy_opportunities": len(r.buy_opportunities),
            "sell_signals": len(r.sell_signals),
            "regime_summary": r.regime_summary,
        }
