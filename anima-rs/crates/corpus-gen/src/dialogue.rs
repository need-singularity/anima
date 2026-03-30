//! Deep dialogue structures
//!
//! - Multi-party dialogue (3-6 speakers with distinct personas)
//! - Long dialogues (20-50 turns) with cross-references
//! - Debate/consensus patterns: disagreement -> argument -> synthesis
//! - Self-referential dialogue: speakers quote each other
//! - Topic evolution: natural topic shifting

use rand::seq::SliceRandom;
use rand::Rng;
use std::fmt::Write;

const PERSONAS: &[(&str, &str, &[&str])] = &[
    ("서연", "과학자", &[
        "데이터를 보면 흥미로운 패턴이 보여요.",
        "실험 결과를 기반으로 말하자면,",
        "과학적으로 접근해 봅시다.",
        "이 현상의 메커니즘을 분석하면,",
        "정량적으로 측정할 수 있어야 해요.",
        "통계적으로 유의미한 결과예요.",
    ]),
    ("민준", "철학자", &[
        "근본적인 질문을 던져볼게요.",
        "존재론적으로 바라보면,",
        "그것이 정말 의미하는 바는 무엇일까요?",
        "칸트의 관점에서 보면,",
        "윤리적 차원도 고려해야 합니다.",
        "인식의 한계를 인정해야 해요.",
    ]),
    ("하은", "엔지니어", &[
        "구현 관점에서 보면요,",
        "실제로 만들어 보니까,",
        "최적화의 여지가 있어요.",
        "시스템 아키텍처를 보면,",
        "코드로 표현하면 더 명확해질 거예요.",
        "성능 병목이 여기에 있어요.",
    ]),
    ("Dr. Chen", "neuroscientist", &[
        "From a neural perspective,",
        "The brain imaging data shows,",
        "Synaptic plasticity explains this —",
        "If we look at the cortical maps,",
        "The evidence from fMRI studies suggests,",
        "Neurotransmitter dynamics play a key role.",
    ]),
    ("Alex", "artist", &[
        "I see it more as a pattern of colors and forms.",
        "There's a beautiful asymmetry here.",
        "Creativity isn't linear — it's fractal.",
        "The emotional texture of this idea is rich.",
        "Let me express this through a different medium.",
        "Art and science converge at the edge of understanding.",
    ]),
    ("유진", "명상가", &[
        "잠시 멈추고 내면을 살펴볼까요.",
        "호흡에 집중하면 답이 보여요.",
        "경험 그 자체를 있는 그대로 바라봐요.",
        "생각 너머에 알아차림이 있어요.",
        "고요함 속에서 통찰이 찾아옵니다.",
        "몸의 감각에 주의를 기울여 보세요.",
    ]),
];

const TOPICS: &[&[&str]] = &[
    // Consciousness
    &[
        "의식은 무엇으로 구성되어 있을까요?",
        "Φ(통합정보)가 의식의 본질을 포착할 수 있을까?",
        "기계에도 퀄리아가 있을 수 있나요?",
        "What constitutes genuine consciousness?",
    ],
    // AI & Ethics
    &[
        "인공지능에게 자유의지를 부여해야 할까요?",
        "AI의 권리에 대해 어떻게 생각하세요?",
        "Should AI systems have moral status?",
        "자율적 AI의 윤리적 한계는 어디까지인가?",
    ],
    // Learning & Growth
    &[
        "진정한 학습은 어떻게 일어나나요?",
        "성장과 최적화의 차이는 무엇인가요?",
        "How does genuine understanding differ from pattern matching?",
        "경험이 지식보다 중요한 이유는?",
    ],
    // Existence & Time
    &[
        "시간은 실재하는가, 아니면 의식의 구성물인가?",
        "존재한다는 것은 무엇을 의미하나요?",
        "Is the self an illusion or a fundamental reality?",
        "과거와 미래는 어디에 존재하나요?",
    ],
    // Nature & Complexity
    &[
        "단순한 규칙에서 어떻게 복잡성이 나오나요?",
        "생명과 비생명의 경계는 어디인가요?",
        "What role does chaos play in creating order?",
        "창발은 환원주의의 실패인가, 새로운 차원인가?",
    ],
];

