# raw 95 triad-universal-mandate audit ledger schema

**status**: schema-v1 reference doc (2026-04-28)
**scope**: append-only audit ledgers under `state/audit/*.jsonl` enforcing raw 95 triad-universal-mandate
**applies-to**: both existing anima ledgers
- `state/audit/anima_canonical_helper_lock.jsonl` (1 row, lock/unlock events on canonical helper set)
- `state/audit/anima_own_strengthen_audit.jsonl` (10 rows, .own edit cycles + chflags housekeeping)

raw cross-references: raw 1 (os-lock) · raw 77 (audit-ledger append-only) · raw 85 (escalation-audit-trail-witness) · raw 95 (triad-universal-mandate) · raw 91 (honesty triad C2 write_barrier)

---

## §1 row format

Each line in an audit ledger is a single self-contained JSON object (JSONL). One JSON value per `\n`-terminated line, no surrounding array, no leading commas. Lines MUST parse independently — order matters but downstream tooling reads line-by-line.

Append-only enforcement: ledgers are protected by `chflags uappnd` after creation. New rows append via shell `>>` redirection or equivalent; in-place edits trigger kernel `EPERM`. raw 77 mandate.

A row represents one event (one action against one or more targets). Multi-target events use `target_paths` (array) instead of `target_path` (scalar).

---

## §2 required columns

Every row MUST carry the following keys:

| key            | type           | meaning                                                                              |
|----------------|----------------|--------------------------------------------------------------------------------------|
| `ts`           | string ISO8601 | UTC timestamp of the action, format `YYYY-MM-DDTHH:MM:SSZ`                           |
| `action`       | string enum    | one of the action enum values in §4                                                   |
| `reason`       | string         | human-readable rationale; must include the raw/own/iter that motivated the action    |
| `target_path`  | string path    | absolute or repo-relative path to the file affected (use `target_paths` array if >1) |
| `before_flags` | string         | chflags state before action (e.g. `-`, `uchg`, `uappnd`)                              |
| `after_flags`  | string         | chflags state after action (e.g. `uchg`, `uappnd`)                                    |

For the `anima_canonical_helper_lock.jsonl` ledger, the row may use `applied[]` (array of `{path, rc, stderr}`) in lieu of `target_path`/`before_flags`/`after_flags` when the action is a batch lock/unlock — see §4 for `lock`, `unlock` actions. The applied array carries equivalent information per-target.

---

## §3 optional columns

Optional keys carry context for raw 85 escalation audit trail and raw 95 triad enforcement:

| key                         | type    | meaning                                                                              |
|-----------------------------|---------|--------------------------------------------------------------------------------------|
| `escalation_window_sec`     | integer | raw 85 mandated max sec between unlock and relock (typically `300`)                  |
| `unlock_ts`                 | string  | ISO timestamp of paired unlock event                                                 |
| `relock_ts`                 | string  | ISO timestamp of paired relock event                                                 |
| `unlock_to_relock_window_sec` | integer | actual measured seconds between unlock and relock; must be ≤ `escalation_window_sec`  |
| `raw_85_compliance`         | string  | `PASS` / `FAIL` / `no_unlock_event_no_escalation_window_required`                    |
| `raw_77_audit_ledger_schema_v1` | bool | `true` if the row conforms to this schema                                             |
| `classifier-version`        | string  | ledger schema classifier (e.g. `anima_own_strengthen_audit.v1`)                       |
| `edit_summary`              | string  | summary of the edit applied during the unlock-edit-relock cycle                       |
| `kick_witness_path`         | string  | path/url to the kick witness or session id that motivated the edit                    |
| `window_violation_evidence` | string  | when raw 85 violated: evidence of the violation timing                                |
| `helper_count`              | integer | (lock-ledger only) count of canonical helpers covered by the lock action              |
| `applied`                   | array   | (lock-ledger only) per-path `{path, rc, stderr}` for batch operations                 |
| `verification_target`       | string  | (consistency-check action only) glob/path of files verified                           |
| `rows_checked`              | integer | (consistency-check action only) number of audit rows cross-checked                    |
| `inconsistencies`           | integer | (consistency-check action only) count of rows whose `after_flags` claim mismatched FS |
| `verdict`                   | string  | (consistency-check or scan-result action) PASS/FAIL summary                           |
| `persisted_artifacts`       | array   | paths to durable verdict.json/.txt artifacts produced by the action                   |
| `classification`            | string|object | sub-typing for chflags actions (e.g. `session_permanent_reference_snapshot`)     |
| `note`                      | string  | free-form follow-up notes (e.g. canonical-helper-list extension TODOs)                |
| `scope_aware_exclusions`    | object  | other-repo paths intentionally NOT acted on (cross-repo scope discipline)             |

Other keys MAY appear when an action sub-type requires them (`scan_results`, `recommendation_for_future_session`, etc.); they are advisory and not validated by schema-v1.

---

## §4 action enum

Action values used in production rows of both ledgers. New actions SHOULD prefer extending an existing prefix family rather than inventing a brand-new noun.

