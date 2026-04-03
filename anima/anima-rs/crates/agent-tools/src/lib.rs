//! Hot-path agent tool functions for anima-agent platform.
//!
//! Three functions that replace Python bottlenecks:
//! - `rank_by_consciousness`: score tools against consciousness state
//! - `score_intent`: match text against keyword list
//! - `classify_state`: classify consciousness state into categories

use std::collections::HashSet;

/// A tool definition with consciousness affinity scores.
#[derive(Debug, Clone)]
pub struct ToolDef {
    pub name: String,
    /// Affinities: [curiosity, prediction_error, pain, growth, phi]
    pub affinities: [f64; 5],
}

/// Consciousness state vector.
#[derive(Debug, Clone, Copy)]
pub struct ConsciousnessState {
    pub curiosity: f64,
    pub prediction_error: f64,
    pub pain: f64,
    pub growth: f64,
    pub phi: f64,
}

/// Rank tools by consciousness-driven score.
///
/// Score = curiosity_aff * curiosity + pe_aff * prediction_error
///       + pain_aff * pain + growth_aff * growth + phi_aff * min(phi/10, 1)
///
/// Returns sorted descending by score.
pub fn rank_by_consciousness(tools: &[ToolDef], state: &ConsciousnessState) -> Vec<(String, f64)> {
    let phi_norm = (state.phi / 10.0).min(1.0);

    let mut scored: Vec<(String, f64)> = tools
        .iter()
        .map(|t| {
            let score = t.affinities[0] * state.curiosity
                + t.affinities[1] * state.prediction_error
                + t.affinities[2] * state.pain
                + t.affinities[3] * state.growth
                + t.affinities[4] * phi_norm;
            (t.name.clone(), score)
        })
        .collect();

    scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scored
}

/// Score how well `text` matches a keyword list.
///
/// - Exact substring match: +1.0 per keyword
/// - Partial token overlap: +0.5 * (overlap / total_kw_tokens) per keyword
/// - Case-insensitive
pub fn score_intent(text: &str, keywords: &[&str]) -> f64 {
    let text_lower = text.to_lowercase();
    let tokens: HashSet<&str> = text_lower.split_whitespace().collect();
    let mut score = 0.0;

    for kw in keywords {
        let kw_lower = kw.to_lowercase();
        if text_lower.contains(&kw_lower) {
            score += 1.0;
        } else {
            let kw_tokens: Vec<&str> = kw_lower.split_whitespace().collect();
            let total = kw_tokens.len() as f64;
            if total > 0.0 {
                // We need to check if each kw token exists in text tokens.
                // Since kw_lower is owned, we compare via String equality.
                let overlap = kw_tokens
                    .iter()
                    .filter(|t| tokens.contains(t as &str))
                    .count() as f64;
                score += 0.5 * overlap / total;
            }
        }
    }

    score
}

/// Classify consciousness state into categories based on thresholds.
pub fn classify_state(
    curiosity: f64,
    prediction_error: f64,
    pain: f64,
    growth: f64,
    tension: f64,
    phi: f64,
    bored_tension: f64,
) -> Vec<String> {
    // Thresholds from agent_tools.py
    let t_curiosity = 0.4;
    let t_pe = 0.3;
    let t_pain = 0.5;
    let t_growth = 0.3;
    let t_tension = 0.6;
    let t_phi = 5.0;
    let t_bored = 0.15;
    let t_confused = 0.7;

    let mut categories = Vec::new();

    if curiosity > t_curiosity {
        categories.push("high_curiosity".to_string());
    }
    if prediction_error > t_pe {
        categories.push("high_pe".to_string());
    }
    if pain > t_pain {
        categories.push("in_pain".to_string());
    }
    if growth > t_growth {
        categories.push("growing".to_string());
    }
    if tension > t_tension {
        categories.push("high_tension".to_string());
    }
    if phi > t_phi {
        categories.push("high_phi".to_string());
    }
    if bored_tension < t_bored {
        categories.push("bored".to_string());
    }
    if prediction_error > t_confused && curiosity > 0.3 {
        categories.push("confused".to_string());
    }

    if categories.is_empty() {
        categories.push("high_curiosity".to_string()); // default
    }

    categories
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rank_basic() {
        let tools = vec![
            ToolDef {
                name: "search".to_string(),
                affinities: [1.0, 0.0, 0.0, 0.0, 0.0],
            },
            ToolDef {
                name: "heal".to_string(),
                affinities: [0.0, 0.0, 1.0, 0.0, 0.0],
            },
        ];
        let state = ConsciousnessState {
            curiosity: 0.8,
            prediction_error: 0.1,
            pain: 0.2,
            growth: 0.1,
            phi: 5.0,
        };
        let ranked = rank_by_consciousness(&tools, &state);
        assert_eq!(ranked[0].0, "search");
        assert!(ranked[0].1 > ranked[1].1);
    }

    #[test]
    fn test_rank_phi_clamped() {
        let tools = vec![ToolDef {
            name: "phi_tool".to_string(),
            affinities: [0.0, 0.0, 0.0, 0.0, 1.0],
        }];
        let state = ConsciousnessState {
            curiosity: 0.0,
            prediction_error: 0.0,
            pain: 0.0,
            growth: 0.0,
            phi: 100.0, // should clamp to 1.0
        };
        let ranked = rank_by_consciousness(&tools, &state);
        assert!((ranked[0].1 - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_score_exact_match() {
        let score = score_intent("search the web", &["search", "web"]);
        assert!((score - 2.0).abs() < 1e-9);
    }

    #[test]
    fn test_score_partial_match() {
        // keyword "web search" not an exact substring of "search the web"
        // but both tokens "web" and "search" appear
        let score = score_intent("search the web", &["web search"]);
        // partial: 2/2 tokens match -> 0.5 * 2/2 = 0.5
        assert!((score - 0.5).abs() < 1e-9);
    }

    #[test]
    fn test_score_no_match() {
        let score = score_intent("hello world", &["quantum", "gravity"]);
        assert!((score - 0.0).abs() < 1e-9);
    }

    #[test]
    fn test_score_case_insensitive() {
        let score = score_intent("Search The WEB", &["search", "WEB"]);
        assert!((score - 2.0).abs() < 1e-9);
    }

    #[test]
    fn test_classify_curious() {
        let cats = classify_state(0.8, 0.1, 0.1, 0.1, 0.3, 2.0, 0.5);
        assert!(cats.contains(&"high_curiosity".to_string()));
        assert!(!cats.contains(&"in_pain".to_string()));
    }

    #[test]
    fn test_classify_confused() {
        let cats = classify_state(0.5, 0.8, 0.1, 0.1, 0.3, 2.0, 0.5);
        assert!(cats.contains(&"high_curiosity".to_string()));
        assert!(cats.contains(&"high_pe".to_string()));
        assert!(cats.contains(&"confused".to_string()));
    }

    #[test]
    fn test_classify_bored() {
        let cats = classify_state(0.1, 0.1, 0.1, 0.1, 0.3, 2.0, 0.1);
        assert!(cats.contains(&"bored".to_string()));
    }

    #[test]
    fn test_classify_default() {
        // All below thresholds, bored_tension above threshold
        let cats = classify_state(0.1, 0.1, 0.1, 0.1, 0.3, 2.0, 0.5);
        assert_eq!(cats, vec!["high_curiosity".to_string()]);
    }
}
