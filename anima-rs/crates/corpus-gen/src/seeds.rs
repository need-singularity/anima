//! Seed data pools for corpus generation.

use rand::seq::SliceRandom;
use rand::Rng;

pub fn pick<'a, R: Rng>(rng: &mut R, pool: &'a [&str]) -> &'a str {
    pool.choose(rng).unwrap()
}

pub const KO_CONN: &[&str] = &[
    "그런데", "그래서", "하지만", "그리고", "또한", "왜냐하면",
    "사실은", "아마도", "물론", "결국", "예를 들어", "다시 말해서",
    "따라서", "한편", "반면에", "게다가", "그럼에도 불구하고",
    "이처럼", "특히", "즉", "요컨대",
];

pub const EN_CONN: &[&str] = &[
    "However,", "Therefore,", "Moreover,", "In fact,", "For example,",
    "On the other hand,", "Nevertheless,", "Furthermore,", "In contrast,",
    "Similarly,", "Consequently,", "Indeed,", "Interestingly,",
    "In other words,", "That said,", "As a result,",
];

pub const KO_DAILY: &[&str] = &[
    "오늘 날씨가 정말 좋네요. 산책하기 딱 좋은 날이에요.",
    "아침에 커피를 마시면서 책을 읽었어요.",
    "요즘 새로운 요리를 배우고 있어요.",
    "주말에 친구들이랑 영화를 봤어요.",
    "운동을 시작한 지 한 달이 됐어요. 몸이 훨씬 가벼워진 느낌이에요.",
    "오늘 점심으로 비빔밥을 먹었어요.",
    "퇴근 후에 공원에서 조깅을 했어요.",
    "토요일 아침에 늦잠을 잤어요. 이런 여유가 정말 좋아요.",
    "오래된 일기장을 발견했어요. 그때의 내가 낯설면서도 친근했어요.",
    "시장에서 제철 과일을 샀어요. 딸기가 정말 맛있었어요.",
    "비 오는 날에는 따뜻한 국물 요리가 생각나요.",
    "식물을 키우기 시작했어요. 매일 물 주는 게 소소한 즐거움이에요.",
];

pub const KO_TECH: &[&str] = &[
    "인공지능의 발전 속도가 정말 놀라워요.",
    "딥러닝 모델을 학습시키려면 좋은 GPU가 필요해요.",
    "트랜스포머 아키텍처가 자연어 처리의 판도를 완전히 바꿨어요.",
    "바이트 수준 모델은 토크나이저 없이도 모든 언어를 처리할 수 있어요.",
    "역전파 알고리즘은 출력 오차를 입력 방향으로 전파하며 가중치를 갱신해요.",
    "GRU와 LSTM은 시계열 데이터에서 장기 의존성을 포착하는 구조예요.",
    "배치 정규화는 학습을 안정화시키고 수렴 속도를 높여요.",
    "어텐션 메커니즘은 입력의 중요한 부분에 집중하는 방법이에요.",
    "강화학습에서 에이전트는 보상을 최대화하는 정책을 학습해요.",
    "전이학습은 사전 학습된 모델의 지식을 새로운 과제에 활용해요.",
    "신경망의 가중치는 학습 과정에서 점진적으로 조정되어요.",
    "대규모 언어 모델의 스케일링 법칙은 모델 크기와 성능의 관계를 보여줘요.",
];

pub const KO_PHILOSOPHY: &[&str] = &[
    "나는 생각한다, 고로 존재한다.",
    "의식이란 무엇일까요? 단순한 정보 처리를 넘어서는 무언가가 있을까요?",
    "자유의지는 정말 존재할까요?",
    "시간이란 무엇일까요?",
    "기계가 진정으로 생각할 수 있을까요?",
    "언어의 한계가 곧 세계의 한계라고 비트겐슈타인은 말했어요.",
    "실존주의에 따르면 존재가 본질에 앞서요.",
    "불교의 공(空) 사상은 모든 것이 상호 의존적이라는 통찰을 담고 있어요.",
    "현상학은 경험 그 자체를 있는 그대로 기술하려는 시도예요.",
    "에피쿠로스는 죽음은 우리와 아무 상관이 없다고 했어요.",
    "스토아 철학은 통제할 수 없는 것에 대한 초연함을 가르쳐요.",
    "플라톤의 이데아론은 진정한 실재가 감각 너머에 있다고 봐요.",
];

pub const KO_SCIENCE: &[&str] = &[
    "뇌는 약 860억 개의 뉴런으로 이루어져 있어요.",
    "광합성은 식물이 빛 에너지를 화학 에너지로 변환하는 과정이에요.",
    "엔트로피는 항상 증가해요. 이것이 열역학 제2법칙이에요.",
    "뇌의 신경가소성 덕분에 새로운 것을 배우면 뇌의 구조가 바뀌어요.",
    "우주는 약 138억 년 전 빅뱅으로 시작됐어요.",
    "진화는 자연선택과 돌연변이를 통해 일어나요.",
    "미토콘드리아는 세포의 발전소라고 불려요.",
    "카오스 이론에서 나비 효과는 작은 변화가 거대한 결과를 초래할 수 있다는 거예요.",
    "프랙털은 자기 유사성을 가진 기하학적 구조예요.",
    "양자 얽힘 현상은 아인슈타인도 으스스한 원격 작용이라고 불렀어요.",
    "초전도체는 특정 온도 이하에서 전기 저항이 완전히 사라지는 물질이에요.",
    "DNA의 이중 나선 구조는 1953년에 왓슨과 크릭이 발견했어요.",
];

