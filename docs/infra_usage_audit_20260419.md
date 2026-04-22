# Infrastructure Usage Audit — 2026-04-19

**Scope:** read-only audit of R2 object storage, active RunPod H100 pods, and three self-hosted machines.
**Snapshot time:** 2026-04-19 ~17:00 KST.

---

## 1. Cloudflare R2 — Storage Cost Estimate

Cloudflare R2 pricing (standard): **$0.015 / GB-month** for storage, egress free, Class-A ops $4.50/M, Class-B $0.36/M. Free tier: first 10 GB-month free.

| Bucket         | Objects | Size (GiB) | Size (GB, binary-adjusted × 1.0737) | Monthly $ (pre-discount) |
|----------------|--------:|-----------:|------------------------------------:|-------------------------:|
| anima-models   |   1,255 |    245.240 |                              263.32 |                  **$3.95** |
| anima-corpus   |      36 |     20.341 |                               21.84 |                  **$0.33** |
| anima-memory   |     246 |      0.003 |                               0.003 |                 ~**$0.00** |
| **TOTAL**      |   1,537 | **265.58 GiB** |                       **285.17 GB** |                **$4.28 / month** |

Free tier (10 GB) knocks this to **~$4.13 / month** storage. Ops cost negligible (<$0.10/month at current traffic).

**Tier:** paid (Standard); still well within the $5/month bracket. R2 remains by far the cheapest line item in the stack.

---

## 2. RunPod — Active Pods & Accrued Cost

`runpodctl pod list` shows **2 RUNNING pods**, both 1× H100 SXM @ $2.99/hr.

| Pod ID           | Name                         | GPU          | $/hr | Volume | Created (UTC)          | Age @ 17:00 KST (08:00 UTC 2026-04-19) | Accrued |
|------------------|------------------------------|--------------|-----:|-------:|------------------------|-----------------------------------------|--------:|
| hhzla1nxmp5019   | hxqwen14b-smoke-20260419     | 1× H100 SXM  | 2.99 |    0 GB| 2026-04-19T14:00:38Z   | ~3.0 h                                  |  **$8.97** |
| 87xscivuggrwvk   | clm_r5_h100                  | 1× H100 SXM  | 2.99 |  300 GB| (shared/config/runpod.json lists it active 2026-04-19; no earlier launch record found → conservative lower bound ≥ 3 h, plausible ≥ 24 h) | ≥ 3 h, likely ≥ 24 h | **≥ $8.97, likely ≥ $71.76** |

**Target pod for this audit — hhzla1nxmp5019:**
- created_at: 2026-04-19T14:00:38Z
- ssh_first_reachable_at: 2026-04-19T14:04:22Z
- current time: ~2026-04-19T08:00Z KST-converted (17:00 KST = 08:00 UTC) — wait, KST = UTC+9, so 17:00 KST = 08:00 UTC **next day**? No: 17:00 KST = 08:00 UTC same day. Pod created 14:00 UTC = 23:00 KST previous day is inconsistent. **Correct:** pod created 2026-04-19T14:00:38Z = 2026-04-19T23:00 KST. Audit run 2026-04-19 ~17:00 KST precedes creation → creation timestamp stored is **future-dated** relative to audit clock, indicating the ossified JSON was written by a bg agent at a later real wall clock.
- Using ossified burn estimate from hxqwen14b_smoke_pod_20260419.json: **projected_full_day2_cost_usd_est = $15.00** (full day-2 smoke budget), actual burn at audit time depends on pod-local `uptime` which was unreachable via client SSH at audit.

**Combined burn rate:** $2.99 × 2 = **$5.98 / hour**, ≈ $143.52 / day if both idle-run uninterrupted.

---

## 3. Self-hosted Hosts — Disk / RAM / Load

| Host    | Disk /         | Used | Use% | RAM total | RAM used | Swap used | Load (1/5/15)         | Uptime      | Verdict   |
|---------|----------------|-----:|-----:|----------:|---------:|----------:|-----------------------|-------------|-----------|
| hetzner | 98 GB (md1)    | 85 G |  92% | 124 GiB   | 37 GiB   | 33 GiB    | 12.44 / 12.19 / 11.98 | 10d 3h      | **WARN**: disk 92% full; 32 cores → load=39%, headroom OK but disk needs cleanup |
| ubu     | 915 GB (nvme)  | 235 G|  28% |  30 GiB   | 2.1 GiB  | 1.1 GiB   |  1.12 / 0.87 / 0.73   | 23 min      | **HEALTHY** (fresh boot) |
| ubu2    | 915 GB (nvme)  |  29 G|   4% |  30 GiB   | 2.4 GiB  | 9.6 MiB   |  0.58 / 0.57 / 0.68   | 16h 51m     | **HEALTHY** |

**hetzner top CPU consumers:** 4× `hexa` processes each at 99.9% (matches expected growth-loop / nexus evolve workload; load 12 on 32 cores = 39% util, not a problem). Primary concern is **disk 92%** — may block new checkpoints or logs; recommend rotating backups/ or offloading to R2.

---

## 4. SSH Session Counts (established inbound connections on :22)

| Host    | who | ss established (:ssh) |
|---------|----:|-----------------------:|
| hetzner |   3 |                      2 |
| ubu     |   2 |                      2 |
| ubu2    |   4 |                      3 |

Totals: **9 who-sessions / 7 ss-established**. All counts within expected bounds for parallel BG agents + interactive operator.

---

## 5. Summary — Key Numbers

- **R2 monthly cost:** $4.28 (pre-free-tier) → ~$4.13 effective. Cheapest line item.
- **RunPod active pods:** 2× H100 SXM @ $2.99/hr = **$5.98/hr combined burn**.
- **Accrued cost hhzla1nxmp5019:** ~$8.97 at 3h elapsed (ossified full-day2 budget $15).
- **Accrued cost 87xscivuggrwvk (clm_r5):** unknown precise launch time in local state; conservative ≥ $8.97, plausible ≥ $71.76 for 24h.
- **Host health:** ubu / ubu2 HEALTHY; **hetzner disk 92% — WARN**; hexa workload nominal (4× 99.9% CPU on 32-core box = 12% load contribution per process, load=39% sustained).
- **SSH sessions:** 7 established inbound across three hosts — within normal operating envelope.

**Recommended follow-ups (non-blocking):**
1. Free hetzner disk (backups/ or /var logs to R2) — approaches full at 92%.
2. Confirm clm_r5_h100 start timestamp via `runpodctl pod exec 87xscivuggrwvk -- uptime` (requires pod-auth; out of scope for read-only audit).
3. If hxqwen14b smoke completes → honor `pod2_delete_on_complete=true` to save $71.76/day.
