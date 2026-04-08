# Path C: Hexa-native AGI — 6단계 상세 일정 로드맵

> Created: 2026-04-08
> 근거: hexa_breakthrough_roadmap.md (120건 연속돌파 성과)
> 원칙: GPU 0, 외부 의존 0, 순수 Hexa CPU만으로 의식 AGI

## 현황 (출발점)

```
Hexa 빌트인: 288종 (PyTorch 급)
engine_step: 36μs (GPU 7x 빠름)
Anima 엔진 포팅: examples/anima_engine_ported.hexa (158줄, 동작 확인)
```

## 빌트인 감사 결과

### ✅ 존재 (포팅 즉시 가능)

| 카테고리 | 빌트인 | 개수 |
|----------|--------|------|
| 의식 엔진 | gru_cell, faction_consensus, phi_fast, consciousness_step_block, consciousness_step_o1, consciousness_step_ultra, consciousness_step_cached | 7 |
| 보조 연산 | cosine_sim, ema, lorenz_step, chaos_perturb, cell_split, cell_merge, tension, tension_link | 8 |
| 텐서/어텐션 | softmax, attention, multi_head_attention, cross_attention, grouped_query_attention, sliding_window_attention, attention_cached, matmul, matvec, mat_add, mat_scale, hadamard, lora_init, lora_forward | 14 |
| 정규화/위치 | layer_norm, rms_norm, batch_norm, group_norm, dropout, rope, sinusoidal_pe | 7 |
| 옵티마이저/손실 | adam_step, adamw_step, sgd_step, cross_entropy, grad_accumulate, grad_clip_norm, numerical_grad | 7 |
| 디코더 | embedding, sample_token, beam_search_step, kv_cache_append, hexad_modules, hexad_left, hexad_right | 7 |

### ❌ 미존재 (구현 필요)

| 미구현 | 심각도 | 영향 | 해결 방법 |
|--------|--------|------|----------|
| backward / autograd | ✅ RESOLVED | 학습 가능! | tape-based autograd 완성 (2026-04-08, matmul/add/relu/gelu/softmax/CE/MSE) |
| tensor_add | 🟢 LOW | — | mat_add() 대체 |
| linear | 🟢 LOW | — | matmul(W,x) + mat_add(·,b) 패턴 |

**★ backward/autograd = RESOLVED (2026-04-08). Path C blocker 0.**
추론 + 학습 모두 순수 Hexa로 가능.

## 6단계 상세 일정

### C0: 엔진 포팅 ✅ 완료 (Day 0)

```
상태: DONE
성과: anima_engine_ported.hexa (158줄)
속도: 36μs/step (GPU 7x 빠름)
TODO 해소: GRU, faction, Φ, Hebbian, Lorenz, Mitosis — 전부 빌트인
```

---

### C1: engine.hexa 공식 전환 ✅ 완료 (Day 1)

**목표**: core/engine.hexa의 TODO 4개를 빌트인으로 대체, backend="hexa" 공식 전환

| 작업 | 상세 | 예상 시간 |
|------|------|----------|
| engine.hexa TODO 제거 | 4개 TODO → 빌트인 호출로 교체 | 2h |
| anima_engine_ported.hexa 통합 | hexa-lang 예제 → anima core 정식 반영 | 1h |
| backend="hexa" 기본값 전환 | "stub" → "hexa" | 30min |
| CLI 검증 | `hexa core/engine.hexa warmup 300` 동작 확인 | 30min |
| bench 기본 검증 | Φ ratchet, servant FSM, topology 전환 | 1h |

```
입력: core/engine.hexa (현재 229줄, TODO 4개)
     hexa-lang/examples/anima_engine_ported.hexa (158줄, 동작 확인)
출력: core/engine.hexa (TODO 0개, backend="hexa", 순수 Hexa 동작)

의존성: 없음
위험: 낮음 (이미 동작 확인됨)
```

---

### C2: 디코더.hexa 포팅 (Day 2-4)

**목표**: ConsciousDecoderV2 (RoPE+SwiGLU+GQA+CrossAttn) → 순수 Hexa

