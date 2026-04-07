#!/usr/bin/env python3
"""Auto-generated tests for model_loader (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestModelLoaderImport:
    """Verify module imports without error."""

    def test_import(self):
        import model_loader


class TestModelWrapper:
    """Smoke tests for ModelWrapper."""

    def test_class_exists(self):
        from model_loader import ModelWrapper
        assert ModelWrapper is not None


def test_load_model_exists():
    """Verify load_model is callable."""
    from model_loader import load_model
    assert callable(load_model)


def test_list_available_models_exists():
    """Verify list_available_models is callable."""
    from model_loader import list_available_models
    assert callable(list_available_models)


def test_generate_exists():
    """Verify generate is callable."""
    from model_loader import generate
    assert callable(generate)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
