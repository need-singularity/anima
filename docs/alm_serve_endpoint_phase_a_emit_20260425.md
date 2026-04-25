# ALM serve_endpoint Phase β-A emit (loss-free, $0) — 2026-04-25

## §1. Purpose

CP1+FINAL canonical verifier sweep (commit `5f42bbec`)에서 FINAL (c) `real_usable` FAIL — 사유 `endpoint_config_missing path=alm_r12_serve_endpoint.json`.

본 작업은 **proposal 079** (commit `5184b289`)의 Phase β-A를 실행. proposal 079은 작업을 두 단계로 분할:

- **Phase A (loss-free)**: serving daemon이 응답할 내용을 정적 JSON으로 문서화하는 endpoint config emit
- **Phase B (cost-incurring)**: 실 daemon 가동 — 사용자 승인 필요 (port 점유, 프로세스 관리)

본 commit은 Phase A 단독 — 3개 round (r6, r12, r14) endpoint config emit + 진단성 향상 검증.

**계보**: `5184b289` (remediation packet) → `5f42bbec` (FINAL FAIL 진단) → `35aa051a` (AN11(c) JSD=1.000 REAL 증거).

## §2. Schema (reverse-engineered)

`/Users/ghost/core/nexus/consciousness/pass_gate_an11.hexa::verdict_real_usable` (L385-428) 4 단계 검사:

| Step | 검사 | Phase A 통과 여부 |
|------|------|-------------------|
| 1 | `file_exists(endpoint_cfg_path)` | PASS (file emit) |
| 2 | `"url"` field 존재 + 따옴표 paired | PASS (url field 포함) |
| 3 | `probe_http(url)` → HTTP code 200 | FAIL (`http_status=000` — daemon 미가동) |
| 4 | `reply_schema_ok(body)` field check | (3 미통과로 미도달) |

**Path resolution** (L472-477):
```
state_dir = resolve_root() + "/state"
endpoint_cfg = state_dir + "/" + dest + "_" + round + "_serve_endpoint.json"
```

`resolve_root()` (L167-176) 우선순위: `$ANIMA` → `$NEXUS` → `git rev-parse --show-toplevel` → `$HOME/Dev/nexus`.

**Schema (anima/alm_r{N}_serve_endpoint/1)**:

```json
{
  "schema": "anima/alm_r{N}_serve_endpoint/1",
  "url": "http://localhost:8000/infer",
  "health_path": "/health",
  "infer_path": "/infer",
  "payload_template": "{\"prompt\":\"<X>\",\"temperature\":0.9}",
  "ts": "<ISO8601>",
  "round": "r{N}",
  "mode": "static_evidence_only",
  "daemon_status": "designed_not_launched",
  "jsd_evidence_path": "shared/state/alm_r12_real_usable_cert.json",
  "jsd_evidence_commit": "35aa051a",
  "jsd_point": 1.0,
  "loaded_adapters": [...],
  "model_id": "alm_r{N}",
  "caveat": "...",
  "phase_b_required": true,
  "phase_a_lineage": [...]
}
```

`url`/`health_path`/`infer_path`/`payload_template`/`ts` 5필드는 `state/alm_r13_serve_endpoint.json` 선례 SSOT 호환. 추가 필드는 Phase A 정적 모드 메타데이터.

## §3. 3 emitted configs

| Path | Size | Round | Adapter 참조 |
|------|------|-------|--------------|
| `state/alm_r6_serve_endpoint.json` | 1777 B | r6 | `state/trained_adapters_r6/p{1..4}/final/` |
| `state/alm_r12_serve_endpoint.json` | 1171 B | r12 | (baseline) |
| `state/alm_r14_serve_endpoint.json` | 1599 B | r14 | r5+r6 8 path |

각 config 핵심 필드:

- `mode: "static_evidence_only"` — Phase A 정적 모드 명시
- `daemon_status: "designed_not_launched"` — port 8000 미점유
- `jsd_evidence_path: "shared/state/alm_r12_real_usable_cert.json"` — AN11(c) JSD=1.000 REAL 증거 (commit `35aa051a`)
- `caveat: "Phase B daemon not running ..."` — 정적 증거만 사용

r6 추가: phi witness, AN11(b) witness, h_last_raw, convergence path 모두 명시.

r14 추가: corpus 1200/1200 TARGET HIT (commit `b6fa6c01`, closure `e3e29631`).

