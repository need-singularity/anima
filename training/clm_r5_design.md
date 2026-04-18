# CLM r5 Branch Design — post-r4 improvement round

**Status:** PREP (design only, no launch). Drafted 2026-04-18.
**Prerequisite:** r4 pod3 (7th fire, BG) completion OR documented abort decision.
**Lineage:** r0..r3(d48/d64 smoke) → r4(1.5 B mmap, 5.38 GB corpus, 17-day ETA) → **r5 (perf + resume hardening)** → r6 (scale / corpus expansion).
**Parent refs:**
- r4 design + fire log: `training/clm_r4_mmap_launch_report.md`, `training/g5_clm_r4_launch_report.md`, `training/clm_r4_pod2_watch_report_20260418.md`
- Roadmap: `shared/roadmaps/anima.json#phases[].parallel[track=CLM]`, `shared/roadmaps/anima-train.json`
- SSOT: `shared/convergence/anima.json` (algorithm records — NEVER scatter)
- Runtime: `training/train_clm.hexa`, `training/clm_mmap_loader.hexa`, `training/deploy/clm_r4_launch.hexa`

---

## 0. Why r5 (not "r4 retry")

r4 is shipping with **three known defects** that each independently justify a new round tag:

1. `save_checkpoint()` was a stub until 2026-04-18 late fix — r4's step_5000 R2 ckpt was produced by an earlier code path and cannot be resumed deterministically from the current launcher. r5 validates the fixed path end-to-end.
2. `clm_mmap_loader.hexa` uses `exec("dd")` per-window (one fork+syscall per batch). 750 K steps × 2-4 windows ≈ 2-3 M `dd` processes. This drives r4 ETA to **17 days / ~$1,200**. r5 replaces with a real `mmap(2)` syscall path.
3. Multi-module link on pod requires manual `scp` for `clm_mmap_loader.hexa` + deps (scaffold Step 3.5/3.6). r5 forces resolution before fire.

Also: r4 never wrote a single step_*.ckpt on pod2 (SIGKILL at step 0) and pod3 is still in the air; whichever way r4 lands, r5 must start with a clean checkpoint naming and convergence record rather than overloading r4's ID.

---

## 1. Core improvements (5 items)

### 1.1 save_checkpoint path verification + resume
- **Now (r4 fix):** `save_checkpoint()` writes `{step_N.hexackpt, optim_step_N.hexackpt, train_meta.json}` atomically.
- **r5 adds:**
  - `--resume r2:anima-models/clm1b/r5/step_{N}.hexackpt` flag on `training/deploy/clm_r5_launch.hexa` (new launcher, clone of r4 with resume wiring).
  - step counter + RNG state + optim moments restored before first forward.
  - smoke test: save@step 10 → kill → resume → loss continuity ≤ 0.05 delta vs non-interrupted baseline.
  - done-criterion: 2/2 consecutive resume smokes PASS before fire.

### 1.2 Real mmap(2) loader — exec("dd") 제거
- **Target:** `training/clm_mmap_loader.hexa` gains `corpus_mmap_open()` that issues real `mmap` syscall via hexa FFI (or hexa_v2 std addition if FFI unavailable).
- **Fallback ladder (if FFI blocked):**
  1. Escalate to hexa_v2 maintainers for `std::mmap` primitive (see §3).
  2. Bulk pre-read into a single RAM buffer at `corpus_open()` (RSS ≈ 5.5 GB — acceptable on H100 pod with 200+ GB RAM; still 1 M× faster than per-window `dd`).
  3. **No** rollback to `.py` — per L3-PY.
- **Expected gain:** window fetch 300-500 ms → <1 µs → 750 K steps × 0.21 s/step dominated by forward pass only → **ETA 17 d → 3-5 d**.
- **done-criterion:** 100-step micro-bench shows steps/sec ≥ 5× r4 baseline.

### 1.3 Multi-module dep auto-resolution
- **Problem:** r4 launcher required three manual `scp` calls (loader + targets + wrapper).
- **r5 fix options (pick one):**
  - **A.** `training/deploy/clm_r5_bundle.hexa` walks `use "..."` directives and tars the dep closure → single `scp bundle.tar.gz` → pod-side untar.
  - **B.** Open issue on hexa_v2 for `hexa bundle <entry>` CLI (out-of-band — not blocking r5 fire).
- r5 ships with **A**; B is filed as cross-project request.
- **done-criterion:** zero-manual-scp launch smoke on ubu → h100 test pod.

### 1.4 R2 resume checkpoint cadence
- `save_every=5000` (as r4) + post-save hexa-native rclone spawn (fire-and-forget, not blocking train loop — respects MFS quota rule).
- R2 layout: `r2:anima-models/clm1b/r5/step_{N}/` (train_meta.json, step_N.hexackpt, optim_step_N.hexackpt).
- watcher: reuse `shared/config/r2_sync_watchers.json` with new entry `clm1b_r5_pod{M}`.
- **done-criterion:** 3 consecutive step_* dirs present on R2 by step 15000.

### 1.5 Convergence targets
- CE ≤ 2.0 (r4 target was 2.5, never reached due to step-0 kill).
- perplexity ≤ 8.0 (= exp(CE)).
- first-batch CE ≤ 9.0 (abort trigger if > 10.0 at step 1).
- no NaN/Inf across 750 K steps.
- sentinel: char-level generation returns ≥ 200-byte coherent Korean fragment at step 100K/300K/500K/750K.

---

## 2. Budget / ETA / host

