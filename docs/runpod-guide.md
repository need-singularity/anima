# RunPod H100 Training Guide

## Quick Start (오류 없이 바로 진행)

### 1. Pod 생성
```bash
runpodctl config --apiKey YOUR_KEY
runpodctl pod create --name "AnimaLM" --template-id runpod-torch-v280 --gpu-id "NVIDIA H100 80GB HBM3" --container-disk-in-gb 50 --volume-in-gb 100
```

### 2. SSH 대기 (provisioning 5-15분)
```bash
# 상태 확인 (runtime이 None이면 아직 provisioning)
runpodctl pod list -o json | python3 -c "import sys,json; [print(f'{p[\"name\"]} uptime={p.get(\"runtime\",{}).get(\"uptimeInSeconds\",0) if p.get(\"runtime\") else \"provisioning\"}') for p in json.load(sys.stdin)]"

# SSH 정보 확인
runpodctl ssh info POD_ID
```

### 3. 파일 전송 (⚠️ 중요: scp 실패 시 base64 사용)
```bash
# 방법 1: scp (workspace에 쓸 수 없을 때 실패)
scp -i ~/.runpod/ssh/RunPod-Key-Go -P PORT file root@IP:/root/

# 방법 2: base64 (scp 실패 시 확실한 방법)
base64 -i local_file.py | ssh -i ~/.runpod/ssh/RunPod-Key-Go root@IP -p PORT "base64 -d > /root/file.py"

# 전송 확인
ssh ... "wc -l /root/file.py"
```

### 4. Dependencies 설치
```bash
ssh ... "pip install transformers datasets accelerate huggingface_hub --break-system-packages -q"
```

### 5. 학습 실행 (⚠️ 로그 경로 = /tmp)
```bash
# /workspace에 로그 쓰기 실패할 수 있음 → /tmp 사용
ssh ... "cd /root && PYTHONUNBUFFERED=1 python script.py > /tmp/train.log 2>&1 & echo PID=\$!"
```

### 6. 모니터링
```bash
# 로그
ssh ... "tail -10 /tmp/train.log"

# GPU 상태
ssh ... "nvidia-smi | grep -E 'MiB|Util'"

# 프로세스 확인
ssh ... "ps aux | grep python | grep -v grep"
```

### 7. 결과 다운로드
```bash
scp -i ~/.runpod/ssh/RunPod-Key-Go -P PORT root@IP:/workspace/checkpoints/final.pt ~/Dev/models/
# 또는
ssh ... "cat /workspace/checkpoints/final.pt" > ~/Dev/models/final.pt
```

### 8. Pod 정지
```bash
runpodctl pod stop POD_ID
# 또는 삭제
runpodctl pod remove POD_ID
```

---

## Troubleshooting

### scp 실패: "close remote: Failure"
- **원인**: /workspace가 NFS 마운트라 scp write가 실패할 수 있음
- **해결**: `/root/`에 쓰거나, base64 파이프로 전송
```bash
base64 -i file.py | ssh ... "base64 -d > /root/file.py"
```

### nohup 로그가 0줄
- **원인**: /workspace에 쓰기 실패 + Python output buffering
- **해결**:
  1. 로그를 `/tmp/`에 쓰기
  2. `PYTHONUNBUFFERED=1` 환경변수 설정
  3. `python -u` 플래그 사용

### pip install 실패: PEP 668
- **원인**: Ubuntu 24.04에서 system Python 보호
- **해결**: `--break-system-packages` 플래그 추가

### SSH exit code 255
- **원인**: 원격 명령에서 pkill/kill이 대상을 못 찾으면 exit 1 → SSH가 255 반환
- **해결**: `kill ... 2>/dev/null; echo done` 패턴 사용 (항상 echo로 종료)

### torch.save 실패: "unexpected pos" on /workspace
- **원인**: /workspace가 NFS (mfs) 마운트라 large file write가 불안정
- **해결**: checkpoint를 `/tmp/`에 저장 후 나중에 scp/cat으로 다운로드
```python
# Bad
torch.save(state, "/workspace/checkpoints/model.pt")
# Good
torch.save(state, "/tmp/checkpoints/model.pt")
```

### base64 전송 시 0줄 파일
- **원인**: macOS `base64 -i`와 `openssl base64` 모두 파이프에서 간헐적 실패
- **해결**: Python base64 사용 (가장 안정적)
```bash
python3 -c "
import base64, sys
with open('file.py', 'rb') as f:
    sys.stdout.buffer.write(base64.b64encode(f.read()))
" | ssh ... "base64 -d > /root/file.py"
```

### torch.save 크래시: "unexpected pos" (대용량 파일)
- **원인**: 22GB+ checkpoint → torch zipfile writer 불안정
- **해결**: trainable params만 저장 (LoRA delta only)
```python
# Bad: 전체 state dict (22GB)
states = {n: m.state_dict() for n, m in model.named_modules()}
# Good: delta만 저장 (~0.5GB)
states = {n: {k: v for k, v in m.state_dict().items() if "delta" in k or k == "scale"} for n, m in model.named_modules()}
```

### CUDA OOM
- **원인**: Mistral 7B bf16(~15GB) + PureFieldMLP(2x MLP ~15GB) + optimizer state + activations
- **해결**:
  1. LoRA-style delta (rank 64) → trainable 0.87%
  2. gradient_checkpointing_enable()
  3. batch_size=1, grad_accum=16
  4. block_size 256 (512 대신)
  5. 8-bit Adam (bitsandbytes)

### `total_mem` AttributeError
- **원인**: PyTorch 2.8에서 API 변경
- **해결**: `torch.cuda.get_device_properties(0).total_memory` (total_mem → total_memory)

### `torch_dtype` deprecated 경고
- **원인**: transformers 최신 버전에서 `dtype` 사용 권장
- **해결**: 무시해도 됨 (작동함)

### Tuple unpacking 오류 ("tuple has no attribute dtype")
- **원인**: Mistral decoder layer forward가 tuple 반환 → 다음 레이어에서 unpacking 안 됨
- **해결**: MLP 교체 시 tuple 반환하지 말고 tensor만 반환. Tension은 `self.last_tension` attribute로 저장.

### DataLoader shuffle 멈춤
- **원인**: 50M 항목 shuffle에 수분~수십분 소요
- **해결**: `RandomSampler(replacement=True, num_samples=N)` 사용

### Gradient checkpointing 첫 step 느림
- **원인**: 12.9B 모델의 첫 forward+backward + CUDA graph compilation
- **해결**: 정상임. 첫 step에 5-10분 걸릴 수 있음. GPU util 확인해서 진행 중이면 대기.

---

## Memory Budget (H100 80GB)

| Component | Size |
|-----------|------|
| Mistral 7B bf16 | ~15 GB |
| PureFieldMLP (full Engine G) | ~15 GB |
| LoRA delta (rank 64) | ~0.4 GB |
| Adam state (full G) | ~30 GB → OOM |
| Adam state (delta only) | ~0.8 GB ✅ |
| Activations (batch=1, seq=256) | ~5 GB |
| Grad checkpointing savings | -10 GB |
| **Total (LoRA approach)** | **~36 GB ✅** |

## Key Learnings
1. **항상 tensor만 반환** — custom MLP는 tuple 반환 금지
2. **LoRA-style delta가 핵심** — full Engine G 학습은 OOM
3. **파일 전송은 base64** — scp가 NFS에서 실패
4. **로그는 /tmp** — /workspace 쓰기 불안정
5. **PYTHONUNBUFFERED=1 필수** — 안 쓰면 로그 안 보임
6. **RandomSampler** — 대규모 데이터에서 shuffle 대체
