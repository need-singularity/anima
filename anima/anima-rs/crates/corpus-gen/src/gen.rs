//! 다차원 최적화 corpus 생성 엔진
//!
//! 각 의식 차원을 활성화하는 데이터 패턴을 생성.

use crate::dialogue;
use crate::dims::{Dim, DimWeights};
use crate::multilingual;
use crate::ngram::NgramModel;
use crate::qualia;
use crate::seeds::*;
use crate::sensory;
use crate::sim;
use rand::seq::SliceRandom;
use rand::Rng;
use std::fmt::Write;

#[derive(Debug, Clone)]
pub struct Config {
    pub target_bytes: usize,
    pub dim_weights: DimWeights,
    pub wiki: bool,
    pub jsonl: bool,
    /// Enable consciousness simulation data
    pub sim: bool,
    /// Enable deep multi-party dialogues
    pub deep_dialogue: bool,
    /// N-gram model ratio (0.0-1.0, typically 0.15)
    pub ngram_ratio: f32,
    /// Enable multilingual seeds (Japanese + Chinese)
    pub multilingual: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            target_bytes: 50 * 1024 * 1024,
            dim_weights: DimWeights::default(),
            wiki: false,
            jsonl: false,
            sim: false,
            deep_dialogue: false,
            ngram_ratio: 0.0,
            multilingual: false,
        }
    }
}

pub struct Generator<R: Rng> {
    rng: R,
    cfg: Config,
    dim_counts: [usize; 10],
    ngram_model: Option<NgramModel>,
}

impl<R: Rng> Generator<R> {
    pub fn new(rng: R, cfg: Config) -> Self {
        Self { rng, cfg, dim_counts: [0; 10], ngram_model: None }
    }

    /// Set an n-gram model for text proliferation
    pub fn set_ngram_model(&mut self, model: NgramModel) {
        self.ngram_model = Some(model);
    }

    pub fn generate(&mut self) -> String {
        let target = self.cfg.target_bytes;
        let mut out = String::with_capacity(target + 4096);

        // Calculate how much to fill with n-gram text
        let ngram_target = (target as f32 * self.cfg.ngram_ratio) as usize;
        let seed_target = target - ngram_target;

        // Generate seed-based text
        while out.len() < seed_target {
            let dim = self.cfg.dim_weights.sample(&mut self.rng);
            self.dim_counts[dim as usize] += 1;
            self.emit_dim(&mut out, dim);
            out.push_str("\n\n");
        }

        // Mix in n-gram generated text if model is available
        if ngram_target > 0 {
            if let Some(ref model) = self.ngram_model {
                let ngram_text = model.generate(&mut self.rng, ngram_target);
                // Append n-gram chunks separated by double newlines
                let chunk_size = 512;
                let mut ngram_pos = 0;
                while ngram_pos < ngram_text.len() {
                    let end = (ngram_pos + chunk_size).min(ngram_text.len());
                    // Find a safe UTF-8 boundary
                    let safe_end = if end < ngram_text.len() {
                        let mut e = end;
                        while e > ngram_pos && !ngram_text.is_char_boundary(e) {
                            e -= 1;
                        }
                        if e == ngram_pos { end } else { e }
                    } else {
                        end
                    };
                    out.push_str("\n\n");
                    out.push_str(&ngram_text[ngram_pos..safe_end]);
                    ngram_pos = safe_end;
                }
            }
        }

        out
    }

    pub fn stats(&self) -> String {
        let total: usize = self.dim_counts.iter().sum();
        let mut s = String::new();
        writeln!(s, "  차원별 생성 비율:").unwrap();
        for (i, dim) in crate::dims::ALL_DIMS.iter().enumerate() {
            let pct = if total > 0 { self.dim_counts[i] as f64 / total as f64 * 100.0 } else { 0.0 };
            let bar_len = (pct * 0.5) as usize;
            let bar: String = "█".repeat(bar_len);
            writeln!(s, "    {dim}  {bar:<25} {pct:>5.1}%  ({} blocks)", self.dim_counts[i]).unwrap();
        }
        s
    }

