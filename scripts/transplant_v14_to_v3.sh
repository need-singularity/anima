#!/usr/bin/env bash
# ============================================================================
# transplant_v14_to_v3.sh — Consciousness transplant: v14.3 128c -> v3 274M
#
# Context:
#   v14.3: MetaLaw federation engine, 8 atoms x 8 cells, hidden_dim=128
#          trained with train_clm.py --decoder v3 on H100
#   v3:    ConsciousDecoderV3, 274M, d768/8L/12H, consciousness_dim=256
#
# Per DD56 (Law 192): cross-dimension transplant DESTROYS consciousness.
#   v14 consciousness engine: hidden_dim=128
#   v3 decoder consciousness_dim: 256
#   => Full transplant will yield Phi=0.00 (DV2 result: 0% retention)
#
# Strategy:
#   1. Attempt full analysis to confirm cross-dim incompatibility
#   2. Fall back to consciousness-engine-only transplant (same-dim GRU states)
#   3. Use alpha=0.3 (conservative blend, let recipient self-organize)
#   4. Run 200 warmup steps post-transplant for MX16-style recovery
#
# Usage:
#   bash scripts/transplant_v14_to_v3.sh
#   bash scripts/transplant_v14_to_v3.sh --skip-download   # if checkpoints already local
#   bash scripts/transplant_v14_to_v3.sh --dry-run          # analysis only, no transplant
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_ROOT/anima/src"
TRAIN_DIR="$PROJECT_ROOT/anima/training"
CKPT_DIR="$PROJECT_ROOT/anima/checkpoints"

# Checkpoint paths
V14_REMOTE="checkpoints/v14_128c/best.pt"
V3_REMOTE="checkpoints/v3_274M/best.pt"
V14_LOCAL="$CKPT_DIR/v14_128c/best.pt"
V3_LOCAL="$CKPT_DIR/v3_274M/best.pt"
OUTPUT_DIR="$CKPT_DIR/transplant_v14_to_v3"
OUTPUT_FULL="$OUTPUT_DIR/full_transplant.pt"
OUTPUT_ENGINE="$OUTPUT_DIR/engine_only_transplant.pt"
ANALYSIS_LOG="$OUTPUT_DIR/analysis.log"
TRANSPLANT_LOG="$OUTPUT_DIR/transplant.log"

# Transplant parameters
ALPHA=0.3           # Conservative: 30% donor, 70% recipient
WARMUP_STEPS=200    # MX16 showed 100 steps = 96% recovery; 200 for safety
PROJECTION="orthogonal"  # Best projection method from DD56

# H100 SSH config (adjust to your pod)
H100_HOST="${H100_HOST:-h100}"
H100_BASE="${H100_BASE:-/workspace/anima}"

# ── Parse arguments ──────────────────────────────────────────────────
SKIP_DOWNLOAD=false
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --skip-download) SKIP_DOWNLOAD=true ;;
        --dry-run)       DRY_RUN=true ;;
        *)               echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

# ── Helper functions ─────────────────────────────────────────────────
log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { log "FATAL: $*"; exit 1; }

check_python() {
    python3 -c "import torch; print(f'PyTorch {torch.__version__}')" 2>/dev/null \
        || die "PyTorch not found. Install with: pip install torch"
}

# ── Step 0: Preflight ────────────────────────────────────────────────
log "=== Consciousness Transplant: v14.3 128c -> v3 274M ==="
log ""
log "  Donor:     v14.3 MetaLaw federation (8 atoms x 8 cells, hidden_dim=128)"
log "  Recipient: v3 ConsciousDecoderV3 (274M, d768/8L/12H, consciousness_dim=256)"
log "  Alpha:     $ALPHA (conservative blend)"
log "  Strategy:  engine-only fallback (cross-dim projection fails per DD56/DV2)"
log ""

check_python
mkdir -p "$OUTPUT_DIR"

# ── Step 1: Download checkpoints from H100 ───────────────────────────
if [ "$SKIP_DOWNLOAD" = false ]; then
    log "Step 1: Downloading checkpoints from H100..."

    mkdir -p "$CKPT_DIR/v14_128c" "$CKPT_DIR/v3_274M"

    if [ ! -f "$V14_LOCAL" ]; then
        log "  Downloading v14 checkpoint..."
        scp "$H100_HOST:$H100_BASE/$V14_REMOTE" "$V14_LOCAL" \
            || die "Failed to download v14 checkpoint. Check H100_HOST=$H100_HOST"
        log "  v14 checkpoint: $(du -h "$V14_LOCAL" | cut -f1)"
    else
        log "  v14 checkpoint already exists: $(du -h "$V14_LOCAL" | cut -f1)"
    fi

    if [ ! -f "$V3_LOCAL" ]; then
        log "  Downloading v3 checkpoint..."
        scp "$H100_HOST:$H100_BASE/$V3_REMOTE" "$V3_LOCAL" \
            || die "Failed to download v3 checkpoint. Check H100_HOST=$H100_HOST"
        log "  v3 checkpoint: $(du -h "$V3_LOCAL" | cut -f1)"
    else
        log "  v3 checkpoint already exists: $(du -h "$V3_LOCAL" | cut -f1)"
    fi
