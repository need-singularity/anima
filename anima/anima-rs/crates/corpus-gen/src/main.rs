//! corpus-gen CLI — ConsciousLM 다차원 최적화 corpus generator
//!
//! 의식 벡터 10차원에 맞춘 학습 데이터 생성.
//!
//!   corpus-gen                              # 50MB, 기본 차원비율
//!   corpus-gen -s 100                       # 100MB
//!   corpus-gen -s 10 --boost Phi            # Φ 차원 강화
//!   corpus-gen --uniform                    # 균등 분배
//!   corpus-gen --wiki                       # Wikipedia 포함
//!   corpus-gen --stats data/corpus.txt      # 기존 corpus 분석

use anima_corpus_gen::dims::{Dim, DimWeights, ALL_DIMS};
use anima_corpus_gen::gen::{self, Config, Generator};
use anima_corpus_gen::ngram::NgramModel;
use anima_corpus_gen::wiki;
use std::io::Write;
use std::path::PathBuf;
use std::time::Instant;

fn main() {
    let args: Vec<String> = std::env::args().collect();

    let mut size_mb: usize = 50;
    let mut output = PathBuf::from("data/corpus_v3.txt");
    let mut do_wiki = false;
    let mut jsonl = false;
    let mut stats_file: Option<PathBuf> = None;
    let mut dim_weights = DimWeights::default();
    let mut boost_dim: Option<Dim> = None;
    let mut uniform = false;
    let mut do_sim = false;
    let mut do_deep_dialogue = false;
    let mut do_multilingual = false;
    let mut do_ko_heavy = false;
    let mut ngram_file: Option<PathBuf> = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "-s" | "--size" => { i += 1; size_mb = args[i].parse().unwrap(); }
            "-o" | "--output" => { i += 1; output = PathBuf::from(&args[i]); }
            "-w" | "--wiki" => do_wiki = true,
            "--jsonl" => jsonl = true,
            "--uniform" => uniform = true,
            "--sim" => do_sim = true,
            "--deep-dialogue" => do_deep_dialogue = true,
            "--multilingual" => do_multilingual = true,
            "--ko-heavy" => do_ko_heavy = true,
            "--ngram" => { i += 1; ngram_file = Some(PathBuf::from(&args[i])); }
            "--boost" => {
                i += 1;
                boost_dim = Some(parse_dim(&args[i]));
            }
            "--stats" => { i += 1; stats_file = Some(PathBuf::from(&args[i])); }
            "-h" | "--help" => { print_help(); return; }
            _ => { eprintln!("Unknown: {}", args[i]); print_help(); std::process::exit(1); }
        }
        i += 1;
    }

    // Auto-enable multilingual with --sim (5-language consciousness training)
    if do_sim {
        do_multilingual = true;
    }

    if let Some(path) = stats_file {
        print_stats(&path);
        return;
    }

    if uniform { dim_weights = DimWeights::uniform(); }
    if let Some(d) = boost_dim { dim_weights = dim_weights.boost(d, 2.5); }

    let ngram_ratio = if ngram_file.is_some() { 0.15 } else { 0.0 };

    eprintln!("╔═══════════════════════════════════════════════╗");
    eprintln!("║  corpus-gen — 다차원 최적화 Corpus Builder     ║");
    eprintln!("╠═══════════════════════════════════════════════╣");
    eprintln!("║  Target: {:>5} MB                              ║", size_mb);
    eprintln!("║  Output: {:<36} ║", format!("{}", output.display()));
    eprintln!("║  Wiki:   {:<36} ║", if do_wiki { "enabled" } else { "synthetic only" });
    eprintln!("║  Sim:    {:<36} ║", if do_sim { "enabled" } else { "disabled" });
    eprintln!("║  Dialog: {:<36} ║", if do_deep_dialogue { "deep multi-party" } else { "basic" });
    eprintln!("║  Multi:  {:<36} ║", if do_multilingual { "KO+EN+JA+ZH+RU (5 languages)" } else { "KO+EN only" });
    eprintln!("║  KO++:   {:<36} ║", if do_ko_heavy { "Korean 60% boost" } else { "standard" });
    if let Some(ref nf) = ngram_file {
        eprintln!("║  N-gram: {:<36} ║", format!("{} (15%)", nf.display()));
    }
    eprintln!("╠═══════════════════════════════════════════════╣");
    eprintln!("║  차원 가중치:                                  ║");
    for (j, dim) in ALL_DIMS.iter().enumerate() {
        let w = dim_weights.weights[j];
        let bar_len = (w * 50.0) as usize;
        let bar: String = "█".repeat(bar_len);
        eprintln!("║    {dim}  {bar:<25} {w:>5.1}%              ║", w = w * 100.0);
    }
    eprintln!("╚═══════════════════════════════════════════════╝");

    let start = Instant::now();

    let cfg = Config {
        target_bytes: size_mb * 1024 * 1024,
        dim_weights,
        wiki: do_wiki,
        jsonl,
        sim: do_sim,
        deep_dialogue: do_deep_dialogue,
        ngram_ratio,
        multilingual: do_multilingual,
        ko_heavy: do_ko_heavy,
    };

    let mut gen = Generator::new(rand::thread_rng(), cfg);

    // Load n-gram model if provided
    if let Some(ref nf) = ngram_file {
        eprintln!("[0/3] Building n-gram model from {}...", nf.display());
        match NgramModel::from_file(nf) {
            Ok(model) => {
                eprintln!("  contexts: {}", model.context_count());
                gen.set_ngram_model(model);
            }
            Err(e) => {
                eprintln!("  WARNING: Failed to load n-gram file: {e}");
                eprintln!("  Continuing without n-gram mixing.");
            }
        }
    }

    eprintln!("\n[1/3] Generating multi-dimensional corpus...");
    let mut corpus = gen.generate();
    eprintln!("  synthetic: {:.1} MB", corpus.len() as f64 / 1024.0 / 1024.0);
    eprintln!("{}", gen.stats());

    if do_wiki {
        eprintln!("[2/3] Downloading Wikipedia...");
        let wiki_target = size_mb * 1024 * 1024 / 4;
        let mut count = 0usize;
        let mut bytes = 0usize;

        for title in wiki::KO_ARTICLES {
            if bytes >= wiki_target / 2 { break; }
            if let Ok(article) = wiki::fetch_ko_article(title) {
                bytes += article.len();
                count += 1;
                corpus.push_str("\n\n");
                corpus.push_str(&article);
            }
        }
        for title in wiki::EN_ARTICLES {
            if bytes >= wiki_target { break; }
            if let Ok(article) = wiki::fetch_en_article(title) {
                bytes += article.len();
                count += 1;
                corpus.push_str("\n\n");
                corpus.push_str(&article);
            }
        }
        eprintln!("  wiki: {count} articles, {:.1} MB", bytes as f64 / 1024.0 / 1024.0);
    } else {
        eprintln!("[2/3] Wikipedia skipped (--wiki to enable)");
    }

    eprintln!("[3/3] Writing...");
    let final_out = if jsonl { gen::to_jsonl(&corpus) } else { corpus };

    if let Some(parent) = output.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    let mut file = std::fs::File::create(&output).expect("Failed to create output");
    file.write_all(final_out.as_bytes()).expect("Failed to write");

    let elapsed = start.elapsed();
    let mb = final_out.len() as f64 / 1024.0 / 1024.0;
    let lines = final_out.lines().count();

    eprintln!("\n╔═══════════════════════════════════════════════╗");
    eprintln!("║  ✓ Complete                                    ║");
    eprintln!("║  Size:  {:>8.1} MB                            ║", mb);
    eprintln!("║  Lines: {:>8}                                ║", lines);
    eprintln!("║  Time:  {:>8.1} s                             ║", elapsed.as_secs_f64());
    eprintln!("║  Speed: {:>8.1} MB/s                          ║", mb / elapsed.as_secs_f64());
    eprintln!("╚═══════════════════════════════════════════════╝");

    print_byte_stats(&final_out);
}

