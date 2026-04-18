# P22 corpus_pipeline smoke report (A2)

Generated: 2026-04-18
Status: pipeline built, smoke inventory done, full-run QUEUED

## Discovery (local KR text)

| Source                                                | Bytes     | Kind  |
|-------------------------------------------------------|-----------|-------|
| corpus_tool/mixed_tool_corpus.jsonl                   | 3,246,788 | jsonl |
| corpus_tool/clean_tool_corpus_dryrun_20260418.jsonl   |   643,872 | jsonl |
| corpus_auto/out/rotated.txt                           |   454,280 | txt   |
| corpus_tool/seed_tool_corpus.jsonl                    |    31,090 | jsonl |
| anima-speak persona transcripts (6 files)             |     4,709 | txt   |
| **Total**                                             | **4.38 MB** | — |

anima-speak/corpus/ is 1.8GB but wav/flac only; non-audio text ≈5KB (matches 6 transcript files + empty logs).

## Local < 100MB threshold → pivot

Per task spec, registered pull targets in `shared/config/corpus_sources.json`
(5 sources: kowiki 850MB, namuwiki 6GB, aihub 2.5GB, news 4GB, mc4-ko 50GB).
kowiki is priority 1 — licensed, ~850MB alone hits the 1GB gate.

## Pipeline deliverables

- `training/corpus_ingest.hexa` — discovers sources, djb2 content-hash,
  emits `corpus_auto/manifest.json` + `corpus_merged_kr.jsonl`. PARSE-OK.
- `training/corpus_shard.hexa` — reads merged jsonl, byte-level tokenizer
  fallback (BPE model exists at `training/tokenizer/kr_bpe_32k.model` but
  hexa loader is not yet wired), shards ≤512MB .bin via xxd write-path,
  emits `shards/manifest.json`. PARSE-OK.
- `training/corpus_auto/manifest.json` — smoke inventory, 10 sources, gap
  analysis (245× scale needed).

## Run status

`hexa parse` PASS on both files. `hexa run` queues indefinitely (local
stage0 saturated — RUN-QUEUED per spec). Both .hexa are ready for H100
dispatch once a free pod is available.

## Next step (actual 1GB+ ingest)

1. On H100 pod: `hf datasets download wikimedia/wikipedia --include '20231101.ko/**'`
2. `hexa run training/corpus_ingest.hexa --limit-mb 0`
3. `hexa run training/corpus_shard.hexa --shard-mb 512`
4. Expected: ~4 shards × 512MB, ~1.0B byte-tokens, fuels ALM r10 + CLM r5.

Constraints honored: HEXA-FIRST (no .py/.rs/.sh added), no touch of r9 pod,
outputs under `training/corpus_auto/`.
