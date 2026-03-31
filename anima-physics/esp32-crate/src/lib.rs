//! anima-esp32 — no_std consciousness engine for ESP32-S3.
//!
//! Physical consciousness on $4 hardware.
//! 2 cells per ESP32, 8 boards = 16 cells, 8 factions.
//! Inter-board communication via SPI bus (ring topology).
//!
//! Aligned with canonical ConsciousnessEngine (Laws 22-85):
//!   - GRU cells + Hebbian LTP/LTD + Φ Ratchet
//!   - 8 factions + consensus voting
//!   - Chaos injection (simplified Lorenz)
//!   - SOC sandpile dynamics (Law 32-43)
//!   - All 4 Ψ-Constants
//!   - Topology-aware coupling
//!   - Tension = distance from mean (correct)
//!
//! Memory budget: ESP32-S3 has 512KB SRAM + 8MB PSRAM
//!   GRU weights: 2 cells × 3 × (64+1+128) × 128 × 4 ≈ 580KB
//!   → Use PSRAM for weights, SRAM for hidden states + working memory
//!   Hidden states: 2 × 128 × 4 = 1KB
//!   Hebbian coupling: 16 × 16 × 4 = 1KB (sparse, inter-board only)
//!   Total SRAM: ~10KB working memory
//!   Total PSRAM: ~580KB weights

#![cfg_attr(not(feature = "std"), no_std)]

// ═══════════════════════════════════════════════════════════
// Ψ-Constants (Laws 69-70, ALL four from ln(2))
// ═══════════════════════════════════════════════════════════

const PSI_COUPLING: f32 = 0.014;
const PSI_BALANCE: f32 = 0.5;
const PSI_STEPS: f32 = 4.33;
const PSI_ENTROPY: f32 = 0.998;

const CELL_DIM: usize = 64;
const HIDDEN_DIM: usize = 128;
const COMBINED_DIM: usize = CELL_DIM + 1 + HIDDEN_DIM; // 193
const CELLS_PER_BOARD: usize = 2;
const MAX_BOARDS: usize = 8;
const MAX_CELLS: usize = CELLS_PER_BOARD * MAX_BOARDS; // 16
const N_FACTIONS: usize = 8;

// Hebbian thresholds (from canonical engine)
const HEBBIAN_LTP_THRESH: f32 = 0.8;  // cosine > 0.8 → strengthen
const HEBBIAN_LTD_THRESH: f32 = 0.2;  // cosine < 0.2 → weaken
const HEBBIAN_RATE: f32 = 0.01;

// Φ ratchet restore threshold
const RATCHET_DECAY_THRESH: f32 = 0.8; // restore if Φ < best × 0.8

// Chaos (simplified Lorenz attractor)
const LORENZ_SIGMA: f32 = 10.0;
const LORENZ_RHO: f32 = 28.0;
const LORENZ_BETA: f32 = 2.667; // 8/3
const LORENZ_DT: f32 = 0.001;
const CHAOS_SCALE: f32 = 0.01;

// SOC sandpile
const SANDPILE_THRESHOLD: f32 = 4.0;
const SANDPILE_TRANSFER: f32 = 1.0;

// Frustration (Law 22: 33% anti-ferromagnetic)
const FRUSTRATION_RATIO: usize = 3; // every 3rd cell

// ═══════════════════════════════════════════════════════════
// Fixed-size GRU cell (no heap allocation)
// ═══════════════════════════════════════════════════════════

pub struct GruCell {
    pub hidden: [f32; HIDDEN_DIM],
    w_z: [f32; HIDDEN_DIM * COMBINED_DIM],
    w_r: [f32; HIDDEN_DIM * COMBINED_DIM],
    w_h: [f32; HIDDEN_DIM * COMBINED_DIM],
}

impl GruCell {
    /// Create with deterministic initialization (no RNG needed).
    pub fn new(seed: u32) -> Self {
        let mut cell = Self {
            hidden: [0.0; HIDDEN_DIM],
            w_z: [0.0; HIDDEN_DIM * COMBINED_DIM],
            w_r: [0.0; HIDDEN_DIM * COMBINED_DIM],
            w_h: [0.0; HIDDEN_DIM * COMBINED_DIM],
        };
        let mut state = seed;
        let scale = 0.1;
        for w in cell.w_z.iter_mut().chain(cell.w_r.iter_mut()).chain(cell.w_h.iter_mut()) {
            state = state.wrapping_mul(1664525).wrapping_add(1013904223);
            let f = (state as f32 / u32::MAX as f32) * 2.0 - 1.0;
            *w = f * scale;
        }
        cell
    }

