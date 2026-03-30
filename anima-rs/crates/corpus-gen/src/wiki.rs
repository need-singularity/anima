//! Wikipedia article fetcher for corpus enrichment.


const USER_AGENT: &str = "AnimaCorpus/1.0 (ConsciousLM training)";

/// Fetch a Korean Wikipedia article by title.
pub fn fetch_ko_article(title: &str) -> Result<String, String> {
    let url = format!(
        "https://ko.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&titles={}",
        urlenc(title)
    );
    fetch_and_extract(&url)
}

/// Fetch an English Wikipedia article by title.
pub fn fetch_en_article(title: &str) -> Result<String, String> {
    let url = format!(
        "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&titles={}",
        urlenc(title)
    );
    fetch_and_extract(&url)
}

fn fetch_and_extract(url: &str) -> Result<String, String> {
    let resp = ureq::get(url)
        .set("User-Agent", USER_AGENT)
        .timeout(std::time::Duration::from_secs(15))
        .call()
        .map_err(|e| format!("HTTP error: {e}"))?;

    let body: serde_json::Value = resp
        .into_json()
        .map_err(|e| format!("JSON parse error: {e}"))?;

    let pages = body
        .pointer("/query/pages")
        .and_then(|p| p.as_object())
        .ok_or("no pages in response")?;

    for (id, page) in pages {
        if id == "-1" {
            continue;
        }
        if let Some(extract) = page.get("extract").and_then(|e| e.as_str()) {
            let cleaned = clean_wiki(extract);
            if cleaned.len() >= 200 {
                let title = page
                    .get("title")
                    .and_then(|t| t.as_str())
                    .unwrap_or("Untitled");
                return Ok(format!("# {title}\n\n{cleaned}"));
            }
        }
    }

    Err("no usable extract".into())
}

fn clean_wiki(text: &str) -> String {
    let mut s = text.to_string();
    // Remove remaining HTML-like tags
    s = regex_replace(&s, r"<[^>]+>", "");
    // Collapse multiple newlines
    s = regex_replace(&s, r"\n{3,}", "\n\n");
    // Collapse multiple spaces
    s = regex_replace(&s, r" {2,}", " ");
    s.trim().to_string()
}

fn regex_replace(text: &str, pattern: &str, _replacement: &str) -> String {
    // Simple regex-free replacements for common patterns
    let mut result = text.to_string();
    match pattern {
        r"<[^>]+>" => {
            // Strip HTML tags
            let mut out = String::with_capacity(result.len());
            let mut in_tag = false;
            for c in result.chars() {
                if c == '<' {
                    in_tag = true;
                } else if c == '>' {
                    in_tag = false;
                } else if !in_tag {
                    out.push(c);
                }
            }
            result = out;
        }
        r"\n{3,}" => {
            while result.contains("\n\n\n") {
                result = result.replace("\n\n\n", "\n\n");
            }
        }
        r" {2,}" => {
            while result.contains("  ") {
                result = result.replace("  ", " ");
            }
        }
        _ => {}
    }
    result
}

fn urlenc(s: &str) -> String {
    let mut out = String::new();
    for b in s.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                out.push(b as char);
            }
            _ => {
                out.push_str(&format!("%{:02X}", b));
            }
        }
    }
    out
}

/// Korean Wikipedia article titles for corpus building.
pub const KO_ARTICLES: &[&str] = &[
    "인공지능", "기계_학습", "딥_러닝", "신경망", "자연어_처리",
    "양자_컴퓨터", "상대성이론", "빅뱅", "블랙홀", "DNA",
    "진화", "광합성", "엔트로피", "뇌", "뉴런",
    "의식", "자유의지", "인식론", "존재론", "현상학",
    "실존주의", "합리주의", "유물론", "이원론",
    "철학", "심리학", "인지과학", "수학", "물리학",
    "화학", "생물학", "천체물리학", "유전학", "신경과학",
    "한글", "세종대왕", "조선", "고려", "삼국시대",
    "한국_전쟁", "대한민국", "서울", "한국_문학",
    "미적분학", "선형대수학", "확률론", "통계학", "정보_엔트로피",
    "그래프_이론", "위상수학", "카오스_이론", "프랙털", "게임_이론",
    "태양계", "은하", "우주", "지구", "달",
    "생태계", "기후_변화", "생물_다양성",
];

/// English Wikipedia article titles.
pub const EN_ARTICLES: &[&str] = &[
    "Artificial_intelligence", "Machine_learning", "Deep_learning", "Neural_network",
    "Natural_language_processing", "Transformer_(machine_learning_model)",
    "Quantum_computing", "Theory_of_relativity", "Big_Bang", "Black_hole",
    "DNA", "Evolution", "Photosynthesis", "Entropy", "Neuron",
    "Consciousness", "Hard_problem_of_consciousness", "Integrated_information_theory",
    "Global_workspace_theory", "Free_will", "Qualia", "Philosophy_of_mind",
    "Panpsychism", "Phenomenology_(philosophy)", "Existentialism", "Epistemology",
    "René_Descartes", "Immanuel_Kant", "Friedrich_Nietzsche",
    "Alan_Turing", "John_von_Neumann", "Claude_Shannon",
    "Artificial_general_intelligence", "Chinese_room", "Turing_test",
    "Neuroscience", "Brain", "Cerebral_cortex", "Hippocampus",
    "Hebbian_theory", "Neurotransmitter", "Neural_oscillation",
    "Calculus", "Linear_algebra", "Probability_theory", "Information_entropy",
    "Graph_theory", "Chaos_theory", "Fractal", "Game_theory",
    "Universe", "Galaxy", "Solar_System", "Earth",
    "Thermodynamics", "Standard_Model", "Ecosystem",
];
