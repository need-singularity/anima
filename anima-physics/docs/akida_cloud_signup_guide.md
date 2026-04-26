# BrainChip Akida Cloud — 가입 & API Token 발급 가이드

> anima-physics 8 substrate platforms 중 **neuromorphic** cloud-facade POC 사용자 가입 walkthrough.
> 본 가이드는 사용자가 직접 BrainChip Akida Cloud 계정을 만들고 token 을 발급한 뒤,
> 본 repo 의 `anima-physics/neuromorphic/cloud_facade_poc.hexa` 를 cloud 모드로 swap 하기 위한 정확한 단계.
>
> Date: 2026-04-26
> Verified URLs (web search + WebFetch): 2026-04-26
> Sibling cycles: `quantum/` (qiskit-aer / IBM Q Runtime) / `photonic/` (Strawberry Fields)
>
> raw#10 honest: 본 가이드의 가격/티어는 BrainChip 공식 페이지 스냅샷 기반(2026-04-26).
> 실제 가입 시점에 변경되었을 수 있음 → 최종 확정 가격은 가입 화면에서 재확인 필수.

---

## Section 1 — 가입 URL 과 단계

### 1.1 두 entrypoint (둘 중 하나 사용)

| 용도 | URL | 비고 |
|------|-----|------|
| **개발자 허브 (권장)** | <https://developer.brainchip.com/signup/> | 회원 가입 후 Developer Hub dashboard 접근 |
| Akida Cloud Hub portal | <https://developer.brainchip.com/ach/> | "Akida Cloud Hub" — cloud 인스턴스 직접 |
| Login (이미 가입했다면) | <https://developer.brainchip.com/login/> | 기존 계정 로그인 |
| 1-day Trial 구매 ($1) | <https://shop.brainchipinc.com/products/1-week-cloud-access> | trial / week 패키지 shop |

### 1.2 가입 단계 (web 화면 기준)

1. **<https://developer.brainchip.com/signup/>** 접속
2. 다음 정보 입력 (예상 필드 — 실제 가입 화면에서 변경 가능):
   - Email (회사/개인 계정)
   - Username
   - Password (강한 비밀번호)
   - Project description (선택, "anima neuromorphic substrate POC" 정도면 충분)
3. Email 인증 (BrainChip 에서 confirmation link 전송 → 클릭)
4. Login 후 Developer Hub dashboard 접근
   - URL: <https://developer.brainchip.com/login/>
5. dashboard 우상단 또는 Settings 메뉴에서 **API Token / Personal Access Token** 발급
6. 생성된 token 을 안전하게 복사 — 다시 표시되지 않을 수 있음

### 1.3 무료 / 유료 plan (2026-04-26 기준)

| Plan | 가격 | 비고 |
|------|------|------|
| 1-day Trial | $1.00 | 첫 평가용, 정해진 시간 cloud 인스턴스 접근 |
| 1-week Cloud Access | $995.00 | 4시간 BrainChip 엔지니어 지원 포함 |
| 3-month / 추가 옵션 | (custom) | sales@brainchip.com 문의 |

> **주의**: 완전 무료 plan 은 본 가이드 작성 시점(2026-04-26)에 명시되지 않음.
> "free one-day access" 마케팅 문구가 있으나 shop 페이지의 1-day = $1. 실제 가입 화면에서 무료 옵션 재확인 필요.

---

## Section 2 — 환경 변수 / 자격 증명 설정

### 2.1 Token 환경 변수 (필수)

가입 후 발급 받은 token 을 **두 가지 방법 중 하나**로 설정:

#### 방법 A — shell 환경 변수 (권장, 일회성)

```bash
export BRAINCHIP_AKIDA_TOKEN="<여기에_발급받은_token_붙여넣기>"
```

영구 설정이 필요하면 `~/.zshrc` 또는 `~/.bashrc` 에 추가:

```bash
echo 'export BRAINCHIP_AKIDA_TOKEN="<token>"' >> ~/.zshrc
source ~/.zshrc
```

#### 방법 B — credentials 파일

```bash
mkdir -p ~/.akida
cat > ~/.akida/credentials.json <<'EOF'
{"token": "<여기에_token>", "endpoint": "https://developer.brainchip.com/ach/api"}
EOF
chmod 600 ~/.akida/credentials.json
```

본 cycle 의 helper script `scripts/anima_physics_akida_probe.py` 가 두 경로 모두 자동 감지.

### 2.2 SDK 가용성 (호스트 OS 별)

