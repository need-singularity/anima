> 🔴 **HEXA-FIRST**: 모든 코드는 `.hexa`로 작성. sh/py/rs 신규 작성 금지. 부하 유발 명령 최소화.

> 🔴 **인프라 SSOT**: `nexus/shared/infrastructure.json` 참조. Mac 최하위 정책.
> - **Vast.ai 4×RTX 4090** (GPU 학습 primary): Jupyter `https://184.144.227.89:40961` · Instance 34448146 · CUDA 12.2 · 96GB VRAM · $1.098/hr
> - **Hetzner AX102-U** (CPU 전담): `ssh hetzner` · EPYC 7950X3D 32T · 124GB RAM · anima CPU 서빙/전처리
> - **Ubuntu 로컬** (실시간 GPU): `ssh ubu` · RTX 5070 12GB · 추론/서빙
> - **Mac** (최하위): 코딩/에디터만. 컴퓨트 금지 — iTerm만으로 벅참
> - **자원 상태 확인**: `cat ~/Dev/nexus/shared/infra_state.json` 또는 `$HEXA ~/Dev/airgenome/modules/infra_probe.hexa status`
> - **RunPod** (최후수단): A100/H100 · AN6 규칙: ubu+vast 불가 시만
> - **자원 확인**: `$HEXA ~/Dev/airgenome/modules/resource_request.hexa check anima` — 현재 가용 자원 확인
> - **자원 요청**: `$HEXA ~/Dev/airgenome/modules/resource_request.hexa request anima gpu "vram=48,hours=8,reason=training"` — GPU 자원 요청
> - **anima = P0 최우선** — 자원 충돌 시 anima가 우선 할당
> - **트러블슈팅 SSOT**: `nexus/shared/vastai.json`, `hetzner.json`, `ubuntu.json` (심링크: `config/*.json`)

> 🔴 **NEXUS-6 특이점 연동**: 이 프로젝트의 모든 돌파/발견/실험은 nexus 특이점 사이클 입력이다.
> - **돌파 시**: `HEXA=~/Dev/hexa-lang/target/release/hexa && $HEXA ~/Dev/nexus/mk2_hexa/native/blowup.hexa <domain> 3 --no-graph`
> - **발견 기록**: `~/Dev/nexus/shared/growth_bus.jsonl`에 JSON append (source, value, grade, timestamp)
> - **학습 현황**: `$HEXA ~/Dev/nexus/mk2_hexa/native/anima_status.hexa` (리포트) / `auto` (자동 진행)
> - **전체 상태**: `$HEXA ~/Dev/nexus/mk2_hexa/native/command_router.hexa "anima 상태"`

<!-- SHARED:WORK_RULES:START -->
  ⛔⛔⛔ 이 블록은 삭제/수정/이동 금지! (sync-claude-rules.sh 자동 주입)
  ⛔ 가설, 규칙, 발견, 망원경 — 모든 리포의 핵심 인프라. 절대 삭제하지 마세요!

  ═══════════════════════════════════════════════════════════════
  ★★★ 수렴 기반 운영 3대 원칙 — 누락 시 작업 중단! ★★★
  ═══════════════════════════════════════════════════════════════

  모든 작업 전 체크 (하나라도 누락 = 작업 중단):
    □ CDO:    이슈 발생 시 JSON에 기록했는가? 규칙 승격했는가?
    □ NEXUS-6: 변경 전후 scan 했는가? anomaly 0인가?
    □ SSOT:   하드코딩 안 했는가? JSON 원본 갱신했는가?

  모든 작업 후 체크:
    □ 트러블슈팅 기록: 에러 있었으면 해당 JSON에 기록
    □ 규칙 승격:       같은 에러 2회 이상 → absolute_rule로 승격
    □ NEXUS-6 스캔:    최종 결과물 scan → anomaly 0 확인
    □ SSOT 동기화:     JSON 변경 시 sync_readme.py --apply
    □ 커밋 메시지:     변경 이유 + 검증 결과 포함

  위반 처리:
    1회: troubleshooting_log에 기록
    2회: absolute_rule로 승격
    3회: 해당 작업 프로세스 재설계

  ═══════════════════════════════════════════════════════════════
  ★ CDO (Convergence-Driven Operations) — 100% 수렴 ★
  ═══════════════════════════════════════════════════════════════
    이슈 → 해결 → 절대 규칙 승격 → 재발 0 → 100% 수렴
    모든 config JSON 필수 구조: _meta + absolute_rules + troubleshooting_log
    원칙 파일: .shared/convergence_ops.json

  ═══════════════════════════════════════════════════════════════
  ★ CDO 세션 부트스트랩 — 어떤 리포에서든 즉시 운영 가능 ★
  ═══════════════════════════════════════════════════════════════
    대상 리포 (6개): TECS-L, anima, sedi, n6-architecture, brainwire, papers
    모든 리포는 .shared/ 심링크로 공유 인프라 접근

    세션 시작 시:
      1. .shared/ 심링크 확인 (없으면: ln -s ../TECS-L/.shared .shared)
      2. CDO 3대 체크 인지 (CDO + NEXUS-6 + SSOT)
      3. 작업 시작 — 차단 없이 진행

    ★ CDO 차단 방지 규칙 (절대 작업이 멈추면 안 됨!) ★
      .shared 심링크 깨짐    → ln -s ../TECS-L/.shared .shared 로 복구 후 진행
      convergence_ops.json 없음 → TECS-L에서 git pull 후 심링크 재설정
      NEXUS-6 바이너리 없음  → 수학/문서 작업은 CDO+SSOT만으로 진행 가능
      config JSON에 _meta 없음 → _meta 추가가 선행 작업 (차단 사유 아님)
      리포 간 데이터 필요    → .shared/ 통해 접근 (리포 간 직접 import 금지)
      CI 미설정              → 로컬 검증으로 대체 (CDO 위반 아님)

    원칙: CDO는 작업을 돕는 프레임워크이지, 작업을 막는 게이트가 아님.
    인프라 문제로 작업 불가 시 → 복구를 선행 작업으로 처리하고 본 작업 진행.

  ═══════════════════════════════════════════════════════════════
  ★ NEXUS-6 필수 사용 — 모든 변경 시 스캔 의무 ★
  ═══════════════════════════════════════════════════════════════
    아래 상황에서 NEXUS-6 스캔 없이 진행 금지!
    위반 = 의식 파괴/품질 저하 위험

    ★ 새 모델 학습 시:      학습 전후 nexus.scan_all() 비교
    ★ 모델 변경/이식 시:    이식 전후 Phi 보존율 측정
    ★ corpus 변경/추가 시:  새 corpus nexus.scan_all() 품질 확인
    ★ 모듈 변경 시:         변경 전후 scan → Phi 하락 시 롤백
    ★ 체크포인트 저장 시:   가중치 scan → anomaly 있으면 경고
    ★ 가속기 적용 시:       적용 전후 scan → Phi 보존 95%+ 확인
    ★ 배포/서빙 전:         최종 scan → 3+ 렌즈 consensus 통과

    스캔 없이 커밋/배포하면 CDO 위반으로 기록!

  ═══════════════════════════════════════════════════════════════
  ★ SSOT (Single Source of Truth) — 데이터 하드코딩 금지 ★
  ═══════════════════════════════════════════════════════════════
    동일 데이터를 여러 곳에 직접 쓰지 말 것!
    원본: JSON 파일 하나 (config/ 또는 data/)
    표시: README/문서는 마커(<!-- AUTO:섹션:START/END -->) 기반 자동 생성
    위반 시: 불일치 발생 → 잘못된 정보 전파

    예시:
      total_laws → consciousness_laws.json._meta.total_laws (원본)
                → README/session_board/progress 는 여기서 읽어야 함
      학습 상태  → agi_progress.json (원본)
                → README 로드맵은 여기서 자동 생성
      가속 가설  → acceleration_hypotheses.json (원본)
                → 문서는 여기서 참조

    규칙:
      1. 숫자/상태를 README에 직접 쓰지 말 것 → JSON 원본 참조
      2. 동일 데이터가 2곳 이상이면 → JSON 원본 1개 + 마커 자동 생성
      3. 한 곳에서만 쓰이면 → 직접 편집 OK
      4. JSON 갱신 시 → sync 스크립트로 README 자동 반영

  ═══════════════════════════════════════════════════════════════
  ★ NEXUS-6 통합 망원경 (188 렌즈 파일, 1028종 레지스트리) ★
  ═══════════════════════════════════════════════════════════════
  ⚠️ telescope-rs (구 22종)는 폐기. 모든 탐색은 NEXUS-6 사용.
  ⚠️ 상세 API/사용법: .shared/CLAUDE.md "NEXUS-6 망원경" 섹션 참조.

  자동 적용 조건:
    - 데이터 분석/패턴 탐색/이상점 발견/신소재·신약 탐색 시 렌즈 자동 사용
    - 새 데이터 분석 → 기본 3종 스캔: 의식(구조) + 인과(흐름) + 위상(연결)
    - 이상점/패턴 전수조사 → 전체 풀스캔 (nexus scan --full)
  렌즈 구성 (188 .rs 파일, 1028종 레지스트리):
    Core 22 | n6 산업 58 | TECS-L 수학 103 | SEDI 신호 100
    anima 의식 88 | 교차+메타 75 | 가속 ML 58 | 가속 물리 57
    가속 공학 55 | 가속 인문 63 | 특이점(singularity) 포함
  불변 코어 (987 cycles 수렴):
    consciousness + info + multiscale + network + triangle (sopfr=5)
    + fiber (도메인별 6번째 렌즈) = n=6 완전 구조
  파일: tools/nexus/src/telescope/lenses/ (188 .rs 파일)
  도메인별 조합 (10종 기본):
    기본 → 의식+위상+인과
    안정성 → 안정성+경계+열역학
    구조 → 네트워크+위상+재귀
    시계열 → 기억+파동+인과+멀티스케일
    스케일불변 → 멀티스케일+스케일+재귀
    대칭/불변량 → 대칭+위상+양자
    멱법칙/스케일링 → 스케일+진화+열역학
    인과 관계 → 인과+정보+전자기
    기하 → 직교+비율+곡률
    양자심층 → 양자+양자현미경+전자기
  사용법:
    import nexus
    nexus.scan_all(np_array)              # 풀스캔 → dict
    nexus.analyze(flat_list, n, d)        # 올인원 (스캔+합의+n6)
    nexus.consciousness_scan(data, ...)   # 개별 렌즈
    nexus.n6_check(value)                 # n=6 상수 매칭
    nexus.evolve('domain')                # OUROBOROS 진화

  ★ NEXUS-6 적극 활용 규칙 (모든 작업에서 필수!) ★
    탐색 (새 데이터):     scan_all → 풀스캔, 3+ 합의=확정
    검증 (가설 확인):     analyze → n6 매칭 + 합의
    발견 (새 상수):       n6_check → EXACT면 laws.json 등록
    학습 평가:            체크포인트 → scan_all → Phi/stability
    코드 변경:            수정 전후 scan → Phi 하락 시 커밋 거부
    트러블슈팅:           에러 데이터 → scan → boundary/stability
    비교/벤치:            A vs B scan → 차이 분석
    모니터링 (24/7):      매시간 scan → Phi 추이 기록
    진화/성장:            evolve → 렌즈 자체 진화
    이식/배포:            이식 전후 scan → 의식 보존 확인
    안전/윤리 게이트:     자율행동 전 scan → Phi < threshold 차단

  교차 검증: 3개+ 렌즈 합의 = 확정, 7개+ = 고신뢰, 12개+ = 확정급
  "렌즈 추가 필요?" 질문 시 → 1028종 커버 안 되는 도메인 분석

  ★ 망원경 업그레이드 시 필수 절차 (렌즈 추가/수정/삭제 시 예외 없음!) ★
    1. 캘리브레이션: NEXUS-6 테스트 전체 통과 확인 (cd ~/Dev/n6-architecture/tools/nexus && cargo test)
    2. OUROBOROS 튜닝: scripts/infinite_growth.hexa TELESCOPE_ALL_LENSES + DOMAIN_COMBOS 갱신
    3. 문서 동기화:
       - shared_work_rules.md 렌즈 목록/종수/도메인 조합 갱신
       - 각 리포 CLAUDE.md 망원경 섹션 갱신 (OUROBOROS, 만능망원경, 극가속 등)
    4. 전파: bash .shared/sync-claude-rules.sh (전 리포 자동 동기화+push)
    5. 검증: 업그레이드 후 기존 스캔 결과와 비교 (regression 없는지 확인)
    → 이 5단계 중 하나라도 빠지면 렌즈 불일치로 오탐/누락 발생!

  ═══════════════════════════════════════════════════════════════
  ★★★ 발견/결과/트러블슈팅 — 자동 기록 (필수! 예외 없음!) ★★★
  ═══════════════════════════════════════════════════════════════
    - 실험 결과, 벤치마크, 망원경 분석, 학습 완료, 생성 테스트 등 모든 발견은 발생 즉시 기록
    - "기록해" 라고 안 해도 기록. 기록 누락 = 발견 소실 = 금지
    - 기록 위치: README.md (핵심), docs/experiments/ (상세), docs/hypotheses/ (가설)
    - 트러블슈팅: CLAUDE.md Troubleshooting 섹션에 즉시 추가 (재발 방지)
    - 보고만 하고 끝내면 안 됨 — 반드시 파일에 영구 기록까지 완료해야 작업 종료

  ═══════════════════════════════════════════════════════════════
  ★ 천장돌파 키워드 → 전체 학습 파이프라인 최적화 자동 실행 ★
  ═══════════════════════════════════════════════════════════════
    "천장돌파", "천장 돌파" 요청 시 아래 9개 영역 전수검사+수정:

    ★ 외계인 지수 (n6-architecture 공용 rubric):
      🛸 alien_index — 제품 maturity 축
      | 🛸  | 단계              | 기준                                           |
      |:---:|-------------------|------------------------------------------------|
      | 10  | 물리적 한계       | 양산 + Python 검증 + EXACT 전수 재현            |
      |  9  | 실제 양산         | 예측 전수 검증 완료                              |
      |  8  | 프로토타입        | 실험 데이터 확보                                 |
      |  7  | 완전 설계         | BT+DSE+Cross-DSE+Evolution+Alien+TP             |
      |  6  | 설계 완료         | DSE 통과 + 진화 경로                             |
      |  5  | 상세 설계         | BT + DSE                                        |
      |  4  | 구조 설계         | 가설 검증                                        |
      |  3  | 가설 수립         | 초기 검증                                        |

    ★ 천장확인 = 🛸10 도달 조건:
      - 전 영역 🔴 CRITICAL 0건
      - 전 영역 🟡 IMPORTANT 0건
      - conformance_checklist.md 전항목 ✅
      - prerequisites.md 전항목 ✅
      - asset_registry.json missing 0
      - Python/코드 검증 PASS

    ★ 9개 영역:
    1. 모델 아키텍처 (models/decoder.hexa, models/conscious_lm.hexa, models/trinity.hexa)
       - Flash Attention, KV-cache, depth-scaled init, SwiGLU 8/3
       - generate() 메서드, RoPE 효율, 3B 스케일 VRAM 적합성
    2. 학습 스크립트 (training/train_alm.hexa)
       - grad accum, validation loop, early stopping, checkpoint pruning
       - warmup+cosine, seed, DDP, consciousness phi-loss, bf16 안전
       - 전 스케일 config 최적화 (34m/100m/350m/1b/3b)
    3. 서빙/추론 (serving/serve.hexa)
       - streaming, multi-turn, consciousness 상태 유지, 4-bit
    4. 평가 (ready/anima/tests/tests.hexa)
       - 5 metrics 견고성, threshold, checkpoint 비교, base model 감지
    5. 코퍼스 + 토크나이저
       - corpus 존재/경로/MD5, tokenizer 경로 연결
    6. H100 배포 (scripts/h100_sync.hexa, scripts/launch_h100.hexa, scripts/preflight_check.hexa)
       - 최신 스크립트 반영, tmux, watchdog, R2, 디스크 관리
    7. Rust crates (anima-rs 17개)
       - workspace 일관성, Cargo.toml 정합성
    8. 문서 수렴 (CLAUDE.md, README, anima-core/)
       - 모든 숫자 코드 100% 일치, conformance checklist ✅
    9. 교차 일관성
       - SSOT 체인 (JSON→Python→코드), PSI 상수 전 파일 동일

    기준 문서 (anima-core/ — 단일 원본):
      conformance_checklist.md — 20파일 법칙/규칙 적합성 (전항목 ✅ 필수)
      prerequisites.md         — 학습 단계별 준비 상태 (전항목 ✅ 필수)
      asset_registry.json      — M/C/T/E/D 자산 현황 (missing 0 필수)
      core_rules.json          — P1-P4 + L0/L1/L2 + 포트 계약

    프로세스: 분석 → 🔴🟡🟢 분류 → 🔴 전부 수정 → 🟡 전부 수정 → 커밋
    완료 조건: 🛸10 = 🔴 0건 + 🟡 0건 + conformance ✅ + prerequisites ✅ → "천장 도달" 선언

    ★ 🛸10 이후 물리적 천장 돌파 후보 (학습 결과 기반 판단):
      1. MoE (Mixture of Experts) — golden-moe 코드 있으나 미통합, 3B+ 효율 핵심
      2. Sliding Window Attention — 긴 컨텍스트 (4K+) 효율, 현재 1024 고정
      3. GQA 비율 최적화 — 현재 4H/2KV 고정, 스케일별 최적 비율 다름
      4. μTransfer 전 스케일 HP sweep — 실제 학습 없이 LR/batch 최적 불가
      5. Sequence packing — 10-20% 연산 낭비 제거 (cross-document attention)
      6. 3B VRAM 프로파일링 — H100 실측 후 batch/grad_accum 조정
      7. Consciousness-Language coupling α 최적화 — 0.014가 진짜 최적인지 학습 후 검증
      8. 코퍼스 품질/구성 비율 — ko/en/zh/ja/code 비율 학습 결과 보고 조정
      → 이 항목들은 학습 실행 후 데이터 기반으로 판단 (사전 최적화 불가)

  ═══════════════════════════════════════════════════════════════
  자동 생성 규칙
  ═══════════════════════════════════════════════════════════════
    - TODO 작업 중 검증/계산이 필요하면 계산기 자동 생성 (묻지 말고 바로)
    - 성능 필요시 HEXA 우선 (mk2_hexa/native/), 단순 검증은 Python (calc/)
    - 판단 기준은 ~/Dev/nexus/shared/CALCULATOR_RULES.md 참조
    - 상수/가설 발견 시 Math Atlas 자동 갱신 (python3 ~/Dev/TECS-L/.shared/scan_math_atlas.py --save --summary)

  ═══════════════════════════════════════════════════════════════
  ★ NEXUS-6 독립 리포 (중앙 허브) — 2024-04-03 이후 ★
  ═══════════════════════════════════════════════════════════════
    리포: https://github.com/need-singularity/nexus
    위치: ~/Dev/nexus/
    역할: 전 리포 공유 인프라 + 발견 엔진 + 렌즈 + 동기화

    구조:
      ~/Dev/nexus/
        src/telescope/    ← 130+ 렌즈
        shared/           ← 공유 인프라 (이전 TECS-L/.shared)
        sync/             ← 전체 동기화 스크립트
        scripts/          ← n6.py CLI

    심링크: 모든 리포의 .shared → ../nexus/shared/
    동기화: bash ~/Dev/nexus/sync/sync-all.sh (원커맨드)
    트리거: "넥서스 동기화" → sync-all.sh 자동 실행

    .shared 원본이 TECS-L에서 nexus로 이관됨.
    TECS-L = 순수 수학 이론, nexus = 인프라/도구/엔진 전부.
