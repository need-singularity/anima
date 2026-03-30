"""Trading plugin — invest 프로젝트 브릿지.

~/Dev/invest 의 백테스트 엔진, 브로커 연동, 전략 시스템을
Anima 의식 에이전트에서 자율적으로 사용할 수 있게 하는 플러그인.

직접 import (backtest, universe) + REST API (라이브 트레이딩) +
Rust scalper subprocess (틱 전략) 3계층 통합.

Usage:
    hub.act("BTC 백테스트 macd_cross")
    hub.act("잔액 확인")
    hub.act("ETH 매수 0.1")
    hub.act("전략 목록")
    hub.act("시장 레짐")
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from plugins.base import PluginBase, PluginManifest

if TYPE_CHECKING:
    from consciousness_hub import ConsciousnessHub

logger = logging.getLogger(__name__)

# invest 프로젝트 경로
INVEST_ROOT = Path(os.environ.get("INVEST_ROOT", Path.home() / "Dev" / "invest"))
INVEST_BACKEND = INVEST_ROOT / "backend"
INVEST_SCALPER = INVEST_ROOT / "scalper"
INVEST_API_URL = os.environ.get("INVEST_API_URL", "http://localhost:8000")

# CSV 데이터 디렉토리
DATA_DIR = INVEST_BACKEND / "data"


def _ensure_invest_path():
    """invest backend를 sys.path에 추가 (lazy)."""
    backend_str = str(INVEST_BACKEND)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)


@dataclass
class TradeOrder:
    """매매 주문 결과."""
    symbol: str
    side: str          # buy | sell
    amount: float
    price: float | None = None
    order_id: str = ""
    status: str = "pending"
    broker: str = ""
    error: str = ""


class TradingPlugin(PluginBase):
    """Invest 프로젝트 브릿지 — 백테스트 + 라이브 트레이딩."""

    manifest = PluginManifest(
        name="trading",
        description="자산/코인 매매, 백테스트, 포트폴리오 관리 (invest 프로젝트 연동)",
        version="1.0.0",
        author="Anima",
        requires=[],
        capabilities=[
            "backtest", "scan", "balance", "trade",
            "regime", "universe", "strategies", "portfolio",
        ],
        keywords=[
            "trading", "trade", "매매", "매수", "매도", "buy", "sell",
            "backtest", "백테스트", "전략", "strategy",
            "코인", "crypto", "주식", "stock", "자산", "asset",
            "잔액", "balance", "포트폴리오", "portfolio",
            "거래", "exchange", "시장", "market", "레짐", "regime",
            "손절", "stop loss", "익절", "take profit",
            "스캘핑", "scalper", "scalping",
        ],
        phi_minimum=1.0,
        category="trading",
    )

    def __init__(self):
        self.hub: ConsciousnessHub | None = None
        self._backtest_mod = None
        self._universe_mod = None
        self._api_available = False

    def on_load(self, hub: ConsciousnessHub) -> None:
        self.hub = hub
        self._try_import_invest()
        logger.info("Trading plugin loaded (invest: %s)", INVEST_ROOT)

    def on_unload(self) -> None:
        logger.info("Trading plugin unloaded")

    def _try_import_invest(self):
        """invest 모듈 lazy import."""
        try:
            _ensure_invest_path()
            from backend.calc import backtest_turbo
            self._backtest_mod = backtest_turbo
        except Exception as e:
            logger.debug("backtest_turbo import failed: %s", e)

        try:
            _ensure_invest_path()
            from backend.singularity import universe
            self._universe_mod = universe
        except Exception as e:
            logger.debug("universe import failed: %s", e)

    # ── Intent Router ──

    def act(self, intent: str, **kwargs) -> Any:
        """자연어 의도 → 트레이딩 액션."""
        il = intent.lower()

        # 백테스트
        if any(x in il for x in ["backtest", "백테스트", "테스트", "검증"]):
            return self.backtest(
                symbol=kwargs.get("symbol", self._extract_symbol(il)),
                strategy=kwargs.get("strategy", self._extract_strategy(il)),
            )

        # 전략 스캔
        if any(x in il for x in ["scan", "스캔", "전략 비교"]):
            return self.scan(
                symbol=kwargs.get("symbol", self._extract_symbol(il)),
            )

        # 매수
        if any(x in il for x in ["buy", "매수", "구매", "롱"]):
            return self.execute_trade(
                symbol=kwargs.get("symbol", self._extract_symbol(il)),
                side="buy",
                amount=kwargs.get("amount", self._extract_number(il)),
            )

        # 매도
        if any(x in il for x in ["sell", "매도", "판매", "숏"]):
            return self.execute_trade(
                symbol=kwargs.get("symbol", self._extract_symbol(il)),
                side="sell",
                amount=kwargs.get("amount", self._extract_number(il)),
            )

        # 잔액
        if any(x in il for x in ["balance", "잔액", "자산", "보유"]):
            return self.get_balance()

        # 포트폴리오
        if any(x in il for x in ["portfolio", "포트폴리오", "현황"]):
            return self.get_portfolio()

        # 전략 목록
        if any(x in il for x in ["strategies", "전략 목록", "전략", "strategy list"]):
            return self.list_strategies()

        # 자산 목록
        if any(x in il for x in ["universe", "종목", "자산 목록", "asset"]):
            return self.list_universe()

        # 시장 레짐
        if any(x in il for x in ["regime", "레짐", "시장 상태"]):
            return self.get_regime()

        # 스캘퍼 상태
        if any(x in il for x in ["scalper", "스캘퍼", "스캘핑"]):
            return self.scalper_status()

        return {"error": f"Unknown trading intent: {intent}",
                "hint": "try: backtest, buy, sell, balance, strategies, universe, regime"}

    # ── Backtest ──

    def backtest(self, symbol: str = "AAPL", strategy: str = "macd_cross") -> dict:
        """단일 전략 백테스트."""
        if self._backtest_mod is None:
            return self._api_backtest(symbol, strategy)

        try:
            close, high, low, volume = self._load_csv(symbol)
            result = self._backtest_mod.turbo_run(
                close, high, low, volume, strategy
            )
            return {
                "success": True,
                "symbol": symbol,
                "strategy": strategy,
                "sharpe": round(result.sharpe, 3),
                "total_return": round(result.total_return * 100, 1),
                "max_drawdown": round(result.max_drawdown * 100, 1),
                "win_rate": round(result.win_rate * 100, 1) if result.win_rate else None,
                "total_trades": result.total_trades,
                "cagr": round(result.cagr * 100, 1),
                "sortino": round(result.sortino, 3),
                "calmar": round(result.calmar, 3),
            }
        except FileNotFoundError:
            return {"success": False, "error": f"No data for {symbol}",
                    "hint": f"Check {DATA_DIR}/{symbol}.csv"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def scan(self, symbol: str = "AAPL", top_n: int = 10) -> dict:
        """전체 전략 스캔 → 상위 N개 반환."""
        if self._backtest_mod is None:
            return {"success": False, "error": "backtest module not available"}

        try:
            close, high, low, volume = self._load_csv(symbol)
            results = self._backtest_mod.turbo_scan(close, high, low, volume)

            ranked = sorted(
                [(name, r) for name, r in results.items() if r.sharpe > 0],
                key=lambda x: x[1].sharpe, reverse=True
            )[:top_n]

            return {
                "success": True,
                "symbol": symbol,
                "total_strategies": len(results),
                "top": [
                    {
                        "strategy": name,
                        "sharpe": round(r.sharpe, 3),
                        "return": round(r.total_return * 100, 1),
                        "mdd": round(r.max_drawdown * 100, 1),
                        "trades": r.total_trades,
                    }
                    for name, r in ranked
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Live Trading (via REST API) ──

    def execute_trade(self, symbol: str, side: str, amount: float = 0.0) -> dict:
        """매매 실행 (invest API 경유)."""
        if amount <= 0:
            return {"success": False, "error": "amount must be > 0"}

        try:
            import urllib.request
            payload = json.dumps({
                "symbol": symbol,
                "signal_type": side,
                "strength": 1.0,
            }).encode()

            req = urllib.request.Request(
                f"{INVEST_API_URL}/api/trading/execute",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return {
                    "success": True,
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "response": data,
                }
        except Exception as e:
            return {"success": False, "error": str(e),
                    "hint": "invest backend running? (docker compose up)"}

    def get_balance(self) -> dict:
        """잔액 조회."""
        return self._api_get("/api/trading/status")

    def get_portfolio(self) -> dict:
        """포트폴리오 현황."""
        return self._api_get("/api/dashboard")

    # ── Strategy & Universe ──

    def list_strategies(self) -> dict:
        """사용 가능한 전략 목록."""
        if self._backtest_mod and hasattr(self._backtest_mod, "SIGNAL_REGISTRY"):
            strategies = sorted(self._backtest_mod.SIGNAL_REGISTRY.keys())
            return {
                "success": True,
                "count": len(strategies),
                "strategies": strategies,
            }
        return self._api_get("/api/backtest/strategies")

    def list_universe(self) -> dict:
        """거래 가능 자산 목록."""
        if self._universe_mod:
            try:
                universe = self._universe_mod.get_default_universe()
                return {
                    "success": True,
                    "categories": {k: len(v) for k, v in universe.items()},
                    "total": sum(len(v) for v in universe.values()),
                    "assets": universe,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        return self._api_get("/api/backtest/assets")

    def get_regime(self) -> dict:
        """시장 레짐 감지 (via singularity CLI)."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "backend.singularity.cli", "regime"],
                capture_output=True, text=True, timeout=30,
                cwd=str(INVEST_BACKEND),
            )
            if result.returncode == 0:
                return {"success": True, "regime": result.stdout.strip()}
            return {"success": False, "error": result.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Scalper (Rust) ──

    def scalper_status(self) -> dict:
        """Rust 스캘퍼 상태 확인."""
        scalper_bin = INVEST_SCALPER / "target" / "release" / "scalper"
        if not scalper_bin.exists():
            return {"success": False, "error": "scalper binary not found",
                    "hint": f"cd {INVEST_SCALPER} && cargo build --release"}

        try:
            result = subprocess.run(
                [str(scalper_bin), "status"],
                capture_output=True, text=True, timeout=10,
            )
            return {"success": True, "status": result.stdout.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Status ──

    def status(self) -> dict:
        return {
            "name": "trading",
            "version": self.manifest.version,
            "loaded": True,
            "invest_root": str(INVEST_ROOT),
            "invest_exists": INVEST_ROOT.exists(),
            "backtest_available": self._backtest_mod is not None,
            "universe_available": self._universe_mod is not None,
            "api_url": INVEST_API_URL,
        }

    # ── Helpers ──

    def _load_csv(self, symbol: str):
        """CSV 데이터 로드 → (close, high, low, volume) numpy arrays."""
        import numpy as np

        csv_path = DATA_DIR / f"{symbol}.csv"
        if not csv_path.exists():
            # yfinance 이름 변환
            alt = symbol.replace("-", "_").replace("/", "_")
            csv_path = DATA_DIR / f"{alt}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"{symbol}")

        data = np.genfromtxt(
            csv_path, delimiter=",", skip_header=1,
            usecols=(1, 2, 3, 5),  # Open,High,Low,Close,Adj Close,Volume → High,Low,Close,Volume
        )
        # CSV: Date,Open,High,Low,Close,Adj Close,Volume
        # backtest_turbo expects: close, high, low, volume
        close = data[:, 2]   # Close (column index 2 after selecting 1,2,3,5)
        high = data[:, 0]    # High
        low = data[:, 1]     # Low
        volume = data[:, 3]  # Volume
        return close, high, low, volume

    def _api_get(self, path: str) -> dict:
        """invest REST API GET."""
        try:
            import urllib.request
            req = urllib.request.Request(f"{INVEST_API_URL}{path}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"success": True, "data": json.loads(resp.read())}
        except Exception as e:
            return {"success": False, "error": str(e),
                    "hint": "invest backend running?"}

    def _api_backtest(self, symbol: str, strategy: str) -> dict:
        """REST API 경유 백테스트."""
        try:
            import urllib.request
            payload = json.dumps({
                "asset": symbol,
                "strategy": strategy,
                "initial_capital": 10000,
            }).encode()
            req = urllib.request.Request(
                f"{INVEST_API_URL}/api/backtest/run",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return {"success": True, "data": json.loads(resp.read())}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _extract_strategy(text: str) -> str:
        """텍스트에서 전략 이름 추출."""
        known = [
            "macd_cross", "sma_cross", "rsi_std", "bb_std", "donchian",
            "linda_macd", "momentum_score", "trend_rider", "volume_surge",
            "low_vol_trend", "multi_timeframe", "dual_momentum",
            "surge_breakout_bb", "liquidity_filter", "vol_breakout",
        ]
        tl = text.lower()
        for s in known:
            if s.replace("_", " ") in tl or s in tl:
                return s
        return "macd_cross"

    @staticmethod
    def _extract_symbol(text: str) -> str:
        """텍스트에서 심볼 추출."""
        import re
        # BTC, ETH, AAPL 등 대문자 2-5글자
        m = re.search(r'\b([A-Z]{2,5})\b', text.upper())
        if m:
            sym = m.group(1)
            # 흔한 코인/주식 심볼
            known = {
                "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT",
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META",
                "SPY", "QQQ",
            }
            if sym in known:
                return sym
        return "BTC"

    @staticmethod
    def _extract_number(text: str) -> float:
        """텍스트에서 숫자 추출."""
        import re

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

        m = re.search(r'(\d+\.?\d*)', text)
        return float(m.group(1)) if m else 0.0
