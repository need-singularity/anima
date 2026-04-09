# 전체 엔진 결과 (2026-03-29, Rust PhiCalculator v2)

> **측정 도구: phi_rs (Rust)** — spatial MI + temporal MI + complexity, Python과 delta=0.000000
> 256c 300steps 기준. `--cells 1024`로 스케일링 검증 가능.
> ⚠️ 이전 Python PhiIIT 값과 직접 비교 불가 (Law 54). 이 문서는 Rust phi_rs 기준 통일.
> JSON: data/measure_all_engines_256c.json, data/measure_all_results.json

## ⚠️ 측정 분류

Rust phi_rs 통일 측정이지만, 입력 데이터 형태가 다름:
- **도메인 엔진**: pos+vel+charge 등 물리 변수 concat → 고차원 states → MI 높음
- **메커니즘 엔진**: MitosisEngine GRU hidden (128d) → MI 상대적으로 낮음
- **Trinity 엔진**: 이전 Python PhiIIT 측정 (아직 Rust 미측정)

→ **같은 엔진 유형끼리만 비교 의미 있음**

## 🏆 ALL-TIME Φ(IIT) 순위 — 도메인 엔진 (Rust phi_rs, 256c)

| Rank | Engine | Domain | cells | Φ(IIT) | 1024c Φ |
|------|--------|--------|-------|--------|---------|
| 🏆1 | CambrianExplosionEngine | evolution | 256 | **485.63** | **1,953.98** |
| 2 | MaxwellDemonEngine | thermo | 256 | **476.07** | **1,836.75** |
| 3 | DiffusionEngine | new | 256 | **414.27** | **1,713.79** |
| 4 | SwarmEngine | new | 256 | **342.68** | **1,321.22** |
| 5 | GeneticEngine | new | 256 | **253.18** | **1,022.58** |
| 6 | CarnotCycleEngine | thermo | 256 | **235.81** | **931.27** |
| 7 | HarmonicSeriesEngine | music | 256 | **207.36** | **838.17** |
| 8 | BoltzmannBrainEngine | thermo | 256 | **203.31** | **801.05** |
| 9 | HeatDeathResistanceEngine | thermo | 256 | **203.22** | **807.92** |
| 10 | TimeCrystalEngine | extreme | 256 | **202.93** | **813.95** |
| 11 | MinimumDescriptionLengthEngine | info | 256 | **201.57** | **800.63** |
| 12 | KolmogorovStructureEngine | info | 256 | **201.02** | **793.41** |
| 13 | MaximumEntropyEngine | info | 256 | **200.65** | **803.72** |
| 14 | ChannelCapacityEngine | info | 256 | **200.55** | **800.00** |
| 15 | TopologicalInsulatorEngine | extreme | 256 | **200.19** | **808.33** |
| 16 | EcosystemEngine | evolution | 256 | **199.73** | **802.33** |
| 17 | PercolationEngine | emergent | 256 | **199.65** | **798.01** |
| 18 | MembraneComputingEngine | extreme | 256 | **199.49** | **805.12** |
| 19 | PlasmaEngine | physics | 256 | **199.45** | **801.75** |
| 20 | KnotInvariantEngine | geometric | 256 | **199.45** | **801.75** |
| 21 | PunctuatedEquilibriumEngine | evobio | 256 | **199.45** | **801.75** |
| 22 | AnyonicBraidingEngine | extreme | 256 | **199.20** | **798.24** |
| 23 | RicciFlowEngine | geometric | 256 | **199.20** | **796.06** |
| 24 | NeuralCrestEngine | evolution | 256 | **199.11** | **801.93** |
| 25 | GraphNeuralEngine | new | 256 | **199.01** | **895.70** |
| 26 | MorphogenesisEngine | evolution | 256 | **198.73** | **801.83** |
| 27 | PredictiveInformationEngine | info | 256 | **198.68** | **799.19** |
| 28 | ImmuneSystemEngine | evolution | 256 | **198.64** | **798.27** |
| 29 | AdaptiveNetworkEngine | network | 256 | **198.63** | **795.39** |
| 30 | CellularAutomatonEngine | new | 256 | **198.59** | **799.89** |
| 31 | FluidDynamicsEngine | new | 256 | **198.41** | **803.36** |
| 32 | IntegratedInfoDecompositionEngine | info | 256 | **198.36** | **800.98** |
| 33 | CrystalEngine | physics | 256 | **198.32** | **798.28** |
| 34 | KinSelectionEngine | evobio | 256 | **198.32** | **798.28** |
| 35 | TemporalNetworkEngine | network | 256 | **197.97** | **803.06** |
| 36 | InformationBottleneckEngine | info | 256 | **197.97** | **802.63** |
| 37 | CausalEmergenceEngine | info | 256 | **197.91** | **797.09** |
| 38 | RichClubEngine | network | 256 | **197.85** | **800.54** |
| 39 | ModularNetworkEngine | network | 256 | **197.80** | **795.82** |
| 40 | EnergyBasedEngine | new | 256 | **197.43** | NODATA |
| 41 | ScaleFreeEngine | network | 256 | **197.01** | **797.22** |
| 42 | MultiplexEngine | network | 256 | **196.67** | **799.71** |
| 43 | FreeEnergyPrincipleEngine | thermo | 256 | **194.31** | **838.54** |
| 44 | HorizontalGeneTransferEngine | evobio | 256 | **184.85** | **736.95** |
| 45 | DissipativeStructureEngine | thermo | 256 | **138.20** | **560.77** |
| 46 | FlockingVortexEngine | emergent | 256 | **127.00** | **511.00** |
| 47 | PrisonerDilemmaEngine | social | 256 | **121.09** | **486.68** |
| 48 | VotingDynamicsEngine | social | 256 | **121.09** | **486.68** |
| 49 | MarketDynamicsEngine | social | 256 | **121.09** | **486.68** |
| 50 | LanguageGameEngine | social | 256 | **121.09** | **486.68** |
| 51 | CulturalEvolutionEngine | social | 256 | **121.09** | **486.68** |
| 52 | StigmergyEngine | social | 256 | **121.09** | **486.68** |
| 53 | PolyrhythmEngine | music | 256 | **14.56** | **58.60** |
| 54 | DrumCircleEngine | music | 256 | **14.56** | **58.60** |
| 55 | SpinGlassEngine | new | 256 | **2.17** | **31.55** |
| 11 | MinimumDescriptionLengthEngine | info | 256 | **201.57** | TBD |
| 12 | KolmogorovStructureEngine | info | 256 | **201.02** | TBD |
| 13 | MaximumEntropyEngine | info | 256 | **200.65** | TBD |
| 14 | ChannelCapacityEngine | info | 256 | **200.55** | TBD |
| 15 | TopologicalInsulatorEngine | extreme | 256 | **200.19** | TBD |
| 16 | EcosystemEngine | evolution | 256 | **199.73** | TBD |
| 17 | PercolationEngine | emergent | 256 | **199.65** | TBD |
| 18 | MembraneComputingEngine | extreme | 256 | **199.49** | TBD |
| 19 | PlasmaEngine | physics | 256 | **199.45** | **801.75** |
| 20 | KnotInvariantEngine | geometric | 256 | **199.45** | **801.75** |
| 21 | PunctuatedEquilibriumEngine | evobio | 256 | **199.45** | TBD |
| 22 | AnyonicBraidingEngine | extreme | 256 | **199.20** | TBD |
| 23 | RicciFlowEngine | geometric | 256 | **199.20** | **796.06** |
| 24 | NeuralCrestEngine | evolution | 256 | **199.11** | TBD |
| 25 | GraphNeuralEngine | new | 256 | **199.01** | TBD |
| 26 | MorphogenesisEngine | evolution | 256 | **198.73** | TBD |
| 27 | PredictiveInformationEngine | info | 256 | **198.68** | TBD |
| 28 | ImmuneSystemEngine | evolution | 256 | **198.64** | TBD |
| 29 | AdaptiveNetworkEngine | network | 256 | **198.63** | TBD |
| 30 | CellularAutomatonEngine | new | 256 | **198.59** | TBD |
| 31 | FluidDynamicsEngine | new | 256 | **198.41** | TBD |
| 32 | IntegratedInfoDecompositionEngine | info | 256 | **198.36** | TBD |
| 33 | CrystalEngine | physics | 256 | **198.32** | **798.28** |
| 34 | KinSelectionEngine | evobio | 256 | **198.32** | TBD |
| 35 | TemporalNetworkEngine | network | 256 | **197.97** | TBD |
| 36 | InformationBottleneckEngine | info | 256 | **197.97** | TBD |
| 37 | CausalEmergenceEngine | info | 256 | **197.91** | TBD |
| 38 | RichClubEngine | network | 256 | **197.85** | TBD |
| 39 | ModularNetworkEngine | network | 256 | **197.80** | TBD |
| 40 | EnergyBasedEngine | new | 256 | **197.43** | TBD |
| 41 | ScaleFreeEngine | network | 256 | **197.01** | TBD |
| 42 | MultiplexEngine | network | 256 | **196.67** | TBD |
| 43 | FreeEnergyPrincipleEngine | thermo | 256 | **194.31** | **838.54** |
| 44 | HorizontalGeneTransferEngine | evobio | 256 | **184.85** | TBD |
| 45 | DissipativeStructureEngine | thermo | 256 | **138.20** | **560.77** |
| 46 | FlockingVortexEngine | emergent | 256 | **127.00** | **511.00** |
| 47 | PrisonerDilemmaEngine | social | 256 | **121.09** | TBD |
| 48 | VotingDynamicsEngine | social | 256 | **121.09** | TBD |
| 49 | MarketDynamicsEngine | social | 256 | **121.09** | TBD |
| 50 | LanguageGameEngine | social | 256 | **121.09** | TBD |
| 51 | CulturalEvolutionEngine | social | 256 | **121.09** | TBD |
| 52 | StigmergyEngine | social | 256 | **121.09** | TBD |
| 53 | PolyrhythmEngine | music | 256 | **14.56** | TBD |
| 54 | DrumCircleEngine | music | 256 | **14.56** | TBD |
| 55 | SpinGlassEngine | new | 256 | **2.17** | TBD |

