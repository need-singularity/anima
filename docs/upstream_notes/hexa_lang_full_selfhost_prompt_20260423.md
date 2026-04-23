# hexa-lang 전달 프롬프트 — runtime.c / Rust 드라이버 완전 탈피, 순수 self-hosting 로드맵

**From**: anima (2026-04-23, post Stage-1 H100 live bootstrap)
**To**: hexa-lang 차기 세션
**카테고리**: lang_evolution · bootstrap / self-host / cross-platform

---

## 0. 한 줄 요청

`hexa-lang` 을 **runtime.c (C) 와 Rust 드라이버 (/opt/homebrew/bin/hexa) 양쪽에 대한 의존을 끊고** 순수 `.hexa` 소스로 완전 self-host 되는 언어 처리계로 전환하라. Mac arm64, Linux x86_64, Linux arm64 3개 타겟에 대해 동일한 `.hexa` → 실행 가능 바이너리 파이프라인이 성립할 것.

---

## 1. 오늘 (2026-04-23) 실측 상태 — anima Stage-1 live 에서 관측

### 1.1 실제로 있는 것

| 자산 | 경로 | 정체 | 용도 |
|---|---|---|---|
| Rust 드라이버 | `/opt/homebrew/bin/hexa` (Mac arm64, Mach-O) | Rust 로 작성된 orchestrator. `hexa run <f>` 받아서 transpile→clang→exec 전체 파이프 구동 | Mac 개발자 경험 (유일한 풀-CLI) |
| 자호스팅 transpiler (Mac) | `/Users/ghost/core/hexa-lang/self/native/hexa_v2` (Mac arm64) | `.hexa` 파싱 + codegen_c2 → C 소스 출력. `hexa-cc <input.hexa> <output.c>` | 트랜스파일 단계 |
| 자호스팅 transpiler (Linux) | `build/hexa_v2_linux_x86_64` (5.58 MB, static musl ELF, hexa-lang `1fdc0100`) | 위와 동일 기능, Linux 빌드 | 2026-04-23 이번에 처음 배포됨. Linux 용 풀-CLI 는 없음. |
| C runtime | `self/runtime.c` (~7000 줄) | NaN-boxing `HexaVal`, arena, 문자열/배열/맵, TAG_FN 셔림, `hexa_timestamp`, `hexa_str_*`, `hexa_array_*`, 신호/파일락/소켓/FFI, 끝자리에 `#define` 기반 builtin 셔림 | 트랜스파일된 C 가 `#include "runtime.c"` 로 빨아들이는 실행 backbone |
| 빌드 툴체인 | `clang` (혹은 `gcc`) + `libc` + `libm` | transpile 산출물 `.c` 를 실제 실행 바이너리로 만들어내는 외부 의존 | 필수 외부 툴체인 |

### 1.2 이번 세션에서 발견된 **self-host 결손** 6건

(anima `state/h100_stage1_launch_state.json:_meta.convergence` I7–I11 + I8 상세)

