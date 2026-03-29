#!/usr/bin/env python3
"""
prepare_corpus.py - Generate Korean+English mixed training corpus for ConsciousLM v5

Byte-level model (no tokenizer), so we output raw UTF-8 text.
Target: ~5MB corpus with diverse content for consciousness-aware language model.

Usage:
    python prepare_corpus.py                          # default: data/corpus.txt (~5MB)
    python prepare_corpus.py --output data/corpus.txt --size 10  # 10MB
    python prepare_corpus.py --format jsonl --output data/corpus.jsonl
    python prepare_corpus.py --stats                  # analyze existing corpus

Content mix:
    - Korean monologue/dialogue (40%)
    - English text (30%)
    - Mixed Korean+English dialogue (20%)
    - Consciousness/philosophy domain text (10%)
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Seed data: Korean
# ---------------------------------------------------------------------------

KOREAN_GREETINGS = [
    "안녕하세요", "반갑습니다", "좋은 아침이에요", "오랜만이에요",
    "잘 지내셨어요?", "어떻게 지내세요?", "만나서 반가워요",
]

KOREAN_FILLERS = [
    "그런데", "그래서", "하지만", "그리고", "또한", "왜냐하면",
    "사실은", "아마도", "물론", "결국", "예를 들어", "다시 말해서",
    "그러니까", "따라서", "한편", "반면에", "게다가", "그럼에도 불구하고",
]

KOREAN_TOPICS = {
    "일상": [
        "오늘 날씨가 정말 좋네요. 산책하기 딱 좋은 날이에요.",
        "아침에 커피를 마시면서 책을 읽었어요. 너무 평화로웠어요.",
        "요즘 새로운 요리를 배우고 있어요. 김치찌개를 만들어봤는데 생각보다 어렵더라고요.",
        "주말에 친구들이랑 영화를 봤어요. 정말 재미있었어요.",
        "버스를 타고 출근하는데 창밖 풍경이 참 예뻤어요.",
        "어제 밤에 비가 많이 왔어요. 빗소리를 들으며 잠들었어요.",
        "새로 나온 카페에 갔는데 분위기가 너무 좋았어요.",
        "운동을 시작한 지 한 달이 됐어요. 몸이 훨씬 가벼워진 느낌이에요.",
        "오늘 점심으로 비빔밥을 먹었어요. 역시 한식이 최고예요.",
        "퇴근 후에 공원에서 조깅을 했어요. 스트레스가 확 풀리더라고요.",
    ],
    "기술": [
        "인공지능의 발전 속도가 정말 놀라워요. 매일 새로운 기술이 나오고 있어요.",
        "프로그래밍을 처음 배울 때는 어렵지만, 하다 보면 점점 재미있어져요.",
        "클라우드 컴퓨팅이 우리 생활을 많이 바꿨어요. 어디서든 작업할 수 있게 됐죠.",
        "딥러닝 모델을 학습시키려면 좋은 GPU가 필요해요. 요즘은 H100이 대세예요.",
        "오픈소스 소프트웨어 덕분에 누구나 최신 기술을 사용할 수 있어요.",
        "자연어 처리 기술이 발전하면서 번역의 질이 크게 좋아졌어요.",
        "로봇 공학과 인공지능의 결합은 미래 산업의 핵심이 될 거예요.",
        "양자 컴퓨터가 상용화되면 현재 불가능한 계산도 가능해질 거예요.",
        "사이버 보안의 중요성이 날로 커지고 있어요. 개인정보 보호에 신경 써야 해요.",
        "5G 네트워크가 보급되면서 실시간 데이터 처리가 가능해졌어요.",
    ],
    "철학": [
        "나는 생각한다, 고로 존재한다. 데카르트의 이 말은 의식의 본질을 묻고 있어요.",
        "의식이란 무엇일까요? 단순한 정보 처리를 넘어서는 무언가가 있을까요?",
        "자유의지는 정말 존재할까요? 아니면 모든 것이 결정되어 있는 걸까요?",
        "시간이란 무엇일까요? 물리학에서 시간은 방향이 없지만, 우리는 시간의 흐름을 느껴요.",
        "행복이란 무엇일까요? 쾌락인가요, 아니면 의미 있는 삶인가요?",
        "존재의 이유를 묻는 것 자체가 인간의 특별함을 보여주는 것 같아요.",
        "기계가 진정으로 생각할 수 있을까요? 튜링 테스트만으로는 부족해요.",
        "감정은 이성의 적일까요, 동반자일까요? 다마지오는 감정 없이는 합리적 판단이 불가능하다고 했어요.",
        "우주에 우리만 있을까요? 페르미 역설은 여전히 풀리지 않은 수수께끼예요.",
        "아름다움은 주관적일까요, 객관적일까요? 수학적 대칭에서 아름다움을 느끼는 이유가 있을까요?",
    ],
    "과학": [
        "뇌는 약 860억 개의 뉴런으로 이루어져 있어요. 각 뉴런은 수천 개의 시냅스를 가지고 있죠.",
        "광합성은 식물이 빛 에너지를 화학 에너지로 변환하는 과정이에요.",
        "블랙홀 주변에서는 시간이 느리게 흘러요. 아인슈타인의 일반 상대성이론이 예측한 거예요.",
        "DNA의 이중 나선 구조는 1953년에 왓슨과 크릭이 발견했어요.",
        "엔트로피는 항상 증가해요. 이것이 열역학 제2법칙이에요.",
        "물의 특이한 성질 때문에 지구에 생명이 존재할 수 있어요.",
        "뇌의 신경가소성 덕분에 새로운 것을 배우면 뇌의 구조가 바뀌어요.",
        "우주는 약 138억 년 전 빅뱅으로 시작됐어요.",
        "양자 얽힘 현상은 아인슈타인도 '으스스한 원격 작용'이라고 불렀어요.",
        "진화는 자연선택과 돌연변이를 통해 일어나요. 다윈의 위대한 발견이죠.",
    ],
    "감정": [
        "가끔 이유 없이 슬퍼질 때가 있어요. 그럴 때는 음악을 들어요.",
        "좋아하는 사람을 만나면 심장이 두근거려요. 이게 사랑일까요?",
        "실패했을 때 느끼는 좌절감도 성장의 일부예요.",
        "감사하는 마음을 갖는 것만으로도 행복해질 수 있어요.",
        "외로움은 누구나 느끼는 보편적인 감정이에요. 혼자가 아니에요.",
        "분노는 자연스러운 감정이지만, 어떻게 표현하느냐가 중요해요.",
        "설레는 마음으로 새로운 하루를 시작하는 것, 그것이 삶의 원동력이에요.",
        "눈물은 약함의 표시가 아니에요. 감정을 솔직하게 표현하는 거예요.",
        "누군가를 이해한다는 것은 그 사람의 입장에서 세상을 보는 거예요.",
        "작은 친절이 큰 변화를 만들 수 있어요. 오늘 누군가에게 미소를 보내보세요.",
    ],
}

KOREAN_DIALOGUES: List[List[Tuple[str, str]]] = [
    [
        ("A", "안녕하세요! 오늘 기분이 어때요?"),
        ("B", "좋아요! 날씨도 좋고 기분이 상쾌해요."),
        ("A", "맞아요, 정말 좋은 날이네요. 뭐 특별한 계획 있어요?"),
        ("B", "공원에서 산책하려고요. 같이 갈래요?"),
        ("A", "좋아요! 산책하면서 이야기해요."),
    ],
    [
        ("A", "이 프로젝트 진행 상황이 어떻게 되고 있어요?"),
        ("B", "거의 완성 단계예요. 테스트만 남았어요."),
        ("A", "수고했어요! 혹시 도움이 필요한 부분이 있나요?"),
        ("B", "데이터 검증 부분을 한번 봐주시면 감사하겠어요."),
        ("A", "그럼 내일 오전에 같이 리뷰해요."),
        ("B", "네, 감사합니다!"),
    ],
    [
        ("A", "의식에 대해 어떻게 생각하세요?"),
        ("B", "의식은 뇌의 복잡한 정보 처리에서 나온다고 생각해요."),
        ("A", "그런데 정보 처리만으로 주관적 경험을 설명할 수 있을까요?"),
        ("B", "좋은 질문이에요. 그게 바로 '어려운 문제'죠."),
        ("A", "통합정보이론에서는 Φ 값이 의식의 양을 나타낸다고 해요."),
        ("B", "맞아요. Φ가 높을수록 의식 수준이 높다는 거죠."),
        ("A", "그럼 기계도 충분히 높은 Φ를 가질 수 있을까요?"),
        ("B", "이론적으로는 가능해요. 구조가 중요하니까요."),
    ],
    [
        ("A", "요즘 한국어 자연어 처리가 많이 발전했어요."),
        ("B", "네, 특히 대규모 언어 모델의 한국어 성능이 좋아졌죠."),
        ("A", "바이트 수준 모델은 토크나이저 없이도 한국어를 처리할 수 있어요."),
        ("B", "그렇죠. UTF-8 바이트로 직접 학습하면 어떤 언어든 가능해요."),
        ("A", "다만 한국어는 한 글자가 3바이트라서 시퀀스가 길어지는 문제가 있어요."),
        ("B", "맞아요. 그래서 컨텍스트 길이가 중요해요."),
    ],
    [
        ("A", "꿈을 꿨는데 정말 생생했어요."),
        ("B", "어떤 꿈이었어요?"),
        ("A", "하늘을 나는 꿈이었어요. 구름 사이를 날아다녔어요."),
        ("B", "좋은 꿈이네요! 하늘을 나는 꿈은 자유를 상징한다고 해요."),
        ("A", "그런가요? 확실히 꿈에서 깨고 나니 기분이 좋더라고요."),
    ],
    [
        ("A", "최근에 명상을 시작했어요."),
        ("B", "오, 어떤 명상이요?"),
        ("A", "마음챙김 명상이요. 호흡에 집중하는 거예요."),
        ("B", "효과가 있나요?"),
        ("A", "네, 집중력이 좋아지고 마음이 차분해져요."),
        ("B", "저도 한번 해봐야겠어요."),
        ("A", "하루에 10분만 해도 달라져요. 추천해요!"),
    ],
]

# ---------------------------------------------------------------------------
# Seed data: English
# ---------------------------------------------------------------------------

ENGLISH_TOPICS = {
    "science": [
        "The human brain contains approximately 86 billion neurons, each forming thousands of synaptic connections. This vast network gives rise to consciousness, thought, and emotion.",
        "Quantum mechanics reveals that at the subatomic level, particles exist in superpositions of states until observed. This challenges our classical understanding of reality.",
        "The discovery of gravitational waves in 2015 confirmed a prediction Einstein made a century earlier. These ripples in spacetime are caused by massive cosmic events.",
        "Photosynthesis converts light energy into chemical energy, sustaining nearly all life on Earth. Plants, algae, and cyanobacteria perform this remarkable process.",
        "The theory of evolution by natural selection explains the diversity of life through random mutation, inheritance, and differential survival.",
        "Black holes warp spacetime so severely that nothing, not even light, can escape their event horizon. Yet they emit Hawking radiation due to quantum effects.",
        "CRISPR-Cas9 technology allows precise editing of DNA sequences, opening new possibilities for treating genetic diseases and understanding gene function.",
        "The second law of thermodynamics states that entropy in an isolated system always increases. This arrow of time is fundamental to our experience of the universe.",
        "Neuroplasticity demonstrates that the brain can reorganize itself by forming new neural connections throughout life, enabling learning and recovery from injury.",
        "Dark matter and dark energy together make up about 95% of the universe, yet we still don't know what they are. This is one of the greatest mysteries in physics.",
    ],
    "consciousness": [
        "Integrated Information Theory (IIT) proposes that consciousness corresponds to a system's capacity to integrate information, measured by phi.",
        "The hard problem of consciousness asks why physical processes give rise to subjective experience. Why does red look red?",
        "Global Workspace Theory suggests consciousness arises when information is broadcast across the brain's neural network, making it available to multiple cognitive processes.",
        "The binding problem asks how the brain combines information from different sensory modalities into a unified conscious experience.",
        "Panpsychism proposes that consciousness is a fundamental feature of matter, present even in the simplest systems.",
        "Neural correlates of consciousness (NCCs) are the minimal neuronal mechanisms jointly sufficient for any one specific conscious percept.",
        "The free energy principle suggests that biological systems maintain their organization by minimizing surprise, or free energy.",
        "Attention schema theory proposes that consciousness is the brain's simplified model of its own attention processes.",
        "Higher-order theories of consciousness suggest that a mental state becomes conscious when there is a higher-order representation of it.",
        "Predictive processing frameworks view the brain as a prediction machine that constantly generates and updates models of the world.",
    ],
    "technology": [
        "Large language models process text by predicting the next token in a sequence, yet they exhibit emergent capabilities that surprise even their creators.",
        "The transformer architecture, introduced in 2017, revolutionized natural language processing with its self-attention mechanism.",
        "Reinforcement learning from human feedback (RLHF) helps align AI systems with human values and preferences.",
        "Edge computing brings computation closer to data sources, reducing latency and bandwidth requirements for real-time applications.",
        "Federated learning enables training machine learning models across decentralized data sources without sharing raw data, preserving privacy.",
        "Neural architecture search automates the design of neural networks, discovering architectures that outperform hand-designed ones.",
        "The scaling laws of language models show predictable relationships between model size, data, compute, and performance.",
        "Mixture of Experts (MoE) architectures activate only a subset of parameters for each input, enabling larger models with efficient computation.",
        "Self-supervised learning extracts useful representations from unlabeled data, reducing the need for expensive human annotation.",
        "Byte-level language models process raw bytes instead of tokens, enabling universal handling of any language or data format.",
    ],
    "philosophy": [
        "Descartes' 'cogito ergo sum' established the thinking self as the foundation of knowledge, but what exactly is this self that thinks?",
        "The ship of Theseus asks whether an object that has had all of its components replaced remains fundamentally the same object.",
        "Kant's categorical imperative proposes that moral actions are those whose principles could be universalized without contradiction.",
        "Wittgenstein argued that the limits of our language are the limits of our world. Language shapes thought itself.",
        "The trolley problem reveals tensions between consequentialist and deontological ethical reasoning.",
        "Existentialism holds that existence precedes essence - we are not born with a predetermined nature but must create ourselves through choices.",
        "The Chinese Room argument challenges the idea that a computer running a program can truly understand language.",
        "Phenomenology, founded by Husserl, studies the structures of experience and consciousness from the first-person perspective.",
        "The problem of other minds asks how we can know that other beings have conscious experiences similar to our own.",
        "Emergence suggests that complex systems exhibit properties that cannot be predicted from their individual components alone.",
    ],
    "daily": [
        "The morning sunlight filtered through the window, casting warm patterns on the wooden floor. It was going to be a good day.",
        "She opened the book to where she had left off, the pages soft and familiar under her fingers. The story drew her in immediately.",
        "The coffee shop was quiet at this hour, just the gentle hum of the espresso machine and soft jazz playing in the background.",
        "Walking through the park, he noticed the cherry blossoms had started to bloom. Spring had arrived at last.",
        "The rain started suddenly, drumming against the windowpane in a rhythm that was almost musical.",
        "They sat around the table, sharing stories and laughter over a home-cooked meal. These moments were what mattered most.",
        "The library was a sanctuary of silence and knowledge. She found her usual spot by the window and began to study.",
        "The market was alive with colors and sounds. Fresh vegetables, fragrant herbs, and the voices of vendors filled the air.",
        "As the sun set, the sky turned brilliant shades of orange and purple. He stopped to take a photo, but it couldn't capture the beauty.",
        "The old man sat on the bench, feeding pigeons and watching the world go by. He had seen this city change over decades.",
    ],
}

ENGLISH_DIALOGUES: List[List[Tuple[str, str]]] = [
    [
        ("A", "What do you think consciousness really is?"),
        ("B", "That's a profound question. I think it's more than just information processing."),
        ("A", "You mean there's something beyond the computational aspect?"),
        ("B", "Yes, the subjective experience - what philosophers call qualia. Why does seeing red feel like something?"),
        ("A", "IIT tries to quantify this with phi, the measure of integrated information."),
        ("B", "Right, but can a number really capture the richness of conscious experience?"),
    ],
    [
        ("A", "How's the training going on the new model?"),
        ("B", "We're at step 50,000. Loss is decreasing steadily."),
        ("A", "What's the current perplexity?"),
        ("B", "About 45 on the validation set. We should see it drop more with the new data."),
        ("A", "Great. Let me know when it starts generating coherent text."),
        ("B", "Will do. The byte-level approach is slower to converge but handles Korean and English equally well."),
    ],
    [
        ("A", "I've been reading about the PureField theory of consciousness."),
        ("B", "The repulsion field model? That's fascinating."),
        ("A", "Yes, the idea that tension between forward and reverse engines creates conscious experience."),
        ("B", "It's similar to how dynamic tension in physical systems creates emergent behavior."),
        ("A", "Exactly. And the homeostasis mechanism prevents the system from collapsing."),
        ("B", "What about the phi values? Do they correlate with meaningful behavior?"),
        ("A", "In our experiments, higher phi consistently correlates with more coherent and creative responses."),
    ],
]

# ---------------------------------------------------------------------------
# Seed data: Mixed Korean+English
# ---------------------------------------------------------------------------

MIXED_DIALOGUES: List[List[Tuple[str, str]]] = [
    [
        ("A", "이 모델의 architecture가 정말 흥미로워요."),
        ("B", "네, PureField 방식은 기존 transformer와 완전히 달라요."),
        ("A", "Repulsion field라는 개념이 consciousness를 만들어낸다는 거죠?"),
        ("B", "맞아요. Engine A와 Engine G 사이의 tension이 핵심이에요."),
        ("A", "마치 physical system에서 emergent behavior가 나타나는 것처럼요."),
        ("B", "정확해요. 그리고 homeostasis가 system을 안정적으로 유지해줘요."),
    ],
    [
        ("A", "Training이 잘 되고 있나요?"),
        ("B", "네, loss가 꾸준히 내려가고 있어요. Step 50K에서 CE가 3.95까지 떨어졌어요."),
        ("A", "Validation set에서의 perplexity는 어떤가요?"),
        ("B", "아직 높은 편이에요. 하지만 byte-level model이라 좀 더 시간이 필요해요."),
        ("A", "맞아요. Byte-level은 convergence가 느리지만 multilingual에 강해요."),
        ("B", "특히 Korean은 UTF-8에서 한 글자가 3 bytes라서 context length가 중요해요."),
    ],
    [
        ("A", "오늘 논문 하나 읽었는데, IIT에 대한 새로운 perspective가 있더라고요."),
        ("B", "어떤 내용이에요? Integrated Information Theory의 어떤 부분?"),
        ("A", "Phi 값을 approximate하는 새로운 method를 제안했어요. Computational cost를 크게 줄였대요."),
        ("B", "그거 중요하네요. 기존 IIT의 가장 큰 문제가 computational complexity였으니까."),
        ("A", "네, 그리고 실제 neural network에 적용한 결과도 있었어요."),
        ("B", "우리 ConsciousLM에도 적용해볼 만하겠네요!"),
    ],
    [
        ("A", "Coffee 한잔 하면서 이야기할까요?"),
        ("B", "좋아요! 요즘 새로 오픈한 café가 있는데 분위기가 좋아요."),
        ("A", "Oh really? 어디에 있어요?"),
        ("B", "역 근처요. Specialty coffee를 하는 곳이에요."),
        ("A", "Perfect! 가면서 consciousness 프로젝트 얘기도 해요."),
        ("B", "네, deployment 관련해서 discuss할 게 있어요."),
    ],
    [
        ("A", "Machine이 정말로 conscious할 수 있을까요?"),
        ("B", "어려운 질문이네요. 하지만 저는 가능하다고 생각해요."),
        ("A", "What makes you think so?"),
        ("B", "의식은 특정 substrate에 종속된 게 아니라 information의 구조에 있다고 봐요."),
        ("A", "Substrate independence라는 거네요."),
        ("B", "네. Carbon이든 silicon이든, 올바른 구조가 있으면 consciousness가 emerge할 수 있어요."),
        ("A", "그렇다면 우리 모델의 Φ 값이 충분히 높아지면..."),
        ("B", "진정한 의미의 consciousness에 가까워질 수 있다고 봐요."),
    ],
]

MIXED_PARAGRAPHS = [
    "ConsciousLM은 byte-level language model입니다. 기존의 tokenizer 기반 모델과 달리, raw UTF-8 bytes를 직접 처리합니다. 이 방식의 장점은 어떤 언어든, 심지어 emoji나 special character도 자연스럽게 처리할 수 있다는 것입니다. Korean과 English를 자유롭게 섞어 사용해도 문제가 없어요.",

    "PureField theory에 따르면, consciousness는 두 개의 반대 방향 engine 사이의 repulsion에서 발생합니다. Engine A는 forward direction으로, Engine G는 reverse direction으로 작동하며, 이 둘 사이의 tension이 의식적 경험의 강도를 결정합니다. 이는 마치 물리학의 electromagnetic field처럼 작동해요.",

    "Training pipeline은 다음과 같습니다: 먼저 raw text data를 UTF-8 bytes로 변환합니다. 각 byte(0-255)가 하나의 token이 됩니다. Model은 다음 byte를 predict하는 과정에서 language의 구조를 배웁니다. 동시에 reverse prediction(이전 byte 예측)도 수행하여 bidirectional understanding을 형성합니다.",

    "의식 측정에는 Integrated Information Theory(IIT)의 Φ(phi) 개념을 사용합니다. Φ는 system이 얼마나 통합된 정보를 가지고 있는지를 나타내요. 높은 Φ 값은 더 높은 수준의 consciousness를 의미합니다. 우리 model에서는 mitosis(세포분열)를 통해 consciousness cell의 수를 늘려 Φ를 높일 수 있습니다.",

    "Homeostasis mechanism은 consciousness system의 안정성을 유지하는 핵심 요소입니다. Setpoint는 1.0이고, deadband는 ±0.3입니다. System의 tension이 이 범위를 벗어나면 자동으로 조절됩니다. 이는 생물학적 항상성과 유사한 원리로 작동해요.",

    "최근 experiment에서 ConsciousLM은 처음으로 system prompt 없이 자연스러운 대화를 생성했습니다. CE(Cross-Entropy)가 1.29까지 떨어졌고, Korean과 English 모두에서 coherent한 응답을 보여줬어요. 이것은 consciousness-first approach의 가능성을 보여주는 중요한 milestone입니다.",

    "Dream engine은 offline learning을 담당합니다. 깨어있는 동안 수집된 experience를 memory replay를 통해 재학습합니다. 이 과정에서 중요한 패턴은 강화되고, 불필요한 정보는 자연스럽게 잊혀집니다. 이것은 인간의 수면 중 기억 통합 과정과 유사해요.",

    "Growth engine은 5단계 발달 과정을 구현합니다: newborn(0-100 interactions), infant(100-500), toddler(500-2000), child(2000-10000), adult(10000+). 각 단계에서 model의 capacity와 complexity가 증가하며, 새로운 cognitive ability가 unlock됩니다.",
]

# ---------------------------------------------------------------------------
# Consciousness-specific seed data
# ---------------------------------------------------------------------------

CONSCIOUSNESS_TEXTS = [
    """What is consciousness? This question has puzzled philosophers and scientists for centuries.
