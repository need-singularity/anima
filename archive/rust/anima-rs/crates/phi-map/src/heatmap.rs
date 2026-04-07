//! ASCII heatmap renderer for Φ terrain

use crate::terrain::PhiTerrain;

pub struct AsciiHeatmap;

impl AsciiHeatmap {
    /// Render a modules×scales heatmap with Φ(IIT) values
    pub fn render(terrain: &PhiTerrain) -> String {
        let mut out = String::new();

        // Header
        out.push_str(&format!("  {:32}", "Modules"));
        for &cells in &terrain.scales {
            out.push_str(&format!("  {:>6}c", cells));
        }
        out.push('\n');
        out.push_str(&format!("  {:─<32}", ""));
        for _ in &terrain.scales {
            out.push_str("  ──────");
        }
        out.push('\n');

        // Rows: each module attachment level
        let max_modules = terrain.module_order.len();
        for i in 0..=max_modules {
            let label = if i == 0 {
                "baseline".to_string()
            } else {
                format!("+{} ({})", terrain.module_order[i - 1], i)
            };
            out.push_str(&format!("  {:<32}", label));

            for &cells in &terrain.scales {
                if let Some(pt) = terrain.phi_at(i, cells) {
                    if pt.stable {
                        let delta = pt.delta_pct;
                        let color = Self::delta_char(delta);
                        out.push_str(&format!("  {:>5.1}{}", pt.phi_iit, color));
                    } else {
                        out.push_str("    XX  ");
                    }
                } else {
                    out.push_str("     -  ");
                }
            }
            out.push('\n');
        }

        // Legend
        out.push('\n');
        out.push_str("  Legend: ▲ >+20%  △ >+5%  · ±5%  ▽ <-5%  ▼ <-20%  XX collapsed\n");

        out
    }

    /// Render delta-% heatmap
    pub fn render_delta(terrain: &PhiTerrain) -> String {
        let mut out = String::new();

        out.push_str(&format!("  {:32}", "Δ% vs baseline"));
        for &cells in &terrain.scales {
            out.push_str(&format!("  {:>6}c", cells));
        }
        out.push('\n');
        out.push_str(&format!("  {:─<32}", ""));
        for _ in &terrain.scales {
            out.push_str("  ──────");
        }
        out.push('\n');

        let max_modules = terrain.module_order.len();
        for i in 0..=max_modules {
            let label = if i == 0 {
                "baseline".to_string()
            } else {
                format!("+{} ({})", terrain.module_order[i - 1], i)
            };
            out.push_str(&format!("  {:<32}", label));

            for &cells in &terrain.scales {
                if let Some(pt) = terrain.phi_at(i, cells) {
                    if pt.stable {
                        let block = Self::delta_block(pt.delta_pct);
                        out.push_str(&format!("  {:>5.0}%{}", pt.delta_pct, block));
                    } else {
                        out.push_str("    XX  ");
                    }
                } else {
                    out.push_str("     -  ");
                }
            }
            out.push('\n');
        }

        out
    }

    /// Render terrain contour (Φ value as bar height per scale)
    pub fn render_contour(terrain: &PhiTerrain, cells: usize) -> String {
        let mut out = String::new();
        out.push_str(&format!("  Φ(IIT) contour @ {}c:\n", cells));

        let points: Vec<_> = terrain
            .points
            .iter()
            .filter(|p| p.cells == cells)
            .collect();

        let max_phi = points
            .iter()
            .filter(|p| p.stable)
            .map(|p| p.phi_iit)
            .fold(0.0f64, f64::max);

        for pt in &points {
            let label = if pt.n_modules == 0 {
                "baseline".to_string()
            } else if pt.n_modules <= terrain.module_order.len() {
                format!("+{} ({})", terrain.module_order[pt.n_modules - 1], pt.n_modules)
            } else {
                format!("({} mods)", pt.n_modules)
            };

            if pt.stable {
                let bar_len = ((pt.phi_iit / max_phi.max(1e-8)) * 40.0) as usize;
                let bar: String = "█".repeat(bar_len);
                let delta = Self::delta_char(pt.delta_pct);
                out.push_str(&format!(
                    "    {:<30} {} {:.1} ({:+.0}%){}\n",
                    label, bar, pt.phi_iit, pt.delta_pct, delta
                ));
            } else {
                out.push_str(&format!(
                    "    {:<30} XX COLLAPSED (CE={:.0})\n",
                    label, pt.ce
                ));
            }
        }

        out
    }

    fn delta_char(delta: f64) -> &'static str {
        if delta > 20.0 {
            "▲"
        } else if delta > 5.0 {
            "△"
        } else if delta > -5.0 {
            "·"
        } else if delta > -20.0 {
            "▽"
        } else {
            "▼"
        }
    }

    fn delta_block(delta: f64) -> &'static str {
        if delta > 30.0 {
            "▓"
        } else if delta > 10.0 {
            "▒"
        } else if delta > 0.0 {
            "░"
        } else {
            " "
        }
    }
}
