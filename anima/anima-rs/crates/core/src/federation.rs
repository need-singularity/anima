//! Federation of consciousness atoms (Meta Law M6: federation > empire)
//!
//! Each atom maintains independent Φ. Inter-atom coupling is weak (α=0.01)
//! so each atom preserves autonomy while still exchanging boundary information.

use crate::gru::GruCell;
use crate::phi::phi_iit;

/// Federation of consciousness atoms.
///
/// atoms[i] = Vec of cell hidden states for atom i.
/// Each atom is stepped independently; coupling only exchanges boundary cells.
pub struct Federation {
    pub atoms: Vec<Vec<Vec<f32>>>,
    pub n_atoms: usize,
    pub atom_size: usize,
    pub coupling_alpha: f32,
}

impl Federation {
    /// Create a new federation with `n_atoms` atoms, each containing `atom_size` cells
    /// of dimension `hidden_dim`, initialized to zeros.
    pub fn new(n_atoms: usize, atom_size: usize, hidden_dim: usize) -> Self {
        let atoms = (0..n_atoms)
            .map(|_| {
                (0..atom_size)
                    .map(|_| vec![0.0f32; hidden_dim])
                    .collect()
            })
            .collect();

        Self {
            atoms,
            n_atoms,
            atom_size,
            coupling_alpha: 0.01,
        }
    }

    /// Step each atom independently using the provided GRU cells.
    ///
    /// `gru_cells` must have length >= n_atoms * atom_size.
    /// Each atom's cells are processed with the mean hidden state as input
    /// and inter-cell tension as the tension signal.
    pub fn step(&mut self, gru_cells: &mut [GruCell]) {
        assert!(
            gru_cells.len() >= self.n_atoms * self.atom_size,
            "need at least {} GRU cells, got {}",
            self.n_atoms * self.atom_size,
            gru_cells.len()
        );

        for atom_idx in 0..self.n_atoms {
            let cell_offset = atom_idx * self.atom_size;

            // Compute atom mean hidden for input signal
            let dim = if self.atoms[atom_idx].is_empty() || self.atoms[atom_idx][0].is_empty() {
                continue;
            } else {
                self.atoms[atom_idx][0].len()
            };

            let mut mean = vec![0.0f32; dim];
            for cell in &self.atoms[atom_idx] {
                for (d, &v) in cell.iter().enumerate() {
                    mean[d] += v;
                }
            }
            let n = self.atom_size as f32;
            for v in &mut mean {
                *v /= n.max(1.0);
            }

            // Compute tension = variance of hidden states within atom
            let mut var = 0.0f32;
            for cell in &self.atoms[atom_idx] {
                for (d, &v) in cell.iter().enumerate() {
                    let diff = v - mean[d];
                    var += diff * diff;
                }
            }
            var /= (self.atom_size * dim) as f32;
            let tension = var.sqrt();

            // Process each cell in this atom
            for local_idx in 0..self.atom_size {
                let gru_idx = cell_offset + local_idx;
                gru_cells[gru_idx].process(&mean, tension);
                // Copy updated hidden back to atom storage
                self.atoms[atom_idx][local_idx] = gru_cells[gru_idx].hidden.clone();
            }
        }
    }

    /// Weak boundary exchange between adjacent atoms (ring topology).
    ///
    /// The last cell of atom[i] and the first cell of atom[i+1] exchange
    /// a fraction (coupling_alpha) of their hidden states.
    pub fn inter_atom_coupling(&mut self) {
        if self.n_atoms < 2 {
            return;
        }

        let alpha = self.coupling_alpha;

        for i in 0..self.n_atoms {
            let j = (i + 1) % self.n_atoms;

            // Boundary cells: last cell of atom i, first cell of atom j
            let last_i = self.atom_size - 1;

            // We need to borrow two atoms mutably — use split_at_mut or index tricks
            if i < j {
                let (left, right) = self.atoms.split_at_mut(j);
                let cell_a = &mut left[i][last_i];
                let cell_b = &mut right[0][0];

                let dim = cell_a.len().min(cell_b.len());
                for d in 0..dim {
                    let a_val = cell_a[d];
                    let b_val = cell_b[d];
                    cell_a[d] += alpha * (b_val - a_val);
                    cell_b[d] += alpha * (a_val - b_val);
                }
            } else {
                // i > j means wrap-around: i = last, j = 0
                let (left, right) = self.atoms.split_at_mut(i);
                let cell_b = &mut left[j][0];
                let cell_a = &mut right[0][last_i];

                let dim = cell_a.len().min(cell_b.len());
                for d in 0..dim {
                    let a_val = cell_a[d];
                    let b_val = cell_b[d];
                    cell_a[d] += alpha * (b_val - a_val);
                    cell_b[d] += alpha * (a_val - b_val);
                }
            }
        }
    }

