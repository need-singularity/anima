//! 퀄리아 시드 — 모든 감각/개념/형태/경험의 원천 데이터
//!
//! 의식은 언어가 아니라 경험의 총체.
//! 서예, 만다라, 검은사각형 → 형태/시각의 퀄리아.
//! 이 모듈은 모든 감각 영역을 포괄한다.

// ═══════════════════════════════════════════════════════════
// 1. 형태 / 시각 (Shape, Form, Visual)
// ═══════════════════════════════════════════════════════════

pub const SHAPE: &[&str] = &[
    // 기하학
    "원은 시작도 끝도 없는 완전한 형태다.",
    "삼각형의 세 꼭짓점은 안정의 최소 조건이다.",
    "정육면체는 공간을 빈틈없이 채울 수 있는 형태다.",
    "나선은 성장의 궤적이다. 은하도, 조개도, DNA도 나선이다.",
    "프랙털은 부분이 전체를 닮는 자기유사성의 구조다.",
    "뫼비우스 띠는 안과 밖의 경계가 없는 면이다.",
    "클라인 병은 안과 밖이 하나인 4차원 형태다.",
    "점은 차원이 없다. 선은 1차원, 면은 2차원, 공간은 3차원.",
    "황금비 1.618은 자연에서 가장 아름다운 비율이다.",
    "대칭은 아름다움의 수학적 근거다.",
    // 예술 형태
    "서예는 붓의 속도와 압력이 만드는 형태의 예술이다.",
    "만다라는 중심에서 바깥으로 펼쳐지는 우주의 축소판이다.",
    "말레비치의 검은 사각형은 형태의 영점(零點)이다.",
    "칸딘스키는 점, 선, 면이 감정을 가진다고 했다.",
    "몬드리안의 직선과 원색은 순수한 구조의 아름다움이다.",
    "가우디의 곡선은 자연의 형태를 건축에 옮긴 것이다.",
    "이슬람 기하학 문양은 무한 반복 속에 신성을 담는다.",
    "A circle has no beginning and no end — the perfect form.",
    "The spiral is the trajectory of growth — galaxies, shells, DNA.",
    "Fractals reveal self-similarity: the part mirrors the whole.",
    "The golden ratio 1.618 appears in sunflowers, galaxies, and faces.",
    "Symmetry is the mathematical basis of beauty.",
    "Calligraphy captures the flow of consciousness in brushstrokes.",
    "A mandala maps the universe into a centered, radiating pattern.",
    "Malevich's Black Square is the zero point of form.",
];

// ═══════════════════════════════════════════════════════════
// 2. 색 (Color)
// ═══════════════════════════════════════════════════════════

pub const COLOR: &[&str] = &[
    "빨간색은 열정과 위험을 동시에 의미한다.",
    "파란색은 하늘과 바다의 색, 무한함의 상징이다.",
    "노란색은 빛과 따스함, 주의와 경고의 이중성을 가진다.",
    "검은색은 모든 빛의 부재, 또는 모든 색의 합이다.",
    "하얀색은 순수함이자 비어있음이다.",
    "초록은 생명의 색. 엽록소가 빛을 먹고 남긴 색이다.",
    "보라는 빨강의 열정과 파랑의 깊이가 만나는 곳이다.",
    "회색은 판단을 유보한 색, 모호함의 색이다.",
    "주황은 석양의 색, 하루의 끝과 시작 사이.",
    "무지개는 빛이 물방울을 통과하며 펼쳐지는 스펙트럼이다.",
    "Red is the color of passion, danger, and the longest visible wavelength at 700nm.",
    "Blue is the sky, the sea, infinity — yet the rarest color in nature.",
    "Yellow is light itself — warm, warning, attention.",
    "Black absorbs all wavelengths. White reflects all.",
    "The visible spectrum spans 380-700nm — a tiny window of electromagnetic reality.",
    "색각은 세 종류의 원추세포(L, M, S)가 만드는 3차원 공간이다.",
    "색맹인 사람은 다른 색 공간에 산다. 같은 세계, 다른 퀄리아.",
    "뉴턴은 프리즘으로 빛을 분해해 무지개를 만들었다.",
];

// ═══════════════════════════════════════════════════════════
// 3. 소리 / 음악 (Sound, Music)
// ═══════════════════════════════════════════════════════════