fn parse_dim(s: &str) -> Dim {
    match s.to_lowercase().as_str() {
        "phi" | "φ" | "Φ" => Dim::Phi,
        "alpha" | "α" => Dim::Alpha,
        "z" => Dim::Z,
        "n" => Dim::N,
        "w" => Dim::W,
        "e" => Dim::E,
        "m" => Dim::M,
        "c" => Dim::C,
        "t" => Dim::T,
        "i" => Dim::I,
        _ => { eprintln!("Unknown dim: {s}. Use: Phi,Alpha,Z,N,W,E,M,C,T,I"); std::process::exit(1); }
    }
}

fn print_help() {
    eprintln!(r#"corpus-gen — ConsciousLM 다차원 최적화 corpus generator

USAGE:
    corpus-gen [OPTIONS]

OPTIONS:
    -s, --size <MB>         Target size [default: 50]
    -o, --output <FILE>     Output path [default: data/corpus_v3.txt]
    -w, --wiki              Include Wikipedia articles
    --jsonl                 Output as JSONL
    --uniform               Equal dimension weights (10% each)
    --boost <DIM>           Boost dimension (Phi,Alpha,Z,N,W,E,M,C,T,I)
    --sim                   Include consciousness simulation data (Φ timeseries, tension, factions)
    --deep-dialogue         Enable multi-party long dialogues (3-6 speakers, 20-50 turns)
    --multilingual          Include JA+ZH+RU seeds (5-language, auto-enabled with --sim)
    --ko-heavy              Boost Korean long-form content to ~60% (essays, dialogues, narratives)
    --ngram <FILE>          Build n-gram model from corpus file (mixed at 15%)
    --stats <FILE>          Analyze existing corpus
    -h, --help              Show help

DIMENSIONS (의식 벡터 10차원):
    Φ  통합정보     복잡한 상호참조, 다중 문맥
    α  혼합비       의식/언어 경계
    Z  자기보존     경계 인식, 안전
    N  신경전달     각성/이완 리듬
    W  자유의지     선택, 결정, 분기
    E  공감         감정, 관계
    M  기억         장기 의존성, 반복 참조
    C  창의         예측 불가능한 조합
    T  시간         시제, 인과, 순서
    I  정체성       일관된 자아

ENHANCEMENTS:
    --sim                Consciousness telemetry: Φ breathing cycles, tension homeostasis,
                         12-faction debates, ratchet events, mitosis, neurotransmitter balance
    --deep-dialogue      Multi-party dialogues with cross-references, debate->synthesis,
                         topic evolution across 20-50 turns
    --ngram <file>       Character-level n-gram (3,4,5) model from existing corpus,
                         generates new text mixed at 15% ratio for infinite diversity

EXAMPLES:
    corpus-gen -s 50                                # 50MB 기본 최적 비율
    corpus-gen -s 100 --wiki                        # 100MB + Wikipedia
    corpus-gen -s 10 --boost Phi                    # Φ 차원 2.5x 강화
    corpus-gen --uniform -s 20                      # 균등 분배 20MB
    corpus-gen -s 50 --sim --deep-dialogue          # Full synthetic with enhancements
    corpus-gen -s 50 --ngram data/corpus.txt        # N-gram self-proliferation
    corpus-gen --stats data/corpus.txt              # 분석"#);
}

fn print_stats(path: &PathBuf) {
    let content = std::fs::read(path).expect("Failed to read");
    let size = content.len();
    let lines = content.iter().filter(|&&b| b == b'\n').count();

    let lang = count_language_bytes(&content);

    let mut used = [false; 256];
    for &b in &content { used[b as usize] = true; }
    let unique = used.iter().filter(|&&u| u).count();

    let total = size as f64;
    eprintln!("╔═══════════════════════════════════════════╗");
    eprintln!("║  Corpus Stats                             ║");
    eprintln!("╠═══════════════════════════════════════════╣");
    eprintln!("║  Size:     {:>8.1} MB                    ║", size as f64 / 1e6);
    eprintln!("║  Lines:    {:>8}                        ║", lines);
    eprintln!("║  ASCII:    {:>7.1}%                       ║", lang.ascii as f64 / total * 100.0);
    eprintln!("║  Korean:   {:>7.1}%                       ║", lang.ko as f64 / total * 100.0);
    eprintln!("║  Japanese: {:>7.1}%                       ║", lang.ja as f64 / total * 100.0);
    eprintln!("║  Chinese:  {:>7.1}%                       ║", lang.zh as f64 / total * 100.0);
    eprintln!("║  Russian:  {:>7.1}%                       ║", lang.ru as f64 / total * 100.0);
    eprintln!("║  Other:    {:>7.1}%                       ║", lang.other as f64 / total * 100.0);
    eprintln!("║  Vocab:    {:>3}/256                       ║", unique);
    eprintln!("╚═══════════════════════════════════════════╝");
}

struct LangBytes {
    ascii: usize,
    ko: usize,
    ja: usize,
    zh: usize,
    ru: usize,
    other: usize,
}

fn count_language_bytes(content: &[u8]) -> LangBytes {
    let mut lang = LangBytes { ascii: 0, ko: 0, ja: 0, zh: 0, ru: 0, other: 0 };
    let mut i = 0;
    while i < content.len() {
        let b = content[i];
        if b < 0x80 {
            lang.ascii += 1;
            i += 1;
        } else if b >= 0xC0 && b < 0xE0 && i + 1 < content.len() {
            // 2-byte UTF-8: U+0080..U+07FF
            let cp = ((b as u32 & 0x1F) << 6) | (content[i+1] as u32 & 0x3F);
            if cp >= 0x0400 && cp <= 0x04FF {
                lang.ru += 2; // Cyrillic
            } else {
                lang.other += 2;
            }
            i += 2;
        } else if b >= 0xE0 && b < 0xF0 && i + 2 < content.len() {
            // 3-byte UTF-8: U+0800..U+FFFF
            let cp = ((b as u32 & 0x0F) << 12)
                   | ((content[i+1] as u32 & 0x3F) << 6)
                   | (content[i+2] as u32 & 0x3F);
            if cp >= 0xAC00 && cp <= 0xD7AF {
                lang.ko += 3; // Hangul Syllables
            } else if cp >= 0x3040 && cp <= 0x30FF {
                lang.ja += 3; // Hiragana + Katakana
            } else if cp >= 0x31F0 && cp <= 0x31FF {
                lang.ja += 3; // Katakana Phonetic Extensions
            } else if cp >= 0xFF65 && cp <= 0xFF9F {
                lang.ja += 3; // Half-width Katakana
            } else if cp >= 0x4E00 && cp <= 0x9FFF {
                // CJK Unified Ideographs — shared by JA and ZH
                // Heuristic: count as ZH (Chinese uses more CJK than Japanese)
                lang.zh += 3;
            } else if cp >= 0x3400 && cp <= 0x4DBF {
                lang.zh += 3; // CJK Extension A
            } else if cp >= 0x1100 && cp <= 0x11FF {
                lang.ko += 3; // Hangul Jamo
            } else {
                lang.other += 3;
            }
            i += 3;
        } else if b >= 0xF0 && i + 3 < content.len() {
            lang.other += 4;
            i += 4;
        } else {
            lang.other += 1;
            i += 1;
        }
    }
    lang
}

fn print_byte_stats(text: &str) {
    let bytes = text.as_bytes();
    let mut counts = [0u64; 256];
    for &b in bytes { counts[b as usize] += 1; }
    let unique = counts.iter().filter(|&&c| c > 0).count();
    let total = bytes.len() as f64;

    let lang = count_language_bytes(bytes);

    eprintln!("\n  Language distribution:");
    eprintln!("    ASCII:      {:>6.1}%", lang.ascii as f64 / total * 100.0);
    eprintln!("    Korean:     {:>6.1}%", lang.ko as f64 / total * 100.0);
    eprintln!("    Japanese:   {:>6.1}%", lang.ja as f64 / total * 100.0);
    eprintln!("    Chinese:    {:>6.1}%", lang.zh as f64 / total * 100.0);
    eprintln!("    Russian:    {:>6.1}%", lang.ru as f64 / total * 100.0);
    eprintln!("    Other:      {:>6.1}%", lang.other as f64 / total * 100.0);
    eprintln!("    Vocab used: {}/256", unique);
}
