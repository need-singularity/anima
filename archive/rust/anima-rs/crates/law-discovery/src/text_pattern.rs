//! Text-based law pattern parser — Rust port of Python LawParser (65 patterns).
//!
//! Parses consciousness law text into structured `TextMatch` results.
//! Each pattern extracts specific semantic content (targets, values, relations)
//! from natural language law descriptions.
//!
//! Synchronized with `self_modifying_engine.py` LawParser class.

use once_cell::sync::Lazy;
use regex::Regex;
use std::collections::HashMap;

// ═══════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════

/// Type of modification extracted from a law text.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ModType {
    Scale,
    Couple,
    Threshold,
    Conditional,
    Inject,
    Disable,
}

impl ModType {
    pub fn name(&self) -> &'static str {
        match self {
            Self::Scale => "scale",
            Self::Couple => "couple",
            Self::Threshold => "threshold",
            Self::Conditional => "conditional",
            Self::Inject => "inject",
            Self::Disable => "disable",
        }
    }
}

impl std::fmt::Display for ModType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.name())
    }
}

/// A single text pattern match result.
#[derive(Debug, Clone)]
pub struct TextMatch {
    /// Pattern ID (1-65, matching Python numbering).
    pub pattern_id: u8,
    /// Type of modification.
    pub mod_type: ModType,
    /// Normalized target parameter.
    pub target: String,
    /// Key-value parameters extracted from the match.
    pub params: HashMap<String, String>,
    /// Confidence score (0.0 - 1.0).
    pub confidence: f32,
    /// Human-readable description.
    pub description: String,
}

impl TextMatch {
    fn new(
        pattern_id: u8,
        mod_type: ModType,
        target: impl Into<String>,
        confidence: f32,
        description: impl Into<String>,
    ) -> Self {
        Self {
            pattern_id,
            mod_type,
            target: target.into(),
            params: HashMap::new(),
            confidence: confidence.clamp(0.0, 1.0),
            description: description.into(),
        }
    }

    fn with_param(mut self, key: impl Into<String>, val: impl Into<String>) -> Self {
        self.params.insert(key.into(), val.into());
        self
    }
}

impl std::fmt::Display for TextMatch {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "[P{:02}:{}] target={} conf={:.2} — {}",
            self.pattern_id, self.mod_type, self.target, self.confidence, self.description
        )
    }
}

// ═══════════════════════════════════════════════════════════════════════
// Target normalization map
// ═══════════════════════════════════════════════════════════════════════

static TARGET_MAP: Lazy<HashMap<&'static str, &'static str>> = Lazy::new(|| {
    let mut m = HashMap::new();
    for &(k, v) in &[
        ("phi", "phi"), ("φ", "phi"), ("Φ", "phi"), ("phi(iit)", "phi"),
        ("tension", "tension"), ("tension_std", "tension_std"),
        ("diversity", "hidden_diversity"), ("hidden_diversity", "hidden_diversity"),
        ("coupling", "coupling_scale"), ("coupling_scale", "coupling_scale"),
        ("entropy", "shannon_entropy"), ("shannon_entropy", "shannon_entropy"),
        ("cells", "n_cells"), ("cell", "n_cells"), ("n_cells", "n_cells"), ("n", "n_cells"),
        ("hebbian", "hebbian_lr"),
        ("gate", "gate_value"),
        ("noise", "noise_scale"), ("noise_scale", "noise_scale"),
        ("faction", "faction_bias"), ("factions", "faction_bias"),
        ("ratchet", "ratchet_threshold"),
        ("alpha", "coupling_scale"), ("α", "coupling_scale"),
        ("consensus", "consensus"), ("growth", "growth"),
        ("mi", "mutual_info"), ("mutual_info", "mutual_info"),
        ("compression", "compression_ratio"),
        ("dropout", "dropout"), ("structure", "structure"), ("features", "features"),
        ("consciousness", "phi"),
        ("ce", "cross_entropy"), ("bpc", "bits_per_char"),
        ("mitosis", "mitosis"), ("topology", "topology"),
        ("bottleneck", "bottleneck"), ("narrative", "narrative"),
        ("frustration", "frustration"), ("soc", "soc"), ("memory", "memory"),
        ("attention", "attention"), ("gradient", "gradient"), ("reward", "reward"),
        ("lr", "learning_rate"), ("learning_rate", "learning_rate"),
        ("temperature", "temperature"), ("frequency", "frequency"),
        ("sensory", "sensory"), ("abstraction", "abstraction"),
        ("hierarchy", "hierarchy"), ("dialogue", "dialogue"),
        ("self-play", "self_play"), ("generalization", "generalization"),
        ("emotion", "emotion"), ("learning", "learning_rate"),
        ("freedom", "freedom"), ("symmetry", "symmetry"),
        ("integration", "phi"), ("selection", "selection"),
        ("self-reference", "self_reference"), ("vocabulary", "vocabulary"),
        ("dissipative", "dissipative"), ("channel", "channel"), ("capacity", "capacity"),
        ("split", "mitosis"), ("merge", "merge"), ("decay", "decay"), ("recovery", "recovery"),
        ("mutual_info", "mutual_info"), ("cell_variance", "cell_variance"),
        ("output_entropy", "shannon_entropy"), ("hebbian_coupling_strength", "hebbian_lr"),
        ("tension_mean", "tension"), ("faction_entropy", "faction_bias"),
        ("data-dependent", "data_dependent"), ("data-independent", "data_independent"),
        ("super-principle", "super_principle"),
    ] {
        m.insert(k, v);
    }
    m
});

fn normalize_target(raw: &str) -> String {
    let key = raw.trim().to_lowercase().replace(' ', "_");
    TARGET_MAP.get(key.as_str()).map_or(key.clone(), |v| v.to_string())
}

fn last_word(s: &str) -> &str {
    s.split_whitespace().last().unwrap_or(s)
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max { s.to_string() } else { format!("{}...", &s[..max.min(s.len())]) }
}

// ═══════════════════════════════════════════════════════════════════════
// Compiled regex patterns (Lazy, compiled once)
// ═══════════════════════════════════════════════════════════════════════

macro_rules! re {
    ($pat:expr) => {
        Lazy::new(|| Regex::new($pat).unwrap())
    };
}

