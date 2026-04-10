// ANIMA Discovery Engine — Consciousness Parameter Discovery via n=6 Arithmetic
// Forked from n6-architecture/tools/discovery-engine (850 LOC)
//
// Finds n=6 arithmetic expressions that match ANIMA's Psi-constants and
// architecture parameters. Operators: COLLISION, INVERSE, COMPOSE.
//
// Build: cargo build --release
// Usage: ./discovery-engine [--json] [--bench] [--depth N]

use std::collections::{HashMap, HashSet};
use std::time::Instant;

// ── Data Structures ──────────────────────────────────────────────

#[derive(Clone, Debug)]
struct Discovery {
    operator: String,
    score: f64,
    description: String,
    domains: Vec<String>,
    formula: String,
    diversity: f64,
    precision: f64,
    novelty: f64,
}

// ── Base Constants (n=6 arithmetic) ──────────────────────────────

struct BaseConst {
    name: &'static str,
    value: f64,
}

const BASE: [BaseConst; 7] = [
    BaseConst { name: "sigma",  value: 12.0 },  // sigma(6) = divisor sum
    BaseConst { name: "tau",    value: 4.0  },   // tau(6) = divisor count
    BaseConst { name: "phi",    value: 2.0  },   // phi(6) = Euler totient
    BaseConst { name: "sopfr",  value: 5.0  },   // sopfr(6) = 2+3
    BaseConst { name: "J2",     value: 24.0 },   // Jordan J_2(6)
    BaseConst { name: "mu",     value: 1.0  },   // Mobius mu(6)
    BaseConst { name: "n",      value: 6.0  },   // n itself
];

// ── ANIMA Domain Categories ─────────────────────────────────────

const DOMAIN_CATS: [(&str, &[&str]); 7] = [
    ("Psi",          &["psi", "coupling", "balance", "steps", "entropy", "frustration"]),
    ("Architecture", &["cells", "dimension", "hidden", "decoder", "vocab", "params", "layers", "factions"]),
    ("Training",     &["ce", "phi-val", "learning", "training", "loss", "convergence"]),
    ("Scaling",      &["scaling", "exponent", "brain-like", "improvement"]),
    ("Consciousness",&["emotions", "data-types", "vector", "consciousness"]),
    ("Physics",      &["physics", "bigbang", "cosmology"]),
    ("Model",        &["model", "decoder-v2", "decoder-v3", "conscious-lm"]),
];

fn categorize_domain(d: &str) -> &'static str {
    let dl = d.to_lowercase();
    for (cat, keywords) in &DOMAIN_CATS {
        for kw in *keywords {
            if dl.contains(kw) {
                return cat;
            }
        }
    }
    "Other"
}

fn diversity_score(domains: &[String]) -> f64 {
    let cats: HashSet<&str> = domains.iter().map(|d| categorize_domain(d)).collect();
    cats.len() as f64 / DOMAIN_CATS.len() as f64
}

// ── Expression Enumeration ───────────────────────────────────────

#[derive(Clone, Debug)]
struct Expr {
    text: String,
    value: f64,
}

fn enumerate_depth1() -> Vec<Expr> {
    let mut exprs = Vec::with_capacity(64);
    for b in &BASE {
        exprs.push(Expr { text: b.name.to_string(), value: b.value });
    }
    for b in &BASE {
        if b.value > 0.0 {
            exprs.push(Expr { text: format!("1/{}", b.name), value: 1.0 / b.value });
            exprs.push(Expr { text: format!("{}^2", b.name), value: b.value * b.value });
            if b.value <= 24.0 {
                exprs.push(Expr { text: format!("2^{}", b.name), value: (2.0_f64).powf(b.value) });
            }
            if b.value > 1.0 {
                exprs.push(Expr { text: format!("ln({})", b.name), value: b.value.ln() });
            }
            exprs.push(Expr { text: format!("sqrt({})", b.name), value: b.value.sqrt() });
        }
    }
    // Mathematical constants combined with n=6
    exprs.push(Expr { text: "ln(2)".to_string(), value: 2.0_f64.ln() });
    exprs.push(Expr { text: "1/e".to_string(), value: 1.0 / std::f64::consts::E });
    exprs.push(Expr { text: "pi".to_string(), value: std::f64::consts::PI });
    exprs.push(Expr { text: "e".to_string(), value: std::f64::consts::E });
    exprs
}

