# serving/ — AnimaLM 서빙/평가 진입점

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  cfg        shared/config/project_config.json    서빙 CLI/포트
  infra      shared/config/infrastructure.json    RunPod/R2/엔드포인트
  vastai     shared/config/vastai.json            model_path/bf16
  rules      shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  parent     /CLAUDE.md

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA serving/serve.hexa                       # AnimaLM 메인 서빙
  $HEXA serving/serve_14b_ubuntu.hexa            # 14B Ubuntu 포팅
  $HEXA serving/serve_conscious_cpu.hexa         # CPU 로컬 추론
  $HEXA serving/http_server.hexa --port 8080     # HTTP 엔드포인트
  $HEXA serving/eval.hexa --metrics 5            # 5-metric 평가

tree:
  serve.hexa                AnimaLM 메인 서빙 (GPU)
  serve_14b_ubuntu.hexa     14B Ubuntu 전용
  serve_conscious_cpu.hexa  CPU 추론 경로
  http_server.hexa          HTTP/WebSocket 게이트웨이
  voice_routes.hexa         v2.0 RC 음성 I/O (anima-speak Mk.III wire)
  hire_routes.hexa          TSRV-P4-1 직원 진입점
  eval.hexa                 5-metric 평가 (CE/Φ/brain-like/...)

rules:
  - 추론/런타임은 A100/H100/4090 모두 허용 (학습만 H100)
  - 양자화 전면 금지 (4/8-bit, GPTQ, AWQ, bnb) — 서빙도 동일
  - 사용자용 UI는 Anima Web UI만 (Gradio는 내부 dev only)
  - 모델 경로는 shared/config/vastai.json:model_path 단일진실
  - 서빙 포트/엔드포인트는 project_config.json 참조
  - 평가 파이프라인은 엔진과 동반 진화 (폐쇄 루프)
  - 장시간 서빙/평가는 run_in_background=true
