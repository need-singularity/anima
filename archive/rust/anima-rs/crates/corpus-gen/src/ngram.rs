//! N-gram self-proliferation — infinite diversity from finite seeds
//!
//! Builds character-level n-gram models (n=3,4,5) from existing corpus,
//! then generates new text. Mixed with seed-based text at configurable ratio.

use rand::Rng;
use std::collections::HashMap;

/// Character-level n-gram model supporting n=3,4,5
pub struct NgramModel {
    /// For each n, map from context (n-1 chars) -> Vec<(next_char, count)>
    models: [HashMap<Vec<u8>, Vec<(u8, u32)>>; 3],
}

impl NgramModel {
    /// Build n-gram model from raw bytes of an existing corpus.
    pub fn from_bytes(data: &[u8]) -> Self {
        let mut raw: [HashMap<Vec<u8>, HashMap<u8, u32>>; 3] = [
            HashMap::new(),
            HashMap::new(),
            HashMap::new(),
        ];

        // Build counts for n=3,4,5
        for (idx, n) in [3usize, 4, 5].iter().enumerate() {
            if data.len() <= *n {
                continue;
            }
            for window in data.windows(*n) {
                let context = window[..*n - 1].to_vec();
                let next = window[*n - 1];
                *raw[idx]
                    .entry(context)
                    .or_default()
                    .entry(next)
                    .or_insert(0) += 1;
            }
        }

        // Convert to sorted Vec for sampling
        let models = [
            Self::compile(&raw[0]),
            Self::compile(&raw[1]),
            Self::compile(&raw[2]),
        ];

        NgramModel { models }
    }

    /// Load an n-gram model from a file path.
    pub fn from_file(path: &std::path::Path) -> std::io::Result<Self> {
        let data = std::fs::read(path)?;
        Ok(Self::from_bytes(&data))
    }

    fn compile(
        raw: &HashMap<Vec<u8>, HashMap<u8, u32>>,
    ) -> HashMap<Vec<u8>, Vec<(u8, u32)>> {
        raw.iter()
            .map(|(ctx, counts)| {
                let mut v: Vec<(u8, u32)> = counts.iter().map(|(&b, &c)| (b, c)).collect();
                v.sort_by(|a, b| b.1.cmp(&a.1));
                (ctx.clone(), v)
            })
            .collect()
    }

    /// Generate `target_len` bytes using the n-gram model with backoff.
    /// Uses n=5 first, backing off to n=4, then n=3, then random.
    pub fn generate<R: Rng>(&self, rng: &mut R, target_len: usize) -> String {
        let mut buf: Vec<u8> = Vec::with_capacity(target_len);

        // Seed with a random context from the n=5 model
        if let Some(ctx) = self.random_context(rng, 2) {
            buf.extend_from_slice(&ctx);
        } else if let Some(ctx) = self.random_context(rng, 1) {
            buf.extend_from_slice(&ctx);
        } else {
            // Fallback: start with space
            buf.extend_from_slice(b"   ");
        }

        while buf.len() < target_len {
            let next = self.predict_next(rng, &buf);
            buf.push(next);

            // Occasionally inject a newline for paragraph structure
            if buf.len() % 200 == 0 && next != b'\n' {
                buf.push(b'\n');
            }
        }

        // Best-effort UTF-8 conversion
        String::from_utf8_lossy(&buf).into_owned()
    }

    fn predict_next<R: Rng>(&self, rng: &mut R, buf: &[u8]) -> u8 {
        // Try n=5 (context=4), n=4 (context=3), n=3 (context=2)
        for (idx, ctx_len) in [(2usize, 4usize), (1, 3), (0, 2)] {
            if buf.len() >= ctx_len {
                let context = &buf[buf.len() - ctx_len..];
                if let Some(candidates) = self.models[idx].get(context) {
                    return Self::weighted_sample(rng, candidates);
                }
            }
        }
        // Random ASCII fallback
        rng.gen_range(b' '..=b'~')
    }

    fn weighted_sample<R: Rng>(rng: &mut R, candidates: &[(u8, u32)]) -> u8 {
        let total: u32 = candidates.iter().map(|(_, c)| c).sum();
        if total == 0 {
            return b' ';
        }
        let mut r = rng.gen_range(0..total);
        for &(byte, count) in candidates {
            if r < count {
                return byte;
            }
            r -= count;
        }
        candidates[0].0
    }

    fn random_context<R: Rng>(&self, rng: &mut R, model_idx: usize) -> Option<Vec<u8>> {
        let model = &self.models[model_idx];
        if model.is_empty() {
            return None;
        }
        let keys: Vec<&Vec<u8>> = model.keys().collect();
        let idx = rng.gen_range(0..keys.len());
        Some(keys[idx].clone())
    }

    /// Returns true if model has any data
    pub fn is_empty(&self) -> bool {
        self.models.iter().all(|m| m.is_empty())
    }

    /// Total unique contexts across all n
    pub fn context_count(&self) -> usize {
        self.models.iter().map(|m| m.len()).sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ngram_basic() {
        let data = b"hello world hello world hello";
        let model = NgramModel::from_bytes(data);
        assert!(!model.is_empty());
        let text = model.generate(&mut rand::thread_rng(), 100);
        assert!(text.len() >= 100);
    }
}