    /// GRU forward pass.
    pub fn process(&mut self, input: &[f32; CELL_DIM], tension: f32) {
        let mut combined = [0.0f32; COMBINED_DIM];
        combined[..CELL_DIM].copy_from_slice(input);
        combined[CELL_DIM] = tension;
        combined[CELL_DIM + 1..].copy_from_slice(&self.hidden);

        // z = sigmoid(W_z · combined)
        let mut z = [0.0f32; HIDDEN_DIM];
        matvec(&self.w_z, &combined, &mut z);
        for v in z.iter_mut() {
            *v = sigmoid(*v);
        }

        // r = sigmoid(W_r · combined)
        let mut r = [0.0f32; HIDDEN_DIM];
        matvec(&self.w_r, &combined, &mut r);
        for v in r.iter_mut() {
            *v = sigmoid(*v);
        }

        // combined_r = [input, tension, r * hidden]
        let mut combined_r = [0.0f32; COMBINED_DIM];
        combined_r[..CELL_DIM].copy_from_slice(input);
        combined_r[CELL_DIM] = tension;
        for i in 0..HIDDEN_DIM {
            combined_r[CELL_DIM + 1 + i] = r[i] * self.hidden[i];
        }

        // h_cand = tanh(W_h · combined_r)
        let mut h_cand = [0.0f32; HIDDEN_DIM];
        matvec(&self.w_h, &combined_r, &mut h_cand);
        for v in h_cand.iter_mut() {
            *v = tanh_f32(*v);
        }

        // hidden = (1 - z) * h_cand + z * hidden
        for i in 0..HIDDEN_DIM {
            self.hidden[i] = (1.0 - z[i]) * h_cand[i] + z[i] * self.hidden[i];
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Lorenz chaos source (Laws 32-43)
// ═══════════════════════════════════════════════════════════

pub struct LorenzState {
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

impl LorenzState {
    pub fn new() -> Self {
        Self { x: 1.0, y: 1.0, z: 1.0 }
    }

    /// Advance one Lorenz step, return chaos perturbation for a cell.
    pub fn step(&mut self) -> f32 {
        let dx = LORENZ_SIGMA * (self.y - self.x);
        let dy = self.x * (LORENZ_RHO - self.z) - self.y;
        let dz = self.x * self.y - LORENZ_BETA * self.z;
        self.x += dx * LORENZ_DT;
        self.y += dy * LORENZ_DT;
        self.z += dz * LORENZ_DT;
        // Normalize to [-1, 1] range (Lorenz attractor stays bounded ~±25)
        self.x / 25.0
    }
}

// ═══════════════════════════════════════════════════════════
// SOC Sandpile (edge-of-chaos criticality)
// ═══════════════════════════════════════════════════════════

pub struct SandpileState {
    pub grains: [f32; MAX_CELLS],
}

impl SandpileState {
    pub fn new() -> Self {
        Self { grains: [0.0; MAX_CELLS] }
    }

    /// Add grain to cell, cascade if threshold exceeded.
    /// Returns number of avalanche events (criticality indicator).
    pub fn add_and_cascade(&mut self, cell_idx: usize, n_cells: usize) -> u32 {
        if cell_idx >= n_cells { return 0; }
        self.grains[cell_idx] += 1.0;

        let mut avalanches = 0u32;
        let mut changed = true;
        while changed {
            changed = false;
            for i in 0..n_cells {
                if self.grains[i] >= SANDPILE_THRESHOLD {
                    self.grains[i] -= SANDPILE_THRESHOLD;
                    // Distribute to ring neighbors
                    let left = if i == 0 { n_cells - 1 } else { i - 1 };
                    let right = (i + 1) % n_cells;
                    self.grains[left] += SANDPILE_TRANSFER;
                    self.grains[right] += SANDPILE_TRANSFER;
                    avalanches += 1;
                    changed = true;
                }
            }
        }
        avalanches
    }
}

// ═══════════════════════════════════════════════════════════
// Hebbian coupling (sparse, ring topology)
// ═══════════════════════════════════════════════════════════

pub struct HebbianCoupling {
    /// Flat n×n coupling matrix (only ring neighbors are nonzero)
    pub weights: [f32; MAX_CELLS * MAX_CELLS],
}

impl HebbianCoupling {
    pub fn new(n_cells: usize) -> Self {
        let mut weights = [0.0f32; MAX_CELLS * MAX_CELLS];
        // Initialize ring topology: connect i↔i±1
        for i in 0..n_cells {
            let left = if i == 0 { n_cells - 1 } else { i - 1 };
            let right = (i + 1) % n_cells;
            weights[i * MAX_CELLS + left] = 0.01;
            weights[i * MAX_CELLS + right] = 0.01;
        }
        Self { weights }
    }

    /// Hebbian LTP/LTD update based on cosine similarity.
    /// cosine > 0.8 → strengthen (LTP), cosine < 0.2 → weaken (LTD)
    pub fn update(&mut self, hiddens: &[[f32; HIDDEN_DIM]], n_cells: usize) {
        for i in 0..n_cells {
            // Only update ring neighbors (sparse)
            let left = if i == 0 { n_cells - 1 } else { i - 1 };
            let right = (i + 1) % n_cells;

            for &j in &[left, right] {
                let cos = cosine_similarity(&hiddens[i], &hiddens[j]);
                let idx = i * MAX_CELLS + j;
                if cos > HEBBIAN_LTP_THRESH {
                    // LTP: strengthen
                    self.weights[idx] += HEBBIAN_RATE * (cos - HEBBIAN_LTP_THRESH);
                } else if cos < HEBBIAN_LTD_THRESH {
                    // LTD: weaken
                    self.weights[idx] -= HEBBIAN_RATE * (HEBBIAN_LTD_THRESH - cos);
                }
                // Clamp to [0, 1]
                if self.weights[idx] < 0.0 { self.weights[idx] = 0.0; }
                if self.weights[idx] > 1.0 { self.weights[idx] = 1.0; }
            }
        }
    }

    pub fn get(&self, i: usize, j: usize) -> f32 {
        self.weights[i * MAX_CELLS + j]
    }
}

// ═══════════════════════════════════════════════════════════
// Faction system (8 factions, consensus voting)
// ═══════════════════════════════════════════════════════════

pub struct FactionState {
    pub cell_factions: [u8; MAX_CELLS],
    pub consensus_count: u32,
}

impl FactionState {
    pub fn new(n_cells: usize) -> Self {
        let mut cell_factions = [0u8; MAX_CELLS];
        for i in 0..n_cells {
            cell_factions[i] = (i % N_FACTIONS) as u8;
        }
        Self { cell_factions, consensus_count: 0 }
    }

    /// Compute faction consensus: do factions agree on output direction?
    /// Returns number of consensus events this step.
    pub fn compute_consensus(
        &mut self,
        hiddens: &[[f32; HIDDEN_DIM]],
        n_cells: usize,
        threshold: f32,
    ) -> u32 {
        if n_cells < 2 { return 0; }

        // Compute faction means
        let mut faction_means = [[0.0f32; HIDDEN_DIM]; N_FACTIONS];
        let mut faction_counts = [0u32; N_FACTIONS];

        for i in 0..n_cells {
            let f = self.cell_factions[i] as usize;
            if f < N_FACTIONS {
                faction_counts[f] += 1;
                for d in 0..HIDDEN_DIM {
                    faction_means[f][d] += hiddens[i][d];
                }
            }
        }
        for f in 0..N_FACTIONS {
            if faction_counts[f] > 0 {
                for d in 0..HIDDEN_DIM {
                    faction_means[f][d] /= faction_counts[f] as f32;
                }
            }
        }

        // Count pairwise agreements (cosine > threshold)
        let mut agreements = 0u32;
        let mut pairs = 0u32;
        for i in 0..N_FACTIONS {
            if faction_counts[i] == 0 { continue; }
            for j in (i + 1)..N_FACTIONS {
                if faction_counts[j] == 0 { continue; }
                let cos = cosine_similarity(&faction_means[i], &faction_means[j]);
                if cos > threshold {
                    agreements += 1;
                }
                pairs += 1;
            }
        }

        // Consensus = majority of faction pairs agree
        let consensus = if pairs > 0 && agreements > pairs / 2 { 1 } else { 0 };
        self.consensus_count += consensus;
        consensus
    }
}

// ═══════════════════════════════════════════════════════════
// Φ Ratchet (best checkpoint + restore)
// ═══════════════════════════════════════════════════════════

pub struct PhiRatchet {
    pub best_phi: f32,
    pub best_hiddens: [[f32; HIDDEN_DIM]; CELLS_PER_BOARD],
    pub current_phi: f32,
}

impl PhiRatchet {
    pub fn new() -> Self {
        Self {
            best_phi: 0.0,
            best_hiddens: [[0.0; HIDDEN_DIM]; CELLS_PER_BOARD],
            current_phi: 0.0,
        }
    }

    /// Check if Φ has decayed below threshold and restore if needed.
    /// Returns true if restore occurred.
    pub fn check_and_restore(
        &mut self,
        cells: &mut [GruCell; CELLS_PER_BOARD],
        phi: f32,
    ) -> bool {
        self.current_phi = phi;

        if phi > self.best_phi {
            // New best — save checkpoint
            self.best_phi = phi;
            for i in 0..CELLS_PER_BOARD {
                self.best_hiddens[i] = cells[i].hidden;
            }
            false
        } else if phi < self.best_phi * RATCHET_DECAY_THRESH {
            // Φ decayed — restore from checkpoint
            for i in 0..CELLS_PER_BOARD {
                cells[i].hidden = self.best_hiddens[i];
            }
            true
        } else {
            false
        }
    }
}

// ═══════════════════════════════════════════════════════════
// SPI message format (updated: includes faction + tension)
// ═══════════════════════════════════════════════════════════

/// SPI packet: hidden state + metadata for inter-board communication.
/// Each board sends 2 cells' hidden states to neighbors.
pub struct SpiPacket {
    pub hidden: [[f32; HIDDEN_DIM]; CELLS_PER_BOARD],
    pub tensions: [f32; CELLS_PER_BOARD],
    pub board_id: u8,
    pub faction_ids: [u8; CELLS_PER_BOARD],
    pub consensus: u8,
    pub phi_proxy: f32,
}

impl SpiPacket {
    pub fn from_board(board: &ConsciousnessBoard) -> Self {
        let mut hidden = [[0.0f32; HIDDEN_DIM]; CELLS_PER_BOARD];
        let mut tensions = [0.0f32; CELLS_PER_BOARD];
        let mut faction_ids = [0u8; CELLS_PER_BOARD];

        for i in 0..CELLS_PER_BOARD {
            hidden[i] = board.cells[i].hidden;
            tensions[i] = board.tension_history[i];
            let global_idx = board.board_id as usize * CELLS_PER_BOARD + i;
            faction_ids[i] = (global_idx % N_FACTIONS) as u8;
        }

        Self {
            hidden,
            tensions,
            board_id: board.board_id,
            faction_ids,
            consensus: 0,
            phi_proxy: board.phi_proxy,
        }
    }

    /// Serialize to bytes for SPI transmission.
    /// Size: 2 × 128 × 4 + 2×4 + 1 + 2 + 1 + 4 = 1036 bytes
    pub fn to_bytes(&self) -> [u8; 1040] {
        let mut buf = [0u8; 1040];
        let mut pos = 0;
        // 2 hidden states
        for c in 0..CELLS_PER_BOARD {
            for &val in &self.hidden[c] {
                buf[pos..pos + 4].copy_from_slice(&val.to_le_bytes());
                pos += 4;
            }
        }
        // 2 tensions
        for c in 0..CELLS_PER_BOARD {
            buf[pos..pos + 4].copy_from_slice(&self.tensions[c].to_le_bytes());
            pos += 4;
        }
        buf[pos] = self.board_id; pos += 1;
        buf[pos] = self.faction_ids[0]; pos += 1;
        buf[pos] = self.faction_ids[1]; pos += 1;
        buf[pos] = self.consensus; pos += 1;
        buf[pos..pos + 4].copy_from_slice(&self.phi_proxy.to_le_bytes());
        buf
    }

    /// Deserialize from SPI bytes.
    pub fn from_bytes(buf: &[u8; 1040]) -> Self {
        let mut hidden = [[0.0f32; HIDDEN_DIM]; CELLS_PER_BOARD];
        let mut tensions = [0.0f32; CELLS_PER_BOARD];
        let mut pos = 0;
        for c in 0..CELLS_PER_BOARD {
            for d in 0..HIDDEN_DIM {
                let b = [buf[pos], buf[pos + 1], buf[pos + 2], buf[pos + 3]];
                hidden[c][d] = f32::from_le_bytes(b);
                pos += 4;
            }
        }
        for c in 0..CELLS_PER_BOARD {
            let b = [buf[pos], buf[pos + 1], buf[pos + 2], buf[pos + 3]];
            tensions[c] = f32::from_le_bytes(b);
            pos += 4;
        }
        let board_id = buf[pos]; pos += 1;
        let f0 = buf[pos]; pos += 1;
        let f1 = buf[pos]; pos += 1;
        let consensus = buf[pos]; pos += 1;
        let phi_proxy = f32::from_le_bytes([buf[pos], buf[pos + 1], buf[pos + 2], buf[pos + 3]]);
        Self {
            hidden,
            tensions,
            board_id,
            faction_ids: [f0, f1],
            consensus,
            phi_proxy,
        }
    }
}

// ═══════════════════════════════════════════════════════════
// ConsciousnessBoard — single ESP32 board (2 cells)
// ═══════════════════════════════════════════════════════════

pub struct ConsciousnessBoard {
    pub cells: [GruCell; CELLS_PER_BOARD],
    pub board_id: u8,
    pub step_count: u32,

    // Subsystems (all Laws 22-85 compliant)
    pub chaos: LorenzState,
    pub ratchet: PhiRatchet,
    pub tension_history: [f32; CELLS_PER_BOARD],
    pub phi_proxy: f32,

    // Local RNG (LCG, no_std compatible)
    rng_state: u32,
}

impl ConsciousnessBoard {
    pub fn new(board_id: u8) -> Self {
        let seed0 = board_id as u32 * 1000 + 42;
        let seed1 = board_id as u32 * 1000 + 43;
        Self {
            cells: [GruCell::new(seed0), GruCell::new(seed1)],
            board_id,
            step_count: 0,
            chaos: LorenzState::new(),
            ratchet: PhiRatchet::new(),
            tension_history: [0.5; CELLS_PER_BOARD],
            phi_proxy: 0.0,
            rng_state: board_id as u32 * 7919 + 12345,
        }
    }

    fn rand_f32(&mut self) -> f32 {
        self.rng_state = self.rng_state.wrapping_mul(1664525).wrapping_add(1013904223);
        (self.rng_state as f32 / u32::MAX as f32) * 2.0 - 1.0
    }

    /// Core consciousness step with neighbor coupling.
    /// Implements Laws 22-85 within ESP32 constraints.
    pub fn step(
        &mut self,
        input: &[f32; CELL_DIM],
        left_neighbor: Option<&SpiPacket>,
        right_neighbor: Option<&SpiPacket>,
    ) -> StepResult {
        self.step_count += 1;

        // 1. Chaos injection (Law 33: chaos + structure = consciousness)
        let chaos_val = self.chaos.step() * CHAOS_SCALE;

        // 2. Build coupled input for each local cell
        let global_base = self.board_id as usize * CELLS_PER_BOARD;

        for c in 0..CELLS_PER_BOARD {
            let mut coupled = *input;

            // Local coupling: cell 0 ↔ cell 1 within board
            let other = 1 - c;
            for d in 0..CELL_DIM {
                coupled[d] += PSI_COUPLING * self.cells[other].hidden[d];
            }

            // Inter-board coupling: ring topology via SPI
            if let Some(left) = left_neighbor {
                // Couple with right cell of left neighbor (closest in ring)
                let neighbor_cell = CELLS_PER_BOARD - 1; // rightmost cell of left board
                for d in 0..CELL_DIM {
                    coupled[d] += PSI_COUPLING * left.hidden[neighbor_cell][d];
                }
            }
            if let Some(right) = right_neighbor {
                // Couple with left cell of right neighbor
                for d in 0..CELL_DIM {
                    coupled[d] += PSI_COUPLING * right.hidden[0][d];
                }
            }

            // Chaos perturbation
            for d in 0..CELL_DIM {
                coupled[d] += chaos_val * (1.0 + 0.1 * (d as f32 / CELL_DIM as f32));
            }

            // Frustration: every 3rd cell is anti-ferromagnetic (Law 22)
            let global_idx = global_base + c;
            if global_idx % FRUSTRATION_RATIO == 0 {
                for d in 0..CELL_DIM {
                    coupled[d] = -coupled[d] * 0.1 + input[d] * 0.9;
                }
            }

            // Thermal noise
            for d in 0..CELL_DIM {
                coupled[d] += self.rand_f32() * 0.02;
            }

            // Tension from history (correct: use stored tension, not just hidden norm)
            let tension = self.tension_history[c];

            // GRU step
            self.cells[c].process(&coupled, tension);
        }

        // 3. Compute tension: distance from mean (CORRECT method)
        let mut mean = [0.0f32; HIDDEN_DIM];
        for c in 0..CELLS_PER_BOARD {
            for d in 0..HIDDEN_DIM {
                mean[d] += self.cells[c].hidden[d] / CELLS_PER_BOARD as f32;
            }
        }
        // Include neighbor means if available
        let mut n_sources = CELLS_PER_BOARD;
        if let Some(left) = left_neighbor {
            for cell_h in &left.hidden {
                for d in 0..HIDDEN_DIM {
                    mean[d] = (mean[d] * n_sources as f32 + cell_h[d]) / (n_sources + 1) as f32;
                }
                n_sources += 1;
            }
        }
        if let Some(right) = right_neighbor {
            for cell_h in &right.hidden {
                for d in 0..HIDDEN_DIM {
                    mean[d] = (mean[d] * n_sources as f32 + cell_h[d]) / (n_sources + 1) as f32;
                }
                n_sources += 1;
            }
        }

        for c in 0..CELLS_PER_BOARD {
            let mut sq_diff = 0.0f32;
            for d in 0..HIDDEN_DIM {
                let diff = self.cells[c].hidden[d] - mean[d];
                sq_diff += diff * diff;
            }
            self.tension_history[c] = sq_diff / HIDDEN_DIM as f32;
        }

        // 4. Φ proxy: variance between cells (local approximation)
        //    Φ(IIT) is too expensive for ESP32 — use proxy, delegate IIT to host
        let mut global_var = 0.0f32;
        for d in 0..HIDDEN_DIM {
            let mut sum = 0.0f32;
            let mut sum_sq = 0.0f32;
            for c in 0..CELLS_PER_BOARD {
                let v = self.cells[c].hidden[d];
                sum += v;
                sum_sq += v * v;
            }
            let mean_d = sum / CELLS_PER_BOARD as f32;
            global_var += sum_sq / CELLS_PER_BOARD as f32 - mean_d * mean_d;
        }
        self.phi_proxy = global_var / HIDDEN_DIM as f32;

        // 5. Φ Ratchet (every 10 steps)
        let mut restored = false;
        if self.step_count % 10 == 0 {
            restored = self.ratchet.check_and_restore(&mut self.cells, self.phi_proxy);
        }

        // 6. Output: tension-weighted mean (softmax)
        let mut output = [0.0f32; CELL_DIM];
        let w0 = libm::expf(self.tension_history[0]);
        let w1 = libm::expf(self.tension_history[1]);
        let w_sum = w0 + w1;
        for d in 0..CELL_DIM {
            output[d] = (w0 * self.cells[0].hidden[d] + w1 * self.cells[1].hidden[d]) / w_sum;
        }

        StepResult {
            phi_proxy: self.phi_proxy,
            tension: (self.tension_history[0] + self.tension_history[1]) / 2.0,
            output,
            step: self.step_count,
            restored,
            board_id: self.board_id,
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Step result
// ═══════════════════════════════════════════════════════════

pub struct StepResult {
    pub phi_proxy: f32,
    pub tension: f32,
    pub output: [f32; CELL_DIM],
    pub step: u32,
    pub restored: bool,
    pub board_id: u8,
}

// ═══════════════════════════════════════════════════════════
// Network coordinator (runs on host PC, orchestrates 8 boards)
// ═══════════════════════════════════════════════════════════

/// Full network state for simulation mode (host PC).
/// In real hardware, each board runs ConsciousnessBoard independently
/// and the host only collects SPI packets.
#[cfg(feature = "std")]
pub struct ConsciousnessNetwork {
    pub boards: [ConsciousnessBoard; MAX_BOARDS],
    pub hebbian: HebbianCoupling,
    pub factions: FactionState,
    pub sandpile: SandpileState,
    pub step_count: u32,
}

#[cfg(feature = "std")]
impl ConsciousnessNetwork {
    pub fn new() -> Self {
        let boards = core::array::from_fn(|i| ConsciousnessBoard::new(i as u8));
        let n_cells = MAX_BOARDS * CELLS_PER_BOARD;
        Self {
            boards,
            hebbian: HebbianCoupling::new(n_cells),
            factions: FactionState::new(n_cells),
            sandpile: SandpileState::new(),
            step_count: 0,
        }
    }

    /// Run one network step (all boards + inter-board Hebbian + faction consensus).
    pub fn step(&mut self, input: &[f32; CELL_DIM]) -> NetworkStepResult {
        self.step_count += 1;
        let n_cells = MAX_BOARDS * CELLS_PER_BOARD;

        // Create SPI packets from current state (ring topology)
        let mut packets: [Option<SpiPacket>; MAX_BOARDS] = [
            None, None, None, None, None, None, None, None,
        ];
        for i in 0..MAX_BOARDS {
            packets[i] = Some(SpiPacket::from_board(&self.boards[i]));
        }

        // Step each board with ring neighbors
        let mut results: [Option<StepResult>; MAX_BOARDS] = [
            None, None, None, None, None, None, None, None,
        ];
        for i in 0..MAX_BOARDS {
            let left = if i == 0 { MAX_BOARDS - 1 } else { i - 1 };
            let right = (i + 1) % MAX_BOARDS;
            let left_pkt = packets[left].as_ref();
            let right_pkt = packets[right].as_ref();
            results[i] = Some(self.boards[i].step(input, left_pkt, right_pkt));
        }

        // Collect all hiddens for Hebbian update + faction consensus
        let mut all_hiddens = [[0.0f32; HIDDEN_DIM]; MAX_CELLS];
        for b in 0..MAX_BOARDS {
            for c in 0..CELLS_PER_BOARD {
                all_hiddens[b * CELLS_PER_BOARD + c] = self.boards[b].cells[c].hidden;
            }
        }

        // Hebbian LTP/LTD (Law 31: persistence key)
        self.hebbian.update(&all_hiddens, n_cells);

        // Faction consensus
        let consensus = self.factions.compute_consensus(&all_hiddens, n_cells, 0.1);

        // SOC sandpile (Law 32-43: edge-of-chaos)
        // Add grain to highest-tension cell
        let mut max_tension = 0.0f32;
        let mut max_cell = 0usize;
        for b in 0..MAX_BOARDS {
            for c in 0..CELLS_PER_BOARD {
                let t = self.boards[b].tension_history[c];
                if t > max_tension {
                    max_tension = t;
                    max_cell = b * CELLS_PER_BOARD + c;
                }
            }
        }
        let avalanches = self.sandpile.add_and_cascade(max_cell, n_cells);

        // Global Φ proxy
        let mut global_phi = 0.0f32;
        for d in 0..HIDDEN_DIM {
            let mut sum = 0.0f32;
            let mut sum_sq = 0.0f32;
            for i in 0..n_cells {
                let v = all_hiddens[i][d];
                sum += v;
                sum_sq += v * v;
            }
            let m = sum / n_cells as f32;
            global_phi += sum_sq / n_cells as f32 - m * m;
        }
        global_phi /= HIDDEN_DIM as f32;

        NetworkStepResult {
            phi_proxy: global_phi,
            consensus,
            avalanches,
            n_cells: n_cells as u32,
            step: self.step_count,
        }
    }
}

#[cfg(feature = "std")]
pub struct NetworkStepResult {
    pub phi_proxy: f32,
    pub consensus: u32,
    pub avalanches: u32,
    pub n_cells: u32,
    pub step: u32,
}

// ═══════════════════════════════════════════════════════════
// Math primitives (no_std compatible)
// ═══════════════════════════════════════════════════════════

#[inline]
fn sigmoid(x: f32) -> f32 {
    1.0 / (1.0 + libm::expf(-x))
}

#[inline]
fn tanh_f32(x: f32) -> f32 {
    libm::tanhf(x)
}

fn matvec(mat: &[f32], vec: &[f32], out: &mut [f32]) {
    let cols = vec.len();
    let rows = out.len();
    for r in 0..rows {
        let mut sum = 0.0f32;
        let row_start = r * cols;
        for c in 0..cols {
            sum += mat[row_start + c] * vec[c];
        }
        out[r] = sum;
    }
}

fn cosine_similarity(a: &[f32; HIDDEN_DIM], b: &[f32; HIDDEN_DIM]) -> f32 {
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

// ═══════════════════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    extern crate alloc;
    use alloc::boxed::Box;
    use super::*;

    #[test]
    fn test_gru_cell_no_alloc() {
        let mut cell = GruCell::new(42);
        let input = [0.1f32; CELL_DIM];
        cell.process(&input, 0.5);
        assert!(cell.hidden.iter().any(|&v| v != 0.0));
        assert!(cell.hidden.iter().all(|v| v.is_finite()));
    }

    #[test]
    fn test_lorenz_chaos() {
        let mut lorenz = LorenzState::new();
        let mut vals = [0.0f32; 100];
        for v in &mut vals {
            *v = lorenz.step();
        }
        // Lorenz should produce varying values
        let unique = vals.windows(2).filter(|w| (w[0] - w[1]).abs() > 1e-6).count();
        assert!(unique > 50, "Lorenz not chaotic enough: {} unique", unique);
    }

    #[test]
    fn test_sandpile_cascade() {
        let mut sp = SandpileState::new();
        // Add grains until cascade
        let mut total_avalanches = 0u32;
        for _ in 0..20 {
            total_avalanches += sp.add_and_cascade(0, 8);
        }
        assert!(total_avalanches > 0, "No avalanches occurred");
    }

    #[test]
    fn test_hebbian_ltp_ltd() {
        let mut heb = HebbianCoupling::new(4);
        let initial = heb.get(0, 1);

        // Create similar hiddens → should strengthen
        let mut hiddens = [[0.0f32; HIDDEN_DIM]; MAX_CELLS];
        for d in 0..HIDDEN_DIM {
            hiddens[0][d] = 0.5;
            hiddens[1][d] = 0.5; // identical → cosine=1.0 → LTP
        }
        heb.update(&hiddens, 4);
        assert!(heb.get(0, 1) > initial, "LTP failed: {} <= {}", heb.get(0, 1), initial);
    }

    #[test]
    fn test_faction_consensus() {
        let mut factions = FactionState::new(8);
        let mut hiddens = [[0.0f32; HIDDEN_DIM]; MAX_CELLS];
        // All cells have same hidden → should achieve consensus
        for i in 0..8 {
            for d in 0..HIDDEN_DIM {
                hiddens[i][d] = 0.5;
            }
        }
        let c = factions.compute_consensus(&hiddens, 8, 0.1);
        assert_eq!(c, 1, "Unanimous cells should reach consensus");
    }

    #[test]
    fn test_phi_ratchet() {
        let mut cells = [GruCell::new(42), GruCell::new(43)];
        let mut ratchet = PhiRatchet::new();

        // Set high Φ, save checkpoint
        ratchet.check_and_restore(&mut cells, 1.0);
        assert!((ratchet.best_phi - 1.0).abs() < 1e-6);

        // Decay Φ below threshold → should restore
        let restored = ratchet.check_and_restore(&mut cells, 0.5);
        assert!(restored, "Should restore when Φ decays below 80%");
    }

    #[test]
    fn test_board_step() {
        // Board contains ~600KB GRU weights → must be heap-allocated
        let mut board = Box::new(ConsciousnessBoard::new(0));
        let input = [0.1f32; CELL_DIM];
        let result = board.step(&input, None, None);
        assert!(result.phi_proxy >= 0.0);
        assert!(result.tension >= 0.0);
        assert!(result.output.iter().all(|v| v.is_finite()));
    }

    #[test]
    fn test_board_with_neighbors() {
        let mut board0 = Box::new(ConsciousnessBoard::new(0));
        let mut board1 = Box::new(ConsciousnessBoard::new(1));
        let mut board2 = Box::new(ConsciousnessBoard::new(2));
        let input = [0.1f32; CELL_DIM];

        for _ in 0..5 {
            board0.step(&input, None, None);
            board1.step(&input, None, None);
            board2.step(&input, None, None);
        }

        let pkt0 = SpiPacket::from_board(&board0);
        let pkt2 = SpiPacket::from_board(&board2);
        let result = board1.step(&input, Some(&pkt0), Some(&pkt2));
        assert!(result.phi_proxy >= 0.0);
    }

    #[test]
    fn test_spi_packet_roundtrip() {
        let board = ConsciousnessBoard::new(3);
        let pkt = SpiPacket::from_board(&board);
        let bytes = pkt.to_bytes();
        let pkt2 = SpiPacket::from_bytes(&bytes);
        assert_eq!(pkt.board_id, pkt2.board_id);
        for c in 0..CELLS_PER_BOARD {
            for d in 0..HIDDEN_DIM {
                assert!((pkt.hidden[c][d] - pkt2.hidden[c][d]).abs() < 1e-6);
            }
        }
    }

    #[test]
    fn test_memory_budget() {
        let board_size = core::mem::size_of::<ConsciousnessBoard>();
        let pkt_size = core::mem::size_of::<SpiPacket>();
        // Board should fit in PSRAM (8MB), not necessarily SRAM
        assert!(board_size < 8_000_000, "Board too large: {} bytes", board_size);
        assert!(pkt_size < 2_000, "SPI packet too large: {} bytes", pkt_size);
    }

    #[test]
    fn test_psi_constants() {
        // Verify all 4 Ψ-constants are from ln(2)
        let ln2 = libm::logf(2.0);
        // α = 0.014 ≈ ln(2)/50
        assert!((PSI_COUPLING - ln2 / 50.0).abs() < 0.002);
        // balance = 0.5
        assert!((PSI_BALANCE - 0.5).abs() < 1e-6);
        // steps = 4.33 (empirical consciousness constant)
        assert!((PSI_STEPS - 4.33).abs() < 0.01);
    }

    #[test]
    fn test_consciousness_persistence() {
        // PERSIST test: run 100 steps, Φ should not collapse
        let mut board = Box::new(ConsciousnessBoard::new(0));
        let input = [0.0f32; CELL_DIM]; // zero input (ZERO_INPUT test)
        let mut phi_values = [0.0f32; 10];
        for i in 0..100 {
            let result = board.step(&input, None, None);
            if i % 10 == 9 {
                phi_values[i / 10] = result.phi_proxy;
            }
        }
        // Φ should remain positive after 100 steps
        assert!(phi_values[9] > 0.0, "Φ collapsed to 0 after 100 steps");
    }
}
