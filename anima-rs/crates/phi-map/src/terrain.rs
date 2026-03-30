//! Φ terrain data structure — stores module×scale measurement grid

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TerrainPoint {
    pub modules: Vec<String>,   // enabled modules at this point
    pub n_modules: usize,       // count of enabled modules
    pub cells: usize,           // cell scale
    pub phi_iit: f64,           // Φ(IIT) measurement
    pub phi_proxy: f64,         // Φ(proxy) measurement
    pub ce: f64,                // cross-entropy loss
    pub stable: bool,           // proxy < 100 (not exploded)
    pub delta_pct: f64,         // % change vs baseline at same scale
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhiTerrain {
    pub points: Vec<TerrainPoint>,
    pub scales: Vec<usize>,
    pub module_order: Vec<String>,
}

impl PhiTerrain {
    pub fn new(module_order: Vec<String>, scales: Vec<usize>) -> Self {
        Self {
            points: Vec::new(),
            scales,
            module_order,
        }
    }

    pub fn add_point(&mut self, point: TerrainPoint) {
        self.points.push(point);
    }

    /// Get baseline Φ for a given scale
    pub fn baseline_phi(&self, cells: usize) -> f64 {
        self.points
            .iter()
            .find(|p| p.cells == cells && p.n_modules == 0)
            .map(|p| p.phi_iit)
            .unwrap_or(0.0)
    }

    /// Get Φ for a specific (n_modules, cells) coordinate
    pub fn phi_at(&self, n_modules: usize, cells: usize) -> Option<&TerrainPoint> {
        self.points
            .iter()
            .find(|p| p.n_modules == n_modules && p.cells == cells)
    }

    /// Find the peak Φ point across entire terrain
    pub fn peak(&self) -> Option<&TerrainPoint> {
        self.points
            .iter()
            .filter(|p| p.stable)
            .max_by(|a, b| a.phi_iit.partial_cmp(&b.phi_iit).unwrap())
    }

    /// Find collapse points (unstable)
    pub fn collapse_points(&self) -> Vec<&TerrainPoint> {
        self.points.iter().filter(|p| !p.stable).collect()
    }

    /// Find the optimal module count for each scale
    pub fn optimal_per_scale(&self) -> Vec<(usize, &TerrainPoint)> {
        self.scales
            .iter()
            .filter_map(|&cells| {
                self.points
                    .iter()
                    .filter(|p| p.cells == cells && p.stable)
                    .max_by(|a, b| a.phi_iit.partial_cmp(&b.phi_iit).unwrap())
                    .map(|p| (cells, p))
            })
            .collect()
    }

    /// Detect the "death valley" — scale where adding modules hurts most
    pub fn death_valley(&self) -> Option<usize> {
        let mut worst_scale = None;
        let mut worst_delta = 0.0f64;

        for &cells in &self.scales {
            let base = self.baseline_phi(cells);
            if base <= 0.0 {
                continue;
            }
            // Find the worst stable point at this scale
            let min_phi = self
                .points
                .iter()
                .filter(|p| p.cells == cells && p.stable && p.n_modules > 0)
                .map(|p| p.phi_iit)
                .fold(f64::MAX, f64::min);

            if min_phi < f64::MAX {
                let delta = (min_phi - base) / base;
                if delta < worst_delta {
                    worst_delta = delta;
                    worst_scale = Some(cells);
                }
            }
        }
        worst_scale
    }

    /// Export to JSON
    pub fn to_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_default()
    }

    /// Import from JSON
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }
}
