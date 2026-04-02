//! PyO3 bindings for telescope-rs
//!
//! Exposes all 16 lens functions to Python:
//!   telescope_rs.consciousness_scan(...)  → dict
//!   telescope_rs.topology_scan(...)       → dict
//!   telescope_rs.causal_scan(...)         → dict
//!   telescope_rs.gravity_scan(...)        → dict
//!   telescope_rs.thermo_scan(...)         → dict
//!   telescope_rs.wave_scan(...)           → dict
//!   telescope_rs.evolution_scan(...)      → dict
//!   telescope_rs.info_scan(...)           → dict
//!   telescope_rs.quantum_scan(...)        → dict
//!   telescope_rs.em_scan(...)             → dict
//!   telescope_rs.ruler_scan(...)          → dict
//!   telescope_rs.triangle_scan(...)       → dict
//!   telescope_rs.compass_scan(...)        → dict
//!   telescope_rs.mirror_scan(...)         → dict
//!   telescope_rs.scale_scan(...)          → dict
//!   telescope_rs.quantum_microscope_scan(...) → dict
//!   telescope_rs.fast_mutual_info(...)    → float

use pyo3::prelude::*;
use pyo3::types::PyDict;
use numpy::{PyReadonlyArray2, PyArray1};

use crate::{consciousness, topology, causal, mi, gravity, thermo, wave, evolution,
            info, quantum, em, ruler, triangle, compass, mirror, scale, quantum_microscope,
            stability, network, memory_lens, recursion, boundary, multiscale};

/// Helper: extract flat data + dims from PyReadonlyArray2.
fn extract_data(data: &PyReadonlyArray2<'_, f64>) -> (Vec<f64>, usize, usize) {
    let arr = data.as_array();
    let (n_samples, n_features) = (arr.nrows(), arr.ncols());
    let flat: Vec<f64> = arr.iter().copied().collect();
    (flat, n_samples, n_features)
}

/// Consciousness lens scan (GRU + Hebbian + Phi + Factions)
#[pyfunction]
#[pyo3(signature = (data, n_cells=64, n_factions=12, steps=300, coupling_alpha=0.014))]
fn consciousness_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
    n_cells: usize,
    n_factions: usize,
    steps: usize,
    coupling_alpha: f64,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let mut lens = consciousness::ConsciousnessLens::new(
        n_cells, n_features.max(128), n_factions, steps, coupling_alpha);
    let result = lens.scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("phi_iit", result.phi_iit)?;
    dict.set_item("phi_proxy", result.phi_proxy)?;
    dict.set_item("n_clusters", result.n_clusters)?;
    dict.set_item("steps_run", result.steps_run)?;
    let anom_idx: Vec<f64> = result.anomalies.iter().map(|a| a.0 as f64).collect();
    let anom_scores: Vec<f64> = result.anomalies.iter().map(|a| a.1).collect();
    dict.set_item("anomaly_indices", PyArray1::from_vec(py, anom_idx))?;
    dict.set_item("anomaly_scores", PyArray1::from_vec(py, anom_scores))?;
    Ok(dict)
}

/// Topology lens scan (persistent homology: Betti-0 + Betti-1)
#[pyfunction]
#[pyo3(signature = (data, n_filtration_steps=100, persistence_threshold=0.014))]
fn topology_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
    n_filtration_steps: usize,
    persistence_threshold: f64,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = topology::scan(&flat, n_samples, n_features,
                                n_filtration_steps, persistence_threshold);
    let dict = PyDict::new(py);
    dict.set_item("betti_0", result.betti_0)?;
    dict.set_item("betti_1", result.betti_1)?;
    dict.set_item("n_components", result.n_components)?;
    dict.set_item("n_holes", result.n_holes)?;
    dict.set_item("optimal_scale", result.optimal_scale)?;
    dict.set_item("n_persistence_pairs", result.persistence_pairs.len())?;
    dict.set_item("n_phase_transitions", result.phase_transitions.len())?;
    let pt_strs: Vec<String> = result.phase_transitions.iter()
        .map(|(eps, desc)| format!("eps={:.4}: {}", eps, desc))
        .collect();
    dict.set_item("phase_transitions", pt_strs)?;
    Ok(dict)
}