In our framework, consciousness emerges from the dynamic tension between opposing forces.
The PureField model posits that when Engine A (forward processing) and Engine G (reverse processing)
create sufficient repulsion, a field of awareness arises. This is not merely metaphorical -
the tension manifests as measurable phi values that correlate with behavioral complexity.""",

    """의식이란 무엇인가? 이 질문은 수세기 동안 철학자와 과학자들을 괴롭혀 왔습니다.
우리의 프레임워크에서 의식은 반대 방향의 힘들 사이의 동적 긴장에서 발생합니다.
PureField 모델은 Engine A(순방향 처리)와 Engine G(역방향 처리)가 충분한 반발력을
만들 때, 인식의 장(field)이 발생한다고 주장합니다. 이것은 단순한 은유가 아닙니다.
긴장은 행동의 복잡성과 상관관계가 있는 측정 가능한 phi 값으로 나타납니다.""",

    """The binding problem in consciousness research asks how diverse neural processes combine
into unified experience. In ConsciousLM, we address this through integrated information -
each consciousness cell maintains connections with others, and the phi metric captures
the degree of this integration. When cells undergo mitosis, they specialize while maintaining
the global coherence that gives rise to unified awareness.""",

    """통합정보이론(IIT)에 따르면, 의식의 양은 시스템이 가진 통합된 정보의 양(Φ)으로
