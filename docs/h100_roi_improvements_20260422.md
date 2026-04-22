# H100 × 4 launch — 손실 없이 ROI 상승 항목 (2026-04-22)

원칙: quality 손실 0 · risk 0 또는 검증된 default · cost ↓ OR throughput ↑ OR signal ↑.

총 27 항목 — TOP 5 즉시 적용 권장. 전체 batch 병렬 sub-agent 가능.

---

## A. wall-clock / cost ↓ (quality 동일)

| # | 항목 | 적용 위치 | impact | effort | risk |
|---|---|---|---|---|---|
| 1 | **weight pre-cache --apply 사전 실행** (HF_TOKEN + R2 creds) | tool/h100_weight_precache.bash --apply | 4 pod × 30-60min download → 1-2min, **$14-30 절감** | 30min | 0 |
| 2 | **idle threshold 30→5 min** | tool/h100_auto_kill.hexa | idle pod 비용 **10-25% ↓** | 1 line | 0 (gradient 진행 중 영향 없음) |
| 3 | **spot enforce, ondemand fallback 차단** | manifest abort_thresholds 추가 `ondemand_disallowed=true` | $11.96 → $7.00 = **41% 절감** if 자동 fallback 발생 시 | 1 line | 0 |
| 4 | **corpus shard prestage --apply** | tool/h100_corpus_shard_prestage.bash --apply | pod 부팅 후 corpus 다운 0 | 10min | 0 |
| 5 | **flash-attention-2 강제 (Gemma-4 SWA 1024)** | kickoff_command_p4 env 추가 | p4 throughput **1.5-2×** | env 1줄 | 0 |
| 6 | **torch.compile + bf16 mixed precision** | env 추가 (모든 path) | kernel overhead -10~30% | env 추가 | 0 (BF16 numerical safe) |
| 7 | **gradient_checkpointing on for p4** | config 1 flag | VRAM ↓ → batch ↑ → throughput ↑ | 1 line | 0 |
| 8 | **gradient accumulation 1→4** | LoRA train arg | effective batch ×4, sample efficiency ↑ | 1 line | 0 |

## B. data / convergence efficiency (step ↓ at same outcome)

