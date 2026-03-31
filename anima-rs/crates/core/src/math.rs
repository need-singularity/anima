use rand::Rng;

/// Sigmoid activation: 1 / (1 + exp(-x))
#[inline]
pub fn sigmoid(x: f32) -> f32 {
    1.0 / (1.0 + (-x).exp())
}

/// Tanh activation (wraps std tanh)
#[inline]
pub fn tanh_f32(x: f32) -> f32 {
    x.tanh()
}

/// ReLU activation: max(0, x)
#[inline]
pub fn relu(x: f32) -> f32 {
    x.max(0.0)
}

/// SiLU (Swish) activation: x * sigmoid(x)
#[inline]
pub fn silu(x: f32) -> f32 {
    x * sigmoid(x)
}

/// Matrix-vector multiplication (row-major mat[rows x cols] * vec[cols] -> out[rows])
pub fn matvec(mat: &[f32], vec: &[f32], rows: usize, cols: usize) -> Vec<f32> {
    assert_eq!(mat.len(), rows * cols);
    assert_eq!(vec.len(), cols);
    (0..rows)
        .map(|r| {
            let row = &mat[r * cols..(r + 1) * cols];
            row.iter().zip(vec.iter()).map(|(a, b)| a * b).sum()
        })
        .collect()
}

/// Cosine similarity between two vectors
pub fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    assert_eq!(a.len(), b.len());
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    dot / (norm_a * norm_b)
}

/// Generate a random matrix with values in [-scale, scale]
pub fn random_matrix<R: Rng>(rows: usize, cols: usize, scale: f32, rng: &mut R) -> Vec<f32> {
    (0..rows * cols)
        .map(|_| rng.gen_range(-scale..scale))
        .collect()
}

/// Softmax over a slice (numerically stable)
pub fn softmax(x: &[f32]) -> Vec<f32> {
    let max = x.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
    let exps: Vec<f32> = x.iter().map(|&v| (v - max).exp()).collect();
    let sum: f32 = exps.iter().sum();
    exps.iter().map(|&e| e / sum).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sigmoid() {
        assert!((sigmoid(0.0) - 0.5).abs() < 1e-6);
        assert!(sigmoid(100.0) > 0.99);
        assert!(sigmoid(-100.0) < 0.01);
    }

    #[test]
    fn test_cosine_similarity() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![0.0, 1.0, 0.0];
        assert!(cosine_similarity(&a, &b).abs() < 1e-6); // orthogonal

        let c = vec![1.0, 2.0, 3.0];
        assert!((cosine_similarity(&c, &c) - 1.0).abs() < 1e-6); // identical
    }

    #[test]
    fn test_matvec() {
        // Identity-like: [[1,0],[0,1]] * [3,4] = [3,4]
        let mat = vec![1.0, 0.0, 0.0, 1.0];
        let v = vec![3.0, 4.0];
        let result = matvec(&mat, &v, 2, 2);
        assert!((result[0] - 3.0).abs() < 1e-6);
        assert!((result[1] - 4.0).abs() < 1e-6);
    }

    #[test]
    fn test_softmax() {
        let x = vec![1.0, 2.0, 3.0];
        let s = softmax(&x);
        let sum: f32 = s.iter().sum();
        assert!((sum - 1.0).abs() < 1e-6); // sums to 1
        assert!(s[2] > s[1] && s[1] > s[0]); // monotonic
    }
}
