# corpus_ingest kowiki wiring — E2 (2026-04-18)

## What shipped

- **`training/corpus_ingest.hexa`**: `discover_sources_impl(only_new)` now scans `corpus_auto/*.jsonl`, picking up `kowiki.jsonl` (1.28 GiB, 647,897 lines). New flags: `--only-new` (restrict to `corpus_auto/*.jsonl` pull-targets) and `--list-only` (enumerate sources without reading). Self-loop guard excludes `corpus_merged_kr.jsonl`.
- **`training/corpus_ingest_probe.hexa`**: standalone 1000-line probe. Streams via `head | jq -r .text | head -c 5120` to stay under the 4 GB RSS cap, then byte-decodes UTF-8 and tallies U+AC00..U+D7AF (Hangul syllables).
- **`training/corpus_auto/manifest.json`**: kowiki entry appended with `bytes=1,377,317,862`, `lines=647,897`, `sha256=d1aabfdb…cb1c`, probe payload, and an `only_new_ingest` block.

## Probe result

```
[probe] kowiki lines_sample=1000 bytes_sample=10435766 hangul_ratio=85% verdict=OK
```

85% Hangul — well above the 60% OK threshold.

## Discovery verification

- `--list-only` (full):  11 sources (kowiki + 3 tool_corpus + rotated.txt + 6 transcripts).
- `--list-only --only-new`: 1 source (kowiki.jsonl only).

## What did NOT run

Full `--only-new` ingest deferred: `read_file(1.28 GiB)` + content_hash loop blows the 4 GB RSS cap (confirmed empirically — SIGKILL on first attempt at 10 MB sample). Run on H100 with `HEXA_LOCAL=0 hexa run training/corpus_ingest.hexa --only-new --limit-mb 2048` or refactor to streaming via `corpus_shard.hexa`.

## Pitfalls logged

`shared/state/hexa_pitfalls_log.jsonl` (+2 entries): stage0 `.find()` absence and exec+split OOM pattern.
