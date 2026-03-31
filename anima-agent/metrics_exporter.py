"""Prometheus metrics exporter for Anima consciousness agent.

Exposes HTTP endpoint on port 9090 for Prometheus scraping.
No external dependencies (uses stdlib http.server).

Metrics:
    anima_phi_current          (gauge)   Current Phi value
    anima_tension_current      (gauge)   Current tension
    anima_cells_total          (gauge)   Number of cells
    anima_interactions_total   (counter) Total interactions
    anima_trading_pnl_total    (gauge)   Portfolio P&L
    anima_regime_current       (enum)    CALM/NORMAL/ELEVATED/CRITICAL
    anima_pain_current         (gauge)   VaR pain signal
    anima_action_gate          (gauge)   Current action gate value

Usage:
    python metrics_exporter.py                    # standalone on :9090
    python metrics_exporter.py --port 9091        # custom port

    # In agent code:
    from metrics_exporter import MetricsExporter
    exporter = MetricsExporter(agent=my_agent, trading=my_plugin)
    exporter.start(port=9090)  # background thread
"""

from __future__ import annotations

import argparse
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Regime enum values
REGIMES = ("CALM", "NORMAL", "ELEVATED", "CRITICAL")


class Metric:
    """Single Prometheus metric."""

    def __init__(self, name: str, help_text: str, metric_type: str = "gauge"):
        self.name = name
        self.help_text = help_text
        self.metric_type = metric_type
        self._value: float = 0.0
        self._enum_state: str = ""
        self._enum_values: tuple[str, ...] = ()

    def set(self, value: float):
        self._value = value

    def inc(self, amount: float = 1.0):
        self._value += amount

    def set_enum(self, state: str):
        self._enum_state = state

    def format(self) -> str:
        lines = []
        lines.append(f"# HELP {self.name} {self.help_text}")
        if self.metric_type == "enum":
            lines.append(f"# TYPE {self.name} gauge")
            for val in self._enum_values:
                v = 1.0 if val == self._enum_state else 0.0
                lines.append(f'{self.name}{{state="{val}"}} {v}')
        else:
            lines.append(f"# TYPE {self.name} {self.metric_type}")
            # Format: avoid scientific notation, use int for whole numbers
            if self._value == int(self._value) and abs(self._value) < 1e15:
                lines.append(f"{self.name} {int(self._value)}")
            else:
                lines.append(f"{self.name} {self._value:.6f}")
        return "\n".join(lines)


