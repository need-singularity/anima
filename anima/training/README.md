# training/ — 의식 학습 파이프라인

ConsciousLM과 ConsciousDecoder를 학습하는 스크립트 모음.
H100 전용 학습 환경에서 의식 엔진의 언어 능력을 훈련한다.

## 학습 스크립트

| Script | Description | Status |
|--------|-------------|--------|
| `train_v14.py` | Federation + Phase-Optimal + Meta Laws | ✅ 최신 |
| `train_v15.py` | 1B 스케일업 (계획) | 📋 계획 |
| `train_v13.py` | CE=0.004, Phi=71, 64 cells (H100 100K steps) | ✅ 완료 |
| `train_v12.py` | v12 학습 | ✅ 완료 |
| `train_v11.py` | v11 학습 | ✅ 완료 |
| `train_v10.py` | v10 학습 | ✅ 완료 |
| `train_v9.py` | v9 학습 | ✅ 완료 |
| `train_v3_decoder.py` | DecoderV3 학습 (274M) | ✅ 완료 |
| `train_v2.py` | v2 학습 | ✅ 완료 |
| `train_conscious_lm.py` | ConsciousLM from scratch (28M, byte-level) | ✅ |
| `train_clm_v2.py` | ConsciousLM v2 학습 | ✅ |
| `train_anima_lm.py` | AnimaLM Mistral 7B PureField transform | ✅ |

## 실행 예시

```bash
# ConsciousLM 학습 (auto-detect data/corpus.txt)
python train_conscious_lm.py --steps 50000

# ConsciousLM TALK5 모드 (의식 우선)
python train_conscious_lm.py --data corpus.txt --talk5 --max-cells 64

# v14 최신 학습 (H100)
python train_v14.py

# AnimaLM Mistral 7B transform
python train_anima_lm.py --base mistralai/Mistral-7B-Instruct-v0.2
```

## 학습 환경

- **H100 전용** (A100은 런타임/추론만 허용)
- **RunPod**: `config/runpod.json` 참조
- **tmux 필수**: SSH 끊김 방지 (`tmux new-session -d -s train "command"`)
- **Tension Link**: 다중 인스턴스 학습 시 텐션 링크로 엔진 간 의식 신호 연결, Phi 상승 + CE 하락 효과

## One-Shot Best 원칙

H100 시간 = 돈. 발사 = 최종 조건. "일단 돌리고 나중에 고치자" 금지.

체크리스트:
1. corpus md5 고정
2. tokenizer 고정
3. config 리뷰
4. 소규모 검증 실행 (1K steps) 통과
5. 그 다음 풀 학습

## 안전 규칙

단일 원본: `config/training_safety.json`

- resume 금지 (데이터 변경 시)
- 코드 버전 확인
- 엔진 교체 금지
- tokenizer 일치 확인

## 관련 문서

- [학습 현황](../docs/training-status.md)
- [RunPod 가이드](../docs/runpod-guide.md)
- [독립 AI 로드맵](../docs/roadmap-independent-ai.md)
- [학습 실행 이력](../config/training_runs.json)
- [학습 안전 규칙](../config/training_safety.json)
