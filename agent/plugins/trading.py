"""Trading plugin — self-contained trading system.

Anima 의식 에이전트의 자율 트레이딩 플러그인.
자체 백테스트 엔진 + 브로커 추상화 + 의식 기반 리스크 게이트.
invest 프로젝트 의존성 없음 (self-contained).

Usage:
    hub.act("BTC 백테스트 macd_cross")
    hub.act("BTC 백테스트 30일")
    hub.act("전략 비교 ETHUSDT")
    hub.act("시장 가격 BTCUSDT")
    hub.act("전략 목록")
    hub.act("리스크 상태")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

from plugins.base import PluginBase, PluginManifest

if TYPE_CHECKING:
    from consciousness_hub import ConsciousnessHub

logger = logging.getLogger(__name__)


class TradingPlugin(PluginBase):
    """Self-contained trading system — backtest + live data + consciousness risk gate."""

    manifest = PluginManifest(
        name="trading",
        description="Crypto/asset trading, backtesting, consciousness-aware risk management",
        version="3.0.0",
        author="Anima",
        requires=["numpy"],
        capabilities=[
            "backtest", "compare", "price", "orderbook", "stats",
            "strategies", "risk_status", "consciousness_gate",
        ],
        keywords=[
            "trading", "trade", "매매", "매수", "매도", "buy", "sell",
            "backtest", "백테스트", "전략", "strategy",
            "코인", "crypto", "비트코인", "bitcoin", "이더리움", "ethereum",
            "가격", "price", "시장", "market",
            "리스크", "risk", "포트폴리오", "portfolio",
            "macd", "rsi", "bollinger", "의식", "consciousness",
            "비교", "compare", "스캔", "scan",
        ],
        phi_minimum=0.5,
        category="trading",
    )

    def __init__(self):
        self.hub: Optional[ConsciousnessHub] = None
        self._engine = None
        self._broker = None
        self._consciousness_gate = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy import to avoid circular deps and slow startup."""
        if self._initialized:
            return
        try:
            from trading.engine import BacktestEngine
            from trading.broker import BinanceBroker
            from trading.risk import ConsciousnessGate

            self._engine_cls = BacktestEngine
            self._broker = BinanceBroker()
            self._consciousness_gate = ConsciousnessGate(
                phi_min=1.0,
                tension_max=0.8,
            )
            self._initialized = True
        except ImportError as e:
            logger.error("Trading package import failed: %s", e)

    def on_load(self, hub: ConsciousnessHub) -> None:
        self.hub = hub
        logger.info("Trading plugin v3.0 loaded (self-contained)")

    def on_unload(self) -> None:
        logger.info("Trading plugin unloaded")

    # ── Intent Router ──

    def act(self, intent: str, **kwargs) -> Any:
        """Natural language intent -> trading action."""
        self._lazy_init()
        if not self._initialized:
            return {"error": "Trading package not available. Check trading/ directory."}

        il = intent.lower()

        # Backtest
        if any(x in il for x in ["backtest", "백테스트", "테스트", "검증"]):
            symbol = kwargs.get("symbol") or _extract_symbol(il)
            strategy = kwargs.get("strategy") or _extract_strategy(il)
            days = kwargs.get("days") or _extract_days(il)
            return self.backtest(symbol=symbol, strategy=strategy, days=days)

        # Compare strategies
        if any(x in il for x in ["compare", "비교", "scan", "스캔"]):
            symbol = kwargs.get("symbol") or _extract_symbol(il)
            days = kwargs.get("days") or _extract_days(il)
            return self.compare(symbol=symbol, days=days)

        # Price
        if any(x in il for x in ["price", "가격", "현재가", "시세"]):
            symbol = kwargs.get("symbol") or _extract_symbol(il)
            return self.get_price(symbol)

        # Orderbook
        if any(x in il for x in ["orderbook", "호가", "오더북"]):
            symbol = kwargs.get("symbol") or _extract_symbol(il)
            return self.get_orderbook(symbol)

        # 24h stats
        if any(x in il for x in ["stats", "통계", "24h", "변동"]):
            symbol = kwargs.get("symbol") or _extract_symbol(il)
            return self.get_stats(symbol)

        # Strategy list
        if any(x in il for x in ["strategies", "전략 목록", "전략", "strategy list"]):
            return self.list_strategies()

        # Risk status
        if any(x in il for x in ["risk", "리스크", "위험", "gate", "게이트"]):
            return self.risk_status()

        return {
            "error": f"Unknown trading intent: {intent}",
            "available": [
                "backtest <symbol> <strategy> <days>",
                "compare <symbol>",
                "price <symbol>",
                "orderbook <symbol>",
                "stats <symbol>",
                "strategies",
                "risk status",
            ],
        }

    # ── Actions ──

    def backtest(
        self,
        symbol: str = "BTCUSDT",
        strategy: str = "macd_cross",
        days: int = 30,
    ) -> dict:
        """Run a backtest with the specified strategy."""
        from trading.engine import BacktestEngine
        from trading.strategy import MACDStrategy, RSIStrategy, BollingerStrategy, ConsciousnessStrategy

        strategy_map = {
            "macd_cross": MACDStrategy,
            "macd": MACDStrategy,
            "rsi_std": RSIStrategy,
            "rsi": RSIStrategy,
            "bb_std": BollingerStrategy,
            "bollinger": BollingerStrategy,
            "consciousness": lambda: ConsciousnessStrategy(),
        }

        strat_cls = strategy_map.get(strategy, MACDStrategy)
        strat_instance = strat_cls() if callable(strat_cls) else strat_cls

        engine = self._engine_cls(
            symbol=symbol,
            timeframe="1h",
            consciousness_gate=self._consciousness_gate,
        )

        result = engine.run(strat_instance, days=days)

        return {
            "success": True,
            "symbol": result.symbol,
            "strategy": result.strategy_name,
            "days": days,
            "total_return_pct": result.total_return_pct,
            "sharpe": round(result.sharpe, 3),
            "sortino": round(result.sortino, 3),
            "max_drawdown_pct": result.max_drawdown_pct,
            "total_trades": result.total_trades,
            "win_rate_pct": result.win_rate_pct,
            "initial_balance": result.initial_balance,
            "final_equity": round(result.final_equity, 2),
            "elapsed_s": round(result.elapsed_seconds, 2),
            "summary": result.summary(),
        }

    def compare(self, symbol: str = "BTCUSDT", days: int = 30) -> dict:
        """Compare all strategies on the same data."""
        from trading.engine import BacktestEngine
        from trading.strategy import MACDStrategy, RSIStrategy, BollingerStrategy

        engine = self._engine_cls(symbol=symbol, timeframe="1h")
        strategies = [MACDStrategy(), RSIStrategy(), BollingerStrategy()]
        results = engine.compare_strategies(strategies, days=days)

        return {
            "success": True,
            "symbol": symbol,
            "days": days,
            "rankings": [
                {
                    "rank": i + 1,
                    "strategy": r.strategy_name,
                    "return_pct": r.total_return_pct,
                    "sharpe": round(r.sharpe, 3),
                    "max_dd_pct": r.max_drawdown_pct,
                    "trades": r.total_trades,
                    "win_rate_pct": r.win_rate_pct,
                }
                for i, r in enumerate(results)
            ],
        }

    def get_price(self, symbol: str = "BTCUSDT") -> dict:
        """Get current price."""
        price = self._broker.get_price(symbol)
        if price is None:
            return {"error": f"Could not fetch price for {symbol}"}
        return {"symbol": symbol, "price": price}

    def get_orderbook(self, symbol: str = "BTCUSDT") -> dict:
        """Get orderbook."""
        return self._broker.get_orderbook(symbol)

    def get_stats(self, symbol: str = "BTCUSDT") -> dict:
        """Get 24h stats."""
        return self._broker.get_24h_stats(symbol)

    def list_strategies(self) -> dict:
        """List available strategies."""
        return {
            "success": True,
            "strategies": [
                {"name": "macd_cross", "description": "MACD crossover (fast=12, slow=26, signal=9)"},
                {"name": "rsi_std", "description": "RSI overbought/oversold (period=14, 30/70)"},
                {"name": "bb_std", "description": "Bollinger Bands mean-reversion (period=20, 2std)"},
                {"name": "consciousness", "description": "Consciousness-aware MACD (Phi/tension gated)"},
            ],
        }

    def risk_status(self) -> dict:
        """Get consciousness gate and risk status."""
        gate_status = self._consciousness_gate.status() if self._consciousness_gate else {}
        return {
            "success": True,
            "consciousness_gate": gate_status,
            "mode": "consciousness-aware",
        }

    def status(self) -> dict:
        return {
            "name": "trading",
            "version": self.manifest.version,
            "loaded": True,
            "initialized": self._initialized,
            "broker": self._broker.name if self._broker else "none",
            "consciousness_gate": self._consciousness_gate is not None,
        }