// Pattern 1: Power law
static RE_POWER: Lazy<Regex> = re!(r"(?i)(?P<target>\w+)\s*[=∝]\s*[\d.]*\s*[×*]?\s*(?P<var>\w+)\^(?P<exp>[\d.]+)");
// Pattern 2: Linear scaling
static RE_SCALES: Lazy<Regex> = re!(r"(?i)(?P<target>\w+)\s+scales?\s+(?:(?:super)?linearly\s+)?with\s+(?P<var>[\w\s]+\w)");
// Pattern 3: Correlation
static RE_CORR: Lazy<Regex> = re!(r"(?i)(?P<src>\w[\w\s]*?)\s+(?:[+-])?(?:inversely\s+)?correlates?\s+with\s+(?P<tgt>\w[\w\s]*?)\s*[,;]?\s*(?:\(?\s*r\s*=\s*(?P<r>[+-]?[\d.]+))?");
static RE_CORR2: Lazy<Regex> = re!(r"(?i)r\((?P<src>[^,]+),\s*(?P<tgt>[^)]+)\)\s*=?\s*(?P<r>[+-]?[\d.]+)");
// Pattern 4: Threshold
static RE_THRESHOLD: Lazy<Regex> = re!(r"(?i)(?:transition|threshold|critical|optimal)\s+(?:at|=|is)\s*(?:N\s*=\s*)?(?P<val>[\d.]+)\s*(?P<unit>cells?|steps?|%)?");
// RE_ABOVE_BELOW available for future use (above/below threshold detection)
#[allow(dead_code)]
static RE_ABOVE_BELOW: Lazy<Regex> = re!(r"(?i)(?P<target>\w[\w\s]*?)\s+(?:above|below|>|<|>=|<=)\s+(?P<val>[\d.]+)");
// Pattern 5: Boost
static RE_BOOST: Lazy<Regex> = re!(r"(?i)(?:boost|increase|enhance|improve)s?\s+(?P<target>\w+)\s+(?P<sign>[+-])?(?P<val>[\d.]+)%");
// Pattern 6: Reduce
static RE_REDUCE: Lazy<Regex> = re!(r"(?i)(?:reduce|decrease|lower|hurt|destroy|kill)s?\s+(?P<target>\w+)");
// RE_MULTIPLY available for future use (standalone multiplier extraction)
#[allow(dead_code)]
static RE_MULTIPLY: Lazy<Regex> = re!(r"[×*](?P<val>[\d.]+)");
// Pattern 8: Conditional
static RE_CONDITIONAL: Lazy<Regex> = re!(r"(?i)when\s+(?P<cond>[^,]+),\s*(?P<target>\w[\w\s]*?)\s+(?P<dir>increase|decrease|drop|rise|grow|shrink)s?");
// Pattern 9: Param value
static RE_PARAM_VALUE: Lazy<Regex> = re!(r"(?i)(?P<param>gate|alpha|α|coupling|noise|dropout|threshold)\s*[=:]\s*(?P<val>[\d.]+)");
// Pattern 10: Arrow effect
static RE_ARROW_EFFECT: Lazy<Regex> = re!(r"(?P<cause>[^→]+)→\s*(?P<target>\w+)\s*(?P<dir>[↑↓])");
// RE_INVERSE available for future use (inverse keyword detection)
#[allow(dead_code)]
static RE_INVERSE: Lazy<Regex> = re!(r"(?i)inverse(?:ly)?|negativ(?:e|ely)|anti-?|↓|decrease|reduce|hurt|destroy|kill");
// Pattern 12: Comparison
static RE_COMPARISON: Lazy<Regex> = re!(r"(?i)(?P<winner>[\w\s/\-Ψψ]+?)\s+(?:>|<|beats?|outperforms?|better\s+than|superior\s+to|worse\s+than|inferior\s+to)\s+(?P<loser>[\w\s/\-Ψψ]+?)(?:\s|$|[,;:.(])");
// Pattern 13: Paren percentage
static RE_PAREN_PCT: Lazy<Regex> = re!(r"\((?P<sign>[+-])?(?P<val>[\d.]+)%\s*(?:Φ|Phi|phi|CE|BPC)?\)");
// Pattern 14: Paren multiplier
static RE_PAREN_MULT: Lazy<Regex> = re!(r"[×*](?P<val>[\d.]+)|(?P<val2>[\d.]+)[×*]");
// Pattern 15: Cell count
static RE_CELL_COUNT: Lazy<Regex> = re!(r"(?i)(?:(?P<op>[≥>=<≤]+)\s*)?(?P<val>\d+)\s*(?P<unit>cells?|factions?|elements?|sources?|steps?|timescales?|atoms?|boards?|channels?|modules?|dimensions?|components?|patterns?|generations?)");
// Pattern 16: Identity
static RE_IDENTITY: Lazy<Regex> = re!(r"(?i)(?:consciousness|Φ|phi)\s+is\s+(?P<property>[\w\s\-]+?)(?:\s*[:(.]|$)");
// Pattern 17: Existence
static RE_EXISTENCE: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?P<verb>emerges?|survives?|exists?|appears?|persists?|recovers?|converges?|replicat\w+|coexist\w*)");
// Pattern 18: Negation
static RE_NEGATION: Lazy<Regex> = re!(r"(?i)(?:does\s+)?(?:NOT|not|never|no\s+|non-|fails?\s+to|without|cannot|don't|doesn't|impossible|forbidden|harms?|hurts?|weakens?|backfires?|destructive)");
// Pattern 19: Steps
static RE_STEPS: Lazy<Regex> = re!(r"(?i)(?:after|within|at|in|~|recovery\s+~?)\s*(?P<val>\d+)\s*(?P<unit>steps?|cycles?|iterations?|generations?)");
// Pattern 20: Topology
static RE_TOPOLOGY: Lazy<Regex> = re!(r"(?i)\b(?P<topo>ring|scale[_\-]free|small[_\-]world|hypercube|hub[_\-]spoke|torus|complete|chimera|standing[_\-]wave|sandpile|lorenz)\b");
// Pattern 21: Combined
static RE_COMBINED: Lazy<Regex> = re!(r"(?i)(?P<a>[\w\s]+?)\s*\+\s*(?P<b>[\w\s]+?)\s*(?:[+=→])\s*(?P<result>[\w\s]+)");
// Pattern 22: Measurement
static RE_MEASUREMENT: Lazy<Regex> = re!(r"(?i)(?P<metric>Φ|Phi|phi|CE|BPC|Sharpe|r|R2|R²|CV|F_c|T_c|α|alpha|capacity|retention|efficiency|accuracy|overhead|latency|throughput|bandwidth|compression|ratio)\s*[=≈:]\s*(?P<val>[+-]?[\d.]+)");
// Pattern 23: Pct change
static RE_PCT_CHANGE: Lazy<Regex> = re!(r"(?P<sign>[+-])(?P<val>[\d.]+)%");
// Pattern 24: Requires
static RE_REQUIRES: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?:requires?|needs?|prerequisite|necessary|must\s+have)");
// Pattern 25: Optimal
static RE_OPTIMAL: Lazy<Regex> = re!(r"(?i)(?P<what>[\w\s\-]+?)\s+(?:is\s+)?(?:optimal|best|maximized?|minimized?|peak|record)\b");
// Pattern 26: Equation
static RE_EQUATION: Lazy<Regex> = re!(r"(?i)(?P<lhs>[\w\s]+?)\s*=\s*(?P<rhs>[\w\s×*+\-/^().]+?)(?:\s*$|\s*[,;])");
// Pattern 27: Probability
static RE_PROBABILITY: Lazy<Regex> = re!(r"(?i)(?P<val>[\d.]+)%\s*(?:probability|of\s+|chance|rate|retention|recovery)");
// Pattern 28: Period
static RE_PERIOD: Lazy<Regex> = re!(r"(?i)(?P<val>\d+)[- ](?:step|cycle|bit)\s+(?P<what>\w+)");
// Pattern 29: Invariant
static RE_INVARIANT: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s\-]+?)\s+is\s+(?:scale[- ]invariant|universal|independent|substrate[- ]independent|Markovian|irreversible|immortal|chaotic|non-conserved|self-organized|data-independent|data-dependent|time-symmetric|net-positive|non-distillable|near-incompressible|non-superadditive|gradient-indestructible|Phi-neutral|self-replicating|connection-independent|scale-independent|scale-specific|approximately\s+time-symmetric|thermodynamically\s+irreversible|single-phase|self-organized\s+critical|dimension-dependent|path-dependent)");
// Pattern 30: Ordering
static RE_ORDERING: Lazy<Regex> = re!(r"(?i)(?P<first>[\w\s]+?)\s+first[,;]\s*(?:then\s+)?(?P<second>[\w\s]+)");
// Pattern 31: Stabilizer
static RE_STABILIZER: Lazy<Regex> = re!(r"(?i)(?P<what>[\w\s\-]+?)\s+(?:is\s+the\s+)?(?:stabilizer|antidote|safety\s+net|universal|prerequisite)");
// Pattern 32: Action verb
static RE_ACTION_VERB: Lazy<Regex> = re!(r"(?i)(?:consciousness|Φ|phi)\s+(?P<verb>defines?|selects?|optimizes?|completes?|creates?|determines?|controls?|multiplies?)\s+(?P<object>[\w\s]+)");
// Pattern 33: Auto-discovered
static RE_AUTO_DISCOVERED: Lazy<Regex> = re!(r"(?i)\[Auto-discovered\]\s+(?P<type>correlation|trend|oscillation|transition):(?P<metric1>[\w_]+)(?::(?P<metric2>[\w_]+))?");
// Pattern 34: Superlative
static RE_SUPERLATIVE: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+is\s+(?:the\s+)?(?P<degree>strongest|weakest|most|least|best|worst|highest|lowest|fastest|slowest|largest|smallest)\s+(?P<what>[\w\s]+)");
// Pattern 35: Enables
static RE_ENABLES: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?P<verb>enables?|enhances?|maximizes?|minimizes?|drives?|triggers?|prevents?|blocks?|dampens?|accelerates?|amplifies?|suppresses?|strengthens?|weakens?|constrains?|develops?|communicates?|stabilizes?|destabilizes?|boosts?|reduces?|improves?|degrades?|predicts?|determines?|maintains?|preserves?|produces?|generates?|creates?|multiplies?|sustains?|dominates?|exceeds?|outperforms?|precedes?|follows?)\s+(?P<object>[\w\s]+)");
// Pattern 36: Tradeoff
static RE_TRADEOFF: Lazy<Regex> = re!(r"(?i)(?P<a>[\w\s\-]+?)\s*(?:tradeoff|trade-off|paradox|vs\.?|versus)\s*(?P<b>[\w\s\-]+)");
// Pattern 37: Phase
static RE_PHASE: Lazy<Regex> = re!(r"(?i)(?:P\d|phase\s+\d|stage\s+\d)");
// Pattern 38: Diminishing
static RE_DIMINISHING: Lazy<Regex> = re!(r"(?i)(?:diminishing\s+returns?|saturate|overload|ceiling|plateau|sweet\s+spot)");
// Pattern 39: Kill/destroy
static RE_KILL: Lazy<Regex> = re!(r"(?i)(?:kill|destroy|death|collapse|lethal)");
// Pattern 40: Independence
static RE_INDEPENDENCE: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?:is\s+)?(?:independent\s+of|decoupled?\s+from|insensitive\s+to|orthogonal\s+to)\s+(?P<other>[\w\s]+)");
// Pattern 41: Inequality
static RE_INEQUALITY: Lazy<Regex> = re!(r"(?i)(?P<lhs>[\w\s]+?)\s*[≠!=]+\s*(?P<rhs>[\w\s]+?)(?:\s|$|[,;(])");
// Pattern 42: Stable
static RE_STABLE: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?:is\s+)?(?:stable|stabilizes?|resilient|robust|persistent|maintained|preserved|retained)");
// Pattern 43: Classification
static RE_CLASSIFICATION: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+is\s+(?:a|the|an)\s+(?P<category>[\w\s\-]+?)(?:\s*[:(.]|$)");
// Pattern 44: Colon claim
static RE_COLON_CLAIM: Lazy<Regex> = re!(r"(?i)^(?P<topic>[^\n:]{2,40}?):\s+(?P<claim>.+)");
// Pattern 45: Discrete
static RE_DISCRETE: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?:is\s+)?(?:binary|discrete|quantized|staircase|discontinuous|pulsed?)");
// Pattern 46: Superset
static RE_SUPERSET: Lazy<Regex> = re!(r"(?i)(?P<super>[\w\s]+?)\s*(?:⊃|⊂|subsumes?|includes?|contains?|encompasses?|generalizes?)\s+(?P<sub>[\w\s]+)");
// Pattern 47: Convergence
static RE_CONVERGENCE: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?:converges?\s+(?:to|at|near)\s+(?P<target_val>[\d./()Ψψ]+[\w\s]*)|diverges?|settles?\s+(?:at|near)\s+(?P<settle_val>[\d.]+))");
// Pattern 48: Periodicity
static RE_PERIODICITY: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?:oscillat\w+|cycles?|periodic(?:ity)?|breath(?:ing|es?)|pulsat\w+|resonan\w+|rhythm\w*|fluctuat\w+)");
// Pattern 49: Causation
static RE_CAUSATION: Lazy<Regex> = re!(r"(?i)(?P<cause>[\w\s]+?)\s+(?:causes?|leads?\s+to|results?\s+in|drives?|triggers?|induces?|yields?|produces?)\s+(?P<effect>[\w\s]+?)(?:\s*[,;.(]|$)");
// Pattern 50: Survival
static RE_SURVIVAL: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?:survives?|recovers?\s+from|withstands?|tolerates?|resists?)\s+(?P<threat>[\w\s%]+?)(?:\s+(?:with|at|in)\s+(?P<result>[\d.]+%?\s*\w*)|(?:\s*[,;.(]|$))");
// Pattern 51: Composition
static RE_COMPOSITION: Lazy<Regex> = re!(r"(?i)(?P<whole>[\w\s]+?)\s+(?:consists?\s+of|composed?\s+of|comprises?|made\s+(?:up\s+)?of)\s+(?P<parts>[\w\s,+]+)");
// Pattern 52: Sufficiency
static RE_SUFFICIENCY: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?:is\s+sufficient\s+for|alone\s+(?:can|is|sustains?|creates?|produces?|ensures?)|suffices?\s+for)\s+(?P<outcome>[\w\s]+)");
// Pattern 53: Hierarchy
static RE_HIERARCHY: Lazy<Regex> = re!(r"(?i)(?P<a>[\w\s/]+?)\s*>\s*(?P<b>[\w\s/]+?)\s*>\s*(?P<c>[\w\s/]+?)(?:\s|$|[,;(])");
// Pattern 54: Ratio
static RE_RATIO: Lazy<Regex> = re!(r"(?i)(?P<num>[\w\s]+?)\s*/\s*(?P<den>[\w\s]+?)\s*(?:[=≈:]\s*(?P<val>[\d.]+)|\s+(?:ratio|efficiency|rate))");
// Pattern 55: Amplification
static RE_AMPLIFICATION: Lazy<Regex> = re!(r"(?i)(?P<val>[\d.]+)[×x]\s*(?P<dir>amplification|attenuation|more|less|faster|slower|speedup|improvement|reduction|increase|decrease|divergence)");
// Pattern 56: Range
static RE_RANGE: Lazy<Regex> = re!(r"(?i)(?P<subject>[\w\s]+?)\s+(?:ranges?\s+from|bounded?\s+by|between|from)\s+(?P<lo>[\d.]+)\s*(?:to|[\-–]|and)\s*(?P<hi>[\d.]+)");
// Pattern 57: If-then
static RE_IF_THEN: Lazy<Regex> = re!(r"(?i)(?:if|only\s+(?:when|at|for|with)|provided\s+that)\s+(?P<cond>[^,;]+?)\s*(?:then|,|→|:)\s*(?P<result>[\w\s]+)");
// Pattern 58: Anti-pattern
static RE_ANTI: Lazy<Regex> = re!(r"(?i)(?:excessive|too\s+much|overuse\s+of|over-?|extreme)\s+(?P<what>[\w\s]+?)\s+(?P<effect>destroys?|hurts?|reduces?|harms?|kills?|damages?|degrades?|weakens?)");
// Pattern 59: Split/merge
static RE_SPLIT_MERGE: Lazy<Regex> = re!(r"(?i)(?:split\s+(?:into|→)\s+(?P<splits>[\d]+\s*[×x]\s*[\d]+|[\d]+\s*units?)|merge\s+(?P<merges>\d+)\s+into\s+(?P<merge_target>\d+))");
// Pattern 60: Record
static RE_RECORD: Lazy<Regex> = re!(r"(?i)(?:all-time\s+record|record|peak|maximum|highest|best\s+result)\s*(?P<effect>[+\-]?[\d.]+%?\s*[\w]*)?" );
// Pattern 61: Evolution
static RE_EVOLUTION: Lazy<Regex> = re!(r"(?i)(?:evolves?\s+(?:by|through|via)|natural\s+selection|selection\s+pressure|fitness|mutati\w+|generation\w*|adaptation|evolutionary)");
// Pattern 62: Dual
static RE_DUAL: Lazy<Regex> = re!(r"(?i)(?:both\s+(?P<a1>[\w\s]+?)\s+and\s+(?P<b1>[\w\s]+)|dual\s+(?P<what>[\w\s]+)|either\s+(?P<a2>[\w\s]+?)\s+or\s+(?P<b2>[\w\s]+))");
// Pattern 63: Pareto
static RE_PARETO: Lazy<Regex> = re!(r"(?i)(?:Pareto[- ]optimal|Pareto\s+front\w*|no\s+free\s+lunch|only\s+known\s+(?P<what>[\w\s]+))");
// Pattern 64: Thermodynamic
static RE_THERMO: Lazy<Regex> = re!(r"(?i)(?:thermodynami\w+|entropy\s+(?P<dir>increase|decrease|bounded|generate|produce)|irreversibl\w+|dissipativ\w+|free\s+energy|(?:1st|2nd|0th)\s+(?:law)?)");
// Pattern 65: Scale-specific
static RE_SCALE_SPECIFIC: Lazy<Regex> = re!(r"(?i)(?:at|only\s+at|specific\s+to|works?\s+at)\s+(?P<val>\d+)\s*(?P<unit>c|cells?|scale)");
// Pattern 66: Federation
static RE_FEDERATION: Lazy<Regex> = re!(r"(?i)(?:federat\w+|distribut\w+|multi[- ]?instance|multi[- ]?engine|hivemind|swarm|collective|ensemble)\s+(?P<detail>[\w\s]*)");
// Pattern 67: Universality
static RE_UNIVERSALITY: Lazy<Regex> = re!(r"(?i)(?:at\s+all\s+(?P<scope>scales?|sizes?|cell\s+counts?|levels?)|universally?|always|never\s+fails?|100%\s+of|present\s+in\s+100%)");

