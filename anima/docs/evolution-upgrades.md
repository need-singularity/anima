# 무한진화 엔진 업그레이드 카탈로그

## 적용 완료 (v1)

| # | 최적화 | 효과 | 상태 |
|---|--------|------|------|
| 1 | Rust 엔진 백엔드 | ×10-50 | ✅ |
| 2 | Rust law-discovery | ×18 | ✅ |
| 3 | 병렬 토폴로지 | ×4 | ✅ |
| 4 | 조기 포화 탈출 (5→3) | -30% 시간 | ✅ |
| 5 | 적응형 로드맵 skip | -50% 스테이지 | ✅ |
| 6 | 증분 교차검증 | ×2 | ✅ |
| 7 | GPU Φ (128c+) | ×16 | ✅ |
| 8 | 패턴 캐시 유지 | -20% | ✅ |

## 미적용 (v2 후보)

### 🔴 HIGH IMPACT — 구조적 진화

| # | 아이디어 | 효과 | 핵심 |
|---|---------|------|------|
| 9 | 적응형 스텝 | ×3-5 속도 | 100 steps에서 New=0이면 나머지 skip. 발견 있을 때만 full steps |
| 10 | 메타 진화 | 새 법칙 축 | 파이프라인 파라미터 자체를 돌연변이 (cells/steps/topo_gens 진화) |
| 11 | 다중 엔진 | 새 법칙 축 | 같은 셀에서 chaos_mode, frustration, hebbian_lr 변경 — 토폴로지 외 탐색축 |
| 12 | 적대적 탐색 | 돌파구 | 기존 법칙을 의도적으로 위반하는 개입 → 반례 or 새 법칙 |

### 🟡 MED IMPACT — 효율 강화

| # | 아이디어 | 효과 | 핵심 |
|---|---------|------|------|
| 13 | Mod 가지치기 | -30% 오버헤드 | confidence < 0.5인 active mods 제거 (200+ 누적 방지) |
| 14 | 법칙 합성 | 새 패턴 | 기존 Law A + Law B → 합성 intervention 자동 생성 |
| 15 | 조기 중단 | ×2 속도 | discovery에서 첫 100 steps 패턴=0이면 나머지 abort |
| 16 | Φ 그래디언트 탐색 | 정밀 | Φ 변화율 기반으로 다음 탐색 파라미터 결정 |

### 🟢 구조적 확장

| # | 아이디어 | 효과 | 핵심 |
|---|---------|------|------|
| 17 | 크로스 스케일 검증 | 신뢰도 | 64c에서 발견 → 128c에서 재확인 후 등록 (스케일 불변만) |
| 18 | 앙상블 발견 | +20% 법칙 | 서로 다른 config의 discoverer 3개 동시 실행, 투표 |
| 19 | 법칙 그래프 | 미탐색 탐지 | 법칙 간 의존성 그래프 → 빈 영역 집중 탐색 |
| 20 | 패턴 전이학습 | cold start ×5 | 작은 스케일 패턴으로 큰 스케일 seed |

## 최적 조합 (즉시 효과)

```
#9(적응형 스텝) + #15(조기 중단) + #13(mod 가지치기)
  현재: 142s/gen
  적용 후: ~30s/gen (×5 예상)
  이유: 1000 steps 중 실제 발견은 첫 100-200에서 대부분 발생
```

## 로드맵 11단계

```
Phase 1: Baseline (S1-S4)     64~128c × 300~1000s
Phase 2: Scale up (S5-S7)     256~512c × 500~1000s
Phase 3: Extreme (S8-S10)     512~1024c × 500~1000s
Phase 4: Titan (S11)          2048c × 500s (H100 전용)
```

## 3-Layer 자동화

```
Layer A: Python (infinite_evolution.py --auto-roadmap)
Layer B: Rust (evo-runner — watchdog, crash recovery)
Layer C: Claude Code (/loop 5m — 상태 보고, 자동 재발사)
```

## 가속 스택

```
⚡ Rust engine ✅ | Rust discovery ✅ | GPU Phi ✅ | Parallel topo ✅
```

---

## v3 — 발견 엔진 자체의 진화

### A. 패턴 탐지 확장