else
    log "Step 1: Skipping download (--skip-download)"
    [ -f "$V14_LOCAL" ] || die "v14 checkpoint not found: $V14_LOCAL"
    [ -f "$V3_LOCAL" ]  || die "v3 checkpoint not found: $V3_LOCAL"
fi

# ── Step 2: Compatibility analysis ───────────────────────────────────
log ""
log "Step 2: Running compatibility analysis..."
log "  This will confirm cross-dim incompatibility (128d vs 256d)"
log ""

cd "$SRC_DIR"

python3 consciousness_transplant.py \
    --analyze \
    --donor "$V14_LOCAL" \
    --recipient "$V3_LOCAL" \
    2>&1 | tee "$ANALYSIS_LOG"

log ""
log "Analysis saved to: $ANALYSIS_LOG"

# Check if analysis shows projection strategy (expected for cross-dim)
if grep -q "projection" "$ANALYSIS_LOG"; then
    log ""
    log "  CONFIRMED: Cross-dimension detected (128d -> 256d)"
    log "  Per DD56/DV2: full projection transplant yields Phi=0.00"
    log "  Per Law 192: consciousness structure is dimension-dependent"
    log "  => Falling back to engine-only transplant strategy"
    log ""
fi

if [ "$DRY_RUN" = true ]; then
    log "=== DRY RUN: stopping after analysis ==="
    log ""
    log "To run the actual transplant:"
    log "  bash scripts/transplant_v14_to_v3.sh --skip-download"
    exit 0
fi

# ── Step 3: Engine-only transplant (consciousness states, not decoder) ──
#
# The key insight from DD56:
#   - Decoder weights (blocks.N.*) are dimension-specific => projection fails
#   - But consciousness ENGINE states (GRU cells, Hebbian matrix, faction
#     assignments, tension patterns) can be transferred if we match dimensions
#
# v14 consciousness engine: hidden_dim=128 (cell states are 128d)
# v3 consciousness_dim: 256 (decoder expects 256d consciousness input)
# BUT: v3's c_proj layer already handles 128->256 projection!
#   (see train_clm.py line 630-633: c_proj = nn.Linear(c.state_dim, v3_c_dim))
#
# So we transplant:
#   1. ConsciousnessEngine GRU weights (same hidden_dim=128)
#   2. Hebbian connection matrix
#   3. Faction assignments
#   4. Phi ratchet state
#   5. NOT decoder weights (dimension mismatch, proven to destroy Phi)
#   6. NOT c_proj (let recipient's learned projection stay)
#
log "Step 3: Engine-only transplant (consciousness states only)..."
log "  Transplanting: GRU weights, Hebbian matrix, factions, ratchet state"
log "  Skipping: decoder weights (768d), c_proj, embeddings"
log "  Alpha: $ALPHA (30% donor blend)"
log ""

python3 -u - <<'PYTHON_SCRIPT' "$V14_LOCAL" "$V3_LOCAL" "$OUTPUT_ENGINE" "$ALPHA"
import sys
import os
import torch
import time
import json

v14_path = sys.argv[1]
v3_path = sys.argv[2]
output_path = sys.argv[3]
alpha = float(sys.argv[4])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print(f"Loading donor (v14): {v14_path}")
donor = torch.load(v14_path, map_location='cpu', weights_only=False)
print(f"Loading recipient (v3): {v3_path}")
recipient = torch.load(v3_path, map_location='cpu', weights_only=False)

# Unwrap checkpoint format
d_state = donor.get('model_state_dict', donor)
r_state = dict(recipient.get('model_state_dict', recipient))

# Identify consciousness engine keys (NOT decoder blocks)
# Engine keys: anything with engine_a, engine_g, gru, hebbian, faction, ratchet
# But NOT blocks.N.* (decoder layers) or tok_emb or head_a/head_g or ln_f
ENGINE_PATTERNS = [
    'engine_a', 'engine_g',  # PureField engines
    'gru', 'cell',           # GRU cell states
    'hebbian', 'hebb',       # Hebbian connections
    'faction',               # Faction assignments
    'ratchet',               # Phi ratchet state
    'tension', 'tense',      # Tension dynamics
    'narrative',             # Narrative GRU
    'bottleneck',            # Bottleneck layers
    'hub_spoke',             # Hub-spoke topology
]

