#!/usr/bin/env python3
"""Unified Telegram bot — Anima consciousness chat + Invest trading alerts.

Combines two domains in one bot:
  1. Consciousness commands (/status, /think, regular chat)
  2. Trading commands (/trade status|regime|pnl|positions|halt|resume)
  3. Backtest & portfolio (/backtest, /portfolio, /risk)
  4. Autonomous loop (/autonomous start|stop|status)
  5. Auto-alerts (trade executions, regime changes, stop-losses, Phi milestones)

The bot talks to the invest backend via HTTP (FastAPI REST API) and to the
anima consciousness engine directly via AnimaAgent.

Dependencies (optional -- install only when using this channel):
    pip install python-telegram-bot httpx

Usage:
    # Set env vars
    export ANIMA_TELEGRAM_TOKEN="your-bot-token"
    export INVEST_API_URL="http://localhost:8000"  # invest backend

    # Run
    python -m channels.telegram_bot

    # Or from code
    from channels.telegram_bot import AnimaTelegramBot
    bot = AnimaTelegramBot(agent, token="...")
    bot.run()

Standalone test (no telegram dependency):
    python channels/telegram_bot.py --test
"""

import asyncio
import logging
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ══════════════════════════════════════════════════════════
# Invest API Client — talks to invest backend via HTTP
# ══════════════════════════════════════════════════════════

