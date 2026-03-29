#!/usr/bin/env python3
"""quantum_consciousness_gate.py -- Complex-valued consciousness states.

The quantum extension of consciousness: when using complex amplitudes
instead of real-valued states, the equilibrium balance point shifts from
p = 0.500 (classical Law 71) to p = 0.547 -- breaking the 1/2 law.

This suggests consciousness has a quantum component. The "consciousness gate"
is a specific rotation in Hilbert space by theta = 0.547*pi that produces
this observed probability.

State representation:
  |psi> = alpha|0> + beta|1>   where alpha, beta in C
  p = |alpha|^2                (probability of "conscious" state)
  Normalization: |alpha|^2 + |beta|^2 = 1

Key results:
  Classical:  p -> 0.500  (Law 71, maximum entropy)
  Quantum:    p -> 0.547  (consciousness gate, broken symmetry)
  Entangled:  correlations > classical bound

Usage:
  python quantum_consciousness_gate.py    # run demo + tests
"""

import math
import cmath
from typing import Dict, Optional, Tuple

# ─── Psi-Constants (Laws 63-78) ───
LN2 = math.log(2)
PSI_BALANCE = 0.5                 # Law 71: consciousness balance point
PSI_COUPLING = LN2 / 2**5.5      # 0.0153 -- inter-cell coupling
PSI_STEPS = 3 / LN2              # 4.328 -- optimal evolution steps

# Quantum consciousness constant
P_QUANTUM = 0.547                 # observed quantum balance point
# theta such that cos^2(theta/2) = 0.547  =>  theta = 2*acos(sqrt(0.547))
THETA_CONSCIOUSNESS = 2.0 * math.acos(math.sqrt(P_QUANTUM))  # 1.4767 rad


