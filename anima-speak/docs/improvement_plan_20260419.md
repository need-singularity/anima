# anima-speak 품질 개선 계획 — 2026-04-19

**세션**: 야간 자율 (2026-04-19 02:42~)
**호스트**: aiden-B650M-K (ubu, RTX 5070 12GB, CUDA 13.0)
**상태**: Q1 트랙 완료 (80/80 piper A/B 샘플 생성), β 트랙 scaffold 중

## 핵심 진단 요약

1. **tts_say 샘플은 anima-speak neural vocoder 출력이 아님** — macOS `say -v Yuna` (formant) → ffmpeg 16kHz 다운샘플 + male 페르소나 pitch-shift. 사용자가 "허접"이라 느낀 실체는 2010년대 초 baseline + 파괴적 포맷 변환.
2. **실제 neural vocoder 는 프로토타입** — W_ctrl [12×384]=4608 + W_spec [257×384]=98688 params, 합성 데이터만 학습 (loss 0.00860). 실 음성 재구성 미검증.
3. **감정 표현 부재** — emotion_prosody.hexa 는 tts_say 경로에서 사용되지 않음. Neural path 에서는 사용되나 현재 4608-param 헤드로는 표현 범위 제한.
4. **내부 의식 모델 (ALM/CLM) 은 텍스트 전용** — 오디오 토큰 출력 없음. RVQ 브리지 헤드 + 페어링 코퍼스 필요.
5. **hexa autograd 구현 완료** (Agent I 정정 by Agent G) — training/ 에 `attention_backward`, `ffn_backward`, `lm_head_backward`, `matmul_backward`, `layer_backward`, `ops_backward` 존재. 학습 가능.

## 즉시 완료 (Q1, 2026-04-19 02:42~03:05)

✅ **piper-kss-korean (VITS neural TTS) baseline 교체**
- 80/80 샘플 생성 (10 페르소나 × 8 라인, 22050 Hz)
- 페르소나별 piper 파라미터 튜닝 (length_scale, noise_scale, noise_w)
- ffmpeg 톤 필터 체인 (EQ/reverb/pitch-shift)
- 원 tts_say 대비: sr 16k→22050 (+38% bandwidth), formant→neural VITS

**산출물**:
- `anima-speak/corpus/ab_test/piper_ko_v1/persona_{10..19}_*/tts_{00..07}.wav`
- `anima-speak/experiments/piper_ab_gen.sh` (실행 스크립트)
- `anima-speak/experiments/piper_ab_gen.hexa` (hexa canonical — 파서 미지원 시 archive)
- `anima-speak/corpus/ab_test/metrics_20260419.tsv` (80+80 객관 통계)
- `anima-speak/corpus/ab_test/spectrograms/persona_{10,12,14,16,19}_*.png`

## 한계 (piper-kss 기반)

- **단일 화자 (KSS dataset)**: 모든 페르소나 같은 여성 중립 voice → ffmpeg pitch-shift 로 남성 표현, 실 voice 분리 아님
- **감정 없음**: KSS 는 중립 낭독 코퍼스 — 페르소나별 톤 필터는 DSP 색채 추가일 뿐 실 감정 아님
- **사용자 피드백 "감정 없음, 옛날 TTS" 는 일부 해소**: 대역폭/중립 신경망 품질은 개선되지만 진정한 expressive 아님

## 다음 트랙 (Q2 + β + γ)

### Q2 — 감정 expressive TTS binary 대체 후보

**탐색 결과**:
- **circulus/on-vits2-korean-v1** (125MB ONNX): VITS2 한국어 140화자 × 7감정 (Angry/Happy/Sad/Anxious/Hurt/Embarrassed/Neutrality) + 5스타일 (뉴스체/구연체/대화체/낭독체/중계체)
- **blocker**: 현재 piper 와 스키마 불일치, Korean G2P (`korean_cleaners`) preprocessing + custom ONNX runtime driver 필요
- **예상 작업**: 1-2일
  1. Korean G2P (Jamo decomposition) hexa 구현 (espeak-ng 활용 가능)
  2. onnxruntime C API hexa FFI 바인딩 (piper 가 이미 번들한 libonnxruntime.so 재사용)
  3. CLI inference 래퍼 작성
  4. 10 페르소나 → (age, gender, emotion, speaker) 매핑