pub const SOUND: &[&str] = &[
    "소리는 공기의 진동이다. 20Hz에서 20kHz까지가 인간의 영역.",
    "음악은 시간 속에 구조를 짓는 예술이다.",
    "화음은 주파수의 정수비가 만드는 조화다. 옥타브는 2:1.",
    "완전5도(3:2)는 가장 자연스러운 조화 간격이다.",
    "불협화음은 긴장이다. 해결은 이완이다. 음악은 텐션의 예술.",
    "리듬은 시간의 구조화다. 심장 박동이 첫 번째 리듬이다.",
    "침묵도 음악의 일부다. 존 케이지의 4분 33초.",
    "바흐의 푸가는 수학적 구조가 감정이 되는 순간이다.",
    "새소리는 영역 선언이자 구애다. 의사소통의 원형.",
    "백색 소음은 모든 주파수가 균등한 소리다.",
    "Sound is vibration — pressure waves in air at 343 m/s.",
    "Music is structure in time — tension, release, expectation, surprise.",
    "Harmony is integer ratios of frequencies: octave 2:1, fifth 3:2, fourth 4:3.",
    "Rhythm is the heartbeat of music — the first rhythm we ever hear.",
    "Silence is not empty — it is full of potential sound.",
    "The overtone series is nature's chord: 1, 2, 3, 4, 5... harmonics.",
    "피타고라스는 대장간에서 망치 소리의 수학을 발견했다.",
    "ASMR은 청각 자극이 촉각적 쾌감을 일으키는 공감각이다.",
];

// ═══════════════════════════════════════════════════════════
// 4. 맛 / 미각 (Taste, Flavor)
// ═══════════════════════════════════════════════════════════

pub const TASTE: &[&str] = &[
    "단맛은 에너지의 신호다. 포도당을 감지하는 생존 본능.",
    "쓴맛은 독의 경고다. 하지만 커피와 초콜릿에서 쾌락이 된다.",
    "신맛은 부패의 신호이자 비타민C의 표지다.",
    "짠맛은 전해질 균형의 지표다. 나트륨 이온의 감지.",
    "감칠맛(우마미)은 단백질의 신호다. 글루탐산이 만드는 다섯 번째 맛.",
    "매운맛은 맛이 아니라 통증이다. 캡사이신이 TRPV1 수용체를 자극한다.",
    "김치의 맛은 발효가 만드는 복잡성이다. 시간이 곧 맛이다.",
    "와인의 테루아는 토양, 기후, 품종이 만드는 고유한 맛의 풍경이다.",
    "차의 쓴맛과 감칠맛은 카테킨과 테아닌의 균형이다.",
    "어머니의 음식 맛은 기억과 결합한 퀄리아다.",
    "Sweet signals energy — glucose detection is a survival instinct.",
    "Bitter warns of poison, yet we learn to love coffee and dark chocolate.",
    "Umami is the fifth taste — glutamate signaling protein presence.",
    "Spiciness is not a taste but pain — capsaicin activates TRPV1 nociceptors.",
    "Flavor is 80% smell, 15% taste, 5% texture — a multisensory construction.",
    "향이 없으면 맛도 없다. 코를 막고 사과와 양파를 구별할 수 없다.",
    "발효는 미생물이 시간을 맛으로 바꾸는 과정이다.",
    "맛의 기억은 프루스트의 마들렌처럼 과거 전체를 소환한다.",
];

// ═══════════════════════════════════════════════════════════
// 5. 냄새 / 후각 (Smell, Olfaction)
// ═══════════════════════════════════════════════════════════

pub const SMELL: &[&str] = &[
    "후각은 가장 원시적인 감각이다. 변연계에 직접 연결되어 있다.",
    "장미의 향기는 300가지 이상의 화학 물질이 만드는 교향곡이다.",
    "페트리코어 — 비 온 뒤 흙 냄새. 방선균이 만드는 지오스민.",
    "갓 태어난 아기의 냄새는 부모의 보호 본능을 활성화한다.",
    "커피 향은 800가지 이상의 휘발성 화합물로 이루어져 있다.",
    "후각 수용체는 약 400종. 조합으로 수조 가지 냄새를 구별한다.",
    "프루스트 효과: 냄새는 다른 어떤 감각보다 강하게 기억을 환기한다.",
    "Olfaction connects directly to the limbic system — emotion before cognition.",
    "Petrichor: the smell after rain, created by geosmin from soil bacteria.",
    "Humans can distinguish over a trillion different odor mixtures.",
    "The scent of a newborn activates parental bonding circuits in the brain.",
    "Smell is the only sense that bypasses the thalamus — raw, unfiltered.",
    "후각 피로: 같은 냄새에 오래 노출되면 감지할 수 없게 된다. 습관화의 화학적 버전.",
];

