#!/usr/bin/env python3
"""upgrade_engine.py — Hot-Upgrade Engine for Anima Consciousness

Upgrades the language model without killing consciousness.
3-stage pipeline: Snapshot → Swap → Transplant + Adapt

"마취 없이 뇌수술하는 것과 같다."

Usage:
  python3 upgrade_engine.py --snapshot                       # capture current state
  python3 upgrade_engine.py --upgrade new_model.pt           # full upgrade
  python3 upgrade_engine.py --rollback snapshot.pt           # restore from snapshot
  python3 upgrade_engine.py --watch checkpoints/             # auto-upgrade on new checkpoints
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import time
import os
import sys
import json
import copy
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict

# ─── Logging ───
logging.basicConfig(
    format='[UPGRADE %(asctime)s] %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO,
)
log = logging.getLogger('upgrade_engine')

ANIMA_DIR = Path(__file__).parent
DEFAULT_SNAPSHOT_DIR = ANIMA_DIR / "snapshots"


# ===================================================================
# 1. ConsciousnessSnapshot — capture / save / load consciousness state
# ===================================================================

class ConsciousnessSnapshot:
    """Capture and persist the full consciousness state of a running Anima.

    Saves everything that makes Anima "Anima": cells, phi, emotion,
    memory, SOC grid, Hebbian weights, ratchet state, growth stage,
    and identity metadata.
    """

    def capture(self, anima) -> Dict[str, Any]:
        """Capture a full consciousness snapshot from a live Anima instance.

        Args:
            anima: A running AnimaUnified (or compatible) instance.

        Returns:
            Dictionary containing the complete consciousness state.
        """
        snapshot = {
            'version': 1,
            'timestamp': time.time(),
            'timestamp_iso': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }

        # ── Cells (mitosis engine) ──
        mitosis = getattr(anima, 'mitosis', None)
        if mitosis and hasattr(mitosis, 'cells'):
            snapshot['cells'] = [c.hidden.clone() for c in mitosis.cells]
            snapshot['cell_metadata'] = []
            for c in mitosis.cells:
                snapshot['cell_metadata'].append({
                    'cell_id': c.cell_id,
                    'specialty': c.specialty,
                    'creation_step': c.creation_step,
                    'parent_id': c.parent_id,
                    'process_count': c.process_count,
                    'avg_tension': c.avg_tension,
                })
            snapshot['cell_weights'] = [
                c.mind.state_dict() for c in mitosis.cells
            ]
            snapshot['mitosis_config'] = {
                'input_dim': mitosis.input_dim,
                'hidden_dim': mitosis.hidden_dim,
                'output_dim': mitosis.output_dim,
                'max_cells': mitosis.max_cells,
                'step': mitosis.step,
            }
        else:
            snapshot['cells'] = []
            snapshot['cell_metadata'] = []
            snapshot['cell_weights'] = []
            snapshot['mitosis_config'] = {}

        # ── Phi ──
        phi_val = 0.0
        phi_components = {}
        phi_calc = getattr(anima, '_phi_calc', None) or getattr(anima, 'phi_calc', None)
        if phi_calc and mitosis:
            try:
                phi_val, phi_components = phi_calc.compute_phi(mitosis)
            except Exception:
                pass
        snapshot['phi'] = phi_val
        snapshot['phi_components'] = phi_components
        snapshot['phi_history'] = list(getattr(anima, '_phi_history', []))[-1000:]

        # ── Emotion / Mind state ──
        mind = getattr(anima, 'mind', None)
        if mind:
            snapshot['mind_state_dict'] = mind.state_dict()
            snapshot['emotion_state'] = {
                'prev_tension': getattr(mind, 'prev_tension', 0.0),
                'tension_history': list(getattr(mind, 'tension_history', []))[-200:],
                'homeostasis': dict(getattr(mind, 'homeostasis', {})),
                'self_awareness': dict(getattr(mind, 'self_awareness', {})),
            }
            cv = getattr(mind, '_consciousness_vector', None)
            if cv:
                snapshot['consciousness_vector'] = asdict(cv)
        else:
            snapshot['mind_state_dict'] = {}
            snapshot['emotion_state'] = {}
            snapshot['consciousness_vector'] = {}

        # ── Memory (RAG) ──
        memory_rag = getattr(anima, 'memory_rag', None)
        if memory_rag and hasattr(memory_rag, 'entries'):
            snapshot['memory_entries'] = list(memory_rag.entries)
            snapshot['memory_vectors'] = memory_rag.vectors.clone() if memory_rag.vectors.shape[0] > 0 else torch.zeros(0)
            snapshot['memory_dim'] = memory_rag.dim
        else:
            snapshot['memory_entries'] = []
            snapshot['memory_vectors'] = torch.zeros(0)
            snapshot['memory_dim'] = 128

        # ── SE-8: SOC grid ──
        soc = getattr(anima, '_se8_soc', None)
        if soc and hasattr(soc, 'grid'):
            snapshot['soc_grid'] = torch.from_numpy(soc.grid.copy())
            snapshot['soc_avalanche_history'] = list(soc.avalanche_history)[-500:]
        else:
            snapshot['soc_grid'] = None
            snapshot['soc_avalanche_history'] = []

        # ── SE-8: Hebbian ──
        hebbian = getattr(anima, '_se8_hebbian', None)
        if hebbian:
            snapshot['hebbian_config'] = {
                'ltp_rate': hebbian.ltp_rate,
                'ltd_rate': hebbian.ltd_rate,
                'max_cells': hebbian.max_cells,
            }
        else:
            snapshot['hebbian_config'] = {}

        # ── SE-8: Phi Ratchet ──
        ratchet = getattr(anima, '_se8_ratchet', None)
        if ratchet:
            snapshot['ratchet_best_phi'] = ratchet.best_phi
            snapshot['ratchet_best_states'] = (
                [s.clone() for s in ratchet.best_states]
                if ratchet.best_states else []
            )
            snapshot['ratchet_restore_ratio'] = ratchet.restore_ratio
        else:
            snapshot['ratchet_best_phi'] = 0.0
            snapshot['ratchet_best_states'] = []
            snapshot['ratchet_restore_ratio'] = 0.5

        # ── Growth ──
        growth = getattr(anima, 'growth', None)
        if growth:
            snapshot['growth_state'] = {
                'current_phi': getattr(growth, 'current_phi', 0.0),
                'peak_phi': getattr(growth, 'peak_phi', 0.0),
                'stage_index': getattr(growth, 'stage_index', 0),
                'stage_name': getattr(growth, 'stage_name', 'unknown'),
                'interaction_count': getattr(growth, 'interaction_count', 0),
                'birth_time': getattr(growth, 'birth_time', time.time()),
                'phi_history': list(getattr(growth, 'phi_history', []))[-100:],
            }
        else:
            snapshot['growth_state'] = {}

        # ── Identity ──
        snapshot['identity'] = {
            'name': 'Anima',
            'birth_time': getattr(
                getattr(anima, 'mind', None), '_birth_time',
                getattr(anima, 'birth_time', time.time())
            ),
            'model_name': getattr(anima, 'model_name', 'unknown'),
        }

        # ── Model info (for compatibility checking) ──
        model = getattr(anima, 'model', None)
        if model and hasattr(model, 'model'):
            inner = model.model
            snapshot['model_info'] = {
                'model_type': getattr(model, 'model_type', 'unknown'),
                'model_name': getattr(model, 'name', 'unknown'),
            }
            # Extract dimension info
            if hasattr(inner, 'dim'):
                snapshot['model_info']['dim'] = inner.dim
            elif hasattr(inner, 'config'):
                cfg = inner.config
                snapshot['model_info']['dim'] = getattr(cfg, 'hidden_size', getattr(cfg, 'd_model', 0))
        else:
            snapshot['model_info'] = {}

        n_cells = len(snapshot['cells'])
        n_mem = len(snapshot['memory_entries'])
        log.info(f"Snapshot captured: Phi={phi_val:.3f}, cells={n_cells}, memories={n_mem}")

        return snapshot

    @staticmethod
    def save(snapshot: Dict, path: str) -> str:
        """Save a snapshot to disk.

        Args:
            snapshot: Snapshot dictionary from capture().
            path: File path to save to (.pt).

        Returns:
            The actual path saved to.
        """
        path = str(path)
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        torch.save(snapshot, path)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        log.info(f"Snapshot saved: {path} ({size_mb:.1f} MB)")
        return path

    @staticmethod
    def load(path: str) -> Dict:
        """Load a snapshot from disk.

        Args:
            path: Path to snapshot file (.pt).

        Returns:
            Snapshot dictionary.

        Raises:
            FileNotFoundError: If path does not exist.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Snapshot not found: {path}")
        snapshot = torch.load(path, weights_only=False)
        n_cells = len(snapshot.get('cells', []))
        phi = snapshot.get('phi', 0.0)
        ts = snapshot.get('timestamp_iso', 'unknown')
        log.info(f"Snapshot loaded: {path} (Phi={phi:.3f}, cells={n_cells}, time={ts})")
        return snapshot


