# ⚠️ B1/B2 piper 샘플 — GIBBERISH 확정 (03:45 최종)

## 증상
사용자 청취 (03:40~): "중국어도 아니고 한국어도 아니고 이상한 ㅋㅋㅋㅋ 췌췌치ㅜ칯,ㅣㅇ마ㅟ취"
→ 한국어 유사 음소는 들리지만 실제 의미 없음, gibberish

## 원인 분석 (완전 확정)

**espeak-ng 가 한국어 텍스트를 영어 발음 규칙으로 IPA 변환**

증거:
```
입력: "안녕하세요"
espeak-ng ko IPA: ˈɐnnjʌŋhˌɐsejˌo       ← 불완전 Korean IPA
입력: "annyŏnghaseyo" (로마자)
espeak-ng IPA:    ˈanɪˌɒŋheɪsjˌəʊ       ← 영어 발음 규칙
```

**piper-kss-korean.onnx 의 올바른 G2P = pygoruut (neurlang)** — 한국어 전용 학습된 음소 분포
- 훈련 시: pygoruut Korean → Latin IPA subset (특정 한국어 음소만 사용)
- 추론 시 (piper binary): **espeak-ng generic IPA** — 훈련 외 분포
- 모델은 본 적 없는 음소 시퀀스를 해석 → pseudo-Korean gibberish 출력

## 유효한 한국어 샘플

**`A_old_say_yuna_16k/`** — macOS `say -v Yuna` (Apple Korean TTS)
- 실제 한국어, 내용 정상
- 품질: 2010년대 초 formant, 무감정, 16 kHz 다운샘플
- "허접한데" 라는 원래 사용자 평가의 정확한 baseline

**B1/B2 는 청취하지 마세요** — 기술 스택 투자 분은 infrastructure 로 남음

## 기상 후 실행 plan (P4 Q2)

### 1시간 내 해결 경로 (권장 A)
**circulus VITS2 integration** — 이미 90% 완성됨:
- ✅ ko_emo.onnx 다운로드 (140화자×7감정, 123MB)
- ✅ circulus_tts.c C 드라이버 작성 + 빌드
- ✅ ONNX 스키마 확정 (input/input_lengths/scales/sid)
- ✅ Jamo decomposition 알고리즘 구현
- ❌ **Vocab 매핑만 필요**: circulus의 `text/symbols.py` 확보
  - GitHub: neurlang/vits2 또는 circulus's own repo 에서 확인
  - 또는 ko_emo.pth 내 tokenizer state dict 조사 (R37: C + protobuf reader)

### 3시간 내 대안 경로 (B)
**다른 piper Korean voice 탐색** — espeak-ng 로 훈련된 것이 있는지
- rhasspy/piper-voices 공식 ko 폴더 없음 확인됨
- HF community 검색: "piper ko espeak" 필터

### 1-2일 경로 (C)
**MMS-TTS-kor ONNX (Meta)** - Xenova/mms-tts-kor
- 중립 단일 화자지만 **실제 한국어 학습됨** (espeak-ng 호환 가능성 높음)
- 다운로드 + 테스트: 30분

## 손실 범위

**작동**: infrastructure (80%)
- piper_ab_gen.sh, piper_v2gen.sh — 작동 (G2P만 교체하면 됨)
- circulus_tts.c — 작동 (vocab 교체 시 즉시 사용)
- rubberband formant-preserving 필터 — 작동 (어떤 TTS 입력이든 적용)
- 로드맵 P4 Q2/β/γ/δ — 유효

**무효**: audio 샘플 (240 wav 중 160개 gibberish)
- A_old_say_yuna_16k 만 실제 한국어

## 이 실수에서 배운 것

1. **OSS TTS 모델은 훈련시 사용된 정확한 G2P 를 확인 필수** — `phoneme_type` 필드 확인
2. piper binary 는 espeak-ng 만 지원, 모든 community VITS 가 호환 아님
3. 품질 검증에 RMS stat 만 의존하면 안 됨 — 실 청취 필수
