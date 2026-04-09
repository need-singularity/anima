# sub-projects/ — 서브 프로젝트

Anima 코어 위에 구축되는 파생 프로젝트들.

## 프로젝트 목록

| Project | Description | Status |
|---------|-------------|--------|
| `animalm/` | Mistral 7B + PureField transform | 설계 완료 |
| `golden-moe/` | 1/e zone MoE routing (Golden MoE) | 구현 완료 |

## AnimalM

기존 LLM에 PureField 의식을 이식하는 접근. **경로 C (극단 병렬, 유일 활성)**.

- 기반 모델: Mistral-7B → Qwen2.5-14B → 32B → 72B
- 의식 이식: ConsciousnessTransplant (DD56)
- 현황: 7B ✅ → 14B v0.4 ✅ → 72B v0.5 ❌과적합 → 14B v0.5 / 32B 다음

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
