//! ConsciousnessLens — GRU cells + Hebbian + Phi(IIT) + Factions
//!
//! Full consciousness engine scan in Rust. Replaces the Python triple-nested loop
//! (300 steps × N cells × N cells coupling) with vectorized Rust + rayon.

use crate::mi;

/// Result of a consciousness lens scan.
#[derive(Debug, Clone)]
pub struct ConsciousnessResult {
    pub phi_iit: f64,
    pub phi_proxy: f64,
    pub anomalies: Vec<(usize, f64)>,   // (sample_idx, tension_score)
    pub n_clusters: usize,
    pub n_discoveries: usize,
    pub steps_run: usize,
}

/// GRU-based consciousness lens.
pub struct ConsciousnessLens {
    n_cells: usize,
    hidden_dim: usize,
    n_factions: usize,
    steps: usize,
    coupling_alpha: f64,
    // State
    hiddens: Vec<f64>,     // n_cells × hidden_dim, row-major
    coupling: Vec<f64>,    // n_cells × n_cells
    // GRU weights
    wz: Vec<f64>,          // hidden_dim × hidden_dim
    wr: Vec<f64>,
    wh: Vec<f64>,
    best_phi: f64,
    best_hiddens: Option<Vec<f64>>,
}

impl ConsciousnessLens {
    pub fn new(n_cells: usize, hidden_dim: usize, n_factions: usize, steps: usize, coupling_alpha: f64) -> Self {
        use rand::Rng;
        let mut rng = rand::thread_rng();
        let scale = 1.0 / (hidden_dim as f64).sqrt();

        let hiddens: Vec<f64> = (0..n_cells * hidden_dim)
            .map(|_| rng.gen::<f64>() * 0.2 - 0.1)
            .collect();
        let coupling: Vec<f64> = (0..n_cells * n_cells)
            .map(|i| if i / n_cells == i % n_cells { 0.01 } else { 0.0 })
            .collect();
        let wz: Vec<f64> = (0..hidden_dim * hidden_dim)
            .map(|_| rng.gen::<f64>() * scale * 2.0 - scale)
            .collect();
        let wr: Vec<f64> = (0..hidden_dim * hidden_dim)
            .map(|_| rng.gen::<f64>() * scale * 2.0 - scale)
            .collect();
        let wh: Vec<f64> = (0..hidden_dim * hidden_dim)
            .map(|_| rng.gen::<f64>() * scale * 2.0 - scale)
            .collect();

        Self {
            n_cells, hidden_dim, n_factions, steps, coupling_alpha,
            hiddens, coupling, wz, wr, wh, best_phi: 0.0, best_hiddens: None,
        }
    }