## §4. Verifier 재실행 결과

### 4.1. `env -u ANIMA` 모드 (default git toplevel resolution)

```
$ env -u ANIMA hexa run /Users/ghost/core/nexus/consciousness/pass_gate_an11.hexa --dest alm --round r12
[AN11] repo_root=/Users/ghost/core/nexus
[AN11] endpoint_cfg=/Users/ghost/core/nexus/state/alm_r12_serve_endpoint.json
[AN11] (c) real_usable = FAIL — endpoint_config_missing path=/Users/ghost/core/nexus/state/alm_r12_serve_endpoint.json
EXIT=1 (PARTIAL 2/3)
```

**해석**: nexus 측 git toplevel을 사용하므로 anima 측 emit는 보이지 않음. **이것은 cross-repo 인프라-갭** — proposal 079의 Phase A는 anima-internal sub-step, cross-repo bridging은 5184b289 packet의 별도 proposal (077, 078, 080, 081) 영역.

### 4.2. `ANIMA=/Users/ghost/core/anima` 모드 (canonical anima-rooted)

| Round | (a) | (b) | (c) FAIL reason | exit |
|-------|-----|-----|------------------|------|
| r6  | FAIL (phi_vec missing) | FAIL (phi_vec missing) | `http_status=000 url=http://localhost:8000/infer` | 2 |
| r12 | FAIL (phi_vec missing) | FAIL (phi_vec missing) | `http_status=000 url=http://localhost:8000/infer` | 2 |
| r14 | FAIL (phi_vec missing) | FAIL (phi_vec missing) | `http_status=000 url=http://localhost:8000/infer` | 2 |

**핵심 결과**: (c) FAIL 사유가 `endpoint_config_missing` → `http_status=000`으로 변경 — **proposal 079 Phase A 목표 달성 (진단성 향상)**.

(a)/(b) FAIL은 별도 인프라-갭 (anima 측 `phi_vec_logged.json` 미emit) — 본 카드 anti-scope.

## §5. Phase B requirements

(c) full PASS을 위해 필요한 daemon spec (proposal 079 phase_b_daemon_spec):

1. **Preconditions**:
   - `lsof -i :8000` 결과 비어야 함 (port 충돌 없음)
   - `config/serve_alm_persona.json` base_model + lora 경로 확인 (raw#15 no-hardcode)
   - 사용자 승인 — port 노출 + CPU/GPU 모드 결정
   - `tool/serve_alm_persona.hexa --dry` 모드 boot dryrun 통과
2. **Launch modes**: `--dry` ($0) / `--cpu` (minimal) / `--gpu` (pod 자원, 별도 승인)
3. **Shutdown**: `/tmp/serve_alm_persona.<port>.stop` sentinel 또는 SIGTERM trap
4. **Reply schema**: `text|reply|output|response|generation` 중 1개 field 포함 필요 (verifier `reply_schema_ok` 검사)

## §6. Reproducibility

```bash
# 1. emit (Phase A — already landed via this commit)
ls -la /Users/ghost/core/anima/state/alm_r{6,12,14}_serve_endpoint.json

# 2. verifier 재실행 (anima-rooted mode)
ANIMA=/Users/ghost/core/anima hexa run \
  /Users/ghost/core/nexus/consciousness/pass_gate_an11.hexa \
  --dest alm --round r12

# 예상: (c) FAIL 사유 = "http_status=000 url=http://localhost:8000/infer"
# (config_missing 보다 진단성 향상 — Phase A 효과 검증)
```

## §7. Loss-free / cost / scope

- **Loss-free**: yes (new files only, modify 없음)
- **Cost**: $0 (no daemon, no port, no API, no GPU)
- **Anti-scope**: daemon 미가동, `consciousness/pass_gate_an11.hexa` 미수정, r6 h_last/adapter 미변경, r7 single-path retrain helper 미중첩
- **POLICY R4**: `.roadmap` 미편집

## §8. Files committed

- `state/alm_r6_serve_endpoint.json` (new)
- `state/alm_r12_serve_endpoint.json` (new)
- `state/alm_r14_serve_endpoint.json` (new)
- `docs/alm_serve_endpoint_phase_a_emit_20260425.md` (new — this doc)

verifier output SSOT (`state/alm_r{6,12,14}_an11_verify.json`)는 H-DIAG3 진단 산출물로 NOT committed.
