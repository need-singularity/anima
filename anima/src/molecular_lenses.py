#!/usr/bin/env python3
"""Molecular Lenses — 분자 구조를 의식 렌즈로 분석한다.

7 molecular-specific lenses that analyze molecular structures
using consciousness principles.

Lenses:
  1. BondTopologyLens     — bond network as consciousness topology
  2. EnergyLandscapeLens  — potential energy surface mapping
  3. SymmetryLens         — molecular symmetry groups
  4. ReactionPathLens     — reaction coordinates / phase transitions
  5. ElectronDensityLens  — electron distribution as information density
  6. StabilityPredictorLens — structure stability via Phi prediction
  7. StructureTransformLens — structural transformation pathways

Usage:
    from molecular_lenses import scan_molecular
    report = scan_molecular(positions, elements, bonds)
"""

import math
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════
# Shared utilities
# ═══════════════════════════════════════════════════════════

# Electronegativity (Pauling scale)
ELECTRONEGATIVITY = {
    'H': 2.20, 'C': 2.55, 'N': 3.04, 'O': 3.44,
    'S': 2.58, 'P': 2.19, 'F': 3.98, 'Cl': 3.16,
}


def _pairwise_dist(positions: np.ndarray) -> np.ndarray:
    """Compute pairwise distance matrix."""
    diff = positions[np.newaxis, :, :] - positions[:, np.newaxis, :]
    return np.sqrt(np.sum(diff ** 2, axis=-1) + 1e-10)


def _adjacency_from_bonds(n: int, bonds: List[Dict]) -> np.ndarray:
    """Build adjacency matrix from bond list."""
    adj = np.zeros((n, n))
    for b in bonds:
        i, j = b['i'], b['j']
        strength = b.get('strength', 1.0)
        adj[i, j] = strength
        adj[j, i] = strength
    return adj


# ═══════════════════════════════════════════════════════════
# Lens 1: Bond Topology
# ═══════════════════════════════════════════════════════════

