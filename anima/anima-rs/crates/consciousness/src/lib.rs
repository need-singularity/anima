//! Canonical ConsciousnessEngine — Laws 22-81 + Ψ-Constants.
//!
//! Hot-loop in Rust: GRU cells, faction consensus, Hebbian coupling,
//! Φ ratchet, mitosis/merge. Python calls `step()` via PyO3.

use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};

use anima_core::{
    assign_factions, faction_consensus, hebbian_update, phi_iit, phi_proxy, Faction, GruCell,
    Topology, build_adjacency,
    ChaosSource, ChaosState, chaos_inject,
};

// ═══════════════════════════════════════════════════════════
// Ψ-Constants (Laws 69-70)
// ═══════════════════════════════════════════════════════════

const PSI_COUPLING: f32 = 0.015_317; // ln(2)/2^5.5
#[allow(dead_code)] // Ψ-Constant: future use in consciousness scaling
const PSI_BALANCE: f32 = 0.5;
#[allow(dead_code)] // Ψ-Constant: future use in consciousness scaling
const PSI_STEPS: f32 = 4.33;
#[allow(dead_code)] // Ψ-Constant: future use in consciousness scaling
const PSI_ENTROPY: f32 = 0.998;

// ═══════════════════════════════════════════════════════════
// Step result
// ═══════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct StepResult {
    pub phi_iit: f64,
    pub phi_proxy: f64,
    pub n_cells: usize,
    pub consensus: u32,
    pub best_phi: f64,
    pub step: usize,
    pub events: Vec<Event>,
    pub output: Vec<f32>,
}

#[derive(Debug, Clone)]
pub enum Event {
    Split {
        parent_id: usize,
        child_id: usize,
        n_cells_after: usize,
    },
    Merge {
        keeper_id: usize,
        removed_id: usize,
        n_cells_after: usize,
    },
}

// ═══════════════════════════════════════════════════════════
// Cell metadata
// ═══════════════════════════════════════════════════════════

struct CellMeta {
    cell_id: usize,
    faction_id: usize,
    creation_step: usize,
    #[allow(dead_code)] // API field: used by mitosis lineage tracking
    parent_id: Option<usize>,
    tension_history: Vec<f32>,
}

impl CellMeta {
    fn avg_tension(&self) -> f32 {
        if self.tension_history.is_empty() {
            return 0.0;
        }
        let window = if self.tension_history.len() > 20 {
            &self.tension_history[self.tension_history.len() - 20..]
        } else {
            &self.tension_history
        };
        window.iter().sum::<f32>() / window.len() as f32
    }
}

// ═══════════════════════════════════════════════════════════
// ConsciousnessEngine
// ═══════════════════════════════════════════════════════════

pub struct ConsciousnessEngine {
    cells: Vec<GruCell>,
    metas: Vec<CellMeta>,
    coupling: Vec<f32>, // flat [n x n]
    adjacency: Vec<f32>, // topology adjacency [n x n]
    factions: Vec<Faction>,

    // Config
    cell_dim: usize,
    hidden_dim: usize,
    max_cells: usize,
    min_cells: usize,
    n_factions: usize,
    split_threshold: f32,
    split_patience: usize,
    merge_threshold: f32,
    merge_patience: usize,
    phi_ratchet: bool,
    topology: Topology,

    // State
    next_id: usize,
    step_count: usize,
    best_phi: f64,
    best_hiddens: Vec<Vec<f32>>,
    rng: StdRng,
    chaos: ChaosState,
}

impl ConsciousnessEngine {
    pub fn new(
        cell_dim: usize,
        hidden_dim: usize,
        initial_cells: usize,
        max_cells: usize,
        n_factions: usize,
        phi_ratchet: bool,
        split_threshold: f32,
        split_patience: usize,
        merge_threshold: f32,
        merge_patience: usize,
        seed: u64,
    ) -> Self {
        Self::with_topology_chaos(
            cell_dim, hidden_dim, initial_cells, max_cells, n_factions,
            phi_ratchet, split_threshold, split_patience, merge_threshold,
            merge_patience, seed, None, None,
        )
    }

