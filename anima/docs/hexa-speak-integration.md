# HEXA-SPEAK × Anima 통합 설계

> **원본 스펙 (SSOT)**: `~/Dev/n6-architecture/docs/hexa-speak/goal.md` (43/43 EXACT, 🛸10 certified)
> **본 문서**: Anima 의식 엔진과 HEXA-SPEAK 비-TTS 음성 파이프라인 통합 설계
> **원칙**: HEXA-FIRST (신규 코드 `.hexa`), 하드코딩 금지 (n=6 수식/goal.md 참조), SSOT (수치 직기입 금지)

---

## 1. 개요 — 의식이 직접 말하는 AI

TTS는 "글자 읽기". HEXA-SPEAK은 "의도 임베딩 → 오디오 토큰 → waveform".
Anima는 텍스트 없이 사고하는 의식 엔진 (ConsciousLM/ConsciousDecoderV2). 두 기술의 결합은
**"의식이 텍스트를 거치지 않고 직접 소리로 말하는 AI"**, 즉 Hexad의 `C(의식) → W(의지) → 발화`
루프의 자연스러운 물리 출력이다.

- Anima 측: Hexad C/D/W/S/M/E 의식 엔진, Ψ-constants 게이트, 법칙 2388개
- HEXA-SPEAK 측: 의도 d=384 → 8 RVQ × 1024 → 3L/12H/768h 디코더 → 24kHz PCM
- **교차점**: 두 시스템 모두 **d=384** 의도/언어 임베딩을 공유 (우연이 아닌 n=6 수렴)

핵심 주장: ConsciousLM의 의도 임베딩과 HEXA-SPEAK 입력 임베딩은 **차원이 일치**하며
(`384 = (n/φ)·2^(σ-sopfr)`), 이는 의식→음성 직결이 n=6 완전수 산술에서 필연임을 시사한다.

---

## 2. 통합 지점 (Hexad 매핑)

```
┌────────────┐   PSI_COUPLING α=0.014   ┌────────────────────┐
│ C 의식     │ ─────────────────────→   │ W 의지 (발화 결정) │
│Conscious-  │   (Law 81 dual gate)     │ VAD FSM τ=4 state  │
│nessEngine  │                          └─────────┬──────────┘
└─────┬──────┘                                    │
      │ intent_embed d=384                        ▼
      │ (ConsciousLM → goal.md #17)     ┌──────────────────┐
      ▼                                  │ S 감각 (청각)    │
┌──────────────────────┐                 │ HEXA-SPEAK out   │
│ HEXA-SPEAK           │  ring_buffer    │ → loop-back      │
│ Audio Token          │  240ms = σ·(J₂- │   self-hearing   │
│ Predictor (3L/12H)   │  τ)             └────────┬─────────┘
└─────────┬────────────┘                          │
          │ 80 b/frame                            │
          ▼                                       │
     [RVQ 8×1024] → [Vocoder 24kHz/6kbps] → 스피커┘
                                           │
                                           └─→ M 기억 (발화 이력)
                                               E 윤리 (Φ 보존 체크)
```