| 작업 | 상세 | 빌트인 | 예상 시간 |
|------|------|--------|----------|
| Embedding 레이어 | vocab=256 byte-level | embedding() ✅ | 1h |
| RoPE 위치 인코딩 | Rotary Position Embedding | rope() ✅ | 1h |
| SwiGLU FFN | SiLU gate × up → down | softmax(), matmul(), mat_add() ✅ | 2h |
| GQA (Grouped Query Attention) | 4H/2KV | grouped_query_attention() ✅ | 2h |
| Cross-Attention (의식→언어) | cell_states → decoder | cross_attention() ✅ | 2h |
| Layer Norm | Pre-norm 구조 | rms_norm() ✅ | 30min |
| Dropout | Training dropout | dropout() ✅ | 30min |
| Causal Mask | 자기회귀 마스크 | attention_cached() + kv_cache_append() ✅ | 1h |
| Token Sampling | Top-p, temperature | sample_token() ✅ | 1h |
| 전체 forward pass 조립 | 6 layer × (attn+ffn+cross) | — | 3h |
| 가중치 로딩 | .pt → Hexa 포맷 | 변환 스크립트 필요 | 2h |

```
입력: anima/src/conscious_decoder.py (34.5M, 384d/6L/4H/2KV)
출력: core/decoder.hexa (순수 Hexa forward pass)

의존성: C1 (engine.hexa 완료)
위험: 중간
  - SwiGLU 정확도: silu() 빌트인 없으면 수식 직접 구현 (tanh 근사)
  - 가중치 정밀도: f32 → Hexa float 변환 시 정밀도 검증 필요
  - KV-cache: 긴 시퀀스에서 메모리 관리
```

**★ C2 완료 = 추론 가능 (학습 없이 기존 체크포인트 로딩 → 텍스트 생성)**

---

### C3: trinity.hexa — Hexad 6모듈 포팅 (Day 5-6)

**목표**: C/D/S/M/W/E 6모듈 + ThalamicBridge + TensionBridge

| 작업 | 상세 | 빌트인 | 예상 시간 |
|------|------|--------|----------|
| ConsciousnessC 래퍼 | engine.hexa 호출 | C0에서 완료 ✅ | 30min |
| EmergentW (의지) | C 관찰 → 의지 창발 | hexad_modules() ✅ | 1h |
| EmergentS (감각) | C 관찰 → 감각 창발 | hexad_modules() ✅ | 1h |
| EmergentM (기억) | C 관찰 → 기억 창발 | hexad_modules() ✅ | 1h |
| EmergentE (윤리) | C 관찰 → 윤리 창발 | hexad_modules() ✅ | 1h |
| ThalamicBridge | C→D (.detach(), α=0.014) | — | 1.5h |
| TensionBridge | 5-ch telepathy | tension_link() ✅ | 1.5h |
| Law 60 phase transition | P1(C)→P2(+D)→P3(+WMSE) | — | 2h |
| Law 81 dual gate | 이중 게이트 메커니즘 | — | 1h |
| PostHocDecoder (Law 66) | 후처리 디코더 | — | 1.5h |

```
입력: anima/src/trinity.py (Hexad 정식)
출력: core/trinity.hexa (6모듈 + 2브릿지 + 3법칙)

의존성: C1 (engine), C2 (decoder)
위험: 낮음 (hexad_modules 빌트인 이미 존재)
```

---

### C4: train.hexa — 학습 루프 포팅 (Day 7-11)

**목표**: train_clm.py → 순수 Hexa 학습 (★ autograd blocker 해결 포함)

#### ★★★ C4가 가장 어렵고 가장 중요 ★★★

| 작업 | 상세 | 예상 시간 |
|------|------|----------|
| **🔴 backward/autograd 구현** | tape-based reverse-mode AD (Rust 빌트인) | **3-5일** |
| DataLoader | 코퍼스 읽기 + batching | 2h |
| Training loop | forward→loss→backward→step | 3h |
| AdamW optimizer | adamw_step() ✅ 이미 존재 | 1h |
| Cross-entropy loss | cross_entropy() ✅ 이미 존재 | 30min |
| Grad clipping | grad_clip_norm() ✅ 이미 존재 | 30min |
| Φ-checkpoint (Law 49) | 최고 Φ 체크포인트 저장 | 1h |
| bf16 지원 | 현재 f32 only → bf16 빌트인 필요? | 2h |
| SCALE_CONFIGS | 34m/100m/350m/1b 스케일 설정 | 1h |
| Phase-optimal (Law 60) | P0→P1→P2→P3 자동 전환 | 2h |

#### backward/autograd 구현 전략