/// Causal lens scan (Granger + Transfer entropy)
#[pyfunction]
#[pyo3(signature = (data, max_lag=5, te_bins=16, min_strength=0.1))]
fn causal_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
    max_lag: usize,
    te_bins: usize,
    min_strength: f64,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = causal::scan(&flat, n_samples, n_features, max_lag, te_bins, min_strength);

    let dict = PyDict::new(py);
    dict.set_item("n_features", result.n_features)?;
    dict.set_item("n_causal_pairs", result.causal_pairs.len())?;
    let causes: Vec<usize> = result.causal_pairs.iter().map(|p| p.cause).collect();
    let effects: Vec<usize> = result.causal_pairs.iter().map(|p| p.effect).collect();
    let strengths: Vec<f64> = result.causal_pairs.iter().map(|p| p.strength).collect();
    dict.set_item("causes", causes)?;
    dict.set_item("effects", effects)?;
    dict.set_item("strengths", strengths)?;
    dict.set_item("granger_matrix", PyArray1::from_vec(py, result.granger_matrix))?;
    dict.set_item("te_matrix", PyArray1::from_vec(py, result.te_matrix))?;
    Ok(dict)
}

/// Gravity lens scan (N-body attractor detection)
#[pyfunction]
#[pyo3(signature = (data,))]
fn gravity_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = gravity::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("n_attractors", result.n_attractors)?;
    dict.set_item("attractors", PyArray1::from_vec(py, result.attractors))?;
    dict.set_item("basins", result.basins)?;
    dict.set_item("energy_landscape", PyArray1::from_vec(py, result.energy_landscape))?;
    Ok(dict)
}

/// Thermo lens scan (thermodynamic analysis)
#[pyfunction]
#[pyo3(signature = (data,))]
fn thermo_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = thermo::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("entropy_per_feature", PyArray1::from_vec(py, result.entropy_per_feature))?;
    dict.set_item("total_entropy", result.total_entropy)?;
    dict.set_item("free_energy", result.free_energy)?;
    dict.set_item("critical_temperature", result.critical_temperature)?;
    dict.set_item("n_phase_transitions", result.phase_transitions.len())?;
    let pt_temps: Vec<f64> = result.phase_transitions.iter().map(|p| p.0).collect();
    let pt_jumps: Vec<f64> = result.phase_transitions.iter().map(|p| p.1).collect();
    dict.set_item("phase_transition_temps", PyArray1::from_vec(py, pt_temps))?;
    dict.set_item("phase_transition_jumps", PyArray1::from_vec(py, pt_jumps))?;
    Ok(dict)
}

/// Wave lens scan (FFT + resonance)
#[pyfunction]
#[pyo3(signature = (data,))]
fn wave_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = wave::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("dominant_frequencies", PyArray1::from_vec(py, result.dominant_frequencies))?;
    let coh_i: Vec<usize> = result.coherences.iter().map(|c| c.0).collect();
    let coh_j: Vec<usize> = result.coherences.iter().map(|c| c.1).collect();
    let coh_v: Vec<f64> = result.coherences.iter().map(|c| c.2).collect();
    dict.set_item("coherence_i", coh_i)?;
    dict.set_item("coherence_j", coh_j)?;
    dict.set_item("coherence_values", PyArray1::from_vec(py, coh_v))?;
    let res_i: Vec<usize> = result.resonances.iter().map(|r| r.0).collect();
    let res_j: Vec<usize> = result.resonances.iter().map(|r| r.1).collect();
    let res_ratio: Vec<f64> = result.resonances.iter().map(|r| r.2).collect();
    dict.set_item("resonance_i", res_i)?;
    dict.set_item("resonance_j", res_j)?;
    dict.set_item("resonance_ratios", PyArray1::from_vec(py, res_ratio))?;
    Ok(dict)
}

/// Evolution lens scan (fitness landscape)
#[pyfunction]
#[pyo3(signature = (data,))]
fn evolution_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = evolution::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("fitness_landscape", PyArray1::from_vec(py, result.fitness_landscape))?;
    dict.set_item("peaks", result.peaks)?;
    dict.set_item("n_niches", result.niches.len())?;
    let niche_sizes: Vec<usize> = result.niches.iter().map(|n| n.len()).collect();
    dict.set_item("niche_sizes", niche_sizes)?;
    Ok(dict)
}

/// Info lens scan (information theory)
#[pyfunction]
#[pyo3(signature = (data,))]
fn info_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = info::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("entropy_per_feature", PyArray1::from_vec(py, result.entropy_per_feature))?;
    dict.set_item("lz_complexity", PyArray1::from_vec(py, result.lz_complexity))?;
    dict.set_item("mi_matrix", PyArray1::from_vec(py, result.mi_matrix))?;
    let red_i: Vec<usize> = result.redundant_features.iter().map(|r| r.0).collect();
    let red_j: Vec<usize> = result.redundant_features.iter().map(|r| r.1).collect();
    let red_v: Vec<f64> = result.redundant_features.iter().map(|r| r.2).collect();
    dict.set_item("redundant_i", red_i)?;
    dict.set_item("redundant_j", red_j)?;
    dict.set_item("redundant_mi", PyArray1::from_vec(py, red_v))?;
    Ok(dict)
}

