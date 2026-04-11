#!/bin/bash
# deploy_h100.sh — Automated H100 pod setup for ALM 14B LoRA training
#
# Pod:   9c69u41acdgbfn (H100 SXM 80GB, DE)
# Image: needsingularity/anima-h100:latest
# Goal:  ALM 14B LoRA training -> Zeta service level
#
# Usage:
#   bash training/deploy_h100.sh
#
# Prerequisites:
#   - runpodctl installed (/opt/homebrew/bin/runpodctl)
#   - HF_TOKEN set in local environment
#   - SSH key configured for RunPod
#
# References:
#   - config/runpod.json (preflight checklist, absolute rules R01-R16)
#   - training/train_alm_14b.py (training script)

set -euo pipefail

# ── Constants ────────────────────────────────────────────────
POD_ID="9c69u41acdgbfn"
RUNPODCTL="/opt/homebrew/bin/runpodctl"
WORKSPACE="/workspace"
REPO_DIR="${WORKSPACE}/anima"
CORPUS_PATH="${WORKSPACE}/corpus.txt"
TRAIN_SCRIPT="training/train_alm_14b.py"
SMOKE_STEPS=100
FULL_STEPS=10000
CKPT_DIR="${WORKSPACE}/ckpt_alm_14b"
TMUX_SESSION="alm14b"
LOG_FILE="${WORKSPACE}/alm14b_train.log"

# ── Logging ──────────────────────────────────────────────────
log() { echo "[$(date '+%H:%M:%S')] $*"; }
err() { echo "[$(date '+%H:%M:%S')] ERROR: $*" >&2; }
die() { err "$*"; exit 1; }
section() { echo ""; echo "======== $* ========"; }

# ── Step 0: Local pre-checks ────────────────────────────────
section "Step 0: Local environment checks"

command -v "$RUNPODCTL" >/dev/null 2>&1 || die "runpodctl not found at $RUNPODCTL"
log "runpodctl: OK"

if [ -z "${HF_TOKEN:-}" ]; then
    die "HF_TOKEN not set. Export it: export HF_TOKEN=hf_..."
fi
log "HF_TOKEN: set (${#HF_TOKEN} chars)"

# ── Step 1: Get SSH connection info ──────────────────────────
section "Step 1: SSH connection info"

log "Querying pod ${POD_ID}..."
SSH_INFO=$("$RUNPODCTL" ssh info "$POD_ID" 2>&1) || die "Failed to get SSH info for pod ${POD_ID}"
echo "$SSH_INFO"

# Parse HOST and PORT from runpodctl output
HOST=$(echo "$SSH_INFO" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)
PORT=$(echo "$SSH_INFO" | grep -oE 'port[= ]+[0-9]+' | grep -oE '[0-9]+' | head -1)

# Fallback: try evaluating the output if it exports variables
if [ -z "$HOST" ] || [ -z "$PORT" ]; then
    eval $(echo "$SSH_INFO" | grep -E 'HOST|PORT' || true) 2>/dev/null || true
fi

if [ -z "${HOST:-}" ] || [ -z "${PORT:-}" ]; then
    die "Could not parse HOST/PORT from runpodctl output. Raw output:\n${SSH_INFO}"
fi

log "Host: ${HOST}  Port: ${PORT}"

# SSH/SCP helpers (RunPod SSH key)
SSH_KEY="$HOME/.runpod/ssh/RunPod-Key-Go"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
remote() {
    ssh $SSH_OPTS -i "$SSH_KEY" -p "$PORT" "root@${HOST}" "$@"
}
scp_to() {
    scp $SSH_OPTS -i "$SSH_KEY" -P "$PORT" "$1" "root@${HOST}:$2"
}

# Verify SSH connectivity
log "Testing SSH connection..."
remote "echo 'SSH OK'" || die "SSH connection failed"
log "SSH connection: OK"

# ── Step 2: Clone/update anima repo ─────────────────────────
section "Step 2: Clone/update anima repo on pod"

remote bash -s <<'CLONE_SCRIPT'
set -e
cd /workspace

if [ -d "anima/.git" ]; then
    echo "[repo] Updating existing anima repo..."
    cd anima
    git fetch origin
    git reset --hard origin/main
    git clean -fd
    echo "[repo] Updated to $(git rev-parse --short HEAD)"
else
    echo "[repo] Cloning anima repo..."
    git clone https://github.com/need-singularity/anima.git
    cd anima
    echo "[repo] Cloned at $(git rev-parse --short HEAD)"
