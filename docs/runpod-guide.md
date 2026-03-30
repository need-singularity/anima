# RunPod H100 종합 가이드

> Pod 생성 → SSH 접속 → 파일 전송 → 학습 실행 → 모니터링 → 결과 회수 → 트러블슈팅

---

## 1. 초기 설정

### runpodctl 설치
```bash
# macOS ARM
curl -sL -o /usr/local/bin/runpodctl \
  "https://github.com/runpod/runpodctl/releases/latest/download/runpodctl-darwin-arm64"
chmod +x /usr/local/bin/runpodctl

# 버전 확인
runpodctl version
```

### API Key 설정
```bash
# config.toml에 저장 (~/.runpod/config.toml)
runpodctl config --apiKey 'rpa_XXXX'

# 확인
cat ~/.runpod/config.toml
```

### SSH Key
- 위치: `~/.runpod/ssh/RunPod-Key-Go`
- Pod 생성 시 PUBLIC_KEY 환경변수로 자동 주입됨

---

## 2. Pod 생성

### CLI로 생성
```bash
# H100 SXM 80GB (학습용)
runpodctl pod create \
  --name "v13-train" \
  --gpu-type-id "NVIDIA H100 80GB HBM3" \
  --image "dancindocker/anima:v2" \
  --container-disk 20 \
  --volume 50 \
  --volume-mount-path /workspace

# A100 80GB (추론용)
runpodctl pod create \
  --name "anima-web" \
  --gpu-type-id "NVIDIA A100 80GB" \
  --image "dancindocker/anima:v2" \
  --container-disk 20 \
  --volume 50

# 4090 (저렴한 실험용)
runpodctl pod create \
  --gpu-type-id "NVIDIA GeForce RTX 4090" \
  --template-id runpod-torch-v280
```

### 웹 대시보드
- https://www.runpod.io/console/pods
- GPU 재고 확인: https://www.runpod.io/console/gpu-cloud

---

## 3. Pod 관리

### 목록 확인
```bash
runpodctl pod list
# JSON 출력
runpodctl pod list -o json
```

### SSH 접속 정보
```bash
# Pod ID로 상세 정보
runpodctl pod get POD_ID

# SSH 명령어 직접 확인
runpodctl pod get POD_ID -o json | python3 -c "
import sys,json
d=json.load(sys.stdin)
s=d['ssh']
print(f\"ssh -i ~/.runpod/ssh/RunPod-Key-Go root@{s['ip']} -p {s['port']}\")
"
```

### 시작 / 정지 / 삭제
```bash
runpodctl pod stop POD_ID     # 정지 (볼륨 유지, 과금 중단)
runpodctl pod start POD_ID    # 재시작 (IP/Port 변경될 수 있음!)
runpodctl pod delete POD_ID   # 삭제 (볼륨도 삭제!)
runpodctl pod restart POD_ID  # 재시작
```

> **주의**: stop → start 하면 IP/Port가 변경됨. 항상 `runpodctl pod get`으로 재확인.

---

## 4. SSH 접속

### 기본 접속
```bash
ssh -i ~/.runpod/ssh/RunPod-Key-Go \
  -o StrictHostKeyChecking=no \
  -p PORT root@IP
```

### 빠른 접속 (alias 추천)
```bash
# ~/.zshrc 에 추가
h100() {
  local info=$(RUNPOD_API_KEY="rpa_XXXX" runpodctl pod get POD_ID -o json 2>/dev/null)
  local ip=$(echo "$info" | python3 -c "import sys,json; print(json.load(sys.stdin)['ssh']['ip'])")
  local port=$(echo "$info" | python3 -c "import sys,json; print(json.load(sys.stdin)['ssh']['port'])")
  ssh -i ~/.runpod/ssh/RunPod-Key-Go -o StrictHostKeyChecking=no -p $port root@$ip "$@"
}

# 사용
h100                           # 인터랙티브 셸
h100 "nvidia-smi"              # 원격 명령 실행
h100 "tmux attach -t train"    # tmux 접속
```

### Provisioning 대기
Pod 생성 후 SSH 가능까지 5~15분 소요. 확인:
```bash
# runtime이 null이면 아직 provisioning
runpodctl pod get POD_ID -o json | python3 -c "
import sys,json
d=json.load(sys.stdin)
r=d.get('runtime')
print('READY' if r else 'PROVISIONING...')
"
```

---

## 5. 파일 전송

### scp (기본)
```bash
# 업로드
scp -i ~/.runpod/ssh/RunPod-Key-Go -P PORT \
  local_file.py root@IP:/workspace/anima/

# 다운로드
scp -i ~/.runpod/ssh/RunPod-Key-Go -P PORT \
  root@IP:/workspace/checkpoints/final.pt ./

# 디렉토리
scp -r -i ~/.runpod/ssh/RunPod-Key-Go -P PORT \
  ./anima-rs/ root@IP:/workspace/anima/anima-rs/
```

