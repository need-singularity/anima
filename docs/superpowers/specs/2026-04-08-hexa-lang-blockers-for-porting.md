# Hexa-lang Blockers — Anima 포팅 (2026-04-08)

## 환경
- Bootstrap: `~/Dev/hexa-lang/ready/self/hexa_bootstrap` (gcc -O2 C)
- Probe dir: `/tmp/anima-probe/`

## 블로커 #1 — `format()` precision spec 미지원

**증상**: `format("{:.4f}", 0.7148)` → literal `{:.4f}` 출력 (전처리 안 됨)

**재현**:
```hexa
let a = 732.0
let b = 1024.0
println(format("{:.4f}", a / b))
```
**실제 출력**: `{:.4f}`
**기대 출력**: `0.7148`

**영향**: 정밀도 포맷 필요한 모든 파일 차단
- `anima/tools/r2_cost_calculator.py` (비용 테이블)
- `anima/tools/math_explorer.py` (수식 탐색)
- `anima/tools/param_optimizer.py`
- `anima/tools/optimal_config.py`
- `anima/tools/phi_scaling_calculator.py`
- 수치 출력 계열 전반

**요청사항 (hexa-lang)**:
- `format()` 내 `{:.Nf}` precision spec 구현
- 또는 대체 API: `format_float(x, precision)` 전용 함수
- 정수 `{:,}` thousands separator도 함께 고려

## 상태
- Probe A 실패 → 포팅 진입 전 중단
- 다른 블로커 감지 시 본 문서에 append