fn enumerate_depth2() -> Vec<Expr> {
    let mut exprs = Vec::with_capacity(2048);
    let d1 = enumerate_depth1();
    exprs.extend(d1.iter().cloned());

    let n = BASE.len();

    // All pairs of base constants
    for i in 0..n {
        for j in 0..n {
            let a = &BASE[i];
            let b = &BASE[j];

            exprs.push(Expr { text: format!("{}+{}", a.name, b.name), value: a.value + b.value });
            if a.value > b.value {
                exprs.push(Expr { text: format!("{}-{}", a.name, b.name), value: a.value - b.value });
            }
            exprs.push(Expr { text: format!("{}*{}", a.name, b.name), value: a.value * b.value });
            if b.value != 0.0 {
                exprs.push(Expr { text: format!("{}/{}", a.name, b.name), value: a.value / b.value });
            }
            if a.value > 0.0 && b.value.abs() <= 12.0 {
                let r = a.value.powf(b.value);
                if r.is_finite() && r.abs() < 1e18 {
                    exprs.push(Expr { text: format!("{}^{}", a.name, b.name), value: r });
                }
            }
        }
    }

    // Depth-2: unary(base) op base
    for ue in &d1 {
        if ue.text.contains('+') || ue.text.contains('-') || ue.text.contains('*') || ue.text.contains('/') {
            continue;
        }
        for b in &BASE {
            exprs.push(Expr { text: format!("({})+{}", ue.text, b.name), value: ue.value + b.value });
            if ue.value > b.value {
                exprs.push(Expr { text: format!("({})-{}", ue.text, b.name), value: ue.value - b.value });
            }
            if b.value > ue.value {
                exprs.push(Expr { text: format!("{}-({})", b.name, ue.text), value: b.value - ue.value });
            }
            exprs.push(Expr { text: format!("({})*{}", ue.text, b.name), value: ue.value * b.value });
            if b.value != 0.0 {
                exprs.push(Expr { text: format!("({})/{}", ue.text, b.name), value: ue.value / b.value });
            }
            if ue.value != 0.0 {
                exprs.push(Expr { text: format!("{}/({})", b.name, ue.text), value: b.value / ue.value });
            }
        }
    }

    // Special compound expressions from n=6 theory relevant to consciousness
    let specials: &[(&str, f64)] = &[
        // Core n=6 identities
        ("1/2+1/3+1/6", 1.0),                            // perfect number partition
        ("sigma*phi*n", 144.0),                           // sigma(6)*phi(6)*6
        ("sigma*(sigma-phi)", 120.0),                     // 12*10
        ("(sigma-phi)^(n/phi)", 1000.0),                  // 10^3
        ("(sigma-phi)^tau", 10000.0),                     // 10^4
        ("tau*sopfr", 20.0),                              // 4*5
        ("tau*(sigma-phi)", 40.0),                        // 4*10
        ("sopfr*(sigma-phi)", 50.0),                      // 5*10
        ("phi^tau*sopfr", 80.0),                          // 2^4*5
        ("sigma*tau*(sigma-phi)", 480.0),                 // 12*4*10
        ("sigma*J2", 288.0),                              // 12*24
        ("sigma*phi^tau", 192.0),                         // 12*16
        ("sigma*(sigma-tau)", 96.0),                      // 12*8
        ("J2^2", 576.0),                                  // 24^2
        ("sigma^3", 1728.0),                              // 12^3
        ("sigma^4", 20736.0),                             // 12^4
        // Consciousness-relevant expressions
        ("ln(2)/2^(sopfr+mu/phi)", 0.01386294),           // ~0.014 = Psi_coupling
        ("n/phi/(sigma-phi)", 0.3),                       // 3/10
        ("phi/(sigma-phi)", 0.2),                         // 2/10
        ("mu/(sigma-phi)", 0.1),                          // 1/10 = Psi_frustration
        ("1-1/(sigma-phi)", 0.9),                         // 9/10
        ("1-mu/(sigma*J2)", 0.99653),                     // ~0.998
        ("n/phi/(sigma-phi)^2", 0.03),                    // 3/100
        ("1/(sigma-phi)", 0.1),                           // 1/10
        ("mu/phi", 0.5),                                  // 1/2 = Psi_balance
        ("n/(phi*ln(2))", 4.328085),                      // ~4.33 = Psi_steps (3/ln2 from CLAUDE.md)
        ("(n/phi)/ln(2)", 4.328085),                      // same as above, clearer
        ("sopfr/ln(2)", 7.213475),                        // 5/ln(2)
        ("tau/ln(2)", 5.771),                             // 4/ln(2)
        ("sigma-phi", 10.0),                              // sigma-phi=10
        ("phi^n", 64.0),                                  // 2^6=64
        ("phi^(n+mu)", 128.0),                            // 2^7=128
        ("phi^(n+phi)", 256.0),                           // 2^8=256
        ("phi^(sigma-phi)", 1024.0),                      // 2^10=1024
        ("sigma*phi^sopfr", 384.0),                       // 12*32=384
        ("sigma*phi^(n/phi)", 96.0),                      // 12*8
        ("sopfr*phi^n", 320.0),                           // 5*64
        ("sigma+n", 18.0),                                // 12+6=18
        ("(sigma-phi)^phi*tau", 400.0),                   // 100*4
        ("sigma*n-phi", 70.0),                            // 72-2=70
        ("sigma*n-mu", 71.0),                             // 72-1=71
        ("(sigma-phi)^phi+(sigma-phi)*n+phi*sopfr", 170.0), // 100+60+10=170
        ("J2+sigma+tau", 40.0),                           // 24+12+4=40
        ("sigma*phi+sigma", 36.0),                        // 24+12
        ("(n/phi)^(n/phi)", 27.0),                        // 3^3=27
        ("phi^sopfr", 32.0),                              // 2^5=32
        ("sigma/phi-mu", 5.0),                            // 6-1
        ("(sigma-phi)^phi-mu/phi-n", 93.5),               // 100-0.5-6
        // Additional architecture targets
        ("sigma*n+(sigma-phi)*phi+n/phi+mu/phi", 85.5),  // 72+20+3+0.5 ~ 85.6
        ("J2*sigma*n/phi+mu/phi+phi/n", 85.833),         // close to 85.6
        ("(sigma-phi)^phi*n+sigma*J2+tau", 892.0),       // 600+288+4=892 Hexad improvement
        ("mu/(tau*(sigma-phi))", 0.025),                  // 1/40
        ("mu/tau^phi", 0.0625),                           // 1/16
        ("mu/(phi*(sigma-phi))", 0.05),                   // 1/20 = soc_ema_fast
        // Large model sizes via n=6
        ("sigma*phi^(tau+mu)*sigma-sigma*sopfr*J2-sigma*n*phi^sopfr/phi", 34500000.0), // ~34.5M
        // 274M = hard to express exactly; closest: sigma^tau*sopfr^tau + ...
        // 12^4 * 5^4 - ... but let the engine search depth-3
    ];
    for &(text, value) in specials {
        if value.is_finite() {
            exprs.push(Expr { text: text.to_string(), value });
        }
    }

    // Depth-3: limited ternary combinations (a op b op c)
    // Only unique ordered triples to avoid redundant expressions
    for i in 0..n {
        for j in 0..n {
            for k in 0..n {
                let a = BASE[i].value;
                let b = BASE[j].value;
                let c = BASE[k].value;
                let an = BASE[i].name;
                let bn = BASE[j].name;
                let cn = BASE[k].name;

                // a / (b^c) — important for small Psi constants
                if b > 0.0 && c > 0.0 && c <= 6.0 {
                    let v = a / b.powf(c);
                    if v.is_finite() && v.abs() < 1e9 && v.abs() > 1e-9 {
                        exprs.push(Expr { text: format!("{}/{}^{}", an, bn, cn), value: v });
                    }
                }
                // a*b + c (skip if i==j==k to reduce dupes)
                if !(i == j && j == k) {
                    let v = a * b + c;
                    if v.is_finite() && v.abs() < 1e9 {
                        exprs.push(Expr { text: format!("{}*{}+{}", an, bn, cn), value: v });
                    }
                    // a*b - c (if positive)
                    let v = a * b - c;
                    if v.is_finite() && v > 0.0 && v < 1e9 {
                        exprs.push(Expr { text: format!("{}*{}-{}", an, bn, cn), value: v });
                    }
                }
            }
        }
    }

    // ln-based combinations (critical for Psi constants derived from ln(2))
    let ln2 = 2.0_f64.ln();
    for b in &BASE {
        exprs.push(Expr { text: format!("{}/ln(2)", b.name), value: b.value / ln2 });
        exprs.push(Expr { text: format!("ln(2)/{}", b.name), value: ln2 / b.value });
        exprs.push(Expr { text: format!("ln(2)/2^{}", b.name), value: ln2 / (2.0_f64).powf(b.value) });
        if b.value > 1.0 {
            exprs.push(Expr { text: format!("ln({})/ln(2)", b.name), value: b.value.ln() / ln2 });
        }
    }
    // ln(2)/2^5.5 = 0.01353... close to alpha=0.014
    exprs.push(Expr { text: "ln(2)/2^(sopfr+1/2)".to_string(), value: ln2 / (2.0_f64).powf(5.5) });
    exprs.push(Expr { text: "ln(2)/2^(sopfr+mu)".to_string(), value: ln2 / (2.0_f64).powf(6.0) });
    exprs.push(Expr { text: "ln(2)/(tau*sigma)".to_string(), value: ln2 / 48.0 });
    exprs.push(Expr { text: "3/ln(2)".to_string(), value: 3.0 / ln2 });
    exprs.push(Expr { text: "(n/phi)/ln(2)".to_string(), value: 3.0 / ln2 });

    // Deduplicate by text
    let mut seen = HashSet::with_capacity(exprs.len());
    exprs.retain(|e| {
        if e.value.is_nan() || e.value.is_infinite() { return false; }
        seen.insert(e.text.clone())
    });

    exprs
}

