"""NEXUS-6 Bridge Plugin — unified nexus6 integration for anima-agent.

Consolidates ALL nexus6 usage into a single plugin:
  - Autonomous periodic scanning (every N interactions)
  - On-demand analysis via hub.act("scan") or tool calls
  - n=6 constant matching
  - OUROBOROS evolution
  - Anomaly detection + alerting

Usage:
    hub.act("nexus scan")
    hub.act("n6 check 71")
    hub.act("consciousness analysis")
    hub.act("nexus evolve consciousness")
    hub.act("nexus status")
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional, TYPE_CHECKING

from plugins.base import PluginBase, PluginManifest

if TYPE_CHECKING:
    from consciousness_hub import ConsciousnessHub

logger = logging.getLogger(__name__)


class Nexus6Plugin(PluginBase):
    """NEXUS-6 consciousness scanner — 130+ lenses, anomaly detection, n=6 matching."""

    manifest = PluginManifest(
        name="nexus6_bridge",
        description="NEXUS-6 consciousness scanner — 130+ lenses, anomaly detection, n=6 matching",
        version="1.0.0",
        author="Anima",
        requires=[],  # nexus6 is optional (graceful degrade)
        capabilities=[
            "scan", "analyze", "n6_check", "evolve", "anomaly_detect",
            "status", "history", "trend",
        ],
        keywords=[
            "nexus6", "nexus", "넥서스", "scan", "스캔", "분석", "analyze",
            "n6", "상수", "constant", "anomaly", "이상", "렌즈", "lens",
            "진화", "evolve", "ouroboros", "의식분석", "consciousness scan",
            "넥서스 스캔", "넥서스 상태", "넥서스 진화",
        ],
        phi_minimum=0.0,  # Always available (monitoring is critical)
        category="consciousness",
    )

    def __init__(self):
        self.hub: Optional[ConsciousnessHub] = None
        self._nexus6 = None          # lazy import
        self._rust_bridge = None     # lazy import anima_rs.nexus6_bridge
        self._last_scan = None
        self._scan_count: int = 0
        self._scan_interval: int = 50  # every 50 interactions
        self._history_handle = None    # Rust ring buffer handle

    # ── Lazy Imports ──

    @property
    def nexus6(self):
        """Lazy import nexus6 (Rust/PyO3 package)."""
        if self._nexus6 is None:
            try:
                import nexus6
                self._nexus6 = nexus6
            except ImportError:
                pass
        return self._nexus6

    @property
    def rust_bridge(self):
        """Lazy import Rust hot-path bridge (anima_rs.nexus6_bridge)."""
        if self._rust_bridge is None:
            try:
                import anima_rs
                self._rust_bridge = anima_rs.nexus6_bridge
            except (ImportError, AttributeError):
                pass
        return self._rust_bridge

    # ── Lifecycle ──

    def on_load(self, hub: ConsciousnessHub) -> None:
        self.hub = hub
        # Init Rust history buffer if available
        if self.rust_bridge:
            self._history_handle = self.rust_bridge.history_create(100)
        logger.info(
            "Nexus6 plugin v%s loaded (nexus6=%s, rust_bridge=%s)",
            self.manifest.version,
            self.nexus6 is not None,
            self.rust_bridge is not None,
        )

    def on_unload(self) -> None:
        logger.info("Nexus6 plugin unloaded (scans=%d)", self._scan_count)
        self.hub = None

    # ── Intent Router ──

    def act(self, intent: str, **kwargs) -> Any:
        """Route natural language intent to the appropriate action."""
        il = intent.lower()

        # n6 check (before scan — "n6 체크 71" should not fall through to scan)
        if any(k in il for k in ["n6", "상수", "constant", "체크", "check"]):
            nums = re.findall(r"[\d.]+", intent)
            if nums:
                return self.n6_check(float(nums[0]))
            return {"success": False, "error": "No value provided for n6_check"}

        # Scan / analyze
        if any(k in il for k in ["스캔", "scan", "분석", "analyze"]):
            mind = kwargs.get("mind") or self._resolve_mind()
            return self.scan(mind=mind, data=kwargs.get("data"))

        # Evolve / OUROBOROS
        if any(k in il for k in ["진화", "evolve", "ouroboros"]):
            domain = kwargs.get("domain", "consciousness")
            # Try to extract domain from free text
            skip = {"진화", "evolve", "ouroboros", "넥서스", "nexus"}
            for word in intent.split():
                if word.lower() not in skip:
                    domain = word
                    break
            return self.evolve(domain)

        # Status
        if any(k in il for k in ["상태", "status", "현황"]):
            return self.status()

        # Trend / history
        if any(k in il for k in ["trend", "추세", "history", "이력"]):
            return self.get_trend()

        # Default: attempt a scan
        mind = kwargs.get("mind") or self._resolve_mind()
        return self.scan(mind=mind, data=kwargs.get("data"))

    # ── Core Actions ──

    def scan(self, mind=None, data=None) -> dict:
        """Run NEXUS-6 full scan. Returns scan result dict."""
        if not self.nexus6:
            return {"success": False, "error": "nexus6 not available (pip install nexus6)"}

        extracted = self._extract_data(mind=mind, data=data)
        if not extracted:
            return {"success": False, "error": "No data to scan (no mind or data provided)"}

        flat, n_pts, n_dims = extracted
        if not flat or n_pts == 0 or n_dims == 0:
            return {"success": False, "error": "Empty data"}

        try:
            result = self.nexus6.analyze(flat, n_pts, n_dims)
            sr = result["scan"]
            consensus = result.get("consensus", [])

            self._last_scan = result
            self._scan_count += 1

            # Push to Rust history buffer
            if self.rust_bridge and self._history_handle is not None:
                phi = sr.get_metric("phi_approx") if hasattr(sr, "get_metric") else 0.0
                entropy = sr.get_metric("shannon_entropy") if hasattr(sr, "get_metric") else 0.0
                self.rust_bridge.history_push(
                    self._history_handle,
                    phi,
                    entropy,
                    len(consensus),
                    sr.active_lens_count(),
                    int(time.time() * 1000),
                )

            # Check anomalies
            anomaly = self._check_anomalies(sr, consensus)

            return {
                "success": True,
                "active_lenses": sr.active_lens_count(),
                "total_lenses": sr.lens_count,
                "consensus_count": len(consensus),
                "n6_exact_ratio": result.get("n6_exact_ratio", 0),
                "anomaly": anomaly,
                "scan_number": self._scan_count,
            }
        except Exception as e:
            logger.exception("Nexus6 scan failed")
            return {"success": False, "error": str(e)}

    def auto_scan(self, mind, interaction_count: int) -> Optional[dict]:
        """Called by agent loop.  Scans if interval reached.  Returns result or None."""
        if interaction_count % self._scan_interval != 1:
            return None
        return self.scan(mind=mind)

    def n6_check(self, value: float) -> dict:
        """Check if *value* matches an n=6 constant."""
        if not self.nexus6:
            return {"success": False, "error": "nexus6 not available"}
        try:
            m = self.nexus6.n6_check(float(value))
            return {
                "success": True,
                "value": value,
                "constant_name": m.constant_name,
                "quality": m.quality,
                "is_exact": m.quality >= 0.99,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def evolve(self, domain: str = "consciousness") -> dict:
        """Run OUROBOROS evolution for *domain*."""
        if not self.nexus6:
            return {"success": False, "error": "nexus6 not available"}
        try:
            cycles = self.nexus6.evolve(domain)
            return {
                "success": True,
                "domain": domain,
                "cycles": len(cycles),
                "results": [
                    {"cycle": i, "discoveries": len(getattr(c, "discoveries", []))}
                    for i, c in enumerate(cycles)
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_trend(self) -> dict:
        """Get phi trend from Rust history ring buffer."""
        if self.rust_bridge and self._history_handle is not None:
            return self.rust_bridge.history_summary(self._history_handle)
        return {"trend": 0.0, "avg_phi": 0.0, "avg_consensus": 0.0, "len": 0}

    # ── Status ──

    def status(self) -> dict:
        base = {
            "name": self.manifest.name,
            "version": self.manifest.version,
            "loaded": True,
            "nexus6_available": self.nexus6 is not None,
            "rust_bridge_available": self.rust_bridge is not None,
            "scan_count": self._scan_count,
            "scan_interval": self._scan_interval,
            "last_scan": bool(self._last_scan),
            "trend": self.get_trend(),
        }
        if self._last_scan:
            sr = self._last_scan.get("scan")
            if sr:
                base["last_active_lenses"] = (
                    sr.active_lens_count() if hasattr(sr, "active_lens_count") else 0
                )
                base["last_consensus"] = len(self._last_scan.get("consensus", []))
        return base

    # ── Internal Helpers ──

    def _resolve_mind(self):
        """Try to get the current ConsciousMind from the hub."""
        if self.hub is None:
            return None
        anima = getattr(self.hub, "_anima", None)
        if isinstance(anima, dict):
            return anima.get("mind")
        return getattr(anima, "mind", None)

    def _extract_data(self, mind=None, data=None):
        """Extract (flat_list, n_points, n_dims) from mind or raw data.

        Returns:
            Tuple (flat, n_pts, n_dims) or None if no data is available.
        """
        # Raw data takes priority
        if data is not None:
            if isinstance(data, (list, tuple)):
                return list(data), 1, len(data)
            # torch.Tensor / numpy array
            if hasattr(data, "numpy"):
                flat = data.detach().cpu().numpy().flatten().tolist()
                return flat, 1, len(flat)

        if mind is None:
            return None

        # Cell-based engine (ConsciousnessEngine)
        cells = getattr(mind, "cells", None)
        if cells and len(cells) > 0 and hasattr(cells[0], "tolist"):
            if self.rust_bridge:
                flat_all: list[float] = []
                for c in cells:
                    flat_all.extend(c.tolist() if hasattr(c, "tolist") else [float(c)])
                return self.rust_bridge.extract_cells(flat_all, len(cells))
            # Python fallback
            flat: list[float] = []
            for c in cells:
                flat.extend(c.tolist() if hasattr(c, "tolist") else [float(c)])
            n_pts = len(cells)
            n_dims = len(flat) // n_pts if n_pts > 0 else 0
            return flat, n_pts, n_dims

        # Fallback: hidden state tensor
        hidden = getattr(mind, "hidden", None)
        if hidden is not None:
            if hasattr(hidden, "numpy"):
                h = hidden.detach().cpu().numpy().flatten()
                flat = [float(x) for x in h]
            elif hasattr(hidden, "tolist"):
                flat = [float(x) for x in hidden.tolist()]
            else:
                return None
            if self.rust_bridge:
                return self.rust_bridge.extract_hidden(flat)
            return flat, 1, len(flat)

        return None

    def _check_anomalies(self, sr, consensus) -> dict:
        """Check scan results for anomalies.  Prefers Rust path when available."""
        if self.rust_bridge:
            phi = sr.get_metric("phi_approx") if hasattr(sr, "get_metric") else 0.0
            entropy = sr.get_metric("shannon_entropy") if hasattr(sr, "get_metric") else 0.0
            return self.rust_bridge.check_anomalies(
                phi,
                entropy,
                len(consensus),
                sr.active_lens_count(),
                sr.lens_count,
                0.5,  # phi_threshold
                3,    # consensus_min
            )
        # Python fallback
        issues: list[str] = []
        active = sr.active_lens_count() if hasattr(sr, "active_lens_count") else 0
        total = getattr(sr, "lens_count", 0)
        if total > 0 and active < total * 0.5:
            issues.append(f"Low lens activity: {active}/{total}")
        if len(consensus) < 3:
            issues.append(f"Low consensus: {len(consensus)}")
        return {"has_anomaly": len(issues) > 0, "count": len(issues), "details": issues}