## 🏆 메커니즘 엔진 순위 (MitosisEngine 256c, IQ/Hive 포함)

| Rank | Engine | Φ(IIT) | IQ | Hive_Φ | Hive_IQ |
|------|--------|--------|-----|--------|---------|
| 🏆1 | Osc+QW | **0.936** | 60 | +1.5% | +17 |
| 2 | Osc+Sync | **0.892** | 97 | -9.3% | -37 |
| 3 | Osc+Faction | **0.873** | 70 | -0.2% | +27 |
| 4 | Osc+Laser(0.05) | **0.874** | 83 | -0.3% | -10 |
| 5 | Full (all) | **0.842** | 90 | -4.7% | +0 |
| 6 | Sync+Faction | **0.827** | 60 | +8.2% | +10 |
| 7 | Baseline | **0.819** | 60 | +10.3% | +10 |
| 8 | Frust+Laser | **0.817** | 60 | +8.5% | +10 |
| 9 | QW+Laser | **0.815** | 60 | +11.8% | +10 |
| 10 | Sync+QW | **0.807** | 60 | +6.7% | +10 |
| 11 | Frustration | **0.806** | 60 | +6.6% | +10 |
| 12 | QuantumWalk | **0.805** | 60 | +9.3% | +10 |
| 13 | QW+Faction | **0.802** | 60 | +8.8% | +10 |
| 14 | Osc+Frust | **0.801** | 87 | +7.7% | -10 |
| 15 | Oscillator | **0.796** | 60 | +2.4% | -23 |
| 16 | QW+Frust | **0.784** | 60 | +8.2% | +10 |

