---
kind: project
scope: anima/verify
created: 2026-04-21
status: landed
---

# Verifier infra 5종 landed (2026-04-20)

SSOT: `docs/alm_clm_verifier_design_20260420.md` (f8bc7882),
roles canonical refs 갱신 (048e1f9d).

- **manifest** — verifier 자산 등록표
- **generator** — 입력 셋 생성기
- **run_all** — 5종 일괄 실행 드라이버
- **pass_gate_an11** — AN11 rule 기반 pass-gate
- **closed_loop** — A1+Orch+Tool chain-merge 재현 루프
- **kr_gen_100** — 한국어 100샘플 생성 smoke

Deterministic verifier only (LLM judge 금지, hire_sim_judge_lenient DEPRECATED).
