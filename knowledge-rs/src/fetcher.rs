use pyo3::prelude::*;
use rayon::prelude::*;
use serde::Deserialize;

#[derive(Deserialize)]
struct WikiSummary {
    title: Option<String>,
    extract: Option<String>,
}

/// Fetch N random Wikipedia articles in parallel
/// Returns list of (title, summary)
#[pyfunction]
pub fn batch_fetch_wikipedia(
    count: usize,
    lang: Option<String>,
) -> PyResult<Vec<(String, String)>> {
    let lang = lang.unwrap_or_else(|| "ko".to_string());
    let url = format!(
        "https://{}.wikipedia.org/api/rest_v1/page/random/summary",
        lang
    );

    let client = reqwest::blocking::Client::builder()
        .user_agent("Anima/1.0 (knowledge-rs)")
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    let results: Vec<Option<(String, String)>> = (0..count)
        .into_par_iter()
        .map(|_| {
            match client.get(&url).send() {
                Ok(resp) => {
                    if let Ok(data) = resp.json::<WikiSummary>() {
                        let title = data.title.unwrap_or_default();
                        let extract = data.extract.unwrap_or_default();
                        if !title.is_empty() && !extract.is_empty() {
                            return Some((title, extract));
                        }
                    }
                    None
                }
                Err(_) => None,
            }
        })
        .collect();

    Ok(results.into_iter().flatten().collect())
}
