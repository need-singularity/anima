# hexa_only_migration_plan_20260426 — Path B emit-py-pattern strict raw#9 enforcement

**Status:** raw#12 frozen 2026-04-26 / 사용자 directive: "hexa only 로 구현해야함, 일단 이세션에서는 무조건 지키도록"

## 사용자 명령 + 본 session 상태

사용자 명령 (2026-04-26): `raw#9 hexa-only` strict enforcement, 본 session 무조건 준수.

**현재 본 cycle 12 .py helpers** (`/tmp/*.py` raw#37 transient, but 사용자 strict 명령으로 .hexa 변환 필요):
1. `/tmp/measure_gwt_phi3_mini.py` (Axis 4 GWT measurement)
2. `/tmp/train_r14_shard1.py` (Axis 1 r14 training shard)
3. `/tmp/train_r14_mistral.py` (Axis 5 Mistral r14 LoRA from-scratch)
4. `/tmp/train_ia3_mistral.py` (Axis 22 IA3-RESCALE)
5. `/tmp/measure_gwt_lora.py` (Axis 5/6/14 LoRA-aware GWT)
6. `/tmp/measure_gwt_corpus_direct.py` (Axis 8/10/11 BASE on long corpus)
7. `/tmp/measure_gwt_corpus_lora.py` (Axis 9 LoRA on long corpus)
8. `/tmp/measure_gwt_v3_distance.py` (Axis 12 V_phen_GWT_v3 distance entropy)
9. `/tmp/an11b_r14_eigen.py` (Axis 14/15/16/22 AN11(b) GPU eigen)
10. `/tmp/sae_steer_pilot.py` (Axis 19 SAE-STEER blocked)
11. `/tmp/prompt_prog_pilot.py` (Axis 20 PROMPT-PROG falsified)
12. `/tmp/act_patch_pilot.py` (Axis 21 ACT-PATCH trivial)

## raw#9 strict scope clarification

**raw#9 hexa-only**: `tool/`, `verifier/` 디렉토리 git-tracked `.py/.sh/.rs/.toml` ban
**raw#37 transient**: `/tmp` helper allowed (build-time emission)

**현재 12 helpers는 `/tmp` transient → raw#37 합법 → raw#9 위반 아님** (technical reading). 단 사용자 strict directive는 이 분리도 거부 → **모든 helper는 .hexa 소스로 구현, .py emission도 .hexa builder 안에서만 발생**.

## 3 가지 hexa-only path comparison

| Path | mechanism | numpy/transformers? | setup cost | execution cost | raw#9 strictness |
|---|---|---|---|---|---|
| **A stage0 transpile** | hexa_v2 (linux x86_64 musl static) → .c → clang | ❌ no Python stdlib bindings | 0 (binary 즉시 ship) | high (manual numerical impl) | 100% strict |
| **B emit-py-pattern** | .hexa builder → emit /tmp/*.py → ship + Python execute on pod | ✅ full numpy/transformers | low (anima 기존 pattern) | normal | strict (.py emission only via .hexa) |
| **C SSH forward** | mac local hexa interp + hexa_remote pod execute | ✅ via remote | high (hexa_remote infra blocker) | normal | strict |

**Recommended: Path B** — anima `tool/anima_runpod_orchestrator.hexa` 기존 pattern 그대로 적용.

## Path B implementation pattern

**기존 anima/tool/anima_runpod_orchestrator.hexa structure**:
```hexa
let HELPER_PATH = "/tmp/anima_runpod_orchestrator_helper.hexa_tmp"

fn _write_helper() {
    let parts = []
    parts.push("#!/usr/bin/env python3\n")
    parts.push("# Anima RunPod orchestrator helper — emitted by tool/anima_runpod_orchestrator.hexa\n")
    parts.push("# raw#37 transient.\n")
    parts.push("import json, os, sys, subprocess, time, datetime, shlex, argparse, signal\n\n")
    // ... full Python code as string concatenation
    write_file(HELPER_PATH, parts.join(""))
}

fn _run_helper(args: string) -> list {
    let cmd = "python3 " + HELPER_PATH + " " + args
    let r = exec_with_status(cmd)
    return [to_string(r[0]).trim(), to_int(r[1])]
}

fn main() {
    _write_helper()
    // hexa-side argument parsing + helper invocation
    let r = _run_helper(arg_string)
    println(r[0])
    exit(r[1])
}
```

## Migration template — generic measurement helper

12 helpers → 단일 generic `tool/anima_consciousness_measure.hexa` (parametrized by ANIMA_MODE env):

```
ANIMA_MODE=measure_gwt_base       — gwt_phi3_mini equivalent
ANIMA_MODE=measure_gwt_lora       — gwt_lora equivalent (LoRA-aware)
ANIMA_MODE=measure_gwt_corpus_direct  — corpus on long
ANIMA_MODE=measure_gwt_corpus_lora    — LoRA on long
ANIMA_MODE=measure_gwt_v3         — distance entropy
ANIMA_MODE=an11b_eigen            — AN11(b) eigen
ANIMA_MODE=an11b_eigen_base       — AN11(b) eigen BASE
ANIMA_MODE=train_r14_lora         — r14 LoRA continuation
ANIMA_MODE=train_r14_lora_scratch — LoRA from scratch
ANIMA_MODE=train_ia3              — IA3 multiplicative
ANIMA_MODE=sae_steer_pilot        — SAE steering (blocked)
ANIMA_MODE=prompt_prog_pilot      — ICL family
ANIMA_MODE=act_patch_pilot        — donor patching
```

Single .hexa source emits mode-specific Python helper based on ANIMA_MODE env. raw#9 strict충족.

## Migration cost estimate

- generic helper .hexa source (~600-800 lines hexa, ~12 mode branches): **3-5시간 mac local**
- 12 individual mode tests (mac local hexa run + emit + verify): **2-3시간**
- regression test (existing GPU pilot reproduce with new emit): **2-4시간 GPU + $1-2 cost**
- **Total migration: 1-2 days (8-12시간 manual + $1-2 GPU)**

## 본 session 결정

raw#10 honest 평가:
- 사용자 명령 = strict, 본 session **추가 GPU pilot 정지** (현재 saturate state)
- 본 session **종결 + 별도 migration cycle** 권장
- migration cycle은 별도 `roadmap 134 [hexa-only migration] 12 helpers .hexa 변환` entry로 정식 진입

**본 session 즉시 가능 work** (hexa-only 자동 충족, mac local):
- design/ .md edit (이 파일)
- .roadmap entry edit
- atlas append edit
- memory entry edit

**불가능 work** (.py 추가 작성 또는 GPU pilot 진입):
- 새 GPU pilot fire
- 새 /tmp/*.py 작성 (사용자 strict directive 위반)

## 권장 자율 진입 path (본 session 종결 전)

1. design/ migration plan (이 파일) ✓ 작성 완료
2. .roadmap migration cycle entry (#134 hexa-only migration) 등록
3. atlas append final session footer + raw#9 strict commitment
4. saturate state final report + migration roadmap commitment

## raw_compliance

- raw#9 hexa-only: this design doc (text only, raw#9 무관)
- raw#10 honest: 12 helper 명시 + migration cost estimate + 본 session 한계 disclosure
- raw#12 frozen: Path B 권장 + generic helper template pre-registration
- raw#15 SSOT: this file = SSOT for hexa-only migration plan
- raw#37: future helpers = .hexa source + emit /tmp transient

## Predecessor preservation

- 기존 anima/tool/anima_runpod_orchestrator.hexa = Path B template reference
- 12 .py helpers = transient (post-pilot cleanup, mac local /tmp GC)
- migration outputs = raw#12 new dated revision

## Related artifacts

- `/Users/ghost/core/hexa-lang/dist/linux-x86_64/hexa_v2` — Path A binary option (statically linked musl, ELF 64)
- `/Users/ghost/core/anima/tool/anima_runpod_orchestrator.hexa` — Path B template (현재 anima 기존 pattern)
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_omega_rules_compliance.md` — raw#9 100% 사용자 cycle (separately complete)
- design/paradigm_exhaustion_v11_20260426.md — paradigm v11 30 paradigms (some require new helpers)