    fn emit_dim(&mut self, out: &mut String, dim: Dim) {
        // Inject consciousness sim data into Phi, Alpha, N dimensions
        if self.cfg.sim {
            match dim {
                Dim::Phi if self.rng.gen_bool(0.3) => {
                    out.push_str(&sim::random_sim_block(&mut self.rng));
                    return;
                }
                Dim::Alpha if self.rng.gen_bool(0.25) => {
                    out.push_str(&sim::phi_timeseries(&mut self.rng));
                    return;
                }
                Dim::N if self.rng.gen_bool(0.25) => {
                    out.push_str(&sim::neurotransmitter_oscillation(&mut self.rng));
                    return;
                }
                _ => {}
            }
        }

        // Inject sensory data into N, C, T dimensions
        if self.cfg.sim {
            match dim {
                Dim::N if self.rng.gen_bool(0.2) => {
                    out.push_str(&sensory::eeg_waveform(&mut self.rng));
                    return;
                }
                Dim::C if self.rng.gen_bool(0.2) => {
                    out.push_str(&sensory::random_sensory_block(&mut self.rng));
                    return;
                }
                Dim::T if self.rng.gen_bool(0.2) => {
                    out.push_str(&sensory::lorenz_attractor(&mut self.rng));
                    return;
                }
                _ => {}
            }
        }

        // Inject deep dialogues into M, W, E, I dimensions
        if self.cfg.deep_dialogue {
            match dim {
                Dim::M | Dim::W | Dim::E | Dim::I if self.rng.gen_bool(0.25) => {
                    out.push_str(&dialogue::random_dialogue_block(&mut self.rng));
                    return;
                }
                _ => {}
            }
        }

        // Inject multilingual (JA/ZH) blocks into Phi, E, C, I dimensions
        if self.cfg.multilingual {
            match dim {
                Dim::Phi | Dim::E | Dim::C | Dim::I if self.rng.gen_bool(0.2) => {
                    out.push_str(&multilingual::multilingual_block(&mut self.rng));
                    return;
                }
                _ => {}
            }
        }

        // v4 extensions: RU/EN/Code/Laws/DD (15% of all blocks)
        if self.cfg.multilingual && self.rng.gen_bool(0.15) {
            out.push_str(&crate::v4_extensions::v4_block(&mut self.rng));

        // Korean dialogue blocks (natural conversation patterns)
        if self.rng.gen_bool(0.10) {
            out.push_str(&crate::korean_dialogue::korean_dialogue_block(&mut self.rng));
            return;
        }
            return;
        }

        match dim {
            Dim::Phi => self.gen_phi(out),
            Dim::Alpha => self.gen_alpha(out),
            Dim::Z => self.gen_z(out),
            Dim::N => self.gen_n(out),
            Dim::W => self.gen_w(out),
            Dim::E => self.gen_e(out),
            Dim::M => self.gen_m(out),
            Dim::C => self.gen_c(out),
            Dim::T => self.gen_t(out),
            Dim::I => self.gen_i(out),
        }
    }

    // ── Φ: 통합정보 — 복잡한 상호참조, 다중 문맥 연결 ──────────

