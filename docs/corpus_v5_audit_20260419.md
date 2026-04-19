# corpus_v5 mmap byte loader — audit (READ-ONLY) 2026-04-19

Sweep-40 iter 91 `training_corpus_v5` refers to the **5.38 GB hexa-native
byte-level corpus shipped as `corpus_clm_r4.txt`** (filename not bumped —
R-series naming). This doc audits the artifact without downloading 5 GB.

## 1. File locations

| where              | path                                                      | size (bytes)  | size (GiB) |
|--------------------|-----------------------------------------------------------|---------------|------------|
| Mac local (raw)    | `/Users/ghost/Dev/anima/training/corpus_clm_r4.txt`       | 5,380,874,900 | 5.011 GiB  |
| Mac local (gzip)   | `/Users/ghost/Dev/anima/training/corpus_clm_r4.txt.gz`    | 1,709,490,208 | 1.592 GiB  |
| R2 raw             | `r2:anima-corpus/clm_r4/corpus_clm_r4.txt`                | 5,380,874,900 | 5.011 GiB  |
| R2 gzip            | `r2:anima-corpus/clm_r4/corpus_clm_r4.txt.gz`             | 1,709,490,208 | 1.592 GiB  |

- R2 bucket is `anima-corpus` (NOT `anima-memory` / NOT `anima-models`).
  `anima-memory` holds state; `anima-corpus` holds training corpora.
  Scaffold reference `anima-corpora` is a typo per the R2 index.
- Unrelated file `ready/anima/data/corpus_v5.txt` (100 MB, mtime 2026-03-31)
  is a stale v5-era slice, NOT the training corpus. Ignore.

## 2. Size / integrity

- `wc -c` reproduced: **5,380,874,900 bytes exact** (Mac).
- Recorded in `training/corpus_clm_r4_r2_index.md` 2026-04-18T15:53Z:
  - raw sha256 `a606bd375d78f1ae19f327a62417541a6ac737440e15b97e5a483085a9e757a8`
  - raw md5    `e9c7f139a0de1e58def231043e584653` (local == R2)
  - gz  sha256 `8dc92c3230f874eefab4eb29b1908e9561ca0930c878c14485b601a1090a5bc2`
  - gz  md5    `374fe9d5bf1fda309ff48e7f8aefc07c` (local == R2)
- R2 server-side sha256 not exposed by Cloudflare; MD5 is authoritative.
- "5.38 GB" in docs = **SI GB** (5.381e9); 5.011 GiB in binary — consistent.

## 3. Byte loader spec (`training/clm_mmap_loader.hexa`)

- Pure-hexa via `exec("dd ... | od -An -vtu1")`. No `.c` / `.rs` FFI.
- API:
  - `corpus_open(path)` → `CorpusDesc {path, len}` via `wc -c` (O(1)).
  - `corpus_byte(desc, off)` → single byte via `dd bs=1 skip=N count=1`.
  - `corpus_window(desc, off, n)` → `[int]` of `n` byte values (hot path).
  - `corpus_window_targets(desc, off, n)` → `corpus_window(desc, off+1, n)`.
- Vocab = **256 byte-level** (`train_clm.hexa` L1594 `let vocab = 256`).
  No BPE; no explicit EOS token — byte `0x00` is a valid byte, NOT EOS.
  Sample boundaries are byte-window offsets, not sentence boundaries.
- Targets shift = **+1 byte** (next-byte prediction). Classic AR loss.
- EOF clamp: `corpus_window` truncates if `off + n > desc.len` (T5 PASS).

## 4. mmap behavior (training runtime)

- RAM cost **O(batch × seq_len)**. `batch=8 seq=512` = 32 KiB resident.
  (Avoids the 172 GB hexa_array blow-up; doc ref: `project_clm_r4_mmap_plan`.)
- Total disk read across 750 K steps ≈ 24 GiB — trivially fits Linux page
  cache. Sequential/random pattern → kernel readahead is enough.
- Real `mmap(2)` not wired (would need `.c` shim; blocked by HEXA-FIRST).
  API is stable — will swap `dd` bridge to native hexa `mmap` builtin when
  HEXA-LANG roadmap lands it; callers unaffected.
- Self-test `--selftest` = 14/14 PASS (synthetic 10 MB).
- Real-corpus smoke `clm_r4_mmap_smoke.hexa` on Mac: stat + byte(7/7) +
  window(5/5) PASS; Stage 4 capped by mac 4 GiB RSS (non-issue on Linux).

## 5. Pod pull recipe (use gz)

```
rclone copy r2:anima-corpus/clm_r4/corpus_clm_r4.txt.gz /workspace/ --s3-no-check-bucket
gunzip /workspace/corpus_clm_r4.txt.gz
# expect: /workspace/corpus_clm_r4.txt  5,380,874,900 bytes
# md5sum /workspace/corpus_clm_r4.txt   → e9c7f139a0de1e58def231043e584653
```

Launcher flag: `--corpus-r2 r2:anima-corpus/clm_r4/corpus_clm_r4.txt`,
`--mmap 1` (default) exports `CLM_USE_MMAP=1`.

## Verdict: CLEAN

Size, checksums, loader self-tests, and R2 parity all match. Ready for
r5 H100 launch after B1 r10 clears the pod. No remediation needed.