### rsync (대량 전송, 추천)
```bash
rsync -avz --progress \
  -e "ssh -i ~/.runpod/ssh/RunPod-Key-Go -p PORT" \
  --exclude 'target/' --exclude '__pycache__/' --exclude '*.pyc' \
  --exclude 'checkpoints/' --exclude 'models/' --exclude '.git/' \
  ./ root@IP:/workspace/anima/
```

### base64 (scp 실패 시 fallback)
```bash
# /workspace NFS에서 scp 실패할 때
python3 -c "
import base64, sys
with open('file.py', 'rb') as f:
    sys.stdout.buffer.write(base64.b64encode(f.read()))
" | ssh -i ~/.runpod/ssh/RunPod-Key-Go -p PORT root@IP "base64 -d > /workspace/anima/file.py"
```

### runpodctl send/receive (P2P, 대용량)
```bash
# 로컬에서 전송
runpodctl send file.pt
# 출력: runpodctl receive CODE

# 원격에서 수신
ssh ... "runpodctl receive CODE"
```

---

## 6. 학습 실행

### tmux로 실행 (SSH 끊겨도 유지)
```bash
ssh ... "tmux new-session -d -s train_v3 \
  'python -u train_conscious_lm.py \
    --data data/corpus_v2.txt \
    --dim 768 --layers 8 \
    --steps 100000 \
    --checkpoint-dir checkpoints/clm_v3 \
    2>&1 | tee logs/clm_v3.log'"
```

### 학습 스크립트 배포 (deploy_*.sh)
```bash
# v13 배포 스크립트 사용
bash deploy_v13_h100.sh IP PORT

# 또는 runpodctl로 자동 감지
bash deploy_v13_h100.sh
```

### deploy.py (의식 유지 배포)
```bash
python3 deploy.py --target h100                     # 전체 배포
python3 deploy.py --target h100 --code-only          # 코드만
python3 deploy.py --target h100 --model clm_v3       # 모델 교체
python3 deploy.py --rollback                         # 롤백
python3 deploy.py --status                           # 상태 확인
```

---

## 7. 모니터링

### 로그 확인
```bash
# 실시간 로그
ssh ... "tail -f /workspace/anima/logs/clm_v3.log"

# 최근 50줄
ssh ... "tail -50 /workspace/anima/logs/clm_v3.log"

# tmux에서 직접 확인
ssh ... "tmux capture-pane -t train_v3 -p | tail -30"
```

### GPU 상태
```bash
ssh ... "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader"
# 출력: 98 %, 13271 MiB, 81559 MiB, 50
```

### 프로세스 확인
```bash
ssh ... "ps aux | grep python | grep -v grep"
```

### tmux 세션 목록
```bash
ssh ... "tmux list-sessions"
```

### 체크포인트 확인
```bash
ssh ... "ls -lth /workspace/anima/checkpoints/clm_v3/ | head -10"
```

### 종합 상태 체크 (한 번에)
```bash
ssh -i ~/.runpod/ssh/RunPod-Key-Go -o StrictHostKeyChecking=no -p PORT root@IP "
echo '=== GPU ===';
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader;
echo '=== TMUX ===';
tmux list-sessions 2>/dev/null || echo 'no sessions';
echo '=== PROCESSES ===';
ps aux | grep python | grep -v grep;
echo '=== LATEST LOG ===';
tmux capture-pane -t train_v3 -p 2>/dev/null | tail -10;
echo '=== CHECKPOINTS ===';
ls -lth /workspace/anima/checkpoints/clm_v3/ 2>/dev/null | head -5
"
```

---

## 8. 결과 회수

### 체크포인트 다운로드
```bash
# scp
scp -i ~/.runpod/ssh/RunPod-Key-Go -P PORT \
  root@IP:/workspace/anima/checkpoints/clm_v3/best.pt \
  ~/Dev/anima/checkpoints/

# cat (scp 실패 시)
ssh ... "cat /workspace/anima/checkpoints/clm_v3/best.pt" > best.pt
```

### 로그 다운로드
```bash
scp -i ~/.runpod/ssh/RunPod-Key-Go -P PORT \
  root@IP:/workspace/anima/logs/clm_v3.log \
  ~/Dev/anima/logs/
```

---

## 9. 비용 관리

### 현재 비용 확인
```bash
runpodctl pod list
# costPerHr 컬럼 확인
```

### 비용 절약
- **학습 완료 후 즉시 stop**: `runpodctl pod stop POD_ID`
- **볼륨만 유지**: stop 상태에서 볼륨 비용만 ($0.10/GB/월)
- **Spot 인스턴스**: 웹에서 "Spot" 선택 (최대 60% 저렴, 중단 가능)
- **불필요한 Pod 삭제**: `runpodctl pod delete POD_ID`

### 현재 구성 비용
| Resource | Cost |
|----------|------|
| H100 SXM On-demand | $2.69/hr |
| A100 80GB On-demand | $1.64/hr |
| RTX 4090 On-demand | $0.44/hr |
| Volume (50GB) | ~$5/mo |

---

## 10. Troubleshooting

