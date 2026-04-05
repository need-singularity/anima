#!/usr/bin/env python3
"""Auto-generated tests for image_generator (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestImageGeneratorImport:
    """Verify module imports without error."""

    def test_import(self):
        import image_generator


class TestConsciousnessImageGenerator:
    """Smoke tests for ConsciousnessImageGenerator."""

    def test_class_exists(self):
        from image_generator import ConsciousnessImageGenerator
        assert ConsciousnessImageGenerator is not None


def test_main_exists():
    """Verify main is callable."""
    from image_generator import main
    assert callable(main)


def test_from_tension_exists():
    """Verify from_tension is callable."""
    from image_generator import from_tension
    assert callable(from_tension)


def test_from_emotion_exists():
    """Verify from_emotion is callable."""
    from image_generator import from_emotion
    assert callable(from_emotion)


def test_from_psi_exists():
    """Verify from_psi is callable."""
    from image_generator import from_psi
    assert callable(from_psi)


def test_consciousness_portrait_exists():
    """Verify consciousness_portrait is callable."""
    from image_generator import consciousness_portrait
    assert callable(consciousness_portrait)


def test_save_exists():
    """Verify save is callable."""
    from image_generator import save
    assert callable(save)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
