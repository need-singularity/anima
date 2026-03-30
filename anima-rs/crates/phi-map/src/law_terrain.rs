//! Law terrain — maps law interventions to Φ effects
//!
//! Analogous to PhiTerrain (module × scale), but for law × law interactions.
//! Takes JSON from law_landscape.py and renders synergy heatmaps.

use serde::{Deserialize, Serialize};

/// Single law intervention effect
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LawPoint {
    pub key: String,        // e.g., "T_EQ", "SYM"
    pub name: String,       // e.g., "텐션 균등화"
    pub law_ids: Vec<u32>,  // related law numbers (e.g., [105, 124])
    pub phi: f64,           // Φ(IIT) measured
    pub phi_std: f64,       // standard deviation
    pub delta_pct: f64,     // % change vs baseline
    pub law_type: LawType,  // causal, ecological, observational
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LawType {
    Causal,       // single intervention works (Δ > +2%)
    Ecological,   // harmful alone, beneficial in combination
    Observational,// correlation but no causal effect
    AntiCausal,   // intervention makes things worse
}

/// Pairwise law interaction
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LawInteraction {
    pub law_a: String,
    pub law_b: String,
    pub combined_delta: f64,  // actual Δ% of A+B
    pub expected_delta: f64,  // sum of individual Δ%
    pub synergy: f64,         // combined - expected (positive = synergistic)
}

/// Full law landscape
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LawTerrain {
    pub baseline_phi: f64,
    pub baseline_std: f64,
    pub laws: Vec<LawPoint>,
    pub interactions: Vec<LawInteraction>,
    pub integrated_phi: f64,      // all laws combined
    pub integrated_delta: f64,
    pub total_synergy: f64,       // integrated - sum(individual)
}

impl LawTerrain {
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }

    pub fn to_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_default()
    }

    /// Render single-law effect bar chart
    pub fn render_effects(&self) -> String {
        let mut out = String::new();
        out.push_str("  ══════════════════════════════════════════════════\n");
        out.push_str("  법칙 단독 효과 (Law Single Effects)\n");
        out.push_str("  ══════════════════════════════════════════════════\n");

        let mut sorted: Vec<_> = self.laws.iter().collect();
        sorted.sort_by(|a, b| b.delta_pct.partial_cmp(&a.delta_pct).unwrap());

        let max_abs = sorted
            .iter()
            .map(|l| l.delta_pct.abs())
            .fold(0.0f64, f64::max)
            .max(1.0);

        for law in &sorted {
            let bar_len = ((law.delta_pct.abs() / max_abs) * 25.0) as usize;
            let (bar, sign) = if law.delta_pct >= 0.0 {
                ("█".repeat(bar_len), "+")
            } else {
                ("▒".repeat(bar_len), "")
            };

            let type_str = match law.law_type {
                LawType::Causal => "★ CAUSAL",
                LawType::Ecological => "○ ECOLOG",
                LawType::Observational => "─ OBSERV",
                LawType::AntiCausal => "✗ ANTI  ",
            };

            out.push_str(&format!(
                "  {:<8} {:<12} │{:<25} {}{:.1}%  {}\n",
                law.key, law.name, bar, sign, law.delta_pct, type_str
            ));
        }

        out.push_str(&format!(
            "\n  Baseline: Φ={:.4} ±{:.4}\n",
            self.baseline_phi, self.baseline_std
        ));

        out
    }

    /// Render law×law synergy heatmap
    pub fn render_synergy_matrix(&self) -> String {
        let mut out = String::new();
        out.push_str("  ══════════════════════════════════════════════════\n");
        out.push_str("  법칙 상호작용 행렬 (Synergy Matrix)\n");
        out.push_str("  ══════════════════════════════════════════════════\n");

        let keys: Vec<&str> = self.laws.iter().map(|l| l.key.as_str()).collect();

        // Header
        out.push_str(&format!("  {:>8}", ""));
        for k in &keys {
            out.push_str(&format!(" {:>7}", k));
        }
        out.push('\n');

        // Rows
        for k1 in &keys {
            out.push_str(&format!("  {:>8}", k1));
            for k2 in &keys {
                if k1 == k2 {
                    out.push_str("      ──");
                } else {
                    let synergy = self
                        .interactions
                        .iter()
                        .find(|i| {
                            (i.law_a == *k1 && i.law_b == *k2)
                                || (i.law_a == *k2 && i.law_b == *k1)
                        })
                        .map(|i| i.synergy)
                        .unwrap_or(0.0);

                    let sym = Self::synergy_char(synergy);
                    out.push_str(&format!(" {:>+5.1}%{}", synergy, sym));
                }
            }
            out.push('\n');
        }

        out.push_str("\n  Legend: ⬆ >+5%  ↑ >+2%  · ±2%  ↓ <-2%  ⬇ <-5%\n");

        out
    }

    /// Render integrated analysis
    pub fn render_integrated(&self) -> String {
        let mut out = String::new();
        out.push_str("  ══════════════════════════════════════════════════\n");
        out.push_str("  통합 분석 (Integrated Analysis)\n");
        out.push_str("  ══════════════════════════════════════════════════\n");

        let sum_individual: f64 = self.laws.iter().map(|l| l.delta_pct).sum();

        out.push_str(&format!("  개별 합:   {:+.1}%\n", sum_individual));
        out.push_str(&format!(
            "  통합 적용: {:+.1}% (Φ={:.4})\n",
            self.integrated_delta, self.integrated_phi
        ));
        out.push_str(&format!("  시너지:    {:+.1}%\n", self.total_synergy));

        if self.total_synergy > 5.0 {
            out.push_str("\n  ★ 강한 시너지 — 법칙들이 서로를 강화\n");
        } else if self.total_synergy > 0.0 {
            out.push_str("\n  ○ 약한 시너지 — 가산적에 가까움\n");
        } else {
            out.push_str("\n  ✗ 간섭 — 법칙들이 서로를 약화\n");
        }

        // Top synergy pairs
        let mut sorted_int: Vec<_> = self.interactions.iter().collect();
        sorted_int.sort_by(|a, b| b.synergy.partial_cmp(&a.synergy).unwrap());

        out.push_str("\n  상위 시너지 조합:\n");
        for i in sorted_int.iter().take(5) {
            let sym = if i.synergy > 0.0 { "시너지" } else { "간섭" };
            out.push_str(&format!(
                "    {}+{}: Δ={:+.1}% (예상 {:+.1}%, {} {:+.1}%)\n",
                i.law_a, i.law_b, i.combined_delta, i.expected_delta, sym, i.synergy
            ));
        }

        out
    }

    /// Full render
    pub fn render_all(&self) -> String {
        let mut out = String::new();
        out.push_str(&self.render_effects());
        out.push('\n');
        out.push_str(&self.render_synergy_matrix());
        out.push('\n');
        out.push_str(&self.render_integrated());
        out
    }

    fn synergy_char(synergy: f64) -> &'static str {
        if synergy > 5.0 {
            "⬆"
        } else if synergy > 2.0 {
            "↑"
        } else if synergy > -2.0 {
            "·"
        } else if synergy > -5.0 {
            "↓"
        } else {
            "⬇"
        }
    }
}