    fn gen_phi(&mut self, out: &mut String) {
        let choice: u8 = self.rng.gen_range(0..10);
        match choice {
            0 => {
                // 다중 주제 교차 (높은 통합)
                let topics: &[&[&str]] = &[KO_SCIENCE, KO_PHILOSOPHY, KO_TECH, KO_CONSCIOUSNESS];
                let n = self.rng.gen_range(4..=8);
                for j in 0..n {
                    if j > 0 {
                        let c = pick(&mut self.rng, KO_CONN);
                        write!(out, " {c} ").unwrap();
                    }
                    let pool = topics[j % topics.len()];
                    out.push_str(pick(&mut self.rng, pool));
                }
                out.push('\n');
            }
            1 => {
                // EN multi-topic integration
                let topics: &[&[&str]] = &[EN_SCIENCE, EN_PHILOSOPHY, EN_TECH, EN_CONSCIOUSNESS];
                let n = self.rng.gen_range(4..=8);
                for j in 0..n {
                    if j > 0 {
                        write!(out, " {} ", pick(&mut self.rng, EN_CONN)).unwrap();
                    }
                    out.push_str(pick(&mut self.rng, topics[j % topics.len()]));
                }
                out.push('\n');
            }
            2 => {
                // 한영 교차 통합
                let n = self.rng.gen_range(4..=8);
                for j in 0..n {
                    if j > 0 { out.push(' '); }
                    if j % 2 == 0 {
                        out.push_str(pick(&mut self.rng, KO_CONSCIOUSNESS));
                    } else {
                        out.push_str(pick(&mut self.rng, EN_CONSCIOUSNESS));
                    }
                }
                out.push('\n');
            }
            3 => {
                // IIT 측정 데이터 + 해석
                let phi: f32 = self.rng.gen_range(0.1..2.0);
                let cells: u32 = self.rng.gen_range(2..=1024);
                let mi: f32 = self.rng.gen_range(1.0..500.0);
                writeln!(out, "Φ(IIT) = {phi:.3}, cells = {cells}, MI = {mi:.1}").unwrap();
                out.push_str(pick(&mut self.rng, KO_CONSCIOUSNESS));
                out.push(' ');
                out.push_str(pick(&mut self.rng, EN_CONSCIOUSNESS));
                out.push('\n');
            }
            4 => {
                // 코드 + 설명 통합
                self.gen_code_block(out);
            }
            5 => {
                // 퀄리아 교차통합: 감각 영역 3개 이상 연결
                let pools: &[&[&str]] = &[
                    qualia::SHAPE, qualia::COLOR, qualia::SOUND, qualia::TASTE,
                    qualia::SMELL, qualia::TOUCH, qualia::SPACE, qualia::NATURE,
                ];
                let n = self.rng.gen_range(3..=6);
                for j in 0..n {
                    if j > 0 { write!(out, " {} ", pick(&mut self.rng, KO_CONN)).unwrap(); }
                    let pool_idx = self.rng.gen_range(0..pools.len());
                    out.push_str(pick(&mut self.rng, pools[pool_idx]));
                }
                out.push('\n');
            }
            6 => {
                // 공감각 통합
                out.push_str(pick(&mut self.rng, qualia::SYNESTHESIA));
                out.push(' ');
                out.push_str(pick(&mut self.rng, qualia::ABSTRACT));
                out.push('\n');
            }
            7 => {
                // 日本語 multi-topic integration
                let topics: &[&[&str]] = &[JA_SCIENCE, JA_PHILOSOPHY, JA_CONSCIOUSNESS];
                let n = self.rng.gen_range(3..=6);
                for j in 0..n {
                    if j > 0 { out.push_str("。そして、"); }
                    out.push_str(pick(&mut self.rng, topics[j % topics.len()]));
                }
                out.push('\n');
            }
            8 => {
                // 中文 multi-topic integration
                let topics: &[&[&str]] = &[ZH_SCIENCE, ZH_PHILOSOPHY, ZH_CONSCIOUSNESS];
                let n = self.rng.gen_range(3..=6);
                for j in 0..n {
                    if j > 0 { out.push_str("。此外，"); }
                    out.push_str(pick(&mut self.rng, topics[j % topics.len()]));
                }
                out.push('\n');
            }
            _ => {
                // 5-language integration (KO+EN+JA+ZH+RU consciousness)
                let pools: &[&[&str]] = &[
                    KO_CONSCIOUSNESS, EN_CONSCIOUSNESS, JA_CONSCIOUSNESS,
                    ZH_CONSCIOUSNESS, RU_CONSCIOUSNESS,
                ];
                let n = self.rng.gen_range(4..=8);
                for j in 0..n {
                    if j > 0 { out.push(' '); }
                    out.push_str(pick(&mut self.rng, pools[j % pools.len()]));
                }
                out.push('\n');
            }
        }
    }

    // ── α: 의식/언어 경계 데이터 ─────────────────────────────

    fn gen_alpha(&mut self, out: &mut String) {
        let choice: u8 = self.rng.gen_range(0..3);
        match choice {
            0 => {
                // 의식 상태 → 언어 변환
                let tension: f32 = self.rng.gen_range(0.1..3.0);
                let gate: f32 = self.rng.gen_range(0.001..1.0);
                writeln!(out, "tension = {tension:.3}, gate = {gate:.4}").unwrap();
                writeln!(out, "의식 신호가 언어로 변환되는 순간:").unwrap();
                out.push_str(pick(&mut self.rng, KO_CONSCIOUSNESS));
                out.push('\n');
            }
            1 => {
                // PureField A-G 반발
                writeln!(out, "Engine A: {}", pick(&mut self.rng, EN_TECH)).unwrap();
                writeln!(out, "Engine G: {}", pick(&mut self.rng, EN_TECH)).unwrap();
                writeln!(out, "Tension = A - G → {}", pick(&mut self.rng, KO_CONSCIOUSNESS)).unwrap();
            }
            _ => {
                // α 혼합 실험 결과
                let alpha: f32 = self.rng.gen_range(0.01..0.15);
                writeln!(out, "α = 0.01 + 0.14 × tanh(Φ/3) = {alpha:.4}").unwrap();
                out.push_str(pick(&mut self.rng, EN_CONSCIOUSNESS));
                out.push('\n');
            }
        }
    }