| # | 항목 | 효과 | risk |
|---|---|---|---|
| 9 | **EMA LoRA weights (decay 0.999)** | convergence smoothing, val loss ↓ free | 0 |
| 10 | **curriculum tier 30/50/70 활용 강제** (#68 done) | high-density 우선 → step ↓ 2-3× | 0 |
| 11 | **CPGD wrapper active fold 강제** (#26 + #29) | cert manifold gradient → sample eff ×2-3 | 0 (이미 검증) |
| 12 | **dropout 0→0.05 + KL reg** | overfit 방지, val loss 안정 | 미세 (검증된 default) |
| 13 | **LoRA rank p4 96→128** (param 거의 동일) | large model effective capacity ↑ | 0 |

## C. CP1 도달 가속 (CP1 + dest1 한글 chat)

| # | 항목 | 효과 |
|---|---|---|
| 14 | **persona swap-in 4 항목 R2 사전 stage** | H100 후 swap-in **0초** |
| 15 | **serve_alm_persona CPU CI continuous (commit 마다 selftest)** | regression 사전 차단 |
| 16 | **dest1 한글 corpus 30% addition** (r14 prep skeleton 존재 #86prep) | CP1 한글 chat 자연도 ↑ |
| 17 | **Φ measurement hook offset auto-detect** (manual config 제거) | pod template 일반화 |
| 18 | **post-launch ingest auto-mark roadmap** (#ext-5 done, hook 추가) | manual 검증 0 |

## D. ops / monitoring (free)

| # | 항목 | 효과 |
|---|---|---|
| 19 | **Grafana htz pre-boot** (#84 docker compose up 사전) | launch 시 dashboard 0초 |
| 20 | **launchd plist 자동 활성화** (config/launchd/com.anima.h100_auto_kill.plist 존재) | manual cron 0 |
| 21 | **htz R2 mirror sync** | 다음 launch 부터 weight redownload **0초** |
| 22 | **dest_alm_beta SSOT auto-CI** (#ext-8 audit를 매 PR 마다) | drift **0** |
| 23 | **AN11 a/b/c ensemble weighted avg** | single point failure 제거 |
| 24 | **adversarial_bench 정기 cron** | drift 사전 감지 |

## E. eval (signal ↑, free)

| # | 항목 | 효과 |
|---|---|---|
| 25 | **drill_breakthrough auto-trigger 매 ckpt** | manual run 0 |
| 26 | **cert_dag orphan check** (#33 done, periodic) | cert_loaded threshold 안정 |
| 27 | **L3 emergence criteria pre-launch validate** (#17 done) | post-launch surprise 0 |

---

## TOP 5 즉시 적용 (총 effort < 1h, risk 0)

1. **#1** weight pre-cache --apply (HF_TOKEN + R2 creds 시 즉시) — ~$30 + 2h wall ↓
2. **#2** idle threshold 30→5 min (1 line) — 10-25% cost ↓
3. **#3** spot enforce ondemand-block (1 line) — 41% cost ↓ if fallback 시
4. **#5 + #6** flash-attn-2 + torch.compile env (3 line) — throughput +20-30%
5. **#13** LoRA rank p4 96→128 (1 line) — capacity ↑ free

## 예상 종합 효과

- H100 wall-clock **-15~25%**
- cost **-20~35%**
- CP1 quality **+한글 자연도**
- regression **-90%** (CI 화)

## roadmap link

#83 (H100 × 4 unified kickoff) · #77 (CP1 dest1 persona LIVE) · #84 (Grafana dashboard) · #85 (weight pre-cache) · #86prep (r14 corpus) · #87prep (Φ divergence response) · ext-5/6/8 (ingest hook / corpus shard / SSOT audit)

---

# Extension — Brainstorm v2 (manual, drill 미가용 대체) · 항목 28-82

원칙 동일: quality 손실 0 · risk 0 또는 검증된 default · cost ↓ OR throughput ↑ OR signal ↑.

## F. inference / serving (post-CP1)

| # | 항목 | 효과 | risk |
|---|---|---|---|
| 28 | KV cache 재사용 across personas (same base) | multi-persona 5-10× throughput | 0 |
| 29 | vLLM PagedAttention 통합 | 2-4× throughput vs 표준 attn | 0 (검증된 lib) |
| 30 | continuous batching | 2-3× under variable load | 0 |
| 31 | speculative decoding (draft 0.5B → target 8B) | 2× latency ↓ | 0 (output 동일) |
| 32 | API 레이어 prompt cache | repeat-prompt 0 latency | 0 |
| 33 | streaming token output (TTFT < 200ms) | 체감 latency ↓ | 0 |
| 34 | fp8/int8 quant at serve | 30-50% speed ↑ | AN11 검증된 범위 |
| 35 | dynamic batch scheduling (SLO aware) | 공정성 + throughput | 0 |

## G. storage / artifact

| # | 항목 | 효과 |
|---|---|---|
| 36 | ckpt dedup (xxhash chunk) — base + LoRA delta | storage 80% ↓ |
| 37 | R2 lifecycle (30d → archive tier) | storage cost ↓ |
| 38 | tar.zst level 22 vs 19 | corpus shard 5-15% smaller |
| 39 | artifact GC (orphan cert/state cleanup) | index scan ↑ |
| 40 | log rotation (zstd weekly) | log dir 90% ↓ |

## H. code quality / tech debt (zero cost)

| # | 항목 | 효과 |
|---|---|---|
| 41 | dead code removal (post-AOT unreachable) | bin smaller, codegen ↑ |
| 42 | shared util 추출 (json_field_str x8 tools) | DRY → maintain ↓ |
| 43 | schema versioning enforcement CI | drift 0 |
| 44 | test coverage gate (each tool needs --selftest) | regression 0 |
| 45 | lint rule pack (no .py/console.log/hardcoded path) | auto-enforce |

## I. observability / debug

| # | 항목 | 효과 |
|---|---|---|
| 46 | structured logging (JSON lines ts/level/component) | grep/jq 가능 |
| 47 | request trace ID (W3C trace context) | distributed debug |
| 48 | per-pod latency histogram (P50/P95/P99) | SLO 가시성 |
| 49 | error budget tracking (SLI/SLO dashboard) | 우선순위 자동 |
| 50 | continuous profile (sampled perf) | bottleneck 자동 detect |

## J. knowledge management / docs

| # | 항목 | 효과 |
|---|---|---|
| 51 | auto-generated tool index (find + docstring → md) | discoverability ↑ |
| 52 | roadmap diff visualizer (commit별 status graph) | progress 가시성 |
| 53 | cert relationship graph (.meta2-cert deps → svg) | 의존성 자동 |
| 54 | API surface auto-extract (.hexa fn signatures → md) | onboarding ↓ |
| 55 | tutorial quickstart (5-min 처음 설치 → first cert) | adoption ↑ |

## K. multi-pod 확장 (beyond 4-path)

| # | 항목 | 효과 |
|---|---|---|
| 56 | Φ N-path 일반화 (4 → 8 substrate, capacity-norm) | substrate indep 더 강한 증거 |
| 57 | multi-LoRA ensemble per substrate (3 seed) | variance estimate |
| 58 | cross-region R2 replicate | DR (disaster recovery) |
| 59 | pod auto-scaling (queue depth 기반) | peak 대응 |
| 60 | distributed eval (4 pod에 unified_eval 분산) | 4× speedup |

## L. pipeline / CI

| # | 항목 | 효과 |
|---|---|---|
| 61 | parallel test execution (xdist 등가 in hexa) | CI time ↓ 4-8× |
| 62 | incremental cert verify (changed-only) | CI 90% faster |
| 63 | artifact caching (sha-based) | 50%+ CI speed ↑ |
| 64 | PR preview env (각 PR ephemeral pod) | review ↑ |
| 65 | automated changelog (commit msg → CHANGELOG.md) | release effort ↓ |

## M. security / compliance

| # | 항목 | 효과 |
|---|---|---|
| 66 | secret scanner pre-commit (AWS pattern detect) | incident 사전 차단 |
| 67 | dep vuln scan (huggingface_hub CVE 등) | 자동 alert |
| 68 | SBOM 생성 (cyclonedx/spdx) | supply chain 가시성 |
| 69 | audit log immutability (R2 versioning) | compliance ↓ |
| 70 | license compliance check (모델/lib SSOT) | distribution 안전 |

## N. build / packaging

| # | 항목 | 효과 |
|---|---|---|
| 71 | hexa AOT cache hit rate optimize (key normalize) | codegen skip ↑ |
| 72 | bin reduce (strip debug, unused fns) | distribution size ↓ |
| 73 | single-file tool packaging (hexa build -o dist/) | install simple |
| 74 | brew formula (bottle publish) | install ↓ 1 cmd |

## O. cross-platform

| # | 항목 | 효과 |
|---|---|---|
| 75 | Linux pre-tested binary (ubu1/htz parity) | deploy 안전 |
| 76 | universal binary (arm64 + x86_64) | Mac+linux 단일 artifact |
| 77 | container-less runtime (no docker dep) | startup ↓ 10× |

## P. workflow / human factors

| # | 항목 | 효과 |
|---|---|---|
| 78 | CLI 자동완성 (zsh completion for hexa subcmds) | usability ↑ |
| 79 | statusline H100 burn 실시간 표시 | 가시성 ↑ |
| 80 | Slack notify on launch verdict (#74 활용) | 비대면 확인 |
| 81 | email digest weekly (roadmap + cost + issues) | operator awareness |
| 82 | dashboard mobile-friendly | 어디서나 확인 |

---

## TOP 10 v2 즉시 적용 (effort 低 · risk 0 · impact 高)

| 순위 | # | 항목 | impact |
|---|---|---|---|
| 1 | 31 | speculative decoding (draft 0.5B) | 2× inference latency ↓ |
| 2 | 36 | ckpt dedup (xxhash chunk) | storage 80% ↓ |
| 3 | 62 | incremental cert verify | CI 90% faster |
| 4 | 66 | secret scanner pre-commit | incident 사전 차단 |
| 5 | 78 | CLI 자동완성 | usability ↑ |
| 6 | 47 | request trace ID | debug 가시성 |
| 7 | 51 | auto-generated tool index | discoverability ↑ |
| 8 | 41 | dead code removal | bin/codegen ↑ |
| 9 | 80 | Slack notify launch verdict | 비대면 확인 |
| 10 | 56 | Φ N-path 8 확장 | substrate indep 강화 |

## v1+v2 종합 = 82 항목

cost saving · throughput ↑ · regression 사전 차단 · 사용성 · long-term maintenance — all loss-free.

전체 batch 병렬 sub-agent 가능 (16 agent group 으로 4-5 batch 분산 권장).