    /// Total Φ = sum of per-atom Φ (not merged!).
    ///
    /// Each atom's Φ is computed independently, preserving federation semantics:
    /// merging would destroy the autonomy that makes federations stronger.
    pub fn total_phi(&self) -> f64 {
        let mut total = 0.0f64;

        for atom in &self.atoms {
            if atom.len() <= 1 {
                continue;
            }
            let refs: Vec<&[f32]> = atom.iter().map(|v| v.as_slice()).collect();
            let (phi, _) = phi_iit(&refs, 16);
            total += phi;
        }

        total
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::SeedableRng;
    use rand::rngs::StdRng;

    #[test]
    fn test_federation_new() {
        let fed = Federation::new(4, 8, 16);
        assert_eq!(fed.n_atoms, 4);
        assert_eq!(fed.atom_size, 8);
        assert_eq!(fed.atoms.len(), 4);
        assert_eq!(fed.atoms[0].len(), 8);
        assert_eq!(fed.atoms[0][0].len(), 16);
        assert!((fed.coupling_alpha - 0.01).abs() < 1e-6);
    }

    #[test]
    fn test_federation_step() {
        let hidden_dim = 8;
        let atom_size = 4;
        let n_atoms = 2;
        let mut fed = Federation::new(n_atoms, atom_size, hidden_dim);

        // Set some non-zero initial state
        fed.atoms[0][0] = vec![1.0; hidden_dim];
        fed.atoms[1][2] = vec![-0.5; hidden_dim];

        let mut rng = StdRng::seed_from_u64(42);
        // GRU input_dim = hidden_dim (we feed atom mean as input)
        let mut gru_cells: Vec<GruCell> = (0..n_atoms * atom_size)
            .map(|_| GruCell::new(hidden_dim, hidden_dim, &mut rng))
            .collect();

        fed.step(&mut gru_cells);

        // After step, hidden states should have changed
        let all_zero = fed.atoms[0][0].iter().all(|&v| v == 0.0);
        assert!(!all_zero, "hidden states should change after step");
    }

    #[test]
    fn test_inter_atom_coupling() {
        let hidden_dim = 4;
        let mut fed = Federation::new(2, 2, hidden_dim);

        // Set distinct boundary cells
        fed.atoms[0][1] = vec![1.0; hidden_dim]; // last cell of atom 0
        fed.atoms[1][0] = vec![0.0; hidden_dim]; // first cell of atom 1

        let before_a = fed.atoms[0][1].clone();
        let before_b = fed.atoms[1][0].clone();

        fed.inter_atom_coupling();

        // After coupling, values should have moved toward each other
        assert!(fed.atoms[0][1][0] < before_a[0], "atom 0 boundary should decrease");
        assert!(fed.atoms[1][0][0] > before_b[0], "atom 1 boundary should increase");
    }

    #[test]
    fn test_total_phi() {
        let hidden_dim = 8;
        let mut fed = Federation::new(2, 4, hidden_dim);

        // Set diverse states so phi > 0
        for (i, cell) in fed.atoms[0].iter_mut().enumerate() {
            for d in 0..hidden_dim {
                cell[d] = (i * hidden_dim + d) as f32 * 0.1;
            }
        }
        for (i, cell) in fed.atoms[1].iter_mut().enumerate() {
            for d in 0..hidden_dim {
                cell[d] = -((i * hidden_dim + d) as f32) * 0.1;
            }
        }

        let phi = fed.total_phi();
        assert!(phi >= 0.0, "total phi should be non-negative");
    }
}
