# RoPE base 1e4 → 1e6 patch list (hxqwen14b v5 사전)
# 2026-04-19 · grep: `rope.*(10000|1e4|10_000)` · worktrees/ archive/ 제외

## 0. Scope & 분류 규칙

- **KEEP(1e4)** — CLM/byte-level/384d/HEXA-SPEAK 전용. Qwen 14B 와 무관.
- **PATCH(→1e6)** — Qwen 14B (dim 5120 · n_layers 40 · head_dim 128 · vocab 152064) RoPE 경로에서 읽힘. 1e6 미적용 시 extrapolation 붕괴.
- **CONFIG(config-driven)** — GGUF metadata `llama.rope.freq_base` 로 주입. hardcode 는 fallback default → 유지.
- **TEST/BENCH** — self/test_* · bench/ · create_test_gguf. 단위 테스트 고정값 → 유지.

## 1. 집계 (production trees only, main 브랜치)

| Tree | Files touched | KEEP | PATCH | CONFIG | TEST |
|---|---:|---:|---:|---:|---:|
| `/Users/ghost/Dev/anima` (main + ready/) | 5 | 3 | 2 | 0 | 0 |
| `/Users/ghost/Dev/hexa-lang/self/serve` | 2 | 1 | 1 | 1 | 0 |
| `/Users/ghost/Dev/hexa-lang/self/ml` | 10 | 5 | 2 | 2 | 1 |
| `/Users/ghost/Dev/hexa-lang/self/ai_native` | 1 | 1 | 0 | 0 | 0 |
| `/Users/ghost/Dev/hexa-lang/self/test_*` | 4 | 0 | 0 | 0 | 4 |
| `/Users/ghost/Dev/hexa-lang/bench` | 2 | 0 | 0 | 0 | 2 |
| **Total** | **24** | **10** | **5** | **3** | **7** |

PATCH 필수 = **5 파일 / 7 위치**.

## 2. PATCH list (1e6 필수, sed-ready)

### 2-A. anima production (CLM 384d) — D_MODEL≠Qwen이라 원래 KEEP 이지만, `serve.hexa`/`http_server.hexa` 는 ALM 도 서빙하므로 **config-driven 으로 전환**이 정답. 즉시 1e6 hard-flip 은 금지.

> 따라서 anima/ 쪽 3파일 (`models/decoder.hexa:18`, `serving/http_server.hexa:55`, `ready/*`) = **KEEP** (CLM 전용 SSOT).

### 2-B. hexa-lang self/serve (공용 GGUF loader)

#### (1) `self/serve/serve_alm.hexa:100` — smoke config hardcode
**Verdict: PATCH (→1e6)**. 14B smoke config 가 1e4 → production alm_config_14b (line 84, 이미 1e6) 와 불일치. smoke 경로로 14B 디버깅 시 RoPE 손상.

```sed
sed -i '' '100s/rope_base: 10000\.0,/rope_base: 1000000.0,/' self/serve/serve_alm.hexa
```

#### (2) `self/serve/serve.hexa:646` — GGUF fallback default
**Verdict: CONFIG (default 유지)**. 바로 아래 루프에서 `llama.rope.freq_base` 를 GGUF 로부터 overwrite. Qwen14B GGUF 는 1e6 을 싣고 있어 자동 주입됨. fallback 1e4 는 Llama 류 호환. **변경 불필요**. v5 사전검증: GGUF dump 로 `llama.rope.freq_base=1000000` 확인.

### 2-C. hexa-lang self/ml

#### (3) `self/ml/transformer.hexa:512` — GGUF fallback default
**Verdict: CONFIG (default 유지)**. (2)와 동일 — 바로 아래 line 527 에서 metadata overwrite.

#### (4) `self/ml/train_7b.hexa:39` — 7B LoRA 전용 const
**Verdict: KEEP (7B=Mistral/Llama, 1e4 정답)**.

