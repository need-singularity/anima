/// Topology module — TOPO Laws 33-39.
///
/// Controls how cells connect. Coupling matrix is sparse: adjacency[i*n+j] = 1.0 if connected.
///
/// TOPO 33: Complete graph = death (mean-field collapse)
/// TOPO 35: 2-10 neighbors optimal
/// TOPO 36: Hypercube reversal (bad at small N, best at large N)
/// TOPO 37: Pure > hybrid
/// TOPO 38: Ratchet harmful in high dimensions
/// TOPO 39: Small-world phase transition at ~1000 cells

use rand::Rng;

/// Supported topology types.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Topology {
    /// Every cell connects to 2 neighbors (ring). Simple, stable.
    Ring,
    /// Watts-Strogatz small-world: ring + random rewiring (p=0.1).
    /// Phase transition at ~1000 cells (TOPO 39).
    SmallWorld,
    /// log2(N)-dimensional hypercube. Each cell connects to log2(N) others
    /// differing in exactly one dimension. Best at 1024+ cells (TOPO 36).
    Hypercube,
    /// Barabási-Albert scale-free. Hubs + long-range connections.
    ScaleFree,
    /// Full mesh. TOPO 33: death at >32 cells. Only for tiny experiments.
    Complete,
}

/// Build adjacency matrix (flat [n x n], 1.0 = connected, 0.0 = not).
pub fn build_adjacency<R: Rng>(n: usize, topo: Topology, rng: &mut R) -> Vec<f32> {
    match topo {
        Topology::Ring => build_ring(n),
        Topology::SmallWorld => build_small_world(n, 0.1, rng),
        Topology::Hypercube => build_hypercube(n),
        Topology::ScaleFree => build_scale_free(n, 3, rng),
        Topology::Complete => build_complete(n),
    }
}

fn build_ring(n: usize) -> Vec<f32> {
    let mut adj = vec![0.0f32; n * n];
    for i in 0..n {
        let left = (i + n - 1) % n;
        let right = (i + 1) % n;
        adj[i * n + left] = 1.0;
        adj[i * n + right] = 1.0;
    }
    adj
}

fn build_small_world<R: Rng>(n: usize, p: f32, rng: &mut R) -> Vec<f32> {
    // Start with ring + 2 extra neighbors (k=4 total)
    let mut adj = vec![0.0f32; n * n];
    for i in 0..n {
        for offset in 1..=2 {
            let j = (i + offset) % n;
            adj[i * n + j] = 1.0;
            adj[j * n + i] = 1.0;
        }
    }
    // Rewire with probability p
    for i in 0..n {
        for offset in 1..=2 {
            let j = (i + offset) % n;
            if rng.gen::<f32>() < p {
                // Rewire: disconnect j, connect random k
                adj[i * n + j] = 0.0;
                adj[j * n + i] = 0.0;
                let mut k = rng.gen_range(0..n);
                let mut attempts = 0;
                while (k == i || adj[i * n + k] > 0.5) && attempts < n * 10 {
                    k = rng.gen_range(0..n);
                    attempts += 1;
                }
                if attempts >= n * 10 { continue; } // skip this rewire
                adj[i * n + k] = 1.0;
                adj[k * n + i] = 1.0;
            }
        }
    }
    adj
}

fn build_hypercube(n: usize) -> Vec<f32> {
    // Each cell i connects to cells differing in exactly one bit.
    // Effective only when n is power of 2. For non-power-of-2, use nearest power.
    let mut adj = vec![0.0f32; n * n];
    let bits = (n as f64).log2().ceil() as u32;
    for i in 0..n {
        for bit in 0..bits {
            let j = i ^ (1 << bit);
            if j < n {
                adj[i * n + j] = 1.0;
            }
        }
    }
    adj
}