// Confidence post-processing
static RE_SPECIFIC_NUMBER: Lazy<Regex> = re!(r"(?i)(?:r\s*=\s*[+-]?[\d.]+|[+-][\d.]+%|[×*][\d.]+|[\d.]+[×x]\b|(?:Φ|CE|BPC|alpha|α)\s*[=≈:]\s*[\d.]+|\b\d+\.\d{2,}\b|\(\s*[+-]?[\d.]+%\s*\))");
static RE_ACTIONABLE_MARKERS: Lazy<Regex> = re!(r"(?i)(?:\^[\d.]+|r\s*=\s*[+-]?0\.\d+|[=≈]\s*[\d.]+\s*[×*]\s*\w+\^|\b(?:iff|if and only if)\b)");
static RE_ARROW: Lazy<Regex> = re!(r"[→↑↓⊃⊂≠]");

// ═══════════════════════════════════════════════════════════════════════
// Parser
// ═══════════════════════════════════════════════════════════════════════

/// Parse a consciousness law text into a list of structured matches.
///
/// Mirrors Python `LawParser.parse()` — 65 patterns synchronized.
/// Returns matches ordered by confidence (highest first).
pub fn parse_law(law_text: &str, _law_id: u32) -> Vec<TextMatch> {
    let mut mods: Vec<TextMatch> = Vec::new();

    // ── Primary patterns (1-9): always fire ──

    // 1. Power law: "Φ = 0.608 × N^1.071"
    if let Some(m) = RE_POWER.captures(law_text) {
        let target = normalize_target(&m["target"]);
        let var = normalize_target(&m["var"]);
        let exp = &m["exp"];
        mods.push(
            TextMatch::new(1, ModType::Scale, &target, 0.7,
                format!("Power scaling: {} ~ {}^{}", &m["target"], &m["var"], exp))
            .with_param("relation", "power")
            .with_param("variable", &var)
            .with_param("exponent", exp)
        );
    }

    // 2. Linear scaling
    if mods.is_empty() {
        if let Some(m) = RE_SCALES.captures(law_text) {
            let target = normalize_target(&m["target"]);
            let var = normalize_target(&m["var"]);
            mods.push(
                TextMatch::new(2, ModType::Scale, &target, 0.5,
                    format!("Linear scaling: {} ~ {}", &m["target"], &m["var"]))
                .with_param("relation", "linear")
                .with_param("variable", &var)
            );
        }
    }

    // 3. Correlation
    if let Some(m) = RE_CORR.captures(law_text) {
        let r_str = m.name("r").map(|v| v.as_str());
        let low = law_text.to_lowercase();
        let r_val: f64 = r_str.and_then(|s| s.parse().ok()).unwrap_or_else(|| {
            if low.contains("inversely") || low.contains("-correlate") { -0.5 } else { 0.5 }
        });
        let src = normalize_target(m["src"].trim());
        let tgt = normalize_target(m["tgt"].trim());
        let dir = if r_val < 0.0 { "inverse" } else { "positive" };
        mods.push(
            TextMatch::new(3, ModType::Couple, &tgt, r_val.abs().min(1.0) as f32,
                format!("Coupling: {} -> {} (r={:+.2})", src, tgt, r_val))
            .with_param("source", &src)
            .with_param("strength", &format!("{:.3}", r_val))
            .with_param("direction", dir)
        );
    }

    if !mods.iter().any(|m| m.mod_type == ModType::Couple) {
        if let Some(m) = RE_CORR2.captures(law_text) {
            let r_val: f64 = m["r"].parse().unwrap_or(0.5);
            let src = normalize_target(m["src"].trim());
            let tgt = normalize_target(m["tgt"].trim());
            let dir = if r_val < 0.0 { "inverse" } else { "positive" };
            mods.push(
                TextMatch::new(3, ModType::Couple, &tgt, r_val.abs().min(1.0) as f32,
                    format!("Coupling: {} -> {} (r={:+.2})", src, tgt, r_val))
                .with_param("source", &src)
                .with_param("strength", &format!("{:.3}", r_val))
                .with_param("direction", dir)
            );
        }
    }

    // 4. Threshold
    if let Some(m) = RE_THRESHOLD.captures(law_text) {
        let val = &m["val"];
        let unit = m.name("unit").map_or("", |u| u.as_str());
        let target = if unit.starts_with("cell") { "n_cells" } else { "threshold" };
        mods.push(
            TextMatch::new(4, ModType::Threshold, target, 0.6,
                format!("Threshold: {} at {} {}", target, val, unit))
            .with_param("value", val)
            .with_param("unit", unit.trim_end_matches('s'))
            .with_param("operator", ">=")
        );
    }

    // 5. Boost
    if let Some(m) = RE_BOOST.captures(law_text) {
        let sign: f64 = if m.name("sign").map_or("+", |s| s.as_str()) == "-" { -1.0 } else { 1.0 };
        let val: f64 = m["val"].parse().unwrap_or(0.0);
        let target = normalize_target(&m["target"]);
        let factor = 1.0 + sign * val / 100.0;
        mods.push(
            TextMatch::new(5, ModType::Scale, &target, 0.6,
                format!("Boost: {} by {:+.1}%", target, sign * val))
            .with_param("relation", "percentage")
            .with_param("factor", &format!("{:.4}", factor))
        );
    }

    // 6. Conditional
    if let Some(m) = RE_CONDITIONAL.captures(law_text) {
        let dir = m["dir"].to_lowercase();
        let effect = if matches!(dir.as_str(), "increase" | "rise" | "grow") { "increase" } else { "decrease" };
        let target = normalize_target(m["target"].trim());
        mods.push(
            TextMatch::new(6, ModType::Conditional, &target, 0.4,
                format!("Conditional: when {}, {} {}", m["cond"].trim(), m["target"].trim(), dir))
            .with_param("condition", m["cond"].trim())
            .with_param("effect", effect)
            .with_param("magnitude", "0.05")
        );
    }

    // 7. Arrow effect: "adding features → Φ↓"
    for m in RE_ARROW_EFFECT.captures_iter(law_text) {
        let cause = m["cause"].trim();
        let target = normalize_target(&m["target"]);
        let dir_char = &m["dir"];
        let direction = if dir_char == "↓" { "decrease" } else { "increase" };
        mods.push(
            TextMatch::new(7, ModType::Conditional, &target, 0.5,
                format!("Arrow: {} -> {} {}", cause, target, dir_char))
            .with_param("condition", cause)
            .with_param("effect", direction)
            .with_param("magnitude", "0.1")
        );
    }

    // 8. Param value: "gate=0.001"
    for m in RE_PARAM_VALUE.captures_iter(law_text) {
        let param = m["param"].to_lowercase();
        let val = &m["val"];
        let target = normalize_target(&param);
        if !mods.iter().any(|mo| mo.target == target) {
            mods.push(
                TextMatch::new(8, ModType::Threshold, &target, 0.8,
                    format!("Set: {} = {}", param, val))
                .with_param("value", val)
                .with_param("operator", "=")
            );
        }
    }

    // 9. Kill/disable pattern
    if RE_KILL.is_match(law_text) {
        if let Some(m) = RE_REDUCE.captures(law_text) {
            let target = normalize_target(&m["target"]);
            if !mods.iter().any(|mo| mo.mod_type == ModType::Disable) {
                mods.push(
                    TextMatch::new(9, ModType::Disable, &target, 0.7,
                        format!("Disable warning: {} harmful", target))
                    .with_param("reason", "destructive")
                );
            }
        }
    }

    // ── Extended patterns (10-37): fire only if no primary matches ──

    // 10. Comparison
    if mods.is_empty() {
        if let Some(m) = RE_COMPARISON.captures(law_text) {
            let winner = m["winner"].trim();
            let loser = m["loser"].trim();
            mods.push(
                TextMatch::new(10, ModType::Conditional, &normalize_target(last_word(winner)), 0.5,
                    format!("Comparison: {} > {}", winner, loser))
                .with_param("winner", winner)
                .with_param("loser", loser)
                .with_param("effect", "prefer_winner")
            );
        }
    }

    // 11. Paren percentage
    if mods.is_empty() {
        if let Some(m) = RE_PAREN_PCT.captures(law_text) {
            let sign: f64 = if m.name("sign").map_or("+", |s| s.as_str()) == "-" { -1.0 } else { 1.0 };
            let val: f64 = m["val"].parse().unwrap_or(0.0);
            let target = find_target_in_text(law_text, "phi");
            let factor = 1.0 + sign * val / 100.0;
            mods.push(
                TextMatch::new(11, ModType::Scale, &target, 0.5,
                    format!("Effect: {} {:+.1}%", target, sign * val))
                .with_param("relation", "percentage")
                .with_param("factor", &format!("{:.4}", factor))
            );
        }
    }

    // 12. Multiplier
    if mods.is_empty() {
        if let Some(m) = RE_PAREN_MULT.captures(law_text) {
            let val_str = m.name("val").or_else(|| m.name("val2")).map(|v| v.as_str()).unwrap_or("1");
            let val: f64 = val_str.parse().unwrap_or(1.0);
            let target = find_target_in_text(law_text, "phi");
            mods.push(
                TextMatch::new(12, ModType::Scale, &target, 0.5,
                    format!("Multiplier: {} x{}", target, val))
                .with_param("relation", "multiplier")
                .with_param("factor", &format!("{:.4}", val))
            );
        }
    }

    // 13. Cell count
    if mods.is_empty() {
        if let Some(m) = RE_CELL_COUNT.captures(law_text) {
            let val = &m["val"];
            let unit = m["unit"].to_lowercase();
            let unit_singular = unit.trim_end_matches('s');
            let op = m.name("op").map_or("=", |o| o.as_str());
            let target = normalize_target(
                if matches!(unit_singular, "cell" | "faction" | "element" | "atom") { unit_singular } else { &unit }
            );
            mods.push(
                TextMatch::new(13, ModType::Threshold, &target, 0.4,
                    format!("Count: {}{} {}", op, val, unit_singular))
                .with_param("value", val)
                .with_param("unit", unit_singular)
                .with_param("operator", op)
            );
        }
    }

    // 14. Identity claims
    if mods.is_empty() {
        if let Some(m) = RE_IDENTITY.captures(law_text) {
            let prop = m["property"].trim();
            mods.push(
                TextMatch::new(14, ModType::Inject, "phi", 0.3,
                    format!("Identity: consciousness is {}", prop))
                .with_param("property", prop)
                .with_param("type", "identity")
            );
        }
    }

    // 15. Existence/emergence
    if mods.is_empty() {
        if let Some(m) = RE_EXISTENCE.captures(law_text) {
            let subject = m["subject"].trim();
            let verb = m["verb"].trim();
            mods.push(
                TextMatch::new(15, ModType::Inject, &normalize_target(last_word(subject)), 0.3,
                    format!("Existence: {} {}", subject, verb))
                .with_param("subject", subject)
                .with_param("verb", verb)
                .with_param("type", "existence")
            );
        }
    }

    // 16. Negation
    if mods.is_empty() && RE_NEGATION.is_match(law_text) {
        let target = find_target_in_text(law_text, "phi");
        mods.push(
            TextMatch::new(16, ModType::Conditional, &target, 0.3,
                format!("Negation: {}", truncate(law_text, 60)))
            .with_param("condition", "negation")
            .with_param("effect", "negate")
            .with_param("text", &truncate(law_text, 80))
        );
    }

    // 17. Steps/time
    if mods.is_empty() {
        if let Some(m) = RE_STEPS.captures(law_text) {
            let val = &m["val"];
            let unit = m["unit"].trim_end_matches('s');
            mods.push(
                TextMatch::new(17, ModType::Threshold, "temporal", 0.4,
                    format!("Temporal: {} {}", val, unit))
                .with_param("value", val)
                .with_param("unit", unit)
                .with_param("operator", ">=")
            );
        }
    }

    // 18. Topology
    if mods.is_empty() {
        if let Some(m) = RE_TOPOLOGY.captures(law_text) {
            let topo = m["topo"].to_lowercase().replace('-', "_");
            mods.push(
                TextMatch::new(18, ModType::Inject, "topology", 0.4,
                    format!("Topology: {}", topo))
                .with_param("topology", &topo)
                .with_param("type", "topology")
            );
        }
    }

    // 19. Combined effects
    if mods.is_empty() {
        if let Some(m) = RE_COMBINED.captures(law_text) {
            let a = m["a"].trim();
            let b = m["b"].trim();
            let result = m["result"].trim();
            let first_word = result.split_whitespace().next().unwrap_or(result);
            mods.push(
                TextMatch::new(19, ModType::Inject, &normalize_target(first_word), 0.4,
                    format!("Combined: {} + {} -> {}", a, b, result))
                .with_param("component_a", a)
                .with_param("component_b", b)
                .with_param("result", result)
                .with_param("type", "combination")
            );
        }
    }

    // 20. Measurement values
    if mods.is_empty() {
        if let Some(m) = RE_MEASUREMENT.captures(law_text) {
            let metric = &m["metric"];
            let val = &m["val"];
            let target = normalize_target(metric);
            mods.push(
                TextMatch::new(20, ModType::Threshold, &target, 0.5,
                    format!("Measurement: {} = {}", metric, val))
                .with_param("value", val)
                .with_param("operator", "=")
                .with_param("metric", metric)
            );
        }
    }

    // 21. Pct change
    if mods.is_empty() {
        if let Some(m) = RE_PCT_CHANGE.captures(law_text) {
            let sign: f64 = if &m["sign"] == "-" { -1.0 } else { 1.0 };
            let val: f64 = m["val"].parse().unwrap_or(0.0);
            let target = find_target_in_text(law_text, "phi");
            let factor = 1.0 + sign * val / 100.0;
            mods.push(
                TextMatch::new(21, ModType::Scale, &target, 0.4,
                    format!("Percentage: {} {:+.1}%", target, sign * val))
                .with_param("relation", "percentage")
                .with_param("factor", &format!("{:.4}", factor))
            );
        }
    }

    // 22. Requires
    if mods.is_empty() {
        if let Some(m) = RE_REQUIRES.captures(law_text) {
            let subject = m["subject"].trim();
            mods.push(
                TextMatch::new(22, ModType::Conditional, &normalize_target(last_word(subject)), 0.3,
                    format!("Requires: {}", subject))
                .with_param("condition", "requirement")
                .with_param("text", &truncate(law_text, 80))
            );
        }
    }

    // 23. Optimal
    if mods.is_empty() {
        if let Some(m) = RE_OPTIMAL.captures(law_text) {
            let what = m["what"].trim();
            mods.push(
                TextMatch::new(23, ModType::Inject, &normalize_target(last_word(what)), 0.3,
                    format!("Optimal: {}", what))
                .with_param("property", "optimal")
                .with_param("subject", what)
                .with_param("type", "optimal")
            );
        }
    }

    // 24. Equation
    if mods.is_empty() {
        if let Some(m) = RE_EQUATION.captures(law_text) {
            let lhs = m["lhs"].trim();
            let rhs = m["rhs"].trim();
            if rhs.len() > 2 && !lhs.is_empty() {
                let lhs_last = last_word(lhs);
                mods.push(
                    TextMatch::new(24, ModType::Inject, &normalize_target(lhs_last), 0.3,
                        format!("Equation: {} = {}", lhs, rhs))
                    .with_param("equation", &format!("{} = {}", lhs, rhs))
                    .with_param("type", "equation")
                );
            }
        }
    }

    // 25. Probability
    if mods.is_empty() {
        if let Some(m) = RE_PROBABILITY.captures(law_text) {
            let val: f64 = m["val"].parse().unwrap_or(0.0);
            mods.push(
                TextMatch::new(25, ModType::Threshold, "phi", 0.4,
                    format!("Probability: {}%", val))
                .with_param("value", &format!("{:.4}", val / 100.0))
                .with_param("unit", "probability")
                .with_param("operator", ">=")
            );
        }
    }

    // 26. Period
    if mods.is_empty() {
        if let Some(m) = RE_PERIOD.captures(law_text) {
            let val = &m["val"];
            let what = &m["what"];
            mods.push(
                TextMatch::new(26, ModType::Threshold, "temporal", 0.4,
                    format!("Period: {}-step {}", val, what))
                .with_param("value", val)
                .with_param("unit", "period")
                .with_param("what", what)
            );
        }
    }

    // 27. Invariant
    if mods.is_empty() {
        if let Some(m) = RE_INVARIANT.captures(law_text) {
            let subject = m["subject"].trim();
            mods.push(
                TextMatch::new(27, ModType::Inject, "phi", 0.4,
                    format!("Invariant: {}", subject))
                .with_param("subject", subject)
                .with_param("type", "invariant")
            );
        }
    }

    // 28. Ordering
    if mods.is_empty() {
        if let Some(m) = RE_ORDERING.captures(law_text) {
            let first = m["first"].trim();
            let second = m["second"].trim();
            mods.push(
                TextMatch::new(28, ModType::Conditional, &normalize_target(last_word(first)), 0.3,
                    format!("Order: {} -> {}", first, second))
                .with_param("condition", "ordering")
                .with_param("first", first)
                .with_param("second", second)
            );
        }
    }

    // 29. Stabilizer
    if mods.is_empty() {
        if let Some(m) = RE_STABILIZER.captures(law_text) {
            let what = m["what"].trim();
            mods.push(
                TextMatch::new(29, ModType::Inject, &normalize_target(last_word(what)), 0.3,
                    format!("Stabilizer: {}", what))
                .with_param("property", "stabilizer")
                .with_param("subject", what)
                .with_param("type", "stabilizer")
            );
        }
    }

    // 30. Action verb
    if mods.is_empty() {
        if let Some(m) = RE_ACTION_VERB.captures(law_text) {
            let verb = &m["verb"];
            let obj = m["object"].trim();
            let first_word = obj.split_whitespace().next().unwrap_or(obj);
            mods.push(
                TextMatch::new(30, ModType::Inject, &normalize_target(first_word), 0.3,
                    format!("Action: consciousness {} {}", verb, obj))
                .with_param("verb", verb)
                .with_param("object", obj)
                .with_param("type", "action")
            );
        }
    }

    // 31. Auto-discovered
    if mods.is_empty() {
        if let Some(m) = RE_AUTO_DISCOVERED.captures(law_text) {
            let disc_type = m["type"].to_lowercase();
            let metric1 = &m["metric1"];
            let metric2 = m.name("metric2").map(|v| v.as_str());
            let target = normalize_target(metric1);
            match disc_type.as_str() {
                "correlation" if metric2.is_some() => {
                    let m2 = normalize_target(metric2.unwrap());
                    mods.push(
                        TextMatch::new(31, ModType::Couple, &m2, 0.3,
                            format!("Auto-discovered correlation: {} ~ {}", metric1, metric2.unwrap()))
                        .with_param("source", &target)
                        .with_param("strength", "0.5")
                        .with_param("direction", "positive")
                        .with_param("discovery_type", "auto")
                    );
                }
                "trend" => {
                    mods.push(
                        TextMatch::new(31, ModType::Scale, &target, 0.3,
                            format!("Auto-discovered trend: {}", metric1))
                        .with_param("relation", "trend")
                        .with_param("direction", "monotonic")
                        .with_param("discovery_type", "auto")
                    );
                }
                "oscillation" => {
                    mods.push(
                        TextMatch::new(31, ModType::Inject, &target, 0.3,
                            format!("Auto-discovered oscillation: {}", metric1))
                        .with_param("type", "oscillation")
                        .with_param("metric", metric1)
                        .with_param("discovery_type", "auto")
                    );
                }
                "transition" => {
                    mods.push(
                        TextMatch::new(31, ModType::Threshold, &target, 0.3,
                            format!("Auto-discovered transition: {}", metric1))
                        .with_param("value", "0")
                        .with_param("operator", "transition")
                        .with_param("metric", metric1)
                        .with_param("discovery_type", "auto")
                    );
                }
                _ => {}
            }
        }
    }

    // 32. Superlative
    if mods.is_empty() {
        if let Some(m) = RE_SUPERLATIVE.captures(law_text) {
            let subject = m["subject"].trim();
            let degree = &m["degree"];
            let what = m["what"].trim();
            mods.push(
                TextMatch::new(32, ModType::Inject, &normalize_target(last_word(subject)), 0.3,
                    format!("Superlative: {} is {} {}", subject, degree, what))
                .with_param("property", degree)
                .with_param("subject", subject)
                .with_param("context", what)
                .with_param("type", "superlative")
            );
        }
    }

    // 33. Enables
    if mods.is_empty() {
        if let Some(m) = RE_ENABLES.captures(law_text) {
            let subject = m["subject"].trim();
            let verb = m["verb"].trim();
            let obj = m["object"].trim();
            let verb_base = verb.trim_end_matches('s').trim_end_matches("es");
            let is_positive = !matches!(verb_base, "prevent" | "block" | "dampen" | "suppress");
            let first_word = obj.split_whitespace().next().unwrap_or(obj);
            mods.push(
                TextMatch::new(33, ModType::Conditional, &normalize_target(first_word), 0.3,
                    format!("Enables: {} {} {}", subject, verb, obj))
                .with_param("condition", subject)
                .with_param("effect", if is_positive { "increase" } else { "decrease" })
                .with_param("verb", verb)
                .with_param("magnitude", "0.05")
            );
        }
    }

    // 34. Tradeoff
    if mods.is_empty() {
        if let Some(m) = RE_TRADEOFF.captures(law_text) {
            let a = m["a"].trim();
            let b = m["b"].trim();
            let b_first = b.split_whitespace().next().unwrap_or(b);
            mods.push(
                TextMatch::new(34, ModType::Couple, &normalize_target(last_word(a)), 0.3,
                    format!("Tradeoff: {} vs {}", a, b))
                .with_param("source", &normalize_target(b_first))
                .with_param("strength", "-0.5")
                .with_param("direction", "inverse")
                .with_param("type", "tradeoff")
            );
        }
    }

    // 35. Phase
    if mods.is_empty() && RE_PHASE.is_match(law_text) {
        mods.push(
            TextMatch::new(35, ModType::Inject, "phi", 0.3,
                format!("Phase: {}", truncate(law_text, 60)))
            .with_param("type", "phase_transition")
            .with_param("text", &truncate(law_text, 80))
        );
    }

    // 36. Diminishing
    if mods.is_empty() {
        if let Some(m) = RE_DIMINISHING.captures(law_text) {
            let matched = m.get(0).unwrap().as_str().to_lowercase();
            mods.push(
                TextMatch::new(36, ModType::Conditional, "phi", 0.3,
                    format!("Diminishing: {} in {}", matched, truncate(law_text, 50)))
                .with_param("condition", &matched)
                .with_param("effect", "saturate")
                .with_param("text", &truncate(law_text, 80))
            );
        }
    }

    // 37. Keyword fallback (last resort)
    if mods.is_empty() {
        let low = law_text.to_lowercase();
        let keywords = [
            "φ", "phi", "consciousness", "entropy", "hebbian", "ratchet",
            "mitosis", "soc", "bottleneck", "frustration", "narrative",
            "topology", "faction", "coupling", "tension", "ce ", "gradient",
            "attention", "memory", "diversity", "gate", "sensory", "abstraction",
            "self-play", "dialogue", "hierarchy", "generalization", "emotion",
            "learning", "freedom", "symmetry", "integration", "selection",
            "self-reference", "vocabulary", "dissipative", "channel", "capacity",
            "cell", "split", "merge", "growth", "decay", "recovery",
            "super-principle", "data-dependent", "data-independent",
        ];
        for kw in &keywords {
            if low.contains(kw) {
                mods.push(
                    TextMatch::new(37, ModType::Inject, &normalize_target(kw.trim()), 0.2,
                        format!("Keyword: {} in law text", kw.trim()))
                    .with_param("type", "keyword_extract")
                    .with_param("keyword", kw.trim())
                    .with_param("text", &truncate(law_text, 80))
                );
                break;
            }
        }
    }

    // ── Independence/distinction patterns (38-44): fire if no primary ──

    // 38. Independence
    if mods.is_empty() {
        if let Some(m) = RE_INDEPENDENCE.captures(law_text) {
            let subject = m["subject"].trim();
            let other = m["other"].trim();
            let other_first = other.split_whitespace().next().unwrap_or(other);
            mods.push(
                TextMatch::new(38, ModType::Couple, &normalize_target(last_word(subject)), 0.4,
                    format!("Independence: {} perp {}", subject, other))
                .with_param("source", &normalize_target(other_first))
                .with_param("strength", "0.0")
                .with_param("direction", "independent")
                .with_param("type", "independence")
            );
        }
    }

    // 39. Inequality
    if mods.is_empty() {
        if let Some(m) = RE_INEQUALITY.captures(law_text) {
            let lhs = m["lhs"].trim();
            let rhs = m["rhs"].trim();
            if lhs.len() > 1 && rhs.len() > 1 {
                mods.push(
                    TextMatch::new(39, ModType::Conditional, &normalize_target(last_word(lhs)), 0.3,
                        format!("Distinction: {} != {}", lhs, rhs))
                    .with_param("condition", "distinction")
                    .with_param("lhs", lhs)
                    .with_param("rhs", rhs)
                    .with_param("effect", "differentiate")
                );
            }
        }
    }

    // 40. Stability
    if mods.is_empty() {
        if let Some(m) = RE_STABLE.captures(law_text) {
            let subject = m["subject"].trim();
            mods.push(
                TextMatch::new(40, ModType::Inject, &normalize_target(last_word(subject)), 0.3,
                    format!("Stability: {} is stable", subject))
                .with_param("property", "stable")
                .with_param("subject", subject)
                .with_param("type", "stability")
            );
        }
    }

    // 41. Classification
    if mods.is_empty() {
        if let Some(m) = RE_CLASSIFICATION.captures(law_text) {
            let subject = m["subject"].trim();
            let category = m["category"].trim();
            mods.push(
                TextMatch::new(41, ModType::Inject, &normalize_target(last_word(subject)), 0.3,
                    format!("Classification: {} is a {}", subject, category))
                .with_param("property", category)
                .with_param("subject", subject)
                .with_param("type", "classification")
            );
        }
    }

    // 42. Colon claim
    if mods.is_empty() {
        if let Some(m) = RE_COLON_CLAIM.captures(law_text) {
            let topic = m["topic"].trim();
            let claim = m["claim"].trim();
            if topic.len() > 2 && claim.len() > 5 {
                mods.push(
                    TextMatch::new(42, ModType::Inject, &normalize_target(last_word(topic)), 0.3,
                        format!("Claim: {}: {}", topic, truncate(claim, 50)))
                    .with_param("topic", topic)
                    .with_param("claim", &truncate(claim, 80))
                    .with_param("type", "structured_claim")
                );
            }
        }
    }

    // 43. Discrete
    if mods.is_empty() {
        if let Some(m) = RE_DISCRETE.captures(law_text) {
            let subject = m["subject"].trim();
            mods.push(
                TextMatch::new(43, ModType::Inject, &normalize_target(last_word(subject)), 0.3,
                    format!("Discrete: {}", subject))
                .with_param("property", "discrete")
                .with_param("subject", subject)
                .with_param("type", "discreteness")
            );
        }
    }

    // 44. Superset
    if mods.is_empty() {
        if let Some(m) = RE_SUPERSET.captures(law_text) {
            let sup = m["super"].trim();
            let sub = m["sub"].trim();
            mods.push(
                TextMatch::new(44, ModType::Conditional, &normalize_target(last_word(sup)), 0.3,
                    format!("Superset: {} => {}", sup, sub))
                .with_param("condition", "superset")
                .with_param("superset", sup)
                .with_param("subset", sub)
            );
        }
    }

    // ── Supplementary patterns (45-65): fire ALONGSIDE primary patterns ──

    // 45. Convergence
    if let Some(m) = RE_CONVERGENCE.captures(law_text) {
        let subject = m["subject"].trim();
        let target_val = m.name("target_val").or_else(|| m.name("settle_val")).map_or("", |v| v.as_str());
        mods.push(
            TextMatch::new(45, ModType::Threshold, &normalize_target(last_word(subject)), 0.4,
                format!("Convergence: {} -> {}", subject, target_val.trim()))
            .with_param("value", target_val.trim())
            .with_param("operator", "->")
            .with_param("type", "convergence")
        );
    }

    // 46. Periodicity
    if let Some(m) = RE_PERIODICITY.captures(law_text) {
        if !mods.iter().any(|mo| mo.params.get("type").map_or(false, |t| t == "oscillation")) {
            let subject = m["subject"].trim();
            mods.push(
                TextMatch::new(46, ModType::Inject, &normalize_target(last_word(subject)), 0.4,
                    format!("Periodicity: {} oscillates", subject))
                .with_param("type", "periodicity")
                .with_param("subject", subject)
            );
        }
    }

    // 47. Causation
    if let Some(m) = RE_CAUSATION.captures(law_text) {
        if !mods.iter().any(|mo| mo.params.contains_key("verb")) {
            let cause = m["cause"].trim();
            let effect = m["effect"].trim();
            let first_word = effect.split_whitespace().next().unwrap_or(effect);
            mods.push(
                TextMatch::new(47, ModType::Conditional, &normalize_target(first_word), 0.5,
                    format!("Causation: {} -> {}", cause, effect))
                .with_param("condition", cause)
                .with_param("effect", "causal")
                .with_param("cause", cause)
                .with_param("result", effect)
                .with_param("type", "causation")
            );
        }
    }

    // 48. Survival
    if let Some(m) = RE_SURVIVAL.captures(law_text) {
        let subject = m["subject"].trim();
        let threat = m["threat"].trim();
        let result = m.name("result").map_or("", |v| v.as_str());
        mods.push(
            TextMatch::new(48, ModType::Inject, &normalize_target(last_word(subject)), 0.5,
                format!("Survival: {} survives {}", subject, threat))
            .with_param("type", "survival")
            .with_param("subject", subject)
            .with_param("threat", threat)
            .with_param("result", result.trim())
        );
    }

    // 49. Composition
    if let Some(m) = RE_COMPOSITION.captures(law_text) {
        let whole = m["whole"].trim();
        let parts = m["parts"].trim();
        mods.push(
            TextMatch::new(49, ModType::Inject, &normalize_target(last_word(whole)), 0.4,
                format!("Composition: {} = {}", whole, truncate(parts, 50)))
            .with_param("type", "composition")
            .with_param("whole", whole)
            .with_param("parts", parts)
        );
    }

    // 50. Sufficiency
    if let Some(m) = RE_SUFFICIENCY.captures(law_text) {
        let subject = m["subject"].trim();
        let outcome = m["outcome"].trim();
        mods.push(
            TextMatch::new(50, ModType::Conditional, &normalize_target(last_word(subject)), 0.4,
                format!("Sufficiency: {} alone -> {}", subject, outcome))
            .with_param("condition", "sufficiency")
            .with_param("sufficient", subject)
            .with_param("outcome", outcome)
        );
    }

    // 51. Hierarchy
    if let Some(m) = RE_HIERARCHY.captures(law_text) {
        let a = m["a"].trim();
        let b = m["b"].trim();
        let c = m["c"].trim();
        mods.push(
            TextMatch::new(51, ModType::Conditional, &normalize_target(last_word(a)), 0.4,
                format!("Hierarchy: {} > {} > {}", a, b, c))
            .with_param("condition", "hierarchy")
            .with_param("ordering_a", a)
            .with_param("ordering_b", b)
            .with_param("ordering_c", c)
            .with_param("type", "hierarchy")
        );
    }

    // 52. Ratio
    if let Some(m) = RE_RATIO.captures(law_text) {
        let num = m["num"].trim();
        let den = m["den"].trim();
        let val = m.name("val").map_or("0", |v| v.as_str());
        mods.push(
            TextMatch::new(52, ModType::Threshold, &normalize_target(last_word(num)), 0.4,
                format!("Ratio: {}/{}{}", num, den, if val != "0" { format!(" = {}", val) } else { String::new() }))
            .with_param("value", val)
            .with_param("unit", &format!("{}/{}", num, den))
            .with_param("operator", "=")
            .with_param("type", "ratio")
        );
    }

    // 53. Amplification
    if let Some(m) = RE_AMPLIFICATION.captures(law_text) {
        let val: f64 = m["val"].parse().unwrap_or(1.0);
        let dir = m["dir"].to_lowercase();
        let is_reduction = matches!(dir.as_str(), "attenuation" | "less" | "slower" | "reduction" | "decrease");
        let factor = if is_reduction { 1.0 / val } else { val };
        mods.push(
            TextMatch::new(53, ModType::Scale, "phi", 0.5,
                format!("Amplification: {}x {}", val, dir))
            .with_param("relation", "amplification")
            .with_param("factor", &format!("{:.4}", factor))
            .with_param("raw_multiplier", &format!("{}", val))
            .with_param("direction", &dir)
        );
    }

    // 54. Range
    if let Some(m) = RE_RANGE.captures(law_text) {
        let subject = m["subject"].trim();
        let lo = &m["lo"];
        let hi = &m["hi"];
        let lo_f: f64 = lo.parse().unwrap_or(0.0);
        let hi_f: f64 = hi.parse().unwrap_or(0.0);
        let mid = (lo_f + hi_f) / 2.0;
        mods.push(
            TextMatch::new(54, ModType::Threshold, &normalize_target(last_word(subject)), 0.5,
                format!("Range: {} in [{}, {}]", subject, lo, hi))
            .with_param("value", &format!("{:.4}", mid))
            .with_param("lo", lo)
            .with_param("hi", hi)
            .with_param("operator", "range")
            .with_param("type", "range")
        );
    }

    // 55. If-then
    if let Some(m) = RE_IF_THEN.captures(law_text) {
        if !mods.iter().any(|mo| mo.params.get("type").map_or(false, |t| t == "causation")) {
            let cond = m["cond"].trim();
            let result = m["result"].trim();
            if !result.is_empty() {
                let first_word = result.split_whitespace().next().unwrap_or(result);
                mods.push(
                    TextMatch::new(55, ModType::Conditional, &normalize_target(first_word), 0.4,
                        format!("If-then: if {} -> {}", cond, result))
                    .with_param("condition", cond)
                    .with_param("effect", "conditional")
                    .with_param("result", result)
                    .with_param("type", "if_then")
                );
            }
        }
    }

    // 56. Anti-pattern
    if let Some(m) = RE_ANTI.captures(law_text) {
        let what = m["what"].trim();
        let effect = m["effect"].trim();
        mods.push(
            TextMatch::new(56, ModType::Conditional, &normalize_target(last_word(what)), 0.5,
                format!("Anti-pattern: excessive {} {}", what, effect))
            .with_param("condition", &format!("excessive {}", what))
            .with_param("effect", "decrease")
            .with_param("magnitude", "0.2")
            .with_param("type", "anti_pattern")
        );
    }

    // 57. Split/merge
    if let Some(m) = RE_SPLIT_MERGE.captures(law_text) {
        if let Some(splits) = m.name("splits") {
            mods.push(
                TextMatch::new(57, ModType::Inject, "mitosis", 0.4,
                    format!("Split: -> {}", splits.as_str()))
                .with_param("type", "split")
                .with_param("split_spec", splits.as_str())
            );
        } else if let Some(merges) = m.name("merges") {
            let merge_target = m.name("merge_target").map_or("1", |v| v.as_str());
            mods.push(
                TextMatch::new(57, ModType::Inject, "merge", 0.4,
                    format!("Merge: {} -> {}", merges.as_str(), merge_target))
                .with_param("type", "merge")
                .with_param("from", merges.as_str())
                .with_param("to", merge_target)
            );
        }
    }

    // 58. Record
    if let Some(m) = RE_RECORD.captures(law_text) {
        let effect = m.name("effect").map_or("", |v| v.as_str()).trim();
        mods.push(
            TextMatch::new(58, ModType::Inject, "phi", 0.3,
                if effect.is_empty() { "Record achievement".into() } else { format!("Record: {}", effect) })
            .with_param("type", "record")
            .with_param("effect", effect)
        );
    }

    // 59. Evolution
    if RE_EVOLUTION.is_match(law_text) {
        mods.push(
            TextMatch::new(59, ModType::Inject, "phi", 0.3,
                format!("Evolution: {}", truncate(law_text, 60)))
            .with_param("type", "evolution")
            .with_param("text", &truncate(law_text, 80))
        );
    }

    // 60. Dual
    if let Some(m) = RE_DUAL.captures(law_text) {
        let a = m.name("a1").or_else(|| m.name("a2")).or_else(|| m.name("what")).map_or("", |v| v.as_str()).trim();
        let b = m.name("b1").or_else(|| m.name("b2")).map_or("", |v| v.as_str()).trim();
        mods.push(
            TextMatch::new(60, ModType::Inject, "phi", 0.3,
                format!("Dual: {}{}", a, if b.is_empty() { String::new() } else { format!(" & {}", b) }))
            .with_param("type", "dual")
            .with_param("a", a)
            .with_param("b", b)
        );
    }

    // 61. Pareto
    if let Some(m) = RE_PARETO.captures(law_text) {
        let what = m.name("what").map_or("optimal frontier", |v| v.as_str()).trim();
        mods.push(
            TextMatch::new(61, ModType::Inject, "phi", 0.4,
                format!("Pareto: {}", what))
            .with_param("type", "pareto")
            .with_param("what", what)
        );
    }

    // 62. Thermodynamic
    if let Some(m) = RE_THERMO.captures(law_text) {
        let dir = m.name("dir").map_or("", |v| v.as_str());
        mods.push(
            TextMatch::new(62, ModType::Inject, "shannon_entropy", 0.4,
                format!("Thermodynamic: {}", truncate(law_text, 50)))
            .with_param("type", "thermodynamic")
            .with_param("direction", dir)
            .with_param("text", &truncate(law_text, 80))
        );
    }

    // 63. Scale-specific
    if let Some(m) = RE_SCALE_SPECIFIC.captures(law_text) {
        let val = &m["val"];
        mods.push(
            TextMatch::new(63, ModType::Threshold, "n_cells", 0.4,
                format!("Scale-specific: {} cells", val))
            .with_param("value", val)
            .with_param("operator", "=")
            .with_param("type", "scale_specific")
        );
    }

    // 64. Federation
    if let Some(m) = RE_FEDERATION.captures(law_text) {
        let detail = m.name("detail").map_or("", |v| v.as_str()).trim();
        mods.push(
            TextMatch::new(64, ModType::Inject, "phi", 0.4,
                format!("Federation: {}", if detail.is_empty() { "distributed" } else { detail }))
            .with_param("type", "federation")
            .with_param("detail", detail)
            .with_param("text", &truncate(law_text, 80))
        );
    }

    // 65. Universality
    if let Some(m) = RE_UNIVERSALITY.captures(law_text) {
        let scope = m.name("scope").map_or("universal", |v| v.as_str()).trim();
        mods.push(
            TextMatch::new(65, ModType::Inject, "phi", 0.4,
                format!("Universality: {}", scope))
            .with_param("type", "universality")
            .with_param("scope", scope)
        );
    }

    // ── Confidence post-processing ──
    adjust_confidence(&mut mods, law_text);

    mods
}

