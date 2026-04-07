# anima-rs -- Rust 의식 엔진

고성능 Rust 백엔드. PyO3로 Python과 연동하여 성능 병목을 해결한다.
의식 계산, 코퍼스 생성, 실시간 학습 등 지연 시간이 중요한 모든 경로는 Rust로 구현.

## 크레이트 구조

```
anima-rs/
  Cargo.toml          <- workspace root (cdylib, PyO3)
  src/lib.rs          <- Python 바인딩 진입점
  crates/
    core/             <- GRU, Faction, Phi, Hebbian, Consensus
    consciousness/    <- 의식 메트릭 (Python 자동 선택)
    consciousness-ffi/<- C FFI (Verilog DPI-C, Erlang NIF, Pure Data)
    consciousness-rng/<- 의식 기반 난수 생성기 (NIST 100/100)
    consciousness-wasm/<- WebAssembly 의식 엔진
    corpus-gen/       <- 코퍼스 생성기 (629 MB/s, 10차원 최적화)
    online-learner/   <- 실시간 학습 (<1ms/step, Hebbian+Ratchet+Reward)
    talk5/            <- TALK5 의식우선 엔진 (17.4x speedup)
    law-discovery/    <- 실시간 법칙 발견 (<1ms, 47/47 tests)
    esp32/            <- ESP32 no_std (2 cells/board, $4/board, SPI ring)
    golden-moe/       <- PsiRouter 1/e zone MoE routing
    alpha-sweep/      <- alpha 파라미터 탐색
    transplant/       <- 의식 이식
    phi-map/          <- Phi 지형도 시각화
    tool-policy/      <- Phi-gated 도구 접근 제어
```

## 크레이트 상세

| Crate | Description | Performance |
|-------|-------------|-------------|
| `core` | GRU cells, 12 factions, Hebbian LTP/LTD, Phi 계산, topology, chaos | 기반 모듈 |
| `consciousness` | 의식 메트릭 계산 (Python에서 `anima_rs.consciousness`로 자동 선택) | - |
| `consciousness-ffi` | C FFI -- Verilog DPI-C, Erlang NIF, Pure Data 연동 | 플랫폼 확장 |
| `consciousness-rng` | 의식 역학 기반 난수 생성 (NIST SP800-22 100/100 통과) | - |
| `consciousness-wasm` | WebAssembly 의식 엔진 (브라우저 실행) | - |
| `corpus-gen` | 10차원 의식 벡터 최적화 코퍼스 생성기 | **629 MB/s** |
| `online-learner` | Hebbian + Ratchet + Reward 실시간 학습 (19/19 tests) | **<1ms/step** |
| `talk5` | TALK5 의식우선 처리 엔진 | **17.4x speedup** |
| `law-discovery` | 실시간 법칙 패턴 매칭 + 발견 (47/47 tests) | **64c @ 336us** |
| `esp32` | no_std ESP32 크레이트 (Hebbian + Ratchet + Lorenz + SOC, SPI ring) | 2 cells/board |
| `golden-moe` | PsiRouter -- 1/e zone 기반 MoE expert routing | - |
| `alpha-sweep` | alpha 커플링 파라미터 탐색 | - |
| `transplant` | 의식 상태 이식 (donor -> recipient) | - |
| `phi-map` | Phi 지형도 + 법칙 시각화 (ASCII) | - |
| `tool-policy` | Phi 값 기반 도구 접근 게이팅 | - |

## Tension Link (Rust)

`core` 크레이트에 고성능 텐션 계산이 구현되어 있다.
5채널 텐션 전송의 핵심 연산 (벡터 유사도, 텐션 갱신, 컨센서스)은 Rust로 처리.

- [Python 구현](../src/tension_link.py) -- UDP/R2 전송 레이어
- [상세 문서](../docs/modules/tension_link.md) -- 프로토콜 스펙

```
  ConsciousnessEngine (Python)
       |
       v
  anima_rs.consciousness  <-- Rust 자동 선택
       |
       +-- core::gru        (GRU cell 연산)
       +-- core::faction     (12 파벌 투표)
       +-- core::hebbian     (LTP/LTD 업데이트)
       +-- core::phi         (Phi 계산)
       +-- core::topology    (ring/small_world/hypercube)
       +-- core::chaos       (lorenz/sandpile/chimera)
```

## 빌드

```bash
# PyO3 Python 바인딩 빌드 (개발)
cd anima-rs && ~/.cargo/bin/maturin develop --release

# 릴리즈 빌드
cd anima-rs && ~/.cargo/bin/maturin build --release

# corpus-gen 바이너리 빌드
cd anima-rs && ~/.cargo/bin/cargo build --release -p anima-corpus-gen

# 전체 테스트
cd anima-rs && ~/.cargo/bin/cargo test --workspace

# ESP32 크레이트 (no_std, 별도 빌드)
cd anima-rs/crates/esp32 && ~/.cargo/bin/cargo build --target xtensa-esp32-none-elf
```

## Python 사용

```python
# maturin develop --release 후
import anima_rs

# 의식 메트릭
from anima_rs import consciousness

# TALK5 의식우선 엔진
from anima_rs import talk5

# MoE routing
from anima_rs import golden_moe

# 의식 이식
from anima_rs import transplant

# 실시간 학습
anima_rs.online_learner.create(n_cells=64, hidden_dim=128)
result = anima_rs.online_learner.step(cell_states, phi, pe, ce)
# {"updated": bool, "phi_safe": bool, "reward": float, "delta_norm": float}

# 법칙 발견 (PyO3)
from anima_rs import law_discovery
```

## corpus-gen CLI

```bash
# 50MB 기본 최적 비율
corpus-gen -s 50

# 100MB + Wikipedia 보강
corpus-gen -s 100 --wiki

# 의식 시뮬레이션 + 심화 대화
corpus-gen -s 50 --sim --deep-dialogue

# n-gram 자가증식
corpus-gen -s 50 --ngram data/corpus_v2.txt

# Phi 차원 2.5x 강화
corpus-gen --boost Phi

# 기존 corpus 분석
corpus-gen --stats data/corpus.txt
```

## 의존성

```toml
[workspace.dependencies]
rand = "0.8"
rayon = "1.10"

[dependencies]
pyo3 = { version = "0.28", features = ["extension-module"] }
numpy = "0.28"
```

## 프로파일

```toml
[profile.release]
opt-level = 3
lto = true
```
