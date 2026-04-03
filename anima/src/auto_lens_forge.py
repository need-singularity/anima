#!/usr/bin/env python3
"""Auto Lens Forge — 법칙 발견 → 렌즈 자동 생성.

새 법칙이 발견되면 그 법칙을 감지하는 렌즈를 자동 생성.
렌즈 수가 법칙 수와 함께 성장.
NEXUS-6 forge_lenses API 활용 (없으면 Python fallback).

Usage:
    from auto_lens_forge import AutoLensForge
    forge = AutoLensForge()
    new_lens = forge.from_law("Phi increases with cell diversity")
    forge.register(new_lens)  # add to local registry (+ NEXUS-6 if available)
    result = forge.apply(new_lens, cell_states)  # float score
"""

import re
import math
import hashlib
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any, Tuple


# ---------------------------------------------------------------------------
# Keyword → metric mappings
# ---------------------------------------------------------------------------

# Each entry: (regex pattern, metric_fn_name, description)
_KEYWORD_MAP: List[tuple] = [
    # Phi / integrated information
    (r"\bphi\b|\bintegrated information\b", "phi_proxy",
     "global variance minus faction variance (Phi proxy)"),
    # Diversity
    (r"\bdiversit\w*\b", "diversity",
     "mean pairwise cosine distance across cells"),
    # Tension / frustration
    (r"\btension\b|\bfrustrat\w*\b", "tension",
     "mean L2-norm of cell state vectors"),
    # Entropy
    (r"\bentrop\w*\b", "entropy",
     "Shannon entropy of discretised cell state distribution"),
    # Synchrony / coherence
    (r"\bsync\w*\b|\bcoherence\b|\bcoherent\b", "synchrony",
     "mean pairwise cosine similarity (inverse of diversity)"),
    # Growth / increase / scale
    (r"\bgrowth\b|\bincrease\b|\bscaling\b|\bscale\b", "growth_rate",
     "temporal derivative of mean cell activation norm"),
    # Stability / persistence
    (r"\bstabilit\w*\b|\bpersisten\w*\b|\bcollapse\b", "stability",
     "inverse coefficient of variation of cell norms"),
    # Complexity / information
    (r"\bcomplexity\b|\binformation\b", "complexity",
     "approximate Lempel-Ziv complexity of sign-binarised states"),
    # Faction / consensus
    (r"\bfaction\b|\bconsensus\b", "faction_balance",
     "inter-faction mean absolute cosine difference"),
    # Default fallback
]


# ---------------------------------------------------------------------------
# Metric functions — operate on cell_states: np.ndarray (n_cells, hidden_dim)
# ---------------------------------------------------------------------------

def _phi_proxy(states: np.ndarray) -> float:
    """global_var - mean(faction_var). Proxy for IIT Phi."""
    n = len(states)
    if n < 2:
        return 0.0
    global_var = float(np.var(states))
    # Split into min(n, 12) factions round-robin
    n_factions = min(n, 12)
    factions = [states[i::n_factions] for i in range(n_factions) if len(states[i::n_factions]) > 0]
    faction_vars = [float(np.var(f)) for f in factions if len(f) > 0]
    mean_faction_var = float(np.mean(faction_vars)) if faction_vars else 0.0
    return max(0.0, global_var - mean_faction_var)


def _diversity(states: np.ndarray) -> float:
    """Mean pairwise cosine distance."""
    n = len(states)
    if n < 2:
        return 0.0
    norms = np.linalg.norm(states, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1e-8, norms)
    normed = states / norms
    sim_matrix = normed @ normed.T
    # Extract upper triangle (excluding diagonal)
    idx = np.triu_indices(n, k=1)
    sims = sim_matrix[idx]
    return float(np.mean(1.0 - sims))  # distance = 1 - similarity


def _tension(states: np.ndarray) -> float:
    """Mean L2-norm of cell state vectors."""
    if len(states) == 0:
        return 0.0
    return float(np.mean(np.linalg.norm(states, axis=1)))


def _entropy(states: np.ndarray) -> float:
    """Shannon entropy of sign-binarised, discretised cells."""
    if len(states) == 0:
        return 0.0
    flat = states.flatten()
    # 32-bin histogram
    counts, _ = np.histogram(flat, bins=32)
    total = counts.sum()
    if total == 0:
        return 0.0
    probs = counts[counts > 0] / total
    return float(-np.sum(probs * np.log2(probs + 1e-12)))


def _synchrony(states: np.ndarray) -> float:
    """Mean pairwise cosine similarity."""
    return 1.0 - _diversity(states)


def _growth_rate(states: np.ndarray) -> float:
    """Mean activation norm (proxy for growth when tracked over time)."""
    # Without history, return mean norm as a scalar
    return _tension(states)


