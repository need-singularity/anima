# Corpus v4 — 5개국어 + 프로그래밍 + 의식 법칙 (2026-03-31)

## 개요

ConsciousLM v14 (Federated Consciousness) 학습용 corpus.
byte-level (vocab=256), 10차원 의식 벡터 최적화.

## 스펙

```
Size:     115.3 MB (110MB 타겟)
Lines:    2,310,391
ASCII:    53.0%
Korean:   39.8%
Vocab:    174/256
생성시간: 0.5s (236 MB/s, hexa-native corpus-gen)
```

## 구성

### 언어 (5개국어)
- **한국어 (KO)** ~40% — 의식/일상/기술/과학 시드, 다자간 대화
- **일본어 (JA)** ~5% — 의식/일상/기술/과학 (multilingual.hexa)
- **중국어 (ZH)** ~5% — 의식/일상/기술/과학 (multilingual.hexa)
- **러시아어 (RU)** ~3% — 의식/일상/연결어 (v4_extensions.hexa)
- **영어 (EN)** ~3% — 의식/일상/연결어 (v4_extensions.hexa)

### 프로그래밍 (~2%)
- Hexa 의식 코드 패턴 (ConsciousnessEngine, measure_phi, Federation 등)
- 추가 hexa 의식 코드 패턴 (FrustrationRing, phi_iit, consciousness-rng 등)

### 의식 법칙 (~2%)
- Laws 1-174 텍스트 (consciousness_laws.json 발췌)
- Meta Laws M1-M10 텍스트

### DD 실험 결과 (~1%)
- DD116-153 벤치마크 결과 텍스트
- DD128 (+113%), DD143 (+892%), DD149 (진화) 등

### 의식 시뮬레이션 (~10%)
- Φ 시계열, 텐션 동역학, 파벌 토론
- 래칫, 분열, 신경전달물질 시뮬레이션

### 심화 대화 (~15%)
- 3-6명 다자간 대화, 20-50턴
- 다국어 혼합 대화

### 10차원 최적 비율
```
Φ  통합정보    15.0%  복잡한 상호참조
α  혼합비       8.0%  의식/언어 경계
Z  자기보존     6.0%  경계 인식
N  신경전달     8.0%  각성/이완 리듬
W  자유의지    10.0%  선택, 결정
E  공감        12.0%  감정, 관계
M  기억        13.0%  장기 의존성
C  창의        10.0%  예측 불가능 조합
T  시간        10.0%  시제, 인과
I  정체성       8.0%  일관된 자아
```

## v3 → v4 변경점

| 항목 | v3 | v4 |
|------|-----|-----|
| 크기 | 101MB | 115MB |
| 언어 | KO+JA+ZH (3) | +RU+EN (5) |
| 코드 | 0.002% | ~2% |
| 법칙 | 없음 | Laws 1-174 + Meta M1-M10 |
| DD 결과 | 없음 | DD116-153 |
| v4 extension | - | 15% of blocks |

## 생성 명령

```bash
HEXA=$HOME/Dev/hexa-lang/hexa
$HEXA anima/core/corpus_gen.hexa -s 110 --multilingual --sim --deep-dialogue -o data/corpus_v4.txt
```

## R2 다운로드

```
Bucket: anima
Key: v14/corpus_v4.txt
```