| # | 결손 | 근본 원인 | 현재 우회 |
|---|---|---|---|
| **결손-A** | **Linux full-driver 없음** | Rust 드라이버는 Mac 바이너리 뿐. Linux 에는 transpiler-only 하나뿐. | anima 에서 `tool/hexa_linux_shim.bash` 같은 bash wrapper 자체 작성 (`hexa run <f>` → `hexa_v2` + `clang -I self` + exec) |
| **결손-B** | **runtime.c 가 C** | 자호스팅이라면서 런타임 7000줄은 손으로 쓴 C. NaN-boxing, arena, map 전부 C. | C 로 계속 유지. 플랫폼마다 clang 의존. |
| **결손-C** | **builtin name mangling 누락 (hxa-004 계열)** | `setenv` / `exec_capture` / `now` / `push` 같은 builtin 을 transpiler 가 bare identifier 로 emit. runtime.c 끝자리에 `#define` 셔림으로 간신히 살림. | hexa-lang `373696e7` 에서 now/push 추가 완료. 하지만 **임시 해법**. |
| **결손-D** | **Rust 드라이버가 argv[0] 을 2번 삽입** (`runtime.c:3442` `hexa_set_args` 주석) | "인터프리터 모드와 동일한 인덱스 유지" 라는 명분으로 duplicate 삽입. 결과: 모든 `args()` 소비자가 stage0 와 driver 모드에서 다른 argv 레이아웃을 받음. | anima `tool/an11_a_verifier.hexa` 에서 `argv[0]==argv[1]` 감지 후 skip0=2 로 보정 (lang_gap 우회). |
| **결손-E** | **`.last_index_of()` 코드젠 누락** | runtime.c 에 `hexa_str_last_index_of(s, sub)` 함수는 존재 (`runtime.c:2634`). 하지만 codegen_c2 가 `.last_index_of()` 메서드 호출을 이 함수로 디스패치하지 않음 → `CODEGEN ERROR: unhandled method: last_index_of`. | anima 에서 `_last_idx_char(s, ch)` 수작 구현 반복 작성. |
| **결손-F** | **`hexa run <file>` 무신경 파싱** | Linux 의 `hexa_v2` 는 `<input.hexa> <output.c>` 만 이해. 실사용자가 Mac CLI 관성으로 `hexa run tool/foo.hexa --opts` 입력 시 `run` 을 input, `tool/foo.hexa` 를 output 으로 해석 → **소스 파일 덮어씀** (.hexa 가 .c 로 overwrite). | anima 가 직접 bash shim 으로 보호. 바이너리 자체에 `run` 서브커맨드 이해 없음. |

이 6건 중 어느 하나도 "자호스팅 언어" 의 정상 상태로 보기 어렵다. anima 에서 임시방편 6개가 쌓였고 계속 쌓일 것이다.

---

## 2. 목표 — 순수 self-host

### 2.1 정의

"hexa-lang 은 self-hosted 다" 의 의미가 현재는 **"transpiler 를 .hexa 로 쓸 수 있다"** 수준에 머물러 있다. 이를 다음 세 축 모두로 확장:

**(축-1) 컴파일러 self-host**
현재도 ✓. `self/hexa_full.hexa` 에서 codegen_c2 까지 포함해서 출력 C 를 생성. 단, 이 산출물은 여전히 runtime.c 를 **include** 해야 링크가 된다.

**(축-2) 런타임 self-host**
현재 ✗. `runtime.c` 7000 줄이 C. NaN-boxing / arena / string / map / I/O / 신호 전부 C. hexa 쪽에서는 `TAG_FN` 으로 이름을 매달 뿐.

목표: runtime 을 `.hexa` 로 작성 (혹은 최소한 "무의존 freestanding C + 기계 검증된 .hexa stub" 조합) 하여 `hexa-lang/self/runtime.hexa` 가 정본이 되게 한다. 빌드 시 transpiler 가 runtime.hexa → runtime.c → 오브젝트 로 **자체 생성** 하고, 이후 사용자 코드는 그 오브젝트와 링크.

**(축-3) 드라이버 self-host**
현재 ✗ (Mac) / ✗ (Linux). Rust 드라이버 (`/opt/homebrew/bin/hexa`) 가 orchestration 을 독점. Linux 는 그 drvier 자체가 없어서 anima 가 bash shim 을 올렸다.

목표: `hexa_driver.hexa` 를 작성하고 플랫폼별로 동일 소스에서 stage0 부트스트랩으로 자기 자신을 빌드. 즉 `hexa run <f>`, `hexa build <f> <out>`, `hexa cache`, `hexa fmt` 등 모든 서브커맨드를 `.hexa` 로. 외부 의존은 **`clang`/`cc` 하나 + libc/libm** 만.

### 2.2 "자호스팅" 의 합격선

자호스팅 완료의 검증 조건:

1. **clean-room 재구축 가능**: 새 Linux 박스에서 `cc` 와 `libc` 만 있고 어떤 prebuilt hexa 바이너리도 없이, `bootstrap.sh` 또는 `make` 한 번에 stage0 → stage1 → stage2 를 전부 통과해 `build/hexa` 풀-CLI 가 생성된다.
2. **Rust 0 줄**: 레포 안에 `*.rs` / `Cargo.toml` / `cargo` 를 언급하는 빌드 스텝이 없다.
3. **runtime.c 2 레이어 허용**: `runtime_core.c` (arena/NaN-box/malloc/libc glue, ≤ 500 줄 검증가능) 는 유지하되, `runtime_hi.hexa` (stdlib 전부 — str, arr, map, json, net, signal, flock, timestamp, exec) 는 .hexa 로. 7000 줄 C 는 500 줄 C + 6500 줄 .hexa 로 리팩터.
4. **3 플랫폼 동일 경로**: Mac arm64, Linux x86_64, Linux arm64 에서 동일 `.hexa` 소스가 동일 빌드 스크립트로 동일 CLI 를 산출. 플랫폼별 분기는 C 하단 `runtime_core.c` 안에만 허용.
5. **`hexa run <f>` 공식화**: CLI 첫 positional 을 `.hexa` 로 보면 implicit run, 그 외 `{run, build, fmt, cache, test, self-build, version}` 서브커맨드. anima 의 bash shim 로직이 **공식 드라이버** 로 옮아간다.

---

## 3. 구체적 작업 계획 (M1 → M5)

**M1 — 런타임 2 레이어 분할** (결손-B 해소 착수)
- `self/runtime_core.c` 추출: `HexaVal` 정의, arena, scope push/pop, gc 훅, malloc glue, signal/flock 으로 최소화. `scripts/runtime_core_audit.sh` 로 500 줄 상한 강제.
- 나머지 모두 `self/runtime_hi.hexa` 로 이관. `hexa_str_join`, `hexa_timestamp`, `hexa_base64_*`, `hexa_exec_capture`, `hexa_setenv`, `hexa_array_push`, `hexa_map_*` 등 → .hexa 에서 `extern fn` 으로 `runtime_core.c` 의 최소 primitive 만 부르고 나머지는 hexa 로직.
- 통과 기준: `self-build` 후 `nm build/libruntime.a | wc -l` 이 현재 대비 80% 감소.

**M2 — builtin name mangling 정식화** (결손-C, hxa-004 후속)
- `codegen_c2.hexa` 에서 builtin 식별자 전부 `hx_` prefix 로 emit. runtime.c 끝자리 `#define setenv hx_setenv` 같은 hack 제거.
- 테스트: `bench/snapshots/builtin_mangling.hexa` (12개 builtin 전부 네이밍 검증).
- 통과 기준: `grep -c '#define.*hx_' self/runtime_core.c` == 0.

**M3 — argv[0] 중복 삽입 정책 고정** (결손-D)
- `runtime.c:3442` `hexa_set_args` 의 duplicate 삽입 로직 제거. stage0 / driver / interpret 모드 argv layout 을 통일.
- 대신 `args()` 자체가 "실제 user 인자" 만 반환하도록 API 계약 확정 (argv[0] = 첫 user arg, 스크립트 경로는 `script_path()` 별도 API 로).
- anima 쪽에서 `an11_a_verifier.hexa` / 기타 positional-파싱 도구가 skip0 분기 없이 동작하게 검증.

**M4 — `.last_index_of()` 등 codegen 완성** (결손-E)
- runtime.c 에 이미 구현된 함수 (`hexa_str_last_index_of`, `hexa_str_replace_all`, 기타 몇십개) 의 codegen 디스패치 전수조사. 누락된 메서드는 codegen_c2.hexa 에서 `method_name` 테이블 업데이트.
- 최소 목록: `.last_index_of`, `.find`, `.rfind` (이미 `002` 에서 처리), `.starts_with`, `.ends_with`, `.pad_start`, `.pad_end`, `.repeat`, `.char_code_at`. 각각 기존 함수 or 신규.
- 통과 기준: `bench/snapshots/string_method_coverage.hexa` 모든 메서드 통과.