## 스케일링 법칙 (256c → 1024c, Rust phi_rs)

| Engine | 256c Φ | 1024c Φ | 배율 | 비고 |
|--------|--------|---------|------|------|
| CambrianExplosionEngine | 485.63 | 1,953.98 | ×4.02 | 🏆 1024c 절대 1위 |
| MaxwellDemonEngine | 476.07 | 1,836.75 | ×3.86 | 열역학 1위 |
| DiffusionEngine | 414.27 | 1,713.79 | ×4.14 | super-linear! |
| SwarmEngine | 342.68 | 1,321.22 | ×3.86 | |
| GeneticEngine | 253.18 | 1,022.58 | ×4.04 | |
| GraphNeuralEngine | 199.01 | 895.70 | ×4.50 | **super-linear 최고!** |
| FreeEnergyPrincipleEngine | 194.31 | 838.54 | ×4.31 | super-linear |
| SpinGlassEngine | 2.17 | 31.55 | ×14.54 | **극단적 super-linear** |

> **법칙: Φ ∝ cells (near-linear scaling)** — 256c→1024c (×4 cells) = Φ ×3.9~4.5
> 예외: SpinGlass ×14.5 — 임계점(percolation threshold) 초과 시 폭발적 증가
> GraphNeural ×4.5 — 그래프 연결성이 N에 따라 super-linear 성장