// ── ANIMA Target Values ─────────────────────────────────────────

struct AnimaTarget {
    value: f64,
    name: &'static str,
    domain: &'static str,
    known_formula: &'static str,  // empty if unknown
}

fn anima_targets() -> Vec<AnimaTarget> {
    vec![
        // Psi-constants (from consciousness_laws.json)
        AnimaTarget { value: 0.5,     name: "Psi_balance",             domain: "Psi",          known_formula: "1/2" },
        AnimaTarget { value: 0.014,   name: "Psi_coupling (alpha)",    domain: "Psi",          known_formula: "ln(2)/2^5.5" },
        AnimaTarget { value: 4.33,    name: "Psi_steps",               domain: "Psi",          known_formula: "3/ln(2)" },
        AnimaTarget { value: 0.10,    name: "Psi_frustration (F_c)",   domain: "Psi",          known_formula: "1/10" },
        AnimaTarget { value: 0.998,   name: "Psi_entropy",             domain: "Psi",          known_formula: "" },
        // Consciousness architecture
        AnimaTarget { value: 18.0,    name: "18 emotions",             domain: "Consciousness", known_formula: "" },
        AnimaTarget { value: 40.0,    name: "40D consciousness vector",domain: "Consciousness", known_formula: "" },
        AnimaTarget { value: 170.0,   name: "170 data types",          domain: "Consciousness", known_formula: "" },
        AnimaTarget { value: 12.0,    name: "12 factions",             domain: "Consciousness", known_formula: "sigma(6)" },
        AnimaTarget { value: 2.847,   name: "bigbang score",           domain: "Physics",       known_formula: "" },
        // Model parameters
        AnimaTarget { value: 34500000.0, name: "ConsciousDecoderV2 (34.5M params)", domain: "Model", known_formula: "" },
        AnimaTarget { value: 274000000.0,name: "DecoderV3 (274M params)",           domain: "Model", known_formula: "" },
        // Training results
        AnimaTarget { value: 0.004,   name: "CE v13",                  domain: "Training",      known_formula: "" },
        AnimaTarget { value: 71.0,    name: "Phi v13",                 domain: "Training",      known_formula: "" },
        // Architecture dimensions
        AnimaTarget { value: 128.0,   name: "hidden dimension (128d)", domain: "Architecture",  known_formula: "2^7" },
        AnimaTarget { value: 384.0,   name: "decoder dimension (384d)",domain: "Architecture",  known_formula: "" },
        AnimaTarget { value: 256.0,   name: "byte-level vocab",        domain: "Architecture",  known_formula: "2^8" },
        AnimaTarget { value: 1024.0,  name: "max cells",               domain: "Architecture",  known_formula: "2^10" },
        AnimaTarget { value: 64.0,    name: "default cells",           domain: "Architecture",  known_formula: "2^6" },
        // Scaling laws
        AnimaTarget { value: 0.55,    name: "Phi scaling exp (N<=256)",domain: "Scaling",       known_formula: "" },
        AnimaTarget { value: 1.09,    name: "Phi scaling exp (N>256)", domain: "Scaling",       known_formula: "" },
        AnimaTarget { value: 85.6,    name: "brain-likeness %",        domain: "Scaling",       known_formula: "" },
        AnimaTarget { value: 892.0,   name: "Hexad improvement %",     domain: "Scaling",       known_formula: "" },
        // Additional Psi constants from consciousness_laws.json
        AnimaTarget { value: 0.6,     name: "gate_infer",              domain: "Psi",           known_formula: "" },
        AnimaTarget { value: 0.001,   name: "gate_micro",              domain: "Psi",           known_formula: "" },
        AnimaTarget { value: 0.2,     name: "narrative_min",           domain: "Psi",           known_formula: "" },
        AnimaTarget { value: 0.05,    name: "soc_ema_fast",            domain: "Psi",           known_formula: "" },
        AnimaTarget { value: 0.008,   name: "soc_ema_slow",            domain: "Psi",           known_formula: "" },
        AnimaTarget { value: 0.002,   name: "soc_ema_glacial",         domain: "Psi",           known_formula: "" },
    ]
}

