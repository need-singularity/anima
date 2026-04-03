#!/usr/bin/env python3
"""Tests for infinite_evolution.py — the core infinite self-evolution loop.

Focuses on testable utility functions, data structures, and configuration
without requiring long-running evolution cycles.
"""

import os
import sys
import json
import tempfile
import math
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ═══════════════════════════════════════════
# Test module constants and configuration
# ═══════════════════════════════════════════

class TestModuleConstants:
    def test_topologies_defined(self):
        from infinite_evolution import TOPOLOGIES
        assert isinstance(TOPOLOGIES, list)
        assert len(TOPOLOGIES) >= 4
        assert 'ring' in TOPOLOGIES
        assert 'small_world' in TOPOLOGIES
        assert 'scale_free' in TOPOLOGIES
        assert 'hypercube' in TOPOLOGIES

    def test_roadmap_defined(self):
        from infinite_evolution import ROADMAP
        assert isinstance(ROADMAP, list)
        assert len(ROADMAP) >= 7  # S1 through S7 at minimum

    def test_roadmap_structure(self):
        from infinite_evolution import ROADMAP
        for stage in ROADMAP:
            assert 'name' in stage
            assert 'cells' in stage
            assert 'steps' in stage
            assert 'topo_gens' in stage
            assert 'sat_streak' in stage
            assert isinstance(stage['cells'], int)
            assert isinstance(stage['steps'], int)

    def test_roadmap_escalation(self):
        """Roadmap stages should generally escalate in cells or steps."""
        from infinite_evolution import ROADMAP
        # First few stages should have increasing cells or steps
        max_cells_seen = 0
        for stage in ROADMAP[:7]:
            max_cells_seen = max(max_cells_seen, stage['cells'])
        assert max_cells_seen >= 256  # Should reach at least 256 cells

    def test_cross_validation_threshold(self):
        from infinite_evolution import CROSS_VALIDATION_THRESHOLD
        assert CROSS_VALIDATION_THRESHOLD == 3

    def test_data_paths_defined(self):
        from infinite_evolution import DATA_DIR, STATE_PATH, LIVE_STATUS_PATH
        assert DATA_DIR is not None
        assert STATE_PATH.endswith('.json')
        assert LIVE_STATUS_PATH.endswith('.json')


# ═══════════════════════════════════════════
# Test _parallel_map
# ═══════════════════════════════════════════

class TestParallelMap:
    def test_empty_items(self):
        from infinite_evolution import _parallel_map
        result = _parallel_map(lambda x: x * 2, [])
        assert result == []

    def test_single_item(self):
        from infinite_evolution import _parallel_map
        result = _parallel_map(lambda x: x * 2, [5])
        assert result == [10]

    def test_multiple_items(self):
        from infinite_evolution import _parallel_map
        result = _parallel_map(lambda x: x ** 2, [1, 2, 3, 4])
        assert result == [1, 4, 9, 16]

    def test_preserves_order(self):
        from infinite_evolution import _parallel_map
        items = list(range(20))
        result = _parallel_map(lambda x: x * 3, items)
        assert result == [x * 3 for x in items]

    def test_sequential_fallback_on_no_parallel(self):
        import infinite_evolution as ie
        old_val = ie.ENABLE_PARALLEL
        try:
            ie.ENABLE_PARALLEL = False
            result = _parallel_map_fn(lambda x: x + 1, [10, 20, 30])
            assert result == [11, 21, 31]
        finally:
            ie.ENABLE_PARALLEL = old_val


def _parallel_map_fn(fn, items):
    from infinite_evolution import _parallel_map
    return _parallel_map(fn, items)


# ═══════════════════════════════════════════
# Test _parallel_submit
# ═══════════════════════════════════════════

class TestParallelSubmit:
    def test_empty(self):
        from infinite_evolution import _parallel_submit
        result = _parallel_submit([])
        assert result == []

    def test_single_fn(self):
        from infinite_evolution import _parallel_submit
        result = _parallel_submit([(lambda: 42, ())])
        assert result == [42]

    def test_multiple_fns(self):
        from infinite_evolution import _parallel_submit
        fns = [
            (lambda: 1, ()),
            (lambda: 2, ()),
            (lambda: 3, ()),
        ]
        result = _parallel_submit(fns)
        assert result == [1, 2, 3]

    def test_with_args(self):
        from infinite_evolution import _parallel_submit
        def add(a, b):
            return a + b
        fns = [
            (add, (1, 2)),
            (add, (3, 4)),
        ]
        result = _parallel_submit(fns)
        assert result == [3, 7]

    def test_with_kwargs(self):
        from infinite_evolution import _parallel_submit
        def greet(name, prefix="hello"):
            return f"{prefix} {name}"
        fns = [
            (greet, ("world",), {"prefix": "hi"}),
        ]
        result = _parallel_submit(fns)
        assert result == ["hi world"]