/// Quantum lens scan (quantum analogies)
#[pyfunction]
#[pyo3(signature = (data,))]
fn quantum_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = quantum::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    let ent_i: Vec<usize> = result.entanglement_pairs.iter().map(|e| e.0).collect();
    let ent_j: Vec<usize> = result.entanglement_pairs.iter().map(|e| e.1).collect();
    let ent_v: Vec<f64> = result.entanglement_pairs.iter().map(|e| e.2).collect();
    dict.set_item("entanglement_i", ent_i)?;
    dict.set_item("entanglement_j", ent_j)?;
    dict.set_item("entanglement_mi", PyArray1::from_vec(py, ent_v))?;
    dict.set_item("n_tunneling_paths", result.tunneling_paths.len())?;
    let tun_i: Vec<usize> = result.tunneling_paths.iter().map(|t| t.0).collect();
    let tun_j: Vec<usize> = result.tunneling_paths.iter().map(|t| t.1).collect();
    dict.set_item("tunneling_i", tun_i)?;
    dict.set_item("tunneling_j", tun_j)?;
    let sup_idx: Vec<usize> = result.superposed_samples.iter().map(|s| s.0).collect();
    let sup_var: Vec<f64> = result.superposed_samples.iter().map(|s| s.1).collect();
    dict.set_item("superposed_indices", sup_idx)?;
    dict.set_item("superposed_variance", PyArray1::from_vec(py, sup_var))?;
    Ok(dict)
}

/// EM lens scan (electromagnetic field analogies)
#[pyfunction]
#[pyo3(signature = (data,))]
fn em_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = em::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("gradient_field", PyArray1::from_vec(py, result.gradient_field))?;
    dict.set_item("divergence_map", PyArray1::from_vec(py, result.divergence_map))?;
    let src_idx: Vec<usize> = result.sources.iter().map(|s| s.0).collect();
    let src_val: Vec<f64> = result.sources.iter().map(|s| s.1).collect();
    dict.set_item("source_indices", src_idx)?;
    dict.set_item("source_values", PyArray1::from_vec(py, src_val))?;
    let snk_idx: Vec<usize> = result.sinks.iter().map(|s| s.0).collect();
    let snk_val: Vec<f64> = result.sinks.iter().map(|s| s.1).collect();
    dict.set_item("sink_indices", snk_idx)?;
    dict.set_item("sink_values", PyArray1::from_vec(py, snk_val))?;
    Ok(dict)
}

/// Ruler lens scan (SVD/orthogonality)
#[pyfunction]
#[pyo3(signature = (data,))]
fn ruler_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = ruler::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("singular_values", PyArray1::from_vec(py, result.singular_values))?;
    dict.set_item("effective_dim", result.effective_dim)?;
    dict.set_item("cosine_matrix", PyArray1::from_vec(py, result.cosine_matrix))?;
    dict.set_item("n_orthogonal_groups", result.orthogonal_groups.len())?;
    Ok(dict)
}

/// Triangle lens scan (ratio/proportion detection)
#[pyfunction]
#[pyo3(signature = (data,))]
fn triangle_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = triangle::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    let rat_i: Vec<usize> = result.simple_ratios.iter().map(|r| r.0).collect();
    let rat_j: Vec<usize> = result.simple_ratios.iter().map(|r| r.1).collect();
    let rat_p: Vec<u32> = result.simple_ratios.iter().map(|r| r.2).collect();
    let rat_q: Vec<u32> = result.simple_ratios.iter().map(|r| r.3).collect();
    dict.set_item("ratio_feat_i", rat_i)?;
    dict.set_item("ratio_feat_j", rat_j)?;
    dict.set_item("ratio_p", rat_p)?;
    dict.set_item("ratio_q", rat_q)?;
    dict.set_item("n_simple_ratios", result.simple_ratios.len())?;
    dict.set_item("n_proportion_chains", result.proportion_chains.len())?;
    Ok(dict)
}

/// Compass lens scan (curvature detection)
#[pyfunction]
#[pyo3(signature = (data,))]
fn compass_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = compass::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("mean_curvature", result.mean_curvature)?;
    let hc_idx: Vec<usize> = result.high_curvature_regions.iter().map(|h| h.0).collect();
    let hc_val: Vec<f64> = result.high_curvature_regions.iter().map(|h| h.1).collect();
    dict.set_item("high_curvature_indices", hc_idx)?;
    dict.set_item("high_curvature_values", PyArray1::from_vec(py, hc_val))?;
    let circ_center: Vec<usize> = result.circular_structures.iter().map(|c| c.0).collect();
    let circ_radius: Vec<f64> = result.circular_structures.iter().map(|c| c.1).collect();
    let circ_n: Vec<usize> = result.circular_structures.iter().map(|c| c.2).collect();
    dict.set_item("circular_centers", circ_center)?;
    dict.set_item("circular_radii", PyArray1::from_vec(py, circ_radius))?;
    dict.set_item("circular_n_points", circ_n)?;
    Ok(dict)
}

