# ubu CUDA Install — 완료 기록 (2026-04-19)

## 상태: SUCCESS (Claude 자동 설치 완료)

### 하드웨어 / 드라이버
- Host: `aiden@192.168.50.119` (ubu), Ubuntu 24.04.2 LTS noble, x86_64
- GPU: NVIDIA GeForce RTX 5070, 12.3 GB, **SM 12.0 (Blackwell)**
- Driver: 580.126.09 (CUDA 12.6+ 지원)
- Disk: 656 GB free on /
- sudo: `aiden ALL=(ALL) NOPASSWD: ALL` → 전체 자동 설치 가능했음

### 설치된 것
| 컴포넌트 | 버전 | 경로 |
|---|---|---|
| CUDA Toolkit | **12.8.1** (nvcc V12.8.93) | `/usr/local/cuda-12.8` |
| cuDNN | **9.21.0** (cudnn9-cuda-12) | `/usr/include/x86_64-linux-gnu/cudnn*.h`, `/usr/lib/x86_64-linux-gnu/libcudnn*` |
| OpenBLAS | 0.3.26 | `/usr/lib/x86_64-linux-gnu/openblas-*` |
| NVIDIA CUDA apt repo | ubuntu2404 | `cuda-keyring 1.1-1` via `developer.download.nvidia.com` |

### 설정된 환경변수 (`~/.bashrc` 에 append 완료)
```bash
export CUDA_HOME=/usr/local/cuda-12.8
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
```

### 검증 결과 (smoke test)
`/tmp/cuda_probe.cu` 컴파일 & 실행 성공:
```
CUDA devices=1 name=NVIDIA GeForce RTX 5070 SM=12.0 mem=12.3GB
cuDNN=9.21.0
```
- nvcc는 SM 12.0 binary 를 생성 가능 (Blackwell native)
- cuDNN 9.21 runtime 링크 OK
- nvcc warning: "Support for <sm_75 will be removed" — 무시 (informational)

## 새 세션에서 확인 (사용자 깨어난 뒤)
```bash
ssh ubu 'nvcc --version && echo "---" && cat /usr/include/x86_64-linux-gnu/cudnn_version.h | grep CUDNN_MAJOR -A2'
```
새 shell 이면 `~/.bashrc` 자동 source — PATH 그대로 사용 가능.

## 다음 단계 (hxcuda 포팅)
1. `cd $HEXA_LANG && ls hxcuda 2>/dev/null` — 기존 hxcuda 리소스 확인
2. ubu 에 hexa-lang clone & build:
   ```bash
   ssh ubu 'git clone <hexa-lang repo> ~/hexa-lang && cd ~/hexa-lang && make hxcuda'
   ```
3. SM 12.0 대상 nvcc 플래그: `-arch=sm_120` (또는 PTX JIT 용 `-arch=compute_120 -code=sm_120`)
4. 벤치: anima CLM 소형 모델로 inference 속도 측정 (기준: RTX 3090 COMMUNITY 대비)

## Rollback (만약 필요시)
```bash
sudo apt-get remove --purge 'cuda-*' 'cudnn*' cuda-keyring
sudo apt-get autoremove
sudo rm -rf /usr/local/cuda-12.8 /var/cuda-*
# ~/.bashrc 에서 CUDA 블록 3줄 제거
```

## 기록
- 설치 소요: ~5-6 분 (apt-get 다운로드 포함)
- Python 사용 0회 — 전 과정 apt + cu++ 만으로 완료 (R37 / AN13 / L3-PY 준수)
- `.sh` 생성 0회
- 모든 작업: `ssh ubu '<command>'` 원격 실행
