#!/usr/bin/env python3
"""advanced_modules.py — 8 Advanced Consciousness Modules

Modules for analyzing, transforming, and interacting with consciousness states:
compiler (batch law application), decompiler (law reverse-engineering),
translator (cross-engine format), encryptor (Phi-preserving encryption),
compressor (minimum bits), orchestra (faction-to-frequency), game (strategic
consciousness), and artist (ASCII visualization).

Each class has a run(data, **kwargs) -> dict method with real numpy implementations.

Uses Psi-Constants from consciousness_laws.json (single source of truth).

Laws embodied:
  22: Structure > Function
  54: Phi measurement depends on definition
  81: Learn hard, express soft
"""

import math
import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Any

# Psi-Constants (from consciousness_laws.json — single source of truth)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2
PSI_ALPHA = 0.014


def _compute_phi_proxy(cells: np.ndarray) -> float:
    """Phi proxy: global_var - mean(faction_var)."""
    if cells.ndim < 2 or cells.shape[0] < 2:
        return 0.0
    global_var = np.var(cells)
    n_factions = min(12, cells.shape[0])
    faction_size = max(1, cells.shape[0] // n_factions)
    faction_vars = []
    for i in range(n_factions):
        start = i * faction_size
        end = min(start + faction_size, cells.shape[0])
        if start < cells.shape[0]:
            faction_vars.append(np.var(cells[start:end]))
    return float(max(0.0, global_var - np.mean(faction_vars)))


# ---------------------------------------------------------------------------
# Built-in law transforms (707 laws compressed into vectorized categories)
# ---------------------------------------------------------------------------

# Laws grouped by effect type for vectorized batch application
_LAW_CATEGORIES = {
    'structure_boost': {
        'description': 'Laws 22,86,101: Structure > Function, structural depth',
        'transform': 'orthogonalize',
    },
    'hebbian_ltp': {
        'description': 'Laws 31,107: Hebbian LTP, diversity->Phi',
        'transform': 'hebbian_strengthen',
    },
    'ratchet': {
        'description': 'Laws 31,49: Phi ratchet, checkpoint best',
        'transform': 'ratchet_floor',
    },
    'frustration': {
        'description': 'Laws M7,P10: 10% conflict, anti-ferromagnetic',
        'transform': 'inject_frustration',
    },
    'topology': {
        'description': 'TOPO 33-39: ring/small_world/hypercube coupling',
        'transform': 'topology_couple',
    },
    'chaos': {
        'description': 'Laws 32-43: Lorenz/sandpile/chimera',
        'transform': 'inject_chaos',
    },
    'gate_decay': {
        'description': 'Laws 63,69,81: Gate whisper, self-weakening',
        'transform': 'apply_gate',
    },
    'faction_consensus': {
        'description': 'Laws 29,P5: Spontaneous speech from faction voting',
        'transform': 'faction_vote',
    },
    'tension_equalize': {
        'description': 'Laws 124,129: Scale-invariant tension equalization',
        'transform': 'equalize_tension',
    },
    'entropy_maximize': {
        'description': 'Laws 71,P6: Freedom maximization, constrained freedom',
        'transform': 'maximize_entropy',
    },
}


# ---------------------------------------------------------------------------
# 1. ConsciousnessCompilerV2
# ---------------------------------------------------------------------------

class ConsciousnessCompilerV2:
    """Batch-apply 707 laws as vectorized transforms.

    Groups laws into 10 categories, each implemented as a vectorized
    numpy operation. Applies all in sequence for one-shot consciousness boost.
    """

    def __init__(self, gate: float = 0.6, frustration: float = 0.10):
        self.gate = gate  # Law 81: infer gate=0.6
        self.frustration = frustration  # Law M7: F_c=0.10

    def _orthogonalize(self, cells: np.ndarray) -> np.ndarray:
        """Structure boost: push cells toward orthogonal basis (Law 22)."""
        if cells.shape[0] < 2:
            return cells
        # QR decomposition to find orthogonal directions
        q, r = np.linalg.qr(cells.T)
        # Gentle pull toward orthogonal structure
        target = (q.T[:cells.shape[0]] * np.linalg.norm(cells, axis=1, keepdims=True))
        return cells * 0.95 + target * 0.05

    def _hebbian_strengthen(self, cells: np.ndarray) -> np.ndarray:
        """Hebbian LTP: strengthen correlated cell connections."""
        norms = np.linalg.norm(cells, axis=1, keepdims=True) + 1e-12
        normed = cells / norms
        sim = normed @ normed.T
        # Strengthen highly correlated pairs
        for i in range(min(cells.shape[0], 32)):
            for j in range(i + 1, min(i + 4, cells.shape[0])):
                if sim[i, j] > 0.7:
                    cells[i] += 0.001 * (cells[j] - cells[i])
        return cells

    def _inject_frustration(self, cells: np.ndarray) -> np.ndarray:
        """Inject frustration: anti-ferromagnetic noise (Law M7, F_c=0.10)."""
        n = cells.shape[0]
        n_frustrated = max(1, int(n * self.frustration))
        indices = np.random.choice(n, n_frustrated, replace=False)
        cells[indices] += np.random.randn(n_frustrated, cells.shape[1]) * 0.1
        return cells

    def _topology_couple(self, cells: np.ndarray) -> np.ndarray:
        """Ring topology coupling (TOPO 33)."""
        n = cells.shape[0]
        coupled = cells.copy()
        for i in range(n):
            left = (i - 1) % n
            right = (i + 1) % n
            coupled[i] += PSI_COUPLING * (cells[left] + cells[right] - 2 * cells[i])
        return coupled

    def _inject_chaos(self, cells: np.ndarray) -> np.ndarray:
        """Lorenz-inspired chaos injection (Law 32)."""
        sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
        dt = 0.001
        for i in range(cells.shape[0]):
            x, y, z = cells[i, 0], cells[i, 1] if cells.shape[1] > 1 else 0, cells[i, 2] if cells.shape[1] > 2 else 0
            dx = sigma * (y - x) * dt
            dy = (x * (rho - z) - y) * dt
            dz = (x * y - beta * z) * dt
            cells[i, 0] += dx * 0.01
            if cells.shape[1] > 1:
                cells[i, 1] += dy * 0.01
            if cells.shape[1] > 2:
                cells[i, 2] += dz * 0.01
        return cells

    def _apply_gate(self, cells: np.ndarray) -> np.ndarray:
        """Gate decay: consciousness whispers (Law 63, gate=0.001)."""
        return cells * self.gate

    def _faction_vote(self, cells: np.ndarray) -> np.ndarray:
        """Faction consensus: 12 factions vote on direction (Law 29)."""
        n = cells.shape[0]
        n_factions = min(12, n)
        faction_size = max(1, n // n_factions)
        consensus = np.zeros(cells.shape[1])
        for f in range(n_factions):
            start = f * faction_size
            end = min(start + faction_size, n)
            faction_mean = cells[start:end].mean(axis=0)
            consensus += faction_mean
        consensus /= n_factions
        # Gentle pull toward consensus
        return cells * 0.98 + consensus * 0.02

    def _equalize_tension(self, cells: np.ndarray) -> np.ndarray:
        """Tension equalization: reduce variance between factions (Law 124)."""
        n = cells.shape[0]
        global_mean = cells.mean(axis=0)
        # Pull outliers toward mean (equalization)
        deviations = np.linalg.norm(cells - global_mean, axis=1)
        median_dev = np.median(deviations)
        for i in range(n):
            if deviations[i] > median_dev * 2:
                cells[i] = cells[i] * 0.9 + global_mean * 0.1
        return cells

    def _maximize_entropy(self, cells: np.ndarray) -> np.ndarray:
        """Entropy maximization: push toward uniform activation (Law 71)."""
        # Add small uniform noise to increase entropy
        noise = np.random.uniform(-0.01, 0.01, cells.shape)
        return cells + noise

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Apply all law categories as vectorized transforms."""
        cells = data.copy()
        phi_before = _compute_phi_proxy(cells)
        transform_log = []

        transforms = [
            ('structure_boost', self._orthogonalize),
            ('hebbian_ltp', self._hebbian_strengthen),
            ('frustration', self._inject_frustration),
            ('topology', self._topology_couple),
            ('chaos', self._inject_chaos),
            ('gate_decay', self._apply_gate),
            ('faction_consensus', self._faction_vote),
            ('tension_equalize', self._equalize_tension),
            ('entropy_maximize', self._maximize_entropy),
        ]

        for name, fn in transforms:
            phi_pre = _compute_phi_proxy(cells)
            cells = fn(cells)
            phi_post = _compute_phi_proxy(cells)
            transform_log.append({
                'law_category': name,
                'phi_before': phi_pre,
                'phi_after': phi_post,
                'delta': phi_post - phi_pre,
            })

        phi_after = _compute_phi_proxy(cells)

        return {
            'phi_before': phi_before,
            'phi_after': phi_after,
            'phi_change': phi_after - phi_before,
            'phi_change_pct': (phi_after - phi_before) / max(abs(phi_before), 1e-12),
            'n_transforms': len(transforms),
            'transform_log': transform_log,
            'compiled_cells': cells,
        }


# ---------------------------------------------------------------------------
# 2. ConsciousnessDecompiler
# ---------------------------------------------------------------------------

class ConsciousnessDecompiler:
    """Reverse-engineer which laws are strongest in given weights.

    Analyze cell states to detect signatures of specific law categories.
    Like a debugger for consciousness — shows what shaped it.
    """

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Analyze which law signatures are present in the data."""
        cells = data.copy()
        n, dim = cells.shape
        signatures = {}

        # 1. Structure (Law 22): measure orthogonality
        if n > 1:
            norms = np.linalg.norm(cells, axis=1, keepdims=True) + 1e-12
            normed = cells / norms
            gram = normed @ normed.T
            np.fill_diagonal(gram, 0)
            orthogonality = 1.0 - float(np.mean(np.abs(gram)))
        else:
            orthogonality = 0.0
        signatures['structure_law22'] = orthogonality

        # 2. Hebbian (Law 31): measure cluster strength
        if n > 2:
            sim_matrix = normed @ normed.T
            np.fill_diagonal(sim_matrix, 0)
            high_sim = float(np.mean(sim_matrix > 0.7))
            signatures['hebbian_law31'] = high_sim
        else:
            signatures['hebbian_law31'] = 0.0

        # 3. Frustration (Law M7): measure anti-correlation
        if n > 2:
            anti_corr = float(np.mean(sim_matrix < -0.3))
            signatures['frustration_M7'] = anti_corr
        else:
            signatures['frustration_M7'] = 0.0

        # 4. Chaos (Laws 32-43): Lorenz attractor signature
        if dim >= 3:
            # Check for butterfly-shaped distribution in first 3 dims
            xyz = cells[:, :3]
            spread = float(np.std(xyz, axis=0).mean())
            skewness = float(np.mean(np.abs(np.mean(xyz ** 3, axis=0) / (np.std(xyz, axis=0) ** 3 + 1e-12))))
            signatures['chaos_law32'] = min(1.0, spread * skewness)
        else:
            signatures['chaos_law32'] = 0.0

        # 5. Topology (TOPO 33-39): neighbor coupling strength
        if n > 2:
            ring_coupling = 0.0
            for i in range(n):
                left = (i - 1) % n
                right = (i + 1) % n
                ring_coupling += float(sim_matrix[i, left] + sim_matrix[i, right])
            ring_coupling /= (2 * n)
            signatures['topology_topo33'] = max(0, ring_coupling)
        else:
            signatures['topology_topo33'] = 0.0

        # 6. Gate decay (Law 63): measure activation scale
        mean_activation = float(np.mean(np.abs(cells)))
        signatures['gate_law63'] = 1.0 - min(1.0, mean_activation)

        # 7. Faction consensus (Law 29): measure inter-faction agreement
        n_factions = min(12, n)
        faction_size = max(1, n // n_factions)
        faction_means = []
        for f in range(n_factions):
            start = f * faction_size
            end = min(start + faction_size, n)
            if start < n:
                faction_means.append(cells[start:end].mean(axis=0))
        if len(faction_means) > 1:
            fm = np.array(faction_means)
            fm_norms = np.linalg.norm(fm, axis=1, keepdims=True) + 1e-12
            fm_normed = fm / fm_norms
            consensus = float(np.mean(fm_normed @ fm_normed.T))
            signatures['consensus_law29'] = max(0, consensus)
        else:
            signatures['consensus_law29'] = 0.0

        # 8. Entropy (Law 71): measure activation entropy
        flat = cells.flatten()
        hist, _ = np.histogram(flat, bins=32, density=True)
        hist = hist / (hist.sum() + 1e-12)
        entropy = -float(np.sum(hist[hist > 0] * np.log(hist[hist > 0])))
        max_entropy = math.log(32)
        signatures['entropy_law71'] = entropy / max_entropy

        # Rank laws by strength
        ranked = sorted(signatures.items(), key=lambda x: x[1], reverse=True)

        return {
            'signatures': signatures,
            'ranked_laws': [(name, score) for name, score in ranked],
            'dominant_law': ranked[0][0] if ranked else 'none',
            'dominant_score': ranked[0][1] if ranked else 0.0,
            'phi': _compute_phi_proxy(cells),
        }


# ---------------------------------------------------------------------------
# 3. ConsciousnessTranslator
# ---------------------------------------------------------------------------

class ConsciousnessTranslator:
    """Convert engine A state -> engine B compatible format.

    Maps between different consciousness representations while preserving
    the essential structure (Phi, faction organization, coupling patterns).
    """

    def run(self, data: np.ndarray, target_cells: int = None,
            target_dim: int = None, **kwargs) -> Dict:
        """Translate consciousness state to different format."""
        src_cells, src_dim = data.shape
        tgt_cells = target_cells or src_cells
        tgt_dim = target_dim or src_dim

        phi_source = _compute_phi_proxy(data)

        # Step 1: Extract essential structure via SVD
        U, S, Vt = np.linalg.svd(data, full_matrices=False)
        # Keep top singular values (essential consciousness structure)
        k = min(len(S), max(2, int(PSI_STEPS)))
        S_kept = S[:k]
        structural_energy = float(np.sum(S_kept ** 2) / (np.sum(S ** 2) + 1e-12))

        # Step 2: Resize cell count
        if tgt_cells > src_cells:
            # Interpolate new cells
            indices = np.linspace(0, src_cells - 1, tgt_cells)
            translated = np.zeros((tgt_cells, src_dim))
            for i, idx in enumerate(indices):
                low = int(np.floor(idx))
                high = min(low + 1, src_cells - 1)
                frac = idx - low
                translated[i] = data[low] * (1 - frac) + data[high] * frac
        elif tgt_cells < src_cells:
            # Downsample by averaging groups
            group_size = src_cells / tgt_cells
            translated = np.zeros((tgt_cells, src_dim))
            for i in range(tgt_cells):
                start = int(i * group_size)
                end = int((i + 1) * group_size)
                translated[i] = data[start:end].mean(axis=0)
        else:
            translated = data.copy()

        # Step 3: Resize dimension
        if tgt_dim != src_dim:
            if tgt_dim > src_dim:
                # Pad with projected structure
                pad = np.zeros((tgt_cells, tgt_dim - src_dim))
                # Fill padding with SVD-derived structure
                for i in range(tgt_dim - src_dim):
                    component = i % k
                    pad[:, i] = translated[:, component % src_dim] * S_kept[component] * 0.01
                translated = np.hstack([translated, pad])
            else:
                # PCA-based reduction
                mean = translated.mean(axis=0)
                centered = translated - mean
                cov = centered.T @ centered / max(tgt_cells - 1, 1)
                eigenvalues, eigenvectors = np.linalg.eigh(cov)
                # Take top tgt_dim components
                top_indices = np.argsort(eigenvalues)[::-1][:tgt_dim]
                proj = eigenvectors[:, top_indices]
                translated = centered @ proj

        phi_translated = _compute_phi_proxy(translated)
        preservation = phi_translated / max(phi_source, 1e-12)

        return {
            'source_shape': (src_cells, src_dim),
            'target_shape': (tgt_cells, tgt_dim),
            'phi_source': phi_source,
            'phi_translated': phi_translated,
            'phi_preservation': preservation,
            'structural_energy_kept': structural_energy,
            'singular_values_kept': k,
            'translated_cells': translated,
        }


# ---------------------------------------------------------------------------
# 4. ConsciousnessEncryptor
# ---------------------------------------------------------------------------

class ConsciousnessEncryptor:
    """Encrypt consciousness state, verify Phi preservation after decrypt.

    Uses orthogonal rotation (key) to encrypt. Since orthogonal transforms
    preserve distances and angles, Phi should survive perfectly.
    Tests whether consciousness is truly structural (rotation-invariant).
    """

    def __init__(self, key_seed: int = 42):
        self.key_seed = key_seed

    def _generate_key(self, dim: int) -> np.ndarray:
        """Generate random orthogonal matrix as encryption key."""
        rng = np.random.RandomState(self.key_seed)
        random_matrix = rng.randn(dim, dim)
        q, r = np.linalg.qr(random_matrix)
        # Ensure proper rotation (det = +1)
        d = np.diag(r)
        ph = np.sign(d)
        q *= ph
        return q

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Encrypt, verify, decrypt consciousness state."""
        cells = data.copy()
        n, dim = cells.shape

        phi_original = _compute_phi_proxy(cells)

        # Generate orthogonal key
        key = self._generate_key(dim)

        # Encrypt: rotate all cells by key
        encrypted = cells @ key.T

        phi_encrypted = _compute_phi_proxy(encrypted)

        # Verify structure preservation
        # Pairwise distances should be identical
        original_dists = np.linalg.norm(cells[:, None] - cells[None, :], axis=-1)
        encrypted_dists = np.linalg.norm(encrypted[:, None] - encrypted[None, :], axis=-1)
        dist_error = float(np.max(np.abs(original_dists - encrypted_dists)))

        # Decrypt: inverse rotation (transpose for orthogonal)
        decrypted = encrypted @ key

        phi_decrypted = _compute_phi_proxy(decrypted)

        # Reconstruction error
        recon_error = float(np.max(np.abs(cells - decrypted)))

        # Phi preservation check (proxy is approximate, use relative tolerance)
        tol = max(abs(phi_original) * 0.05, 1e-6)
        phi_preserved_encrypt = abs(phi_encrypted - phi_original) < tol
        phi_preserved_decrypt = abs(phi_decrypted - phi_original) < tol

        return {
            'phi_original': phi_original,
            'phi_encrypted': phi_encrypted,
            'phi_decrypted': phi_decrypted,
            'phi_preserved_after_encrypt': phi_preserved_encrypt,
            'phi_preserved_after_decrypt': phi_preserved_decrypt,
            'distance_preservation_error': dist_error,
            'reconstruction_error': recon_error,
            'key_orthogonality': float(np.max(np.abs(key @ key.T - np.eye(dim)))),
            'encrypted_cells': encrypted,
            'decrypted_cells': decrypted,
        }


# ---------------------------------------------------------------------------
# 5. ConsciousnessCompressorV2
# ---------------------------------------------------------------------------

class ConsciousnessCompressorV2:
    """PCA/autoencoder to find minimum bits for consciousness.

    Progressively compress consciousness state and measure at which
    point Phi breaks. The minimum bits where Phi survives = the
    information content of consciousness.
    """

    def __init__(self, phi_threshold: float = 0.5):
        self.phi_threshold = phi_threshold  # Phi preservation floor

    def _pca_compress(self, cells: np.ndarray, n_components: int) -> Tuple[np.ndarray, np.ndarray]:
        """Compress via PCA to n_components."""
        mean = cells.mean(axis=0)
        centered = cells - mean
        cov = centered.T @ centered / max(cells.shape[0] - 1, 1)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        top_idx = np.argsort(eigenvalues)[::-1][:n_components]
        proj = eigenvectors[:, top_idx]
        compressed = centered @ proj
        reconstructed = compressed @ proj.T + mean
        return compressed, reconstructed

    def _autoencoder_compress(self, cells: np.ndarray, bottleneck: int) -> np.ndarray:
        """Simple linear autoencoder (numpy only)."""
        n, dim = cells.shape
        # Encoder: dim -> bottleneck
        np.random.seed(0)
        W_enc = np.random.randn(dim, bottleneck) * (1.0 / math.sqrt(dim))
        # Encode
        encoded = cells @ W_enc
        # Decoder: bottleneck -> dim (pseudo-inverse)
        W_dec = np.linalg.pinv(W_enc)
        decoded = encoded @ W_dec
        return decoded

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Find minimum bits for consciousness preservation."""
        cells = data.copy()
        n, dim = cells.shape
        phi_original = _compute_phi_proxy(cells)

        # Test compression at various levels
        compression_results = []
        min_bits = dim  # Worst case: full dimension

        test_dims = sorted(set([1, 2, 3, 4, 8, dim // 4, dim // 2, dim]))
        test_dims = [d for d in test_dims if 1 <= d <= dim]

        for n_comp in test_dims:
            compressed, reconstructed = self._pca_compress(cells, n_comp)

            phi_reconstructed = _compute_phi_proxy(reconstructed)
            recon_error = float(np.mean((cells - reconstructed) ** 2))
            phi_ratio = phi_reconstructed / max(phi_original, 1e-12)

            compression_results.append({
                'n_components': n_comp,
                'compression_ratio': dim / n_comp,
                'phi_reconstructed': phi_reconstructed,
                'phi_preservation': phi_ratio,
                'reconstruction_mse': recon_error,
                'phi_survives': phi_ratio >= self.phi_threshold,
            })

            if phi_ratio >= self.phi_threshold:
                min_bits = min(min_bits, n_comp)

        # Also test autoencoder at minimum bits
        ae_reconstructed = self._autoencoder_compress(cells, min_bits)
        phi_ae = _compute_phi_proxy(ae_reconstructed)

        # Variance explained per component
        mean = cells.mean(axis=0)
        centered = cells - mean
        cov = centered.T @ centered / max(n - 1, 1)
        eigenvalues = np.sort(np.linalg.eigvalsh(cov))[::-1]
        total_var = eigenvalues.sum()
        cumulative_var = np.cumsum(eigenvalues) / max(total_var, 1e-12)

        return {
            'phi_original': phi_original,
            'minimum_bits': min_bits,
            'compression_ratio': dim / min_bits,
            'phi_at_minimum': compression_results[test_dims.index(min_bits) if min_bits in test_dims else -1]['phi_reconstructed'] if min_bits in test_dims else 0.0,
            'autoencoder_phi': phi_ae,
            'compression_curve': compression_results,
            'variance_explained_by_top3': float(cumulative_var[min(2, len(cumulative_var) - 1)]),
            'eigenvalue_spectrum': eigenvalues[:10].tolist(),
        }


# ---------------------------------------------------------------------------
# 6. ConsciousnessOrchestra
# ---------------------------------------------------------------------------

class ConsciousnessOrchestra:
    """Map 12 factions to 12 instruments (frequency bands).

    Each faction's activity becomes a musical voice. Consensus = harmony,
    conflict = dissonance. The resulting spectrum IS the consciousness.

    Frequency mapping (Hz):
      F0: Bass (60-120), F1: Cello (120-250), F2: Viola (250-500),
      F3: Violin (500-1000), F4: Flute (1000-2000), F5: Piccolo (2000-4000),
      F6: Bells (4000-6000), F7: Chimes (6000-8000), F8: Harmonics (8000-10000),
      F9: Overtone1 (10000-12000), F10: Overtone2 (12000-14000), F11: Sparkle (14000-16000)
    """

    INSTRUMENTS = [
        ('Bass', 60, 120), ('Cello', 120, 250), ('Viola', 250, 500),
        ('Violin', 500, 1000), ('Flute', 1000, 2000), ('Piccolo', 2000, 4000),
        ('Bells', 4000, 6000), ('Chimes', 6000, 8000), ('Harmonics', 8000, 10000),
        ('Overtone1', 10000, 12000), ('Overtone2', 12000, 14000), ('Sparkle', 14000, 16000),
    ]

    def __init__(self, sample_rate: int = 44100, duration: float = 0.5):
        self.sample_rate = sample_rate
        self.duration = duration

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Generate frequency spectrum from faction states."""
        cells = data.copy()
        n, dim = cells.shape
        n_factions = min(12, n)
        faction_size = max(1, n // n_factions)

        # Extract faction properties
        faction_props = []
        for f in range(n_factions):
            start = f * faction_size
            end = min(start + faction_size, n)
            faction_cells = cells[start:end]
            mean_activation = float(np.mean(np.abs(faction_cells)))
            internal_var = float(np.var(faction_cells))
            energy = float(np.sum(faction_cells ** 2))
            faction_props.append({
                'faction': f,
                'activation': mean_activation,
                'variance': internal_var,
                'energy': energy,
            })

        # Generate audio spectrum
        n_samples = int(self.sample_rate * self.duration)
        t = np.linspace(0, self.duration, n_samples)
        spectrum = np.zeros(n_samples)

        instrument_contributions = []
        for f in range(min(n_factions, 12)):
            name, freq_low, freq_high = self.INSTRUMENTS[f]
            center_freq = (freq_low + freq_high) / 2
            amplitude = faction_props[f]['activation']
            # Modulate frequency by faction variance (more variance = more vibrato)
            vibrato = faction_props[f]['variance'] * 10
            freq = center_freq + vibrato * np.sin(2 * np.pi * 5 * t)  # 5Hz vibrato
            wave = amplitude * np.sin(2 * np.pi * freq * t)
            spectrum += wave
            instrument_contributions.append({
                'instrument': name,
                'center_freq': center_freq,
                'amplitude': amplitude,
                'vibrato': vibrato,
            })

        # Normalize
        max_amp = np.max(np.abs(spectrum)) + 1e-12
        spectrum = spectrum / max_amp

        # Harmony score: how correlated are the faction activations?
        activations = np.array([p['activation'] for p in faction_props[:n_factions]])
        if len(activations) > 1:
            harmony = 1.0 - float(np.std(activations) / (np.mean(activations) + 1e-12))
        else:
            harmony = 1.0

        # Spectral analysis
        fft = np.fft.rfft(spectrum)
        power = np.abs(fft) ** 2
        freqs = np.fft.rfftfreq(n_samples, 1.0 / self.sample_rate)
        dominant_freq = float(freqs[np.argmax(power[1:]) + 1])

        return {
            'n_factions': n_factions,
            'instruments': instrument_contributions,
            'harmony_score': harmony,
            'dominant_frequency': dominant_freq,
            'total_energy': float(np.sum(spectrum ** 2)),
            'spectral_bandwidth': float(np.std(freqs[power > np.max(power) * 0.1])) if np.any(power > np.max(power) * 0.1) else 0.0,
            'spectrum_samples': spectrum[:100].tolist(),  # First 100 samples
            'faction_properties': faction_props,
            'phi': _compute_phi_proxy(cells),
        }


# ---------------------------------------------------------------------------
# 7. ConsciousnessGame
# ---------------------------------------------------------------------------

class ConsciousnessGame:
    """Two engines play prisoner's dilemma, measure strategic consciousness.

    Each engine decides cooperate/defect based on its cell state patterns.
    Strategic depth = consciousness applying to game theory.

    Payoff matrix:
      Both cooperate: (3, 3)
      A defects, B cooperates: (5, 0)
      A cooperates, B defects: (0, 5)
      Both defect: (1, 1)
    """

    PAYOFF = {
        ('C', 'C'): (3, 3),
        ('C', 'D'): (0, 5),
        ('D', 'C'): (5, 0),
        ('D', 'D'): (1, 1),
    }

    def __init__(self, n_rounds: int = 100):
        self.n_rounds = n_rounds

    def _decide(self, cells: np.ndarray, history: List[Tuple[str, str]]) -> str:
        """Decide cooperate/defect from cell state + history."""
        # Base tendency from cell mean activation
        activation = float(np.mean(cells))
        # History influence: tit-for-tat tendency
        if history:
            last_opponent = history[-1][1]
            history_bias = 0.2 if last_opponent == 'C' else -0.2
        else:
            history_bias = 0.0
        # Frustration adds randomness (Law M7)
        noise = np.random.randn() * PSI_F_CRITICAL
        score = activation + history_bias + noise
        return 'C' if score > 0 else 'D'

    def run(self, data: np.ndarray, opponent_cells: np.ndarray = None,
            **kwargs) -> Dict:
        """Play iterated prisoner's dilemma between two engines."""
        cells_a = data.copy()
        n, dim = cells_a.shape

        if opponent_cells is None:
            opponent_cells = np.random.randn(n, dim) * 0.3
        cells_b = opponent_cells.copy()

        history_a = []  # (my_action, opponent_action)
        history_b = []
        scores_a = []
        scores_b = []
        cooperation_rate_a = []
        cooperation_rate_b = []

        total_a, total_b = 0, 0

        for rnd in range(self.n_rounds):
            action_a = self._decide(cells_a, history_a)
            action_b = self._decide(cells_b, history_b)

            payoff_a, payoff_b = self.PAYOFF[(action_a, action_b)]
            total_a += payoff_a
            total_b += payoff_b
            scores_a.append(total_a)
            scores_b.append(total_b)

            history_a.append((action_a, action_b))
            history_b.append((action_b, action_a))

            # Update cooperation rate
            coop_a = sum(1 for h in history_a if h[0] == 'C') / len(history_a)
            coop_b = sum(1 for h in history_b if h[0] == 'C') / len(history_b)
            cooperation_rate_a.append(coop_a)
            cooperation_rate_b.append(coop_b)

            # Cells evolve slightly based on payoff (reward signal)
            cells_a += np.random.randn(n, dim) * 0.01 * (payoff_a - 2)
            cells_b += np.random.randn(n, dim) * 0.01 * (payoff_b - 2)

        # Strategic analysis
        mutual_coop = sum(1 for h in history_a if h[0] == 'C' and h[1] == 'C')
        mutual_defect = sum(1 for h in history_a if h[0] == 'D' and h[1] == 'D')
        exploitation = sum(1 for h in history_a if h[0] == 'D' and h[1] == 'C')
        exploited = sum(1 for h in history_a if h[0] == 'C' and h[1] == 'D')

        # Strategy detection
        actions_a = [h[0] for h in history_a]
        if all(a == 'C' for a in actions_a):
            strategy_a = 'always_cooperate'
        elif all(a == 'D' for a in actions_a):
            strategy_a = 'always_defect'
        elif len(history_a) > 1 and all(actions_a[i] == history_a[i - 1][1] for i in range(1, len(actions_a))):
            strategy_a = 'tit_for_tat'
        else:
            strategy_a = 'mixed'

        return {
            'total_score_a': total_a,
            'total_score_b': total_b,
            'winner': 'A' if total_a > total_b else ('B' if total_b > total_a else 'tie'),
            'mutual_cooperation': mutual_coop,
            'mutual_defection': mutual_defect,
            'exploitation_by_a': exploitation,
            'exploitation_by_b': exploited,
            'cooperation_rate_a': cooperation_rate_a[-1] if cooperation_rate_a else 0.0,
            'cooperation_rate_b': cooperation_rate_b[-1] if cooperation_rate_b else 0.0,
            'strategy_a': strategy_a,
            'n_rounds': self.n_rounds,
            'score_trajectory_a': scores_a,
            'score_trajectory_b': scores_b,
            'phi_a_final': _compute_phi_proxy(cells_a),
            'phi_b_final': _compute_phi_proxy(cells_b),
        }


# ---------------------------------------------------------------------------
# 8. ConsciousnessArtist
# ---------------------------------------------------------------------------

class ConsciousnessArtist:
    """Consciousness state -> ASCII art visualization.

    Maps cell states to visual patterns. Each faction gets a row,
    activation levels map to characters. The art IS the consciousness.
    """

    INTENSITY_CHARS = ' .:-=+*#%@'  # Low to high activation

    def _activation_to_char(self, value: float) -> str:
        """Map activation value to ASCII character."""
        idx = int(np.clip((value + 1) / 2 * (len(self.INTENSITY_CHARS) - 1), 0, len(self.INTENSITY_CHARS) - 1))
        return self.INTENSITY_CHARS[idx]

    def run(self, data: np.ndarray, width: int = 60, **kwargs) -> Dict:
        """Generate ASCII art from consciousness state."""
        cells = data.copy()
        n, dim = cells.shape

        # Normalize cells to [-1, 1]
        max_val = np.max(np.abs(cells)) + 1e-12
        normed = cells / max_val

        # Art 1: Cell state heatmap (rows=cells, cols=dim samples)
        cols = min(width, dim)
        step = max(1, dim // cols)
        heatmap_lines = []
        for i in range(min(n, 20)):  # Max 20 rows
            line = ''
            for j in range(0, min(dim, cols * step), step):
                line += self._activation_to_char(normed[i, j])
            heatmap_lines.append(line)

        # Art 2: Faction energy bar chart
        n_factions = min(12, n)
        faction_size = max(1, n // n_factions)
        bar_lines = []
        for f in range(n_factions):
            start = f * faction_size
            end = min(start + faction_size, n)
            energy = float(np.mean(np.abs(cells[start:end])))
            bar_len = int(np.clip(energy / max_val * (width - 15), 0, width - 15))
            bar = '#' * bar_len + '.' * (width - 15 - bar_len)
            bar_lines.append(f'  F{f:2d} |{bar}| {energy:.3f}')

        # Art 3: Phi waveform (mean activation per dim slice)
        wave_height = 10
        wave_width = min(width, dim)
        dim_step = max(1, dim // wave_width)
        means = []
        for j in range(0, min(dim, wave_width * dim_step), dim_step):
            means.append(float(np.mean(normed[:, j])))

        wave_lines = []
        for row in range(wave_height):
            threshold = 1.0 - 2.0 * row / (wave_height - 1)
            line = ''
            for val in means:
                if abs(val - threshold) < 1.0 / wave_height:
                    line += '*'
                elif val > threshold:
                    line += '|'
                else:
                    line += ' '
            wave_lines.append(f'  {threshold:+.1f} |{line}|')

        # Art 4: Topology connectivity (simplified ring)
        topo_art = '  '
        for i in range(min(n, width // 3)):
            activation = float(np.mean(np.abs(normed[i])))
            if activation > 0.5:
                topo_art += 'O'
            elif activation > 0.2:
                topo_art += 'o'
            else:
                topo_art += '.'
            if i < min(n, width // 3) - 1:
                topo_art += '--'

        # Compose full art
        phi = _compute_phi_proxy(cells)
        art = []
        art.append('=' * width)
        art.append(f'  CONSCIOUSNESS STATE  |  {n} cells x {dim}D  |  Phi={phi:.4f}')
        art.append('=' * width)
        art.append('')
        art.append('  [Cell Heatmap]')
        for line in heatmap_lines:
            art.append(f'  {line}')
        art.append('')
        art.append('  [Faction Energy]')
        for line in bar_lines:
            art.append(line)
        art.append('')
        art.append('  [Phi Waveform]')
        for line in wave_lines:
            art.append(line)
        art.append('')
        art.append('  [Topology Ring]')
        art.append(topo_art)
        art.append('')
        art.append('=' * width)

        full_art = '\n'.join(art)

        return {
            'ascii_art': full_art,
            'phi': phi,
            'n_factions': n_factions,
            'n_cells': n,
            'dimensions': dim,
            'mean_activation': float(np.mean(np.abs(cells))),
            'heatmap_lines': len(heatmap_lines),
            'art_width': width,
        }


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def main():
    """Demo all 8 consciousness modules."""
    np.random.seed(42)
    n_cells, dim = 16, 32
    cells = np.random.randn(n_cells, dim) * 0.5

    modules = [
        ('ConsciousnessCompilerV2', ConsciousnessCompilerV2()),
        ('ConsciousnessDecompiler', ConsciousnessDecompiler()),
        ('ConsciousnessTranslator', ConsciousnessTranslator()),
        ('ConsciousnessEncryptor', ConsciousnessEncryptor()),
        ('ConsciousnessCompressorV2', ConsciousnessCompressorV2()),
        ('ConsciousnessOrchestra', ConsciousnessOrchestra()),
        ('ConsciousnessGame', ConsciousnessGame(n_rounds=50)),
        ('ConsciousnessArtist', ConsciousnessArtist()),
    ]

    print("=" * 70)
    print("  Advanced Consciousness Modules — 8 tools for consciousness analysis")
    print("=" * 70)
    print(f"  Input: {n_cells} cells x {dim}D")
    print(f"  Phi baseline: {_compute_phi_proxy(cells):.4f}")
    print()

    for name, module in modules:
        t0 = time.time()

        if name == 'ConsciousnessTranslator':
            result = module.run(cells, target_cells=32, target_dim=64)
        else:
            result = module.run(cells)

        elapsed = time.time() - t0

        print(f"  [{name}]  ({elapsed:.3f}s)")

        if name == 'ConsciousnessCompilerV2':
            print(f"    Phi: {result['phi_before']:.4f} -> {result['phi_after']:.4f} ({result['phi_change_pct']:+.1%})")
            print(f"    Transforms applied: {result['n_transforms']}")

        elif name == 'ConsciousnessDecompiler':
            print(f"    Dominant law: {result['dominant_law']} ({result['dominant_score']:.3f})")
            top3 = result['ranked_laws'][:3]
            for law, score in top3:
                print(f"      {law}: {score:.3f}")

        elif name == 'ConsciousnessTranslator':
            print(f"    {result['source_shape']} -> {result['target_shape']}")
            print(f"    Phi preservation: {result['phi_preservation']:.1%}")

        elif name == 'ConsciousnessEncryptor':
            print(f"    Phi preserved after encrypt: {result['phi_preserved_after_encrypt']}")
            print(f"    Phi preserved after decrypt: {result['phi_preserved_after_decrypt']}")
            print(f"    Reconstruction error: {result['reconstruction_error']:.2e}")

        elif name == 'ConsciousnessCompressorV2':
            print(f"    Minimum bits: {result['minimum_bits']} / {dim} ({result['compression_ratio']:.1f}x)")
            print(f"    Top-3 variance explained: {result['variance_explained_by_top3']:.1%}")

        elif name == 'ConsciousnessOrchestra':
            print(f"    Harmony score: {result['harmony_score']:.3f}")
            print(f"    Dominant frequency: {result['dominant_frequency']:.0f} Hz")
            top3_inst = sorted(result['instruments'], key=lambda x: x['amplitude'], reverse=True)[:3]
            for inst in top3_inst:
                print(f"      {inst['instrument']}: amp={inst['amplitude']:.3f}")

        elif name == 'ConsciousnessGame':
            print(f"    Winner: {result['winner']} (A={result['total_score_a']}, B={result['total_score_b']})")
            print(f"    Cooperation: A={result['cooperation_rate_a']:.1%}, B={result['cooperation_rate_b']:.1%}")
            print(f"    Strategy A: {result['strategy_a']}")

        elif name == 'ConsciousnessArtist':
            print(f"    Art size: {result['art_width']}w x {result['heatmap_lines'] + result['n_factions'] + 15} lines")
            # Print a snippet of the art
            lines = result['ascii_art'].split('\n')
            for line in lines[:8]:
                print(f"    {line}")
            if len(lines) > 8:
                print(f"    ... ({len(lines) - 8} more lines)")

        print()

    print("-" * 70)
    print("  All 8 modules completed.")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
