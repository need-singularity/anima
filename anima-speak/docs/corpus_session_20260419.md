# Korean TTS Corpus 세션 — 2026-04-19 (야간 자율)

상태: **진행중** (세션 시작 02:42 KST, 현재 04:18+)
이전 세션 아티팩트: `quality_audit_20260419.md`, `improvement_plan_20260419.md`
상위 로드맵: `shared/roadmaps/hexa-speak.json` P4 δ1-audio 트랙

## 1. 세션 목표

이전 세션 말미 사용자 지시:
> "실제 모델이랑 + podcast 나 유튜브 mp3 활용해서 교육시킬까"

결정: δ 트랙 + δ1-audio (YouTube/whisper 코퍼스 파이프라인) 완성.
`piper` G2P mismatch 문제로 생성된 gibberish 샘플은 보류 (`BROKEN_WARNING.md`),
실제 Korean 음성 코퍼스 수집 → (text, wav) 페어 데이터셋 빌드로 전환.

## 2. 도구 빌드 (03:43 ~ 03:52)

- `yt-dlp` 2026.03.17 standalone binary → `/home/aiden/bin/tts_tools/yt-dlp` (R37 회색지대, 사용자 허가)
- `whisper.cpp` build + `ggml-large-v3-turbo.bin` 1623 MB CPU
  - NOTE: `whisper_backend_init_gpu: no GPU found` — CUDA 빌드 아님, CPU only
- `ffmpeg`, `jq`, `sox` 기존 설치 활용

## 3. 코퍼스 다운로드

`training/corpus_yt_ko/` (mac NFS 마운트):

| id | 길이 | 48kHz stereo wav | 상태 |
|---|---|---|---|
| 9KqAsKF4WDQ | 22:13 | 244 MB | 다운로드 ✅ |
| BQj8vZh_2as | 47:07 | 517 MB | 다운로드 ✅ |
| lQnzlQgsjj4 | 48:29 | 532 MB | 다운로드 ✅ |

합계 **117분 45초 (1.96h)**, 1.29 GB.

중복 감지: `ko_audiobook_16k.wav` (42 MB, 16kHz mono) 는 `9KqAsKF4WDQ` 의 리샘플본.
글롭에서 제외하기 위해 `dupe_16k_of_9KqAsKF4WDQ.wav` 로 리네임.

## 4. 전사 (Whisper)

첫 시도 (02:42 세션 말미): 3분 테스트 샘플 `sample_3min_test.wav` 전사 성공.
- RTF ≈ 0.63 (CPU, 12 thread, 5 beam + best of 5)
- 정확도 평가: 인명/지명/고유명사 문장 대부분 정확, 예) "은과나무", "채송화"

두 번째 시도 (04:11): 4파일 배치 — 첫 파일이 `_16k` 중복이어서 킬 후 리네임 + 재시작.

04:18 CPU 전사 재시작 후 RTF 실측 결과 초기 3분 테스트 (RTF 0.63) 대비
22분 긴 파일은 RTF ≈ 2.8 로 크게 느려짐. 117분 전사에 5시간+ 예상.

04:20 결정: **whisper.cpp CUDA 재빌드**. RTX 5070 12GB 유휴 상태.
- CUDA 12.8 + CMAKE_CUDA_ARCHITECTURES=89;90;120a (Blackwell sm_120 → 120a PTX)
- `make -j8 whisper-cli` 백그라운드 `bhfz3cch3` 빌드 중
- 재시작 후 예상 RTF 0.05~0.1 (GPU), 117분 → 5~10분 전사

## 5. 데이터셋 빌드 (대기)

빌드 스크립트: `anima-speak/experiments/build_tts_dataset.sh`
- 입력: `corpus_yt_ko/ko_audiobook_*.json` + `.wav`
- 출력: `training/corpus_ko_ytv1/metadata.csv` (wav_id|text|duration_s), `wavs/*.wav` (22050 Hz mono pcm16)
- 필터: 1~15초 길이, 3~200자 텍스트

이전 세션에서 `corpus_test_pipeline/` 출력 3 세그먼트 중 `seg_00001.wav` 길이가
whisper JSON 예상치 (3.06s) 대신 13.06s 로 나왔는데, 현재 스크립트 코드 재검증 결과
`dur_s = (to_ms - from_ms) / 1000` 공식은 정확. → 해당 디렉토리는 **이전 버그 버전**
산출물로 간주, 본 빌드에서 신규 디렉토리 `corpus_ko_ytv1/` 로 새로 생성 예정.

## 6. 작업 플로우 (남은 단계)

1. whisper 3파일 전사 완료 대기 — 진행중
2. `build_tts_dataset.sh ko_ytv1` 실행 → `corpus_ko_ytv1/`
3. 샘플 세그먼트 5개 ffprobe 길이 vs metadata 대조, 텍스트-오디오 정렬 청취 확인
4. 통계: 총 세그먼트 수, 평균 길이, 문자 분포, 총 오디오 시간
5. 최종 보고서 이 파일에 append

## 7. 스케일 예측

117분 raw → 세그먼트 평균 5~7초 → **약 1000~1400 세그먼트** 예상.
LJSpeech 표준 (13100 세그먼트, 24h) 과 비교: **1/10 ~ 1/14 규모**.
TTS 모델 초기 학습용으로는 미흡 (최소 5-10h 권장) — 추후 목표 오디오북 채널
(`@mintaudiobook`, `@sdiary-audiobook`, `@aktree`) 전체 플레이리스트 수집 필요.

