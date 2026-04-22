# Grafana htz Pre-Boot Guide — pre-H100 ROI P1 (#84)

Purpose: bring Grafana + Prometheus + Alertmanager **into a ready-to-serve state**
on the Hetzner `htz` (ax102) box BEFORE H100 × 4 (#83) kickoff, so the moment
the first pod boots the dashboard already shows live panels (no operator wait
for `docker compose up` cold-start, image pull, datasource provision).

This guide is **READY-state spec only** — the agent does NOT execute these
commands. Operator copy-paste only after explicit go.

Cross-refs:
- `docs/h100_launch_dashboard_setup.md` — full launch-time runbook
- `docs/htz_compile_farm_20260419.md` — htz host inventory
- `docs/h100_roi_improvements_20260422.md` row #19 (this ROI item)
- `config/grafana/docker-compose.yml` — compose SSOT (managed by #84)

---

## 0. Pre-conditions (verify on operator workstation, not htz)

```bash
ssh hetzner "docker --version && docker compose version"
# expect:  Docker version >= 24.0   /   Docker Compose v2.20+
ssh hetzner "ls -la /opt/anima 2>/dev/null || echo 'repo not cloned yet'"
ssh hetzner "ls config/grafana/docker-compose.yml" \
    || echo 'compose file not synced — rsync repo first'
```

If repo not on htz:

```bash
rsync -avz --delete \
    --exclude='.git/' --exclude='checkpoints/' --exclude='models/' \
    --exclude='/tmp_audit/' --exclude='/build/' --exclude='/dist/' \
    /Users/ghost/core/anima/ hetzner:/opt/anima/
```

## 1. Pre-boot env file (htz, NOT committed)

Create `/opt/anima/config/grafana/.env.preboot` with placeholder pod URLs
(real proxy URLs are filled in at #83 kickoff time — Grafana scrape jobs
will simply show DOWN until then, which is the expected pre-boot state).

```bash
ssh hetzner 'cat > /opt/anima/config/grafana/.env.preboot' <<'ENV'
POD_P1_URL=placeholder.invalid:9100
POD_P2_URL=placeholder.invalid:9100
POD_P3_URL=placeholder.invalid:9100
POD_P4_URL=placeholder.invalid:9100
GRAFANA_ADMIN_PASSWORD=__SET_BEFORE_BOOT__
SLACK_WEBHOOK_URL=
TELEGRAM_WEBHOOK_URL=
ENV
ssh hetzner 'chmod 600 /opt/anima/config/grafana/.env.preboot'
```

`GRAFANA_ADMIN_PASSWORD` MUST be replaced with a real strong password before
`docker compose up`. The placeholder string is intentionally invalid so an
unconfigured boot fails loud.

## 2. Pre-pull images (warm local image cache)

```bash
ssh hetzner '
  cd /opt/anima
  docker compose -f config/grafana/docker-compose.yml --env-file config/grafana/.env.preboot pull
'
```

Expected: 3 images pulled (grafana/grafana, prom/prometheus, prom/alertmanager).
This is the longest cold-start step (~200-400 MB) — doing it pre-boot saves
3-5 min at H100 launch.

## 3. Dry-render compose config (validate SSOT before boot)

```bash
ssh hetzner '
  cd /opt/anima
  docker compose -f config/grafana/docker-compose.yml --env-file config/grafana/.env.preboot config
' | head -60
```

Verify:
- 3 services (`grafana`, `prometheus`, `alertmanager`)
- 4 prometheus scrape targets pointing at `${POD_PX_URL}` placeholders
- volume mounts for `grafana_data`, `prometheus_data`, `alertmanager_data`

## 4. Boot (operator-go only — do NOT execute pre-launch)

```bash
ssh hetzner '
  cd /opt/anima
  docker compose -f config/grafana/docker-compose.yml --env-file config/grafana/.env.preboot up -d
  docker compose -f config/grafana/docker-compose.yml ps
'
```

Expected output: 3 services with `Status = running (healthy)`.

## 5. Verification matrix

| Check | Command | Expected |
|---|---|---|
| Grafana UI reachable | `curl -sI http://<htz-ip>:3000/login` | `HTTP/1.1 200 OK` |
| Prometheus targets endpoint | `curl -s http://<htz-ip>:9090/api/v1/targets \| jq '.data.activeTargets \| length'` | `>= 4` |
| Alertmanager status | `curl -s http://<htz-ip>:9093/api/v2/status \| jq -r .cluster.status` | `ready` |
| Datasource provisioned | grafana UI → Connections → Data sources | `Prometheus` listed, status green |
| Dashboard auto-imported | grafana UI → Dashboards | `ANIMA H100 × 4 Launch — Stage 2` visible |
| Alert rules loaded | `curl -s http://<htz-ip>:9090/api/v1/rules \| jq '.data.groups[].rules \| length'` | `2` (LossNaN, PhiDivergence) |

Failed checks → see Troubleshooting (§7).

## 6. Dashboard import (manual fallback if auto-provision fails)

If §5 shows the dashboard missing:

```bash
# locate the json
ssh hetzner 'ls /opt/anima/config/grafana/dashboards/'
# expected: anima_h100x4_stage2.json (or similar)

# import via Grafana HTTP API (admin password from .env.preboot)
ssh hetzner '
  GP=$(grep ^GRAFANA_ADMIN_PASSWORD /opt/anima/config/grafana/.env.preboot | cut -d= -f2)
  curl -s -u "admin:${GP}" -H "Content-Type: application/json" \
       -X POST http://localhost:3000/api/dashboards/db \
       --data @/opt/anima/config/grafana/dashboards/anima_h100x4_stage2.json
'
```

Response should contain `"status":"success"` and a non-zero `id`.

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `docker compose pull` 401 | private registry, missing creds | Use only public images (grafana/grafana, prom/*) — confirm compose file |
| Grafana 502 on `/login` | container started but boot loop | `docker compose logs grafana --tail 100` — usually `GRAFANA_ADMIN_PASSWORD` placeholder still set |
| Prometheus targets all DOWN | placeholder pod URLs | EXPECTED until #83 kickoff overrides `.env.preboot` with real proxy URLs |
| Alertmanager receivers empty | `SLACK_WEBHOOK_URL` empty | EXPECTED pre-boot; #74 endpoint wires receivers at launch |
| Port 3000/9090/9093 unreachable from operator IP | UFW closed | `ssh hetzner 'sudo ufw status'`; open only operator IP per §0 of `h100_launch_dashboard_setup.md` |

## 8. Pre-launch handover checklist

When #83 kickoff begins, operator MUST:

1. Replace 4 `POD_PX_URL` placeholders in `.env.preboot` with real runpod proxy URLs.
2. Set `SLACK_WEBHOOK_URL` and `TELEGRAM_WEBHOOK_URL` (or leave empty if #74 not live).
3. `docker compose -f config/grafana/docker-compose.yml --env-file config/grafana/.env.preboot up -d --force-recreate prometheus`
   (only prometheus needs reload to pick up new scrape targets; grafana + alertmanager unaffected).
4. Re-run §5 verification matrix — all 4 prometheus targets should flip to UP within 30 s.

## 9. Teardown (post-Stage-2)

```bash
ssh hetzner '
  cd /opt/anima
  docker compose -f config/grafana/docker-compose.yml down            # keep volumes
  # OR: docker compose -f config/grafana/docker-compose.yml down -v   # also drop volumes
'
```

Volumes preserved by default so the dashboard history survives across launches.

---

Authored: 2026-04-22 — pre-H100 ROI P1.
Status: SPEC ONLY — no actual deployment performed.
