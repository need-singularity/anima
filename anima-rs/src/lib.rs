use pyo3::prelude::*;

#[pymodule]
fn anima_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", "0.1.0")?;
    Ok(())
}
