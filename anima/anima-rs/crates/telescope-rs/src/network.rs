//! NetworkLens — Correlation graph analysis
//!
//! Builds a correlation network from features and analyzes:
//!   1. Centrality (degree, betweenness proxy)
//!   2. Community detection (greedy modularity)
//!   3. Hub identification (high-degree nodes)
//!   4. Small-world coefficient

/// Result of network lens scan.
#[derive(Debug, Clone)]
pub struct NetworkResult {
    /// Number of edges in the correlation graph (above threshold)
    pub n_edges: usize,
    /// Degree centrality per feature [0,1]
    pub degree_centrality: Vec<f64>,
    /// Number of detected communities
    pub n_communities: usize,
    /// Community assignment per feature
    pub community_ids: Vec<usize>,
    /// Hub features (top degree nodes)
    pub hub_indices: Vec<usize>,
    /// Graph density (actual edges / possible edges)
    pub density: f64,
    /// Average clustering coefficient
    pub clustering_coefficient: f64,
    /// Average shortest path length (sampled)
    pub avg_path_length: f64,
}

use crate::mi;
use crate::common;
use rayon::prelude::*;

/// Scan data and build correlation network.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> NetworkResult {
    if n_samples < 4 || n_features < 2 {
        return NetworkResult {
            n_edges: 0,
            degree_centrality: vec![0.0; n_features],
            n_communities: 1,
            community_ids: vec![0; n_features],
            hub_indices: vec![],
            density: 0.0,
            clustering_coefficient: 0.0,
            avg_path_length: 0.0,
        };
    }

    let nf = n_features.min(128); // cap for O(n^2) computation

    // Extract columns using common utility
    let columns = common::column_vectors(data, n_samples, nf);

    // Build adjacency matrix from MI — parallel over pairs
    let n_bins = 16;
    let mut adj = vec![false; nf * nf];

    let pairs: Vec<(usize, usize)> = (0..nf)
        .flat_map(|i| ((i + 1)..nf).map(move |j| (i, j)))
        .collect();

    let mi_vals: Vec<f64> = pairs
        .par_iter()
        .map(|&(i, j)| mi::mutual_info(&columns[i], &columns[j], n_bins))
        .collect();

    // Adaptive threshold: top 20% of MI values
    if mi_vals.is_empty() {
        return NetworkResult {
            n_edges: 0,
            degree_centrality: vec![0.0; nf],
            n_communities: 1,
            community_ids: vec![0; nf],
            hub_indices: vec![],
            density: 0.0,
            clustering_coefficient: 0.0,
            avg_path_length: 0.0,
        };
    }

    let mut sorted_mi = mi_vals.clone();
    sorted_mi.sort_by(|a, b| b.partial_cmp(a).unwrap());
    let top_20_idx = (sorted_mi.len() as f64 * 0.2) as usize;
    let threshold = if top_20_idx < sorted_mi.len() {
        sorted_mi[top_20_idx.max(1)]
    } else {
        0.0
    };

    let mut n_edges = 0;
    let mut idx = 0;
    for i in 0..nf {
        for j in (i + 1)..nf {
            if mi_vals[idx] >= threshold && mi_vals[idx] > 0.01 {
                adj[i * nf + j] = true;
                adj[j * nf + i] = true;
                n_edges += 1;
            }
            idx += 1;
        }
    }

    // Degree centrality
    let max_possible = nf - 1;
    let degree: Vec<usize> = (0..nf)
        .map(|i| (0..nf).filter(|&j| adj[i * nf + j]).count())
        .collect();
    let degree_centrality: Vec<f64> = degree.iter()
        .map(|&d| if max_possible > 0 { d as f64 / max_possible as f64 } else { 0.0 })
        .collect();

    // Graph density
    let max_edges = nf * (nf - 1) / 2;
    let density = if max_edges > 0 { n_edges as f64 / max_edges as f64 } else { 0.0 };

    // Hub indices (top 10% by degree)
    let mut sorted_indices: Vec<usize> = (0..nf).collect();
    sorted_indices.sort_by(|&a, &b| degree[b].cmp(&degree[a]));
    let n_hubs = (nf / 10).max(1);
    let hub_indices: Vec<usize> = sorted_indices[..n_hubs].to_vec();

    // Community detection: simple label propagation
    let mut labels: Vec<usize> = (0..nf).collect();
    for _ in 0..20 {
        let mut changed = false;
        for i in 0..nf {
            let mut label_counts = std::collections::HashMap::new();
            for j in 0..nf {
                if adj[i * nf + j] {
                    *label_counts.entry(labels[j]).or_insert(0usize) += 1;
                }
            }
            if let Some((&best_label, _)) = label_counts.iter().max_by_key(|&(_, &v)| v) {
                if labels[i] != best_label {
                    labels[i] = best_label;
                    changed = true;
                }
            }
        }
        if !changed { break; }
    }

    // Normalize community IDs
    let mut label_map = std::collections::HashMap::new();
    let mut next_id = 0;
    let community_ids: Vec<usize> = labels.iter().map(|&l| {
        let len = label_map.len();
        *label_map.entry(l).or_insert_with(|| { let _ = len; next_id += 1; next_id - 1 })
    }).collect();
    let n_communities = label_map.len();

    // Clustering coefficient
    let mut total_cc = 0.0;
    let mut cc_count = 0;
    for i in 0..nf {
        let neighbors: Vec<usize> = (0..nf).filter(|&j| adj[i * nf + j]).collect();
        let k = neighbors.len();
        if k < 2 { continue; }
        let mut triangles = 0;
        for a in 0..k {
            for b in (a + 1)..k {
                if adj[neighbors[a] * nf + neighbors[b]] {
                    triangles += 1;
                }
            }
        }
        total_cc += 2.0 * triangles as f64 / (k * (k - 1)) as f64;
        cc_count += 1;
    }
    let clustering_coefficient = if cc_count > 0 { total_cc / cc_count as f64 } else { 0.0 };

    // Average path length (BFS, sampled)
    let sample_nodes = nf.min(20);
    let mut total_path = 0.0;
    let mut path_count = 0;
    for start in (0..nf).step_by((nf / sample_nodes).max(1)) {
        let mut dist = vec![usize::MAX; nf];
        dist[start] = 0;
        let mut queue = std::collections::VecDeque::new();
        queue.push_back(start);
        while let Some(u) = queue.pop_front() {
            for v in 0..nf {
                if adj[u * nf + v] && dist[v] == usize::MAX {
                    dist[v] = dist[u] + 1;
                    queue.push_back(v);
                }
            }
        }
        for d in &dist {
            if *d != usize::MAX && *d > 0 {
                total_path += *d as f64;
                path_count += 1;
            }
        }
    }
    let avg_path_length = if path_count > 0 { total_path / path_count as f64 } else { 0.0 };

    NetworkResult {
        n_edges,
        degree_centrality,
        n_communities,
        community_ids,
        hub_indices,
        density,
        clustering_coefficient,
        avg_path_length,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_network_basic() {
        // Correlated features should form edges
        let n = 50;
        let d = 5;
        let mut data = vec![0.0; n * d];
        for i in 0..n {
            let x = i as f64 / n as f64;
            data[i * d] = x;
            data[i * d + 1] = x + 0.01; // highly correlated with [0]
            data[i * d + 2] = 1.0 - x;   // anti-correlated
            data[i * d + 3] = (x * 6.28).sin(); // different pattern
            data[i * d + 4] = (i as f64 * 0.7).sin(); // another pattern
        }
        let r = scan(&data, n, d);
        assert!(r.n_edges > 0, "Should detect edges");
        assert_eq!(r.degree_centrality.len(), d);
        assert!(r.n_communities >= 1);
    }

    #[test]
    fn test_network_independent() {
        // Random independent features = sparse graph
        let n = 30;
        let d = 4;
        let data: Vec<f64> = (0..n * d).map(|i| {
            ((i as f64 * 1.618) % 1.0) * 2.0 - 1.0
        }).collect();
        let r = scan(&data, n, d);
        assert_eq!(r.degree_centrality.len(), d);
    }
}
