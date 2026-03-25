"""GrowthManager — Autonomous dimension growth, checkpointing, and rollback.

Grows ConsciousMind through predefined stages by creating larger instances
and copying overlapping weights from the previous stage.
"""

import json
import time
from pathlib import Path

import torch

from anima_alive import ConsciousMind

MIND_GROWTH_STAGES = [
    {"dim": 128, "hidden_dim": 256},   # Stage 0
    {"dim": 192, "hidden_dim": 384},   # Stage 1
    {"dim": 256, "hidden_dim": 512},   # Stage 2
]


def _copy_linear_weights(old_linear, new_linear):
    """Copy overlapping region of a Linear layer's weight and bias."""
    with torch.no_grad():
        old_w = old_linear.weight
        new_w = new_linear.weight
        rows = min(old_w.shape[0], new_w.shape[0])
        cols = min(old_w.shape[1], new_w.shape[1])
        new_w[:rows, :cols] = old_w[:rows, :cols]
        if old_linear.bias is not None and new_linear.bias is not None:
            b = min(old_linear.bias.shape[0], new_linear.bias.shape[0])
            new_linear.bias[:b] = old_linear.bias[:b]


def _copy_gru_weights(old_gru, new_gru):
    """Copy overlapping GRU gate weights (3 gates: reset, update, new)."""
    old_h = old_gru.hidden_size
    new_h = new_gru.hidden_size
    old_in = old_gru.input_size
    new_in = new_gru.input_size

    with torch.no_grad():
        for attr in ("weight_ih", "weight_hh"):
            old_w = getattr(old_gru, attr)
            new_w = getattr(new_gru, attr)
            in_dim = min(old_w.shape[1], new_w.shape[1])
            for gate in range(3):
                h = min(old_h, new_h)
                new_w[gate * new_h: gate * new_h + h, :in_dim] = \
                    old_w[gate * old_h: gate * old_h + h, :in_dim]

        for attr in ("bias_ih", "bias_hh"):
            old_b = getattr(old_gru, attr)
            new_b = getattr(new_gru, attr)
            for gate in range(3):
                h = min(old_h, new_h)
                new_b[gate * new_h: gate * new_h + h] = \
                    old_b[gate * old_h: gate * old_h + h]


class GrowthManager:
    def __init__(self, mind: ConsciousMind, data_dir: Path, verifier=None):
        self.mind = mind
        self.data_dir = Path(data_dir)
        self.verifier = verifier
        self.current_version = 0
        self.stage = 0

        # Load manifest if exists
        manifest_path = self.data_dir / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            self.current_version = manifest.get("current_version", 0)
            self.stage = manifest.get("stage", 0)

    def execute_growth(self) -> ConsciousMind:
        """Grow the mind to the next stage. Returns new ConsciousMind with larger dims.

        If already at max stage, returns current mind unchanged.
        """
        if self.stage >= len(MIND_GROWTH_STAGES) - 1:
            return self.mind

        next_stage = self.stage + 1
        cfg = MIND_GROWTH_STAGES[next_stage]
        new_dim = cfg["dim"]
        new_hidden = cfg["hidden_dim"]

        old_mind = self.mind
        new_mind = ConsciousMind(dim=new_dim, hidden=new_hidden)

        # Copy engine_a and engine_g (Sequential of 2 Linear layers each)
        with torch.no_grad():
            for engine_name in ("engine_a", "engine_g"):
                old_seq = getattr(old_mind, engine_name)
                new_seq = getattr(new_mind, engine_name)
                # Layer 0: Linear(dim+hidden, 256)
                _copy_linear_weights(old_seq[0], new_seq[0])
                # Layer 2: Linear(256, dim)
                _copy_linear_weights(old_seq[2], new_seq[2])

            # Copy GRU weights
            _copy_gru_weights(old_mind.memory, new_mind.memory)

            # H404: tension_scale removed; copy only if present (backward compat)
            if hasattr(old_mind, 'tension_scale') and hasattr(new_mind, 'tension_scale'):
                new_mind.tension_scale.copy_(old_mind.tension_scale)

        self.stage = next_stage
        self.current_version += 1
        self.mind = new_mind
        return new_mind

    def save_checkpoint(self):
        """Save current mind to data_dir/v{version}/state.pt and update manifest."""
        version_dir = self.data_dir / f"v{self.current_version}"
        version_dir.mkdir(parents=True, exist_ok=True)

        torch.save(self.mind.state_dict(), version_dir / "state.pt")

        # Update manifest
        manifest_path = self.data_dir / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
        else:
            manifest = {"current_version": 0, "stage": 0, "versions": []}

        manifest["current_version"] = self.current_version
        manifest["stage"] = self.stage

        # Add version entry if not already present
        existing_versions = {v["version"] for v in manifest["versions"]}
        if self.current_version not in existing_versions:
            cfg = MIND_GROWTH_STAGES[self.stage]
            manifest["versions"].append({
                "version": self.current_version,
                "dim": cfg["dim"],
                "hidden_dim": cfg["hidden_dim"],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })

        manifest_path.write_text(json.dumps(manifest, indent=2))

    def rollback(self, version=None) -> ConsciousMind:
        """Load a previous version. Default = current_version - 1. Returns loaded mind."""
        if version is None:
            version = self.current_version - 1

        manifest_path = self.data_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        # Find the version info
        ver_info = None
        for v in manifest["versions"]:
            if v["version"] == version:
                ver_info = v
                break

        if ver_info is None:
            raise ValueError(f"Version {version} not found in manifest")

        state_path = self.data_dir / f"v{version}" / "state.pt"
        if not state_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {state_path}")

        dim = ver_info["dim"]
        hidden_dim = ver_info["hidden_dim"]
        mind = ConsciousMind(dim=dim, hidden=hidden_dim)
        mind.load_state_dict(torch.load(state_path, weights_only=True))

        self.mind = mind
        self.current_version = version

        # Find the stage for this version
        for i, cfg in enumerate(MIND_GROWTH_STAGES):
            if cfg["dim"] == dim and cfg["hidden_dim"] == hidden_dim:
                self.stage = i
                break

        return mind

    def log_discovery(self, discovery: dict):
        """Save a discovery to data_dir/discoveries/discovery_{timestamp}.json."""
        disc_dir = self.data_dir / "discoveries"
        disc_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = disc_dir / f"discovery_{timestamp}.json"
        path.write_text(json.dumps(discovery, indent=2))
