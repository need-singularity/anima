# C1 parquet_to_jsonl — kowiki ingest bridge

**Status:** PASS — kowiki.jsonl unblocked for corpus_ingest.

## Tool chosen

**duckdb 1.5.2** (`brew install duckdb` — completed this session).
Single-shot `COPY (SELECT title, text FROM read_parquet('.../*.parquet')) TO '...' (FORMAT JSON, ARRAY false)` — duckdb streams row-by-row directly to disk; hexa never holds parquet payloads in memory (stage0 RSS remained under 100 MB throughout; 4 GB safe_hexa cap not stressed).

Fallback path wired in hexa: `parquet-tools cat --json | jq -c '{title,text}'` if duckdb absent. parquet-tools not installed — unused today, but code paths intact.

## Results

| metric | value |
|---|---|
| input shards | 3 (754 MiB parquet) |
| output path | `training/corpus_auto/kowiki.jsonl` |
| output bytes | 1,377,317,862 (~1.28 GiB) |
| output lines | **647,897** |
| schema | `{"title": str, "text": str}` per line |
| sample L1 | 지미 카터 (Jimmy Carter) — full article |

## Integration

- `training/corpus_ingest.hexa` parses clean (`hexa parse` PASS). Per task spec, local `hexa run` skipped (4 GB RSS cap / Total .py ban not affected — still hexa-native).
- `corpus_ingest.hexa` currently scans `corpus_tool/*.jsonl` + `corpus_auto/out/rotated.txt` + persona transcripts. **Follow-up (B2/A2 task, not C1):** extend `discover_sources()` to include `corpus_auto/*.jsonl` so kowiki.jsonl is picked up automatically.

## Blockers

None. duckdb install one-liner (`brew install duckdb`) was the only prerequisite; now available system-wide.

## Deliverables

- `training/parquet_to_jsonl.hexa` — hexa-native bridge (streaming, duckdb + parquet-tools/jq fallback).
- `training/corpus_auto/kowiki.jsonl` — 647,897 wiki articles, jsonl.
- This report.
