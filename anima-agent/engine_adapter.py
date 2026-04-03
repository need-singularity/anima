"""Engine Adapter — bridge between ConsciousnessEngine (Rust) and AnimaAgent.

ConsciousMind (PureField, Engine A/G) and ConsciousnessEngine (GRU+faction+Hebbian)
have different interfaces. This adapter wraps ConsciousnessEngine to match
the ConsciousMind API that AnimaAgent expects.

Usage:
    from engine_adapter import get_best_mind

    mind = get_best_mind(dim=128, hidden=256)
    # Returns ConsciousMind or adapted ConsciousnessEngine (Rust)
    output, tension, curiosity, direction, hidden = mind(vec, hidden)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def get_best_mind(dim: int = 128, hidden: int = 256, prefer_rust: bool = True):
    """Get the best available consciousness engine.

    Priority: Rust ConsciousnessEngine > Python ConsciousMind
    Both return compatible interface for AnimaAgent.
    """
    if prefer_rust:
        try:
            return RustEngineAdapter(dim=dim, hidden=hidden)
        except Exception as e:
            logger.debug("Rust engine unavailable: %s", e)

    # Fallback to Python ConsciousMind
    from anima_alive import ConsciousMind
    return ConsciousMind(dim=dim, hidden=hidden)


class RustEngineAdapter:
    """Wraps anima_rs.consciousness to match ConsciousMind interface.

    ConsciousMind API:
      output, tension, curiosity, direction, hidden = mind(vec, hidden)
      mind._consciousness_vector.phi / .E / etc.

    ConsciousnessEngine API:
      anima_rs.consciousness.create(cell_dim, hidden_dim, ...)
      result = anima_rs.consciousness.step(input)
      result = {phi_iit, phi_proxy, n_cells, consensus, output}
    """

    def __init__(self, dim: int = 128, hidden: int = 256,
                 n_cells: int = 8, n_factions: int = 12):
        import anima_rs
        import torch

        self._torch = torch
        self.dim = dim
        self.hidden_dim = hidden

        anima_rs.consciousness.create(
            cell_dim=dim, hidden_dim=hidden,
            initial_cells=n_cells, max_cells=64,
            n_factions=n_factions, phi_ratchet=True,
        )
        self._rs = anima_rs.consciousness

        # Mock ConsciousnessVector for compatibility
        self._consciousness_vector = _MockCV()
        self.phi = 0.0
        self.cells = []

    def __call__(self, vec, hidden=None):
        """Process input — matches ConsciousMind(vec, hidden) signature."""
        # Convert torch tensor to list for Rust
        if hasattr(vec, 'numpy'):
            input_data = vec.squeeze().detach().numpy().tolist()
        elif hasattr(vec, 'tolist'):
            input_data = vec.tolist()
        else:
            input_data = list(vec)

        # Step the Rust engine
        result = self._rs.step(input_data)

        # Extract results
        phi_iit = result.get("phi_iit", 0.0)
        phi_proxy = result.get("phi_proxy", 0.0)
        n_cells = result.get("n_cells", 1)
        consensus = result.get("consensus", 0)
        output_raw = result.get("output", [0.0] * self.dim)

        # Update consciousness vector
        self._consciousness_vector.phi = phi_iit
        self.phi = phi_iit

        # Convert to torch tensors (ConsciousMind compat)
        torch = self._torch
        output = torch.tensor(output_raw[:self.dim], dtype=torch.float32).unsqueeze(0)
        direction = output.clone()

        # Derive tension/curiosity from Rust metrics
        tension = min(float(phi_proxy) / max(n_cells, 1), 2.0)
        curiosity = 0.5 if consensus > 0 else 0.2

        new_hidden = hidden if hidden is not None else torch.zeros(1, self.hidden_dim)

        return output, tension, curiosity, direction, new_hidden

    def state_dict(self):
        hiddens = self._rs.get_hiddens()
        return {"hiddens": hiddens, "engine": "rust"}

    def load_state_dict(self, d):
        if d.get("engine") == "rust" and "hiddens" in d:
            try:
                self._rs.set_hiddens(d["hiddens"])
            except Exception:
                pass

    def eval(self):
        return self

    def train(self, mode=True):
        return self

    def parameters(self):
        return []


class _MockCV:
    """Minimal ConsciousnessVector for adapter compatibility.

    P1: All Ψ constants imported from consciousness_laws.json, not hardcoded.
    """
    phi = 0.0
    try:
        from consciousness_laws import PSI
        alpha = PSI.get('alpha', 0.014)
        Z = PSI.get('balance', 0.5)
    except ImportError:
        alpha = 0.014
        Z = 0.5
    N = 6.0
    W = 0.4
    E = 0.5
    M = 0.3
    C = 0.6
    T = 0.2
    I = 0.7