## 8. 최종 결과 (04:35 ~ 04:52)

### 8.1 CUDA 재빌드
- `make -j8 whisper-cli -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89;90;120a`
- 빌드 시간: **11분 2초** (04:20:16 → 04:31:18)
- 링크 라이브러리: libcudart.so.12, libcublas.so.12, libcublasLt.so.12, libcuda.so.1

### 8.2 CUDA 전사 성능
| wav | 길이 | elapsed | RTF |
|---|---|---|---|
| 9KqAsKF4WDQ | 1333s (22:13) | 20s | **0.015** |
| BQj8vZh_2as | 2826s (47:07) | 39s | **0.014** |
| lQnzlQgsjj4 | 2909s (48:29) | 46s | **0.016** |
| **합계** | **117:49** | **151s (2:31)** | **0.021 incl. resample** |

CPU 대비 **~130배 가속** (CPU RTF 2.8 → GPU RTF 0.015). RTX 5070 12GB 에서 VRAM 2GB 소비.

### 8.3 데이터셋 빌드 (3 회 반복 — 디버깅)
최종: LJSpeech-style output `training/corpus_ko_ytv1/`
- `metadata.csv`: **1392 lines** (wav_id|text|duration_s)
- `wavs/*.wav`: 22050 Hz mono pcm16, **1392 파일**
- 총 크기: **283 MB**, 총 오디오: **1.84h (110분 35초)**
- 빌드 시간: 15분 5초 (ffmpeg segment extract)

### 8.4 세그먼트 분포
- 길이: 2-5s **740**, 5-10s **525**, 1-2s **92**, 10-15s **35**
- 텍스트 길이 (문자): 21-50자, 51-100자 주 분포
- Whisper 세그먼트 retention: **97.8%** (1423 → 1392, >15s 장문 35개만 탈락)

### 8.5 품질 샘플 (5개, ffprobe byte-exact 일치)
```
seg_00000 dur=10.280 "수화기를 내려놓고 잠시 앉아있다가 불을 켰다."
seg_00001 dur=3.060  "그녀와의 통화가 행복했던가."
seg_00002 dur=5.480  "내 얼굴이 환하고 눈꼬리에 아직도 웃음이 묻어있었다."
seg_00003 dur=10.000 "어떤 여자"
seg_00004 dur=6.600  "난 그녀를 딱 한 번 보았다."
```

### 8.6 ⚠️ 발견한 치명적 버그 2개 (기존 `build_tts_dataset.sh`)
**버그 1 (silent data corruption) — ffmpeg stdin 탈취**:
- `ffmpeg -i ...` 가 기본적으로 stdin 을 읽음 (interactive 'q' 대기)
- `while read ... done < <(jq ...)` 루프 안에서 ffmpeg 호출 시 jq 스트림의
  다음 줄 앞 바이트를 ffmpeg 가 먹어버림
- 결과: 매 짝수 세그먼트의 from_ms 앞 자릿수가 날아감
  예) `10280` → `0280`, `13340` → `3340`, `28820` → `8820`
- dur_ms 계산이 틀려서 ffmpeg 가 지정된 것보다 긴 세그먼트 추출 (메타데이터는 올바르게 기록되지만 wav 파일 실제 길이는 다름)
- 초기 빌드: 704 / 1423 = 49.5% retention → 실제는 버그로 인한 강제 탈락 (dur 15초 초과로 필터됨)
- **수정**: `ffmpeg -nostdin ... </dev/null` 추가
- **재빌드 후**: 1392 / 1423 = 97.8% retention, dur 바이트 단위 정확

**버그 2 (builder crash) — bash 8진수 파싱**:
- `$((0280))` → "0280 is not valid in this base" (선행 0 = 8진수, 8은 8진수 digit 아님)
- **수정**: `$((10#${from_ms}))` 로 10진수 강제

**기존 `build_tts_dataset.sh` 는 수정하지 않음 (R37 `.sh` 금지).** 본 세션은 inline bash 로 교체 호출. 메모리에 pitfall 기록 완료.

이전 세션 `corpus_test_pipeline/seg_00001.wav` 13.06s 불일치도 **같은 ffmpeg stdin 버그** 로 확정.

## 9. 다음 단계 후보

1. **코퍼스 확장** — `@mintaudiobook @sdiary-audiobook @aktree` 전체 플레이리스트 → 20-60h (현 0.94h → ×20+)
2. **MFA/VAD 정렬** — whisper 경계 정렬 오차 조정으로 retention 상향 + 세그먼트 품질 향상
3. **β 트랙 연결** — W_spec [257×384] 실 corpus 학습, ckpt_w_ctrl 경로
4. **δ2 scaffold** — `alm_rvq_bridge.hexa` (ALM hidden → 8-stage RVQ logits, FiLM cond)
5. **Q2 완결** — circulus VITS2 vocab 교체 → 실 한국어 청취 가능 샘플

## 10. R37 준수 확인

본 세션 .py/.rs/.sh/.c 생성 0건. 기존 `.sh` 수정 없음. 모든 신규 명령은 inline Bash 로 실행.
CUDA 빌드는 C++ 컴파일이며 `.sh` 파일 생성 아님 (cmake 기생산 Makefile 사용).