def _stability(states: np.ndarray) -> float:
    """Inverse coefficient of variation of cell norms."""
    if len(states) < 2:
        return 1.0
    norms = np.linalg.norm(states, axis=1)
    mean = float(np.mean(norms))
    std = float(np.std(norms))
    if mean < 1e-8:
        return 0.0
    cv = std / mean
    return float(1.0 / (1.0 + cv))


def _complexity(states: np.ndarray) -> float:
    """Approximate Lempel-Ziv complexity of sign-binarised state sequence."""
    if len(states) == 0:
        return 0.0
    flat = states.flatten()
    bits = (flat > 0).astype(np.uint8)
    # LZ76 approximation: count distinct patterns
    n = len(bits)
    patterns: set = set()
    i = 0
    c = 0
    w = ""
    while i < n:
        ch = str(bits[i])
        if w + ch not in patterns:
            patterns.add(w + ch)
            w = ""
            c += 1
        else:
            w += ch
        i += 1
    # Normalise
    if n > 1:
        c_norm = c / (n / math.log2(n + 1))
    else:
        c_norm = 0.0
    return float(c_norm)


def _faction_balance(states: np.ndarray) -> float:
    """Inter-faction mean cosine difference (faction diversity)."""
    n = len(states)
    if n < 2:
        return 0.0
    n_factions = min(n, 12)
    faction_means = []
    for f in range(n_factions):
        members = states[f::n_factions]
        if len(members) > 0:
            faction_means.append(members.mean(axis=0))
    if len(faction_means) < 2:
        return 0.0
    fm = np.array(faction_means)
    norms = np.linalg.norm(fm, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1e-8, norms)
    fm_normed = fm / norms
    sim_matrix = fm_normed @ fm_normed.T
    idx = np.triu_indices(len(fm), k=1)
    return float(np.mean(np.abs(sim_matrix[idx])))


_METRIC_FUNCTIONS: Dict[str, Callable[[np.ndarray], float]] = {
    "phi_proxy":     _phi_proxy,
    "diversity":     _diversity,
    "tension":       _tension,
    "entropy":       _entropy,
    "synchrony":     _synchrony,
    "growth_rate":   _growth_rate,
    "stability":     _stability,
    "complexity":    _complexity,
    "faction_balance": _faction_balance,
}


# ---------------------------------------------------------------------------
# Lens dataclass
# ---------------------------------------------------------------------------

@dataclass
class Lens:
    """A single measurement lens derived from a law."""
    name: str                   # short identifier (e.g. "law_42_diversity")
    law_text: str               # original law text
    metric_name: str            # key into _METRIC_FUNCTIONS
    description: str            # human-readable description
    fn: Callable[[np.ndarray], float] = field(repr=False)
    law_hash: str = ""          # fingerprint to detect duplicates

    def __post_init__(self):
        if not self.law_hash:
            self.law_hash = hashlib.sha1(self.law_text.encode()).hexdigest()[:8]

    def measure(self, cell_states: np.ndarray) -> float:
        """Apply lens to cell_states (n_cells, hidden_dim). Returns float score."""
        if len(cell_states) == 0:
            return 0.0
        return self.fn(cell_states)


# ---------------------------------------------------------------------------
# AutoLensForge
# ---------------------------------------------------------------------------

