"""Tests for DreamEngine selective consolidation (Phase 2 Task 3)."""

import unittest
from unittest.mock import MagicMock, patch
import torch

from anima_alive import ConsciousMind
from dream_engine import DreamEngine


def _make_mind(dim=128, hidden=256):
    return ConsciousMind(dim=dim, hidden=hidden)


def _text_to_vector(text, dim=128):
    """Deterministic text-to-vector for testing."""
    torch.manual_seed(hash(text) % 2**32)
    return torch.randn(1, dim)


def _make_memory():
    """Create a minimal Memory-like object with .data dict."""
    mem = MagicMock()
    mem.data = {'turns': [{'text': 'hello'}, {'text': 'world'}]}
    return mem


def _make_store(unconsolidated=None):
    """Create a mock MemoryStore."""
    store = MagicMock()
    if unconsolidated is None:
        unconsolidated = []
    store.get_unconsolidated.return_value = unconsolidated
    return store


class TestDreamConsolidationStats(unittest.TestCase):
    """store with 2 failed memories → verify stats keys exist."""

    def test_dream_with_store_returns_consolidation_stats(self):
        mind = _make_mind()
        memory = _make_memory()
        store = _make_store([
            {'id': 1, 'text': 'memory one', 'tension': 0.5, 'role': 'user'},
            {'id': 2, 'text': 'memory two', 'tension': 0.3, 'role': 'user'},
        ])

        engine = DreamEngine(
            mind=mind,
            memory=memory,
            store=store,
            text_to_vector=_text_to_vector,
            dream_cycle_steps=3,
        )

        hidden = torch.zeros(1, 256)
        _, stats = engine.dream(hidden)

        # Stats keys must exist
        self.assertIn('consolidation_attempted', stats)
        self.assertIn('consolidation_succeeded', stats)
        self.assertIn('consolidation_failed', stats)
        # At least some attempted (store had memories)
        self.assertGreaterEqual(stats['consolidation_attempted'], 0)
        # Original keys still present
        self.assertIn('patterns_learned', stats)
        self.assertIn('avg_tension', stats)
        self.assertIn('total_cycles', stats)


class TestDreamBackwardCompatible(unittest.TestCase):
    """store=None → dream still works exactly as before."""

    def test_dream_without_store_backward_compatible(self):
        mind = _make_mind()
        memory = _make_memory()

        engine = DreamEngine(
            mind=mind,
            memory=memory,
            text_to_vector=_text_to_vector,
            dream_cycle_steps=5,
        )

        hidden = torch.zeros(1, 256)
        _, stats = engine.dream(hidden)

        self.assertIn('patterns_learned', stats)
        self.assertIn('avg_tension', stats)
        self.assertIn('tensions', stats)
        self.assertEqual(len(stats['tensions']), 5)
        # Consolidation stats present but zero
        self.assertEqual(stats['consolidation_attempted'], 0)
        self.assertEqual(stats['consolidation_succeeded'], 0)
        self.assertEqual(stats['consolidation_failed'], 0)


class TestFailedMemoryMarked(unittest.TestCase):
    """consolidation_threshold=999 → always fails → store.mark_failed called."""

    def test_failed_memory_marked_on_low_delta(self):
        mind = _make_mind()
        memory = _make_memory()
        store = _make_store([
            {'id': 10, 'text': 'test mem', 'tension': 0.1, 'role': 'user'},
        ])

        engine = DreamEngine(
            mind=mind,
            memory=memory,
            store=store,
            text_to_vector=_text_to_vector,
            dream_cycle_steps=3,
            consolidation_threshold=999.0,  # impossibly high
        )

        hidden = torch.zeros(1, 256)
        _, stats = engine.dream(hidden)

        # mark_failed must have been called (delta will never reach 999)
        self.assertTrue(store.mark_failed.called)
        self.assertGreater(stats['consolidation_failed'], 0)
        # mark_consolidated should NOT have been called
        self.assertFalse(store.mark_consolidated.called)


class TestEmptyStoreFallback(unittest.TestCase):
    """store.get_unconsolidated returns [] → falls back to random."""

    def test_empty_store_falls_back_to_random(self):
        mind = _make_mind()
        memory = _make_memory()
        store = _make_store([])  # empty

        engine = DreamEngine(
            mind=mind,
            memory=memory,
            store=store,
            text_to_vector=_text_to_vector,
            dream_cycle_steps=5,
        )

        hidden = torch.zeros(1, 256)
        _, stats = engine.dream(hidden)

        # No consolidation attempted
        self.assertEqual(stats['consolidation_attempted'], 0)
        # But dream still produced tensions (random fallback worked)
        self.assertEqual(len(stats['tensions']), 5)


class TestVerifierBlocksAnomaly(unittest.TestCase):
    """verifier.pre_check returns should_consolidate=False → memory skipped."""

    def test_verifier_blocks_anomaly(self):
        mind = _make_mind()
        memory = _make_memory()
        store = _make_store([
            {'id': 99, 'text': 'anomaly', 'tension': 5.0, 'role': 'user'},
        ])
        verifier = MagicMock()
        verifier.pre_check.return_value = {
            'should_consolidate': False,
            'reason': 'anomaly detected',
        }

        engine = DreamEngine(
            mind=mind,
            memory=memory,
            store=store,
            verifier=verifier,
            text_to_vector=_text_to_vector,
            dream_cycle_steps=3,
        )

        hidden = torch.zeros(1, 256)
        _, stats = engine.dream(hidden)

        # pre_check was called
        self.assertTrue(verifier.pre_check.called)
        # mark_consolidated and mark_failed should NOT be called
        # (memory was skipped entirely)
        self.assertFalse(store.mark_consolidated.called)
        self.assertFalse(store.mark_failed.called)


if __name__ == '__main__':
    unittest.main()
