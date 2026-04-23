# R2 → Pod Bandwidth Measurement Guide (pre-H100 ROI S2)

**Date:** 2026-04-22
**Owner:** anima/serving
**Track:** pre-H100 ROI · S2
**Status:** spec-only (DO NOT spawn pod from this doc)

## 1. Purpose

H100 × 4 cold-start latency is dominated by R2 → pod weight transfer
(~25–50 GiB per shard set). Before scheduling the live pod we need a
calibrated bandwidth estimate so the launch budget can be defended.

This guide specifies a **single 30-minute minimal-pod measurement run**.
It is the *only* live R2-egress activity sanctioned in pre-H100 phase.

## 2. Hard constraints

- **Pod size:** smallest available CPU pod (no GPU). Target: 4 vCPU / 8 GiB RAM.
- **Wall-clock cap:** 30 minutes (incl. container pull + tear-down).
- **Egress cap:** 50 GiB total (R2 egress is free intra-Cloudflare; still cap as guard).
- **DO NOT** issue PUT/DELETE; read-only credentials only.
- **DO NOT** modify any object metadata.
- **DO NOT** run on H100 (waste of $/hr); CPU pod is sufficient for net-IO bench.

## 3. Test matrix (single run, 30 min)

| Phase | Duration | Object pattern | Concurrency | Purpose |
|-------|----------|----------------|-------------|---------|
| P0 warmup    | 2 min  | 1 × 100 MiB | 1   | DNS / TLS handshake amortization |
| P1 sequential| 6 min  | 6 × 4 GiB   | 1   | Cold per-stream throughput baseline |
| P2 parallel-4| 6 min  | 4 × 4 GiB   | 4   | Match TP=4 weight fan-in |
| P3 parallel-8| 6 min  | 8 × 4 GiB   | 8   | Find saturation knee |
| P4 mixed     | 6 min  | 16 × 256 MiB + 1 × 4 GiB | 8 | Realistic shard mix |
| P5 cooldown  | 4 min  | —           | —   | Drain logs, metrics flush |

Total bytes transferred: ~120 GiB worst case → keep under 50 GiB by reusing
the same 4 GiB scratch object across phases (prefix
`anima-models/scratch/bw_probe_4g.bin`, lifecycle-expired in 14 days).

## 4. Pod spec (paste into provisioner — DO NOT auto-launch)

```yaml
provider: runpod-cpu  # or vast.ai cpu
image: rclone/rclone:1.72.1
resources:
  vcpu: 4
  ram_gib: 8
  disk_gib: 60
network:
  region: us-east  # match R2 jurisdiction
env:
  R2_ENDPOINT_URL: ${R2_ENDPOINT_URL}
  RCLONE_S3_ACCESS_KEY_ID: ${R2_RO_KEY}
  RCLONE_S3_SECRET_ACCESS_KEY: ${R2_RO_SECRET}
runtime_max_minutes: 30
```

## 5. Measurement commands (rclone)

Each phase logged via `rclone copy ... --progress --stats=5s --use-json-log`.
Save raw logs to `state/r2_bandwidth_<phase>_<utc>.json`.

```bash
# P1 — sequential 1-stream
rclone copy r2:anima-models/scratch/bw_probe_4g.bin /tmp/dl/p1/ \
  --transfers 1 --use-json-log --stats 5s --log-file /var/log/p1.json

# P2 — parallel 4
rclone copy r2:anima-models/scratch/ /tmp/dl/p2/ \
  --transfers 4 --include "bw_probe_4g.bin" --use-json-log --log-file /var/log/p2.json

# (P3/P4 analogous; vary --transfers and --include patterns)
```

## 6. Reported metrics (state/r2_bandwidth_summary.json)

```json
{
  "phase": "P2",
  "concurrency": 4,
  "total_bytes": 17179869184,
  "wall_seconds": 41.3,
  "throughput_mib_s": 396.7,
  "p50_first_byte_ms": 78,
  "p99_first_byte_ms": 412,
  "egress_cost_usd": 0.0,
  "errors": 0
}
```

## 7. Acceptance gates

- P2 throughput >= 250 MiB/s aggregate → H100 cold-load ETA <= 7 min for 100 GiB shard set
- Error rate < 0.1 % across all phases
- p99 first-byte latency < 1500 ms

If gates fail, escalate to track #83 (track_relation) before booking H100.

## 8. Tear-down (mandatory)

1. `rclone purge r2:anima-models/scratch/bw_probe_4g.bin` — *only* if uploaded fresh
2. Stop pod, confirm billing minute count <= 30
3. Append run summary to `state/r2_bandwidth_runs.jsonl`
4. Open follow-up entry in roadmap track #83 if any gate failed

## 9. References

- `config/vllm_container_template.json` — S1 template that consumes this BW estimate
- `docs/R2-BUCKET-STRUCTURE.md` — bucket layout
- `docs/r2_bucket_audit_20260419.md` — current size/object counts
- `tool/r2_lifecycle_apply.bash` — scratch/ expiry policy