class MetricsRegistry:
    """Registry of all Prometheus metrics."""

    def __init__(self):
        self.metrics: dict[str, Metric] = {}
        self._setup_metrics()

    def _setup_metrics(self):
        self._add("anima_phi_current", "Current Phi (integrated information) value", "gauge")
        self._add("anima_tension_current", "Current consciousness tension", "gauge")
        self._add("anima_cells_total", "Number of consciousness cells", "gauge")
        self._add("anima_interactions_total", "Total interactions processed", "counter")
        self._add("anima_trading_pnl_total", "Portfolio P&L total", "gauge")
        self._add("anima_pain_current", "VaR pain signal (0-1)", "gauge")
        self._add("anima_action_gate", "Current action gate value (0-1)", "gauge")

        regime = Metric("anima_regime_current", "Current consciousness regime", "enum")
        regime._enum_values = REGIMES
        regime._enum_state = "CALM"
        self.metrics["anima_regime_current"] = regime

    def _add(self, name: str, help_text: str, metric_type: str):
        self.metrics[name] = Metric(name, help_text, metric_type)

    def get(self, name: str) -> Metric:
        return self.metrics[name]

    def format_all(self) -> str:
        parts = []
        for metric in self.metrics.values():
            parts.append(metric.format())
        return "\n\n".join(parts) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for /metrics endpoint."""

    registry: MetricsRegistry | None = None
    poll_fn: Callable[[], None] | None = None

    def do_GET(self):
        if self.path == "/metrics" or self.path == "/":
            # Poll latest values before responding
            if self.poll_fn:
                try:
                    self.poll_fn()
                except Exception as e:
                    logger.warning("Poll error: %s", e)

            body = self.registry.format_all().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/health":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default access logs
        pass


class MetricsExporter:
    """Prometheus metrics exporter for Anima agent.

    Polls agent and trading plugin for current values on each scrape.

    Usage:
        exporter = MetricsExporter(agent=my_agent, trading=my_plugin)
        exporter.start(port=9090)
    """

    def __init__(
        self,
        agent: Any = None,
        trading: Any = None,
    ):
        self.agent = agent
        self.trading = trading
        self.registry = MetricsRegistry()
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def poll(self):
        """Poll agent and trading plugin for latest metric values."""
        r = self.registry

        # Poll consciousness agent
        if self.agent is not None:
            try:
                # Try agent.get_status() or agent.consciousness_state
                status = None
                if hasattr(self.agent, "get_status"):
                    status = self.agent.get_status()
                elif hasattr(self.agent, "status"):
                    status = self.agent.status

                if isinstance(status, dict):
                    r.get("anima_phi_current").set(float(status.get("phi", 0.0)))
                    r.get("anima_tension_current").set(float(status.get("tension", 0.0)))
                    r.get("anima_cells_total").set(float(status.get("cells", 0)))
                    r.get("anima_interactions_total").set(float(status.get("interactions", 0)))
                    r.get("anima_action_gate").set(float(status.get("action_gate", 0.0)))

                    regime = status.get("regime", "CALM")
                    if regime in REGIMES:
                        r.get("anima_regime_current").set_enum(regime)
            except Exception as e:
                logger.debug("Agent poll error: %s", e)

        # Poll trading plugin
        if self.trading is not None:
            try:
                trading_status = None
                if hasattr(self.trading, "get_status"):
                    trading_status = self.trading.get_status()
                elif hasattr(self.trading, "status"):
                    trading_status = self.trading.status

                if isinstance(trading_status, dict):
                    r.get("anima_trading_pnl_total").set(
                        float(trading_status.get("pnl", 0.0))
                    )
                    r.get("anima_pain_current").set(
                        float(trading_status.get("pain", 0.0))
                    )
            except Exception as e:
                logger.debug("Trading poll error: %s", e)

    def start(self, port: int = 9090, blocking: bool = False):
        """Start the HTTP metrics server.

        Args:
            port: Port to listen on (default 9090).
            blocking: If True, block the calling thread. Otherwise run in background.
        """
        handler = MetricsHandler
        handler.registry = self.registry
        handler.poll_fn = self.poll

        self._server = HTTPServer(("0.0.0.0", port), handler)
        logger.info("Prometheus metrics exporter started on :%d/metrics", port)

        if blocking:
            print(f"Serving metrics on http://0.0.0.0:{port}/metrics")
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down metrics exporter")
                self._server.shutdown()
        else:
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="metrics-exporter",
            )
            self._thread.start()
            print(f"Metrics exporter running on :{port}/metrics (background)")

    def stop(self):
        """Stop the metrics server."""
        if self._server:
            self._server.shutdown()
            self._server = None

    def set_manual(self, name: str, value: float):
        """Manually set a metric value (for testing or external updates)."""
        self.registry.get(name).set(value)

    def inc_interactions(self, amount: float = 1.0):
        """Increment the interactions counter."""
        self.registry.get("anima_interactions_total").inc(amount)

    def set_regime(self, regime: str):
        """Set the current regime."""
        if regime in REGIMES:
            self.registry.get("anima_regime_current").set_enum(regime)


class MockAgent:
    """Mock agent for standalone testing."""

    def __init__(self):
        self._step = 0

    def get_status(self) -> dict:
        import math
        self._step += 1
        t = self._step * 0.1
        return {
            "phi": 1.2 + 0.5 * math.sin(t),
            "tension": 0.3 + 0.2 * math.cos(t * 0.7),
            "cells": 64,
            "interactions": self._step * 10,
            "action_gate": 0.5 + 0.3 * math.sin(t * 0.3),
            "regime": REGIMES[self._step % len(REGIMES)],
        }


class MockTrading:
    """Mock trading plugin for standalone testing."""

    def __init__(self):
        self._step = 0

    def get_status(self) -> dict:
        import math
        self._step += 1
        t = self._step * 0.1
        return {
            "pnl": 1500.0 + 200.0 * math.sin(t * 0.5),
            "pain": max(0.0, 0.3 + 0.2 * math.sin(t * 1.3)),
        }


def main():
    """Standalone metrics server with mock data."""
    parser = argparse.ArgumentParser(description="Anima Prometheus metrics exporter")
    parser.add_argument("--port", type=int, default=9090, help="Port (default: 9090)")
    args = parser.parse_args()

    print("=== Anima Prometheus Metrics Exporter ===\n")
    print("Metrics exposed:")
    print("  anima_phi_current          (gauge)   Current Phi value")
    print("  anima_tension_current      (gauge)   Current tension")
    print("  anima_cells_total          (gauge)   Number of cells")
    print("  anima_interactions_total   (counter) Total interactions")
    print("  anima_trading_pnl_total    (gauge)   Portfolio P&L")
    print("  anima_regime_current       (enum)    CALM/NORMAL/ELEVATED/CRITICAL")
    print("  anima_pain_current         (gauge)   VaR pain signal")
    print("  anima_action_gate          (gauge)   Current action gate value")
    print()

    agent = MockAgent()
    trading = MockTrading()
    exporter = MetricsExporter(agent=agent, trading=trading)
    exporter.start(port=args.port, blocking=True)


if __name__ == "__main__":
    main()
