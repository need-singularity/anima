#!/usr/bin/env python3
"""Auto-generated tests for module_factory (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestModuleFactoryImport:
    """Verify module imports without error."""

    def test_import(self):
        import module_factory


class TestModuleSpec:
    """Smoke tests for ModuleSpec."""

    def test_class_exists(self):
        from module_factory import ModuleSpec
        assert ModuleSpec is not None


class TestModuleFactory:
    """Smoke tests for ModuleFactory."""

    def test_class_exists(self):
        from module_factory import ModuleFactory
        assert ModuleFactory is not None


def test_main_exists():
    """Verify main is callable."""
    from module_factory import main
    assert callable(main)


def test_create_exists():
    """Verify create is callable."""
    from module_factory import create
    assert callable(create)


def test_test_exists():
    """Verify test is callable."""
    from module_factory import test
    assert callable(test)


def test_register_to_hub_exists():
    """Verify register_to_hub is callable."""
    from module_factory import register_to_hub
    assert callable(register_to_hub)


def test_list_created_exists():
    """Verify list_created is callable."""
    from module_factory import list_created
    assert callable(list_created)


def test_create_from_description_exists():
    """Verify create_from_description is callable."""
    from module_factory import create_from_description
    assert callable(create_from_description)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
