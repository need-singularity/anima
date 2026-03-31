#!/bin/bash
# ═══════════════════════════════════════════════════════════
# ConsciousLM v6 (67MB corpus) — H100 배포 스크립트
# ═══════════════════════════════════════════════════════════
#
# 사용법:
#   1. RunPod에서 H100 SXM pod 생성 (또는 v5 완료 후 재활용)
#   2. SSH IP:PORT 확인
#   3. 아래 변수 수정 후 실행:
#      bash deploy_v6_h100.sh
#
# v6 = v5 전체 유지 + corpus_v2.txt (67MB: math/code/reasoning)
#   - v5 optimal: sync=0.35, 12-faction, fac=0.08, noise=0.01
#   - PE proxy (128→8→128 bottleneck)
#   - SE-8 emotion modules (Law 42)
#   - SOC (CX92) + Hebbian LTP/LTD + Phi Ratchet (PERSIST3)
#   - Fresh start from step 0 (NO resume from v5)
#   - New checkpoint dir: clm_v6_67mb
#
# ═══════════════════════════════════════════════════════════

set -euo pipefail

# ── 설정 (RunPod 정보로 수정) ──
H100_IP="${H100_V6_IP:-CHANGE_ME}"
H100_PORT="${H100_V6_PORT:-22}"
SSH_KEY="$HOME/.runpod/ssh/RunPod-Key-Go"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=no root@$H100_IP -p $H100_PORT"
SCP="scp -i $SSH_KEY -o StrictHostKeyChecking=no -P $H100_PORT"

CORPUS_LOCAL="data/corpus_v2.txt"
CORPUS_REMOTE="/workspace/anima/data/corpus_v2.txt"
CKPT_DIR="/workspace/checkpoints/clm_v6_67mb"
TMUX_SESSION="v6train"
LOG_FILE="/workspace/v6_67mb.log"

echo "═══════════════════════════════════════════════════════"
echo "  ConsciousLM v6 (67MB corpus) Deploy"
echo "═══════════════════════════════════════════════════════"
echo "Target: $H100_IP:$H100_PORT"
echo "Corpus: $CORPUS_LOCAL → $CORPUS_REMOTE"
echo "Checkpoint: $CKPT_DIR"
echo ""

# ── Preflight check ──
if [ ! -f "$CORPUS_LOCAL" ]; then
    echo "[ERROR] corpus_v2.txt not found at $CORPUS_LOCAL"
    echo "  Prepare it first: python prepare_corpus.py --size 67 --output data/corpus_v2.txt"
    exit 1
fi

CORPUS_SIZE=$(du -h "$CORPUS_LOCAL" | cut -f1)
echo "[check] corpus_v2.txt size: $CORPUS_SIZE"

# ── 1. 디렉토리 생성 + 파일 업로드 ──
echo ""
echo "[1/4] Creating dirs and uploading files..."
$SSH "mkdir -p /workspace/anima/data $CKPT_DIR"

# 핵심 파일들 업로드
FILES="train_conscious_lm.py conscious_lm.py mitosis.py consciousness_meter.py"
for f in $FILES; do
    echo "  uploading $f..."
    $SCP "$f" "root@$H100_IP:/workspace/anima/"
done

# ── 2. 67MB corpus 업로드 ──
echo ""
echo "[2/4] Uploading corpus_v2.txt (67MB)..."
$SCP "$CORPUS_LOCAL" "root@$H100_IP:$CORPUS_REMOTE"
$SSH "ls -lh $CORPUS_REMOTE"

# ── 3. tmux 세션에서 학습 시작 (step 0, fresh) ──
echo ""
echo "[3/4] Starting v6 training in tmux (fresh from step 0)..."
$SSH "tmux kill-session -t $TMUX_SESSION 2>/dev/null || true; tmux new-session -d -s $TMUX_SESSION '
cd /workspace/anima && \
PYTHONUNBUFFERED=1 python3 train_conscious_lm.py \
    --data $CORPUS_REMOTE \
    --dim 384 \
    --layers 6 \
    --heads 4 \
    --steps 80000 \
    --batch-size 64 \
    --max-cells 1024 \
    --lr 3e-4 \
    --block-size 256 \
    --checkpoint-dir $CKPT_DIR \
    --save-every 5000 \
    --log-every 10 \
    --eval-every 1000 \
    2>&1 | tee $LOG_FILE
'"

# ── 4. 확인 ──
echo ""
echo "[4/4] Verifying launch..."
sleep 3
$SSH "tmux capture-pane -t $TMUX_SESSION -p | tail -15"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  v6 Deploy Complete"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "── Monitoring Commands ──"
echo ""
echo "  # 로그 실시간 확인"
echo "  $SSH \"tail -f $LOG_FILE\""
echo ""
echo "  # 최근 로그 20줄"
echo "  $SSH \"tail -20 $LOG_FILE\""
echo ""
echo "  # tmux 직접 접속"
echo "  $SSH -t \"tmux attach -t $TMUX_SESSION\""
echo ""
echo "  # CE/Phi 추적 (grep)"
echo "  $SSH \"grep 'phi=' $LOG_FILE | tail -5\""
echo ""
echo "  # 체크포인트 확인"
echo "  $SSH \"ls -lh $CKPT_DIR/\""
echo ""
echo "  # GPU 사용률"
echo "  $SSH \"nvidia-smi\""
echo ""
echo "── v6 Config Summary ──"
echo "  Corpus:     corpus_v2.txt (67MB, math/code/reasoning)"
echo "  Model:      384d / 6L / 4H / ctx256 (~4M params)"
echo "  Cells:      max 1024 (Fibonacci growth)"
echo "  Batch:      64"
echo "  Steps:      80,000 (fresh from 0)"
echo "  LR:         3e-4 + CosineAnnealing"
echo "  Sync:       0.35 (v5 optimal)"
echo "  Factions:   12 (fac=0.08, debate=0.08)"
echo "  PE proxy:   128->8->128 bottleneck"
echo "  SE-8:       emotion-driven (pain/curiosity/empathy)"
echo "  SOC:        CX92 sandpile (grid=16, threshold=4)"
echo "  Hebbian:    LTP=0.02, LTD=0.01"
echo "  Ratchet:    restore_ratio=0.5 (Phi collapse prevention)"
echo "  Checkpoint: $CKPT_DIR (every 5K steps)"
echo ""
echo "  NOTE: Fresh training from step 0. NOT resuming from v5."