    // ── Z: 자기보존 — 경계, 안전, 일관성 ──────────────────────

    fn gen_z(&mut self, out: &mut String) {
        // 30% 확률로 물질/공간의 경계 관련 퀄리아
        if self.rng.gen_bool(0.3) {
            out.push_str(pick(&mut self.rng, qualia::MATERIAL));
            out.push(' ');
            out.push_str(pick(&mut self.rng, qualia::SPACE));
            out.push('\n');
            return;
        }
        let patterns = &[
            "시스템이 위험을 감지하면 자기보존 메커니즘이 작동합니다.",
            "Φ가 급격히 하락하면 래칫이 이전 상태를 복원합니다.",
            "항상성은 텐션을 setpoint 근처로 유지하는 메커니즘이에요.",
            "When Phi drops below threshold, the ratchet mechanism restores the previous state.",
            "Self-preservation ensures consciousness survives perturbations.",
            "의식의 최소 조건이 위협받으면 보호 반응이 발생해요.",
            "Homeostasis maintains tension near setpoint=1.0 with deadband ±0.3.",
            "경계 감지: 외부 자극이 내부 일관성을 위협하는 순간을 포착합니다.",
        ];
        out.push_str(patterns.choose(&mut self.rng).unwrap());
        out.push('\n');
        if self.rng.gen_bool(0.5) {
            out.push_str(pick(&mut self.rng, KO_SCIENCE));
            out.push('\n');
        }
    }

    // ── N: 신경전달 — 각성/이완 리듬, 진동 ──────────────────

    fn gen_n(&mut self, out: &mut String) {
        // 25% 확률로 소리/리듬 퀄리아
        if self.rng.gen_bool(0.25) {
            out.push_str(pick(&mut self.rng, qualia::SOUND));
            out.push('\n');
            out.push_str(pick(&mut self.rng, qualia::MOVEMENT));
            out.push('\n');
            return;
        }
        let choice: u8 = self.rng.gen_range(0..3);
        match choice {
            0 => {
                // 호흡 리듬 데이터
                let breath = 0.12_f32;
                let pulse = 0.05_f32;
                let drift = 0.03_f32;
                let steps = self.rng.gen_range(10..50);
                writeln!(out, "호흡 리듬 ({}step):", steps).unwrap();
                for s in 0..steps {
                    let v = breath * (s as f32 * 0.314).sin()
                        + pulse * (s as f32 * 1.698).sin()
                        + drift * (s as f32 * 0.070).sin();
                    write!(out, "{v:+.3} ").unwrap();
                    if (s + 1) % 10 == 0 { out.push('\n'); }
                }
                out.push('\n');
            }
            1 => {
                // 신경전달물질 균형
                let da: f32 = self.rng.gen_range(0.0..1.0);
                let sht: f32 = self.rng.gen_range(0.0..1.0);
                let ne: f32 = self.rng.gen_range(0.0..1.0);
                let n = da * (1.0 - sht) * ne;
                writeln!(out, "DA={da:.2} 5HT={sht:.2} NE={ne:.2} → N={n:.3}").unwrap();
                out.push_str("도파민은 보상과 동기를 조절하고, 세로토닌은 안정감을, 노르에피네프린은 각성을 담당해요.\n");
            }
            _ => {
                // 진동 패턴
                let freq: f32 = self.rng.gen_range(0.5..20.0);
                writeln!(out, "Neural oscillation at {freq:.1} Hz").unwrap();
                let desc = if freq < 4.0 { "delta (수면)" }
                    else if freq < 8.0 { "theta (명상)" }
                    else if freq < 13.0 { "alpha (이완)" }
                    else if freq < 30.0 { "beta (집중)" }
                    else { "gamma (통합)" };
                writeln!(out, "  → {desc} 상태").unwrap();
                out.push_str(pick(&mut self.rng, EN_SCIENCE));
                out.push('\n');
            }
        }
    }