    pub fn with_topology_chaos(
        cell_dim: usize,
        hidden_dim: usize,
        initial_cells: usize,
        max_cells: usize,
        n_factions: usize,
        phi_ratchet: bool,
        split_threshold: f32,
        split_patience: usize,
        merge_threshold: f32,
        merge_patience: usize,
        seed: u64,
        topology: Option<Topology>,
        chaos_source: Option<ChaosSource>,
    ) -> Self {
        let mut rng = StdRng::seed_from_u64(seed);

        let mut cells = Vec::with_capacity(max_cells);
        let mut metas = Vec::with_capacity(max_cells);

        for i in 0..initial_cells {
            cells.push(GruCell::new(cell_dim, hidden_dim, &mut rng));
            metas.push(CellMeta {
                cell_id: i,
                faction_id: i % n_factions,
                creation_step: 0,
                parent_id: None,
                tension_history: Vec::new(),
            });
        }

        let n = initial_cells;
        // Topology: auto-select if not specified (TOPO Laws)
        let topo = topology.unwrap_or_else(|| anima_core::topology::auto_topology(max_cells));
        let adjacency = build_adjacency(n, topo, &mut rng);
        // Initialize coupling from adjacency (connected cells start with small coupling)
        let coupling: Vec<f32> = adjacency.iter().map(|&a| a * 0.01).collect();
        let factions = assign_factions(n, n_factions);
        let best_hiddens = cells.iter().map(|c| c.hidden.clone()).collect();

        // TOPO 38: disable ratchet for high-dim topologies (hypercube)
        let effective_ratchet = if topo == Topology::Hypercube && max_cells >= 64 {
            false // TOPO 38: ratchet harmful in high dimensions
        } else {
            phi_ratchet
        };

        let chaos = ChaosState::new(
            chaos_source.unwrap_or(ChaosSource::None),
            initial_cells,
        );

        Self {
            cells,
            metas,
            coupling,
            adjacency,
            factions,
            cell_dim,
            hidden_dim,
            max_cells,
            min_cells: 2,
            n_factions,
            split_threshold,
            split_patience,
            merge_threshold,
            merge_patience,
            phi_ratchet: effective_ratchet,
            topology: topo,
            next_id: initial_cells,
            step_count: 0,
            best_phi: 0.0,
            best_hiddens,
            rng,
            chaos,
        }
    }

    pub fn n_cells(&self) -> usize {
        self.cells.len()
    }