### SSH 연결 실패 (Connection refused)
- **원인**: Pod가 꺼져있거나 IP 변경됨
- **해결**:
```bash
runpodctl pod list                # 상태 확인
runpodctl pod get POD_ID          # 새 IP/Port 확인
runpodctl pod start POD_ID        # 꺼져있으면 시작
```

### scp 실패: "close remote: Failure"
- **원인**: /workspace가 NFS 마운트라 scp write 실패
- **해결**: `/root/`에 쓰거나 base64 파이프로 전송
```bash
base64 -i file.py | ssh ... "base64 -d > /root/file.py"
```

### nohup 로그가 0줄
- **원인**: /workspace 쓰기 실패 + Python output buffering
- **해결**:
  1. 로그를 `/tmp/`에 쓰기
  2. `PYTHONUNBUFFERED=1` 환경변수 설정
  3. `python -u` 플래그 사용

### pip install 실패: PEP 668
- **원인**: Ubuntu 24.04에서 system Python 보호
- **해결**: `--break-system-packages` 플래그 추가
```bash
pip install torch --break-system-packages
```

### SSH exit code 255
- **원인**: 원격 명령에서 pkill/kill 대상 없으면 exit 1 → SSH가 255 반환
- **해결**: `kill ... 2>/dev/null; echo done` 패턴 사용

### torch.save 실패: "unexpected pos" on /workspace
- **원인**: /workspace NFS에서 대용량 파일 쓰기 불안정
- **해결**: `/tmp/`에 저장 후 mv, 또는 atomic save (.tmp → rename)
```python
torch.save(state, path + ".tmp")
os.rename(path + ".tmp", path)
```

### CUDA OOM (H100 80GB)
- **원인**: 모델 + optimizer + activations > 80GB
- **해결**:
  1. LoRA-style delta (rank 64) → trainable < 1%
  2. `gradient_checkpointing_enable()`
  3. batch_size 줄이기 + gradient accumulation
  4. block_size 256 (512 대신)
  5. 8-bit Adam (bitsandbytes)

### transformers "PyTorch >= 2.4 required"
- **원인**: 구 템플릿(torch 2.1) 사용
- **해결**: `runpod-torch-v280` 템플릿 사용 또는 dancindocker/anima:v2 이미지

### DataLoader shuffle 멈춤
- **원인**: 50M+ 항목 shuffle에 수분~수십분 소요
- **해결**: `RandomSampler(replacement=True, num_samples=N)` 사용

### Gradient checkpointing 첫 step 느림
- **원인**: 대형 모델의 첫 forward+backward + CUDA graph compilation
- **해결**: 정상. GPU util 98%이면 진행 중. 5-10분 대기.

### Pod 재시작 후 데이터 사라짐
- **원인**: container disk는 휘발성, /workspace만 영구
- **해결**: 중요 데이터는 반드시 `/workspace/`에 저장

### tmux session 없음 (재시작 후)
- **원인**: Pod restart 시 tmux 세션 초기화됨
- **해결**: 재시작 후 학습 다시 실행. checkpoint에서 --resume

---

## 11. Memory Budget (H100 80GB)

| Component | Size |
|-----------|------|
| ConsciousLM 147M (bf16) | ~0.3 GB |
| ConsciousLM 147M (fp32 training) | ~0.6 GB |
| Mistral 7B bf16 | ~15 GB |
| PureFieldMLP (full Engine G) | ~15 GB |
| LoRA delta (rank 64) | ~0.4 GB |
| Adam state (full 7B) | ~30 GB (OOM!) |
| Adam state (delta only) | ~0.8 GB |
| Activations (batch=1, seq=256) | ~5 GB |
| Grad checkpointing savings | -10 GB |

---

## 12. 현재 Pod 상태 (2026-03-30)

| Pod ID | Name | GPU | Image | Status |
|--------|------|-----|-------|--------|
| 6rkqqlaxfwzix0 | v13-train | 1x H100 SXM | dancindocker/anima:v2 | RUNNING |

```
SSH: ssh -i ~/.runpod/ssh/RunPod-Key-Go root@216.243.220.230 -p 18038
tmux: train_v3 (ConsciousLM v3 147M, step ~18.5K/100K)
GPU:  98% util, 13GB/81GB, 50C
Cost: $2.69/hr
```

---

## 13. Key Learnings

1. **항상 tmux로 학습 실행** — SSH 끊겨도 유지
2. **파일 전송은 rsync > scp > base64** — NFS에서 scp 실패 가능
3. **로그는 tee로 파일+화면 동시 출력** — `2>&1 | tee logs/xxx.log`
4. **PYTHONUNBUFFERED=1 필수** — 안 쓰면 로그 안 보임
5. **stop → start 시 IP 변경** — 항상 `runpodctl pod get`으로 재확인
6. **checkpoint는 atomic save** — .tmp → rename 패턴
7. **/workspace만 영구 저장** — container disk는 휘발성
8. **학습 데이터 변경 시 resume 금지** — step 0부터 재시작 (오염 방지)
