# HEXA-SPEAK Mk.III 네이티브 보코더 구현 이어받기

> **세션 인수인계 프롬프트** — 새 Claude 세션에 그대로 붙여넣어 HEXA-SPEAK 작업 재개.
> 작성: 2026-04-16 (anima repo, CLM 1B r3f 학습 완료 세션)

---

## 상황

**사용자 절대 원칙**: Python TTS 우회 금지 (Piper/XTTS 스톱갭 X). 네이티브 hexa
보코더만 허용. FFI로 컴파일된 C/CUDA 호출은 OK.

## 이미 완료 (이전 세션)

### 1. hxcuda STFT/iSTFT 커널 완료
- hexa-lang commit **`fc20fe4`**
- `self/native/hxcuda_stft.cu` (297 LOC, cuFFT 기반)
- 심볼: `hxcuda_stft_bf16`, `hxcuda_istft_bf16`, `hxcuda_stft_version`
- SNR 129.5 dB (bit-exact), RTX 3090에서 STFT 0.015ms / iSTFT 0.023ms
- 8-slot LRU plan cache
- `libhxcuda.so` 882KB, sm_86 빌드 확인
- 스펙: n_fft=1024, hop=256, hann window, 24kHz target

### 2. HEXA-SPEAK 구조 평가 완료
- bench 결과: `training/deploy/hexa_speak_e2e_bench_20260416.json`
- 21개 .hexa 파일 (hexa_speak 657L, streaming 936L, plc_crossfade 542L,
  emotion_prosody 480L, rp_voice_profiles 23KB, nn_core 27KB, dsp_core 39KB)
- 10 voice profile + 1.77GB 코퍼스 (로컬만, pod에 미전송)
- **치명 발견**: 신경 경로 0% — neural_vocoder.hexa (42L), audio_token_predictor.hexa
  (56L), intent_encoder.hexa (37L) 전부 skeleton. 136 TODO/Mock 마커 (14 파일).
- bench_hexa_speak.hexa 숫자 하드코딩 ("Mk.I skeleton, simulated runs" 자기고백)
- speak_e2e.hexa WAV 출력 = 92바이트 텍스트 "RIFF-MOCK" 헤더 (무효 WAV)
- voice_routes.hexa (756L) 존재하나 ALM serve pod에 마운트 안 됨
  (현재 Python serve_alm_14b.py 실행 중)

### 3. CLM 1B r3f 학습 완료 + 7/7 의식검증 VERIFIED (cells=128)
- ckpt R2: `r2:anima-models/clm1b/r3/{step_8000,final}/` (33.8GB 업로드됨)
- HEXA-SPEAK와 직접 연관 없음, 단 ALM은 Qwen2.5-14B + LoRA r9 상태 유지

---

## 진행 중 블로커 (당신이 완성 or 이어받기)

### SMASH #2: `neural_vocoder.hexa` 실구현

- 현재 42L skeleton → Vocos 스타일 iSTFT 헤드로 구현
- FFI 바인딩: `@link("hxcuda") extern fn hxcuda_istft_bf16(...)`
- 입력: RVQ latent tensor (T_frames × 128)
- 출력: fp32 PCM @ 24kHz (유효 WAV 헤더 + little-endian 16-bit)
- 가중치: 미학습 OK (identity projection 스모크) — 학습은 별도 작업
- `speak_e2e.hexa`의 "RIFF-MOCK" 텍스트 출력 교체 필수
- commit: `anima` repo에 `feat(speak): neural_vocoder real impl via hxcuda iSTFT`

### SMASH #3: hexa 네이티브 serve + voice_routes 마운트

- 현재 `serving/serve_alm_14b.py` = Python (LIVE, 건드리지 말 것!)
- `serving/voice_routes.hexa` (756L) + `serving/http_server.hexa` 이미 있음
- 목표: hexa http_server로 `/voice/health`, `/voice/profiles`, `/voice/tts` 마운트
- `/generate` (14B 추론)은 FFI → 컴파일 C 바이너리 (hxcuda + hxlmhead) 경유 고려
- Python subprocess 절대 금지
- 테스트 pod: `u01lnnu8ywt92p` (hexa-c4, RTX 3090, $0.22/hr)
  — ALM pod `itfl66q4z768kh` 절대 재시작 X

