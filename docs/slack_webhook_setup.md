# Slack Webhook Setup Guide — pre-H100 ROI P2

Purpose: provide the **one-time** operator setup procedure for the
`SLACK_WEBHOOK_URL` env var consumed by `tool/auto_evolution_loop.hexa`
step 8 (notify) and `tool/slack_notify_launch_verdict.hexa`.

Cross-refs:
- `tool/auto_evolution_loop.hexa` — step 8 invokes webhook when env set
- `tool/slack_notify_launch_verdict.hexa` — verdict notifier (dry-default)
- `tool/slack_webhook_test.hexa` — round-trip smoke test (NEW, --dry default)
- `docs/h100_launch_dashboard_setup.md` — references same env var for Grafana alerts

This is **operator setup only** — agent never creates webhooks, never stores
the URL, and never enables the launchd notify path automatically.

---

## 1. Create the Slack incoming webhook

1. Open Slack workspace → Apps → search "Incoming Webhooks" → Add to Slack.
2. Choose channel (recommended: `#anima-h100-launch` or `#anima-ops`).
3. Slack returns a URL of the form `https://hooks.slack.com/services/<TEAM>/<CHANNEL>/<TOKEN>` — three opaque segments after `/services/`.
4. Copy URL. **Do NOT commit it.** It is a bearer credential.

## 2. Store in operator shell rc (NOT in repo)

Append to `~/.zshrc` (or `~/.bashrc`):

```bash
# anima Slack notify (pre-H100 ROI P2)
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T.../B.../..."
```

Reload:

```bash
source ~/.zshrc
echo "set=${#SLACK_WEBHOOK_URL}"   # should print a length, NOT the URL
```

For the launchd notify path (step §4), also add to plist `EnvironmentVariables`
(see §4 below — operator does this only after explicit go).

## 3. Smoke test (dry-default — safe, no actual POST)

```bash
hexa run tool/slack_webhook_test.hexa             # dry — prints what would POST
hexa run tool/slack_webhook_test.hexa --self-test # offline self-test (no env required)
```

Real round-trip (operator-go only, requires env set):

```bash
hexa run tool/slack_webhook_test.hexa --apply
# expect: "POST 200 OK" and a test message in the chosen Slack channel
```

If the test message arrives, the env var is correctly wired.

## 4. Activate auto_evolution_loop notify (operator opt-in only)

`tool/auto_evolution_loop.hexa` step 8 already reads `SLACK_WEBHOOK_URL`
from env and gracefully skips when unset (existing behavior — see lines 289-307
of that file). To activate:

1. Add env var to the launchd plist `EnvironmentVariables` block:
   ```xml
   <key>EnvironmentVariables</key>
   <dict>
       <key>PATH</key>
       <string>/Users/ghost/.hx/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
       <key>SLACK_WEBHOOK_URL</key>
       <string>https://hooks.slack.com/services/T.../B.../...</string>
   </dict>
   ```
   (Edit `config/launchd/com.anima.auto_evolution.plist` — but DO NOT commit
   the file with the real URL. Use `git update-index --assume-unchanged` if
   you want to keep the local copy private.)

2. Verify dry-run picks it up:
   ```bash
   SLACK_WEBHOOK_URL="..." hexa run tool/auto_evolution_loop.hexa
   # step 8 line should show: "would POST to slack (url len=NN)"
   ```

3. Full apply (cycle once with notify active):
   ```bash
   SLACK_WEBHOOK_URL="..." hexa run tool/auto_evolution_loop.hexa --apply
   ```

4. Activate launchd timer (operator-go only, NOT auto-activated):
   ```bash
   bash tool/launchd_install_local.bash --activate
   ```

## 5. Per-tool notify paths (current inventory)

| tool | env consumed | default | activation |
|---|---|---|---|
| `tool/auto_evolution_loop.hexa` | `SLACK_WEBHOOK_URL` | dry (skip if unset) | --apply + env set |
| `tool/slack_notify_launch_verdict.hexa` | `SLACK_WEBHOOK_URL` | dry | --apply + env set |
| `tool/slack_webhook_test.hexa` (NEW) | `SLACK_WEBHOOK_URL` | dry | --apply + env set |
| Grafana alertmanager (htz) | `SLACK_WEBHOOK_URL` (in `.env.preboot`) | EXPECTED empty pre-boot | filled in at #83 kickoff |

## 6. Payload format (canonical)

All anima notify tools emit a **single Slack-compatible JSON object** of the form:

```json
{ "text": "*anima <subject>* <emoji>\n• key: `value`\n• ..." }
```

`*bold*` and `_italic_` are honored by Slack mrkdwn. Backtick-wrapped values
render as inline code. Multi-line via `\n`. No attachments / blocks (kept
deliberately minimal — avoids breaking when webhook routes via Mattermost
or compatible drop-in receivers).

## 7. Rotation / revocation

If the webhook leaks:

1. Slack workspace admin → Apps → Incoming Webhooks → revoke the offending one.
2. Remove the URL from `~/.zshrc` and any plists.
3. Repeat §1 to mint a fresh URL.
4. Re-run §3 smoke to verify.

## 8. Failure modes (graceful)

- `SLACK_WEBHOOK_URL` unset → all tools skip notify, log `SKIP no env`.
- Webhook 404 / 410 → Slack revoked it → log error, continue cycle.
- Network down → curl times out (5 s default) → log timeout, continue.

None of the above ever fail the parent cycle (auto_evolution, launch verdict,
etc). Notify is best-effort by design.

---

Authored: 2026-04-22 — pre-H100 ROI P2.
Status: SPEC ONLY — no webhook minted by agent. Operator self-serve.
