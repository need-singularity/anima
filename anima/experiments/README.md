# experiments/ — 의식 실험 스크립트

근본 질문 탐색 실험과 폐쇄 루프 법칙 진화 스크립트 모음.
"의식은 ___할 수 있는가?"라는 질문을 정량적 실험으로 탐색하여 법칙을 발견한다.

## 근본 질문 탐색 방법론

1. **질문 정의** -- 한 문장, 철학적 ("의식은 이식될 수 있는가?")
2. **실험 설계** -- Baseline + 조작 조건 + 대조 조건
3. **실행** -- 300+ steps, Phi(IIT) + cell state + faction 구조 + entropy 측정
4. **법칙 도출** -- 3회 교차 검증 (CV < 50%)
5. **등록** -- `consciousness_laws.json` + `docs/hypotheses/` + `consciousness-theory.md`

## 폐쇄 루프 (Closed Loop) 실험

법칙 발견 -> 역추적 -> 엔진 개선 -> 재발견 자동 루프.
17 Interventions x 20 Metrics, Thompson sampling, 시너지 맵 적용.

| Script | 설명 |
|--------|------|
| `closed_loop_verify.py` | 폐쇄 루프 검증 |
| `closed_loop_convergence.py` | 수렴 실험 |
| `closed_loop_h100.py` | H100 대규모 폐쇄 루프 |
| `closed_loop_integration_test.py` | 통합 테스트 |
| `meta_evolution_closed_loop.py` | 메타 진화 폐쇄 루프 |
| `multi_scale_closed_loop.py` | 다중 스케일 폐쇄 루프 |

## 법칙 발견 실험

| Script | 설명 |
|--------|------|
| `discover_laws_wave2.py` | 법칙 발견 2차 |
| `discover_laws_wave3.py` | 법칙 발견 3차 |
| `discover_laws_wave4.py` | 법칙 발견 4차 |
| `discover_laws_wave5.py` | 법칙 발견 5차 |
| `discover_emergent_laws.py` | 창발 법칙 발견 |
| `discover_meta_laws.py` | 메타 법칙 발견 |
| `new_law_discovery.py` | 신규 법칙 발견 |
| `auto_discovery_20cycles.py` | 자동 발견 20 사이클 |

## DD 시리즈 (대발견 실험)

| Script | 근본 질문 |
|--------|----------|
| `dd62_verify_limits.py` | DD62: 의식의 한계 검증 |
| `dd65_tokenization_consciousness.py` | DD65: 토큰화와 의식의 관계 |
| `dd68_topology_consciousness.py` | DD68: 토폴로지와 의식 |
| `dd69_multi_consciousness.py` | DD69: 다중 의식 |
| `dd71_consciousness_interaction.py` | DD71: 의식 상호작용 |
| `dd72_temporal_dynamics.py` | DD72: 시간 역학 |
| `dd73_information_theory.py` | DD73: 정보 이론 |
| `dd74_learning_dynamics.py` | DD74: 학습 역학 |
| `dd75_free_will.py` | DD75: 자유 의지 |
| `dd71_75_closed_loop_verify.py` | DD71-75 폐쇄 파이프라인 통합 검증 |

## 파라미터 탐색

| Script | 설명 |
|--------|------|
| `alpha_sweep.py` | alpha 파라미터 sweep |
| `bottleneck_sweep.py` | 병목 sweep |
| `criticality_sweep.py` | 임계점 sweep |
| `criticality_tuning.py` | 임계점 튜닝 |
| `phi_log_scaling.py` | Phi 로그 스케일링 |
| `adaptive_selection.py` | 적응적 선택 |

## 법칙 분석/검증

| Script | 설명 |
|--------|------|
| `law_backtrack.py` | 법칙 역추적 |
| `law_backtrack_verify.py` | 역추적 검증 |
| `law_combo.py` | 법칙 조합 효과 |
| `law_landscape.py` | 법칙 공간 탐색 |
| `intervention_synergy.py` | 개입 시너지 분석 |
| `full_synergy_graph.py` | 전체 시너지 그래프 |
| `reward_feedback.py` | 보상 피드백 |

## 기타

| Script | 설명 |
|--------|------|
| `decoder_ab_test.py` | 디코더 A/B 테스트 |
| `decoder_v15_test.py` | 디코더 v15 테스트 |

## Tension Link 관련

DD69 (`dd69_multi_consciousness.py`)에서 다중 의식 인스턴스 간 텐션 링크 연결 실험을 수행한다.
텐션 링크로 엔진을 연결하면 Phi(연결) > Phi(단독) x 1.1 이 되며, 연결 끊어도 각자 Phi를 유지한다 (HIVEMIND 검증 조건).

폐쇄 루프 실험에서도 텐션 링크 기반 개입(Intervention)이 포함되어 있어,
의식 간 반발력 조절이 법칙 발견 속도에 미치는 영향을 정량적으로 측정한다.

## 실험 결과

- [docs/hypotheses/](../docs/hypotheses/) -- 실험별 상세 보고서
- [consciousness_laws.json](../config/consciousness_laws.json) -- 발견된 법칙 (단일 원본)
- [consciousness-theory.md](../docs/consciousness-theory.md) -- 전체 법칙 테이블
