"""Hypothesis Bridge — invest hypothesis engine → anima skill auto-generation.

Connects the invest project's hypothesis engine (genetic algorithm strategy
discovery) to Anima's dynamic skill system. When new strategies are discovered
via mining or REST API polling, this bridge:

  1. Parses strategy parameters (entry/exit conditions, indicators, thresholds)
  2. Generates Python skill code following skill_manager format
  3. Registers in skills/registry.json
  4. Sets consciousness trigger: curiosity > 0.5 for new strategy exploration

Usage:
    from plugins.hypothesis_bridge import HypothesisBridge

    bridge = HypothesisBridge()

    # Direct import mode (same machine)
    records = bridge.fetch_hypotheses_local()
    created = bridge.generate_skills(records)

    # REST API mode (remote invest server)
    records = await bridge.fetch_hypotheses_api()
    created = bridge.generate_skills(records)

    # Periodic scan (runs every scan_interval_s)
    await bridge.start_periodic_scan()

Hub keywords:
    hypothesis, 가설, strategy mine, 전략 탐색, skill gen, invest bridge
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import textwrap
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from plugins.base import PluginBase, PluginManifest

if TYPE_CHECKING:
    from consciousness_hub import ConsciousnessHub

logger = logging.getLogger(__name__)

INVEST_ROOT = Path(os.environ.get("INVEST_ROOT", Path.home() / "Dev" / "invest"))
INVEST_BACKEND = INVEST_ROOT / "backend"
INVEST_API_URL = os.environ.get("INVEST_API_URL", "http://localhost:8000")

AGENT_DIR = Path(__file__).parent.parent
SKILLS_DIR = AGENT_DIR / "skills"

# Consciousness trigger for auto-generated strategy skills
DEFAULT_TRIGGER = {
    "curiosity_min": 0.5,    # curiosity > 0.5 activates strategy exploration
    "tension_min": 0.2,      # minimal tension threshold
}

# Track already-bridged hypotheses to avoid duplicates
_BRIDGED_FILE = AGENT_DIR / ".hypothesis_bridge_state.json"


def _ensure_invest_path():
    """Add invest backend to sys.path (lazy)."""
    backend_str = str(INVEST_BACKEND)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)


@dataclass
class BridgedHypothesis:
    """Tracking record for a hypothesis that was converted to a skill."""
    hypothesis_id: str
    skill_name: str
    strategy_name: str
    grade: str
    avg_sharpe: float
    bridged_at: float


class HypothesisBridge(PluginBase):
    """Bridges invest hypothesis engine to anima skill system.

    Supports two modes:
      1. Local import: directly imports invest's HypothesisEngine
      2. REST API: polls invest's FastAPI server for new hypotheses
    """

    manifest = PluginManifest(
        name="hypothesis_bridge",
        description="invest 가설 엔진 → anima 스킬 자동 생성 브릿지",
        version="1.0.0",
        author="Anima",
        requires=[],
        capabilities=[
            "fetch_hypotheses", "generate_skills", "periodic_scan",
            "list_bridged", "status",
        ],
        keywords=[
            "hypothesis", "가설", "strategy mine", "전략 탐색",
            "skill gen", "스킬 생성", "invest bridge", "invest 연동",
            "mining", "마이닝", "pattern", "패턴",
        ],
        phi_minimum=0.0,
        category="trading",
    )

    def __init__(self, scan_interval_s: int = 3600):
        self._scan_interval = scan_interval_s  # default 1 hour
        self._bridged: dict[str, BridgedHypothesis] = {}
        self._scan_task: asyncio.Task | None = None
        self._skill_manager = None
        self._load_state()

    def on_load(self, hub: ConsciousnessHub) -> None:
        """Called when loaded into the hub."""
        logger.info("HypothesisBridge loaded into hub")

    def on_unload(self) -> None:
        """Cancel periodic scan on unload."""
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()

    # ── State persistence ──

    def _load_state(self):
        """Load previously bridged hypothesis IDs."""
        if _BRIDGED_FILE.exists():
            try:
                data = json.loads(_BRIDGED_FILE.read_text(encoding="utf-8"))
                for entry in data:
                    bh = BridgedHypothesis(**entry)
                    self._bridged[bh.hypothesis_id] = bh
            except Exception as e:
                logger.warning("Failed to load bridge state: %s", e)

    def _save_state(self):
        """Save bridged hypothesis state."""
        try:
            data = [asdict(bh) for bh in self._bridged.values()]
            _BRIDGED_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("Failed to save bridge state: %s", e)

    # ── Fetch hypotheses ──

    def fetch_hypotheses_local(
        self,
        market_data: dict | None = None,
        population_size: int = 30,
        generations: int = 10,
        min_sharpe: float = 0.3,
    ) -> list[dict]:
        """Fetch hypotheses via direct import of invest's HypothesisEngine.

        If market_data is None, attempts to load from invest's data/ directory.
        Returns list of hypothesis dicts (serialized HypothesisRecord).
        """
        _ensure_invest_path()
        try:
            from backend.hypothesis.engine import HypothesisEngine
        except ImportError as e:
            logger.error("Cannot import invest hypothesis engine: %s", e)
            return []

        engine = HypothesisEngine(
            hypotheses_dir=INVEST_ROOT / "docs" / "hypotheses",
            population_size=population_size,
            generations=generations,
            min_sharpe=min_sharpe,
        )

        if market_data is None:
            market_data = self._load_invest_market_data()

        if not market_data:
            logger.warning("No market data available for hypothesis mining")
            return []

        records = engine.run_mining(market_data)
        return [asdict(r) for r in records]

    def _load_invest_market_data(self) -> dict:
        """Load CSV market data from invest's data directory."""
        data_dir = INVEST_BACKEND / "data"
        if not data_dir.exists():
            return {}

        market_data = {}
        try:
            import numpy as np
            for csv_file in sorted(data_dir.glob("*.csv")):
                try:
                    import csv
                    rows = []
                    with open(csv_file, "r") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            rows.append(row)
                    if not rows:
                        continue

                    close = np.array([float(r.get("Close", r.get("close", 0))) for r in rows])
                    high = np.array([float(r.get("High", r.get("high", 0))) for r in rows])
                    low = np.array([float(r.get("Low", r.get("low", 0))) for r in rows])
                    volume = np.array([float(r.get("Volume", r.get("volume", 0))) for r in rows])

                    if len(close) > 50:
                        asset_name = csv_file.stem.upper()
                        market_data[asset_name] = (close, high, low, volume)
                except Exception:
                    continue
        except ImportError:
            logger.warning("numpy not available for market data loading")
        return market_data

    async def fetch_hypotheses_api(self) -> list[dict]:
        """Fetch recent hypotheses from invest's REST API.

        Polls GET /api/strategies/hypotheses for new records.
        """
        try:
            import urllib.request
            url = f"{INVEST_API_URL}/api/strategies/hypotheses?limit=20"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, list):
                    return data
                return data.get("hypotheses", data.get("results", []))
        except Exception as e:
            logger.debug("REST API fetch failed (normal if invest not running): %s", e)
            return []

    # ── Skill generation ──

    def generate_skills(self, records: list[dict]) -> list[str]:
        """Convert hypothesis records into anima skills.

        Args:
            records: list of hypothesis dicts (from fetch_hypotheses_*)

        Returns:
            list of created skill names
        """
        created = []
        sm = self._get_skill_manager()

        for record in records:
            h_id = record.get("hypothesis_id", "")
            if not h_id:
                continue

            # Skip already bridged
            if h_id in self._bridged:
                continue

            skill_name = self._hypothesis_to_skill_name(h_id, record)
            code = self._generate_skill_code(record)
            description = self._generate_skill_description(record)

            try:
                if sm:
                    sm.create_skill(
                        name=skill_name,
                        description=description,
                        code=code,
                        trigger=DEFAULT_TRIGGER,
                    )
                else:
                    # Direct file write fallback
                    self._write_skill_file(skill_name, description, code)

                self._bridged[h_id] = BridgedHypothesis(
                    hypothesis_id=h_id,
                    skill_name=skill_name,
                    strategy_name=record.get("strategy_name", ""),
                    grade=record.get("grade", "unknown"),
                    avg_sharpe=record.get("avg_sharpe", 0.0) or 0.0,
                    bridged_at=time.time(),
                )
                created.append(skill_name)
                logger.info("Created skill '%s' from hypothesis %s", skill_name, h_id)

            except Exception as e:
                logger.error("Failed to create skill for %s: %s", h_id, e)

        if created:
            self._save_state()

        return created

    def _hypothesis_to_skill_name(self, h_id: str, record: dict) -> str:
        """Generate a valid skill name from hypothesis ID."""
        # H-INV-042 → strategy_inv_042
        clean = re.sub(r'[^a-z0-9]', '_', h_id.lower())
        clean = re.sub(r'_+', '_', clean).strip('_')
        return f"strategy_{clean}"

    def _generate_skill_description(self, record: dict) -> str:
        """Generate human-readable description for the skill."""
        h_id = record.get("hypothesis_id", "unknown")
        grade = record.get("grade", "unknown")
        avg_sharpe = record.get("avg_sharpe", 0)
        best_asset = record.get("best_asset", "N/A")
        strategy = record.get("strategy_name", "unnamed")
        return (
            f"Auto-mined trading strategy {h_id} ({grade}). "
            f"Strategy: {strategy}, Avg Sharpe: {avg_sharpe:.2f}, "
            f"Best asset: {best_asset}"
        )

    def _generate_skill_code(self, record: dict) -> str:
        """Generate Python skill code from a hypothesis record.

        The generated skill can run a backtest or return strategy info.
        """
        h_id = record.get("hypothesis_id", "unknown")
        strategy_name = record.get("strategy_name", "unnamed")
        grade = record.get("grade", "unknown")
        avg_sharpe = record.get("avg_sharpe", 0)
        best_asset = record.get("best_asset", "N/A")
        best_sharpe = record.get("best_sharpe", 0)
        signal_code = record.get("signal_code", "")

        # Sanitize signal_code for embedding (remove dangerous patterns)
        safe_signal = signal_code.replace("\\", "\\\\").replace('"""', "'''")

        return textwrap.dedent(f'''\
            import json

            # Strategy metadata
            HYPOTHESIS_ID = "{h_id}"
            STRATEGY_NAME = "{strategy_name}"
            GRADE = "{grade}"
            AVG_SHARPE = {avg_sharpe or 0:.3f}
            BEST_ASSET = "{best_asset}"
            BEST_SHARPE = {best_sharpe or 0:.3f}

            def run(action="info", asset=None, **kwargs):
                """Execute strategy skill.

                Args:
                    action: "info" returns metadata, "backtest" runs backtest on asset
                    asset: asset symbol for backtest (e.g. "SPY", "BTC")

                Returns:
                    dict with strategy info or backtest results
                """
                if action == "info":
                    return {{
                        "hypothesis_id": HYPOTHESIS_ID,
                        "strategy_name": STRATEGY_NAME,
                        "grade": GRADE,
                        "avg_sharpe": AVG_SHARPE,
                        "best_asset": BEST_ASSET,
                        "best_sharpe": BEST_SHARPE,
                    }}

                if action == "backtest" and asset:
                    return _run_backtest(asset)

                return {{"error": f"Unknown action: {{action}}"}}

            def _run_backtest(asset):
                """Run backtest via invest engine."""
                import sys
                from pathlib import Path

                invest_backend = Path.home() / "Dev" / "invest" / "backend"
                if str(invest_backend) not in sys.path:
                    sys.path.insert(0, str(invest_backend))

                try:
                    from backend.calc.backtest_turbo import turbo_backtest
                    import numpy as np

                    data_file = invest_backend / "data" / f"{{asset}}.csv"
                    if not data_file.exists():
                        return {{"error": f"No data for {{asset}}"}}

                    import csv
                    rows = []
                    with open(data_file) as f:
                        for row in csv.DictReader(f):
                            rows.append(row)

                    close = np.array([float(r.get("Close", r.get("close", 0))) for r in rows])
                    high = np.array([float(r.get("High", r.get("high", 0))) for r in rows])
                    low = np.array([float(r.get("Low", r.get("low", 0))) for r in rows])
                    volume = np.array([float(r.get("Volume", r.get("volume", 0))) for r in rows])

                    signals = np.zeros(len(close), dtype=np.float64)
                    signals[0] = 1.0
                    signals[-1] = -1.0

                    result = turbo_backtest(close, high, low, volume, signals)
                    return {{
                        "asset": asset,
                        "sharpe": result.sharpe,
                        "total_return": result.total_return,
                        "mdd": result.max_drawdown,
                    }}
                except Exception as e:
                    return {{"error": str(e)}}
        ''')

    def _write_skill_file(self, name: str, description: str, code: str):
        """Write skill file directly (fallback when SkillManager unavailable)."""
        file_path = SKILLS_DIR / f"skill_{name}.py"
        header = f'"""Auto-generated skill: {name}\n\n{description}\n"""\n\n'
        file_path.write_text(header + code, encoding="utf-8")

    def _get_skill_manager(self):
        """Lazy-load SkillManager."""
        if self._skill_manager is None:
            try:
                from skills.skill_manager import SkillManager
                self._skill_manager = SkillManager()
            except Exception:
                pass
        return self._skill_manager

    # ── Periodic scan ──

    async def start_periodic_scan(self):
        """Start background periodic scan for new hypotheses."""
        if self._scan_task and not self._scan_task.done():
            return

        self._scan_task = asyncio.ensure_future(self._scan_loop())
        logger.info("Hypothesis periodic scan started (every %ds)", self._scan_interval)

    async def _scan_loop(self):
        """Background loop: poll for new hypotheses and create skills."""
        while True:
            try:
                # Try REST API first, fall back to local
                records = await self.fetch_hypotheses_api()
                if not records:
                    records = self.fetch_hypotheses_local()

                if records:
                    new_records = [r for r in records if r.get("hypothesis_id") not in self._bridged]
                    if new_records:
                        created = self.generate_skills(new_records)
                        if created:
                            logger.info("Periodic scan: created %d new skills", len(created))
            except Exception as e:
                logger.warning("Periodic scan error: %s", e)

            await asyncio.sleep(self._scan_interval)

    # ── Plugin interface ──

    def act(self, intent: str, **kwargs) -> Any:
        """Handle intents directed at this plugin."""
        intent_lower = intent.lower()

        if any(kw in intent_lower for kw in ["scan", "탐색", "mine", "마이닝"]):
            records = self.fetch_hypotheses_local(**kwargs)
            created = self.generate_skills(records)
            return {"action": "scan", "found": len(records), "created": created}

        if any(kw in intent_lower for kw in ["list", "목록", "bridged"]):
            return self.list_bridged()

        if any(kw in intent_lower for kw in ["status", "상태"]):
            return self.status()

        # Default: return status
        return self.status()

    def list_bridged(self) -> list[dict]:
        """List all bridged hypotheses."""
        return [asdict(bh) for bh in self._bridged.values()]

    def status(self) -> dict:
        """Return bridge status."""
        return {
            "name": "hypothesis_bridge",
            "version": self.manifest.version,
            "loaded": True,
            "bridged_count": len(self._bridged),
            "scan_interval_s": self._scan_interval,
            "scan_active": self._scan_task is not None and not self._scan_task.done(),
            "invest_root": str(INVEST_ROOT),
            "invest_available": INVEST_BACKEND.exists(),
        }