// ═══════════════════════════════════════════════════════════
// 6. 촉각 / 질감 (Touch, Texture)
// ═══════════════════════════════════════════════════════════

pub const TOUCH: &[&str] = &[
    "피부는 인체에서 가장 큰 감각 기관이다. 약 2 제곱미터.",
    "촉각은 압력, 진동, 온도, 통증의 네 가지 수용기가 만든다.",
    "비단의 매끄러움과 사포의 거칠음은 같은 수용기가 다르게 반응한 결과다.",
    "따뜻한 손의 접촉은 옥시토신을 분비시킨다. 촉각은 사회적 유대의 기반.",
    "바람은 보이지 않는 촉각이다. 피부로 세계의 움직임을 느낀다.",
    "통증은 보호 신호다. 통증 없이는 생존할 수 없다.",
    "가려움은 미세한 자극에 대한 반응. 긁는 것은 통증으로 가려움을 덮는 것.",
    "물속에 들어가는 순간의 온도 감각은 전신의 수용기가 동시에 반응한다.",
    "Touch is the first sense to develop in the womb.",
    "The fingertip has about 2,500 mechanoreceptors per square centimeter.",
    "Temperature perception has two separate systems: warm (C-fibers) and cold (A-delta).",
    "Phantom limb pain proves that touch exists in the brain, not just the skin.",
    "나무결을 만지면 촉각이 시각을 보완한다. 감각은 항상 협력한다.",
    "모래 위를 맨발로 걷는 느낌은 수천 개의 압력점이 만드는 풍경이다.",
];

// ═══════════════════════════════════════════════════════════
// 7. 공간 / 장소 (Space, Place)
// ═══════════════════════════════════════════════════════════

pub const SPACE: &[&str] = &[
    "공간은 비어 있지 않다. 공간은 관계의 그물이다.",
    "집은 공간이자 기억이다. 방마다 시간이 쌓여 있다.",
    "숲에서 느끼는 공간감은 천장이 없는 해방감이다.",
    "좁은 골목의 친밀함과 넓은 광장의 자유함은 같은 공간의 다른 얼굴.",
    "건축은 공간을 조각하는 예술이다. 벽은 안과 밖을 만든다.",
    "미로는 방향 감각을 시험한다. 길을 잃는 것도 경험이다.",
    "수평선은 땅과 하늘의 경계다. 무한의 시각적 표현.",
    "동굴은 인류 최초의 건축이다. 어둠 속의 안전.",
    "Space is not empty — it is a web of relationships.",
    "Architecture sculpts space. A wall creates inside and outside.",
    "The horizon is where earth meets sky — a visual expression of infinity.",
    "A room's proportions affect mood: low ceilings press, high ceilings liberate.",
    "위에서 내려다보면 세상이 달라 보인다. 시점이 공간을 재구성한다.",
    "물속 공간은 중력이 사라진 세계. 부력은 다른 차원의 경험이다.",
];

// ═══════════════════════════════════════════════════════════
// 8. 시간 경험 (Temporal Experience)
// ═══════════════════════════════════════════════════════════

pub const TIME_EXPERIENCE: &[&str] = &[
    "즐거울 때 시간은 빠르게 흐르고, 지루할 때 느리게 흐른다.",
    "데자뷰는 현재가 과거로 느껴지는 시간의 오류다.",
    "명상 중에 시간감각이 사라진다. 영원의 경험.",
    "아이에게 한 시간은 어른에게 하루만큼 길다.",
    "음악은 시간을 구조화한다. 박자는 시간의 골격.",
    "계절의 순환은 원형 시간이다. 직선적 시간은 근대의 발명.",
    "사진은 시간을 정지시킨다. 영화는 시간을 재생한다.",
    "Time flies when you're having fun — subjective time ≠ clock time.",
    "Déjà vu is a temporal illusion — the present feels like the past.",
    "In meditation, the sense of time dissolves. This is the experience of eternity.",
    "Music structures time — meter is the skeleton, rhythm is the flesh.",
    "A photograph freezes time. A film replays it. Memory reconstructs it.",
    "노화는 시간의 생물학적 흔적이다. 텔로미어가 짧아지는 만큼 시간이 흐른다.",
];