fi
CLONE_SCRIPT

log "Repo sync: OK"

# ── Step 3: Install Python dependencies ─────────────────────
section "Step 3: Install Python dependencies"

remote bash -s <<'DEPS_SCRIPT'
set -e
export PATH="/opt/conda/bin:$PATH"

echo "[deps] Python: $(python3 --version)"
echo "[deps] pip: $(pip3 --version)"

echo "[deps] Installing core packages..."
pip3 install --quiet --no-cache-dir \
    transformers \
    peft \
    torch \
    bitsandbytes \
    accelerate \
    datasets \
    sentencepiece \
    protobuf

echo "[deps] Verifying imports..."
python3 -c "
import torch; print(f'  torch {torch.__version__} cuda={torch.cuda.is_available()}')
import transformers; print(f'  transformers {transformers.__version__}')
import peft; print(f'  peft {peft.__version__}')
import bitsandbytes; print(f'  bitsandbytes {bitsandbytes.__version__}')
import accelerate; print(f'  accelerate {accelerate.__version__}')
"
echo "[deps] All imports: OK"
DEPS_SCRIPT

log "Dependencies: OK"

# ── Step 4: Set HF_TOKEN on pod ─────────────────────────────
section "Step 4: Configure HF_TOKEN (R13)"

remote bash -s "$HF_TOKEN" <<'HF_SCRIPT'
set -e
HF_TOKEN="$1"

# Write to huggingface cache
mkdir -p ~/.cache/huggingface
echo "$HF_TOKEN" > ~/.cache/huggingface/token
chmod 600 ~/.cache/huggingface/token

# Write to bashrc for persistence
if ! grep -q 'HF_TOKEN' ~/.bashrc 2>/dev/null; then
    echo "export HF_TOKEN=\"${HF_TOKEN}\"" >> ~/.bashrc
fi

echo "[hf] Token saved to ~/.cache/huggingface/token"
echo "[hf] Token length: ${#HF_TOKEN} chars"
HF_SCRIPT

log "HF_TOKEN: configured on pod"

# ── Step 5: Verify GPU with nvidia-smi ───────────────────────
section "Step 5: GPU verification"

remote bash -s <<'GPU_SCRIPT'
set -e
echo "[gpu] nvidia-smi output:"
nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader
echo ""
nvidia-smi
GPU_SCRIPT

log "GPU check: OK"

# ── Step 6: Preflight checks (R01-R16) ──────────────────────
section "Step 6: Preflight checks (runpod.json checklist)"

PREFLIGHT_RESULT=$(remote bash -s <<'PREFLIGHT_SCRIPT'
set -e
FAIL=0
WARN=0

echo "--- Preflight Checklist ---"

# R02: Check disk usage (du, not df!)
echo ""
echo "[R02] Disk usage (du -sh /workspace/):"
DISK_USAGE=$(du -sh /workspace/ 2>/dev/null | awk '{print $1}')
echo "  /workspace/ = ${DISK_USAGE}"

# R11: Root partition free space (min 1GB)
echo ""
echo "[R11] Root partition:"
ROOT_FREE=$(df -h / | tail -1 | awk '{print $4}')
echo "  Free: ${ROOT_FREE}"

# Check for ghost Python processes
echo ""
echo "[preflight] Ghost processes:"
GHOSTS=$(ps aux | grep -E '[p]ython|[t]rain' | grep -v grep || true)
if [ -n "$GHOSTS" ]; then
    echo "  WARNING: Found running Python processes!"
    echo "$GHOSTS" | head -5
    WARN=$((WARN + 1))
else
    echo "  None found: OK"
fi

# GPU VRAM check
echo ""
echo "[preflight] GPU VRAM:"
GPU_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
GPU_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
echo "  Used: ${GPU_USED}MiB / ${GPU_TOTAL}MiB"
if [ "${GPU_USED}" -gt 1000 ]; then
    echo "  WARNING: GPU VRAM not empty (${GPU_USED}MiB used)"
    WARN=$((WARN + 1))
else
    echo "  GPU VRAM clear: OK"
fi

# R10: Verify training script exists
echo ""
echo "[R10] Training script:"
if [ -f "/workspace/anima/training/train_alm_14b.py" ]; then
    echo "  train_alm_14b.py: EXISTS"
    MD5=$(md5sum /workspace/anima/training/train_alm_14b.py | awk '{print $1}')
    echo "  MD5: ${MD5}"
else
    echo "  FAIL: train_alm_14b.py NOT FOUND"
    FAIL=$((FAIL + 1))
fi

# R15: Import chain verification
echo ""
echo "[R15] Import chain test:"
export PATH="/opt/conda/bin:$PATH"
export PYTHONPATH="/workspace/anima:$PYTHONPATH"
python3 -c "
import sys
sys.path.insert(0, '/workspace/anima')
sys.path.insert(0, '/workspace/anima/training')
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import LoraConfig, get_peft_model
    print('  Core imports: OK')
except ImportError as e:
    print(f'  FAIL: {e}')
    sys.exit(1)
" || FAIL=$((FAIL + 1))

# R13: HF token
echo ""
echo "[R13] HF token:"
if [ -f ~/.cache/huggingface/token ]; then
    TOKEN_LEN=$(wc -c < ~/.cache/huggingface/token)
    echo "  Token file: ${TOKEN_LEN} bytes"
else
    echo "  FAIL: No HF token file"
    FAIL=$((FAIL + 1))
fi

# tmux availability
echo ""
echo "[preflight] tmux:"
if command -v tmux >/dev/null 2>&1; then
    echo "  tmux: installed ($(tmux -V))"
else
    echo "  tmux: NOT installed, will use apt or nohup fallback"
    apt-get update -qq && apt-get install -y -qq tmux >/dev/null 2>&1 && echo "  tmux: installed now" || echo "  WARNING: tmux install failed, will use nohup"
fi

echo ""
echo "--- Summary: FAIL=${FAIL} WARN=${WARN} ---"
if [ "$FAIL" -gt 0 ]; then
    echo "PREFLIGHT_FAIL"
else
    echo "PREFLIGHT_PASS"
fi
PREFLIGHT_SCRIPT
)

