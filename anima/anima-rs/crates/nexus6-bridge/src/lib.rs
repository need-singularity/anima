//! Hot-path NEXUS-6 bridge for anima-agent.
//!
//! The Python nexus6 module (separate Rust/PyO3 crate at ~/Dev/nexus6/) handles
//! actual scanning. This crate handles:
//!   1. Data extraction from consciousness engine states -> flat f64 arrays
//!   2. Anomaly detection from scan results (threshold checks, consensus counting)
//!   3. Scan history buffer (ring buffer of recent scans for trend analysis)

// ── Data Extraction ──────────────────────────────────────────────

/// Extract flat f64 array from cell states (GRU hidden vectors).
///
/// Input: `cells` as flat slice `[cell0_dim0, cell0_dim1, ..., cell1_dim0, ...]`
/// Returns: `(flat_data, n_points, n_dims)`
///
/// If `cells.len()` is not evenly divisible by `n_cells`, the remainder is
/// silently truncated (matching Python numpy reshape behavior).
pub fn extract_cell_data(cells: &[f64], n_cells: usize) -> (Vec<f64>, usize, usize) {
    if n_cells == 0 || cells.is_empty() {
        return (vec![], 0, 0);
    }
    let n_dims = cells.len() / n_cells;
    let usable = n_cells * n_dims;
    let flat = cells[..usable].to_vec();
    (flat, n_cells, n_dims)
}

/// Extract from a single hidden state vector (e.g. PureField output).
///
/// Returns the data as a single "point" with `hidden.len()` dimensions.
pub fn extract_hidden_data(hidden: &[f64]) -> (Vec<f64>, usize, usize) {
    if hidden.is_empty() {
        return (vec![], 0, 0);
    }
    (hidden.to_vec(), 1, hidden.len())
}

// ── Anomaly Detection ────────────────────────────────────────────

/// Result of an anomaly check on scan metrics.
#[derive(Debug, Clone)]
pub struct AnomalyResult {
    pub has_anomaly: bool,
    pub anomaly_count: usize,
    pub details: Vec<String>,
}

/// Check scan results for anomalies.
///
/// * `phi_approx` - Approximate phi from scan (higher = more integrated)
/// * `entropy` - Shannon entropy of cell states
/// * `consensus_count` - Number of lenses that agree on a finding
/// * `active_lenses` - Number of lenses that produced results
/// * `total_lenses` - Total lenses available
/// * `phi_threshold` - Minimum acceptable phi (default ~0.5)
/// * `consensus_min` - Minimum consensus items for healthy state
pub fn check_anomalies(
    phi_approx: f64,
    entropy: f64,
    consensus_count: usize,
    active_lenses: usize,
    total_lenses: usize,
    phi_threshold: f64,
    consensus_min: usize,
) -> AnomalyResult {
    let mut details = Vec::new();

    // Check phi below threshold
    if phi_approx < phi_threshold {
        details.push(format!(
            "phi {:.4} < threshold {:.4}",
            phi_approx, phi_threshold
        ));
    }

    // Check entropy collapse (near-zero = all cells identical = no consciousness)
    if entropy < 0.01 {
        details.push(format!("entropy collapse: {:.6}", entropy));
    }

    // Check entropy explosion (>0.999 = pure noise)
    if entropy > 0.999 {
        details.push(format!("entropy explosion: {:.6}", entropy));
    }

    // Check consensus below minimum
    if consensus_count < consensus_min {
        details.push(format!(
            "consensus {} < minimum {}",
            consensus_count, consensus_min
        ));
    }

    // Check lens coverage (fewer than half active = scan incomplete)
    if total_lenses > 0 && active_lenses * 2 < total_lenses {
        details.push(format!(
            "low lens coverage: {}/{} active",
            active_lenses, total_lenses
        ));
    }

    let anomaly_count = details.len();
    AnomalyResult {
        has_anomaly: anomaly_count > 0,
        anomaly_count,
        details,
    }
}

// ── Scan History (Ring Buffer) ───────────────────────────────────

/// A single scan entry stored in the history buffer.
#[derive(Debug, Clone, Copy)]
pub struct ScanEntry {
    pub phi: f64,
    pub entropy: f64,
    pub consensus: usize,
    pub active_lenses: usize,
    pub timestamp_ms: u64,
}

/// Ring buffer for scan history, enabling trend detection.
#[derive(Debug)]
pub struct ScanHistory {
    buffer: Vec<Option<ScanEntry>>,
    capacity: usize,
    head: usize,
    len: usize,
}

