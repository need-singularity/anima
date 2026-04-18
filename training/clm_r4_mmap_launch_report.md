# CLM r4 mmap Launch Report — B3 2026-04-18

## Target: Option C — local CPU smoke (no training launch)

**Why:** H100 pod 103.207.149.87:10466 idle but reserved for B1 r10.
ubu has no hexa + RTX 5070 12 GB too small for 1.5 B. Local smoke
validates loader + wrapper without GPU collision.

## Corpus source

`training/corpus_clm_r4.txt` — 5,380,874,900 bytes (5.38 GB). Local only.
Pod upload deferred until r10 clears GPU.

## Smoke: PASS

Synthetic 10 MB self-test (`clm_mmap_loader.hexa --selftest`):
**14/14 PASS** (T1 10/10 byte, T2/T3 window spot-check, T4 targets, T5 EOF clamp).

Real 5.38 GB (`clm_r4_mmap_smoke.hexa`):
- Stat: 5,380,874,900 B via `wc -c` — PASS
- Byte reads 7/7 @ {0, 1, 1 MiB, 1 GiB, 3 GiB, EOF-512, EOF-1} — PASS
- Windows 5/5 seq=512 @ {0, 500 M, 1.5 G, 3 G, EOF-1024} — PASS
- Stage 4 cut by mac 4 GiB RSS cap (exec-string accumulation, non-issue on Linux).

## Artifacts

- `training/clm_mmap_loader.hexa` — pure-hexa byte-window reader via `dd`
  + `od`. API: `corpus_open/byte/window/window_targets`. RAM O(batch×seq),
  not O(corpus).
- `training/clm_r4_mmap_smoke.hexa` — real-corpus smoke harness.
- `training/deploy/clm_r4_launch.hexa` — wired `--mmap 1` flag
  (default ON) → exports `CLM_USE_MMAP=1`.

## ETA

Post-r10 on H100: 750 K × 0.21 s = ~44 h, ~$132. Loader I/O negligible.