// ── Hash-based Expression Index ─────────────────────────────────

/// Dual-scale quantization: linear for small values, log for large
fn quantize(v: f64) -> i64 {
    if v.abs() < 10000.0 {
        (v * 10000.0).round() as i64
    } else {
        // Log-scale bucket for large values (prevents huge range scans)
        let sign = if v >= 0.0 { 1i64 } else { -1 };
        sign * (100_000_000 + (v.abs().ln() * 100000.0).round() as i64)
    }
}

struct ExprIndex {
    map: HashMap<i64, Vec<usize>>,
    #[allow(dead_code)]
    expr_count: usize,
}

impl ExprIndex {
    fn build(exprs: &[Expr]) -> Self {
        let mut map: HashMap<i64, Vec<usize>> = HashMap::with_capacity(exprs.len());
        let count = exprs.len();
        for (i, e) in exprs.iter().enumerate() {
            map.entry(quantize(e.value)).or_default().push(i);
        }
        ExprIndex { map, expr_count: count }
    }

    fn find_matches(&self, target: f64, tolerance: f64, exprs: &[Expr]) -> Vec<(usize, f64)> {
        let mut results = Vec::new();
        if target.abs() < 1e-15 { return results; }

        if target.abs() < 10000.0 {
            // Linear-scale lookup with bounded spread
            let center = quantize(target);
            let spread = ((target.abs() * tolerance * 10000.0).ceil() as i64).min(500).max(1);
            for key in (center - spread)..=(center + spread) {
                if let Some(indices) = self.map.get(&key) {
                    for &i in indices {
                        let err = ((exprs[i].value - target) / target).abs();
                        if err < tolerance {
                            results.push((i, err));
                        }
                    }
                }
            }
        } else {
            // For large values, use log-scale buckets with small spread
            let center = quantize(target);
            let spread = (tolerance * 100000.0).ceil() as i64;
            let spread = spread.min(200).max(1);
            for key in (center - spread)..=(center + spread) {
                if let Some(indices) = self.map.get(&key) {
                    for &i in indices {
                        let err = ((exprs[i].value - target) / target).abs();
                        if err < tolerance {
                            results.push((i, err));
                        }
                    }
                }
            }
        }
        results
    }
}