# ═══════════════════════════════════════════
# Test ExplorationBandit
# ═══════════════════════════════════════════

class TestExplorationBandit:
    def test_init(self):
        from infinite_evolution import ExplorationBandit
        bandit = ExplorationBandit()
        assert hasattr(bandit, 'update')

    def test_update_and_avg_score(self):
        from infinite_evolution import ExplorationBandit
        bandit = ExplorationBandit()
        bandit.update(64, 'ring', 'lorenz', 5)
        bandit.update(64, 'ring', 'lorenz', 3)
        key = (64, 'ring', 'lorenz')
        avg = bandit.avg_score(key)
        assert avg == 4.0  # (5+3)/2

    def test_top_bottom(self):
        from infinite_evolution import ExplorationBandit
        bandit = ExplorationBandit()
        bandit.update(64, 'ring', 'lorenz', 10)
        bandit.update(64, 'small_world', 'lorenz', 1)
        top, bottom = bandit.top_bottom(1)
        assert len(top) >= 1
        assert top[0][0] == (64, 'ring', 'lorenz')

    def test_is_bottom(self):
        from infinite_evolution import ExplorationBandit
        bandit = ExplorationBandit()
        bandit.update(64, 'ring', 'lorenz', 10)
        bandit.update(64, 'small_world', 'lorenz', 1)
        assert bandit.is_bottom(64, 'small_world', 'lorenz', n=1)


# ═══════════════════════════════════════════
# Test _ucb_select_topology
# ═══════════════════════════════════════════

class TestUCBSelectTopology:
    def test_insufficient_data_returns_none(self):
        from infinite_evolution import _ucb_select_topology, TOPOLOGIES
        # total_gens < len(TOPOLOGIES)*3 = 12 → returns None
        topo_stats = {t: {'total_laws': 0, 'gens': 0} for t in TOPOLOGIES}
        selected = _ucb_select_topology(topo_stats, total_gens=1)
        assert selected is None

    def test_selects_with_sufficient_stats(self):
        from infinite_evolution import _ucb_select_topology, TOPOLOGIES
        topo_stats = {
            'ring': {'total_laws': 15, 'gens': 5},
            'small_world': {'total_laws': 24, 'gens': 8},
            'scale_free': {'total_laws': 9, 'gens': 3},
            'hypercube': {'total_laws': 6, 'gens': 3},
        }
        selected = _ucb_select_topology(topo_stats, total_gens=19)
        assert selected in TOPOLOGIES

    def test_returns_none_if_any_topo_undercounted(self):
        from infinite_evolution import _ucb_select_topology, TOPOLOGIES
        topo_stats = {
            'ring': {'total_laws': 15, 'gens': 5},
            'small_world': {'total_laws': 24, 'gens': 8},
            'scale_free': {'total_laws': 9, 'gens': 3},
            'hypercube': {'total_laws': 2, 'gens': 2},  # < 3 gens
        }
        selected = _ucb_select_topology(topo_stats, total_gens=18)
        assert selected is None  # insufficient data for hypercube


# ═══════════════════════════════════════════
# Test _get_seasonal_phase
# ═══════════════════════════════════════════

class TestSeasonalPhase:
    def test_returns_string(self):
        from infinite_evolution import _get_seasonal_phase
        phase = _get_seasonal_phase(0)
        assert isinstance(phase, str)

    def test_cycles(self):
        from infinite_evolution import _get_seasonal_phase
        phases = [_get_seasonal_phase(i) for i in range(40)]
        # Should cycle through different phases
        unique_phases = set(phases)
        assert len(unique_phases) >= 2  # At least 2 different phases


# ═══════════════════════════════════════════
# Test LawNetwork
# ═══════════════════════════════════════════

class TestLawNetwork:
    def test_init(self):
        from infinite_evolution import LawNetwork
        net = LawNetwork()
        assert hasattr(net, 'record_discovery')
        assert hasattr(net, 'summary')
        assert isinstance(net.intervention_to_laws, dict)
        assert isinstance(net.co_occurrence, dict)

    def test_record_discovery(self):
        from infinite_evolution import LawNetwork
        net = LawNetwork()
        net.record_discovery(gen=1, law_id=100, intervention_id='noise')
        assert 'noise' in net.intervention_to_laws
        assert 100 in net.intervention_to_laws['noise']
        assert '1' in net.generation_laws

    def test_co_occurrence(self):
        from infinite_evolution import LawNetwork
        net = LawNetwork()
        net.record_discovery(gen=1, law_id=100)
        net.record_discovery(gen=1, law_id=200)
        # Co-occurrence should have been recorded
        assert len(net.co_occurrence) >= 1

    def test_summary(self):
        from infinite_evolution import LawNetwork
        net = LawNetwork()
        net.record_discovery(gen=1, law_id=100)
        net.record_discovery(gen=2, law_id=200, intervention_id='coupling')
        s = net.summary()
        assert s['total_laws_tracked'] == 2
        assert s['generations_tracked'] == 2