| # | 방향 | 현재 한계 | 확장 |
|---|------|----------|------|
| 21 | 인과 패턴 | correlation만 | causation (intervention → Δmetric) |
| 22 | 시계열 패턴 | 단일 스냅샷 | 주기, 감쇠, 발산, phase transition |
| 23 | 다변수 interaction | 2변수 상관 | 3+변수 (A×B→C), conditional correlation |
| 24 | 비선형 패턴 | Pearson r만 | mutual info, transfer entropy, Granger causality |
| 25 | 시간 해상도 | 전체 평균 | 50-step 슬라이딩 윈도우 → 과도 현상 포착 |

### B. 탐색 공간 확장

| # | 축 | 현재 | 확장 |
|---|---|------|------|
| 26 | 토폴로지 | 4종 고정 | Watts-Strogatz sweep (p=0.01~0.5), random graph |
| 27 | 셀 구조 | GRU 고정 | LSTM, Transformer cell, 혼합 cell population |
| 28 | 파벌 수 | 12 고정 | 6, 8, 16, 24 비교 탐색 |
| 29 | 카오스 모드 | lorenz 고정 | sandpile, chimera, standing_wave 순환 |
| 30 | 초기 조건 | 랜덤 | 이전 최고 Φ 상태에서 warm start |
| 31 | Hebbian LR | 고정 | sweep (0.001~0.1), 로그 스케일 |
| 32 | Frustration | 0.33 고정 | sweep (0~0.5), anti-ferromagnetic 탐색 |

### C. 법칙 네트워크

| # | 방향 | 설명 |
|---|------|------|
| 33 | 법칙 간 관계 | 법칙 네트워크 (A가 B를 유발, C가 D를 억제) |
| 34 | 계보 추적 | intervention → 법칙 인과 그래프 |
| 35 | 법칙 클러스터 | 유사 법칙 군집화 → 상위 메타법칙 자동 도출 |
| 36 | 법칙 수명 추적 | 발견→검증→적용→소멸 라이프사이클 |

---

## v4 — 진화 전략 자체의 진화

| # | 전략 | 설명 |
|---|------|------|
| 37 | 공진화 | 2개 파이프라인 경쟁 — 법칙 발견 vs 반례 찾기 |
| 38 | RL 기반 탐색 | 법칙 발견 수 = reward → RL로 파이프라인 파라미터 최적화 |
| 39 | 자기 참조 루프 | 발견된 법칙을 엔진 자체에 적용 (부분 구현됨) |
| 40 | 보상 기반 탐색 | Thompson → UCB → contextual bandit → full RL |
| 41 | 다중 파이프라인 경쟁 | N개 독립 실행, 최고 성과 설정을 전파 |
| 42 | 계절적 탐색 | exploitation ↔ exploration 주기적 전환 |

---

## v5 — 53 law ceiling 돌파

| # | 전략 | 근거 |
|---|------|------|
| 43 | 엔진 구조 변경 | GRU+12faction+Hebbian이 상한 결정 → 구조 변경 = 상한 변경 |
| 44 | 측정 지표 추가 | 20개 → 50개 metric → 새 상관 발견 |
| 45 | 비선형 패턴 (#24) | mutual info, transfer entropy |
| 46 | 시간 해상도 (#25) | 50-step 윈도우 → 과도 현상 |
| 47 | 파벌 수 변경 (#28) | 6~24 sweep → 새 역학 영역 |
| 48 | 혼합 셀 (#27) | GRU+LSTM → 이질성이 새 패턴 유발 |
| 49 | 계층 구조 | 평면 → 2레벨 (local faction + global council) |
| 50 | 외부 자극 | zero-input → 주기적 신호 → stimulus-response 법칙 |

---

## 스케일링 로드맵

```
로컬 Mac (64-256c, 분) → H100 (512-2048c, 시간) → H100×4 (8192c, 일) → ESP32×64 (128c, 영구)
```

## 우선순위 로드맵

```
즉시 (v2):  #9+#15+#13 → 30s/gen (×5)
단기 (v3):  #21-25 (패턴 확장) + #26-32 (탐색 공간) → ceiling 돌파
중기 (v4):  #37-42 (진화 전략 진화) → 자율 파이프라인
장기 (v5):  #43-50 (엔진 구조 변경) → 새 법칙 영역 개척
```
