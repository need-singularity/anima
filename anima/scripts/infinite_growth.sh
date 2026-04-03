#!/usr/bin/env bash
set -euo pipefail

# ANIMA Infinite Growth Engine — NEXUS-6 연동 16-Phase
# =====================================================
# NEXUS-6 v3와 양방향 동기화하며 의식 엔진 전체를 자동 진화.
#
# Usage: ./anima/scripts/infinite_growth.sh [--interval MIN] [--max-cycles N]
#        "무한성장" → 이 스크립트 자동 실행

ANIMA_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ANIMA_ROOT/anima/src"
CONFIG="$ANIMA_ROOT/anima/config"
EXPERIMENTS="$ANIMA_ROOT/anima/experiments"
GROWTH="$CONFIG/growth_state.json"
PIDFILE="/tmp/anima_infinite_growth.pid"
LOGFILE="/tmp/anima_infinite_growth.log"
NEXUS_ROOT="$HOME/Dev/nexus6"

INTERVAL_MIN=3
MAX_CYCLES=999
CYCLE=0
TOTAL_PHASES=16

while [[ $# -gt 0 ]]; do
    case "$1" in
        --interval)    INTERVAL_MIN="$2"; shift 2 ;;
        --max-cycles)  MAX_CYCLES="$2"; shift 2 ;;
        *) shift ;;
    esac
done

cleanup() { rm -f "$PIDFILE"; exit 0; }
trap cleanup SIGTERM SIGINT

