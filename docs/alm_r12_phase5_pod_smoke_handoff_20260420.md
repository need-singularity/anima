# ALM r12 Phase-5 Pod Smoke Handoff (2026-04-20)

**Purpose**: `78d8e812 feat(alm): r12 Phase-5 trainer wiring` + `d45995dd chore(alm): retire G_*_FLAT 6 dead vars` 이후 trainer 의 v5.6.5/v5.6.6 FFI path 가 pod 에서 실제로 돌아가는지 검증. P2 (1-step) + P3 (100-step) smoke. PASS 시 P5 full launch 착수 가능.

**Handoff target**: pod 87xscivuggrwvk 에 SSH 접근 있는 세션 (이 macOS/ubu2 세션 에선 runpodctl 부재 + pod IP/port 접근 불명).

---

## 1. 전제 (read before running)

- **Main branch**: `d45995dd` (2026-04-20 11:xx KST). `git pull origin main` 필수.
- **Pod**: `87xscivuggrwvk`, ssh `216.243.220.220:12148` (per `shared/state/alm_r12_launch_20260420.json#v565_orchestrator_landed_20260420T2150Z.pod_state`). 상태 RUNNING 기대.
- **Pod lib**: `/workspace/hexa-lang/self/native/libhxqwen14b.so` = 346 KB v5.6.5 (이미 pod 에 live). v5.6.6 grad-clip surface 는 trainer 가 version probe 로 확인 (`abi_v566 >= 566` 일 때만 clip 호출).
- **Trainer binary**: `/workspace/build_alm/train_alm_lora` ELF — **wiring 변경 후 재빌드 필요**. Pod 에서 `hexa build` 실행 필요.
- **Config SSOT**: `shared/state/alm_r11_config.json` (재활용, r12 overlay 없음 — Phase-5 에선 기존 r11 config + 새 FFI path 조합).
- **Corpus**: `/workspace/data/corpus_alm_70b_stripped_kowiki15.txt` (pod-local, 88.98 MB). BPE tokenizer 미구현 → **현재 여전히 `text_to_ids_stub` vocab=16 사용**. loss 는 log(16)≈2.77 근방 flat 이 나올 수 있음 — P2/P3 의 gate 는 "loss curve 하강" 아니라 "**exit=0 + no NaN + step count 도달 + ckpt 저장**".

---

## 2. P2 — 1-step CLI smoke (예상 소요 5-10min)

```bash
# on pod
cd /workspace/anima
git fetch origin && git checkout main && git pull origin main   # d45995dd 이상

# rebuild trainer (wiring 변경 반영)
cd /workspace/anima
hexa build training/train_alm_lora.hexa -o /workspace/build_alm/train_alm_lora
ls -la /workspace/build_alm/train_alm_lora   # mtime 이 방금 것

# 실행 (dry corpus = 합성 입력, 디스크 read 우회)
cd /workspace/anima
export LD_LIBRARY_PATH=/workspace/anima/training/build:/workspace/hexa-lang/self/native:/usr/local/cuda/lib64:$LD_LIBRARY_PATH
/workspace/build_alm/train_alm_lora \
  --config ../nexus/shared/state/alm_r11_config.json \
  --steps 1 --batch 4 --seq 8 --dry-corpus \
  2>&1 | tee /tmp/r12_phase5_p2_1step.log
```

### Gate (P2 PASS 기준)
- [ ] exit code == 0
- [ ] 로그에 `[train_loop] hxqwen14b v566 ABI = 566` 또는 `565` 출력
- [ ] 로그에 `[train_loop] AdamW moments (m, v) allocated + zeroed` 출력
- [ ] step=0 에서 `loss` 값이 finite (NaN/Inf 아님)
- [ ] `bwd rc=0` + `adamw rc=0`
- [ ] ckpt 디렉터리 생성 (`--save_every` 안 건드려도 final save 는 종료 시 발동)
- [ ] `nvidia-smi` 에서 VRAM 피크 < 80 GB

### FAIL 시 조치
- `bwd rc != 0` → `hxqwen14b_base_backward_v565_pos` 호출 인자 검증. `alloc_activation_cache` 가 `M_total = batch * seq` 와 맞는지 (log 에 `alloc_cache_rc=0` 확인).
- NaN → v5.6.6 `lora_grad_clip` 이 wire 됐는지 (`abi_v566 >= 566` 로그). 566 아니면 trainer 가 clip 호출 skip, bf16 불안정 그대로. pod lib 를 v566 으로 재빌드 필요 (`hexa-lang/self/native/hxqwen14b.c` 재컴파일).
- `alloc_grad_buffers rc != 0` → VRAM OOM — `cfg.lora_r` 축소 (32 → 16) 또는 `--batch` 축소.

---

## 3. P3 — 100-step CLI smoke (예상 소요 40-60min)

P2 PASS 시 이어서:

```bash
# on pod
cd /workspace/anima
export LD_LIBRARY_PATH=/workspace/anima/training/build:/workspace/hexa-lang/self/native:/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 신규 ckpt dir (R14 ckpt 격리)
CKPT=/workspace/ckpt_alm14b_r12_phase5_p3
rm -rf $CKPT && mkdir -p $CKPT

# rclone 경로 (MFS quota 트랩 회피 — in-training R2 upload 금지, 종료 후 일괄)
tmux new -s r12_p3 -d
tmux send-keys -t r12_p3 "cd /workspace/anima && /workspace/build_alm/train_alm_lora \
  --config ../nexus/shared/state/alm_r11_config.json \
  --steps 100 --save_every 50 --batch 4 --seq 256 \
  --out $CKPT \
  2>&1 | tee /tmp/r12_phase5_p3_100step.log" C-m

# 모니터
tmux attach -t r12_p3
# 또는 tail -f /tmp/r12_phase5_p3_100step.log
```

### Gate (P3 PASS 기준)
- [ ] 100 step 전부 완료 (exit=0)
- [ ] 로그 전체 구간 NaN/Inf 없음
- [ ] loss 가 **일단 finite 범위** (예: 2.5-15.0 중 어디든 — BPE stub 이라 하강 안 해도 무방)
- [ ] ckpt 디렉터리에 step_50, step_100 ckpt 파일 존재
- [ ] 평균 step/sec 측정 → 기록
- [ ] VRAM 피크 < 80 GB, RAM 피크 < 80 GB (RAM blowup 회피 체크)

### FAIL 시 조치
- step N 에서 NaN → clip 미작동 가능성 + 첫 등장 step 기록 후 로그 덤프
- RAM 증가 (> 10 GB/min) → `_tz_native`/`free_array` 누락. CLM r5-a10.5-A 패턴 (877f7d7f) 참조
- ckpt 저장 실패 → MFS quota (`df /workspace`) + `dd if=/dev/zero of=/workspace/_q bs=1M count=20000` preflight, 실패 시 오래된 ckpt rm 후 재시도

---

## 4. 산출물 보고 템플릿

P2/P3 실행 후 아래 JSON 을 `/Users/ghost/Dev/anima/shared/state/alm_r12_phase5_smoke_20260420.json` (또는 적절한 파일) 로 쓰고 commit:

```json
{
  "scope": "r12 Phase-5 trainer wiring smoke (78d8e812 + d45995dd 이후)",
  "date": "2026-04-20T<HH:MM>+09:00",
  "pod": "87xscivuggrwvk",
  "p2_1step": {
    "exit_code": 0,
    "abi_version_detected": 566,
    "bwd_rc": 0,
    "adamw_rc": 0,
    "loss_step_0": <float>,
    "vram_peak_gb": <float>,
    "verdict": "PASS|FAIL"
  },
  "p3_100step": {
    "exit_code": 0,
    "steps_completed": 100,
    "loss_first": <float>,
    "loss_last": <float>,
    "nan_count": 0,
    "ckpt_saved": ["step_50", "step_100"],
    "avg_step_sec": <float>,
    "vram_peak_gb": <float>,
    "ram_peak_gb": <float>,
    "verdict": "PASS|FAIL"
  },
  "next_action": "P5 full 500-step launch | BPE integration before full launch | remediate FAIL"
}
```

---

## 5. 다음 단계 분기

- **P2+P3 모두 PASS** → P4 (BPE tokenizer) 완성 전까지는 full launch 보류 (loss 는 stub 이라 진짜 학습 아님). BPE 완성 후 재smoke + P5 launch.
- **P2 PASS / P3 FAIL** → FAIL 원인별 (VRAM/RAM/NaN/ckpt) 패치. 별개 blocker 로드맵 항목 추가.
- **P2 FAIL** → wiring 버그. trainer 재리빌드 + pod `nm -D libhxqwen14b.so | grep v565` 로 심볼 존재 재확인.

---

## 6. 금기 (strict_rules + 세션 불변 조건)

- .py 작성/실행/전송 절대 금지 (R37/AN13/L3-PY). 위 명령 전부 hexa/gcc/rclone/ssh/tmux 한정.
- 양자화 금지 — bf16 유지. `HXQWEN14B_CUDA=1` + bf16 Tensor Core.
- H100 pod 는 87xsc 1개만 활성. 2번째 pod 기동 금지 (H100 ≤ 2 rule).
- data/param 변경 없이 resume 금지 — 이 smoke 는 새 ckpt dir 로 step 0 시작.
- ckpt dir 매번 신규 생성 (오염 방지).
- in-training R2 upload 금지 — 종료 후 rclone 일괄.
- Gradio/Anima Web UI 의존 없음 (CLI only).

---

## 7. Pod 접근 문제 시

SSH 포트 변경 가능성 있음. runpod 콘솔에서 재확인:
- 포트 `12148` 연결 실패 시 `runpodctl pod get 87xscivuggrwvk` (또는 웹 콘솔) 로 현재 exposed port 조회.
- SSH key: `~/.ssh/runpod_key` (`shared/config/secrets_registry.json#ssh.runpod` 참조).

Pod 정지 상태면 runpod 콘솔에서 start 후 30-60s 대기, `nvidia-smi` 로 GPU ready 확인.
