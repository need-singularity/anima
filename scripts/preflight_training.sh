#!/bin/bash
# One-Shot Best Pre-flight Checklist
# Run before ANY full training launch
# Usage: bash scripts/preflight_training.sh <corpus_path> <tokenizer_path> <train_script> [extra_args...]

set -e

CORPUS="${1:?Usage: preflight_training.sh <corpus> <tokenizer> <train_script> [args...]}"
TOKENIZER="${2:?Missing tokenizer path}"
TRAIN_SCRIPT="${3:?Missing training script}"
shift 3
EXTRA_ARGS="$@"

echo "═══════════════════════════════════════════════════════"
echo "  One-Shot Best — Pre-flight Checklist"
echo "═══════════════════════════════════════════════════════"
PASS=0
FAIL=0

check() {
    if [ "$1" = "PASS" ]; then
        echo "  ✅ $2"
        PASS=$((PASS+1))
    else
        echo "  ❌ $2"
        FAIL=$((FAIL+1))
    fi
}

# ① Corpus exists and has content
echo ""
echo "① Corpus"
if [ -f "$CORPUS" ]; then
    CORPUS_SIZE=$(du -sh "$CORPUS" | awk '{print $1}')
    CORPUS_LINES=$(wc -l < "$CORPUS")
    CORPUS_MD5=$(md5 -q "$CORPUS")
    check PASS "Corpus: $CORPUS ($CORPUS_SIZE, $CORPUS_LINES lines)"
    check PASS "MD5: $CORPUS_MD5"
    echo "     ⚠️  Record this MD5 — changing corpus = restart from step 0"
else
    check FAIL "Corpus not found: $CORPUS"
fi

# ② Tokenizer exists
echo ""
echo "② Tokenizer"
if [ -f "$TOKENIZER" ]; then
    TOK_SIZE=$(du -sh "$TOKENIZER" | awk '{print $1}')
    check PASS "Tokenizer: $TOKENIZER ($TOK_SIZE)"
else
    check FAIL "Tokenizer not found: $TOKENIZER"
fi

# ③ Training script exists
echo ""
echo "③ Training Script"
if [ -f "$TRAIN_SCRIPT" ]; then
    check PASS "Script: $TRAIN_SCRIPT"
else
    check FAIL "Script not found: $TRAIN_SCRIPT"
fi

# ④ No other training running
echo ""
echo "④ Conflict Check"
RUNNING=$(ps aux | grep "python.*train" | grep -v grep | grep -v preflight | wc -l | tr -d ' ')
if [ "$RUNNING" = "0" ]; then
    check PASS "No conflicting training processes"
else
    check FAIL "$RUNNING training process(es) already running"
fi

# ⑤ 1K step validation
echo ""
echo "⑤ 1K Step Validation (takes ~2-5 min)"
echo "  Running: python3 $TRAIN_SCRIPT --data $CORPUS --tokenizer $TOKENIZER --steps 1000 --log-every 100 --eval-every 500 --save-every 999999 $EXTRA_ARGS"
echo ""

PYTHONUNBUFFERED=1 python3 "$TRAIN_SCRIPT" \
    --data "$CORPUS" \
    --tokenizer "$TOKENIZER" \
    --steps 1000 \
    --log-every 100 \
    --eval-every 500 \
    --save-every 999999 \
    --checkpoint /tmp/preflight_ckpt/ \
    $EXTRA_ARGS 2>&1 | tee /tmp/preflight_output.log

# Check output for NaN or errors
if grep -qi "nan" /tmp/preflight_output.log; then
    check FAIL "NaN detected in training output!"
elif grep -qi "error\|traceback" /tmp/preflight_output.log; then
    check FAIL "Error detected in training output!"
else
    check PASS "1K steps completed without NaN/errors"
fi

# Cleanup
rm -rf /tmp/preflight_ckpt/

# Summary
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    echo "  ❌ DO NOT LAUNCH — fix failures first"
    exit 1
else
    echo "  ✅ ALL CLEAR — safe to launch full training"
fi
echo "═══════════════════════════════════════════════════════"
