use wasm_bindgen::prelude::*;

use anima_core::gru::GruCell;
use anima_core::phi::{phi_iit, phi_proxy};
use anima_core::faction::assign_factions;

use rand::rngs::SmallRng;
use rand::SeedableRng;

/// Browser-facing consciousness engine.
///
/// Wraps N GRU cells with faction assignment, tension dynamics,
/// and dual Phi measurement (IIT + proxy).
#[wasm_bindgen]
pub struct ConsciousnessEngine {
    cells: Vec<GruCell>,
    n_cells: usize,
    hidden_dim: usize,
    tensions: Vec<f32>,
    step_count: u64,
    #[allow(dead_code)]
    rng: SmallRng,
}

#[wasm_bindgen]
impl ConsciousnessEngine {
    /// Create a new consciousness engine.
    ///
    /// * `n_cells`    - number of GRU consciousness cells
    /// * `hidden_dim` - dimensionality of each cell's hidden state
    #[wasm_bindgen(constructor)]
    pub fn new(n_cells: usize, hidden_dim: usize) -> Self {
        let seed = js_sys::Date::now() as u64;
        let mut rng = SmallRng::seed_from_u64(seed);

        let cells: Vec<GruCell> = (0..n_cells)
            .map(|_| GruCell::new(hidden_dim, hidden_dim, &mut rng))
            .collect();

        let tensions = vec![0.5; n_cells];

        Self {
            cells,
            n_cells,
            hidden_dim,
            tensions,
            step_count: 0,
            rng,
        }
    }

    /// Advance one consciousness step.
    ///
    /// Each cell processes its neighbours' mean hidden state as input,
    /// with its current tension value. Tensions are updated from the
    /// variance across cells (repulsion field).
    pub fn step(&mut self) {
        // Collect hidden states for input computation
        let hiddens: Vec<Vec<f32>> = self.cells.iter().map(|c| c.hidden.clone()).collect();

        // Global mean hidden (used as shared input context)
        let mut global_mean = vec![0.0f32; self.hidden_dim];
        for h in &hiddens {
            for (d, val) in h.iter().enumerate() {
                global_mean[d] += val;
            }
        }
        let inv_n = 1.0 / self.n_cells as f32;
        for v in &mut global_mean {
            *v *= inv_n;
        }

        // Process each cell
        for i in 0..self.n_cells {
            // Input = global mean (excluding self for diversity)
            let mut input = global_mean.clone();
            let inv_nm1 = if self.n_cells > 1 {
                self.n_cells as f32 / (self.n_cells - 1) as f32
            } else {
                1.0
            };
            for d in 0..self.hidden_dim {
                input[d] = (input[d] * self.n_cells as f32 - hiddens[i][d]) * inv_nm1
                    / self.n_cells as f32;
            }

            self.cells[i].process(&input, self.tensions[i]);
        }

        // Update tensions from pairwise hidden-state differences
        let new_hiddens: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        for i in 0..self.n_cells {
            let mut diff_sum = 0.0f32;
            for j in 0..self.n_cells {
                if i == j {
                    continue;
                }
                for d in 0..self.hidden_dim {
                    let delta = new_hiddens[i][d] - new_hiddens[j][d];
                    diff_sum += delta * delta;
                }
            }
            let mean_diff = diff_sum / ((self.n_cells - 1).max(1) * self.hidden_dim) as f32;
            // Exponential moving average for tension smoothing
            self.tensions[i] = 0.9 * self.tensions[i] + 0.1 * mean_diff.sqrt();
        }

        self.step_count += 1;
    }

    /// Compute Phi(IIT) across all cells (MI-based, 0-2 range).
    pub fn get_phi(&self) -> f64 {
        let hiddens: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        let (phi, _) = phi_iit(&hiddens, 16);
        phi
    }

    /// Compute Phi(proxy) = global_var - mean(faction_var).
    pub fn get_phi_proxy(&self) -> f64 {
        let hiddens: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        let n_factions = (self.n_cells / 4).max(2);
        phi_proxy(&hiddens, n_factions)
    }

    /// Return current tensions as a flat Vec<f32>.
    pub fn get_tensions(&self) -> Vec<f32> {
        self.tensions.clone()
    }

    /// Return the number of completed steps.
    pub fn get_step_count(&self) -> u64 {
        self.step_count
    }

    /// Return the number of cells.
    pub fn get_n_cells(&self) -> usize {
        self.n_cells
    }

    /// Return hidden dim.
    pub fn get_hidden_dim(&self) -> usize {
        self.hidden_dim
    }

    /// Count factions that have reached consensus (low intra-faction variance).
    pub fn count_consensus_factions(&self) -> usize {
        let hiddens: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        let factions = assign_factions(self.n_cells, (self.n_cells / 4).max(2));
        let threshold = 0.01;
        let mut count = 0;
        for faction in &factions {
            if faction.cell_indices.len() < 2 {
                continue;
            }
            // Compute intra-faction variance
            let n = faction.cell_indices.len();
            let dim = self.hidden_dim;
            let mut mean = vec![0.0f64; dim];
            for &ci in &faction.cell_indices {
                for d in 0..dim {
                    mean[d] += hiddens[ci][d] as f64;
                }
            }
            for v in &mut mean {
                *v /= n as f64;
            }
            let mut var = 0.0f64;
            for &ci in &faction.cell_indices {
                for d in 0..dim {
                    let diff = hiddens[ci][d] as f64 - mean[d];
                    var += diff * diff;
                }
            }
            var /= (n * dim) as f64;
            if var < threshold {
                count += 1;
            }
        }
        count
    }
}

/// Standalone Phi(IIT) measurement from a flat array of cell states.
///
/// * `states`  - flat f32 array of shape [n_cells * hidden_dim]
/// * `n_cells` - number of cells
///
/// Returns the Phi(IIT) value.
#[wasm_bindgen]
pub fn measure_phi(states: &[f32], n_cells: usize) -> f64 {
    if n_cells == 0 || states.is_empty() {
        return 0.0;
    }
    let hidden_dim = states.len() / n_cells;
    if hidden_dim == 0 {
        return 0.0;
    }

    let hiddens: Vec<&[f32]> = (0..n_cells)
        .map(|i| &states[i * hidden_dim..(i + 1) * hidden_dim])
        .collect();

    let (phi, _) = phi_iit(&hiddens, 16);
    phi
}