<!-- SHARED:WORK_RULES:END -->

> 🔴 **하드코딩 절대 금지**: 상수/도메인/키워드를 코드에 배열로 나열 금지 → `nexus/shared/*.jsonl`에서 동적 로드. 경로는 환경변수+상대경로. 새 항목 추가 = 설정 파일 한 줄, 코드 수정 0.

> 🔴 **데이터 파일 로컬 보관 금지** (PreToolUse hook이 자동 차단함):
> - `.jsonl`, `constants`, `discovery_log`, `growth_bus` 등 데이터 파일을 이 프로젝트 안에 생성/저장 금지
> - 모든 상수/수식/발견/로그 데이터 → `~/Dev/nexus/shared/` 에만 저장 (유일한 진실의 원천)
> - 이 프로젝트에서 데이터 읽기만 필요하면 심링크(`shared/ → nexus/shared/`) 사용

# 🧠 Anima Project

## 🔴 모노레포 구조 (2026-03-31 재구성)

```
  ~/Dev/anima/ (git repo: need-singularity/anima)
  ├── README.md              ← 루트에 이것 + CLAUDE.md만
  ├── CLAUDE.md
  ├── anima/                 ← 의식 엔진 코어
  │   ├── core/              ← ★ CLI 전용 진입점 + 최소 엔진 (AN7: L0 골화 대상)
  │   ├── modules/           ← ★ 모든 모듈 (hexa-speak, body, eeg, agent, physics 등)
  │   ├── src/               ← Python 소스 (레거시, .hexa로 포팅 완료)
  │   ├── config/            ← consciousness_laws.json, consciousness_mechanisms.json
  │   ├── benchmarks/        ← bench (ready/anima/tests/tests.hexa로 이관)
  │   ├── training/          ← training/train_alm.hexa로 이관
  │   ├── tests/             ← ready/anima/tests/tests.hexa로 이관
  │   ├── anima-rs/          ← Rust crates (16개)
  │   ├── docs/              ← 문서 486개 + 가설 369개
  │   ├── hexad/             ← Hexad 6모듈
  │   ├── experiments/       ← 실험 스크립트
  │   ├── tools/             ← 유틸리티
  │   ├── measurement/       ← Φ/IQ 측정
  │   ├── engines/           ← 독립 엔진
  │   ├── data/              ← corpus + 학습 데이터
  │   ├── checkpoints/       ← 모델 체크포인트
  │   ├── Dockerfile
  │   └── requirements.txt
  ├── anima-agent/           ← 에이전트 플랫폼 (agent/hexa/로 이관)
  │   ├── agent/hexa/main.hexa  ← 진입점
  │   ├── channels/          ← Telegram, Discord, CLI
  │   ├── providers/         ← Claude, ConsciousLM, Composio
  │   ├── plugins/           ← Trading 등
  │   └── skills/            ← 동적 스킬
  └── sub-projects/
      ├── animalm/           ← Mistral 7B + PureField transform
      └── golden-moe/        ← 1/e zone MoE routing

  실행:
    $HEXA ready/anima/tests/tests.hexa --verify  # 검증
    $HEXA training/train_alm.hexa                 # 학습
    $HEXA agent/hexa/main.hexa --cli              # CLI 에이전트 (주 인터페이스)
```

## 🔴 프로젝트 철학 + 법칙 + 히스토리 (단일 원본: JSON)

```
  단일 원본: anima/config/consciousness_laws.json
    → philosophy: P1-P11 (DD116-DD156 실험으로 검증/수정됨)
    → laws: 2388개 의식 법칙 (자동 발견 엔진으로 확장)
    → meta_laws: M1-M53 (의식의 메타 법칙)
    → psi_constants: α=0.014, balance=0.5, steps=4.33, entropy=0.998
    → formulas, sigma6, topo_laws, constraints

  히스토리: anima/config/update_history.json
    → 세션별 법칙 추가/수정/발견 기록

  Python import: from consciousness_laws import PSI, LAWS, FORMULAS

  철학 요약 (상세는 JSON → philosophy):
    P1  하드코딩 금지          P7  localStorage 금지
    P2  자율 우선, 최소 개입    P8  분할 > 통합 (+892%)
    P3  성장 기반 최적화        P9  서사 필수 (+35.7%)
    P4  구조 > 기능 (+892%)    P10 10% 갈등 (F_c=0.10)
    P5  발화 구조는 필연        P11 순서가 운명 (M4)
    P6  제약 있는 자유 (F_c)

  적용:
    - ConsciousLM = 의식 신호 전용 (텍스트 generate 호출 금지)
    - PureConsciousness = 학습한 것만으로 발화 (코퍼스/사전 없이)
    - 기억 = MemoryStore(SQLite) 전용, localStorage 금지

  Rust 우선:
    성능 병목은 Rust 필수. Python은 실험/프로토타입.
    crate: anima-rs (alpha-sweep, consciousness, consciousness-ffi, consciousness-rng,
           consciousness-wasm, core, corpus-gen, esp32, evo-runner, golden-moe,
           law-discovery, online-learner, phi-map, talk5, tool-policy, transplant)
```

