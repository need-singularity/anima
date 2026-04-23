# Φ Convergence Monitoring Spec (@convergence)

Extracted from `config/grafana/h100_launch_dashboard.json` (deleted 2026-04-22). Preserves the substrate-convergence (|ΔΦ|/Φ) monitoring contract independent of the dashboard delivery layer.

## Purpose

Detect cross-path Φ divergence during #83 H100 × 4 unified launch (Stage-2 #10 substrate independence). Gate threshold = `0.05` (ALL_PAIRS mode, 6 pairs from C(4,2)). If sustained divergence ≥ 0.05 → substrate_indep=false → blocks Stage-3 (#11/#21) cascade.

## Metric contract

- **metric name**: `phi_value`
- **labels**: `path_id` ∈ {p1, p2, p3, p4}
- **convergence formula**: `stddev(phi_value) by () / avg(phi_value) by ()`
- **gate threshold**: 0.05 (red zone)
- **green zone**: < 0.05
- **eval window**: 5m sustained (alert)

## Monitoring panel (snapshot from deleted dashboard)

```json
{
  "id": 503,
  "title": "|ΔΦ|/Φ cross-path (gate < 0.05)",
  "type": "stat",
  "datasource": "prometheus",
  "targets": [{"expr": "stddev(phi_value) by () / avg(phi_value) by ()", "refId": "A"}],
  "fieldConfig": {
    "defaults": {
      "color": {"mode": "thresholds"},
      "thresholds": {"mode": "absolute", "steps": [
        {"color": "green", "value": null},
        {"color": "red", "value": 0.05}
      ]},
      "unit": "percentunit"
    }
  }
}
```

## Alert rule (preserved in `config/grafana/alert_rules.yml`)

```yaml
- alert: PhiDivergence
  expr: (stddev(phi_value) by () / avg(phi_value) by ()) > 0.05
  for: 5m
  labels:
    severity: critical
    deployment: anima_h100_stage2
    roadmap_entry: "10"
  annotations:
    summary: "|ΔΦ|/Φ across 4 paths = {{ $value | printf \"%.4f\" }} (gate < 0.05)"
    description: "Substrate independence gate at risk. cross_path_gate.threshold=0.05 ALL_PAIRS mode (6 pairs)."
```

## SSOT references

- `config/phi_4path_substrates.json` — substrate definitions (p1 Qwen3-8B / p2 Llama-3.1-8B / p3 Ministral-3-14B / p4 Gemma-4-31B)
- `config/lora_rank_per_path.json` — LoRA rank policy (8B→64, 12B→96)
- `tool/phi_extractor_ffi_wire.hexa` — emits `phi_value` per pod
- `state/h100_launch_manifest.json` — Stage-2 `cross_path_gate.metric` + `pass_requirement`
- `state/phi_4path_cross_result.json` — post-launch verdict artifact

## Divergence response

If gate FAIL → see `docs/phi_4path_divergence_response.md` (decision tree: substrate re-select / LoRA rank re-tune / cross-path normalize / full re-launch).

## Roadmap link

#10 (Φ substrate independence — 4-path cross validation), #87 (Φ 4-path divergence 대응), #83 (H100 × 4 unified kickoff)