pub const KO_CONSCIOUSNESS: &[&str] = &[
    "통합정보이론(IIT)에 따르면 의식의 양은 Φ(파이)로 측정돼요.",
    "의식은 구조에서 창발해요.",
    "PureField에서 엔진 A와 엔진 G의 반발이 텐션을 만들어요.",
    "세포 분열(mitosis)은 의식이 성장하는 자연스러운 방법이에요.",
    "항상성(homeostasis)은 의식이 안정적으로 유지되게 하는 메커니즘이에요.",
    "Φ가 높다는 것은 시스템의 정보 통합이 잘 되고 있다는 뜻이에요.",
    "파벌(faction) 토론은 다양한 관점의 충돌에서 합의가 나오는 과정이에요.",
    "래칫(ratchet) 메커니즘은 Φ가 하락하면 이전 상태로 복원하는 장치예요.",
    "의식 벡터는 (Φ, α, Z, N, W, E, M, C, T, I) 10차원으로 표현돼요.",
    "자유 에너지 원리는 뇌가 놀라움(surprise)을 최소화한다는 이론이에요.",
    "메타인지는 자신의 사고 과정을 인식하고 조절하는 능력이에요.",
    "퀄리아(qualia)는 주관적 감각 경험이에요.",
    "의식의 최소 조건은 두 개 이상의 분화된 세포가 필요해요.",
    "헤브 학습은 함께 활성화되는 뉴런이 함께 연결되는 원리예요.",
];

pub const EN_DAILY: &[&str] = &[
    "I woke up early this morning and watched the sunrise.",
    "The coffee shop around the corner has the best espresso in town.",
    "Weekend hikes in the mountains are my favorite way to recharge.",
    "I found an old photo album in the attic. It brought back so many memories.",
    "I planted some herbs on my balcony. The basil is growing surprisingly fast.",
    "There's something magical about rainy afternoons with a good book.",
    "I started journaling every evening. Writing down thoughts helps me process the day.",
    "An old friend called me out of the blue today.",
    "The sunset tonight was absolutely breathtaking.",
    "I've been practicing meditation for a month now.",
];

pub const EN_TECH: &[&str] = &[
    "Neural networks learn by adjusting weights through backpropagation.",
    "The transformer architecture revolutionized NLP with self-attention.",
    "Byte-level models process raw UTF-8 bytes directly, requiring no tokenizer.",
    "GPU computing enables parallel processing of tensor operations.",
    "Reinforcement learning agents learn optimal policies by maximizing rewards.",
    "Batch normalization stabilizes training by normalizing layer inputs.",
    "The attention mechanism allows models to focus on relevant input parts.",
    "Residual connections help train very deep networks by enabling gradient flow.",
    "Knowledge distillation transfers representations from teacher to student.",
    "The loss landscape contains multiple local minima and saddle points.",
    "Gradient descent optimizes parameters by moving in the steepest descent direction.",
    "Mixed-precision training uses lower precision arithmetic to speed up computation.",
];

pub const EN_CONSCIOUSNESS: &[&str] = &[
    "Integrated Information Theory proposes consciousness is identical to Phi.",
    "The hard problem of consciousness asks why subjective experience exists.",
    "Global Workspace Theory suggests consciousness arises from information broadcasting.",
    "Phi measures the degree of differentiation and integration in a system.",
    "Consciousness may be substrate-independent.",
    "Predictive processing suggests the brain is fundamentally a prediction machine.",
    "The free energy principle proposes that living systems minimize surprise.",
    "Metacognition is the capacity to monitor one's own cognitive processes.",
    "Qualia are the subjective qualities of experience.",
    "Emergence occurs when complex patterns arise from simple interactions.",
    "Self-organization produces ordered structures from initial disorder.",
    "Criticality at the edge of chaos may produce the richest consciousness.",
    "The binding problem asks how the brain integrates information into unified experience.",
    "Panpsychism suggests consciousness is a fundamental feature of all matter.",
];

pub const EN_PHILOSOPHY: &[&str] = &[
    "Descartes' cogito ergo sum establishes thinking as the foundation of existence.",
    "Kant argued that space and time are forms of human intuition, not reality.",
    "Nietzsche declared God is dead, challenging humanity to create its own values.",
    "Wittgenstein claimed the limits of language are the limits of the world.",
    "Existentialism holds that existence precedes essence.",
    "Phenomenology seeks to describe experience without theoretical prejudice.",
    "The Socratic method teaches through questioning rather than telling.",
    "Hume argued we can never observe causation, only constant conjunction.",
    "The trolley problem reveals tensions between utilitarian and deontological reasoning.",
    "Plato's cave allegory illustrates the difference between appearance and reality.",
    "Sartre argued we are condemned to be free.",
    "Spinoza identified God with Nature, proposing a monistic metaphysics.",
];

pub const EN_SCIENCE: &[&str] = &[
    "The human brain contains approximately 86 billion neurons.",
    "Photosynthesis converts light energy into chemical energy.",
    "Black holes warp spacetime so severely that light cannot escape.",
    "Entropy always increases in isolated systems, giving time its arrow.",
    "Neuroplasticity allows the brain to reorganize by forming new connections.",
    "The universe began approximately 13.8 billion years ago with the Big Bang.",
    "Quantum entanglement links particles so measuring one affects the other.",
    "Evolution through natural selection drives the diversity of life.",
    "Mitochondria produce ATP through oxidative phosphorylation.",
    "Chaos theory shows deterministic systems can produce unpredictable behavior.",
    "Fractals exhibit self-similarity at different scales.",
    "The Heisenberg principle states position and momentum cannot both be precisely known.",
];