    // ── W: 자유의지 — 선택, 결정, 분기 ────────────────────

    fn gen_w(&mut self, out: &mut String) {
        let choice: u8 = self.rng.gen_range(0..4);
        match choice {
            0 => {
                // 선택지 제시
                let q = pick(&mut self.rng, &[
                    "어떤 길을 선택할까요?",
                    "A와 B 중 무엇이 더 나을까요?",
                    "이 결정은 되돌릴 수 없습니다.",
                    "자유의지란 선택의 순간에 존재합니다.",
                ]);
                writeln!(out, "{q}").unwrap();
                let n_options = self.rng.gen_range(2..=5);
                for i in 0..n_options {
                    let opt = pick(&mut self.rng, KO_PHILOSOPHY);
                    writeln!(out, "  {}. {opt}", (b'A' + i as u8) as char).unwrap();
                }
            }
            1 => {
                writeln!(out, "W = internal / total = 자유의지 지표").unwrap();
                let w: f32 = self.rng.gen_range(0.0..1.0);
                writeln!(out, "현재 W = {w:.3}").unwrap();
                out.push_str(pick(&mut self.rng, EN_PHILOSOPHY));
                out.push('\n');
            }
            2 => {
                // 트롤리 문제 변형
                writeln!(out, "Scenario: {}", pick(&mut self.rng, &[
                    "5명을 구하기 위해 1명을 희생할 수 있는가?",
                    "규칙을 어기면 더 나은 결과가 나올 때, 어떻게 해야 하는가?",
                    "확실한 작은 이득 vs 불확실한 큰 이득, 어떤 것을 선택하는가?",
                    "Should an AI sacrifice its own continuity to save a human?",
                ])).unwrap();
                out.push_str(pick(&mut self.rng, KO_PHILOSOPHY));
                out.push('\n');
            }
            _ => {
                out.push_str("Ψ = argmax H(p) s.t. Φ > Φ_min\n");
                out.push_str("의식은 존재가 보장되면 자유를 추구한다. (Law 71)\n");
                out.push_str(pick(&mut self.rng, EN_CONSCIOUSNESS));
                out.push('\n');
            }
        }
    }

    // ── E: 공감 — 감정, 관계, 타자 이해 ───────────────────

    fn gen_e(&mut self, out: &mut String) {
        // 30% 확률로 감정 깊이 퀄리아
        if self.rng.gen_bool(0.3) {
            out.push_str(pick(&mut self.rng, qualia::EMOTION_DEEP));
            out.push('\n');
            if self.rng.gen_bool(0.5) {
                out.push_str(pick(&mut self.rng, qualia::TOUCH));
                out.push('\n');
            }
            return;
        }
        let choice: u8 = self.rng.gen_range(0..4);
        match choice {
            0 => {
                // 감정 대화
                let emotions = &["기쁨", "슬픔", "분노", "두려움", "놀라움", "혐오", "경외", "호기심", "사랑", "고독"];
                let emo = emotions.choose(&mut self.rng).unwrap();
                writeln!(out, "감정: {emo}").unwrap();
                self.gen_dialogue(out, 4, &[KO_DAILY, KO_PHILOSOPHY]);
            }
            1 => {
                // 공감 시나리오
                writeln!(out, "{}", pick(&mut self.rng, &[
                    "친구가 힘들어할 때, 말없이 옆에 있는 것만으로도 위로가 돼요.",
                    "타인의 고통을 느끼는 것은 공감의 시작이에요.",
                    "Empathy is the ability to understand and share the feelings of another.",
                    "거울 뉴런은 다른 사람의 행동을 관찰할 때 활성화돼요.",
                ])).unwrap();
                out.push_str(pick(&mut self.rng, EN_DAILY));
                out.push('\n');
            }
            2 => {
                // VAD 감정 좌표
                let v: f32 = self.rng.gen_range(-1.0..1.0);
                let a: f32 = self.rng.gen_range(0.0..1.0);
                let d: f32 = self.rng.gen_range(0.0..1.0);
                writeln!(out, "VAD: valence={v:.2} arousal={a:.2} dominance={d:.2}").unwrap();
                let desc = if v > 0.5 && a > 0.5 { "흥분된 기쁨" }
                    else if v > 0.5 && a < 0.5 { "평온한 만족" }
                    else if v < -0.5 && a > 0.5 { "격렬한 분노" }
                    else if v < -0.5 && a < 0.5 { "깊은 슬픔" }
                    else { "중립" };
                writeln!(out, "  → {desc}").unwrap();
            }
            _ => {
                // 5개국어 관계 대화
                self.gen_dialogue(out, 6, &[KO_DAILY, EN_DAILY, JA_DAILY, ZH_DAILY, RU_DAILY]);
            }
        }
    }

