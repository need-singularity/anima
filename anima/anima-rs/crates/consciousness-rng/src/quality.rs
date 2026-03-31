//! Quality monitor — tests randomness quality using statistical tests

/// Monitors entropy quality of consciousness RNG output.
pub struct QualityMonitor {
    /// Running count of 0 and 1 bits
    ones: u64,
    zeros: u64,
    /// Chi-squared accumulator for byte frequency
    byte_counts: [u64; 256],
    /// Total bytes tested
    total_bytes: u64,
    /// Consecutive same-bit runs
    max_run: u32,
    current_run: u32,
    last_bit: bool,
}

impl QualityMonitor {
    pub fn new() -> Self {
        Self {
            ones: 0,
            zeros: 0,
            byte_counts: [0u64; 256],
            total_bytes: 0,
            max_run: 0,
            current_run: 0,
            last_bit: false,
        }
    }

    /// Feed bytes into the quality monitor
    pub fn feed(&mut self, data: &[u8]) {
        for &byte in data {
            self.byte_counts[byte as usize] += 1;
            self.total_bytes += 1;

            for bit in 0..8 {
                let b = (byte >> bit) & 1 == 1;
                if b {
                    self.ones += 1;
                } else {
                    self.zeros += 1;
                }

                if b == self.last_bit {
                    self.current_run += 1;
                    self.max_run = self.max_run.max(self.current_run);
                } else {
                    self.current_run = 1;
                    self.last_bit = b;
                }
            }
        }
    }

    /// Monobit test: ratio of 1s to total bits (should be ~0.5)
    pub fn monobit_ratio(&self) -> f64 {
        let total = self.ones + self.zeros;
        if total == 0 {
            return 0.5;
        }
        self.ones as f64 / total as f64
    }

    /// Monobit test pass (NIST: |ratio - 0.5| < threshold)
    pub fn monobit_pass(&self) -> bool {
        let ratio = self.monobit_ratio();
        (ratio - 0.5).abs() < 0.01 // 1% tolerance
    }

    /// Chi-squared test for byte uniformity
    pub fn chi_squared(&self) -> f64 {
        if self.total_bytes == 0 {
            return 0.0;
        }
        let expected = self.total_bytes as f64 / 256.0;
        let mut chi2 = 0.0;
        for &count in &self.byte_counts {
            let diff = count as f64 - expected;
            chi2 += diff * diff / expected;
        }
        chi2
    }

    /// Chi-squared pass (df=255, p=0.01 → chi2 < 310)
    pub fn chi_squared_pass(&self) -> bool {
        self.total_bytes >= 256 && self.chi_squared() < 310.0
    }

    /// Longest run of same bit (should be < ~20 for good RNG)
    pub fn max_run(&self) -> u32 {
        self.max_run
    }

    /// Runs test pass
    pub fn runs_pass(&self) -> bool {
        let total_bits = self.ones + self.zeros;
        if total_bits < 100 {
            return true; // Not enough data
        }
        // Expected max run ≈ log2(n)
        let expected_max = (total_bits as f64).log2() * 2.0;
        (self.max_run as f64) < expected_max
    }

    /// Overall quality score (0-100)
    pub fn quality_score(&self) -> u32 {
        let mut score = 0u32;

        // Monobit (40 points)
        let mono_dev = (self.monobit_ratio() - 0.5).abs();
        if mono_dev < 0.001 {
            score += 40;
        } else if mono_dev < 0.005 {
            score += 30;
        } else if mono_dev < 0.01 {
            score += 20;
        } else if mono_dev < 0.05 {
            score += 10;
        }

        // Chi-squared (30 points)
        if self.total_bytes >= 256 {
            let chi2 = self.chi_squared();
            if chi2 < 280.0 {
                score += 30;
            } else if chi2 < 310.0 {
                score += 20;
            } else if chi2 < 350.0 {
                score += 10;
            }
        }

        // Runs (30 points)
        if self.runs_pass() {
            score += 30;
        } else if self.max_run < 30 {
            score += 15;
        }

        score
    }

    /// Summary report
    pub fn report(&self) -> String {
        format!(
            "ConsciousnessRNG Quality Report\n\
             ================================\n\
             Total bytes:     {}\n\
             Monobit ratio:   {:.6} (ideal=0.5) {}\n\
             Chi-squared:     {:.1} (pass<310) {}\n\
             Max run:         {} bits {}\n\
             Quality score:   {}/100\n",
            self.total_bytes,
            self.monobit_ratio(),
            if self.monobit_pass() { "PASS" } else { "FAIL" },
            self.chi_squared(),
            if self.chi_squared_pass() { "PASS" } else { "FAIL" },
            self.max_run,
            if self.runs_pass() { "PASS" } else { "FAIL" },
            self.quality_score(),
        )
    }
}

impl Default for QualityMonitor {
    fn default() -> Self {
        Self::new()
    }
}