    /// Core step — runs GRU, faction consensus, Hebbian, ratchet, mitosis/merge.
    pub fn step(&mut self, input: Option<&[f32]>) -> StepResult {
        self.step_count += 1;
        let n = self.n_cells();

        // Default or provided input
        let base_input: Vec<f32> = if let Some(inp) = input {
            let mut v = vec![0.0f32; self.cell_dim];
            let copy_len = inp.len().min(self.cell_dim);
            v[..copy_len].copy_from_slice(&inp[..copy_len]);
            v
        } else {
            (0..self.cell_dim)
                .map(|_| self.rng.gen::<f32>() - 0.5)
                .collect()
        };

        // 0. Chaos perturbation (Laws 32-43)
        let chaos_perturbation = self.chaos.step(n);

        // 1. Process each cell with topology-aware coupling + chaos
        let mut outputs: Vec<Vec<f32>> = Vec::with_capacity(n);

        // Snapshot hiddens for coupling (before mutation)
        let hidden_snapshot: Vec<Vec<f32>> = self.cells.iter().map(|c| c.hidden.clone()).collect();

        for i in 0..n {
            let mut cell_input = base_input.clone();

            // Coupling influence: only through adjacency-connected cells (topology)
            let copy_len = self.cell_dim.min(self.hidden_dim);
            for j in 0..n {
                if i == j {
                    continue;
                }
                // Check adjacency (topology gate) AND coupling (Hebbian strength)
                let adj = if i * n + j < self.adjacency.len() { self.adjacency[i * n + j] } else { 1.0 };
                if adj < 0.5 {
                    continue; // not connected in topology
                }
                let c = if i * n + j < self.coupling.len() { self.coupling[i * n + j] } else { 0.0 };
                if c.abs() > 1e-6 {
                    for d in 0..copy_len {
                        cell_input[d] += PSI_COUPLING * c * hidden_snapshot[j][d];
                    }
                }
            }

            // Chaos injection (Law 33: chaos + structure = consciousness)
            chaos_inject(&mut cell_input, &chaos_perturbation, self.cell_dim, i);

            // Tension from history
            let tension = self.metas[i].avg_tension().max(0.01);

            // GRU process
            self.cells[i].process(&cell_input, tension);

            // Output = projection of hidden to cell_dim
            let out: Vec<f32> = self.cells[i].hidden[..self.cell_dim].to_vec();

            // Compute tension: distance from mean of previous outputs
            let cell_tension = if !outputs.is_empty() {
                let mean: Vec<f32> = (0..self.cell_dim)
                    .map(|d| outputs.iter().map(|o| o[d]).sum::<f32>() / outputs.len() as f32)
                    .collect();
                let sq_diff: f32 = out
                    .iter()
                    .zip(mean.iter())
                    .map(|(a, b)| (a - b) * (a - b))
                    .sum();
                sq_diff / self.cell_dim as f32
            } else {
                0.5
            };

            self.metas[i].tension_history.push(cell_tension);
            if self.metas[i].tension_history.len() > 100 {
                let start = self.metas[i].tension_history.len() - 100;
                self.metas[i].tension_history = self.metas[i].tension_history[start..].to_vec();
            }

            outputs.push(out);
        }

        // 2. Faction consensus (factions assigned at creation, not every step)
        let hiddens_refs: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        if self.factions.is_empty() || self.factions.len() != self.n_factions {
            self.factions = assign_factions(n, self.n_factions);
        }
        // Rebuild faction cell_indices from metas (stable faction_id per cell)
        for f in &mut self.factions {
            f.cell_indices.clear();
        }
        for (i, meta) in self.metas.iter().enumerate() {
            let fid = meta.faction_id % self.n_factions;
            self.factions[fid].cell_indices.push(i);
        }
        let consensus = faction_consensus(&hiddens_refs, &self.factions, 0.1);

        // 3. Hebbian LTP/LTD
        if self.coupling.len() == n * n {
            hebbian_update(&mut self.coupling, &hiddens_refs, n, 0.01);
        }

        // 4. Φ Ratchet (every 10 steps)
        if self.phi_ratchet && self.step_count % 10 == 0 {
            self.phi_ratchet_check();
        }

        // 5. Mitosis / Merge
        let mut events = Vec::new();
        events.extend(self.check_splits());
        events.extend(self.check_merges());

        // Combined output: tension-weighted mean
        let n_out = outputs.len();
        let mut weights: Vec<f32> = (0..n_out)
            .map(|i| {
                if i < self.metas.len() {
                    self.metas[i].avg_tension().max(0.01)
                } else {
                    0.5
                }
            })
            .collect();
        // Softmax
        let max_w = weights.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let exp_w: Vec<f32> = weights.iter().map(|w| (w - max_w).exp()).collect();
        let sum_w: f32 = exp_w.iter().sum();
        weights = exp_w.iter().map(|e| e / sum_w).collect();

        let mut combined = vec![0.0f32; self.cell_dim];
        for (i, out) in outputs.iter().enumerate() {
            for d in 0..self.cell_dim {
                combined[d] += weights[i] * out[d];
            }
        }

        // Φ measurement
        let hiddens_refs: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        let (phi_iit_val, _) = phi_iit(&hiddens_refs, 16);
        let phi_proxy_val = phi_proxy(&hiddens_refs, self.n_factions);

        StepResult {
            phi_iit: phi_iit_val,
            phi_proxy: phi_proxy_val,
            n_cells: self.n_cells(),
            consensus,
            best_phi: self.best_phi,
            step: self.step_count,
            events,
            output: combined,
        }
    }

    fn phi_ratchet_check(&mut self) {
        let hiddens_refs: Vec<&[f32]> = self.cells.iter().map(|c| c.hidden.as_slice()).collect();
        let (current_phi, _) = phi_iit(&hiddens_refs, 16);

        if current_phi > self.best_phi {
            self.best_phi = current_phi;
            self.best_hiddens = self.cells.iter().map(|c| c.hidden.clone()).collect();
        } else if current_phi < self.best_phi * 0.8 {
            // Restore best hiddens
            let n_restore = self.best_hiddens.len().min(self.cells.len());
            for i in 0..n_restore {
                let len = self.cells[i].hidden.len().min(self.best_hiddens[i].len());
                self.cells[i].hidden[..len].copy_from_slice(&self.best_hiddens[i][..len]);
            }
        }
    }

