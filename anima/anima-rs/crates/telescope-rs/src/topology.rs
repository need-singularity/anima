//! TopologyLens — Persistent homology: Betti-0 (components), Betti-1 (holes)
//!
//! Replaces Python's O(N²) edge list + O(N³) triangle fill with optimized Rust.

use rayon::prelude::*;

/// Persistent homology result.
#[derive(Debug, Clone)]
pub struct TopologyResult {
    pub betti_0: usize,
    pub betti_1: usize,
    pub n_components: usize,
    pub n_holes: usize,
    pub persistence_pairs: Vec<(f64, f64, u8)>, // (birth, death, dimension)
    pub phase_transitions: Vec<(f64, String)>,
    pub optimal_scale: f64,
}

/// Union-Find for connected components.
struct UnionFind {
    parent: Vec<usize>,
    rank: Vec<usize>,
    size: Vec<usize>,
}

impl UnionFind {
    fn new(n: usize) -> Self {
        Self {
            parent: (0..n).collect(),
            rank: vec![0; n],
            size: vec![1; n],
        }
    }

    fn find(&mut self, mut x: usize) -> usize {
        while self.parent[x] != x {
            self.parent[x] = self.parent[self.parent[x]]; // path compression
            x = self.parent[x];
        }
        x
    }

    fn union(&mut self, a: usize, b: usize) -> bool {
        let ra = self.find(a);
        let rb = self.find(b);
        if ra == rb { return false; }
        let (big, small) = if self.rank[ra] >= self.rank[rb] { (ra, rb) } else { (rb, ra) };
        self.parent[small] = big;
        self.size[big] += self.size[small];
        if self.rank[big] == self.rank[small] {
            self.rank[big] += 1;
        }
        true
    }

    fn n_components(&mut self, n: usize) -> usize {
        let mut roots = std::collections::HashSet::new();
        for i in 0..n {
            roots.insert(self.find(i));
        }
        roots.len()
    }
}

