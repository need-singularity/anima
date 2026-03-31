use pyo3::prelude::*;

mod vector;
mod scanner;
mod fetcher;

#[pymodule]
fn knowledge_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(vector::vector_search, m)?)?;
    m.add_function(wrap_pyfunction!(vector::vector_add, m)?)?;
    m.add_function(wrap_pyfunction!(vector::vector_build, m)?)?;
    m.add_function(wrap_pyfunction!(scanner::scan_hardcoding, m)?)?;
    m.add_function(wrap_pyfunction!(fetcher::batch_fetch_wikipedia, m)?)?;
    Ok(())
}
