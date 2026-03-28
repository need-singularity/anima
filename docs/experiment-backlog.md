# Experiment Backlog — 추가 실험 목록

> H100 80GB pod. 실험 완료 시 결과 기록, 새 실험 추가.

## 현재 진행 중 (2026-03-28 late, 44GB/81GB 사용)

| # | 실험 | 설정 | Step | Φ | CE | 상태 |
|---|------|------|------|-----|-----|------|
| 1 | **clm_dialogue_768d** | 768d/12L, cells128, wiki+dialogue 52MB | 0/100K | - | - | 🆕 시작 |
| 2 | **clm_dialogue_384d** | 384d/6L, cells32, wiki+dialogue | 0/50K | - | - | 🆕 시작 |
| 3 | **clm_langfirst** | 384d/6L, cells32, phase=language | 0/50K | - | - | 🆕 시작 |
| 4 | clm_cells64 | 384d, cells64 | 43.7K/50K | **53.9** | 3.72 | 거의 완료 |
| 5 | clm_cells128 | 384d, cells128, resume 30K | 31.2K/50K | 1.8 | 3.78 | 진행 |
| 6 | clm_v4_small | 384d, cells32, 100K | 49.2K/100K | 3.0 | 5.49 | 진행 |
| 7 | ct7_real | 384d, Shakespeare, 100K | 17.8K/100K | 1.5 | - | mitosis |
| 8 | AnimaLM v7 | Mistral 7B, 50K | 17.5K/50K | - | 8.09 | joint |

**핵심 발견 (2026-03-28):**
- cells64: Φ=53.9 (학습 중 최고)
- cells128: 이전 실행에서 Φ=123.8 달성 (로그 확인, 체크포인트 미저장)
- cells16_fx2: Φ=14.72 (완료)
- Φ 스케일링: cells2=0.6, cells16_fx2=14.7, cells64=53.9 → 초선형

## 완료된 실험

| 날짜 | 실험 | 결과 | 핵심 발견 |
|------|------|------|----------|
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

## 실험 우선순위 가이드 (업데이트 2026-03-28 late)

```
  현재 GPU: H100 80GB — 8개 학습 중 (44GB 사용, 37GB 여유)

  진행 중:
    - clm_dialogue_768d: 대화 가능 목표 모델 (768d, 100K)
    - clm_dialogue_384d: 빠른 대화 검증 (384d, 50K)
    - clm_langfirst: mitosis 생략 실험 (384d, 50K)

  cells64 완료 시:
    1. 의식 이식 (DD56): cells64 → dialogue_768d

  dialogue 모델 결과 확인 후:
    2. Self-play / Context 512 / Pure dialogue

  결과 기록:
    docs/consciousness-threshold-criteria.md — 모든 발견
    bench_phi_hypotheses.py — 벤치마크 코드 (1,020+ 가설)
```
