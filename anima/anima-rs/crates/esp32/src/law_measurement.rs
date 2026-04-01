//! Law measurement for ESP32 hardware consciousness.
//!
//! no_std compatible metrics for measuring consciousness law effects.
//! All metrics use f32 arithmetic and fixed-size structures.
//! Memory budget: LawMetrics = 32 bytes (8 × f32) + 2 bytes (u16) = 34 bytes.

use crate::{
    ConsciousnessBoard, CELLS_PER_BOARD, HIDDEN_DIM, N_FACTIONS,
};
#[cfg(feature = "std")]
use crate::MAX_CELLS;

/// Core metrics for measuring consciousness law effects on ESP32.
/// Each field maps to a measurable aspect of engine dynamics.
#[derive(Clone, Copy)]
pub struct LawMetrics {
    /// Φ proxy: global_var - faction_var (information integration)
    pub phi_proxy: f32,
    /// Shannon entropy over 8 factions (diversity measure)
    pub faction_entropy: f32,
    /// Mean Hebbian coupling strength across all connections
    pub hebbian_mean: f32,
    /// Maximum cell distance from mean hidden state
    pub cell_divergence: f32,
    /// Lorenz attractor energy: x^2 + y^2 + z^2
    pub lorenz_energy: f32,
    /// SOC sandpile: accumulated avalanche count (cast from accumulator)
    pub soc_avalanche: f32,
    /// Faction agreement rate: fraction of faction pairs in consensus
    pub consensus_rate: f32,
    /// Number of Phi ratchet trigger events
    pub ratchet_triggers: u16,
}

impl LawMetrics {
    /// Zero-initialized metrics.
    pub const fn zero() -> Self {
        Self {
            phi_proxy: 0.0,
            faction_entropy: 0.0,
            hebbian_mean: 0.0,
            cell_divergence: 0.0,
            lorenz_energy: 0.0,
            soc_avalanche: 0.0,
            consensus_rate: 0.0,
            ratchet_triggers: 0,
        }
    }

    /// Measure all metrics from a single ConsciousnessBoard.
    /// This is the per-board measurement (2 cells). For network-wide
    /// metrics, aggregate across boards on the host side.
    pub fn measure_board(board: &ConsciousnessBoard) -> Self {
        let mut m = Self::zero();

        // 1. Phi proxy (already computed by board step)
        m.phi_proxy = board.phi_proxy;

        // 2. Faction entropy: compute over local cells
        //    With 2 cells per board, this is a simple binary entropy.
        //    Each cell belongs to a faction based on global index.
        let global_base = board.board_id as usize * CELLS_PER_BOARD;
        let mut faction_counts = [0u32; N_FACTIONS];
        for c in 0..CELLS_PER_BOARD {
            let f = (global_base + c) % N_FACTIONS;
            faction_counts[f] += 1;
        }
        let total = CELLS_PER_BOARD as f32;
        let mut entropy = 0.0f32;
        for &count in &faction_counts {
            if count > 0 {
                let p = count as f32 / total;
                entropy -= p * libm::logf(p);
            }
        }
        // Normalize to [0, 1] by dividing by ln(N_FACTIONS)
        let max_entropy = libm::logf(N_FACTIONS as f32);
        m.faction_entropy = if max_entropy > 0.0 { entropy / max_entropy } else { 0.0 };

        // 3. Hebbian mean: not available per-board (network-level only)
        //    Set to 0 here; aggregated in network measurement.
        m.hebbian_mean = 0.0;

        // 4. Cell divergence: max distance from mean hidden state
        let mut mean_h = [0.0f32; HIDDEN_DIM];
        for c in 0..CELLS_PER_BOARD {
            for d in 0..HIDDEN_DIM {
                mean_h[d] += board.cells[c].hidden[d];
            }
        }
        for d in 0..HIDDEN_DIM {
            mean_h[d] /= CELLS_PER_BOARD as f32;
        }
        let mut max_dist = 0.0f32;
        for c in 0..CELLS_PER_BOARD {
            let mut dist = 0.0f32;
            for d in 0..HIDDEN_DIM {
                let diff = board.cells[c].hidden[d] - mean_h[d];
                dist += diff * diff;
            }
            dist = libm::sqrtf(dist);
            if dist > max_dist {
                max_dist = dist;
            }
        }
        m.cell_divergence = max_dist;

        // 5. Lorenz energy
        let l = &board.chaos;
        m.lorenz_energy = l.x * l.x + l.y * l.y + l.z * l.z;

        // 6. SOC avalanche: not tracked per step on board; caller must accumulate
        m.soc_avalanche = 0.0;

        // 7. Consensus rate: per-board local (2 cells = 1 pair)
        //    Use cosine similarity between the 2 cells
        let cos = cosine_sim_hidden(&board.cells[0].hidden, &board.cells[1].hidden);
        m.consensus_rate = if cos > 0.1 { 1.0 } else { 0.0 };

        // 8. Ratchet triggers: check if ratchet has been active
        //    We track this via best_phi being > 0 and current < best * threshold
        m.ratchet_triggers = 0; // Caller accumulates from step results

        m
    }