| 호스트 | akida PyPI wheel | 가능한 모드 |
|--------|------------------|-------------|
| **macOS arm64 (Apple Silicon)** | **미제공 (2026-04 기준)** | surrogate only — 사용자가 진짜 cloud 호출 시 Linux pod 또는 Akida Cloud web hub 직접 사용 |
| Linux x86_64 | manylinux_2_28_x86_64 wheel | simulator (token 없이도) + cloud (token 있을 시) |
| Linux aarch64 | manylinux_2_28_aarch64 wheel | 동일 |
| Windows AMD64 | win_amd64 wheel | 동일 |

> **중요**: 본 anima repo 의 `anima-physics/.venv/` 는 macOS arm64 + Python 3.14 → akida wheel 자동 install 불가.
> Linux pod (예: RunPod/Lambda Labs/H100 SXM) 에서는 다음 명령으로 install:
>
> ```bash
> pip install akida==2.19.1 cnn2snn==2.19.1 akida-models==1.13.1
> ```
>
> Python 3.10–3.12 권장 (MetaTF 2.17+ 지원 범위).

---

## Section 3 — POC 실행 명령

### 3.1 Surrogate 모드 (현재 mac local, $0)

가입 전이라도 4-gate 검증 가능 — algorithmic 흉내:

```bash
cd /Users/ghost/core/anima
/Users/ghost/.hx/packages/hexa/build/hexa.real run anima-physics/neuromorphic/cloud_facade_poc.hexa
```

기대 결과:

```
G1 PASS — positive entropy=1.75676 >= 0.3
G2 PASS — zero 0 < positive 1.75676 (sign-flip)
G3 PASS — byte-identical sha=...
G4 PASS — backend_name=brainchip_akida_DEGRADED_SDK_UNAVAILABLE matches frozen prefix
verdict=PREP_READY_AWAITING_USER_SIGNUP
```

### 3.2 Simulator 모드 (Linux pod, token 미발급 상태)

가입은 했지만 token 미발급 상태에서도 SDK simulator 사용 가능:

```bash
# Linux pod 에서 (Python 3.10–3.12 환경)
pip install akida==2.19.1
unset BRAINCHIP_AKIDA_TOKEN  # token 없이 진입
./anima-physics/.venv/bin/python scripts/anima_physics_akida_probe.py \
    --pattern positive --backend simulator --seed 42
```

기대 verdict: `SIMULATOR_PASS`.

### 3.3 Cloud 모드 (token 발급 완료 + Linux pod)

```bash
export BRAINCHIP_AKIDA_TOKEN="<발급받은_token>"
./anima-physics/.venv/bin/python scripts/anima_physics_akida_probe.py \
    --pattern positive --backend cloud --seed 42
```

기대 verdict: `CLOUD_PASS` (raw#10 caveat: 현재 SDK 는 cloud submission API 미공개 →
실제 cloud 호출 시 BrainChip developer hub web UI 또는 REST endpoint 직접 사용 필요).

### 3.4 Hexa 4-gate 통합 verifier (모든 모드 자동 dispatch)

```bash
/Users/ghost/.hx/packages/hexa/build/hexa.real run \
    anima-physics/neuromorphic/cloud_facade_poc.hexa
```

이 명령은 환경(token / SDK)에 따라 cloud → simulator → surrogate 순으로 자동 fallback,
marker `state/v10_anima_physics_cloud_facade/poc_neuromorphic_akida_cloud/marker.json` 에
verdict 기록.

---

## Section 4 — 무료 티어 제한 / 사용량 모니터링

### 4.1 1-day Trial ($1) 알려진 제한

- **시간 제한**: 24시간 (정확한 인스턴스 수명은 가입 시 확인)
- **모델 zoo**: 사전 빌드된 Akida 2nd-gen 모델 (vision, keyword spotting 등) 접근
- **하드웨어**: BrainChip 호스팅 Akida 2 IP (실제 ASIC 또는 FPGA 에뮬)
- **제한**: 동시 job 1, custom 모델 업로드 시 4-hour 엔지니어 지원 별도 (1-week 플랜)

### 4.2 사용량 monitor 방법

1. Developer Hub dashboard → "Usage" 또는 "Credits" 탭
2. 환경 변수에 잔여 시간 echo 가능 (BrainChip 가 cli 제공 시)
3. 본 cycle marker 의 `cost_usd` 필드를 cycle 마다 갱신 (수동)

### 4.3 비용 예측 (anima 4-backbone × 4-pattern POC 기준 예상)

