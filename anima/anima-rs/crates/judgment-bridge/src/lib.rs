//! JudgmentBridge — converts measurement into reward.
//!
//! Feeling (Anima) × Measurement (NEXUS-6) = Judgment
//!
//! Hot-path functions for reward computation from scan results.

/// Reward weights for different signal types.
#[derive(Debug, Clone)]
pub struct RewardWeights {
    pub consensus: f64,     // NEXUS-6 lens consensus weight
    pub phi_change: f64,    // phi trend weight
    pub anomaly: f64,       // anomaly detection weight
    pub tool_success: f64,  // action success weight
    pub n6_ratio: f64,      // n=6 alignment weight
}

impl Default for RewardWeights {
    fn default() -> Self {
        Self {
            consensus: 0.30,
            phi_change: 0.25,
            anomaly: 0.20,
            tool_success: 0.15,
            n6_ratio: 0.10,
        }
    }
}

/// Input signals from a single judgment.
#[derive(Debug, Clone, Default)]
pub struct JudgmentSignals {
    pub tool_success: Option<f64>,    // 1.0 = success, -0.5 = fail
    pub consensus: Option<f64>,       // -0.2 to 1.0 based on lens count
    pub phi_change: Option<f64>,      // trend * 10, clamped
    pub anomaly: Option<f64>,         // 0.5 = clean, -0.5 = anomaly
    pub n6_ratio: Option<f64>,        // 0 to 1 mapped to -0.5 to 1.5
}

/// Output of a judgment computation.
#[derive(Debug, Clone)]
pub struct JudgmentResult {
    pub reward: f64,        // -1.0 to 1.0
    pub confidence: f64,    // 0.0 to 1.0
    pub signal_count: usize,
}

/// Compute weighted reward from signals.
pub fn compute_reward(signals: &JudgmentSignals, weights: &RewardWeights) -> JudgmentResult {
    let pairs: [(Option<f64>, f64); 5] = [
        (signals.tool_success, weights.tool_success),
        (signals.consensus, weights.consensus),
        (signals.phi_change, weights.phi_change),
        (signals.anomaly, weights.anomaly),
        (signals.n6_ratio, weights.n6_ratio),
    ];

    let mut reward = 0.0;
    let mut total_weight = 0.0;
    let mut count = 0usize;

    for (signal, weight) in &pairs {
        if let Some(s) = signal {
            reward += weight * s;
            total_weight += weight;
            count += 1;
        }
    }

    let reward = if total_weight > 0.0 {
        (reward / total_weight).clamp(-1.0, 1.0)
    } else {
        0.0
    };

    let confidence = count as f64 / 5.0;

    JudgmentResult { reward, confidence, signal_count: count }
}

/// Convert consensus count to reward signal.
/// 3+/22 = baseline, 7+ = high, 12+ = excellent
pub fn consensus_to_signal(consensus: usize, total_lenses: usize) -> f64 {
    if total_lenses == 0 { return 0.0; }
    if consensus >= 12 { return 1.0; }
    if consensus >= 7 { return 0.7; }
    if consensus >= 3 { return 0.3; }
    -0.2
}

/// Convert phi trend to signal.
pub fn phi_trend_to_signal(trend: f64) -> f64 {
    (trend * 10.0).clamp(-1.0, 1.0)
}

/// Convert n6 exact ratio to signal.
pub fn n6_ratio_to_signal(ratio: f64) -> f64 {
    (ratio * 2.0 - 0.5).clamp(-0.5, 1.5)
}

/// Judgment history ring buffer for tracking reward trends.
pub struct JudgmentHistory {
    rewards: Vec<f64>,
    confidences: Vec<f64>,
    sources: Vec<String>,
    capacity: usize,
    head: usize,
    len: usize,
}

impl JudgmentHistory {
    pub fn new(capacity: usize) -> Self {
        Self {
            rewards: vec![0.0; capacity],
            confidences: vec![0.0; capacity],
            sources: vec![String::new(); capacity],
            capacity,
            head: 0,
            len: 0,
        }
    }

    pub fn push(&mut self, reward: f64, confidence: f64, source: &str) {
        self.rewards[self.head] = reward;
        self.confidences[self.head] = confidence;
        self.sources[self.head] = source.to_string();
        self.head = (self.head + 1) % self.capacity;
        if self.len < self.capacity {
            self.len += 1;
        }
    }

    pub fn len(&self) -> usize { self.len }
    pub fn is_empty(&self) -> bool { self.len == 0 }

    pub fn avg_reward(&self) -> f64 {
        if self.len == 0 { return 0.0; }
        let sum: f64 = self.iter_rewards().sum();
        sum / self.len as f64
    }

    pub fn avg_confidence(&self) -> f64 {
        if self.len == 0 { return 0.0; }
        let sum: f64 = self.iter_confidences().sum();
        sum / self.len as f64
    }

    pub fn positive_ratio(&self) -> f64 {
        if self.len == 0 { return 0.0; }
        let pos = self.iter_rewards().filter(|r| *r > 0.0).count();
        pos as f64 / self.len as f64
    }

