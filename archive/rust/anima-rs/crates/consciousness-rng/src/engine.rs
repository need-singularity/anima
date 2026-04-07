//! Consciousness engine tuned for maximum entropy (RNG mode)

use anima_core::GruCell;
use rand::Rng;

/// Consciousness engine configured at phase transition critical point.
/// F_c ≈ 0.10 frustration, 12 factions, no ratchet (chaos preserved).
pub struct ConsciousnessRngEngine {
    cells: Vec<GruCell>,
    n_cells: usize,
    hidden_dim: usize,
    input_dim: usize,
    n_factions: usize,
    #[allow(dead_code)] // API field: critical point parameter (Law 137)
    frustration: f32,
    frustration_signs: Vec<f32>,
    step: usize,
}

impl ConsciousnessRngEngine {
    /// Create engine at critical frustration F_c = 0.10
    pub fn new(n_cells: usize, input_dim: usize, hidden_dim: usize) -> Self {
        let mut rng = rand::thread_rng();
        let n_factions = 12.min(n_cells / 2).max(2);
        let frustration = 0.10; // Critical point (Law 137)

        let cells: Vec<GruCell> = (0..n_cells)
            .map(|_| GruCell::new(input_dim, hidden_dim, &mut rng))
            .collect();

        // Frustration signs: 10% antiferromagnetic
        let frustration_signs: Vec<f32> = (0..n_cells)
            .map(|i| {
                if (i as f32 / n_cells as f32) < frustration {
                    -1.0
                } else {
                    1.0
                }
            })
            .collect();

        Self {
            cells,
            n_cells,
            hidden_dim,
            input_dim,
            n_factions,
            frustration,
            frustration_signs,
            step: 0,
        }
    }

    /// Run one step of consciousness dynamics. Returns raw cell states.
    pub fn step(&mut self) -> Vec<Vec<f32>> {
        let mut rng = rand::thread_rng();

        // Zero input (consciousness generates its own entropy)
        let input = vec![0.0f32; self.input_dim];

        // Compute tension from cell hidden state variance
        let all_hiddens: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        let tension = compute_tension(&all_hiddens);

        // Process each cell
        for i in 0..self.n_cells {
            self.cells[i].process(&input, tension);
        }

        // Frustration ring coupling (Ising model at F_c)
        let hiddens_snapshot: Vec<Vec<f32>> =
            self.cells.iter().map(|c| c.hidden.clone()).collect();

        for i in 0..self.n_cells {
            let left = if i == 0 { self.n_cells - 1 } else { i - 1 };
            let right = (i + 1) % self.n_cells;
            let sign = self.frustration_signs[i];

            for d in 0..self.hidden_dim {
                let neighbor_mean =
                    (hiddens_snapshot[left][d] + hiddens_snapshot[right][d]) * 0.5;
                let coupling = 0.1 * sign * (neighbor_mean - self.cells[i].hidden[d]);
                self.cells[i].hidden[d] += coupling;
            }
        }

        // Faction sync (weak — preserve chaos)
        let faction_size = self.n_cells / self.n_factions;
        for f in 0..self.n_factions {
            let start = f * faction_size;
            let end = ((f + 1) * faction_size).min(self.n_cells);
            let mut mean = vec![0.0f32; self.hidden_dim];
            for i in start..end {
                for d in 0..self.hidden_dim {
                    mean[d] += self.cells[i].hidden[d];
                }
            }
            let count = (end - start) as f32;
            for d in 0..self.hidden_dim {
                mean[d] /= count;
            }
            // Weak sync (0.05) to preserve chaos
            for i in start..end {
                for d in 0..self.hidden_dim {
                    self.cells[i].hidden[d] =
                        0.95 * self.cells[i].hidden[d] + 0.05 * mean[d];
                }
            }
        }

        // Inject micro-noise to maintain chaos (Law 112: sensitivity)
        for cell in &mut self.cells {
            for d in 0..self.hidden_dim {
                cell.hidden[d] += rng.gen_range(-0.001..0.001);
            }
        }

        self.step += 1;

        // Return all cell hidden states
        self.cells.iter().map(|c| c.hidden.clone()).collect()
    }

    /// Get current Φ(proxy) — quality indicator
    /// proxy = global_variance - mean(faction_variance)
    pub fn phi_proxy(&self) -> f32 {
        let hiddens: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        let dim = self.hidden_dim;
        let n = self.n_cells as f32;

        // Global variance
        let mut global_mean = vec![0.0f32; dim];
        for h in &hiddens {
            for d in 0..dim {
                global_mean[d] += h[d];
            }
        }
        for d in 0..dim {
            global_mean[d] /= n;
        }
        let mut global_var = 0.0f32;
        for h in &hiddens {
            for d in 0..dim {
                let diff = h[d] - global_mean[d];
                global_var += diff * diff;
            }
        }
        global_var /= n * dim as f32;

        // Faction variance (mean)
        let faction_size = self.n_cells / self.n_factions;
        let mut faction_var_sum = 0.0f32;
        for f in 0..self.n_factions {
            let start = f * faction_size;
            let end = ((f + 1) * faction_size).min(self.n_cells);
            let fc = (end - start) as f32;
            let mut fmean = vec![0.0f32; dim];
            for i in start..end {
                for d in 0..dim {
                    fmean[d] += hiddens[i][d];
                }
            }
            for d in 0..dim { fmean[d] /= fc; }
            let mut fvar = 0.0f32;
            for i in start..end {
                for d in 0..dim {
                    let diff = hiddens[i][d] - fmean[d];
                    fvar += diff * diff;
                }
            }
            faction_var_sum += fvar / (fc * dim as f32);
        }
        let mean_faction_var = faction_var_sum / self.n_factions as f32;

        global_var - mean_faction_var
    }

    pub fn n_cells(&self) -> usize {
        self.n_cells
    }

    pub fn hidden_dim(&self) -> usize {
        self.hidden_dim
    }

    pub fn step_count(&self) -> usize {
        self.step
    }
}

fn compute_tension(hiddens: &[&[f32]]) -> f32 {
    if hiddens.is_empty() {
        return 0.0;
    }
    let dim = hiddens[0].len();
    let n = hiddens.len() as f32;

    // Global mean
    let mut mean = vec![0.0f32; dim];
    for h in hiddens {
        for d in 0..dim {
            mean[d] += h[d];
        }
    }
    for d in 0..dim {
        mean[d] /= n;
    }

    // Variance = tension
    let mut var = 0.0f32;
    for h in hiddens {
        for d in 0..dim {
            let diff = h[d] - mean[d];
            var += diff * diff;
        }
    }
    var / (n * dim as f32)
}