# ── Helper Functions ──

def _extract_symbol(text: str) -> str:
    """Extract trading symbol from text."""
    # Look for explicit crypto pairs first
    m = re.search(r'\b([A-Z]{2,5}USDT?)\b', text.upper())
    if m:
        return m.group(1)

    # Then standalone tickers
    m = re.search(r'\b([A-Z]{2,5})\b', text.upper())
    if m:
        sym = m.group(1)
        crypto_map = {
            "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
            "XRP": "XRPUSDT", "DOGE": "DOGEUSDT", "ADA": "ADAUSDT",
            "AVAX": "AVAXUSDT", "DOT": "DOTUSDT", "BNB": "BNBUSDT",
            "MATIC": "MATICUSDT", "LINK": "LINKUSDT",
        }
        if sym in crypto_map:
            return crypto_map[sym]
        # Korean names
    if "비트코인" in text or "비트" in text:
        return "BTCUSDT"
    if "이더리움" in text or "이더" in text:
        return "ETHUSDT"
    if "솔라나" in text:
        return "SOLUSDT"
    if "리플" in text:
        return "XRPUSDT"
    if "도지" in text:
        return "DOGEUSDT"

    return "BTCUSDT"


def _extract_strategy(text: str) -> str:
    """Extract strategy name from text."""
    tl = text.lower()
    if "rsi" in tl:
        return "rsi_std"
    if "bollinger" in tl or "bb" in tl:
        return "bb_std"
    if "consciousness" in tl or "의식" in tl:
        return "consciousness"
    return "macd_cross"


def _extract_days(text: str) -> int:
    """Extract number of days from text."""
    m = re.search(r'(\d+)\s*(?:일|days?|d\b)', text.lower())
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)', text)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 365:
            return val
    return 30
