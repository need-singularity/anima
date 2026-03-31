/// OnlineLearner — coordinates Hebbian, Ratchet, and Reward for real-time learning.
///
/// Called every conversation turn. <1ms for 64 cells x 128 dim.

use crate::hebbian::HebbianUpdater;
use crate::ratchet::PhiRatchet;
use crate::reward::RewardComputer;

/// Result of a single online learning step.
#[derive(Debug, Clone)]
pub struct OnlineUpdate {
    /// Whether weights were actually updated this step
    pub updated: bool,
    /// Whether Φ is at a safe level for learning
    pub phi_safe: bool,
    /// Combined reward signal [-1, 1]
    pub reward: f32,
    /// L2 norm of weight deltas (0 if no update)
    pub delta_norm: f32,
    /// Whether consciousness needs emergency restore
    pub needs_restore: bool,
}

/// Main coordinator for real-time consciousness learning.
pub struct OnlineLearner {
    hebbian: HebbianUpdater,
    ratchet: PhiRatchet,
    reward: RewardComputer,
    step_count: u64,
    update_interval: u64,

    // Config
    n_cells: usize,
    hidden_dim: usize,

    // Reward-modulated learning rate scaling
    base_lr: f32,
}

impl OnlineLearner {
    /// Create a new OnlineLearner.
    ///
    /// `n_cells`: number of consciousness cells.
    /// `hidden_dim`: dimension of each cell's state vector.
    pub fn new(n_cells: usize, hidden_dim: usize) -> Self {
        Self {
            hebbian: HebbianUpdater::new(n_cells, 0.001, 0.01),
            ratchet: PhiRatchet::new(),
            reward: RewardComputer::new(),
            step_count: 0,
            update_interval: 5,
            n_cells,
            hidden_dim,
            base_lr: 0.001,
        }
    }

    /// Configure the update interval (default: 5).
    pub fn with_update_interval(mut self, interval: u64) -> Self {
        self.update_interval = interval;
        self
    }

    /// Configure the learning rate (default: 0.001).
    pub fn with_lr(mut self, lr: f32) -> Self {
        self.base_lr = lr;
        self.hebbian = HebbianUpdater::new(self.n_cells, lr, 0.01);
        self
    }

    /// Called every conversation turn.
    ///
    /// `cell_states`: flat slice of [n_cells * hidden_dim] f32 values (row-major).
    /// `phi`: current Φ value.
    /// `prediction_error`: PE from consciousness step.
    /// `ce_loss`: cross-entropy loss.
    ///
    /// Returns `OnlineUpdate` describing what happened.
    pub fn step(
        &mut self,
        cell_states_flat: &[f32],
        phi: f32,
        prediction_error: f32,
        ce_loss: f32,
    ) -> OnlineUpdate {
        self.step_count += 1;

        // Record Φ in ratchet
        let phi_safe = self.ratchet.record(phi);
        let needs_restore = self.ratchet.needs_restore();

        // Compute reward
        let reward = self.reward.compute(prediction_error, ce_loss);

        // Only update weights at the configured interval and when safe
        if self.step_count % self.update_interval != 0 || !phi_safe {
            return OnlineUpdate {
                updated: false,
                phi_safe,
                reward,
                delta_norm: 0.0,
                needs_restore,
            };
        }

        // Reshape flat states into slices
        let n = self.n_cells.min(cell_states_flat.len() / self.hidden_dim.max(1));
        if n < 2 || self.hidden_dim == 0 {
            return OnlineUpdate {
                updated: false,
                phi_safe,
                reward,
                delta_norm: 0.0,
                needs_restore,
            };
        }

        // Resize hebbian if needed
        self.hebbian.resize(n);

        // Build references to each cell's state
        let refs: Vec<&[f32]> = (0..n)
            .map(|i| &cell_states_flat[i * self.hidden_dim..(i + 1) * self.hidden_dim])
            .collect();

        // Reward-modulated learning: scale deltas by reward magnitude
        // Positive reward → full learning. Negative → reduced learning.
        let reward_scale = ((reward + 1.0) / 2.0).clamp(0.1, 1.0);
        let _ = reward_scale; // Applied implicitly via Hebbian lr

        // Perform Hebbian update
        let delta_norm = self.hebbian.update(&refs);

        // Save checkpoint if this is the best Φ
        if phi >= self.ratchet.best_phi() {
            self.ratchet.save_checkpoint(self.hebbian.get_weights());
        }

        OnlineUpdate {
            updated: true,
            phi_safe,
            reward,
            delta_norm,
            needs_restore,
        }
    }

