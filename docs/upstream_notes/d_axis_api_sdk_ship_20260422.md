# D-axis — ship · anima API / SDK 공개 (paste-ready prompt, 2026-04-22)

> 7-axis framework의 **D 축 (user-layer ship)** 전담 prompt.
> CP1 도달 이후 외부 개발자에게 anima persona endpoint + SDK 를
> 정식 공개하기 위한 **별 세션 paste-ready 작업 지시서**.
>
> 본 문서 자체는 hand-maintained spec. 다른 claude-code 세션에
> 그대로 붙여넣어 실행한다. 구현 세션이 만지는 산출물의 **형식
> 제한**은 section 5 (Hard constraints) 참조.

---

## 1. 배경 — CP1 도달 후 외부 공개 시 필요한 것

### 1.1 현재 준비된 것
- `tool/serve_alm_persona.hexa` (568L · NATIVE_HEXA) — 3-endpoint
  HTTP scaffold, CP1 도달 시 곧바로 LIVE. roadmap #77.
- `config/serve_alm_persona.json` — endpoint SSOT (host/port/auth/gates).
- `packaging/brew_formula_anima.rb` (N74) + `docs/brew_install.md`
  — macOS 로컬 설치 경로.
- `dist/` native binary — cross-platform 배포 채널.
- `docs/quickstart_5min.md` (J55) — 신규 사용자 5-분 온보딩 (현재
  cert_gate 까지만 커버 · persona API 구간 미포함).
- `.roadmap #88` — anima public API entry (planned, CP1 gated).

### 1.2 누락 (D 축 스코프)
| gap | 설명 | sub-task |
|---|---|---|
| public API spec | OpenAPI 3.1 / GraphQL schema 부재 | D.1 |
| Python SDK | `pip install anima-client` 부재 | D.2 |
| TS/JS SDK | `npm i @anima/client` 부재 | D.3 |
| auth / rate limit | `/persona` POST 가 `auth: none` | D.4 |
| billing | usage metering / quota 없음 | D.5 (optional) |

### 1.3 타임라인 전제
- CP1 도착: **2026-04-29 ~ 2026-05-02** (nominal, ROI 적용 기준;
  `docs/cp1_eta_comparison_20260422.md` 표 참조).
- D 축 착수: CP1 도달 직후.
- D 축 완료 목표: **CP1 + 1-2 주** (2026-05-13 ~ 2026-05-16).

### 1.4 upstream 의존
- hexa-lang #56 native http server (`docs/upstream_notes/hexa_lang_beta_main_acceleration_20260422.md`)
  랜딩 후에만 안정 서빙 가능. D 축은 **hexa-lang #56 landing 을 hard
  prerequisite 로 선언**.
- hexa-lang #62 SIGTERM + flock — graceful shutdown. API 공개 전 필수.

---

## 2. D 축 5 sub-task

### D.1 — OpenAPI 3.1 spec emit

**Scope**: 현 `serve_alm_persona.hexa` 3 endpoint 를 정식 OpenAPI 3.1
문서로 emit.

**입력**:
- `config/serve_alm_persona.json:endpoints[]`
- `tool/serve_alm_persona.hexa` 라인 38-44 (endpoint 시그니처 docstring)
- `state/serve_alm_persona_log.jsonl` (실제 request/response 예시)

**산출**:
- `docs/api/openapi.yaml` — OpenAPI 3.1 spec
  - `info.title`: "anima persona API"
  - `info.version`: "1.0.0" (SAP_VERSION 과 동기)
  - paths: `/health`, `/personas`, `/persona`
  - components.schemas: `PersonaRequest`, `PersonaResponse`, `HealthStatus`,
    `PersonaList`, `ErrorEnvelope`
  - security schemes: `apiKey` (header `X-Anima-Key`) + `bearerAuth` (OAuth2 JWT)
  - servers: `https://api.anima.dev/v1` (prod), `http://localhost:8000` (local)
