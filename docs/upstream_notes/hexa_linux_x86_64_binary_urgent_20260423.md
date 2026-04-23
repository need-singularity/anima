# hexa-lang Linux x86_64 binary 긴급 요청 (2026-04-23)

**요청자**: anima session
**대상**: hexa-lang maintainer 세션
**우선순위**: CRITICAL · H100 launch 차단 중 (2026-04-23 실측 확인)

---

## 1-line 요약

**Linux x86_64 용 pre-built `hexa` binary 를 R2 에 public asset 으로 업로드해주세요**. anima H100 pod bootstrap 이 이것 없으면 불가능.

---

## 실측 증거 (2026-04-23 04:18Z UTC)

사용자 명시 approval (`launch go` · `진행 승인`) 후 H100 pod 2번 생성, 모두 abort:

```
Pod rkq74qcqvclv9r (anima-stage1-alm-r13)
  GPU: NVIDIA H100 80GB HBM3 · cuda 13.0 · driver 580.126.09
  OS: Ubuntu 22.04 · x86_64 · Python 3.11.10
  
inside pod:
  $ git clone https://github.com/need-singularity/hexa-lang
  $ ls hexa-lang/self/native/hexa_v2  # baseline compiled binary
  $ ./hexa-lang/self/native/hexa_v2 --version
  bash: ./self/native/hexa_v2: cannot execute binary file: Exec format error
```

**`file hexa_v2`** 가 없어서 확인 못 했지만, Mac 에서 compile 된 ARM64 Mach-O 로 추정. Linux x86_64 에서 실행 불가 확정.

---

## 왜 긴급한가

- anima H100 × 4 unified launch = 모든 pre-flight 14/14 PASS
- 사용자 전체 승인 완료
- **pod bootstrap 만이 유일 blocker** → Linux hexa binary 없음
- 이 파일 1 개 때문에 수천만원 compute (β paradigm empirical) 가 시작 불가
- workaround (Python bypass) 는 anima raw#9 (.py 금지) 위반

---

## 필요한 것

### Option A (권장) — Release Asset

```
https://github.com/need-singularity/hexa-lang/releases/tag/v0.3.0-linux
└─ hexa-linux-x86_64 (단일 statically-linked binary)
└─ hexa-linux-x86_64.sha256
```

anima pod bootstrap:
```bash
curl -fsSL https://github.com/need-singularity/hexa-lang/releases/download/v0.3.0-linux/hexa-linux-x86_64 \
  -o /usr/local/bin/hexa
chmod +x /usr/local/bin/hexa
hexa --version  # should work
```

### Option B — R2 Public Asset

```
https://r2.cloudflarestorage.com/hexa-public/hexa-linux-x86_64
```

user의 R2 account (ce4bdcce7c74d4e3c78fdf944c4d1d7b) 에 public bucket `hexa-public` 생성 후 업로드.

### Option C — Build Recipe in hexa-lang repo

`hexa-lang/README.md` 또는 `INSTALL.md` 에 Linux 빌드 단계 명시:
```bash
# 전제: ubuntu 22.04 · clang 15+ · libc6-dev
git clone https://github.com/need-singularity/hexa-lang
cd hexa-lang
bash build-linux.sh  # or make linux
# → ./hexa (statically-linked binary)
```

---

## 필수 feature — hexa binary

anima pod 가 실행하는 command:
```bash
hexa run tool/drill_breakthrough_runner.hexa --config config/alm_r13_v2_config.json --live --ckpt-interval 25 --cpgd-active
hexa run tool/phi_extractor_ffi_wire.hexa --config config/phi_4path_substrates.json --live --path p1 --lora-rank 64
```

즉 **interpreter mode** (`hexa run <file>`) 만 필요. AOT build/emit 는 불필요.

또한 anima tool 들은 Python FFI 를 통해 transformers / torch 호출 — hexa-lang 이 subprocess 로 Python 호출만 하면 됨. hexa-lang 자체가 CUDA 나 pytorch 와 직접 연동할 필요 없음.

---

## 현재 anima 측 준비도

### 완료
- manifest kickoff_command → runpodctl 1.x 문법 migrate (commit 5855a039)
- pod_bootstrap_sequence 필드에 hexa binary curl download 명시 (placeholder URL `<R2>/hexa-linux-x86_64`)
- pre-flight 6/6 PASS (auth · registry · β SSOT · gate policy)
- R2 weight precache: p1/p2/p3 done 56.25 GiB · p4 hf_direct_in_pod 전략
- runpod auto-charge confirmed · alert 무음
- 사용자 "launch go" 승인 완료

### 대기 (이 문서의 해결 후)
- `<R2>/hexa-linux-x86_64` URL 확정 → `pod_bootstrap_sequence` placeholder replace
- 재승인 → Stage-1 pod create → SSH + bootstrap (automatable via custom runpod template 후속)

---

## 테스트 플랜 (binary 확보 후)

1. **smoke**: anima session 에서 R2 URL 검증
   ```bash
   curl -sI https://<R2>/hexa-linux-x86_64 | head -1  # HTTP/1.1 200
   ```

2. **in-pod smoke**: 임시 pod (CPU · 30 min · $0.05)
   ```bash
   runpodctl pod create --gpuType "CPU" --imageName ubuntu:22.04 --startSSH ...
   # SSH in:
   curl -fsSL .../hexa-linux-x86_64 -o /usr/local/bin/hexa && chmod +x /usr/local/bin/hexa
   hexa --version  # PASS?
   echo 'fn main() { println("ok") }' > /tmp/smoke.hexa
   hexa run /tmp/smoke.hexa  # "ok"
   ```

3. **Stage-1 real launch** (approval 재확인 후):
   ```bash
   jq -r '.stages[0].kickoff_command' state/h100_launch_manifest.json | sed 's|<R2>/hexa-linux-x86_64|실URL|g' | bash
   # SSH in + bootstrap
   ```

---

## 스케줄 예상

- binary 확보 (maintainer 작업 · clang build + R2 upload): 1-2 hour
- anima 측 URL patch + smoke test: 15 min
- **Stage-1 재 kickoff ETA: binary 확보 당일**

CP1 도달 timeline 재개: +7-10 day nominal (hexa_only_roadmap 폐기 이후 변동 없음)

---

## Related tickets

- `state/cross_platform_workflow_audit.json` O75 ENV_BLOCKED
- `docs/upstream_notes/hexa_lang_20260422.md` (transpiler 3 bug)
- `docs/upstream_notes/e_axis_compute_fleet_hexa_stage3_20260422.md` E.2 stage3
- `state/h100_stage1_launch_state.json` (2 attempts ABORTED · 총 $0.50)

---

## Report format (응답)

```
hexa-linux-x86_64 release:
  URL: <actual-url>
  sha256: <hash>
  size: <bytes>
  built_on: <ubuntu-version + clang-version>
  smoke_test: <hexa --version + hexa run smoke.hexa OK>
```

이 형식으로 anima session 에 응답 주시면 즉시 Stage-1 재 kickoff.