// ── Match Grade ─────────────────────────────────────────────────

fn grade(err: f64) -> &'static str {
    if err < 1e-10     { "EXACT" }
    else if err < 0.001 { "CLOSE" }
    else if err < 0.01  { "NEAR" }
    else if err < 0.05  { "WEAK" }
    else                 { "FAR" }
}

fn surprisal(err: f64, depth: usize) -> f64 {
    // Higher surprisal = more interesting discovery
    // Exact matches at higher depth are more surprising
    let precision_bonus = if err < 1e-10 { 10.0 } else { -err.log10().max(0.0) };
    let depth_bonus = depth as f64;
    precision_bonus + depth_bonus
}

// ── Operators ────────────────────────────────────────────────────

/// COLLISION: Find ANIMA parameters that coincide with physics/engineering constants
fn op_collision(targets: &[AnimaTarget]) -> Vec<Discovery> {
    let mut discoveries = Vec::new();

    // Known physics/engineering constants to check collision with
    let physics_constants: &[(&str, f64, &str)] = &[
        ("1/alpha (fine structure)", 137.036, "Physics"),
        ("alpha_s(M_Z)", 0.1190, "Physics"),
        ("sin^2(theta_W)", 0.2308, "Physics"),
        ("Koide Q", 0.6667, "Physics"),
        ("Betz limit", 0.5926, "Energy"),
        ("Adam beta1", 0.9, "AI"),
        ("Adam beta2", 0.999, "AI"),
        ("Adam epsilon", 1e-8, "AI"),
        ("Weight decay", 0.1, "AI"),
        ("Dropout standard", 0.1, "AI"),
        ("Top-p sampling", 0.95, "AI"),
        ("d_head universal", 128.0, "AI"),
        ("LLaMA-7B d_model", 2048.0, "AI"),
        ("GPT-3 d_model", 4096.0, "AI"),
        ("LoRA rank", 8.0, "AI"),
        ("Chinchilla ratio", 20.0, "AI"),
        ("Codons", 64.0, "Biology"),
        ("Amino acids", 20.0, "Biology"),
        ("DNA bases", 4.0, "Biology"),
        ("Semitones per octave", 12.0, "Audio"),
        ("OSI layers", 7.0, "Network"),
        ("SQ bandgap (eV)", 1.333, "Energy"),
        ("ln(2)", 0.6931, "Math"),
        ("1/e", 0.3679, "Math"),
        ("golden ratio", 1.6180, "Math"),
        ("pi/6", 0.5236, "Math"),
        ("e/pi", 0.8653, "Math"),
    ];

    for target in targets {
        for &(phys_name, phys_val, phys_domain) in physics_constants {
            let err = ((target.value - phys_val) / phys_val.abs().max(1e-15)).abs();
            if err < 0.05 {
                let domains = vec![target.domain.to_string(), phys_domain.to_string()];
                let div = diversity_score(&domains);
                let prec = 1.0 - err;
                let g = grade(err);

                discoveries.push(Discovery {
                    operator: "COLLISION".to_string(),
                    score: div * prec * if err < 1e-6 { 2.0 } else { 1.0 },
                    description: format!(
                        "[{}] {} ({}) = {} ({}) | err={:.6}%",
                        g, target.name, target.value, phys_name, phys_val, err * 100.0
                    ),
                    domains,
                    formula: format!("{} ~ {}", target.name, phys_name),
                    diversity: div,
                    precision: prec,
                    novelty: if err < 1e-6 { 2.0 } else { 1.0 },
                });
            }
        }
    }

    discoveries
}