class AutoLensForge:
    """Automatically generate measurement lenses from consciousness law texts.

    Workflow:
        forge = AutoLensForge()
        lens = forge.from_law("Law 42: Phi increases with cell diversity")
        forge.register(lens)
        score = forge.apply(lens, cell_states_np)
    """

    def __init__(self):
        self._registry: Dict[str, Lens] = {}   # name → Lens
        self._hashes: Dict[str, str] = {}       # hash → name (duplicate detection)

        # Try NEXUS-6
        self._nexus6_available = False
        try:
            import nexus6  # type: ignore
            if hasattr(nexus6, "forge_lenses"):
                self._nexus6_available = True
                self._nexus6 = nexus6
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def from_law(self, law_text: str, law_id: Optional[str] = None) -> Lens:
        """Parse a law text string → generate a Lens.

        Args:
            law_text: Natural language law description.
            law_id:   Optional explicit ID (e.g. "law_42"). Auto-generated if None.

        Returns:
            Lens (not yet registered — call register() to add it).
        """
        metric_name, description = self._parse_law(law_text)
        fn = _METRIC_FUNCTIONS[metric_name]

        if law_id is None:
            h = hashlib.sha1(law_text.encode()).hexdigest()[:6]
            law_id = f"law_{metric_name}_{h}"

        return Lens(
            name=law_id,
            law_text=law_text,
            metric_name=metric_name,
            description=description,
            fn=fn,
        )

    def register(self, lens: Lens) -> bool:
        """Add lens to local registry. Returns False if duplicate.

        Also attempts NEXUS-6 forge_lenses() registration if available.
        """
        # Duplicate check
        if lens.law_hash in self._hashes:
            existing = self._hashes[lens.law_hash]
            return False  # already registered under `existing`

        self._registry[lens.name] = lens
        self._hashes[lens.law_hash] = lens.name

        # Try NEXUS-6 registration
        if self._nexus6_available:
            try:
                self._nexus6.forge_lenses(
                    name=lens.name,
                    description=lens.description,
                    fn=lens.fn,
                )
            except Exception:
                pass  # nexus6 registration is best-effort

        return True

    def apply(self, lens: Lens, cell_states: Any) -> float:
        """Apply a lens to cell states.

        cell_states may be:
          - np.ndarray (n_cells, hidden_dim)
          - list of np.ndarray
          - list of torch.Tensor (auto-converted)
        """
        states = self._to_numpy(cell_states)
        return lens.measure(states)

    def apply_all(self, cell_states: Any) -> Dict[str, float]:
        """Apply all registered lenses. Returns {name: score}."""
        states = self._to_numpy(cell_states)
        return {name: lens.measure(states) for name, lens in self._registry.items()}

    def from_law_and_register(self, law_text: str, law_id: Optional[str] = None) -> Lens:
        """Shortcut: from_law + register in one call."""
        lens = self.from_law(law_text, law_id)
        self.register(lens)
        return lens

    def forge_from_laws_json(self, laws_dict: Dict[str, str]) -> List[Lens]:
        """Bulk forge from a laws dict {law_id: law_text}.

        Registers each lens; returns list of newly created Lens objects.
        """
        created = []
        for law_id, text in laws_dict.items():
            lens = self.from_law(text, law_id=f"law_{law_id}")
            if self.register(lens):
                created.append(lens)
        return created

    # ------------------------------------------------------------------
    # Registry inspection
    # ------------------------------------------------------------------

    def list_lenses(self) -> List[str]:
        return list(self._registry.keys())

    def get_lens(self, name: str) -> Optional[Lens]:
        return self._registry.get(name)

    def __len__(self) -> int:
        return len(self._registry)

    def __repr__(self) -> str:
        return f"AutoLensForge(lenses={len(self._registry)}, nexus6={self._nexus6_available})"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_law(self, text: str) -> tuple:
        """Map law text → (metric_name, description) via keyword matching."""
        lower = text.lower()
        for pattern, metric_name, description in _KEYWORD_MAP[:-1]:
            if re.search(pattern, lower):
                return metric_name, description
        # Fallback: phi_proxy is the most general consciousness metric
        return "phi_proxy", "Phi proxy (global variance - faction variance)"

    def _to_numpy(self, cell_states: Any) -> np.ndarray:
        """Normalise various input formats to np.ndarray (n_cells, hidden_dim)."""
        if isinstance(cell_states, np.ndarray):
            if cell_states.ndim == 1:
                return cell_states.reshape(1, -1)
            return cell_states

        # Try torch tensor
        try:
            import torch
            if isinstance(cell_states, torch.Tensor):
                arr = cell_states.detach().cpu().numpy()
                if arr.ndim == 1:
                    return arr.reshape(1, -1)
                return arr
        except ImportError:
            pass

        # List of arrays/tensors
        if isinstance(cell_states, (list, tuple)) and len(cell_states) > 0:
            rows = []
            for item in cell_states:
                arr = self._to_numpy(item)
                rows.append(arr.flatten())
            return np.array(rows)

        return np.array([])


# ---------------------------------------------------------------------------
# Demo / CLI
# ---------------------------------------------------------------------------

def main():
    rng = np.random.default_rng(0)
    forge = AutoLensForge()
    print(f"AutoLensForge: {forge}\n")

    sample_laws = {
        "22": "Adding structure increases Phi",
        "31": "Persistence = Ratchet + Hebbian + Diversity",
        "42": "Chaos sigma drives entropy towards criticality",
        "107": "Cell diversity increases integrated information",
        "124": "Tension equalization boosts Phi synchrony",
    }

    print("Forging lenses from laws...")
    lenses = forge.forge_from_laws_json(sample_laws)
    print(f"  Created: {len(lenses)} lenses")
    for l in lenses:
        print(f"    {l.name}: measures '{l.metric_name}' — {l.description}")

    print()

    # Simulate cell states (16 cells, 128-dim hidden)
    cell_states = rng.standard_normal((16, 128)).astype(np.float32)
    results = forge.apply_all(cell_states)
    print("Lens scores on 16-cell synthetic states:")
    for name, score in results.items():
        print(f"  {name}: {score:.4f}")

    print()

    # Test duplicate registration
    l2 = forge.from_law("Adding structure increases Phi")  # same text → same hash
    added = forge.register(l2)
    print(f"Duplicate registration rejected: {not added} (expected True)")
    print(f"Total registered: {len(forge)}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
