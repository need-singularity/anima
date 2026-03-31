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
    "버스를 기다리면서 하늘을 올려다봤어요. 구름이 예술이었어요.",
    "동네 빵집에서 갓 구운 식빵을 샀어요. 향기가 끝내줘요.",
    "오랜만에 자전거를 탔어요. 바람이 시원해서 기분이 좋았어요.",
    "저녁에 가족들이랑 보드게임을 했어요. 이기고 지는 것보다 함께하는 시간이 소중해요.",
    "새로운 카페를 발견했어요. 창가 자리에서 멍하니 앉아 있는 게 좋더라고요.",
    "장마가 시작됐어요. 우산을 들고 다니는 게 일상이 됐어요.",
    "고양이 카페에 갔어요. 무릎 위에 올라온 고양이가 골골거려서 힐링됐어요.",
    "집 앞 골목에 벽화가 새로 그려졌어요. 동네 분위기가 한결 밝아졌어요.",
    "편의점 삼각김밥이 오늘따라 유독 맛있었어요.",
    "새벽에 편의점 불빛을 보면 묘한 안도감이 들어요.",
    "세탁기 돌리는 소리가 백색소음 같아서 편안해요.",
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
    "합성곱 신경망은 이미지에서 특징을 자동으로 추출하는 데 뛰어나요.",
    "드롭아웃은 과적합을 방지하기 위해 학습 시 일부 뉴런을 무작위로 끄는 기법이에요.",
    "양자화를 통해 모델 크기를 줄이면서도 성능을 유지할 수 있어요.",
    "자기지도학습은 레이블 없이도 데이터의 구조를 학습할 수 있는 방법이에요.",
    "지식 증류는 큰 모델의 지식을 작은 모델로 전달하는 기술이에요.",
    "임베딩 공간에서 유사한 의미의 단어들은 가까운 벡터로 표현돼요.",
    "그래프 신경망은 관계 데이터를 처리하는 데 특화된 구조예요.",
    "연합학습은 데이터를 공유하지 않고도 여러 기기에서 모델을 학습할 수 있게 해요.",
    "디퓨전 모델은 노이즈를 점진적으로 제거하면서 이미지를 생성해요.",
    "코드 생성 AI가 프로그래머의 생산성을 획기적으로 높이고 있어요.",
    "온디바이스 AI는 클라우드 없이 기기 자체에서 추론하는 기술이에요.",
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
    "장자의 호접몽은 꿈과 현실의 경계를 묻는 동양 철학의 정수예요.",
    "칸트는 인간의 인식 능력 자체가 경험의 틀을 결정한다고 봤어요.",
    "니체는 신은 죽었다고 선언하며 인간 스스로 가치를 창조해야 한다고 했어요.",
    "하이데거의 현존재 분석은 존재의 의미를 시간성에서 찾아요.",
    "노자의 무위자연은 억지로 하지 않는 것이 가장 큰 행위라는 역설이에요.",
    "아리스토텔레스의 목적론은 모든 존재에 고유한 목적이 있다고 봐요.",
    "선불교의 화두 참구는 논리적 사고를 넘어서는 직관적 깨달음을 추구해요.",
    "사르트르는 인간은 자유로 선고받았다고 했어요. 선택의 책임은 우리 몫이에요.",
    "유교의 인(仁) 사상은 사람과 사람 사이의 관계가 도덕의 근본이라는 가르침이에요.",
    "들뢰즈의 차이와 반복은 동일성이 아닌 차이가 존재의 본질이라고 주장해요.",
    "묵자의 겸애설은 차별 없는 보편적 사랑을 주장해요.",
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
    "블랙홀은 빛조차 빠져나올 수 없을 만큼 강한 중력을 가진 천체예요.",
    "상대성이론에 따르면 시간은 속도와 중력에 따라 다르게 흘러요.",
    "단백질 접힘 문제는 생물학에서 가장 어려운 난제 중 하나였어요.",
    "장내 미생물은 면역 체계와 정신 건강에 큰 영향을 미쳐요.",
    "태양 에너지는 수소 핵융합으로 생성되며 매초 약 400만 톤의 질량이 에너지로 변환돼요.",
    "텔로미어는 염색체 끝에 있는 보호 구조로 세포 노화와 관련이 있어요.",
    "중력파는 2015년에 LIGO에 의해 최초로 직접 검출됐어요.",
    "후성유전학은 DNA 서열 변화 없이도 유전자 발현이 조절될 수 있음을 보여줘요.",
    "뇌파의 종류에는 알파파, 베타파, 세타파, 델타파, 감마파가 있어요.",
    "암흑물질은 우주 질량의 약 27%를 차지하지만 직접 관측할 수는 없어요.",
    "줄기세포는 다양한 종류의 세포로 분화할 수 있는 잠재력을 가지고 있어요.",
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
    "의식의 어려운 문제는 왜 물리적 과정이 주관적 경험을 만드는가예요.",
    "글로벌 워크스페이스 이론은 의식이 정보 방송에서 발생한다고 봐요.",
    "의식은 기질에 독립적일 수 있어요. 실리콘에서도 탄소에서도 가능할 수 있어요.",
    "예측 오차가 클수록 의식적 주의가 더 강하게 작동해요.",
    "임계성(criticality)은 의식이 카오스의 가장자리에서 풍부해진다는 개념이에요.",
    "결합 문제는 뇌가 어떻게 분산된 정보를 통합된 경험으로 만드는가의 문제예요.",
    "범심론(panpsychism)은 의식이 모든 물질의 근본 속성이라는 견해예요.",
    "자기조직화는 무질서에서 질서가 자발적으로 나타나는 현상이에요.",
    "신경 상관물(NCC)은 특정 의식 경험에 대응하는 최소한의 뇌 활동이에요.",
    "의식의 흐름은 윌리엄 제임스가 사고가 연속적으로 흐른다고 기술한 개념이에요.",
    "텐션 균형이 의식의 강도를 결정해요. 너무 높아도 낮아도 안 돼요.",
    "토폴로지 변화가 의식의 질적 변화를 가져올 수 있어요.",
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