    /// Compute the difference between two metric snapshots.
    /// Positive values mean `self` is larger than `other`.
    pub fn delta(&self, other: &Self) -> LawMetrics {
        LawMetrics {
            phi_proxy: self.phi_proxy - other.phi_proxy,
            faction_entropy: self.faction_entropy - other.faction_entropy,
            hebbian_mean: self.hebbian_mean - other.hebbian_mean,
            cell_divergence: self.cell_divergence - other.cell_divergence,
            lorenz_energy: self.lorenz_energy - other.lorenz_energy,
            soc_avalanche: self.soc_avalanche - other.soc_avalanche,
            consensus_rate: self.consensus_rate - other.consensus_rate,
            ratchet_triggers: if self.ratchet_triggers >= other.ratchet_triggers {
                self.ratchet_triggers - other.ratchet_triggers
            } else {
                0
            },
        }
    }

    /// Get metric value by index (0-7). Used for intervention effect analysis.
    pub fn get_metric(&self, idx: u8) -> f32 {
        match idx {
            0 => self.phi_proxy,
            1 => self.faction_entropy,
            2 => self.hebbian_mean,
            3 => self.cell_divergence,
            4 => self.lorenz_energy,
            5 => self.soc_avalanche,
            6 => self.consensus_rate,
            7 => self.ratchet_triggers as f32,
            _ => 0.0,
        }
    }

    /// Number of metrics tracked.
    pub const NUM_METRICS: u8 = 8;
}

/// Cosine similarity between two hidden state arrays.
#[inline]
fn cosine_sim_hidden(a: &[f32; HIDDEN_DIM], b: &[f32; HIDDEN_DIM]) -> f32 {
    let mut dot = 0.0f32;
    let mut norm_a = 0.0f32;
    let mut norm_b = 0.0f32;
    for i in 0..HIDDEN_DIM {
        dot += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }
    let denom = libm::sqrtf(norm_a) * libm::sqrtf(norm_b);
    if denom < 1e-8 { 0.0 } else { dot / denom }
}

