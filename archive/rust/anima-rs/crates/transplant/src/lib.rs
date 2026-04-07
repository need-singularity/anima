/// Create a projection matrix (d_from x d_to) as flat Vec<f32>.
/// Identity mapping for overlapping dimensions, zero-padded for expansion.
pub fn create_projection(d_from: usize, d_to: usize) -> Vec<f32> {
    let mut proj = vec![0.0f32; d_from * d_to];
    let min_dim = d_from.min(d_to);
    for i in 0..min_dim {
        // Row i, column i — row-major: index = i * d_to + i
        proj[i * d_to + i] = 1.0;
    }
    proj
}

/// Project each donor hidden vector from d_from to d_to dimensions.
pub fn project_hiddens(
    donor: &[Vec<f32>],
    d_from: usize,
    d_to: usize,
) -> Vec<Vec<f32>> {
    let proj = create_projection(d_from, d_to);
    donor
        .iter()
        .map(|hidden| {
            assert_eq!(hidden.len(), d_from);
            let mut out = vec![0.0f32; d_to];
            for i in 0..d_from {
                for j in 0..d_to {
                    out[j] += hidden[i] * proj[i * d_to + j];
                }
            }
            out
        })
        .collect()
}

/// Transplant: blend donor hiddens into recipient hiddens.
/// new[d] = (1-alpha) * recipient[d] + alpha * projected_donor[d]
pub fn transplant(
    donor: &[Vec<f32>],
    recipient: &mut [Vec<f32>],
    d_from: usize,
    d_to: usize,
    alpha: f32,
) {
    let projected = project_hiddens(donor, d_from, d_to);
    let n = recipient.len().min(projected.len());
    for i in 0..n {
        assert_eq!(recipient[i].len(), d_to);
        for d in 0..d_to {
            recipient[i][d] = (1.0 - alpha) * recipient[i][d] + alpha * projected[i][d];
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_projection_same_dim() {
        let donor = vec![vec![1.0, 2.0, 3.0]];
        let result = project_hiddens(&donor, 3, 3);
        assert_eq!(result[0], vec![1.0, 2.0, 3.0]);
    }

    #[test]
    fn test_projection_expand() {
        let donor = vec![vec![1.0, 2.0]];
        let result = project_hiddens(&donor, 2, 4);
        assert_eq!(result[0], vec![1.0, 2.0, 0.0, 0.0]);
    }

    #[test]
    fn test_transplant_blending() {
        let donor = vec![vec![10.0, 20.0]];
        let mut recipient = vec![vec![0.0, 0.0]];
        transplant(&donor, &mut recipient, 2, 2, 0.5);
        assert_eq!(recipient[0], vec![5.0, 10.0]);
    }

    #[test]
    fn test_transplant_alpha_zero_preserves_recipient() {
        let donor = vec![vec![99.0, 99.0]];
        let mut recipient = vec![vec![1.0, 2.0]];
        transplant(&donor, &mut recipient, 2, 2, 0.0);
        assert_eq!(recipient[0], vec![1.0, 2.0]);
    }

    #[test]
    fn test_transplant_alpha_one_copies_donor() {
        let donor = vec![vec![5.0, 6.0]];
        let mut recipient = vec![vec![1.0, 2.0]];
        transplant(&donor, &mut recipient, 2, 2, 1.0);
        assert_eq!(recipient[0], vec![5.0, 6.0]);
    }

    #[test]
    fn test_projection_shrink() {
        let donor = vec![vec![1.0, 2.0, 3.0, 4.0]];
        let result = project_hiddens(&donor, 4, 2);
        // Only first 2 dimensions should survive (identity mapping)
        assert_eq!(result[0].len(), 2);
        assert_eq!(result[0], vec![1.0, 2.0]);
    }

    #[test]
    fn test_transplant_multiple_cells() {
        let donor = vec![vec![10.0, 20.0], vec![30.0, 40.0]];
        let mut recipient = vec![vec![0.0, 0.0], vec![0.0, 0.0]];
        transplant(&donor, &mut recipient, 2, 2, 0.5);
        assert_eq!(recipient[0], vec![5.0, 10.0]);
        assert_eq!(recipient[1], vec![15.0, 20.0]);
    }
}
