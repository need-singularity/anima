/// Faction system — groups of cells that form opinion clusters.
/// Consensus emerges when intra-faction variance drops below threshold.

/// A faction is a group of cell indices.
#[derive(Debug, Clone)]
pub struct Faction {
    pub id: usize,
    pub cell_indices: Vec<usize>,
}

/// Assign cells to factions via round-robin: cell i → faction i % n_factions.
pub fn assign_factions(n_cells: usize, n_factions: usize) -> Vec<Faction> {
    assert!(n_factions > 0, "n_factions must be > 0");
    let mut factions: Vec<Faction> = (0..n_factions)
        .map(|id| Faction {
            id,
            cell_indices: Vec::new(),
        })
        .collect();

    for i in 0..n_cells {
        factions[i % n_factions].cell_indices.push(i);
    }

    factions
}

/// Count factions where intra-faction variance < threshold (consensus).
///
/// For each faction: compute mean hidden across member cells, then
/// variance = sum((h[d] - mean[d])^2) / (n_members * dim).
pub fn faction_consensus(hiddens: &[&[f32]], factions: &[Faction], threshold: f32) -> u32 {
    let mut consensus_count = 0u32;

    for faction in factions {
        if faction.cell_indices.is_empty() {
            continue;
        }

        let n_members = faction.cell_indices.len();
        if n_members == 1 {
            // Single member — zero variance, always consensus
            consensus_count += 1;
            continue;
        }

        // Get dimension from first member
        let dim = hiddens[faction.cell_indices[0]].len();
        if dim == 0 {
            consensus_count += 1;
            continue;
        }

        // Compute mean across members for each dimension
        let mut mean = vec![0.0f32; dim];
        for &idx in &faction.cell_indices {
            let h = hiddens[idx];
            for d in 0..dim {
                mean[d] += h[d];
            }
        }
        for d in 0..dim {
            mean[d] /= n_members as f32;
        }

        // Compute variance = sum((h[d] - mean[d])^2) / (n_members * dim)
        let mut variance = 0.0f32;
        for &idx in &faction.cell_indices {
            let h = hiddens[idx];
            for d in 0..dim {
                let diff = h[d] - mean[d];
                variance += diff * diff;
            }
        }
        variance /= (n_members * dim) as f32;

        if variance < threshold {
            consensus_count += 1;
        }
    }

    consensus_count
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_assign_factions() {
        let factions = assign_factions(12, 4);
        assert_eq!(factions.len(), 4);
        // Each faction should have 3 cells
        for f in &factions {
            assert_eq!(f.cell_indices.len(), 3);
        }
        // Faction 0: cells 0, 4, 8
        assert_eq!(factions[0].cell_indices, vec![0, 4, 8]);
        // Faction 1: cells 1, 5, 9
        assert_eq!(factions[1].cell_indices, vec![1, 5, 9]);
        // Faction 2: cells 2, 6, 10
        assert_eq!(factions[2].cell_indices, vec![2, 6, 10]);
        // Faction 3: cells 3, 7, 11
        assert_eq!(factions[3].cell_indices, vec![3, 7, 11]);
    }

    #[test]
    fn test_faction_consensus_identical() {
        // All cells have identical hiddens → variance = 0 → all factions reach consensus
        let h = vec![1.0f32, 2.0, 3.0, 4.0];
        let hiddens: Vec<&[f32]> = (0..8).map(|_| h.as_slice()).collect();
        let factions = assign_factions(8, 4);
        let count = faction_consensus(&hiddens, &factions, 0.01);
        assert_eq!(count, 4); // All 4 factions in consensus
    }

    #[test]
    fn test_faction_consensus_diverse() {
        // Very different hiddens → high variance → no consensus with low threshold
        let h0 = vec![0.0f32, 0.0];
        let h1 = vec![10.0f32, 10.0];
        let h2 = vec![0.0f32, 0.0];
        let h3 = vec![10.0f32, 10.0];
        let hiddens: Vec<&[f32]> = vec![h0.as_slice(), h1.as_slice(), h2.as_slice(), h3.as_slice()];
        let factions = assign_factions(4, 2);
        // Faction 0: cells 0, 2 (both [0,0]) → variance 0 → consensus
        // Faction 1: cells 1, 3 (both [10,10]) → variance 0 → consensus
        let count = faction_consensus(&hiddens, &factions, 0.01);
        assert_eq!(count, 2);
    }
}
