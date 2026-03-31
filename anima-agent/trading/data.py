"""Market data fetching — free APIs, no auth required.

Supports Binance public API for crypto OHLCV data.
Falls back to generated sample data for offline testing.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Binance public API (no auth needed)
BINANCE_BASE = "https://api.binance.com"
BINANCE_KLINES = f"{BINANCE_BASE}/api/v3/klines"

# Timeframe -> milliseconds
TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
    "1w": 604_800_000,
}


@dataclass
class MarketData:
    """OHLCV market data container."""

    symbol: str
    timeframe: str
    timestamps: np.ndarray  # unix ms
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray

    @property
    def n_candles(self) -> int:
        return len(self.close)

    @property
    def start_time(self) -> datetime:
        return datetime.fromtimestamp(self.timestamps[0] / 1000, tz=timezone.utc)

    @property
    def end_time(self) -> datetime:
        return datetime.fromtimestamp(self.timestamps[-1] / 1000, tz=timezone.utc)

    def returns(self) -> np.ndarray:
        """Log returns."""
        return np.diff(np.log(self.close))

    def slice(self, start_idx: int, end_idx: int) -> "MarketData":
        """Slice a sub-range of candles."""
        return MarketData(
            symbol=self.symbol,
            timeframe=self.timeframe,
            timestamps=self.timestamps[start_idx:end_idx],
            open=self.open[start_idx:end_idx],
            high=self.high[start_idx:end_idx],
            low=self.low[start_idx:end_idx],
            close=self.close[start_idx:end_idx],
            volume=self.volume[start_idx:end_idx],
        )


def fetch_ohlcv(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    days: int = 30,
    limit: int = 1000,
) -> MarketData:
    """Fetch OHLCV data from Binance public API.

    Args:
        symbol: Trading pair (e.g. BTCUSDT, ETHUSDT).
        timeframe: Candle interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w).
        days: Number of days of history.
        limit: Max candles per API call (Binance max 1000).

    Returns:
        MarketData with OHLCV arrays.

    Falls back to synthetic data if API is unreachable.
    """
    tf_ms = TIMEFRAME_MS.get(timeframe, 3_600_000)
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (days * 86_400_000)

    all_candles: list = []
    cursor = start_ms

    while cursor < now_ms:
        batch_limit = min(limit, max(1, (now_ms - cursor) // tf_ms + 1))
        url = (
            f"{BINANCE_KLINES}"
            f"?symbol={symbol}"
            f"&interval={timeframe}"
            f"&startTime={cursor}"
            f"&limit={batch_limit}"
        )
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "anima-trading/1.0")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            if not data:
                break

            all_candles.extend(data)

            # Move cursor past the last candle
            last_ts = data[-1][0]
            cursor = last_ts + tf_ms

            # Binance rate limit: be polite
            if len(data) == limit:
                time.sleep(0.1)
            else:
                break

        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            logger.warning("Binance API failed (%s), using synthetic data", e)
            return _generate_synthetic(symbol, timeframe, days)
        except Exception as e:
            logger.warning("Unexpected error fetching data: %s", e)
            return _generate_synthetic(symbol, timeframe, days)

    if not all_candles:
        logger.info("No candles fetched, generating synthetic data")
        return _generate_synthetic(symbol, timeframe, days)

    return _parse_binance_klines(symbol, timeframe, all_candles)


def _parse_binance_klines(
    symbol: str, timeframe: str, klines: list
) -> MarketData:
    """Parse Binance kline response into MarketData.

    Binance kline format:
    [open_time, open, high, low, close, volume, close_time, ...]
    """
    n = len(klines)
    timestamps = np.zeros(n, dtype=np.float64)
    o = np.zeros(n)
    h = np.zeros(n)
    lo = np.zeros(n)
    c = np.zeros(n)
    v = np.zeros(n)

    for i, k in enumerate(klines):
        timestamps[i] = float(k[0])
        o[i] = float(k[1])
        h[i] = float(k[2])
        lo[i] = float(k[3])
        c[i] = float(k[4])
        v[i] = float(k[5])

    return MarketData(
        symbol=symbol,
        timeframe=timeframe,
        timestamps=timestamps,
        open=o,
        high=h,
        low=lo,
        close=c,
        volume=v,
    )


def _generate_synthetic(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    days: int = 30,
    base_price: float = 60000.0,
    volatility: float = 0.02,
) -> MarketData:
    """Generate synthetic OHLCV data for offline testing.

    Uses geometric Brownian motion with mean-reversion.
    """
    tf_ms = TIMEFRAME_MS.get(timeframe, 3_600_000)
    n_candles = int(days * 86_400_000 / tf_ms)
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - n_candles * tf_ms

    rng = np.random.default_rng(42)
    timestamps = np.arange(start_ms, start_ms + n_candles * tf_ms, tf_ms, dtype=np.float64)
    n_candles = len(timestamps)

    # GBM with mean-reversion
    log_returns = rng.normal(0, volatility, n_candles)
    # Mean-revert toward base_price
    prices = np.zeros(n_candles)
    prices[0] = base_price
    for i in range(1, n_candles):
        revert = -0.001 * (prices[i - 1] - base_price) / base_price
        prices[i] = prices[i - 1] * np.exp(log_returns[i] + revert)

    # Generate OHLC from close prices
    spread = volatility * 0.5
    high = prices * (1 + rng.uniform(0, spread, n_candles))
    low = prices * (1 - rng.uniform(0, spread, n_candles))
    open_ = np.roll(prices, 1)
    open_[0] = base_price
    volume = rng.exponential(1000, n_candles) * prices / base_price

    return MarketData(
        symbol=symbol,
        timeframe=timeframe,
        timestamps=timestamps,
        open=open_,
        high=high,
        low=low,
        close=prices,
        volume=volume,
    )