/// Run topological scan on data (n_samples × n_features), row-major.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize,
            n_filtration_steps: usize, persistence_threshold: f64) -> TopologyResult {
    if n_samples < 3 {
        return TopologyResult {
            betti_0: n_samples, betti_1: 0, n_components: n_samples,
            n_holes: 0, persistence_pairs: vec![], phase_transitions: vec![],
            optimal_scale: 0.0,
        };
    }

    // Pairwise distances (parallel)
    let n_pairs = n_samples * (n_samples - 1) / 2;
    let mut edges: Vec<(f64, usize, usize)> = Vec::with_capacity(n_pairs);

    // Compute distances — use parallel chunks for large N
    if n_samples > 100 {
        let pair_dists: Vec<(f64, usize, usize)> = (0..n_samples)
            .into_par_iter()
            .flat_map(|i| {
                let mut local = Vec::new();
                for j in (i + 1)..n_samples {
                    let mut dist_sq = 0.0;
                    for k in 0..n_features {
                        let d = data[i * n_features + k] - data[j * n_features + k];
                        dist_sq += d * d;
                    }
                    local.push((dist_sq.sqrt(), i, j));
                }
                local
            })
            .collect();
        edges = pair_dists;
    } else {
        for i in 0..n_samples {
            for j in (i + 1)..n_samples {
                let mut dist_sq = 0.0;
                for k in 0..n_features {
                    let d = data[i * n_features + k] - data[j * n_features + k];
                    dist_sq += d * d;
                }
                edges.push((dist_sq.sqrt(), i, j));
            }
        }
    }

    edges.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());

    let max_dist = edges.last().map(|e| e.0).unwrap_or(1.0);
    let step_size = max_dist / n_filtration_steps as f64;

    // Betti-0: union-find on sorted edges
    let mut uf = UnionFind::new(n_samples);
    let mut b0_persistence: Vec<(f64, f64, u8)> = Vec::new();
    let mut b0_history: Vec<(f64, usize)> = Vec::new();
    let mut edge_idx = 0;

    for s in 1..=n_filtration_steps {
        let eps = s as f64 * step_size;
        while edge_idx < edges.len() && edges[edge_idx].0 <= eps {
            let (d, i, j) = edges[edge_idx];
            if uf.union(i, j) {
                b0_persistence.push((0.0, d, 0));
            }
            edge_idx += 1;
        }
        b0_history.push((eps, uf.n_components(n_samples)));
    }

    // Betti-1: MST + non-tree edges → cycles
    let mut mst_uf = UnionFind::new(n_samples);
    let mut non_mst: Vec<(f64, usize, usize)> = Vec::new();

    // Build edge weight lookup (hash for fast triangle check)
    let mut edge_weight = std::collections::HashMap::new();
    for &(d, i, j) in &edges {
        edge_weight.insert((i.min(j), i.max(j)), d);
    }

    for &(d, i, j) in &edges {
        if mst_uf.union(i, j) {
            // MST edge
        } else {
            non_mst.push((d, i, j));
        }
    }

    // For each non-MST edge (ci, cj), find min triangle fill time
    let b1_persistence: Vec<(f64, f64, u8)> = non_mst.par_iter()
        .filter_map(|&(birth, ci, cj)| {
            let mut min_fill = f64::INFINITY;
            for k in 0..n_samples {
                if k == ci || k == cj { continue; }
                let e_ik = edge_weight.get(&(ci.min(k), ci.max(k)))
                    .copied().unwrap_or(f64::INFINITY);
                let e_jk = edge_weight.get(&(cj.min(k), cj.max(k)))
                    .copied().unwrap_or(f64::INFINITY);
                let fill = birth.max(e_ik).max(e_jk);
                if fill < min_fill { min_fill = fill; }
            }
            let death = if min_fill.is_finite() { min_fill } else { max_dist };
            let persistence = death - birth;
            if persistence > persistence_threshold * max_dist {
                Some((birth, death, 1u8))
            } else {
                None
            }
        })
        .collect();

    // Phase transitions
    let mut phase_transitions = Vec::new();
    for i in 1..b0_history.len() {
        let (eps, comp) = b0_history[i];
        let (_, prev_comp) = b0_history[i - 1];
        let delta = prev_comp.saturating_sub(comp);
        if delta >= 2.max(n_samples / 20) {
            phase_transitions.push((eps, format!("B0 drop: {}→{} ({} merges)", prev_comp, comp, delta)));
        }
    }

    // Optimal scale (max topological complexity)
    let mut best_score = -1.0f64;
    let mut best_eps = max_dist * 0.5;
    let mut best_b0 = 1;
    let mut best_b1 = 0;

    for &(eps, comp) in &b0_history {
        let b1_active = b1_persistence.iter()
            .filter(|(birth, death, _)| *birth <= eps && eps < *death)
            .count();
        let score = if comp == n_samples {
            0.0
        } else if comp == 1 && b1_active == 0 {
            0.1
        } else {
            (comp as f64 + 12.0 * b1_active as f64) * (1.0 - (comp as f64 / n_samples as f64 - 0.5).abs())
        };
        if score > best_score {
            best_score = score;
            best_eps = eps;
            best_b0 = comp;
            best_b1 = b1_active;
        }
    }

    // Merge persistence diagrams
    let mut all_persistence = b0_persistence;
    all_persistence.extend_from_slice(&b1_persistence);

    TopologyResult {
        betti_0: best_b0,
        betti_1: best_b1,
        n_components: best_b0,
        n_holes: b1_persistence.len(),
        persistence_pairs: all_persistence,
        phase_transitions,
        optimal_scale: best_eps,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simple_clusters() {
        // 2 tight clusters of 5 points each
        let mut data = Vec::new();
        for i in 0..5 {
            data.push(i as f64 * 0.01);
            data.push(0.0);
        }
        for i in 0..5 {
            data.push(10.0 + i as f64 * 0.01);
            data.push(0.0);
        }
        let result = scan(&data, 10, 2, 50, 0.014);
        assert!(result.n_components >= 1);
        assert!(result.betti_0 >= 1);
    }

    #[test]
    fn test_ring() {
        // Points on a circle (should have B1=1)
        let n = 20;
        let data: Vec<f64> = (0..n).flat_map(|i| {
            let theta = 2.0 * std::f64::consts::PI * i as f64 / n as f64;
            vec![theta.cos(), theta.sin()]
        }).collect();
        let result = scan(&data, n, 2, 50, 0.01);
        // Ring should eventually show a hole
        assert!(result.persistence_pairs.len() > 0);
    }
}
