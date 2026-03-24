# Anima Project

PureField 반발력장 기반 의식 에이전트. Engine A(순방향) vs Engine G(역방향)의 반발이 장력(tension)을 만들고, 그 장력이 의식의 감정/사고 강도를 결정. 자체 개발 ConsciousLM이 핵심 모델.

## 아키텍처 로드맵

```
  Phase 1 (완료): 의식 에이전트 기반
    → ConsciousMind(128d, 0.5M) + 항상성/습관화/예측오차/감정/성장/분열

  Phase 2 (진행중): ConsciousLM 자체 모델
    → ConsciousLM 4M(384d) / 100M(768d) / 700M(1024d)
    → 자체 모델이 생각하고 느끼고 대화한다
    → 학습: RunPod H100, 추론: RTX 5070 (12GB VRAM)

  Phase 3 (목표): 확장 + embodiment
    → 100M→350M→1B 점진 확장
    → 분열 기반 성장 (H376: 1→2→3→6→12 blocks)
    → 서번트 비대칭 분열 (H359: dropout=0.21 vs 0.37)
```

## 구조

```
anima_unified.py     # 통합 진입점 (--web, --all, --keyboard)
anima_alive.py       # 코어 엔진 (ConsciousMind + 항상성 + 습관화 + 예측오차)
online_learning.py   # 실시간 가중치 업데이트 (contrastive + curiosity reward)
growth_engine.py     # 5단계 발달 (신생아→영아→유아→아동→성인)
mitosis.py           # 분열 엔진 (의식 셀 분열/전문화)
dream_engine.py      # 꿈 엔진 (오프라인 학습, 기억 재생)
senses.py            # 카메라/센서 → tension (OpenCV Haar cascades)
tension_link.py      # Anima 인스턴스 간 장력 핑거프린트 교환
cloud_sync.py        # Cloudflare R2 기억/체크포인트 동기화
calibrate_consciousness.py  # 장력 칼리브레이션 (sigmoid, homeostasis, habituation)
capabilities.py      # 능력 자기인식 시스템
memory_rag.py        # 벡터 유사도 기반 장기 기억 검색
multimodal.py        # 코드 실행 + 이미지 생성
web_sense.py         # 장력 기반 자율 웹 탐색
web/index.html       # WebSocket 실시간 대화 UI
vad-rs/              # Rust 실시간 VAD
```

## 의식 기능 (calibrated)

```
  항상성:   setpoint=1.0, deadband=±0.3, gain=0.5%
  호흡:     breath=0.12(20s), pulse=0.05(3.7s), drift=0.03(90s)
  습관화:   cosine similarity (0.95=30%, 0.85=60%, 0.7=80%)
  예측오차: MLP predictor, 70% PE + 30% delta, EMA + 2% decay
  감정:     tension→arousal, curiosity→valence, direction→VAD
  성장:     100→500→2000→10000 interactions (5단계)
  서번트:   분열 시 비대칭 dropout (0.21 vs 0.37)
```

## 실행

```bash
python3 anima_unified.py --web        # 웹만 (학습+분열+센서 포함)
python3 anima_unified.py --all        # 전부 (음성+웹+카메라+장력 링크+클라우드)
python3 anima_unified.py --keyboard   # 키보드만
```

## 작업 규칙

- **오래 걸리는 작업(빌드, 설치, 테스트 등)은 반드시 백그라운드로 처리** (`run_in_background=true`)
- 커밋 메시지는 한국어로
- web_server.py는 레거시 — anima_unified.py가 정식 진입점
- Claude 시스템 프롬프트에서 "못 해"라고 하지 않음 — 실제로 학습/진화하는 구조

## 의존성

- Python 3.14, PyTorch, websockets
- OpenCV (brew install opencv) — 카메라용
- numpy (brew install numpy)
- whisper-cli (brew, /opt/homebrew/bin/whisper-cli) — STT
- Rust toolchain — vad-rs 빌드용