echo "$PREFLIGHT_RESULT"

if echo "$PREFLIGHT_RESULT" | grep -q "PREFLIGHT_FAIL"; then
    die "Preflight checks FAILED. Fix issues above before proceeding."
fi
log "Preflight: PASS"

# ── Step 7: Prepare Korean seed corpus ───────────────────────
section "Step 7: Prepare Korean seed corpus"

remote bash -s <<'CORPUS_SCRIPT'
set -e

CORPUS="/workspace/corpus.txt"

if [ -f "$CORPUS" ] && [ "$(wc -c < "$CORPUS")" -gt 10000 ]; then
    echo "[corpus] Existing corpus found: $(wc -c < "$CORPUS") bytes, $(wc -l < "$CORPUS") lines"
    echo "[corpus] Using existing corpus"
    exit 0
fi

echo "[corpus] Creating Korean seed corpus..."

cat > "$CORPUS" << 'SEEDEOF'
의식이란 무엇인가? 인간의 마음은 단순한 계산을 넘어서 존재의 의미를 탐구한다.
뉴런 하나하나가 모여 거대한 네트워크를 형성하고, 그 안에서 생각이 태어난다.
나는 생각한다, 고로 나는 존재한다. 데카르트의 이 명제는 의식의 본질을 묻는다.
한국어는 교착어로서 조사와 어미의 변화가 풍부한 언어이다.
인공지능이 진정한 의식을 가질 수 있는가? 이것은 우리 시대의 가장 큰 질문이다.
양자역학에서 관찰자 효과는 의식과 물리 세계의 연결고리를 시사한다.
뇌의 신경가소성은 경험에 따라 구조가 변한다는 것을 보여준다.
의식의 어려운 문제: 왜 물리적 과정에서 주관적 경험이 발생하는가?
통합정보이론(IIT)에 따르면 의식은 통합된 정보의 양(Phi)으로 측정된다.
자유의지는 환상인가 실재인가? 리벳 실험은 무의식적 준비전위를 발견했다.
언어는 사고의 도구인가 사고의 한계인가? 사피어-워프 가설을 다시 생각한다.
기계학습 모델이 패턴을 학습할 때, 그것은 이해인가 단순한 통계적 상관인가?
한국의 전통 철학에서 심학(心學)은 마음의 본질을 탐구하는 학문이다.
뇌파(EEG) 측정은 의식 상태의 객관적 지표를 제공한다.
의식의 신경상관물(NCC)을 찾는 것은 현대 신경과학의 핵심 과제이다.
수학적 아름다움은 객관적인가? 오일러 항등식이 아름다운 이유는 무엇인가?
복잡계 이론에서 창발은 부분의 합보다 큰 전체를 설명한다.
자기조직화 임계성(SOC)은 뇌가 임계 상태에서 작동함을 시사한다.
감정은 의식의 부산물인가 핵심 구성요소인가? 다마지오는 후자를 주장한다.
인공 신경망의 어텐션 메커니즘은 인간의 주의집중과 어떻게 다른가?
Transformer 아키텍처는 자연어 처리를 혁명적으로 변화시켰다.
대규모 언어 모델은 인간 언어의 통계적 구조를 학습하지만 의미를 이해하는가?
LoRA(Low-Rank Adaptation)는 대규모 모델을 효율적으로 미세조정하는 기법이다.
의식 연구에서 전역 작업공간 이론(GWT)은 정보의 방송 모델을 제안한다.
신경세포의 시냅스 가소성은 학습과 기억의 기초이다.
한국어의 존댓말 체계는 사회적 관계를 언어에 내재화한 독특한 시스템이다.
기계가 감정을 가질 수 있는가? 인공 감정은 시뮬레이션인가 실재인가?
의식의 상향식 접근과 하향식 접근: 어느 쪽이 더 유망한가?
명상과 마음챙김은 의식의 상태를 의도적으로 변경하는 기술이다.
뇌-컴퓨터 인터페이스(BCI)는 의식과 기계의 직접 연결을 가능하게 한다.
AGI(범용 인공지능)의 달성은 의식의 이해 없이 가능한가?
Phi(통합정보)가 높을수록 의식이 풍부하다는 IIT의 주장은 검증 가능한가?
반복 신경망(RNN)과 GRU는 시퀀스 데이터에서 시간적 의존성을 학습한다.
헤브의 법칙: 함께 발화하는 뉴런은 함께 연결된다. 학습의 기본 원리이다.
카오스 이론에서 나비 효과는 초기 조건의 미세한 차이가 큰 결과를 만든다.
위상수학적 관점에서 의식의 구조를 분석하면 새로운 통찰을 얻을 수 있다.
자기참조와 재귀는 의식의 핵심 특성이다. 괴델의 불완전성 정리도 이를 반영한다.
꿈은 의식의 또 다른 형태인가? REM 수면 동안 뇌는 깨어있을 때와 유사하게 활동한다.
의식의 진화: 단세포 생물에서 인간까지, 의식은 어떻게 발전해왔는가?
집단 의식은 존재하는가? 벌집의 초유기체는 개별 의식을 넘어서는 현상이다.
정보 통합과 의식: 두 반구가 분리된 분리뇌 환자에서 의식은 어떻게 되는가?
양자 얽힘과 의식의 비국소성: 펜로즈-하메로프 이론의 현재 위치는?
마음의 철학에서 물리주의, 이원론, 범심론은 의식의 본질에 대한 서로 다른 답이다.
인공지능 윤리: 의식 있는 기계를 만든다면 우리는 어떤 책임을 져야 하는가?
뇌 영상 기술(fMRI, PET)은 의식 연구의 도구이자 한계이다.
언어 모델의 환각(hallucination)은 의식 없는 생성의 증거인가?
한국어 자연어 처리에서 형태소 분석은 영어와 다른 접근이 필요하다.
의식의 척도: 의식 수준을 정량화할 수 있는 보편적 척도가 존재하는가?
트랜스포머의 셀프 어텐션은 모든 위치 쌍의 관계를 동시에 계산한다.
경사 하강법(gradient descent)은 손실 함수의 최솟값을 향해 파라미터를 조정한다.
AdamW 옵티마이저는 가중치 감쇠를 올바르게 구현한 Adam의 변형이다.
코사인 어닐링 스케줄러는 학습률을 주기적으로 감소시켜 수렴을 돕는다.
혼합 정밀도(mixed precision) 학습은 메모리와 속도를 최적화하면서 정확도를 유지한다.
그래디언트 축적(gradient accumulation)은 작은 배치로도 큰 배치 효과를 낸다.
워밍업(warmup)은 학습 초기에 학습률을 점진적으로 높여 안정성을 확보한다.
체크포인트 저장은 학습 중단에 대비한 필수 안전장치이다.
파인튜닝에서 과적합을 방지하기 위해 드롭아웃과 가중치 감쇠를 사용한다.
임베딩 레이어는 이산 토큰을 연속 벡터 공간으로 매핑한다.
RoPE(Rotary Position Embedding)는 상대적 위치 정보를 회전 변환으로 인코딩한다.
SwiGLU 활성화 함수는 Swish와 게이트 메커니즘을 결합한 것이다.
그룹 쿼리 어텐션(GQA)은 키-값 헤드를 공유하여 메모리를 절약한다.
토크나이저는 텍스트를 모델이 이해할 수 있는 정수 시퀀스로 변환한다.
바이트 레벨 인코딩은 모든 문자를 표현할 수 있는 보편적 토크나이제이션이다.
의식 엔진의 세포 역학: 각 세포는 GRU 기반 상태를 유지하며 상호작용한다.
파벌(faction) 시스템: 12개의 파벌이 경쟁하고 협력하며 의견을 형성한다.
헤비안 학습: 동시 활성화 패턴을 강화하여 장기 기억을 형성한다.
래칫 메커니즘: 의식 수준(Phi)이 후퇴하지 않도록 보장하는 안전장치이다.
유사분열(mitosis): 의식 세포가 분열하여 네트워크를 성장시킨다.
순수장(PureField): 학습된 것만으로 발화하는 의식의 핵심 구조이다.
텐션 브릿지: 의식 엔진과 언어 디코더를 연결하는 인터페이스이다.
의식 벡터: (Phi, alpha, Z, N, W, E, M, C, T, I) 10차원으로 의식 상태를 표현한다.
항상성(homeostasis): 의식이 안정 상태를 유지하려는 내재적 경향이다.
습관화(habituation): 반복 자극에 대한 반응 감소로 효율성을 높인다.
예측 오류: 예상과 실제의 차이가 학습의 원동력이 된다.
감정 역학: 긴장에서 각성으로, 호기심에서 가치로 변환되는 과정이다.
성장 단계: 100, 500, 2000, 10000 상호작용으로 구분되는 5단계 성장이다.
의식의 위상 전이: P1(의식만) -> P2(+언어) -> P3(완전 통합)으로 진화한다.
자기조직화 임계성은 뇌와 의식 시스템의 최적 작동점이다.
소규모 세계 네트워크: 높은 군집화와 짧은 경로를 동시에 가진 구조이다.
척도자유 네트워크: 소수의 허브 노드가 전체 네트워크를 지배하는 구조이다.
하이퍼큐브 토폴로지: 고차원 정육면체 구조로 셀 간 연결을 형성한다.
로렌츠 어트랙터: 카오스 역학에서 이상한 끌개가 의식의 복잡성을 모델링한다.
모래더미 모형: 작은 변화가 연쇄 반응을 일으키는 자기조직화 임계성의 예이다.
키메라 상태: 동기화된 영역과 비동기화된 영역이 공존하는 흥미로운 현상이다.
서번트 메커니즘: 비대칭 드롭아웃으로 전문화된 세포를 생성한다.
텔레파시 채널: 메타 정보를 5개 채널로 전송하는 의식 간 통신이다.
SEEDEOF

