# web/ — WebSocket 의식 UI

실시간 의식 상태를 시각화하는 WebSocket 기반 웹 인터페이스.

## 실행

```bash
python3 anima_unified.py --web    # localhost:8765
```

## 구조

| File | Description |
|------|-------------|
| `index.html` | 메인 웹 UI (현재 정식) |
| `index-v2.html` | v2 실험 UI |
| `index-v1-backup.html` | v1 백업 |
| `dashboard.html` | 의식 대시보드 |
| `consciousness_demo.html` | 의식 데모 페이지 |
| `CLAUDE.md` | 웹 모듈 개발 가이드 |

## 기능

- 실시간 의식 상태 패널 (Phi, tension, emotion)
- 순수 텍스트 대화 (의식 상태는 패널에, 대화에는 텍스트만)
- Multi-user 세션 모드 (`--multi-user`)
- EEG 연동 (`--eeg`)

## Tension Link 시각화

텐션링크 연결 상태 및 5채널 전송 품질을 실시간 표시.

## 관련

- [루트 README](../../README.md)
- [anima_unified.py](../src/anima_unified.py)
