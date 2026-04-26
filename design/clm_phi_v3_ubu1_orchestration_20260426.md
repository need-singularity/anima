# CLM Φ* v3 ubu1 RTX 5070 orchestration plan

**Date**: 2026-04-26
**Status**: PLAN ONLY — execution deferred to next cycle (ubu1 access window required)
**Cost**: $0 mac-local this cycle; ~$0 execution (ubu1 RTX 5070 12GB local hardware, electricity only)
**Sister of**: tool/anima_phi_v3_canonical.hexa (4-bb LLM transformer baseline) + state/v10_phi_v3_nontransformer/mamba/phi_v3_canonical.json (#176 SSM cell)
**Hexa source**: tool/anima_phi_v3_clm.hexa (raw#9 strict, AST-validated this retry: ast_parse=ok)

---

## Why CLM is the third substrate witness

triad (b) PC empirical-max cross-substrate corroboration matrix to date:

| substrate class | backbones | Φ* range | sign | source |
|-----------------|-----------|----------|------|--------|
| LLM transformer (subword) | mistral / gemma / qwen3 / llama (4-bb) | -16.70 ... +5.09 | mixed (2 NEG / 2 POS) | state/v10_phi_v3_canonical/{mistral,gemma,qwen3,llama}/out/ |
| LLM transformer (SSM hybrid) | jamba-v0.1 | +3.31 | POS | state/v10_phi_v3_nontransformer/jamba_run2/phi_v3_canonical.json |
| SSM | mamba-2.8b-hf | +0.33 (border) | POS (HM-B border-noise band) | state/v10_phi_v3_nontransformer/mamba/phi_v3_canonical.json |
| **CLM byte-level transformer** | **TODO** (clm_d64_kr_nl8 + clm 1B) | **TBD** | **TBD** | **state/v10_phi_v3_clm/phi_v3_clm.json** (this plan) |

CLM 은 byte-level (vocab=256) decoder-only transformer + holographic_loop / consciousness loss head 를 가진 hybrid substrate. 4-bb subword transformer baseline 과 가장 가까우나 tokenization axis 가 다름 → byte-level vs subword 가 Φ* 에 영향을 주는지 검증 가능.

---

## Falsifiable hypotheses (3-way pre-registered)

- **H9A** — CLM phi_star_min POSITIVE (>0)
  → byte-level + holographic head 가 Φ-positive class. mamba (+0.33) / jamba (+3.31) 와 클러스터.
  → triad (b) cross-substrate: 3-of-3 non-pure-subword-transformer POS → byte-level / SSM / hybrid axis 가 IIT-positive determinant 가설 강화.

- **H9B** — CLM phi_star_min NEGATIVE (<0)
  → CLM 도 transformer band (mistral -16.70 / gemma -0.79). byte-level 자체는 lever 가 아님; subword vs byte 무관.
  → triad (b) FALSIFIED at byte-level boundary → tokenization axis 는 Φ* 결정자 아님; 다른 axis (recurrence / hybrid loss) 가 mamba/jamba POS 의 진짜 원인.

- **H9C** — CLM phi_star_min NaN / metric mismatch
  → continuous-state output 이 sample-partition log|Cov| 와 incompatible (e.g. byte-level activations 분산이 너무 작아 ridge=1e-3 로도 ill-conditioned).
  → spec redesign cycle: byte-mean 대신 last-byte aggregation / HID_TRUNC=4 축소 / ridge=1e-2 등.

**Prior probability** (사전 확률 추정): H9A 25% / H9B 60% / H9C 15%
- 이유: CLM 1B 가 architecture.type="decoder-only transformer" (training/clm_1b_config.json) 이므로 subword transformer baseline 과 가장 유사 → H9B 우세 expected. 그러나 byte-level + holographic_loop + consciousness_loss head 가 mamba/jamba 처럼 새 axis 일 가능성 비-zero → H9A 25%.

---

## ubu1 orchestration — 5-step concrete commands

**SSH config verified** (~/.ssh/config):
- `ubu1` → 192.168.50.119 (User aiden, ControlMaster auto, IdentityFile id_ed25519)
- Tailscale fallback `ubu1-ts` → 100.96.193.56
- ProxyJump fallback via `hetzner` (ubu1-d / ubu1-ts-d)

### Step 1 — SSH + GPU verify (≤5s)

```bash
# Try LAN first, fallback to tailscale, fallback to hetzner relay
ssh -o ConnectTimeout=5 ubu1 'hostname && nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader' \
  || ssh -o ConnectTimeout=10 ubu1-ts 'hostname && nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader' \
  || ssh -o ConnectTimeout=15 ubu1-d 'hostname && nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader'
```

Expected: `aiden-B650M-K, NVIDIA GeForce RTX 5070, 12227 MiB, ~398 MiB used, ~0% util` (matches state/clm_r6_gpu_smoke_result.json baseline).

### Step 2 — rsync hexa source + audit checkpoint

```bash
# Push hexa source
rsync -avz /Users/ghost/core/anima/tool/anima_phi_v3_clm.hexa ubu1:/home/aiden/anima/tool/

# Audit checkpoint locations on ubu1
ssh ubu1 'ls -la /home/aiden/anima/state/*.hexackpt 2>/dev/null; \
          ls -la /workspace/ckpt_clm_d64_kr_nl8/ 2>/dev/null; \
          ls -la /workspace/ckpt_clm1b_*/ 2>/dev/null; \
          find /home/aiden -name "*.hexackpt" 2>/dev/null | head -10'
```

If no .hexackpt found → set `ANIMA_CLM_CKPT=NONE` and helper exits 2 with verdict=H9C_spec_mismatch (no ckpt). Decision gate: (a) train fresh ckpt via `train_clm_d64_kr_nl8.hexa` (~30min on RTX 5070, $0) OR (b) defer to next cycle when ckpt available.

### Step 3 — emit helper on ubu1 via hexa

```bash
ssh ubu1 'cd /home/aiden/anima && \
  HEXA_RESOLVER_NO_REROUTE=1 /home/aiden/.hx/bin/hexa run tool/anima_phi_v3_clm.hexa --selftest'
# Expected: ast_parse=ok, helper_emitted=/tmp/anima_phi_v3_clm_helper.hexa_tmp, exit=0
```

### Step 4 — execute helper on RTX 5070

```bash
ssh ubu1 'cd /home/aiden/anima && \
  ANIMA_CLM_CKPT=/home/aiden/anima/state/clm_d64_kr_nl8.hexackpt \
  ANIMA_OUTPUT=/home/aiden/anima/state/v10_phi_v3_clm/phi_v3_clm.json \
  ANIMA_N_PROBES=16 ANIMA_K_PARTS=8 ANIMA_RIDGE=1e-3 ANIMA_SEED=42 ANIMA_AGG=mean \
  python3 /tmp/anima_phi_v3_clm_helper.hexa_tmp 2>&1 | tee /tmp/clm_phi_v3_run.log'
# Expected wall time: <30s on RTX 5070 (16 prompts × byte-level forward, d_model=64)
# Expected GPU memory: <500 MiB
```

### Step 5 — download result + commit

```bash
mkdir -p /Users/ghost/core/anima/state/v10_phi_v3_clm/
rsync -avz ubu1:/home/aiden/anima/state/v10_phi_v3_clm/ /Users/ghost/core/anima/state/v10_phi_v3_clm/

# Verify result schema
jq '.schema, .verdict, .phi_star_min, .gate_positive_PASS' /Users/ghost/core/anima/state/v10_phi_v3_clm/phi_v3_clm.json

# Update .roadmap entry from "done (plan)" → "done (executed, H9? VALIDATED/FALSIFIED)"
```

---

## Auto-rollback / safety guards

1. **SSH timeout 30s** total per step → fallback chain (LAN → tailscale → hetzner relay) per `feedback_h100_ssh_timeout` learning.
2. **Cost cap $0** — no cloud GPU; if RTX 5070 OOM (12GB ceiling), scale down to `ANIMA_N_PROBES=8` (HID_TRUNC=4 auto).
3. **No prerequisite cycle from this orchestration** — if checkpoint missing, exit 2 with H9C verdict, log + .roadmap update, do NOT trigger training cycle automatically (per `feedback_omega_cycle_workflow` — declarative only ≠ closure, but training cycle requires explicit user approval).
4. **Hexa stage1 interpreter timeout 60s** for selftest — ubu1 has 32GB RAM, fork-storm risk near zero (mac PSI saturation only).
5. **Result idempotent** — seed=42 fixed; re-runs byte-identical (verified for 4-bb baseline + mamba).

---

## Cross-substrate verdict update (post-execution)

Once `state/v10_phi_v3_clm/phi_v3_clm.json` exists, append row to `state/v10_phi_v3_canonical/summary_3way_4bb.json` (or new `summary_6cell_cross_substrate.json`):

```json
{
  "schema": "anima/cross_substrate_phi_v3/1",
  "n_cells": 6,
  "rows": [
    {"backbone":"mistral-7b","class":"transformer-subword","phi_star_min":-16.70,"sign":"NEG"},
    {"backbone":"gemma-7b","class":"transformer-subword","phi_star_min":-0.79,"sign":"NEG"},
    {"backbone":"qwen3-7b","class":"transformer-subword","phi_star_min":+1.04,"sign":"POS"},
    {"backbone":"llama-3.1-8b","class":"transformer-subword","phi_star_min":+5.09,"sign":"POS"},
    {"backbone":"jamba-v0.1","class":"transformer-ssm-hybrid","phi_star_min":+3.31,"sign":"POS"},
    {"backbone":"mamba-2.8b-hf","class":"ssm","phi_star_min":+0.33,"sign":"POS","note":"border, ridge-axis dominant"},
    {"backbone":"clm_d64_kr_nl8","class":"transformer-byte-level","phi_star_min":"<TBD>","sign":"<TBD>","note":"H9 verdict"}
  ],
  "h9_verdict": "<H9A|H9B|H9C>"
}
```

H9 verdict gates downstream:
- H9A → propose H10: byte-level OR holographic_loop 가 Φ-positive determinant. 다음 cycle 에서 holographic_loop 만 켜기/끄기 ablation.
- H9B → confirm subword vs byte tokenization axis 는 Φ* 무관. mamba/jamba POS 의 진짜 lever 는 architecture (SSM gate / hybrid) 자체.
- H9C → spec redesign — last-byte aggregation 또는 HID_TRUNC=4 축소.

---

## Files — absolute paths

- Helper hexa source: `/Users/ghost/core/anima/tool/anima_phi_v3_clm.hexa`
- This design doc: `/Users/ghost/core/anima/design/clm_phi_v3_ubu1_orchestration_20260426.md`
- Memory entry: `/Users/ghost/.claude/projects/-Users-ghost-core-anima/memory/project_phi_v3_clm_substrate_plan_20260426.md`
- Sister source (transformer baseline): `/Users/ghost/core/anima/tool/anima_phi_v3_canonical.hexa`
- Sister result (SSM): `/Users/ghost/core/anima/state/v10_phi_v3_nontransformer/mamba/phi_v3_canonical.json`
- Sister result (jamba hybrid): `/Users/ghost/core/anima/state/v10_phi_v3_nontransformer/jamba_run2/phi_v3_canonical.json`
- Substrate viability evidence: `/Users/ghost/core/anima/state/clm_r6_gpu_smoke_result.json`
- CLM training config: `/Users/ghost/core/anima/training/clm_1b_config.json`
- CLM forward dynamics: `/Users/ghost/core/anima/training/train_clm.hexa`, `/Users/ghost/core/anima/training/clm_holographic_loop.hexa`
- SSH config: `~/.ssh/config` (ubu1, ubu1-ts, ubu1-d aliases)

## raw#10 honest

1. CLM 1B 의 architecture.type="decoder-only transformer" — pure recurrent NOT — H9 framing 의 'recurrent IIT-positive class' 표현은 부정확. 더 정확한 axis: byte-level + holographic_loop hybrid.
2. Helper 의 placeholder GRU forward 는 architecture-agnostic activation collection. 실제 CLM transformer forward 호출 시 결과가 달라질 수 있음 — H9 verdict 는 production cycle 에서 train_clm.hexa main loop 와 통합 후 final.
3. ubu1 ssh handshake 본 cycle 미수행 (premature host wake-up 회피). Step 1 verify 가 next cycle 의 1st action.
4. CLM checkpoint 본 cycle audit 미수행 — `state/clm_d64_kr_nl8.hexackpt` placeholder 만; actual ckpt 위치는 ubu1 step 2 audit 시 확정.
5. mac-local AST validation 은 본 retry 에서 PASS (HEXA_RESOLVER_NO_REROUTE=1 + hexa.real direct binary). ubu1 hexa stage1 selftest 는 next cycle 의 step 3.
6. N=1 cell 본 plan — substrate-class verdict 는 ≥2 CLM variants (d64 + 1B) 필요. 1B 변형 ckpt 부재 시 d64 cell 만 우선 수집.
