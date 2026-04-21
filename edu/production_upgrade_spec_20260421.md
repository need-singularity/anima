# ANIMA β main Production 승격 Spec (2026-04-21)

> CPU micro-scale PoC → 실사용 production 승격 로드맵 (60일).
> Source: Seed task 38 (production upgrade spec), 2026-04-21.

## 1. Scale gap 정량 (micro vs production)

| metric | CPU micro | Qwen 14B production | gap |
|--------|-----------|---------------------|-----|
| V (vocab) | 8 (folded ASCII) | 152064 | 1.9e4× |
| H (hidden) | 4 | 5120 | 1.3e3× |
| params | ~34 (4-gen [18,16,16,9]) | ~1.4e10 | 4.1e8× |
| FLOPs/token | 12.7K | ~7e13 | 5.5e9× |
| corpus | 100 bigram pairs | 117k lines target | 1170× |
| wall-time/step | <1s CPU native | H100 필요 | — |

**Landauer 51× 보존 여부**: 추측 — β FULL no-weight-update 시 bit-erasure 는 cell fixpoint seal 에만 의존 → scale-invariant 후보. 실측 0.

## 2. 각 β STAGE production 구현

- **STAGE 1 CPGD**: V ∈ R^(16×16) → Qwen LoRA adapter low-rank subspace projection. block-diag P_S (6 Hexad 모듈 분할 주입)
- **STAGE 2 cell trajectory**: per-layer/head 단위 4-gen crystallize. Qwen 40 layer → layer-group 10 단위 replicate
- **STAGE 3 Hexad 활성**: 6-module adapter 6-head 주입, Law60 phase inference-time gating
- **STAGE 4 AN11**: 14B → 64 shard × 2.2e8 param/shard 로 shard_cv 검증. H100 scale gap 여기 집중

## 3. Hardware 3 scenario

| scenario | 제약 | 가능 작업 | cost |
|----------|------|----------|------|
| **CPU Mac 64GB** | Qwen 14B 4-bit(~8GB) 가능, 학습 불가 | β STAGE 0-3 verify, AN11(b) math | $0 |
| **단일 RTX 5070 16GB** (Hetzner, 현재 offline) | Qwen 7B 4-bit fine-tune | β STAGE 1-4 small-scale | ~€60/월 |
| **H100 rental** ($2.99/hr) | 14B full + AN11 triple | STAGE 4 full + latency | **~$2150** (24h×3 + 7일 uptime) |

**추천: H100 rental 단발** ($1500-2200 범위)

## 4. Data scale

r13 117k lines → AN11(a) shard_cv ∈ [0.05, 3.0] 요구 → **최소 64 shard × 1827 line/shard**. G2/G5 FAIL 해결 전 launch 금지.

## 5. Deployment architecture

- **serve**: FastAPI + vLLM (Qwen 14B 4-bit AWQ), SSE streaming
- **bridge**: tool/cell_token_bridge_proto.hexa per-request 삽입
- **endpoint**: /v1/chat/completions (OpenAI-compat) + /an11/verify
- **monitor**: I_irr per-step, V_sync Kuramoto r, Landauer bit-counter
- **latency budget**: first-token <500ms (추측, 4-bit + vLLM CUDA graph)

## 6. Production validation gates

1. AN11 triple PASS 유지 (deterministic, identical prompt → identical verdict)
2. Seed B anti-denial 0건 (enforce_anti_denial_policy L1302)
3. Latency p50<300ms / p95<800ms / p99<2s
4. Regression: 7일 AN11 verdict 변동 <5%
5. Bridge round-trip cos ≥ 0.5 (spec §4 ablation C)
6. I_irr non-zero 유지 (fixpoint collapse 전까지, option_b PoC 실측 0.037-0.104)
7. Uptime SLA 99.9%

## 7. Timeline 60일

| period | 주요 작업 |
|--------|-----------|
| **D0-D7** | corpus G2/G5 fix (task 31) + bridge PoC 완성 (task 36) |
| **D8-D21** | Qwen 14B on H100 rental, CPGD init + 4-gen crystallize 1-pass, AN11 triple 측정 |
| **D22-D35** | anima-serve FastAPI+vLLM 구축, latency 최적화 |
| **D36-D60** | regression 1주, 7-day uptime, 논문 draft |

## 8. Risk register

| risk | mitigation |
|------|-----------|
| H100 rental cost overrun | D14 cutoff, α fallback (gradient hybrid) |
| Qwen 14B license + KR deployment | Apache 2.0 (확인 필요), Fellows 정직 공시 |
| micro→production scale 신호 소실 | γ path Llama 3 8B 병행 replicability |
| I_irr fixpoint collapse → λ 무효 | EMA smoothing, arrow cusp 전 sampling |
| AN11(a) shard_cv boundary FAIL | shard 64→128 증가, Frob>τ 재측정 |

## 9. 추천 시나리오

**H100 rental 단발 ($2150) + CPU Mac 연속 verify + γ Llama 3 8B 병렬**
- raw#12: Hetzner/ubu H100 offline, 자체 H100 없음
- 비용-효과: D8-D21 14일 집중
- β fallback α: 30일 내 tier_3 미달 시 gradient hybrid

## 10. Day 1-3 즉시 실행

1. **D1**: tool/cell_token_bridge_proto.hexa (spec §6, 3 fixture) — task 36 진행 중
2. **D1**: r13 corpus G2/G5 validator PASS — task 31 진행 중
3. **D2**: tool/flops_landauer_bench.hexa — task 34 진행 중
4. **D2**: tool/anima_learning_free_driver.hexa orchestrator — task 33 진행 중
5. **D3**: H100 rental vendor 견적 (Lambda / RunPod / vast.ai)

## 참조
- edu/paths.json (β main SSOT)
- edu/cell_token_bridge_spec_20260421.md
- edu/an11_closure_gap_probe_20260421.md (Z3 recommended)
- docs/option_b_p1_minimal_poc_result_20260421.md
- docs/alm_r13_corpus_rebuild_plan_20260420.md