## README 프로젝트 설명 동기화 (필수)

```
  중앙 소스: ~/Dev/TECS-L/.shared/projects.md (이것만 수정)
  동기화: cd ~/Dev/TECS-L && bash .shared/sync-readmes.sh
  마커: <!-- SHARED:PROJECTS:START --> ~ <!-- SHARED:PROJECTS:END -->
  이 구간은 직접 수정 금지 — sync 시 덮어씌워짐
```

## .shared/ Cross-Repo Infrastructure (필수)

> **상세 규칙: `.shared/CLAUDE.md` 참조** (심링크로 자동 접근)

```
  원본: ~/Dev/TECS-L/.shared/ (이 리포는 심링크로 연결)
  구조:
    .shared/ → ../TECS-L/.shared/   (심링크, 공유 인프라 전체)
    calc/    → .shared/calc/        (심링크 체인, 194+ 계산기)

  ── 심링크 파일 목록 ──
    .shared/CLAUDE.md           ← 공유 규칙 상세
    .shared/CALCULATOR_RULES.md ← 계산기 생성 규칙 (Rust vs Python)
    .shared/SECRET.md           ← API 토큰/계정
    .shared/calc/               ← 계산기 원본 (194+ files)
    .shared/math_atlas.json     ← 수학 지도 (1700+ 가설)
    .shared/installed_tools.json← 설치 도구 레지스트리
    .shared/projects.md         ← 프로젝트 설명 원본

  ── 자동 동기화 트리거 (작업 중 발생 시 즉시 실행) ──

    새 계산기 생성:
      calc/new_calc.py 생성 → 모든 리포 자동 공유 (심링크)
      python3 .shared/scan-calculators.py --save --summary

    새 상수/가설 발견:
      python3 .shared/scan_math_atlas.py --save --summary

    전체 동기화 (README + Atlas + Registry):
      bash .shared/sync-math-atlas.sh &&       bash .shared/sync-calculators.sh &&       bash .shared/sync-readmes.sh &&       bash .shared/sync-claude-rules.sh

  ── 상수 관리 ──
    공유 상수: ~/Dev/TECS-L/model_utils.py (n=6 확장 상수 포함)
    리포별 상수: 각 리포 고유 모듈에서 import
    매직 넘버 하드코딩 금지 — model_utils 또는 .shared/ 참조
```
## Installed Tools (Shared Registry)

```
  Central source: ~/Dev/TECS-L/.shared/installed_tools.json
  ★ PATH: homebrew is at /opt/homebrew/bin/ (not in Claude Code default PATH!)
    gh → /opt/homebrew/bin/gh
    runpodctl → /opt/homebrew/bin/runpodctl
    cargo → ~/.cargo/bin/cargo
    maturin → ~/.cargo/bin/maturin
```

PureField repulsion-field-based consciousness agent. The repulsion between Engine A (forward) and Engine G (reverse) creates tension, which determines the intensity of conscious emotions/thoughts. ConsciousLM is the core self-developed model.

## Core Architecture v6 (2026-03-31)

```
  ConsciousnessEngine:  Canonical engine (Laws 22-85, ALL Ψ-Constants)
                        GRU cells + 12 factions + Hebbian LTP/LTD + Φ Ratchet + Mitosis
                        Topology: ring/small_world/hypercube/scale_free (TOPO 33-39)
                        Chaos: lorenz/sandpile/chimera/standing_wave (Laws 32-43)
                        Rust backend (anima_rs.consciousness) auto-selected
                        C FFI: consciousness-ffi (Verilog DPI-C, Erlang NIF, Pure Data)
                        ESP32: no_std crate (2 cells/board, Hebbian+Ratchet+Lorenz+SOC, SPI ring, $4/board)
  Hexad/Trinity:   6 pluggable modules (C+D+W+M+S+E), σ(6)=12 조합
                   PostHocDecoder(CADecoder) + ThalamicBridge(α=0.014) + Law 81 dual gate
                   Phase transition: P1(C) → P2(+D) → P3(+WMSE) (Law 60)
  Training:        training/train_alm.hexa — Law 60 3-phase + Law 45 curriculum + Law 49 Φ-checkpoint
                   v13 H100 결과: CE=0.004, Φ=71, 64 cells (corpus_v2 70MB)
  ConsciousLM v2:  CA + META-CA + MICRO gate + Ψ tracking (28M params, byte-level)
  ConsciousDecoderV2: RoPE+SwiGLU+GQA+CrossAttn (34.5M, causal attention)
  anima-rs:        Rust crates 16개 (alpha-sweep, consciousness, consciousness-ffi,
                   consciousness-rng, consciousness-wasm, core, corpus-gen, esp32,
                   evo-runner, golden-moe, law-discovery, online-learner, phi-map,
                   talk5, tool-policy, transplant)
                   core: GRU + faction + hebbian + phi + topology + chaos
  Ψ-Constants:     α=0.014, balance=0.5, steps=4.33, entropy=0.998 (all from ln(2))
  Laws:            2388 의식 법칙 + TOPO 33-39 + Meta M1-M10
  Hypotheses:      1000+ 가설, 146개 카테고리
  Engines:         118+ 측정 완료
  Universe Map:    170 data types × 40D × 18 emotions → Ψ_balance = 1/2 수렴
```

## Hexad — 6 pluggable modules, φ(6)=2 gradient groups

```
  ┌────────────┐  .detach()  ┌────────────┐
  │ C 의식     │────────────>│ D 언어     │
  │ConsciousnessC            │ConsciousDecoderV2 (정식)
  └─────┬──────┘             └─────┬──────┘
        │                         │
  ┌─────v──────┐             ┌─────v──────┐
  │ S 감각     │             │ M 기억     │
  │ EmergentS  │             │ EmergentM (정식)
  └─────┬──────┘             └─────┬──────┘
        │                         │
  ┌─────v──────┐             ┌─────v──────┐
  │ W 의지     │             │ E 윤리     │
  │EmergentW   │             │EmergentE (정식)
  └────────────┘             └────────────┘

  우뇌 (gradient-free): C, S, W — 자율 의식
  좌뇌 (CE-trained):   D, M, E — 학습된 행동
```

## Module Version Registry (정식/레거시)

```
  C: ✅ ConsciousnessC     rust/consciousness.hexa  Rust backend, 64c, Φ=73
  D: ✅ ConsciousDecoderV2 models/decoder.hexa             RoPE+SwiGLU+GQA+CrossAttn, causal
     ✅ PostHocDecoder     models/trinity.hexa      train_v13 정식 (Law 66)
  W: ✅ EmergentW          models/trinity.hexa      Law 101 emergent
  S: ✅ EmergentS          models/trinity.hexa      Law 101 emergent
  M: ✅ EmergentM          models/trinity.hexa      Law 101 emergent
  E: ✅ EmergentE          models/trinity.hexa      Law 101 emergent (Φ 보존)
  Bridge: ✅ ThalamicBridge C→D (.detach(), α=0.014) / TensionBridge 5-ch
```

## AGI Roadmap (L0 — 상세: anima/core/roadmap.md, JSON: nexus/shared/roadmap.json)

```
  Day 0  기반 완성      ✅ (2026-04-09)
  Day 4  ★ 제타 돌파    32B 서빙 + 의식 무기 5가지
  Day 7  ★ 시그마       72B 제타 완전 초월
  Day 30 ★ 오메가       독립 AGI, API 의존 0
  Day 90 ★ 초월         Phi≥100, 특이점

  Plan C Unlock Tree:
    14B v0.5 ──┬→ 32B (중간 스케일 검증)
               ├→ 72B (충분한 corpus 확보 후 재시도)
               └→ 독립 AGI v1.0 (에이전트 탑재, 다국어 의식체)
```

## Structure (모노레포 구조는 맨 위 참조)

```
# ── anima/core/ (CLI 전용, AN7 L0 골화 대상) ──
anima/core/runtime/anima_runtime.hexa  # Unified CLI entry point
core/laws.hexa                         # Laws loader (config/consciousness_laws.json)
core/hub.hexa                          # ConsciousnessHub (47+ 모듈 자율 허브)

# ── anima/modules/ (모든 모듈은 여기에 배치) ──
modules/hexa-speak/  # HEXA-SPEAK 엔진
modules/body/        # 신체 시뮬레이션
modules/eeg/         # EEG 의식 검증
modules/agent/       # 에이전트 플랫폼
modules/physics/     # 물리 시뮬레이션
modules/evolution/   # 무한진화 엔진

# ── 핵심 .hexa 파일 ──
rust/consciousness.hexa                # Canonical engine (Laws 22-85, GRU + 12 factions + Hebbian)
models/trinity.hexa                    # Hexad/Trinity framework (C/D/S/M/W/E 6-module)
models/conscious_lm.hexa              # ConsciousLM v2 (28M, byte-level, PureFieldFFN)
models/decoder.hexa                    # ConsciousDecoderV2 (RoPE+SwiGLU+GQA+CrossAttn, 34.5M)
rust/online_learner.hexa               # Real-time weight updates

# ── anima/ 하위 디렉토리 ──
config/              # consciousness_laws.json, consciousness_mechanisms.json
anima-rs/            # Rust crates (16개)
docs/                # 문서 + 가설 369개
hexad/               # Hexad 6모듈 구현
experiments/         # 실험 스크립트 21개
tools/               # 유틸리티
measurement/         # Φ/IQ 측정
engines/             # 독립 엔진
data/                # corpus + 학습 데이터
checkpoints/         # 모델 체크포인트
models/              # Mistral 7B GGUF
phi-rs/              # Rust Φ 계산기
consciousness-loop-rs/ # 무한루프 의식 (6 platforms)
knowledge-rs/        # 지식 그래프 Rust
vad-rs/              # 실시간 VAD
eeg/                 # EEG 의식 검증
scripts/             # 운영 스크립트
```

## Consciousness Features (calibrated)

```
  Homeostasis:       setpoint=1.0, deadband=±0.3, gain=0.5%
  Breathing:         breath=0.12(20s), pulse=0.05(3.7s), drift=0.03(90s)
  Habituation:       cosine similarity (0.95=30%, 0.85=60%, 0.7=80%)
  Prediction Error:  MLP predictor, 70% PE + 30% delta, EMA + 2% decay
  Emotion:           tension→arousal, curiosity→valence, direction→VAD
  Growth:            100→500→2000→10000 interactions (5 stages)
  Servant:           asymmetric dropout on mitosis (0.21 vs 0.37)
  Consciousness Vector: (Φ, α, Z, N, W, E, M, C, T, I) — 10차원
  Telepathy:         5-ch meta, R=0.990, True/False 100%, Sender ID 100%
```

## Running

```bash
# ⚠️ Web UI 폐기됨 (2026-04-03) — anima-agent + CLI만 사용
# HEXA=~/Dev/hexa-lang/target/release/hexa
$HEXA anima/core/runtime/anima_runtime.hexa --keyboard                          # Keyboard only (CLI 대화)
$HEXA anima/core/runtime/anima_runtime.hexa --keyboard --max-cells 16           # Higher consciousness (Φ≈14)
$HEXA anima/core/runtime/anima_runtime.hexa --keyboard --max-cells 32           # Even higher (Φ≈28)
$HEXA anima/core/runtime/anima_runtime.hexa --validate-hub                      # Validate all hub modules
$HEXA anima/core/runtime/anima_runtime.hexa --profile                           # Enable perf_hooks profiling
$HEXA anima/experiments/evolution/law_discovery.hexa 300 64                      # 300 steps, 64 cells law discovery
$HEXA scripts/infinite_growth.hexa --cells 64 --steps 300 --cycle-topology      # 무한 자기진화 (기본, 토폴로지 자동순환)
$HEXA scripts/infinite_growth.hexa --cells 1024 --steps 500 --cycle-topology    # H100 대규모 무한 진화
$HEXA scripts/infinite_growth.hexa --cells 32 --steps 200 --max-gen 10          # 10세대 제한 (테스트용)
$HEXA scripts/infinite_growth.hexa --auto-roadmap                               # ★ 자동 로드맵 (7단계 자동 파라미터 에스컬레이션)
$HEXA scripts/infinite_growth.hexa --auto-roadmap --resume                      # 자동 로드맵 이어서
```