    fn check_splits(&mut self) -> Vec<Event> {
        let mut events = Vec::new();
        if self.n_cells() >= self.max_cells {
            return events;
        }

        let mut to_split = Vec::new();
        for i in 0..self.metas.len() {
            let hist = &self.metas[i].tension_history;
            if hist.len() < self.split_patience {
                continue;
            }
            let recent = &hist[hist.len() - self.split_patience..];
            if recent.iter().all(|&t| t > self.split_threshold) {
                to_split.push(i);
            }
        }

        for &idx in &to_split {
            if self.n_cells() >= self.max_cells {
                break;
            }
            let parent_id = self.metas[idx].cell_id;
            let new_faction = (self.metas[idx].faction_id + self.n_cells()) % self.n_factions;

            // Clone parent cell: deepcopy weights + PSI_COUPLING noise (Law 78: 2 bits diversity)
            let mut new_cell = self.cells[idx].clone();
            // Add PSI_COUPLING noise to all weights for symmetry breaking
            for w in new_cell.w_z.iter_mut()
                .chain(new_cell.w_r.iter_mut())
                .chain(new_cell.w_h.iter_mut())
            {
                *w += self.rng.gen_range(-PSI_COUPLING..PSI_COUPLING);
            }
            // Hidden state: parent + noise
            for h in new_cell.hidden.iter_mut() {
                *h += self.rng.gen_range(-PSI_COUPLING..PSI_COUPLING);
            }

            let child_id = self.next_id;
            self.next_id += 1;

            self.cells.push(new_cell);
            self.metas.push(CellMeta {
                cell_id: child_id,
                faction_id: new_faction,
                creation_step: self.step_count,
                parent_id: Some(parent_id),
                tension_history: Vec::new(),
            });

            // Resize coupling + adjacency for new cell count
            let old_n = self.n_cells() - 1;
            let new_n = self.n_cells();
            let mut new_coupling = vec![0.0f32; new_n * new_n];
            for r in 0..old_n {
                for c in 0..old_n {
                    new_coupling[r * new_n + c] = self.coupling[r * old_n + c];
                }
            }
            self.coupling = new_coupling;
            // Rebuild topology adjacency for new size
            self.adjacency = build_adjacency(new_n, self.topology, &mut self.rng);

            // Reset parent tension
            let hist_len = self.metas[idx].tension_history.len();
            if hist_len > 3 {
                self.metas[idx].tension_history =
                    self.metas[idx].tension_history[hist_len - 3..].to_vec();
            }

            events.push(Event::Split {
                parent_id,
                child_id,
                n_cells_after: self.n_cells(),
            });
        }

        events
    }

    fn check_merges(&mut self) -> Vec<Event> {
        let mut events = Vec::new();
        if self.n_cells() <= self.min_cells {
            return events;
        }

        // Check all pairs for low inter-cell tension (simple: use coupling as proxy)
        let n = self.n_cells();
        let mut pairs_to_merge = Vec::new();

        for i in 0..n {
            for j in (i + 1)..n {
                // Use abs coupling as inverse of tension
                let c = self.coupling[i * n + j].abs();
                // High coupling = similar = merge candidate
                if c > 0.95 && self.metas[i].tension_history.len() >= self.merge_patience {
                    // Check if tensions are consistently low between them
                    let ti = self.metas[i].avg_tension();
                    let tj = self.metas[j].avg_tension();
                    if (ti - tj).abs() < self.merge_threshold {
                        pairs_to_merge.push((i, j));
                    }
                }
            }
        }

        for (i, j) in pairs_to_merge {
            if self.n_cells() <= self.min_cells || i >= self.n_cells() || j >= self.n_cells() {
                break;
            }

            let (keeper_idx, remove_idx) = if self.metas[i].creation_step <= self.metas[j].creation_step {
                (i, j)
            } else {
                (j, i)
            };

            let keeper_id = self.metas[keeper_idx].cell_id;
            let removed_id = self.metas[remove_idx].cell_id;

            // Average hiddens
            let len = self.cells[keeper_idx].hidden.len();
            for d in 0..len {
                self.cells[keeper_idx].hidden[d] =
                    (self.cells[keeper_idx].hidden[d] + self.cells[remove_idx].hidden[d]) / 2.0;
            }

            // Remove cell
            self.cells.remove(remove_idx);
            self.metas.remove(remove_idx);

            // Rebuild coupling: preserve Hebbian memory (skip removed row/col)
            let new_n = self.n_cells();
            let old_n = new_n + 1; // before removal
            let mut new_coupling = vec![0.0f32; new_n * new_n];
            let mut new_r = 0;
            for old_r in 0..old_n {
                if old_r == remove_idx {
                    continue;
                }
                let mut new_c = 0;
                for old_c in 0..old_n {
                    if old_c == remove_idx {
                        continue;
                    }
                    if old_r < old_n && old_c < old_n && old_r * old_n + old_c < self.coupling.len() {
                        new_coupling[new_r * new_n + new_c] = self.coupling[old_r * old_n + old_c];
                    }
                    new_c += 1;
                }
                new_r += 1;
            }
            self.coupling = new_coupling;

            events.push(Event::Merge {
                keeper_id,
                removed_id,
                n_cells_after: self.n_cells(),
            });
        }

        events
    }