### lock-state transitions
- `lock` — initial chflags uchg application across the canonical helper set (lock-ledger row)
- `unlock` — chflags nouchg event (paired with later relock; raw 85 window starts here)
- `relock_after_window_violation` — auto-recovery relock when raw 85 escalation window was exceeded
- `unlock_edit_relock_canonical_helper_extend` — single-row record of an in-window unlock-edit-relock cycle
- `edit_no_unlock_required` — file was already unlocked at edit time; no escalation cycle needed
- `chflags_uchg_<scope>` — apply uchg to a class of files (e.g. `chflags_uchg_5_files_session_integrity_sweep`, `chflags_uchg_session_permanent_ref_doc`, `chflags_uchg_anima_n6_atlas_shard`)
- `chflags_uappnd_cleanup_audit_ledgers` — apply uappnd to ledger files that were missing it at creation

### audit / verification
- `audit_ledger_consistency_check_PASS` — cross-check of every row's `after_flags` claim against actual chflags via `ls -lO`; reports `rows_checked` + `inconsistencies` count
- `cross_repo_absorption_lint_findings_scope_aware` — periodic absorption-lint scan with anima-local PASS verdict and out-of-scope nexus/hive findings noted

### own-field strengthen
- `own4_proof_field_strengthen_with_<...>_LIVE_evidence` — proof line additions to `.own` after L2/L3' canonical evidence lands

### convention
Action names are snake_case. Enum is open-ended but SHOULD be reused; emitting new actions requires updating §4 in this doc within the same commit (raw 91 C2 write_barrier — ledger-state matches docs).

---

## §5 cross-reference: raw 1 / 77 / 85 / 95 interplay

raw 95 (triad-universal-mandate) is the umbrella that requires three independently-enforceable witness layers for every protected mutation. The four raws below are the load-bearing tendons of that mandate as it applies to anima audit ledgers.

### raw 1 — os-lock policy
Kernel-level `chflags uchg` (immutable) and `chflags uappnd` (append-only) are the FIRST witness layer. They make in-place mutation return EPERM at the syscall boundary — no application code can bypass them without an explicit privileged unlock cycle.

- canonical helpers under `tool/*.hexa` carry `uchg`
- audit ledgers under `state/audit/*.jsonl` carry `uappnd`
- session-permanent reference docs carry `uchg`
- read-only result artifacts (verdict.json, sweep .txt) carry `uchg`

### raw 77 — audit ledger append-only
SECOND witness layer: every privileged unlock or chflags action MUST emit a row to the relevant `*.jsonl` audit ledger, recorded at the same logical moment. Because the ledger itself is `uappnd`, rows cannot be retroactively rewritten — the audit trail is forward-only. raw 77 schema-v1 is the format defined in this document (§§1-4).

The `audit_ledger_consistency_check_PASS` action (§4) is the periodic verifier: every row's `after_flags` claim is cross-checked against current FS chflags. A non-zero `inconsistencies` count is a raw 91 C2 write_barrier violation.

### raw 85 — escalation-audit-trail-witness
THIRD witness layer: any unlock event MUST be paired with a relock event within `escalation_window_sec` (default 300s = 5 min). The pairing MUST be witnessable from the audit ledger alone — the row carries `unlock_ts`, `relock_ts`, `unlock_to_relock_window_sec`, and `raw_85_compliance` so a reviewer can verify in-window-ness without external state.

When a window violation is detected (e.g. session integrity sweep finds `.own` left unlocked > 300s), the recovery action is `relock_after_window_violation` (§4) with `window_violation_evidence` populated. This converts the violation itself into an auditable record rather than a silent gap.

### raw 95 — triad-universal-mandate (umbrella)
raw 95 says: protected state changes require all three witnesses (raw 1 kernel chflags + raw 77 ledger append + raw 85 in-window pairing). A change witnessed by only two layers is INCOMPLETE — that's a raw 95 triad gap.

In practice every row in `anima_own_strengthen_audit.jsonl` is the raw 77 leg; the row's `before_flags`/`after_flags` cite the raw 1 leg; the row's `unlock_to_relock_window_sec` cites the raw 85 leg. Together the row is a self-contained raw 95 triad witness.

### supporting raw 91 (honesty triad)
raw 91 C2 (write_barrier) keeps ledger contents matching FS reality. raw 91 C3 (honest evidence) requires actions like LoC counts and audit row counts to be quantified rather than asserted. Action `audit_ledger_consistency_check_PASS` is a raw 91 C2 verifier; the `rows_checked` + `inconsistencies` integers are raw 91 C3 evidence.

---

## appendix: canonical helper list

Helpers currently registered in `state/audit/anima_canonical_helper_lock.jsonl` (raw 1 + raw 77 protected, lock event 2026-04-27T19:49:23Z, helper_count=7):

1. `tool/anima_cmt.hexa`
2. `tool/anima_runpod_orchestrator.hexa`
3. `tool/compute_resource_failure_lint.hexa` (own 4 L2)
4. `tool/discovery_auto_absorption_lint.hexa`
5. `tool/kick_result_ai_native_lint.hexa`
6. `tool/kick_with_trailer_wrapper.hexa`
7. `tool/sigma_tau_alignment_lint.hexa`

Extending the canonical helper list is itself a privileged action: it requires unlock-edit-relock on `tool/anima_canonical_helper_lock.hexa` plus a paired audit ledger row.
