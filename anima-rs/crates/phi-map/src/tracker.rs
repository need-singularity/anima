//! Real-time Φ tracker — records consciousness state over time

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhiSnapshot {
    pub step: usize,
    pub phi_iit: f64,
    pub phi_proxy: f64,
    pub ce: f64,
    pub cells: usize,
    pub modules: Vec<String>,
    pub laws_active: Vec<u32>,  // active law numbers at this step
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhiTracker {
    pub history: Vec<PhiSnapshot>,
    pub laws_registry: Vec<LawEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LawEntry {
    pub id: u32,
    pub name: String,
    pub effect: LawEffect,     // expected Φ effect
    pub verified: bool,
    pub phi_delta_pct: f64,    // measured Φ change when active
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LawEffect {
    PhiUp,      // law should increase Φ
    PhiDown,    // law should decrease Φ
    Stabilize,  // law should prevent collapse
    Neutral,    // no direct Φ effect
}

impl PhiTracker {
    pub fn new() -> Self {
        Self {
            history: Vec::new(),
            laws_registry: Vec::new(),
        }
    }

    pub fn record(&mut self, snapshot: PhiSnapshot) {
        self.history.push(snapshot);
    }

    pub fn register_law(&mut self, law: LawEntry) {
        self.laws_registry.push(law);
    }

    /// Get Φ trend over last N steps
    pub fn trend(&self, window: usize) -> f64 {
        let n = self.history.len();
        if n < 2 {
            return 0.0;
        }
        let start = if n > window { n - window } else { 0 };
        let slice = &self.history[start..];
        if slice.len() < 2 {
            return 0.0;
        }

        // Linear regression slope
        let n_f = slice.len() as f64;
        let x_mean = (n_f - 1.0) / 2.0;
        let y_mean: f64 = slice.iter().map(|s| s.phi_iit).sum::<f64>() / n_f;
        let mut num = 0.0;
        let mut den = 0.0;
        for (i, s) in slice.iter().enumerate() {
            let xi = i as f64 - x_mean;
            num += xi * (s.phi_iit - y_mean);
            den += xi * xi;
        }
        if den.abs() < 1e-12 {
            0.0
        } else {
            num / den
        }
    }

    /// Detect collapse events (Φ drop > 30% in 10 steps)
    pub fn detect_collapses(&self) -> Vec<(usize, f64, f64)> {
        let mut collapses = Vec::new();
        for i in 10..self.history.len() {
            let prev = self.history[i - 10].phi_iit;
            let curr = self.history[i].phi_iit;
            if prev > 0.0 && (curr - prev) / prev < -0.3 {
                collapses.push((i, prev, curr));
            }
        }
        collapses
    }

    /// Map which laws correlate with Φ changes
    pub fn law_correlation(&self) -> Vec<(u32, f64)> {
        // For each law, compare avg Φ when active vs inactive
        let mut results = Vec::new();
        for law in &self.laws_registry {
            let active_phis: Vec<f64> = self
                .history
                .iter()
                .filter(|s| s.laws_active.contains(&law.id))
                .map(|s| s.phi_iit)
                .collect();
            let inactive_phis: Vec<f64> = self
                .history
                .iter()
                .filter(|s| !s.laws_active.contains(&law.id))
                .map(|s| s.phi_iit)
                .collect();

            if !active_phis.is_empty() && !inactive_phis.is_empty() {
                let avg_active = active_phis.iter().sum::<f64>() / active_phis.len() as f64;
                let avg_inactive =
                    inactive_phis.iter().sum::<f64>() / inactive_phis.len() as f64;
                let delta = if avg_inactive > 0.0 {
                    (avg_active - avg_inactive) / avg_inactive * 100.0
                } else {
                    0.0
                };
                results.push((law.id, delta));
            }
        }
        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        results
    }

    /// Export timeline as JSON
    pub fn to_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_default()
    }
}

impl Default for PhiTracker {
    fn default() -> Self {
        Self::new()
    }
}
