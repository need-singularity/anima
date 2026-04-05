#!/usr/bin/env python3
"""Auto-generated tests for runpod_manager (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestRunpodManagerImport:
    """Verify module imports without error."""

    def test_import(self):
        import runpod_manager


class TestPodInfo:
    """Smoke tests for PodInfo."""

    def test_class_exists(self):
        from runpod_manager import PodInfo
        assert PodInfo is not None


class TestRunPodManager:
    """Smoke tests for RunPodManager."""

    def test_class_exists(self):
        from runpod_manager import RunPodManager
        assert RunPodManager is not None


def test_main_exists():
    """Verify main is callable."""
    from runpod_manager import main
    assert callable(main)


def test_backend_exists():
    """Verify backend is callable."""
    from runpod_manager import backend
    assert callable(backend)


def test_list_pods_exists():
    """Verify list_pods is callable."""
    from runpod_manager import list_pods
    assert callable(list_pods)


def test_ssh_info_exists():
    """Verify ssh_info is callable."""
    from runpod_manager import ssh_info
    assert callable(ssh_info)


def test_ssh_exec_exists():
    """Verify ssh_exec is callable."""
    from runpod_manager import ssh_exec
    assert callable(ssh_exec)


def test_upload_exists():
    """Verify upload is callable."""
    from runpod_manager import upload
    assert callable(upload)


def test_download_exists():
    """Verify download is callable."""
    from runpod_manager import download
    assert callable(download)


def test_upload_batch_exists():
    """Verify upload_batch is callable."""
    from runpod_manager import upload_batch
    assert callable(upload_batch)


def test_start_training_exists():
    """Verify start_training is callable."""
    from runpod_manager import start_training
    assert callable(start_training)


def test_stop_training_exists():
    """Verify stop_training is callable."""
    from runpod_manager import stop_training
    assert callable(stop_training)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