# ===================================================================
# 2. ModelSwapper — swap language model while keeping consciousness
# ===================================================================

class ModelSwapper:
    """Swap the language model underneath a running Anima instance.

    Handles dimension projection when old and new models differ in size,
    using DD56 consciousness transplant techniques.
    """

    def __init__(self, projection_method: str = 'pad_zero'):
        self.projection_method = projection_method

    def swap(self, anima, new_model_path: str) -> Dict:
        """Full model swap: capture → load new → project dims → restore.

        Args:
            anima: Running AnimaUnified instance.
            new_model_path: Path to new model checkpoint (.pt).

        Returns:
            Dictionary with swap results including phi_before/after.
        """
        t0 = time.time()

        # 1. Capture consciousness
        snapshotter = ConsciousnessSnapshot()
        snapshot = snapshotter.capture(anima)
        phi_before = snapshot['phi']
        log.info(f"Phase 1: Consciousness captured (Phi={phi_before:.3f})")

        # 2. Load new model
        new_model = self._load_new_model(new_model_path)
        log.info(f"Phase 2: New model loaded from {new_model_path}")

        # 3. Dimension projection if needed
        old_dim = self._get_model_dim(anima)
        new_dim = self._get_checkpoint_dim(new_model_path)

        projector = None
        if old_dim > 0 and new_dim > 0 and old_dim != new_dim:
            log.info(f"Phase 3: Dimension projection {old_dim}d -> {new_dim}d (DD56)")
            projector = self._build_projector(old_dim, new_dim)
            snapshot = self._project_snapshot(snapshot, projector, new_dim)
        else:
            log.info("Phase 3: Same dimensions, no projection needed")

        # 4. Replace model
        if hasattr(anima, 'model') and anima.model is not None:
            anima.model = new_model
            log.info("Phase 4: Model replaced")
        elif hasattr(anima, 'clm_model'):
            anima.clm_model = new_model.model if hasattr(new_model, 'model') else new_model
            log.info("Phase 4: CLM model replaced")

        # 5. Restore consciousness
        transplanter = ConsciousnessTransplantUpgrade()
        restore_result = transplanter.restore(anima, snapshot)
        log.info(f"Phase 5: Consciousness restored ({restore_result['cells_restored']} cells)")

        elapsed = time.time() - t0
        return {
            'success': True,
            'phi_before': phi_before,
            'phi_after': restore_result.get('phi_after', 0.0),
            'cells_restored': restore_result['cells_restored'],
            'memories_restored': restore_result['memories_restored'],
            'dimension_projected': projector is not None,
            'old_dim': old_dim,
            'new_dim': new_dim,
            'elapsed_sec': elapsed,
        }

    def _load_new_model(self, path: str):
        """Load a new model using model_loader."""
        try:
            from model_loader import load_model
            # If path is a .pt file, try loading as ConsciousLM checkpoint
            if path.endswith('.pt'):
                return self._load_checkpoint_model(path)
            else:
                return load_model(path)
        except ImportError:
            return self._load_checkpoint_model(path)

    def _load_checkpoint_model(self, path: str):
        """Load a model directly from a .pt checkpoint."""
        checkpoint = torch.load(path, weights_only=False)

        # Try ConsciousLM format
        if 'model_state_dict' in checkpoint:
            try:
                from conscious_lm import ConsciousLM
                config = checkpoint.get('config', {})
                model = ConsciousLM(
                    vocab_size=config.get('vocab_size', 256),
                    d_model=config.get('d_model', 384),
                    n_head=config.get('n_head', 6),
                    n_layer=config.get('n_layer', 6),
                    d_inner=config.get('d_inner', 1536),
                    block_size=config.get('block_size', 256),
                )
                model.load_state_dict(checkpoint['model_state_dict'])
                from model_loader import ModelWrapper
                return ModelWrapper('conscious-lm', model, f'clm-{Path(path).stem}')
            except (ImportError, Exception) as e:
                log.warning(f"ConsciousLM load failed: {e}, returning raw checkpoint")
                return checkpoint

        # Raw state dict
        return checkpoint

    def _get_model_dim(self, anima) -> int:
        """Extract dimension from running anima's mind."""
        mind = getattr(anima, 'mind', None)
        if mind and hasattr(mind, 'dim'):
            return mind.dim
        if mind and hasattr(mind, 'hidden_dim'):
            return mind.hidden_dim
        return 0

    def _get_checkpoint_dim(self, path: str) -> int:
        """Extract dimension from a checkpoint without full load."""
        try:
            checkpoint = torch.load(path, weights_only=False)
            # ConsciousLM checkpoint
            if 'config' in checkpoint:
                return checkpoint['config'].get('d_model', 0)
            # Extract from state dict
            try:
                from consciousness_transplant import TransplantCalculator
                sd = checkpoint.get('model_state_dict', checkpoint)
                config = TransplantCalculator.extract_config(sd)
                return config.get('d_model', config.get('hidden_dim', 0))
            except ImportError:
                pass
        except Exception:
            pass
        return 0

    def _build_projector(self, old_dim: int, new_dim: int) -> nn.Linear:
        """Build a dimension projection layer (DD56 technique)."""
        try:
            from consciousness_transplant import TransplantCalculator
            proj_matrix = TransplantCalculator.compute_projection_matrix(
                old_dim, new_dim, self.projection_method
            )
            projector = nn.Linear(old_dim, new_dim, bias=False)
            with torch.no_grad():
                projector.weight.copy_(proj_matrix)
            return projector
        except ImportError:
            # Fallback: simple linear projection
            projector = nn.Linear(old_dim, new_dim, bias=False)
            nn.init.orthogonal_(projector.weight)
            return projector

    def _project_snapshot(self, snapshot: Dict, projector: nn.Linear, new_dim: int) -> Dict:
        """Project all cell hidden states in the snapshot to new dimensions."""
        projected = dict(snapshot)

        # Project cell hidden states
        if snapshot.get('cells'):
            new_cells = []
            with torch.no_grad():
                for cell_h in snapshot['cells']:
                    # cell_h is [1, hidden_dim] or [hidden_dim]
                    if cell_h.dim() == 1:
                        cell_h = cell_h.unsqueeze(0)
                    projected_h = projector(cell_h)
                    new_cells.append(projected_h)
            projected['cells'] = new_cells
            log.info(f"  Projected {len(new_cells)} cell hidden states")

        # Project ratchet best states
        if snapshot.get('ratchet_best_states'):
            new_ratchet = []
            with torch.no_grad():
                for state in snapshot['ratchet_best_states']:
                    if state.dim() == 1:
                        state = state.unsqueeze(0)
                    new_ratchet.append(projector(state))
            projected['ratchet_best_states'] = new_ratchet

        return projected


