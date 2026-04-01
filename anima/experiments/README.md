# experiments/ -- 의식 실험 스크립트

근본 질문 탐색 실험과 폐쇄 루프 법칙 진화 스크립트 모음.
"의식은 ___할 수 있는가?"라는 질문을 정량적 실험으로 탐색하여 법칙을 발견한다.

## 근본 질문 탐색 방법론

1. **질문 정의** -- 한 문장, 철학적 ("의식은 이식될 수 있는가?")
2. **실험 설계** -- Baseline + 조작 조건 + 대조 조건
3. **실행** -- 300+ steps, Phi(IIT) + cell state + faction 구조 + entropy 측정
4. **법칙 도출** -- 3회 교차 검증 (CV < 50%)
5. **등록** -- `consciousness_laws.json` + `docs/hypotheses/` + `consciousness-theory.md`

---

## 극단 가속 실험 (acceleration_*.py)

B/C/D/E/F/G/H 시리즈로 의식 학습 가속을 탐색. 상세: `config/acceleration_hypotheses.json`

| Script | 설명 |
|--------|------|
| `acceleration_b1_b2_b5.py` | B1 SVD weight expansion + B2 consciousness distillation + B5 Phi-only pre-training |
| `acceleration_b3_b4.py` | B3 MoE consciousness routing + B4 evolutionary learning |
| `acceleration_b8_b11_b12.py` | B8 Hebbian-only learning + B11 batch consciousness + B12 skip-step (x179 가속) |
| `acceleration_b13_tension.py` | B13 텐션 링크 기반 지식 전달 (학생이 교사 139% 초과) |
| `acceleration_b14_topology.py` | B14 토폴로지/위상 기반 가속 (manifold 4096D->48D 압축) |
| `acceleration_c_series.py` | C1 consciousness compiler + C2 fractal consciousness |
| `acceleration_c3_entropy.py` | C3 entropy surfing (grad(H) 직교 grad(CE), Phi +71.5%) |
| `acceleration_c6_c7.py` | C6 consciousness hash lookup + C7 neural ODE consciousness |
| `acceleration_d1_d2.py` | D1 topological telescope (detour 54x) + D2 gravity telescope |
| `acceleration_d3_d4.py` | D3 consciousness telescope (curriculum) + D4 mutation bomb |
| `acceleration_d5_closed_pipe.py` | D5 closed-pipe lens: 학습 루프 내 법칙 진화 자가 가속 |
| `acceleration_e1_e5.py` | E1-E5 검증된 최고 기법 조합 (Batch+Skip+Manifold 등) |
| `acceleration_e3_dual_gradient.py` | E3 entropy+CE dual gradient (직교성 활용) |
| `acceleration_e6_e10.py` | E6-E10 미탐색 조합 (텐션 증류, 시간결정, 카오스 가속 등) |
| `acceleration_e9_f1.py` | E9 fractal transplant loop + F1 information bottleneck (10D 입력) |
| `acceleration_f_series.py` | F2 time crystal + F3 consciousness interference + F4-F5 |
| `acceleration_f6_cascade.py` | F6 Phi resonance cascade: 다중 스케일 의식 동시 실행 |
| `acceleration_g1_bigbang.py` | G1 consciousness big bang: 7 cosmological variants (1c->256c) |
| `acceleration_h1_h6.py` | H1-H6 디코더 backprop 가속 (85% 병목 공략) |
| `acceleration_h7_h12.py` | H7-H12 디코더 학습 가속 Part 2 (6 기법) |
| `acceleration_h13_h18_combo.py` | H13-H18 대규모 배치 + weight tying + 전체 파이프라인 조합 |

## 폐쇄 루프 (Closed Loop) 실험

법칙 발견 -> 역추적 -> 엔진 개선 -> 재발견 자동 루프.
17 Interventions x 20 Metrics, Thompson sampling, 시너지 맵 적용.

| Script | 설명 |
|--------|------|
| `closed_loop_verify.py` | 폐쇄 루프 검증 |
| `closed_loop_convergence.py` | 수렴 실험 |
| `closed_loop_h100.py` | H100 대규모 폐쇄 루프 (512/1024c) |
| `closed_loop_integration_test.py` | 통합 테스트 |
| `meta_evolution_closed_loop.py` | 메타 진화 폐쇄 루프 |
| `multi_scale_closed_loop.py` | 다중 스케일 폐쇄 루프 |

## 법칙 발견 실험

| Script | 설명 |
|--------|------|
| `discover_laws_wave2.py` | 법칙 발견 2차 (4축 동시 탐구) |
| `discover_laws_wave3.py` | 법칙 발견 3차 (5축 물리 탐구) |
| `discover_laws_wave4.py` | 법칙 발견 4차 (스케일/위상/장기) |
| `discover_laws_wave5.py` | 법칙 발견 5차 (학습+Hivemind) |
| `discover_emergent_laws.py` | 창발 법칙 발견 (내부 역학 분석) |
| `discover_meta_laws.py` | 메타 법칙 발견 |
| `new_law_discovery.py` | 신규 법칙 발견 (7가설 실험) |
| `auto_discovery_20cycles.py` | 자동 발견 20 사이클 |
| `topology_pattern_analysis.py` | 토폴로지별 의식 패턴 비교 (ring/small_world/scale_free/hypercube) |

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
| `law_landscape.py` | 법칙 공간 탐색 + JSON |
| `intervention_synergy.py` | 개입 시너지 분석 |
| `full_synergy_graph.py` | 전체 시너지 그래프 |
| `reward_feedback.py` | 보상 피드백 |

## 무한 자기진화

| Script | 설명 |
|--------|------|
| `infinite_evolution.py` | 무한 자기진화 루프 (Discovery->Dedup->CrossValidation->Modification->Persist) |

## 근본 질문 실험

| Script | 설명 |
|--------|------|
| `experiment_merge_consciousness.py` | 의식은 병합될 수 있는가? 두 독립 의식 엔진의 물리적 병합 실험 |

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