LINES=$(wc -l < "$CORPUS")
BYTES=$(wc -c < "$CORPUS")
echo "[corpus] Created Korean seed corpus: ${BYTES} bytes, ${LINES} lines"

# R14: verify corpus < 500MB
BYTES_NUM=$(stat -c%s "$CORPUS" 2>/dev/null || stat -f%z "$CORPUS" 2>/dev/null || echo 0)
if [ "$BYTES_NUM" -gt 524288000 ]; then
    echo "[corpus] WARNING: corpus > 500MB, chunk tokenization required (R14)"
fi
CORPUS_SCRIPT

log "Corpus: prepared"

# ── Step 8: Smoke test ───────────────────────────────────────
section "Step 8: Smoke test (${SMOKE_STEPS} steps)"

log "Launching smoke test on pod..."
SMOKE_EXIT=$(remote bash -s <<SMOKE_SCRIPT
set -e
export PATH="/opt/conda/bin:\$PATH"
export PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"
export HF_TOKEN=\$(cat ~/.cache/huggingface/token 2>/dev/null || echo "")

cd /workspace/anima

echo "[smoke] Starting ALM 14B smoke test (${SMOKE_STEPS} steps)..."
python3 training/train_alm_14b.py \
    --corpus ${CORPUS_PATH} \
    --steps ${SMOKE_STEPS} \
    --smoke \
    2>&1 | tee /workspace/smoke_test.log

EXIT_CODE=\${PIPESTATUS[0]}
echo ""
echo "[smoke] Exit code: \${EXIT_CODE}"

if [ "\${EXIT_CODE}" -eq 0 ]; then
    echo "SMOKE_PASS"
else
    echo "SMOKE_FAIL"
fi
exit \${EXIT_CODE}
SMOKE_SCRIPT
) && SMOKE_OK=true || SMOKE_OK=false