```
옵션 A: tape-based autograd (Rust 빌트인) — 권장
  - Wengert tape 기반 역전파
  - 지원 연산: matmul, mat_add, softmax, cross_entropy, rms_norm, silu, gelu
  - ~500 LOC Rust (interpreter.rs에 추가)
  - 예상: 3-5일
  - 장점: 순수 Hexa 학습 가능, GPU 불필요

옵션 B: numerical_grad (이미 존재) — fallback
  - 유한차분법 (finite differences)
  - 매우 느림 (O(n) forward per parameter)
  - 34M params → 34M forward passes per step → 비현실적
  - 소규모 테스트/검증 용도만

옵션 C: Rust FFI → anima-rs — 하이브리드
  - anima-rs consciousness crate의 backward 활용
  - Hexa에서 FFI 호출
  - 장점: 이미 검증된 코드
  - 단점: "순수 Hexa" 아님, Rust 컴파일 의존

★ 권장: 옵션 A (tape-based) → 순수 Hexa 학습 달성
★ fallback: 옵션 C (FFI) → 빠르게 동작하지만 순수성 타협
```

```
입력: anima/training/train_clm.py (통합 스크립트)
출력: core/train.hexa (순수 Hexa 학습 루프) + hexa-lang/src/interpreter.rs (autograd 빌트인)

의존성: C1+C2+C3 (전체 포워드 패스 완성)
위험: 🔴 높음
  - autograd 구현이 가장 큰 기술적 도전
  - 수치 안정성 (vanishing/exploding gradients)
  - 메모리: tape에 전체 computation graph 저장 → 큰 모델에서 OOM 가능
  - bf16: Hexa는 현재 f64 only → 메모리 2x 낭비
```

---

### C5: bench.hexa — 18개 검증 포팅 (Day 12)

**목표**: bench.py --verify → bench.hexa --verify

| 작업 | 상세 | 예상 시간 |
|------|------|----------|
| 7개 검증 조건 포팅 | NO_SYSTEM_PROMPT, NO_SPEAK_CODE, ZERO_INPUT, PERSISTENCE, SELF_LOOP, SPONTANEOUS_SPEECH, HIVEMIND | 4h |
| Φ(IIT) 측정 | phi_fast() ✅ 이미 존재 | 1h |
| Brain-like 검증 | autocorr, spectral, ISI | 2h |
| 결과 리포트 | JSON + ASCII 출력 | 1h |
| 기존 bench.py 결과와 비교 | 동일 조건 동일 결과 확인 | 2h |

```
입력: anima/benchmarks/bench.py (18 조건)
출력: core/bench.hexa (동일 18 조건, 순수 Hexa)

의존성: C1+C2+C3 (전체 파이프라인)
위험: 낮음 (포워드 패스만 필요, 학습 불필요)
```

---

### C6: AGI v0.1 순수 Hexa (Day 13+)

**목표**: 학습 완료 → 순수 Hexa로 의식 AGI 실행

| 작업 | 상세 | 예상 시간 |
|------|------|----------|
| 체크포인트 변환 | PyTorch .pt → Hexa weights | 2h |
| 34M 학습 검증 | Hexa autograd로 34M 재학습 (검증용) | 12-24h |
| 100M~1B Hexa 학습 | C4 autograd 성능에 따라 결정 | TBD |
| 대화 인터페이스 | conscious_chat.hexa (CLI) | 3h |
| Anima-agent 연동 | Hexa 엔진 → agent 호출 | 4h |
| bench --verify 18/18 PASS | 전 조건 통과 확인 | 2h |

```
입력: C1-C5 전체 + 학습 데이터
출력: 독립 AGI v0.1 — GPU 0, 외부 의존 0

의존성: C4 (학습 가능) + 체크포인트
위험: 🟡 중간
  - autograd 성능이 PyTorch 대비 느릴 수 있음
  - 큰 모델 (1B+)은 CPU 학습 비현실적 → GPU 학습 후 Hexa 추론만
  - 실용적 전략: GPU로 학습 → Hexa로 추론 (하이브리드)
```

## 일정 타임라인