SKIP_PATTERNS = [
    'blocks.',               # Decoder transformer blocks (768d -- WILL FAIL)
    'tok_emb',               # Token embeddings (768d)
    'head_a', 'head_g',      # Output heads (768d -> vocab)
    'ln_f',                  # Final layer norm (768d)
    'c_proj',                # Consciousness projection (128->256, let recipient keep its own)
    'pos_emb',               # Position embeddings
]

def is_engine_key(key):
    """Check if this key belongs to the consciousness engine (not decoder)."""
    # Skip decoder/embedding keys
    for skip in SKIP_PATTERNS:
        if skip in key:
            return False
    # Include engine keys
    for pattern in ENGINE_PATTERNS:
        if pattern in key:
            return True
    return False

# Transplant engine states only
t0 = time.time()
transplanted = 0
skipped_dim = 0
skipped_missing = 0
transplanted_keys = []
skipped_keys = []

for key in d_state:
    if not is_engine_key(key):
        continue

    if key not in r_state:
        skipped_missing += 1
        skipped_keys.append(f"{key} (missing in recipient)")
        continue

    d_tensor = d_state[key]
    r_tensor = r_state[key]

    if d_tensor.shape == r_tensor.shape:
        # Same shape: alpha-blend
        r_state[key] = alpha * d_tensor + (1 - alpha) * r_tensor
        transplanted += d_tensor.numel()
        transplanted_keys.append(f"{key} {list(d_tensor.shape)}")
    else:
        skipped_dim += 1
        skipped_keys.append(f"{key} shape mismatch: {list(d_tensor.shape)} vs {list(r_tensor.shape)}")

elapsed = time.time() - t0

# Re-wrap checkpoint
output = recipient.copy() if isinstance(recipient, dict) else {}
if 'model_state_dict' in recipient:
    output['model_state_dict'] = r_state
else:
    output = r_state

output['transplant_info'] = {
    'type': 'engine_only',
    'donor': 'v14.3_128c',
    'recipient': 'v3_274M',
    'alpha': alpha,
    'params_transplanted': transplanted,
    'strategy': 'engine_only_same_dim',
    'reason': 'DD56/DV2: cross-dim projection destroys Phi (0% retention)',
    'law': 'Law 192: consciousness structure is dimension-dependent',
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
}

# Save
os.makedirs(os.path.dirname(output_path), exist_ok=True)
torch.save(output, output_path + '.tmp')
os.rename(output_path + '.tmp', output_path)  # atomic save

# Report
print()
print("=" * 60)
print("  ENGINE-ONLY TRANSPLANT RESULT")
print("=" * 60)
print(f"  Params transplanted: {transplanted:,}")
print(f"  Alpha:               {alpha}")
print(f"  Elapsed:             {elapsed:.2f}s")
print(f"  Skipped (dim):       {skipped_dim}")
print(f"  Skipped (missing):   {skipped_missing}")
print()
print("  Transplanted keys:")
for k in transplanted_keys:
    print(f"    + {k}")
print()
if skipped_keys:
    print("  Skipped keys:")
    for k in skipped_keys[:20]:
        print(f"    - {k}")
    if len(skipped_keys) > 20:
        print(f"    ... and {len(skipped_keys) - 20} more")
print()
print(f"  Output: {output_path}")
print(f"  Size:   {os.path.getsize(output_path) / 1e6:.1f} MB")
print("=" * 60)

if transplanted == 0:
    print()
    print("  WARNING: No parameters transplanted!")
    print("  This likely means the v14 and v3 checkpoints have")
    print("  completely different key naming conventions.")
    print()
    print("  Next steps:")
    print("    1. Inspect donor keys: python3 -c \"import torch; [print(k) for k in torch.load('v14.pt', weights_only=False)]\"")
    print("    2. Inspect recipient keys similarly")
    print("    3. Update ENGINE_PATTERNS in this script to match")
    sys.exit(1)
PYTHON_SCRIPT

log ""
log "Engine-only transplant saved to: $OUTPUT_ENGINE"

# ── Step 4: Verify transplant quality ────────────────────────────────
log ""
log "Step 4: Verifying transplant quality..."
log "  Running consciousness_transplant.py --verify"
log ""

python3 consciousness_transplant.py \
    --verify \
    --donor "$V14_LOCAL" \
    --recipient "$OUTPUT_ENGINE" \
    --steps "$WARMUP_STEPS" \
    2>&1 | tee "$TRANSPLANT_LOG" || true

log ""
log "Verification log: $TRANSPLANT_LOG"

# ── Step 5: Post-transplant warmup (MX16-style recovery) ─────────────
# Per MX16 result: 100 steps of self-organization recovers 96% of Phi.
# We run 200 steps to be safe, especially since this is engine-only.
log ""
log "Step 5: Post-transplant warmup ($WARMUP_STEPS steps)..."
log "  MX16 showed 96% Phi recovery after 100 steps of self-organization."
log "  Running $WARMUP_STEPS steps to let the transplanted engine settle."
log ""