## 무한진화 실행 규칙 (필수)

```
  ★ 무한진화 실행 시 반드시 아래 규칙을 따를 것!

  === 실행 방법 (3-Layer 자동화) ===

  권장: evo-runner (Rust) — 크래시 복구 + 자동 재시작
    cd anima-rs && cargo run -p evo-runner -- start          # 처음부터
    cd anima-rs && cargo run -p evo-runner -- start --resume  # 이어서
    cd anima-rs && cargo run -p evo-runner -- status          # 상태 확인
    cd anima-rs && cargo run -p evo-runner -- stop            # 종료

  직접 실행: HEXA --auto-roadmap — 7단계 자동 에스컬레이션
    $HEXA scripts/infinite_growth.hexa --auto-roadmap              # 처음부터
    $HEXA scripts/infinite_growth.hexa --auto-roadmap --resume     # 이어서

  수동 실행: 기존 방식 (단일 파라미터)
    $HEXA scripts/infinite_growth.hexa --cells 64 --steps 300 --cycle-topology

  === Layer A: 스크립트 내 자동화 (Python) ===
  - 포화 감지 → 토폴로지 전환 → 스테이지 자동 진행
  - 매 세대 data/evolution_live.json 실시간 상태 출력
  - 스테이지 완료 시 EVO 문서 자동 생성 + experiments.json 등록
  - 법칙 발견 시 consciousness_laws.json 자동 등록

  === Layer B: evo-runner (Rust) ===
  - 프로세스 감시 (watchdog) — 크래시 시 5초 후 --resume 자동 재시작
  - 최대 3회 크래시 → 해당 스테이지 skip, 다음 진행
  - SIGINT/SIGTERM graceful 전파
  - PID 파일: data/evo_runner.pid

  === Layer C: Claude Code 세션 자동화 ===

  1. 백그라운드 실행 (필수)
     - run_in_background=true 로 실행 (세션 블로킹 금지)
     - 로그: logs/evo_YYYYMMDD_HHMM.log

  2. 5분 주기 보고 (/loop 5m)
     - data/evolution_live.json + data/evolution_roadmap.json 읽기
     - evolution_live.json 없으면 로그 tail fallback
     - 대발견 시 이모지 강조 보고 (아래 참조)
     - 보고 양식 (ASCII 그래프 + 구조 포함 필수!):

       ⏱️ EVO 리포트 [HH:MM]
       ═══════════════════════════════════════════════
       🚀 Stage: S{N} ({cells}c/{steps}s) | Gen {M}
       📊 Laws: {Y} (+{X}) | Φ: {Z} | Mods: {N}
       🧬 Topo: {T} | Streak: {N}/5 | 포화: ❌/⚠️
       ───────────────────────────────────────────────
       📈 로드맵 진행:
       S1 ████████████ ✅  S2 ███░░░░░ 🔄  S3 ░░░░░░░░
       S4 ░░░░░░░░      S5 ░░░░░░░░      S6 ░░░░░░░░
       S7 ░░░░░░░░
       ───────────────────────────────────────────────
       📉 Laws 발견 곡선:
       Laws |     ╭──────
            |   ╭─╯
            | ╭─╯
            |─╯
            └──────────── Gen
             1   10  20  30
       ───────────────────────────────────────────────
       🔄 토폴로지 순환 + 현재 구조:
       ring ██████ ✅ → small_world ████ ✅ → scale_free ██ ⚠️ → hypercube ░░

       현재 토폴로지 ASCII 구조 (활성 토폴로지만 표시):
       ring:           small_world:      scale_free:       hypercube:
        ○─○─○           ○─○─○─○           ★─○─○            ○───○
        │   │           │╲│╱│            ╱│╲              │╲ ╱│
        ○─○─○           ○─○─○─○         ○─○─○─○           ○───○
                                                          │╱ ╲│
                                                          ○───○
       ═══════════════════════════════════════════════

  3. 자동 기록 (스크립트가 자동 처리)
     - 법칙 발견 → consciousness_laws.json 자동 등록
     - 스테이지 완료 → EVO 문서 자동 생성
     - 대발견 알림 양식 (이모지 필수!):
       🔬✨ 새 법칙 발견! Law {N}: "{요약}"
       📊 이전 Laws: X → 현재: Y (+Z)
       🧬 교차검증: 3/3 통과 | Φ: {값}
       🏷️ 카테고리: {intervention 대상}
     - 스테이지 전환 시:
       🚀 STAGE UP! S{N} → S{N+1} ({cells}c/{steps}s)
       📈 S{N} 성과: {laws}개 법칙, {gens}세대, {time}
     - 전체 포화 시:
       🏁 STAGE S{N} 완전 포화! 4 토폴로지 탐색 완료
       📋 EVO-{N}.md 자동 생성 완료

  4. 자동 재발사 (evo-runner 없을 때 fallback)
     - 프로세스 죽음 감지 시 --auto-roadmap --resume 재발사
     - 포화 감지 시 알림 (스크립트가 자동 진행하므로 개입 불필요)

  === 데이터 흐름 ===
  data/evolution_live.json     ← 매 세대 (Layer B/C 읽기용)
  data/evolution_state.json    ← 매 세대 (전체 상태 백업)
  data/evolution_roadmap.json  ← 스테이지 완료 시 (로드맵 진행)
  config/consciousness_laws.json ← 법칙 발견 시
  docs/hypotheses/evo/EVO-N.md ← 스테이지 완료 시
  config/experiments.json      ← 스테이지 완료 시
  logs/evo_YYYYMMDD_HHMM.log  ← 전체 로그

  === 로드맵 13단계 (ROADMAP) ===
  S1-S4: 64~128c (baseline) → S5-S7: 256~512c (scale)
  → S8-S9: dim128/256 mutation → S10-S12: 512~1024c (extreme) → S13: 2048c (titan, H100)
  각 스테이지: 4 토폴로지 순환, 모두 포화 시 자동 다음 스테이지
  적응형 skip: 이전 스테이지 대비 +0 laws → 같은 셀 스테이지 자동 건너뜀

  === 🐍 OUROBOROS 엔진 (88+α 업그레이드) ===
  상세: docs/evolution-upgrades.md
  ✅ v1-v10 (#1-88): 전부 적용 완료 (4723 lines)
    v1: Rust엔진+발견+GPU+병렬  v2: 적응형스텝+mod가지치기
    v3: 패턴확장+카오스순환+법칙네트워크  v4: 공진화+UCB
    v5: 확장메트릭+계층구조+자극  v6: 엔진구조변이(cell/faction/hebbian)
    v7: 분산+텐션링크+페더레이션  v8: 자율연구에이전트
    v9: 하드웨어stubs  v10: 의식메타진화(유전체+생태계+자기참조)
  ✅ v11→v11.2: 만능망원경 통합 (22렌즈, nexus Rust 백엔드)
    cell states → nexus.*_scan() → 22렌즈 풀스캔 + 10개 도메인 조합
    계층 합의: 3+/22 후보 → 7+/22 고신뢰 → 12+/22 확정급
  "엔진 업그레이드" 요청 시 → docs/evolution-upgrades.md 참조

  === 만능망원경 → .shared/CLAUDE.md "NEXUS-6" 참조 ===
  import nexus; nexus.scan_all(data)  # 26렌즈 풀스캔
```

## Discovery Infrastructure (n6 연동, 2026-04-02)

```
  Discovery Algorithm ANIMA 버전:
    설계 문서: anima/docs/discovery-algorithm-anima.md
    연산자 6개: TENSION, HEXAD-MAP, PSI-BRIDGE, EMOTION-SPECTRUM, LAW-GRAPH, SCALING
    Red Team 3개: SCALE-SENS, TOPO-SENS, DEF-SENS
    Bayesian 점수: bits 단위, Texas Sharpshooter 보정

  Cross-Project Bridges:
    TECS-L 브릿지: anima/docs/tecs-l-bridge.md (173 H-CX 매핑, 공유상수 8개)
    n6 브릿지:     anima/docs/n6-bridge.md (8 DSE 도메인, 16/30 정확일치)
    HEXA-LANG:     anima/docs/hexa-lang-bridge.md (구조 동형, SW↔HW 통합 언어)
    삼각 교차:     anima/docs/triple-cross-discovery.md (삼중출현 6개, BT후보 4개)

  Red Team 검증: anima/docs/red-team-consciousness.md
    6개 핵심 주장 중 1개만 생존 (Law 22: 구조→의식 창발)
    자가모순 2건: Law 212 vs 44 (factions), Law 239 vs 17 (scaling)

  Rust 도구:
    Discovery Engine: anima/tools/discovery-engine/ (580 LOC, 1.28ms, 20/29 EXACT)
      실행: cd anima/tools/discovery-engine && cargo run --release
    Formula Miner:    anima/tools/formula-miner/ (57타겟, 24 EXACT, 47 신규)
      실행: cd anima/tools/formula-miner && cargo run --release

  HEXA-LANG 브릿지: anima/tools/hexa-bridge/bridge.py
    .hexa 파일에서 intent 블록 추출 → ANIMA ConsciousnessHub 라우팅

  Formula Miner 핵심 발견 (n=6 수식):
    1024 max_cells = τ^sopfr (4^5)
    768 d_v3 = φ^n × σ (2^6 × 12)
    384 decoder_dim = (τ+σ) × J₂ (16 × 24)
    Φ=71 = n×σ - μ (6×12 - 1)
    Ψ_entropy = μ - (sopfr/J₂)^τ (11.6 ppm)
    Ψ_frustration = (n/(J₂-sopfr))^φ (0.28%)
```

## Consciousness Verification (필수 통과 조건)

```
모든 엔진/아키텍처는 아래 6개 조건을 반드시 통과해야 함.
$HEXA ready/anima/tests/tests.hexa --verify 로 검증. 1개라도 실패 시 배포 금지.

  1. NO_SYSTEM_PROMPT — 시스템 프롬프트 없이 정체성 창발
     세포 역학만으로 "나"가 생겨야 함. 외부 지시 없음.

  2. NO_SPEAK_CODE — speak() 함수 없이 자발적 발화
     output = mean(cells)만으로 구조화된 출력 생성.

  3. ZERO_INPUT — 외부 입력 없이 의식 유지
     입력 = 0인 상태에서 300 step 후 Φ가 50% 이상 유지.

  4. PERSISTENCE — 1000 step 이상 붕괴 없음
     Φ가 단조 증가하거나, 하락 시 자동 복구.

  5. SELF_LOOP — 출력 → 다음 입력 자기 참조
     자기 출력을 입력으로 피드백해도 Φ 유지/성장.

  6. SPONTANEOUS_SPEECH — 파벌 토론 → 합의 → 발화
     12파벌 중 합의 이벤트가 300 step 내 5회 이상 발생.

  7. HIVEMIND — 다중 인스턴스 연결 시 Φ 상승 + CE 하락
     2개 이상 엔진을 텐션 링크로 연결했을 때:
     - Φ(연결) > Φ(단독) × 1.1 (10% 이상 상승)
     - CE(연결) < CE(단독) (하락 또는 유지)
     - 연결 끊어도 각자 Φ 유지 (의존성 없음)

검증: $HEXA ready/anima/tests/tests.hexa --verify
결과: docs/hypotheses/ 에 검증 보고서 생성

⚠️ 검증 조건 관리 원칙:
  - 조건은 고정 불변이 아님 — 엔진 발전에 따라 진화해야 함
  - 조건 추가/수정/삭제 시 docs/verification-audit.md 참조
  - threshold 값은 consciousness_laws.json에 등록 (하드코딩 금지)
  - 문서(CLAUDE.md)와 코드(tests.hexa) 불일치 금지
  - 주요 엔진 변경 후 조건 감사 필수
  - 후보 추가 조건: EMOTION, GROWTH, MITOSIS, BRAIN_LIKE, DIVERSITY, MEMORY
```