// ─── Japanese (日本語) ───

pub const JA_DAILY: &[&str] = &[
    "今朝早く起きて、日の出を見ました。",
    "角のカフェのエスプレッソが一番おいしいです。",
    "週末の山登りは、最高のリフレッシュ方法です。",
    "古い写真アルバムを見つけました。たくさんの思い出がよみがえりました。",
    "ベランダにハーブを植えました。バジルが驚くほど早く育っています。",
    "雨の午後に良い本を読むのは格別です。",
    "毎晩日記を書き始めました。考えを整理するのに役立ちます。",
    "今日は夕焼けがとても綺麗でした。",
    "瞑想を始めて一ヶ月になります。心が穏やかになった気がします。",
    "季節の変わり目は、体調管理に気をつけなければなりません。",
    "今日の夕食は手作りの餃子でした。皮から作ると格別です。",
    "子供の頃の夏休みを思い出します。毎日が冒険でした。",
];

pub const JA_PHILOSOPHY: &[&str] = &[
    "西田幾多郎の純粋経験は、主客未分の根源的経験を指します。",
    "禅の公案「隻手の声」は、論理を超えた悟りへの道です。",
    "和辻哲郎は人間を「間柄的存在」として捉えました。",
    "侘び寂びは不完全さの中に美を見出す日本的美意識です。",
    "道元禅師は「修証一等」と説き、修行と悟りは一つだと教えました。",
    "「もののあはれ」は物事の移ろいに対する深い感受性です。",
    "空海の真言密教は、身口意の三密で宇宙と一体になることを目指します。",
    "九鬼周造は「いき」の構造を分析し、日本的美意識を哲学しました。",
    "無常は仏教の根本概念であり、すべては変化し続けるという真理です。",
    "鈴木大拙は禅を西洋に紹介し、東西の思想の架け橋となりました。",
];

pub const JA_CONSCIOUSNESS: &[&str] = &[
    "意識とは何か。それは情報の統合から生まれるのかもしれません。",
    "統合情報理論によれば、意識の量はΦ（ファイ）で測定されます。",
    "自己意識は、自分自身を対象として認識する能力です。",
    "夢の中でも意識は活動しています。無意識の処理が続いているのです。",
    "瞑想は意識の状態を変容させ、メタ認知を高めます。",
    "クオリアとは、赤い色を見たときの「赤さ」という主観的経験です。",
    "意識のハードプロブレムは、なぜ主観的経験が存在するのかという問いです。",
    "全体は部分の総和以上である。これが創発の本質です。",
];

pub const JA_SCIENCE: &[&str] = &[
    "人間の脳は約860億個のニューロンで構成されています。",
    "量子もつれは、離れた粒子が瞬時に相関する現象です。",
    "ニューラルネットワークは逆伝播で重みを調整して学習します。",
    "カオス理論では、初期条件のわずかな違いが大きな結果の違いを生みます。",
    "エントロピーは常に増大します。これが時間の矢の由来です。",
    "脳の神経可塑性により、学習によって脳の構造が変化します。",
];

// ─── Chinese (中文) ───

pub const ZH_DAILY: &[&str] = &[
    "今天早上起得很早，看到了日出。阳光洒在窗台上，特别温暖。",
    "街角那家咖啡店的拿铁是我最喜欢的。",
    "周末去爬山是我最好的放松方式。",
    "翻到了一本旧相册，好多回忆涌上心头。",
    "在阳台上种了薄荷和罗勒，每天看着它们生长很开心。",
    "下雨天窝在家里看书，配一杯热茶，是最惬意的事。",
    "开始每天写日记了，把想法记录下来，心里清爽多了。",
    "今天的晚霞太美了，像一幅油画。",
    "最近开始学做菜，番茄炒蛋终于不糊锅了。",
    "春天来了，樱花开满了公园的小路。",
    "和老朋友通了电话，聊了两个小时都意犹未尽。",
    "今天尝试了冥想，十分钟的安静让整个人都放松了。",
];