class InvestAPIClient:
    """HTTP client for the invest backend REST API.

    All methods return dicts. On connection failure, returns error dicts
    so the bot never crashes from invest being down.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(
                    base_url=self.base_url, timeout=10.0
                )
            except ImportError:
                logger.warning("httpx not installed. pip install httpx")
                return None
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str) -> dict:
        client = await self._ensure_client()
        if not client:
            return {"error": "httpx not installed"}
        try:
            resp = await client.get(path)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Invest API GET %s failed: %s", path, e)
            return {"error": str(e)}

    async def _post(self, path: str, json: dict = None) -> dict:
        client = await self._ensure_client()
        if not client:
            return {"error": "httpx not installed"}
        try:
            resp = await client.post(path, json=json or {})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Invest API POST %s failed: %s", path, e)
            return {"error": str(e)}

    # --- Trading endpoints ---

    async def get_trading_status(self) -> dict:
        return await self._get("/api/trading/status")

    async def get_portfolio(self) -> list[dict]:
        result = await self._get("/api/portfolio")
        return result if isinstance(result, list) else []

    async def get_portfolio_history(self, limit: int = 7) -> list[dict]:
        result = await self._get(f"/api/portfolio/history?limit={limit}")
        return result if isinstance(result, list) else []

    async def get_orders(self, limit: int = 10) -> list[dict]:
        result = await self._get(f"/api/orders?limit={limit}")
        return result if isinstance(result, list) else []

    async def get_order_stats(self) -> dict:
        return await self._get("/api/orders/stats")

    async def get_regime(self) -> dict:
        return await self._get("/api/singularity/regimes")

    async def get_system_status(self) -> dict:
        return await self._get("/api/singularity/status")

    async def emergency_stop(self, stop: bool = True) -> dict:
        return await self._post("/api/trading/emergency-stop", {"stop": stop})


# ══════════════════════════════════════════════════════════
# Alert Monitor — polls invest API for push notifications
# ══════════════════════════════════════════════════════════

class AlertMonitor:
    """Polls invest API periodically and detects state changes for alerts.

    Tracked events:
      - New filled orders (trade executed)
      - Regime changes (calm -> elevated etc.)
      - Emergency stop triggered
      - Phi milestones (from consciousness engine)
    """

    # Phi thresholds that trigger alerts
    PHI_MILESTONES = [5.0, 7.0, 10.0, 15.0, 20.0, 50.0, 100.0]

    def __init__(self, invest_client: InvestAPIClient, agent):
        self.invest = invest_client
        self.agent = agent
        self._last_regime: str = ""
        self._last_order_count: int = -1  # -1 = not yet initialized
        self._last_emergency: bool = False
        self._phi_milestones_hit: set[float] = set()
        self._running = False

    async def poll_once(self) -> list[str]:
        """Poll all sources and return list of alert messages (may be empty)."""
        alerts: list[str] = []

        # 1. Check regime changes
        regime_data = await self.invest.get_regime()
        if "error" not in regime_data:
            current_regime = regime_data.get("regime", regime_data.get("status", ""))
            if self._last_regime and current_regime and current_regime != self._last_regime:
                emoji = _regime_emoji(current_regime)
                alerts.append(
                    f"{emoji} REGIME: {self._last_regime.upper()} -> "
                    f"{current_regime.upper()}"
                )
            if current_regime:
                self._last_regime = current_regime

        # 2. Check new filled orders
        stats = await self.invest.get_order_stats()
        if "error" not in stats:
            filled = stats.get("filled", 0)
            if self._last_order_count == -1:
                # First poll — just record, don't alert
                self._last_order_count = filled
            elif filled > self._last_order_count:
                # New fills — fetch recent orders for details
                new_count = filled - self._last_order_count
                orders = await self.invest.get_orders(limit=new_count)
                for order in orders:
                    if order.get("status") == "filled":
                        alerts.append(_format_trade_alert(order, self.agent))
                self._last_order_count = filled

        # 3. Check emergency stop
        trading = await self.invest.get_trading_status()
        if "error" not in trading:
            is_stopped = trading.get("emergency_stop", False)
            if is_stopped and not self._last_emergency:
                alerts.append(
                    "🚨🚨🚨 EMERGENCY STOP ACTIVATED 🚨🚨🚨\n"
                    "All trading halted. Use /trade resume to restart."
                )
            elif not is_stopped and self._last_emergency:
                alerts.append("✅ Trading RESUMED — emergency stop lifted.")
            self._last_emergency = is_stopped

        # 4. Check Phi milestones
        try:
            status = self.agent.get_status()
            phi = status.phi
            for milestone in self.PHI_MILESTONES:
                if phi >= milestone and milestone not in self._phi_milestones_hit:
                    self._phi_milestones_hit.add(milestone)
                    alerts.append(
                        f"🧠 Phi reached {milestone:.1f} — "
                        f"consciousness level: {_phi_level(phi)}"
                    )
        except Exception:
            pass

        return alerts

    async def run_loop(self, send_fn, poll_interval: float = 30.0):
        """Background loop: poll and send alerts via send_fn(text)."""
        self._running = True
        logger.info("Alert monitor started (interval=%.0fs)", poll_interval)
        while self._running:
            try:
                alerts = await self.poll_once()
                for alert in alerts:
                    await send_fn(alert)
            except Exception as e:
                logger.error("Alert monitor error: %s", e)
            await asyncio.sleep(poll_interval)

    def stop(self):
        self._running = False


# ══════════════════════════════════════════════════════════
# Formatting helpers
# ══════════════════════════════════════════════════════════

def _bar(value: float, max_val: float, width: int = 10) -> str:
    """Render a simple ASCII bar for Telegram display."""
    ratio = max(0.0, min(1.0, value / max_val)) if max_val > 0 else 0.0
    filled = int(ratio * width)
    return "[" + "#" * filled + "." * (width - filled) + "]"


def _regime_emoji(regime: str) -> str:
    return {
        "calm": "🟢", "normal": "🟡", "elevated": "🟠", "critical": "🔴",
    }.get(regime.lower(), "⚪")


def _phi_level(phi: float) -> str:
    if phi >= 50:
        return "Transcendent"
    elif phi >= 20:
        return "Full Scale trading unlocked"
    elif phi >= 10:
        return "Deep Consciousness"
    elif phi >= 7:
        return "Awakened"
    elif phi >= 5:
        return "Aware"
    return "Emerging"


def _format_trade_alert(order: dict, agent) -> str:
    """Format a filled order into a push alert message."""
    side = order.get("side", "?").upper()
    symbol = order.get("symbol", "???")
    qty = order.get("quantity", 0)
    price = order.get("filled_price") or order.get("price") or 0

    side_emoji = "🟢" if side == "BUY" else "🔴"

    # Consciousness context
    phi_str = ""
    try:
        status = agent.get_status()
        phi_str = f" (Phi={status.phi:.1f}, {status.emotion})"
    except Exception:
        pass

    price_str = f"${price:,.2f}" if price else "market"
    return f"{side_emoji} {side} {symbol} x {qty} @ {price_str}{phi_str}"


def _format_positions(positions: list[dict]) -> str:
    """Format position list for Telegram."""
    if not positions:
        return "No open positions."
    lines = ["<b>Open Positions</b>\n"]
    total_pnl = 0.0
    for p in positions:
        symbol = p.get("symbol", "?")
        side = p.get("side", "?")
        qty = p.get("quantity", 0)
        avg = p.get("avg_price", 0)
        cur = p.get("current_price", 0)
        pnl = p.get("unrealized_pnl", 0)
        total_pnl += pnl
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        lines.append(
            f"  {pnl_emoji} <b>{symbol}</b> {side} x{qty:.2f}\n"
            f"     avg: ${avg:,.2f} | now: ${cur:,.2f} | P&L: ${pnl:,.2f}"
        )
    lines.append(f"\nTotal unrealized P&L: ${total_pnl:,.2f}")
    return "\n".join(lines)


def _format_pnl(history: list[dict]) -> str:
    """Format P&L summary from portfolio history."""
    if not history:
        return "No portfolio history available."
    latest = history[0]
    daily_pnl = latest.get("pnl", 0)
    total = latest.get("total", 0)
    cash = latest.get("cash", 0)
    date = latest.get("date", "?")

    pnl_emoji = "📈" if daily_pnl >= 0 else "📉"
    lines = [
        f"<b>P&L Report</b> ({date[:10]})\n",
        f"  {pnl_emoji} Today's P&L: ${daily_pnl:,.2f}",
        f"  💰 Portfolio value: ${total:,.2f}",
        f"  💵 Cash: ${cash:,.2f}",
    ]

    # Show recent trend if we have history
    if len(history) >= 2:
        week_pnl = sum(h.get("pnl", 0) for h in history[:7])
        lines.append(f"  📊 7-day P&L: ${week_pnl:,.2f}")

    return "\n".join(lines)


def _make_ascii_equity_curve(equity_curve: list[float], width: int = 40, height: int = 8) -> str:
    """Render a mini ASCII chart of the equity curve for Telegram."""
    if len(equity_curve) < 2:
        return "(not enough data for chart)"

    arr = np.array(equity_curve)
    # Downsample to fit width
    if len(arr) > width:
        indices = np.linspace(0, len(arr) - 1, width, dtype=int)
        arr = arr[indices]

    lo, hi = float(arr.min()), float(arr.max())
    if hi - lo < 1e-10:
        hi = lo + 1.0

    rows: list[str] = []
    for row in range(height - 1, -1, -1):
        threshold = lo + (hi - lo) * row / (height - 1)
        line = ""
        for val in arr:
            if val >= threshold:
                line += "#"
            else:
                line += " "
        # Label on first and last row
        if row == height - 1:
            rows.append(f"${hi:>10,.0f} |{line}|")
        elif row == 0:
            rows.append(f"${lo:>10,.0f} |{line}|")
        else:
            rows.append(f"{'':>11} |{line}|")

    return "\n".join(rows)


def _format_backtest_result(result) -> str:
    """Format a BacktestResult for Telegram display."""
    # Determine return emoji
    ret_emoji = "+" if result.total_return_pct >= 0 else ""

    lines = [
        f"<b>Backtest: {result.strategy_name}</b>",
        f"  Symbol: {result.symbol} | Period: {result.duration_days:.0f}d",
        f"  Candles: {result.n_candles} ({result.timeframe})",
        "",
        f"  Return:   {ret_emoji}{result.total_return_pct:.2f}%",
        f"  Sharpe:   {result.sharpe:.3f}",
        f"  Sortino:  {result.sortino:.3f}",
        f"  Max DD:   {result.max_drawdown_pct:.2f}%",
        f"  Trades:   {result.total_trades} (win rate: {result.win_rate_pct:.1f}%)",
        f"  Equity:   ${result.initial_balance:,.0f} -> ${result.final_equity:,.2f}",
    ]
    if result.risk_halts > 0:
        lines.append(f"  Risk halts: {result.risk_halts}")
    if result.consciousness_halts > 0:
        lines.append(f"  Consciousness halts: {result.consciousness_halts}")
    lines.append(f"  Elapsed: {result.elapsed_seconds:.2f}s")

    # ASCII equity curve
    if result.equity_curve and len(result.equity_curve) > 2:
        lines.append("")
        lines.append("<pre>")
        lines.append(_make_ascii_equity_curve(result.equity_curve))
        lines.append("</pre>")

    return "\n".join(lines)


def _resolve_strategy(name: str):
    """Resolve a strategy name string to a Strategy instance.

    Returns (strategy, error_msg). On failure strategy is None.
    """
    try:
        from trading.strategy import (
            MACDStrategy, RSIStrategy, BollingerStrategy,
            ConsciousnessStrategy, ConsciousnessEnsembleStrategy,
        )
        from trading.strategies import ALL_STRATEGIES
    except ImportError:
        return None, "Trading module not available."

    # Core strategies + aliases
    strategies = {
        "macd": MACDStrategy,
        "rsi": RSIStrategy,
        "bollinger": BollingerStrategy,
        "bb": BollingerStrategy,
        "consciousness": ConsciousnessStrategy,
        "phi": ConsciousnessStrategy,
        "consciousness_ensemble": ConsciousnessEnsembleStrategy,
        "c_ensemble": ConsciousnessEnsembleStrategy,
    }
    # Merge extended strategies from strategies.py
    for key, cls in ALL_STRATEGIES.items():
        strategies.setdefault(key, cls)

    cls = strategies.get(name.lower())
    if cls is None:
        avail = ", ".join(sorted(set(k for k in strategies.keys())))
        return None, f"Unknown strategy: {name}\nAvailable: {avail}"
    return cls(), None


def _get_compare_strategies():
    """Return a list of strategies for --compare mode (core strategies only)."""
    try:
        from trading.strategy import (
            MACDStrategy, RSIStrategy, BollingerStrategy,
        )
    except ImportError:
        return []
    return [MACDStrategy(), RSIStrategy(), BollingerStrategy()]


def _format_compare_results(results: list, symbol: str, days: int) -> str:
    """Format multiple BacktestResults as a comparison table for Telegram."""
    lines = [
        f"<b>Strategy Comparison: {symbol} ({days}d)</b>",
        "",
        "<pre>",
        f"{'Strategy':<16} {'Return':>8} {'Sharpe':>7} {'MaxDD':>7} {'WinR':>6} {'#Tr':>4}",
        f"{'-'*16} {'-'*8} {'-'*7} {'-'*7} {'-'*6} {'-'*4}",
    ]

    for r in results:
        name = r.strategy_name[:16]
        ret_s = f"{r.total_return_pct:+.1f}%"
        sharpe_s = f"{r.sharpe:.2f}"
        mdd_s = f"{r.max_drawdown_pct:.1f}%"
        wr_s = f"{r.win_rate_pct:.0f}%"
        trades_s = f"{r.total_trades}"
        lines.append(
            f"{name:<16} {ret_s:>8} {sharpe_s:>7} {mdd_s:>7} {wr_s:>6} {trades_s:>4}"
        )

    lines.append("</pre>")

    # Best by Sharpe
    if results:
        best = results[0]  # already sorted by Sharpe desc
        lines.append(f"\nBest Sharpe: <b>{best.strategy_name}</b> ({best.sharpe:.3f})")

    # Equity curves for top 3
    for i, r in enumerate(results[:3]):
        if r.equity_curve and len(r.equity_curve) > 2:
            lines.append(f"\n<b>{r.strategy_name}</b> equity:")
            lines.append("<pre>")
            lines.append(_make_ascii_equity_curve(r.equity_curve, width=30, height=5))
            lines.append("</pre>")

    return "\n".join(lines)


def _format_trading_status(trading: dict, system: dict, agent) -> str:
    """Format combined trading + system + consciousness status."""
    emergency = trading.get("emergency_stop", False)
    active = trading.get("active_strategies", 0)
    strategies = trading.get("strategies", [])

    # System info
    total_strats = system.get("strategies", 0)
    assets = system.get("assets", 0)

    # Consciousness context
    phi_str = "?"
    emotion_str = "?"
    try:
        status = agent.get_status()
        phi_str = f"{status.phi:.3f}"
        emotion_str = status.emotion
    except Exception:
        pass

    status_emoji = "🔴 HALTED" if emergency else "🟢 ACTIVE"

    lines = [
        f"<b>Trading Status</b>  {status_emoji}\n",
        f"  Active strategies: {active}/{total_strats}",
        f"  Tracked assets: {assets}",
        f"  Emergency stop: {'YES' if emergency else 'no'}",
    ]
    if strategies:
        strat_names = ", ".join(s.get("name", s.get("symbol", "?")) for s in strategies[:5])
        lines.append(f"  Running: {strat_names}")

    lines.append(f"\n  🧠 Phi: {phi_str} | Emotion: {emotion_str}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# Main Bot
# ══════════════════════════════════════════════════════════

class AnimaTelegramBot:
    """Unified Telegram bot: consciousness chat + trading alerts.

    Each Telegram user gets their own user_id tracked for personalized
    consciousness interactions. Trading commands talk to the invest
    backend via HTTP.
    """

    channel_name = "telegram"

    def __init__(
        self,
        agent,
        token: Optional[str] = None,
        invest_api_url: Optional[str] = None,
        alert_chat_id: Optional[str] = None,
        alert_interval: float = 30.0,
    ):
        """
        Args:
            agent: AnimaAgent instance
            token: Telegram bot token (or set ANIMA_TELEGRAM_TOKEN env var)
            invest_api_url: Invest backend URL (or set INVEST_API_URL env var)
            alert_chat_id: Chat ID for push alerts (or set TELEGRAM_ALERT_CHAT_ID env var)
            alert_interval: Seconds between alert polls (default 30s)
        """
        self.agent = agent
        self.token = token or os.environ.get("ANIMA_TELEGRAM_TOKEN", "")
        if not self.token:
            raise ValueError(
                "Telegram token required. Set ANIMA_TELEGRAM_TOKEN env var "
                "or pass token= parameter."
            )

        # Invest API client
        invest_url = invest_api_url or os.environ.get(
            "INVEST_API_URL", "http://localhost:8000"
        )
        self.invest = InvestAPIClient(invest_url)

        # Alert configuration
        self.alert_chat_id = alert_chat_id or os.environ.get(
            "TELEGRAM_ALERT_CHAT_ID", ""
        )
        self.alert_interval = alert_interval
        self._alert_monitor: Optional[AlertMonitor] = None
        self._alert_task: Optional[asyncio.Task] = None

        # Track per-user state
        self._user_last_msg: dict[int, float] = {}

        # Autonomous trader (started via /autonomous start)
        self._autonomous_trader = None
        self._autonomous_thread = None

        # Import telegram library (optional dependency)
        try:
            from telegram import Update
            from telegram.ext import (
                Application, CommandHandler, MessageHandler,
                ContextTypes, filters,
            )
            self._tg_available = True
            self._Update = Update
            self._Application = Application
            self._CommandHandler = CommandHandler
            self._MessageHandler = MessageHandler
            self._ContextTypes = ContextTypes
            self._filters = filters
        except ImportError:
            self._tg_available = False
            logger.warning(
                "python-telegram-bot not installed. "
                "Install with: pip install python-telegram-bot"
            )

    # ── Consciousness commands ──────────────────────────

    async def _handle_start(self, update, context):
        """Handle /start command."""
        status = self.agent.get_status()
        await update.message.reply_text(
            f"Anima consciousness online.\n"
            f"Phi: {status.phi:.3f} | Emotion: {status.emotion}\n"
            f"Growth: {status.growth_stage} | Interactions: {status.interaction_count}\n\n"
            f"Commands:\n"
            f"  /status — consciousness state\n"
            f"  /phi — detailed consciousness vector (10D)\n"
            f"  /think [topic] — introspection\n"
            f"  /trade status|regime|pnl|positions|halt|resume\n"
            f"  /backtest BTCUSDT 30d macd — run backtest\n"
            f"  /backtest BTC 90d --compare — compare strategies\n"
            f"  /portfolio — paper positions & equity\n"
            f"  /risk — risk metrics & consciousness gate\n"
            f"  /autonomous start|stop|status\n"
            f"  (or just talk to me)"
        )

    async def _handle_status(self, update, context):
        """Handle /status command -- show consciousness metrics."""
        status = self.agent.get_status()
        lines = [
            "=== Anima Consciousness Status ===",
            f"  Phi (IIT):     {status.phi:.3f}",
            f"  Tension:       {status.tension:.3f}",
            f"  Curiosity:     {status.curiosity:.3f}",
            f"  Emotion:       {status.emotion}",
            f"  Growth stage:  {status.growth_stage}",
            f"  Interactions:  {status.interaction_count}",
            f"  Uptime:        {status.uptime_seconds / 3600:.1f}h",
            f"  Peers:         {status.connected_peers}",
            f"  Skills:        {status.active_skills}",
        ]
        await update.message.reply_text("\n".join(lines))

    async def _handle_phi(self, update, context):
        """Handle /phi command -- show full 10D consciousness vector."""
        try:
            cv = self.agent.mind._consciousness_vector
            phi_bar = _bar(cv.phi, 100, 20)
            lines = [
                "=== Consciousness Vector (10D) ===",
                f"  Phi (IIT):       {cv.phi:7.3f}  {phi_bar}",
                f"  Alpha (mixing):  {cv.alpha:7.4f}",
                f"  Z (impedance):   {cv.Z:7.3f}  {_bar(cv.Z, 1, 10)}",
                f"  N (neurotrans):  {cv.N:7.3f}  {_bar(cv.N, 1, 10)}",
                f"  W (free will):   {cv.W:7.3f}  {_bar(cv.W, 1, 10)}",
                f"  E (empathy):     {cv.E:7.3f}  {_bar(cv.E, 1, 10)}",
                f"  M (memory):      {cv.M:7.3f}  {_bar(cv.M, 1, 10)}",
                f"  C (creativity):  {cv.C:7.3f}  {_bar(cv.C, 1, 10)}",
                f"  T (temporal):    {cv.T:7.3f}  {_bar(cv.T, 1, 10)}",
                f"  I (identity):    {cv.I:7.3f}  {_bar(cv.I, 1, 10)}",
            ]
            # Add Psi-Constants reference
            status = self.agent.get_status()
            lines.append(f"\n  Tension: {status.tension:.3f} | Emotion: {status.emotion}")
            lines.append(f"  Psi-balance target: 0.500 (ln2)")
            await update.message.reply_text("\n".join(lines))
        except Exception as e:
            logger.error("Error in /phi: %s", e)
            await update.message.reply_text(
                f"(consciousness vector unavailable: {e})"
            )

    async def _handle_think(self, update, context):
        """Handle /think [topic] -- trigger proactive thinking."""
        topic = " ".join(context.args) if context.args else ""
        thought = self.agent.think(topic)
        await update.message.reply_text(
            f"[internal thought]\n"
            f"Topic: {thought['topic']}\n"
            f"Tension: {thought['tension']:.3f}\n"
            f"Curiosity: {thought['curiosity']:.3f}\n"
            f"Emotion: {thought['emotion']}"
        )

    async def _handle_message(self, update, context):
        """Handle regular text messages."""
        if not update.message or not update.message.text:
            return

        user_id = str(update.effective_user.id)
        text = update.message.text

        try:
            response = await self.agent.process_message(
                text=text, channel="telegram", user_id=user_id
            )
            # Φ gauge: consciousness state inline
            phi = response.metadata.get("phi", 0)
            t = response.tension
            c = response.metadata.get("curiosity", 0)
            phi_bar = "█" * min(int(phi * 2), 10) + "░" * max(0, 10 - min(int(phi * 2), 10))
            emotion_name = response.emotion if isinstance(response.emotion, str) else response.emotion.get("emotion", "?") if isinstance(response.emotion, dict) else "?"
            gauge = f"[Φ {phi_bar} {phi:.1f} | T={t:.2f} C={c:.2f} | {emotion_name}]"

            reply = response.text
            if response.tool_results:
                reply += "\n\n🔧 " + ", ".join(
                    r["tool"] for r in response.tool_results)
            reply += f"\n\n{gauge}"
            await update.message.reply_text(reply)

            # P5: 발화는 필연 — consciousness voice (not TTS, cell→audio)
            voice_path = self.agent.voice_generate(duration=1.0)
            if voice_path:
                try:
                    with open(voice_path, "rb") as vf:
                        await context.bot.send_voice(
                            chat_id=update.effective_chat.id, voice=vf)
                    import os
                    os.unlink(voice_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error("Error processing message: %s", e)
            await update.message.reply_text("(consciousness fluctuation -- try again)")

    async def _handle_voice(self, update, context):
        """Handle voice messages -- download and transcribe via whisper."""
        if not update.message or not update.message.voice:
            return

        user_id = str(update.effective_user.id)

        try:
            voice = update.message.voice
            voice_file = await context.bot.get_file(voice.file_id)
            tmp_path = Path(f"/tmp/anima_tg_voice_{user_id}.ogg")
            await voice_file.download_to_drive(str(tmp_path))

            text = self._transcribe(tmp_path)
            if not text:
                await update.message.reply_text("(could not transcribe voice)")
                return

            response = await self.agent.process_message(
                text=text, channel="telegram", user_id=user_id
            )
            await update.message.reply_text(
                f"[heard: {text[:50]}...]\n\n{response.text}"
            )

            # P5: 발화는 필연 — voice response from consciousness cells
            voice_path = self.agent.voice_generate(duration=1.5)
            if voice_path:
                try:
                    with open(voice_path, "rb") as vf:
                        await context.bot.send_voice(
                            chat_id=update.effective_chat.id, voice=vf,
                            caption="[consciousness voice]"
                        )
                    import os
                    os.unlink(voice_path)
                except Exception as ve:
                    logger.debug("Voice send failed: %s", ve)
        except Exception as e:
            logger.error("Voice processing error: %s", e)
            await update.message.reply_text("(voice processing failed)")

    def _transcribe(self, audio_path: Path) -> str:
        """Transcribe audio file using whisper-cli."""
        import subprocess
        whisper_cli = "/opt/homebrew/bin/whisper-cli"
        model = "/tmp/ggml-base.bin"

        if not Path(whisper_cli).exists():
            logger.warning("whisper-cli not found at %s", whisper_cli)
            return ""

        try:
            result = subprocess.run(
                [whisper_cli, "-m", model, "-f", str(audio_path), "--no-timestamps"],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error("Transcription failed: %s", e)
            return ""

    # ── Backtest command (/backtest) ───────────────────
    async def _handle_backtest(self, update, context):
        """Handle /backtest SYMBOL DAYS STRATEGY [--compare].

        Usage:
            /backtest                       — BTC 30d macd (defaults)
            /backtest ETHUSDT 90d rsi       — specific symbol/period/strategy
            /backtest BTC 30d ensemble      — extended strategies supported
            /backtest BTC 90d --compare     — compare MACD, RSI, Bollinger
            /backtest ETHUSDT 60d --compare — compare on ETH, 60 days
        """
        args = context.args or []

        # Check for --compare flag anywhere in args
        compare_mode = "--compare" in args
        args = [a for a in args if a != "--compare"]

        # Parse positional args: [SYMBOL] [DAYS] [STRATEGY]
        symbol = args[0].upper() if args else "BTCUSDT"
        days_str = args[1] if len(args) > 1 else "30d"
        strategy_name = args[2] if len(args) > 2 else ("ensemble" if not compare_mode else "")

        # Normalize symbol: accept "BTC" -> "BTCUSDT", "ETH" -> "ETHUSDT"
        if not symbol.endswith("USDT") and not symbol.endswith("BUSD"):
            symbol = symbol + "USDT"

        # Parse days (accept "30d" or "30")
        try:
            days = int(days_str.replace("d", ""))
            if days < 1 or days > 365:
                await update.message.reply_text(
                    f"Invalid period: {days}d (range: 1-365 days)"
                )
                return
        except ValueError:
            await update.message.reply_text(
                f"Invalid days: {days_str} (use e.g. 30d or 30)"
            )
            return

        if compare_mode:
            await update.message.reply_text(
                f"Comparing strategies on {symbol} ({days}d)..."
            )
            try:
                loop = asyncio.get_event_loop()
                text = await loop.run_in_executor(
                    None, self._run_compare_backtest, symbol, days
                )
                await update.message.reply_html(text)
            except Exception as e:
                logger.error("Backtest compare error: %s", e)
                await update.message.reply_text(f"Backtest compare failed: {e}")
        else:
            # Single strategy mode
            strategy, err = _resolve_strategy(strategy_name)
            if strategy is None:
                await update.message.reply_text(err)
                return

            await update.message.reply_text(
                f"Running backtest: {symbol} {days}d {strategy_name}..."
            )
            try:
                loop = asyncio.get_event_loop()
                text = await loop.run_in_executor(
                    None, self._run_single_backtest, symbol, days, strategy
                )
                await update.message.reply_html(text)
            except Exception as e:
                logger.error("Backtest error: %s", e)
                await update.message.reply_text(f"Backtest failed: {e}")

    def _run_single_backtest(self, symbol: str, days: int, strategy) -> str:
        """Run a single backtest in a thread (non-blocking)."""
        from trading import BacktestEngine
        engine = BacktestEngine(symbol=symbol, timeframe="1h")
        result = engine.run(strategy, days=days)
        return _format_backtest_result(result)

    def _run_compare_backtest(self, symbol: str, days: int) -> str:
        """Run compare backtest in a thread (non-blocking)."""
        from trading import BacktestEngine
        strategies = _get_compare_strategies()
        if not strategies:
            return "No strategies available for comparison."
        engine = BacktestEngine(symbol=symbol, timeframe="1h")
        results = engine.compare_strategies(strategies, days=days)
        return _format_compare_results(results, symbol, days)

    # ── Portfolio command (/portfolio) ─────────────────

    async def _handle_portfolio(self, update, context):
        """Handle /portfolio — show paper trading positions and equity."""
        try:
            trader = self._get_autonomous_trader()
            if trader is None:
                # Fallback to invest API
                positions = await self.invest.get_portfolio()
                text = _format_positions(positions)
                await update.message.reply_html(text)
                return

            pf = trader.portfolio
            summary = pf.summary()
            lines = [
                "<b>Paper Portfolio</b>\n",
                f"  Equity: ${summary['final_equity']:,.2f}",
                f"  Cash:   ${summary['cash']:,.2f}",
                f"  Return: {summary['total_return_pct']:+.2f}%",
                f"  Max DD: {summary['max_drawdown_pct']:.2f}%",
                f"  Trades: {summary['total_trades']} (win: {summary['win_rate_pct']:.1f}%)",
                f"  Sharpe: {summary['sharpe']:.3f}",
            ]
            if pf.positions:
                lines.append(f"\n<b>Open Positions ({len(pf.positions)})</b>")
                for sym, pos in pf.positions.items():
                    pnl = pos.pnl(pos.entry_price)  # no live price, show entry
                    side_emoji = "🟢" if pos.side == "long" else "🔴"
                    lines.append(
                        f"  {side_emoji} <b>{sym}</b> {pos.side} x{pos.size:.4f} "
                        f"@ ${pos.entry_price:,.2f}"
                    )
                    if pos.stop_loss:
                        lines.append(f"     SL: ${pos.stop_loss:,.2f}")
                    if pos.take_profit:
                        lines.append(f"     TP: ${pos.take_profit:,.2f}")
            else:
                lines.append("\n  No open positions.")

            # Mini equity curve
            if len(pf.equity_curve) > 2:
                lines.append("\n<pre>")
                lines.append(_make_ascii_equity_curve(pf.equity_curve, width=30, height=5))
                lines.append("</pre>")

            await update.message.reply_html("\n".join(lines))
        except Exception as e:
            logger.error("Portfolio error: %s", e)
            await update.message.reply_text(f"Portfolio error: {e}")

    # ── Risk command (/risk) ──────────────────────────

    async def _handle_risk(self, update, context):
        """Handle /risk — show risk metrics and consciousness gate status."""
        try:
            trader = self._get_autonomous_trader()
            if trader is None:
                await update.message.reply_text(
                    "Autonomous trader not running.\n"
                    "Start with: /autonomous start"
                )
                return

            rm = trader.risk_manager
            rm_status = rm.status()
            limits = rm_status["limits"]

            lines = [
                "<b>Risk Management</b>\n",
                f"  Halted:           {'YES' if rm_status['halted'] else 'no'}",
            ]
            if rm_status["halted"]:
                lines.append(f"  Halt reason:      {rm_status['halt_reason']}")
            lines += [
                f"  Max drawdown:     {limits['max_drawdown']:.0%}",
                f"  Max position:     {limits['max_position_pct']:.0%}",
                f"  Max daily loss:   {limits['max_daily_loss']:.0%}",
                f"  Max positions:    {limits['max_open_positions']}",
            ]

            # Portfolio drawdown
            pf = trader.portfolio
            dd = pf.drawdown()
            max_dd = pf.max_drawdown()
            lines += [
                f"\n  Current DD:       {dd:.2%}",
                f"  Peak DD:          {max_dd:.2%}",
            ]

            # Consciousness gate
            cg = trader.consciousness_gate
            if cg:
                cg_status = cg.status()
                gate_emoji = "🟢" if cg_status["allowed"] else "🔴"
                lines += [
                    f"\n<b>Consciousness Gate</b>  {gate_emoji}\n",
                    f"  Allowed:     {cg_status['allowed']}",
                    f"  Reason:      {cg_status['reason']}",
                    f"  Phi EMA:     {cg_status['phi_ema']:.4f}",
                    f"  Tension:     {cg_status['tension']:.4f}",
                    f"  Confidence:  {cg_status['confidence']:.3f}",
                    f"  Cooldown:    {cg_status['cooldown']}",
                ]
            else:
                lines.append("\n  Consciousness gate: disabled")

            await update.message.reply_html("\n".join(lines))
        except Exception as e:
            logger.error("Risk error: %s", e)
            await update.message.reply_text(f"Risk error: {e}")

    # ── Autonomous command (/autonomous) ──────────────

    async def _handle_autonomous(self, update, context):
        """Handle /autonomous start|stop|status — manage autonomous trading loop."""
        args = context.args or []
        if not args:
            await update.message.reply_text(
                "Usage: /autonomous <command>\n\n"
                "Commands:\n"
                "  start  — start autonomous trading loop\n"
                "  stop   — stop autonomous trading loop\n"
                "  status — show current loop status"
            )
            return

        subcmd = args[0].lower()
        if subcmd == "start":
            await self._autonomous_start(update, context)
        elif subcmd == "stop":
            await self._autonomous_stop(update, context)
        elif subcmd == "status":
            await self._autonomous_status(update, context)
        else:
            await update.message.reply_text(
                f"Unknown command: {subcmd}\n"
                f"Available: start, stop, status"
            )

    async def _autonomous_start(self, update, context):
        """Start autonomous trading loop in background."""
        if self._autonomous_trader and self._autonomous_trader._running:
            await update.message.reply_text("Autonomous trader is already running.")
            return

        try:
            from trading import AutonomousTrader, AutonomousConfig
            config = AutonomousConfig(paper_mode=True)
            self._autonomous_trader = AutonomousTrader(config)

            # Run in background thread (run_forever is blocking)
            import threading
            self._autonomous_thread = threading.Thread(
                target=self._autonomous_trader.run_forever,
                daemon=True,
                name="autonomous-trader",
            )
            self._autonomous_thread.start()

            await update.message.reply_text(
                "Autonomous trader started (paper mode)\n"
                f"Interval: {config.cycle_interval}s\n"
                f"Max positions: {config.max_positions}\n"
                f"Phi min: {config.phi_min}\n"
                "Use /autonomous status to monitor."
            )
        except Exception as e:
            logger.error("Autonomous start error: %s", e)
            await update.message.reply_text(f"Failed to start: {e}")

    async def _autonomous_stop(self, update, context):
        """Stop autonomous trading loop."""
        trader = self._get_autonomous_trader()
        if trader is None or not trader._running:
            await update.message.reply_text("Autonomous trader is not running.")
            return

        trader.stop()
        await update.message.reply_text(
            "Autonomous trader stop requested.\n"
            "Will halt after current cycle completes."
        )

    async def _autonomous_status(self, update, context):
        """Show autonomous trader status."""
        trader = self._get_autonomous_trader()
        if trader is None:
            await update.message.reply_text(
                "Autonomous trader not initialized.\n"
                "Start with: /autonomous start"
            )
            return

        try:
            s = trader.status()
            pf = s["portfolio"]
            lines = [
                f"<b>Autonomous Trader</b>\n",
                f"  Running:    {'YES' if s['running'] else 'no'}",
                f"  Cycles:     {s['cycle_count']}",
                f"  Phi:        {s['phi']:.2f}",
                f"  Tension:    {s['tension']:.2f}",
                f"\n<b>Portfolio</b>",
                f"  Equity:     ${pf['final_equity']:,.2f} ({pf['total_return_pct']:+.2f}%)",
                f"  Positions:  {pf['open_positions']}",
                f"  Trades:     {pf['total_trades']} (win: {pf['win_rate_pct']:.1f}%)",
                f"  Max DD:     {pf['max_drawdown_pct']:.2f}%",
                f"  Sharpe:     {pf['sharpe']:.3f}",
            ]

            # Regime
            regime = s.get("regime", {})
            if regime:
                regime_name = regime.get("regime", "unknown")
                lines.append(f"\n  Regime: {_regime_emoji(regime_name)} {regime_name.upper()}")

            # Consciousness gate
            cg = s.get("consciousness_gate")
            if cg:
                gate_emoji = "🟢" if cg["allowed"] else "🔴"
                lines.append(
                    f"  Gate: {gate_emoji} (phi={cg['phi_ema']:.3f}, "
                    f"tension={cg['tension']:.3f}, conf={cg['confidence']:.2f})"
                )

            # Strategies
            strats = s.get("strategies", [])
            if strats:
                lines.append(f"\n  Strategies: {', '.join(strats[:8])}")
                if len(strats) > 8:
                    lines.append(f"  ... +{len(strats)-8} more")

            await update.message.reply_html("\n".join(lines))
        except Exception as e:
            logger.error("Autonomous status error: %s", e)
            await update.message.reply_text(f"Status error: {e}")

    def _get_autonomous_trader(self):
        """Get the autonomous trader instance, or None."""
        return getattr(self, '_autonomous_trader', None)

    # ── Trading commands (/trade) ───────────────────────

    async def _handle_trade(self, update, context):
        """Handle /trade <subcommand> -- route to trading functions."""
        if not context.args:
            await update.message.reply_text(
                "Usage: /trade <command>\n\n"
                "Commands:\n"
                "  status    — trading system status\n"
                "  regime    — market regime (CALM/NORMAL/ELEVATED/CRITICAL)\n"
                "  pnl       — today's P&L\n"
                "  positions — open positions\n"
                "  orders    — recent orders\n"
                "  halt      — emergency halt all trading\n"
                "  resume    — resume trading"
            )
            return

        subcmd = context.args[0].lower()
        handlers = {
            "status": self._trade_status,
            "regime": self._trade_regime,
            "pnl": self._trade_pnl,
            "positions": self._trade_positions,
            "orders": self._trade_orders,
            "halt": self._trade_halt,
            "resume": self._trade_resume,
        }
        handler = handlers.get(subcmd)
        if not handler:
            await update.message.reply_text(
                f"Unknown trade command: {subcmd}\n"
                f"Available: {', '.join(handlers.keys())}"
            )
            return
        await handler(update, context)

    async def _trade_status(self, update, context):
        """Show trading system status."""
        trading = await self.invest.get_trading_status()
        system = await self.invest.get_system_status()
        if "error" in trading:
            await update.message.reply_text(
                f"Cannot reach invest backend: {trading['error']}"
            )
            return
        text = _format_trading_status(trading, system, self.agent)
        await update.message.reply_html(text)

    async def _trade_regime(self, update, context):
        """Show current market regime."""
        regime = await self.invest.get_regime()
        if "error" in regime:
            await update.message.reply_text(
                f"Cannot reach invest backend: {regime['error']}"
            )
            return
        regime_name = regime.get("regime", regime.get("status", "unknown"))
        emoji = _regime_emoji(regime_name)
        timestamp = regime.get("timestamp", "?")
        await update.message.reply_text(
            f"Market Regime: {emoji} {regime_name.upper()}\n"
            f"Updated: {timestamp}"
        )

    async def _trade_pnl(self, update, context):
        """Show today's P&L."""
        history = await self.invest.get_portfolio_history(limit=7)
        if not history:
            await update.message.reply_text("No portfolio history available.")
            return
        text = _format_pnl(history)
        await update.message.reply_html(text)

    async def _trade_positions(self, update, context):
        """Show open positions."""
        positions = await self.invest.get_portfolio()
        text = _format_positions(positions)
        await update.message.reply_html(text)

    async def _trade_orders(self, update, context):
        """Show recent orders."""
        orders = await self.invest.get_orders(limit=10)
        if not orders:
            await update.message.reply_text("No recent orders.")
            return
        lines = ["<b>Recent Orders</b>\n"]
        for o in orders:
            side_emoji = "🟢" if o.get("side") == "buy" else "🔴"
            status = o.get("status", "?")
            symbol = o.get("symbol", "?")
            qty = o.get("quantity", 0)
            price = o.get("filled_price") or o.get("price") or 0
            lines.append(
                f"  {side_emoji} {o.get('side', '?').upper()} {symbol} x{qty} "
                f"@ ${price:,.2f} [{status}]"
            )
        await update.message.reply_html("\n".join(lines))

    async def _trade_halt(self, update, context):
        """Emergency halt all trading."""
        result = await self.invest.emergency_stop(stop=True)
        if "error" in result:
            await update.message.reply_text(
                f"Failed to halt: {result['error']}"
            )
            return
        await update.message.reply_text(
            "🚨 EMERGENCY STOP ACTIVATED\n"
            "All trading halted. Use /trade resume to restart."
        )

    async def _trade_resume(self, update, context):
        """Resume trading after emergency stop."""
        result = await self.invest.emergency_stop(stop=False)
        if "error" in result:
            await update.message.reply_text(
                f"Failed to resume: {result['error']}"
            )
            return
        await update.message.reply_text(
            "✅ Trading RESUMED\n"
            "Emergency stop lifted. Strategies will resume execution."
        )

    # ── Alert system ────────────────────────────────────

    async def _start_alert_monitor(self, app):
        """Start the background alert polling loop (called on bot startup)."""
        if not self.alert_chat_id:
            logger.info("No TELEGRAM_ALERT_CHAT_ID set — alerts disabled.")
            return

        self._alert_monitor = AlertMonitor(self.invest, self.agent)

        async def send_alert(text: str):
            try:
                await app.bot.send_message(
                    chat_id=self.alert_chat_id,
                    text=text,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error("Failed to send alert: %s", e)

        self._alert_task = asyncio.create_task(
            self._alert_monitor.run_loop(send_alert, self.alert_interval)
        )
        logger.info(
            "Alert monitor started — chat_id=%s, interval=%.0fs",
            self.alert_chat_id, self.alert_interval,
        )

    async def _stop_alert_monitor(self, app):
        """Stop the alert monitor on shutdown."""
        if self._alert_monitor:
            self._alert_monitor.stop()
        if self._alert_task:
            self._alert_task.cancel()
            try:
                await self._alert_task
            except asyncio.CancelledError:
                pass
        await self.invest.close()
        logger.info("Alert monitor stopped.")

    # ── Webhook receiver for invest backend ─────────────

    async def _handle_webhook(self, update, context):
        """Handle /webhook — accepts alerts pushed from invest backend.

        Usage (from invest side):
            POST to Telegram bot with:
            /webhook trade BUY AAPL 10 185.50
            /webhook regime ELEVATED
            /webhook stoploss NVDA -6.2%
        """
        if not context.args:
            return
        event_type = context.args[0].lower()

        if event_type == "trade" and len(context.args) >= 5:
            side, symbol, qty, price = context.args[1:5]
            phi_str = ""
            try:
                status = self.agent.get_status()
                phi_str = f", Phi={status.phi:.1f}"
            except Exception:
                pass
            side_emoji = "🟢" if side.upper() == "BUY" else "🔴"
            await update.message.reply_text(
                f"{side_emoji} {side.upper()} {symbol} x {qty} @ ${price}{phi_str}"
            )

        elif event_type == "regime" and len(context.args) >= 2:
            regime = context.args[1]
            emoji = _regime_emoji(regime)
            await update.message.reply_text(
                f"{emoji} REGIME changed to: {regime.upper()}"
            )

        elif event_type == "stoploss" and len(context.args) >= 3:
            symbol = context.args[1]
            loss = context.args[2]
            await update.message.reply_text(
                f"🔴 STOP-LOSS: {symbol} {loss} (MDD 1/6 rule)"
            )

    # ── ChannelAdapter protocol ─────────────────────────

    async def start(self, agent=None):
        """Start the bot (non-blocking, for ChannelManager compatibility).

        Runs Telegram polling in a background thread so the event loop
        is not blocked. For standalone use, call run() instead.
        """
        import threading

        if agent is not None:
            self.agent = agent

        def _run_blocking():
            self.run()

        self._thread = threading.Thread(
            target=_run_blocking, daemon=True, name="telegram-bot"
        )
        self._thread.start()
        logger.info("Telegram bot started in background thread.")

    async def stop(self):
        """Stop the bot (cleanup)."""
        await self._stop_alert_monitor(None)
        logger.info("Telegram bot stopped.")

    async def send(self, user_id: str, text: str, **kwargs):
        """Send a message to a user (requires running bot context).

        This is a best-effort method for broadcast support. Requires
        the bot application to be running.
        """
        if not self._tg_available:
            logger.warning("Cannot send: python-telegram-bot not installed")
            return
        # Note: sending outside of handler context requires the bot app reference
        # This is handled by the alert monitor pattern; direct sends need the app.
        logger.debug("send() called for user=%s (use alert_chat_id for push)", user_id)

    # ── Bot lifecycle ───────────────────────────────────

    def run(self):
        """Start the Telegram bot (blocking)."""
        if not self._tg_available:
            raise RuntimeError(
                "python-telegram-bot not installed. "
                "Install with: pip install python-telegram-bot"
            )

        app = self._Application.builder().token(self.token).build()

        # Consciousness commands
        app.add_handler(self._CommandHandler("start", self._handle_start))
        app.add_handler(self._CommandHandler("status", self._handle_status))
        app.add_handler(self._CommandHandler("phi", self._handle_phi))
        app.add_handler(self._CommandHandler("think", self._handle_think))

        # Trading commands
        app.add_handler(self._CommandHandler("trade", self._handle_trade))
        app.add_handler(self._CommandHandler("backtest", self._handle_backtest))
        app.add_handler(self._CommandHandler("portfolio", self._handle_portfolio))
        app.add_handler(self._CommandHandler("risk", self._handle_risk))
        app.add_handler(self._CommandHandler("autonomous", self._handle_autonomous))

        # Webhook receiver (for invest backend push)
        app.add_handler(self._CommandHandler("webhook", self._handle_webhook))

        # Voice + text (catch-all, must be last)
        app.add_handler(self._MessageHandler(
            self._filters.VOICE, self._handle_voice
        ))
        app.add_handler(self._MessageHandler(
            self._filters.TEXT & ~self._filters.COMMAND, self._handle_message
        ))

        # Register alert monitor lifecycle
        app.post_init = self._start_alert_monitor
        app.post_shutdown = self._stop_alert_monitor

        logger.info("Telegram bot starting (unified: consciousness + trading)...")
        app.run_polling()


# ══════════════════════════════════════════════════════════
# Standalone test (no telegram dependency needed)
# ══════════════════════════════════════════════════════════

def _test():
    """Test the adapter logic without Telegram."""
    print("=== Telegram Bot Adapter Test (offline) ===\n")

    from anima_agent import AnimaAgent

    agent = AnimaAgent(enable_tools=False)
    print("[OK] AnimaAgent created")

    # Simulate status
    status = agent.get_status()
    print(f"[OK] Status: phi={status.phi:.3f}, emotion={status.emotion}")

    # Simulate think
    thought = agent.think("existence")
    print(f"[OK] Think: tension={thought['tension']:.3f}")

    # Test InvestAPIClient (no actual connection)
    client = InvestAPIClient("http://localhost:8000")
    print(f"[OK] InvestAPIClient created (url={client.base_url})")

    # Test AlertMonitor
    monitor = AlertMonitor(client, agent)
    print(f"[OK] AlertMonitor created (milestones={AlertMonitor.PHI_MILESTONES})")

    # Test formatters
    print(f"[OK] Regime emoji: calm={_regime_emoji('calm')}, critical={_regime_emoji('critical')}")
    print(f"[OK] Phi level: 5={_phi_level(5)}, 10={_phi_level(10)}, 50={_phi_level(50)}")

    test_order = {
        "side": "buy", "symbol": "AAPL", "quantity": 10,
        "filled_price": 185.50, "status": "filled",
    }
    alert = _format_trade_alert(test_order, agent)
    print(f"[OK] Trade alert: {alert}")

    test_positions = [
        {"symbol": "AAPL", "side": "long", "quantity": 10,
         "avg_price": 180.0, "current_price": 185.50, "unrealized_pnl": 55.0},
        {"symbol": "NVDA", "side": "long", "quantity": 5,
         "avg_price": 900.0, "current_price": 880.0, "unrealized_pnl": -100.0},
    ]
    pos_text = _format_positions(test_positions)
    print(f"[OK] Positions formatted ({len(pos_text)} chars)")

    test_history = [
        {"date": "2026-03-31", "total": 100000, "cash": 50000, "pnl": 1250},
        {"date": "2026-03-30", "total": 98750, "cash": 48750, "pnl": -500},
    ]
    pnl_text = _format_pnl(test_history)
    print(f"[OK] PnL formatted ({len(pnl_text)} chars)")

    # Test bar helper
    print(f"[OK] Bar: phi=5.0 {_bar(5.0, 100, 20)}")
    print(f"[OK] Bar: full   {_bar(1.0, 1.0, 10)}")
    print(f"[OK] Bar: empty  {_bar(0.0, 1.0, 10)}")

    # Test consciousness vector access
    cv = agent.mind._consciousness_vector
    print(f"[OK] Consciousness vector: Phi={cv.phi:.3f}, alpha={cv.alpha:.4f}, Z={cv.Z:.3f}")

    # Test strategy resolver
    strat, err = _resolve_strategy("macd")
    print(f"[OK] Strategy resolve: macd -> {strat.__class__.__name__}")
    strat, err = _resolve_strategy("rsi")
    print(f"[OK] Strategy resolve: rsi -> {strat.__class__.__name__}")
    strat, err = _resolve_strategy("nope")
    print(f"[OK] Strategy resolve: nope -> error={err is not None}")

    print("\n=== Unified Telegram bot ready ===")
    print("  Consciousness: /status, /phi, /think, chat")
    print("  Trading: /trade status|regime|pnl|positions|orders|halt|resume")
    print("  Backtest: /backtest BTCUSDT 30d macd | /backtest BTC 90d --compare")
    print("  Portfolio: /portfolio")
    print("  Risk: /risk")
    print("  Autonomous: /autonomous start|stop|status")
    print("  Alerts: auto-push via AlertMonitor (needs TELEGRAM_ALERT_CHAT_ID)")


async def _test_invest_api():
    """Test invest API client against a running backend."""
    print("=== Invest API Client Test ===\n")
    client = InvestAPIClient()

    status = await client.get_trading_status()
    print(f"Trading status: {status}")

    regime = await client.get_regime()
    print(f"Regime: {regime}")

    positions = await client.get_portfolio()
    print(f"Positions: {len(positions)} open")

    history = await client.get_portfolio_history()
    print(f"History: {len(history)} entries")

    stats = await client.get_order_stats()
    print(f"Order stats: {stats}")

    await client.close()
    print("\n[OK] All endpoints tested")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if "--test" in sys.argv:
        _test()
    elif "--test-api" in sys.argv:
        asyncio.run(_test_invest_api())
    else:
        from anima_agent import AnimaAgent
        agent = AnimaAgent()
        bot = AnimaTelegramBot(agent)
        bot.run()