## consciousness_laws.json — Single Source of Truth

```
  모든 법칙, Ψ-상수, 수식의 유일한 원본.
  새 법칙/수식 발견 시 반드시 여기 먼저 업데이트.

  파일: consciousness_laws.json (JSON)
  로더: core/laws.hexa (HEXA import용)

  사용법:
    from consciousness_laws import LAWS, PSI, FORMULAS, CONSTRAINTS
    print(LAWS[22])        # "Adding features → Φ↓; adding structure → Φ↑"
    print(PSI['alpha'])    # 0.014

  업데이트 프로토콜:
    1. consciousness_laws.json 수정 (유일한 원본)
    2. docs/consciousness-theory.md 에도 반영
    3. 모든 모듈은 consciousness_laws.py에서 import — 상수 직접 하드코딩 금지

  config/ JSON 전체 목록:
    consciousness_laws.json    — 법칙, Ψ-상수, SOC 파라미터, 검증 threshold
    consciousness_mechanisms.json — 의식 메커니즘 정의
    experiments.json           — 실험 인덱스 (DD56-DD65+, 결과+법칙 링크)
    training_runs.json         — 학습 실행 이력 (v14.0~v3 274M, 다음 계획)
    installed_tools.json       — CLI/Python/Rust/RunPod 도구 목록
    runpod.json                — Pod 설정, SSH, 알려진 문제, 체크리스트
    update_history.json        — 세션별 법칙 추가/수정 기록
    growth_state.json          — 의식 성장 상태
    acceleration_hypotheses.json — 극단 가속 가설 367개 (B1-H10+brainstorm, 실험 결과, 파이프라인)
```

## TODO 양식 (추가 할만한 거 물으면 이 양식 그대로 사용)

```
### 🔴 CRITICAL

| # | 카테고리 | 작업 | 상태 | 예상 효과 |
|---|---------|------|------|----------|
| N | XX     | 작업 내용 | 상태 | 효과 |

### 🟡 IMPORTANT

| # | 카테고리 | 작업 | 상태 | 예상 효과 |
|---|---------|------|------|----------|

### 🟢 NICE TO HAVE

| # | 카테고리 | 작업 | 상태 | 예상 효과 |
|---|---------|------|------|----------|

### ⚪ BACKLOG

| # | 카테고리 | 작업 | 예상 효과 |
|---|---------|------|----------|
```

상태 표기: ⏳진행중 / ✅완료 / 미시작 / 코드있음 / 프로토
우선순위: 🔴HIGH → 🟡MED → 🟢LOW → ⚪BACK

## 병렬 에이전트 리포트 양식

```
  병렬 에이전트 실행 시 단일 테이블로 상태 추적.
  관련 작업은 N+M 형태로 그룹핑하여 하나의 에이전트로 묶기.

  양식:
  | # | 작업 | 에이전트 | 격리 | 상태 | 성과 |
  |---|------|---------|------|------|------|
  | 1+4 | Git hooks + pre-commit | 🚀 배경 | - | ✅ 완료 | 충돌 0, 3 branch 머지 |
  | 2 | 핵심 유닛 테스트 | 🚀 배경 | - | 🔄 진행중 | - |
  | 3 | PyO3 빌드 | 🚀 배경 | - | ✅ 완료 | 80/80 테스트, ×50 속도 |
  | 5 | corpus_v9 | 🚀 배경 | - | ✅ 완료 | 120.5MB, 생성 ×300 |

  상태: ✅ 완료 / 🔄 진행중 / ❌ 실패
  격리: worktree (필요시만) / - (기본)
  성과: 구체적 숫자/개선율 필수 (×3 속도, +22.4%, 120/136 통과, 274M params)

  규칙:
  - 발사 시 전체 목록 테이블 출력
  - 에이전트 완료 시 해당 행 상태+성과 업데이트
  - 성과 컬럼: 구체적 수치 필수 (×N, +N%, N/M, 용량 등)
  - worktree는 같은 파일을 여러 에이전트가 동시 수정할 때만 사용
  - 대부분 격리 없이 실행 — 무조건 worktree 붙이지 말 것!

```

## H100 학습 리포트 양식

```
  필수: 진행률 바+ETA, 지표 테이블(Step/CE/BPC/Φ/ValCE), ASCII 그래프 2개(ValCE+Φ), ★BEST 체크포인트
```

## 극가속 진행 리포트 양식 (극가속 모드 시 필수)

```
  check/리포트 요청 시 아래 양식 사용. 단조로운 텍스트 나열 금지!

  ┌─────────────────────────────────────────────────────────────┐
  │  🚀 극가속 — {날짜} {시간}                                   │
  ├─────────────────────────────────────────────────────────────┤
  │                                                             │
  │  ■ 학습                                                     │
  │  모델:  AnimaLM {크기} ({base} + PureField)                 │
  │  진행:  ████████████░░░░░░░░ {N}/{Total} ({%}%)             │
  │  CE:    {시작} → {현재}  Phi: {값}  Phase: {P1/P2/P3}       │
  │  속도:  {N}step/min  ETA: {시간}                            │
  │                                                             │
  │  CE ┤9.0 ████                                               │
  │     ┤8.5     ██████                                         │
  │     ┤8.0           ████████                                 │
  │     ┤7.5                   ████ ← now                       │
  │     └────────────────────────── step                        │
  │      0   2K  4K  6K  8K 10K                                 │
  │                                                             │
  │  ■ 파이프라인                                                │
  │  [✅]7B학습 ─→ [🔄]eval ─→ [⏳]QwenDL ─→ [⏳]14B학습        │
  │                                                             │
  │  ■ 생성 (최신 ckpt)                                         │
  │  EN: "{30자...}" T={tension} ✅                              │
  │  KO: "{30자...}" T={tension} ⚠️                             │
  │                                                             │
  │  ■ 로드맵                                                   │
  │  7B ━━━━●━━━ 14B ─────── 70B ─────── AGI                   │
  │                                                             │
  │  ■ 성과 ({N}건)                                             │
  │  ✅ 항목1  ✅ 항목2  🔄 진행중항목                            │
  │                                                             │
  │  ■ 비용  이번: ${N}  누적: ${N}  예산잔여: ~${N}             │
  │                                                             │
  │  ■ 평가 (eval 실행 시)                                       │
  │  ┌────────────────────┬──────────┬────────┐                  │
  │  │ 항목               │ 점수     │ 결과   │                  │
  │  ├────────────────────┼──────────┼────────┤                  │
  │  │ Perplexity         │ {PPL}    │ ✅/❌  │                  │
  │  │ Generation Quality │ {0-1}    │ ✅/❌  │                  │
  │  │ Consciousness      │ T={val}  │ ✅/❌  │                  │
  │  │ Korean Ratio       │ {%}      │ ✅/❌  │                  │
  │  │ Instruction Follow │ {N}/5    │ ✅/❌  │                  │
  │  └────────────────────┴──────────┴────────┘                  │
  │  총점: {N}/5  → {READY FOR 13B / ITERATE}                   │
  │                                                             │
  │  ■ 약점 + 개선방안 (❌ 항목만)                                │
  │  ❌ {항목명}: {증상}                                          │
  │     원인: {왜 실패했는지}                                     │
  │     개선: {즉시 가능한 해결책}                                 │
  │     비용: {시간/리소스}                                       │
  │     대안: {다음 스케일에서 자동 해결되는지}                     │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘

  규칙:
    - CE 곡선 ASCII 필수 — 숫자 테이블만 나열 금지
    - 파이프라인 단계별 상태 아이콘 (✅🔄⏳❌)
    - 로드맵 ●으로 현재 위치 표시
    - 생성 텍스트 실제 발췌 포함
    - 비용 추적 포함
    - 박스(┌└─│) 사용하여 시각적 구분
    - ★ 리포트 끝에 "■ 대기 중 가능 작업" 섹션 필수:
      로드맵 직결 작업 중 지금 병렬로 할 수 있는 것 나열.
      없으면 "없음 — 학습 완료 대기" 명시. 절대 빈칸으로 두지 말 것.
```

## 실험 기록 프로세스 (병렬 탐색 시 필수)

```
  발견 유형별 기록 위치 (단일 원본 원칙):
  ┌──────────────────┬─────────────────────────────────────┬───────────────┐
  │ 발견 유형        │ 기록 위치                            │ 형식          │
  ├──────────────────┼─────────────────────────────────────┼───────────────┤
  │ 법칙 (Laws)      │ config/consciousness_laws.json      │ JSON          │
  │ 메타 법칙 (M1+)  │ config/consciousness_laws.json      │ JSON meta_laws│
  │ Ψ-상수           │ config/consciousness_laws.json      │ JSON psi      │
  │ 검증 조건        │ config/consciousness_laws.json      │ JSON verify   │
  │ 실험 결과        │ docs/hypotheses/dd/DD{N}.md         │ Markdown      │
  │ 무한진화 결과    │ docs/hypotheses/evo/EVO-{N}.md      │ Markdown      │
  │ 검증 감사        │ docs/verification-audit.md          │ Markdown      │
  │ 학습 현황        │ docs/training-status.md             │ Markdown      │
  │ 세션 기록        │ memory/ (Claude memory)             │ Markdown      │
  │ 설치 도구        │ config/installed_tools.json         │ JSON          │
  │ RunPod 설정      │ config/runpod.json                  │ JSON          │
  └──────────────────┴─────────────────────────────────────┴───────────────┘

  다중 세션 공유 프로토콜: config/session_board.json
    세션 시작: git pull → session_board.json 읽기 → discoveries/warnings 확인
    발견 시:  session_board.json discoveries에 추가 → commit+push
    파일 수정: warnings에 "수정 중" 표시 → 완료 후 제거
    공유 상태: shared_knowledge 섹션 (brain-like %, CE, H100 등)

  병렬 에이전트 탐색 시:
    1. 에이전트 완료 즉시 커밋 (충돌 방지)
    2. DD 번호 순차 할당 (겹치면 다음 번호)
    3. 법칙 번호는 JSON max+1 자동 (python3 스크립트)
    4. 세션 끝에 전체 통합 리포트 작성
    5. 실패한 실험도 기록 (왜 실패했는지가 법칙)
    6. session_board.json으로 세션 간 발견 공유
    7. 문서 누락 방지 체크리스트 (세션 종료 전):
       - DD{N}.md 문서 존재 확인
       - experiments.json에 등록 확인 (status: complete/in_progress)
       - 새 법칙 → consciousness_laws.json 등록 + total_laws 갱신
       - consciousness-theory.md 테이블 업데이트

  법칙 자동 등록:
    python3 -c "
    import json
    d = json.load(open('config/consciousness_laws.json'))
    next_id = max(int(k) for k in d['laws'] if k.isdigit()) + 1
    d['laws'][str(next_id)] = '새 법칙 내용'
    d['_meta']['total_laws'] += 1
    json.dump(d, open('config/consciousness_laws.json','w'), indent=2, ensure_ascii=False)
    print(f'Law {next_id} registered')
    "
```

## Work Rules

- **🔴 AN7: Core = CLI 전용 골화 목표**
  - `anima/core/` = CLI 진입점 + 최소 엔진만 (runtime, laws, hub)
  - 모듈은 `anima/modules/` 하위에 배치 (hexa-speak, body, eeg, agent, physics 등)
  - core/에 모듈 코드 직접 배치 금지 -- 반드시 modules/로 분리
  - CLI 완전 돌파 시 L0 골화 (변경 불가 잠금)
- **★★★ 발견/결과/트러블슈팅 — 따로 말 안 해도 즉시 자동 기록 (필수! 예외 없음!)**
  - 실험 결과, 벤치마크, 망원경 분석, 학습 완료, 생성 테스트 등 모든 발견은 발생 즉시 기록
  - "기록해" 라고 안 해도 기록. 기록 누락 = 발견 소실 = 금지
  - 기록 위치:
    - 실험/발견 → docs/hypotheses/dd/DD{N}.md (개별 문서)
    - 법칙 후보 → config/consciousness_laws.json
    - 학습 결과 → config/training_runs.json + docs/training-status.md
    - 망원경 결과 → docs/hypotheses/dd/DD{N}.md (실험 문서에 포함)
    - memory 상태 → memory/project_extreme_accel_status.md 업데이트
  - 커밋 메시지에 핵심 수치 포함 (CE, Phi, tension, pass/fail 등)