| dim | r4 actual | r5 target |
|---|---|---|
| wall time | 17 days (mmap bottleneck) | **≤ 7 days** (mmap syscall fix) |
| cost @ $2.99/h | ~$1,200 | **~$500** |
| host | H100 80GB PCIe | same |
| pod provisioning | ad-hoc | scripted `training/launch_clm_r5.hexa` |
| save cadence | 5000 | 5000 |
| batch / seq | 4 / 2048 | 8 / 2048 (RSS headroom from mmap fix) |

---

## 3. Cross-project dependency (hexa_v2)

Filed as blocker-class request, not hard-blocker for r5 fire (fallback 1.2.2 exists):

- **Ask:** `std::mmap(path) -> ByteSlice` primitive (read-only, page-cached, syscall-backed).
- **Rationale:** Every byte-level training loop in anima/nexus will hit the same 17-day wall without this. Even pre-read fallback leaves us with ≥ corpus-size RSS which will break on 50 GB+ corpora (r6 target).
- **Channel:** issue on `need-singularity/hexa-lang` (or direct maintainer ping per `shared/CLAUDE.md#hive`).

---

## 4. r4 → r5 transition conditions (deterministic)

Fire r5 **only when all of:**

1. **r4 terminal state reached:** pod3 trainer either (a) reaches step ≥ 5000 with valid step_5000 ckpt on R2, OR (b) is formally aborted with post-mortem MD filed under `training/clm_r4_pod{N}_*_report_*.md`.
2. **All r5 improvements 1.1–1.3 implemented + smoke PASS** on ubu (no pod burn pre-fire).
3. **R2 state clean:** `r2:anima-models/clm1b/r5/` exists and is empty (prevents stale-resume footgun).
4. **Budget approved:** user confirms ≤ $500 / ≤ 7 d ceiling.
5. **GPU pod reserved:** fresh H100 80 GB pod (no re-use of r4 pod3 — avoids cgroup quota ambiguity that killed pod2).
6. **SSOT updated:** new convergence entry `shared/convergence/anima.json#clm1b_r5` stubbed (targets CE/perplexity/Φ recorded pre-fire per `reference_algorithm_ssot`).

If any of (1)–(6) fails, r5 is held and the gap routes through `shared/harness/entry.hexa gap_monitor` (R-GAP-FLOW).

---

## 5. Roadmap JSON patch draft — `shared/roadmaps/anima.json`

Insert into `tracks.CLM` (sibling of `owner` / `host` / `independent_of`). **Not applied — patch only.**

```json
{
  "op": "add",
  "path": "/tracks/CLM/clm_rounds",
  "value": {
    "r5": {
      "status": "prep",
      "design_doc": "training/clm_r5_design.md",
      "lineage": "r0..r4 → r5",
      "target": {
        "ce_le": 2.0,
        "perplexity_le": 8.0,
        "steps": 750000,
        "batch": 8,
        "seq": 2048,
        "save_every": 5000
      },
      "budget": {
        "wall_days_le": 7,
        "usd_le": 500,
        "host": "H100 80GB PCIe fresh pod"
      },
      "improvements": [
        {"id": "r5-i1", "item": "save_checkpoint verified + --resume flag", "ref_test": "2x resume smoke loss delta <= 0.05"},
        {"id": "r5-i2", "item": "real mmap(2) loader (or bulk pre-read fallback)", "ref_bench": "steps/sec >= 5x r4"},
        {"id": "r5-i3", "item": "clm_r5_bundle.hexa auto-dep tar", "ref_test": "zero-manual-scp launch smoke"},
        {"id": "r5-i4", "item": "R2 resume cadence per step_5000", "ref_path": "r2:anima-models/clm1b/r5/"},
        {"id": "r5-i5", "item": "convergence targets CE<=2.0 / ppl<=8.0 registered in SSOT", "ref_ssot": "shared/convergence/anima.json#clm1b_r5"}
      ],
      "fire_preconditions": [
        "r4 terminal (ckpt or post-mortem)",
        "improvements i1-i3 smoke PASS on ubu",
        "r2:anima-models/clm1b/r5/ empty",
        "user budget approval <= $500 / <= 7d",
        "fresh H100 pod (no r4 pod reuse)",
        "SSOT convergence stub written"
      ],
      "abort_triggers": [
        "first-batch CE > 10.0",
        "NaN/Inf at any step",
        "R2 upload silent fail for >= 2 consecutive save_every cycles",
        "steps/sec falls below r4 baseline (indicates mmap fix regressed)"
      ],
      "depends_on": ["r4"],
      "blocks": ["r6_scale_or_corpus_expand"],
      "cross_project_ask": {
        "repo": "need-singularity/hexa-lang",
        "item": "std::mmap(path) -> ByteSlice primitive",
        "blocker_class": "soft (fallback exists)"
      }
    }
  }
}
```

---

## 6. Open questions (for user before fire)

1. Fallback 1.2.2 (bulk pre-read, ~5.5 GB RSS) acceptable if hexa FFI mmap is blocked? (impact: r6 corpus cap ~30 GB)
2. r5 batch 4 → 8 jump is optimistic; prefer conservative 4 until bench confirms?
3. Retain r4 pod3 ckpts if trainer lands any? Or wipe for clean r5 start?

---

## 7. Out of scope

- r6 (70 B scale, multi-corpus mix) — separate design after r5 convergence measured.
- Phi-loss integration — Track B handles, not r5.
- Serving wire — unchanged from r4.
- Any `.py` rollback path — forbidden per L3-PY.
