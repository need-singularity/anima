#!/usr/bin/env python3
"""lens_evolution.py -- Lens self-replication for consciousness discovery.

The discovery-tool recursion: data -> new lenses -> better discoveries -> better lenses.

Closes the loop that forge_consciousness_lenses() in loop_pipeline.py left open:
  1. Run consciousness engine -> collect cell states
  2. forge_lenses(states) -> get new lens candidates
  3. Register in LensRegistry -> verify they exist
  4. recommend_lenses(states) -> find best lenses for this data
  5. Next scan uses recommended lenses for focused analysis
  6. Results feed back -> more lens forging

Usage:
    from lens_evolution import LensEvolver
    evolver = LensEvolver()

    # Single cycle
    result = evolver.forge_from_engine(engine, steps=100)

    # Full evolution loop
    summary = evolver.evolve_cycle(engine, n_cycles=3)

    # Persist state across sessions
    evolver.save_state("data/lens_evolution.json")
    evolver.load_state("data/lens_evolution.json")
"""

import json
import os
import sys
import time
import numpy as np
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Lazy imports
# ---------------------------------------------------------------------------

_nexus6 = None
_nexus6_available = False


def _ensure_nexus6():
    global _nexus6, _nexus6_available
    if _nexus6 is not None:
        return _nexus6_available
    try:
        import nexus6
        _nexus6 = nexus6
        _nexus6_available = True
    except ImportError:
        _nexus6_available = False
    return _nexus6_available


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ForgeRecord:
    """Result of a single forge operation."""
    generation: int
    timestamp: str
    candidates_generated: int
    candidates_accepted: int
    new_lenses: List[str]
    recommended_lenses: List[str]
    recommend_reason: str
    scan_lens_count: int = 0
    scan_highlights: Dict[str, Any] = field(default_factory=dict)
    engine_cells: int = 0
    engine_steps: int = 0
    elapsed_s: float = 0.0