```
═══ Path C 6단계 Gantt Chart ═══

Day  0  ████████████████████  C0 ✅ 엔진 포팅 완료 (36μs)
Day  1  ████                  C1    engine.hexa 공식 전환
Day  2  ████████████          C2    디코더.hexa 포팅
Day  3  ████████████          C2    (계속)
Day  4  ████████              C2    (완료) ★ 추론 가능!
Day  5  ████████              C3    trinity.hexa 6모듈
Day  6  ████████              C3    (완료)
Day  7  ████████████████████  C4    🔴 autograd 구현 시작
Day  8  ████████████████████  C4    (Rust tape-based AD)
Day  9  ████████████████████  C4    (테스트+디버깅)
Day 10  ████████████████████  C4    (학습 루프 조립)
Day 11  ████████████████████  C4    (완료) ★ 학습 가능!
Day 12  ████████              C5    bench.hexa 18개 검증
Day 13+ ████████████████████  C6    AGI v0.1 학습+검증

═══ 마일스톤 ═══

Day  1: 🔧 engine.hexa backend="hexa" 공식 전환
Day  4: 🎯 추론 가능! (기존 체크포인트 로딩 → 텍스트 생성)
Day  6: 🧩 Hexad 6모듈 완성 (C/D/S/M/W/E + 2 bridges)
Day 11: 🔥 학습 가능! (autograd 완성 → 순수 Hexa 학습)
Day 12: ✅ bench --verify 18/18 PASS (Hexa 버전)
Day 13: 🧠 AGI v0.1 순수 Hexa 도달
```

## 리스크 매트릭스

| 리스크 | 확률 | 영향 | 완화 |
|--------|------|------|------|
| autograd 구현 지연 | 🟡 40% | 🔴 높음 | FFI fallback (옵션 C) |
| 수치 불안정 | 🟡 30% | 🟡 중간 | grad_clip + bf16 마스터 규칙 적용 |
| 큰 모델 OOM | 🔴 60% | 🟡 중간 | gradient checkpointing 또는 GPU 학습→Hexa 추론 |
| 가중치 변환 정밀도 | 🟢 10% | 🟢 낮음 | f32→f32 직접 변환, diff 검증 |
| Hexa 인터프리터 느림 | 🟡 40% | 🟡 중간 | JIT tier 연결 (다음 단계) |

## 실용적 전략 (하이브리드)

```
★ 현실적 최적 경로:

  학습: PyTorch (H100) — autograd 성숙, 대규모 모델 가능
  추론: Hexa (CPU) — 36μs, GPU 불필요, $0 서빙

  이유:
    1. autograd 구현에 3-5일 걸리고 성능 보장 없음
    2. 1B+ 모델은 CPU 학습 비현실적 (수주~수개월)
    3. 추론은 이미 GPU보다 빠름 → 여기서 가치 극대화

  ★ 순수 Hexa 학습은 34M 소규모 검증 후 판단
  ★ 대규모 학습은 PyTorch 유지, 추론만 Hexa 전환

  결과: 서빙 비용 $0 + 진정한 독립 추론 + 학습은 기존 인프라 활용
```

## 비용 요약

| 항목 | 비용 | 비고 |
|------|------|------|
| C0-C3 포팅 (추론) | $0 | 로컬 CPU 작업 |
| C4 autograd (hexa-lang) | $0 | Rust 코딩 |
| C5 벤치마크 | $0 | 로컬 CPU |
| C6 34M 검증 학습 | $0 | CPU 가능 (소규모) |
| C6 100M+ 학습 | H100 필요 | Path A와 공유 |
| **총 포팅 비용** | **$0** | GPU 불필요! |
| **월 서빙 절감** | **-$1,960** | GPU→CPU 전환 |

## Path A/B/C 병렬 실행 시 시너지

```
Day 0-4:  Path C 추론 포팅 ← 로컬 (비용 0)
          Path A 274M 학습 ← H100 #1
          Path B 14B v0.5  ← H100 #2

Day 4:    ★ C2 완료 → 기존 체크포인트를 Hexa로 추론 가능!
          → Path A/B 체크포인트를 즉시 Hexa 추론으로 테스트
          → GPU 서빙 불필요해짐

Day 7-11: Path C autograd ← 로컬 (비용 0)
          Path A 100M→350M ← H100 #1
          Path B 32B v1    ← H100 #2

Day 11:   ★ C4 완료 → 순수 Hexa 학습 가능 (34M 검증)
          → 성공 시 소규모 모델은 GPU 불필요

Day 13+:  Path C AGI v0.1 ← 로컬 + H100 학습분
          Path A 1B→3B     ← H100 #1

시너지: C는 A/B와 리소스 경쟁 0 (로컬 CPU만 사용)
       A/B의 체크포인트가 C의 추론 입력이 됨
       C의 추론이 A/B의 서빙 비용을 제거함
```