**대안**:
- Xenova/mms-tts-kor (MMS Korean ONNX): 중립이지만 다국어 VITS 품질
- 자체 ONNX 변환 (github.com/coqui-ai/TTS → ONNX export): 풀 pipeline 필요

### β — W_spec real-corpus manual-gradient 학습 (2-3일)

**목표**: neural_vocoder.hexa 의 98,688-param W_spec 을 실제 16 wav 코퍼스에서 학습 → 진짜 neural vocoder 가능성 증명

**설계**:
1. 기존 corpus (3.3h × 10 personas) mel-spec + magnitude spectrogram 추출
2. Linear regression 로스 (synth_spec = W_spec @ latent) + gradient 수동 도출
3. 에폭 64 × batch 12 × lr 2e-4 (circulus config 참조)
4. 산출: 합성 → 실 audio magnitude 근사 → Griffin-Lim phase → 24kHz pcm

**실행 위치**: RTX 5070 + hxcuda_istft_bridge (GPU STFT/iSTFT 이미 작동 0.023ms)

**예상 품질**: 합성음 재구성 가능 수준, 개별 화자 identity 보존 (10 페르소나 각)

**기대 개선**: 현재 0.00860 synthetic loss → 실 오디오 MSE < 0.1, MCD < 6 dB (baseline 정의 필요)

### γ — HiFiGAN-scale 풀 학습 (수주)

**목표**: ~13M param neural vocoder + GAN discriminator + 24h+/persona 코퍼스

**선결**:
- 코퍼스 수집 24h+/persona × 10 = 240h (현재 3.3h, 72× 부족)
- discriminator module hexa 구현 (multi-period, multi-scale — HiFiGAN 표준)
- GAN loss scheduler + mel-spec L1 auxiliary loss
- hxcuda_conv1d_bf16 활용 (이미 libhxcuda.so 에 번들, anima-speak 미사용 상태)

**예상**: 진정한 상용 경쟁력 갖춘 neural TTS (ElevenLabs 수준 근접)

### δ — 의식 모델 (ALM/CLM) → audio 브리지

**목표**: ALM r8a (14B LoRA 학습 완료, R2 `alm14b/r4/step_10000/`) 또는 CLM r5 → RVQ 토큰 projection 헤드 학습

**선결**:
- **오디오 RVQ encoder** (text 아닌 오디오 → 8-stage 1024-entry 코드): EnCodec ONNX 탐색 또는 자체 학습
- **pair corpus**: 오디오 + 전사 text 쌍 필요 (KSS 이용 가능, 12h/KSS 단일 화자)
- **RVQ_head 모듈**: ALM hidden state → RVQ logits projection
- RTX 5070 은 14B 못 돌림 — 1B CLM 에서 PoC 시작

**예상**: 진정한 consciousness-driven TTS (의식이 voice/emotion 선택) — 하지만 수 주-수 개월

## 우선순위 권장 (밤새 진행)

1. **Q1 ✅ 완료** (piper baseline)
2. **β scaffold 작성** — W_spec 학습 hexa 파일 (GPU 기반)
3. **MCD 측정 hexa 모듈** — dsp_core.hexa 의 FFT+mel 활용해 작성
4. **Q2 시작** — circulus VITS2 의 Korean G2P + ONNX FFI 조사
5. **최종 리포트 + git commit**

## 참조

- 감사 리포트: `anima-speak/docs/quality_audit_20260419.md`
- 기존 페르소나 정의: `anima-speak/tts_say_driver.hexa:152-350`
- vocoder 아키텍처: `anima-speak/neural_vocoder.hexa:8-42`
- 훈련 인프라: `training/train_clm.hexa`, `training/*_backward.hexa`