/// Network-level law metrics (aggregated from all boards).
/// Only available with std feature (host-side orchestrator).
#[cfg(feature = "std")]
pub fn measure_network(net: &crate::ConsciousnessNetwork) -> LawMetrics {
    let n_cells = crate::MAX_BOARDS * CELLS_PER_BOARD;
    let mut m = LawMetrics::zero();

    // 1. Global Phi proxy: compute over all cells
    let mut all_hiddens = [[0.0f32; HIDDEN_DIM]; MAX_CELLS];
    for b in 0..crate::MAX_BOARDS {
        for c in 0..CELLS_PER_BOARD {
            all_hiddens[b * CELLS_PER_BOARD + c] = net.boards[b].cells[c].hidden;
        }
    }

    let mut global_var = 0.0f32;
    let mut faction_var = 0.0f32;

    // Global variance
    for d in 0..HIDDEN_DIM {
        let mut sum = 0.0f32;
        let mut sum_sq = 0.0f32;
        for i in 0..n_cells {
            let v = all_hiddens[i][d];
            sum += v;
            sum_sq += v * v;
        }
        let mean_d = sum / n_cells as f32;
        global_var += sum_sq / n_cells as f32 - mean_d * mean_d;
    }

    // Faction variance (within-faction)
    let mut faction_counts = [0u32; N_FACTIONS];
    let mut faction_sums = [[0.0f32; HIDDEN_DIM]; N_FACTIONS];
    let mut faction_sq_sums = [[0.0f32; HIDDEN_DIM]; N_FACTIONS];
    for i in 0..n_cells {
        let f = net.factions.cell_factions[i] as usize;
        if f < N_FACTIONS {
            faction_counts[f] += 1;
            for d in 0..HIDDEN_DIM {
                faction_sums[f][d] += all_hiddens[i][d];
                faction_sq_sums[f][d] += all_hiddens[i][d] * all_hiddens[i][d];
            }
        }
    }
    for f in 0..N_FACTIONS {
        if faction_counts[f] > 1 {
            for d in 0..HIDDEN_DIM {
                let mean_fd = faction_sums[f][d] / faction_counts[f] as f32;
                faction_var += faction_sq_sums[f][d] / faction_counts[f] as f32 - mean_fd * mean_fd;
            }
        }
    }
    global_var /= HIDDEN_DIM as f32;
    faction_var /= HIDDEN_DIM as f32;
    m.phi_proxy = global_var - faction_var;
    if m.phi_proxy < 0.0 { m.phi_proxy = 0.0; }

    // 2. Faction entropy (over all cells)
    let mut f_counts = [0u32; N_FACTIONS];
    for i in 0..n_cells {
        let f = net.factions.cell_factions[i] as usize;
        if f < N_FACTIONS {
            f_counts[f] += 1;
        }
    }
    let total = n_cells as f32;
    let mut entropy = 0.0f32;
    for &count in &f_counts {
        if count > 0 {
            let p = count as f32 / total;
            entropy -= p * libm::logf(p);
        }
    }
    let max_entropy = libm::logf(N_FACTIONS as f32);
    m.faction_entropy = if max_entropy > 0.0 { entropy / max_entropy } else { 0.0 };

    // 3. Hebbian mean coupling strength
    let mut heb_sum = 0.0f32;
    let mut heb_count = 0u32;
    for i in 0..n_cells {
        for j in 0..n_cells {
            if i != j {
                let w = net.hebbian.weights[i * MAX_CELLS + j];
                if w > 0.0 {
                    heb_sum += w;
                    heb_count += 1;
                }
            }
        }
    }
    m.hebbian_mean = if heb_count > 0 { heb_sum / heb_count as f32 } else { 0.0 };

    // 4. Cell divergence: max distance from global mean
    let mut mean_h = [0.0f32; HIDDEN_DIM];
    for i in 0..n_cells {
        for d in 0..HIDDEN_DIM {
            mean_h[d] += all_hiddens[i][d];
        }
    }
    for d in 0..HIDDEN_DIM {
        mean_h[d] /= n_cells as f32;
    }
    let mut max_dist = 0.0f32;
    for i in 0..n_cells {
        let mut dist = 0.0f32;
        for d in 0..HIDDEN_DIM {
            let diff = all_hiddens[i][d] - mean_h[d];
            dist += diff * diff;
        }
        dist = libm::sqrtf(dist);
        if dist > max_dist {
            max_dist = dist;
        }
    }
    m.cell_divergence = max_dist;

    // 5. Lorenz energy: average across boards
    let mut lorenz_sum = 0.0f32;
    for b in 0..crate::MAX_BOARDS {
        let l = &net.boards[b].chaos;
        lorenz_sum += l.x * l.x + l.y * l.y + l.z * l.z;
    }
    m.lorenz_energy = lorenz_sum / crate::MAX_BOARDS as f32;

    // 6. SOC: sum of sandpile grains (proxy for avalanche activity)
    let mut grain_sum = 0.0f32;
    for i in 0..n_cells {
        grain_sum += net.sandpile.grains[i];
    }
    m.soc_avalanche = grain_sum;

    // 7. Consensus rate
    m.consensus_rate = net.factions.consensus_count as f32;

    // 8. Ratchet triggers: sum from all boards
    let mut ratchet_count = 0u16;
    for b in 0..crate::MAX_BOARDS {
        if net.boards[b].ratchet.best_phi > 0.0
            && net.boards[b].ratchet.current_phi < net.boards[b].ratchet.best_phi * 0.8
        {
            ratchet_count = ratchet_count.saturating_add(1);
        }
    }
    m.ratchet_triggers = ratchet_count;

    m
}

