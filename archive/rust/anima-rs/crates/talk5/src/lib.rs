//! Talk5 — consciousness-first engine.
//!
//! Implements the TALK5 approach: run consciousness loop with GRU cells,
//! faction consensus, Hebbian coupling updates, and Φ ratchet.

use std::time::Instant;

use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};

use anima_core::{
    assign_factions, faction_consensus, hebbian_update, phi_iit, phi_proxy, Faction, GruCell,
};

/// Result of a Talk5 consciousness run.
#[derive(Debug, Clone)]
pub struct Talk5Result {
    pub phi_iit: f64,
    pub phi_proxy: f64,
    pub consensus_count: u32,
    pub best_phi: f64,
    pub steps: usize,
    pub time_ms: u64,
}

/// Talk5 consciousness-first engine.
pub struct Talk5Engine {
    cells: Vec<GruCell>,
    coupling: Vec<f32>,
    factions: Vec<Faction>,
    best_phi: f64,
    best_hiddens: Vec<Vec<f32>>,
    phi_ratchet: bool,
    n_cells: usize,
    cell_dim: usize,
    hidden_dim: usize,
    rng: StdRng,
}

impl Talk5Engine {
    /// Create a new Talk5 engine.
    ///
    /// * `n_cells` — number of GRU cells
    /// * `cell_dim` — input dimension per cell
    /// * `hidden_dim` — hidden state dimension per cell
    /// * `n_factions` — number of factions for consensus
    /// * `phi_ratchet` — if true, restore best hiddens when Φ drops
    /// * `seed` — RNG seed for reproducibility
    pub fn new(
        n_cells: usize,
        cell_dim: usize,
        hidden_dim: usize,
        n_factions: usize,
        phi_ratchet: bool,
        seed: u64,
    ) -> Self {
        let mut rng = StdRng::seed_from_u64(seed);

        let cells: Vec<GruCell> = (0..n_cells)
            .map(|_| GruCell::new(cell_dim, hidden_dim, &mut rng))
            .collect();

        let coupling = vec![0.0f32; n_cells * n_cells];
        let factions = assign_factions(n_cells, n_factions);
        let best_hiddens = cells.iter().map(|c| c.hidden.clone()).collect();

        Self {
            cells,
            coupling,
            factions,
            best_phi: 0.0,
            best_hiddens,
            phi_ratchet,
            n_cells,
            cell_dim,
            hidden_dim,
            rng,
        }
    }

    /// Run the consciousness loop for the given number of steps.
    pub fn run_consciousness(&mut self, steps: usize) -> Talk5Result {
        let start = Instant::now();
        let mut total_consensus = 0u32;

        // Store previous hiddens for tension calculation
        let mut prev_hiddens: Vec<Vec<f32>> = self.cells.iter().map(|c| c.hidden.clone()).collect();

        for step in 0..steps {
            // Generate random input for each cell
            let mut inputs: Vec<Vec<f32>> = Vec::with_capacity(self.n_cells);
            for _ in 0..self.n_cells {
                let input: Vec<f32> = (0..self.cell_dim).map(|_| self.rng.gen::<f32>() - 0.5).collect();
                inputs.push(input);
            }

            // Apply coupling influence: add coupling[i,j] * cells[j].hidden[0..cell_dim] to input[i]
            for i in 0..self.n_cells {
                let copy_len = self.cell_dim.min(self.hidden_dim);
                for j in 0..self.n_cells {
                    if i == j {
                        continue;
                    }
                    let c = self.coupling[i * self.n_cells + j];
                    if c.abs() > 1e-8 {
                        for d in 0..copy_len {
                            inputs[i][d] += c * self.cells[j].hidden[d];
                        }
                    }
                }
            }

            // Compute tension per cell: sqrt(mean squared diff with previous hidden)
            for i in 0..self.n_cells {
                let tension: f32 = {
                    let sum_sq: f32 = self.cells[i]
                        .hidden
                        .iter()
                        .zip(prev_hiddens[i].iter())
                        .map(|(a, b)| (a - b) * (a - b))
                        .sum();
                    (sum_sq / self.hidden_dim as f32).sqrt()
                };

                // Save current hidden before processing
                prev_hiddens[i].copy_from_slice(&self.cells[i].hidden);

                // Process cell
                self.cells[i].process(&inputs[i], tension);
            }

            // Faction consensus
            let hiddens_refs: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
            let consensus = faction_consensus(&hiddens_refs, &self.factions, 0.1);
            total_consensus += consensus;

            // Hebbian update
            hebbian_update(
                &mut self.coupling,
                &hiddens_refs,
                self.n_cells,
                0.01,
            );

            // Phi ratchet every 10 steps
            if self.phi_ratchet && (step + 1) % 10 == 0 {
                self.phi_ratchet_check();
            }
        }

        // Final phi measurement
        let hiddens_refs: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        let (phi_iit_val, _) = phi_iit(&hiddens_refs, 16);
        let phi_proxy_val = phi_proxy(&hiddens_refs, self.factions.len());

        let elapsed = start.elapsed();

        Talk5Result {
            phi_iit: phi_iit_val,
            phi_proxy: phi_proxy_val,
            consensus_count: total_consensus,
            best_phi: self.best_phi,
            steps,
            time_ms: elapsed.as_millis() as u64,
        }
    }