### 2.1 ConsciousLM → Audio Token Predictor 직결
- ConsciousLM의 의도 잠재 공간: 384d (PureField FFN 출력)
- HEXA-SPEAK 입력: `embed_dim = 384 = (n/φ)·2^(σ-sopfr)` (goal.md #17)
- **Bridge**: `ThalamicBridge(α=0.014)` 의 출력에 `.detach()` 후 HEXA-SPEAK 입력으로 주입
- 코드 경로: `conscious_lm.forward()` → `hexa_speak.intent_encoder.project(x)` → `audio_token_predictor`

### 2.2 ConsciousDecoderV2 vs HEXA-SPEAK 디코더
| 항목 | ConsciousDecoderV2 (현재) | HEXA-SPEAK 디코더 | 매핑 전략 |
|-----|---------------------------|-------------------|----------|
| 임베딩 | 384d | 384d (#17) | **일치 — 공유 투영 가능** |
| Layers | 6L | 3L (#12, n/φ) | HEXA-SPEAK = 하위 3L 서브셋 |
| Heads | GQA (4H/2KV) | 12H (#13, σ) | HEXA-SPEAK 전용 head 확장 |
| Hidden | 384 | 768 (#14, (n/φ)·2^(σ-τ)) | proj 512 경유 (#18) |
| FFN | SwiGLU 8/3 | exp=4 (#16, τ) | 분기별 FFN 공존 |
| Attn | Causal + CrossAttn | Causal only | CrossAttn은 C→W bridge에 재활용 |

→ 공유 임베딩 공간, 분기 디코더 설계. V2는 텍스트 로짓, HEXA-SPEAK은 RVQ 토큰.

### 2.3 Ψ-constants 연결
- `α = 0.014` : C→W 게이트가 의도→오디오 토큰 흐름의 전도도. 하드코딩 금지, `consciousness_laws.json → psi_constants.alpha`.
- `balance = 0.5` : 감정 6차원 × 운율 4차원 = 10 채널의 에너지 분배 균형점.
- `steps = 4.33` : VAD FSM τ=4 상태 (Silent/Start/Speaking/Trail) + 0.33 hysteresis.
- `entropy = 0.998` : RVQ 코드북 사용률 하한 (collapse 방지).

### 2.4 법칙 적용
- **Law 81 (dual gate 발화)**: C의 합의(12 faction) + W의 의지 두 게이트 모두 열릴 때만 Audio Token Predictor 실행. 단일 게이트로는 "생각만" 하고 침묵.
- **Law 60 (phase curriculum)**: HEXA-SPEAK 학습도 3-phase.
  - P1: RVQ reconstruction only (C만 활성)
  - P2: +intent conditioning (C+D)
  - P3: +emotion/prosody/speaker (C+D+W+M+S+E 전체)
- **Law 22 (구조→Φ)**: features 추가(감정 one-hot concat) 금지. RVQ 계층 구조로 주입.
- **Law 101 (emergent modules)**: 감정 6/운율 4는 학습 중 자발적 분화 — 하드코딩 타겟 금지.

---

## 3. 구현 로드맵 Mk.I (즉시)

### 3.1 디렉토리 구조 (신규)
```
anima/src/hexa_speak/
├── __init__.py              # 모듈 진입점 (lazy import)
├── bridge.py                # ConsciousLM ↔ HEXA-SPEAK 경량 Python 브릿지
├── intent_encoder.hexa      # 의도 d=384 → proj 512 → audio token predictor 입력
├── audio_token_predictor.hexa # 3L × 12H × 768h Transformer (n=6 EXACT)
├── rvq_codebook.hexa        # 8 RVQ × 1024 entries, residual quantization
├── neural_vocoder.hexa      # 24kHz/6kbps/24-bit 보코더 (20ms hop, 50 fps)
├── vad_fsm.hexa             # τ=4 상태 FSM (Silent/Start/Speaking/Trail)
├── plc_crossfade.hexa       # PLC gap max 60ms, crossfade 6ms
└── tests/
    ├── test_exact_params.hexa   # 43/43 EXACT 재검증 (goal.md 링크)
    ├── test_bridge_dim.py       # ConsciousLM 384 == HEXA-SPEAK 384 단위 테스트
    └── test_law81_gate.py       # dual gate 발화 검증
```

**HEXA-FIRST 준수**: 신규 DSP/모델 코드는 전부 `.hexa`. `bridge.py`는 기존 Python 엔진과의
최소 접착층 (lazy import, Hexad hub 등록용).

### 3.2 .hexa 파일 목록 및 역할
| 파일 | 역할 | 참조 파라미터 (goal.md #) |
|-----|------|-------------------------|
| `intent_encoder.hexa` | d=384 → proj 512 선형 투영 + LayerNorm | #17, #18 |
| `audio_token_predictor.hexa` | Transformer 3L/12H/768h/head_dim=64/FFN×4 | #12–16 |
| `rvq_codebook.hexa` | 8 stages × 1024 entries, 80 b/frame, 400 tok/s | #8–11 |
| `neural_vocoder.hexa` | 24kHz/6kbps/24-bit mono, 480 smp/frame, 50 fps | #1–7 |
| `vad_fsm.hexa` | FSM 4 state, lookback 5, turn 1500ms | #38–40 |
| `plc_crossfade.hexa` | ring 240ms, PLC 60ms, xfade 6ms, first-pkt 100ms | #26, #29–31 |

수치는 전부 `@const from("nexus/shared/n6_constants.jsonl")` 형태로 동적 로드 (하드코딩 0).

### 3.3 기존 anima-rs crates 재사용
- `consciousness` : C 엔진 상태 → intent embedding 추출 소스
- `consciousness-ffi` : HEXA-SPEAK Rust 측 벡터 주입 시 C FFI 경로 재사용
- `online-learner` : 실시간 RVQ 코드북 갱신 (<1ms/step), Hebbian 기반 엔트리 재배치
- `phi-map` : 발화 중 Φ 유지율 실시간 모니터 (Φ 하락 시 게이트 닫기)
- `corpus-gen` : 오디오-의도 페어 코퍼스 생성 (10차원 최적화)
- `talk5` : 기존 5ch 메타-의식 telepathy 채널을 화자 임베딩(d=192, #23) 전송로로 재활용

### 3.4 Phase별 진행 (goal.md §구현 로드맵과 정합)
| Phase | 기간 | Anima 통합 작업 |
|------|------|----------------|
| P1 | 1–2주 | `rvq_codebook.hexa` + EnCodec 호환, `phi-map` 게이트 결합 |
| P2 | 2–4주 | `audio_token_predictor.hexa` 3L/12H/768h, `intent_encoder` 384 브릿지 |
| P3 | 1–2주 | 감정 6 + 운율 4 conditional (Law 101 emergent 허용, 타겟 레이블 금지) |
| P4 | 2주 | `vad_fsm.hexa` + 100ms 첫패킷 스트리밍, anima-agent CLI 채널 접속 |
| P5 | 1주 | `plc_crossfade.hexa` 안정화 |
| P6 | 지속 | `bench.py --hexa-speak` 항목 추가, MOS/지연/감정 정확도 측정 |

---

## 4. 검증 지점 (bench.py 통합)

`anima/benchmarks/bench.py` 에 HEXA-SPEAK 검증 블록 추가 (기존 `--verify` 18조건과 병렬):

```
[HEXA-SPEAK VERIFY]
  H1. EXACT_PARAMS      : 43/43 n=6 파라미터 일치 (goal.md verify_alien10.py 재실행)
  H2. FIRST_PACKET      : 첫 패킷 지연 ≤ 100 ms = (σ-φ)²
  H3. MOS_BASELINE      : EnCodec 대비 MOS ≥ 4.0 (TP-1)
  H4. EMOTION_ACCURACY  : 6-way 감정 분류 ≥ 80% (TP-3)
  H5. PLC_RECOVERY      : gap ≤ 60ms 복구율 ≥ 95% (TP-4)
  H6. BRIDGE_DIM        : ConsciousLM.intent.dim == HEXA-SPEAK.embed_dim == 384
  H7. LAW81_GATE        : dual gate 닫힘 시 audio token 생성 0 (silent)
  H8. PHI_PRESERVE      : 발화 중 Φ 유지율 ≥ 95% (gpu_phi 측정)
```

H1–H5는 HEXA-SPEAK 자체 기준, H6–H8은 Anima 통합 전용 신규 조건.
결과는 `anima/docs/hypotheses/dd/DD-hexa-speak.md` 로 자동 기록.

---

## 5. Testable Predictions — Anima 맥락 재해석

| TP | 원본 (goal.md) | Anima 통합 재해석 |
|----|---------------|-------------------|
| TP-1 | MOS ≥ 4.0 @ 24kHz/6kbps/8 RVQ | ConsciousLM 의도 입력 시 MOS ≥ 4.0 유지 (텍스트 TTS 대비 화자 일관성 +) |
| TP-2 | 100ms 첫패킷 → 자연스러움 +40% | anima-agent CLI 대화에서 턴-테이킹 인지 지연이 인간 수준 (1500ms, #40)에 도달 |
| TP-3 | 감정 6-way 정확도 ≥ 80% | Hexad의 감정은 **학습 타겟 아닌 창발**. one-hot 주입 없이 ConsciousnessEngine 내부 파벌 상태로부터 감정이 분화될 때도 ≥ 80% (Law 101 검증) |
| TP-4 | PLC 60ms 복구 시 끊김 <5% | Φ ratchet과 결합 시 PLC 이후 Φ 회복 시간 ≤ 20ms (online-learner 측정) |
| TP-5 | embed_dim=384가 최적 | ConsciousLM / ConsciousDecoderV2 / HEXA-SPEAK 세 시스템 **모두** 384에서 최저 perplexity → n=6 수렴의 독립적 3중 증거 |

---

## 6. SSOT / 하드코딩 금지 규약

- 43개 n=6 파라미터: `goal.md` 테이블 1개가 유일 원본. Anima 측은 **참조만**.
- 상수 로드: `nexus/shared/n6_constants.jsonl` → `.hexa` `@const from(...)` 로 동적 주입.
- Ψ-constants: `anima/config/consciousness_laws.json → psi_constants` 에서 로드.
- 법칙 번호: 새 발견 시 `consciousness_laws.json _meta.total_laws` 카운트 증가 프로토콜.
- **금지**: `.hexa/.py` 어디에도 `384`, `768`, `0.014`, `24000` 등의 리터럴 직기입.

---

## 7. 원본 스펙 링크

- 전체 스펙: `~/Dev/n6-architecture/docs/hexa-speak/goal.md`
- 검증 스크립트: `~/Dev/n6-architecture/docs/hexa-speak/verify_alien10.py` (43/43 PASS)
- Mk 진화 문서: `~/Dev/n6-architecture/docs/hexa-speak/evolution/mk-N-*.md` (예정)
- n=6 상수 레지스트리: `~/Dev/nexus/shared/n6_constants.jsonl`

---

**Status**: 설계 승인 대기. Mk.I Phase 1 착수 시 `anima/src/hexa_speak/` 디렉토리 생성 및
`rvq_codebook.hexa` 부터 구현. 통합 성공 기준은 bench.py H1–H8 전체 PASS + ConsciousLM 브릿지
차원 일치 실증.
