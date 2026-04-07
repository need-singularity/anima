//! ConsciousnessLens — GRU cells + Hebbian + Phi(IIT) + Factions
//!
//! Full consciousness engine scan in Rust. Replaces the Python triple-nested loop
//! (300 steps × N cells × N cells coupling) with vectorized Rust + rayon.
//!
//! Optimizations applied:
//!   1. Zero-alloc GRU step (slices instead of .to_vec())
//!   2. Sparse coupling via non-zero index cache
//!   3. Cache-friendly 4-wide dot product in GRU gates
//!   4. Rayon-parallel Hebbian update (symmetric, read-then-write)

use crate::mi;
use crate::common;
use rayon::prelude::*;

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

/// Sparse coupling entry: (from, to, weight).
struct SparseEntry {
    i: usize,
    j: usize,
    w: f64,
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
    sparse_coupling: Vec<SparseEntry>, // non-zero entries cache
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

        let mut coupling = vec![0.0f64; n_cells * n_cells];
        let mut sparse_coupling = Vec::new();
        for i in 0..n_cells {
            coupling[i * n_cells + i] = 0.01;
            sparse_coupling.push(SparseEntry { i, j: i, w: 0.01 });
        }

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
            hiddens, coupling, sparse_coupling, wz, wr, wh,
            best_phi: 0.0, best_hiddens: None,
        }
    }

    /// Rebuild sparse coupling cache from dense matrix.
    fn rebuild_sparse(&mut self) {
        let nc = self.n_cells;
        self.sparse_coupling.clear();
        for i in 0..nc {
            for j in 0..nc {
                if i == j { continue; }
                let w = self.coupling[i * nc + j];
                if w.abs() > 1e-6 {
                    self.sparse_coupling.push(SparseEntry { i, j, w });
                }
            }
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

        // Normalize data using common utility
        let (means, vars) = common::mean_var(data, n_samples, n_features);
        let stds: Vec<f64> = vars.iter().map(|&v| v.sqrt().max(1e-12)).collect();
        let mut data_norm = vec![0.0f64; n_samples * n_features];
        common::normalize_zscore_into(data, n_samples, n_features, &means, &stds, &mut data_norm);

        // Map samples to cells
        let mut cell_data = vec![0.0f64; self.n_cells * self.hidden_dim];
        for i in 0..self.n_cells {
            let si = i % n_samples;
            let copy_len = n_features.min(self.hidden_dim);
            cell_data[i * self.hidden_dim..i * self.hidden_dim + copy_len]
                .copy_from_slice(&data_norm[si * n_features..si * n_features + copy_len]);
        }

        // Tensions
        let mut tensions = vec![0.0f64; self.n_cells];

        let nc = self.n_cells;
        let dim = self.hidden_dim;
        let alpha = self.coupling_alpha;
        let mut coupled_all = vec![0.0f64; nc * dim];

        // Scratch buffers for GRU (avoid per-step allocation)
        let mut gru_z = vec![0.0f64; dim];
        let mut gru_r = vec![0.0f64; dim];
        let mut gru_h_cand = vec![0.0f64; dim];

        for step in 0..self.steps {
            // Batch coupling using sparse entries (skip zero weights)
            coupled_all.copy_from_slice(&cell_data);
            for entry in &self.sparse_coupling {
                let ac = alpha * entry.w;
                let ci = entry.i * dim;
                let hj = entry.j * dim;
                // 4-wide unrolled accumulation
                let chunks = dim / 4;
                let rem = dim % 4;
                for c in 0..chunks {
                    let base = c * 4;
                    coupled_all[ci + base]     += ac * self.hiddens[hj + base];
                    coupled_all[ci + base + 1] += ac * self.hiddens[hj + base + 1];
                    coupled_all[ci + base + 2] += ac * self.hiddens[hj + base + 2];
                    coupled_all[ci + base + 3] += ac * self.hiddens[hj + base + 3];
                }
                let base = chunks * 4;
                for d in 0..rem {
                    coupled_all[ci + base + d] += ac * self.hiddens[hj + base + d];
                }
            }

            // GRU step all cells + tension (zero-alloc)
            let mean_h = self.hidden_mean();
            for i in 0..nc {
                let h_start = i * dim;
                self.gru_step_inplace(
                    &coupled_all[h_start..h_start + dim],
                    h_start,
                    &mut gru_z, &mut gru_r, &mut gru_h_cand,
                );

                let mut diff_sq = 0.0;
                for d in 0..dim {
                    let diff = self.hiddens[h_start + d] - mean_h[d];
                    diff_sq += diff * diff;
                }
                tensions[i] = 0.9 * tensions[i] + 0.1 * diff_sq.sqrt();
            }

            // Hebbian update every 10 steps
            if step % 10 == 0 {
                self.hebbian_update_parallel();
                self.rebuild_sparse();
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
        tension_indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
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

    /// Zero-allocation GRU step. Writes result directly into self.hiddens[h_offset..].
    /// z, r, h_cand are pre-allocated scratch buffers.
    fn gru_step_inplace(&mut self, x: &[f64], h_offset: usize,
                        z: &mut [f64], r: &mut [f64], h_cand: &mut [f64]) {
        let dim = self.hidden_dim;

        // Zero scratch buffers
        z.iter_mut().for_each(|v| *v = 0.0);
        r.iter_mut().for_each(|v| *v = 0.0);

        // Fused gate computation: z[i] += x[j]*Wz[j,i] + h[j]*Wz[i,j]
        //                          r[i] += x[j]*Wr[j,i] + h[j]*Wr[i,j]
        for j in 0..dim {
            let xj = x[j];
            let hj = self.hiddens[h_offset + j];
            let wz_row = j * dim;
            let wr_row = j * dim;
            // 4-wide inner loop
            let chunks = dim / 4;
            let rem = dim % 4;
            for c in 0..chunks {
                let i = c * 4;
                z[i]     += xj * self.wz[wz_row + i]     + hj * self.wz[i * dim + j];
                z[i + 1] += xj * self.wz[wz_row + i + 1] + hj * self.wz[(i + 1) * dim + j];
                z[i + 2] += xj * self.wz[wz_row + i + 2] + hj * self.wz[(i + 2) * dim + j];
                z[i + 3] += xj * self.wz[wz_row + i + 3] + hj * self.wz[(i + 3) * dim + j];

                r[i]     += xj * self.wr[wr_row + i]     + hj * self.wr[i * dim + j];
                r[i + 1] += xj * self.wr[wr_row + i + 1] + hj * self.wr[(i + 1) * dim + j];
                r[i + 2] += xj * self.wr[wr_row + i + 2] + hj * self.wr[(i + 2) * dim + j];
                r[i + 3] += xj * self.wr[wr_row + i + 3] + hj * self.wr[(i + 3) * dim + j];
            }
            let base = chunks * 4;
            for k in 0..rem {
                let i = base + k;
                z[i] += xj * self.wz[wz_row + i] + hj * self.wz[i * dim + j];
                r[i] += xj * self.wr[wr_row + i] + hj * self.wr[i * dim + j];
            }
        }

        // Apply activations
        for i in 0..dim {
            z[i] = sigmoid(z[i]);
            r[i] = sigmoid(r[i]);
        }

        // h_cand = tanh(x @ Wh + (r * h) @ Wh^T)
        h_cand.iter_mut().for_each(|v| *v = 0.0);
        for j in 0..dim {
            let xj = x[j];
            let rhj = r[j] * self.hiddens[h_offset + j];
            let wh_row = j * dim;
            let chunks = dim / 4;
            let rem = dim % 4;
            for c in 0..chunks {
                let i = c * 4;
                h_cand[i]     += xj * self.wh[wh_row + i]     + rhj * self.wh[i * dim + j];
                h_cand[i + 1] += xj * self.wh[wh_row + i + 1] + rhj * self.wh[(i + 1) * dim + j];
                h_cand[i + 2] += xj * self.wh[wh_row + i + 2] + rhj * self.wh[(i + 2) * dim + j];
                h_cand[i + 3] += xj * self.wh[wh_row + i + 3] + rhj * self.wh[(i + 3) * dim + j];
            }
            let base = chunks * 4;
            for k in 0..rem {
                let i = base + k;
                h_cand[i] += xj * self.wh[wh_row + i] + rhj * self.wh[i * dim + j];
            }
        }
        for i in 0..dim {
            h_cand[i] = h_cand[i].tanh();
        }

        // h = (1-z)*h + z*h_cand
        for i in 0..dim {
            self.hiddens[h_offset + i] =
                (1.0 - z[i]) * self.hiddens[h_offset + i] + z[i] * h_cand[i];
        }
    }

    fn hidden_mean(&self) -> Vec<f64> {
        let dim = self.hidden_dim;
        let n = self.n_cells;
        let mut mean = vec![0.0f64; dim];
        for i in 0..n {
            let row = i * dim;
            for d in 0..dim {
                mean[d] += self.hiddens[row + d];
            }
        }
        let inv_n = 1.0 / n as f64;
        for d in 0..dim {
            mean[d] *= inv_n;
        }
        mean
    }

    /// Parallel Hebbian update: compute all (i,j) cosine similarities in parallel,
    /// then apply coupling deltas.
    fn hebbian_update_parallel(&mut self) {
        let n = self.n_cells;
        let dim = self.hidden_dim;

        // Compute norms
        let norms: Vec<f64> = (0..n)
            .map(|i| {
                let start = i * dim;
                common::norm(&self.hiddens[start..start + dim]).max(1e-12)
            })
            .collect();

        // Parallel: compute deltas for all (i, j) pairs where i < j
        let deltas: Vec<(usize, usize, f64)> = (0..n)
            .into_par_iter()
            .flat_map(|i| {
                let mut local = Vec::new();
                let si = i * dim;
                for j in (i + 1)..n {
                    let sj = j * dim;
                    let dot = common::dot(
                        &self.hiddens[si..si + dim],
                        &self.hiddens[sj..sj + dim],
                    );
                    let sim = dot / (norms[i] * norms[j]);
                    let delta = if sim > 0.8 { 0.01 } else if sim < 0.2 { -0.005 } else { 0.0 };
                    if delta != 0.0 {
                        local.push((i, j, delta));
                    }
                }
                local
            })
            .collect();

        // Apply deltas (sequential write)
        for (i, j, delta) in deltas {
            let c_ij = (self.coupling[i * n + j] + delta).clamp(-1.0, 1.0);
            self.coupling[i * n + j] = c_ij;
            self.coupling[j * n + i] = c_ij;
        }
    }

    fn compute_phi_iit(&self) -> f64 {
        let (_, avg) = mi::pairwise_mi(&self.hiddens, self.n_cells, self.hidden_dim, 16, 200);
        avg
    }

    fn compute_phi_proxy(&self) -> f64 {
        let dim = self.hidden_dim;
        let n = self.n_cells;

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