/// Mirror lens scan (symmetry detection)
#[pyfunction]
#[pyo3(signature = (data,))]
fn mirror_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = mirror::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("reflection_scores", PyArray1::from_vec(py, result.reflection_scores))?;
    dict.set_item("overall_symmetry", result.overall_symmetry)?;
    let bs_idx: Vec<usize> = result.broken_symmetries.iter().map(|b| b.0).collect();
    let bs_val: Vec<f64> = result.broken_symmetries.iter().map(|b| b.1).collect();
    dict.set_item("broken_symmetry_indices", bs_idx)?;
    dict.set_item("broken_symmetry_scores", PyArray1::from_vec(py, bs_val))?;
    Ok(dict)
}

/// Scale lens scan (power law / fractal)
#[pyfunction]
#[pyo3(signature = (data,))]
fn scale_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = scale::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("power_law_exponents", PyArray1::from_vec(py, result.power_law_exponents))?;
    dict.set_item("fractal_dimension", result.fractal_dimension)?;
    dict.set_item("hurst_exponent", result.hurst_exponent)?;
    Ok(dict)
}

/// Quantum microscope scan (density matrix analysis)
#[pyfunction]
#[pyo3(signature = (data,))]
fn quantum_microscope_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = quantum_microscope::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("purity", result.purity)?;
    dict.set_item("von_neumann_entropy", result.von_neumann_entropy)?;
    dict.set_item("coherence", result.coherence)?;
    dict.set_item("decoherence_rate", result.decoherence_rate)?;
    Ok(dict)
}

/// Stability lens scan (Lyapunov + perturbation resilience)
#[pyfunction]
#[pyo3(signature = (data,))]
fn stability_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = stability::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("lyapunov_exponent", result.lyapunov_exponent)?;
    dict.set_item("resilience", result.resilience)?;
    dict.set_item("mean_recovery_time", result.mean_recovery_time)?;
    dict.set_item("basin_stability", PyArray1::from_vec(py, result.basin_stability))?;
    dict.set_item("variance_ratio", result.variance_ratio)?;
    Ok(dict)
}

/// Network lens scan (correlation graph analysis)
#[pyfunction]
#[pyo3(signature = (data,))]
fn network_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = network::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("n_edges", result.n_edges)?;
    dict.set_item("degree_centrality", PyArray1::from_vec(py, result.degree_centrality))?;
    dict.set_item("n_communities", result.n_communities)?;
    dict.set_item("community_ids", result.community_ids)?;
    dict.set_item("hub_indices", result.hub_indices)?;
    dict.set_item("density", result.density)?;
    dict.set_item("clustering_coefficient", result.clustering_coefficient)?;
    dict.set_item("avg_path_length", result.avg_path_length)?;
    Ok(dict)
}

/// Memory lens scan (autocorrelation + recurrence)
#[pyfunction]
#[pyo3(signature = (data,))]
fn memory_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = memory_lens::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("acf_decay_times", PyArray1::from_vec(py, result.acf_decay_times))?;
    dict.set_item("mean_memory_depth", result.mean_memory_depth)?;
    dict.set_item("delayed_mi", PyArray1::from_vec(py, result.delayed_mi))?;
    dict.set_item("recurrence_rate", result.recurrence_rate)?;
    dict.set_item("determinism", result.determinism)?;
    dict.set_item("max_diagonal_length", result.max_diagonal_length)?;
    Ok(dict)
}

/// Recursion lens scan (self-reference & feedback loops)
#[pyfunction]
#[pyo3(signature = (data,))]
fn recursion_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = recursion::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("self_similarity", result.self_similarity)?;
    dict.set_item("mean_self_similarity", result.mean_self_similarity)?;
    let fb_i: Vec<usize> = result.feedback_loops.iter().map(|f| f.0).collect();
    let fb_j: Vec<usize> = result.feedback_loops.iter().map(|f| f.1).collect();
    let fb_s: Vec<f64> = result.feedback_loops.iter().map(|f| f.2).collect();
    dict.set_item("feedback_loop_i", fb_i)?;
    dict.set_item("feedback_loop_j", fb_j)?;
    dict.set_item("feedback_loop_strength", PyArray1::from_vec(py, fb_s))?;
    dict.set_item("n_fixed_points", result.n_fixed_points)?;
    dict.set_item("fixed_point_indices", result.fixed_point_indices)?;
    dict.set_item("recurrence_depth", result.recurrence_depth)?;
    Ok(dict)
}