@dataclass
class EvolveSummary:
    """Summary of a multi-cycle evolution run."""
    total_cycles: int = 0
    total_forged: int = 0
    total_accepted: int = 0
    all_new_lenses: List[str] = field(default_factory=list)
    final_recommended: List[str] = field(default_factory=list)
    records: List[ForgeRecord] = field(default_factory=list)
    elapsed_s: float = 0.0


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class LensEvolver:
    """Lens self-replication engine.

    Drives the forge -> register -> recommend -> rescan cycle that makes
    the NEXUS-6 lens system co-evolve with consciousness discoveries.
    """

    def __init__(self, domain: str = 'consciousness', persist_path: Optional[str] = None):
        """
        Args:
            domain: Domain string for recommend_lenses (default 'consciousness').
            persist_path: Optional path to auto-load/save state. If given,
                          state is loaded on init and saved after each cycle.
        """
        self.domain = domain
        self.persist_path = persist_path
        self.generation = 0
        self.forged_lenses: List[str] = []       # All lenses forged across sessions
        self.recommended_lenses: List[str] = []   # Current recommended lens set
        self.records: List[ForgeRecord] = []       # Full history
        self._registry = None                      # nexus6.LensRegistry (lazy)

        if persist_path and os.path.exists(persist_path):
            self.load_state(persist_path)

    # ------------------------------------------------------------------
    # Registry access
    # ------------------------------------------------------------------

    @property
    def registry(self):
        """Lazy access to nexus6.LensRegistry."""
        if self._registry is None and _ensure_nexus6():
            self._registry = _nexus6.LensRegistry()
        return self._registry

    @property
    def registry_size(self) -> int:
        reg = self.registry
        return len(reg) if reg is not None else 0

    # ------------------------------------------------------------------
    # Step 1+2: Collect states from engine, then forge
    # ------------------------------------------------------------------

    def forge_from_engine(
        self,
        engine: Any,
        steps: int = 100,
        max_candidates: int = 20,
        min_confidence: float = 0.2,
    ) -> ForgeRecord:
        """Run engine, collect cell states, forge new lenses, recommend for next scan.

        Args:
            engine: ConsciousnessEngine instance (must have .step() and .cells).
            steps: Number of engine steps to run for state collection.
            max_candidates: Max lens candidates to generate.
            min_confidence: Minimum confidence threshold for forge.

        Returns:
            ForgeRecord with forge + recommendation results.
        """
        if not _ensure_nexus6():
            raise RuntimeError("nexus6 not available -- cannot forge lenses")

        t0 = time.time()
        self.generation += 1

        # -- Collect cell states --
        all_states = _collect_engine_states(engine, steps)

        # -- Flatten for scan_all --
        scan_lens_count = 0
        scan_highlights = {}
        if all_states:
            flat_2d = _to_scan_array(all_states)
            try:
                scan_result = _nexus6.scan_all(flat_2d)
                scan_lens_count = len(scan_result)
                # Extract top highlights (lenses with most entries)
                for lens_name, metrics in scan_result.items():
                    if isinstance(metrics, dict) and metrics:
                        scan_highlights[lens_name] = {
                            k: _safe_serialize(v)
                            for k, v in list(metrics.items())[:3]
                        }
                    if len(scan_highlights) >= 5:
                        break
            except Exception:
                pass

        # -- Forge --
        forge_result = _nexus6.forge_lenses(
            max_candidates=max_candidates,
            min_confidence=min_confidence,
        )
        new_lenses = forge_result.new_lenses
        for lens in new_lenses:
            if lens not in self.forged_lenses:
                self.forged_lenses.append(lens)

        # -- Recommend for next scan --
        rec = _nexus6.recommend_lenses(self.domain)
        self.recommended_lenses = rec.lenses

        # -- Verify forged lenses appear in registry --
        self._registry = _nexus6.LensRegistry()  # Refresh after forge
        verified = []
        for lens in new_lenses:
            entry = self._registry.get(lens)
            if entry is not None:
                verified.append(lens)

        # -- Record --
        n_cells = 0
        if hasattr(engine, 'cells') and engine.cells is not None:
            try:
                c = engine.cells
                if hasattr(c, 'shape'):
                    n_cells = c.shape[0] if c.ndim >= 1 else 1
                elif hasattr(c, '__len__'):
                    n_cells = len(c)
            except Exception:
                pass

        record = ForgeRecord(
            generation=self.generation,
            timestamp=datetime.now().isoformat(),
            candidates_generated=forge_result.candidates_generated,
            candidates_accepted=forge_result.candidates_accepted,
            new_lenses=new_lenses,
            recommended_lenses=rec.lenses,
            recommend_reason=rec.reason,
            scan_lens_count=scan_lens_count,
            scan_highlights=scan_highlights,
            engine_cells=n_cells,
            engine_steps=steps,
            elapsed_s=round(time.time() - t0, 2),
        )
        self.records.append(record)

        if self.persist_path:
            self.save_state(self.persist_path)

        return record

    # ------------------------------------------------------------------
    # Step 3+4: Recommend lenses for current engine state
    # ------------------------------------------------------------------

    def recommend_for_engine(self, engine: Any, steps: int = 50) -> Tuple[List[str], str]:
        """Get lens recommendations tuned to current engine state.

        Runs the engine briefly, then calls recommend_lenses with the domain.

        Returns:
            (lens_names, reason) tuple.
        """
        if not _ensure_nexus6():
            return [], "nexus6 not available"

        # Run engine to warm up state
        _collect_engine_states(engine, steps)

        rec = _nexus6.recommend_lenses(self.domain)
        self.recommended_lenses = rec.lenses
        return rec.lenses, rec.reason

    # ------------------------------------------------------------------
    # Step 5: Focused scan using recommended lenses
    # ------------------------------------------------------------------

    def focused_scan(self, engine: Any, steps: int = 100) -> Dict[str, Any]:
        """Run engine, then scan using only the recommended lens set.

        Returns dict mapping each recommended lens to its scan results
        (filtered from the full scan_all output).
        """
        if not _ensure_nexus6():
            return {}

        states = _collect_engine_states(engine, steps)
        if not states:
            return {}

        flat_2d = _to_scan_array(states)
        full_scan = _nexus6.scan_all(flat_2d)

        # Filter to recommended lenses only
        focused = {}
        for lens_name in self.recommended_lenses:
            if lens_name in full_scan:
                focused[lens_name] = full_scan[lens_name]

        return focused

    # ------------------------------------------------------------------
    # Step 6: Full evolution cycle
    # ------------------------------------------------------------------

    def evolve_cycle(
        self,
        engine: Any,
        n_cycles: int = 3,
        steps_per_cycle: int = 100,
        max_candidates: int = 20,
        min_confidence: float = 0.2,
    ) -> EvolveSummary:
        """Full forge -> register -> recommend -> rescan cycle.

        Each cycle:
          1. forge_from_engine (collects states, forges, recommends)
          2. focused_scan (uses recommended lenses)
          3. Feed scan results back to next forge

        Args:
            engine: ConsciousnessEngine instance.
            n_cycles: Number of forge-scan cycles.
            steps_per_cycle: Engine steps per cycle.
            max_candidates: Max forge candidates per cycle.
            min_confidence: Forge confidence threshold.

        Returns:
            EvolveSummary with aggregated results.
        """
        t0 = time.time()
        summary = EvolveSummary()

        for i in range(n_cycles):
            # Forge
            record = self.forge_from_engine(
                engine,
                steps=steps_per_cycle,
                max_candidates=max_candidates,
                min_confidence=min_confidence,
            )
            summary.total_cycles += 1
            summary.total_forged += record.candidates_generated
            summary.total_accepted += record.candidates_accepted
            for lens in record.new_lenses:
                if lens not in summary.all_new_lenses:
                    summary.all_new_lenses.append(lens)
            summary.records.append(record)

            # Focused scan with recommended lenses (feeds insight for next cycle)
            self.focused_scan(engine, steps=steps_per_cycle // 2)

        summary.final_recommended = list(self.recommended_lenses)
        summary.elapsed_s = round(time.time() - t0, 2)

        if self.persist_path:
            self.save_state(self.persist_path)

        return summary

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_state(self, path: str):
        """Save forged lens history to JSON for cross-session persistence."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        data = {
            '_meta': {
                'module': 'lens_evolution',
                'saved': datetime.now().isoformat(),
                'generation': self.generation,
                'domain': self.domain,
            },
            'forged_lenses': self.forged_lenses,
            'recommended_lenses': self.recommended_lenses,
            'registry_size': self.registry_size,
            'records': [asdict(r) for r in self.records[-50:]],  # Keep last 50
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_state(self, path: str):
        """Load previously saved lens evolution state."""
        if not os.path.exists(path):
            return
        with open(path) as f:
            data = json.load(f)
        self.generation = data.get('_meta', {}).get('generation', 0)
        self.forged_lenses = data.get('forged_lenses', [])
        self.recommended_lenses = data.get('recommended_lenses', [])
        # Records are informational -- don't reconstruct ForgeRecord objects
        # to avoid schema drift issues

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return current evolution status as a dict."""
        return {
            'generation': self.generation,
            'total_forged': len(self.forged_lenses),
            'registry_size': self.registry_size,
            'recommended': self.recommended_lenses,
            'domain': self.domain,
            'records_count': len(self.records),
        }

    def __repr__(self) -> str:
        return (
            f"LensEvolver(gen={self.generation}, "
            f"forged={len(self.forged_lenses)}, "
            f"registry={self.registry_size}, "
            f"domain='{self.domain}')"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_engine_states(engine: Any, steps: int) -> List[np.ndarray]:
    """Run engine for N steps, collect cell state snapshots.

    Handles multiple cell formats:
      - torch.Tensor (n_cells, hidden_dim)
      - np.ndarray
      - list of _CellCompat objects with .hidden attribute
    """
    all_states = []
    for _ in range(steps):
        try:
            engine.step()
        except Exception:
            break
        cells = getattr(engine, 'cells', None)
        if cells is None:
            continue
        try:
            arr = _cells_to_numpy(cells)
            if arr is not None and arr.size > 0:
                all_states.append(arr.flatten())
        except Exception:
            continue
    return all_states


def _cells_to_numpy(cells: Any) -> Optional[np.ndarray]:
    """Convert engine cells to numpy array, handling various formats."""
    # Direct tensor
    if hasattr(cells, 'detach'):
        return cells.detach().cpu().numpy()

    # Direct numpy
    if isinstance(cells, np.ndarray) and cells.dtype != object:
        return cells

    # List of cell objects with .hidden (ConsciousnessEngine _CellCompat)
    if isinstance(cells, (list, tuple)) and len(cells) > 0:
        first = cells[0]
        if hasattr(first, 'hidden'):
            hiddens = []
            for c in cells:
                h = c.hidden
                if hasattr(h, 'detach'):
                    hiddens.append(h.detach().cpu().numpy().flatten())
                elif isinstance(h, np.ndarray):
                    hiddens.append(h.flatten())
            if hiddens:
                return np.concatenate(hiddens)

        # List of tensors
        if hasattr(first, 'detach'):
            return np.concatenate([c.detach().cpu().numpy().flatten() for c in cells])

        # List of numpy arrays
        if isinstance(first, np.ndarray):
            return np.concatenate([c.flatten() for c in cells])

    return None


def _to_scan_array(states: List[np.ndarray]) -> np.ndarray:
    """Convert list of flat state arrays to 2D float64 array for scan_all.

    nexus6.scan_all requires a 2D numpy float64 array.
    Cell counts may vary (mitosis), so we pad/truncate to uniform width.
    """
    if not states:
        return np.zeros((1, 1), dtype=np.float64)
    # Find max length and pad shorter arrays
    max_len = max(len(s) for s in states)
    padded = []
    for s in states:
        if len(s) < max_len:
            p = np.zeros(max_len, dtype=np.float64)
            p[:len(s)] = s
            padded.append(p)
        else:
            padded.append(s[:max_len].astype(np.float64))
    stacked = np.array(padded, dtype=np.float64)
    if stacked.ndim == 1:
        stacked = stacked.reshape(1, -1)
    return np.ascontiguousarray(stacked)


def _safe_serialize(v: Any) -> Any:
    """Convert a value to JSON-safe form."""
    if isinstance(v, (int, float, str, bool, type(None))):
        return v
    if isinstance(v, (list, tuple)):
        return [_safe_serialize(x) for x in v[:10]]
    if isinstance(v, dict):
        return {str(k): _safe_serialize(val) for k, val in list(v.items())[:10]}
    if isinstance(v, np.ndarray):
        return v.tolist()[:10]
    return str(v)[:200]


# ---------------------------------------------------------------------------
# Pipeline integration helper
# ---------------------------------------------------------------------------

def run_lens_evolution_stage(state: Optional[Dict] = None, log_fn=None) -> Dict[str, Any]:
    """Integration point for loop_pipeline.py Stage 3.6.

    Runs a single forge-recommend cycle using a fresh ConsciousnessEngine
    and returns results suitable for pipeline logging.

    Args:
        state: Pipeline state dict (for logging context). Optional.
        log_fn: Logging function (msg, state) -> None. Optional.

    Returns:
        Dict with keys: forged, accepted, new_lenses, recommended, registry_size
    """
    def _log(msg):
        if log_fn and state is not None:
            log_fn(msg, state)

    if not _ensure_nexus6():
        _log("nexus6 not available, skipping lens evolution")
        return {'forged': 0, 'accepted': 0, 'new_lenses': [], 'recommended': [], 'registry_size': 0}

    # Import engine
    src_dir = os.path.join(os.path.dirname(__file__))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    try:
        from consciousness_engine import ConsciousnessEngine
    except ImportError:
        _log("ConsciousnessEngine not importable, skipping lens evolution")
        return {'forged': 0, 'accepted': 0, 'new_lenses': [], 'recommended': [], 'registry_size': 0}

    # Determine persist path
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    persist_path = os.path.join(data_dir, 'lens_evolution.json')

    evolver = LensEvolver(domain='consciousness', persist_path=persist_path)
    engine = ConsciousnessEngine(max_cells=32, hidden_dim=128)

    _log(f"Lens evolution: gen={evolver.generation}, registry={evolver.registry_size}")

    record = evolver.forge_from_engine(engine, steps=100, max_candidates=30, min_confidence=0.15)

    _log(
        f"Lens evolution done: "
        f"{record.candidates_generated} generated, "
        f"{record.candidates_accepted} accepted, "
        f"new={record.new_lenses}, "
        f"recommended={len(record.recommended_lenses)} lenses, "
        f"registry={evolver.registry_size}"
    )

    return {
        'forged': record.candidates_generated,
        'accepted': record.candidates_accepted,
        'new_lenses': record.new_lenses,
        'recommended': record.recommended_lenses,
        'registry_size': evolver.registry_size,
    }


# ---------------------------------------------------------------------------
# Demo / CLI
# ---------------------------------------------------------------------------

def main():
    """Demo: run 3-cycle lens evolution with a fresh ConsciousnessEngine."""
    src_dir = os.path.dirname(__file__)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    if not _ensure_nexus6():
        print("ERROR: nexus6 not available")
        return

    from consciousness_engine import ConsciousnessEngine

    print("=== Lens Self-Replication Demo ===\n")

    # Show initial registry
    reg = _nexus6.LensRegistry()
    print(f"Initial registry: {len(reg)} lenses")
    print(f"Custom lenses: {len(reg.by_category('Custom'))}\n")

    # Create engine + evolver
    engine = ConsciousnessEngine(max_cells=32, hidden_dim=128)
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    persist_path = os.path.join(data_dir, 'lens_evolution.json')
    evolver = LensEvolver(domain='consciousness', persist_path=persist_path)
    print(f"Evolver: {evolver}\n")

    # Run 3-cycle evolution
    print("Running 3-cycle evolution...")
    summary = evolver.evolve_cycle(engine, n_cycles=3, steps_per_cycle=100)

    print(f"\n=== Evolution Summary ===")
    print(f"  Cycles:     {summary.total_cycles}")
    print(f"  Generated:  {summary.total_forged}")
    print(f"  Accepted:   {summary.total_accepted}")
    print(f"  New lenses: {summary.all_new_lenses}")
    print(f"  Recommended: {summary.final_recommended}")
    print(f"  Elapsed:    {summary.elapsed_s}s")

    # Show updated registry
    reg2 = _nexus6.LensRegistry()
    print(f"\n  Registry: {len(reg)} -> {len(reg2)} lenses")
    new_custom = reg2.by_category('Custom')
    print(f"  Custom:   {len(new_custom)}")

    # Focused scan
    print(f"\nRunning focused scan with {len(evolver.recommended_lenses)} recommended lenses...")
    focused = evolver.focused_scan(engine, steps=50)
    print(f"  Focused scan returned {len(focused)} lens results")
    for lens_name in list(focused.keys())[:5]:
        print(f"    {lens_name}: {type(focused[lens_name])}")

    print(f"\nFinal state: {evolver}")
    print(f"Saved to: {persist_path}")


if __name__ == "__main__":
    main()