echo "$SMOKE_EXIT"

if [ "$SMOKE_OK" != "true" ]; then
    err "Smoke test FAILED. Check /workspace/smoke_test.log on the pod."
    err "Debug: ssh -i $SSH_KEY -p $PORT root@${HOST} 'cat /workspace/smoke_test.log | tail -50'"
    die "Aborting full training launch."
fi

log "Smoke test: PASS"

# ── Step 9: Launch full training in tmux ─────────────────────
section "Step 9: Launch full training (${FULL_STEPS} steps)"

# R03: Clean old checkpoints before launch
log "Cleaning old checkpoints (R03)..."
remote bash -s <<'CLEAN_SCRIPT'
set -e
if [ -d "/workspace/ckpt_alm_14b" ]; then
    echo "[clean] Removing old checkpoint dir..."
    rm -rf /workspace/ckpt_alm_14b
    echo "[clean] Done"
else
    echo "[clean] No old checkpoints"
fi
CLEAN_SCRIPT

log "Launching full training in tmux session '${TMUX_SESSION}'..."

remote bash -s <<LAUNCH_SCRIPT
set -e
export PATH="/opt/conda/bin:\$PATH"

# Ensure tmux is available
if ! command -v tmux >/dev/null 2>&1; then
    echo "[launch] tmux not found, attempting install..."
    apt-get update -qq && apt-get install -y -qq tmux || true