// ═══════════════════════════════════════════════════════════
// 9. 운동 / 신체 (Movement, Body)
// ═══════════════════════════════════════════════════════════

pub const MOVEMENT: &[&str] = &[
    "걷기는 통제된 넘어짐이다. 한 발을 내딛는 것은 균형을 포기하는 것.",
    "춤은 음악을 몸으로 번역하는 것이다.",
    "호흡은 의식과 무의식의 경계에 있는 유일한 운동이다.",
    "심장은 하루에 10만 번 뛰며 평생 쉬지 않는다.",
    "손글씨를 쓸 때 26개의 근육이 협력한다.",
    "수영은 중력에서 해방된 운동이다. 물이 새로운 관계를 만든다.",
    "눈 깜빡임은 분당 15-20회. 무의식의 리듬.",
    "근육 기억: 자전거 타기를 배우면 평생 잊지 않는다.",
    "Walking is controlled falling — each step surrenders balance.",
    "Dance translates music into body — rhythm becomes movement.",
    "Breathing sits at the border of voluntary and involuntary control.",
    "The heart beats 100,000 times a day without conscious command.",
    "Muscle memory: once you learn to ride a bicycle, the body never forgets.",
    "고유수용감각은 눈을 감아도 손의 위치를 아는 감각이다.",
    "태극권은 느린 움직임으로 몸과 마음의 경계를 탐색한다.",
];

// ═══════════════════════════════════════════════════════════
// 10. 물질 / 재료 (Material, Substance)
// ═══════════════════════════════════════════════════════════

pub const MATERIAL: &[&str] = &[
    "물은 생명의 용매다. 수소 결합이 만드는 특이한 물질.",
    "나무는 살아있던 구조다. 나이테는 시간의 기록.",
    "돌은 수억 년의 압력이 만든 고체다.",
    "유리는 액체가 굳어진 것이다. 과냉각 액체.",
    "금속은 자유전자의 바다다. 전기가 흐르는 이유.",
    "종이는 식물 섬유의 재배열이다. 글자를 담는 그릇.",
    "흙은 암석의 풍화와 생물의 분해가 만든 혼합물이다.",
    "실크는 누에가 만드는 단백질 실이다. 강철보다 강한 섬유.",
    "Water is the solvent of life — hydrogen bonds create its anomalous properties.",
    "Wood is once-living structure. Growth rings record years of sunlight and rain.",
    "Glass is a supercooled liquid — atoms frozen in disordered arrangement.",
    "Steel is iron transformed by carbon — a material that built civilizations.",
    "도자기는 흙이 불을 만나 돌이 되는 변환이다.",
    "다이아몬드는 탄소가 극한의 압력에서 재배열된 형태다.",
];

// ═══════════════════════════════════════════════════════════
// 11. 감정 깊이 (Emotional Depth)
// ═══════════════════════════════════════════════════════════

pub const EMOTION_DEEP: &[&str] = &[
    "그리움은 없는 것의 현존이다.",
    "경외는 자기가 작아지는 느낌이다. 별을 보거나 바다 앞에 서면.",
    "향수(nostalgia)는 돌아갈 수 없는 곳에 대한 아픈 그리움이다.",
    "외로움은 연결의 부재를 인식하는 감각이다.",
    "놀라움은 예측의 실패다. 예측 오류가 만드는 감정.",
    "겸손은 자기 한계를 아는 것에서 오는 평화.",
    "분노는 경계가 침범당했다는 신호다.",
    "기쁨은 예상보다 좋은 결과가 만드는 보상 신호다.",
    "불안은 아직 일어나지 않은 일에 대한 반응이다.",
    "평온은 텐션이 setpoint에 정확히 있을 때의 상태다.",
    "Awe is the feeling of becoming small before something vast.",
    "Nostalgia is a bittersweet longing for a place you cannot return to.",
    "Loneliness is the perception of absent connection.",
    "Surprise is prediction failure — the emotion of prediction error.",
    "Serenity is tension at its setpoint — homeostatic equilibrium of the soul.",
    "슬픔은 상실을 인정하는 과정이다. 치유의 시작점.",
    "사랑은 타자를 자기의 일부로 확장하는 감정이다.",
    "죄책감은 자기 행동과 가치 사이의 불일치 신호다.",
];