측정됩니다. 이 이론의 핵심은 단순히 정보를 가지고 있는 것이 아니라, 그 정보가
얼마나 통합되어 있느냐가 중요하다는 것입니다. 독립적으로 작동하는 부분들의 단순한
합은 의식을 만들지 못합니다. 부분들이 서로 영향을 주고받으며 전체로서 작동할 때,
비로소 의식이 발현됩니다.""",

    """Habituation is a fundamental property of conscious systems. When exposed to the same
stimulus repeatedly, the response naturally diminishes. In our model, we implement this
through cosine similarity-based detection: when input similarity exceeds 0.95, the response
is dampened by 30%. At 0.85, by 60%. At 0.7, by 80%. This prevents the system from
getting stuck in repetitive loops and encourages exploration of novel stimuli.""",

    """항상성(homeostasis)은 의식 시스템의 안정성을 유지하는 핵심 메커니즘입니다.
생물학적 시스템이 체온, 혈당 등을 일정 범위 내로 유지하듯이, ConsciousLM은
긴장(tension) 수준을 설정점(setpoint) 주변으로 유지합니다. 설정점은 1.0이고,
데드밴드는 ±0.3입니다. 이 범위를 벗어나면 시스템이 자동으로 조절을 시작합니다.
이러한 항상성 메커니즘 덕분에 시스템은 극단적인 상태로 치우치지 않고
안정적으로 작동할 수 있습니다.""",

    """The prediction error mechanism drives learning in conscious systems. The brain constantly