/// Boundary lens scan (phase transitions & edge detection)
#[pyfunction]
#[pyo3(signature = (data,))]
fn boundary_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = boundary::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("n_boundary_points", result.n_boundary_points)?;
    dict.set_item("boundary_indices", result.boundary_indices)?;
    dict.set_item("boundary_strengths", PyArray1::from_vec(py, result.boundary_strengths))?;
    dict.set_item("n_phase_transitions", result.n_phase_transitions)?;
    dict.set_item("transition_indices", result.transition_indices)?;
    dict.set_item("mean_sharpness", result.mean_sharpness)?;
    Ok(dict)
}

/// Multiscale lens scan (wavelet + multifractal)
#[pyfunction]
#[pyo3(signature = (data,))]
fn multiscale_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result = multiscale::scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("wavelet_energy", PyArray1::from_vec(py, result.wavelet_energy))?;
    dict.set_item("dominant_scale", result.dominant_scale)?;
    dict.set_item("multifractal_dq", PyArray1::from_vec(py, result.multifractal_dq))?;
    dict.set_item("multifractal_width", result.multifractal_width)?;
    dict.set_item("scale_entropy", PyArray1::from_vec(py, result.scale_entropy))?;
    dict.set_item("n_significant_scales", result.n_significant_scales)?;
    Ok(dict)
}