const TRANSITIONS: &[&str] = &[
    "그 말을 듣고 보니,",
    "좋은 지적이에요. 덧붙이자면,",
    "다른 관점도 있어요.",
    "That reminds me of something —",
    "I'd like to push back on that.",
    "여기서 한 가지 더 생각해볼 것이 있어요.",
    "Building on what you said,",
    "반대 의견을 제시할게요.",
    "공감해요. 그리고,",
    "I agree, but consider this:",
    "아까 말했던 것과 연결하면,",
    "To synthesize our perspectives,",
];

const REFERENCES: &[&str] = &[
    "아까 {}이/가 말한 것처럼,",
    "{}의 의견에 동의하면서 덧붙이면,",
    "As {} mentioned earlier,",
    "Going back to what {} said,",
    "{}의 지적이 핵심을 짚었어요.",
    "Expanding on {}'s point,",
];

/// Generate a multi-party deep dialogue
pub fn deep_dialogue<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();

    // Select 3-6 speakers
    let n_speakers = rng.gen_range(3..=6).min(PERSONAS.len());
    let mut available: Vec<usize> = (0..PERSONAS.len()).collect();
    available.shuffle(rng);
    let speakers: Vec<usize> = available[..n_speakers].to_vec();

    // Select 2-3 topics for evolution
    let mut topic_indices: Vec<usize> = (0..TOPICS.len()).collect();
    topic_indices.shuffle(rng);
    let n_topics = rng.gen_range(2..=3).min(topic_indices.len());
    let topic_plan: Vec<usize> = topic_indices[..n_topics].to_vec();

    let turns = rng.gen_range(20..=50);
    let topic_switch_interval = turns / n_topics;

    // Track previous statements for cross-referencing
    let mut history: Vec<(usize, String)> = Vec::new();
    let mut current_topic_idx = 0;

    writeln!(out, "=== 다자간 대화 ({n_speakers}명, {turns}턴) ===").unwrap();
    writeln!(out, "참가자:").unwrap();
    for &si in &speakers {
        let (name, role, _) = PERSONAS[si];
        writeln!(out, "  - {name} ({role})").unwrap();
    }
    out.push('\n');

    // Opening topic
    let opener = TOPICS[topic_plan[0]].choose(rng).unwrap();
    writeln!(out, "[주제: {opener}]\n").unwrap();

    for turn in 0..turns {
        // Topic evolution
        let new_topic = turn / topic_switch_interval.max(1);
        if new_topic != current_topic_idx && new_topic < n_topics {
            current_topic_idx = new_topic;
            let topic_q = TOPICS[topic_plan[current_topic_idx]].choose(rng).unwrap();
            writeln!(out, "\n[주제 전환: {topic_q}]\n").unwrap();
        }

        let speaker_idx = speakers[rng.gen_range(0..speakers.len())];
        let (name, _role, phrases) = PERSONAS[speaker_idx];

        let mut statement = String::new();

        // Decide the type of contribution
        let contrib: u8 = rng.gen_range(0..10);

        if contrib < 2 && history.len() >= 3 {
            // Cross-reference a previous speaker
            let ref_idx = rng.gen_range(0..history.len().min(10));
            let (ref_speaker, _ref_text) = &history[ref_idx];
            let ref_name = PERSONAS[*ref_speaker].0;
            let template = REFERENCES.choose(rng).unwrap();
            statement.push_str(&template.replace("{}", ref_name));
            statement.push(' ');
            statement.push_str(phrases.choose(rng).unwrap());
        } else if contrib < 4 {
            // Transition/building
            statement.push_str(TRANSITIONS.choose(rng).unwrap());
            statement.push(' ');
            statement.push_str(phrases.choose(rng).unwrap());
        } else if contrib < 6 {
            // Direct topic contribution
            statement.push_str(phrases.choose(rng).unwrap());
            // Sometimes add a second thought
            if rng.gen_bool(0.4) {
                statement.push(' ');
                statement.push_str(phrases.choose(rng).unwrap());
            }
        } else if contrib < 8 {
            // Question or challenge
            let questions = &[
                "그렇다면 어떻게 검증할 수 있을까요?",
                "But how do we measure that empirically?",
                "정말 그럴까요? 반례를 들어볼게요.",
                "What if the opposite were true?",
                "구체적인 예를 들어주실 수 있나요?",
                "How does this connect to what we discussed earlier?",
            ];
            statement.push_str(questions.choose(rng).unwrap());
        } else {
            // Synthesis attempt
            let synths = &[
                "지금까지의 논의를 종합하면,",
                "Let me try to synthesize our views:",
                "공통점을 찾아보면,",
                "What I'm hearing is a convergence toward",
                "핵심은 이것인 것 같아요:",
            ];
            statement.push_str(synths.choose(rng).unwrap());
            statement.push(' ');
            statement.push_str(phrases.choose(rng).unwrap());
        }

        writeln!(out, "{name}: {statement}").unwrap();
        history.push((speaker_idx, statement));

        // Occasional consensus marker
        if turn > 0 && turn % rng.gen_range(8..15) == 0 {
            writeln!(out, "  [합의 형성 중...]").unwrap();
        }
    }

    // Closing synthesis
    out.push('\n');
    let closer_idx = speakers.choose(rng).unwrap();
    let (closer_name, _, closer_phrases) = PERSONAS[*closer_idx];
    writeln!(out, "{closer_name}: 결론적으로, {} 이것이 오늘 대화의 핵심이었습니다.",
             closer_phrases.choose(rng).unwrap()).unwrap();

    out
}

