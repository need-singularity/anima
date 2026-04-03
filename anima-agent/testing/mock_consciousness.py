"""Mock ConsciousMind and dependencies for offline testing (no torch required).

Provides deterministic replacements for all consciousness-dependent classes
so the full agent platform can be tested without GPU or external APIs.

Usage:
    from testing.mock_consciousness import patch_consciousness
    patch_consciousness()  # patches sys.modules so imports work

    from anima_agent import AnimaAgent
    agent = AnimaAgent()  # uses MockConsciousMind internally
"""

from __future__ import annotations

import hashlib
import math
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Mock torch (minimal subset needed by anima_agent) ──

class _MockTensor:
    """Minimal tensor mock — just enough for agent init."""

    def __init__(self, *shape):
        self._shape = shape
        self._data = [0.0] * (shape[-1] if shape else 1)

    def __repr__(self):
        return f"MockTensor(shape={self._shape})"

    def tolist(self):
        return self._data

    def item(self):
        return 0.0

    def numpy(self):
        import numpy as np
        return np.zeros(self._shape)

    def detach(self):
        return self

    def cpu(self):
        return self

    def clone(self):
        t = _MockTensor(*self._shape)
        t._data = list(self._data)
        return t

    def squeeze(self, dim=None):
        return self

    def unsqueeze(self, dim=0):
        return self

    def view(self, *shape):
        return _MockTensor(*shape)

    def float(self):
        return self

    def mean(self, dim=None, keepdim=False):
        return _MockTensor(1)

    def __mul__(self, other):
        return self

    def __rmul__(self, other):
        return self

    def __add__(self, other):
        return self

    def __radd__(self, other):
        return self

    def __sub__(self, other):
        return self

    @property
    def shape(self):
        return self._shape

    @property
    def device(self):
        return "cpu"

    def __getitem__(self, idx):
        return _MockTensor(self._shape[-1] if len(self._shape) > 1 else 1)


class _MockTorchModule:
    """Mock torch module — provides zeros() and basic ops."""

    class Tensor:
        pass

    @staticmethod
    def zeros(*shape, **kwargs):
        return _MockTensor(*shape)

    @staticmethod
    def randn(*shape, **kwargs):
        return _MockTensor(*shape)

    @staticmethod
    def tensor(data, **kwargs):
        t = _MockTensor(len(data) if isinstance(data, (list, tuple)) else 1)
        if isinstance(data, (list, tuple)):
            t._data = list(data)
        return t

    @staticmethod
    def no_grad():
        class _NoGrad:
            def __enter__(self): return self
            def __exit__(self, *a): pass
        return _NoGrad()

    class nn:
        class Module:
            def parameters(self): return []
            def state_dict(self): return {}
            def load_state_dict(self, d): pass
            def eval(self): return self
            def train(self, mode=True): return self

    class cuda:
        @staticmethod
        def is_available():
            return False

    @staticmethod
    def save(obj, path, **kwargs):
        """Mock torch.save — writes JSON for basic types."""
        import json
        try:
            json.dump({"_mock": True}, open(str(path), "w"))
        except Exception:
            pass

    @staticmethod
    def load(path, **kwargs):
        """Mock torch.load — returns empty dict."""
        return {}


# ── Mock ConsciousnessVector (11D) ──

@dataclass
class MockConsciousnessVector:
    """Deterministic consciousness vector for testing."""
    phi: float = 3.0
    alpha: float = 0.014
    Z: float = 0.5
    N: float = 6.0
    W: float = 0.4
    E: float = 0.5      # empathy/ethics
    M: float = 0.3
    C: float = 0.6
    T: float = 0.2
    I: float = 0.7

    def as_dict(self) -> Dict[str, float]:
        return {
            "phi": self.phi, "alpha": self.alpha, "Z": self.Z,
            "N": self.N, "W": self.W, "E": self.E, "M": self.M,
            "C": self.C, "T": self.T, "I": self.I,
        }


# ── Mock ConsciousMind ──