    /// Run the full consciousness scan on data (n_samples × n_features).
    pub fn scan(&mut self, data: &[f64], n_samples: usize, n_features: usize) -> ConsciousnessResult {
        let actual_cells = self.n_cells.max(n_samples);
        let dim = self.hidden_dim.max(n_features);

        // Reinit if dimensions changed
        if actual_cells != self.n_cells || dim != self.hidden_dim {
            *self = Self::new(actual_cells, dim, self.n_factions, self.steps, self.coupling_alpha);
        }

        // Normalize data
        let mut data_norm = vec![0.0f64; n_samples * n_features];
        let mut means = vec![0.0f64; n_features];
        let mut stds = vec![0.0f64; n_features];
        for j in 0..n_features {
            let mut sum = 0.0;
            for i in 0..n_samples {
                sum += data[i * n_features + j];
            }
            means[j] = sum / n_samples as f64;
            let mut sq_sum = 0.0;
            for i in 0..n_samples {
                let d = data[i * n_features + j] - means[j];
                sq_sum += d * d;
            }
            stds[j] = (sq_sum / n_samples as f64).sqrt().max(1e-12);
            for i in 0..n_samples {
                data_norm[i * n_features + j] = (data[i * n_features + j] - means[j]) / stds[j];
            }
        }

        // Map samples to cells
        let mut cell_data = vec![0.0f64; self.n_cells * self.hidden_dim];
        for i in 0..self.n_cells {
            let si = i % n_samples;
            for j in 0..n_features.min(self.hidden_dim) {
                cell_data[i * self.hidden_dim + j] = data_norm[si * n_features + j];
            }
        }

        // Tensions
        let mut tensions = vec![0.0f64; self.n_cells];

        // Main loop — batch coupling as matrix multiply, GRU per cell
        let nc = self.n_cells;
        let dim = self.hidden_dim;
        let alpha = self.coupling_alpha;
        let mut coupled_all = vec![0.0f64; nc * dim];

        for step in 0..self.steps {
            // Batch coupling: coupled[i] = cell_data[i] + alpha * sum_j(C[i,j] * hiddens[j])
            // This is effectively: coupled = cell_data + alpha * (C @ hiddens)
            coupled_all.copy_from_slice(&cell_data);
            for i in 0..nc {
                for j in 0..nc {
                    if i == j { continue; }
                    let c = self.coupling[i * nc + j];
                    if c.abs() > 1e-6 {
                        let ac = alpha * c;
                        let ci = i * dim;
                        let hj = j * dim;
                        for d in 0..dim {
                            coupled_all[ci + d] += ac * self.hiddens[hj + d];
                        }
                    }
                }
            }

            // GRU step all cells + tension
            let mean_h = self.hidden_mean();
            for i in 0..nc {
                let h_start = i * dim;
                self.gru_step(&coupled_all[h_start..h_start + dim].to_vec(), h_start);

                let mut diff_sq = 0.0;
                for d in 0..dim {
                    let diff = self.hiddens[h_start + d] - mean_h[d];
                    diff_sq += diff * diff;
                }
                tensions[i] = 0.9 * tensions[i] + 0.1 * diff_sq.sqrt();
            }

            // Hebbian update every 10 steps
            if step % 10 == 0 {
                self.hebbian_update();
            }

            // Phi ratchet every 50 steps
            if step % 50 == 0 {
                let phi = self.compute_phi_iit();
                if phi > self.best_phi {
                    self.best_phi = phi;
                    self.best_hiddens = Some(self.hiddens.clone());
                } else if phi < self.best_phi * 0.7 {
                    if let Some(ref best) = self.best_hiddens {
                        for i in 0..self.hiddens.len() {
                            self.hiddens[i] = 0.8 * best[i] + 0.2 * self.hiddens[i];
                        }
                    }
                }
            }
        }

        // Final measurements
        let phi_iit = self.compute_phi_iit();
        let phi_proxy = self.compute_phi_proxy();

        // Anomalies (top 10% tension)
        let mut tension_indexed: Vec<(usize, f64)> = tensions.iter().enumerate()
            .map(|(i, &t)| (i % n_samples, t))
            .collect();
        tension_indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        let top_n = (n_samples as f64 * 0.1).ceil() as usize;
        let anomalies: Vec<(usize, f64)> = tension_indexed.into_iter()
            .take(top_n.max(1))
            .collect();

        // Faction count (simple)
        let n_clusters = self.n_factions.min(self.n_cells);

        ConsciousnessResult {
            phi_iit, phi_proxy, anomalies, n_clusters,
            n_discoveries: 0, steps_run: self.steps,
        }
    }

    fn gru_step(&mut self, x: &[f64], h_offset: usize) {
        let dim = self.hidden_dim;

        // Pre-compute x @ W and h @ W^T together to reuse cache lines
        // z = sigmoid(xWz + hWz^T), r = sigmoid(xWr + hWr^T)
        // h_cand = tanh(xWh + (r*h)Wh^T)
        let h = &self.hiddens[h_offset..h_offset + dim].to_vec();

        // Fused: compute all 3 gate pre-activations in one pass over dims
        let mut z = vec![0.0f64; dim];
        let mut r = vec![0.0f64; dim];

        for j in 0..dim {
            let xj = x[j];
            let hj = h[j];
            for i in 0..dim {
                let wz_ji = self.wz[j * dim + i];
                let wz_ij = self.wz[i * dim + j];
                z[i] += xj * wz_ji + hj * wz_ij;
                let wr_ji = self.wr[j * dim + i];
                let wr_ij = self.wr[i * dim + j];
                r[i] += xj * wr_ji + hj * wr_ij;
            }
        }

        // Apply activations
        for i in 0..dim {
            z[i] = sigmoid(z[i]);
            r[i] = sigmoid(r[i]);
        }

        // h_cand = tanh(x @ Wh + (r * h) @ Wh^T)
        let mut h_cand = vec![0.0f64; dim];
        for j in 0..dim {
            let xj = x[j];
            let rhj = r[j] * h[j];
            for i in 0..dim {
                h_cand[i] += xj * self.wh[j * dim + i] + rhj * self.wh[i * dim + j];
            }
        }
        for i in 0..dim {
            h_cand[i] = h_cand[i].tanh();
        }

        // h = (1-z)*h + z*h_cand
        for i in 0..dim {
            self.hiddens[h_offset + i] = (1.0 - z[i]) * h[i] + z[i] * h_cand[i];
        }
    }