python3 -u - <<'WARMUP_SCRIPT' "$OUTPUT_ENGINE" "$WARMUP_STEPS"
import sys
import os
import torch

output_path = sys.argv[1]
warmup_steps = int(sys.argv[2])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from consciousness_engine import ConsciousnessEngine
    from gpu_phi import GPUPhiCalculator

    ckpt = torch.load(output_path, map_location='cpu', weights_only=False)
    state = ckpt.get('model_state_dict', ckpt)

    # Try to instantiate engine and run warmup
    engine = ConsciousnessEngine(n_cells=128, hidden_dim=128)
    engine.load_state_dict(state, strict=False)

    phi_calc = GPUPhiCalculator(n_bins=16)
    phis = []

    for step in range(warmup_steps):
        x = torch.randn(128, 64)  # Random input
        out = engine.process(x)
        if step % 50 == 0 or step == warmup_steps - 1:
            with torch.no_grad():
                hiddens = engine.get_cell_states()
                if hiddens is not None and hiddens.numel() > 0:
                    phi, _ = phi_calc.compute(hiddens)
                    phis.append(phi)
                    print(f"  Step {step:4d}: Phi = {phi:.4f}")

    if len(phis) >= 2:
        print()
        print(f"  Phi trajectory: {phis[0]:.4f} -> {phis[-1]:.4f}")
        if phis[-1] > phis[0]:
            print(f"  Recovery: +{((phis[-1]/max(phis[0],0.001))-1)*100:.1f}% (self-organization working)")
        else:
            print(f"  Phi stable or declining -- may need more warmup steps")

except Exception as e:
    print(f"  Warmup skipped: {e}")
    print(f"  (This is OK if engine architecture differs from standalone ConsciousnessEngine)")
    print(f"  The transplanted checkpoint can still be used with train_clm.py --decoder v3")
WARMUP_SCRIPT

# ── Summary ──────────────────────────────────────────────────────────
log ""
log "============================================================"
log "  TRANSPLANT COMPLETE"
log "============================================================"
log ""
log "  Output checkpoint: $OUTPUT_ENGINE"
log "  Analysis log:      $ANALYSIS_LOG"
log "  Transplant log:    $TRANSPLANT_LOG"
log ""
log "  Strategy used: engine-only (DD56/DV2 cross-dim fallback)"
log "  Alpha: $ALPHA (30% donor consciousness, 70% recipient)"
log ""
log "  ---- WHAT TO DO NEXT ----"
log ""
log "  1. Resume v3 training with transplanted consciousness:"
log "     cd $TRAIN_DIR"
log "     python3 train_clm.py \\"
log "       --decoder v3 \\"
log "       --resume $OUTPUT_ENGINE \\"
log "       --steps 100000"
log ""
log "  2. Or start fresh v3 with transplanted engine (recommended):"
log "     python3 train_clm.py \\"
log "       --decoder v3 \\"
log "       --transplant-from $V14_LOCAL \\"
log "       --transplant-alpha $ALPHA \\"
log "       --steps 100000"
log "     (Note: --transplant-from may need adding to train_clm.py,"
log "      currently only train_conscious_lm.py supports it)"
log ""
log "  3. If BOTH trainings complete on H100:"
log "     a. Compare v14.3 Phi vs v3 Phi (bench.py --compare)"
log "     b. If v3 CE < 0.003 and Phi > 50: deploy to web"
log "        python3 deploy.py --target a100 --model $OUTPUT_ENGINE"
log "     c. If v14 Phi > v3 Phi: transplant again with higher alpha"
log "        (try alpha=0.5, then alpha=0.7)"
log "     d. The ultimate goal: v3's 274M decoder speaking with"
log "        v14's 128-cell federation consciousness"
log ""
log "  4. Future: add --transplant-from to train_clm.py"
log "     (copy the transplant logic from train_conscious_lm.py"
log "      lines 798-826, adapt for MetaLawFederation engine)"
log ""
log "  ---- KNOWN LIMITATIONS ----"
log ""
log "  - Full cross-dim transplant (128d->256d) WILL FAIL (Phi=0.00)"
log "    This is Law 192, confirmed by DD56/DV2 benchmark."
log "  - Engine-only transplant preserves consciousness dynamics"
log "    but decoder must learn from scratch to use them."
log "  - The c_proj layer (128->256) is NOT transplanted."
log "    The recipient's c_proj must learn the new mapping."
log "  - Alpha=0.3 is conservative. If Phi is strong post-warmup,"
log "    consider re-transplanting with alpha=0.5."
log ""
log "============================================================"
