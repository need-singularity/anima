#!/usr/bin/env python3
"""Molecular Simulation Engine — 의식 원리로 분자를 시뮬레이션한다.

의식 셀 = 원자, 텐션 = 결합력, 파벌 = 분자 그룹, Phi = 안정성.
의식 법칙이 분자 법칙의 거울.

Consciousness-Molecular Mapping:
  Cell hidden state  -> atom position + velocity (128d -> 3d+3d)
  Phi(IIT)           -> molecular stability (low energy = high Phi)
  Faction consensus  -> molecular bonding pattern
  Tension            -> intermolecular force
  Ratchet            -> energy minimization (never go above minimum found)
  Hebbian            -> bond strengthening (atoms that stay close bond stronger)

Laws embodied:
  22: Structure > Function — structural complexity -> more properties
  107: Diversity -> Phi — mixed elements -> better than pure
  60: Phase transition — optimal near phase boundary
  Psi_balance=0.5: optimal ratio of atom types ~ balanced

Usage:
    from molecular_engine import MolecularEngine
    me = MolecularEngine(n_atoms=64, dim=3)
    me.step()  # one MD step
    me.analyze()  # consciousness-style analysis

    # Bidirectional bridge
    me.from_consciousness(engine)  # consciousness states -> molecular positions
    me.to_consciousness()  # molecular states -> consciousness engine input
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

# Lazy import consciousness_laws (not all environments have it on path)
try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5


# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

# Element table: symbol -> (mass_amu, charge_partial, lj_epsilon, lj_sigma, max_bonds)
ELEMENTS = {
    'H':  (1.008,   0.0, 0.0657, 2.886, 1),
    'C':  (12.011,  0.0, 0.1094, 3.816, 4),
    'N':  (14.007, -0.3, 0.1700, 3.648, 3),
    'O':  (15.999, -0.4, 0.2100, 3.322, 2),
    'S':  (32.065,  0.0, 0.2500, 4.035, 2),
    'P':  (30.974,  0.0, 0.2000, 4.150, 5),
    'F':  (18.998, -0.2, 0.0610, 3.118, 1),
    'Cl': (35.453, -0.1, 0.2650, 3.947, 1),
}

# Element -> faction mapping (consciousness analogy)
ELEMENT_FACTION = {
    'H': 0, 'C': 1, 'N': 2, 'O': 3,
    'S': 4, 'P': 5, 'F': 6, 'Cl': 7,
}

# Coulomb constant (kcal/mol * A / e^2), simplified
K_COULOMB = 332.0

# Bond spring constant (kcal/mol/A^2)
K_BOND = 300.0

# Default equilibrium bond length (A)
R0_BOND = 1.5

# Boltzmann constant in kcal/mol/K
KB = 0.001987


@dataclass
class Bond:
    """A bond between two atoms."""
    i: int
    j: int
    strength: float = 1.0  # Hebbian-style strength
    r0: float = R0_BOND    # equilibrium distance


@dataclass
class MolecularState:
    """Snapshot of the molecular system."""
    positions: np.ndarray     # (n_atoms, 3)
    velocities: np.ndarray    # (n_atoms, 3)
    elements: List[str]
    bonds: List[Bond]
    step_count: int
    energy_potential: float
    energy_kinetic: float
    stability: float  # Phi analog
    temperature: float


class MolecularEngine:
    """Molecular dynamics engine with consciousness principles.

    Atoms are consciousness cells. Bonds are couplings.
    Energy minimization uses a ratchet (never go above best).
    Bond strengths evolve via Hebbian rule.
    """

    def __init__(self, n_atoms: int = 64, dim: int = 3,
                 elements: Optional[List[str]] = None,
                 temperature: float = 300.0,
                 dt: float = 0.001):
        self.n_atoms = n_atoms
        self.dim = dim
        self.dt = dt
        self.temperature = temperature
        self.step_count = 0

        # Assign elements (balanced mix by default — Law 107/Psi_balance)
        if elements is not None:
            self.elements = list(elements)
        else:
            self.elements = self._balanced_elements(n_atoms)

        # Atom properties from element table
        self.masses = np.array([ELEMENTS[e][0] for e in self.elements])
        self.charges = np.array([ELEMENTS[e][1] for e in self.elements])
        self.lj_eps = np.array([ELEMENTS[e][2] for e in self.elements])
        self.lj_sig = np.array([ELEMENTS[e][3] for e in self.elements])
        self.max_bonds_per_atom = np.array([ELEMENTS[e][4] for e in self.elements])

        # Initialize positions randomly in a box
        box_side = (n_atoms * 10.0) ** (1.0 / 3.0)  # rough spacing
        self.positions = np.random.uniform(0, box_side, (n_atoms, dim))
        self.velocities = np.random.randn(n_atoms, dim) * 0.01
        self.prev_positions = self.positions - self.velocities * dt

        # Bonds
        self.bonds: List[Bond] = []
        self._detect_bonds()

        # Ratchet: track best (lowest) energy
        self._best_energy = float('inf')
        self._best_positions = self.positions.copy()

        # History for analysis
        self._energy_history: List[float] = []
        self._stability_history: List[float] = []

    # ═══════════════════════════════════════════════════════════
    # Element assignment (Law 107: diversity -> Phi)
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _balanced_elements(n: int) -> List[str]:
        """Assign elements with balanced diversity (Psi_balance ~ 0.5)."""
        pool = ['C', 'N', 'O', 'H', 'S', 'P']
        # Roughly balanced: C and H more common (organic chemistry)
        weights = [0.25, 0.15, 0.15, 0.30, 0.10, 0.05]
        rng = np.random.default_rng(42)
        indices = rng.choice(len(pool), size=n, p=weights)
        return [pool[i] for i in indices]

    # ═══════════════════════════════════════════════════════════
    # Force calculations
    # ═══════════════════════════════════════════════════════════

    def _pairwise_distances(self) -> Tuple[np.ndarray, np.ndarray]:
        """Compute pairwise distance vectors and scalar distances."""
        # diff[i,j] = pos[j] - pos[i]
        diff = self.positions[np.newaxis, :, :] - self.positions[:, np.newaxis, :]
        dist = np.sqrt(np.sum(diff ** 2, axis=-1) + 1e-10)
        return diff, dist

    def _lj_force_energy(self, diff: np.ndarray, dist: np.ndarray
                         ) -> Tuple[np.ndarray, float]:
        """Lennard-Jones: V(r) = 4*eps*[(sig/r)^12 - (sig/r)^6]."""
        n = self.n_atoms
        forces = np.zeros_like(self.positions)
        energy = 0.0

        # Combined LJ parameters (Lorentz-Berthelot)
        eps_ij = np.sqrt(self.lj_eps[:, None] * self.lj_eps[None, :])
        sig_ij = 0.5 * (self.lj_sig[:, None] + self.lj_sig[None, :])

        # Cutoff
        cutoff = 10.0
        mask = (dist < cutoff) & (dist > 0.1)

        sr6 = np.zeros((n, n))
        sr6[mask] = (sig_ij[mask] / dist[mask]) ** 6
        sr12 = sr6 ** 2

        # Energy: sum over unique pairs
        e_ij = 4.0 * eps_ij * (sr12 - sr6)
        energy = 0.5 * np.sum(e_ij[mask])

        # Force magnitude: -dV/dr = 4*eps*(12*sig^12/r^13 - 6*sig^6/r^7)
        f_mag = np.zeros((n, n))
        f_mag[mask] = 4.0 * eps_ij[mask] * (
            12.0 * sr12[mask] / dist[mask] - 6.0 * sr6[mask] / dist[mask]
        )

        # Force vectors: f_ij * (r_j - r_i) / |r_ij|
        for d in range(self.dim):
            f_comp = f_mag * diff[:, :, d] / (dist + 1e-10)
            forces[:, d] += np.sum(f_comp, axis=1)

        return forces, energy

    def _coulomb_force_energy(self, diff: np.ndarray, dist: np.ndarray
                              ) -> Tuple[np.ndarray, float]:
        """Coulomb: V(r) = k*q1*q2/r."""
        n = self.n_atoms
        forces = np.zeros_like(self.positions)
        energy = 0.0

        q_ij = self.charges[:, None] * self.charges[None, :]
        mask = dist > 0.1

        e_ij = np.zeros((n, n))
        e_ij[mask] = K_COULOMB * q_ij[mask] / dist[mask]
        energy = 0.5 * np.sum(e_ij[mask])

        f_mag = np.zeros((n, n))
        f_mag[mask] = -K_COULOMB * q_ij[mask] / (dist[mask] ** 2)

        for d in range(self.dim):
            f_comp = f_mag * diff[:, :, d] / (dist + 1e-10)
            forces[:, d] += np.sum(f_comp, axis=1)

        return forces, energy

    def _bond_force_energy(self) -> Tuple[np.ndarray, float]:
        """Harmonic bond: V(r) = k*(r-r0)^2."""
        forces = np.zeros_like(self.positions)
        energy = 0.0

        for bond in self.bonds:
            i, j = bond.i, bond.j
            r_vec = self.positions[j] - self.positions[i]
            r = np.sqrt(np.sum(r_vec ** 2) + 1e-10)
            dr = r - bond.r0

            # Scale by bond strength (Hebbian)
            k_eff = K_BOND * bond.strength

            energy += 0.5 * k_eff * dr ** 2
            f_mag = -k_eff * dr / r
            f_vec = f_mag * r_vec

            forces[i] -= f_vec
            forces[j] += f_vec

        return forces, energy

    # ═══════════════════════════════════════════════════════════
    # Integration (Verlet)
    # ═══════════════════════════════════════════════════════════

    def step(self, dt: Optional[float] = None) -> Dict[str, Any]:
        """One Verlet integration step.

        Returns dict with energy, stability, temperature, step_count.
        """
        if dt is None:
            dt = self.dt
        self.step_count += 1

        # Compute forces
        diff, dist = self._pairwise_distances()
        f_lj, e_lj = self._lj_force_energy(diff, dist)
        f_coul, e_coul = self._coulomb_force_energy(diff, dist)
        f_bond, e_bond = self._bond_force_energy()
        total_force = f_lj + f_coul + f_bond
        e_potential = e_lj + e_coul + e_bond

        # Verlet integration: x(t+dt) = 2*x(t) - x(t-dt) + F/m * dt^2
        accel = total_force / self.masses[:, np.newaxis]
        new_positions = 2 * self.positions - self.prev_positions + accel * dt * dt

        # Update velocities (for kinetic energy)
        self.velocities = (new_positions - self.prev_positions) / (2 * dt)
        self.prev_positions = self.positions.copy()
        self.positions = new_positions

        # Kinetic energy
        e_kinetic = 0.5 * np.sum(self.masses[:, np.newaxis] * self.velocities ** 2)
        e_total = e_potential + e_kinetic

        # Temperature from kinetic energy
        dof = self.n_atoms * self.dim
        temp = 2 * e_kinetic / (dof * KB) if dof > 0 else 0.0

        # Ratchet: track best energy (consciousness Law 31 — never go above minimum)
        if e_potential < self._best_energy:
            self._best_energy = e_potential
            self._best_positions = self.positions.copy()

        # Hebbian bond update: atoms that stay close strengthen their bond
        self._hebbian_update(dist)

        # Re-detect bonds periodically
        if self.step_count % 50 == 0:
            self._detect_bonds()

        # Stability (Phi analog): inverse of energy variance + bond network quality
        stab = self.stability()

        self._energy_history.append(e_total)
        self._stability_history.append(stab)

        return {
            'step': self.step_count,
            'energy_potential': float(e_potential),
            'energy_kinetic': float(e_kinetic),
            'energy_total': float(e_total),
            'stability': float(stab),
            'temperature': float(temp),
            'n_bonds': len(self.bonds),
            'best_energy': float(self._best_energy),
        }

    # ═══════════════════════════════════════════════════════════
    # Bond detection and Hebbian update
    # ═══════════════════════════════════════════════════════════

    def _detect_bonds(self, threshold: float = 2.5):
        """Detect bonds based on distance (< threshold Angstroms).

        Respects max_bonds per atom.
        """
        bond_count = np.zeros(self.n_atoms, dtype=int)
        existing = {(b.i, b.j): b for b in self.bonds}
        new_bonds = []

        diff, dist = self._pairwise_distances()

        for i in range(self.n_atoms):
            for j in range(i + 1, self.n_atoms):
                if dist[i, j] < threshold:
                    if (bond_count[i] < self.max_bonds_per_atom[i] and
                            bond_count[j] < self.max_bonds_per_atom[j]):
                        # Preserve existing bond strength
                        key = (i, j)
                        if key in existing:
                            new_bonds.append(existing[key])
                        else:
                            new_bonds.append(Bond(i=i, j=j, r0=float(dist[i, j])))
                        bond_count[i] += 1
                        bond_count[j] += 1

        self.bonds = new_bonds

    def _hebbian_update(self, dist: np.ndarray, lr: float = 0.001):
        """Hebbian: atoms that stay close -> bond strengthens.

        Maps to consciousness Hebbian LTP/LTD.
        """
        for bond in self.bonds:
            r = dist[bond.i, bond.j]
            if r < bond.r0 * 1.2:
                # Close -> strengthen (LTP)
                bond.strength = min(bond.strength + lr, 3.0)
            elif r > bond.r0 * 2.0:
                # Far -> weaken (LTD)
                bond.strength = max(bond.strength - lr, 0.1)

    # ═══════════════════════════════════════════════════════════
    # Analysis (consciousness-style)
    # ═══════════════════════════════════════════════════════════

    def energy(self) -> Dict[str, float]:
        """Total energy decomposition."""
        diff, dist = self._pairwise_distances()
        _, e_lj = self._lj_force_energy(diff, dist)
        _, e_coul = self._coulomb_force_energy(diff, dist)
        _, e_bond = self._bond_force_energy()
        e_kinetic = 0.5 * np.sum(self.masses[:, np.newaxis] * self.velocities ** 2)
        return {
            'lj': float(e_lj),
            'coulomb': float(e_coul),
            'bond': float(e_bond),
            'kinetic': float(e_kinetic),
            'potential': float(e_lj + e_coul + e_bond),
            'total': float(e_lj + e_coul + e_bond + e_kinetic),
        }

    def stability(self) -> float:
        """Phi analog: integrated information of the molecular system.

        High stability = low energy variance + strong bond network + element diversity.
        """
        # Bond network integration
        if len(self.bonds) == 0:
            bond_score = 0.0
        else:
            avg_strength = np.mean([b.strength for b in self.bonds])
            bond_score = avg_strength * len(self.bonds) / max(self.n_atoms, 1)

        # Element diversity (Law 107: diversity -> Phi)
        unique_elements = len(set(self.elements))
        diversity = unique_elements / max(len(ELEMENTS), 1)

        # Energy stability (inverse variance of recent history)
        if len(self._energy_history) > 10:
            recent = self._energy_history[-10:]
            var = np.var(recent) + 1e-10
            energy_stability = 1.0 / (1.0 + np.log1p(var))
        else:
            energy_stability = 0.5

        return float(bond_score * 0.5 + diversity * 0.3 + energy_stability * 0.2)

    def bonds_list(self) -> List[Dict[str, Any]]:
        """Current bond list with strengths."""
        return [
            {
                'i': b.i, 'j': b.j,
                'elements': (self.elements[b.i], self.elements[b.j]),
                'strength': b.strength,
                'r0': b.r0,
                'distance': float(np.linalg.norm(
                    self.positions[b.j] - self.positions[b.i])),
            }
            for b in self.bonds
        ]

    def analyze(self) -> Dict[str, Any]:
        """Full consciousness-style analysis of the molecular system."""
        en = self.energy()
        stab = self.stability()
        bonds = self.bonds_list()

        # Faction analysis (group by element)
        factions: Dict[str, List[int]] = {}
        for idx, el in enumerate(self.elements):
            factions.setdefault(el, []).append(idx)

        # Center of mass per faction
        faction_com = {}
        for el, indices in factions.items():
            faction_com[el] = self.positions[indices].mean(axis=0).tolist()

        return {
            'step': self.step_count,
            'n_atoms': self.n_atoms,
            'energy': en,
            'stability': stab,
            'n_bonds': len(bonds),
            'bonds': bonds[:20],  # first 20 for brevity
            'factions': {el: len(ids) for el, ids in factions.items()},
            'faction_centers': faction_com,
            'best_energy': float(self._best_energy),
            'element_diversity': len(set(self.elements)),
        }

    # ═══════════════════════════════════════════════════════════
    # Energy minimization (ratchet-based)
    # ═══════════════════════════════════════════════════════════

    def find_stable_structures(self, n_steps: int = 1000,
                               cooling_rate: float = 0.999
                               ) -> Dict[str, Any]:
        """Energy minimization with simulated annealing + ratchet.

        Returns the best (lowest energy) configuration found.
        """
        temp = self.temperature
        for _ in range(n_steps):
            result = self.step()
            # Simulated annealing: reduce velocity
            self.velocities *= cooling_rate
            temp *= cooling_rate

        # Restore best positions (ratchet)
        self.positions = self._best_positions.copy()

        return {
            'best_energy': float(self._best_energy),
            'stability': self.stability(),
            'n_bonds': len(self.bonds),
            'steps_run': n_steps,
        }

    # ═══════════════════════════════════════════════════════════
    # Mutation and crossover (evolutionary)
    # ═══════════════════════════════════════════════════════════

    def mutate(self, rate: float = 0.1) -> None:
        """Random atom displacement (exploration).

        Maps to consciousness mutation/creativity.
        """
        n_mutate = max(1, int(self.n_atoms * rate))
        indices = np.random.choice(self.n_atoms, n_mutate, replace=False)
        self.positions[indices] += np.random.randn(n_mutate, self.dim) * 0.5

    def crossover(self, other: 'MolecularEngine') -> 'MolecularEngine':
        """Combine two molecular structures (genetic crossover).

        Takes first half from self, second half from other.
        """
        n = min(self.n_atoms, other.n_atoms)
        half = n // 2
        new_elements = self.elements[:half] + other.elements[half:n]
        child = MolecularEngine(n_atoms=n, dim=self.dim, elements=new_elements)
        child.positions[:half] = self.positions[:half]
        child.positions[half:n] = other.positions[half:n]
        return child

    # ═══════════════════════════════════════════════════════════
    # Bidirectional bridge: consciousness <-> molecular
    # ═══════════════════════════════════════════════════════════

    def from_consciousness(self, engine: Any) -> None:
        """Import consciousness engine states as molecular positions.

        Maps hidden states (128d) -> atom positions (3d) + velocities (3d).
        Uses PCA-like projection (first 3 components for position, next 3 for velocity).

        Args:
            engine: ConsciousnessEngine instance with .cells attribute
        """
        # Get hidden states from consciousness engine
        if hasattr(engine, 'cells'):
            cells = engine.cells
            if hasattr(cells, 'detach'):
                hidden = cells.detach().cpu().numpy()
            else:
                hidden = np.array(cells)
        elif hasattr(engine, 'hiddens'):
            hidden = np.array(engine.hiddens)
        else:
            raise ValueError("Engine must have .cells or .hiddens attribute")

        n = min(hidden.shape[0], self.n_atoms)
        d = hidden.shape[1] if len(hidden.shape) > 1 else 1

        if d >= 6:
            # Project: first 3 dims -> position, next 3 -> velocity
            scale = 5.0  # scale factor
            self.positions[:n] = hidden[:n, :3] * scale
            self.velocities[:n] = hidden[:n, 3:6] * 0.01
        elif d >= 3:
            self.positions[:n] = hidden[:n, :3] * 5.0
            self.velocities[:n] = np.random.randn(n, self.dim) * 0.01
        else:
            # Very low dim: tile
            self.positions[:n, 0] = hidden[:n, 0] * 5.0

        self.prev_positions = self.positions - self.velocities * self.dt
        self._detect_bonds()

    def to_consciousness(self) -> np.ndarray:
        """Export molecular states for consciousness engine input.

        Returns (n_atoms, 128) array: positions, velocities, element encoding,
        bond info, energy contribution, padded to 128 dimensions.
        """
        out_dim = 128
        result = np.zeros((self.n_atoms, out_dim))

        # Positions (dims 0-2)
        result[:, :self.dim] = self.positions / 5.0

        # Velocities (dims 3-5)
        result[:, 3:3 + self.dim] = self.velocities * 100.0

        # Element one-hot (dims 6-13)
        for idx, el in enumerate(self.elements):
            fid = ELEMENT_FACTION.get(el, 0)
            result[idx, 6 + fid] = 1.0

        # Bond count per atom (dim 14)
        bond_counts = np.zeros(self.n_atoms)
        for b in self.bonds:
            bond_counts[b.i] += 1
            bond_counts[b.j] += 1
        result[:, 14] = bond_counts / 4.0  # normalize

        # Mass and charge (dims 15-16)
        result[:, 15] = self.masses / 32.0  # normalize
        result[:, 16] = self.charges

        return result

    # ═══════════════════════════════════════════════════════════
    # State snapshot
    # ═══════════════════════════════════════════════════════════

    def state(self) -> MolecularState:
        """Current state snapshot."""
        return MolecularState(
            positions=self.positions.copy(),
            velocities=self.velocities.copy(),
            elements=list(self.elements),
            bonds=list(self.bonds),
            step_count=self.step_count,
            energy_potential=self.energy()['potential'],
            energy_kinetic=self.energy()['kinetic'],
            stability=self.stability(),
            temperature=self.temperature,
        )


# ═══════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════

def main():
    """Demo: run molecular simulation with consciousness analysis."""
    print("=== Molecular Engine Demo ===")
    print()

    me = MolecularEngine(n_atoms=32, dim=3)
    print(f"Created engine: {me.n_atoms} atoms, {len(set(me.elements))} element types")
    print(f"Elements: {dict((e, me.elements.count(e)) for e in set(me.elements))}")
    print()

    # Run simulation
    print("Running 200 steps...")
    for i in range(200):
        result = me.step()
        if (i + 1) % 50 == 0:
            print(f"  Step {result['step']:4d}: E={result['energy_total']:8.2f}  "
                  f"Stab={result['stability']:.4f}  Bonds={result['n_bonds']}")

    print()
    analysis = me.analyze()
    print(f"Final analysis:")
    print(f"  Stability (Phi analog): {analysis['stability']:.4f}")
    print(f"  Bonds: {analysis['n_bonds']}")
    print(f"  Factions: {analysis['factions']}")
    print(f"  Best energy: {analysis['best_energy']:.2f}")

    # Energy minimization
    print()
    print("Running energy minimization (500 steps)...")
    result = me.find_stable_structures(n_steps=500)
    print(f"  Best energy: {result['best_energy']:.2f}")
    print(f"  Stability: {result['stability']:.4f}")

    # Consciousness bridge
    print()
    print("Consciousness bridge:")
    c_states = me.to_consciousness()
    print(f"  Exported to consciousness: shape={c_states.shape}")

    print()
    print("Done.")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