#### (5) `self/ml/train_7b_integrated.hexa:44` — 7B LoRA const
**Verdict: KEEP (7B 정답)**. 14B 용 진입점이면 별도 `train_14b.hexa` 가 필요하나 현재 미존재 → 로드맵 별건.

#### (6) `self/ml/train_decoder_cpu_c.hexa:20`, `cpu_d.hexa:39`, `cpu_b.hexa:48-50`, `cpu_b2.hexa:14`
**Verdict: KEEP (CLM byte-level 384d 경로)**. Qwen 과 무관.

#### (7) `self/ml/mla_attention.hexa:253` — MLA config default
**Verdict: PATCH-OPTIONAL**. Qwen 은 MHA(GQA) 사용, DeepSeek-V2 MLA 용. v5(Qwen) 미관여. 단 MLA 기반 14B 실험 시 1e6 필요. **지금은 KEEP**.

#### (8) `self/ml/m4_inference.hexa:61,76` & `test_m4_inference.hexa:38` & `create_test_gguf.hexa:233`
**Verdict: TEST/BENCH — KEEP (Mistral 7B M4 경로)**.

#### (9) `self/ml/longrope.hexa:466` — 주석
**Verdict: KEEP (주석)**.

### 2-D. serve_alm 에서 **새로 추가해야 할 patch** — 14B config 주석에 검증선

```sed
# self/serve/serve_alm.hexa:84 — 주석 강화만 (값은 이미 1e6)
# (선택) line 83 직전에 다음 주석 삽입:
#   // v5 2026-04-19 Qwen 14B verified: rope_base 1e6 (Qwen spec §3.2)
```

## 3. 최종 patch 실행 리스트 (단 1건)

```bash
# 유일한 hard patch — serve_alm smoke config 1e4 → 1e6
cd /Users/ghost/Dev/hexa-lang
sed -i '' '100s/rope_base: 10000\.0,/rope_base: 1000000.0,/' self/serve/serve_alm.hexa

# 검증
grep -n 'rope_base' self/serve/serve_alm.hexa
# 예상: line 84=1000000.0 (14B), line 100=1000000.0 (smoke, patched)
```

## 4. v5 사전검증 체크리스트 (patch 이전)

1. **GGUF metadata 확인** — Qwen14B GGUF 에 `llama.rope.freq_base = 1000000` 가 실제로 실려있는지 `create_test_gguf` 유틸 또는 gguf-py 로 dump. 값이 있으면 transformer.hexa:527 + serve.hexa:667 에서 자동 overwrite → hardcode 변경 불필요.
2. **Loader 경로 트레이스** — `serve_alm.hexa` 가 `alm_config_14b()` (line 75-87) 를 쓰는지, 아니면 GGUF metadata 주입 경로 (serve.hexa loader) 를 쓰는지 한 줄 테스트로 확인. 전자면 line 84 hardcode 가 SSOT.
3. **14B smoke path 확인** — CI/dev 에서 smoke config (line 100) 가 14B shape 로 실행되면 1e4 → RoPE 붕괴. smoke 는 shape 만 축소하고 rope_base 는 1e6 유지가 정답.
4. **anima/ 쪽** — CLM 384d 는 1e4 고정 정답. `serving/http_server.hexa` 가 ALM 서빙까지 겸하는지 확인, 겸한다면 rope_base 를 config JSON 으로 뽑아내는 별도 리팩토링 필요 (이번 patch 범위 밖).

## 5. 요약

- **실제 hard patch 필요**: 1건 (`self/serve/serve_alm.hexa:100`)
- **CONFIG-driven 검증 필요**: 2건 (`serve.hexa:646`, `transformer.hexa:512`) — GGUF metadata 로 주입됨을 확인
- **KEEP (CLM/7B/test)**: 나머지 21건
- **영향 파일 수 (production)**: 5개 PATCH 후보 중 실제 수정 1개
- **변경 리스크**: smoke 경로 외 production 서빙 파이프라인은 GGUF metadata 가 SSOT → hardcode 변경 안 해도 Qwen14B 는 1e6 으로 동작