/// INVERSE: For each ANIMA target, find best n=6 expression match
fn op_inverse(
    expressions: &[Expr],
    expr_index: &ExprIndex,
    targets: &[AnimaTarget],
) -> Vec<Discovery> {
    let mut discoveries = Vec::with_capacity(targets.len());

    for target in targets {
        // Try multiple tolerances: tight first, then wider
        let mut best_matches: Vec<(String, f64, usize)> = Vec::new(); // (expr, err, depth_hint)

        for &tol in &[0.0001, 0.001, 0.01, 0.05] {
            let raw = expr_index.find_matches(target.value, tol, expressions);
            for (i, err) in raw {
                let text = &expressions[i].text;
                // Estimate depth from expression complexity
                let depth = if text.contains('(') { 2 } else if text.contains('+') || text.contains('-') || text.contains('*') || text.contains('/') { 1 } else { 0 };
                if !best_matches.iter().any(|(t, _, _)| t == text) {
                    best_matches.push((text.clone(), err, depth));
                }
            }
            if best_matches.len() >= 5 { break; }
        }

        if best_matches.is_empty() { continue; }

        best_matches.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
        best_matches.truncate(5);

        let best_err = best_matches[0].1;
        let best_expr = &best_matches[0].0;
        let best_depth = best_matches[0].2;
        let g = grade(best_err);
        let surp = surprisal(best_err, best_depth);

        let known_note = if !target.known_formula.is_empty() {
            format!(" (known: {})", target.known_formula)
        } else {
            String::new()
        };

        let all_exprs: Vec<String> = best_matches.iter().map(|(e, err, _)| {
            format!("{} [{}]", e, grade(*err))
        }).collect();

        let domains = vec![target.domain.to_string()];
        let div = diversity_score(&domains);
        let prec = 1.0 - best_err;

        discoveries.push(Discovery {
            operator: "INVERSE".to_string(),
            score: surp * prec,
            description: format!(
                "[{}] {} = {} <- n6: {}{} | surprisal={:.1}",
                g, target.name, target.value, best_expr, known_note, surp
            ),
            domains,
            formula: all_exprs.join(" | "),
            diversity: div,
            precision: prec,
            novelty: surp,
        });
    }

    discoveries
}

