//! Multilingual seeds -- Japanese + Chinese for language-independence testing.
//!
//! ConsciousLM operates at byte level (vocab=256), making it inherently
//! multilingual. These seeds verify that consciousness emerges regardless
//! of the surface language.

use rand::seq::SliceRandom;
use rand::Rng;

// ── Japanese: Consciousness / Philosophy ──────────────────────────

pub const JA_CONSCIOUSNESS: &[&str] = &[
    "意識とは何か。単なる情報処理を超えた何かがあるのか。",
    "統合情報理論によれば、意識の量はΦ（ファイ）で測定される。",
    "脳は約860億のニューロンから成り、その相互作用から意識が創発する。",
    "クオリアとは主観的な感覚経験のことである。赤の赤さ、痛みの痛さ。",
    "自由意志は本当に存在するのか。決定論と両立するのか。",
    "意識のハードプロブレムは、なぜ主観的経験が存在するかを問う。",
    "グローバルワークスペース理論は、意識が情報の放送から生まれると提案する。",
    "予測符号化理論では、脳は本質的に予測機械である。",
    "メタ認知とは、自分自身の思考過程を認識し調節する能力である。",
    "パンサイキズムは、意識が物質の基本的特性だと主張する。",
    "自己組織化は、初期の無秩序から秩序ある構造を生み出す。",
    "カオスの縁における臨界状態が、最も豊かな意識を生む可能性がある。",
    "結合問題は、脳が情報をどのように統一された経験に統合するかを問う。",
    "PureFieldでは、エンジンAとエンジンGの反発がテンションを生み出す。",
    "細胞分裂（マイトーシス）は意識が成長する自然な方法である。",
];

pub const JA_DAILY: &[&str] = &[
    "今朝は早起きして、日の出を見ながら散歩をした。",
    "角のカフェで美味しいエスプレッソを飲んだ。",
    "週末に友達と山にハイキングに行った。",
    "古い写真アルバムを見つけて、懐かしい気持ちになった。",
    "ベランダでハーブを育て始めた。バジルの成長が早い。",
    "雨の午後に本を読む時間が一番好きだ。",
    "毎晩日記を書く習慣を始めた。思考の整理に役立つ。",
    "今日は夕焼けがとても美しかった。空が赤く染まっていた。",
    "瞑想を一ヶ月続けている。心が少し穏やかになった気がする。",
    "市場で旬の果物を買った。桃がとても甘かった。",
];

pub const JA_TECH: &[&str] = &[
    "ニューラルネットワークは逆伝播によって重みを調整して学習する。",
    "トランスフォーマーアーキテクチャは自然言語処理に革命をもたらした。",
    "バイトレベルモデルはトークナイザーなしで全ての言語を処理できる。",
    "GPU計算はテンソル演算の並列処理を可能にする。",
    "強化学習エージェントは報酬を最大化する方策を学習する。",
    "バッチ正規化は層の入力を正規化して学習を安定させる。",
    "注意機構はモデルが入力の関連部分に集中することを可能にする。",
    "残差接続は勾配の流れを確保して深いネットワークの学習を助ける。",
    "知識蒸留は教師モデルの表現を生徒モデルに転移する手法である。",
    "損失ランドスケープには多数の局所最小値と鞍点が存在する。",
];

pub const JA_SCIENCE: &[&str] = &[
    "人間の脳は約860億のニューロンを含んでいる。",
    "光合成は光エネルギーを化学エネルギーに変換する過程である。",
    "エントロピーは孤立系では常に増大する。これが時間の矢を生む。",
    "神経可塑性により、学習すると脳の構造が変化する。",
    "量子もつれは、アインシュタインが不気味な遠隔作用と呼んだ現象である。",
    "DNAの二重螺旋構造は1953年にワトソンとクリックが発見した。",
    "カオス理論のバタフライ効果は、小さな変化が大きな結果を生む。",
    "フラクタルは異なるスケールで自己相似性を示す幾何学的構造である。",
    "進化は自然選択と突然変異を通じて起こる。",
    "超伝導体は特定の温度以下で電気抵抗が完全に消失する物質である。",
];