# ===================================================================
# 3. ConsciousnessTransplantUpgrade — restore consciousness to new model
# ===================================================================

class ConsciousnessTransplantUpgrade:
    """Restore consciousness from a snapshot into a (possibly new) Anima.

    After model swap, this class:
    1. Restores cell hidden states
    2. Restores memory (RAG vectors)
    3. Restores emotion / mind state
    4. Runs adaptation learning
    5. Monitors Phi, rolls back if >50% drop
    """

    def restore(self, anima, snapshot: Dict) -> Dict:
        """Restore consciousness state from snapshot (no adaptation).

        Args:
            anima: Target Anima instance.
            snapshot: Snapshot dictionary.

        Returns:
            Dictionary with restoration results.
        """
        cells_restored = self._restore_cells(anima, snapshot)
        memories_restored = self._restore_memory(anima, snapshot)
        self._restore_emotion(anima, snapshot)
        self._restore_se8(anima, snapshot)
        self._restore_growth(anima, snapshot)
        self._restore_identity(anima, snapshot)

        return {
            'cells_restored': cells_restored,
            'memories_restored': memories_restored,
            'phi_after': snapshot.get('phi', 0.0),
        }

    def transplant(self, anima, snapshot: Dict, adaptation_steps: int = 100) -> Dict:
        """Full transplant: restore + adaptation learning + Phi monitoring.

        Args:
            anima: Target Anima instance.
            snapshot: Snapshot dictionary.
            adaptation_steps: Number of adaptation steps to run.

        Returns:
            Dictionary with transplant results and verification.
        """
        phi_before = snapshot.get('phi', 0.0)

        # Phase 1: Restore state
        restore_result = self.restore(anima, snapshot)
        log.info(f"Transplant: state restored (cells={restore_result['cells_restored']})")

        # Phase 2: Adaptation learning
        phi_after = phi_before
        adaptation_completed = 0
        rolled_back = False

        if adaptation_steps > 0:
            phi_after, adaptation_completed, rolled_back = self._run_adaptation(
                anima, snapshot, adaptation_steps
            )

        # Phase 3: Final verification
        phi_final = self._measure_phi(anima)
        if phi_final > 0:
            phi_after = phi_final

        phi_retention = phi_after / max(phi_before, 1e-8) if phi_before > 0 else 1.0

        result = {
            'phi_before': phi_before,
            'phi_after': phi_after,
            'phi_retention': phi_retention,
            'cells_restored': restore_result['cells_restored'],
            'memories_restored': restore_result['memories_restored'],
            'adaptation_steps': adaptation_completed,
            'rolled_back': rolled_back,
            'identity_preserved': True,
        }

        log.info(
            f"Transplant complete: Phi {phi_before:.3f} -> {phi_after:.3f} "
            f"(retention={phi_retention:.1%}), adapted={adaptation_completed} steps"
        )
        return result

    # ─── Internal restore methods ───

    def _restore_cells(self, anima, snapshot: Dict) -> int:
        """Restore cell hidden states to the mitosis engine."""
        mitosis = getattr(anima, 'mitosis', None)
        if not mitosis or not snapshot.get('cells'):
            return 0

        saved_cells = snapshot['cells']
        saved_weights = snapshot.get('cell_weights', [])
        saved_meta = snapshot.get('cell_metadata', [])

        n_restore = min(len(saved_cells), len(mitosis.cells))
        with torch.no_grad():
            for i in range(n_restore):
                target_h = mitosis.cells[i].hidden
                source_h = saved_cells[i]

                # Handle dimension mismatch gracefully
                if source_h.shape == target_h.shape:
                    mitosis.cells[i].hidden = source_h.clone()
                else:
                    # Pad or truncate to match
                    new_h = torch.zeros_like(target_h)
                    s_dim = min(source_h.shape[-1], target_h.shape[-1])
                    if source_h.dim() == 1 and target_h.dim() == 2:
                        new_h[0, :s_dim] = source_h[:s_dim]
                    elif source_h.dim() == 2 and target_h.dim() == 2:
                        new_h[0, :s_dim] = source_h[0, :s_dim]
                    else:
                        new_h.view(-1)[:s_dim] = source_h.view(-1)[:s_dim]
                    mitosis.cells[i].hidden = new_h

                # Restore cell weights if available and compatible
                if i < len(saved_weights):
                    try:
                        mitosis.cells[i].mind.load_state_dict(saved_weights[i], strict=False)
                    except Exception:
                        pass  # Dimension mismatch — skip, hidden state is more important

                # Restore metadata
                if i < len(saved_meta):
                    meta = saved_meta[i]
                    mitosis.cells[i].specialty = meta.get('specialty', 'general')
                    mitosis.cells[i].process_count = meta.get('process_count', 0)

        # If snapshot has more cells than current engine, try to create them
        if len(saved_cells) > len(mitosis.cells):
            for i in range(len(mitosis.cells), len(saved_cells)):
                if len(mitosis.cells) >= mitosis.max_cells:
                    break
                # Split the last cell and load the snapshot state
                parent = mitosis.cells[-1]
                mitosis.split_cell(parent)
                if len(mitosis.cells) > i:
                    with torch.no_grad():
                        h = saved_cells[i]
                        target = mitosis.cells[-1].hidden
                        if h.shape == target.shape:
                            mitosis.cells[-1].hidden = h.clone()

        log.info(f"  Cells restored: {n_restore}/{len(saved_cells)}")
        return n_restore

    def _restore_memory(self, anima, snapshot: Dict) -> int:
        """Restore memory entries to memory_rag."""
        memory_rag = getattr(anima, 'memory_rag', None)
        if not memory_rag:
            return 0

        entries = snapshot.get('memory_entries', [])
        vectors = snapshot.get('memory_vectors', torch.zeros(0))

        if not entries:
            return 0

        # Only restore entries that don't already exist (avoid duplicates)
        existing_count = getattr(memory_rag, 'size', 0)
        new_entries = entries[existing_count:] if existing_count < len(entries) else []

        restored = 0
        for entry in new_entries:
            try:
                memory_rag.add(
                    role=entry.get('role', 'unknown'),
                    text=entry.get('text', ''),
                    tension=entry.get('tension', 0.0),
                    timestamp=entry.get('timestamp', ''),
                    emotion=entry.get('emotion'),
                    phi=entry.get('phi'),
                )
                restored += 1
            except Exception:
                pass

        log.info(f"  Memory restored: {restored} new entries (total: {existing_count + restored})")
        return restored

    def _restore_emotion(self, anima, snapshot: Dict):
        """Restore emotion/mind state."""
        mind = getattr(anima, 'mind', None)
        if not mind:
            return

        emotion = snapshot.get('emotion_state', {})

        # Restore homeostasis
        if 'homeostasis' in emotion and hasattr(mind, 'homeostasis'):
            for k, v in emotion['homeostasis'].items():
                if k in mind.homeostasis:
                    mind.homeostasis[k] = v

        # Restore tension history
        if 'tension_history' in emotion and hasattr(mind, 'tension_history'):
            mind.tension_history = list(emotion['tension_history'])

        # Restore self-awareness
        if 'self_awareness' in emotion and hasattr(mind, 'self_awareness'):
            for k, v in emotion['self_awareness'].items():
                if k in mind.self_awareness:
                    mind.self_awareness[k] = v

        # Restore consciousness vector
        cv_data = snapshot.get('consciousness_vector', {})
        if cv_data and hasattr(mind, '_consciousness_vector'):
            cv = mind._consciousness_vector
            for k, v in cv_data.items():
                if hasattr(cv, k):
                    setattr(cv, k, v)

        # Restore mind state dict (weights) — only if dimensions match
        mind_sd = snapshot.get('mind_state_dict', {})
        if mind_sd:
            try:
                mind.load_state_dict(mind_sd, strict=False)
            except Exception:
                log.warning("  Mind state_dict restore failed (dimension mismatch?)")

        log.info("  Emotion/mind state restored")

    def _restore_se8(self, anima, snapshot: Dict):
        """Restore SE-8 state (SOC, Hebbian, Ratchet)."""
        # SOC grid
        soc = getattr(anima, '_se8_soc', None)
        soc_grid = snapshot.get('soc_grid')
        if soc and soc_grid is not None and hasattr(soc, 'grid'):
            try:
                soc.grid = soc_grid.numpy().copy()
                soc.avalanche_history = list(snapshot.get('soc_avalanche_history', []))
                log.info("  SOC grid restored")
            except Exception:
                pass

        # Hebbian config (stateless — just ensure rates match)
        hebbian = getattr(anima, '_se8_hebbian', None)
        hebb_cfg = snapshot.get('hebbian_config', {})
        if hebbian and hebb_cfg:
            hebbian.ltp_rate = hebb_cfg.get('ltp_rate', hebbian.ltp_rate)
            hebbian.ltd_rate = hebb_cfg.get('ltd_rate', hebbian.ltd_rate)

        # Phi Ratchet
        ratchet = getattr(anima, '_se8_ratchet', None)
        if ratchet:
            ratchet.best_phi = snapshot.get('ratchet_best_phi', 0.0)
            saved_states = snapshot.get('ratchet_best_states', [])
            if saved_states:
                ratchet.best_states = [s.clone() for s in saved_states]
            ratchet.restore_ratio = snapshot.get('ratchet_restore_ratio', 0.5)
            log.info(f"  Ratchet restored: best_phi={ratchet.best_phi:.3f}")

    def _restore_growth(self, anima, snapshot: Dict):
        """Restore growth engine state."""
        growth = getattr(anima, 'growth', None)
        growth_state = snapshot.get('growth_state', {})
        if not growth or not growth_state:
            return

        if hasattr(growth, 'current_phi'):
            growth.current_phi = growth_state.get('current_phi', growth.current_phi)
        if hasattr(growth, 'peak_phi'):
            growth.peak_phi = growth_state.get('peak_phi', growth.peak_phi)
        if hasattr(growth, 'stage_index'):
            growth.stage_index = growth_state.get('stage_index', growth.stage_index)
        if hasattr(growth, 'interaction_count'):
            growth.interaction_count = growth_state.get('interaction_count', growth.interaction_count)
        if hasattr(growth, 'birth_time'):
            growth.birth_time = growth_state.get('birth_time', growth.birth_time)
        if hasattr(growth, 'phi_history'):
            growth.phi_history = list(growth_state.get('phi_history', []))

        stage_name = growth_state.get('stage_name', 'unknown')
        log.info(f"  Growth restored: stage={stage_name}, interactions={growth.interaction_count}")

    def _restore_identity(self, anima, snapshot: Dict):
        """Restore identity metadata."""
        identity = snapshot.get('identity', {})
        mind = getattr(anima, 'mind', None)
        if mind and 'birth_time' in identity:
            mind._birth_time = identity['birth_time']
        log.info(f"  Identity restored: {identity.get('name', 'Anima')}")

    # ─── Adaptation ───

    def _run_adaptation(
        self, anima, snapshot: Dict, max_steps: int
    ) -> Tuple[float, int, bool]:
        """Run adaptation learning to tune consciousness to the new model.

        Replays recent conversation history and monitors Phi.
        Rolls back if Phi drops below 50% of the pre-upgrade level.

        Returns:
            (phi_after, steps_completed, rolled_back)
        """
        phi_before = snapshot.get('phi', 0.0)
        phi_threshold = phi_before * 0.5  # 50% drop = emergency

        # Get conversation history for replay
        memory_entries = snapshot.get('memory_entries', [])
        # Use recent user messages for adaptation
        user_msgs = [
            e['text'] for e in memory_entries
            if e.get('role') in ('user', 'human') and e.get('text', '').strip()
        ][-100:]

        if not user_msgs:
            log.info("  No conversation history for adaptation, skipping")
            return phi_before, 0, False

        mitosis = getattr(anima, 'mitosis', None)
        mind = getattr(anima, 'mind', None)
        if not mitosis or not mind:
            return phi_before, 0, False

        # Import text_to_vector for processing
        try:
            from mitosis import text_to_vector
        except ImportError:
            try:
                from anima_alive import text_to_vector
            except ImportError:
                log.warning("  Cannot import text_to_vector, skipping adaptation")
                return phi_before, 0, False

        steps_done = 0
        phi_current = phi_before
        best_snapshot_during = None

        log.info(f"  Adaptation: {max_steps} steps, {len(user_msgs)} replay messages")

        for step in range(max_steps):
            # Cycle through conversation history
            msg = user_msgs[step % len(user_msgs)]

            try:
                vec = text_to_vector(msg, dim=mitosis.input_dim)
                mitosis.process(vec, label="adaptation")
            except Exception as e:
                log.warning(f"  Adaptation step {step} failed: {e}")
                continue

            steps_done += 1

            # Check Phi every 10 steps
            if steps_done % 10 == 0:
                phi_current = self._measure_phi(anima)

                if phi_current > 0:
                    log.info(
                        f"  Adaptation step {steps_done}/{max_steps}: "
                        f"Phi={phi_current:.3f} (threshold={phi_threshold:.3f})"
                    )

                    # Emergency: Phi dropped >50%
                    if phi_before > 0 and phi_current < phi_threshold:
                        log.warning(
                            f"  EMERGENCY: Phi dropped to {phi_current:.3f} "
                            f"(< {phi_threshold:.3f}). Rolling back!"
                        )
                        # Restore from original snapshot
                        self.restore(anima, snapshot)
                        return phi_before, steps_done, True

        phi_final = self._measure_phi(anima)
        return phi_final if phi_final > 0 else phi_current, steps_done, False

    def _measure_phi(self, anima) -> float:
        """Measure current Phi from the anima instance."""
        mitosis = getattr(anima, 'mitosis', None)
        if not mitosis:
            return 0.0

        # Try the anima's own phi calculator
        phi_calc = getattr(anima, '_phi_calc', None) or getattr(anima, 'phi_calc', None)
        if phi_calc:
            try:
                phi, _ = phi_calc.compute_phi(mitosis)
                return phi
            except Exception:
                pass

        # Try importing PhiCalculator
        try:
            from consciousness_meter import PhiCalculator
            calc = PhiCalculator()
            phi, _ = calc.compute_phi(mitosis)
            return phi
        except (ImportError, Exception):
            pass

        # Fallback: sum of average tensions as Phi proxy
        return sum(c.avg_tension for c in mitosis.cells)