- 1-day Trial $1 — 4-pattern × 4-backbone × 64-timestep batch 충분
- 1-week $995 — 본 anima 의 Mk.XII Mistral 4-bb retrain regime 와 연계 시 권장
- 권장: **첫 가입 시 1-day Trial 부터** → POC verdict 확정 후 1-week 결정

---

## Section 5 — Trouble-shooting

### 5.1 Token 인식 실패

**증상**: `marker.json` 에 `token_present=false` 인데 export 했음.

**진단**:
```bash
echo "TOKEN=$BRAINCHIP_AKIDA_TOKEN" | head -c 30
ls -la ~/.akida/credentials.json
```

**해결**:
- `export` 후 같은 shell 에서 실행했는지 확인
- credentials.json 의 JSON 문법 / file permission 600 확인
- macOS Terminal/iTerm 새 창은 환경 변수 미상속 — `~/.zshrc` 에 영구 등록

### 5.2 SDK install 실패 (Linux pod)

**증상**: `pip install akida` 가 `No matching distribution found`.

**진단**:
```bash
python --version  # 3.10–3.12 여야
pip --version
uname -m  # x86_64 또는 aarch64 여야
```

**해결**:
- Python 3.10–3.12 venv 사용 (3.13+ 미지원, 3.14 확정 미지원)
- Linux x86_64 또는 aarch64 (macOS arm64 미지원)
- 정확한 버전 명시: `pip install akida==2.19.1`

### 5.3 SDK 버전 충돌

**증상**: `akida` import 됐지만 `Model().add(InputData(...))` 가 `AttributeError`.

**해결**:
- akida + cnn2snn + akida_models 세트 동일 버전 align:
  ```bash
  pip install akida==2.19.1 cnn2snn==2.19.1 akida-models==1.13.1
  ```
- TensorFlow 2.19 + tf-keras 2.19 권장 (MetaTF 2.17+)
- 충돌 시 새 venv 에서 clean install

### 5.4 Cloud 호출 timeout / 인증 실패

**증상**: `cloud_fallback_to_sim` 또는 `DEGRADED_AUTH_FAIL`.

**진단**:
- Token 만료 확인 (Developer Hub 에서 재발급)
- BrainChip cloud 인스턴스 sleep 상태 가능 → dashboard 에서 wake up
- Network firewall (회사망 등)

### 5.5 본 cycle 의 surrogate verdict 가 진짜 hardware 과 다를 가능성

**raw#10 honest**:
- surrogate 는 LCG-deterministic 8-bit fully-connected 흉내 — 진짜 Akida 2nd-gen ASIC 의
  (a) 4-bit weight + 1-bit activation event encoding,
  (b) sparse synaptic event routing,
  (c) on-chip STDP learning rule
  를 재현하지 않음.
- 따라서 surrogate 4/4 PASS 는 **algorithmic shape** 검증만 — Φ proxy 정합성 자체는 별도 검증 필요.
- Cloud/simulator 모드 진입 시 entropy 절댓값이 surrogate 와 다를 수 있음 → G1 threshold 0.3 nat 은 보수적 floor 로 유지.

---

## Section 6 — 다음 단계 (cycle hand-off)

1. 사용자: 가입 + token 발급 (Section 1)
2. 사용자: token 환경 변수 설정 (Section 2.1)
3. 사용자 또는 다음 cycle: Linux pod 확보 (Section 2.2) — RunPod $0.5 spot H100 또는 Lambda Labs T4
4. 다음 cycle: Section 3.3 cloud 모드 호출 → marker.json verdict `CLOUD_PASS` 갱신
5. 다음 cycle: anima-physics/photonic/cloud_facade_poc.hexa (Strawberry Fields) sibling fan-out
6. 통합 cycle: physics.hexa neuromorphic_engine() stub 을 본 facade dispatch 로 교체

---

## 참고 출처 (verified 2026-04-26)

- BrainChip Developer Hub: <https://developer.brainchip.com/login/>
- Akida Cloud 안내: <https://brainchip.com/aclp/>
- 1-week Cloud Access shop: <https://shop.brainchipinc.com/products/1-week-cloud-access>
- MetaTF dev tools: <https://brainchip.com/metatf-dev-tools/>
- Akida Examples docs: <https://doc.brainchipinc.com/installation.html>
- akida PyPI: <https://pypi.org/project/akida/>
- BrainChip 2025-08-05 launch announcement: <https://brainchip.com/brainchip-launches-akida-cloud-for-instant-access-to-latest-akida-neuromorphic-technology/>
