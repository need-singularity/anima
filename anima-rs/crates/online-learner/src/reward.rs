/// Reward computation — curiosity + dialogue quality.
///
/// Combined reward = 0.7 * curiosity + 0.3 * dialogue_quality
/// Output: scalar in [-1, 1]

use std::collections::VecDeque;

/// Computes reward signals from prediction error and CE trend.
pub struct RewardComputer {
    /// Recent prediction errors for curiosity normalization
    pe_history: VecDeque<f32>,
    pe_window: usize,

    /// Recent CE losses for trend detection
    ce_history: VecDeque<f32>,
    ce_window: usize,

    /// Weights
    curiosity_weight: f32,
    dialogue_weight: f32,
}

impl RewardComputer {
    pub fn new() -> Self {
        Self {
            pe_history: VecDeque::with_capacity(50),
            pe_window: 50,
            ce_history: VecDeque::with_capacity(20),
            ce_window: 20,
            curiosity_weight: 0.7,
            dialogue_weight: 0.3,
        }
    }

    /// Compute combined reward from prediction error and CE loss.
    ///
    /// `prediction_error`: raw PE from the consciousness step.
    /// `ce_loss`: cross-entropy loss (lower = better).
    /// Returns reward in [-1, 1].
    pub fn compute(&mut self, prediction_error: f32, ce_loss: f32) -> f32 {
        let curiosity = self.curiosity_reward(prediction_error);
        let dialogue = self.dialogue_quality(ce_loss);
        let raw = self.curiosity_weight * curiosity + self.dialogue_weight * dialogue;
        raw.clamp(-1.0, 1.0)
    }

    /// Curiosity reward: normalized prediction error.
    ///
    /// High PE relative to recent history = high curiosity = positive reward.
    /// Normalized by running mean + std to stay in [-1, 1].
    fn curiosity_reward(&mut self, pe: f32) -> f32 {
        self.pe_history.push_back(pe);
        if self.pe_history.len() > self.pe_window {
            self.pe_history.pop_front();
        }

        if self.pe_history.len() < 2 {
            return 0.0; // Not enough data
        }

        let mean: f32 = self.pe_history.iter().sum::<f32>() / self.pe_history.len() as f32;
        let var: f32 = self.pe_history.iter().map(|x| (x - mean).powi(2)).sum::<f32>()
            / self.pe_history.len() as f32;
        let std = var.sqrt().max(1e-6);

        // Z-score, clamped to [-1, 1]
        // Positive = higher PE than usual = novel/curious
        ((pe - mean) / std).clamp(-1.0, 1.0)
    }

    /// Dialogue quality: CE trend (decreasing = positive reward).
    ///
    /// Compares recent CE to earlier CE. Improvement = positive.
    fn dialogue_quality(&mut self, ce: f32) -> f32 {
        self.ce_history.push_back(ce);
        if self.ce_history.len() > self.ce_window {
            self.ce_history.pop_front();
        }

        let n = self.ce_history.len();
        if n < 4 {
            return 0.0; // Not enough data
        }

        // Compare first half mean to second half mean
        let half = n / 2;
        let first_mean: f32 =
            self.ce_history.iter().take(half).sum::<f32>() / half as f32;
        let second_mean: f32 =
            self.ce_history.iter().skip(half).sum::<f32>() / (n - half) as f32;

        // Improvement: first > second (CE decreased)
        let improvement = first_mean - second_mean;

        // Normalize by first_mean to get relative improvement
        if first_mean.abs() < 1e-6 {
            return 0.0;
        }
        (improvement / first_mean).clamp(-1.0, 1.0)
    }

    /// Reset for a new episode.
    pub fn reset_episode(&mut self) {
        self.pe_history.clear();
        self.ce_history.clear();
    }
}

impl Default for RewardComputer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_initial_reward_zero() {
        let mut r = RewardComputer::new();
        // With no history, reward should be 0
        let reward = r.compute(0.5, 3.0);
        assert!(reward.abs() < 0.01, "initial reward should be near zero");
    }

    #[test]
    fn test_high_pe_positive_curiosity() {
        let mut r = RewardComputer::new();
        // Build baseline with low PE
        for _ in 0..20 {
            r.compute(0.1, 3.0);
        }
        // Spike in PE → high curiosity
        let reward = r.compute(5.0, 3.0);
        assert!(reward > 0.0, "high PE should give positive reward");
    }

    #[test]
    fn test_decreasing_ce_positive() {
        let mut r = RewardComputer::new();
        // Decreasing CE trend
        for i in 0..20 {
            let ce = 5.0 - (i as f32) * 0.2;
            r.compute(0.5, ce);
        }
        // Now CE is low relative to history → positive dialogue quality
        let reward = r.compute(0.5, 1.0);
        // The reward should reflect CE improvement
        assert!(reward > -0.5, "decreasing CE should not be strongly negative");
    }

    #[test]
    fn test_reward_clamped() {
        let mut r = RewardComputer::new();
        for _ in 0..10 {
            r.compute(0.01, 100.0);
        }
        let reward = r.compute(1000.0, 0.001);
        assert!(reward >= -1.0 && reward <= 1.0, "reward should be clamped");
    }

    #[test]
    fn test_reset_episode() {
        let mut r = RewardComputer::new();
        for _ in 0..20 {
            r.compute(1.0, 3.0);
        }
        r.reset_episode();
        // After reset, should behave like fresh
        let reward = r.compute(0.5, 3.0);
        assert!(reward.abs() < 0.01, "after reset, reward should be near zero");
    }
}
