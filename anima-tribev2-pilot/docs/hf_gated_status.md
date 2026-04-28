# Pilot-T1 HF Gated Access Status

## Current state (2026-04-26)

- **Status**: ✅ **APPROVED** (cron `98896ff1` polling detect)
- **Approval timestamp**: 2026-04-26 (cron fire 시점)
- **Account**: HF `dancinlife`
- **Model**: `meta-llama/Llama-3.2-3B`
- **License**: Llama 3.2 Community License (`gated:"manual"` → granted)
- **Verification**: `hf_hub_download('meta-llama/Llama-3.2-3B', 'config.json')` 성공, `/tmp/llama_check/config.json` 다운로드
- **Pilot-T1 v2 status**: `T1_V2_LAUNCHED` (cron self-disable trigger)

## Pilot-T1 v2 trigger

Once HF approval lands, Pilot-T1 full-mode v2 재시도 활성화. Trigger flow:

1. 사용자가 HF 승인 통지 받으면 메인 세션에 알림
2. 즉시 Pilot-T1 v2 subagent 발사 (`acbb32a9` 후속)
3. 재실행 명령:
   ```bash
   cp anima-tribev2-pilot/state/launch_h100_pilot_t1.sh.txt anima-tribev2-pilot/scripts/launch_h100_pilot_t1.sh
   chmod +x anima-tribev2-pilot/scripts/launch_h100_pilot_t1.sh
   bash anima-tribev2-pilot/scripts/launch_h100_pilot_t1.sh
   ```
   (`install_pod_deps.sh` / `pilot_t1_inference_full.py` 동일 방식 `.txt` → live form 복원)

## Estimated cost (v2)

- Pod cache primed (TRIBE ckpt 3.6GB + whisperx PEX 5GB + spacy lg 400MB 보존)
- Llama config.json 한번 fetch만 추가
- ~**13분 × $2.99/hr ≈ $0.65**
- 이전 v1 cycle cost: $0.90 (이미 spent, pod RUNNING idle)

## Outcomes (v2 PASS 시)

- **T1_PASS** (inter r < 0.7 AND intra r > 0.85) → Pilot-T2 (paradigm v11 8th orthogonal axis) un-park (이미 PREP_COMPLETE)
- **T1_FAIL** (r > 0.95) → R33 ledger entry는 architectural_reference tier 유지
- **T1_INCONCLUSIVE_FULL** → n_per_family 확장 또는 single-modality ablation iterate

## Cross-link

- `anima-tribev2-pilot/state/pilot_t1_full_mode_result_v1.json` — v1 DEFERRED verdict
- `anima-tribev2-pilot/state/manifest_full_mode.md` — full-mode runbook
- `anima-tribev2-pilot/state/launch_h100_pilot_t1.sh.txt` — H100 launch script (cleanup-resistant `.txt`)
- `.roadmap` #167 — Pilot-T1 v1 DEFERRED entry
- 메인 세션 trigger 대기 상태