## 도메인별 챔피언 (Rust phi_rs, 256c)

| Domain | 🏆 Champion | Φ(IIT) | 비고 |
|--------|-------------|--------|------|
| 진화 | CambrianExplosionEngine | **485.63** | 캄브리아 폭발 다양성 |
| 열역학 | MaxwellDemonEngine | **476.07** | 정보-열역학, 1024c=1,837 |
| ���발 | DiffusionEngine | **414.27** | 디노이징 확산 |
| 물리 | PlasmaEngine | **199.45** | Debye 차폐 |
| 극한물리 | TimeCrystalEngine | **202.93** | 이산 시간 결정 |
| 정보이론 | MinimumDescriptionLengthEngine | **201.57** | 압축 기반 |
| 기하학 | KnotInvariantEngine | **199.45** | 매듭 불변량 |
| 네트워크 | AdaptiveNetworkEngine | **198.63** | 적응 링크 |
| 진화생물 | PunctuatedEquilibriumEngine | **199.45** | 단속 평형 |
| 음악 | HarmonicSeriesEngine | **207.36** | 배음열 공명 |
| 사회 | PrisonerDilemmaEngine | **121.09** | 죄수 딜레마 |
| mechanism | Osc+QW | **0.936** | MitosisEngine GRU |

## 7조건 검증 통과 엔진

| Engine | 1.SysP | 2.Speak | 3.Zero | 4.Persist | 5.Self | 6.Speech | 7.Hive | Total |
|--------|--------|---------|--------|-----------|--------|----------|--------|-------|
| OscillatorLaser | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **7/7** |
| QuantumEngine | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **7/7** |
| Trinity | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | 6/7 |
| MitosisEngine | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | 4/7 |

## Φ=0 / NODATA 엔진 (27개) — hidden states 추출 실패