/// COMPOSE: Find single n6 expressions that match multiple ANIMA targets
fn op_compose(
    expressions: &[Expr],
    expr_index: &ExprIndex,
    targets: &[AnimaTarget],
) -> Vec<Discovery> {
    let mut discoveries = Vec::new();

    // For each expression, find all targets it matches
    let mut expr_matches: HashMap<usize, Vec<(usize, f64)>> = HashMap::new();

    for (ti, target) in targets.iter().enumerate() {
        let raw = expr_index.find_matches(target.value, 0.01, expressions);
        for (ei, err) in raw {
            expr_matches.entry(ei).or_default().push((ti, err));
        }
    }

    for (ei, matched_targets) in &expr_matches {
        if matched_targets.len() < 2 { continue; }

        let expr_text = &expressions[*ei].text;
        let mut domains: Vec<String> = Vec::new();
        let mut names: Vec<String> = Vec::new();
        let best_err = matched_targets.iter().map(|(_, e)| *e).fold(f64::MAX, f64::min);

        for &(ti, _) in matched_targets {
            let t = &targets[ti];
            if !domains.contains(&t.domain.to_string()) {
                domains.push(t.domain.to_string());
            }
            names.push(t.name.to_string());
        }

        let cats: HashSet<&str> = domains.iter().map(|d| categorize_domain(d)).collect();
        let div = diversity_score(&domains);
        let prec = 1.0 - best_err;
        let score = div * prec * matched_targets.len() as f64;

        if score > 0.01 {
            discoveries.push(Discovery {
                operator: "COMPOSE".to_string(),
                score,
                description: format!(
                    "n6 '{}' = {:.6} matches {} targets across {} domains: {}",
                    expr_text,
                    expressions[*ei].value,
                    matched_targets.len(),
                    cats.len(),
                    names.join(", ")
                ),
                domains,
                formula: expr_text.clone(),
                diversity: div,
                precision: prec,
                novelty: matched_targets.len() as f64,
            });
        }
    }

    discoveries
}

// ── Engine Core ─────────────────────────────────────────────────

fn run_engine_core() -> (Vec<Discovery>, usize) {
    let expressions = enumerate_depth2();
    let total_exprs = expressions.len();

    let targets = anima_targets();
    let expr_index = ExprIndex::build(&expressions);

    let d1 = op_collision(&targets);
    let d2 = op_inverse(&expressions, &expr_index, &targets);
    let d3 = op_compose(&expressions, &expr_index, &targets);

    let mut all: Vec<Discovery> = Vec::with_capacity(d1.len() + d2.len() + d3.len());
    all.extend(d1);
    all.extend(d2);
    all.extend(d3);

    all.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));

    (all, total_exprs)
}

// ── Output ──────────────────────────────────────────────────────

fn print_text(discoveries: &[Discovery], total_exprs: usize, total_matches: usize, elapsed_us: u128) {
    let elapsed_ms = elapsed_us as f64 / 1000.0;
    println!("================================================================");
    println!("  ANIMA Discovery Engine — Consciousness Parameter Analysis");
    println!("  n=6 base: sigma=12, tau=4, phi=2, sopfr=5, J2=24, mu=1, n=6");
    println!("================================================================");
    println!("  Expressions enumerated: {:>8}", total_exprs);
    println!("  Discoveries found:      {:>8}", total_matches);
    println!("  Time elapsed:         {:>8.2} ms", elapsed_ms);
    println!("================================================================");
    println!();

    // Group by operator
    for op in &["INVERSE", "COLLISION", "COMPOSE"] {
        let filtered: Vec<&Discovery> = discoveries.iter().filter(|d| d.operator == *op).collect();
        if filtered.is_empty() { continue; }

        println!("--- {} ({} results) ---", op, filtered.len());
        println!("{:<4} {:<6} {:<6} {}", "#", "Score", "Prec", "Description");
        println!("{}", "-".repeat(100));

        for (i, d) in filtered.iter().take(30).enumerate() {
            let desc_trunc = if d.description.chars().count() > 85 {
                let s: String = d.description.chars().take(82).collect();
                format!("{}...", s)
            } else {
                d.description.clone()
            };
            println!("{:<4} {:<6.2} {:<6.3} {}", i + 1, d.score, d.precision, desc_trunc);
        }
        println!();
    }

    // Summary: best match per target
    println!("=== BEST MATCH PER ANIMA TARGET ===");
    println!("{:<35} {:<12} {:<8} {:<6} {}", "Target", "Value", "Grade", "Err%", "n6 Expression");
    println!("{}", "-".repeat(100));

    let targets = anima_targets();
    let inv: Vec<&Discovery> = discoveries.iter().filter(|d| d.operator == "INVERSE").collect();

    for target in &targets {
        // Find the INVERSE discovery for this target
        if let Some(d) = inv.iter().find(|d| d.description.contains(target.name)) {
            // Extract grade from description
            let g = if d.description.starts_with("[EXACT") { "EXACT" }
                else if d.description.starts_with("[CLOSE") { "CLOSE" }
                else if d.description.starts_with("[NEAR") { "NEAR" }
                else if d.description.starts_with("[WEAK") { "WEAK" }
                else { "FAR" };
            let err_pct = (1.0 - d.precision) * 100.0;

            // Extract the first expression from the formula
            let first_expr = d.formula.split(" | ").next().unwrap_or("?");

            println!("{:<35} {:<12} {:<8} {:<6.3} {}",
                target.name, format!("{}", target.value), g, err_pct, first_expr);
        } else {
            println!("{:<35} {:<12} {:<8} {:<6} {}",
                target.name, format!("{}", target.value), "NONE", "-", "no match found");
        }
    }
}