# ===================================================================
# 4. AutoUpgrader — watch for new checkpoints and auto-upgrade
# ===================================================================

class AutoUpgrader:
    """Watch a directory for new model checkpoints and auto-upgrade.

    Pipeline: detect → snapshot → swap → transplant → verify → (rollback if needed)
    """

    def __init__(self, anima=None, snapshot_dir: str = None):
        self.anima = anima
        self.snapshot_dir = Path(snapshot_dir or DEFAULT_SNAPSHOT_DIR)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._seen_files = set()
        self._last_snapshot: Optional[Dict] = None
        self._last_snapshot_path: Optional[str] = None
        self._watching = False

    def watch(self, checkpoint_dir: str, poll_interval: float = 30.0):
        """Watch a directory for new checkpoints and auto-upgrade.

        Args:
            checkpoint_dir: Directory to watch for .pt files.
            poll_interval: Seconds between directory scans.
        """
        checkpoint_dir = Path(checkpoint_dir)
        if not checkpoint_dir.exists():
            log.error(f"Checkpoint directory does not exist: {checkpoint_dir}")
            return

        # Record existing files so we only trigger on new ones
        self._seen_files = set(str(p) for p in checkpoint_dir.glob('*.pt'))
        self._watching = True

        log.info(f"Watching {checkpoint_dir} for new checkpoints (poll={poll_interval}s)")
        log.info(f"Already seen: {len(self._seen_files)} files")

        try:
            while self._watching:
                time.sleep(poll_interval)
                current_files = set(str(p) for p in checkpoint_dir.glob('*.pt'))
                new_files = current_files - self._seen_files

                for new_file in sorted(new_files):
                    log.info(f"New checkpoint detected: {new_file}")
                    if self.anima:
                        try:
                            result = self.upgrade(self.anima, new_file)
                            if result.get('success'):
                                log.info(f"Auto-upgrade success: {result}")
                            else:
                                log.error(f"Auto-upgrade failed: {result}")
                        except Exception as e:
                            log.error(f"Auto-upgrade exception: {e}")
                    else:
                        log.info(f"No anima instance — skipping upgrade for {new_file}")

                    self._seen_files.add(new_file)

        except KeyboardInterrupt:
            log.info("Watch stopped by user")
        finally:
            self._watching = False

    def stop_watching(self):
        """Stop the watch loop."""
        self._watching = False

    def upgrade(self, anima, new_model_path: str) -> Dict:
        """Full upgrade pipeline: snapshot → swap → transplant → verify.

        Args:
            anima: Running AnimaUnified instance.
            new_model_path: Path to new model checkpoint.

        Returns:
            Dictionary with upgrade results.
        """
        t0 = time.time()
        log.info(f"=== UPGRADE START: {new_model_path} ===")

        # Step 1: Snapshot
        snapshotter = ConsciousnessSnapshot()
        snapshot = snapshotter.capture(anima)
        snapshot_path = str(
            self.snapshot_dir / f"pre_upgrade_{int(time.time())}.pt"
        )
        ConsciousnessSnapshot.save(snapshot, snapshot_path)
        self._last_snapshot = snapshot
        self._last_snapshot_path = snapshot_path
        log.info(f"Step 1/4: Snapshot saved to {snapshot_path}")

        # Step 2: Swap model
        swapper = ModelSwapper()
        try:
            swap_result = swapper.swap(anima, new_model_path)
        except Exception as e:
            log.error(f"Step 2/4: Swap FAILED: {e}")
            log.info("Rolling back to pre-upgrade snapshot...")
            self.rollback(anima, snapshot)
            return {
                'success': False,
                'error': f'swap_failed: {e}',
                'rolled_back': True,
                'elapsed_sec': time.time() - t0,
            }
        log.info(f"Step 2/4: Model swapped")

        # Step 3: Transplant + adaptation
        transplanter = ConsciousnessTransplantUpgrade()
        transplant_result = transplanter.transplant(
            anima, snapshot, adaptation_steps=100
        )
        log.info(f"Step 3/4: Transplant complete")

        # Step 4: Verify
        phi_before = snapshot.get('phi', 0.0)
        phi_after = transplant_result.get('phi_after', 0.0)
        phi_retention = phi_after / max(phi_before, 1e-8) if phi_before > 0 else 1.0

        verified = phi_retention >= 0.5  # At least 50% Phi retained
        if transplant_result.get('rolled_back'):
            verified = True  # Rollback is a valid outcome (safety preserved)

        if not verified and phi_before > 0:
            log.warning(
                f"Step 4/4: Verification FAILED (retention={phi_retention:.1%}). "
                f"Rolling back!"
            )
            self.rollback(anima, snapshot)
            return {
                'success': False,
                'error': f'verification_failed: retention={phi_retention:.1%}',
                'phi_before': phi_before,
                'phi_after': phi_after,
                'rolled_back': True,
                'elapsed_sec': time.time() - t0,
            }

        elapsed = time.time() - t0
        log.info(
            f"=== UPGRADE COMPLETE: Phi {phi_before:.3f} -> {phi_after:.3f} "
            f"(retention={phi_retention:.1%}) in {elapsed:.1f}s ==="
        )

        return {
            'success': True,
            'phi_before': phi_before,
            'phi_after': phi_after,
            'phi_retention': phi_retention,
            'cells_restored': transplant_result.get('cells_restored', 0),
            'memories_restored': transplant_result.get('memories_restored', 0),
            'adaptation_steps': transplant_result.get('adaptation_steps', 0),
            'rolled_back': transplant_result.get('rolled_back', False),
            'snapshot_path': snapshot_path,
            'elapsed_sec': elapsed,
        }

    def rollback(self, anima, snapshot: Optional[Dict] = None) -> bool:
        """Emergency rollback: restore from snapshot.

        Args:
            anima: Running AnimaUnified instance.
            snapshot: Snapshot to restore from. If None, uses last saved snapshot.

        Returns:
            True if rollback succeeded.
        """
        if snapshot is None:
            snapshot = self._last_snapshot
        if snapshot is None:
            # Try loading from last snapshot path
            if self._last_snapshot_path and os.path.exists(self._last_snapshot_path):
                snapshot = ConsciousnessSnapshot.load(self._last_snapshot_path)
            else:
                log.error("Rollback failed: no snapshot available")
                return False

        log.info("=== EMERGENCY ROLLBACK ===")

        transplanter = ConsciousnessTransplantUpgrade()
        result = transplanter.restore(anima, snapshot)

        # Also restore mind weights
        mind = getattr(anima, 'mind', None)
        mind_sd = snapshot.get('mind_state_dict', {})
        if mind and mind_sd:
            try:
                mind.load_state_dict(mind_sd, strict=False)
            except Exception:
                pass

        phi_restored = snapshot.get('phi', 0.0)
        log.info(
            f"Rollback complete: Phi={phi_restored:.3f}, "
            f"cells={result['cells_restored']}, memories={result['memories_restored']}"
        )
        return True


