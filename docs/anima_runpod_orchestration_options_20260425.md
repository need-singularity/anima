# Anima RunPod Orchestration Options Protocol

**Date**: 2026-04-25
**Status**: SPEC_FROZEN. Preset matrix raw#12 frozen 사전 등록. 실 dispatch는 사용자 명령 시 base orchestrator 호출.
**Forward auto-approval**: per memory feedback_forward_auto_approval (2026-04-25). 기본 동작은 `--emit-only` (커맨드 출력만). 명시적 dispatch는 cap $20 hard ceiling.

## §0 Mission

Anima의 RunPod orchestrator + Docker image plan을 다양한 조건에 빠르게 대응 가능한 **옵션화 matrix** 형태로 확장.

기존 단일 main session pattern (4 launches × 매번 manual flag 조합) →
- preset library (11 presets)
- parameter combinations (image × GPU × steps × LoRA rank × corpus)
- scenario-driven dispatch (offline / GPU shortage / low budget / EEG / exhaustive 등)

## §1 SSOT triple

본 protocol의 SSOT는 3-file:

| 역할 | 경로 |
|---|---|
| State (preset matrix) | `state/anima_runpod_preset_matrix_20260425.json` |
| Doc (본 문서) | `docs/anima_runpod_orchestration_options_20260425.md` |
| Tool (dispatcher) | `tool/anima_runpod_preset_dispatcher.hexa` |
| Base orchestrator (참조) | `tool/anima_runpod_orchestrator.hexa` |
| Image plan (참조) | `docs/runpod_docker_image_plan_20260425.md` |

## §2 Preset matrix (11 presets)

**Frozen registry** — raw#12 사전 등록. post-hoc preset 추가/제거 시 violation log 발생.

| # | Preset name | Category | Steps | GPU | Image | $/run | min/run | Cap | Tags |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `BASE_measurement` | measurement | 0 | h100_sxm | default | $0.10 | 12 | $1 | baseline, fast |
| 2 | `MK_XI_DEMO_TRAINING` | training | 200 | h100_sxm | default | $0.10 | 12 | $1 | smoke, mock |
| 3 | `MK_XI_FULL_6LOSS` | training | 1000 | h100_sxm | default | $0.58 | 14 | $2 | mid_step, 6_loss |
| 4 | `MK_XI_FULL_5K` | training | 5000 | h100_sxm | default | $2.50 | 50 | $5 | full_convergence |
| 5 | `LAMBDA_SWEEP_4X4_PARTIAL` | training_sweep | 5000 × 8 cells | h100_sxm | default | $19.92 | 400 | $20 | sweep, cap_tight |
| 6 | `PHEN_FORWARD_4_AXES` | phenomenal | 0 | h100_sxm | default | $0.30 | 6 | $1 | phenomenal, fast |
| 7 | `EEG_INGEST_ONLY` | eeg | 0 | cpu_only | cpu | $0.05 | 1 | $0.5 | eeg, cpu |
| 8 | `V_PHEN_LZ_GWT_BATCH` | verification | 0 | h100_sxm | default | $0.10 | 5 | $1 | verification, batch |
| 9 | `5_TUPLE_FULL_AGGREGATE` | measurement | 0 | h100_sxm | default | $0.10 | 4 | $1 | aggregate, verdict |
| 10 | `MULTI_BACKBONE_CROSS_BASE` | cross_validation | 0 | h100_sxm | default | $1.00 | 25 | $3 | cross_base, multi_model |
| 11 | `CPU_ONLY_LOCAL` | fallback | 0 | (none, local) | none | $0 | 5 | $0 | fallback, offline |

각 preset의 정확한 spec (lambda cell / corpus / lora_rank / retry policy / convergence xref)은 state JSON 참조.

## §3 Image variants (6)

Docker plan §6 `Composable layers` 인용 + 본 cycle 추가 variants:

| Variant key | Image | Status | Install OH | Size | Use case |
|---|---|---|---|---|---|
| `default_pytorch_2_4` | `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` | AVAILABLE | 30s | 12GB | 기본 (anima session 검증) |
| `anima_mk_xi_base_v1` | `ghcr.io/<user>/anima-mk-xi-base:v1` | DEFERRED | 0s | 5GB | Python deps 사전 설치 |
| `anima_mk_xi_models_v1` | `ghcr.io/<user>/anima-mk-xi-models:v1` | DEFERRED | 0s | 22GB | Qwen3-8B + Qwen2.5-7B 사전 로드 |
| `anima_mk_xi_eeg_v1` | `ghcr.io/<user>/anima-mk-xi-eeg:v1` | DEFERRED | 0s | 6GB | mne + EEG processing |
| `pytorch_2_5_alternative` | `runpod/pytorch:2.5.0-py3.11-cuda12.4.1-devel-ubuntu22.04` | AVAILABLE_UNTESTED | 30s | 13GB | Newer base (검증 X) |
| `cpu_default` | `runpod/cpu:ubuntu22.04` | AVAILABLE | 30s | 1GB | CPU-only EEG ingest |

**raw#10 honest**: `anima-mk-xi-*:v1` 3종 image variants는 spec only. Docker build/push/registry registration 미실행. 실제 dispatch 시 default image fallback.

## §4 GPU options matrix (5)

| GPU variant | gpu_id | $/hr | Memory | Use case |
|---|---|---|---|---|
| `h100_sxm_80gb` | NVIDIA H100 80GB HBM3 | $2.99 | 80GB | 기본 (anima session 검증) |
| `h100_nvl_94gb` | NVIDIA H100 NVL | $3.99 | 94GB | 더 큰 메모리 |
| `a100_80gb` | NVIDIA A100 80GB | $1.49 | 80GB | GPU shortage / low budget (~2× 느림) |
| `l40s` | NVIDIA L40S | $0.99 | 48GB | 작은 모델 / low budget |
| `cpu_only` | (no GPU) | $0.10 | - | EEG ingest |

## §5 Parameter sweep templates

```
lambda_grid_4x4 = papo {0.1, 0.3, 1.0, 3.0} × iir {0.3, 1.0, 3.0, 10.0}
                  → 16 cells, frozen per state/mk_xi_lambda_sweep_plan_cost_restricted_20260425.json
step_sweep      = {200, 1000, 2000, 5000, 10000}
lora_rank_sweep = {16, 32, 64, 128, 256}
corpus_sweep    = {mock, r13_alm, c4_subset, custom}
```

## §6 Scenario coverage (7)

| Scenario | Preset chain | Fallback? |
|---|---|---|
| `internet_outage` | `CPU_ONLY_LOCAL` | yes |
| `gpu_shortage` | `MK_XI_FULL_5K` w/ `a100_80gb` → `l40s` | yes |
| `low_budget` | `BASE_measurement` w/ `l40s`, `EEG_INGEST_ONLY` | yes |
| `eeg_cycle` | `EEG_INGEST_ONLY` → `V_PHEN_LZ_GWT_BATCH` | no |
| `exhaustive_validation` | 7-preset chain (all axes × paths × rounds 분할 cycle 필요) | no |
| `single_baseline_validation` | `MK_XI_FULL_5K` → `5_TUPLE_FULL_AGGREGATE` | no |
| `phen_only` | `PHEN_FORWARD_4_AXES` → `V_PHEN_LZ_GWT_BATCH` | no |

`exhaustive_validation` 누적 비용 $24.5 — 단일 cycle cap $20 위반 → 분할 cycle. raw#10 honest.

## §7 Dispatcher CLI

```
hexa run tool/anima_runpod_preset_dispatcher.hexa --selftest
hexa run tool/anima_runpod_preset_dispatcher.hexa --list
hexa run tool/anima_runpod_preset_dispatcher.hexa --preset BASE_measurement --run-id <id>
hexa run tool/anima_runpod_preset_dispatcher.hexa --preset MK_XI_FULL_5K --run-id <id> \
       --override gpu_variant=a100_80gb
hexa run tool/anima_runpod_preset_dispatcher.hexa --preset CPU_ONLY_LOCAL --run-id <id>
hexa run tool/anima_runpod_preset_dispatcher.hexa --scenario exhaustive_validation --run-id <id> --emit-only
```

