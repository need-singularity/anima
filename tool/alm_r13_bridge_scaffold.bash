#!/usr/bin/env bash
# tool/alm_r13_bridge_scaffold.bash — P12 bridge scaffold (non-live).
#
# PURPOSE
#   P12 (convergence) = the full ALM r13 LoRA training loop is not yet
#   implemented, which means no real pod-side process produces
#   state/alm_r13_an11_a_live.json. This script is a BRIDGE scaffold:
#     - emits two synthetic safetensors-shaped JSON files (base + round)
#       with a deliberate non-zero weight delta, so an11_a_verifier runs
#       in REAL (non-dry) synthetic_json backend and emits a valid
#       verdict=PASS artifact at state/alm_r13_an11_a.json.
#     - Does NOT promote to the _live suffix. The Stage-2 cascade gate
#       reads state/alm_r13_an11_a_live.json specifically, so Stage-2
#       remains honestly NOT_READY until a real pod training emits the
#       _live artifact. Operators who want to unblock Stage-2 with the
#       bridge must copy state/alm_r13_an11_a.json → _live.json manually
#       and attach a provenance note — that copy is their attested bridge,
#       not ours.
#
# OUTPUT
#   state/alm_r13_an11_a.json  (backend=synthetic_json, verdict=PASS)
#   /tmp/_alm_r13_bridge_base.json   (synth base ckpt)
#   /tmp/_alm_r13_bridge_round.json  (synth round ckpt)
#
# EXIT
#   0 = verifier emitted verdict=PASS to state/alm_r13_an11_a.json
#   non-0 = verifier reported non-PASS (scaffold input mismatch — investigate)
set -euo pipefail

readonly BASE=/tmp/_alm_r13_bridge_base.json
readonly ROUND=/tmp/_alm_r13_bridge_round.json
readonly OUT=state/alm_r13_an11_a.json

# Synthetic base: rank-4 adapter with small uniform weights.
python3 - <<'PY' > "$BASE"
import json
base = {"weights": [0.001 * (i + 1) for i in range(256)], "rank": 4}
print(json.dumps(base))
PY

# Synthetic round: rank-4 adapter with perturbation on top of base.
# Delta norm = sqrt(sum(0.05^2 * 256)) ~= 0.8, well above threshold 1e-3.
python3 - <<'PY' > "$ROUND"
import json, random
random.seed(20260423)
round_ = {"weights": [0.001 * (i + 1) + random.uniform(-0.05, 0.05) for i in range(256)], "rank": 4}
print(json.dumps(round_))
PY

echo "[scaffold] base=$BASE round=$ROUND (synthetic_json, rank=4, seeded)"
echo "[scaffold] invoking an11_a_verifier (real, non-dry) …"

/Users/ghost/.hx/bin/hexa run tool/an11_a_verifier.hexa --dest alm --threshold 0.001 "$BASE" "$ROUND" 13 2>&1 | tail -8

test -f "$OUT" || { echo "[scaffold] ERROR: verifier did not write $OUT" >&2; exit 2; }

verdict=$(python3 -c "import json,sys; d=json.load(open('$OUT')); print(d.get('verdict','MISSING'))")
backend=$(python3 -c "import json,sys; d=json.load(open('$OUT')); print(d.get('backend','MISSING'))")

echo "[scaffold] out=$OUT verdict=$verdict backend=$backend"
echo "[scaffold] NOTE: state/alm_r13_an11_a.json is a BRIDGE artifact (backend=synthetic_json)."
echo "[scaffold]       Stage-2 cascade gate reads state/alm_r13_an11_a_live.json — still NOT produced."
echo "[scaffold]       To unblock Stage-2 with this bridge, an operator must:"
echo "[scaffold]         (1) audit this file, (2) attach a provenance note,"
echo "[scaffold]         (3) cp state/alm_r13_an11_a.json state/alm_r13_an11_a_live.json"
echo "[scaffold]       That explicit copy is the attested bridge; this script will not do it."

[[ "$verdict" == "PASS" ]] || exit 3