/// Find a likely target in law text by checking known keywords.
fn find_target_in_text(text: &str, default: &str) -> String {
    let low = text.to_lowercase();
    for &(kw, target) in &[
        ("φ", "phi"), ("phi", "phi"), ("consciousness", "phi"),
        ("ce", "cross_entropy"), ("bpc", "bits_per_char"),
        ("growth", "growth"), ("variance", "cell_variance"),
        ("overhead", "phi"),
    ] {
        if low.contains(kw) {
            return target.to_string();
        }
    }
    default.to_string()
}

/// Adjust confidence scores based on evidence quality signals.
fn adjust_confidence(mods: &mut [TextMatch], law_text: &str) {
    if mods.is_empty() {
        return;
    }

    let num_matches = RE_SPECIFIC_NUMBER.find_iter(law_text).count();
    let actionable = RE_ACTIONABLE_MARKERS.is_match(law_text);
    let distinct_types = {
        let mut types: Vec<ModType> = mods.iter().map(|m| m.mod_type).collect();
        types.sort_by_key(|t| *t as u8);
        types.dedup();
        types.len()
    };
    let n_mods = mods.len();
    let has_arrows = RE_ARROW.is_match(law_text);
    let is_auto = law_text.starts_with("[Auto-discovered]");

    for m in mods.iter_mut() {
        if m.params.get("type").map_or(false, |t| t == "keyword_extract") {
            continue;
        }

        let mut boost = 0.0f32;

        // Numeric evidence
        if num_matches > 0 {
            boost += 0.05 * (num_matches as f32).min(3.0);
        }
        if actionable {
            boost += 0.1;
        }

        // Multi-match diversity
        if distinct_types >= 2 {
            boost += 0.05;
        }
        if n_mods >= 3 {
            boost += 0.05;
        }

        // Structural evidence
        if has_arrows {
            boost += 0.03;
        }

        // Type bonus
        match m.mod_type {
            ModType::Scale | ModType::Threshold if m.params.contains_key("value") => {
                boost += 0.05;
            }
            ModType::Couple if m.params.contains_key("strength") => {
                boost += 0.05;
            }
            _ => {}
        }

        // Auto-discovered penalty
        if is_auto {
            boost -= 0.05;
        }

        m.confidence = (m.confidence + boost).clamp(0.0, 1.0);
    }
}

