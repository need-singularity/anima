# CLM-EEG P1 LZ sha re-sync (post readiness-check) — Landing

> **scope**: resolve P1 LZ tool sha mismatch flagged in `eeg_d_day_readiness_check_landing.md` §3.1; verify v1.1 already covers the re-freeze.
> **created**: 2026-04-27 | **raw_rank**: 9 | **status**: RESOLVED — no v1.2 bump needed.
> **cap**: mac local, $0, no GPU, no LLM.

## §1. Starting state

readiness-check §3.1 flagged P1 LZ: frozen `cd17abd8…` vs disk `cce9a801…` MISMATCH. but active SSOT is `clm_eeg_pre_register_v1_1.json` (frozen 2026-04-27 00:18), not legacy v1.json. v1.1 records P1 sha = `416e6be6f6e0c451a794e4fde160eca6fc3b9741fd81c430900f8b31d209bd27`. disk current = identical. mismatch was a stale-reference artifact (readiness-check compared against v1.0 archive sha block, not v1.1 active).

## §2. Action taken

no re-freeze, no v1.2 bump. v1.1 already covers P1 sha drift per its `v1_0_to_v1_1_diff` block. steps: (1) shasum 10 artifacts vs v1.1 `sha256_v1_1_frozen`; (2) recompute `chain_sha256` per `_recompute_recipe`; (3) re-run --selftest on 4 hexa tools + harness; (4) shasum again post-emission to confirm byte-identical; (5) write this landing doc, do NOT commit.

## §3. Ending state — 10/10 MATCH

| artifact | v1.1 frozen (head16) | disk (head16) | match |
|---|---|---|---|
| synthetic_fixture.hexa | `8297e2bf90acd7ef` | `8297e2bf90acd7ef` | yes |
| p1_lz.hexa | `416e6be6f6e0c451` | `416e6be6f6e0c451` | yes |
| p2_tlr.hexa | `fbff2e85a5e2a892` | `fbff2e85a5e2a892` | yes |
| p3_gcg.hexa | `0eec458cf7cc300b` | `0eec458cf7cc300b` | yes |
| harness_smoke.hexa | `18196513ba2c544e` | `18196513ba2c544e` | yes |
| synthetic_16ch_v1.json | `b6f1cc8669bf5bb5` | `b6f1cc8669bf5bb5` | yes |
| state/p1_emitted.json | `287cf30451866273` | `287cf30451866273` | yes |
| state/p2_emitted.json | `459a9725d5e04544` | `459a9725d5e04544` | yes |
| state/p3_emitted.json | `0c21f51391cf5f05` | `0c21f51391cf5f05` | yes |
| state/harness_emitted.json | `5d9f96e5137cc12c` | `5d9f96e5137cc12c` | yes |

recomputed `chain_sha256` = `647e04f7db5e802ed7069dfb6cbd94f8e90d56b9c25ca3f6097e55110c823a03` — IDENTICAL to v1.1 frozen. self-lock chain consistent. post-selftest re-shasum: 10/10 still MATCH (FNV-deterministic byte-identical).

## §4. Selftest verdicts (5/5 PASS)

synthetic_fixture=SYNTHETIC_FIXTURE_OK / p1_lz=P1_DRY_RUN_PASS / p2_tlr=P2_DRY_RUN_PASS / p3_gcg=P3_DRY_RUN_PASS / harness_smoke=HARNESS_OK (3/3). PASS=5, FAIL=0. harness chained_fingerprint=2588542012 (matches v1.0 archive chain_fnv32 — composite emit invariant).

## §5. Commit status

none. landing doc written, NOT committed. user reviews and decides staging.

## §6. D+1 entry recommendation

patch readiness-check §3.1 line 51 to reference v1.1 `sha256_v1_1_frozen` as authoritative baseline (frozen-v1.1=`416e6be6…` / disk=`416e6be6…` MATCH). on D+1 entry: shasum 10 v1.1 artifacts vs `sha256_v1_1_frozen`, require 10/10 MATCH before real-EEG verify trigger.

## §7. Refs

- v1.1 SSOT: `anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json`
- changelog: `anima-clm-eeg/docs/clm_eeg_pre_register_v1_to_v1_1_changelog.md`
- predecessor: `anima-clm-eeg/docs/eeg_d_day_readiness_check_landing.md` §3.1, §6 #4
- marker: `anima-clm-eeg/state/markers/clm_eeg_v1_1_patch_complete.marker`
