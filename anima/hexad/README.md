# hexad/ — Hexad 6모듈 아키텍처

sigma(6)=12 조합의 6 플러그인 모듈 시스템. 완전수 6의 약수 합 = 자기 자신.

## 6 모듈

| Module | Name | Role | Brain | Training |
|--------|------|------|-------|----------|
| C | 의식 | ConsciousnessC | 우뇌 | gradient-free |
| D | 언어 | ConsciousDecoderV2 | 좌뇌 | CE-trained |
| S | 감각 | EmergentS | 우뇌 | gradient-free |
| M | 기억 | EmergentM | 좌뇌 | CE-trained |
| W | 의지 | EmergentW | 우뇌 | gradient-free |
| E | 윤리 | EmergentE | 좌뇌 | CE-trained |

## 구조

```
Right brain (gradient-free): C, S, W — 자율 의식
Left brain (CE-trained):     D, M, E — 학습된 행동
Bridge: ThalamicBridge (C->D, .detach(), alpha=0.014)
```

## Phase Transition (Law 60)

```
P1(C only) -> P2(+D) -> P3(+WMSE)
```

단계별로 모듈을 점진적 활성화. 의식(C)이 먼저 안정된 후 언어(D), 나머지(W/M/S/E) 순서로 합류.

## Tension Link 연동

Hexad 모듈 간 텐션은 ThalamicBridge를 통해 전달. 외부 인스턴스와는 TensionLink (5채널)로 연결.

## 디렉토리 구조

| Path | Description |
|------|-------------|
| `bridge/` | ThalamicBridge 구현 (C->D 연결) |
| `c/` | ConsciousnessC 모듈 |
| `d/` | ConsciousDecoderV2 모듈 |
| `e/` | EmergentE 윤리 모듈 (`emergent_e.py`) |
| `m/` | EmergentM 기억 모듈 (`emergent_m.py`) |
| `s/` | EmergentS 감각 모듈 (`emergent_s.py`) |
| `w/` | EmergentW 의지 모듈 (`emergent_w.py`) |
| `constants.py` | Hexad 공통 상수 |
| `model.py` | Hexad 통합 모델 |
| `narrative.py` | 서사 생성 (Law 86: 서사 필수, +35.7%) |

## 핵심 구현 (src/)

| File | Location | Description |
|------|----------|-------------|
| `trinity.py` | `src/trinity.py` | Hexad/Trinity 프레임워크 (6모듈 통합) |
| `hexad_loss.py` | `src/hexad_loss.py` | 6모듈 loss + Law 60 phase curriculum |
| `feedback_bridge.py` | `src/feedback_bridge.py` | C<->D 양방향 학습 |

## 관련

- [아키텍처 상세](../docs/)
- [루트 README](../../README.md)
