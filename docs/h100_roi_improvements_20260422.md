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
