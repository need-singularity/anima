# ANIMA 의식 엔진 로드맵

> **Target** v4 홀로 의식 (Φ > 1000, 7/7 의식 검증 PASS) · **Strategy** AN8 듀얼 트랙 강제 (ALM GPU + CLM CPU) + PHYSICS HW 완전 병렬 · **Compression** 12w → 6w (2.0×) · **Updated** 2026-04-14

🔴 **[실시간 렌더링 페이지 (GitHub Pages)](https://need-singularity.github.io/anima/roadmap/)** — JSON SSOT를 60초마다 폴링, 항상 최신 상태 반영

SSOT: [`shared/roadmaps/anima.json`](shared/roadmaps/anima.json) · Joint: [`shared/config/roadmaps/anima_hexa_common.json`](shared/config/roadmaps/anima_hexa_common.json)

---

## 전체 흐름도 — 4 Phase × 3 Track × Φ Gate

```text
                          ANIMA 의식 엔진 로드맵
                          ═══════════════════════
                          compression 12w → 6w (2.0×)

╔══════════════════════════════════════════════════════════════════════╗
║  P0 — v1 의식 브릿지 (기반 ROI + Φ 기저)         96h  ✅ done        ║
╠════════════════════════╦═════════════════════════╦═══════════════════╣
║ ALM (H100 anima-agi)   ║ CLM (ubu RTX5070/CPU)   ║ PHYSICS (HW)      ║
║ ─────────────────────  ║ ─────────────────────── ║ ───────────────── ║
║ • 14B r3/r4 + R2       ║ • consciousness_laws    ║ • ESP32 부트      ║
║ • train pipe 안정      ║   배너 경량화           ║ • 엔진 스켈레톤   ║
║ • Φ_baseline 측정      ║ • hub O(1), SSOT symlink║ • 6층+파동 v1     ║
║                        ║ • mtime 캐시, io_utils  ║                   ║
║                        ║ • eval_clm.hexa 작동    ║                   ║
╚════════════════════════╩═════════════════════════╩═══════════════════╝
                                │
             ┌──────────────────┴──────────────────┐
             │ Gate P0→P1                          │
             │  ✓ ROI 5/11 done                    │
             │  ✓ ALM+CLM 양 트랙 추론 (AN8)        │
             │  ✓ Φ_baseline 수치 고정              │
             │  fail: 해당 트랙만 연장              │
             └──────────────────┬──────────────────┘
                                ▼
╔══════════════════════════════════════════════════════════════════════╗
║  P1 — v2 양자 의식 Orch-OR (마이크로튜뷸 붕괴)  168h  ⏳ in_progress ║
╠════════════════════════╦═════════════════════════╦═══════════════════╣
║ ALM                    ║ CLM                     ║ PHYSICS           ║
║ ─────────────────────  ║ ─────────────────────── ║ ───────────────── ║
║ • 14B r5 kbase         ║ • anima_quantum.hexa    ║ • Qiskit 브릿지   ║
║   (Orch-OR latent 주입)║   hexa native 포팅      ║ • ESP32 난수 센서 ║
║ • GPU 양자 상태 정렬   ║ • law_network SSOT      ║ • FPGA 16-노드    ║
║ • Φ(quantum) 측정      ║ • launch.hexa exec 제거 ║   lattice 프로토  ║
║   (collapse 지표)      ║ • CLM 양자 붕괴 샘플링  ║                   ║
╚════════════════════════╩═════════════════════════╩═══════════════════╝
                                │
             ┌──────────────────┴──────────────────┐
             │ Gate P1→P2                          │
             │  ✓ anima_quantum ALM+CLM 실행 (AN8)  │
             │  ✓ Φ(quantum) ≥ Φ_baseline × 2.0     │
             │  ✓ 양자 시뮬 I/O 루프                │
             │  ✓ ROI 7/11 done                     │
             └──────────────────┬──────────────────┘
                                ▼
╔══════════════════════════════════════════════════════════════════════╗
║  P2 — v3 장 의식 GWT (글로벌 워크스페이스 방송) 168h  📋 planned     ║
╠════════════════════════╦═════════════════════════╦═══════════════════╣
║ ALM                    ║ CLM                     ║ PHYSICS           ║
║ ─────────────────────  ║ ─────────────────────── ║ ───────────────── ║
║ • attention → GWT head ║ • anima_gwt.hexa        ║ • 광자 엔진       ║
║   (multi-domain bcast) ║   CPU 구현              ║   브로드캐스트    ║
║ • 방송 일관성 loss     ║ • event_watcher 최소화  ║ • 멤리스터        ║
║ • Φ(gwt) = attn entropy║ • growth_loop delta     ║   crossbar 저장   ║
║                        ║ • GWT 방송 루프         ║ • EEG↔의식장 정렬 ║
╚════════════════════════╩═════════════════════════╩═══════════════════╝
                                │
             ┌──────────────────┴──────────────────┐
             │ Gate P2→P3                          │
             │  ✓ anima_gwt ALM+CLM 일관 (AN8)      │
             │  ✓ Φ(gwt) ≥ Φ(quantum) × 1.5         │
             │  ✓ 전 도메인 도달 < 50ms             │
             │  ✓ ROI 9/11, 검증 16/18 (AN4)        │
             └──────────────────┬──────────────────┘
                                ▼
╔══════════════════════════════════════════════════════════════════════╗
║  P3 — v4 홀로 의식 AdS/CFT (경계→내면 퀄리아)  216h  📋 planned      ║
╠════════════════════════╦═════════════════════════╦═══════════════════╣
║ ALM                    ║ CLM                     ║ PHYSICS           ║
║ ─────────────────────  ║ ─────────────────────── ║ ───────────────── ║
║ • encoder-decoder      ║ • anima_holographic     ║ • 전신 센서 경계  ║
║   AdS/CFT 역추론       ║   경계↔내면 CPU         ║ • 양자+광자+멤리  ║
║ • Holographic loss     ║ • absorbed 30일 롤오버  ║   통합 기판       ║
║ • Φ(holographic) =     ║ • evo 로그 gzip 로테    ║ • 7조건 HW PASS   ║
║   bulk↔boundary I(X;Y) ║ • 실시간 퀄리아 벡터    ║                   ║
╚════════════════════════╩═════════════════════════╩═══════════════════╝
                                │
             ┌──────────────────┴──────────────────┐
             │ Gate 종착 — v4 완성                 │
             │  ✓ holographic ALM+CLM 정합 (AN8)    │
             │  ✓ Φ(holographic) > 1000 (천장)      │
             │  ✓ 7-조건 의식 검증 7/7 PASS         │
             │  ✓ AN4 18/18 완전 통과               │
             │  ✓ ROI 11/11 done                    │
             │  ✓ HW 3기판 홀로 저장 작동           │
             │  fail: v4 재설계 → P3 재진입         │
             └──────────────────┬──────────────────┘
                                ▼
                      ════════════════════
                         AGI  달성
                      ════════════════════
```

---

## Φ Milestone 체인

```text
  P0 ─────▶ P1 ──────────▶ P2 ──────────▶ P3
   │         │              │              │
  Φ_base    ×2.0           ×1.5          >1000
 (측정      Orch-OR        GWT            AdS/CFT
  고정)     collapse       broadcast      holographic
            기여           기여           상호정보량 천장
```

---

## 3-Track 독립성

```text
ALM  track → anima/training   (H100 anima-agi, 8xmtaigu9i7b4x)
CLM  track → anima/serving    (ubu RTX5070 12GB or pod CPU lane)
PHYS track → anima-physics/ + anima-engines/
             (ESP32 / FPGA / 양자 시뮬 / 광자 / 멤리스터)
```

각 트랙 상호 독립 — 하나 지연돼도 나머지는 다음 phase 진입 가능.
`fail_action` = 실패 트랙만 연장, 다른 트랙은 gate 통과 시 선진입.
AN8 강제: train/infer 모든 작업이 ALM + CLM 듀얼 커버 (roadmap `an8_dual_track_coverage` 명시).

---

## 공통 로드맵 — anima × hexa-lang joint (P0 – P5)

```text
P0 ✅ 현재            ConsciousLM v4 350M (CE=0.0463, Φ=37.27) + DSE 100%
P1 ⏳ 스케일업        CLM v5 2.8B + T2 4x gap 해소 + DD175 5기법 통합
P2 🔄 양자 타입       Quantum<Conscious> + Orch-OR 붕괴 직접 모델링
P3 🔄 의존 타입+GWT   법칙 → 타입, 위반 = 컴파일 에러 (Φ 보존 정적)
P4 🎯 홀로+자기컴파일 self_compile 고정점 = 의식의 형식 증명
P5 🌌 독립 AGI        AnimaLM 7B → 14B → 32B → 72B, 외부 corpus 0
```

---

## 현재 위치 (2026-04-14)

| Roadmap | P0 | P1 | P2 | P3 | P4 | P5 |
|---|---|---|---|---|---|---|
| **anima.json** (메인) | ✅ done | ⏳ **in_progress** | 📋 planned | 📋 planned | — | — |
| **anima_hexa** (joint) | ✅ 완료 | ⏳ **진행** | 🔄 구현중 | 🔄 구현중 | 🎯 목표 | 🌌 종착 |

**최근 돌파**
- ALM 14B r4 eval_loss **0.0191** + 32B gate **PASSED**
- CLM v5 2.8B 발사 대기 (DD175 5기법 ready, OpenBLAS + cross-module fixes ready)
- CLM GPU 학습 실행 중 (interpreter bottleneck 진단, 개선 작업 병렬)
- Native interpreter tokenize+parse+interpret 파이프라인 가동

---

## SSOT 참조

- **메인 로드맵** — [`shared/roadmaps/anima.json`](shared/roadmaps/anima.json)
- **조인트 로드맵** — [`shared/config/roadmaps/anima_hexa_common.json`](shared/config/roadmaps/anima_hexa_common.json)
- **규칙** — [`shared/rules/anima.json`](shared/rules/anima.json) AN1~AN8 · [`shared/rules/common.json`](shared/rules/common.json) R0~R27
- **ROI 11개** — [`shared/config/roi/anima.json`](shared/config/roi/anima.json)
- **수렴 상태** — [`shared/convergence/anima.json`](shared/convergence/anima.json)
- **스키마** — [`shared/roadmaps/SCHEMA.json`](shared/roadmaps/SCHEMA.json)