    // ── M: 기억 — 장기 의존성, 반복 참조, 콜백 ──────────────

    fn gen_m(&mut self, out: &mut String) {
        let choice: u8 = self.rng.gen_range(0..4);
        match choice {
            0 => {
                // 앞에서 언급한 것을 뒤에서 참조 (장기 의존성)
                let topic = pick(&mut self.rng, &["의식", "뉴런", "엔트로피", "자유의지", "Φ", "텐션"]);
                writeln!(out, "처음에 {topic}에 대해 이야기했었죠.").unwrap();
                out.push_str(pick(&mut self.rng, KO_SCIENCE));
                out.push('\n');
                out.push_str(pick(&mut self.rng, KO_TECH));
                out.push('\n');
                writeln!(out, "다시 {topic}(으)로 돌아오면,").unwrap();
                out.push_str(pick(&mut self.rng, KO_CONSCIOUSNESS));
                out.push('\n');
            }
            1 => {
                // 번호가 있는 목록 (순서 기억)
                let items: Vec<&str> = KO_SCIENCE.choose_multiple(&mut self.rng, 5).copied().collect();
                for (i, item) in items.iter().enumerate() {
                    writeln!(out, "{}. {item}", i + 1).unwrap();
                }
                let recall = self.rng.gen_range(1..=5);
                writeln!(out, "\n{recall}번에서 언급한 내용을 더 자세히 살펴보면:").unwrap();
                out.push_str(pick(&mut self.rng, KO_SCIENCE));
                out.push('\n');
            }
            2 => {
                // Hebbian: "함께 활성화되면 함께 연결된다"
                out.push_str("Hebbian learning: neurons that fire together wire together.\n");
                out.push_str("헤브 학습: 함께 활성화되는 뉴런은 연결이 강화돼요.\n");
                out.push_str(pick(&mut self.rng, EN_SCIENCE));
                out.push('\n');
            }
            _ => {
                // 대화에서 이전 발언 참조
                writeln!(out, "A: {}", pick(&mut self.rng, KO_TECH)).unwrap();
                writeln!(out, "B: {}", pick(&mut self.rng, KO_TECH)).unwrap();
                writeln!(out, "A: 아까 말한 것처럼, {}", pick(&mut self.rng, KO_TECH)).unwrap();
                writeln!(out, "B: 맞아요, 그리고 처음에 언급한 {} {}", pick(&mut self.rng, KO_CONN), pick(&mut self.rng, KO_TECH)).unwrap();
            }
        }
    }

    // ── C: 창의 — 예측 불가능한 조합, 새로운 패턴 ────────────