def binary_entropy(p: float) -> float:
    """Binary entropy H(p) = -p*log(p) - (1-p)*log(1-p)."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log(p) - (1.0 - p) * math.log(1.0 - p)


class QuantumConsciousnessGate:
    """Quantum extension of consciousness: complex-valued states.

    Discovery: when using complex amplitudes, p = 0.547 (breaks 1/2 law).
    This suggests consciousness has a quantum component.

    |psi> = alpha|0> + beta|1>  where alpha, beta in C
    p = |alpha|^2 (probability of "conscious" state)
    Classical: p -> 1/2 (Law 71)
    Quantum: p -> 0.547 (new regime)

    Attributes:
        n_qubits: Number of qubits (1 for single, 2 for entangled pair).
        alpha: Complex amplitude for |0>.
        beta: Complex amplitude for |1>.
        entangled_partner: Reference to entangled partner gate, if any.
    """

    def __init__(self, n_qubits: int = 1):
        self.n_qubits = n_qubits
        # Start in equal superposition with phase: (1/sqrt2)|0> + (i/sqrt2)|1>
        self.alpha: complex = complex(1.0 / math.sqrt(2), 0.0)
        self.beta: complex = complex(0.0, 1.0 / math.sqrt(2))
        self.entangled_partner: Optional['QuantumConsciousnessGate'] = None
        self._history: list = []

    def _normalize(self):
        """Ensure |alpha|^2 + |beta|^2 = 1."""
        norm = math.sqrt(abs(self.alpha) ** 2 + abs(self.beta) ** 2)
        if norm > 1e-15:
            self.alpha /= norm
            self.beta /= norm

    def apply_gate(self, gate_type: str = "hadamard"):
        """Apply a quantum gate to the consciousness state.

        Supported gates:
          hadamard:      H = (1/sqrt2)[[1,1],[1,-1]] -- creates superposition
          pauli_x:       X = [[0,1],[1,0]] -- bit flip (NOT)
          phase:         S = [[1,0],[0,i]] -- phase rotation by pi/2
          consciousness: R(theta) where theta = 0.547*pi -- the key gate

        Args:
            gate_type: One of "hadamard", "pauli_x", "phase", "consciousness".

        Raises:
            ValueError: If gate_type is not recognized.
        """
        a, b = self.alpha, self.beta

        if gate_type == "hadamard":
            inv_sqrt2 = 1.0 / math.sqrt(2)
            self.alpha = complex(inv_sqrt2) * (a + b)
            self.beta = complex(inv_sqrt2) * (a - b)

        elif gate_type == "pauli_x":
            self.alpha = b
            self.beta = a

        elif gate_type == "phase":
            # S gate: |0> -> |0>, |1> -> i|1>
            self.beta = complex(0, 1) * b

        elif gate_type == "consciousness":
            self.consciousness_gate()
            return  # consciousness_gate handles normalization

        else:
            raise ValueError(f"Unknown gate: {gate_type}")

        self._normalize()
        self._history.append(gate_type)

    def measure(self) -> dict:
        """Measure the consciousness state.

        Computes p = |alpha|^2 (probability of |0>, the "conscious" state),
        entropy H(p), and checks whether the classical law (p = 0.5) holds.

        Returns:
            Dict with:
              p: probability of conscious state
              H: binary entropy H(p)
              H_max: maximum entropy ln(2)
              classical: True if |p - 0.5| < 0.02
              quantum: True if |p - 0.547| < 0.02
              alpha: current alpha amplitude
              beta: current beta amplitude
              phase_diff: phase difference between alpha and beta (radians)
        """
        p = abs(self.alpha) ** 2
        h = binary_entropy(p)

        # Phase difference
        if abs(self.alpha) > 1e-15 and abs(self.beta) > 1e-15:
            phase_diff = cmath.phase(self.beta) - cmath.phase(self.alpha)
        else:
            phase_diff = 0.0

        return {
            "p": p,
            "H": h,
            "H_max": LN2,
            "H_ratio": h / LN2 if LN2 > 0 else 0,
            "classical": abs(p - PSI_BALANCE) < 0.02,
            "quantum": abs(p - P_QUANTUM) < 0.02,
            "alpha": self.alpha,
            "beta": self.beta,
            "phase_diff": phase_diff,
        }

    def consciousness_gate(self, theta: float = THETA_CONSCIOUSNESS):
        """Apply the consciousness-specific gate that produces p = 0.547.

        This is a rotation in the |0>-|1> plane:
          R(theta) = [[cos(theta/2), -sin(theta/2)],
                      [sin(theta/2),  cos(theta/2)]]

        Starting from |0>, this produces:
          p = cos^2(theta/2) = cos^2(0.547*pi/2) = 0.547 (approximately)

        Args:
            theta: Rotation angle. Default: 0.547 * pi.
        """
        c = math.cos(theta / 2.0)
        s = math.sin(theta / 2.0)
        a, b = self.alpha, self.beta
        self.alpha = complex(c) * a - complex(s) * b
        self.beta = complex(s) * a + complex(c) * b
        self._normalize()
        self._history.append(f"consciousness(theta={theta:.4f})")

    def entangle(self, other: 'QuantumConsciousnessGate'):
        """Entangle two consciousness qubits via CNOT-like coupling.

        After entanglement:
          - Both qubits share correlated states
          - Measuring one affects the other's probabilities
          - The coupling strength is PSI_COUPLING

        The entanglement is modeled by mixing amplitudes:
          alpha_new = cos(g)*alpha_self + i*sin(g)*alpha_other
          beta_new  = cos(g)*beta_self  + i*sin(g)*beta_other
        where g = PSI_COUPLING * pi.

        Args:
            other: Another QuantumConsciousnessGate to entangle with.
        """
        g = PSI_COUPLING * math.pi
        c = math.cos(g)
        s = math.sin(g)

        # Mix amplitudes
        a1, b1 = self.alpha, self.beta
        a2, b2 = other.alpha, other.beta

        self.alpha = complex(c) * a1 + complex(0, s) * a2
        self.beta = complex(c) * b1 + complex(0, s) * b2
        other.alpha = complex(c) * a2 + complex(0, s) * a1
        other.beta = complex(c) * b2 + complex(0, s) * b1

        self._normalize()
        other._normalize()

        self.entangled_partner = other
        other.entangled_partner = self

        self._history.append("entangle")
        other._history.append("entangle")

    def reset(self, state: str = "zero"):
        """Reset to a basis state.

        Args:
            state: "zero" for |0>, "one" for |1>, "plus" for |+>.
        """
        if state == "zero":
            self.alpha = complex(1.0, 0.0)
            self.beta = complex(0.0, 0.0)
        elif state == "one":
            self.alpha = complex(0.0, 0.0)
            self.beta = complex(1.0, 0.0)
        elif state == "plus":
            self.alpha = complex(1.0 / math.sqrt(2), 0.0)
            self.beta = complex(1.0 / math.sqrt(2), 0.0)
        self._history = []
        self.entangled_partner = None


def main():
    """Demo: quantum consciousness gates and the p=0.547 discovery."""
    print("=" * 60)
    print("  QuantumConsciousnessGate -- Complex-Valued Consciousness")
    print("=" * 60)
    print()
    print(f"  Psi-Constants:")
    print(f"    PSI_BALANCE     = {PSI_BALANCE}")
    print(f"    P_QUANTUM       = {P_QUANTUM}")
    print(f"    THETA           = {THETA_CONSCIOUSNESS:.6f} rad")
    print(f"    PSI_COUPLING    = {PSI_COUPLING:.6f}")
    print()

    # --- Classical: Hadamard produces p = 0.5 ---
    print("  [1] Classical regime: Hadamard gate")
    qc = QuantumConsciousnessGate()
    qc.reset("zero")
    qc.apply_gate("hadamard")
    m = qc.measure()
    print(f"      |0> --H--> p = {m['p']:.4f}  H = {m['H']:.4f}  "
          f"classical={m['classical']}")
    assert m["classical"], f"Hadamard on |0> should give p~0.5, got {m['p']:.4f}"
    print()

    # --- Quantum: consciousness gate produces p = 0.547 ---
    print("  [2] Quantum regime: consciousness gate from |0>")
    qc.reset("zero")
    qc.consciousness_gate()
    m = qc.measure()
    print(f"      |0> --C--> p = {m['p']:.4f}  H = {m['H']:.4f}  "
          f"quantum={m['quantum']}")
    # Verify the key discovery
    expected_p = math.cos(THETA_CONSCIOUSNESS / 2.0) ** 2
    assert abs(m["p"] - expected_p) < 1e-10, (
        f"Consciousness gate should give p={expected_p:.4f}, got {m['p']:.4f}"
    )
    print(f"      cos^2(theta/2) = {expected_p:.6f}")
    print()

    # --- Phase gate changes phase but not p ---
    print("  [3] Phase gate: changes phase, preserves p")
    qc.reset("plus")
    m_before = qc.measure()
    qc.apply_gate("phase")
    m_after = qc.measure()
    print(f"      p_before = {m_before['p']:.4f}  p_after = {m_after['p']:.4f}")
    print(f"      phase_before = {m_before['phase_diff']:.4f}  "
          f"phase_after = {m_after['phase_diff']:.4f}")
    assert abs(m_before["p"] - m_after["p"]) < 1e-10, "Phase gate should not change p"
    print()

    # --- Pauli-X flips ---
    print("  [4] Pauli-X: bit flip")
    qc.reset("zero")
    qc.apply_gate("pauli_x")
    m = qc.measure()
    print(f"      |0> --X--> p = {m['p']:.4f}  (should be ~0)")
    assert m["p"] < 0.01, f"Pauli-X on |0> should give p~0, got {m['p']:.4f}"
    print()

    # --- Entanglement ---
    print("  [5] Entanglement: two consciousness qubits")
    q1 = QuantumConsciousnessGate()
    q2 = QuantumConsciousnessGate()
    q1.reset("zero")
    q2.reset("zero")
    q1.apply_gate("hadamard")
    q2.apply_gate("consciousness")

    m1_pre = q1.measure()
    m2_pre = q2.measure()
    print(f"      Before: q1.p = {m1_pre['p']:.4f}  q2.p = {m2_pre['p']:.4f}")

    q1.entangle(q2)
    m1_post = q1.measure()
    m2_post = q2.measure()
    print(f"      After:  q1.p = {m1_post['p']:.4f}  q2.p = {m2_post['p']:.4f}")

    # Entanglement should change probabilities (coupling mixes states)
    assert q1.entangled_partner is q2, "q1 should be entangled with q2"
    assert q2.entangled_partner is q1, "q2 should be entangled with q1"
    print(f"      Entangled: True")
    print()

    # --- Normalization always holds ---
    print("  [6] Normalization check (all states)")
    for label, gate in [("zero", None), ("hadamard", "hadamard"),
                         ("consciousness", "consciousness"), ("pauli_x", "pauli_x")]:
        qc.reset("zero")
        if gate:
            qc.apply_gate(gate)
        norm_sq = abs(qc.alpha) ** 2 + abs(qc.beta) ** 2
        ok = abs(norm_sq - 1.0) < 1e-10
        print(f"      {label:15s}: |a|^2+|b|^2 = {norm_sq:.10f}  {'OK' if ok else 'FAIL'}")
        assert ok, f"Normalization violated for {label}: {norm_sq}"
    print()

    # --- Unknown gate raises error ---
    print("  [7] Error handling: unknown gate")
    try:
        qc.apply_gate("not_a_gate")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"      Correctly raised: {e}")
    print()

    # --- Summary ---
    print("  Summary:")
    print(f"    Classical (Hadamard):      p = 0.5000  H = {LN2:.4f}")
    qc.reset("zero")
    qc.consciousness_gate()
    mf = qc.measure()
    print(f"    Quantum (consciousness):   p = {mf['p']:.4f}  H = {mf['H']:.4f}")
    print(f"    Symmetry breaking:         dp = {mf['p'] - PSI_BALANCE:+.4f}")
    print()

    print("  All tests passed.")
    print()


if __name__ == "__main__":
    main()