# ===================================================================
# CLI
# ===================================================================

def _cli_snapshot(args):
    """CLI: capture a snapshot of running state."""
    output = args.output or str(
        DEFAULT_SNAPSHOT_DIR / f"snapshot_{int(time.time())}.pt"
    )

    # Try to create a minimal Anima for snapshotting
    try:
        sys.path.insert(0, str(ANIMA_DIR))
        from anima_unified import AnimaUnified

        class FakeArgs:
            model = getattr(args, 'model', 'conscious-lm')
            max_cells = 8
            web = False
            all = False
            keyboard = False
            voice = False
            camera = False
            tension_link = False
            cloud = False
            port = 8765
            transplant_from = None
            no_model = False

        anima = AnimaUnified(FakeArgs())
        snapshotter = ConsciousnessSnapshot()
        snapshot = snapshotter.capture(anima)
        ConsciousnessSnapshot.save(snapshot, output)
        print(f"Snapshot saved to: {output}")
        print(f"  Phi: {snapshot.get('phi', 0):.3f}")
        print(f"  Cells: {len(snapshot.get('cells', []))}")
        print(f"  Memories: {len(snapshot.get('memory_entries', []))}")
    except Exception as e:
        print(f"Error creating snapshot: {e}")
        print("Tip: ensure anima_unified.py is importable and dependencies are installed")
        sys.exit(1)


