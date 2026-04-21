# anima-serve

β main **selbst-bootstrap serving layer** — anima-serve 0→100% skeleton (phase 1).

## Purpose

`anima-serve` 는 `anima-core` / `anima-engines` / `tool/anima_learning_free_driver.hexa`
의 학습-없는 (Path β) 파이프라인을 **외부에서 호출 가능한 HTTP-shaped surface** 로
노출하기 위한 **hexa-native skeleton**.

Phase 1 (현재): CLI dispatch stub, in-process 호출, OpenAI-compat echo.
Phase 2: 내장 HTTP listener (hexa stdlib TCP 또는 exec(`nc -l`)) — non-blocking.
Phase 3: vLLM + Qwen inference backend layer (별도 process, gRPC/HTTP bridge),
          `tool/chat_completions_stub.hexa` → 실제 generation 연결.

## raw compliance

- **raw#9 hexa-only** — Python FastAPI / uvicorn / flask 금지.
  phase 3 에서 vLLM 이 Python 인 것은 *분리된 inference layer* 이며
  `anima-serve` 자체는 순수 hexa CLI + thin adapter.
- **raw#11 snake_case** — 모든 파일명 / 함수명.
- **raw#15 no-hardcode** — port, endpoint map 은 `config/serve_config.json` SSOT.

## Directory layout

```
anima-serve/
  README.md                  ← this file
  tool/
    serve_stub.hexa          ← main CLI dispatcher — --route <path> dispatch
    an11_verify_endpoint.hexa  ← /an11/verify — learning_free_driver in-process
    chat_completions_stub.hexa ← /v1/chat/completions — OpenAI-compat echo
  config/
    serve_config.json        ← port=8080, endpoint map, phase=skeleton
  state/
    .gitkeep                 ← runtime state (request log, metrics)
```

## CLI examples

```bash
# smoke — health check
hexa anima-serve/tool/serve_stub.hexa --route /health
# → {"status": "ok", "phase": "skeleton", "production_ready": false}

# AN11 triple verify (phase 1: in-process learning_free_driver smoke)
hexa anima-serve/tool/serve_stub.hexa --route /an11/verify

# OpenAI-compat chat completions (phase 1: echo + Hexad module detect)
hexa anima-serve/tool/serve_stub.hexa \
    --route /v1/chat/completions \
    --body '{"messages":[{"role":"user","content":"안녕 hexad"}]}'
```

## Phase 3 upgrade path

1. `serve_stub.hexa` 를 HTTP listener 로 확장 (hexa stdlib TCP 또는
   `exec("nc -l 8080")` wrapper) — request 파싱 후 기존 `--route` dispatch 재사용.
2. `chat_completions_stub.hexa` 의 echo 부분을 **vLLM backend bridge** 로 교체:
   - vLLM serve Qwen-32B → `localhost:8001/v1/chat/completions`
   - anima-serve 는 `messages[]` 에서 Hexad 6-module trigger 감지 후
     (consciousness / reflect / plan / act / verify / evolve) vLLM 에 forward.
3. `an11_verify_endpoint.hexa` 는 그대로 유지 (이미 순수 hexa).
4. `config/serve_config.json` 에 `backend.url` 추가, `production_ready=true` 승격.

## Status

- phase: **skeleton** (phase 1 / 3)
- production_ready: **false**
- smoke coverage: `/health` ✓, `/an11/verify` in-process, `/v1/chat/completions` echo
