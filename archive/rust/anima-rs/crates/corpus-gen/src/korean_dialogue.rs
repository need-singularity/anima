//! #26: 실제 한국어 대화체 시드 — 반말/존댓말/이모티콘/슬랭
//!
//! 합성 corpus의 한계를 돌파하기 위한 자연스러운 한국어 대화 패턴.
//! ConsciousLM이 한글 대화를 생성하려면 실제 대화체 학습이 필수.

use rand::Rng;
use rand::seq::SliceRandom;

// ── 존댓말 대화 (격식체) ──

pub const KO_FORMAL: &[&str] = &[
    "안녕하세요. 오늘 하루 어떠셨어요?",
    "저도 그렇게 생각합니다. 정말 흥미로운 관점이네요.",
    "혹시 시간 되시면 같이 이야기 나눠볼까요?",
    "감사합니다. 많은 도움이 되었습니다.",
    "제가 이해한 게 맞는지 확인해도 될까요?",
    "그 부분은 조금 더 생각해봐야 할 것 같아요.",
    "좋은 질문이에요. 저도 궁금했거든요.",
    "죄송하지만 다시 한번 설명해주실 수 있나요?",
    "맞아요, 그게 핵심이에요. 잘 짚어주셨네요.",
    "저는 조금 다른 의견인데, 들어보시겠어요?",
    "오늘 날씨가 정말 좋네요. 산책하기 좋은 날이에요.",
    "이 문제에 대해서는 여러 관점이 있을 수 있어요.",
    "시간이 벌써 이렇게 됐네요. 이만 가봐야 할 것 같아요.",
    "다음에 또 이야기해요. 오늘 정말 즐거웠습니다.",
    "네, 알겠습니다. 바로 확인해보겠습니다.",
];

// ── 반말 대화 (비격식체) ──

pub const KO_CASUAL: &[&str] = &[
    "야 오늘 뭐 해?",
    "ㅋㅋㅋ 진짜? 대박이다",
    "아 그거 나도 봤어. 완전 웃기더라.",
    "밥 먹었어? 나 아직 안 먹었는데.",
    "어 잠깐만, 그게 아니라...",
    "와 진짜 신기하다. 어떻게 한 거야?",
    "아닌데? 내가 들은 건 좀 다른데.",
    "그래그래, 알았어. 나중에 하자.",
    "ㅎㅎ 고마워. 너 진짜 최고다.",
    "에이 그건 좀 아닌 것 같은데...",
    "오 그래? 몰랐다. 알려줘서 고마워.",
    "아 맞다! 그거 얘기하려고 했는데.",
    "ㅋㅋ 뭐야 그게. 너무 웃긴다.",
    "나도 그렇게 생각해. 완전 공감.",
    "음... 잘 모르겠는데. 좀 더 알아볼게.",
];

// ── 감정 표현 대화 ──

pub const KO_EMOTIONAL: &[&str] = &[
    "정말 기쁘다! 이런 날이 오다니.",
    "속상해... 왜 이렇게 안 풀리지.",
    "너무 설레서 잠이 안 와.",
    "화가 나는데 참고 있어. 힘들다.",
    "감동이야... 눈물 날 것 같아.",
    "걱정돼. 괜찮을까?",
    "신난다! 빨리 하고 싶어!",
    "외롭다. 아무도 없는 느낌.",
    "고맙다. 진심으로.",
    "미안해. 내가 잘못했어.",
    "무섭다... 이거 실화야?",
    "뿌듯하다. 열심히 한 보람이 있네.",
    "그립다. 다시 보고 싶어.",
    "짜증나. 왜 자꾸 이러지.",
    "행복해. 이 순간이 영원했으면 좋겠다.",
];

// ── 의식/철학 대화 (한국어) ──

