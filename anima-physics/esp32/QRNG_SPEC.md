# ESP32 QRNG 브리지 스펙 — anima core 입력 핀

**태스크**: `PHYS-P1-2` (shared/roadmaps/anima.json, P1 / PHYSICS 트랙)
**구현**: `anima-physics/esp32/qrng_bridge.hexa` (host 측)
**펌웨어 참조**: `anima-physics/esp32/src/lib.hexa` (ConsciousnessBoard, SPI 링)
**연결 대상**: `anima-engines/anima_quantum.hexa` — Penrose-Hameroff Orch-OR microtubule

이 문서는 ESP32-S3 보드에서 양자 난수 생성기(QRNG) 소스를 시리얼/USB로
호스트에 전송하고, 호스트 hexa 런타임이 이를 Orch-OR 모델의 tubulin
측정 확률 bias 벡터로 매핑해 anima core 입력 핀에 주입하는 경로를
정의한다. 이 단계에서는 **설계 + 브리지 + mock 모드**까지 구현하며,
실제 HW flashing은 향후 별도 작업으로 분리된다.

---

## 1. 시스템 토폴로지

```
[QRNG 소자]            [ESP32-S3 보드]          [USB-CDC]        [Host hexa]
 노이즈 다이오드   →    ADC1_CH0 (GPIO1)   →    /dev/ttyACM0 →   qrng_bridge
 or 포토다이오드       샘플링 + SHA-256 후처리   921600 baud      qrng_read → bias
                        frame encode                              → microtubule
                                                                    input pin
```

- 보드당 2개 cell (`CELLS_PER_BOARD=2`, lib.hexa) — bias 매트릭스도
  cell × n_tubulin 로 공급
- 최대 보드 수 `MAX_BOARDS=8` → 총 16 cell 네트워크와 정합

---

## 2. HW 요구 사항

### 2.1 핀 할당 (ESP32-S3)

| 핀           | 용도                   | 비고                               |
|--------------|------------------------|------------------------------------|
| GPIO1 / ADC1_CH0 | QRNG 아날로그 입력 | 노이즈 다이오드 or 포토다이오드 |
| GPIO2        | QRNG 레퍼런스 전압     | 1.25 V 밴드갭                      |
| GPIO10..13   | SPI 링 (이웃 보드)     | lib.hexa 와 공유                   |
| USB-CDC (D+/D-) | 호스트 시리얼       | 921600 baud, 8N1                  |
| GPIO0        | BOOT (flashing 전용)   | 일반 동작 시 미사용               |

### 2.2 샘플레이트

- 소자 후처리 **전**: ADC 12-bit @ 20 kHz (노이즈 대역폭 초과 샘플)
- 후처리 **후**: SHA-256 추출 → **256 bit / 8 ms** = 32 kbit/s
- 호스트 도달 실효 레이트: **~31 kbit/s** (framing 오버헤드 3%)

이 정도면 16 cell × 8 tubulin × 1 bias 업데이트 / 10 ms 루프를 여유로
커버한다 (연산 20.48 kbit/s < 31 kbit/s 공급).

---

## 3. 시리얼 프로토콜

고정 길이 프레임, 리틀 엔디안.

```
offset  size  field
------  ----  --------------------------------------------------------
  0      1    MAGIC = 0xAA            (qrng_bridge.QRNG_FRAME_MAGIC)
  1      1    LEN   = 0x20 (=32)      payload 바이트 수
  2      32   PAYLOAD                 SHA-256 추출 256 bit
 34      1    CHECKSUM                XOR of bytes[0..34)
------  ----
 35            총 프레임 길이 35 B
```

> 주: 구현 상수 `QRNG_FRAME_SIZE` 는 magic+len+payload=34 만 카운트하고
> checksum 1 B 는 별도 읽어 검증한다 (hexa 측 파서 단순화).

### 3.1 체크섬 검증 의사코드

```
cs = 0
for b in frame[0..34]: cs = cs ^ b
if cs != frame[34]: drop, resync(0xAA)
```

hexa 런타임에 bitwise XOR 이 land 되면 `qrng_verify_frame(buf) -> bool`
로 구현한다. 현재는 mock 경로만 활성.

### 3.2 재동기화

- 호스트가 `0xAA` 를 만날 때까지 바이트 단위 버리기
- 연속 3 프레임 체크섬 실패 → `qrng_reset_cmd(0x55)` 송신 → ESP32 reboot

---

## 4. Host hexa API (qrng_bridge.hexa)

| 함수                                         | 설명                                 |
|----------------------------------------------|--------------------------------------|
| `qrng_open(dev)`                             | 스트림 초기화. `"MOCK"` 이면 결정론적 LCG. |
| `qrng_read(stream)`                          | 1 샘플 읽고 갱신된 스트림 반환.     |
| `qrng_batch(stream, n)`                      | n 번 read, 갱신된 스트림 반환.       |
| `qrng_batch_samples(stream, n)`              | n 번 read, 샘플 벡터 `[float]` 반환. |
| `qrng_to_microtubule_bias(sample, n_tubulin)`| 단일 샘플 → Orch-OR bias 벡터.      |