# ═══════════════════════════════════════════
# Test _apply_chaos_mode
# ═══════════════════════════════════════════

class TestApplyChaosMode:
    def test_lorenz(self):
        from infinite_evolution import _apply_chaos_mode
        from consciousness_engine import ConsciousnessEngine
        engine = ConsciousnessEngine(
            cell_dim=64, hidden_dim=128, max_cells=8, initial_cells=2,
        )
        # Should not crash
        _apply_chaos_mode(engine, 'lorenz')

    def test_sandpile(self):
        from infinite_evolution import _apply_chaos_mode
        from consciousness_engine import ConsciousnessEngine
        engine = ConsciousnessEngine(
            cell_dim=64, hidden_dim=128, max_cells=8, initial_cells=2,
        )
        _apply_chaos_mode(engine, 'sandpile')

    def test_unknown_mode(self):
        from infinite_evolution import _apply_chaos_mode
        from consciousness_engine import ConsciousnessEngine
        engine = ConsciousnessEngine(
            cell_dim=64, hidden_dim=128, max_cells=8, initial_cells=2,
        )
        # Unknown mode should not crash
        _apply_chaos_mode(engine, 'nonexistent_mode')


# ═══════════════════════════════════════════
# Test _entropy_reset
# ═══════════════════════════════════════════

class TestEntropyReset:
    def test_runs_without_crash(self):
        from infinite_evolution import _entropy_reset
        from consciousness_engine import ConsciousnessEngine
        engine = ConsciousnessEngine(
            cell_dim=64, hidden_dim=128, max_cells=8, initial_cells=2,
        )
        for _ in range(5):
            engine.step()
        # Should not crash
        _entropy_reset(engine, gen=6)


# ═══════════════════════════════════════════
# Test EngineGenome
# ═══════════════════════════════════════════

class TestEngineGenome:
    def test_init(self):
        from infinite_evolution import EngineGenome
        genome = EngineGenome()
        assert hasattr(genome, 'mutate') or hasattr(genome, 'to_dict') or hasattr(genome, 'genes')

    def test_can_be_serialized(self):
        from infinite_evolution import EngineGenome
        genome = EngineGenome()
        if hasattr(genome, 'to_dict'):
            d = genome.to_dict()
            assert isinstance(d, dict)


# ═══════════════════════════════════════════
# Test BestEngineTracker
# ═══════════════════════════════════════════

class TestBestEngineTracker:
    def test_init(self):
        from infinite_evolution import BestEngineTracker
        tracker = BestEngineTracker()
        assert tracker is not None

    def test_update_and_summary(self):
        from infinite_evolution import BestEngineTracker
        from consciousness_engine import ConsciousnessEngine
        tracker = BestEngineTracker()
        engine = ConsciousnessEngine(
            cell_dim=64, hidden_dim=128, max_cells=8, initial_cells=2,
        )
        for _ in range(5):
            engine.step()
        tracker.update('S1', phi=1.0, engine=engine)
        tracker.update('S1', phi=2.0, engine=engine)
        s = tracker.summary()
        assert s['global_best_phi'] >= 2.0
        assert s['global_best_stage'] == 'S1'
        assert s['stages_tracked'] == 1


# ═══════════════════════════════════════════
# Test _prune_mods
# ═══════════════════════════════════════════

class TestPruneMods:
    def test_prune_with_mock_sme(self):
        from infinite_evolution import _prune_mods
        # Create a mock SelfModifyingEngine
        sme = MagicMock()
        sme.active_mods = {}
        # Should not crash even with empty mods
        _prune_mods(sme, min_confidence=0.5, max_mods=50)


# ═══════════════════════════════════════════
# Test feature flags
# ═══════════════════════════════════════════

class TestFeatureFlags:
    def test_has_rust_engine_is_bool(self):
        from infinite_evolution import HAS_RUST_ENGINE
        assert isinstance(HAS_RUST_ENGINE, bool)

    def test_has_rust_discovery_is_bool(self):
        from infinite_evolution import HAS_RUST_DISCOVERY
        assert isinstance(HAS_RUST_DISCOVERY, bool)

    def test_has_gpu_phi_is_bool(self):
        from infinite_evolution import HAS_GPU_PHI
        assert isinstance(HAS_GPU_PHI, bool)

    def test_has_parallel_is_bool(self):
        from infinite_evolution import HAS_PARALLEL
        assert isinstance(HAS_PARALLEL, bool)

    def test_has_telescope_is_bool(self):
        from infinite_evolution import HAS_TELESCOPE
        assert isinstance(HAS_TELESCOPE, bool)

    def test_enable_parallel_is_bool(self):
        from infinite_evolution import ENABLE_PARALLEL
        assert isinstance(ENABLE_PARALLEL, bool)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