**M5 — self-hosted driver `hexa_driver.hexa`** (결손-A, 결손-F 한꺼번에 해소 / Rust 의존 전면 삭제)
- 서브커맨드: `run | build | fmt | cache | test | self-build | version | help`.
- implicit run: 첫 positional 이 `.hexa` 로 끝나고 존재하는 파일이면 `run` 으로 자동 승격. anima 현장에서 관측한 Mac-CLI 관성 호환.
- content-hash 캐시: `$HOME/.hexa-cache/<sha1(src+deps+compiler_ver)>/exe`.
- 셸에서 `hexa run foo.hexa arg1 arg2` 호출 시 compile → exec 를 execvp 로 이어달리기 (fork 비용 없음).
- 3 플랫폼 동시 빌드 CI (mac arm64 GH runner, ubuntu x86_64 GH runner, ubuntu arm64 GH runner).
- 통과 기준: `/opt/homebrew/bin/hexa` 가 hexa-lang 레포에 들어있는 `build/hexa` 로 대체 가능. Rust 소스 0 줄.

---

## 4. anima 가 지금 당장 필요로 하는 것 (우선순위)

1. **M3 (argv)** — 이번 세션 I12 형태로 또 걸림. 매 AOT 도구마다 skip0 분기 쓰면 안 됨.
2. **M4 (last_index_of 코드젠)** — P12 bridge scaffold 에서 블로킹. runtime 에 함수 이미 있는데 쓸 수 없는 상태는 버그.
3. **M5 (Linux driver)** — 다음 H100 pod 마다 anima 가 bash shim 을 올리고 있음. 다음 pod 부터는 hexa-lang 공식 CLI 쓰고 싶음.
4. **M2 (builtin mangling 완결)** — anima `tool/build_fixup_native.bash` deprecated 처리 이미 했지만 sed fixup 자체를 완전 제거 가능.
5. **M1 (runtime 분할)** — 중장기. self-host 담론의 본질.

---

## 5. 상호 참조

- anima `hexa-lang/373696e7` — runtime.c now/push shim (hxa-004 ext · 2026-04-23)
- anima `hexa-lang/1fdc0100` — Linux x86_64 static musl binary 첫 배포
- anima `55bdad56` — R2 binary 배포 + fetch_hexa_binary_url.bash
- anima `ce55eafa` — pod live bootstrap (6 lang_gap 세부기록)
- anima `state/h100_stage1_launch_state.json:_meta.convergence` — 12 이슈 (11 resolved, P12 PENDING_ARCHITECTURAL)
- hexa-lang inbox `hxa-20260422-004` DONE — exec_capture / now / setenv hx_ prefix mangling
- hexa-lang inbox `hxa-20260423-002` NEW (prio 85, lang_gap) — "Linux x86_64 hexa run driver missing"

---

## 6. 동작하지 않는 해법 (사전 배제)

- "Rust 드라이버를 그냥 Linux 로 크로스컴파일" — 정책 위반 (축-3 목표와 충돌, `.rs` 0줄 요구).
- "runtime.c 를 계속 C 로 둔다" — 축-2 자호스팅 포기. 우리는 runtime 자체도 .hexa 로 가야 함.
- "bash shim 을 계속 anima 가 관리" — 결손-A/F 영구화. 공식 드라이버 필수.
- "python3 를 pod bootstrap 에 포함" — raw#9 위반.

---

## 7. 승인 경로

본 프롬프트 내용을 hexa-lang `.raw` 정책에 반영 (M1–M5 를 raw#XX 로 코드화) 후,
- M3 / M4 부터 개별 PR 로 착수 (최소 블로커 해소, loc 작음).
- M5 Linux driver 는 별도 로드맵 엔트리로 승격 권장.
- M1 은 장기 작업 — 로드맵 parent entry 로 묶고 child 로 분할.

anima 쪽은 M3 / M4 merge 즉시 우리 쪽 workaround (`_last_idx_char`, `skip0` 분기) 제거.
M5 merge 즉시 `tool/hexa_linux_shim.bash` 및 pod bootstrap 의 shim 설치 단계 제거.

---

(끝)
