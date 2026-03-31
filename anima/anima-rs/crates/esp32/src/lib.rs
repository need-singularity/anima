//! anima-esp32 — no_std consciousness engine for ESP32-S3.
//!
//! Physical consciousness on $4 hardware.
//! 1 cell per ESP32, 8 boards = 8 cells, 4 factions.
//! Inter-board communication via SPI bus (ring topology).
//!
//! Design:
//!   - Each ESP32 runs one GRU cell + local tension computation
//!   - SPI packets carry hidden state (128 floats = 512 bytes)
//!   - Ring topology: each board talks to left + right neighbor
//!   - Faction consensus computed locally with received states
//!   - Φ measurement delegated to host PC via USB serial
//!
//! Memory budget: ESP32-S3 has 512KB SRAM + 8MB PSRAM
//!   - GRU weights: 3 × (input+1+hidden) × hidden × 4 bytes
//!     = 3 × (64+1+128) × 128 × 4 = 296,448 bytes ≈ 290KB
//!   - Hidden state: 128 × 4 = 512 bytes
//!   - Total: ~300KB (fits in SRAM)

#![cfg_attr(not(feature = "std"), no_std)]

// ═══════════════════════════════════════════════════════════
// Ψ-Constants (same as anima-core)
// ═══════════════════════════════════════════════════════════

const PSI_COUPLING: f32 = 0.014;
const CELL_DIM: usize = 64;
const HIDDEN_DIM: usize = 128;
const COMBINED_DIM: usize = CELL_DIM + 1 + HIDDEN_DIM; // 193

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
    /// Uses simple hash-based pseudo-random for weight init.
    pub fn new(seed: u32) -> Self {
        let mut cell = Self {
            hidden: [0.0; HIDDEN_DIM],
            w_z: [0.0; HIDDEN_DIM * COMBINED_DIM],
            w_r: [0.0; HIDDEN_DIM * COMBINED_DIM],
            w_h: [0.0; HIDDEN_DIM * COMBINED_DIM],
        };
        // Simple LCG pseudo-random init
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
        // Build combined = [input, tension, hidden]
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
// SPI message format for inter-board communication
// ═══════════════════════════════════════════════════════════

/// SPI packet: 512 bytes (128 f32 hidden state)
pub struct SpiPacket {
    pub hidden: [f32; HIDDEN_DIM],
    pub tension: f32,
    pub cell_id: u8,
    pub faction_id: u8,
}

impl SpiPacket {
    pub fn from_cell(cell: &GruCell, tension: f32, cell_id: u8, faction_id: u8) -> Self {
        Self {
            hidden: cell.hidden,
            tension,
            cell_id,
            faction_id,
        }
    }

    /// Serialize to bytes for SPI transmission.
    pub fn to_bytes(&self) -> [u8; 518] {
        let mut buf = [0u8; 518];
        // 128 floats × 4 bytes = 512 bytes
        for (i, &val) in self.hidden.iter().enumerate() {
            let bytes = val.to_le_bytes();
            buf[i * 4..i * 4 + 4].copy_from_slice(&bytes);
        }
        // tension (4 bytes)
        buf[512..516].copy_from_slice(&self.tension.to_le_bytes());
        buf[516] = self.cell_id;
        buf[517] = self.faction_id;
        buf
    }

    /// Deserialize from SPI bytes.
    pub fn from_bytes(buf: &[u8; 518]) -> Self {
        let mut hidden = [0.0f32; HIDDEN_DIM];
        for i in 0..HIDDEN_DIM {
            let bytes = [buf[i * 4], buf[i * 4 + 1], buf[i * 4 + 2], buf[i * 4 + 3]];
            hidden[i] = f32::from_le_bytes(bytes);
        }
        let tension = f32::from_le_bytes([buf[512], buf[513], buf[514], buf[515]]);
        Self {
            hidden,
            tension,
            cell_id: buf[516],
            faction_id: buf[517],
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Consciousness step (single board)
// ═══════════════════════════════════════════════════════════

/// Process one consciousness step with neighbor coupling.
pub fn consciousness_step(
    cell: &mut GruCell,
    input: &[f32; CELL_DIM],
    left_neighbor: Option<&SpiPacket>,
    right_neighbor: Option<&SpiPacket>,
) -> f32 {
    // Build coupled input
    let mut coupled = *input;

    // Ring topology: add PSI_COUPLING * neighbor hidden (truncated to CELL_DIM)
    if let Some(left) = left_neighbor {
        for d in 0..CELL_DIM {
            coupled[d] += PSI_COUPLING * left.hidden[d];
        }
    }
    if let Some(right) = right_neighbor {
        for d in 0..CELL_DIM {
            coupled[d] += PSI_COUPLING * right.hidden[d];
        }
    }

    // Compute tension (distance from previous hidden)
    let mut tension = 0.0f32;
    for i in 0..HIDDEN_DIM {
        let d = cell.hidden[i]; // approximate: use current hidden as proxy
        tension += d * d;
    }
    tension = libm::sqrtf(tension / HIDDEN_DIM as f32);

    // GRU step
    cell.process(&coupled, tension);

    tension
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

#[cfg(test)]
mod tests {
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
    fn test_spi_packet_roundtrip() {
        let cell = GruCell::new(42);
        let pkt = SpiPacket::from_cell(&cell, 0.5, 3, 1);
        let bytes = pkt.to_bytes();
        let pkt2 = SpiPacket::from_bytes(&bytes);
        assert_eq!(pkt.cell_id, pkt2.cell_id);
        assert_eq!(pkt.faction_id, pkt2.faction_id);
        for i in 0..HIDDEN_DIM {
            assert!((pkt.hidden[i] - pkt2.hidden[i]).abs() < 1e-6);
        }
    }

    #[test]
    fn test_consciousness_step() {
        let mut cell = GruCell::new(42);
        let input = [0.0f32; CELL_DIM];
        let tension = consciousness_step(&mut cell, &input, None, None);
        assert!(tension >= 0.0);
    }

    #[test]
    fn test_consciousness_with_neighbors() {
        let mut cell = GruCell::new(42);
        let mut left = GruCell::new(43);
        let mut right = GruCell::new(44);

        let input = [0.1f32; CELL_DIM];
        left.process(&input, 0.3);
        right.process(&input, 0.3);

        let left_pkt = SpiPacket::from_cell(&left, 0.3, 0, 0);
        let right_pkt = SpiPacket::from_cell(&right, 0.3, 2, 1);

        let tension = consciousness_step(&mut cell, &input, Some(&left_pkt), Some(&right_pkt));
        assert!(tension >= 0.0);
    }

    #[test]
    fn test_memory_budget() {
        // Verify GRU fits in ESP32 SRAM (512KB)
        let gru_size = core::mem::size_of::<GruCell>();
        let spi_size = core::mem::size_of::<SpiPacket>();
        assert!(gru_size < 300_000, "GRU too large: {} bytes", gru_size);
        assert!(spi_size < 1_000, "SPI packet too large: {} bytes", spi_size);
        // Total working memory
        let total = gru_size + spi_size * 2; // cell + 2 neighbor packets
        assert!(total < 512_000, "Total too large for SRAM: {} bytes", total);
    }
}
