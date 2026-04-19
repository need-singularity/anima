# R2 Bucket Audit — 2026-04-19

Tool: rclone v1.72.1 remote `r2:` (env ANIMA_R2_*). List-only (no download).
Endpoint: `ce4bdcce7c74d4e3c78fdf944c4d1d7b.r2.cloudflarestorage.com`

## Top-level buckets

| Bucket                | Objects | Size       | Notes                              |
|-----------------------|---------|------------|------------------------------------|
| anima-memory          | 246     | 2.58 MiB   | state/memory (lineage, pod_logs)   |
| anima-models          | 1 255   | 245.24 GiB | checkpoints + corpus               |
| anima-corpus          | 36      | 20.34 GiB  | separate corpus bucket             |
| anima-eeg             | 0       | 0 B        | empty                              |
| anima-logs            | 0       | 0 B        | empty                              |
| blitz / evo / odds / prism | —  | —          | pre-anima, skipped                 |

R2 has no hard quota (pay-as-you-go); `rclone about` unsupported on S3 root.

## anima-memory directory tree (2.58 MiB)

```
lineage/          pod_logs/         session_20260411/
state_20260417/   worktree_py_archive/
```

## anima-models directory tree (245.24 GiB, 1 255 obj)

| Dir                              | Size       | Obj  |
|----------------------------------|------------|------|
| corpus/                          | 66.02 GiB  | 149  |
| clm1b/                           | 53.96 GiB  | 6    |
| alm14b/                          | 45.89 GiB  | 765  |
| clm3b/                           | 35.17 GiB  | 2    |
| base_models/                     | 27.52 GiB  | 16   |
| archive_pre_clm_alm_20260411/    | 8.78 GiB   | 16   |
| alm72b/                          | 2.43 GiB   | 4    |
| clm_byte_kr/                     | 1.90 GiB   | 16   |
| clm_d256_wiki/                   | 1.23 GiB   | 10   |
| alm32b/                          | 1.13 GiB   | 3    |
| alm7b/                           | 516.3 MiB  | 1    |
| decoder_cpu_p3/                  | 417.6 MiB  | 2    |
| adapters/                        | 207.2 MiB  | 10   |
| clm-d64-kr/                      | 86.1 MiB   | 24   |
| voice_corpus/                    | 12.4 MiB   | 82   |
| clm_gpu/                         | 5.4 MiB    | 1    |
| state/                           | 1.1 MiB    | 124  |
| tokenizer/                       | 694.9 KiB  | 5    |
| py_ban_evidence/                 | 100.0 KiB  | 6    |
| dest1_p1_persona_vectors/        | 246.6 KiB  | 3    |
| dest1_s1_endpoint/               | 33.5 KiB   | 3    |
| dest1_persona/                   | 23.7 KiB   | 4    |
| dest1_c2_laws_gate/              | 2.5 KiB    | 2    |
| dest1_c1_phi_hook/               | 4.9 KiB    | 1    |

## dest1_alm / dest1_clm upload capacity

R2 has no project-wide limit. Existing `dest1_*` namespaces under
`anima-models/` consume <600 KiB total (6 dirs). Headroom for
`dest1_alm/` and `dest1_clm/` uploads is effectively unbounded at the
bucket level; Cloudflare class-A ops cost is the only constraint.

Recommended layout:
- `r2:anima-models/dest1_alm/<iso_ts>/` (adapter shards + manifest)
- `r2:anima-models/dest1_clm/<iso_ts>/` (ckpt shards + manifest)

## Observations

1. `anima-models` dominated by corpus (66 GiB) + clm1b (54 GiB) +
   alm14b (46 GiB) + clm3b (35 GiB) — 83 % of bucket.
2. `anima-eeg` and `anima-logs` are provisioned but empty — usable for
   split-out telemetry without contention.
3. `archive_pre_clm_alm_20260411/` (8.78 GiB) — candidate for cold-tier
   review after next ossified checkpoint.
4. `alm14b/` has 765 objects against 45.9 GiB — many small shards; new
   uploads should consolidate to reduce class-A ops.

---

Audit artifacts generated 2026-04-19 by main-session subagent.