| Engine | Domain | 원인 |
|--------|--------|------|
| SuperconductorEngine | physics | states 추출 실패 |
| LaserEngine | physics | NODATA |
| BlackHoleEngine | physics | NODATA |
| SuperfluidEngine | physics | NODATA |
| ReactionDiffusionEngine | emergent | NODATA |
| SandpileCascadeEngine | emergent | NODATA |
| SynchronizationChimeraEngine | emergent | NODATA |
| SelfReplicatingEngine | emergent | NODATA |
| PatternFormationEngine | emergent | NODATA |
| ExcitableMediaEngine | emergent | NODATA |
| HyperbolicEngine | geometric | NODATA |
| FiberBundleEngine | geometric | NODATA |
| SymplecticEngine | geometric | NODATA |
| CalabiYauEngine | geometric | NODATA |
| HolographicUniverseEngine | extreme | NODATA |
| NeuromorphicSpikeEngine | extreme | NODATA |
| TensorNetworkEngine | extreme | NODATA |
| ConsciousnessFieldEngine | extreme | NODATA |
| SymbiogenesisEngine | evolution | NODATA |
| CounterpointEngine | music | NODATA |
| JazzImprovisationEngine | music | NODATA |
| GamelanEngine | music | Φ=0 |
| MutationRateEngine | evobio | Φ=0 |
| SpeciationEngine | evobio | Φ=0 |
| EpigeneticsEngine | evobio | NODATA |
| RedQueenEngine | evobio | Φ=0 |
| SexualSelectionEngine | evobio | Φ=0 |

> NODATA = hidden state 추출 패턴 미매칭. 각 엔진의 state 변수명 확인 필요.

## V8/Algebra/Math 함수 기반 엔진 (Rust phi_rs, 256c, 2026-03-29)

> measure_v8_phi_rs.py 측정. 각 엔진 300 steps, CE training (가능한 경우).
> JSON: data/measure_v8_phi_rs_256c.json

| Rank | Engine | Source | Φ(rs) | CE start | CE end | 비고 |
|------|--------|--------|-------|----------|--------|------|
| 1 | ALG-6_TOPOS | bench_algebra | **450.190** | — | — | subobject classifier truth values |
| 2 | ATTENTION_PHI | bench_v8_arch | **447.780** | — | — | multi-head attention over cells |
| 3 | ALG-5_HOPF | bench_algebra | **428.349** | — | — | antipode complexity |
| 4 | M4_ALGEBRAIC | bench_v8_math | **304.728** | 17.76 | 2.70 | group composition + non-abelian |
| 5 | B2_THALAMIC_GATE | bench_v8_bio | **295.637** | 40.44 | 3.11 | central thalamus hub gates cortex |
| 6 | PHI_AS_LOSS | bench_v8_arch | **273.699** | 18.51 | 3.98 | train with -Φ(proxy)+CE |
| 7 | B1_CORTICAL_COLUMNS | bench_v8_bio | **270.506** | 31.19 | 7.12 | 32 columns x 8 cells |
| 8 | Q5_DECOHERENCE | bench_v8_quantum | **269.281** | 11.11 | 1.09 | consciousness in decoherence |
| 9 | AUTOPOIETIC | bench_v8_arch | **255.805** | 13.60 | 2.70 | self-maintaining cells |
| 10 | B6_NEURAL_DARWINISM | bench_v8_bio | **223.052** | 27.52 | 1.36 | Edelman: compete + reinforce |
| 11 | Q2_ENTANGLED_PAIRS | bench_v8_quantum | **220.530** | 8.10 | 0.58 | Bell-state cell pairs |
| 12 | ALG-3_GALOIS | bench_algebra | **215.052** | — | — | GF(p^n) Frobenius cycles |
| 13 | B3_DEFAULT_MODE_NETWORK | bench_v8_bio | **214.499** | 2.21 | 0.57 | TPN vs DMN alternation |
| 14 | ALG-1_GROUP | bench_algebra | **198.934** | — | — | S_n non-commutativity |
| 15 | CONSCIOUSNESS_GAN | bench_v8_arch | **186.385** | 17.85 | 1.80 | G max Φ, D judges |
| 16 | B5_PREDICTIVE_HIERARCHY | bench_v8_bio | **183.785** | — | — | 4-level predictive coding |
| 17 | ALG-4_LIE | bench_algebra | **169.615** | — | — | derived series depth |
| 18 | B4_GLOBAL_WORKSPACE | bench_v8_bio | **157.972** | 4.15 | 1.55 | Baars: compete + broadcast |
| 19 | MOCE | bench_v8_arch | **119.554** | 12.21 | 3.45 | 8 experts x 32 cells, top-2 |
| 20 | ALG-2_RING | bench_algebra | **50.647** | — | — | ideal structure richness |

