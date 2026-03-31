/// Hebbian LTP/LTD — real-time synaptic weight updates.
///
/// Rule: Δw = η * (pre * post - λ * w)
/// LTP: co-active cells (cosine > 0.8) strengthen
/// LTD: anti-correlated cells (cosine < 0.2) weaken

use anima_core::math::cosine_similarity;

/// Thresholds for LTP/LTD activation.
const LTP_THRESHOLD: f32 = 0.8;
const LTD_THRESHOLD: f32 = 0.2;

/// Hebbian updater with pre-allocated weight matrix.
pub struct HebbianUpdater {
    /// Synaptic weights: flat [n_cells x n_cells]
    pub weights: Vec<f32>,
    /// Weight deltas from last update: flat [n_cells x n_cells]
    pub deltas: Vec<f32>,
    /// Number of cells
    n_cells: usize,
    /// Learning rate η
    lr: f32,
    /// Weight decay λ
    decay: f32,
}

impl HebbianUpdater {
    pub fn new(n_cells: usize, lr: f32, decay: f32) -> Self {
        let size = n_cells * n_cells;
        Self {
            weights: vec![0.0; size],
            deltas: vec![0.0; size],
            n_cells,
            lr,
            decay,
        }
    }

    /// Resize internal buffers if cell count changed.
    pub fn resize(&mut self, n_cells: usize) {
        if n_cells != self.n_cells {
            self.n_cells = n_cells;
            let size = n_cells * n_cells;
            self.weights.resize(size, 0.0);
            self.deltas.resize(size, 0.0);
        }
    }

    /// Perform one Hebbian update step.
    ///
    /// `cell_states`: slice of slices, each [hidden_dim].
    /// Returns total delta norm (L2) for diagnostics.
    pub fn update(&mut self, cell_states: &[&[f32]]) -> f32 {
        let n = cell_states.len();
        debug_assert!(n <= self.n_cells);

        // Zero deltas
        for d in self.deltas.iter_mut() {
            *d = 0.0;
        }

        let mut delta_norm_sq: f32 = 0.0;

        for i in 0..n {
            for j in (i + 1)..n {
                let sim = cosine_similarity(cell_states[i], cell_states[j]);

                // LTP: strongly correlated cells
                let delta = if sim > LTP_THRESHOLD {
                    // Strengthen: positive delta, with decay on current weight
                    self.lr * (sim - self.decay * self.weights[i * self.n_cells + j])
                } else if sim < LTD_THRESHOLD {
                    // LTD: anti-correlated cells weaken
                    self.lr * (sim - 1.0 - self.decay * self.weights[i * self.n_cells + j])
                } else {
                    // Neutral zone: only decay
                    -self.lr * self.decay * self.weights[i * self.n_cells + j]
                };

                self.deltas[i * self.n_cells + j] = delta;
                self.deltas[j * self.n_cells + i] = delta; // symmetric

                // Apply
                self.weights[i * self.n_cells + j] =
                    (self.weights[i * self.n_cells + j] + delta).clamp(-1.0, 1.0);
                self.weights[j * self.n_cells + i] = self.weights[i * self.n_cells + j];

                delta_norm_sq += 2.0 * delta * delta; // symmetric pair
            }
        }

        delta_norm_sq.sqrt()
    }

    /// Get weight between cell i and cell j.
    #[inline]
    pub fn weight(&self, i: usize, j: usize) -> f32 {
        self.weights[i * self.n_cells + j]
    }

    /// Get flat weight deltas (for applying to model).
    pub fn get_deltas(&self) -> &[f32] {
        &self.deltas
    }

    /// Get flat weights.
    pub fn get_weights(&self) -> &[f32] {
        &self.weights
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ltp_strengthens() {
        let mut h = HebbianUpdater::new(2, 0.001, 0.01);
        // Two very similar vectors → cosine > 0.8 → LTP
        let a = vec![1.0, 2.0, 3.0, 4.0];
        let b = vec![1.1, 2.1, 3.1, 4.1];
        let states: Vec<&[f32]> = vec![&a, &b];

        h.update(&states);
        assert!(h.weight(0, 1) > 0.0, "LTP should strengthen connection");
    }

    #[test]
    fn test_ltd_weakens() {
        let mut h = HebbianUpdater::new(2, 0.001, 0.01);
        // Orthogonal vectors → cosine ≈ 0 < 0.2 → LTD
        let a = vec![1.0, 0.0, 0.0, 0.0];
        let b = vec![0.0, 1.0, 0.0, 0.0];
        let states: Vec<&[f32]> = vec![&a, &b];

        h.update(&states);
        assert!(h.weight(0, 1) < 0.0, "LTD should weaken connection");
    }

    #[test]
    fn test_weights_clamp() {
        let mut h = HebbianUpdater::new(2, 1.0, 0.0); // large lr, no decay
        let a = vec![1.0f32, 2.0, 3.0];
        let b = vec![1.0f32, 2.0, 3.0]; // identical → sim=1.0
        let states: Vec<&[f32]> = vec![&a, &b];

        for _ in 0..1000 {
            h.update(&states);
        }
        assert!(h.weight(0, 1) <= 1.0);
        assert!(h.weight(0, 1) >= -1.0);
    }

    #[test]
    fn test_delta_norm_positive() {
        let mut h = HebbianUpdater::new(3, 0.001, 0.01);
        let a = vec![1.0f32, 0.0];
        let b = vec![0.0f32, 1.0];
        let c = vec![1.0f32, 1.0];
        let states: Vec<&[f32]> = vec![&a, &b, &c];

        let norm = h.update(&states);
        assert!(norm > 0.0, "delta norm should be positive when learning");
    }
}
