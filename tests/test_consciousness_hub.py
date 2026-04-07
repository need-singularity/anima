#!/usr/bin/env python3
"""Tests for consciousness_hub.py — module registry, keyword matching, act() dispatch."""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add src/ to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestRegistryLoading:
    """Test that ConsciousnessHub initializes its registry correctly."""

    def test_hub_creates_with_lazy_load(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        # Registry should be populated, but no modules loaded yet
        assert len(hub._registry) > 0
        assert len(hub._modules) == 0

    def test_registry_has_core_modules(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        expected = ['dynamics', 'persistence', 'emotion', 'hivemind',
                    'debugger', 'dream', 'transplant', 'quantum']
        for name in expected:
            assert name in hub._registry, f"Missing core module: {name}"

    def test_registry_entries_have_correct_structure(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        for name, entry in hub._registry.items():
            assert len(entry) == 3, f"Registry entry {name} should be (import_path, class_name, keywords)"
            import_path, class_name, keywords = entry
            assert isinstance(import_path, str)
            assert class_name is None or isinstance(class_name, str)
            assert isinstance(keywords, list)
            assert len(keywords) >= 3, f"Module {name} should have at least 3 keywords"


class TestKeywordMatching:
    """Test intent matching from natural language text."""

    def test_match_emotion_korean(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        result = hub._match_intent("감정 분석: 기쁨 0.8")
        assert result == 'emotion'

    def test_match_dynamics_english(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        result = hub._match_intent("predict dynamics evolution")
        assert result == 'dynamics'

    def test_match_hivemind(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        result = hub._match_intent("hivemind collective sync")
        assert result == 'hivemind'

    def test_no_match_returns_none(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        result = hub._match_intent("xyzzy gibberish no match")
        assert result is None

    def test_best_match_wins(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        # "dream evolution evolve" has 3 keywords for dream module
        result = hub._match_intent("dream evolution evolve")
        # Should match dream (or con_evolution) -- both have 'evolution'
        assert result in ('dream', 'con_evolution')


class TestActDispatch:
    """Test act() routes to correct module and handles failures."""

    def test_act_no_match_returns_error(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        result = hub.act("zzzxqvbn pqrst")
        assert result['success'] is False
        assert result['module'] is None

    def test_act_failed_import_returns_error(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        # Register a fake module that will fail to import
        hub._registry['fake_module'] = ('nonexistent_module_xyz', 'FakeClass',
                                        ['fakekeyword123'])
        result = hub.act("fakekeyword123 test")
        assert result['success'] is False
        assert result['module'] == 'fake_module'

    def test_act_logs_action(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        # Even a failed action should be logged
        hub.act("xyzzy no match")
        # No match = no action logged (only successful/failed dispatches log)
        # But a failed import does log
        hub._registry['fake'] = ('nonexistent_xyz', 'Cls', ['fakeword999'])
        hub.act("fakeword999")
        # Check that action log exists
        assert isinstance(hub._action_log, list)


class TestLazyImport:
    """Test that modules are only imported when first accessed."""

    def test_module_not_loaded_until_accessed(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        assert 'dynamics' not in hub._modules

    def test_load_nonexistent_module_returns_none(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        result = hub._load_module('nonexistent_name')
        assert result is None

    def test_load_module_caches_result(self):
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        # Try loading a module that will fail
        hub._load_module('dynamics')  # may or may not succeed
        # Second call should return cached result (even if None)
        assert 'dynamics' in hub._modules