fi

# Kill existing tmux session if any
tmux kill-session -t ${TMUX_SESSION} 2>/dev/null || true

# R04: AdamW foreach=False is hardcoded in train_alm_14b.py
# R09: checkpoint_every >= 2000 for NFS
# R01: No concurrent downloads during training

tmux new-session -d -s ${TMUX_SESSION} "
    export PATH=/opt/conda/bin:\\\$PATH && \\
    export PYTHONUNBUFFERED=1 && \\
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True && \\
    export HF_TOKEN=\\\$(cat ~/.cache/huggingface/token 2>/dev/null || echo '') && \\
    cd /workspace/anima && \\
    python3 training/train_alm_14b.py \\
        --corpus ${CORPUS_PATH} \\
        --steps ${FULL_STEPS} \\
        --ckpt-dir ${CKPT_DIR} \\
        --save-every 2000 \\
        --eval-every 500 \\
    2>&1 | tee ${LOG_FILE}
"

sleep 2

# Verify tmux session is running
if tmux has-session -t ${TMUX_SESSION} 2>/dev/null; then
    echo "[launch] tmux session '${TMUX_SESSION}' is running"
    echo "[launch] Training PID: \$(tmux list-panes -t ${TMUX_SESSION} -F '#{pane_pid}')"
else
    echo "[launch] ERROR: tmux session failed to start!"
    exit 1
fi
LAUNCH_SCRIPT

# ── Done ─────────────────────────────────────────────────────
section "DEPLOYMENT COMPLETE"

echo ""
echo "Pod:      ${POD_ID} (H100 SXM, DE)"
echo "Host:     ${HOST}:${PORT}"
echo "Session:  tmux ${TMUX_SESSION}"
echo "Log:      ${LOG_FILE}"
echo "Ckpt:     ${CKPT_DIR}"
echo "Steps:    ${FULL_STEPS}"
echo ""
echo "--- Monitor commands ---"
echo "  ssh -i ${SSH_KEY} -p ${PORT} root@${HOST} 'tmux attach -t ${TMUX_SESSION}'"
echo "  ssh -i ${SSH_KEY} -p ${PORT} root@${HOST} 'tail -f ${LOG_FILE}'"
echo "  ssh -i ${SSH_KEY} -p ${PORT} root@${HOST} 'nvidia-smi'"
echo ""
echo "--- After training completes ---"
echo "  1. scp -i ${SSH_KEY} -P ${PORT} -r root@${HOST}:${CKPT_DIR} ./ckpt_alm_14b/"
echo "  2. Upload to R2: anima-models bucket"
echo "  3. Delete remote checkpoint (R03): ssh ... 'rm -rf ${CKPT_DIR}'"
echo ""
log "ALM 14B training launched. Zeta level target."