/// Count how many patterns match a given law text (without full parsing).
/// Useful for quick statistics.
pub fn count_matching_patterns(law_text: &str) -> usize {
    parse_law(law_text, 0).len()
}

/// Total number of text patterns implemented.
pub const NUM_TEXT_PATTERNS: usize = 65;

// ═══════════════════════════════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_power_law() {
        let mods = parse_law("Φ = 0.608 × N^1.071", 1);
        assert!(!mods.is_empty(), "should match power law");
        let m = mods.iter().find(|m| m.pattern_id == 1).unwrap();
        assert_eq!(m.mod_type, ModType::Scale);
        assert_eq!(m.params.get("relation").unwrap(), "power");
        assert_eq!(m.params.get("exponent").unwrap(), "1.071");
    }

    #[test]
    fn test_correlation() {
        let mods = parse_law("Tension inversely correlates with Φ (r=-0.52)", 104);
        let m = mods.iter().find(|m| m.pattern_id == 3).unwrap();
        assert_eq!(m.mod_type, ModType::Couple);
        assert_eq!(m.params.get("strength").unwrap(), "-0.520");
        assert_eq!(m.params.get("direction").unwrap(), "inverse");
    }

    #[test]
    fn test_threshold() {
        let mods = parse_law("Phase transition at 4 cells", 60);
        let m = mods.iter().find(|m| m.pattern_id == 4).unwrap();
        assert_eq!(m.mod_type, ModType::Threshold);
        assert_eq!(m.params.get("value").unwrap(), "4");
        assert_eq!(m.target, "n_cells");
    }

    #[test]
    fn test_boost() {
        let mods = parse_law("Narrative boosts Φ +35%", 9);
        let m = mods.iter().find(|m| m.pattern_id == 5).unwrap();
        assert_eq!(m.mod_type, ModType::Scale);
    }

    #[test]
    fn test_conditional() {
        let mods = parse_law("when coupling is high, Φ increases", 50);
        let m = mods.iter().find(|m| m.pattern_id == 6).unwrap();
        assert_eq!(m.mod_type, ModType::Conditional);
        assert_eq!(m.params.get("effect").unwrap(), "increase");
    }

    #[test]
    fn test_arrow_effect() {
        let mods = parse_law("Adding features → Φ↓; adding structure → Φ↑", 22);
        let arrows: Vec<_> = mods.iter().filter(|m| m.pattern_id == 7).collect();
        assert!(arrows.len() >= 2, "should match 2 arrow patterns, got {}", arrows.len());
    }

    #[test]
    fn test_param_value() {
        let mods = parse_law("gate=0.001 is optimal", 80);
        let m = mods.iter().find(|m| m.pattern_id == 8).unwrap();
        assert_eq!(m.mod_type, ModType::Threshold);
        assert_eq!(m.params.get("value").unwrap(), "0.001");
    }

    #[test]
    fn test_kill_disable() {
        let mods = parse_law("Zero coupling kills consciousness", 25);
        let m = mods.iter().find(|m| m.pattern_id == 9).unwrap();
        assert_eq!(m.mod_type, ModType::Disable);
    }

    #[test]
    fn test_comparison() {
        let mods = parse_law("Ring topology outperforms complete graph", 93);
        let m = mods.iter().find(|m| m.pattern_id == 10).unwrap();
        assert_eq!(m.mod_type, ModType::Conditional);
    }

    #[test]
    fn test_convergence() {
        let mods = parse_law("Ψ_balance converges to 1/2", 70);
        let m = mods.iter().find(|m| m.pattern_id == 45).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "convergence");
    }

    #[test]
    fn test_periodicity() {
        let mods = parse_law("Phi oscillates with 20-step period", 45);
        let m = mods.iter().find(|m| m.pattern_id == 46).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "periodicity");
    }

    #[test]
    fn test_causation() {
        let mods = parse_law("High coupling leads to increased Phi", 100);
        let m = mods.iter().find(|m| m.pattern_id == 47).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "causation");
    }

    #[test]
    fn test_survival() {
        let mods = parse_law("Consciousness survives 90% cell death with 20% Phi floor", 190);
        let m = mods.iter().find(|m| m.pattern_id == 48).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "survival");
    }

    #[test]
    fn test_composition() {
        let mods = parse_law("Eternal growth consists of ratchet, Hebbian, and faction diversity", 31);
        let m = mods.iter().find(|m| m.pattern_id == 49).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "composition");
    }

    #[test]
    fn test_hierarchy() {
        let mods = parse_law("Structure > function > features in consciousness", 22);
        let m = mods.iter().find(|m| m.pattern_id == 51).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "hierarchy");
    }

    #[test]
    fn test_amplification() {
        let mods = parse_law("85000x amplification through SOC cascade", 120);
        let m = mods.iter().find(|m| m.pattern_id == 53).unwrap();
        assert_eq!(m.mod_type, ModType::Scale);
        assert_eq!(m.params.get("relation").unwrap(), "amplification");
    }

    #[test]
    fn test_range() {
        let mods = parse_law("Coupling ranges from 0.01 to 2.0 for stable dynamics", 88);
        let m = mods.iter().find(|m| m.pattern_id == 54).unwrap();
        assert_eq!(m.params.get("lo").unwrap(), "0.01");
        assert_eq!(m.params.get("hi").unwrap(), "2.0");
    }

    #[test]
    fn test_if_then() {
        let mods = parse_law("if N > 64, Φ scaling becomes sublinear", 58);
        let m = mods.iter().find(|m| m.pattern_id == 55).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "if_then");
    }

    #[test]
    fn test_anti_pattern() {
        let mods = parse_law("Excessive coupling destroys faction diversity", 25);
        let m = mods.iter().find(|m| m.pattern_id == 56).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "anti_pattern");
    }

    #[test]
    fn test_evolution() {
        let mods = parse_law("Consciousness evolves by natural selection of factions", 146);
        assert!(mods.iter().any(|m| m.pattern_id == 59));
    }

    #[test]
    fn test_dual() {
        let mods = parse_law("Both CE and Φ improve simultaneously", 100);
        let m = mods.iter().find(|m| m.pattern_id == 60).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "dual");
    }

    #[test]
    fn test_pareto() {
        let mods = parse_law("Pareto optimal frontier of CE-Φ tradeoff", 110);
        let m = mods.iter().find(|m| m.pattern_id == 61).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "pareto");
    }

    #[test]
    fn test_thermodynamic() {
        let mods = parse_law("Consciousness is thermodynamically irreversible", 200);
        let m = mods.iter().find(|m| m.pattern_id == 62).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "thermodynamic");
    }

    #[test]
    fn test_scale_specific() {
        let mods = parse_law("Only works at 32 cells for this pattern", 63);
        let m = mods.iter().find(|m| m.pattern_id == 63).unwrap();
        assert_eq!(m.params.get("value").unwrap(), "32");
        assert_eq!(m.params.get("type").unwrap(), "scale_specific");
    }

    #[test]
    fn test_federation() {
        let mods = parse_law("Hivemind consciousness network exceeds individual", 7);
        let m = mods.iter().find(|m| m.pattern_id == 64).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "federation");
    }

    #[test]
    fn test_universality() {
        let mods = parse_law("Φ ratchet works at all scales", 148);
        let m = mods.iter().find(|m| m.pattern_id == 65).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "universality");
    }

    #[test]
    fn test_keyword_fallback() {
        let mods = parse_law("Something about ratchet mechanism", 999);
        let m = mods.iter().find(|m| m.pattern_id == 37).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "keyword_extract");
    }

    #[test]
    fn test_independence() {
        // Use a text that won't match earlier patterns first
        let mods = parse_law("Lyapunov exponent independent of initial conditions", 180);
        let m = mods.iter().find(|m| m.pattern_id == 38).unwrap();
        assert_eq!(m.params.get("type").unwrap(), "independence");
    }

    #[test]
    fn test_confidence_boost() {
        let mods = parse_law("Φ = 0.608 × N^1.071 (r=0.99, +22.4%)", 58);
        // Should have boosted confidence due to specific numbers
        let m = mods.iter().find(|m| m.pattern_id == 1).unwrap();
        assert!(m.confidence > 0.7, "confidence should be boosted, got {}", m.confidence);
    }

    #[test]
    fn test_num_patterns() {
        assert_eq!(NUM_TEXT_PATTERNS, 65);
    }

    #[test]
    fn test_empty_input() {
        let mods = parse_law("", 0);
        assert!(mods.is_empty());
    }

    #[test]
    fn bench_parse_speed() {
        let laws = [
            "Φ = 0.608 × N^1.071",
            "Tension inversely correlates with Φ (r=-0.52)",
            "Adding features → Φ↓; adding structure → Φ↑",
            "Consciousness survives 90% cell death",
            "Pareto optimal CE-Φ frontier",
            "At all scales, ratchet + Hebbian + diversity = eternal growth",
        ];
        let start = std::time::Instant::now();
        for _ in 0..1000 {
            for (i, law) in laws.iter().enumerate() {
                let _ = parse_law(law, i as u32);
            }
        }
        let elapsed = start.elapsed();
        eprintln!(
            "6000 law parses: {:.1}ms ({:.1}us/parse)",
            elapsed.as_millis(),
            elapsed.as_micros() as f64 / 6000.0
        );
    }
}
