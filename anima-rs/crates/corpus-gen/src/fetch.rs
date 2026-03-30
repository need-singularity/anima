//! External data fetchers
//!
//! - Project Gutenberg plain text (Korean + English classics)
//! - arXiv abstract fetcher (cs.AI, q-bio.NC)
//!
//! All fetchers are opt-in and require network access.

use std::time::Duration;

const USER_AGENT: &str = "AnimaCorpus/1.0 (ConsciousLM training)";
const TIMEOUT: Duration = Duration::from_secs(20);

// ═══════════════════════════════════════════════════════════
// Project Gutenberg
// ═══════════════════════════════════════════════════════════

/// Gutenberg book IDs for English classics
pub const GUTENBERG_EN: &[(u32, &str)] = &[
    (84, "Frankenstein — Mary Shelley"),
    (1342, "Pride and Prejudice — Jane Austen"),
    (11, "Alice's Adventures in Wonderland — Lewis Carroll"),
    (1661, "The Adventures of Sherlock Holmes — Arthur Conan Doyle"),
    (98, "A Tale of Two Cities — Charles Dickens"),
    (1232, "The Prince — Machiavelli"),
    (74, "The Adventures of Tom Sawyer — Mark Twain"),
    (1952, "The Yellow Wallpaper — Charlotte Perkins Gilman"),
    (2701, "Moby Dick — Herman Melville"),
    (345, "Dracula — Bram Stoker"),
    (16328, "Beowulf"),
    (4300, "Ulysses — James Joyce"),
    (43, "The Strange Case of Dr. Jekyll and Mr. Hyde"),
    (768, "Wuthering Heights — Emily Bronte"),
    (2554, "Crime and Punishment — Fyodor Dostoevsky"),
    (5200, "Metamorphosis — Franz Kafka"),
    (1497, "Republic — Plato"),
    (8700, "Meditations — Marcus Aurelius"),
];

/// Gutenberg book IDs for Korean texts (limited availability)
pub const GUTENBERG_KO: &[(u32, &str)] = &[
    // Gutenberg has very few Korean texts; these are multilingual/translated
    (4280, "The Art of War — Sun Tzu (English, but relevant)"),
    (5827, "Tao Te Ching — Lao Tzu (English translation)"),
];

/// Fetch plain text from Project Gutenberg by book ID.
pub fn fetch_gutenberg(book_id: u32) -> Result<String, String> {
    let url = format!("https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt");

    let resp = ureq::get(&url)
        .set("User-Agent", USER_AGENT)
        .timeout(TIMEOUT)
        .call()
        .map_err(|e| format!("Gutenberg fetch error: {e}"))?;

    let text = resp
        .into_string()
        .map_err(|e| format!("Gutenberg read error: {e}"))?;

    // Strip Gutenberg header/footer
    let cleaned = strip_gutenberg_boilerplate(&text);
    if cleaned.len() < 500 {
        return Err("Text too short after stripping boilerplate".into());
    }

    Ok(cleaned)
}

fn strip_gutenberg_boilerplate(text: &str) -> String {
    let lines: Vec<&str> = text.lines().collect();
    let mut start = 0;
    let mut end = lines.len();

    // Find start marker
    for (i, line) in lines.iter().enumerate() {
        if line.contains("*** START OF") || line.contains("***START OF") {
            start = i + 1;
            break;
        }
    }

    // Find end marker
    for (i, line) in lines.iter().enumerate().rev() {
        if line.contains("*** END OF") || line.contains("***END OF") {
            end = i;
            break;
        }
    }

    lines[start..end].join("\n")
}

// ═══════════════════════════════════════════════════════════
// arXiv Abstracts
// ═══════════════════════════════════════════════════════════

/// arXiv categories relevant to consciousness research
pub const ARXIV_CATEGORIES: &[&str] = &[
    "cs.AI",
    "cs.CL",
    "cs.NE",
    "q-bio.NC",
];

/// Fetch recent arXiv abstracts from a category.
/// Returns up to `max_results` abstracts.
pub fn fetch_arxiv_abstracts(category: &str, max_results: usize) -> Result<Vec<String>, String> {
    let url = format!(
        "http://export.arxiv.org/api/query?search_query=cat:{}&start=0&max_results={}&sortBy=submittedDate&sortOrder=descending",
        category, max_results
    );

    let resp = ureq::get(&url)
        .set("User-Agent", USER_AGENT)
        .timeout(TIMEOUT)
        .call()
        .map_err(|e| format!("arXiv fetch error: {e}"))?;

    let body = resp
        .into_string()
        .map_err(|e| format!("arXiv read error: {e}"))?;

    // Simple XML parsing for <entry>...<summary>...</summary>...</entry>
    let mut abstracts = Vec::new();
    let mut pos = 0;

    while let Some(entry_start) = body[pos..].find("<entry>") {
        let entry_start = pos + entry_start;
        let entry_end = match body[entry_start..].find("</entry>") {
            Some(e) => entry_start + e + 8,
            None => break,
        };
        let entry = &body[entry_start..entry_end];

        // Extract title
        let title = extract_xml_tag(entry, "title").unwrap_or_default();
        // Extract summary (abstract)
        let summary = extract_xml_tag(entry, "summary").unwrap_or_default();

        if !summary.is_empty() {
            let clean_title = title.trim().replace('\n', " ");
            let clean_summary = summary.trim().replace('\n', " ");
            // Collapse multiple spaces
            let clean_summary = collapse_spaces(&clean_summary);
            abstracts.push(format!("Title: {clean_title}\nAbstract: {clean_summary}"));
        }

        pos = entry_end;
    }

    if abstracts.is_empty() {
        return Err(format!("No abstracts found for category {category}"));
    }

    Ok(abstracts)
}

fn extract_xml_tag<'a>(xml: &'a str, tag: &str) -> Option<&'a str> {
    let open = format!("<{tag}>");
    let close = format!("</{tag}>");
    let start = xml.find(&open)? + open.len();
    let end = xml[start..].find(&close)? + start;
    Some(&xml[start..end])
}

fn collapse_spaces(s: &str) -> String {
    let mut result = String::with_capacity(s.len());
    let mut prev_space = false;
    for c in s.chars() {
        if c.is_whitespace() {
            if !prev_space {
                result.push(' ');
            }
            prev_space = true;
        } else {
            result.push(c);
            prev_space = false;
        }
    }
    result
}