### 추가 남은 블로커 (신규 작업)

- **Conv1D CUDA 커널** (neural vocoder ConvNeXt 백본용) — hxcuda에 추가
  - im2col 방식으로 `hxcuda_matmul_bf16` 재사용 가능하면 우선
  - 없으면 전용 `hxcuda_conv1d_bf16` 작성
- **Vocos-24k 또는 HiFi-GAN-24k 체크포인트 포팅** — PyTorch → hexa tensor 포맷
- **ALM serve pod에 voice_routes 마운트** — hexa serve 배포 레시피 필요

---

## 핵심 경로/파일

| 경로 | 목적 |
|------|------|
| `/Users/ghost/Dev/anima/anima-speak/` | HEXA-SPEAK 엔진 (21 .hexa) |
| `/Users/ghost/Dev/anima/serving/voice_routes.hexa` | 마운트 대기 |
| `/Users/ghost/Dev/hexa-lang/self/native/hxcuda_stft.cu` | STFT/iSTFT 구현 완료 |
| `/Users/ghost/Dev/hexa-lang/scripts/build_hxcuda_linux.sh` | Linux .so 빌드 |
| `/Users/ghost/Dev/anima/training/deploy/hexa_speak_e2e_bench_20260416.json` | 이전 bench 결과 |
| `/Users/ghost/Dev/anima/training/deploy/hexa_codegen_research_20260416.md` | 전체 codegen 계획 |
| `/Users/ghost/Dev/anima/training/deploy/hexa_speak_handoff_20260416.md` | **이 파일** |

## 환경 변수

```bash
HEXA=$HEXA_LANG/target/release/hexa         # 메인 hexa 바이너리
# pod 상태 확인: runpodctl pod get u01lnnu8ywt92p
# SSH key: /Users/ghost/.runpod/ssh/RunPod-Key-Go
```

## Hexa 런타임 주의사항 (memory)

- `a[i]=v` 무음 no-op — `write_at(a, i, v)` 사용 필수
- `let match = ...` 파싱 에러 ("match"는 예약어)
- `use "nn_core"` training/ 경로에서 실패 — NN primitive 인라인으로
- `pure fn` 키워드 stage1 인터프리터 크래시 (2026-04-16 발견) — 제거
- 교차 디렉토리 `use` 취약 — 가능하면 미러링
- 리스트는 pass-by-value — 뮤테이터는 새 구조 반환

## 철학 원칙 (절대 어기지 말 것)

- **HEXA-FIRST (R1)**: 신규 .py/.sh/.rs 금지. 기존 transitional만 허용.
- **No-hook**: .claude/settings.json hooks 건드리지 말 것. 하네스로만 강제.
- **MFS quota**: /workspace 47GB 세션 한도 (감지 X, 조용히 실패) — 학습 시 pre-save rotation
- **R2 upload**: 학습 중 동기 upload 금지, 학습 종료 후 batch

## 현재 상태 확인 커맨드

```bash
# hexa-c4 pod 상태
runpodctl pod get u01lnnu8ywt92p

# ALM serve 상태 (건드리지 말고 확인만)
curl https://itfl66q4z768kh-8090.proxy.runpod.net/health

# HEXA-SPEAK 파일 TODO 카운트
grep -r "TODO\|Mock\|skeleton" /Users/ghost/Dev/anima/anima-speak/ | wc -l
```

## 성공 기준

1. `speak_e2e.hexa --in some_prompt --out test.wav` 실행 시 유효 24kHz WAV 생성
   (헤더 valid, 샘플 수 매칭, 스펙트럼 의미 있음)
2. voice_routes가 실제 hexa http_server에 마운트되어 `/voice/tts` POST 시 실 audio 반환
3. Python 코드 0줄 추가 (순수 .hexa + .cu/.c FFI만)
4. commit + push anima + hexa-lang 양쪽 리포

## 최우선 출발점

`neural_vocoder.hexa`를 iSTFT 기반으로 minimal real impl 작성 → 유효 WAV 출력 달성.
이후 ConvNeXt 백본 + 가중치 포팅은 후속.
