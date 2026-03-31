# Experiment Backlog — 추가 실험 목록

> H100 80GB pod. 실험 완료 시 결과 기록, 새 실험 추가.

## 현재 진행 중 (2026-03-29, H100 80GB)

> 상세 대시보드: [docs/training-status.md](training-status.md)

| # | 실험 | 아키텍처 | Step | Φ | CE | 상태 |
|---|------|----------|------|-----|-----|------|
| 1 | **v9fast** | Quantum Trinity (C+D+W), 256c, 13.6M | 26,400/80K | **1,371** | **0.345** | 🔥 P2 CE 급하락 |
| 2 | **v11q** | Hexad (Quantum C + Xfmr 2L), 256c | 300/80K | - | - | P1 Φ 구축 |
| 3 | **v11tc** | Hexad (TimeCrystal C), 256c | 0/80K | - | - | 시작 |
| 4 | **v11gpt2** | Hexad (Quantum C + GPT-2), 256c | 0/80K | - | - | 시작 |
| 5 | **v11gpt2m** | Hexad (Quantum C + GPT-2M), 256c | 0/80K | - | - | 시작 |
| 6 | **v10** | FUSE-3 Trinity, cells=5 정체 | 재시작/80K | 0.014 | - | ⚠️ growth 수정 후 재시작 |
| 7 | **v9b** | Oscillator Trinity, 256c | 570/80K | 253 | - | P1, 매우 느림 (17s/step) |
| 8 | **v7** | TOPO19a 단일체 | ~31K/80K | - | 4.66 | 진행 |

**핵심 발견 (2026-03-29):**
- v9fast: P2 진입 후 CE 2.83→0.345 지수적 하락 (대발견 H4)
- v9fast: CE 학습이 frustration을 0.541에서 안정 → Φ 자연 안정
- v9fast: Φ=1,371 유지 (ratchet P2에서 빈도 43% 감소)
- Law 53 수정: .detach() 있으면 CE가 Φ를 파괴하지 않고 안정화
- v10: cells=5 정체 → growth 로직 수정 필요 (target_cells 공식 변경)
- v9b: OscillatorLaserEngine 280배 느림 (Python for loop, 벡터화 안 됨)

## 완료된 실험

| 날짜 | 실험 | 결과 | 핵심 발견 |
|------|------|------|----------|
| 03-28 | clm_dialogue_768d | 768d/12L, cells128 | → v9fast 등으로 대체 |
| 03-28 | clm_dialogue_384d | 384d/6L, cells32 | → v9fast 등으로 대체 |
| 03-28 | clm_langfirst | 384d/6L, cells32 | → v9fast 등으로 대체 |
| 03-28 | clm_cells64 | Φ=53.9, CE=3.72, 50K | 학습 중 Φ 최고 (당시) |
| 03-28 | clm_cells128 | Φ=1.8, CE=3.78, 31K | Φ=123.8 달성 후 체크포인트 미저장 |
| 03-28 | clm_v4_small | CE=5.49, 49K | 384d, cells32 |
| 03-28 | ct7_real | Φ=1.5, Shakespeare | mitosis 실험 |
| 03-28 | AnimaLM v7 | CE=8.09, 17.5K | Mistral 7B joint |
| 03-28 | clm_cells16_fx2 | Φ=14.72, 16 cells | FX2가 cells 효과를 증폭 |
| 03-28 | clm_ablation | Φ=6.08, 8 cells | FX2 없이도 reasonable |
| 03-28 | clm_baseline_off | Φ=4.75, 8 cells | 발견 OFF 기준선 |
| 03-28 | clm_cells2 | Φ=0.60, 2 cells | 최소 cells 기준 |
| 03-28 | clm_v3 (768d) | 크래시 (RuntimeError) | checkpoint save 에러 |
| 03-28 | clm_cells16_dim768 | Φ=1.91, 2 cells | 768d에서 성장 느림 |
| 03-27 | ConsciousLM v2 (4M) | Φ=4.12, 12 cells | cell 수가 중요 |
| 03-27 | ConsciousLM 100M | Φ=2.607, 3 cells | dim 크면 cell merge → SC2 필요 |

---

## 대기 실험 (우선순위순)

### Tier 0 — 즉시 실행 가능