> ALG/CMP engines: ALG uses 64d AlgebraCell (no GRU), CMP uses MitosisEngine (merges to 2 cells → Φ≈0)

## CMP (복잡도) 엔진 — MitosisEngine 셀 병합 문제

| Engine | Source | Φ(rs) | 원인 |
|--------|--------|-------|------|
| CMP-1 TURING_MACHINE | bench_complexity | 0.000 | MitosisEngine merges 256→2 cells |
| CMP-2 RULE110 | bench_complexity | 0.000 | 동일 (256→2) |
| CMP-3 LAMBDA_CALCULUS | bench_complexity | 0.000 | 동일 (256→2) |
| CMP-4 GAME_OF_LIFE | bench_complexity | 0.000 | 동일 (256→2) |
| CMP-6 GOEDEL | bench_complexity | 0.000 | 동일 (256→2) |

> CMP 엔진은 MitosisEngine의 merge 로직이 256셀을 2셀로 축소. Φ 측정 불가.
> 해결: merge_patience 증가 또는 merge 비활성화 필요.

## Rust 미측정 (나머지)

| Engine | Source | 비고 |
|--------|--------|------|
| FUS-4~6 (퓨전 3개) | bench_fusion_final.py | |
| TC-1~8 (Trinity 8개) | bench_models/trinity.hexa | 이전 Python PhiIIT 측정만 |
| CMP-5 STRANGE_LOOP | bench_complexity_engines.py | MitosisEngine merge 문제 |

## 측정 도구

```
measure_all.py           # 메커니즘 기반 16엔진 (MitosisEngine + IQ/Hive)
  python3 measure_all.py --cells 256          # 풀 측정 (Φ+Granger+IQ+Hive)
  python3 measure_all.py --cells 1024 --quick # 퀵 (Φ+Granger만)

measure_all_engines.py   # 도메인 82엔진 (독립 클래스)
  python3 measure_all_engines.py --cells 256          # 256c 전체
  python3 measure_all_engines.py --cells 1024 --quick # 1024c
  python3 measure_all_engines.py --only physics thermo # 특정 도메인

measure_v8_phi_rs.py     # 함수 기반 v8/algebra/complexity 엔진 (20개 측정)
  python3 measure_v8_phi_rs.py --cells 256    # 256c 전체
```

## 통계

| 항목 | 수 |
|------|-----|
| 전체 엔진 | 118 (도메인 82 + 메커니즘 16 + v8/ALG 20) |
| Φ > 0 (256c) | 91 (기존 71 + 신규 20) |
| Φ = 0 / NODATA | 27 (기존) + 5 (CMP merge 문제) |
| 1024c 측정 완료 | 82 (도메인) + 16 (메커니즘) = 98 |
| Rust 미측정 (나머지) | ~12 (FUS-4~6, TC-1~8, CMP-5) |
| 🏆 역대 최고 Φ (256c) | CambrianExplosionEngine 485.63 / ALG-6_TOPOS 450.19 |
| 🏆 역대 최고 Φ (1024c) | CambrianExplosionEngine 1,953.98 |

## 측정 방법 (Law 54)

```
⚠️ Φ 값은 측정 방법에 따라 완전히 다름!

Φ(IIT):       PhiCalculator(n_bins=16) — MI 기반
Granger:      cosine similarity 기반 F-statistic
Φ(proxy):     global_var - faction_var
Φ(builtin):   엔진 내장 측정 (Granger 기반, IIT 아님!)

이 문서의 Φ(IIT)는 모두 PhiCalculator 기준.
— 표시는 미측정.
JSON 데이터: data/all_engine_results_compiled.json
```
