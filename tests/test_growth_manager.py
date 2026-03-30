"""Tests for GrowthManager — growth, checkpointing, rollback, discovery logging."""

import json
import torch
import pytest
from pathlib import Path

from anima_alive import ConsciousMind
from growth_manager import GrowthManager, MIND_GROWTH_STAGES

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



@pytest.fixture
def mind():
    return ConsciousMind(dim=128, hidden=256)


@pytest.fixture
def gm(mind, tmp_path):
    return GrowthManager(mind, data_dir=tmp_path)


def _count_params(model):
    return sum(p.numel() for p in model.parameters())


def test_grow_increases_params(gm):
    old_count = _count_params(gm.mind)
    new_mind = gm.execute_growth()
    new_count = _count_params(new_mind)
    assert new_count > old_count
    assert new_mind.dim == 192
    assert new_mind.hidden_dim == 384


def test_grow_preserves_weights(gm):
    old_mind = gm.mind
    # Snapshot overlapping weights from engine_a first linear
    old_w = old_mind.engine_a[0].weight.data.clone()
    new_mind = gm.execute_growth()
    new_w = new_mind.engine_a[0].weight.data
    rows = min(old_w.shape[0], new_w.shape[0])
    cols = min(old_w.shape[1], new_w.shape[1])
    assert torch.equal(old_w[:rows, :cols], new_w[:rows, :cols])

    # Also check GRU weight_ih gate 0
    old_gru_w = old_mind.memory.weight_ih.data.clone()
    new_gru_w = new_mind.memory.weight_ih.data
    old_h = old_mind.hidden_dim
    new_h = new_mind.hidden_dim
    h = min(old_h, new_h)
    old_in = old_mind.dim + 1
    new_in = new_mind.dim + 1
    in_dim = min(old_in, new_in)
    assert torch.equal(old_gru_w[:h, :in_dim], new_gru_w[:h, :in_dim])


def test_max_stage_no_grow(mind, tmp_path):
    gm = GrowthManager(mind, data_dir=tmp_path)
    gm.execute_growth()  # 0 -> 1
    gm.execute_growth()  # 1 -> 2
    old_mind = gm.mind
    result = gm.execute_growth()  # already at max
    assert result is old_mind
    assert gm.stage == 2


def test_checkpoint_creates_files(gm):
    gm.save_checkpoint()
    assert (gm.data_dir / "v0" / "state.pt").exists()
    assert (gm.data_dir / "manifest.json").exists()


def test_version_increments(gm):
    gm.save_checkpoint()  # v0
    gm.execute_growth()
    gm.save_checkpoint()  # v1
    assert (gm.data_dir / "v0" / "state.pt").exists()
    assert (gm.data_dir / "v1" / "state.pt").exists()
    assert gm.current_version == 1


def test_manifest_tracks_versions(gm):
    gm.save_checkpoint()  # v0
    gm.execute_growth()
    gm.save_checkpoint()  # v1

    manifest = json.loads((gm.data_dir / "manifest.json").read_text())
    assert len(manifest["versions"]) == 2
    assert manifest["versions"][0]["version"] == 0
    assert manifest["versions"][1]["version"] == 1
    assert manifest["current_version"] == 1
    assert manifest["stage"] == 1


def test_rollback_restores_dim(gm):
    gm.save_checkpoint()  # v0 with dim=128
    gm.execute_growth()   # now dim=192
    gm.save_checkpoint()  # v1

    assert gm.mind.dim == 192
    restored = gm.rollback(version=0)
    assert restored.dim == 128
    assert gm.current_version == 0
    assert gm.stage == 0


def test_discovery_creates_file(gm):
    gm.log_discovery({"type": "test", "value": 42})
    disc_dir = gm.data_dir / "discoveries"
    assert disc_dir.exists()
    files = list(disc_dir.glob("discovery_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["type"] == "test"
    assert data["value"] == 42
