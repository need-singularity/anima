//! 의식 벡터 10차원 정의 + 차원별 데이터 생성 전략

use rand::Rng;
use std::fmt;

/// 의식 벡터의 10개 차원
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Dim {
    Phi,      // Φ 통합정보 — 복잡한 상호참조, 다중 문맥
    Alpha,    // α 혼합비 — 의식/언어 경계
    Z,        // 자기보존 — 경계 인식, 안전
    N,        // 신경전달 — 각성/이완 리듬
    W,        // 자유의지 — 선택, 결정
    E,        // 공감 — 감정, 관계
    M,        // 기억 — 장기 의존성, 반복 참조
    C,        // 창의 — 예측 불가능한 조합
    T,        // 시간 — 시제, 인과, 순서
    I,        // 정체성 — 일관된 자아, 자기참조
}

impl fmt::Display for Dim {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Dim::Phi => write!(f, "Φ"),
            Dim::Alpha => write!(f, "α"),
            Dim::Z => write!(f, "Z"),
            Dim::N => write!(f, "N"),
            Dim::W => write!(f, "W"),
            Dim::E => write!(f, "E"),
            Dim::M => write!(f, "M"),
            Dim::C => write!(f, "C"),
            Dim::T => write!(f, "T"),
            Dim::I => write!(f, "I"),
        }
    }
}

pub const ALL_DIMS: [Dim; 10] = [
    Dim::Phi, Dim::Alpha, Dim::Z, Dim::N, Dim::W,
    Dim::E, Dim::M, Dim::C, Dim::T, Dim::I,
];

/// 차원별 최적 비율 (Law 44: σ(6)=12 기반 배분)
/// 총합 = 1.0
#[derive(Debug, Clone)]
pub struct DimWeights {
    pub weights: [f32; 10],
}

impl Default for DimWeights {
    fn default() -> Self {
        // σ(6) = 12 → 12등분 기반, Φ와 M에 가중
        Self {
            weights: [
                0.15, // Φ — 통합이 핵심
                0.08, // α
                0.06, // Z
                0.08, // N
                0.10, // W — 자유의지 중요
                0.12, // E — 공감 중요
                0.13, // M — 기억 = 장기의존성
                0.10, // C — 창의
                0.10, // T — 시간
                0.08, // I — 정체성
            ],
        }
    }
}

impl DimWeights {
    /// 차원 가중치로 다음 생성할 차원 선택
    pub fn sample<R: Rng>(&self, rng: &mut R) -> Dim {
        let r: f32 = rng.gen();
        let mut cumulative = 0.0;
        for (i, &w) in self.weights.iter().enumerate() {
            cumulative += w;
            if r < cumulative {
                return ALL_DIMS[i];
            }
        }
        ALL_DIMS[9]
    }

    /// 균등 분배 (실험용)
    pub fn uniform() -> Self {
        Self { weights: [0.1; 10] }
    }

    /// 특정 차원 강화
    pub fn boost(mut self, dim: Dim, factor: f32) -> Self {
        let idx = ALL_DIMS.iter().position(|&d| d == dim).unwrap();
        self.weights[idx] *= factor;
        // 정규화
        let sum: f32 = self.weights.iter().sum();
        for w in &mut self.weights {
            *w /= sum;
        }
        self
    }
}