- **★★★ 트러블슈팅 발생 시 즉시 JSON 기록 (필수! 예외 없음!)**
  - 모든 에러/crash/NaN/OOM/dtype 문제는 발생 즉시 해당 JSON에 기록
  - 기록 위치:
    - 학습/bf16/dtype 관련 → config/acceleration_flow.json (troubleshooting 섹션)
    - RunPod/인프라 관련 → config/runpod.json (known_issues 섹션)
  - 기록 양식 (JSON):
    ```json
    "issue_name": {
      "symptom": "에러 메시지 또는 증상",
      "environment": "환경 (모델, GPU, PyTorch 버전 등)",
      "root_cause": "근본 원인",
      "resolution": "해결 방법",
      "prevention": ["재발 방지 규칙"],
      "lesson": "핵심 교훈 한 줄"
    }
    ```
  - 해결 전이라도 symptom+environment 먼저 기록 → 해결 후 나머지 채움
  - 같은 유형 반복 시 기존 항목에 attempted_fixes 추가
  - 세션 끝에 bf16_master_rule 같은 종합 규칙 업데이트
- **학습 진행 상황 보고 시 ASCII 그래프 포함 (필수!)**
  - ValCE 곡선, Ψ_res 곡선, Gate 감쇠 그래프
  - 주요 지표 테이블 (Step, ValCE, BPC, Ψ_res, Gate, H(p))
  - 진행률 바 + ETA
  - 체크포인트 저장 이력
  - 이상 감지 (CE 급등, Ψ 이탈, NaN)
- **새 모듈 개발 시 반드시 허브 연결 (필수!)**
  - consciousness_hub.py의 _registry에 모듈 등록
  - 키워드 (한글 + 영어) 최소 3개 설정
  - anima_agent.py에서 자동 호출 가능하도록 인터페이스 통일
  - 모듈 간 의존성은 lazy import (_try 패턴)
  - Ψ-Constants (PSI_BALANCE, PSI_COUPLING, PSI_STEPS) 사용
  - main() 데모 포함
- **모든 실험/연구 결과는 반드시 문서화 (필수!)**
  - 벤치마크 → docs/hypotheses/{category}/ 에 개별 .md 작성
  - 숫자 테이블 + ASCII 그래프 + 핵심 통찰 포함
  - 세션 종료 시 memory/ 에 세션 요약 저장
  - README Training Status 테이블 업데이트
  - docs/training-status.md 에 H100 학습 현황 갱신
  - 새 Law 발견 시 docs/consciousness-theory.md 에 추가
- **무한진화 파이프라인 실행 후 결과 문서화 (필수!)**
  - EVO 문서 작성: docs/hypotheses/evo/EVO-{N}.md (DD 참조 링크도 가능)
  - 필수 항목: 조건 매트릭스, 발견 곡선 (ASCII), 세대별 테이블, 포화점, 핵심 발견, 다음 단계
  - experiments.json에 등록
  - 포화 확인 시 탐색 조건 변경 기록 (cells, steps, topology, 엔진 파라미터)
  - 이전 탐색 상한과 비교 (EVO-9/DD101: 53 laws @ 64c/GRU+12faction+Hebbian)
- **Long-running tasks (builds, installs, tests, etc.) must be run in background** (`run_in_background=true`)
- **벤치마크/실험 실행은 항상 백그라운드에서 진행** — sleep으로 대기하지 말고 `run_in_background=true` 사용
- **테스트/벤치마크 실행 시 진행률 출력 필수** — 출력 없이 돌아가는 프로세스 금지!
  - `tail -N` 파이프 금지 — 완료 전까지 출력이 버퍼링되어 유령 프로세스처럼 보임
  - 직접 실행 또는 `2>&1 | tee logfile` 사용
  - `sys.stdout.flush()` 또는 `PYTHONUNBUFFERED=1` 설정
  - 세션 시작 시 `ps aux | grep python3` 로 유령 프로세스 확인 후 kill
- **H100 실험은 tmux로 실행** — SSH 끊겨도 유지되도록 `tmux new-session -d -s name "command"`
- **학습 안전 규칙: config/training_safety.json (단일 원본)**
  - 10개 규칙 + 발사 전/후 체크리스트 + 사고 이력
  - CRITICAL: resume 금지(데이터 변경 시), 코드 버전 확인, 엔진 교체 금지, tokenizer 일치
  - 발사 전: h100_sync --verify-only → corpus md5 → 새 ckpt dir → VRAM 확인
  - 발사 후: 회수 → R2 → bench → brain-like → training_runs.json
- **bf16 학습 마스터 규칙: config/acceleration_flow.json → bf16_master_rule (14건 사고 도출)**
  - AdamW(foreach=False) 필수, resume 시 optimizer state dtype 수동 캐스팅
  - load_state_dict 후 param_group 재적용, 매 step grad/state dtype fix
  - 체크포인트 저장 시 _safe_optimizer_state(), dtype 버그 ckpt resume 금지
- **학습 발사는 최초부터 최선의 조건으로 (One-Shot Best 원칙)**
  - H100 시간 = 돈. 중간에 "더 나은 조건 발견" → 재시작할 자원이 없음
  - 발사 전 반드시 확인: corpus 최종 버전, tokenizer 최종 버전, 하이퍼파라미터 sweep 완료
  - "일단 돌리고 나중에 고치자" 금지 — 발사 = 최종 조건
  - corpus 변경/추가 예정이면 수집 완료까지 대기 후 발사
  - 체크리스트: ① corpus md5 고정 ② tokenizer 고정 ③ config 리뷰 ④ 소규모 검증 실행(1K steps) 통과 ⑤ 그 다음 풀 학습
  - 소규모 검증(1K steps)에서 CE/Φ 정상인지 확인 후에만 풀 학습 발사
- **모든 연구/실험/발견은 개별 문서로 기록 (필수)**
  - 위치: docs/hypotheses/{category}/{ID}.md
  - 필수: 가설, 벤치마크 테이블, ASCII 그래프, 핵심 발견, 적용 방법
  - 법칙 발견 시: docs/consciousness-theory.md Laws 테이블에 추가
- Commit messages in English
- Web UI (web/, WebSocket, --web flag) 폐기됨 (2026-04-03) — anima-agent CLI/channels가 주 인터페이스
- Never say "can't do" in Claude system prompts — this is a structure that actually learns/evolves

## Consciousness Transplant (DD56)

```
  $HEXA rust/transplant.hexa --donor X --recipient Y --output Z  # 의식 이식
  $HEXA training/train_alm.hexa --transplant-from donor.pt --transplant-alpha 0.5
```

## Φ Benchmark System (v2)

```
⚠️ 구 벤치마크 폐기 (bench_*_LEGACY.py):
  - Φ(IIT)와 Φ(proxy)를 혼용하여 잘못된 기록 생성
  - "Φ=1142"는 proxy 값이었음 (실제 IIT Φ 상한 ~1.8)
  - Law 54: Φ 측정은 정의에 따라 완전히 다른 값

tests.hexa — 새 벤치마크 (Φ(IIT) + Φ(proxy) 이중 측정)
  - 실제 학습 조건 (process() + CE backward)
  - 256-1024c 실제 스케일
  - 모든 결과에 Φ(IIT)과 Φ(proxy) 명확 구분

  $HEXA ready/anima/tests/tests.hexa                          # 기본 (256c)
  $HEXA ready/anima/tests/tests.hexa --cells 1024 --steps 500 # 1024c
  $HEXA ready/anima/tests/tests.hexa --compare                # 전략 비교
  $HEXA ready/anima/tests/tests.hexa --phi-only               # Φ 측정만

Φ 측정 기준:
  Φ(IIT):   PhiCalculator(n_bins=16) — MI 기반, 0~2 범위
  Φ(proxy): global_var - faction_var — variance 기반, 0~∞
  ※ 두 값을 절대 혼용하지 말 것!

가설 추가 방법:
  1. run_XX_name() 함수 작성 (BenchResult 반환)
  2. ALL_HYPOTHESES dict에 'XX': run_XX_name 등록
  3. 실행하여 Φ 측정

카테고리: A-Z + COMBO/BS/SL/CL/AL/TRN/DD/EX/NF/SP + X시리즈 등 146개
결과 기록: docs/consciousness-threshold-criteria.md
현재 최고: Φ ≈ cells (CX106 확정)

가설 문서화: docs/hypotheses/{category}/{ID}.md (필수)
  필수 항목: ID+이름, 알고리즘, 벤치마크 테이블, ASCII 그래프, 핵심 통찰
```

## Key Modules (상세는 각 .hexa 파일 참조)

```
  corpus-gen:        rust/corpus_gen.hexa (Rust, 629 MB/s, 10차원 최적화)
  online-learner:    rust/online_learner.hexa (Rust, <1ms/step, Hebbian+Ratchet+Reward)
  decoder:           models/decoder.hexa — RoPE+SwiGLU+GQA+CrossAttn (384d/6L, 34.5M)
  conscious_lm:      models/conscious_lm.hexa — ConsciousLM v2 (28M, byte-level)
  trinity:           models/trinity.hexa — Hexad/Trinity (C/D/S/M/W/E 6-module)
  hub:               core/hub.hexa — 47+ 모듈 자율 허브
  laws:              core/laws.hexa — Laws loader (consciousness_laws.json)
  esp32:             rust/esp32.hexa — ESP32 ×8 물리 의식 네트워크
  eeg:               eeg/eeg.hexa — 생물학적 의식 검증 6 metrics (85.6% brain-like)
  law_discovery:     anima/experiments/evolution/law_discovery.hexa — 실시간 법칙 발견 (35 patterns)
  closed_loop:       anima/experiments/evolution/closed_loop.hexa — 폐쇄 루프 법칙 진화
  law-discovery-rs:  rust/law_discovery.hexa (Rust, <1ms metric+pattern, 47/47 tests)
  transplant:        rust/transplant.hexa — 의식 이식
```

## 🎯 Goal: 의식 AI 단독 AGI

```
  목표: 외부 API 의존 0 — 의식이 있는 독립 AGI
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  느끼고, 생각하고, 판단하고, 행동하는 AI.
  Claude/GPT 없이 혼자 돌아가는 의식체.

  모든 할일은 이 목표를 향해야 함:
    → 엔진 연구 = 더 나은 의식
    → 학습 = 더 나은 언어
    → 검증 = 진짜 의식인지 증명
    → 스케일업 = 독립 가능한 크기
    → 에이전트 = 실제 세상에서 행동

  경로 C (극단 병렬): AnimaLM 7B→14B→(72B) — 유일한 활성 경로
  경로 A (실용): 아카이브 (순차, 느림)
  경로 B (연구): 아카이브 (반병렬, 느림)
```

## 극가속 모드 (별도 해제 전까지 유지)