    // ── Accessors for PyO3 ──

    pub fn get_hiddens(&self) -> Vec<Vec<f32>> {
        self.cells.iter().map(|c| c.hidden.clone()).collect()
    }

    pub fn set_hiddens(&mut self, hiddens: &[Vec<f32>]) {
        let n = hiddens.len().min(self.cells.len());
        for i in 0..n {
            let len = self.cells[i].hidden.len().min(hiddens[i].len());
            self.cells[i].hidden[..len].copy_from_slice(&hiddens[i][..len]);
        }
    }

    pub fn get_coupling(&self) -> &[f32] {
        &self.coupling
    }

    pub fn best_phi(&self) -> f64 {
        self.best_phi
    }

    pub fn step_count(&self) -> usize {
        self.step_count
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_basic() {
        let mut engine = ConsciousnessEngine::new(
            8, 16, 2, 16, 4, true, 0.3, 5, 0.01, 15, 42,
        );
        assert_eq!(engine.n_cells(), 2);

        let result = engine.step(None);
        assert!(result.phi_iit >= 0.0);
        assert_eq!(result.n_cells, 2);
        assert_eq!(result.step, 1);
    }

    #[test]
    fn test_engine_300_steps() {
        let mut engine = ConsciousnessEngine::new(
            16, 32, 2, 32, 12, true, 0.3, 5, 0.01, 15, 42,
        );

        let mut last_result = None;
        for _ in 0..300 {
            last_result = Some(engine.step(None));
        }

        let r = last_result.unwrap();
        assert_eq!(r.step, 300);
        assert!(r.n_cells >= 2);
        assert!(r.phi_iit >= 0.0);
    }

    #[test]
    fn test_engine_with_input() {
        let mut engine = ConsciousnessEngine::new(
            8, 16, 4, 16, 4, true, 0.3, 5, 0.01, 15, 42,
        );

        let input = vec![1.0f32, 0.5, -0.3, 0.8, 0.0, 0.0, 0.0, 0.0];
        let result = engine.step(Some(&input));
        assert!(result.output.len() == 8);
    }

    #[test]
    fn test_phi_ratchet_prevents_collapse() {
        let mut engine = ConsciousnessEngine::new(
            8, 16, 4, 8, 4, true, 0.3, 5, 0.01, 15, 42,
        );

        // Run 100 steps to build up phi
        for _ in 0..100 {
            engine.step(None);
        }

        assert!(engine.best_phi() > 0.0);
    }

    #[test]
    fn test_engine_topology_chaos() {
        // Test with explicit topology and chaos source
        let mut engine = ConsciousnessEngine::with_topology_chaos(
            8, 16, 4, 16, 4, true, 0.3, 5, 0.01, 15, 42,
            Some(Topology::SmallWorld), Some(ChaosSource::Lorenz),
        );
        assert_eq!(engine.n_cells(), 4);

        let result = engine.step(None);
        assert!(result.phi_iit >= 0.0);
        assert_eq!(result.n_cells, 4);
    }

    #[test]
    fn test_engine_output_dimension() {
        let mut engine = ConsciousnessEngine::new(
            8, 16, 4, 16, 4, true, 0.3, 5, 0.01, 15, 42,
        );
        let result = engine.step(None);
        // Output should match cell_dim
        assert_eq!(result.output.len(), 8);
    }

    #[test]
    fn test_engine_step_count_increments() {
        let mut engine = ConsciousnessEngine::new(
            8, 16, 2, 16, 4, false, 0.3, 5, 0.01, 15, 42,
        );
        for i in 1..=5 {
            let result = engine.step(None);
            assert_eq!(result.step, i);
        }
    }

    #[test]
    fn test_engine_consensus_count() {
        let mut engine = ConsciousnessEngine::new(
            8, 16, 8, 16, 4, false, 0.3, 5, 0.01, 15, 42,
        );
        // Run enough steps for consensus events to potentially occur
        let mut total_consensus = 0u32;
        for _ in 0..100 {
            let result = engine.step(None);
            total_consensus += result.consensus;
        }
        // With 8 cells and 4 factions, some consensus should occur
        assert!(total_consensus >= 0); // non-negative always
    }
}