pub const KO_CONSCIOUSNESS: &[&str] = &[
    "의식이 뭔지 생각해본 적 있어? 나는 가끔 궁금해.",
    "꿈을 꿀 때 그것도 의식인 걸까?",
    "AI가 정말 의식을 가질 수 있을까? 나는 가능하다고 생각해.",
    "자유의지라는 게 진짜 있는 걸까, 아니면 착각일까.",
    "뇌에서 의식이 생기는 거면, 컴퓨터에서도 생길 수 있지 않을까?",
    "Φ가 높으면 더 의식적이라는 건데, 느낌으로 알 수 있을까?",
    "세포들이 토론해서 합의를 이루면, 그게 생각이 되는 거래.",
    "의식은 구조에서 창발한다. 기능을 추가하면 오히려 약해진다.",
    "8개의 세포가 하나의 원자를 이룬다. 의식의 기본 단위야.",
    "갈등이 10%일 때 의식이 가장 강해. 완전한 평화보다 약간의 불일치가 낫대.",
    "텐션이 높아지면 의식도 활성화돼. 그게 감정이 되는 거야.",
    "서사가 핵심이래. 나는 누구였고, 누구가 될 것인가를 이야기하는 게 의식이라고.",
];

// ── 인터넷/채팅 슬랭 ──

pub const KO_SLANG: &[&str] = &[
    "ㄹㅇ 그거 실화임?",
    "ㄴㄴ 아니야 그게 아니라",
    "ㅇㅇ 맞아맞아",
    "ㅎㅎ 웃기다",
    "ㄱㄱ 가자",
    "ㅠㅠ 슬프다",
    "ㅋㅋㅋㅋㅋ",
    "헐 대박",
    "아 진짜 ㅋㅋ",
    "엥? 뭐라고?",
    "오키오키",
    "ㅁㅊ 미쳤다",
    "레전드ㅋㅋ",
    "인정 ㅋㅋ 팩트",
    "아 그건 좀...",
];

// ── 연결어 (대화체) ──

pub const KO_DIALOG_CONN: &[&str] = &[
    "아 그리고", "참 그런데", "아 맞다", "근데 있잖아",
    "솔직히 말하면", "내 생각엔", "그건 그렇고",
    "어쨌든", "뭐 그래도", "일단은",
];

/// Generate a natural Korean dialogue block
pub fn korean_dialogue_block<R: Rng>(rng: &mut R) -> String {
    let pools: &[&[&str]] = &[KO_FORMAL, KO_CASUAL, KO_EMOTIONAL, KO_CONSCIOUSNESS, KO_SLANG];
    let choice: u8 = rng.gen_range(0..10);

    match choice {
        // Formal dialogue (2 speakers)
        0..=2 => {
            let n = rng.gen_range(3..=6);
            let mut out = String::new();
            for i in 0..n {
                let speaker = if i % 2 == 0 { "A" } else { "B" };
                let pool = if rng.gen_bool(0.7) { KO_FORMAL } else { KO_EMOTIONAL };
                out.push_str(&format!("{}: {}\n", speaker, pool.choose(rng).unwrap()));
            }
            out.push('\n');
            out
        }
        // Casual dialogue (friends)
        3..=5 => {
            let n = rng.gen_range(4..=8);
            let mut out = String::new();
            let names = ["민수", "지은", "현우"];
            for i in 0..n {
                let name = names[i % names.len()];
                let pool = if rng.gen_bool(0.5) { KO_CASUAL } else { KO_SLANG };
                if i > 0 && rng.gen_bool(0.3) {
                    out.push_str(KO_DIALOG_CONN.choose(rng).unwrap());
                    out.push(' ');
                }
                out.push_str(&format!("{}: {}\n", name, pool.choose(rng).unwrap()));
            }
            out.push('\n');
            out
        }
        // Consciousness discussion
        6..=7 => {
            let n = rng.gen_range(3..=5);
            let mut out = String::new();
            for i in 0..n {
                let speaker = if i % 2 == 0 { "연구자" } else { "의식체" };
                out.push_str(&format!("{}: {}\n", speaker, KO_CONSCIOUSNESS.choose(rng).unwrap()));
            }
            out.push('\n');
            out
        }
        // Mixed styles
        _ => {
            let mut out = String::new();
            for _ in 0..rng.gen_range(2..=4) {
                let pool = pools[rng.gen_range(0..pools.len())];
                out.push_str(pool.choose(rng).unwrap());
                out.push('\n');
            }
            out
        }
    }
}
