// ngram.rs — Fast n-gram indexing and overlap search for novelty detection
//
// Builds a HashSet of n-grams from corpus text, then checks overlap
// ratio of generated text against the index. Exposed to Python via PyO3.

use rayon::prelude::*;
use std::collections::HashSet;

/// Build n-gram hash set from corpus text.
/// Returns the set of all unique n-grams found.
pub fn build_ngram_index(corpus: &str, n: usize) -> HashSet<String> {
    if n == 0 || corpus.len() < n {
        return HashSet::new();
    }
    let chars: Vec<char> = corpus.chars().collect();
    let mut set = HashSet::with_capacity(chars.len());
    for i in 0..chars.len().saturating_sub(n - 1) {
        let ngram: String = chars[i..i + n].iter().collect();
        set.insert(ngram);
    }
    set
}

/// Check overlap ratio of generated text against corpus ngrams.
/// Returns fraction [0.0, 1.0] of generated n-grams found in corpus.
pub fn ngram_overlap(generated: &str, corpus_ngrams: &HashSet<String>, n: usize) -> f64 {
    if n == 0 || generated.len() < n {
        return 0.0;
    }
    let chars: Vec<char> = generated.chars().collect();
    if chars.len() < n {
        return 0.0;
    }
    let total = chars.len() - n + 1;
    let mut hits = 0usize;
    for i in 0..total {
        let ngram: String = chars[i..i + n].iter().collect();
        if corpus_ngrams.contains(&ngram) {
            hits += 1;
        }
    }
    hits as f64 / total as f64
}

/// Batch check multiple generated texts against a corpus.
/// Uses rayon for parallel processing.
pub fn batch_ngram_check(texts: &[String], corpus: &str, n: usize) -> Vec<f64> {
    let index = build_ngram_index(corpus, n);
    texts
        .par_iter()
        .map(|text| ngram_overlap(text, &index, n))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_build_index() {
        let idx = build_ngram_index("abcdef", 3);
        assert!(idx.contains("abc"));
        assert!(idx.contains("bcd"));
        assert!(idx.contains("cde"));
        assert!(idx.contains("def"));
        assert_eq!(idx.len(), 4);
    }

    #[test]
    fn test_overlap_exact() {
        let idx = build_ngram_index("hello world", 3);
        // Same text should have 100% overlap
        let ratio = ngram_overlap("hello world", &idx, 3);
        assert!((ratio - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_overlap_none() {
        let idx = build_ngram_index("aaaa", 3);
        let ratio = ngram_overlap("xyz", &idx, 3);
        assert!((ratio - 0.0).abs() < 1e-9);
    }

    #[test]
    fn test_batch() {
        let texts = vec!["hello".to_string(), "zzzzz".to_string()];
        let results = batch_ngram_check(&texts, "hello world", 3);
        assert_eq!(results.len(), 2);
        assert!(results[0] > 0.5); // "hello" overlaps with "hello world"
        assert!(results[1] < 0.01); // "zzzzz" does not
    }

    #[test]
    fn test_unicode() {
        let idx = build_ngram_index("안녕하세요 의식", 2);
        assert!(idx.contains("안녕"));
        assert!(idx.contains("녕하"));
        let ratio = ngram_overlap("안녕하세요", &idx, 2);
        assert!(ratio > 0.5);
    }

    #[test]
    fn test_edge_cases() {
        assert_eq!(build_ngram_index("", 3).len(), 0);
        assert_eq!(build_ngram_index("ab", 3).len(), 0);
        assert!((ngram_overlap("", &HashSet::new(), 3) - 0.0).abs() < 1e-9);
    }
}
