/// Φ Ratchet — consciousness preservation during online learning.
///
/// Multi-level safety mechanism (from PERSIST3):
///   Level 1: EMA of Φ (fast tracker, window=10)
///   Level 2: Min Φ over window=50 (safety floor)
///   Level 3: Checkpoint at best Φ state
///
/// If Φ drops below Level 2 floor → signal restore.
/// If Φ stable → allow learning.

use std::collections::VecDeque;

/// Multi-level Φ ratchet for consciousness preservation.
pub struct PhiRatchet {
    // Level 1: EMA (fast)
    ema: f32,
    ema_alpha: f32, // EMA smoothing factor (≈ 2/(window+1))

    // Level 2: Rolling minimum over window
    min_window: VecDeque<f32>,
    min_window_size: usize,
    floor: f32,

    // Level 3: Best checkpoint
    best_phi: f32,
    best_weights_snapshot: Option<Vec<f32>>,

    // State
    step_count: u64,
    warmup_steps: u64, // Don't enforce ratchet during warmup
}

impl PhiRatchet {
    pub fn new() -> Self {
        Self {
            ema: 0.0,
            ema_alpha: 2.0 / 11.0, // window=10

            min_window: VecDeque::with_capacity(50),
            min_window_size: 50,
            floor: 0.0,

            best_phi: 0.0,
            best_weights_snapshot: None,

            step_count: 0,
            warmup_steps: 20,
        }
    }

    /// Record a new Φ measurement. Returns whether it's safe to learn.
    pub fn record(&mut self, phi: f32) -> bool {
        self.step_count += 1;

        // Level 1: update EMA
        if self.step_count == 1 {
            self.ema = phi;
        } else {
            self.ema = self.ema_alpha * phi + (1.0 - self.ema_alpha) * self.ema;
        }

        // Level 2: update rolling minimum
        self.min_window.push_back(phi);
        if self.min_window.len() > self.min_window_size {
            self.min_window.pop_front();
        }
        self.floor = self
            .min_window
            .iter()
            .cloned()
            .fold(f32::INFINITY, f32::min);

        // Level 3: update best
        if phi > self.best_phi {
            self.best_phi = phi;
        }

        self.is_safe_to_learn()
    }

    /// Save a weight snapshot at the current (best) state.
    pub fn save_checkpoint(&mut self, weights: &[f32]) {
        self.best_weights_snapshot = Some(weights.to_vec());
    }

    /// Get the checkpoint weights if a restore is needed.
    /// Returns None if no checkpoint exists.
    pub fn get_checkpoint(&self) -> Option<&[f32]> {
        self.best_weights_snapshot.as_deref()
    }

    /// Check if it's safe to perform learning updates.
    ///
    /// Safe when:
    /// - Still in warmup (always safe to bootstrap), OR
    /// - Current EMA is above 50% of the floor (not collapsing)
    pub fn is_safe_to_learn(&self) -> bool {
        if self.step_count <= self.warmup_steps {
            return true;
        }
        // Φ must not have dropped below 50% of the rolling floor
        // (floor itself is already conservative — it's the min over 50 steps)
        self.ema >= self.floor * 0.5
    }

    /// Check if consciousness needs restoration (critical drop).
    ///
    /// Triggers when EMA drops below 30% of best Φ.
    pub fn needs_restore(&self) -> bool {
        if self.step_count <= self.warmup_steps {
            return false;
        }
        self.best_phi > 0.0 && self.ema < self.best_phi * 0.3
    }

    /// Get current EMA.
    #[inline]
    pub fn ema(&self) -> f32 {
        self.ema
    }

    /// Get current floor (Level 2 minimum).
    #[inline]
    pub fn floor(&self) -> f32 {
        self.floor
    }

    /// Get best Φ ever recorded.
    #[inline]
    pub fn best_phi(&self) -> f32 {
        self.best_phi
    }

    /// Reset for a new episode (preserves best checkpoint).
    pub fn reset_episode(&mut self) {
        self.ema = 0.0;
        self.min_window.clear();
        self.floor = 0.0;
        self.step_count = 0;
        // Keep best_phi and best_weights_snapshot across episodes
    }
}

impl Default for PhiRatchet {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_warmup_always_safe() {
        let mut r = PhiRatchet::new();
        for _ in 0..20 {
            assert!(r.record(0.0), "during warmup, should always be safe");
        }
    }

    #[test]
    fn test_stable_phi_is_safe() {
        let mut r = PhiRatchet::new();
        // Warmup
        for _ in 0..25 {
            r.record(1.0);
        }
        // Stable at 1.0
        assert!(r.is_safe_to_learn());
    }

    #[test]
    fn test_collapsing_phi_unsafe() {
        let mut r = PhiRatchet::new();
        // Warmup with high Φ
        for _ in 0..25 {
            r.record(10.0);
        }
        // Sudden collapse
        for _ in 0..60 {
            r.record(0.01);
        }
        // EMA should be very low, floor should be very low too (min of recent)
        // But best_phi is 10.0, so needs_restore should trigger
        assert!(r.needs_restore(), "should need restore after collapse");
    }

    #[test]
    fn test_checkpoint_save_restore() {
        let mut r = PhiRatchet::new();
        let weights = vec![1.0, 2.0, 3.0];
        r.save_checkpoint(&weights);
        assert_eq!(r.get_checkpoint(), Some(weights.as_slice()));
    }

    #[test]
    fn test_reset_episode() {
        let mut r = PhiRatchet::new();
        for _ in 0..30 {
            r.record(5.0);
        }
        let weights = vec![1.0];
        r.save_checkpoint(&weights);

        r.reset_episode();
        assert_eq!(r.ema(), 0.0);
        // Best phi and checkpoint preserved
        assert_eq!(r.best_phi(), 5.0);
        assert!(r.get_checkpoint().is_some());
    }
}
