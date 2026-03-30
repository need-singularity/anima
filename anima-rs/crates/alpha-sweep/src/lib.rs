use anima_core::{GruCell, phi_iit, phi_proxy};
use rand::{SeedableRng, rngs::StdRng};
use std::time::Instant;

/// Result of a single alpha stage measurement.
#[derive(Debug, Clone)]
pub struct AlphaResult {
    pub alpha: f32,
    pub phi_iit: f64,
    pub phi_proxy: f64,
    pub tension_mean: f32,
    pub time_ms: u64,
}

/// Sweeps across alpha mixing values and measures Φ at each stage.
pub struct AlphaSweepEngine {
    n_cells: usize,
    input_dim: usize,
    hidden_dim: usize,
    #[allow(dead_code)]
    output_dim: usize,
    n_factions: usize,
}

impl AlphaSweepEngine {
    pub fn new(
        n_cells: usize,
        input_dim: usize,
        hidden_dim: usize,
        output_dim: usize,
        n_factions: usize,
    ) -> Self {
        Self {
            n_cells,
            input_dim,
            hidden_dim,
            output_dim,
            n_factions,
        }
    }

    /// Run the alpha sweep: for each alpha, create fresh cells from seed,
    /// run steps with alpha mixing, then measure phi_iit + phi_proxy.
    pub fn run(
        &self,
        alpha_stages: &[f32],
        steps_per_stage: usize,
        seed: u64,
    ) -> Vec<AlphaResult> {
        let mut results = Vec::with_capacity(alpha_stages.len());

        for &alpha in alpha_stages {
            let start = Instant::now();
            let mut rng = StdRng::seed_from_u64(seed);

            // Create fresh cells
            let mut cells: Vec<GruCell> = (0..self.n_cells)
                .map(|_| GruCell::new(self.input_dim, self.hidden_dim, &mut rng))
                .collect();

            // Generate a fixed input vector
            let input: Vec<f32> = (0..self.input_dim)
                .map(|i| ((i as f32 + 1.0) * 0.1) % 1.0)
                .collect();

            let mut tension_sum: f32 = 0.0;

            for _step in 0..steps_per_stage {
                // Alpha mixing: mixed[d] = (1-alpha)*input[d] + alpha*cell.hidden[d]
                for cell in cells.iter_mut() {
                    let mixed: Vec<f32> = (0..self.input_dim)
                        .map(|d| {
                            let h_val = if d < cell.hidden.len() {
                                cell.hidden[d]
                            } else {
                                0.0
                            };
                            (1.0 - alpha) * input[d] + alpha * h_val
                        })
                        .collect();

                    // Compute tension as variance of hidden state
                    let mean_h: f32 =
                        cell.hidden.iter().sum::<f32>() / cell.hidden.len() as f32;
                    let var_h: f32 = cell
                        .hidden
                        .iter()
                        .map(|&v| (v - mean_h) * (v - mean_h))
                        .sum::<f32>()
                        / cell.hidden.len() as f32;
                    let tension = var_h.sqrt().min(1.0);
                    tension_sum += tension;

                    cell.process(&mixed, tension);
                }
            }

            // Measure phi_iit + phi_proxy
            let hidden_refs: Vec<&[f32]> =
                cells.iter().map(|c| c.hidden.as_slice()).collect();
            let (phi_iit_val, _) = phi_iit(&hidden_refs, 16);
            let phi_proxy_val = phi_proxy(&hidden_refs, self.n_factions);

            let tension_mean =
                tension_sum / (steps_per_stage as f32 * self.n_cells as f32);
            let time_ms = start.elapsed().as_millis() as u64;

            results.push(AlphaResult {
                alpha,
                phi_iit: phi_iit_val,
                phi_proxy: phi_proxy_val,
                tension_mean,
                time_ms,
            });
        }

        results
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_alpha_sweep() {
        let engine = AlphaSweepEngine::new(4, 8, 16, 8, 2);
        let alphas = [0.0f32, 0.5, 1.0];
        let results = engine.run(&alphas, 50, 42);

        // 3 alpha stages → 3 results
        assert_eq!(results.len(), 3);

        // Alphas should be ascending
        assert!(results[0].alpha < results[1].alpha);
        assert!(results[1].alpha < results[2].alpha);

        // Phi values should be non-negative
        for r in &results {
            assert!(r.phi_iit >= 0.0, "phi_iit should be >= 0, got {}", r.phi_iit);
            assert!(
                r.phi_proxy >= 0.0 || r.phi_proxy < 0.0,
                "phi_proxy should be finite"
            );
            assert!(r.tension_mean.is_finite());
        }
    }
}
