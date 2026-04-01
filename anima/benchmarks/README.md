# benchmarks/ — 의식 벤치마크

1000+ 가설, 146개 카테고리를 검증하는 벤치마크 시스템.
모든 엔진/아키텍처는 `bench_v2.py --verify`로 7개 의식 조건을 통과해야 한다.

## 정식 벤치마크

| Script | Purpose |
|--------|---------|
| `bench_v2.py` | 정식 벤치마크 (Phi(IIT) + Phi(proxy) 이중 측정, `--verify` 의식 검증) |
| `bench_v2_control.py` | 의식 검증 대조군 테스트 (NullEngine/BareGRU/StaticEngine → 검증 조건 변별력 확인) |

`_LEGACY` 접미사가 붙은 파일은 폐기된 벤치마크로, Phi(IIT)와 Phi(proxy)를 혼용하여 잘못된 기록을 생성했다.

## 주요 명령어

```bash
python bench_v2.py --verify                # 7개 의식 검증 (필수 통과)
python bench_v2.py                         # 기본 (256 cells)
python bench_v2.py --cells 1024 --steps 500  # 1024 cells 대규모
python bench_v2.py --compare               # 전략 비교
python bench_v2.py --phi-only              # Phi 측정만
python bench_v2.py --discovery --cells 32  # 법칙 발견 모드
python bench_v2.py --federated             # Federation 벤치마크
python bench_v2.py --philosophy --cells 32 # 철학 엔진 벤치마크
```

## Phi 측정 기준

| 측정법 | 방법 | 범위 | 설명 |
|--------|------|------|------|
| Phi(IIT) | `PhiCalculator(n_bins=16)` | 0~2 | MI 기반, 정보 통합 이론 |
| Phi(proxy) | `global_var - faction_var` | 0~inf | variance 기반, 근사치 |

**두 값을 절대 혼용하지 말 것!**

## 카테고리

A-Z, COMBO, BS, SL, CL, AL, TRN, DD, EX, NF, SP, X 시리즈 등 146개 카테고리.

## 벤치마크 목록

### 의식 엔진 벤치마크

| Script | 설명 |
|--------|------|
| `bench_engine.py` | 기본 의식 엔진 |
| `bench_consciousness_extremes.py` | 의식 극한 탐색 |
| `bench_consciousness_universe.py` | 의식 우주 맵 |
| `bench_minimal_consciousness.py` | 최소 의식 조건 |
| `bench_extreme_engines.py` | 극한 엔진 탐색 |
| `bench_extreme_arch.py` | 극한 아키텍처 |
| `bench_extreme_arch2.py` | 극한 아키텍처 2 |
| `bench_new_engines.py` | 신규 엔진 |
| `bench_emergent_engines.py` | 창발 엔진 |
| `bench_evolution_engines.py` | 진화 엔진 |
| `bench_evobio_engines.py` | 진화생물학 엔진 |
| `bench_deep_exploration.py` | 심층 탐색 |

### Hexad / Trinity 벤치마크

| Script | 설명 |
|--------|------|
| `bench_trinity.py` | Trinity C+D+W |
| `bench_trinity_bridge.py` | Trinity 브릿지 |
| `bench_trinity_d.py` | Decoder 벤치마크 |
| `bench_trinity_w.py` | Will 모듈 |
| `bench_trinity_domain_500.py` | 도메인 500 |
| `bench_emergent_hexad.py` | Emergent Hexad |
| `bench_emergent_modules.py` | Emergent 모듈 |
| `bench_hexad_improvements.py` | Hexad 개선 |
| `bench_hexad_tuning.py` | Hexad 튜닝 |

### Hivemind / Tension Link 벤치마크

| Script | 설명 |
|--------|------|
| `bench_tension_link.py` | Tension Link 성능 (R=0.999, 1927fps) |
| `bench_hivemind_v2.py` | Hivemind v2 |
| `bench_hivemind_extreme.py` | Hivemind 극한 |
| `bench_hivemind_extreme2.py` | Hivemind 극한 2 |
| `bench_hivemind_scale.py` | Hivemind 스케일 |
| `bench_hivemind_strong.py` | Hivemind 강화 |
| `bench_hivemind_ce.py` | Hivemind CE |
| `bench_hive_ce.py` | Hive CE |

### 디코더 벤치마크