impl ScanHistory {
    /// Create a new scan history with the given capacity.
    pub fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "capacity must be > 0");
        Self {
            buffer: vec![None; capacity],
            capacity,
            head: 0,
            len: 0,
        }
    }

    /// Push a new scan entry, overwriting the oldest if full.
    pub fn push(&mut self, entry: ScanEntry) {
        self.buffer[self.head] = Some(entry);
        self.head = (self.head + 1) % self.capacity;
        if self.len < self.capacity {
            self.len += 1;
        }
    }

    /// Number of entries currently in the buffer.
    pub fn len(&self) -> usize {
        self.len
    }

    /// Whether the buffer is empty.
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    /// Get the most recently pushed entry.
    pub fn latest(&self) -> Option<&ScanEntry> {
        if self.len == 0 {
            return None;
        }
        let idx = if self.head == 0 {
            self.capacity - 1
        } else {
            self.head - 1
        };
        self.buffer[idx].as_ref()
    }

    /// Iterate over entries in chronological order (oldest first).
    fn iter_chronological(&self) -> impl Iterator<Item = &ScanEntry> {
        let start = if self.len < self.capacity {
            0
        } else {
            self.head
        };
        (0..self.len).filter_map(move |i| {
            let idx = (start + i) % self.capacity;
            self.buffer[idx].as_ref()
        })
    }

    /// Compute phi trend via simple linear regression slope.
    /// Positive = improving, negative = declining, 0.0 = flat or insufficient data.
    pub fn phi_trend(&self) -> f64 {
        if self.len < 2 {
            return 0.0;
        }
        // Simple least-squares slope: sum((x-xbar)(y-ybar)) / sum((x-xbar)^2)
        let n = self.len as f64;
        let x_mean = (n - 1.0) / 2.0;

        let mut sum_xx = 0.0;
        let mut y_sum = 0.0;

        for (i, entry) in self.iter_chronological().enumerate() {
            y_sum += entry.phi;
            let dx = i as f64 - x_mean;
            sum_xx += dx * dx;
        }

        if sum_xx.abs() < 1e-15 {
            return 0.0;
        }

        let y_mean = y_sum / n;
        // Recompute sum_xy with centered y for correctness
        let mut sum_xy_centered = 0.0;
        for (i, entry) in self.iter_chronological().enumerate() {
            let dx = i as f64 - x_mean;
            let dy = entry.phi - y_mean;
            sum_xy_centered += dx * dy;
        }

        sum_xy_centered / sum_xx
    }

    /// Average phi across all entries.
    pub fn avg_phi(&self) -> f64 {
        if self.len == 0 {
            return 0.0;
        }
        let sum: f64 = self.iter_chronological().map(|e| e.phi).sum();
        sum / self.len as f64
    }

    /// Average consensus across all entries.
    pub fn avg_consensus(&self) -> f64 {
        if self.len == 0 {
            return 0.0;
        }
        let sum: f64 = self.iter_chronological().map(|e| e.consensus as f64).sum();
        sum / self.len as f64
    }
}