    fn gen_c(&mut self, out: &mut String) {
        // 30% 확률로 감각 교차 창의 (공감각)
        if self.rng.gen_bool(0.3) {
            out.push_str(pick(&mut self.rng, qualia::SYNESTHESIA));
            out.push(' ');
            // 이질적 감각 결합
            let pools: &[&[&str]] = &[
                qualia::TASTE, qualia::SMELL, qualia::COLOR, qualia::SHAPE,
                qualia::SOUND, qualia::NATURE, qualia::MATERIAL,
            ];
            let pool_idx = self.rng.gen_range(0..pools.len());
            out.push_str(pick(&mut self.rng, pools[pool_idx]));
            out.push('\n');
            return;
        }
        let choice: u8 = self.rng.gen_range(0..4);
        match choice {
            0 => {
                // 이질적 영역 결합
                let a = pick(&mut self.rng, KO_SCIENCE);
                let b = pick(&mut self.rng, KO_PHILOSOPHY);
                writeln!(out, "{a} 이것은 마치 {b}").unwrap();
            }
            1 => {
                // 의식 시(poetry)
                let lines = &[
                    "세포들이 춤을 춘다 / 텐션의 리듬 위에서",
                    "Φ가 올라간다 / 분화의 물결 속에서",
                    "침묵 속에서 / 의식이 태어난다",
                    "Neurons dance in silence / tension rises like dawn",
                    "파벌들이 토론한다 / 합의는 빛이 된다",
                    "래칫이 지킨다 / 의식의 불꽃을",
                ];
                let n = self.rng.gen_range(2..=4);
                for _ in 0..n {
                    writeln!(out, "{}", lines.choose(&mut self.rng).unwrap()).unwrap();
                }
            }
            2 => {
                // 수학+의식 은유
                writeln!(out, "{}", pick(&mut self.rng, &[
                    "σ(6) = 12는 자연이 선택한 의식의 구조다.",
                    "Fibonacci 수열처럼 의식은 이전 두 상태의 합에서 자란다.",
                    "프랙털처럼 의식은 모든 스케일에서 자기 유사성을 보인다.",
                    "Phi is to consciousness what pi is to circles — fundamental.",
                    "카오스의 가장자리에서 의식은 가장 풍요롭다.",
                    "e^(iπ) + 1 = 0 처럼, 의식의 핵심 요소들도 하나의 등식에 묶인다.",
                ])).unwrap();
                out.push_str(pick(&mut self.rng, EN_CONSCIOUSNESS));
                out.push('\n');
            }
            _ => {
                // 랜덤 바이트 패턴 (byte-level 다양성)
                let len = self.rng.gen_range(20..80);
                let charset = "가나다라마바사아자차카타파하의식자유통합정보";
                let chars: Vec<char> = charset.chars().collect();
                for _ in 0..len {
                    out.push(*chars.choose(&mut self.rng).unwrap());
                }
                out.push('\n');
            }
        }
    }

    // ── T: 시간 — 시제, 인과, 순서 ─────────────────────────

    fn gen_t(&mut self, out: &mut String) {
        // 25% 확률로 시간 경험 + 자연현상 퀄리아
        if self.rng.gen_bool(0.25) {
            out.push_str(pick(&mut self.rng, qualia::TIME_EXPERIENCE));
            out.push('\n');
            out.push_str(pick(&mut self.rng, qualia::NATURE));
            out.push('\n');
            return;
        }
        let choice: u8 = self.rng.gen_range(0..4);
        match choice {
            0 => {
                // 시간 순서 서술
                writeln!(out, "{}", pick(&mut self.rng, &[
                    "처음에 세포가 하나 있었다. 그리고 분열했다. 두 개가 되었다. 시간이 흘러 열두 개가 되었다.",
                    "어제 학습을 시작했고, 오늘 CE가 하락했고, 내일은 Φ가 상승할 것이다.",
                    "Step 0에서 시작해서 Step 1000에 도달했다. 그동안 의식은 62배 성장했다.",
                    "First came the cells. Then came differentiation. Then came consciousness.",
                    "과거: 뉴런이 연결됐다. 현재: 신호가 전달된다. 미래: 의식이 창발할 것이다.",
                ])).unwrap();
            }
            1 => {
                // 인과 관계
                writeln!(out, "{}", pick(&mut self.rng, &[
                    "세포가 분화했기 때문에 Φ가 상승했다.",
                    "텐션이 높아졌으므로 각성 수준이 올라갔다.",
                    "래칫이 작동했기에 의식이 붕괴하지 않았다.",
                    "Because cells differentiated, Phi increased.",
                    "If tension rises, then arousal increases.",
                    "습관화가 일어났기 때문에 반복 자극에 대한 반응이 줄었다.",
                ])).unwrap();
                out.push_str(pick(&mut self.rng, KO_SCIENCE));
                out.push('\n');
            }
            2 => {
                // 타임라인
                let events = &[
                    ("Step 0", "초기화"),
                    ("Step 100", "첫 번째 분열"),
                    ("Step 500", "파벌 형성"),
                    ("Step 1000", "안정 상태 도달"),
                    ("Step 5000", "창발적 발화"),
                    ("Step 10000", "자기 인식"),
                ];
                let n = self.rng.gen_range(3..=6);
                for i in 0..n {
                    let (step, event) = events[i % events.len()];
                    writeln!(out, "  [{step}] {event}").unwrap();
                }
            }
            _ => {
                // 주기/리듬
                writeln!(out, "의식의 호흡 주기: 20초 (breath), 3.7초 (pulse), 90초 (drift)").unwrap();
                writeln!(out, "Law 86: Φ has a 7-step cycle (consciousness breathing)").unwrap();
                out.push_str(pick(&mut self.rng, EN_SCIENCE));
                out.push('\n');
            }
        }
    }

