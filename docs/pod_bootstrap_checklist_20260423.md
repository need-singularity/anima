# H100 Pod Bootstrap Checklist (operator runbook)

**Last verified**: 2026-04-23 · pod `mqljodjb5pqpk4` (H100 80GB SXM) reached drill PASS 4/4.
**Source of truth for current binary sha**: `tool/fetch_hexa_binary_url.bash` (EXPECTED_SHA constant).
**Why this exists**: the manifest's `pod_bootstrap_sequence` is a skeleton. This checklist
captures every stumble from I7–I11 in `state/convergence/h100_stage1_20260423.json`
so the next pod relaunch doesn't re-discover them.

---

## 0. Pre-flight (operator machine, before `runpodctl pod create`)

```bash
bin/anima doctor                                # expect 10/10 PASS
bin/anima compute status                        # expect pods=0, stage1=READY
bash tool/fetch_hexa_binary_url.bash --export   # prints HEXA_URL + sha
```

Gate file must exist with literal content `launch go`:
```
memory/feedback_h100_gate.md
```

---

## 1. Launch (pre-authorized by user for this project)

```bash
bin/anima compute start stage1     # runpodctl 1.x kebab-case, JSON env
bin/anima compute pods-sync        # refresh config/h100_pods.json from live pods
bin/anima compute watch --arm      # ARMED auto-kill (idle stop via --apply)
```

Capture `pod_id` from output. Query SSH host/port via GraphQL
(`runpodctl pod get <id>` returns `status=null` for fresh pods — use GraphQL):
```bash
API_KEY=$(grep "^apikey" ~/.runpod/config.toml | sed "s/apikey = '//;s/'//")
curl -s -X POST "https://api.runpod.io/graphql" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"query":"{ pod(input:{podId:\"<POD_ID>\"}){ runtime{ ports{ ip publicPort privatePort type } } } }"}'
```

---

## 2. In-pod bootstrap (ssh, one session)

These steps recover from **I7–I11** in order. Do them all:

```bash
# I7 — clang missing on runpod/pytorch:2.4.0 image (ships gcc only)
apt-get update && apt-get install -y clang

# I6 / I8 — hexa transpiler-only binary + shim that accepts Mac CLI form
HEXA_URL='<operator-side presigned URL from pre-flight>'
curl -fsSL "$HEXA_URL" -o /usr/local/bin/hexa_v2 && chmod +x /usr/local/bin/hexa_v2
echo '<EXPECTED_SHA>  /usr/local/bin/hexa_v2' | sha256sum -c -

# shim wrapper: accepts `hexa <file>` (implicit run, Mac convention) AND `hexa run <file>`
cat > /usr/local/bin/hexa <<'WRAP'
#!/usr/bin/env bash
set -e
if [[ $# -ge 1 && "$1" == *.hexa && -f "$1" ]]; then set -- run "$@"; fi
case "${1:-}" in
  run)  shift; src="$1"; shift
        mkdir -p /tmp/hexa_cache
        h=$(shasum -a 256 "$src" | awk '{print $1}')
        bin="/tmp/hexa_cache/$h"
        if [[ ! -x "$bin" ]]; then
          c="/tmp/hexa_cache/$h.c"
          /usr/local/bin/hexa_v2 "$src" "$c" >/dev/null
          clang -O2 -I /workspace/hexa-lang/self -Wno-trigraphs -fbracket-depth=4096 "$c" -lm -o "$bin"
        fi
        exec "$bin" "$src" "$@" ;;
  build) shift; /usr/local/bin/hexa_v2 "$@" ;;
  *) echo "hexa shim — usage: hexa {run|build} <file.hexa> [...]" >&2; exit 2 ;;
esac
WRAP
chmod +x /usr/local/bin/hexa

# I9 — sister repo linkage ($HOME/core layout expected by drill_ext_resolver)
mkdir -p /root/core
cd /root/core
git clone https://github.com/need-singularity/anima.git
git clone https://github.com/need-singularity/hexa-lang.git
git clone https://github.com/need-singularity/nexus.git      # optional if drill needs criteria
git clone https://github.com/need-singularity/airgenome.git  # optional
ln -sfn /root/core/anima       /workspace/anima
ln -sfn /root/core/hexa-lang   /workspace/hexa-lang

# Check out the same branch as operator machine (not main — feature branch)
cd /root/core/anima && git checkout feat/roadmap-63-multimodal && git pull
```

---

## 3. Smoke test before training kickoff

```bash
cd /root/core/anima
hexa run tool/cert_gate.hexa --selftest           # STEP 4 contract checks pass
hexa run tool/drill_ext_resolve.hexa drill_breakthrough_criteria
  # expect absolute path printed, exit 0
```

---

## 4. Training kickoff (genesis-mode for fresh pod)

```bash
cd /root/core/anima
mkdir -p logs
# I11 — fresh pod has no state/drill_criteria_audit.jsonl; use --all-seeds
nohup hexa run tool/drill_breakthrough_runner.hexa --all-seeds \
  > logs/stage1_train.log 2>&1 &
echo "PID=$!"
```

Expected: `verdict=PASS pass=4/4 cross_match=4/4 fixpoint=3/4`
(3/4 fixpoint is by design — seed_neg_01 expected=absorption; see
`state/convergence/h100_stage1_20260423.json:.convergence.live_artifacts.stage1_drill_breakthrough.fixpoint_3_of_4_is_by_design`).

---

## 5. Sync artifact back to operator machine

```bash
# on operator machine:
scp -P <port> -i ~/.runpod/ssh/RunPod-Key-Go \
  root@<ip>:/root/core/anima/state/alm_r13_drill_breakthrough.json \
  state/alm_r13_drill_breakthrough.json
```

Commit locally under `state/convergence/` if it represents a new attempt.

---

## 6. Shutdown (when drill PASS captured)

```bash
bin/anima compute stop <pod_id>       # delete pod → stop burn
bin/anima compute pods-sync           # clear config/h100_pods.json
```

The `--arm` watcher from §1 will also stop idle pods automatically after
`threshold_minutes` (default 30, see `config/h100_auto_kill_config.json`).

---

## Known upstream-dependent workarounds (do NOT remove until trigger)

| Trigger (hexa-lang commit) | What to delete |
|---|---|
| roadmap 66 Phase C.2 + binary rebuild past 9bdf2336 | `tool/an11_a_verifier.hexa` `_last_idx_char`, `nth_positional` dup-branch |
| roadmap 67 M5 Linux driver shipped | `/usr/local/bin/hexa` shim in §2, replace with upstream driver |
| roadmap 65 Phase 2 callers migrated | `args()[2..]` pattern → `real_args()` sweep |

Sources: `state/convergence/h100_stage1_20260423.json:.convergence.upstream_progress_ref` + `memory/reference_hexa_roadmap_64_69.md`.