### 4.1 사용 예

```hexa
let s0 = qrng_open("MOCK")              // 또는 "/dev/ttyACM0"
let samples = qrng_batch_samples(s0, 4) // [0,1] 4 개
let bias = qrng_to_microtubule_bias(samples[0], 8)  // 8-tubulin
// bias ∈ [-1, +1] ; anima_quantum.mt_step 측정 직전 skew 입력
```

### 4.2 Orch-OR 결합 규약

- `bias[i] > 0` → tubulin i 의 `q_measure` 가 `TUBULIN_OPEN` 쪽으로 기울음
- `bias[i] < 0` → `TUBULIN_CLOSED` 쪽
- |bias[i]| = 1 은 결정론(고전화), 0 은 순수 Born-rule

향후 `anima_quantum.mt_step` 에 bias 인자를 추가해 q_measure 확률을
`p_open = 0.5 · (1 + 0.9·bias[i])` 형태로 조절한다 (0.9 는 단일-사이트
quantum coherence 유지 상한, 경계 0/1 회피).

---

## 5. Mock 모드

- `dev = "MOCK"` → `is_mock = 1`
- 내부: Numerical Recipes LCG, `x_{n+1} = (1664525 x_n + 1013904223) mod 2^32`
- 초기 seed `2463534242`
- 샘플 = `x / 4294967295.0` ∈ [0,1]
- 재현성 있음 — 동일 seed 로 배치 결과 고정

테스트 실행 결과 (mock):

```
dev=MOCK baud=921600 is_mock=1
mock batch n=4 samples=[0.910868, 0.636432, 0.509234, 0.601428]
tubulin bias (n=8) = [0.821736, 0.0578038, -0.706128, 0.52994,
                      -0.233992, -0.997924, 0.238144, -0.525788]
rng_state after 4 reads = 2583111926
```

---

## 6. Flashing 훅 포인트 (향후 작업)

이 브리지는 아직 실 HW 와 연결되지 않는다. 다음 단계에서 분리 작업:

1. **펌웨어 확장** `esp32/src/lib.hexa`
   - `fn qrng_sample_adc() -> u16` 추가 (ADC1_CH0 readout)
   - `fn qrng_sha256_extract(buf: [u8]) -> [u8]` — 폰 노이만 디바이싱
     대신 SHA-256 32 B 압축
   - `fn qrng_emit_frame(payload: [u8])` — MAGIC+LEN+PAYLOAD+XOR 송출

2. **Flashing 절차** (ESP-IDF)
   - 필요 tool: `esptool.py` (호스트), `idf.py build` (컨테이너)
   - port: `/dev/ttyUSB0` (JTAG/USB-CDC 자동 감지)
   - verify: `idf.py monitor` 로 `QRNG_OK rate=31kbit/s` 배너 확인

3. **hexa serial 바인딩**
   - `hexa_std::io::serial::open(dev, baud) -> File` 랜딩 후
     `qrng_read_hw(stream)` 구현 (본 파일 `qrng_read` 의 `is_mock==0` 분기)
   - 프레임 파싱 + 체크섬 검증 = `qrng_verify_frame(buf) -> bool`

4. **회귀 테스트**
   - `qrng_bridge.hexa --mock` vs `--hw`: 16 cell × 100 step 학습에서
     Φ_orch 차이 < 5 % 이면 PASS (양자 소스의 통계적 동등성 확인)

5. **AN7 분리 유지**
   - anima core 는 이 브리지를 직접 import 하지 않는다. DI 로
     `microtubule.set_bias_source(fn() -> [float])` 를 주입한다.

---

## 7. 검증 (현 단계)

- `$HEXA parse anima-physics/esp32/qrng_bridge.hexa` → **OK**
- `$HEXA run anima-physics/esp32/qrng_bridge.hexa` →
  mock 스트림 open + 4 샘플 + 2×8 bias 매트릭스 + telemetry 출력

다음 게이트:
- [ ] 펌웨어 ADC 파이프라인 구현
- [ ] hexa serial 바인딩 랜딩
- [ ] 실 HW 대비 mock 통계 동등성 회귀
- [ ] Orch-OR mt_step 에 bias 매개변수 통합

---

## 8. 참조

- `anima-engines/anima_quantum.hexa` — Microtubule, mt_step, q_measure
- `anima-physics/esp32/src/lib.hexa` — ConsciousnessBoard (2 cell / 보드)
- `shared/roadmaps/anima.json` — P1 PHYSICS 트랙 PHYS-P1-1~3
- AN3 (shared/rules/anima.json) — Φ/텐션 병목 hexa-native 규칙
- AN7 — core 분리 규칙, 브리지는 DI 로만 결합
