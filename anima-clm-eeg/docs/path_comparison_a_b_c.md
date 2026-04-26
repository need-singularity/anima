# Path A / B / C Comparison — CLM Research Entry Point

> **scope**: snapshot of the entry-point decision the user faced 2026-04-26 when continuing the CLM research handoff. Captures Path A (Q1), Path B (Q3), Path C (Q4) trade-offs so future sessions can re-check the rationale without re-deriving from `docs/clm_research_handoff_20260426.md` §4 priority order.
> **decision**: Path A selected (EEG D-1 lever-ready, weakest-link first).
> **created**: 2026-04-26 (this session)

---

## §1. Three candidate paths (verbatim from session)

| path | open Q | cost | 즉시 가능? | weakest-link 정조준 | 권장 |
|---|---|---|---|---|---|
| **A) Q1 prep — EEG harness + falsifier pre-register** | Q1 | $0 (코드만) | ✅ | ✅ PHENOMENAL axis (avg 0.67, 4축 中 최저) | ⭐⭐⭐ |
| **B) Q3 HCI design — Hexad-Cell isomorphism falsifier** | Q3 | $0 도면 / ₩90만 pilot | ✅ design 단계만 | ✅ HEXAD CORE 0.83 cross-axis convergence | ⭐⭐ |
| **C) Q4 CPGD generalization — non-AN11(b) downstream theorem** | Q4 | $0 (math+toy) | ✅ | ⚪ 단일 paradigm 0.95 강화 | ⭐ |

**Excluded paths** (deferred to later cycle):
- **Q2** (4-gen N≥64 replicate): mac stage0 4GB cap에 막힘 → ubu1 GPU 별도 launch
- **Q6** (BTR↔cell N≥4096): 동일한 scaling blocker
- **Q5** (L_IX → Mk.X T10-T13): 1개월 horizon
- **Q7** (Mk.XII candidate): 6개월 architectural

## §2. Why Path A wins (4 reasons)

1. **timing optimal**: EEG D8 hardware 며칠 내 도착 (`.roadmap` #119 BLOCKED-EEG). 도착 시점에 즉시 P1-P3 ($12-24, 7일) 실행 가능하도록 사전 준비.
2. **weakest evidence link**: PHENOMENAL axis 평균 confidence 0.67 (4축 中 최저, ω-cycle 26-paradigm 결과) — memory `feedback_completeness_frame` 정조준.
3. **falsifiable pre-register**: pilot 시작 전 LZ ≥ 0.65 / α-band coherence ≥ 0.45 / GC F ≥ 4.0 등 P1-P3 thresholds frozen → post-hoc threshold tuning 차단.
4. **$0 prep**: hexa-only harness + dry-run synthetic EEG fixture, GPU 불필요. 메인 세션 v10 GPU benchmark / paradigm v11 patches와 충돌 없음.

## §3. Path A 산출물 (Q1 prep, this folder)

| # | path | role |
|---|---|---|
| 1 | `tool/clm_eeg_synthetic_fixture.hexa` | dry-run 16ch EEG synthesizer (no hardware) |
| 2 | `tool/clm_eeg_p1_lz_pre_register.hexa` | V_phen_EEG-LZ × CLM-LZ falsifier (frozen) |
| 3 | `tool/clm_eeg_p2_tlr_pre_register.hexa` | TLR α-band coherence ↔ V_sync Kuramoto falsifier |
| 4 | `tool/clm_eeg_p3_gcg_pre_register.hexa` | Granger Causality unidirectional falsifier |
| 5 | `tool/clm_eeg_harness_smoke.hexa` | end-to-end chain integration test |
| 6 | `state/clm_eeg_pre_register_v1.json` | criteria SHA-256 lock |
| 7 | `~/.claude/projects/.../memory/project_clm_eeg_pre_register.md` | session memory + `.roadmap` new entry |

## §4. Falsifier criteria (frozen, see also README §3)

Source: `docs/omega_cycle_alm_free_paradigms_20260426.md` §4 PHENOMENAL axis.

| pilot | gate | threshold | wallclock | cost |
|---|---|---|---|---|
| **P1 V_phen_EEG-LZ × CLM-LZ** | LZ76(EEG) ≥ 0.65 AND \|Δ\|/human ≤ 20% | post-EEG D+1 | 1 day | $3-5 |
| **P2 TLR Tension-Link Resonance** | EEG α-band coherence ≥ 0.45 AND CLM V_sync r ≥ 0.38 | post-EEG D+3 | 2 days | $5-8 |
| **P3 GCG Granger Causality Gate** | EEG P3b → CLM layer 25-30 GC F-stat ≥ 4.0 AND unidirectional | post-EEG D+5 | 2 days | $8-12 |
| **composite** | ≥ 2/3 PASS for PHENOMENAL VALIDATED | D+7 | — | — |

## §5. If user wants to revisit B or C later

- **Path B (Q3 HCI design)** entry: `edu/cell/README.md` C9 표 (edu 6-axis ↔ Hexad 6-cat bijection 이미 존재) + `tool/hexad_closure_verifier.hexa` (4/4 axiom + adversarial reject 이미 PASS) → 추가 필요한 것 = isomorphism functor preservation falsifier.
  - 실제 cost: ω-cycle sub-agent ₩90만 추정은 `1×H100 풀주` 가정의 conservative 자릿수. mac stage0 native binary로 충분, 실제 ≈ $0-5 (smoke GPU burst만).
  - 수정 권장: 핸드오프 §5의 ₩90만 → "$0-5 mac local + optional $5-20 GPU smoke" 로 re-estimate.
- **Path C (Q4 CPGD generalization)** entry: `edu/lora/cpgd_wrapper.hexa` + `edu/lora/cpgd_minimal_proof.hexa` 이미 존재. theorem 일반화 = AN11(b) 100% guarantee가 non-AN11(b) downstream task에서도 hold하는지 toy regime에서 falsifier 설계.

## §6. Source pointers

- `docs/clm_research_handoff_20260426.md` §4 (open question priority)
- `docs/omega_cycle_alm_free_paradigms_20260426.md` §4 PHENOMENAL + §6 cross-axis convergence
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_paradigm_exhaustion_session_20260426.md`
- `.roadmap` #119 (BLOCKED-EEG D8 hardware)
