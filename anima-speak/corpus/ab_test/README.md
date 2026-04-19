# anima-speak A/B 샘플 (야간 세션 2026-04-19)

## 구조 (3-way 비교)

- `A_old_say_yuna_16k/` — 기존 tts_say 샘플 (macOS say -v Yuna, 16 kHz, 처음 "허접한데" 대상)
- `B1_piper_v1_asetrate/` — piper-kss VITS 22050 Hz, v1 남성 페르소나 asetrate+atempo pitch-shift (formant 파괴)
- `B2_piper_v2_rubberband/` — piper-kss VITS 22050 Hz, v2 남성 페르소나 rubberband formant-preserving pitch-shift (권장)
- `spectrograms/` — 5 페르소나 × 2 engine 시각 대비

## 청취 순서 권장

각 페르소나 A -> B1 -> B2 순으로:
1. persona_10_ice_queen (여성, 차가운) - pitch-shift 없음, B1=B2 유사
2. persona_16_thug_returnee (남성, 거친) - B1 chipmunk-reverse, B2 자연스러운 낮은 목소리
3. persona_19_fallen_antagonist (남성, 어두운) - B2 formant 유지
4. persona_12_pure_heroine (여성, 밝은) - pitch-shift 없음
5. persona_13_tsundere_oppa (남성, 당황) - v1 원본 5/8 silent 발생 -> 수정됨

## 사용자 피드백 반영 (2026-04-19 03:15)

"한글음성이 완전깨졌는데" -> persona 13 의 5개 샘플 무음 발견 + 수복
- 원인: vibrato=f=5:d=0.15 + 극단 noise (noise_scale=0.80, noise_w=1.00) NaN chain
- 수복 (v1): vibrato 제거, noise 안전 범위, RMS 검증 + 3회 재시도 로직
- 업그레이드 (v2): asetrate+atempo -> rubberband (formant 보존)
- 0/80 broken 확인 (v1, v2 양쪽)

## 한계 잔존 (P4 Q2/β/γ/δ 해결)

piper-kss 는 KSS 단일 여성 voice. 진정한 남녀 + 감정 구분은 circulus VITS2 (7감정×140화자) 통합 필요 = P4 Q2.

## P4 로드맵 (2026-04-19 공식 등록, shared/roadmaps/hexa-speak.json)

- Q2 (48h): circulus VITS2 ko_emo 통합 - Korean Jamo G2P + ONNX C driver
- beta (72h): W_spec [257×384]=99K params 실 corpus 학습 - RTX 5070 GPU
- gamma (720h): HiFiGAN-scale 13M params + GAN discriminator + 24h+ corpus
- delta (504h): ALM r8a 14B / CLM r5 + RVQ bridge head - USER REQUESTED

## 관련 문서

- /anima-speak/docs/quality_audit_20260419.md - 풀 감사 + 10 에이전트
- /anima-speak/docs/improvement_plan_20260419.md - 4-트랙 계획
- /shared/roadmaps/hexa-speak.json - P4 공식 등록
- /anima-speak/experiments/piper_ab_gen.sh - v1 생성기