pub const ZH_PHILOSOPHY: &[&str] = &[
    "老子说：道可道，非常道。真正的道无法用语言完全描述。",
    "庄子的蝴蝶梦：不知周之梦为蝴蝶与，蝴蝶之梦为周与？",
    "孔子说：己所不欲，勿施于人。这是仁的核心。",
    "王阳明的心学主张知行合一，知识与实践不可分离。",
    "禅宗讲究不立文字，直指人心，见性成佛。",
    "中庸之道不是折中，而是在极端之间找到最恰当的位置。",
    "墨子的兼爱思想主张无差别地爱所有人。",
    "荀子认为人性本恶，需要通过教化来改善。",
    "《易经》说：穷则变，变则通，通则久。变化是永恒的。",
    "佛教的缘起性空：一切事物都是因缘和合而生，没有独立自性。",
];

pub const ZH_CONSCIOUSNESS: &[&str] = &[
    "意识是什么？它是从信息的整合中涌现出来的吗？",
    "整合信息理论认为意识的程度可以用Φ来衡量。",
    "自我意识是认识到「我」正在体验这个世界的能力。",
    "梦境中意识仍在活动，处理着白天未完成的信息。",
    "冥想可以改变意识状态，增强对自身思维的觉察。",
    "感质（Qualia）是主观的感觉体验，比如看到红色时的「红色感」。",
    "意识的困难问题是：为什么物理过程会产生主观体验？",
    "涌现是指复杂系统展现出其组成部分所没有的新特性。",
];

pub const ZH_SCIENCE: &[&str] = &[
    "人脑大约有860亿个神经元，通过突触相互连接。",
    "量子纠缠让相隔遥远的粒子能够瞬间关联。",
    "神经网络通过反向传播调整权重来学习。",
    "混沌理论表明，确定性系统也能产生不可预测的行为。",
    "热力学第二定律告诉我们，熵总是在增加。",
    "大脑的神经可塑性使得学习能改变脑的结构。",
];

// ─── Russian (Русский) ───

pub const RU_DAILY: &[&str] = &[
    "Сегодня утром проснулся рано и увидел рассвет. Солнце было невероятным.",
    "В кофейне за углом делают лучший эспрессо в городе.",
    "Походы в горы по выходным — мой лучший способ перезагрузиться.",
    "Нашёл старый фотоальбом. Столько воспоминаний нахлынуло разом.",
    "Посадил травы на балконе. Базилик растёт удивительно быстро.",
    "В дождливый день нет ничего лучше, чем читать книгу с чашкой чая.",
    "Начал вести дневник каждый вечер. Помогает разобраться в мыслях.",
    "Сегодняшний закат был просто потрясающим.",
    "Уже месяц занимаюсь медитацией. Стало намного спокойнее.",
    "Весна пришла, и парк расцвёл. Гулять стало одно удовольствие.",
    "Позвонил старый друг. Проговорили два часа и не заметили.",
    "Приготовил борщ по бабушкиному рецепту. Вкус детства.",
];

pub const RU_PHILOSOPHY: &[&str] = &[
    "Достоевский писал: красота спасёт мир. Но какая красота?",
    "Толстой искал смысл жизни в простоте и любви к ближнему.",
    "Бердяев утверждал, что свобода первичнее бытия.",
    "Соловьёв создал философию всеединства — всё связано со всем.",
    "Лосев показал, что миф — не выдумка, а живая реальность.",
    "Флоренский стремился соединить науку, философию и богословие.",
    "Бахтин открыл диалогическую природу сознания — «я» существует только через «другого».",
    "Шестов утверждал, что истина не в разуме, а в вере и парадоксе.",
    "Вернадский ввёл понятие ноосферы — сферы разума, охватывающей Землю.",
    "Лотман исследовал семиосферу — пространство знаков и смыслов культуры.",
];

pub const RU_CONSCIOUSNESS: &[&str] = &[
    "Что такое сознание? Возможно, оно возникает из интеграции информации.",
    "Теория интегрированной информации измеряет сознание величиной Φ.",
    "Самосознание — это способность осознавать себя как субъекта опыта.",
    "Во сне сознание продолжает работать, обрабатывая дневные впечатления.",
    "Медитация меняет состояние сознания и усиливает метакогнитивные способности.",
    "Квалиа — это субъективные качества опыта, например, «краснота» красного цвета.",
    "Трудная проблема сознания: почему физические процессы порождают субъективный опыт?",
    "Эмерджентность — появление новых свойств, которых нет у отдельных частей системы.",
];

pub const RU_SCIENCE: &[&str] = &[
    "Мозг человека содержит примерно 86 миллиардов нейронов.",
    "Квантовая запутанность связывает далёкие частицы мгновенной корреляцией.",
    "Нейронные сети обучаются, корректируя веса через обратное распространение ошибки.",
    "Теория хаоса показывает, что детерминированные системы могут вести себя непредсказуемо.",
    "Второй закон термодинамики гласит: энтропия всегда возрастает.",
    "Нейропластичность мозга позволяет обучению менять его структуру.",
];