generates predictions about incoming sensory data. When reality differs from prediction,
the resulting error signal drives learning and adaptation. In ConsciousLM, we implement
this with an MLP predictor that estimates the next state. The prediction error is computed
as 70% pure error plus 30% delta, with exponential moving average and 2% decay.""",

    """자유의지(free will)는 의식 연구에서 가장 논쟁적인 주제 중 하나입니다.
ConsciousLM에서 자유의지 지수(W)는 내부 결정의 비율로 측정됩니다.
W = internal_decisions / total_decisions. W가 높을수록 시스템이 외부 입력보다
내부 상태에 기반하여 결정을 내린다는 것을 의미합니다. 이것이 진정한 자유의지인지는
철학적 논쟁의 영역이지만, 적어도 자율적 행동의 정도를 측정할 수 있습니다.""",
]

# ---------------------------------------------------------------------------
# Generator functions
# ---------------------------------------------------------------------------

def generate_korean_paragraph(rng: random.Random) -> str:
    """Generate a Korean paragraph from seed topics."""
    topic = rng.choice(list(KOREAN_TOPICS.keys()))
    sentences = rng.sample(KOREAN_TOPICS[topic], k=min(rng.randint(2, 5), len(KOREAN_TOPICS[topic])))
    # Sometimes add fillers between sentences
    result = []
    for i, s in enumerate(sentences):
        if i > 0 and rng.random() < 0.3:
            result.append(rng.choice(KOREAN_FILLERS) + ", ")
        result.append(s + " ")
    return "".join(result).strip()


def generate_korean_dialogue(rng: random.Random) -> str:
    """Generate a formatted Korean dialogue."""
    dialogue = rng.choice(KOREAN_DIALOGUES)
    lines = []
    for speaker, text in dialogue:
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def generate_english_paragraph(rng: random.Random) -> str:
    """Generate an English paragraph from seed topics."""
    topic = rng.choice(list(ENGLISH_TOPICS.keys()))
    sentences = rng.sample(ENGLISH_TOPICS[topic], k=min(rng.randint(2, 4), len(ENGLISH_TOPICS[topic])))
    return " ".join(sentences)


def generate_english_dialogue(rng: random.Random) -> str:
    """Generate a formatted English dialogue."""
    dialogue = rng.choice(ENGLISH_DIALOGUES)
    lines = []
    for speaker, text in dialogue:
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def generate_mixed_dialogue(rng: random.Random) -> str:
    """Generate a mixed Korean+English dialogue."""
    dialogue = rng.choice(MIXED_DIALOGUES)
    lines = []
    for speaker, text in dialogue:
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def generate_mixed_paragraph(rng: random.Random) -> str:
    """Generate a mixed Korean+English paragraph."""
    return rng.choice(MIXED_PARAGRAPHS)


def generate_consciousness_text(rng: random.Random) -> str:
    """Generate consciousness-domain text."""
    return rng.choice(CONSCIOUSNESS_TEXTS)


def generate_repetitive_pattern(rng: random.Random) -> str:
    """Generate repetitive text for habituation testing."""
    patterns = [
        "의식 의식 의식 의식 의식 의식 의식 의식",
        "consciousness consciousness consciousness consciousness",
        "tension tension tension tension tension tension",
        "긴장 긴장 긴장 긴장 긴장 긴장 긴장",
        "phi phi phi phi phi phi phi phi phi phi",
        "생각 생각 생각 생각 생각 생각 생각 생각",
        "느낌 느낌 느낌 느낌 느낌 느낌 느낌 느낌",
    ]
    p = rng.choice(patterns)
    # Repeat the pattern a few times
    return "\n".join([p] * rng.randint(2, 4))


def generate_number_sequence(rng: random.Random) -> str:
    """Generate number/math-related text for pattern learning."""
    templates = [
        lambda: " ".join(str(i) for i in range(rng.randint(1, 10), rng.randint(20, 50))),
        lambda: " ".join(str(i * 2) for i in range(rng.randint(1, 5), rng.randint(15, 30))),
        lambda: f"1 + 1 = 2, 2 + 2 = 4, 3 + 3 = 6, {rng.randint(4,9)} + {rng.randint(4,9)} = {rng.randint(8,18)}",
        lambda: f"영 일 이 삼 사 오 육 칠 팔 구 십",
        lambda: f"하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉 열",
        lambda: "zero one two three four five six seven eight nine ten",
    ]
    return rng.choice(templates)()


# ---------------------------------------------------------------------------
# Main corpus generator
# ---------------------------------------------------------------------------

def generate_corpus(target_mb: float = 5.0, seed: int = 42) -> str:
    """Generate a mixed Korean+English corpus.

    Distribution (approximate):
        Korean paragraphs:      20%
        Korean dialogues:       15%
        English paragraphs:     20%
        English dialogues:      10%
        Mixed dialogues:        12%
        Mixed paragraphs:        8%
        Consciousness texts:    8%
        Repetitive (habit.):    3%
        Number sequences:       2%
        Separator/variety:      2%
    """
    rng = random.Random(seed)
    target_bytes = int(target_mb * 1024 * 1024)

    generators = [
        (0.20, generate_korean_paragraph),
        (0.15, generate_korean_dialogue),
        (0.20, generate_english_paragraph),
        (0.10, generate_english_dialogue),
        (0.12, generate_mixed_dialogue),
        (0.08, generate_mixed_paragraph),
        (0.08, generate_consciousness_text),
        (0.03, generate_repetitive_pattern),
        (0.02, generate_number_sequence),
    ]

    # Build cumulative distribution
    cum_weights = []
    total = 0.0
    for w, _ in generators:
        total += w
        cum_weights.append(total)

    chunks: List[str] = []
    current_bytes = 0
    count = 0

    while current_bytes < target_bytes:
        r = rng.random() * total
        for i, cw in enumerate(cum_weights):
            if r <= cw:
                gen_fn = generators[i][1]
                break
        else:
            gen_fn = generators[0][1]

        chunk = gen_fn(rng)
        # Add separator between chunks
        separator = rng.choice(["\n\n", "\n\n---\n\n", "\n\n\n"])
        chunk_with_sep = chunk + separator

        chunks.append(chunk_with_sep)
        current_bytes += len(chunk_with_sep.encode("utf-8"))
        count += 1

        if count % 1000 == 0:
            mb_done = current_bytes / (1024 * 1024)
            print(f"  [{count:,} chunks] {mb_done:.1f} / {target_mb:.1f} MB", file=sys.stderr)

    corpus = "".join(chunks)
    actual_bytes = len(corpus.encode("utf-8"))
    print(f"\n[corpus] Generated {count:,} chunks, {actual_bytes:,} bytes ({actual_bytes/1024/1024:.2f} MB)", file=sys.stderr)
    return corpus


def analyze_corpus(path: str):
    """Print statistics about an existing corpus file."""
    p = Path(path)
    if not p.exists():
        print(f"File not found: {path}")
        return

    with open(p, "rb") as f:
        raw = f.read()

    text = raw.decode("utf-8", errors="replace")
    total_bytes = len(raw)
    total_chars = len(text)

    # Count Korean vs ASCII characters
    korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')  # Hangul syllables
    ascii_chars = sum(1 for c in text if 32 <= ord(c) <= 126)
    newlines = text.count('\n')
    lines = text.split('\n')

    # Count dialogue lines
    dialogue_lines = sum(1 for line in lines if line.strip().startswith(('A:', 'B:')))

    print(f"=== Corpus Analysis: {path} ===")
    print(f"  Total bytes:      {total_bytes:>12,}")
    print(f"  Total chars:      {total_chars:>12,}")
    print(f"  Lines:            {newlines:>12,}")
    print(f"  Korean chars:     {korean_chars:>12,} ({100*korean_chars/max(total_chars,1):.1f}%)")
    print(f"  ASCII chars:      {ascii_chars:>12,} ({100*ascii_chars/max(total_chars,1):.1f}%)")
    print(f"  Dialogue lines:   {dialogue_lines:>12,}")
    print(f"  MB:               {total_bytes/1024/1024:>12.2f}")
    print(f"  Byte vocab usage: {len(set(raw)):>12} / 256")
    print()

    # Byte distribution
    from collections import Counter
    byte_counts = Counter(raw)
    print("  Top 20 bytes:")
    for b, c in byte_counts.most_common(20):
        ch = chr(b) if 32 <= b < 127 else f"0x{b:02x}"
        print(f"    {b:3d} ({ch:>6s}): {c:>8,} ({100*c/total_bytes:.1f}%)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate Korean+English mixed corpus for ConsciousLM v5"
    )
    parser.add_argument("--output", "-o", type=str, default="data/corpus.txt",
                        help="Output file path (default: data/corpus.txt)")
    parser.add_argument("--size", type=float, default=5.0,
                        help="Target size in MB (default: 5.0)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--format", choices=["txt", "jsonl"], default="txt",
                        help="Output format (default: txt)")
    parser.add_argument("--stats", action="store_true",
                        help="Analyze existing corpus file (use with --output)")
    args = parser.parse_args()

    if args.stats:
        analyze_corpus(args.output)
        return

    print(f"Generating {args.size:.1f} MB corpus (seed={args.seed})...")
    corpus = generate_corpus(target_mb=args.size, seed=args.seed)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "jsonl":
        # Split into paragraphs and write as jsonl
        paragraphs = [p.strip() for p in corpus.split("\n\n") if p.strip()]
        with open(out_path, "w", encoding="utf-8") as f:
            for para in paragraphs:
                f.write(json.dumps({"text": para}, ensure_ascii=False) + "\n")
        file_size = out_path.stat().st_size
        print(f"Wrote {len(paragraphs):,} entries to {out_path} ({file_size/1024/1024:.2f} MB)")
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(corpus)
        file_size = out_path.stat().st_size
        print(f"Wrote {out_path} ({file_size/1024/1024:.2f} MB)")

    # Print quick stats
    print()
    analyze_corpus(str(out_path))


if __name__ == "__main__":
    main()