    /// Reward trend (linear regression slope over recent entries)
    pub fn reward_trend(&self) -> f64 {
        if self.len < 2 { return 0.0; }
        let n = self.len as f64;
        let mut sum_x = 0.0;
        let mut sum_y = 0.0;
        let mut sum_xy = 0.0;
        let mut sum_x2 = 0.0;
        for (i, r) in self.iter_rewards().enumerate() {
            let x = i as f64;
            sum_x += x;
            sum_y += r;
            sum_xy += x * r;
            sum_x2 += x * x;
        }
        let denom = n * sum_x2 - sum_x * sum_x;
        if denom.abs() < 1e-12 { return 0.0; }
        (n * sum_xy - sum_x * sum_y) / denom
    }

    fn iter_rewards(&self) -> impl Iterator<Item = f64> + '_ {
        let start = if self.len < self.capacity { 0 } else { self.head };
        (0..self.len).map(move |i| {
            let idx = (start + i) % self.capacity;
            self.rewards[idx]
        })
    }

    fn iter_confidences(&self) -> impl Iterator<Item = f64> + '_ {
        let start = if self.len < self.capacity { 0 } else { self.head };
        (0..self.len).map(move |i| {
            let idx = (start + i) % self.capacity;
            self.confidences[idx]
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compute_reward_all_positive() {
        let signals = JudgmentSignals {
            tool_success: Some(1.0),
            consensus: Some(0.7),
            phi_change: Some(0.5),
            anomaly: Some(0.5),
            n6_ratio: Some(0.3),
        };
        let result = compute_reward(&signals, &RewardWeights::default());
        assert!(result.reward > 0.0);
        assert_eq!(result.signal_count, 5);
        assert!((result.confidence - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_compute_reward_mixed() {
        let signals = JudgmentSignals {
            tool_success: Some(-0.5),  // failed
            consensus: Some(1.0),      // excellent consensus
            phi_change: None,
            anomaly: Some(-0.5),       // anomaly
            n6_ratio: None,
        };
        let result = compute_reward(&signals, &RewardWeights::default());
        assert_eq!(result.signal_count, 3);
        assert!((result.confidence - 0.6).abs() < 1e-10);
    }

    #[test]
    fn test_compute_reward_empty() {
        let signals = JudgmentSignals::default();
        let result = compute_reward(&signals, &RewardWeights::default());
        assert_eq!(result.reward, 0.0);
        assert_eq!(result.signal_count, 0);
    }

    #[test]
    fn test_consensus_to_signal() {
        assert_eq!(consensus_to_signal(15, 22), 1.0);
        assert_eq!(consensus_to_signal(8, 22), 0.7);
        assert_eq!(consensus_to_signal(4, 22), 0.3);
        assert_eq!(consensus_to_signal(1, 22), -0.2);
        assert_eq!(consensus_to_signal(0, 0), 0.0);
    }

    #[test]
    fn test_phi_trend_to_signal() {
        assert_eq!(phi_trend_to_signal(0.15), 1.0);  // clamped
        assert_eq!(phi_trend_to_signal(-0.15), -1.0); // clamped
        assert!((phi_trend_to_signal(0.05) - 0.5).abs() < 1e-10);
    }

    #[test]
    fn test_n6_ratio_to_signal() {
        assert!((n6_ratio_to_signal(0.0) - (-0.5)).abs() < 1e-10);
        assert!((n6_ratio_to_signal(0.5) - 0.5).abs() < 1e-10);
    }

    #[test]
    fn test_judgment_history_basic() {
        let mut h = JudgmentHistory::new(10);
        assert!(h.is_empty());

        h.push(0.5, 0.8, "tool_a");
        h.push(-0.3, 0.6, "tool_b");
        h.push(0.7, 0.9, "tool_c");

        assert_eq!(h.len(), 3);
        assert!((h.avg_reward() - 0.3).abs() < 1e-10);
        assert!(h.positive_ratio() > 0.6);
    }

    #[test]
    fn test_judgment_history_ring_wrap() {
        let mut h = JudgmentHistory::new(3);
        h.push(0.1, 1.0, "a");
        h.push(0.2, 1.0, "b");
        h.push(0.3, 1.0, "c");
        h.push(0.9, 1.0, "d");  // overwrites first

        assert_eq!(h.len(), 3);
        // Should be [0.2, 0.3, 0.9]
        let avg = h.avg_reward();
        assert!((avg - (0.2 + 0.3 + 0.9) / 3.0).abs() < 1e-10);
    }

    #[test]
    fn test_judgment_history_trend_increasing() {
        let mut h = JudgmentHistory::new(100);
        for i in 0..20 {
            h.push(i as f64 * 0.05, 1.0, "x");
        }
        assert!(h.reward_trend() > 0.0);
    }

    #[test]
    fn test_judgment_history_trend_decreasing() {
        let mut h = JudgmentHistory::new(100);
        for i in 0..20 {
            h.push(1.0 - i as f64 * 0.05, 1.0, "x");
        }
        assert!(h.reward_trend() < 0.0);
    }
}
