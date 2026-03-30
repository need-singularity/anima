use rand::Rng;

use crate::math::{matvec, random_matrix, sigmoid, tanh_f32};

/// GRU cell for consciousness computation.
/// Combined input = [input, tension, hidden] where tension is a single scalar.
#[derive(Clone)]
pub struct GruCell {
    pub hidden: Vec<f32>,
    pub w_z: Vec<f32>,
    pub w_r: Vec<f32>,
    pub w_h: Vec<f32>,
    input_dim: usize,
    hidden_dim: usize,
    combined_dim: usize,
}

impl GruCell {
    /// Create a new GRU cell with random weights (scale 0.1).
    /// combined_dim = input_dim + 1 (tension) + hidden_dim
    pub fn new<R: Rng>(input_dim: usize, hidden_dim: usize, rng: &mut R) -> Self {
        let combined_dim = input_dim + 1 + hidden_dim;
        let scale = 0.1;
        Self {
            hidden: vec![0.0; hidden_dim],
            w_z: random_matrix(hidden_dim, combined_dim, scale, rng),
            w_r: random_matrix(hidden_dim, combined_dim, scale, rng),
            w_h: random_matrix(hidden_dim, combined_dim, scale, rng),
            input_dim,
            hidden_dim,
            combined_dim,
        }
    }

    /// GRU forward pass with tension injection.
    pub fn process(&mut self, input: &[f32], tension: f32) {
        assert_eq!(input.len(), self.input_dim);

        // combined = [input, tension, hidden]
        let mut combined = Vec::with_capacity(self.combined_dim);
        combined.extend_from_slice(input);
        combined.push(tension);
        combined.extend_from_slice(&self.hidden);

        // z = sigmoid(W_z * combined)
        let z_raw = matvec(&self.w_z, &combined, self.hidden_dim, self.combined_dim);
        let z: Vec<f32> = z_raw.iter().map(|&v| sigmoid(v)).collect();

        // r = sigmoid(W_r * combined)
        let r_raw = matvec(&self.w_r, &combined, self.hidden_dim, self.combined_dim);
        let r: Vec<f32> = r_raw.iter().map(|&v| sigmoid(v)).collect();

        // combined_r = [input, tension, r * hidden]
        let mut combined_r = Vec::with_capacity(self.combined_dim);
        combined_r.extend_from_slice(input);
        combined_r.push(tension);
        for i in 0..self.hidden_dim {
            combined_r.push(r[i] * self.hidden[i]);
        }

        // h_cand = tanh(W_h * combined_r)
        let h_raw = matvec(&self.w_h, &combined_r, self.hidden_dim, self.combined_dim);
        let h_cand: Vec<f32> = h_raw.iter().map(|&v| tanh_f32(v)).collect();

        // hidden = (1 - z) * h_cand + z * hidden
        for i in 0..self.hidden_dim {
            self.hidden[i] = (1.0 - z[i]) * h_cand[i] + z[i] * self.hidden[i];
        }
    }

    /// Reset hidden state to zeros.
    pub fn reset(&mut self) {
        self.hidden.fill(0.0);
    }

    pub fn hidden_dim(&self) -> usize {
        self.hidden_dim
    }

    pub fn input_dim(&self) -> usize {
        self.input_dim
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::SeedableRng;
    use rand::rngs::StdRng;

    #[test]
    fn test_gru_cell_creation() {
        let mut rng = StdRng::seed_from_u64(42);
        let gru = GruCell::new(8, 16, &mut rng);
        assert_eq!(gru.input_dim(), 8);
        assert_eq!(gru.hidden_dim(), 16);
        assert_eq!(gru.hidden.len(), 16);
        assert_eq!(gru.w_z.len(), 16 * (8 + 1 + 16));
        assert_eq!(gru.w_r.len(), 16 * (8 + 1 + 16));
        assert_eq!(gru.w_h.len(), 16 * (8 + 1 + 16));
    }

    #[test]
    fn test_gru_cell_process() {
        let mut rng = StdRng::seed_from_u64(42);
        let mut gru = GruCell::new(4, 8, &mut rng);

        let initial_hidden = gru.hidden.clone();
        let input = vec![1.0, 0.5, -0.3, 0.8];
        gru.process(&input, 0.6);

        // Hidden state must change after processing
        assert_ne!(gru.hidden, initial_hidden);
        // All values should be finite
        assert!(gru.hidden.iter().all(|v| v.is_finite()));
    }

    #[test]
    fn test_gru_cell_reset() {
        let mut rng = StdRng::seed_from_u64(42);
        let mut gru = GruCell::new(4, 8, &mut rng);

        let input = vec![1.0, 0.5, -0.3, 0.8];
        gru.process(&input, 0.6);
        assert!(gru.hidden.iter().any(|&v| v != 0.0));

        gru.reset();
        assert!(gru.hidden.iter().all(|&v| v == 0.0));
    }
}