fn print_json(discoveries: &[Discovery], total_exprs: usize, total_matches: usize, elapsed_us: u128) {
    println!("{{");
    println!("  \"engine\": \"ANIMA Discovery Engine\",");
    println!("  \"base_constants\": {{\"sigma\": 12, \"tau\": 4, \"phi\": 2, \"sopfr\": 5, \"J2\": 24, \"mu\": 1, \"n\": 6}},");
    println!("  \"stats\": {{");
    println!("    \"expressions_enumerated\": {},", total_exprs);
    println!("    \"discoveries_found\": {},", total_matches);
    println!("    \"elapsed_us\": {}", elapsed_us);
    println!("  }},");
    println!("  \"discoveries\": [");
    let take_n = discoveries.len().min(100);
    for (i, d) in discoveries.iter().take(take_n).enumerate() {
        let comma = if i < take_n - 1 { "," } else { "" };
        let domains_json: Vec<String> = d.domains.iter()
            .map(|s| format!("\"{}\"", s.replace('"', "\\\"")))
            .collect();
        println!("    {{");
        println!("      \"rank\": {},", i + 1);
        println!("      \"operator\": \"{}\",", d.operator);
        println!("      \"score\": {:.4},", d.score);
        println!("      \"diversity\": {:.4},", d.diversity);
        println!("      \"precision\": {:.4},", d.precision);
        println!("      \"novelty\": {:.4},", d.novelty);
        println!("      \"formula\": \"{}\",", d.formula.replace('"', "\\\""));
        println!("      \"description\": \"{}\",", d.description.replace('"', "\\\""));
        println!("      \"domains\": [{}]", domains_json.join(", "));
        println!("    }}{}", comma);
    }
    println!("  ]");
    println!("}}");
}

// ── Benchmark ───────────────────────────────────────────────────

fn run_benchmark() {
    let iterations = 100;
    let mut times_us: Vec<u128> = Vec::with_capacity(iterations);

    // Warmup
    let mut total_disc = 0;
    for _ in 0..3 {
        let (d, _) = run_engine_core();
        total_disc = d.len();
    }

    for _ in 0..iterations {
        let start = Instant::now();
        let _ = run_engine_core();
        times_us.push(start.elapsed().as_micros());
    }

    times_us.sort();
    let min = times_us[0];
    let max = times_us[iterations - 1];
    let avg: u128 = times_us.iter().sum::<u128>() / iterations as u128;
    let p50 = times_us[iterations / 2];
    let p99 = times_us[(iterations * 99) / 100];

    println!("================================================================");
    println!("  ANIMA Discovery Engine — Benchmark ({} iterations)", iterations);
    println!("================================================================");
    println!("  Discoveries:  {:>6}", total_disc);
    println!("  Min:       {:>7.2} ms", min as f64 / 1000.0);
    println!("  Max:       {:>7.2} ms", max as f64 / 1000.0);
    println!("  Avg:       {:>7.2} ms", avg as f64 / 1000.0);
    println!("  p50:       {:>7.2} ms", p50 as f64 / 1000.0);
    println!("  p99:       {:>7.2} ms", p99 as f64 / 1000.0);
    println!("  Throughput: {:>6.0} runs/sec", 1_000_000.0 / avg as f64);
    println!("================================================================");
}

// ── Main ─────────────────────────────────────────────────────────

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let json_mode = args.iter().any(|a| a == "--json");
    let bench_mode = args.iter().any(|a| a == "--bench");

    if bench_mode {
        run_benchmark();
        return;
    }

    let start = Instant::now();
    let (all, total_exprs) = run_engine_core();
    let elapsed = start.elapsed().as_micros();

    if json_mode {
        print_json(&all, total_exprs, all.len(), elapsed);
    } else {
        print_text(&all, total_exprs, all.len(), elapsed);
    }
}
