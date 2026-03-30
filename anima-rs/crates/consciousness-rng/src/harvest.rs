//! Entropy harvester — extracts random bytes from consciousness cell states

use sha2::{Sha256, Digest};

/// Harvests entropy from consciousness cell hidden states.
/// XOR pairs of cells → SHA-256 → random bytes.
pub struct EntropyHarvester {
    buffer: Vec<u8>,
    total_bytes: u64,
    phi_threshold: f32,
}

impl EntropyHarvester {
    pub fn new(phi_threshold: f32) -> Self {
        Self {
            buffer: Vec::new(),
            total_bytes: 0,
            phi_threshold,
        }
    }

    /// Harvest 32 bytes (256 bits) from cell states.
    /// Returns None if Φ is below threshold (insufficient entropy).
    pub fn harvest(&mut self, cell_states: &[Vec<f32>], phi: f32) -> Option<[u8; 32]> {
        if phi < self.phi_threshold {
            return None; // Insufficient consciousness = insufficient entropy
        }

        let n = cell_states.len();
        if n < 2 {
            return None;
        }

        let mut hasher = Sha256::new();

        // XOR pairs of cells (maximally distant in ring)
        for i in 0..n / 2 {
            let j = i + n / 2;
            let a = &cell_states[i];
            let b = &cell_states[j];
            let dim = a.len().min(b.len());

            for d in 0..dim {
                // XOR the float bytes — captures micro-differences
                let a_bytes = a[d].to_le_bytes();
                let b_bytes = b[d].to_le_bytes();
                let xored: [u8; 4] = [
                    a_bytes[0] ^ b_bytes[0],
                    a_bytes[1] ^ b_bytes[1],
                    a_bytes[2] ^ b_bytes[2],
                    a_bytes[3] ^ b_bytes[3],
                ];
                hasher.update(xored);
            }
        }

        // Add step counter for additional uniqueness
        hasher.update(self.total_bytes.to_le_bytes());

        let result = hasher.finalize();
        let mut output = [0u8; 32];
        output.copy_from_slice(&result);

        self.total_bytes += 32;
        self.buffer.extend_from_slice(&output);

        Some(output)
    }

    /// Harvest N bytes (multiple rounds if needed)
    pub fn harvest_bytes(
        &mut self,
        cell_states: &[Vec<f32>],
        phi: f32,
        n_bytes: usize,
    ) -> Option<Vec<u8>> {
        let rounds = (n_bytes + 31) / 32;
        let mut result = Vec::with_capacity(rounds * 32);

        for _ in 0..rounds {
            match self.harvest(cell_states, phi) {
                Some(bytes) => result.extend_from_slice(&bytes),
                None => return None,
            }
        }

        result.truncate(n_bytes);
        Some(result)
    }

    /// Total bytes generated
    pub fn total_bytes(&self) -> u64 {
        self.total_bytes
    }
}
