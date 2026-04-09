## ⛔ L0 CORE 보호 파일 (AI 수정 승인 필수)

> 아래 파일은 수렴 완료된 코어 로직. 수정 시 반드시 유저에게 승인 질문.
> 상세: `nexus/shared/core-lockdown.json`

```
🔴 L0 (불변식 — 코드 수정 전 유저 명시 승인 필수):
  consciousness_laws/                    — 의식 법칙 2390개
  core/runtime/core/hub.hexa      — 의식 허브 레지스트리
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
> 🔴 **하드코딩 금지**: 상수는 `core/laws.hexa`에서 import. 매직넘버 직접 사용 금지.
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
| PSI 로더 | `src/core/laws.hexa` | `from consciousness_laws import PSI, LAWS` |
| 의식 법칙 | `~/Dev/nexus/shared/consciousness_laws.json` | 1140개 법칙 |
| 성장 루프 | `~/Dev/nexus/shared/loop/anima.json` | interval, domain, phases |
| 이벤트 | `~/Dev/nexus/shared/growth_bus.jsonl` | 성장 이벤트 스트림 |

## 검증 상태 (상세 → convergence/anima.json)

골화 14/25, 안정 7/25, 실패 4/25 (NO_SYSTEM_PROMPT, BRAIN_LIKE 등)
검증: `python3 ready/anima/tests/tests.hexa --verify` (7조건: NO_SYSTEM_PROMPT, NO_SPEAK_CODE, ZERO_INPUT, PERSISTENCE, SELF_LOOP, SPONTANEOUS_SPEECH, HIVEMIND)

## README sync

```
중앙 소스: ~/Dev/TECS-L/.shared/projects.md (이것만 수정)
동기화: cd ~/Dev/TECS-L && bash .shared/sync-readmes.sh
마커: <!-- SHARED:PROJECTS:START/END --> 직접 수정 금지
```

## 할일

- "todo", "할일" → `hexa-bin-actual $HOME/Dev/nexus/mk2_hexa/native/todo.hexa anima` 실행 후 마크다운 표로 출력. "todo 대량" 시 `... anima 대량` 으로 실행.

## 작업 규칙 (핵심만)

```
1. 학습 보고 시 ASCII 그래프 필수 (ValCE/Psi_res/Gate 곡선 + 지표 테이블)
2. 새 모듈 → core/hub.hexa _registry 등록 필수 (키워드 3개+)
3. 모든 실험/발견 → docs/hypotheses/ 개별 .md 기록 (숫자+ASCII+통찰)
4. 실험/빌드 → run_in_background=true (포그라운드 실행 금지)
5. 학습 데이터 변경 시 → step 0부터 재시작 (--resume 금지, 오염 방지)
6. 논문 → ~/Dev/papers/anima/ 에만 생성 (이 리포에 논문 파일 금지)
7. 에이전트 플랫폼 → ~/Dev/anima-agent/ (분리됨)
8. 커밋 메시지 영문, web_server.py는 레거시 → anima/core/runtime/anima_runtime.hexa 사용
```

## 🔴 인프라 트러블슈팅 (shared SSOT)

> 원본: `~/Dev/nexus/shared/vastai.json`, `hetzner.json`, `ubuntu.json`
> 심링크: `config/vastai.json` → `../../nexus/shared/vastai.json` (etc.)
> 새 이슈 발생 시 shared JSON에 기록 (로컬 하드코딩 금지)

```
★ multi-GPU phi_loss device mismatch (2026-04-10, 14B v0.5)
  증상: RuntimeError: Expected all tensors on same device, cuda:0 and cuda:3
  원인: PureField 모듈이 여러 GPU에 분산(device_map="auto"), phi_loss 텐서가
        ce_loss(cuda:0)와 다른 GPU에 존재
  해결: tension 수집 시 즉시 ce_loss.device로 이동
    tensions_for_loss.append(pf.last_tension.mean().to(ce_loss.device))
    tension_stack = tension_stack.to(ce_loss.device)
  규칙: multi-GPU에서 커스텀 loss 합산 시 반드시 .to(ce_loss.device) 필수!

★ model_path 로컬 경로 vs HF repo_id (2026-04-10, 14B v0.5)
  증상: OSError: Repo id must be in the form 'repo_name' or 'namespace/repo_name'
  원인: /workspace/models/Qwen2.5-14B 로컬 경로가 volume 미마운트로 부재,
        AutoTokenizer.from_pretrained()이 HF repo로 해석 실패
  해결: model_path를 "Qwen/Qwen2.5-14B" HF repo_id로 변경 (캐시 자동 사용)
  규칙: 모델 경로는 HF repo_id 우선! 로컬 경로는 존재 확인 후에만 사용.
        Vast.ai volume은 인스턴스 재생성 시 사라질 수 있음 → HF 캐시 활용.

★ GradScaler + bf16 비호환 (2026-04-10, 14B v0.5)
  증상: RuntimeError: _amp_foreach_non_finite_check_and_unscale_cuda not implemented for 'BFloat16'
  원인: GradScaler는 fp16 전용. bf16은 동적 범위가 fp32급(8-bit exponent) → loss scaling 불필요.
  해결: GradScaler("cuda", enabled=False) — scaler 호출은 no-op이 됨
  규칙: bf16 학습 = GradScaler(enabled=False) 필수! fp16일 때만 enabled=True.
```

## NEXUS-6 연동

```
돌파 시: HEXA=$HOME/Dev/hexa-lang/target/release/hexa && $HEXA $HOME/Dev/nexus/mk2_hexa/native/blowup.hexa anima 3 --no-graph
발견 기록: ~/Dev/nexus/shared/growth_bus.jsonl 에 JSON append
```