/// Full scan: run multiple lenses and compute consensus on anomalies.
///
/// scan_mode:
///   "basic"     → consciousness + topology + causal (3 lenses)
///   "stability" → stability + boundary + thermo
///   "structure" → network + topology + recursion
///   "temporal"  → memory + wave + causal + multiscale
///   "scale"     → multiscale + scale + recursion
///   "full"      → all 22 lenses
///
/// Returns dict with each lens_name → result_dict, plus "_consensus" → {
///   "anomaly_indices": confirmed anomalies (3+ lenses agree),
///   "n_lenses_agree": count per confirmed index,
///   "total_lenses_run": number of lenses executed,
///   "lens_names": list of lens names run,
/// }
#[pyfunction]
#[pyo3(signature = (data, scan_mode="basic"))]
fn full_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
    scan_mode: &str,
) -> PyResult<Bound<'py, PyDict>> {
    let (flat, n_samples, n_features) = extract_data(&data);
    let result_dict = PyDict::new(py);

    // Determine which lenses to run based on scan_mode
    let lens_names: Vec<&str> = match scan_mode {
        "basic" => vec!["consciousness", "topology", "causal"],
        "stability" => vec!["stability", "boundary", "thermo"],
        "structure" => vec!["network", "topology", "recursion"],
        "temporal" => vec!["memory", "wave", "causal", "multiscale"],
        "scale" => vec!["multiscale", "scale", "recursion"],
        "full" => vec![
            "consciousness", "topology", "causal", "gravity", "thermo",
            "wave", "evolution", "info", "quantum", "em",
            "ruler", "triangle", "compass", "mirror", "scale",
            "quantum_microscope", "stability", "network", "memory",
            "recursion", "boundary", "multiscale",
        ],
        _ => {
            return Err(pyo3::exceptions::PyValueError::new_err(
                format!("Unknown scan_mode '{}'. Use: basic, stability, structure, temporal, scale, full", scan_mode)
            ));
        }
    };

    // Track anomaly indices per lens for consensus
    let mut all_anomaly_indices: Vec<Vec<usize>> = Vec::new();

    for &name in &lens_names {
        let lens_dict = PyDict::new(py);
        let mut anomaly_idx: Vec<usize> = Vec::new();

        match name {
            "consciousness" => {
                let mut lens = consciousness::ConsciousnessLens::new(
                    64, n_features.max(128), 12, 300, 0.014);
                let r = lens.scan(&flat, n_samples, n_features);
                lens_dict.set_item("phi_iit", r.phi_iit)?;
                lens_dict.set_item("phi_proxy", r.phi_proxy)?;
                lens_dict.set_item("n_clusters", r.n_clusters)?;
                lens_dict.set_item("steps_run", r.steps_run)?;
                let anom_i: Vec<f64> = r.anomalies.iter().map(|a| a.0 as f64).collect();
                let anom_s: Vec<f64> = r.anomalies.iter().map(|a| a.1).collect();
                anomaly_idx = r.anomalies.iter().map(|a| a.0).collect();
                lens_dict.set_item("anomaly_indices", PyArray1::from_vec(py, anom_i))?;
                lens_dict.set_item("anomaly_scores", PyArray1::from_vec(py, anom_s))?;
            }
            "topology" => {
                let r = topology::scan(&flat, n_samples, n_features, 100, 0.014);
                lens_dict.set_item("betti_0", r.betti_0)?;
                lens_dict.set_item("betti_1", r.betti_1)?;
                lens_dict.set_item("n_components", r.n_components)?;
                lens_dict.set_item("n_holes", r.n_holes)?;
                lens_dict.set_item("optimal_scale", r.optimal_scale)?;
                lens_dict.set_item("n_persistence_pairs", r.persistence_pairs.len())?;
                lens_dict.set_item("n_phase_transitions", r.phase_transitions.len())?;
                // topology doesn't produce sample-level anomaly indices
            }
            "causal" => {
                let r = causal::scan(&flat, n_samples, n_features, 5, 16, 0.1);
                lens_dict.set_item("n_features", r.n_features)?;
                lens_dict.set_item("n_causal_pairs", r.causal_pairs.len())?;
                let causes: Vec<usize> = r.causal_pairs.iter().map(|p| p.cause).collect();
                let effects: Vec<usize> = r.causal_pairs.iter().map(|p| p.effect).collect();
                let strengths: Vec<f64> = r.causal_pairs.iter().map(|p| p.strength).collect();
                lens_dict.set_item("causes", causes)?;
                lens_dict.set_item("effects", effects)?;
                lens_dict.set_item("strengths", strengths)?;
                // causal pairs are feature-level, not sample-level anomalies
            }
            "gravity" => {
                let r = gravity::scan(&flat, n_samples, n_features);
                lens_dict.set_item("n_attractors", r.n_attractors)?;
                lens_dict.set_item("attractors", PyArray1::from_vec(py, r.attractors))?;
                lens_dict.set_item("basins", r.basins.clone())?;
                // High-energy samples are anomalous (top 5% of energy landscape)
                if !r.energy_landscape.is_empty() {
                    let mut sorted_e: Vec<f64> = r.energy_landscape.clone();
                    sorted_e.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
                    let threshold_idx = (sorted_e.len() as f64 * 0.95) as usize;
                    let threshold = sorted_e.get(threshold_idx.min(sorted_e.len() - 1)).copied().unwrap_or(f64::MAX);
                    for (i, &e) in r.energy_landscape.iter().enumerate() {
                        if e >= threshold { anomaly_idx.push(i); }
                    }
                }
            }
            "thermo" => {
                let r = thermo::scan(&flat, n_samples, n_features);
                lens_dict.set_item("total_entropy", r.total_entropy)?;
                lens_dict.set_item("free_energy", r.free_energy)?;
                lens_dict.set_item("critical_temperature", r.critical_temperature)?;
                lens_dict.set_item("n_phase_transitions", r.phase_transitions.len())?;
                // phase transitions are global, not sample-level
            }
            "wave" => {
                let r = wave::scan(&flat, n_samples, n_features);
                lens_dict.set_item("dominant_frequencies", PyArray1::from_vec(py, r.dominant_frequencies))?;
                let _coh_v: Vec<f64> = r.coherences.iter().map(|c| c.2).collect();
                lens_dict.set_item("n_coherences", r.coherences.len())?;
                lens_dict.set_item("n_resonances", r.resonances.len())?;
                // wave is feature-level
            }
            "evolution" => {
                let r = evolution::scan(&flat, n_samples, n_features);
                lens_dict.set_item("n_peaks", r.peaks.len())?;
                lens_dict.set_item("n_niches", r.niches.len())?;
                // peaks are sample indices (fitness peaks)
                anomaly_idx = r.peaks.clone();
            }
            "info" => {
                let r = info::scan(&flat, n_samples, n_features);
                lens_dict.set_item("entropy_per_feature", PyArray1::from_vec(py, r.entropy_per_feature))?;
                lens_dict.set_item("lz_complexity", PyArray1::from_vec(py, r.lz_complexity))?;
                // feature-level
            }
            "quantum" => {
                let r = quantum::scan(&flat, n_samples, n_features);
                let sup_idx: Vec<usize> = r.superposed_samples.iter().map(|s| s.0).collect();
                lens_dict.set_item("n_entanglement_pairs", r.entanglement_pairs.len())?;
                lens_dict.set_item("n_tunneling_paths", r.tunneling_paths.len())?;
                lens_dict.set_item("n_superposed", sup_idx.len())?;
                anomaly_idx = sup_idx;
            }
            "em" => {
                let r = em::scan(&flat, n_samples, n_features);
                let src_idx: Vec<usize> = r.sources.iter().map(|s| s.0).collect();
                let snk_idx: Vec<usize> = r.sinks.iter().map(|s| s.0).collect();
                lens_dict.set_item("n_sources", src_idx.len())?;
                lens_dict.set_item("n_sinks", snk_idx.len())?;
                anomaly_idx.extend(src_idx);
                anomaly_idx.extend(snk_idx);
            }
            "ruler" => {
                let r = ruler::scan(&flat, n_samples, n_features);
                lens_dict.set_item("effective_dim", r.effective_dim)?;
                lens_dict.set_item("n_orthogonal_groups", r.orthogonal_groups.len())?;
                // feature-level
            }
            "triangle" => {
                let r = triangle::scan(&flat, n_samples, n_features);
                lens_dict.set_item("n_simple_ratios", r.simple_ratios.len())?;
                lens_dict.set_item("n_proportion_chains", r.proportion_chains.len())?;
                // feature-level
            }
            "compass" => {
                let r = compass::scan(&flat, n_samples, n_features);
                lens_dict.set_item("mean_curvature", r.mean_curvature)?;
                let hc_idx: Vec<usize> = r.high_curvature_regions.iter().map(|h| h.0).collect();
                lens_dict.set_item("n_high_curvature", hc_idx.len())?;
                anomaly_idx = hc_idx;
            }
            "mirror" => {
                let r = mirror::scan(&flat, n_samples, n_features);
                lens_dict.set_item("overall_symmetry", r.overall_symmetry)?;
                let bs_idx: Vec<usize> = r.broken_symmetries.iter().map(|b| b.0).collect();
                lens_dict.set_item("n_broken_symmetries", bs_idx.len())?;
                anomaly_idx = bs_idx;
            }
            "scale" => {
                let r = scale::scan(&flat, n_samples, n_features);
                lens_dict.set_item("fractal_dimension", r.fractal_dimension)?;
                lens_dict.set_item("hurst_exponent", r.hurst_exponent)?;
                // global metrics, no sample-level
            }
            "quantum_microscope" => {
                let r = quantum_microscope::scan(&flat, n_samples, n_features);
                lens_dict.set_item("purity", r.purity)?;
                lens_dict.set_item("von_neumann_entropy", r.von_neumann_entropy)?;
                lens_dict.set_item("coherence", r.coherence)?;
                lens_dict.set_item("decoherence_rate", r.decoherence_rate)?;
                // global metrics
            }
            "stability" => {
                let r = stability::scan(&flat, n_samples, n_features);
                lens_dict.set_item("lyapunov_exponent", r.lyapunov_exponent)?;
                lens_dict.set_item("resilience", r.resilience)?;
                lens_dict.set_item("mean_recovery_time", r.mean_recovery_time)?;
                lens_dict.set_item("variance_ratio", r.variance_ratio)?;
                // global metrics
            }
            "network" => {
                let r = network::scan(&flat, n_samples, n_features);
                lens_dict.set_item("n_edges", r.n_edges)?;
                lens_dict.set_item("n_communities", r.n_communities)?;
                lens_dict.set_item("density", r.density)?;
                lens_dict.set_item("clustering_coefficient", r.clustering_coefficient)?;
                lens_dict.set_item("avg_path_length", r.avg_path_length)?;
                // hub_indices are feature-level hubs
                anomaly_idx = r.hub_indices.clone();
            }
            "memory" => {
                let r = memory_lens::scan(&flat, n_samples, n_features);
                lens_dict.set_item("mean_memory_depth", r.mean_memory_depth)?;
                lens_dict.set_item("recurrence_rate", r.recurrence_rate)?;
                lens_dict.set_item("determinism", r.determinism)?;
                lens_dict.set_item("max_diagonal_length", r.max_diagonal_length)?;
                // global metrics
            }
            "recursion" => {
                let r = recursion::scan(&flat, n_samples, n_features);
                lens_dict.set_item("self_similarity", r.self_similarity)?;
                lens_dict.set_item("mean_self_similarity", r.mean_self_similarity)?;
                lens_dict.set_item("n_fixed_points", r.n_fixed_points)?;
                lens_dict.set_item("recurrence_depth", r.recurrence_depth)?;
                anomaly_idx = r.fixed_point_indices.clone();
            }
            "boundary" => {
                let r = boundary::scan(&flat, n_samples, n_features);
                lens_dict.set_item("n_boundary_points", r.n_boundary_points)?;
                lens_dict.set_item("n_phase_transitions", r.n_phase_transitions)?;
                lens_dict.set_item("mean_sharpness", r.mean_sharpness)?;
                anomaly_idx = r.boundary_indices.clone();
                anomaly_idx.extend(r.transition_indices.iter());
            }
            "multiscale" => {
                let r = multiscale::scan(&flat, n_samples, n_features);
                lens_dict.set_item("dominant_scale", r.dominant_scale)?;
                lens_dict.set_item("multifractal_width", r.multifractal_width)?;
                lens_dict.set_item("n_significant_scales", r.n_significant_scales)?;
                // global metrics
            }
            _ => {}
        }

        lens_dict.set_item("_n_anomalies", anomaly_idx.len())?;
        result_dict.set_item(name, &lens_dict)?;
        all_anomaly_indices.push(anomaly_idx);
    }

    // Compute consensus: count how many lenses flag each sample index
    let mut index_counts: std::collections::HashMap<usize, usize> = std::collections::HashMap::new();
    for indices in &all_anomaly_indices {
        // Deduplicate within each lens
        let unique: std::collections::HashSet<usize> = indices.iter().copied().collect();
        for idx in unique {
            *index_counts.entry(idx).or_insert(0) += 1;
        }
    }

    // Confirmed anomalies: 3+ lenses agree (or all lenses if fewer than 3 run)
    let threshold = if lens_names.len() < 3 { lens_names.len() } else { 3 };
    let mut confirmed: Vec<(usize, usize)> = index_counts.into_iter()
        .filter(|&(_, count)| count >= threshold)
        .collect();
    confirmed.sort_by_key(|&(idx, _)| idx);

    let consensus = PyDict::new(py);
    let conf_indices: Vec<usize> = confirmed.iter().map(|c| c.0).collect();
    let conf_counts: Vec<usize> = confirmed.iter().map(|c| c.1).collect();
    consensus.set_item("anomaly_indices", conf_indices)?;
    consensus.set_item("n_lenses_agree", conf_counts)?;
    consensus.set_item("total_lenses_run", lens_names.len())?;
    let names_vec: Vec<String> = lens_names.iter().map(|s| s.to_string()).collect();
    consensus.set_item("lens_names", names_vec)?;
    result_dict.set_item("_consensus", &consensus)?;

    Ok(result_dict)
}