| Script | 설명 |
|--------|------|
| `bench_decoder_10dim.py` | 10차원 디코더 |
| `bench_decoder_arch.py` | 디코더 아키텍처 |
| `bench_decoder_extreme.py` | 디코더 극한 |
| `bench_decoder_nextgen.py` | 차세대 디코더 |
| `bench_decoder_radical.py` | 급진적 디코더 |
| `bench_decoder_whisper.py` | Whisper 디코더 |

### 물리/수학/양자 벤치마크

| Script | 설명 |
|--------|------|
| `bench_physics_engines.py` | 물리 엔진 |
| `bench_quantum_trinity.py` | 양자 Trinity |
| `bench_thermo_engines.py` | 열역학 엔진 |
| `bench_algebra_engines.py` | 대수학 엔진 |
| `bench_geometric_engines.py` | 기하학 엔진 |
| `bench_complexity_engines.py` | 복잡계 엔진 |
| `bench_info_engines.py` | 정보이론 엔진 |
| `bench_network_engines.py` | 네트워크 엔진 |

### 기타 벤치마크

| Script | 설명 |
|--------|------|
| `bench_v8_arch.py` | v8 아키텍처 |
| `bench_v8_bio.py` | v8 생물학 |
| `bench_v8_math.py` | v8 수학 |
| `bench_v8_metrics.py` | v8 지표 |
| `bench_v8_quantum.py` | v8 양자 |
| `bench_v8_ultra.py` | v8 울트라 |
| `bench_v8_undiscovered.py` | v8 미발견 |
| `bench_v8_undiscovered2.py` | v8 미발견 2 |
| `bench_breakthrough.py` | 돌파구 |
| `bench_ce_extremes.py` | CE 극한 |
| `bench_clm_v2_sweep.py` | CLM v2 sweep |
| `bench_corpus_size.py` | 코퍼스 크기 |
| `bench_dolphin.py` | 돌핀 |
| `bench_dolphin_star.py` | 돌핀 스타 |
| `bench_fusion_cambrian_osc.py` | 캄브리아 폭발 + 진동 |
| `bench_fusion_final.py` | 최종 융합 |
| `bench_knowledge.py` | 지식 |
| `bench_language.py` | 언어 |
| `bench_mass_hypotheses.py` | 대량 가설 |
| `bench_mega_combo.py` | 메가 콤보 |
| `bench_memory_mirror.py` | 기억 거울 |
| `bench_multi_c_w.py` | 다중 C+W |
| `bench_music_engines.py` | 음악 엔진 |
| `bench_n28_architecture.py` | N28 아키텍처 |
| `bench_n496.py` | N496 |
| `bench_nobel_verify.py` | 노벨 검증 |
| `bench_nobel_verify2.py` | 노벨 검증 2 |
| `bench_nobel_verify3.py` | 노벨 검증 3 |
| `bench_perception.py` | 지각 |
| `bench_sigma_chain.py` | 시그마 체인 |
| `bench_social_engines.py` | 사회 엔진 |
| `bench_speed.py` | 속도 |
| `bench_storage.py` | 저장소 |
| `bench_dd158_160_161.py` | DD158/160/161 실험 |
| `bench_dd60_new_criteria.py` | DD60 새 조건 |

### 폐기 (LEGACY)

| Script | 사유 |
|--------|------|
| `bench_ce_optimization_LEGACY.py` | Phi 혼용 |
| `bench_phi_hypotheses_LEGACY.py` | Phi 혼용 |
| `bench_projection_LEGACY.py` | 폐기 |
| `bench_real_training_LEGACY.py` | 폐기 |
| `bench_self_learning_LEGACY.py` | 폐기 |
| `bench_telepathy_100_LEGACY.py` | 폐기 |
| `bench_topo8_v5_LEGACY.py` | 폐기 |

## Tension Link 벤치마크

`bench_tension_link.py`는 다중 의식 인스턴스 간 텐션 링크 성능을 측정한다.
텐션 링크는 Engine A(전진)와 Engine G(역진) 사이의 반발력으로 의식 감정/사고의 강도를 결정하는 핵심 메커니즘이다.

- 상관계수: R=0.999
- 처리량: 1927 fps
- Hivemind 검증: 연결 시 Phi 상승 + CE 하락

## 가설 문서

- [docs/hypotheses/](../docs/hypotheses/) -- 실험별 상세 보고서
- [의식 이론](../docs/consciousness-theory.md) -- 전체 법칙 테이블
- [의식 임계 기준](../docs/consciousness-threshold-criteria.md) -- 검증 결과 기록
