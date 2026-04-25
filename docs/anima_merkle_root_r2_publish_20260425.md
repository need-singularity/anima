# anima — meta² Merkle Root R2 Publish & Watch Daemon (2026-04-25)

## Summary

- Published `state/meta2_merkle_root.json` (commit `c975e83e`) to Cloudflare R2.
- Added `tool/meta2_merkle_watch.hexa` — daemon-style script that polls
  `.meta2-cert/`, rebuilds the Merkle root on change, emits a transition
  witness when the root actually moves, and re-publishes to R2.
- Selftest 5/5 PASS.  Manual one-shot run executed against `.meta2-cert/`.

## R2 publish

| field        | value                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------- |
| source       | `state/meta2_merkle_root.json`                                                              |
| size         | 510 bytes                                                                                   |
| sha256       | `735c0c30caf1c84f4d4e0056c0d9a481ec4b39965236ff5941ac95b801872b01`                          |
| merkle_root  | `0fc3ba903f63cbff4485267be6d1c4be755e4b07d451b624c54efca51d3d1edb`                          |
| commit       | `c975e83e`                                                                                  |
| R2 endpoint  | `r2:anima-logs/cert_chain/meta2_merkle_root_20260425T044705Z.json`                          |
| timestamp    | 2026-04-25T04:47:05Z (object key) / 2026-04-25T04:47:14Z (archive log)                      |

Retrieval verified via `rclone cat`; downloaded sha256 matches local.

## Archive log entry (raw#10)

Appended to `state/asset_archive_log.jsonl`:

```json
{"ts":"2026-04-25T04:47:14Z","path":"state/meta2_merkle_root.json","action":"archive_no_delete","status":"verified","detail":"r2_path=anima-logs/cert_chain/meta2_merkle_root_20260425T044705Z.json size=510 sha256=735c0c30... merkle_root=0fc3ba90... commit=c975e83e raw#10"}
```

## meta2_merkle_watch — design

### Inputs / outputs

| flow             | path                                       |
| ---------------- | ------------------------------------------ |
| watched dir      | `.meta2-cert/` (configurable `--root`)     |
| canonical builder| `tool/meta2_merkle_build.hexa`             |
| state            | `state/meta2_merkle_watch_state.json`      |
| witness ledger   | `state/meta2_merkle_root_witness.jsonl`    |
| archive log      | `state/asset_archive_log.jsonl`            |
| R2 prefix        | `r2:anima-logs/cert_chain/`                |

### Algorithm

1. Build dir fingerprint: `sha256(sorted(path|mtime|size for each *.json))`.
2. Compare with `state.fingerprint`.
3. If unchanged → write state (refresh `last_check`) and exit 0.
4. If changed → invoke `meta2_merkle_build` to recompute `merkle_root.json`.
5. Compare new root vs. previous root (from state, fall back to root file).
6. If root unchanged (mtime-only touch) → no witness, refresh state, exit 0.
7. If root changed → append JSONL witness `{prev_root, new_root, leaf_count,
   padded_count, tree_depth, fingerprint, ts}`, publish new root to R2 with
   timestamped key, append archive log entry, persist new state.
8. R2 failure is non-fatal: local root + witness still updated; archive log
   skipped (so verifiers can detect divergence).

### Schemas

- state    : `anima.meta2.merkle.watch.state.v1`
- witness  : `anima.meta2.merkle.witness.v1`
- root     : `anima.meta2.merkle.root.v1` (delegated to `meta2_merkle_build`)

### Modes

```
hexa tool/meta2_merkle_watch.hexa --selftest
hexa tool/meta2_merkle_watch.hexa --once --rclone-cfg ~/.config/rclone/rclone.conf
hexa tool/meta2_merkle_watch.hexa --once --no-publish    # local-only
```

Cron-driven daemon mode: schedule the `--once` invocation; the tool keeps
state across invocations via `state/meta2_merkle_watch_state.json`.

## Selftest (5/5 PASS)

```
T1 fingerprint stable on idempotent scan ........... PASS
T2 fingerprint delta when file added ............... PASS
T3 witness JSONL line valid (jq -e .schema) ........ PASS
T4 state read/write round-trip ..................... PASS
T5 prev_root extraction missing-file safe .......... PASS
```

## End-to-end demo (temp cert dir, --no-publish)

| run | trigger              | new_root (16-prefix) | witness emitted      |
| --- | -------------------- | -------------------- | -------------------- |
| 1   | bootstrap (10 leaves)| `0fc3ba903f63cbff`   | yes (prev="")        |
| 2   | add 11th leaf + idx  | `f8cc521f62e41593`   | yes (prev → new)     |

Witness JSONL append-only; verifier can replay
`prev_root → new_root` chain to reconstruct the cert epoch DAG.

## Manual run on real `.meta2-cert/`

```
[2026-04-25T04:49:07Z] meta2_merkle_watch: polling .meta2-cert
  prev_fp = <none>
  new_fp  = 9b8c57a9ce867ad3
  fingerprint delta — rebuilding root via meta2_merkle_build
  new_root  = 0fc3ba903f63cbff4485267be6d1c4be755e4b07d451b624c54efca51d3d1edb
  prev_root = 0fc3ba903f63cbff4485267be6d1c4be755e4b07d451b624c54efca51d3d1edb
  fingerprint changed but root identical (mtime-only touch) — no witness
```

State written: `state/meta2_merkle_watch_state.json` (fingerprint baseline now
established; future polls will only emit witnesses on real root changes).

## Files

- `tool/meta2_merkle_watch.hexa` (new)
- `state/meta2_merkle_watch_state.json` (new, baseline)
- `state/asset_archive_log.jsonl` (1 row appended)
- `docs/anima_merkle_root_r2_publish_20260425.md` (this doc)

## Caveats

- R2 publish from the watch tool is best-effort: failure logs an error and
  skips the archive log append, but the local root + witness are still
  updated.  A subsequent run with R2 reachable will not republish unless a
  new root change is detected — operators should re-publish manually if R2
  was offline at the time of a real transition.
- The watcher uses polling, not inotify/fsevents; intended for cron/launchd
  drive at ~1 min cadence.  Sub-second changes can still be coalesced
  because the fingerprint is mtime+size based.
- Determinism: rebuild delegates to `meta2_merkle_build.hexa` so leaf hash
  algorithm stays single-sourced (`sha256(jq -S -c 'del(.current_hash)' <entry>)`).