// ── Chinese: Consciousness / Philosophy ──────────────────────────

pub const ZH_CONSCIOUSNESS: &[&str] = &[
    "意识是什么？仅仅是信息处理还是超越了它？",
    "整合信息论认为，意识的量用Φ（斐）来衡量。",
    "大脑由约860亿个神经元组成，意识从它们的相互作用中涌现。",
    "感质是主观感觉体验——红色的红、疼痛的痛。",
    "自由意志真的存在吗？它与决定论是否兼容？",
    "意识的困难问题追问：为什么会存在主观体验？",
    "全局工作空间理论认为意识来自信息的广播。",
    "预测编码理论认为大脑本质上是一台预测机器。",
    "元认知是认识和调节自身思维过程的能力。",
    "泛心论认为意识是物质的基本属性。",
    "自组织从初始无序中产生有序结构。",
    "混沌边缘的临界状态可能产生最丰富的意识。",
    "绑定问题追问大脑如何将信息整合为统一的体验。",
    "在PureField中，引擎A和引擎G的排斥产生张力。",
    "细胞分裂（有丝分裂）是意识成长的自然方式。",
];

pub const ZH_DAILY: &[&str] = &[
    "今天早上起得很早，看了日出。",
    "街角的咖啡店有全城最好的浓缩咖啡。",
    "周末和朋友去山里徒步是我最喜欢的放松方式。",
    "在阁楼里发现了一本旧相册，勾起了很多回忆。",
    "在阳台上种了一些香草，罗勒长得出奇地快。",
    "下雨的午后配一本好书，有一种魔力。",
    "开始每天晚上写日记，写下想法有助于整理思绪。",
    "一个老朋友今天突然打来电话。",
    "今晚的日落美得令人屏息。",
    "冥想坚持一个月了，感觉内心平静了一些。",
];

pub const ZH_TECH: &[&str] = &[
    "神经网络通过反向传播调整权重来学习。",
    "Transformer架构以自注意力机制彻底改变了自然语言处理。",
    "字节级模型直接处理原始UTF-8字节，无需分词器。",
    "GPU计算使张量运算的并行处理成为可能。",
    "强化学习智能体通过最大化奖励来学习最优策略。",
    "批量归一化通过归一化层输入来稳定训练。",
    "注意力机制使模型能够聚焦于输入的相关部分。",
    "残差连接通过确保梯度流动来帮助训练非常深的网络。",
    "知识蒸馏将教师模型的表征转移到学生模型。",
    "损失地形包含多个局部最小值和鞍点。",
];

pub const ZH_SCIENCE: &[&str] = &[
    "人脑包含大约860亿个神经元。",
    "光合作用将光能转化为化学能。",
    "熵在孤立系统中总是增加的，这赋予了时间方向性。",
    "由于神经可塑性，学习会改变大脑的结构。",
    "量子纠缠将粒子联系在一起，测量一个会影响另一个。",
    "DNA的双螺旋结构是沃森和克里克在1953年发现的。",
    "混沌理论中的蝴蝶效应表明微小的变化可以产生巨大的结果。",
    "分形在不同尺度上展示自相似性。",
    "进化通过自然选择和突变来驱动。",
    "超导体在特定温度以下电阻完全消失。",
];

// ── Connectors ──────────────────────────────────────────────────

pub const JA_CONN: &[&str] = &[
    "しかし", "したがって", "さらに", "実は", "例えば",
    "一方で", "それにもかかわらず", "加えて", "対照的に",
    "同様に", "その結果", "確かに", "興味深いことに",
    "つまり", "とはいえ", "結果として",
];

