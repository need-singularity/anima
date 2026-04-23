# anima persona API — human reference

> D-axis D.1 deliverable. SSOT spec: [`openapi.yaml`](./openapi.yaml).
> Emitter: `tool/openapi_emit.hexa`. Validator: `tool/openapi_validate.hexa`.
> Source of truth for endpoint shape: `config/serve_alm_persona.json` +
> `tool/serve_alm_persona.hexa` (3-endpoint HTTP scaffold, roadmap #77,
> CP1 gated).

## Status

- Spec version: `1.0.0` (synced with `SAP_VERSION` constant in
  `tool/serve_alm_persona.hexa`).
- OpenAPI: `3.1.0`.
- LIVE target: CP1 (`2026-04-29 ~ 2026-05-02` nominal).
- Auth enforcement: placeholder (`X-Anima-Key`). Real key issuance lands
  in D.4 (`tool/api_key_issue.hexa`).

## Servers

| env       | url                                           | notes                                        |
|-----------|-----------------------------------------------|----------------------------------------------|
| local     | `http://localhost:8000`                       | `hexa tool/serve_alm_persona.hexa --dry`     |
| prod      | `https://api.anima.needsingularity.io`        | placeholder. gated on D.4 auth + D.5 billing |

## Endpoints

### `GET /health`

Liveness + backend readiness probe.

Response `200 application/json` — schema `HealthStatus`:

| field                | type    | notes                                           |
|----------------------|---------|-------------------------------------------------|
| `status`             | string  | `ok` / `degraded` / `down`                      |
| `persona`            | string  | current persona id                              |
| `mode`               | string  | `dry` / `cpu` / `gpu`                           |
| `base_model`         | string  | absolute base model path                        |
| `lora_loaded`        | bool    | whether the persona LoRA adapter is in memory   |
| `persona_layer_idx`  | int     | steering-injection layer (default 20)           |
| `phi_layer_idx`      | int     | phi-extraction layer (default 24)               |
| `sap_version`        | string  | `serve_alm_persona/<v>` stamp                   |
| `ts`                 | string  | RFC3339 UTC timestamp                           |

### `GET /personas`

Lists registered persona ids (loaded from `config/serve_alm_persona.json`).

Response `200 application/json` — schema `PersonaList`:

```json
{"personas": ["dest1", "default", "friend", "scholar", "engineer", "sorceress"],
 "default": "dest1"}
```

### `POST /persona`

Generate a persona response.

Gates (order): `cert_gate` → `an11_a` → backend forward.
Security: `apiKey` (header `X-Anima-Key`) — enforced in D.4.

Request body `application/json` — schema `PersonaRequest`:

| field          | type   | required | notes                                   |
|----------------|--------|----------|-----------------------------------------|
| `prompt`       | string | yes      | user prompt                             |
| `persona_id`   | string | yes      | one of the registered personas          |
| `max_tokens`   | int    | no       | default `256`, range `[1, 4096]`        |

Response codes:

| code  | schema          | meaning                                     |
|-------|-----------------|---------------------------------------------|
| `200` | `PersonaResponse` | persona output with gate verdicts         |
| `400` | `Error`         | malformed request                           |
| `401` | `Error`         | missing / invalid `X-Anima-Key`             |
| `429` | `Error`         | rate limit exceeded (see D.4 policy)        |

`PersonaResponse` highlights (anima-specific fields first — not present in
upstream Anthropic / OpenAI responses):

- `cert_pass` (bool) — `cert_gate` verdict.
- `an11_a` (bool) — AN11(a) weight_emergent verdict.
- `backend_invoked` (bool) — false if a gate short-circuited.
- `latency_ms` (int) — wall-clock per-request latency.
- `text` (string) — generated persona text.
- `persona_id`, `mode`, `max_tokens`, `ts` — echoed request context.

`Error` shape (OpenAI-compatible envelope):

```json
{"error": {"code": "rate_limited", "message": "...", "retry_after_s": 42}}
```

Error codes: `bad_request`, `unauthorized`, `rate_limited`, `gate_reject`,
`backend_pending`, `internal`.

## Security schemes

- `apiKey` — header `X-Anima-Key`. Issuance flow lands in D.4
  (`tool/api_key_issue.hexa`). Keys prefixed `ak_live_` (prod) or
  `ak_test_` (dev).

## Regeneration

The YAML is deterministic. To re-emit:

```sh
hexa tool/openapi_emit.hexa
hexa tool/openapi_validate.hexa
```

Selftests:

```sh
hexa tool/openapi_emit.hexa --selftest
hexa tool/openapi_validate.hexa --selftest
```

Both selftests run a round-trip (minimal config → emit → validate) and
must exit `0`.

## Related docs

- `docs/upstream_notes/d_axis_api_sdk_ship_20260422.md` — full D-axis SSOT.
- `docs/endpoint_persona_reproduce.md` — pre-CP1 local reproduction flow.
- `docs/reproducible_emit_workflow.md` — `HEXA_REPRODUCIBLE=1` convention.