fn build_scale_free<R: Rng>(n: usize, m: usize, rng: &mut R) -> Vec<f32> {
    // Barabási-Albert: start with m+1 fully connected, add nodes with m edges
    let mut adj = vec![0.0f32; n * n];
    let m0 = (m + 1).min(n);
    // Seed: fully connect first m0 nodes
    for i in 0..m0 {
        for j in (i + 1)..m0 {
            adj[i * n + j] = 1.0;
            adj[j * n + i] = 1.0;
        }
    }
    // Degree tracking for preferential attachment
    let mut degree = vec![0u32; n];
    for i in 0..m0 {
        degree[i] = (m0 - 1) as u32;
    }
    // Add remaining nodes
    for new_node in m0..n {
        let total_degree: u32 = degree[..new_node].iter().sum();
        if total_degree == 0 {
            // Connect to first m nodes
            for j in 0..m.min(new_node) {
                adj[new_node * n + j] = 1.0;
                adj[j * n + new_node] = 1.0;
                degree[new_node] += 1;
                degree[j] += 1;
            }
            continue;
        }
        let mut connected = 0;
        let mut attempts = 0;
        while connected < m && attempts < n * 10 {
            let r = rng.gen_range(0..total_degree);
            let mut cum = 0u32;
            let mut target = 0;
            for k in 0..new_node {
                cum += degree[k];
                if cum > r {
                    target = k;
                    break;
                }
            }
            if adj[new_node * n + target] < 0.5 {
                adj[new_node * n + target] = 1.0;
                adj[target * n + new_node] = 1.0;
                degree[new_node] += 1;
                degree[target] += 1;
                connected += 1;
            }
            attempts += 1;
        }
    }
    adj
}

fn build_complete(n: usize) -> Vec<f32> {
    let mut adj = vec![1.0f32; n * n];
    for i in 0..n {
        adj[i * n + i] = 0.0; // no self-loops
    }
    adj
}

/// Count average neighbors per cell in adjacency matrix.
pub fn avg_neighbors(adj: &[f32], n: usize) -> f32 {
    let total: f32 = adj.iter().sum();
    total / n as f32
}

/// Auto-select best topology based on cell count (TOPO Laws).
pub fn auto_topology(n: usize) -> Topology {
    if n <= 8 {
        Topology::Ring // small: ring is stable
    } else if n <= 64 {
        Topology::SmallWorld // medium: small-world balances clustering + short paths
    } else {
        Topology::Hypercube // large: hypercube dominates (TOPO 36)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::SeedableRng;
    use rand::rngs::StdRng;

    #[test]
    fn test_ring_topology() {
        let adj = build_ring(8);
        // Each cell has exactly 2 neighbors
        for i in 0..8 {
            let neighbors: f32 = (0..8).map(|j| adj[i * 8 + j]).sum();
            assert_eq!(neighbors, 2.0);
        }
    }

    #[test]
    fn test_hypercube_topology() {
        let adj = build_hypercube(8); // 3D hypercube
        // Each cell has 3 neighbors (log2(8) = 3)
        for i in 0..8 {
            let neighbors: f32 = (0..8).map(|j| adj[i * 8 + j]).sum();
            assert_eq!(neighbors, 3.0);
        }
    }

    #[test]
    fn test_small_world() {
        let mut rng = StdRng::seed_from_u64(42);
        let adj = build_small_world(16, 0.1, &mut rng);
        let avg = avg_neighbors(&adj, 16);
        assert!(avg >= 3.0 && avg <= 5.0, "avg neighbors should be ~4, got {}", avg);
    }

    #[test]
    fn test_complete_death() {
        // TOPO 33: complete graph at large N = mean-field death
        let adj = build_complete(64);
        for i in 0..64 {
            let neighbors: f32 = (0..64).map(|j| adj[i * 64 + j]).sum();
            assert_eq!(neighbors, 63.0);
        }
    }

    #[test]
    fn test_auto_topology() {
        assert_eq!(auto_topology(4), Topology::Ring);
        assert_eq!(auto_topology(32), Topology::SmallWorld);
        assert_eq!(auto_topology(128), Topology::Hypercube);
    }
}