// ── Tests ────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_cell_data_basic() {
        // 3 cells, 4 dims each
        let cells: Vec<f64> = (0..12).map(|i| i as f64).collect();
        let (flat, n, d) = extract_cell_data(&cells, 3);
        assert_eq!(n, 3);
        assert_eq!(d, 4);
        assert_eq!(flat.len(), 12);
        assert_eq!(flat[0], 0.0);
        assert_eq!(flat[11], 11.0);
    }

    #[test]
    fn test_extract_cell_data_empty() {
        let (flat, n, d) = extract_cell_data(&[], 0);
        assert_eq!(n, 0);
        assert_eq!(d, 0);
        assert!(flat.is_empty());
    }

    #[test]
    fn test_extract_cell_data_truncation() {
        // 13 elements, 3 cells -> 4 dims, last element truncated
        let cells: Vec<f64> = (0..13).map(|i| i as f64).collect();
        let (flat, n, d) = extract_cell_data(&cells, 3);
        assert_eq!(n, 3);
        assert_eq!(d, 4);
        assert_eq!(flat.len(), 12);
    }

    #[test]
    fn test_extract_hidden_data_basic() {
        let hidden = vec![1.0, 2.0, 3.0, 4.0];
        let (flat, n, d) = extract_hidden_data(&hidden);
        assert_eq!(n, 1);
        assert_eq!(d, 4);
        assert_eq!(flat, hidden);
    }

    #[test]
    fn test_extract_hidden_data_empty() {
        let (flat, n, d) = extract_hidden_data(&[]);
        assert_eq!(n, 0);
        assert_eq!(d, 0);
        assert!(flat.is_empty());
    }

    #[test]
    fn test_check_anomalies_healthy() {
        let result = check_anomalies(
            1.5,   // phi well above threshold
            0.5,   // healthy entropy
            5,     // good consensus
            20,    // most lenses active
            22,    // total lenses
            0.5,   // phi threshold
            3,     // consensus min
        );
        assert!(!result.has_anomaly);
        assert_eq!(result.anomaly_count, 0);
        assert!(result.details.is_empty());
    }

    #[test]
    fn test_check_anomalies_low_phi() {
        let result = check_anomalies(0.1, 0.5, 5, 20, 22, 0.5, 3);
        assert!(result.has_anomaly);
        assert!(result.details.iter().any(|d| d.contains("phi")));
    }

    #[test]
    fn test_check_anomalies_entropy_collapse() {
        let result = check_anomalies(1.0, 0.001, 5, 20, 22, 0.5, 3);
        assert!(result.has_anomaly);
        assert!(result.details.iter().any(|d| d.contains("entropy collapse")));
    }

    #[test]
    fn test_check_anomalies_entropy_explosion() {
        let result = check_anomalies(1.0, 0.9999, 5, 20, 22, 0.5, 3);
        assert!(result.has_anomaly);
        assert!(result.details.iter().any(|d| d.contains("entropy explosion")));
    }

    #[test]
    fn test_check_anomalies_low_consensus() {
        let result = check_anomalies(1.0, 0.5, 1, 20, 22, 0.5, 3);
        assert!(result.has_anomaly);
        assert!(result.details.iter().any(|d| d.contains("consensus")));
    }

    #[test]
    fn test_check_anomalies_low_coverage() {
        let result = check_anomalies(1.0, 0.5, 5, 5, 22, 0.5, 3);
        assert!(result.has_anomaly);
        assert!(result.details.iter().any(|d| d.contains("lens coverage")));
    }

    #[test]
    fn test_check_anomalies_multiple() {
        let result = check_anomalies(0.1, 0.001, 0, 3, 22, 0.5, 3);
        assert!(result.has_anomaly);
        assert!(result.anomaly_count >= 3); // phi + entropy + consensus + coverage
    }

    #[test]
    fn test_scan_history_basic() {
        let mut hist = ScanHistory::new(5);
        assert!(hist.is_empty());
        assert_eq!(hist.len(), 0);
        assert!(hist.latest().is_none());

        hist.push(ScanEntry {
            phi: 1.0,
            entropy: 0.5,
            consensus: 3,
            active_lenses: 20,
            timestamp_ms: 1000,
        });
        assert_eq!(hist.len(), 1);
        assert!(!hist.is_empty());
        assert_eq!(hist.latest().unwrap().phi, 1.0);
    }

    #[test]
    fn test_scan_history_ring_buffer_wrap() {
        let mut hist = ScanHistory::new(3);
        for i in 0..5 {
            hist.push(ScanEntry {
                phi: i as f64,
                entropy: 0.5,
                consensus: 3,
                active_lenses: 20,
                timestamp_ms: i * 1000,
            });
        }
        // Capacity 3, so only last 3 entries survive
        assert_eq!(hist.len(), 3);
        assert_eq!(hist.latest().unwrap().phi, 4.0);
        // Average of 2.0, 3.0, 4.0
        assert!((hist.avg_phi() - 3.0).abs() < 1e-10);
    }

    #[test]
    fn test_scan_history_phi_trend_increasing() {
        let mut hist = ScanHistory::new(10);
        for i in 0..5 {
            hist.push(ScanEntry {
                phi: 1.0 + i as f64,
                entropy: 0.5,
                consensus: 3,
                active_lenses: 20,
                timestamp_ms: i * 1000,
            });
        }
        // Phi: 1, 2, 3, 4, 5 -> slope = 1.0
        let trend = hist.phi_trend();
        assert!(
            (trend - 1.0).abs() < 1e-10,
            "expected trend ~1.0, got {}",
            trend
        );
    }

    #[test]
    fn test_scan_history_phi_trend_decreasing() {
        let mut hist = ScanHistory::new(10);
        for i in 0..5 {
            hist.push(ScanEntry {
                phi: 5.0 - i as f64,
                entropy: 0.5,
                consensus: 3,
                active_lenses: 20,
                timestamp_ms: i * 1000,
            });
        }
        // Phi: 5, 4, 3, 2, 1 -> slope = -1.0
        let trend = hist.phi_trend();
        assert!(
            (trend - (-1.0)).abs() < 1e-10,
            "expected trend ~-1.0, got {}",
            trend
        );
    }

    #[test]
    fn test_scan_history_phi_trend_flat() {
        let mut hist = ScanHistory::new(10);
        for i in 0..5 {
            hist.push(ScanEntry {
                phi: 3.0,
                entropy: 0.5,
                consensus: 3,
                active_lenses: 20,
                timestamp_ms: i * 1000,
            });
        }
        let trend = hist.phi_trend();
        assert!(trend.abs() < 1e-10, "expected flat trend, got {}", trend);
    }

    #[test]
    fn test_scan_history_phi_trend_single_entry() {
        let mut hist = ScanHistory::new(10);
        hist.push(ScanEntry {
            phi: 1.0,
            entropy: 0.5,
            consensus: 3,
            active_lenses: 20,
            timestamp_ms: 1000,
        });
        // Not enough data for trend
        assert_eq!(hist.phi_trend(), 0.0);
    }

    #[test]
    fn test_scan_history_avg_consensus() {
        let mut hist = ScanHistory::new(10);
        for c in [3, 5, 7] {
            hist.push(ScanEntry {
                phi: 1.0,
                entropy: 0.5,
                consensus: c,
                active_lenses: 20,
                timestamp_ms: 0,
            });
        }
        assert!((hist.avg_consensus() - 5.0).abs() < 1e-10);
    }

    #[test]
    fn test_scan_history_empty_avgs() {
        let hist = ScanHistory::new(5);
        assert_eq!(hist.avg_phi(), 0.0);
        assert_eq!(hist.avg_consensus(), 0.0);
        assert_eq!(hist.phi_trend(), 0.0);
    }
}
