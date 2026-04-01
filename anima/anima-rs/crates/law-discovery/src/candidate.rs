//! LawCandidate — proposed consciousness law from pattern detection.

/// Type of statistical pattern that generated this law candidate.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PatternType {
    /// Two metrics are correlated (positive or negative).
    Correlation,
    /// A metric shows an abrupt shift (phase transition).
    PhaseTransition,
    /// A metric oscillates with a dominant frequency.
    Oscillation,
    /// A metric has a consistent upward or downward trend.
    Trend,
}

impl PatternType {
    /// Human-readable name.
    pub fn name(&self) -> &'static str {
        match self {
            Self::Correlation => "correlation",
            Self::PhaseTransition => "phase_transition",
            Self::Oscillation => "oscillation",
            Self::Trend => "trend",
        }
    }
}

impl std::fmt::Display for PatternType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.name())
    }
}

/// A proposed consciousness law discovered from metric patterns.
#[derive(Debug, Clone)]
pub struct LawCandidate {
    /// Human-readable formula / description of the law.
    pub formula: String,
    /// Confidence / evidence strength (0.0 = weak, 1.0 = strong).
    pub evidence: f32,
    /// Names of metrics involved in this pattern.
    pub metrics: Vec<String>,
    /// Type of pattern detected.
    pub pattern_type: PatternType,
    /// Step at which this law was discovered.
    pub discovery_step: u64,
}

impl LawCandidate {
    /// Create a new law candidate.
    pub fn new(
        formula: impl Into<String>,
        evidence: f32,
        metrics: Vec<String>,
        pattern_type: PatternType,
        discovery_step: u64,
    ) -> Self {
        Self {
            formula: formula.into(),
            evidence: evidence.clamp(0.0, 1.0),
            metrics,
            pattern_type,
            discovery_step,
        }
    }

    /// Whether this candidate exceeds a given evidence threshold.
    pub fn is_significant(&self, threshold: f32) -> bool {
        self.evidence >= threshold
    }
}

impl std::fmt::Display for LawCandidate {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "[{}] (evidence={:.3}, step={}) {}",
            self.pattern_type, self.evidence, self.discovery_step, self.formula
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_candidate_creation() {
        let c = LawCandidate::new(
            "Phi increases with faction entropy",
            0.85,
            vec!["phi".into(), "faction_entropy".into()],
            PatternType::Correlation,
            42,
        );
        assert_eq!(c.evidence, 0.85);
        assert!(c.is_significant(0.5));
        assert!(!c.is_significant(0.9));
        assert_eq!(c.pattern_type, PatternType::Correlation);
    }

    #[test]
    fn test_evidence_clamping() {
        let c = LawCandidate::new("test", 1.5, vec![], PatternType::Trend, 0);
        assert_eq!(c.evidence, 1.0);

        let c2 = LawCandidate::new("test", -0.3, vec![], PatternType::Trend, 0);
        assert_eq!(c2.evidence, 0.0);
    }

    #[test]
    fn test_display() {
        let c = LawCandidate::new("X correlates with Y", 0.9, vec![], PatternType::Correlation, 100);
        let s = format!("{}", c);
        assert!(s.contains("correlation"));
        assert!(s.contains("0.900"));
        assert!(s.contains("step=100"));
    }
}