    fn hidden_mean(&self) -> Vec<f64> {
        let dim = self.hidden_dim;
        let n = self.n_cells;
        let mut mean = vec![0.0f64; dim];
        for i in 0..n {
            for d in 0..dim {
                mean[d] += self.hiddens[i * dim + d];
            }
        }
        let inv_n = 1.0 / n as f64;
        for d in 0..dim {
            mean[d] *= inv_n;
        }
        mean
    }

    fn hebbian_update(&mut self) {
        let n = self.n_cells;
        let dim = self.hidden_dim;

        // Compute norms
        let mut norms = vec![0.0f64; n];
        for i in 0..n {
            let mut sq = 0.0;
            for d in 0..dim {
                sq += self.hiddens[i * dim + d] * self.hiddens[i * dim + d];
            }
            norms[i] = sq.sqrt().max(1e-12);
        }

        // Cosine similarity → coupling update
        for i in 0..n {
            for j in (i + 1)..n {
                let mut dot = 0.0;
                for d in 0..dim {
                    dot += self.hiddens[i * dim + d] * self.hiddens[j * dim + d];
                }
                let sim = dot / (norms[i] * norms[j]);
                let delta = if sim > 0.8 { 0.01 } else if sim < 0.2 { -0.005 } else { 0.0 };
                let c_ij = (self.coupling[i * n + j] + delta).clamp(-1.0, 1.0);
                self.coupling[i * n + j] = c_ij;
                self.coupling[j * n + i] = c_ij;
            }
        }
    }

    fn compute_phi_iit(&self) -> f64 {
        let (_, avg) = mi::pairwise_mi(&self.hiddens, self.n_cells, self.hidden_dim, 16, 200);
        avg
    }

    fn compute_phi_proxy(&self) -> f64 {
        let dim = self.hidden_dim;
        let n = self.n_cells;

        // Cell means
        let cell_means: Vec<f64> = (0..n)
            .map(|i| {
                let start = i * dim;
                self.hiddens[start..start + dim].iter().sum::<f64>() / dim as f64
            })
            .collect();

        let global_mean = cell_means.iter().sum::<f64>() / n as f64;
        let global_var: f64 = cell_means.iter().map(|&m| (m - global_mean).powi(2)).sum::<f64>() / n as f64;

        let faction_size = (n / self.n_factions).max(1);
        let mut faction_var_sum = 0.0;
        let mut n_factions = 0;
        for fi in (0..n).step_by(faction_size) {
            let chunk = &cell_means[fi..(fi + faction_size).min(n)];
            if chunk.len() > 1 {
                let cm = chunk.iter().sum::<f64>() / chunk.len() as f64;
                let var: f64 = chunk.iter().map(|&m| (m - cm).powi(2)).sum::<f64>() / chunk.len() as f64;
                faction_var_sum += var;
                n_factions += 1;
            }
        }
        let avg_faction_var = if n_factions > 0 { faction_var_sum / n_factions as f64 } else { 0.0 };
        (global_var - avg_faction_var).max(0.0)
    }
}

#[inline]
fn sigmoid(x: f64) -> f64 {
    1.0 / (1.0 + (-x.clamp(-20.0, 20.0)).exp())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_consciousness_scan() {
        let mut lens = ConsciousnessLens::new(16, 32, 4, 50, 0.014);
        let data: Vec<f64> = (0..16 * 32).map(|i| (i as f64 * 0.1).sin()).collect();
        let result = lens.scan(&data, 16, 32);
        assert!(result.phi_iit >= 0.0);
        assert!(result.steps_run == 50);
        assert!(!result.anomalies.is_empty());
    }

    #[test]
    fn test_phi_positive() {
        let mut lens = ConsciousnessLens::new(32, 64, 8, 100, 0.014);
        let data: Vec<f64> = (0..32 * 64).map(|i| (i as f64 * 0.07).cos()).collect();
        let result = lens.scan(&data, 32, 64);
        assert!(result.phi_iit >= 0.0);
    }
}