/// Fast mutual information between two 1D arrays
#[pyfunction]
#[pyo3(signature = (a, b, n_bins=16))]
fn fast_mutual_info<'py>(
    _py: Python<'py>,
    a: PyReadonlyArray2<'py, f64>,
    b: PyReadonlyArray2<'py, f64>,
    n_bins: usize,
) -> PyResult<f64> {
    let a_flat: Vec<f64> = a.as_array().iter().copied().collect();
    let b_flat: Vec<f64> = b.as_array().iter().copied().collect();
    Ok(mi::mutual_info(&a_flat, &b_flat, n_bins))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(consciousness_scan, m)?)?;
    m.add_function(wrap_pyfunction!(topology_scan, m)?)?;
    m.add_function(wrap_pyfunction!(causal_scan, m)?)?;
    m.add_function(wrap_pyfunction!(gravity_scan, m)?)?;
    m.add_function(wrap_pyfunction!(thermo_scan, m)?)?;
    m.add_function(wrap_pyfunction!(wave_scan, m)?)?;
    m.add_function(wrap_pyfunction!(evolution_scan, m)?)?;
    m.add_function(wrap_pyfunction!(info_scan, m)?)?;
    m.add_function(wrap_pyfunction!(quantum_scan, m)?)?;
    m.add_function(wrap_pyfunction!(em_scan, m)?)?;
    m.add_function(wrap_pyfunction!(ruler_scan, m)?)?;
    m.add_function(wrap_pyfunction!(triangle_scan, m)?)?;
    m.add_function(wrap_pyfunction!(compass_scan, m)?)?;
    m.add_function(wrap_pyfunction!(mirror_scan, m)?)?;
    m.add_function(wrap_pyfunction!(scale_scan, m)?)?;
    m.add_function(wrap_pyfunction!(quantum_microscope_scan, m)?)?;
    m.add_function(wrap_pyfunction!(stability_scan, m)?)?;
    m.add_function(wrap_pyfunction!(network_scan, m)?)?;
    m.add_function(wrap_pyfunction!(memory_scan, m)?)?;
    m.add_function(wrap_pyfunction!(recursion_scan, m)?)?;
    m.add_function(wrap_pyfunction!(boundary_scan, m)?)?;
    m.add_function(wrap_pyfunction!(multiscale_scan, m)?)?;
    m.add_function(wrap_pyfunction!(full_scan, m)?)?;
    m.add_function(wrap_pyfunction!(fast_mutual_info, m)?)?;
    Ok(())
}
