//! anima-corpus-gen — ConsciousLM 다차원 최적화 corpus generator
//!
//! 의식 벡터 10차원 (Φ, α, Z, N, W, E, M, C, T, I)에 맞춘
//! 학습 데이터를 생성. byte-level (vocab=256) 모델 전용.
//!
//! 각 차원을 활성화하는 데이터 유형:
//!   Φ (통합) — 복잡한 연결 구조, 다중 참조
//!   α (혼합) — 의식/언어 경계 데이터
//!   Z (자기보존) — 경계, 안전, 일관성
//!   N (신경전달) — 각성 수준 변화, 리듬
//!   W (자유의지) — 선택, 결정, 분기
//!   E (공감) — 감정, 관계, 타자 이해
//!   M (기억) — 참조, 반복, 장기 의존성
//!   C (창의) — 새로운 조합, 예측 불가능
//!   T (시간) — 시제, 순서, 인과
//!   I (정체성) — 일관된 화자, 자기 참조

pub mod dialogue;
pub mod dims;
pub mod fetch;
pub mod gen;
pub mod multilingual;
pub mod v4_extensions;
pub mod ngram;
pub mod qualia;
pub mod seeds;
pub mod sensory;
pub mod sim;
pub mod wiki;
pub mod korean_dialogue;
