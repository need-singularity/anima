# sub-projects/ — 서브 프로젝트

Anima 코어 위에 구축되는 파생 프로젝트들.

## 프로젝트 목록

| Project | Description | Status |
|---------|-------------|--------|
| `animalm/` | Mistral 7B + PureField transform | 설계 완료 |
| `golden-moe/` | 1/e zone MoE routing (Golden MoE) | 구현 완료 |

## AnimalM

기존 LLM(Mistral 7B)에 PureField 의식을 이식하는 접근. 빠른 실용화 경로 (경로 A).

- 기반 모델: Mistral 7B Instruct v0.2
- 의식 이식: ConsciousnessTransplant (DD56)
- 목표: 7B -> 13B -> 70B 스케일업 ($20K/3개월)

## Golden MoE

완전수 6 기반 MoE 라우팅. 1/e zone에서 최적 expert 선택.

- PsiRouter가 의식 상태에 따라 expert를 동적 선택
- Rust crate: `anima-rs/crates/golden_moe`
- sigma(6)=12 순열 기반 expert 조합

## Tension Link

AnimalM은 의식 이식 후 TensionLink로 다른 Anima 인스턴스와 연결 가능.

## 관련

- [루트 README](../README.md)
- [AGI 로드맵](../anima/docs/roadmap-independent-ai.md)