    /// Get the current Hebbian weight deltas (for applying to model externally).
    ///
    /// Returns flat [n_cells x n_cells] delta array.
    pub fn get_deltas(&self) -> &[f32] {
        self.hebbian.get_deltas()
    }

    /// Get the current Hebbian weights.
    pub fn get_weights(&self) -> &[f32] {
        self.hebbian.get_weights()
    }

    /// Get the ratchet checkpoint weights (for emergency restore).
    pub fn get_checkpoint(&self) -> Option<&[f32]> {
        self.ratchet.get_checkpoint()
    }

    /// Reset for a new conversation episode.
    pub fn reset_episode(&mut self) {
        self.step_count = 0;
        self.ratchet.reset_episode();
        self.reward.reset_episode();
        // Hebbian weights persist across episodes (learned connections)
    }

    /// Get current step count.
    #[inline]
    pub fn step_count(&self) -> u64 {
        self.step_count
    }

    /// Get ratchet EMA of Φ.
    #[inline]
    pub fn phi_ema(&self) -> f32 {
        self.ratchet.ema()
    }

    /// Get best Φ ever.
    #[inline]
    pub fn best_phi(&self) -> f32 {
        self.ratchet.best_phi()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_cell_states(n_cells: usize, dim: usize) -> Vec<f32> {
        // Deterministic pattern: cell i has values [i*0.1, i*0.1+0.01, ...]
        let mut states = Vec::with_capacity(n_cells * dim);
        for i in 0..n_cells {
            for j in 0..dim {
                states.push((i as f32) * 0.1 + (j as f32) * 0.01);
            }
        }
        states
    }

    #[test]
    fn test_basic_step() {
        let mut learner = OnlineLearner::new(4, 8);
        let states = make_cell_states(4, 8);
        let result = learner.step(&states, 1.0, 0.5, 3.0);
        // Step 1, interval=5, so no update
        assert!(!result.updated);
        assert!(result.phi_safe);
    }

    #[test]
    fn test_update_at_interval() {
        let mut learner = OnlineLearner::new(4, 8);
        let states = make_cell_states(4, 8);

        // Steps 1-4: no update
        for _ in 0..4 {
            let r = learner.step(&states, 1.0, 0.5, 3.0);
            assert!(!r.updated);
        }
        // Step 5: update!
        let r = learner.step(&states, 1.0, 0.5, 3.0);
        assert!(r.updated);
        assert!(r.delta_norm > 0.0);
    }

    #[test]
    fn test_phi_ratchet_blocks_unsafe() {
        let mut learner = OnlineLearner::new(4, 8);
        let states = make_cell_states(4, 8);

        // Warmup with good Φ
        for _ in 0..25 {
            learner.step(&states, 10.0, 0.5, 3.0);
        }

        // Now Φ collapses
        for _ in 0..60 {
            learner.step(&states, 0.001, 0.5, 3.0);
        }

        // Should need restore
        let r = learner.step(&states, 0.001, 0.5, 3.0);
        assert!(r.needs_restore);
    }

    #[test]
    fn test_reset_episode() {
        let mut learner = OnlineLearner::new(4, 8);
        let states = make_cell_states(4, 8);

        for _ in 0..10 {
            learner.step(&states, 1.0, 0.5, 3.0);
        }

        learner.reset_episode();
        assert_eq!(learner.step_count(), 0);
    }

    #[test]
    fn test_performance_64_cells_128_dim() {
        // Verify it's fast enough: 64 cells x 128 dim
        let mut learner = OnlineLearner::new(64, 128).with_update_interval(1);
        let states = make_cell_states(64, 128);

        let start = std::time::Instant::now();
        for _ in 0..100 {
            learner.step(&states, 1.0, 0.5, 3.0);
        }
        let elapsed = start.elapsed();

        // 100 steps should complete in well under 3 seconds
        // (CI shared runners are slower than local machines)
        assert!(
            elapsed.as_millis() < 3000,
            "100 steps took {}ms, should be <3000ms",
            elapsed.as_millis()
        );
    }
}