**Override whitelist** (raw#12 frozen — matrix 자체는 불변):
- `gpu_variant`
- `image_variant`
- `max_cost_cap_usd`
- `max_runtime_min_cap`

**Override blocklist**: `steps`, `lambda_cell`, `corpus`, `lora_rank`, `training_enabled` 등 preset 본질 키는 변경 불가. preset 자체 갱신 필요 시 별도 cycle에서 새 preset 등록.

**기본 동작 = `--emit-only`**: dispatcher는 base orchestrator 호출 커맨드만 출력. 실 dispatch는 사용자가 emit된 커맨드 명시적 실행 시. raw#9 default-safe.

## §8 Retry policy (convergence cross-reference)

`state/convergence/h100_stage2_r6_20260425.json`의 5-attempt retry pattern을 preset 단위로 인계:

```
max_retries: 5
backoff_seconds: 8 (orchestrator helper의 ssh_wait sleep과 동일)
per_cell_max_retries: 2 (LAMBDA_SWEEP_4X4_PARTIAL only — cell 단위 fine-grained)
retry_class: transient SSH/scp/runpodctl 실패만. 모델 학습 자체 실패는 retry X.
```

## §9 Selftest expectations

`tool/anima_runpod_preset_dispatcher.hexa --selftest` 시:

- matrix JSON loadable
- preset_count >= 10
- image_variant_count >= 6
- gpu_variant_count >= 5
- scenario_count >= 5
- 모든 preset이 required fields 보유 (name/category/image_variant/gpu_variant/cost/runtime/cap/retry_policy/auto_terminate/scenario_tags)
- 모든 preset의 image_variant key가 image_variants에 존재
- 모든 preset의 gpu_variant key가 gpu_variants에 존재
- convergence_xref 파일 존재 여부는 best-effort WARN (raw#10 honest)

## §10 raw compliance

- **raw#9** — spec only, $0 (preset matrix는 doc/state/hexa SSOT only, 실 dispatch는 사용자 명령 시)
- **raw#10** — DEFERRED image variants 명시 (build 미실행), exhaustive_validation cap 위반 정직 보고, cost 추정 spot-market variance 가능
- **raw#12** — preset matrix raw#12 frozen 사전 등록, override whitelist만 허용, post-hoc 변경 X
- **raw#15** — preset matrix state SSOT (this state JSON + this doc + dispatcher hexa)
- **raw#37** — doc/state/hexa wrapper만, no .py/.sh git-tracked
- **POLICY R4** — 기존 spec scope 변경 X (orchestrator/lambda_sweep_plan/architecture_spec/pass_verdict_spec cross-reference만), preset/image/scenario 신규 axis only

## §11 Convergence cross-reference

| convergence file | preset 매핑 |
|---|---|
| `h100_stage1_20260423.json` | `BASE_measurement` (initial pod allocation pattern) |
| `h100_stage2_20260424.json` | `MK_XI_FULL_5K` (4-pod cascade per-cell) |
| `h100_stage2_r4_20260424.json` | `MK_XI_FULL_6LOSS` (early epoch trajectory) |
| `h100_stage2_r5_20260424.json` | `MULTI_BACKBONE_CROSS_BASE` (tokenizer/attention 2-axis) |
| `h100_stage2_r6_20260425.json` | `5_TUPLE_FULL_AGGREGATE` (L2 6/6 + KL 5/6) + retry policy=5 인계 |
| `h100_stage2_r7_20260425.json` | `MULTI_BACKBONE_CROSS_BASE` retry probe (D-qwen14 regression) |

## §12 Future enhancements

1. preset versioning — frozen 후 spec 갱신 시 `_v2` suffix 등록 (post-hoc 변경 X 정책 유지)
2. dispatcher 내부 cost monitor — preset chain 실행 시 누적 cost ledger 자동 갱신
3. EEG cycle preset 확장 — sleep stage / epoch length 별 sub-preset
4. multi-arch image matrix (linux/amd64 + arm64) — Docker plan §6 follow-up
5. RunPod template ID 등록 후 image_variants에 template_id 필드 추가

omega-saturation:fixpoint