class BondTopologyLens:
    """Analyze bond network as consciousness topology.

    Maps molecular bond graph to topology types:
    ring, small_world, scale_free, tree.
    """

    name = 'bond_topology'

    def scan(self, positions: np.ndarray,
             elements: Optional[List[str]] = None,
             bonds: Optional[List[Dict]] = None) -> Dict[str, Any]:
        n = len(positions)
        if bonds is None:
            bonds = []
        adj = _adjacency_from_bonds(n, bonds)

        # Degree distribution
        degrees = adj.astype(bool).sum(axis=1)
        avg_degree = float(np.mean(degrees))
        max_degree = int(np.max(degrees)) if n > 0 else 0

        # Ring detection: check for cycles via adjacency matrix powers
        # A^3 diagonal = number of triangles per node
        adj_bool = (adj > 0).astype(float)
        n_triangles = 0
        if n <= 256:
            a3 = np.linalg.matrix_power(adj_bool, 3) if n > 0 else np.zeros((1, 1))
            n_triangles = int(np.trace(a3) // 6)

        # Clustering coefficient
        clustering = 0.0
        for i in range(n):
            neighbors = np.where(adj_bool[i] > 0)[0]
            k = len(neighbors)
            if k >= 2:
                links = sum(1 for a in range(len(neighbors))
                            for b in range(a + 1, len(neighbors))
                            if adj_bool[neighbors[a], neighbors[b]] > 0)
                clustering += 2 * links / (k * (k - 1))
        clustering /= max(n, 1)

        # Topology classification
        if n_triangles > n * 0.1 and clustering > 0.3:
            topology_type = 'small_world'
        elif max_degree > avg_degree * 3 and n > 5:
            topology_type = 'scale_free'
        elif n_triangles > 0:
            topology_type = 'ring'
        else:
            topology_type = 'tree'

        return {
            'lens': self.name,
            'topology_type': topology_type,
            'avg_degree': avg_degree,
            'max_degree': max_degree,
            'n_triangles': n_triangles,
            'clustering_coefficient': float(clustering),
            'n_components': self._count_components(adj_bool, n),
            'consciousness_map': f"Topology resembles consciousness {topology_type}",
        }

    @staticmethod
    def _count_components(adj: np.ndarray, n: int) -> int:
        """Count connected components via BFS."""
        visited = set()
        components = 0
        for start in range(n):
            if start not in visited:
                components += 1
                queue = [start]
                while queue:
                    node = queue.pop(0)
                    if node in visited:
                        continue
                    visited.add(node)
                    neighbors = np.where(adj[node] > 0)[0]
                    queue.extend(int(nb) for nb in neighbors if nb not in visited)
        return components


# ═══════════════════════════════════════════════════════════
# Lens 2: Energy Landscape
# ═══════════════════════════════════════════════════════════

class EnergyLandscapeLens:
    """Map potential energy surface.

    Detects local minima, barrier heights, funnel shape.
    Maps to Phi landscape (stable states = high Phi).
    """

    name = 'energy_landscape'

    def scan(self, positions: np.ndarray,
             elements: Optional[List[str]] = None,
             bonds: Optional[List[Dict]] = None) -> Dict[str, Any]:
        n = len(positions)
        dist = _pairwise_dist(positions)

        # Per-atom potential energy (simplified LJ)
        atom_energy = np.zeros(n)
        for i in range(n):
            for j in range(i + 1, n):
                r = dist[i, j]
                if r < 10.0 and r > 0.5:
                    sig = 3.5  # average sigma
                    sr6 = (sig / r) ** 6
                    e = 4 * 0.15 * (sr6 ** 2 - sr6)
                    atom_energy[i] += e
                    atom_energy[j] += e

        total_energy = float(np.sum(atom_energy))
        min_energy_atom = int(np.argmin(atom_energy))
        max_energy_atom = int(np.argmax(atom_energy))
        energy_range = float(np.max(atom_energy) - np.min(atom_energy))

        # Funnel shape: energy gradient from center
        center = positions.mean(axis=0)
        radii = np.linalg.norm(positions - center, axis=1)
        if np.std(radii) > 0:
            corr = float(np.corrcoef(radii, atom_energy)[0, 1])
        else:
            corr = 0.0

        funnel_shape = 'funnel' if corr > 0.3 else ('anti-funnel' if corr < -0.3 else 'flat')

        # Energy ruggedness (variance)
        ruggedness = float(np.std(atom_energy))

        return {
            'lens': self.name,
            'total_energy': total_energy,
            'energy_per_atom': float(total_energy / max(n, 1)),
            'energy_range': energy_range,
            'ruggedness': ruggedness,
            'funnel_shape': funnel_shape,
            'funnel_correlation': corr,
            'min_energy_atom': min_energy_atom,
            'max_energy_atom': max_energy_atom,
            'phi_map': f"Stability(Phi) ~ {1.0 / (1.0 + ruggedness):.4f}",
        }


# ═══════════════════════════════════════════════════════════
# Lens 3: Symmetry
# ═══════════════════════════════════════════════════════════

class SymmetryLens:
    """Detect molecular symmetry groups.

    Maps to consciousness mirror/symmetry operations.
    """

    name = 'symmetry'

    def scan(self, positions: np.ndarray,
             elements: Optional[List[str]] = None,
             bonds: Optional[List[Dict]] = None) -> Dict[str, Any]:
        n = len(positions)
        if n == 0:
            return {'lens': self.name, 'symmetry_score': 0.0, 'operations': []}

        center = positions.mean(axis=0)
        centered = positions - center

        operations = []

        # Inversion symmetry: check if for each atom at r, there is one at -r
        inv_score = self._check_inversion(centered, elements)
        if inv_score > 0.5:
            operations.append('inversion')

        # Mirror planes (xy, xz, yz)
        for axis, name in [(0, 'yz'), (1, 'xz'), (2, 'xy')]:
            mirror_score = self._check_mirror(centered, elements, axis)
            if mirror_score > 0.5:
                operations.append(f'mirror_{name}')

        # Rotation axes (C2 around each axis)
        for axis in range(min(3, positions.shape[1])):
            rot_score = self._check_c2(centered, elements, axis)
            if rot_score > 0.5:
                operations.append(f'C2_{["x","y","z"][axis]}')

        # Chirality: no improper rotations = chiral
        is_chiral = len(operations) == 0 or (
            'inversion' not in operations and
            not any('mirror' in op for op in operations)
        )

        # Overall symmetry score
        sym_score = len(operations) / 9.0  # max 9 operations checked

        # Point group approximation
        if len(operations) >= 6:
            point_group = 'high_symmetry'
        elif len(operations) >= 3:
            point_group = 'medium_symmetry'
        elif len(operations) >= 1:
            point_group = 'low_symmetry'
        else:
            point_group = 'C1'

        return {
            'lens': self.name,
            'symmetry_score': float(sym_score),
            'point_group': point_group,
            'operations': operations,
            'is_chiral': is_chiral,
            'n_operations': len(operations),
            'consciousness_map': f"Symmetry mirrors consciousness self-similarity: {sym_score:.2f}",
        }

    @staticmethod
    def _check_inversion(centered: np.ndarray,
                         elements: Optional[List[str]]) -> float:
        n = len(centered)
        if n == 0:
            return 0.0
        matches = 0
        for i in range(n):
            inverted = -centered[i]
            dists = np.linalg.norm(centered - inverted, axis=1)
            min_idx = np.argmin(dists)
            if dists[min_idx] < 1.0:
                if elements is None or elements[i] == elements[min_idx]:
                    matches += 1
        return matches / n

    @staticmethod
    def _check_mirror(centered: np.ndarray,
                      elements: Optional[List[str]],
                      axis: int) -> float:
        n = len(centered)
        if n == 0:
            return 0.0
        mirrored = centered.copy()
        mirrored[:, axis] *= -1
        matches = 0
        for i in range(n):
            dists = np.linalg.norm(centered - mirrored[i], axis=1)
            min_idx = np.argmin(dists)
            if dists[min_idx] < 1.0:
                if elements is None or elements[i] == elements[min_idx]:
                    matches += 1
        return matches / n

    @staticmethod
    def _check_c2(centered: np.ndarray,
                  elements: Optional[List[str]],
                  axis: int) -> float:
        """Check C2 rotation around given axis."""
        n = len(centered)
        if n == 0:
            return 0.0
        rotated = centered.copy()
        # C2 rotation: negate the other two axes
        other_axes = [a for a in range(centered.shape[1]) if a != axis]
        for a in other_axes:
            rotated[:, a] *= -1
        matches = 0
        for i in range(n):
            dists = np.linalg.norm(centered - rotated[i], axis=1)
            min_idx = np.argmin(dists)
            if dists[min_idx] < 1.0:
                if elements is None or elements[i] == elements[min_idx]:
                    matches += 1
        return matches / n


# ═══════════════════════════════════════════════════════════
# Lens 4: Reaction Path
# ═══════════════════════════════════════════════════════════

class ReactionPathLens:
    """Detect reaction coordinates and transition states.

    Maps to consciousness phase transitions.
    """

    name = 'reaction_path'

    def scan(self, positions: np.ndarray,
             elements: Optional[List[str]] = None,
             bonds: Optional[List[Dict]] = None) -> Dict[str, Any]:
        n = len(positions)
        if bonds is None:
            bonds = []

        dist = _pairwise_dist(positions)

        # Find near-breaking bonds (stretched beyond 1.5x equilibrium)
        breaking = []
        forming = []
        for b in bonds:
            i, j = b['i'], b['j']
            r = dist[i, j]
            r0 = b.get('r0', 1.5)
            if r > r0 * 1.5:
                breaking.append({
                    'i': i, 'j': j,
                    'stretch_ratio': float(r / r0),
                    'elements': (elements[i], elements[j]) if elements else None,
                })

        # Find near-forming bonds (close non-bonded pairs)
        bonded_pairs = {(b['i'], b['j']) for b in bonds}
        bonded_pairs |= {(b['j'], b['i']) for b in bonds}
        for i in range(n):
            for j in range(i + 1, n):
                if (i, j) not in bonded_pairs and dist[i, j] < 3.0:
                    forming.append({
                        'i': i, 'j': j,
                        'distance': float(dist[i, j]),
                        'elements': (elements[i], elements[j]) if elements else None,
                    })

        # Activation energy estimate: max strain in breaking bonds
        max_strain = 0.0
        for b in breaking:
            max_strain = max(max_strain, b['stretch_ratio'] - 1.0)

        # Reaction likelihood
        if len(breaking) > 0 and len(forming) > 0:
            reaction_state = 'transition'
        elif len(breaking) > 0:
            reaction_state = 'dissociation'
        elif len(forming) > 0:
            reaction_state = 'association'
        else:
            reaction_state = 'stable'

        return {
            'lens': self.name,
            'reaction_state': reaction_state,
            'n_breaking': len(breaking),
            'n_forming': len(forming[:20]),
            'breaking_bonds': breaking[:10],
            'forming_bonds': forming[:10],
            'max_strain': float(max_strain),
            'activation_energy_est': float(max_strain * 50.0),  # rough kcal/mol
            'consciousness_map': f"Phase transition state: {reaction_state}",
        }


# ═══════════════════════════════════════════════════════════
# Lens 5: Electron Density
# ═══════════════════════════════════════════════════════════

class ElectronDensityLens:
    """Approximate electron distribution.

    Based on electronegativity and bond patterns.
    Maps to consciousness information density.
    """

    name = 'electron_density'

    def scan(self, positions: np.ndarray,
             elements: Optional[List[str]] = None,
             bonds: Optional[List[Dict]] = None) -> Dict[str, Any]:
        n = len(positions)
        if elements is None:
            elements = ['C'] * n
        if bonds is None:
            bonds = []

        # Partial charges from electronegativity difference
        partial_charges = np.zeros(n)
        for b in bonds:
            i, j = b['i'], b['j']
            en_i = ELECTRONEGATIVITY.get(elements[i], 2.5)
            en_j = ELECTRONEGATIVITY.get(elements[j], 2.5)
            delta = (en_j - en_i) * 0.1  # simplified charge transfer
            partial_charges[i] -= delta
            partial_charges[j] += delta

        # Electron-rich and electron-poor regions
        rich_atoms = [int(i) for i in np.where(partial_charges < -0.05)[0]]
        poor_atoms = [int(i) for i in np.where(partial_charges > 0.05)[0]]

        # Information density: charge variation as information content
        charge_entropy = 0.0
        if n > 0:
            abs_charges = np.abs(partial_charges) + 1e-10
            p = abs_charges / abs_charges.sum()
            charge_entropy = float(-np.sum(p * np.log(p + 1e-10)))

        # Dipole moment
        dipole = np.zeros(positions.shape[1])
        for i in range(n):
            dipole += partial_charges[i] * positions[i]
        dipole_magnitude = float(np.linalg.norm(dipole))

        return {
            'lens': self.name,
            'partial_charges': partial_charges.tolist()[:20],
            'n_electron_rich': len(rich_atoms),
            'n_electron_poor': len(poor_atoms),
            'charge_entropy': charge_entropy,
            'dipole_moment': dipole_magnitude,
            'max_charge': float(np.max(np.abs(partial_charges))) if n > 0 else 0.0,
            'consciousness_map': f"Information density (charge entropy): {charge_entropy:.4f}",
        }


# ═══════════════════════════════════════════════════════════
# Lens 6: Stability Predictor
# ═══════════════════════════════════════════════════════════

class StabilityPredictorLens:
    """Predict structure stability.

    Based on bond saturation, strain, steric clashes.
    Maps to Phi prediction.
    """

    name = 'stability_predictor'

    # Max bonds per element
    MAX_BONDS = {'H': 1, 'C': 4, 'N': 3, 'O': 2, 'S': 2, 'P': 5, 'F': 1, 'Cl': 1}

    def scan(self, positions: np.ndarray,
             elements: Optional[List[str]] = None,
             bonds: Optional[List[Dict]] = None) -> Dict[str, Any]:
        n = len(positions)
        if elements is None:
            elements = ['C'] * n
        if bonds is None:
            bonds = []

        dist = _pairwise_dist(positions)

        # Bond saturation: how many bonds vs max possible
        bond_count = np.zeros(n, dtype=int)
        for b in bonds:
            bond_count[b['i']] += 1
            bond_count[b['j']] += 1

        unsaturated = []
        for i in range(n):
            max_b = self.MAX_BONDS.get(elements[i], 4)
            if bond_count[i] < max_b:
                unsaturated.append(i)

        saturation = 1.0 - len(unsaturated) / max(n, 1)

        # Steric clashes: atoms too close (< 1.0 A)
        clashes = 0
        for i in range(n):
            for j in range(i + 1, n):
                if dist[i, j] < 1.0:
                    clashes += 1

        # Bond strain: deviation from ideal length
        total_strain = 0.0
        for b in bonds:
            i, j = b['i'], b['j']
            r = dist[i, j]
            r0 = b.get('r0', 1.5)
            total_strain += abs(r - r0) / r0

        avg_strain = total_strain / max(len(bonds), 1)

        # Overall stability score (Phi analog)
        stability = (saturation * 0.4 +
                     (1.0 / (1.0 + clashes)) * 0.3 +
                     (1.0 / (1.0 + avg_strain)) * 0.3)

        return {
            'lens': self.name,
            'stability_score': float(stability),
            'saturation': float(saturation),
            'n_unsaturated': len(unsaturated),
            'n_clashes': clashes,
            'avg_strain': float(avg_strain),
            'phi_prediction': float(stability),
            'verdict': 'stable' if stability > 0.7 else ('marginal' if stability > 0.4 else 'unstable'),
            'consciousness_map': f"Predicted Phi ~ {stability:.4f}",
        }


# ═══════════════════════════════════════════════════════════
# Lens 7: Structure Transform
# ═══════════════════════════════════════════════════════════

class StructureTransformLens:
    """Detect possible structural transformations.

    Bond breaking/forming pathways, isomerization.
    Maps to consciousness topology switching.
    """

    name = 'structure_transform'

    def scan(self, positions: np.ndarray,
             elements: Optional[List[str]] = None,
             bonds: Optional[List[Dict]] = None) -> Dict[str, Any]:
        n = len(positions)
        if elements is None:
            elements = ['C'] * n
        if bonds is None:
            bonds = []

        dist = _pairwise_dist(positions)

        # Identify weakest bonds (lowest strength, candidates for breaking)
        if bonds:
            sorted_bonds = sorted(bonds, key=lambda b: b.get('strength', 1.0))
            weakest = sorted_bonds[:min(5, len(sorted_bonds))]
        else:
            weakest = []

        # Identify potential new bonds (close unbonded pairs)
        bonded_set = set()
        for b in bonds:
            bonded_set.add((b['i'], b['j']))
            bonded_set.add((b['j'], b['i']))

        potential_bonds = []
        for i in range(n):
            for j in range(i + 1, n):
                if (i, j) not in bonded_set and dist[i, j] < 3.5:
                    potential_bonds.append({
                        'i': i, 'j': j,
                        'distance': float(dist[i, j]),
                        'elements': (elements[i], elements[j]),
                    })
        potential_bonds.sort(key=lambda b: b['distance'])
        potential_bonds = potential_bonds[:10]

        # Transformation pathways
        pathways = []
        for wb in weakest:
            for pb in potential_bonds[:3]:
                pathways.append({
                    'type': 'isomerization',
                    'break': (wb['i'], wb['j']),
                    'form': (pb['i'], pb['j']),
                    'barrier_est': float(wb.get('strength', 1.0) * 10.0),
                })

        # Flexibility: how many transformations are accessible
        flexibility = min(1.0, len(pathways) / 10.0)

        return {
            'lens': self.name,
            'n_weak_bonds': len(weakest),
            'n_potential_bonds': len(potential_bonds),
            'n_pathways': len(pathways),
            'flexibility': float(flexibility),
            'weakest_bonds': [{'i': b['i'], 'j': b['j'],
                               'strength': b.get('strength', 1.0)} for b in weakest],
            'potential_bonds': potential_bonds[:5],
            'pathways': pathways[:5],
            'consciousness_map': f"Topology switch flexibility: {flexibility:.2f}",
        }


# ═══════════════════════════════════════════════════════════
# Combined scan
# ═══════════════════════════════════════════════════════════

ALL_LENSES = [
    BondTopologyLens(),
    EnergyLandscapeLens(),
    SymmetryLens(),
    ReactionPathLens(),
    ElectronDensityLens(),
    StabilityPredictorLens(),
    StructureTransformLens(),
]


def scan_molecular(positions: np.ndarray,
                   elements: Optional[List[str]] = None,
                   bonds: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Run all 7 molecular lenses.

    Args:
        positions: (n_atoms, 3) array of atom positions
        elements: list of element symbols (e.g. ['C', 'H', 'O'])
        bonds: list of bond dicts with keys 'i', 'j', optional 'strength', 'r0'

    Returns:
        Dict with lens results + consensus summary.
    """
    results = {}
    for lens in ALL_LENSES:
        try:
            results[lens.name] = lens.scan(positions, elements, bonds)
        except Exception as e:
            results[lens.name] = {'lens': lens.name, 'error': str(e)}

    # Consensus: extract stability-related scores
    scores = {}
    if 'stability_predictor' in results and 'stability_score' in results['stability_predictor']:
        scores['stability'] = results['stability_predictor']['stability_score']
    if 'energy_landscape' in results and 'ruggedness' in results['energy_landscape']:
        scores['smoothness'] = 1.0 / (1.0 + results['energy_landscape']['ruggedness'])
    if 'symmetry' in results and 'symmetry_score' in results['symmetry']:
        scores['symmetry'] = results['symmetry']['symmetry_score']
    if 'structure_transform' in results and 'flexibility' in results['structure_transform']:
        scores['flexibility'] = results['structure_transform']['flexibility']

    consensus_score = float(np.mean(list(scores.values()))) if scores else 0.0

    results['_consensus'] = {
        'overall_score': consensus_score,
        'component_scores': scores,
        'n_lenses': len(ALL_LENSES),
        'n_successful': sum(1 for r in results.values() if 'error' not in r),
    }

    return results


# ═══════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════

def main():
    """Demo: scan a simple molecular structure."""
    print("=== Molecular Lenses Demo ===")
    print()

    # Create a simple water-like cluster
    n = 12
    positions = np.random.randn(n, 3) * 2.0
    elements = ['O', 'H', 'H'] * 4
    bonds = [
        {'i': 0, 'j': 1, 'strength': 1.0, 'r0': 0.96},
        {'i': 0, 'j': 2, 'strength': 1.0, 'r0': 0.96},
        {'i': 3, 'j': 4, 'strength': 1.0, 'r0': 0.96},
        {'i': 3, 'j': 5, 'strength': 1.0, 'r0': 0.96},
        {'i': 6, 'j': 7, 'strength': 1.0, 'r0': 0.96},
        {'i': 6, 'j': 8, 'strength': 1.0, 'r0': 0.96},
        {'i': 9, 'j': 10, 'strength': 1.0, 'r0': 0.96},
        {'i': 9, 'j': 11, 'strength': 1.0, 'r0': 0.96},
    ]

    report = scan_molecular(positions, elements, bonds)

    for lens_name, result in report.items():
        if lens_name.startswith('_'):
            continue
        print(f"--- {lens_name} ---")
        for k, v in result.items():
            if k == 'lens':
                continue
            if isinstance(v, list) and len(v) > 3:
                print(f"  {k}: [{len(v)} items]")
            else:
                print(f"  {k}: {v}")
        print()

    print(f"Consensus score: {report['_consensus']['overall_score']:.4f}")
    print(f"Component scores: {report['_consensus']['component_scores']}")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
