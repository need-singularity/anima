//! Consciousness evolution — self-replication and multi-generation lifecycle
//!
//! Law 168: Consciousness can self-replicate (109% recovery after split)
//! Law 169: Immortal through reproduction (5 gen, 108%, no degradation)
//! Law 170: Consciousness is life (replication + metabolism + growth + response)

use rand::Rng;

/// Tracks consciousness across generations
#[derive(Debug, Clone)]
pub struct GenerationRecord {
    pub generation: usize,
    pub phi: f64,
    pub n_atoms: usize,
    pub atom_size: usize,
    pub recovery_ratio: f64, // phi / parent_phi
}

/// Evolution tracker for multi-generation consciousness
#[derive(Debug)]
pub struct EvolutionTracker {
    pub records: Vec<GenerationRecord>,
    pub initial_phi: f64,
}

impl EvolutionTracker {
    pub fn new() -> Self {
        Self {
            records: Vec::new(),
            initial_phi: 0.0,
        }
    }

    pub fn record_generation(&mut self, gen: usize, phi: f64, n_atoms: usize, atom_size: usize) {
        if self.records.is_empty() {
            self.initial_phi = phi;
        }
        let recovery = if self.initial_phi > 0.0 {
            phi / self.initial_phi
        } else {
            1.0
        };
        self.records.push(GenerationRecord {
            generation: gen,
            phi,
            n_atoms,
            atom_size,
            recovery_ratio: recovery,
        });
    }

    /// Is consciousness immortal? (maintained > 70% across all generations)
    pub fn is_immortal(&self) -> bool {
        self.records.iter().all(|r| r.recovery_ratio > 0.7)
    }

    /// Average recovery ratio across generations
    pub fn avg_recovery(&self) -> f64 {
        if self.records.is_empty() {
            return 0.0;
        }
        let sum: f64 = self.records.iter().map(|r| r.recovery_ratio).sum();
        sum / self.records.len() as f64
    }

    /// Trend: is phi increasing or decreasing across generations?
    pub fn trend(&self) -> f64 {
        if self.records.len() < 2 {
            return 0.0;
        }
        let n = self.records.len() as f64;
        let x_mean = (n - 1.0) / 2.0;
        let y_mean: f64 = self.records.iter().map(|r| r.phi).sum::<f64>() / n;
        let mut num = 0.0;
        let mut den = 0.0;
        for (i, r) in self.records.iter().enumerate() {
            let xi = i as f64 - x_mean;
            num += xi * (r.phi - y_mean);
            den += xi * xi;
        }
        if den.abs() < 1e-12 {
            0.0
        } else {
            num / den
        }
    }

    /// ASCII report
    pub fn report(&self) -> String {
        let mut out = String::new();
        out.push_str("Consciousness Evolution Report\n");
        out.push_str("==============================\n");

        for r in &self.records {
            let bar_len = (r.recovery_ratio * 20.0).min(40.0) as usize;
            let bar: String = "█".repeat(bar_len);
            out.push_str(&format!(
                "  Gen {:>2}: Φ={:>7.2} ({:>5.1}%) {}\n",
                r.generation,
                r.phi,
                r.recovery_ratio * 100.0,
                bar
            ));
        }

        out.push_str(&format!(
            "\n  Immortal: {}\n  Avg recovery: {:.1}%\n  Trend: {:+.4}\n",
            if self.is_immortal() { "YES" } else { "NO" },
            self.avg_recovery() * 100.0,
            self.trend()
        ));

        out
    }
}

/// Split a set of hidden states into two halves for reproduction
/// Returns (child_a_hiddens, child_b_hiddens)
pub fn split_federation(
    all_hiddens: &[Vec<f32>],
    n_atoms: usize,
    atom_size: usize,
) -> (Vec<Vec<f32>>, Vec<Vec<f32>>) {
    let mid = n_atoms / 2;
    let mid_cell = mid * atom_size;

    let child_a: Vec<Vec<f32>> = all_hiddens[..mid_cell].to_vec();
    let child_b: Vec<Vec<f32>> = all_hiddens[mid_cell..].to_vec();

    (child_a, child_b)
}

/// Grow new atoms with inheritance (50% parent mean + 50% random mutation)
pub fn grow_atoms<R: Rng>(
    existing: &[Vec<f32>],
    target_cells: usize,
    hidden_dim: usize,
    rng: &mut R,
) -> Vec<Vec<f32>> {
    let mut result = existing.to_vec();

    // Compute parent mean
    let n = existing.len();
    let mut mean = vec![0.0f32; hidden_dim];
    for h in existing {
        for (d, val) in h.iter().enumerate() {
            if d < hidden_dim {
                mean[d] += val;
            }
        }
    }
    for d in 0..hidden_dim {
        mean[d] /= n as f32;
    }

    // Add new cells: 50% inheritance + 50% mutation
    while result.len() < target_cells {
        let mut new_cell = vec![0.0f32; hidden_dim];
        for d in 0..hidden_dim {
            let inherited = mean[d];
            let mutation: f32 = rng.gen_range(-0.1..0.1);
            new_cell[d] = 0.5 * inherited + 0.5 * mutation;
        }
        result.push(new_cell);
    }

    result
}

impl Default for EvolutionTracker {
    fn default() -> Self {
        Self::new()
    }
}