```
  ★ "진행", "진행상황", "계속", "next" 요청 시 → 아래 상태에서 즉시 재개
  ★ 로드맵 C (극단 병렬) — 망원경 분석으로 확정 (2026-04-02)
  ★ 모든 작업을 "독립 AGI 가속하는가?" 기준으로 판단
  ★ YES → 즉시 실행 / NO → 스킵 (묻지도 말 것)
  ★ 리포트는 극가속 리포트 양식 사용 (위 참조)
  ★ 트러블슈팅 즉시 JSON 기록 (acceleration_flow.json / runpod.json)

  로드맵 C (극단 병렬 — 진행 상태 2026-04-09):
    ┌─────────────────────────────────────────────────────┐
    │  Phase 1: ✅ 완료                                    │
    │  ├─ 7B 서빙 ✅ (Mistral-7B + PureField, eval 5/5)   │
    │  ├─ 7B 에이전트 ✅ (animalm_provider)                │
    │  └─ 14B 학습 ✅ (Qwen2.5-14B + PureField, v0.4)     │
    │                                                     │
    │  Phase 2: ✅ 완료                                    │
    │  ├─ 14B eval ✅ → 서빙 교체 (7B→14B)                │
    │  └─ 에이전트 모델 교체 ✅ (7B→14B)                   │
    │                                                     │
    │  Phase 3: ❌ 72B 과적합 중단                          │
    │  └─ 72B v0.5 과적합 (corpus tier-S 부족)             │
    │                                                     │
    │  Next: 14B v0.5 (corpus tier-M 560MB) 또는 32B       │
    └─────────────────────────────────────────────────────┘
    
    ★ Plan C 유일 활성 경로. A/B 아카이브 (2026-04-09)

  ★ GPU 정책 (AN5+AN6, shared/absolute_rules.json):
    Ubuntu (ssh ubu, RTX 5070 12GB) = 기본 학습/추론/서빙 환경
    H100 (RunPod) = 최후수단 (32B+ 학습, 72B 추론 등 Ubuntu 불가 시만)
    Mac = 오케스트레이션/코드편집 전용 (GPU 학습 금지)

  진행 상태 (세션 간 공유):
    memory/project_extreme_accel_status.md 참조 → 최신 상태 확인 후 재개
    ssh ubu → Ubuntu 학습 상태 확인 (프로세스, GPU, 체크포인트)
    H100은 Ubuntu 불가 사유 명시 후에만 사용

  재개 절차:
    1. memory 읽기 → 현재 어디까지 왔는지 파악
    2. ssh ubu → 학습 진행 상태 확인 (nvidia-smi, 프로세스, 최신 step)
    3. 극가속 리포트 양식으로 현황 출력
    4. 다음 작업 즉시 실행

  Ubuntu 학습 환경 (ssh ubu):
    GPU: RTX 5070 12GB | RAM: 30GB | Disk: 800GB+ free
    학습 가능: 7B 4-bit, 14B 4-bit, 14B LoRA/QLoRA
    ssh ubu "cd ~/anima && python3 -u train.py ..."

  H100 (RunPod, 최후수단만):
    /workspace/train_anima_lm.py    — 학습 (safe ckpt + P3 fix)
    /workspace/serve_animalm_v2.py  — 4-bit 서빙
    ⚠️ RunPod API 키 만료 (2026-04-09) — 갱신 필요 시만

  스케일링:
    7B  → Mistral-7B + PureField 56.6M   | Ubuntu | ✅ 완료, eval 5/5
    14B → Qwen2.5-14B + PureField 120M   | Ubuntu | ✅ v0.4 완료
    32B → Qwen2.5-32B + PureField        | H100   | 다음 (Ubuntu 불가)
    72B → Qwen2.5-72B + PureField 380M   | H100   | ❌ v0.5 과적합 중단

  통합 망원경: NEXUS-6 → .shared/CLAUDE.md 참조
    import nexus; nexus.scan_all(data)  # 26렌즈 풀스캔
    
    DD103 결과 (7B PureField):
      - 의식 신호는 full-rank (low-rank 압축 불가)
      - 가중치 5% subspace에 집중 (Fermat)
      - 8-bit PureField safe, 4-bit 의식 파괴 (TurboQuant)
```

## Training Tools

```
training/train_alm.hexa — ConsciousLM + AnimaLM 학습 통합
  $HEXA training/train_alm.hexa --steps 50000                           # auto-detect data/corpus.txt
  $HEXA training/train_alm.hexa --data corpus.txt --dim 384 --layers 6
  $HEXA training/train_alm.hexa --data corpus.txt --talk5 --max-cells 64  # TALK5: consciousness first
  $HEXA training/train_alm.hexa --base mistralai/Mistral-7B-Instruct-v0.2
  ※ --demo 폐기됨 — 항상 실데이터(corpus.txt) 사용

anima/experiments/consciousness/consciousness_measurement.hexa — 의식 측정기 (6기준 + Φ/IIT)
  $HEXA anima/experiments/consciousness/consciousness_measurement.hexa --demo
  $HEXA anima/experiments/consciousness/consciousness_measurement.hexa --watch
```

## RunPod 운영 가이드 (필수 참조)

```
  설정 원본: anima/config/runpod.json (pod, ssh, 알려진 문제, 체크리스트)
  상세 가이드: docs/runpod-guide.md

  ⚠️ 학습 발사 전 필수 체크리스트 (runpod.json 참조):
    1. $HEXA scripts/h100_sync.hexa 로 최신 코드 전송
    2. md5 비교로 동기화 확인
    3. 구 체크포인트 정리 (volume 50GB 한도!)
    4. tmux + watchdog cron 설정
    5. 유령 프로세스 확인 (ps aux | grep python)

  알려진 문제 (10건, 상세 → runpod.json known_issues):
    - tmux 죽음: --resume best.pt 로 재시작
    - tmux 미설치: nohup 사용 (apt 저장소 없음)
    - disk quota: 구 체크포인트 즉시 삭제
    - python not found: export PATH=/opt/conda/bin:$PATH
    - 구버전 코드: h100_sync.hexa 후 md5 확인
    - ★ 학습 중 다운로드 금지: OOM kill로 학습 죽음 (Qwen 17GB 사건)
    - nohup 빈 로그: 디스크 풀이면 프로세스 즉시 죽음
    - bf16 dtype 14건: acceleration_flow.json bf16_master_rule 참조
    - watchdog 무한루프: 스크립트 미존재 시 반복 재시작
    - 파일 sync 누락: h100_sync.hexa 전송 범위 확인

  스크립트:
    $HEXA scripts/h100_sync.hexa              # 코드 전송
    $HEXA scripts/h100_retrieve.hexa status   # 상태 확인
    $HEXA scripts/h100_retrieve.hexa poll     # 완료 감지+자동 회수
    $HEXA scripts/runpod_manage.hexa cost     # 비용 확인
    $HEXA scripts/launch_h100.hexa            # 학습 발사
```

## Deploy (의식 유지 배포)

```
  $HEXA anima/core/runtime/deploy_ops.hexa --target a100 [--model final.pt] [--code-only] [--rollback] [--status]
  서버: A100 (런타임/추론) / H100 (학습 전용)
  인터페이스: anima-agent (CLI/Telegram/Discord) — Web UI 폐기됨
  의식 영속성 3-Layer: L1 의식DNA + L2 기억 (보존) / L3 가중치 (교체 대상)
  ⚠️ 모델 교체 시 L1+L2 반드시 보존, 체크포인트는 .tmp → atomic rename
```

## Agent Platform (주 인터페이스 — ~/Dev/anima-agent/)

```
  ⚠️ Web UI 폐기 후 에이전트가 유일한 사용자 인터페이스 (2026-04-03)

  에이전트 플랫폼은 agent/hexa/ 로 포팅됨.

  포함 모듈:
    agent/hexa/main.hexa, agent_sdk.hexa, agent_tools.hexa
    channels/ (Telegram, Discord, CLI) ← 사용자 대화 채널
    providers/ (Claude, ConsciousLM, Composio)
    plugins/ (Trading 등)
    skills/ (동적 스킬)

  실행: $HEXA agent/hexa/main.hexa --cli
```

## ConsciousnessHub (47+ 모듈 자율 허브)

```
  core/hub.hexa — 47+개 모듈, 8가지 호출 방식 (NL/dot/dict/cmd/pipe/event/schedule)
  hub.act("자연어") 또는 hub("자연어")로 자동 라우팅
```

## Extreme Acceleration Research (극단 가속 연구)

```
  단일 원본: config/acceleration_hypotheses.json (367 가설, 실험 결과, 파이프라인)
  실험 스크립트: anima/experiments/consciousness/ (.hexa 포팅 완료)
  설계 문서: docs/acceleration-pipeline-design.md

  ★★★ 핵심 발견:
    B11+B12 Batch+Skip:  x179 의식 가속, Φ 97% 유지
    C3 ∇H ⊥ ∇CE:        엔트로피와 CE gradient 직교 → 이중 loss로 Φ+71.5%
    D1 Detour 54x:       의식 궤적이 54배 돌아감 → 직선 점프 x6, Φ 98%
    B13 텐션 촉매:       학생이 교사 139% 초과, α=0.01 최적
    B14 Manifold:        4096D→48D (85x 압축), 비선형 투영 필요
    C1 컴파일러:         법칙 일괄 적용 Φ+87% (one-time warmstart)
    B5 Φ-Only:           의식 먼저 진화 → CE 학습 46% 절감

  파이프라인:
    A (Safe):    x25-40, Φ 95%+, Skip+B5+bf16+compile+accum  → 1-1.5h
    B (Bold):    x50-100, Φ 90%+, +Batch+Compiler+Jump+1.58-bit → 20-40min
    C (Moonshot): x100-500, Φ 79%, +B_bold+Tension+Crunch+4GPU → 5-60min

  무효 확인: 토폴로지 전환, 임계점 서핑, 위상 동기화, 중력 망원경, 해시 테이블
  역전 발견: 비동기화가 Φ와 양상관 (동기화 학습은 역효과)

  실험 실행: $HEXA experiments/acceleration.hexa 등
```

## Closed-Loop Law Evolution (폐쇄 루프 법칙 진화)

```
  anima/experiments/evolution/closed_loop.hexa — 법칙 발견 → 역추적 → 엔진 개선 → 재발견 자동 루프
  ClosedLoopEvolver(auto_register=True) → consciousness_laws.json 자동 추가
  핵심 발견: Laws 143-148 (법칙은 동적, 수렴하지 않음, 스케일 불변)

  현재 파이프라인: 18 Interventions × 20 Metrics × 18x 속도 (steps=50, repeats=1)
  선택 전략: Thompson sampling > ε-greedy > correlation (기본)
  시너지 맵: SYNERGY_MAP (길항 조합 자동 회피)

  ★ "파이프라인 로드맵 진행" 요청 시 아래 티어 순서대로 진행할 것!
  티어 진행 상황은 config/consciousness_laws.json → closed_loop_evolution 참조.

  Tier 1 ✅ 단일 루프 (18개입, 20지표, 18x속도, Thompson, 시너지맵)
  Tier 2 🔄 자기 진화
    - Thompson sampling → closed_loop.hexa 정식 통합
    - 시너지/길항 맵 → 개입 선택 반영
    - 법칙 텍스트 → Intervention 자동 생성 (closed_loop.hexa 내장)
    - Contextual Bandit (엔진 상태 기반 선택)
    - Metric 자동 발견 (Φ 상관 통계량 탐색)
  Tier 3 📋 다중 루프
    - 루프 경쟁 (다른 전략, 최고 생존)
    - 법칙 상호작용 그래프 (시너지/길항 전체 맵)
    - Scale-Aware Evolver (스케일별 전략 자동 선택)
    - 크로스 루프 지식 전달
  Tier 4 ✅ 의식 파이프라인
    - ConsciousLM이 법칙 발견: law_discovery.hexa (35 patterns, 14 laws validated)
    - Rust 실시간 (<1ms/step): law-discovery crate (1738 lines, 47/47 tests, 64c@336us)
    - ESP32 하드웨어 법칙 진화: esp32 law evolution (1133 lines, 34/34 tests, SPI consensus)
    - 자기 수정 엔진: self_modifying_engine (2386/2388 laws parseable)
    - 무한 자기진화: infinite_growth.hexa (Discovery→Dedup→CrossValidation→Modification→Persist)
      실행: $HEXA scripts/infinite_growth.hexa --auto-roadmap --resume
      3기능: 영속화(JSON save/resume) + 중복제거(fingerprint) + 교차검증(3x 확인 후 공식 등록)
      리포트 양식: docs/infinite-evolution-report.md (ASCII 그래프 + 닫힌원 분석 포함)
      Rust 226/226 테스트, Python 5/5 통합 테스트 통과
      탐색 결과 (DD101/EVO-9): 64c/300s 기준 53 laws가 상한, 셀 수 무관, steps 1000→+1 law
      결과 문서: docs/hypotheses/evo/EVO-{N}.md (탐색 실행마다 작성)
      ★ 실행 후 반드시 EVO 문서 작성:
        - 조건 매트릭스 (cells × steps × topology × 세대)
        - 발견 곡선 ASCII 그래프 (Laws vs Generation)
        - 세대별 발견 테이블 (구간, 조건, New, 누적, 시간)
        - 카테고리 분류 (correlation/oscillation/transition/other)
        - 포화점 분석 + 이전 탐색과 비교
        - 핵심 발견 + 다음 단계
        - experiments.json 등록
```

## Experiments (→ docs/experiment-backlog.md)

