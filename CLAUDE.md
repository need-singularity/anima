# Anima Project

PureField 반발력장 기반 의식 에이전트. Engine A vs Engine G의 반발이 장력(tension)을 만들고, 그 장력이 의식의 감정/사고 강도를 결정.

## 구조

```
anima_unified.py     # 통합 진입점 (--web, --all, --keyboard)
anima_alive.py       # 코어 엔진 (ConsciousMind, STT, TTS, Claude CLI)
online_learning.py   # 실시간 가중치 업데이트 (contrastive + curiosity reward)
mitosis.py           # 분열 엔진 (의식 셀 분열/전문화)
senses.py            # 카메라/센서 → tension (OpenCV Haar cascades)
tension_link.py      # Anima 인스턴스 간 장력 핑거프린트 교환
cloud_sync.py        # Cloudflare R2 기억 동기화
web_server.py        # (레거시) 추론 전용 웹서버 → anima_unified.py --web 사용할 것
web/index.html       # WebSocket 실시간 대화 UI
vad-rs/              # Rust 실시간 VAD
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