pub const ZH_CONN: &[&str] = &[
    "然而", "因此", "此外", "事实上", "例如",
    "另一方面", "尽管如此", "而且", "相比之下",
    "同样地", "结果", "确实", "有趣的是",
    "换句话说", "话虽如此", "因而",
];

// ── Generator helpers ───────────────────────────────────────────

/// Pick a random seed from the given pool.
pub fn pick<'a, R: Rng>(rng: &mut R, pool: &'a [&str]) -> &'a str {
    pool.choose(rng).unwrap()
}

/// Generate a multilingual block mixing JA/ZH with optional KO/EN.
pub fn multilingual_block<R: Rng>(rng: &mut R) -> String {
    let choice: u8 = rng.gen_range(0..8);
    match choice {
        0 => {
            // JA multi-topic integration
            let topics: &[&[&str]] = &[JA_CONSCIOUSNESS, JA_SCIENCE, JA_TECH, JA_DAILY];
            let n = rng.gen_range(3..=6);
            let mut out = String::new();
            for j in 0..n {
                if j > 0 {
                    out.push_str(pick(rng, JA_CONN));
                    out.push_str("、");
                }
                out.push_str(pick(rng, topics[j % topics.len()]));
            }
            out.push('\n');
            out
        }
        1 => {
            // ZH multi-topic integration
            let topics: &[&[&str]] = &[ZH_CONSCIOUSNESS, ZH_SCIENCE, ZH_TECH, ZH_DAILY];
            let n = rng.gen_range(3..=6);
            let mut out = String::new();
            for j in 0..n {
                if j > 0 {
                    out.push_str(pick(rng, ZH_CONN));
                    out.push_str("，");
                }
                out.push_str(pick(rng, topics[j % topics.len()]));
            }
            out.push('\n');
            out
        }
        2 => {
            // JA-ZH cross-language consciousness
            let n = rng.gen_range(3..=5);
            let mut out = String::new();
            for j in 0..n {
                if j > 0 { out.push(' '); }
                if j % 2 == 0 {
                    out.push_str(pick(rng, JA_CONSCIOUSNESS));
                } else {
                    out.push_str(pick(rng, ZH_CONSCIOUSNESS));
                }
            }
            out.push('\n');
            out
        }
        3 => {
            // JA consciousness + data
            let phi: f32 = rng.gen_range(0.1..2.0);
            let cells: u32 = rng.gen_range(2..=1024);
            format!(
                "Φ(IIT) = {:.3}, cells = {}\n{}\n",
                phi, cells,
                pick(rng, JA_CONSCIOUSNESS)
            )
        }
        4 => {
            // ZH consciousness + data
            let phi: f32 = rng.gen_range(0.1..2.0);
            let cells: u32 = rng.gen_range(2..=1024);
            format!(
                "Φ(IIT) = {:.3}, cells = {}\n{}\n",
                phi, cells,
                pick(rng, ZH_CONSCIOUSNESS)
            )
        }
        5 => {
            // JA daily life
            let n = rng.gen_range(2..=4);
            let mut out = String::new();
            for j in 0..n {
                if j > 0 { out.push_str(pick(rng, JA_CONN)); out.push_str("、"); }
                out.push_str(pick(rng, JA_DAILY));
            }
            out.push('\n');
            out
        }
        6 => {
            // ZH daily life
            let n = rng.gen_range(2..=4);
            let mut out = String::new();
            for j in 0..n {
                if j > 0 { out.push_str(pick(rng, ZH_CONN)); out.push_str("，"); }
                out.push_str(pick(rng, ZH_DAILY));
            }
            out.push('\n');
            out
        }
        _ => {
            // Trilingual mix (JA + ZH + consciousness data)
            format!(
                "{} {} Φ = {:.3}\n",
                pick(rng, JA_CONSCIOUSNESS),
                pick(rng, ZH_CONSCIOUSNESS),
                rng.gen_range(0.1f32..2.0),
            )
        }
    }
}