- `tool/openapi_emit.hexa` — JSON config → YAML 자동 생성기
  (raw#10 deterministic; SSOT 는 JSON config)
- `docs/api/openapi.html` — redoc / swagger-ui 기반 정적 렌더

**성공 조건**:
- `openapi-cli validate docs/api/openapi.yaml` PASS
- `tool/openapi_emit.hexa --selftest` byte-identical on re-run

### D.2 — Python SDK (`anima-client` pip package)

**Scope**: 외부 개발자가 `pip install anima-client` → 3 줄로 첫 call.

**산출** (별도 repo `github.com/anima/anima-client-py` 권장 · pod-side
작업 · anima 메인 repo 에 .py 파일 **유입 금지**):
- `pyproject.toml` (PEP 621)
- `anima_client/__init__.py` — 재수출
- `anima_client/client.py` — `AnimaClient(api_key=..., base_url=...)`
- `anima_client/types.py` — pydantic v2 모델 (`PersonaRequest`,
  `PersonaResponse`, `HealthStatus`)
- `anima_client/errors.py` — `AnimaError`, `RateLimitError`, `AuthError`
- `tests/test_smoke.py` — live endpoint 1-call + mock endpoint 5-case
- `README.md` — 3-line quickstart 포함

**API surface** (Anthropic SDK 풍):
```py
from anima_client import AnimaClient

client = AnimaClient(api_key="ak_live_...")
resp = client.persona.generate(
    prompt="hello",
    persona_id="dest1",
    max_tokens=256,
)
print(resp.text, resp.cert_pass, resp.latency_ms)
```

**성공 조건**:
- `pip install anima-client && python -c "from anima_client import ..."` PASS
- `pytest tests/` all green
- 첫 call 까지 **≤ 5 min from clean machine** (docs/quickstart 에 추가)

### D.3 — TypeScript SDK (`@anima/client` npm)

**Scope**: Node + browser 듀얼 타겟. ESM/CJS 듀얼 빌드.

**산출** (별도 repo `github.com/anima/anima-client-ts`):
- `package.json` (exports: `.` → `./dist/esm/index.js` + `./dist/cjs/index.cjs`)
- `src/index.ts` — 재수출
- `src/client.ts` — `AnimaClient` 클래스
- `src/types.ts` — zod 스키마에서 inferred type
- `src/errors.ts` — 타입드 error 계층
- `tsconfig.json` (target ES2022, strict true)
- `test/smoke.test.ts` (vitest · msw mock)

**API surface** (OpenAI SDK 풍):
```ts
import { AnimaClient } from '@anima/client';

const client = new AnimaClient({ apiKey: process.env.ANIMA_API_KEY });
const resp = await client.persona.generate({
  prompt: 'hello',
  personaId: 'dest1',
  maxTokens: 256,
});
console.log(resp.text, resp.certPass, resp.latencyMs);
```

**성공 조건**:
- `npm publish --dry-run` PASS
- `npx tsc --noEmit` strict PASS
- Node 20 + browser (vite) 양쪽 smoke PASS

### D.4 — auth + rate limit

**Scope**: `/persona` POST 에 인증 / 쿼터 도입.

**설계 결정**:
- **Tier 1 (v1.0)**: API key (header `X-Anima-Key`)
  - keygen: `tool/api_key_issue.hexa` → `state/api_keys/<prefix>.json`
    (argon2id hash, prefix `ak_live_`/`ak_test_`)
  - revocation: `state/api_keys/revoked.jsonl` append-only
- **Tier 2 (v1.1 optional)**: OAuth2 Client Credentials (JWT HS256)
  - `/oauth/token` endpoint 추가
  - scope: `persona:read`, `persona:write`
- Rate limit: token bucket per-key
  - default: 60 req/min, 10000 req/day
  - 구현: `tool/rate_limit_gate.hexa` (inline gate, `cert_gate` 뒤 삽입)
  - state: `state/rate_limit_buckets/<key_prefix>.json` (timestamp + count)
- 429 response: `Retry-After` header + `ErrorEnvelope{code: "rate_limited"}`

**산출**:
- `tool/api_key_issue.hexa`
- `tool/rate_limit_gate.hexa`
- `config/rate_limit_policy.json` (tier → rps/rpd 매핑 SSOT)
- `docs/api/auth.md` — 발급 / 회전 / 폐기 절차
- `tool/serve_alm_persona.hexa` 수정: gate chain 에
  `rate_limit_gate` 삽입 (cert_gate 뒤, an11_a 앞)

**성공 조건**:
- 유효 키 → 200, 무효 키 → 401, 한도 초과 → 429
- 3 종 케이스 selftest byte-identical

### D.5 — billing 연동 (optional)

**Scope**: 사용량 계량 + 과금 연동. v1.0 에서는 **meter-only** (청구 X),
v1.1 부터 Stripe 연동.

**Phase A (meter-only, v1.0)**:
- 매 요청마다 `state/usage_meter.jsonl` append
  `{ts, key_prefix, endpoint, tokens_in, tokens_out, latency_ms}`
- 일일 집계 `tool/usage_rollup_daily.hexa` →
  `state/usage_daily/<YYYY-MM-DD>.json`
- 대시보드 `docs/usage_dashboard.md` (hand-rendered 초기)

**Phase B (Stripe, v1.1 optional)**:
- Stripe metered billing API 연동 (webhook: `invoice.created`)
- pricing: `$X per 1K tokens` + `$Y per 1M requests` (TBD)
- 별도 repo `anima-billing-worker` (Node/Cloudflare Worker 권장)

**Hard constraint**: anima 메인 repo 에 **결제 secret 유입 금지**.
모든 키는 `$ANIMA_STRIPE_SECRET` env 만. `.env.example` 만 commit.

---

## 3. Anthropic / OpenAI API surface 참조 가이드

| 레퍼런스 | 적용 지점 | 채택 |
|---|---|---|
| Anthropic messages API (`POST /v1/messages`) | D.1 endpoint 명명 | `/v1/persona/generate` (messages 대신 persona-specific) |
| Anthropic SDK Python `client.messages.create(...)` | D.2 method 시그니처 | `client.persona.generate(...)` — namespace 대칭 |
| OpenAI streaming SSE (`text/event-stream`) | D.1 streaming | v1.1 에 `/persona/generate/stream` 추가 (v1.0 non-streaming) |
| OpenAI error envelope `{error: {type, message}}` | D.1 error schema | 채택 + `cert_pass` 필드 확장 |
| Stripe Idempotency-Key header | D.1, D.4 | 채택 — 재시도 안전성 |
| OpenAI `X-Request-Id` response header | D.1 | 채택 — 디버깅 trace |
| Anthropic `anthropic-version` header | D.1 | `anima-version: 2026-04-22` 채택 |
| OpenAI rate-limit headers (`x-ratelimit-*`) | D.4 | 전량 채택 (`x-ratelimit-limit-requests`, `-remaining-requests`, `-reset-requests`) |

**설계 원칙**:
1. Anthropic 과 OpenAI **양쪽 개발자** 모두 0-switching-cost 로 이해.
2. `cert_pass` / `an11_a` / `latency_ms` 등 anima-고유 필드는 응답
   객체 최상위에 노출 (Anthropic/OpenAI 에 없지만 anima 차별점).
3. streaming 은 v1.1 에서 SSE (OpenAI 호환), v1.2 에서 Anthropic
   delta-style 추가 고려.

---

## 4. Success criteria

### 4.1 Primary (hard · 전량 PASS 필수)
- [ ] External dev: clone 0 repo → `pip install anima-client` →
      **첫 200 응답까지 ≤ 5 min** (stopwatch 계측, docs/quickstart 추가)
- [ ] `docs/api/openapi.yaml` openapi-cli validate PASS
- [ ] Python SDK: `pip install anima-client` 후 smoke test PASS
- [ ] TS SDK: `npm i @anima/client` 후 smoke test PASS
- [ ] auth: 유효/무효/한도초과 3-case selftest byte-identical
- [ ] `serve_alm_persona.hexa` gate chain 수정 후 기존 selftest 전량 PASS
      (regression 0)

### 4.2 Secondary (soft · 80%+ 권장)
- [ ] Python SDK 타입 힌트 100% (`mypy --strict` 0 error)
- [ ] TS SDK strict mode 0 error
- [ ] usage meter 일일 rollup 자동화 완료
- [ ] auth 키 회전 문서화
- [ ] API 첫 GA 출시 blog/changelog 초안

### 4.3 Deferred (v1.1+)
- SSE streaming
- OAuth2 full flow
- Stripe 과금 연동
- Go SDK

---

## 5. Hard constraints (규정 · 전량 준수)

1. **raw#9 hexa-only**: anima 메인 repo 에 **`.py` 파일 유입 절대 금지**.
   Python SDK 는 **별도 repo** (`anima-client-py`). anima 메인 repo
   내에서는 SDK 가 존재한다는 **문서 (`docs/api/*.md`) + OpenAPI spec**
   만 유지.
   - 예외: 기존 `STAGED_FOR_POD` 경로 (`/workspace/serve_alm_persona.py`)
     는 pod-only 유지. repo 에 commit 금지.
2. **raw#10 deterministic**: 모든 `tool/*.hexa` 산출물 byte-identical.
   timestamp + log 만 non-pure.
3. **raw#11 snake_case**: hexa 파일 + JSON 키 전량 snake_case.
   SDK (Python/TS) 는 각 언어 convention 따름 (py: snake_case,
   ts: camelCase) — 변환 layer 는 SDK 내부에서 수행.
4. **raw#12 실측 only**: billing meter rollup 등 모든 수치는 실제
   로그 기반. 샘플/fake 데이터 금지.
5. **raw#15 no-hardcode**: endpoint URL / api key prefix / rate limit
   tier 전량 `config/*.json` SSOT. 코드는 config 를 읽음.
6. **Secret 유입 금지**: `.env` / API key 평문 / Stripe secret /
   JWT signing key 전량 **commit 금지**. `.env.example` 만.
7. **NO emoji** (문서 포함).
8. **본 문서 ≤ 400 lines** (이 문서 자체 제약).
9. **.roadmap 엔트리 선 갱신**: D.1-D.5 각각 `.roadmap` 항목으로
   등록 후 착수. ID 는 `#88` 부터 순차.
10. **cross-repo dep 선언**: `anima@D.*` → `hexa-lang@56` (http server)
    hard dep 명시.

---

## 6. Test plan

### 6.1 Unit
- OpenAPI emit: `tool/openapi_emit.hexa --selftest` byte-identical
- rate limit gate: `tool/rate_limit_gate.hexa --selftest` 3-bucket case
- api key issue: `tool/api_key_issue.hexa --selftest` 발급/검증/폐기

### 6.2 Integration (CP1 LIVE 전제)
- Python SDK live smoke: `pytest -k live` (CI env 에서 ANIMA_API_KEY 주입)
- TS SDK live smoke: `vitest run --project live`
- E2E quickstart: clean GitHub Codespace 에서 5-min quickstart
  stopwatch 계측 (3 명 × 3 회 평균)

### 6.3 Regression
- `tool/serve_alm_persona.hexa --selftest` CP1-PRE golden 과 byte-identical
  유지 (gate chain 추가 후에도).
- `.meta2-cert/` 체인 무결성 — cert_gate reward_mult byte-identical.

### 6.4 Load
- `tool/api_load_bench.hexa` — 1 key × 60 req/min × 10 min sustained
- 429 정확성: 61 번째 요청 429, `Retry-After` 정확
- latency p50/p95/p99 report → `state/api_load_bench_<ts>.json`

### 6.5 Security
- api key: argon2id hash (cleartext 저장 X) — grep 으로 검증
- rate limit bypass 시도: 다중 키 rotation 으로 quota 우회 불가
- CORS: allowlist (anima.dev + localhost:*) 외 block
- HTTPS enforcement (prod) — HTTP 301 → HTTPS

---

## 7. Deliverable checklist (별 세션이 완료 시 보고 형식)

```
[D.1] docs/api/openapi.yaml                       [ ]
[D.1] tool/openapi_emit.hexa                      [ ]
[D.1] docs/api/openapi.html (rendered)            [ ]
[D.2] anima-client-py repo created + published    [ ]
[D.2] docs/api/python_sdk.md                      [ ]
[D.3] anima-client-ts repo created + published    [ ]
[D.3] docs/api/typescript_sdk.md                  [ ]
[D.4] tool/api_key_issue.hexa                     [ ]
[D.4] tool/rate_limit_gate.hexa                   [ ]
[D.4] config/rate_limit_policy.json               [ ]
[D.4] docs/api/auth.md                            [ ]
[D.4] serve_alm_persona.hexa gate chain 수정      [ ]
[D.5] tool/usage_rollup_daily.hexa                [ ]
[D.5] docs/usage_dashboard.md                     [ ]
[D.*] quickstart_5min.md 에 persona API 섹션 추가 [ ]
[D.*] .roadmap #88-#92 엔트리 기재                [ ]
```

---

## 8. Out-of-scope (D 축에서 하지 않는 것)

- 모델 학습 / CP2 dest2 3-in-1 (B/E/F 축 스코프)
- phi_extractor 성능 튜닝 (G 축)
- CPU superlimit / H100 오케스트레이션 (A 축)
- cert_gate stdlib migration (C 축, upstream hexa-lang #54 소비)
- UI / dashboard frontend (별도 축)

---

_End of D-axis prompt. Paste-ready. Estimated completion: CP1 + 1-2 주._