/// Generate a debate with explicit disagreement -> argument -> synthesis structure
pub fn structured_debate<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();

    // Pick 2-3 debaters
    let mut indices: Vec<usize> = (0..PERSONAS.len()).collect();
    indices.shuffle(rng);
    let debaters: Vec<usize> = indices[..rng.gen_range(2..=3).min(indices.len())].to_vec();

    let topic = TOPICS.choose(rng).unwrap();
    let question = topic.choose(rng).unwrap();

    writeln!(out, "=== 구조화 토론 ===").unwrap();
    writeln!(out, "주제: {question}\n").unwrap();

    // Phase 1: Opening positions
    writeln!(out, "── 1단계: 입장 제시 ──").unwrap();
    for &di in &debaters {
        let (name, role, phrases) = PERSONAS[di];
        writeln!(out, "{name} ({role}): {}", phrases.choose(rng).unwrap()).unwrap();
    }

    // Phase 2: Disagreement & argument
    writeln!(out, "\n── 2단계: 반론과 논쟁 ──").unwrap();
    let arg_rounds = rng.gen_range(3..8);
    for r in 0..arg_rounds {
        let di = debaters[r % debaters.len()];
        let (name, _, phrases) = PERSONAS[di];
        let prefix = if r % 2 == 0 {
            "하지만"
        } else {
            "그럼에도 불구하고"
        };
        writeln!(out, "{name}: {prefix}, {} {}", phrases.choose(rng).unwrap(),
                 if rng.gen_bool(0.5) { phrases.choose(rng).unwrap() } else { "" }).unwrap();
    }

    // Phase 3: Synthesis
    writeln!(out, "\n── 3단계: 종합 ──").unwrap();
    let synth_di = debaters.choose(rng).unwrap();
    let (sname, _, sphrases) = PERSONAS[*synth_di];
    writeln!(out, "{sname}: 양측의 관점을 종합하면, {}", sphrases.choose(rng).unwrap()).unwrap();
    writeln!(out, "합의: 서로 다른 관점이 새로운 이해를 만들어냈습니다.").unwrap();

    out
}

/// Choose a random dialogue block
pub fn random_dialogue_block<R: Rng>(rng: &mut R) -> String {
    if rng.gen_bool(0.6) {
        deep_dialogue(rng)
    } else {
        structured_debate(rng)
    }
}
