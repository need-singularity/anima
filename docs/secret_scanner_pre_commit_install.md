# secret_scanner pre-commit hook — manual install guide

ROI item **T4** — give the user a one-page recipe to wire
`tool/secret_scanner.hexa` into their local git pre-commit hook so secrets
(AWS keys, HF tokens, private keys, slack/openai/github tokens, generic
high-entropy strings) are caught BEFORE any `git commit` lands.

> **Hard constraint — the agent NEVER runs the install commands below.**
> The agent does not symlink, copy, or modify any file under `.git/hooks/`.
> The user MUST run the steps themselves on their workstation. This is a
> deliberate guardrail: a runaway agent should not be able to disable or
> replace pre-commit gates.

---

## What the hook does

On every `git commit`, the hook will:

1. Identify the staged file list (`git diff --cached --name-only`).
2. Invoke `tool/secret_scanner.hexa --paths <staged...>` (HIGH/CRITICAL
   findings exit with code `2`, MEDIUM-only with `1`, clean with `0`).
3. Block the commit if exit code is `2` (CRITICAL/HIGH).
4. Allow commit (with stderr warning) if exit code is `1` (MEDIUM-only).
5. Allow commit silently if exit code is `0`.

The scanner NEVER logs the full secret value — only the first 4 chars +
length redaction land in `state/secret_scan_violations.json`.

---

## One-time install (USER runs these — agent must NOT)

Pick **option A** (symlink, recommended) or **option B** (script copy).

### Option A — symlink (auto-tracks edits to the hook script)

```bash
# 1. Verify scanner runs cleanly first.
hexa tool/secret_scanner.hexa --selftest

# 2. From the repo root, symlink the canonical hook script into .git/hooks/.
cd /Users/ghost/core/anima
ln -s ../../tool/git_hooks/pre_commit_secret_scanner.bash .git/hooks/pre-commit

# 3. Mark executable.
chmod +x .git/hooks/pre-commit

# 4. Verify.
ls -la .git/hooks/pre-commit
.git/hooks/pre-commit --self-check    # prints scanner version + 'OK'
```

### Option B — copy (no symlink — survives `.git/hooks` resets)

```bash
cd /Users/ghost/core/anima
cp tool/git_hooks/pre_commit_secret_scanner.bash .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

> If `tool/git_hooks/pre_commit_secret_scanner.bash` does not yet exist in
> the repo, paste the canonical hook script (next section) into the file
> first, then re-run the install step. The script is intentionally NOT
> auto-created by the agent — adding it requires an explicit user-driven
> commit.

---

## Canonical hook script (paste into `tool/git_hooks/pre_commit_secret_scanner.bash`)

```bash
#!/usr/bin/env bash
# Pre-commit hook — runs tool/secret_scanner.hexa over staged files.
# Exit 0 → allow commit · Exit non-zero → block commit.
set -u

REPO_ROOT="$(git rev-parse --show-toplevel)"
HEXA_BIN="${HEXA_BIN:-/Users/ghost/Dev/hexa-lang/hexa}"
SCANNER="$REPO_ROOT/tool/secret_scanner.hexa"

# Self-check escape hatch.
if [[ "${1:-}" == "--self-check" ]]; then
  "$HEXA_BIN" "$SCANNER" --selftest >/dev/null && echo "OK" || echo "FAIL"
  exit $?
fi

# Collect staged files (added/copied/modified — skip deletions).
mapfile -t STAGED < <(git diff --cached --name-only --diff-filter=ACM)
[[ "${#STAGED[@]}" -eq 0 ]] && exit 0

# Scanner expects --paths followed by space-separated list.
"$HEXA_BIN" "$SCANNER" --paths "${STAGED[@]}"
RC=$?

case "$RC" in
  0) exit 0 ;;
  1) echo "[secret_scanner] MEDIUM finding(s) — commit allowed but please review state/secret_scan_violations.json" >&2; exit 0 ;;
  2) echo "[secret_scanner] HIGH/CRITICAL finding(s) — commit BLOCKED. See state/secret_scan_violations.json" >&2; exit 1 ;;
  *) echo "[secret_scanner] scanner setup error (rc=$RC) — commit BLOCKED out of caution" >&2; exit 1 ;;
esac
```

---

## Uninstall (USER runs these — agent must NOT)

```bash
rm /Users/ghost/core/anima/.git/hooks/pre-commit
```

---

## Bypassing the hook (emergency only)

If the user needs to commit a confirmed false-positive, bypass via:

```bash
git commit --no-verify ...
```

> The agent is explicitly forbidden from using `--no-verify` unless the user
> grants per-commit permission. See top-of-prompt git safety rules.

---

## Audit / verification

- Scanner SSOT: `state/secret_scan_violations.json`
- Append-only history: `state/secret_scan_log.jsonl`
- Run baseline scan: `hexa tool/secret_scanner.hexa`
- Run selftest: `hexa tool/secret_scanner.hexa --selftest`

---

## Why the agent never auto-installs

1. **Trust boundary** — `.git/hooks/` is the user's last enforcement layer.
   An agent that can write hooks can also disable them.
2. **Reversibility** — every step above is a single `rm` away from clean
   removal; auto-install creates ambiguity about who "owns" the hook.
3. **Explicit consent** — pre-commit hooks change the developer's commit
   latency and may block emergency commits. That is a UX choice the human
   must opt into.

If the user wants the hook installed, they paste the install commands
themselves. The agent's job ends at producing this guide.