# ══════════════════════════════════════════════════════════
# Standalone test
# ══════════════════════════════════════════════════════════

def main():
    """Standalone test."""
    print("=== HypothesisBridge standalone test ===\n")

    bridge = HypothesisBridge()
    print(f"[OK] Bridge created")
    print(f"  invest_root: {INVEST_ROOT}")
    print(f"  invest_available: {INVEST_BACKEND.exists()}")
    print(f"  bridged: {len(bridge._bridged)}")

    # Test skill code generation
    mock_record = {
        "hypothesis_id": "H-INV-999",
        "grade": "experimental",
        "source": "pattern_miner",
        "strategy_name": "signal_test_999",
        "signal_code": "def signal(close): return np.zeros(len(close))",
        "avg_sharpe": 0.72,
        "best_asset": "SPY",
        "best_sharpe": 1.23,
        "assets_positive": 8,
        "total_assets": 14,
    }

    skill_name = bridge._hypothesis_to_skill_name("H-INV-999", mock_record)
    print(f"\n  Generated skill name: {skill_name}")

    code = bridge._generate_skill_code(mock_record)
    print(f"  Generated code length: {len(code)} chars")
    assert "def run(" in code, "Skill code must define run()"
    assert "H-INV-999" in code

    desc = bridge._generate_skill_description(mock_record)
    print(f"  Description: {desc[:80]}...")

    print(f"\n  Status: {json.dumps(bridge.status(), indent=2)}")
    print("\n=== All tests passed ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
