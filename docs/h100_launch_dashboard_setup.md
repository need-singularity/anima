# H100 × 4 Launch Dashboard — Setup Guide (#83 / #84)

Real-time Grafana monitoring of 4 H100 pods (Stage-2 Φ substrate independence) hosted on Hetzner ax102 CPU node (htz). Operator-side observability — does NOT execute training. See `state/h100_launch_manifest.json`.

## Prerequisites (verify before #83 kickoff)

1. Docker Engine + Compose v2 installed on htz:
   ```
   docker --version            # >= 24.0
   docker compose version      # >= v2.20
   ```
2. Outbound HTTPS (443) from htz to runpod proxy URLs.
3. Inbound 3000/9090/9093 open only to operator IP (UFW rule).
4. Pod-side `/metrics` exporter wired by `tool/phi_extractor_ffi_wire.hexa` exposing: `loss`, `vram_used_mb`, `cost_usd_so_far`, `phi_measurement_count`, `phi_value`, `launch_epoch` (label: `path_id` ∈ {p1,p2,p3,p4}).

## Launch-time env vars (fill in after `runpodctl create pod` returns proxy URLs)

```bash
export POD_P1_URL="<qwen3-8b proxy host:port>"        # p1 — Qwen/Qwen3-8B
export POD_P2_URL="<llama-3.1-8b proxy host:port>"    # p2 — meta-llama/Llama-3.1-8B
export POD_P3_URL="<ministral-3-14b proxy host:port>" # p3 — mistralai/Ministral-3-14B-Base-2512
export POD_P4_URL="<gemma-4-31b proxy host:port>"     # p4 — google/gemma-4-31B (qlora-nf4)
export GRAFANA_ADMIN_PASSWORD="<strong password>"
export SLACK_WEBHOOK_URL="<#74 endpoint TBD or hooks.slack.com/services/...>"
export TELEGRAM_WEBHOOK_URL="<#74 endpoint TBD or api.telegram.org/bot.../sendMessage>"
```

## Boot

```bash
cd /opt/anima   # or wherever the repo is checked out on htz
docker compose -f config/grafana/docker-compose.yml up -d
docker compose -f config/grafana/docker-compose.yml ps   # verify 3 services healthy
```

Open `http://<htz-ip>:3000` (admin / $GRAFANA_ADMIN_PASSWORD). Dashboard auto-provisioned: **ANIMA H100 × 4 Launch — Stage 2**.

Prometheus UI: `http://<htz-ip>:9090/targets` — confirm 4 pod jobs UP.
Alertmanager UI: `http://<htz-ip>:9093` — confirm receivers loaded.

## Alerts (2 rules, see `config/grafana/alert_rules.yml`)

| rule | expr | severity | route |
|---|---|---|---|
| `LossNaN` | per-pod loss == NaN/Inf | critical | Slack + Telegram |
| `PhiDivergence` | `stddev(phi)/avg(phi) > 0.05` for 5m | critical | Slack + Telegram |

(`BudgetBurn80Pct` 제거됨 2026-04-22 — no cap policy, user-absorbed unlimited. spend tracker dashboard panel 만 유지.)

Webhook wiring lands via #74 endpoint extension (Slack/Telegram receiver). Until #74 is live the placeholder URLs in `docker-compose.yml` cause Alertmanager to log delivery failures — alerts still fire to UI; configure receivers when #74 ships.

## Runbook anchors

- `#loss-nan` — pod should self-abort via `numerical_drift_bound=0.0002`; verify `state/h100_auto_kill_last_run.json`.
- `#phi-divergence` — check per-path hidden-state offsets (p1=4096, p2=4096, p3=5120, p4=5376) in `phi_extractor_ffi_wire.hexa`.

## Teardown (after Stage-2 close + artifacts harvested)

```bash
docker compose -f config/grafana/docker-compose.yml down            # keep volumes
docker compose -f config/grafana/docker-compose.yml down -v         # purge metrics history (only after evidence archived)
```

Archive `prometheus_data` volume to `state/h100_stage2_metrics_<ts>.tar.gz` before `down -v` if post-mortem needed.