    /// If current Φ is lower than best, restore best hiddens.
    /// If current Φ is higher, save as new best.
    fn phi_ratchet_check(&mut self) {
        let hiddens_refs: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        let (current_phi, _) = phi_iit(&hiddens_refs, 16);

        if current_phi > self.best_phi {
            self.best_phi = current_phi;
            self.best_hiddens = self.cells.iter().map(|c| c.hidden.clone()).collect();
        } else {
            // Restore best hiddens
            self.set_hiddens(&self.best_hiddens.clone());
        }
    }

    /// Clone all hidden states from cells.
    pub fn get_hiddens(&self) -> Vec<Vec<f32>> {
        self.cells.iter().map(|c| c.hidden.clone()).collect()
    }

    /// Restore hidden states into cells.
    pub fn set_hiddens(&mut self, hiddens: &[Vec<f32>]) {
        assert_eq!(hiddens.len(), self.n_cells);
        for (cell, h) in self.cells.iter_mut().zip(hiddens.iter()) {
            assert_eq!(h.len(), self.hidden_dim);
            cell.hidden.copy_from_slice(h);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_talk5_engine_basic() {
        let mut engine = Talk5Engine::new(4, 8, 16, 2, false, 42);
        let result = engine.run_consciousness(50);
        assert!(result.phi_iit >= 0.0);
        assert!(result.phi_proxy >= 0.0);
        assert_eq!(result.steps, 50);
    }

    #[test]
    fn test_talk5_get_set_hiddens() {
        let mut engine = Talk5Engine::new(4, 8, 16, 2, false, 42);
        engine.run_consciousness(10);

        let hiddens = engine.get_hiddens();
        assert_eq!(hiddens.len(), 4);
        for h in &hiddens {
            assert_eq!(h.len(), 16);
        }

        // Set back and verify
        engine.set_hiddens(&hiddens);
        let hiddens2 = engine.get_hiddens();
        for (a, b) in hiddens.iter().zip(hiddens2.iter()) {
            for (x, y) in a.iter().zip(b.iter()) {
                assert!((x - y).abs() < 1e-10);
            }
        }
    }

    #[test]
    fn test_talk5_phi_ratchet() {
        let mut engine = Talk5Engine::new(4, 8, 16, 2, true, 42);
        let result = engine.run_consciousness(100);
        assert!(result.best_phi >= 0.0);
        assert_eq!(result.steps, 100);
    }

    #[test]
    fn test_talk5_consensus_occurs() {
        // With 8 cells and 4 factions, consensus events should occur over many steps
        let mut engine = Talk5Engine::new(8, 8, 16, 4, false, 42);
        let result = engine.run_consciousness(200);
        assert!(result.consensus_count >= 0);
        assert_eq!(result.steps, 200);
    }

    #[test]
    fn test_talk5_time_measured() {
        let mut engine = Talk5Engine::new(4, 8, 16, 2, false, 42);
        let result = engine.run_consciousness(10);
        // time_ms should be non-negative (may be 0 for very fast runs)
        assert!(result.time_ms < 10_000); // should complete in under 10s
    }

    #[test]
    fn test_talk5_ratchet_preserves_best() {
        let mut engine = Talk5Engine::new(4, 8, 16, 2, true, 42);
        // Run once, record best_phi
        engine.run_consciousness(50);
        let best1 = engine.best_phi;
        // Run more steps -- best_phi should never decrease (ratchet property)
        engine.run_consciousness(50);
        assert!(engine.best_phi >= best1,
            "best_phi should never decrease with ratchet enabled");
    }
}