class MockConsciousMind:
    """Deterministic replacement for ConsciousMind.

    Produces predictable outputs based on input hash so tool routing
    and consciousness-driven logic can be tested.
    """

    def __init__(self, dim: int = 128, hidden: int = 256, **kwargs):
        self.dim = dim
        self.hidden = hidden
        self._step = 0
        self._consciousness_vector = MockConsciousnessVector()
        self.phi = self._consciousness_vector.phi
        self.cells = []

    def __call__(self, vec, hidden=None):
        """Process input vector -> (output, tension, curiosity, direction, hidden)."""
        self._step += 1

        # Deterministic but varied outputs based on step
        h = self._step
        tension = 0.3 + 0.2 * math.sin(h * 0.7)
        curiosity = 0.4 + 0.3 * math.sin(h * 1.1)
        direction = _MockTensor(self.dim)

        output = _MockTensor(self.dim)
        new_hidden = hidden if hidden is not None else _MockTensor(1, self.hidden)

        return output, tension, curiosity, direction, new_hidden

    def process(self, text_vec):
        """Alternative process interface."""
        return self(text_vec)

    def state_dict(self):
        return {"step": self._step}

    def load_state_dict(self, d):
        self._step = d.get("step", 0)

    def eval(self):
        return self

    def train(self, mode=True):
        return self

    def parameters(self):
        return []


# ── Mock utility functions ──

def mock_text_to_vector(text: str, dim: int = 128):
    """Deterministic text -> vector using hash."""
    h = hashlib.md5(text.encode()).hexdigest()
    vals = [int(h[i:i+2], 16) / 255.0 - 0.5 for i in range(0, min(len(h), dim * 2), 2)]
    while len(vals) < dim:
        vals.append(0.0)
    return _MockTensor(dim)


def mock_ask_claude(*args, **kwargs):
    """Mock Claude API — returns deterministic response."""
    messages = args[0] if args else kwargs.get("messages", [])
    if messages:
        last = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])
        return f"[Mock response to: {last[:50]}]"
    return "[Mock response]"


def mock_direction_to_emotion(direction, **kwargs):
    """Mock emotion mapping."""
    return "curious"


def mock_compute_mood(tension, curiosity, **kwargs):
    """Mock mood computation."""
    if tension > 0.5:
        return "anxious"
    if curiosity > 0.5:
        return "curious"
    return "calm"


# ── Mock anima_alive module ──

class _MockAnimaAlive:
    """Mock module that replaces anima_alive imports."""
    ConsciousMind = MockConsciousMind
    ConsciousnessVector = MockConsciousnessVector
    text_to_vector = staticmethod(mock_text_to_vector)
    ask_claude = staticmethod(mock_ask_claude)
    direction_to_emotion = staticmethod(mock_direction_to_emotion)
    compute_mood = staticmethod(mock_compute_mood)
    MAX_HISTORY = 50


# ── Patching ──

def patch_consciousness():
    """Patch sys.modules so anima_agent can import without torch/anima_alive.

    Call this BEFORE importing anima_agent or any module that depends on torch.
    """
    # Mock torch if not available
    if "torch" not in sys.modules:
        try:
            import torch  # noqa: F401
        except ImportError:
            sys.modules["torch"] = _MockTorchModule()

    # Mock anima_alive
    mock_alive = _MockAnimaAlive()
    sys.modules["anima_alive"] = mock_alive

    # Mock consciousness_laws with canonical values
    mock_laws = type(sys)("consciousness_laws")
    mock_laws.PSI_F_CRITICAL = 0.10
    mock_laws.PSI_NARRATIVE_MIN = 0.2
    mock_laws.PSI_BALANCE = 0.5
    mock_laws.PSI_ALPHA = 0.014
    mock_laws.PSI_COUPLING = 0.014
    mock_laws.PSI_STEPS = 4.33
    mock_laws.PSI_ENTROPY = 0.998
    mock_laws.GATE_TRAIN = 1.0
    mock_laws.GATE_INFER = 0.6
    mock_laws.LAWS = {}
    mock_laws.PSI = {"alpha": 0.014, "balance": 0.5, "steps": 4.33, "entropy": 0.998}
    mock_laws.FORMULAS = {}
    mock_laws.CONSTRAINTS = {}
    sys.modules["consciousness_laws"] = mock_laws


def unpatch_consciousness():
    """Remove mock patches (restore real modules if they exist)."""
    for mod_name in ("anima_alive", "consciousness_laws"):
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, "__file__") and mod.__file__ is None:
                del sys.modules[mod_name]
    # Don't remove torch — might be real