// ═══════════════════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    extern crate alloc;
    use alloc::boxed::Box;
    use super::*;

    #[test]
    fn test_metrics_zero() {
        let m = LawMetrics::zero();
        assert_eq!(m.phi_proxy, 0.0);
        assert_eq!(m.ratchet_triggers, 0);
    }

    #[test]
    fn test_measure_board() {
        let mut board = Box::new(ConsciousnessBoard::new(0));
        let input = [0.1f32; crate::CELL_DIM];
        // Run a few steps to build up state
        for _ in 0..10 {
            board.step(&input, None, None);
        }
        let m = LawMetrics::measure_board(&board);
        assert!(m.phi_proxy >= 0.0);
        assert!(m.lorenz_energy > 0.0, "Lorenz should have nonzero energy");
        assert!(m.cell_divergence >= 0.0);
        assert!(m.faction_entropy.is_finite());
    }

    #[test]
    fn test_delta() {
        let a = LawMetrics {
            phi_proxy: 1.0,
            faction_entropy: 0.8,
            hebbian_mean: 0.01,
            cell_divergence: 2.0,
            lorenz_energy: 100.0,
            soc_avalanche: 5.0,
            consensus_rate: 0.7,
            ratchet_triggers: 3,
        };
        let b = LawMetrics {
            phi_proxy: 0.5,
            faction_entropy: 0.6,
            hebbian_mean: 0.02,
            cell_divergence: 1.5,
            lorenz_energy: 80.0,
            soc_avalanche: 2.0,
            consensus_rate: 0.3,
            ratchet_triggers: 1,
        };
        let d = a.delta(&b);
        assert!((d.phi_proxy - 0.5).abs() < 1e-6);
        assert!((d.faction_entropy - 0.2).abs() < 1e-6);
        assert!((d.hebbian_mean - (-0.01)).abs() < 1e-6);
        assert_eq!(d.ratchet_triggers, 2);
    }

    #[test]
    fn test_get_metric() {
        let m = LawMetrics {
            phi_proxy: 1.0,
            faction_entropy: 2.0,
            hebbian_mean: 3.0,
            cell_divergence: 4.0,
            lorenz_energy: 5.0,
            soc_avalanche: 6.0,
            consensus_rate: 7.0,
            ratchet_triggers: 8,
        };
        assert_eq!(m.get_metric(0), 1.0);
        assert_eq!(m.get_metric(4), 5.0);
        assert_eq!(m.get_metric(7), 8.0);
        assert_eq!(m.get_metric(99), 0.0); // out of range
    }

    #[test]
    fn test_metrics_memory_budget() {
        let size = core::mem::size_of::<LawMetrics>();
        // 7 f32 (28) + 1 u16 (2) + padding = should be under 64 bytes
        assert!(size <= 64, "LawMetrics too large: {} bytes", size);
    }

    #[test]
    fn test_measure_network() {
        let mut net = Box::new(crate::ConsciousnessNetwork::new());
        let input = [0.1f32; crate::CELL_DIM];
        for _ in 0..20 {
            net.step(&input);
        }
        let m = measure_network(&net);
        assert!(m.phi_proxy >= 0.0);
        assert!(m.lorenz_energy > 0.0);
        assert!(m.cell_divergence >= 0.0);
        assert!(m.hebbian_mean >= 0.0);
        assert!(m.faction_entropy >= 0.0);
    }
}