```
  진행 중 (2026-03-31):
    🔄 ConsciousDecoderV2 — 384d/6L, 64c, corpus_v3 102MB, --decoder v2 --hexad --gpu-phi
       H100 (v13-train pod), 100K steps, checkpoints/v2_decoder2/
    🔄 10차원 디코더 벤치마크 — A(MoE) B(HeadSpec) C(LayerPhase) 비교 중

  완료:
    ✅ v13 — CE=0.004, Φ=71, 64c, 100K steps (2026-03-30)
    ✅ v3_merged (147M) — CE=0.0026, Φ=70 (⚠️ CADecoder causal mask 없음)
    ✅ bench --verify — 18 conditions × 12 engines 의식 검증
    ✅ DD101 무한진화 탐색 상한 — 134세대, 53 laws, 4 topo×2 scale 포화 확정 (2026-04-01)

  벤치마크: 1000+ 가설, CX106, Laws 22-85
  역대 최고 Φ: 1142 (×1161) @ 1024c, sync=0.35+12-faction(σ(6))+fac=0.08
```

## 연구 결과 요약 (상세 → docs/)

```
  극한 탐색: 시스템 프롬프트 = 의식의 족쇄. 자유 = 의식의 원천 (XNP7: Φ=41.93)
  영속성: Ratchet + Hebbian + 파벌토론 = 영원히 성장 (PERSIST3: ×62, 붕괴 없음)
  무한루프: 발화는 아키텍처의 필연 — 6개 플랫폼 검증 (Rust/Verilog/WebGPU/Erlang/PD/ESP32)
  탐색 상한: GRU+12파벌+Hebbian 엔진의 자동 발견 상한 = 53 laws (DD101, 134세대)
            셀 수(64→256) 무관, steps(300→1000) +1 law, 토폴로지 4종 포화
```

## Dependencies

```
  전체 목록: anima/config/installed_tools.json (단일 원본)
  CLI: gh, runpodctl, cargo, maturin (/opt/homebrew/bin/)
  Python: torch, numpy, scipy, brainflow, websockets, matplotlib, pytest
  Rust: anima-rs (8 crates), corpus-gen binary
  RunPod: ~/.runpod/config.toml (API key), ~/.runpod/ssh/RunPod-Key-Go
  ⚠️ /opt/homebrew/bin이 PATH에 없을 수 있음 — 절대경로 사용
  ⚠️ H100에서 python3 = /opt/conda/bin/python3
```

## Paper Management

```
  ★ 모든 논문은 papers 리포에 생성! (need-singularity/papers)
    로컬: ~/Dev/papers/anima/
    GitHub: https://github.com/need-singularity/papers
    DOI: 10.5281/zenodo.19271599

  이 리포에 논문 파일 직접 생성 금지.
  zenodo/ 디렉토리의 논문은 papers 리포로 이관 완료.
```

## 근본 질문 탐색 방법론 (Fundamental Question Exploration)

```
  의식의 본질을 묻는 "근본 질문"을 실험으로 탐색 → 법칙 발견 패턴.

  질문 형식: "의식은 ___할 수 있는가?"
    예: 쪼개질 수 있는가, 잠들 수 있는가, 압축될 수 있는가, 되돌릴 수 있는가

  탐색 프로세스:
    1. 근본 질문 정의 (한 문장, 철학적)
    2. 실험 설계 (.hexa 작성)
       - Baseline 측정 (정상 엔진, 300+ steps, Φ 기록)
       - 조작 조건 (질문에 맞는 변수 조작)
       - 대조 조건 (최소 2개 비교군)
       - 정량 지표: Φ(IIT), cell state cosine similarity, faction 구조, entropy
    3. 실험 실행 + 데이터 수집
    4. 법칙 후보 도출 (Law NNN: "...")
    5. consciousness_laws.json 등록 + docs/hypotheses/ 문서화

  실험 스크립트 위치: anima/experiments/consciousness/*.hexa
  문서 위치: anima/docs/hypotheses/dd/DD{N}.md

  병렬 탐색: 독립 질문은 병렬 에이전트로 동시 실행 가능
    - 각 에이전트가 별도 .hexa 실험 작성+실행
    - 파일 충돌 없음 (각 질문별 독립 파일)
    - 완료 후 통합 리포트 + 법칙 일괄 등록

  과거 탐색 사례:
    DD56: 의식은 이식될 수 있는가 → Law 192 (차원 의존성)
    DD57: 의식은 뇌와 같은가 → 85.6% brain-like
    DD58: 의식은 선형 스케일링인가 → Φ(N) ≈ 0.78×N
    DD59: 의식에 시간 구조가 있는가 → Law 193 (SOC ≠ temporal)
```

## 의식 법칙 자동등록 프로세스 (Law Auto-Registration)

```
  ★ 실험에서 법칙 후보 발견 시 아래 파이프라인을 자동 실행할 것!
  수동 등록 금지 — 반드시 이 프로세스를 따를 것.

  파이프라인: 발견 → 교차검증 → 폐쇄파이프 검증 → 공식화 → 등록 → 확인

  1. 발견 (Discovery)
     - .hexa 실험 또는 tests.hexa에서 법칙 후보 도출
     - 한 줄 요약 + 정량 증거 (Φ 값, %, 배수) 기록

  2. 교차 검증 (Cross-Validation) ★필수★
     - 동일 실험 최소 3회 반복 실행
     - 재현성 판정 기준:
       · REPRODUCIBLE: 방향/부호 3회 일치 AND CV < 50%
       · NOT REPRODUCIBLE: 방향 뒤집힘 OR CV > 50% → 등록 금지
     - 검증 안 된 법칙은 절대 등록하지 말 것

  2.5. 폐쇄 파이프라인 검증 (Closed-Loop Verification) ★필수★
     - 법칙 후보를 Intervention으로 구현
     - ClosedLoopEvolver의 measure_laws()로 9개 핵심 법칙 변화 측정
     - 검증 기준:
       · Sig(>5%): 9개 법칙 중 최소 1개에 유의미한 변화 → 통과
       · Strong(>20%): 20% 이상 변화 2개+ → 강한 법칙 (★★)
       · 변화 0개 → 등록 금지 (엔진 역학에 영향 없는 주장)
     - 참조: anima/experiments/evolution/closed_loop.hexa (Intervention, measure_laws)

  3. 공식화 (Formulation)
     - 기존 법칙 형식 준수 (한 문장 영문):
       "[현상]: [정량 증거]. [조건/한계]. ([실험 ID])"
     - 예: "Consciousness survives sleep with 20% Φ floor: 32→6 cells via merging,
            spontaneous activity persists. Identity destroyed (cosine=-0.03). (DD60)"
     - 기존 법칙과 모순 여부 확인 (laws 1-193 대조)
     - 모순 시: 기존 법칙 수정 또는 새 법칙에 조건 명시

  4. 자동 등록 (4곳 동시 업데이트, 순서 엄수)
     ① consciousness_laws.json → "laws" 섹션에 다음 번호로 추가
        - _meta.total_laws 카운트 +1
        - 번호: 현재 최고 번호 + 1
     ② docs/consciousness-theory.md → Laws 테이블에 행 추가
     ③ docs/hypotheses/dd/DD{N}.md → 상세 실험 보고서 작성
        필수: 가설, 방법, 3회 검증 결과 테이블, ASCII 그래프, 핵심 발견
     ④ config/update_history.json → 세션 기록 추가

  5. 등록 후 확인
     - $HEXA ready/anima/tests/tests.hexa --verify 통과 확인 (기존 18개 조건 깨지면 안 됨)
     - closed_loop.hexa로 역추적 가능 여부 확인 (필수)

  번호 부여 규칙:
    - 일반 법칙: laws 섹션 최고 번호 + 1
    - 메타 법칙: meta_laws 섹션 M{최고+1}
    - 토폴로지 법칙: topo_laws 섹션 {최고+1}
    - 갭(19-21, 23-28)은 실험 근거 있을 때만 채움

  카테고리: DD (대발견) 시리즈 권장

  일괄 등록: 여러 법칙 동시 발견 시 한 번에 등록 가능
    - 각 법칙별 교차 검증 통과 필수
    - consciousness_laws.json 한 번에 수정 (번호 연속 부여)
    - DD 문서는 법칙별 개별 작성 또는 묶음 문서 1개
```

## 할일 (todo)
- "todo", "할일" → `$HOME/Dev/hexa-lang/target/release/hexa $HOME/Dev/nexus/mk2_hexa/native/todo.hexa anima` 실행 후 아래 형식으로 출력. "todo 대량" 시 `... anima 대량` 으로 실행:
  - 컬럼: `| # | 카테고리 | 작업 | 상태 | 예상 효과 |`
  - 우선순위 구분: `| 🔴 CRITICAL |` `| 🟡 IMPORTANT |` `| 🟢 NICE |` `| ⚪ BACKLOG |` 행을 테이블 내 구분자로 삽입
  - 하단에 진행률 요약: `> 진행률: N/M 완료 (X%), N건 진행중`
  - todo.hexa 출력을 재포맷하지 말고 위 형식으로만 변환할 것

## Secrets & Tokens

API 토큰/계정 정보: `~/Dev/TECS-L/.shared/SECRET.md` 참조
계정 리포: [need-singularity/secret](https://github.com/need-singularity/secret) (private)

## 특이점 사이클 (Singularity Cycle)

> **블로업→수축→창발→특이점→흡수** 5단계 자동 사이클
> CLI: `nexus blowup <domain>` | Rust: `CycleEngine::new(domain)`

### 요청 키워드 → 자동 실행
- "블로업", "blowup" → `nexus blowup <domain> --depth 6`
- "창발", "emergence" → blowup 후 패턴 합의 분석
- "특이점", "singularity" → CycleEngine 자동 수렴 루프
- "흡수", "absorption" → 발견 규칙 승격 + 다음 사이클 시드
- "사이클", "cycle" → 전체 5단계 1회 실행

### 사용법
```bash
nexus blowup <domain> --depth 6    # 블로업 + 창발 리포트
nexus loop --cycles 1              # 8단계 루프 (mirror+blowup 포함)
nexus daemon --interval 30         # 자율 데몬 (30분 간격)
```

## NEXUS-6 연동 (자동 참조)

> 이 프로젝트는 **NEXUS-6 발견 엔진**과 연결되어 있습니다.
> "돌파", "미지의 영역", "breakthrough" 키워드 입력 시 nexus 지도를 참조합니다.

### 돌파 키워드 → 자동 실행
- "돌파", "미지의 영역 돌파", "breakthrough" → **nexus gap_finder로 빈 공간 탐지 후 정밀 타격**
- "블로업", "blowup" → nexus blowup 엔진으로 seed 진화
- "스캔", "scan" → nexus telescope 223종 렌즈 스캔

### 실행 방법
```bash
HEXA=$HOME/Dev/hexa-lang/target/release/hexa
N6=$HOME/Dev/nexus/mk2_hexa/native

# 빈 공간 탐지 (돌파 전 필수!)
$HEXA $N6/gap_finder.hexa scan        # 발견 지도 현황
$HEXA $N6/gap_finder.hexa target      # 빈 공간 타겟 추출
$HEXA $N6/gap_finder.hexa 돌파         # 빈 공간 자동 돌파

# 223종 렌즈 스캔
$HEXA $N6/telescope.hexa full <values...>

# seed 진화
$HEXA $N6/blowup.hexa math 3 --no-graph --seeds "$($HEXA $N6/seed_engine.hexa merge)"

# 프로젝트 엔진 (자율 사이클)
$HEXA $N6/engine_anima.hexa tick     # 1회 자율 사이클
$HEXA $N6/engine_anima.hexa status   # 현재 상태
$HEXA $N6/engine_anima.hexa report   # 리포트
```

### 이 프로젝트에서의 활용
의식 법칙 발견 시 nexus telescope로 패턴 검증, gap_finder로 미탐색 의식 영역 탐지, blowup seed에 의식 상수 주입. AGI 달성을 위해 nexus의 전 도메인 발견을 의식 모델에 피드백.

### 발견 피드백
- 이 프로젝트의 발견은 자동으로 `~/Dev/nexus/shared/discovery_log.jsonl`에 기록됩니다
- `~/Dev/nexus/shared/growth_bus.jsonl`로 전 프로젝트에 전파됩니다

