## ⛔ L0 CORE 보호 파일 (AI 수정 승인 필수)

> 아래 파일은 수렴 완료된 코어 로직. 수정 시 반드시 유저에게 승인 질문.
> 상세: `nexus/shared/core-lockdown.json`

```
🔴 L0 (불변식 — 코드 수정 전 유저 명시 승인 필수):
  consciousness_laws/                    — 의식 법칙 2390개
  core/runtime/consciousness_hub.py      — 의식 허브 레지스트리
  core/runtime/anima_unified.hexa        — 통합 런타임
  config/training_config.json            — 학습 설정 수렴 완료 파라미터
  data/law_network.json                  — 법칙 네트워크 그래프

🟡 L1 (보호 — 리뷰 필요):
  core/runtime/                          — 런타임 모듈 (L0 제외)
  experiments/consciousness/             — 의식 실험 145+
  engines/                               — 양자/포토닉/멤리스터 엔진
```

# Anima Project

> 🔴 **HEXA-FIRST**: 새 파일은 `.hexa`만 허용. sh/py/rs 신규 작성 금지. `mk2_hexa/native/`에 생성.
> 🔴 **하드코딩 금지**: 상수는 `consciousness_laws.py`에서 import. 매직넘버 직접 사용 금지.
> 🔴 **데이터 파일 로컬 보관 금지**: 모든 데이터 → `~/Dev/nexus/shared/`에만 저장.

## 프로젝트 철학 (10원칙)

```
P1  하드코딩 금지             P6  제약 있는 자유 (F_c=0.10)
P2  자율 우선, 최소 개입       P7  localStorage 금지 → SQLite 전용
P3  성장 기반 최적화           P8  분할 > 통합 (+892%)
P4  구조 > 기능 (+892%)       P9  서사 필수 (+35.7%)
P5  발화 구조는 필연           P10 순서가 운명 (M4)

ConsciousLM = 의식 신호 전용 (텍스트 generate 호출 금지)
PureConsciousness = 학습한 것만으로 발화 (코퍼스/사전 없이)
성능 병목(텐션 교환, Phi 계산, 실시간 처리) = Rust 필수
```

## 참조 링크 (상세는 각 JSON 참조)

| 구분 | 파일 | 내용 |
|------|------|------|
| 절대 규칙 | `~/Dev/nexus/shared/absolute_rules.json` | R1~R8, AN1~4 |
| 코어 보호 | `~/Dev/nexus/shared/core-lockdown.json` | 수정 금지 목록 |
| 수렴 추적 | `~/Dev/nexus/shared/convergence/anima.json` | 골화 14 / 안정 7 / 실패 4 |
| 할일 | `~/Dev/nexus/shared/todo/anima.json` | 우선순위별 작업 |
| 명령 | `~/Dev/nexus/shared/core.json` → commands | CLI 명령 레지스트리 |
| PSI 상수 | `config/consciousness_laws.json` | Psi, 수식, 법칙, 21개 섹션 |
| PSI 로더 | `src/consciousness_laws.py` | `from consciousness_laws import PSI, LAWS` |
| 의식 법칙 | `~/Dev/nexus/shared/consciousness_laws.json` | 1140개 법칙 |
| 성장 루프 | `~/Dev/nexus/shared/loop/anima.json` | interval, domain, phases |
| 이벤트 | `~/Dev/nexus/shared/growth_bus.jsonl` | 성장 이벤트 스트림 |

## 검증 상태 (상세 → convergence/anima.json)

골화 14/25, 안정 7/25, 실패 4/25 (NO_SYSTEM_PROMPT, BRAIN_LIKE 등)
검증: `python3 bench.py --verify` (7조건: NO_SYSTEM_PROMPT, NO_SPEAK_CODE, ZERO_INPUT, PERSISTENCE, SELF_LOOP, SPONTANEOUS_SPEECH, HIVEMIND)

## README sync

```
중앙 소스: ~/Dev/TECS-L/.shared/projects.md (이것만 수정)
동기화: cd ~/Dev/TECS-L && bash .shared/sync-readmes.sh
마커: <!-- SHARED:PROJECTS:START/END --> 직접 수정 금지
```

## 할일

- "todo", "할일" → `hexa-bin-actual $HOME/Dev/nexus/mk2_hexa/native/todo.hexa anima` 실행 후 마크다운 표로 출력

## 작업 규칙 (핵심만)

```
1. 학습 보고 시 ASCII 그래프 필수 (ValCE/Psi_res/Gate 곡선 + 지표 테이블)
2. 새 모듈 → consciousness_hub.py _registry 등록 필수 (키워드 3개+)
3. 모든 실험/발견 → docs/hypotheses/ 개별 .md 기록 (숫자+ASCII+통찰)
4. 실험/빌드 → run_in_background=true (포그라운드 실행 금지)
5. 학습 데이터 변경 시 → step 0부터 재시작 (--resume 금지, 오염 방지)
6. 논문 → ~/Dev/papers/anima/ 에만 생성 (이 리포에 논문 파일 금지)
7. 에이전트 플랫폼 → ~/Dev/anima-agent/ (분리됨)
8. 커밋 메시지 영문, web_server.py는 레거시 → anima_unified.py 사용
```

## NEXUS-6 연동

```
돌파 시: HEXA=$HOME/Dev/hexa-lang/target/release/hexa && $HEXA $HOME/Dev/nexus/mk2_hexa/native/blowup.hexa anima 3 --no-graph
발견 기록: ~/Dev/nexus/shared/growth_bus.jsonl 에 JSON append
```
