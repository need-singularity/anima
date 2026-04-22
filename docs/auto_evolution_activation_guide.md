# anima auto-evolution 12h cycle — manual activation guide

Status: **MANUAL-ONLY** (raw#20 + agent-never-auto-activates invariant).
Scope: pre-H100 ROI N4 — guide for the user (only the user) to activate the
12-hour `com.anima.auto_evolution` launchd agent on their workstation.

> **The agent will never run any of the commands in this document.** They are
> for the human operator to execute, after deciding the proposal stack is
> mature enough to evolve unattended every 12 hours.

---

## 1. What gets activated

Plist file: [`config/launchd/com.anima.auto_evolution.plist`](../config/launchd/com.anima.auto_evolution.plist)

| key | value |
|---|---|
| Label | `com.anima.auto_evolution` |
| StartInterval | 43200 sec (= 12h) |
| RunAtLoad | `false` |
| Working dir | `/Users/ghost/core/anima` |
| Command | `hexa run tool/auto_evolution_loop.hexa --apply` |
| stdout | `/tmp/anima_auto_evolution.out` |
| stderr | `/tmp/anima_auto_evolution.err` |

The loop tool (`tool/auto_evolution_loop.hexa --apply`) executes, in order,
the 8-step proposal stack cycle defined in
`docs/anima_proposal_stack_paradigm_20260422.md` §3:

1. `proposal_inventory_init`
2. per-pending refinement (version bump)
3. `proposal_emit --apply`  (max 20 new per cycle, dedup by sha256)
4. `proposal_cluster_detect --apply`
5. `proposal_conflict_detect --apply`  (auto debate folder routing)
6. `meta/metrics.json` refresh
7. `proposal_dashboard` regenerate
8. notify (slack via env `SLACK_WEBHOOK_URL` when set)

Per-step results are appended to `state/proposals/meta/cycle_log.jsonl`.

**INVARIANT (enforced by every step)**: never mutates `tool/`, `config/`,
or `.roadmap`. Only `state/proposals/` is written.

---

## 2. Pre-flight checklist (run BEFORE activation)

Run each step manually. Do not skip.

```sh
# 2.1 Verify the loop tool selftests pass.
hexa run tool/auto_evolution_loop.hexa --selftest

# 2.2 Verify each component selftest.
hexa run tool/proposal_emit.hexa             --selftest
hexa run tool/proposal_cluster_detect.hexa   --selftest
hexa run tool/proposal_conflict_detect.hexa  --selftest
hexa run tool/proposal_dashboard.hexa        --selftest
hexa run tool/proposal_auto_threshold.hexa   --selftest
hexa run tool/proposal_cluster_consolidate.hexa --selftest

# 2.3 Dry-run a full cycle WITHOUT --apply.
hexa run tool/auto_evolution_loop.hexa

# 2.4 Inspect the dashboard and the top-10 review docs.
cat docs/proposal_dashboard.md
cat docs/proposal_top10_review_20260422.md

# 2.5 Confirm the threshold gate emits 0 (no auto-implement candidates).
hexa run tool/proposal_auto_threshold.hexa --include-pending
```

Acceptance criteria before proceeding to §3:

- [ ] All selftests in 2.1 + 2.2 exit `0`.
- [ ] Dry-run in 2.3 prints a sane plan (per-step counts visible).
- [ ] Top-10 review reflects current `state/proposals/pending/`.
- [ ] Auto-threshold reports **0** approved candidates with score≥80 + risk=0.

If any item fails, **abort activation** and resolve before retrying.

---

## 3. Activation (USER-EXPLICIT)

```sh
# 3.1 Symlink the plist into ~/Library/LaunchAgents/ AND launchctl load.
bash tool/launchd_install_local.bash --activate
```

This invokes the existing helper (`tool/launchd_install_local.bash`) which:

1. `mkdir -p ~/Library/LaunchAgents`
2. `ln -sf $ANIMA_ROOT/config/launchd/com.anima.auto_evolution.plist ~/Library/LaunchAgents/`
3. `launchctl load -w ~/Library/LaunchAgents/com.anima.auto_evolution.plist`

The flag `-w` makes the load persist across reboots. Because the plist sets
`RunAtLoad=false`, **the first cycle fires 12 hours after activation**, not
immediately. To force a manual first run:

```sh
launchctl start com.anima.auto_evolution
tail -f /tmp/anima_auto_evolution.out /tmp/anima_auto_evolution.err
```

---

## 4. Verification (immediately after §3)

```sh
# 4.1 Confirm the agent is loaded.
launchctl list | grep com.anima.auto_evolution
# Expect: <pid_or_-> 0 com.anima.auto_evolution

# 4.2 Confirm the symlink is in place.
ls -l ~/Library/LaunchAgents/ | grep com.anima.auto_evolution

# 4.3 Status report from the install helper.
bash tool/launchd_install_local.bash --status
```

If `launchctl list` shows a non-zero exit code in column 2, run
`cat /tmp/anima_auto_evolution.err` and resolve before relying on the cycle.

---

## 5. Monitoring during steady-state

| signal | where |
|---|---|
| per-cycle results | `state/proposals/meta/cycle_log.jsonl` (append-only) |
| metrics snapshot  | `state/proposals/meta/metrics.json` |
| dashboard         | `docs/proposal_dashboard.md` (rewritten each cycle) |
| stdout            | `/tmp/anima_auto_evolution.out` |
| stderr            | `/tmp/anima_auto_evolution.err` |
| slack notify      | `$SLACK_WEBHOOK_URL` if set in user shell env |

Recommended cron-side observers (also user-only, not agent):

```sh
# Tail the cycle log for the next 6 cycles.
tail -F state/proposals/meta/cycle_log.jsonl

# Daily digest at 09:00 — drop into your own crontab if desired.
hexa run tool/proposal_dashboard.hexa --md > /tmp/anima_proposal_digest.md
```

---

## 6. Deactivation

```sh
# 6.1 Unload + remove the symlink.
bash tool/launchd_install_local.bash --unload

# 6.2 Confirm.
launchctl list | grep com.anima.auto_evolution || echo "(unloaded — ok)"
```

`--unload` is idempotent: re-running on an already-unloaded agent is a
no-op.

---

## 7. Hard constraints (binding on the AGENT, not the user)

| # | rule | enforced where |
|---|---|---|
| 1 | The agent NEVER runs `bash tool/launchd_install_local.bash --activate`. | this guide; agent system prompt |
| 2 | The agent NEVER writes / edits any `*.plist` file. | raw#20 |
| 3 | The agent NEVER edits `.roadmap`. | uchg |
| 4 | The agent NEVER auto-approves a proposal nor implements a module. | raw#20 |
| 5 | Even `--apply` mode of `auto_evolution_loop.hexa` only mutates `state/proposals/`; it cannot create `tool/` or `config/` files. | per-step invariant in `docs/anima_proposal_stack_paradigm_20260422.md` §3 |
| 6 | The threshold gate (`tool/proposal_auto_threshold.hexa`) emits propose-only md (raw#20) and only for proposals already in `state/proposals/approved/`. | tool selftest S5 |

---

## 8. Rollback procedure

If a cycle behaves badly (e.g. flood of bad proposals):

```sh
# 8.1 Immediate stop.
bash tool/launchd_install_local.bash --unload

# 8.2 Triage — every cycle is recorded.
tail -100 state/proposals/meta/cycle_log.jsonl

# 8.3 Optionally roll back the offending pending proposals (manual reject).
hexa run tool/proposal_reject.hexa --id <N> --reason "auto-cycle regression"
```

The proposal stack is append-only by design, so no destructive rollback
is needed — just user-driven reject sweeps.

---

## 9. Decision log entry (append after activation)

When you (the user) activate, please record the decision in
`DECISION_LOG.csv`:

```csv
2026-04-22T??:??Z,roi_n4,user,activate auto_evolution 12h cycle,manual via launchd_install_local.bash --activate
```

This makes the activation visible to future audits without requiring
agent-side bookkeeping.
