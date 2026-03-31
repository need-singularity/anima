use pyo3::prelude::*;
use std::sync::Mutex;

static VECTORS: Mutex<Option<VectorIndex>> = Mutex::new(None);

struct VectorIndex {
    vectors: Vec<(String, Vec<f32>)>,
}

impl VectorIndex {
    fn new() -> Self {
        Self { vectors: Vec::new() }
    }

    fn add(&mut self, key: String, vec: Vec<f32>) {
        self.vectors.retain(|(k, _)| k != &key);
        self.vectors.push((key, vec));
    }

    fn search(&self, query: &[f32], top_k: usize) -> Vec<(String, f32)> {
        let mut scores: Vec<(String, f32)> = self.vectors.iter()
            .map(|(key, vec)| {
                let score = cosine_similarity(query, vec);
                (key.clone(), score)
            })
            .collect();
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scores.truncate(top_k);
        scores
    }
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a < 1e-8 || norm_b < 1e-8 {
        return 0.0;
    }
    dot / (norm_a * norm_b)
}

/// Add a vector to the index
#[pyfunction]
pub fn vector_add(key: String, embedding: Vec<f32>) -> PyResult<()> {
    let mut guard = VECTORS.lock().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
    })?;
    if guard.is_none() {
        *guard = Some(VectorIndex::new());
    }
    guard.as_mut().unwrap().add(key, embedding);
    Ok(())
}

/// Build/rebuild the index — returns current vector count
#[pyfunction]
pub fn vector_build() -> PyResult<usize> {
    let guard = VECTORS.lock().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
    })?;
    Ok(guard.as_ref().map_or(0, |idx| idx.vectors.len()))
}

/// Search for similar vectors, returns list of (key, score)
#[pyfunction]
pub fn vector_search(query: Vec<f32>, top_k: usize) -> PyResult<Vec<(String, f32)>> {
    let guard = VECTORS.lock().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
    })?;
    Ok(guard.as_ref().map_or_else(Vec::new, |idx| idx.search(&query, top_k)))
}