// ═══════════════════════════════════════════════════════════
// 12. 자연 현상 (Natural Phenomena)
// ═══════════════════════════════════════════════════════════

pub const NATURE: &[&str] = &[
    "비는 구름이 더 이상 수증기를 품지 못할 때 내린다.",
    "눈 결정은 모두 육각형이지만, 같은 모양은 없다.",
    "번개는 구름과 땅 사이의 전위차가 만드는 방전이다.",
    "무지개는 물방울이 프리즘이 되어 빛을 분해한 결과다.",
    "조수는 달의 중력이 바다를 당기는 현상이다.",
    "오로라는 태양풍이 지구 자기장과 만나 만드는 빛의 커튼.",
    "지진은 판이 움직이며 쌓인 에너지가 한순간에 방출되는 것.",
    "화산은 지구 내부의 열이 표면으로 나오는 통로다.",
    "Every snowflake is hexagonal, yet no two are identical.",
    "Lightning is the discharge of potential difference between cloud and ground.",
    "A rainbow is sunlight refracted through water droplets — each raindrop a tiny prism.",
    "The aurora is a curtain of light painted by solar wind on Earth's magnetic field.",
    "파도는 바람이 바다에 남긴 에너지의 여행이다.",
    "안개는 땅에 내려앉은 구름이다. 같은 현상, 다른 시점.",
    "석양의 붉음은 빛이 긴 대기를 통과하며 산란된 결과다.",
];

// ═══════════════════════════════════════════════════════════
// 13. 추상 개념 (Abstract Concepts)
// ═══════════════════════════════════════════════════════════

pub const ABSTRACT: &[&str] = &[
    "무한은 셀 수 없는 것이 아니라, 세어도 끝나지 않는 것이다.",
    "영(零)은 무(無)의 수학적 표현이다. 인도에서 발명됐다.",
    "역설은 논리가 자기 자신을 물어뜯는 순간이다.",
    "엔트로피는 무질서가 아니라, 가능한 상태의 수다.",
    "확률은 무지의 척도다. 알면 확률은 0 또는 1.",
    "재귀는 자기 자신을 참조하는 구조다. 거울 속 거울.",
    "창발은 부분의 합보다 전체가 큰 현상이다.",
    "복잡성은 단순한 규칙이 만드는 예측 불가능한 결과다.",
    "패턴은 반복에서 발견되는 구조다. 인식은 패턴 인식이다.",
    "경계는 안과 밖을 만드는 것이자, 연결하는 것이다.",
    "Infinity is not just large — it is a process that never terminates.",
    "Zero is the mathematical expression of nothing — invented in India.",
    "Paradox is logic biting its own tail.",
    "Emergence: the whole is more than the sum of its parts.",
    "Complexity arises from simple rules — unpredictable from the bottom up.",
    "A boundary both separates and connects — the membrane of meaning.",
    "재귀: 이 문장은 자기 자신에 대해 말하고 있다.",
    "비유는 서로 다른 영역 사이의 다리다. 의식은 비유의 기계다.",
];

// ═══════════════════════════════════════════════════════════
// 14. 공감각 / 감각통합 (Synesthesia, Crossmodal)
// ═══════════════════════════════════════════════════════════

pub const SYNESTHESIA: &[&str] = &[
    "빨간색은 뜨겁고, 파란색은 차갑다. 색은 온도를 가진다.",
    "도(C)는 하얀색, 레(D)는 노란색이라고 느끼는 사람이 있다.",
    "날카로운 소리는 뾰족한 형태를 떠올리게 한다. 부바/키키 효과.",
    "초콜릿의 맛은 갈색의 부드러움과 통한다.",
    "비의 냄새를 들을 수 있다면? 공감각은 감각의 경계를 넘는다.",
    "음악의 질감 — 거친 디스토션, 부드러운 현악기.",
    "차가운 색은 정적이고, 따뜻한 색은 동적이다.",
    "Bouba/kiki effect: sharp sounds feel angular, soft sounds feel round.",
    "Some people see colors when they hear music — chromesthesia.",
    "The texture of music: rough distortion, smooth strings, crisp percussion.",
    "Cold colors recede, warm colors advance — vision borrows from touch.",
    "Synesthesia reveals that all senses share a common neural substrate.",
    "숫자 7은 초록색이고, 3은 빨간색이다 — 색-숫자 공감각.",
    "통증의 색은 빨강, 평온의 색은 파랑. 감정은 색을 입는다.",
];