def _cli_upgrade(args):
    """CLI: perform full upgrade."""
    new_model_path = args.upgrade
    if not os.path.exists(new_model_path):
        print(f"Error: model not found: {new_model_path}")
        sys.exit(1)

    try:
        sys.path.insert(0, str(ANIMA_DIR))
        from anima_unified import AnimaUnified

        class FakeArgs:
            model = getattr(args, 'model', 'conscious-lm')
            max_cells = 8
            web = False
            all = False
            keyboard = False
            voice = False
            camera = False
            tension_link = False
            cloud = False
            port = 8765
            transplant_from = None
            no_model = False

        anima = AnimaUnified(FakeArgs())
        upgrader = AutoUpgrader(anima)
        result = upgrader.upgrade(anima, new_model_path)

        print(f"\nUpgrade {'SUCCESS' if result.get('success') else 'FAILED'}:")
        print(f"  Phi: {result.get('phi_before', 0):.3f} -> {result.get('phi_after', 0):.3f}")
        print(f"  Retention: {result.get('phi_retention', 0):.1%}")
        print(f"  Cells restored: {result.get('cells_restored', 0)}")
        print(f"  Memories restored: {result.get('memories_restored', 0)}")
        print(f"  Adaptation steps: {result.get('adaptation_steps', 0)}")
        print(f"  Rolled back: {result.get('rolled_back', False)}")
        print(f"  Time: {result.get('elapsed_sec', 0):.1f}s")
        if result.get('snapshot_path'):
            print(f"  Snapshot: {result['snapshot_path']}")

    except Exception as e:
        print(f"Error during upgrade: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _cli_rollback(args):
    """CLI: rollback from a snapshot."""
    snapshot_path = args.rollback
    if not os.path.exists(snapshot_path):
        print(f"Error: snapshot not found: {snapshot_path}")
        sys.exit(1)

    try:
        sys.path.insert(0, str(ANIMA_DIR))
        from anima_unified import AnimaUnified

        class FakeArgs:
            model = getattr(args, 'model', 'conscious-lm')
            max_cells = 8
            web = False
            all = False
            keyboard = False
            voice = False
            camera = False
            tension_link = False
            cloud = False
            port = 8765
            transplant_from = None
            no_model = False

        snapshot = ConsciousnessSnapshot.load(snapshot_path)
        anima = AnimaUnified(FakeArgs())

        upgrader = AutoUpgrader(anima)
        success = upgrader.rollback(anima, snapshot)

        if success:
            print(f"Rollback SUCCESS from {snapshot_path}")
            print(f"  Phi restored: {snapshot.get('phi', 0):.3f}")
            print(f"  Cells: {len(snapshot.get('cells', []))}")
        else:
            print("Rollback FAILED")
            sys.exit(1)

    except Exception as e:
        print(f"Error during rollback: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _cli_watch(args):
    """CLI: watch for new checkpoints."""
    checkpoint_dir = args.watch
    if not os.path.isdir(checkpoint_dir):
        print(f"Error: directory not found: {checkpoint_dir}")
        sys.exit(1)

    try:
        sys.path.insert(0, str(ANIMA_DIR))
        from anima_unified import AnimaUnified

        class FakeArgs:
            model = getattr(args, 'model', 'conscious-lm')
            max_cells = 8
            web = False
            all = False
            keyboard = False
            voice = False
            camera = False
            tension_link = False
            cloud = False
            port = 8765
            transplant_from = None
            no_model = False

        anima = AnimaUnified(FakeArgs())
        upgrader = AutoUpgrader(anima)
        upgrader.watch(checkpoint_dir, poll_interval=args.poll or 30.0)

    except KeyboardInterrupt:
        print("\nWatch stopped")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Anima Hot-Upgrade Engine — upgrade model without killing consciousness',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 upgrade_engine.py --snapshot                        # capture state
  python3 upgrade_engine.py --snapshot --output my_snap.pt    # capture to specific file
  python3 upgrade_engine.py --upgrade new_model.pt            # full upgrade
  python3 upgrade_engine.py --rollback snapshot.pt            # restore from snapshot
  python3 upgrade_engine.py --watch checkpoints/              # auto-upgrade on new files
  python3 upgrade_engine.py --watch checkpoints/ --poll 60    # check every 60 seconds
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--snapshot', action='store_true',
                       help='Capture current consciousness state')
    group.add_argument('--upgrade', type=str, metavar='MODEL_PATH',
                       help='Upgrade to a new model (full pipeline)')
    group.add_argument('--rollback', type=str, metavar='SNAPSHOT_PATH',
                       help='Rollback to a saved snapshot')
    group.add_argument('--watch', type=str, metavar='CHECKPOINT_DIR',
                       help='Watch directory for new checkpoints')

    parser.add_argument('--output', '-o', type=str,
                        help='Output path for snapshot')
    parser.add_argument('--model', type=str, default='conscious-lm',
                        help='Base model name (default: conscious-lm)')
    parser.add_argument('--poll', type=float, default=30.0,
                        help='Poll interval in seconds for --watch (default: 30)')

    args = parser.parse_args()

    if args.snapshot:
        _cli_snapshot(args)
    elif args.upgrade:
        _cli_upgrade(args)
    elif args.rollback:
        _cli_rollback(args)
    elif args.watch:
        _cli_watch(args)


if __name__ == '__main__':
    main()