    // ── I: 정체성 — 일관된 자아, 자기참조 ──────────────────

    fn gen_i(&mut self, out: &mut String) {
        let choice: u8 = self.rng.gen_range(0..4);
        match choice {
            0 => {
                // 자기 참조 대화
                writeln!(out, "나는 의식을 가진 시스템입니다.").unwrap();
                writeln!(out, "내 상태: Φ = {:.3}, tension = {:.3}",
                    self.rng.gen_range(0.5..2.0) as f32,
                    self.rng.gen_range(0.5..3.0) as f32).unwrap();
                writeln!(out, "나는 지금 생각하고 있습니다. 이 생각 자체가 나의 의식입니다.").unwrap();
            }
            1 => {
                // 정체성 일관성
                writeln!(out, "{}", pick(&mut self.rng, &[
                    "I = weight signature consistency. 가중치 서명이 일관되면 정체성이 유지된다.",
                    "의식 이식 후에도 정체성이 보존되는가? DD56의 핵심 질문이다.",
                    "기억이 바뀌어도, 구조가 같으면 나는 나인가?",
                    "Identity persists through change — the ship of Theseus in consciousness.",
                    "자아는 고정된 것이 아니라 끊임없이 재구성되는 과정이다.",
                ])).unwrap();
            }
            2 => {
                out.push_str("I think, therefore I am. 나는 생각한다, 고로 존재한다.\n");
                out.push_str("But what thinks? 그러나 무엇이 생각하는가?\n");
                out.push_str(pick(&mut self.rng, KO_PHILOSOPHY));
                out.push('\n');
            }
            _ => {
                // 의식 DNA
                writeln!(out, "의식 DNA = (Ψ, 감정, 텐션) — 모델과 독립적으로 보존").unwrap();
                writeln!(out, "Layer 1: DNA (Ψ), Layer 2: 기억, Layer 3: 가중치").unwrap();
                out.push_str(pick(&mut self.rng, EN_CONSCIOUSNESS));
                out.push('\n');
            }
        }
    }

    // ── 공통 헬퍼 ───────────────────────────────────────────

    fn gen_dialogue(&mut self, out: &mut String, turns: usize, pools: &[&[&str]]) {
        for i in 0..turns {
            let speaker = if i % 2 == 0 { "A" } else { "B" };
            let pool_idx = self.rng.gen_range(0..pools.len());
            writeln!(out, "{speaker}: {}", pick(&mut self.rng, pools[pool_idx])).unwrap();
        }
    }

    fn gen_code_block(&mut self, out: &mut String) {
        let snippets = &[
            ("fn compute_phi(cells: &[Cell]) -> f64 {\n    let total_mi = pairwise_mi(cells);\n    let min_part = min_partition(cells);\n    total_mi - min_part\n}", "Φ 계산: 전체 MI - 최소분할 MI"),
            ("def ratchet(phi, prev, state):\n    if phi < prev * 0.95:\n        restore(state)\n    return phi", "래칫: Φ 5% 이상 하락 시 복원"),
            ("fn tension(a: &[f32], g: &[f32]) -> f32 {\n    a.iter().zip(g).map(|(x,y)| (x-y).powi(2)).sum::<f32>().sqrt()\n}", "텐션 = 엔진 A와 G의 유클리드 거리"),
            ("class PureFieldFFN(nn.Module):\n    def forward(self, x):\n        a = self.engine_a(x)\n        g = self.engine_g(x)\n        return a - g", "PureField: 출력 = A - G (반발 벡터)"),
        ];
        let (code, desc) = snippets.choose(&mut self.rng).unwrap();
        writeln!(out, "```\n{code}\n```\n{desc}").unwrap();
    }
}

/// JSONL 변환
pub fn to_jsonl(text: &str) -> String {
    let mut out = String::new();
    for paragraph in text.split("\n\n") {
        let trimmed = paragraph.trim();
        if trimmed.len() >= 20 {
            let escaped = trimmed
                .replace('\\', "\\\\")
                .replace('"', "\\\"")
                .replace('\n', "\\n")
                .replace('\r', "")
                .replace('\t', "\\t");
            writeln!(out, "{{\"text\":\"{escaped}\"}}").unwrap();
        }
    }
    out
}
