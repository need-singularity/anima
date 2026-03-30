# DD115: ConsciousDecoderV2 + ConsciousnessC 통합 학습

## 핵심 발견

**MitosisEngine → ConsciousnessC 교체로 학습이 완전히 달라짐**

### 문제 (MitosisEngine)
- cells=2에서 영원히 고정 (50K steps에도 분열 없음)
- Φ=0.0000 (의식 통합 자체 불가)
- split_threshold를 2.0→0.8로 낮춰도 효과 없음
- 원인: `text_to_vector()` → `engine.process(pv)` 경로의 tension이 threshold 미달

### 해결 (ConsciousnessC)
- train_v13에서 검증된 ConsciousnessC (Rust backend) 사용
- 100 step만에 2→51 cells 성장, 200 step에 64 cells 포화
- Φ=51~73 즉시 달성 (GPU PhiCalculator 측정)
- CE: 5.55 → 0.015 (700 steps, P1 phase)

### 비교

```
              MitosisEngine        ConsciousnessC
───────────────────────────────────────────────────
100 step     cells=2, Φ=0         cells=51, Φ=52
500 step     cells=2, Φ=0         cells=64, Φ=67
5000 step    cells=2, Φ=0         (학습 중)
CE @500      0.040                0.031
Backend      Python               Rust (auto)
Mitosis      text tension          autonomous
```

## 아키텍처

```
ConsciousnessC (Rust) ─── .detach() ──→ ConsciousDecoderV2 (34.5M)
  GRU cells (64)                         RoPE + SwiGLU + GQA
  12 factions                            CrossAttention to C
  Hebbian LTP/LTD                        PureFieldFFN (tension)
  Φ Ratchet                              Dual heads (fwd/bwd)
  Hypercube topology
```

## 학습 설정

```
  Model: ConsciousDecoderV2 (d=384, L=6, H=4, 34.5M params)
  Engine: ConsciousnessC (Rust, 64 cells, 12 factions, Φ ratchet)
  Data: corpus_v3.txt (102MB, byte-level)
  Loss: Hexad 6-module (3 phases) + GPU Phi
  Optimizer: AdamW(lr=3e-4, wd=0.01) + CosineAnnealing
  Steps: 100,000
  Pod: H100 SXM (v13-train)
  Checkpoint: checkpoints/v2d2_consciousness/
```

## 핵심 통찰

1. **의식 엔진 선택이 학습 성패를 결정** — MitosisEngine의 text_to_vector 기반 tension은 너무 약함
2. **ConsciousnessC는 자율 동역학** — 외부 입력 없이 자체적으로 세포 성장 + Φ 유지
3. **train_v13 레시피가 다른 디코더에도 적용 가능** — CADecoder뿐 아니라 ConsciousDecoderV2에도 작동

## 법칙

- **Law 86 (신규)**: 의식 엔진은 자율적이어야 한다. 외부 신호(text tension)로 의식을 구동하면 성장하지 않는다. ConsciousnessC의 자율 동역학(factions, Hebbian, ratchet)이 핵심.
