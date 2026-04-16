# Shell Script `.hexa` Port Audit

**Date:** 2026-04-16
**Rule:** `모든 코드는 .hexa로 작성. sh/py/rs 신규 작성 금지` (ready/CLAUDE.md)

---

## Summary

- **Total `.sh` files:** 50 across 8 locations
- **Active (cited in CLAUDE.md):** 8
- **Already have `.hexa` equivalent:** 23/29
- **Legacy/dead code:** 19

**Port complexity:**
- ✅ Trivial: 21 files
- 🟡 Moderate: 9 files
- 🔴 Hard (bash-specific): 20 files

## Category Breakdown

| Location | Count | Active | With `.hexa` | Status |
|---|---|---|---|---|
| ready/scripts/ | 28 | 8 | 19 | 68% ported |
| training/ | 9 | 1 | 4 | 44% ported |
| ready/anima/ | 4 | 3 | 0 | **BLOCKING** |
| serving/ | 3 | 0 | 0 | Legacy |
| ready/models/ | 2 | 1 | 0 | Legacy |
| ready/core/ | 1 | 0 | 1 | Complete |
| scripts/ (root) | 1 | 0 | 0 | legacy? |
| other | 2 | 0 | 0 | Legacy |

## 8 Active Scripts (Must Port First)

| Script | Purpose | Lines | Complexity | Blocker |
|---|---|---|---|---|
| **h100_sync.sh** | Sync code to H100 (3-tier: rsync→scp→cat\|ssh) | 418 | Hard | Process substitution, pipes |
| **launch_h100.sh** | Launch H100 training + tmux | 397 | Hard | Heredoc, signal handling, tmux |
| **train_watchdog.sh** | Monitor/restart on crash (crontab) | 280 | Hard | Process substitution, signals |
| **notify_telegram.sh** | Telegram alerts | 76 | Trivial | None (curl only) |
| **preflight_training.sh** | Pre-launch validation | 240 | Moderate | md5 hashing, subprocess |
| **h100_retrieve.sh** | Poll for completion + auto-recover | 307 | Hard | — |
| **infinite_growth.sh** | Auto-roadmap for law evolution | 63 | Moderate | Process substitution, signals |
| **monthly_eeg_validate.sh** | EEG consciousness validation | 143 | Hard | Heredoc, trap |

## Recommended Port Order (Value × Feasibility)

### Phase 1 — 2–3 days, unblock monitoring

1. **notify_telegram.sh** (76L, trivial) → hexa HTTP client
2. **preflight_training.sh** (240L, moderate) → prevents training mishaps
3. **auto_restart.sh** (45L, trivial) → already has .hexa equiv, just deprecate .sh

### Phase 2 — 1 week, unblock H100 ops

4. **h100_sync.sh** (418L, hard) → split 3-tier fallback into separate hexa funcs
5. **train_watchdog.sh** (280L, hard) → hexa for logic, delegate signals to Rust

## Top 3 Easy Migrations (Already Have .hexa Equivalent)

| Script | .hexa Equiv | Action |
|---|---|---|
| notify_telegram.sh | ✅ notify_telegram.hexa | 76L → 45L hexa, drop curl |
| auto_restart.sh | ✅ auto_restart.hexa | Drop .sh immediately |
| cleanup_old_runs.sh | ✅ cleanup_old_runs.hexa | Drop .sh immediately |

**Action:** Update CLAUDE.md to reference `.hexa` versions only.

## Top 3 Hard Cases

| Feature | Impact | Hexa Equivalent |
|---|---|---|
| **Heredoc (<<)** × 11 scripts | Config gen, message formatting | ✅ Triple-quote + interpolation |
| **Process substitution `<()`** × 5 scripts | rsync fallback chains | ⚠️ Needs explicit pipe operator |
| **Trap + SIGINT/SIGTERM** × 8 scripts | Graceful shutdown | ⚠️ No signal hooks in hexa yet |

**Key blockers:**
- `h100_sync.sh`: 3-tier fallback needs process substitution. Workaround: separate hexa functions per tier.
- `launch_h100.sh`: tmux + signal forwarding. Workaround: delegate to Rust (anima-rs has tmux bindings).
- `train_watchdog.sh`: cron + SIGINT. Workaround: system cron + hexa logic, shell for signals.

## Dead Code (19 scripts, not referenced)

Candidates for `docs/deprecated_scripts/`:
- launch_animalm.sh (557L)
- launch_animalm_7b.sh (397L)
- transplant_v14_to_v3.sh (462L)
- training/convert_corpus_to_lines.sh
- training/deploy_h100.sh
- training/launch_alm_*.sh (4 files)
- training/native/build.sh
- serving/ckpt_save_hook.sh
- serving/launch_monitor_alm_r4.sh
- serving/serve_http.sh
- (+ 9 more)

**Recommendation:** Create `docs/deprecated_scripts/`, move with rationale comments. Git history preserved.

## Port Complexity Matrix

| Complexity | Count | Examples | Effort |
|---|---|---|---|
| Trivial | 21 | notify_telegram, cleanup, backup | 0.5–1 h |
| Moderate | 9 | preflight, monitor_and_test | 2–4 h |
| Hard | 20 | h100_sync, train_watchdog | 4–8 h |

## Bash-Specific Features → Hexa Equivalent Status

| Feature | Users | Hexa Status |
|---|---|---|
| Heredoc | 11 files | ✅ Triple-quoted strings |
| Process substitution `<()` | 5 files | 🟡 Workaround (nested calls) |
| Trap + signals | 8 files | ⚠️ Feature gap — no SIGINT hook yet |
| Cron integration | 2 files | ✅ System cron + hexa script |
| Sourcing libraries | 4 files | ✅ `import`/`include` |

## Validation Checklist

- [ ] All 8 active scripts ported to `.hexa`
- [ ] CLAUDE.md references only `.hexa`
- [ ] Backward-compat symlinks removed (force `.hexa` usage)
- [ ] CI tests on `.hexa` (no `.sh` fallback)
- [ ] 19 dead scripts moved to `docs/deprecated_scripts/`
- [ ] Hexa feature gaps closed (signal hooks, process sub)

**Next step:** Phase 1 port (notify_telegram.sh + preflight_training.sh + auto_restart.sh deprecation) — 2–3 days.