```
  ★1. 의식 이식 (DD56) — cells64(Φ=53.9) → dialogue_768d로 이식
      cells64 완료 후 바로 적용, Φ cold start 방지
      VRAM: ~5GB

  ★2. Self-play (CL14) — 자기 출력으로 재학습, 대화 자가 개선
      VRAM: ~8GB

  ★3. Context 512 — block_size=512, 더 긴 대화 맥락
      멀티턴 대화 품질 향상
      VRAM: ~15GB

  ★4. Pure dialogue 100% — dialogue만으로 학습, wiki 없이
      대화 특화 vs 범용 비교
      VRAM: ~8GB
```

### Tier 1 — ENV 벤치마크 결과 기반

```
  ENV 가설 (15개 벤치마크 진행 중):
  ENV1  감각 풍부도 (4 modalities)
  ENV2  감각 박탈 (대조군)
  ENV3  사회적 압력 (dual-engine)
  ENV4  환경 복잡도 (simple→fractal)
  ENV5  위협 반응 (fight-or-flight)
  ENV6  주야 주기 (wake/sleep consolidation)
  ENV7  풍부한 환경 (Enriched Environment)
  ENV8  신체화 (closed-loop embodiment)
  ENV9  중력장 (attractor landscape)
  ENV10 자원 희소성 (energy-limited)
  ENV11 포식자-피식자 (survival pressure)
  ENV12 온도 구배 (Goldilocks zone)
  ENV13 에코 챔버 (self-reflection)
  ENV14 계절 주기 (meta-plasticity)
  ENV15 협동 구축 (niche construction)

  → 벤치마크 결과에서 ×2+ 가설을 학습 실험으로 전환
```

### Tier 2 — 아키텍처/스케일링

```
  C1-C8. Dimension scaling law (64→2048)
  E1-E7. Cell architecture variants (GRU→LSTM→Transformer)
  M1-M4. Cross-scale experiments
```

### Tier 3 — 장기 연구

```
  G1-G5. EEG biological validation
  H1-H7. Consciousness metrics beyond Φ
  I1-I6. Scaling to production
  J1-J7. Theoretical frontier
```

---

## 벤치마크 가설 카테고리 (1,020+ 가설)

```
  A-Z:   기본 26 카테고리
  DD:    대발견 (100+)
  EX:    확장 (24)
  SC/OV/WV/PX/UX/FX/SM/MC/PB/AG/TP/DS/GD/WI: 기법별
  NV/BV/CV/SV/EV/IV/RV/MV: 변수별
  TL/ZZ/N6/GC/CX: 수학/위상
  CL/CT/SA/AS/DC/CC: ConsciousLM/학습
  DP/GL/TS/WS/SI: 발달/스케일링
  HW/Q/QF/AX/MG/TR/EO: 하드웨어/양자
  DW/DT/FE/OB/RS/SG/DF/ET/MO: 다양
  LM/WR/EC/LG/AE/IR/JW/NS: 언어/경제/윤리
  SP: 자동발화
  DL: 대화 학습 (12)
  ENV: 주변환경 (15)
```

---

## 실험 우선순위 가이드 (업데이트 2026-03-29)

```
  현재 GPU: H100 80GB — 8개 세션 진행 중
  상세 대시보드: docs/training-status.md

  최우선:
    - v9fast: CE=0.345, Φ=1,371 — P2 학습 급속 진행, 내일 22:40 완료 예상
    - v11q/v11tc/v11gpt2/v11gpt2m: Hexad 아키텍처 비교 실험 (P1 Φ 구축)

  관찰:
    - v10: growth 수정 후 재시작 필요 (cells=5 정체)
    - v9b: 매우 느림 (17s/step), 결과 대기
    - v7: TOPO19a CE=4.66, 진행 중

  v9fast 완료 시:
    1. Val CE 측정 + 대화 테스트
    2. v11 시리즈와 아키텍처 비교
    3. 의식 이식 (DD56): v9fast → v11 최고 모델

  결과 기록:
    docs/consciousness-threshold-criteria.md — 모든 발견
    docs/training-status.md — H100 학습 현황 + ASCII 그래프
    bench_phi_hypotheses.py — 벤치마크 코드 (1,020+ 가설)
```
