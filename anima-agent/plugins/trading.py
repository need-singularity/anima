"""Trading plugin — invest project bridge.

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
    hub.act("스캘퍼 상태")
    hub.act("포트폴리오 현황")
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

from plugins.base import PluginBase, PluginManifest

if TYPE_CHECKING:
    from consciousness_hub import ConsciousnessHub

logger = logging.getLogger(__name__)

# invest project paths
INVEST_ROOT = Path(os.environ.get("INVEST_ROOT", Path.home() / "Dev" / "invest"))
INVEST_BACKEND = INVEST_ROOT / "backend"
INVEST_SCALPER = INVEST_ROOT / "scalper"
INVEST_API_URL = os.environ.get("INVEST_API_URL", "http://localhost:8000")

# CSV data directory
DATA_DIR = INVEST_BACKEND / "data"

# API retry configuration
API_TIMEOUT = 15          # seconds
API_MAX_RETRIES = 3
API_RETRY_DELAY = 1.0     # seconds (doubles each retry)
SCALPER_TIMEOUT = 30       # seconds for scalper subprocess


def _ensure_invest_path():
    """Add invest backend to sys.path (lazy)."""
    backend_str = str(INVEST_BACKEND)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)


@dataclass
class TradeOrder:
    """Trade order result."""
    symbol: str
    side: str          # buy | sell
    amount: float
    price: float | None = None
    order_id: str = ""
    status: str = "pending"
    broker: str = ""
    error: str = ""


# ══════════════════════════════════════════════════════════════════════
#  REST API Client — robust HTTP with retry, timeout, error handling
# ══════════════════════════════════════════════════════════════════════

class InvestAPIClient:
    """HTTP client for invest FastAPI backend with retry logic."""

    def __init__(self, base_url: str = INVEST_API_URL):
        self.base_url = base_url.rstrip("/")
        self._last_error: str = ""
        self._request_count: int = 0
        self._error_count: int = 0

    def get(self, path: str, params: dict | None = None,
            timeout: float = API_TIMEOUT) -> dict:
        """GET request with retry."""
        url = f"{self.base_url}{path}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{qs}"
        return self._request(url, method="GET", timeout=timeout)

    def post(self, path: str, data: dict | None = None,
             timeout: float = API_TIMEOUT) -> dict:
        """POST request with retry."""
        url = f"{self.base_url}{path}"
        return self._request(url, method="POST", body=data, timeout=timeout)

    def _request(self, url: str, method: str = "GET",
                 body: dict | None = None,
                 timeout: float = API_TIMEOUT) -> dict:
        """Execute HTTP request with exponential backoff retry."""
        import urllib.request
        import urllib.error

        self._request_count += 1
        last_err = None
        delay = API_RETRY_DELAY

        for attempt in range(API_MAX_RETRIES):
            try:
                payload = json.dumps(body).encode() if body else None
                headers = {"Content-Type": "application/json"} if body else {}

                req = urllib.request.Request(
                    url, data=payload, headers=headers, method=method,
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                    data = json.loads(raw) if raw else {}
                    return {"success": True, "data": data}

            except urllib.error.HTTPError as e:
                last_err = e
                body_text = ""
                try:
                    body_text = e.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    pass
                # Don't retry 4xx client errors (except 429)
                if 400 <= e.code < 500 and e.code != 429:
                    self._error_count += 1
                    self._last_error = f"HTTP {e.code}: {body_text}"
                    return {
                        "success": False,
                        "error": f"HTTP {e.code}: {e.reason}",
                        "detail": body_text,
                    }
                logger.warning("API %s %s attempt %d: HTTP %d",
                               method, url, attempt + 1, e.code)

            except urllib.error.URLError as e:
                last_err = e
                logger.warning("API %s %s attempt %d: %s",
                               method, url, attempt + 1, e.reason)

            except TimeoutError:
                last_err = TimeoutError(f"Timeout after {timeout}s")
                logger.warning("API %s %s attempt %d: timeout",
                               method, url, attempt + 1)

            except Exception as e:
                last_err = e
                logger.warning("API %s %s attempt %d: %s",
                               method, url, attempt + 1, e)

            # Exponential backoff before retry
            if attempt < API_MAX_RETRIES - 1:
                time.sleep(delay)
                delay *= 2

        # All retries exhausted
        self._error_count += 1
        err_msg = str(last_err) if last_err else "Unknown error"
        self._last_error = err_msg
        return {
            "success": False,
            "error": err_msg,
            "hint": f"Is invest backend running at {self.base_url}? (make dev)",
            "retries_exhausted": True,
        }

    @property
    def stats(self) -> dict:
        return {
            "requests": self._request_count,
            "errors": self._error_count,
            "last_error": self._last_error,
            "base_url": self.base_url,
        }


# ══════════════════════════════════════════════════════════════════════
#  Rust Scalper Bridge — subprocess interface to scalper CLI
# ══════════════════════════════════════════════════════════════════════

class ScalperBridge:
    """Bridge to the Rust scalper binary via subprocess."""

    def __init__(self, scalper_dir: Path = INVEST_SCALPER):
        self.scalper_dir = scalper_dir
        self._bin_path: Path | None = None
        self._detect_binary()

    def _detect_binary(self):
        """Find scalper binary (release > debug)."""
        release = self.scalper_dir / "target" / "release" / "scalper"
        debug = self.scalper_dir / "target" / "debug" / "scalper"
        if release.exists():
            self._bin_path = release
        elif debug.exists():
            self._bin_path = debug

    @property
    def available(self) -> bool:
        return self._bin_path is not None

    def _run(self, command: str, config: str | None = None,
             timeout: float = SCALPER_TIMEOUT) -> dict:
        """Run a scalper CLI command and parse output."""
        if not self.available:
            return {
                "success": False,
                "error": "Scalper binary not found",
                "hint": f"cd {self.scalper_dir} && cargo build --release",
            }

        cmd = [str(self._bin_path), command]
        if config:
            cmd = [str(self._bin_path), "--config", config, command]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.scalper_dir),
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": stderr or f"Exit code {result.returncode}",
                    "stdout": stdout,
                }

            # Try to parse as JSON first (scalper may output JSON)
            try:
                parsed = json.loads(stdout)
                return {"success": True, "data": parsed}
            except (json.JSONDecodeError, ValueError):
                pass

            # Parse structured text output
            return {
                "success": True,
                "output": stdout,
                "parsed": self._parse_text_output(command, stdout),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Scalper command '{command}' timed out after {timeout}s",
            }
        except FileNotFoundError:
            self._bin_path = None
            return {
                "success": False,
                "error": "Scalper binary not found or not executable",
                "hint": f"cd {self.scalper_dir} && cargo build --release",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_text_output(self, command: str, text: str) -> dict:
        """Parse scalper text output into structured data."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        result: dict[str, Any] = {}

        if command == "status":
            for line in lines:
                if ":" in line:
                    key, _, val = line.partition(":")
                    result[key.strip().lower().replace(" ", "_")] = val.strip()
            return result

        if command == "regime":
            # Look for regime labels: CALM, NORMAL, ELEVATED, CRITICAL
            for line in lines:
                upper = line.upper()
                for regime in ("CRITICAL", "ELEVATED", "NORMAL", "CALM"):
                    if regime in upper:
                        result["regime"] = regime.lower()
                        result["description"] = line
                        return result
            result["raw"] = text
            return result

        if command == "strategies":
            strategies = []
            for line in lines:
                # Each strategy line typically has a name
                cleaned = line.lstrip("- ").strip()
                if cleaned and not cleaned.startswith("#"):
                    strategies.append(cleaned)
            result["strategies"] = strategies
            result["count"] = len(strategies)
            return result

        if command == "combos":
            for line in lines:
                if ":" in line:
                    key, _, val = line.partition(":")
                    result[key.strip().lower().replace(" ", "_")] = val.strip()
            return result

        # Generic: return lines
        result["lines"] = lines
        return result

    def status(self) -> dict:
        """Get scalper system status."""
        return self._run("status")

    def regime(self) -> dict:
        """Get current market regime from scalper."""
        return self._run("regime")

    def strategies(self) -> dict:
        """List registered scalper strategies."""
        return self._run("strategies")

    def combos(self) -> dict:
        """Show strategy combination counts."""
        return self._run("combos")

    def run_paper(self, config: str | None = None) -> dict:
        """Start scalper in paper trading mode (non-blocking check)."""
        return self._run("paper", config=config, timeout=SCALPER_TIMEOUT)

    def run_live(self, config: str | None = None) -> dict:
        """Start scalper in live mode (returns immediately with PID)."""
        if not self.available:
            return {
                "success": False,
                "error": "Scalper binary not found",
                "hint": f"cd {self.scalper_dir} && cargo build --release",
            }

        cmd = [str(self._bin_path), "run"]
        if config:
            cmd = [str(self._bin_path), "--config", config, "run"]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.scalper_dir),
            )
            return {
                "success": True,
                "pid": proc.pid,
                "command": " ".join(cmd),
                "note": "Scalper started in background",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════
#  Trading Plugin — main class
# ══════════════════════════════════════════════════════════════════════

class TradingPlugin(PluginBase):
    """Invest project bridge — backtest + live trading + Rust scalper."""

    manifest = PluginManifest(
        name="trading",
        description="Asset/crypto trading, backtesting, portfolio management (invest project bridge)",
        version="2.0.0",
        author="Anima",
        requires=[],
        capabilities=[
            "backtest", "scan", "balance", "trade",
            "regime", "universe", "strategies", "portfolio",
            "scalper_status", "scalper_regime", "scalper_strategies",
            "scalper_run", "orders", "emergency_stop",
        ],
        keywords=[
            "trading", "trade", "매매", "매수", "매도", "buy", "sell",
            "backtest", "백테스트", "전략", "strategy",
            "코인", "crypto", "주식", "stock", "자산", "asset",
            "잔액", "balance", "포트폴리오", "portfolio",
            "거래", "exchange", "시장", "market", "레짐", "regime",
            "손절", "stop loss", "익절", "take profit",
            "스캘핑", "scalper", "scalping",
            "주문", "orders", "긴급정지", "emergency",
        ],
        phi_minimum=1.0,
        category="trading",
    )

    def __init__(self):
        self.hub: ConsciousnessHub | None = None
        self._backtest_mod = None
        self._universe_mod = None
        self._api = InvestAPIClient()
        self._scalper = ScalperBridge()

    def on_load(self, hub: ConsciousnessHub) -> None:
        self.hub = hub
        self._try_import_invest()
        logger.info("Trading plugin loaded (invest: %s, scalper: %s)",
                     INVEST_ROOT, "available" if self._scalper.available else "not found")

    def on_unload(self) -> None:
        logger.info("Trading plugin unloaded")

    def _try_import_invest(self):
        """invest module lazy import."""
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
        """Natural language intent -> trading action."""
        il = intent.lower()

        # Backtest
        if any(x in il for x in ["backtest", "백테스트", "테스트", "검증"]):
            return self.backtest(
                symbol=kwargs.get("symbol", self._extract_symbol(il)),
                strategy=kwargs.get("strategy", self._extract_strategy(il)),
            )

        # Strategy scan
        if any(x in il for x in ["scan", "스캔", "전략 비교"]):
            return self.scan(
                symbol=kwargs.get("symbol", self._extract_symbol(il)),
            )

        # Buy
        if any(x in il for x in ["buy", "매수", "구매", "롱"]):
            return self.execute_trade(
                symbol=kwargs.get("symbol", self._extract_symbol(il)),
                side="buy",
                amount=kwargs.get("amount", self._extract_number(il)),
            )

        # Sell
        if any(x in il for x in ["sell", "매도", "판매", "숏"]):
            return self.execute_trade(
                symbol=kwargs.get("symbol", self._extract_symbol(il)),
                side="sell",
                amount=kwargs.get("amount", self._extract_number(il)),
            )

        # Emergency stop
        if any(x in il for x in ["emergency", "긴급정지", "긴급 정지", "stop all"]):
            return self.emergency_stop()

        # Balance
        if any(x in il for x in ["balance", "잔액", "자산", "보유"]):
            return self.get_balance()

        # Portfolio
        if any(x in il for x in ["portfolio", "포트폴리오", "현황", "포지션"]):
            return self.get_portfolio()

        # Orders
        if any(x in il for x in ["orders", "주문", "주문내역", "order history"]):
            return self.get_orders()

        # Strategy list
        if any(x in il for x in ["strategies", "전략 목록", "전략", "strategy list"]):
            return self.list_strategies()

        # Universe
        if any(x in il for x in ["universe", "종목", "자산 목록", "asset"]):
            return self.list_universe()

        # Market regime (scalper first, then singularity CLI)
        if any(x in il for x in ["regime", "레짐", "시장 상태"]):
            return self.get_regime()

        # Scalper-specific commands
        if any(x in il for x in ["scalper status", "스캘퍼 상태"]):
            return self.scalper_status()
        if any(x in il for x in ["scalper strateg", "스캘퍼 전략"]):
            return self.scalper_strategies()
        if any(x in il for x in ["scalper run", "스캘퍼 실행", "scalper paper"]):
            return self.scalper_paper()
        if any(x in il for x in ["scalper combo", "스캘퍼 조합"]):
            return self.scalper_combos()
        if any(x in il for x in ["scalper", "스캘퍼", "스캘핑"]):
            return self.scalper_status()

        return {"error": f"Unknown trading intent: {intent}",
                "hint": "try: backtest, buy, sell, balance, strategies, "
                        "universe, regime, scalper, orders, portfolio"}

    # ══════════════════════════════════════════════════════════════════
    #  Backtest (direct import or REST API fallback)
    # ══════════════════════════════════════════════════════════════════

    def backtest(self, symbol: str = "AAPL", strategy: str = "macd_cross") -> dict:
        """Single strategy backtest."""
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
        """Full strategy scan -> top N results."""
        # Try direct import first
        if self._backtest_mod is not None:
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
                logger.debug("Direct scan failed, falling back to API: %s", e)

        # REST API fallback: run all strategies via API
        return self._api_backtest(symbol, strategy="all")

    # ══════════════════════════════════════════════════════════════════
    #  Live Trading (via REST API)
    # ══════════════════════════════════════════════════════════════════

    def execute_trade(self, symbol: str, side: str, amount: float = 0.0) -> dict:
        """Execute trade via invest API."""
        if amount <= 0:
            return {"success": False, "error": "amount must be > 0"}

        return self._api.post("/api/trading/execute", data={
            "strategy_id": "",
            "symbol": symbol,
            "signal_type": side,
            "strength": 1.0,
        })

    def emergency_stop(self) -> dict:
        """Emergency stop all trading."""
        return self._api.post("/api/trading/emergency-stop", data={"stop": True})

    def get_balance(self) -> dict:
        """Query trading status / balance."""
        return self._api.get("/api/trading/status")

    def get_portfolio(self) -> dict:
        """Portfolio with positions."""
        result = self._api.get("/api/portfolio")
        if result.get("success"):
            # Also fetch portfolio history
            history = self._api.get("/api/portfolio/history", params={"limit": "7"})
            if history.get("success"):
                result["history"] = history["data"]
        return result

    def get_orders(self, limit: int = 20, status: str | None = None) -> dict:
        """Recent orders."""
        params: dict[str, str] = {"limit": str(limit)}
        if status:
            params["status"] = status
        result = self._api.get("/api/orders", params=params)
        if result.get("success"):
            # Also fetch order stats
            stats = self._api.get("/api/orders/stats")
            if stats.get("success"):
                result["stats"] = stats["data"]
        return result

    def get_dashboard(self) -> dict:
        """Dashboard overview."""
        return self._api.get("/api/dashboard")

    # ══════════════════════════════════════════════════════════════════
    #  Strategy & Universe
    # ══════════════════════════════════════════════════════════════════

    def list_strategies(self) -> dict:
        """Available strategy list (direct import or API)."""
        if self._backtest_mod and hasattr(self._backtest_mod, "SIGNAL_REGISTRY"):
            strategies = sorted(self._backtest_mod.SIGNAL_REGISTRY.keys())
            return {
                "success": True,
                "count": len(strategies),
                "strategies": strategies,
            }
        return self._api.get("/api/backtest/strategies")

    def list_universe(self) -> dict:
        """Available asset list."""
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

        return self._api.get("/api/backtest/assets")

    def get_regime(self) -> dict:
        """Market regime detection — try scalper first, then singularity CLI."""
        # 1. Try Rust scalper regime (fast)
        if self._scalper.available:
            result = self._scalper.regime()
            if result.get("success"):
                return result

        # 2. Try REST API
        api_result = self._api.get("/api/trading/status")
        if api_result.get("success"):
            return api_result

        # 3. Fallback to singularity CLI subprocess
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

    # ══════════════════════════════════════════════════════════════════
    #  Rust Scalper Bridge
    # ══════════════════════════════════════════════════════════════════

    def scalper_status(self) -> dict:
        """Rust scalper status."""
        return self._scalper.status()

    def scalper_regime(self) -> dict:
        """Market regime from Rust scalper."""
        return self._scalper.regime()

    def scalper_strategies(self) -> dict:
        """List scalper strategies."""
        return self._scalper.strategies()

    def scalper_combos(self) -> dict:
        """Show scalper strategy combinations."""
        return self._scalper.combos()

    def scalper_paper(self, config: str | None = None) -> dict:
        """Run scalper in paper trading mode."""
        return self._scalper.run_paper(config=config)

    def scalper_run(self, config: str | None = None) -> dict:
        """Start scalper in live mode (background)."""
        return self._scalper.run_live(config=config)

    # ══════════════════════════════════════════════════════════════════
    #  DB Strategies (CRUD via REST)
    # ══════════════════════════════════════════════════════════════════

    def list_db_strategies(self) -> dict:
        """List strategies from DB."""
        return self._api.get("/api/strategies")

    def create_strategy(self, name: str, strategy_type: str, broker: str,
                        symbol: str, timeframe: str = "1d",
                        params: dict | None = None) -> dict:
        """Create a new strategy in DB."""
        return self._api.post("/api/strategies", data={
            "name": name,
            "type": strategy_type,
            "broker": broker,
            "symbol": symbol,
            "timeframe": timeframe,
            "params": params or {},
        })

    # ══════════════════════════════════════════════════════════════════
    #  Status
    # ══════════════════════════════════════════════════════════════════

    def status(self) -> dict:
        return {
            "name": "trading",
            "version": self.manifest.version,
            "loaded": True,
            "invest_root": str(INVEST_ROOT),
            "invest_exists": INVEST_ROOT.exists(),
            "backtest_available": self._backtest_mod is not None,
            "universe_available": self._universe_mod is not None,
            "scalper_available": self._scalper.available,
            "api_url": INVEST_API_URL,
            "api_stats": self._api.stats,
        }

    # ══════════════════════════════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════════════════════════════

    def _load_csv(self, symbol: str):
        """Load CSV data -> (close, high, low, volume) numpy arrays."""
        import numpy as np

        csv_path = DATA_DIR / f"{symbol}.csv"
        if not csv_path.exists():
            # yfinance name conversion
            alt = symbol.replace("-", "_").replace("/", "_")
            csv_path = DATA_DIR / f"{alt}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"{symbol}")

        data = np.genfromtxt(
            csv_path, delimiter=",", skip_header=1,
            usecols=(1, 2, 3, 5),  # Open,High,Low,Close,Adj Close,Volume
        )
        # CSV: Date,Open,High,Low,Close,Adj Close,Volume
        # backtest_turbo expects: close, high, low, volume
        close = data[:, 2]   # Close (column index 2 after selecting 1,2,3,5)
        high = data[:, 0]    # High
        low = data[:, 1]     # Low
        volume = data[:, 3]  # Volume
        return close, high, low, volume

    def _api_backtest(self, symbol: str, strategy: str) -> dict:
        """Backtest via REST API."""
        return self._api.post("/api/backtest/run", data={
            "asset": symbol,
            "strategy": strategy,
            "initial_capital": 10000,
        })

    @staticmethod
    def _extract_strategy(text: str) -> str:
        """Extract strategy name from text."""
        known = [
            "macd_cross", "sma_cross", "rsi_std", "bb_std", "donchian",
            "linda_macd", "momentum_score", "trend_rider", "volume_surge",
            "low_vol_trend", "multi_timeframe", "dual_momentum",
            "surge_breakout_bb", "liquidity_filter", "vol_breakout",
            "collamaghi", "quad_ma", "ema_bb_gz", "gz_rsi", "gz_bb",
        ]
        tl = text.lower()
        for s in known:
            if s.replace("_", " ") in tl or s in tl:
                return s
        return "macd_cross"

    @staticmethod
    def _extract_symbol(text: str) -> str:
        """Extract symbol from text."""
        m = re.search(r'\b([A-Z]{2,5})\b', text.upper())
        if m:
            sym = m.group(1)
            known = {
                "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT",
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META",
                "SPY", "QQQ", "EWY", "GLD",
            }
            if sym in known:
                return sym
        return "BTC"

    @staticmethod
    def _extract_number(text: str) -> float:
        """Extract number from text."""
        m = re.search(r'(\d+\.?\d*)', text)
        return float(m.group(1)) if m else 0.0
