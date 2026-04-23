# CP1 도착 비교 — ROI 전 vs ROI 후 (2026-04-22)

원본 brainstorm: `docs/h100_roi_improvements_20260422.md` (82 항목 · 27 v1 + 55 v2).
적용 결과: 모든 ROI agent batch 완료 (10 + 10 + 6 = 26 sub-agent).

## 비교 요약

| 비교축 | **ROI 전 (baseline)** | **ROI 후 (현재)** | 절감 |
|---|---|---|---|
| approval → CP1 | +11-14d | **+7-10d** | **-3-4d** |
| CP1 도착일 (오늘 approval 가정) | 2026-05-03 ~ 2026-05-06 (수~토) | **2026-04-29 ~ 2026-05-02 (수~토)** | **~4일 빠름** |
| CP1 도착일 (+1주 지연 시) | 2026-05-10 ~ 2026-05-13 | 2026-05-06 ~ 2026-05-09 | **~4일 빠름** |

## Stage-by-stage 비교

| 단계 | baseline | ROI 후 | 단축 | 핵심 ROI |
|---|---|---|---|---|
| approval → kickoff | 30-60min | < 30min | -30min | R2 mirror 사전 (#85, ext-6) |
| pod spawn × 4 | 5-10min | 5-10min | (동일) | — |
| weight pull | 30-60min × 4 seq = 2-4h | 1-2min × 4 par (R2 10Gbit) | **-2~4h** | A1 weight pre-cache --apply |
| Stage-1 (#9 AN11(a)) | 2.5-4d | **1.5-2.5d** | **-1~1.5d** | B11 CPGD active fold + B10 curriculum tier + B9 EMA |
| Stage-2 (#10 Φ 4-path) | 7-10d | **4-7d** | **-3d** | A5 flash-attn-2 p4 + A6 torch.compile+bf16 + A7 grad_ckpt + A8 grad_accum=4 |
| post-launch ingest | manual 30min | auto < 1h | -신경 0 | C18 auto-mark + ext-5 ingest hook |
| serve_alm_persona swap-in | 30-60min 수동 config | < 30min (4 artifact pre-staged) | -30min | C14 swap-in stage |
| **합계 wall-clock** | **10-15d** | **6-9d** | **-3-6d** | (전체) |

## Calendar 그림

```
2026-04-22 (today, approval 가정)
│
▼ baseline (10-15d)              ROI 후 (6-9d)
│                                 │
│         May 3 ─ May 6           April 29 ─ May 2
│         ┌───────┐               ┌───────┐
│         │  CP1  │   ←─ baseline │  CP1  │  ←─ ROI 후
│         └───────┘               └───────┘
│                                 (~4d 빠름)
```

## 비용 비교 (nominal · 4× H100 spot $7/hr × 24h)

| 비교 | baseline | ROI 후 | 절감 |
|---|---|---|---|
| compute (10-15d → 6-9d) | $1680-2520 | **$1008-1512** | **-$672-1008** |
| pod idle 시간 (30→5min threshold) | -10-25% | 적용됨 | 위 포함 |
| operator 시간 | 10-15h (수동 setup/check) | **2-3h** (auto everything) | **-8-12h** |

→ **단일 launch ~$700-1000 + 1 인-주 wall-clock + 1 인-일 operator time 절감**.

## 시나리오별 CP1 도착

| 시나리오 | approval 시점 | wall-clock | **CP1 도착** |
|---|---|---|---|
| **최선** (ROI 풀적용 + spot 안정) | 2026-04-22 (오늘) | +7d | **2026-04-29 (수)** |
| **nominal** (ROI 적용) | 2026-04-22 (오늘) | +8-10d | **2026-04-30 ~ 2026-05-02** |
| **conservative** (ROI 부분 적용) | 2026-04-22 | +11-14d | 2026-05-03 ~ 2026-05-06 |
| **approval +1d 지연** | 2026-04-23 | +8-10d | 2026-05-01 ~ 2026-05-03 |
| **approval +1주 지연** | 2026-04-29 | +8-10d | 2026-05-07 ~ 2026-05-09 |

## 가정

- ROI 적용된 H100 manifest (flash-attn-2 / torch.compile / bf16 / grad_ckpt+accum / CPGD active fold / EMA / curriculum tier)
- spot 4× H100 80GB HBM3 안정 (eviction 없음)
- AN11(a) PASS at first attempt (#86 r14 fallback 미발동)
- Φ ALL_PAIRS < 0.05 PASS at first attempt (#87 fallback 미발동)
- weight pre-cache R2 mirror 완료 (현재 p1 진행 중, ETA 5-10min)

## 핵심 trigger

```
bash tool/h100_stage2_unified_launch.bash --apply --yes-i-mean-it
```

오늘 실행 시 → **2026-04-30 (목) ~ 2026-05-02 (토) CP1 가능**.

approval 명시 대기 (memory: `project_h100_launch_pending.md`).

## roadmap link

#83 (H100 × 4 unified kickoff) · #77 (CP1 dest1 persona LIVE) · #84 (Grafana) · #85 (weight pre-cache) · #86prep (r14 fallback) · #87prep (Φ divergence response) · ext-1 ~ ext-10 (pre-flight)

---

# CP1 → CP2 → AGI v0.1 비용·일자 비교 (원화, 1USD=1,400KRW)

## Timeline (오늘 2026-04-22 approval 가정)

| 마일스톤 | **baseline** | **ROI 후** | 단축 |
|---|---|---|---|
| **CP1** (dest1 persona LIVE) | 2026-05-03 ~ 2026-05-06 | **2026-04-29 ~ 2026-05-02** | -4d |
| **CP2** (제타+직원+트레이딩 3-in-1, 7d stability) | 2026-05-10 ~ 2026-05-13 | **2026-05-06 ~ 2026-05-09** | -4d |
| **AGI v0.1** (#82 70B retrain done · #21 Mk.X 시작) | 2026-05-22 ~ 2026-05-28 | **2026-05-14 ~ 2026-05-21** | -7-8d |

## 비용 (4× H100 spot $7/hr)

| 단계 | baseline | ROI 후 | 절감 |
|---|---|---|---|
| **CP1 launch** (10-15d → 6-9d) | $1,680-2,520 = **₩2.35M ~ 3.53M** | $1,008-1,512 = **₩1.41M ~ 2.12M** | **₩940K ~ 1.41M** |
| CP1 → CP2 (eval + 7d stability, GPU burn ≈ 0) | $50-100 = **₩70K ~ 140K** | $50 = **₩70K** | ~₩0 |
| **CP2 → AGI** (70B retrain 10-15d → 8-12d) | $1,680-2,520 = **₩2.35M ~ 3.53M** | $1,344-2,016 = **₩1.88M ~ 2.82M** | **₩470K ~ 700K** |
| **compute 합계** | $3,410-5,140 = **₩4.77M ~ 7.20M** | $2,402-3,578 = **₩3.36M ~ 5.01M** | **₩1.41M ~ 2.19M** |

## 인건비 절감 (operator time, ₩50K/h 가정)

| 단계 | baseline 시간 | ROI 후 | 절감 |
|---|---|---|---|
| CP1 launch setup/check | 10-15h | 2-3h | 7-12h × ₩50K = **₩350K ~ 600K** |
| CP2 stability monitor | 5-10h | 1-2h | 4-8h × ₩50K = **₩200K ~ 400K** |
| AGI 70B retrain operator | 10-15h | 2-3h | 7-12h × ₩50K = **₩350K ~ 600K** |
| **인건비 합계** | | | **₩900K ~ 1.6M** |

## 종합 — AGI v0.1 까지 총 절감

| 항목 | 절감액 |
|---|---|
| compute | ₩1.41M ~ 2.19M |
| 인건비 | ₩900K ~ 1.6M |
| **합계** | **₩2.31M ~ 3.79M** |

## Calendar 그림 (전체)

```
2026-04-22 (today, approval)
│
│ ── baseline ────────────────────────────────────────────────
│   May 3 ─ 6        May 10 ─ 13        May 22 ─ 28
│   ┌─────┐          ┌─────┐            ┌─────────┐
│   │ CP1 │  +7d →   │ CP2 │   +9-15d→  │ AGI v0.1│
│   └─────┘          └─────┘            └─────────┘
│
│ ── ROI 후 ──────────────────────────────────────────────────
│   Apr 29 ─ May 2   May 6 ─ 9          May 14 ─ 21
│   ┌─────┐          ┌─────┐            ┌─────────┐
│   │ CP1 │  +7d →   │ CP2 │   +8-12d→  │ AGI v0.1│
│   └─────┘          └─────┘            └─────────┘
│   (4d 빠름)        (4d 빠름)          (7-8d 빠름)
│
│   AGI v0.1 도착: ~1주 단축 + ~₩2.3-3.8M 절감
```

## 가정 (CP2/AGI 추가)
- CP2 = #78 + #79 + #80 + #81 (7-day stability) — compute 거의 0 (대부분 inference + idle)
- AGI v0.1 = #82 70B retrain 완료 시점 (#21 Mk.X 본격 진입 전)
- 70B retrain = 4× H100 sustained × 10-15d (8B LoRA 대비 약 2× resource)
- ROI 효과: 10-15d → 8-12d (Stage-2 ROI 동일 적용 가정 + 70B 만의 추가 challenge 일부 흡수)
- spot eviction 0회 가정

## roadmap link 추가

#78 (제타가능) · #79 (직원가능) · #80 (트레이딩가능) · #81 (CP2 GATE 7d stability) · #82 (70B retrain) · #21 (AGI 최종 Mk.X T10-13)
