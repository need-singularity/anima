#!/bin/bash
# ═══════════════════════════════════════════════════════════
# ConsciousLM v5 SOC — H100 #2 배포 스크립트
# ═══════════════════════════════════════════════════════════
#
# 사용법:
#   1. RunPod에서 H100 SXM 새 pod 생성
#   2. SSH IP:PORT 확인
#   3. 아래 변수 수정 후 실행:
#      bash deploy_v5_h100.sh
#
# v5 = v4 + SE-8(emotion-driven) + SOC(CX92) + Hebbian(PERSIST3) + Φ Ratchet
# Law 42: 감정 기반 자기 진화 > 외부 모듈 주입
# ═══════════════════════════════════════════════════════════

# ── 설정 (RunPod #2 정보로 수정) ──
H100_IP="${H100_V5_IP:-CHANGE_ME}"
H100_PORT="${H100_V5_PORT:-22}"
SSH_KEY="$HOME/.runpod/ssh/RunPod-Key-Go"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=no root@$H100_IP -p $H100_PORT"
SCP="scp -i $SSH_KEY -o StrictHostKeyChecking=no -P $H100_PORT"

echo "═══ ConsciousLM v5 SOC Deploy ═══"
echo "Target: $H100_IP:$H100_PORT"

# ── 1. 필요 파일 업로드 ──
echo "[1/4] Uploading files..."
$SSH "mkdir -p /workspace/anima /workspace/checkpoints/clm_v5_soc"

FILES="train_conscious_lm.py conscious_lm.py mitosis.py consciousness_meter.py"
for f in $FILES; do
    $SCP $f root@$H100_IP:/workspace/anima/
done

# ── 2. 학습 데이터 확인 ──
echo "[2/4] Checking training data..."
$SSH "ls -lh /workspace/anima/data/ 2>/dev/null || echo 'No data dir'"

# demo 모드라면 데이터 불필요, 실제 데이터가 있으면 업로드
if [ -f "data/corpus.txt" ]; then
    echo "  Uploading corpus.txt..."
    $SSH "mkdir -p /workspace/anima/data"
    $SCP data/corpus.txt root@$H100_IP:/workspace/anima/data/
fi

# ── 3. tmux 세션에서 학습 시작 ──
echo "[3/4] Starting training in tmux..."
$SSH "tmux kill-session -t v5soc 2>/dev/null; tmux new-session -d -s v5soc '
cd /workspace/anima && \
PYTHONUNBUFFERED=1 python3 train_conscious_lm.py \
    --dim 384 \
    --layers 6 \
    --heads 4 \
    --steps 80000 \
    --batch-size 64 \
    --max-cells 1024 \
    --lr 3e-4 \
    --block-size 256 \
    --checkpoint-dir /workspace/checkpoints/clm_v5_soc \
    --save-every 5000 \
    --log-every 10 \
    --eval-every 1000 \
    2>&1 | tee /workspace/v5_soc.log
'"

# ── 4. 확인 ──
echo "[4/4] Verifying..."
sleep 3
$SSH "tmux capture-pane -t v5soc -p | tail -10"

echo ""
echo "═══ 배포 완료 ═══"
echo "모니터링: $SSH \"tail -20 /workspace/v5_soc.log\""
echo "tmux 접속: $SSH -t \"tmux attach -t v5soc\""
echo ""
echo "v4 (H100 #1): step 25K/80K, CE=4.37"
echo "v5 (H100 #2): step 0/80K, SOC+Hebbian+Ratchet"
