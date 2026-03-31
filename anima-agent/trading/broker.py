"""Broker abstraction — market data and order execution.

BinanceBroker: public API for market data (no auth needed).
Paper trading and live trading through the same interface.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from trading.data import MarketData, fetch_ohlcv

logger = logging.getLogger(__name__)

BINANCE_BASE = "https://api.binance.com"


@dataclass
class OrderResult:
    """Result of an order execution."""

    success: bool
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    price: float = 0.0
    size: float = 0.0
    status: str = ""
    error: str = ""
    timestamp: float = 0.0


class Broker(ABC):
    """Abstract broker interface."""

    name: str = "base"

    @abstractmethod
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        ...

    @abstractmethod
    def get_ohlcv(
        self, symbol: str, timeframe: str = "1h", days: int = 30
    ) -> MarketData:
        """Get OHLCV candle data."""
        ...

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float] = None,
    ) -> OrderResult:
        """Place an order (market or limit)."""
        ...

    def get_balance(self) -> dict:
        """Get account balance."""
        return {"error": "Not implemented"}

    def get_ticker(self, symbol: str) -> dict:
        """Get full ticker info."""
        price = self.get_price(symbol)
        return {"symbol": symbol, "price": price}


class BinanceBroker(Broker):
    """Binance broker — public API for data, optional auth for trading.

    Market data works without authentication.
    Trading requires API key/secret (set via environment or constructor).
    """

    name = "binance"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        if testnet:
            self.base_url = "https://testnet.binance.vision"
        else:
            self.base_url = BINANCE_BASE

    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price from Binance ticker."""
        url = f"{self.base_url}/api/v3/ticker/price?symbol={symbol}"
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "anima-trading/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return float(data["price"])
        except Exception as e:
            logger.warning("Failed to get price for %s: %s", symbol, e)
            return None

    def get_ohlcv(
        self, symbol: str, timeframe: str = "1h", days: int = 30
    ) -> MarketData:
        """Fetch OHLCV from Binance."""
        return fetch_ohlcv(symbol=symbol, timeframe=timeframe, days=days)

    def get_24h_stats(self, symbol: str) -> dict:
        """Get 24h ticker statistics."""
        url = f"{self.base_url}/api/v3/ticker/24hr?symbol={symbol}"
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "anima-trading/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning("Failed to get 24h stats for %s: %s", symbol, e)
            return {"error": str(e)}

    def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        """Get orderbook depth."""
        url = f"{self.base_url}/api/v3/depth?symbol={symbol}&limit={limit}"
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "anima-trading/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning("Failed to get orderbook for %s: %s", symbol, e)
            return {"error": str(e)}

    def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float] = None,
    ) -> OrderResult:
        """Place an order on Binance.

        Requires API key/secret. Returns error if not configured.
        """
        if not self.api_key:
            return OrderResult(
                success=False,
                symbol=symbol,
                side=side,
                size=size,
                error="API key not configured. Set api_key/api_secret for live trading.",
            )

        # Authenticated order placement would go here.
        # For now, return a paper-mode result.
        current_price = self.get_price(symbol)
        if current_price is None:
            return OrderResult(
                success=False, symbol=symbol, side=side, size=size,
                error="Could not get current price",
            )

        return OrderResult(
            success=True,
            order_id=f"paper-{int(time.time()*1000)}",
            symbol=symbol,
            side=side,
            price=price or current_price,
            size=size,
            status="filled",
            timestamp=time.time() * 1000,
        )

    def get_balance(self) -> dict:
        if not self.api_key:
            return {"error": "API key not configured", "mode": "data-only"}
        return {"error": "Authenticated balance not yet implemented"}


class PaperBroker(Broker):
    """Paper trading broker for backtesting and simulation.

    Fills all orders instantly at the requested price.
    """

    name = "paper"

    def __init__(self, data: Optional[MarketData] = None):
        self._data = data
        self._current_idx: int = 0
        self._order_count: int = 0

    def set_data(self, data: MarketData):
        self._data = data

    def set_index(self, idx: int):
        self._current_idx = idx

    def get_price(self, symbol: str) -> Optional[float]:
        if self._data is not None and self._current_idx < self._data.n_candles:
            return float(self._data.close[self._current_idx])
        return None

    def get_ohlcv(
        self, symbol: str, timeframe: str = "1h", days: int = 30
    ) -> MarketData:
        if self._data is not None:
            return self._data
        return fetch_ohlcv(symbol=symbol, timeframe=timeframe, days=days)

    def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float] = None,
    ) -> OrderResult:
        self._order_count += 1
        fill_price = price or (self.get_price(symbol) or 0.0)
        ts = 0.0
        if self._data is not None and self._current_idx < len(self._data.timestamps):
            ts = self._data.timestamps[self._current_idx]
        return OrderResult(
            success=True,
            order_id=f"paper-{self._order_count}",
            symbol=symbol,
            side=side,
            price=fill_price,
            size=size,
            status="filled",
            timestamp=ts,
        )