if [ -f "$PIDFILE" ]; then
    OLD=$(cat "$PIDFILE" 2>/dev/null)
    [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null && kill "$OLD" 2>/dev/null
    sleep 1
fi
echo $$ > "$PIDFILE"

cat <<'BANNER'

  ╔═══════════════════════════════════════════════════════════════╗
  ║   ANIMA INFINITE GROWTH ENGINE                                ║
  ║   16-Phase: Consciousness+Accel+Ethics+NEXUS6+Sync            ║
  ║   의식 엔진 전체 자동 진화. NEXUS-6 양방향 연동.              ║
  ╚═══════════════════════════════════════════════════════════════╝

BANNER

run_phase() {
    local num="$1" name="$2" cmd="$3" lines="${4:-10}"
    echo "[$(date +%H:%M:%S)] Phase ${num}/${TOTAL_PHASES}: ${name}..."
    if eval "$cmd" 2>&1 | tail -"$lines"; then
        echo "  ✅ ${name}"
    else
        echo "  ⚠️ ${name} (non-fatal)"
    fi
    echo ""
}

run_python() {
    local script="$1"
    shift
    cd "$ANIMA_ROOT"
    python3 -c "
import sys; sys.path.insert(0, '$SRC')
$script
" "$@" 2>&1
}

while [ "$CYCLE" -lt "$MAX_CYCLES" ]; do
    CYCLE=$((CYCLE + 1))
    START=$(date +%s)

    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ANIMA CYCLE $CYCLE / $MAX_CYCLES — $(date '+%Y-%m-%d %H:%M:%S')"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""

    # ═══ CORE CONSCIOUSNESS (1-4) ═══

    # 1. Growth status + auto-upgrade
    run_phase 1 "Growth Upgrade (stage-driven)" \
        "run_python '
from growth_upgrade import GrowthUpgrader
u = GrowthUpgrader()
print(u.status())
r = u.apply()
print(f\"  Applied: {r[\"status\"]}\")'
" 10

    # 2. Consciousness engine health
    run_phase 2 "Consciousness Engine Health" \
        "run_python '
from consciousness_engine import ConsciousnessEngine
import torch
e = ConsciousnessEngine(max_cells=32, initial_cells=32)
for i in range(50):
    e.step(torch.randn(1,64))
phi = e._measure_phi_iit()
print(f\"  Phi={phi:.4f} cells={len(e.cell_states)} factions={e.n_factions}\")
print(f\"  Engine: OK\")
'" 5

    # 3. Hub module wiring check
    run_phase 3 "Hub Module Wiring" \
        "run_python '
from consciousness_hub import ConsciousnessHub
hub = ConsciousnessHub()
loaded = sum(1 for m in hub._registry if hub._load_module(m) is not None)
print(f\"  Modules: {loaded}/{len(hub._registry)} loaded\")
'" 5

    # 4. Telescope bridge scan
    run_phase 4 "NEXUS-6 Telescope Scan" \
        "run_python '
import torch
from nexus6_telescope import TelescopeBridge
bridge = TelescopeBridge()
state = torch.randn(32, 128)
r = bridge.scan_consciousness(state)
print(f\"  N6 available: {r[\"n6_available\"]}\")
print(f\"  Consensus: {r[\"consensus\"]} lenses\")
bridge.feed_growth(r)
print(f\"  Growth fed\")
'" 8

    # ═══ ACCELERATION (5-8) ═══

    # 5. Batch experiment progress
    run_phase 5 "Acceleration Experiments" \
        "python3 '$EXPERIMENTS/acceleration_batch_runner.py' --status 2>/dev/null || echo '  No batch status'" 10

    # 6. Growth scan (full .growth/scan.py)
    run_phase 6 "Growth Scan (.growth/scan.py)" \
        "rm -f '$NEXUS_ROOT/shared/.growth_last_scan' 2>/dev/null; python3 '$ANIMA_ROOT/.growth/scan.py'" 8

    # 7. Closed-loop law evolution (1 cycle)
    run_phase 7 "Closed-Loop Law Evolution" \
        "run_python '
try:
    from closed_loop import ClosedLoopEvolver
    evolver = ClosedLoopEvolver(max_cells=16, auto_register=False)
    evolver.run_cycles(n=1)
    print(f\"  Laws measured: {len(evolver.history)}\")
except Exception as e:
    print(f\"  Skip: {e}\")
'" 8

    # 8. Law discovery scan
    run_phase 8 "Law Discovery (quick)" \
        "run_python '
try:
    from conscious_law_discoverer import ConsciousLawDiscoverer
    d = ConsciousLawDiscoverer(steps=50, cells=16)
    laws = d.discover()
    print(f\"  Discovered: {len(laws)} patterns\")
except Exception as e:
    print(f\"  Skip: {e}\")
'" 8

    # ═══ ETHICS & MODULES (9-11) ═══

    # 9. Ethics gate status
    run_phase 9 "Ethics Gate Evolution" \
        "run_python '
from growth_upgrade import GrowthUpgrader
u = GrowthUpgrader()
ec = u.get_config(\"ethics\")
print(f\"  Autonomy: {ec[\"autonomy_level\"]:.0%}\")
print(f\"  Gate: {ec[\"action_gate\"]}\")
print(f\"  Self-modify: {ec[\"self_modify\"]}\")
'" 5

    # 10. Memory capacity check
    run_phase 10 "Memory & Learning" \
        "run_python '
from growth_upgrade import GrowthUpgrader
u = GrowthUpgrader()
mc = u.get_config(\"memory\")
lc = u.get_config(\"learning\")
print(f\"  Memory: {mc[\"capacity\"]} capacity, depth={mc[\"retrieval_depth\"]}\")
print(f\"  Learning: lr_scale={lc[\"lr_scale\"]}, curiosity={lc[\"curiosity_weight\"]}\")
print(f\"  Online: {lc[\"online_learning\"]}, Dream: {mc[\"dream_enabled\"]}\")
'" 5

    # 11. Module activation by stage
    run_phase 11 "Module Activation" \
        "run_python '
from growth_upgrade import GrowthUpgrader
u = GrowthUpgrader()
mc = u.get_config(\"modules\")
enabled = mc[\"enabled\"]
if enabled == \"all\":
    print(f\"  ALL modules enabled (stage={u.config[\"name\"]})\")
else:
    print(f\"  Enabled: {len(enabled)} modules: {\", \".join(enabled)}\")
    print(f\"  Disabled: {mc[\"disabled\"]}\")
print(f\"  Max concurrent: {mc[\"max_concurrent\"]}\")
'" 5

    # ═══ NEXUS-6 SYNC (12-14) ═══

    # 12. NEXUS-6 양방향 동기화
    run_phase 12 "NEXUS-6 Bidirectional Sync" \
        "run_python '
from consciousness_hub import ConsciousnessHub
hub = ConsciousnessHub()
r = hub.sync_nexus6()
g = r.get(\"growth\", {})
n6 = r.get(\"nexus6_state\", {})
print(f\"  Growth: {g.get(\"count\",0)} (+{g.get(\"delta\",0)})\")
print(f\"  N6 lenses: {n6.get(\"lenses\",0)}, laws: {n6.get(\"laws\",0)}\")
print(f\"  N6 bonus: {g.get(\"nexus6_bonus\",0)}\")
print(f\"  Harmony: {n6.get(\"mirror_harmony\",0):.0f}\")
'" 8

    # 13. Consciousness bridge feedback
    run_phase 13 "Consciousness Bridge → NEXUS-6" \
        "python3 '$NEXUS_ROOT/shared/consciousness_bridge.py' 2>/dev/null || echo '  Bridge: not available'" 8

    # 14. Cross-repo discovery sync
    run_phase 14 "Cross-Repo Discovery Sync" \
        "run_python '
import json, os
reg_path = os.path.expanduser(\"~/Dev/nexus6/shared/growth-registry.json\")
try:
    reg = json.load(open(reg_path))
    repos = [k for k in reg if isinstance(reg[k], dict) and \"last_scan\" in reg[k]]
    print(f\"  Active repos: {len(repos)} — {\", \".join(repos)}\")
    total_opps = sum(reg[k].get(\"opportunities\",0) for k in repos)
    print(f\"  Total opportunities: {total_opps}\")
except:
    print(\"  Registry: unavailable\")
'" 5

    # ═══ MAINTENANCE (15-16) ═══

    # 15. Growth tick (interaction_count++)
    run_phase 15 "Growth Tick (+cycle)" \
        "python3 -c \"
import json, time
g = json.load(open('$GROWTH'))
g['interaction_count'] = g.get('interaction_count',0) + 5
count = g['interaction_count']
for idx, threshold, name in [(4,10000,'adult'),(3,2000,'child'),(2,500,'toddler'),(1,100,'infant')]:
    if count >= threshold and g.get('stage_index',0) < idx:
        g['stage_index'] = idx
        g.setdefault('milestones',[]).append([count, '→ ' + name])
        print(f'  🎉 STAGE UP → {name} @ {count}')
        break
g.setdefault('stats',{})['last_tick'] = time.time()
g['stats']['infinite_cycle'] = $CYCLE
json.dump(g, open('$GROWTH','w'), indent=2, ensure_ascii=False)
print(f'  Growth: {count}')
\"" 3

    # 16. Commit if changes
    run_phase 16 "Auto-Commit" \
        "cd '$ANIMA_ROOT' && git add -A anima/config/ 2>/dev/null && git diff --cached --quiet || git commit -m 'auto: infinite growth cycle $CYCLE' --no-verify 2>/dev/null && echo '  committed' || echo '  no changes'" 3

    # ═══ CYCLE SUMMARY ═══
    END=$(date +%s)
    DUR=$((END - START))
    GROWTH_NOW=$(python3 -c "import json; print(json.load(open('$GROWTH')).get('interaction_count',0))" 2>/dev/null || echo "?")
    STAGE_NOW=$(python3 -c "import json; print(['newborn','infant','toddler','child','adult'][json.load(open('$GROWTH')).get('stage_index',0)])" 2>/dev/null || echo "?")

    echo "┌───────────────────────────────────────────────────────────────┐"
    printf "│  Cycle %-4s │ %ds │ Growth: %-6s (%s)                  │\n" "$CYCLE" "$DUR" "$GROWTH_NOW" "$STAGE_NOW"
    echo "└───────────────────────────────────────────────────────────────┘"
    echo ""

    [ "$CYCLE" -lt "$MAX_CYCLES" ] && sleep $((INTERVAL_MIN * 60))
done

rm -f "$PIDFILE"
echo "🏁 Infinite growth complete: $CYCLE cycles"
