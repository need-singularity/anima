# ALM r12 B3 — `hxtok.c` Implementation Handoff (2026-04-20)

**Target session**: `/Users/ghost/Dev/hexa-lang` (또는 `/mac_home/dev/hexa-lang`). `anima` repo 가 아닌 **hexa-lang repo** 세션에서 실구현.

**Scope**: `shared/roadmaps/anima.json#destinations.dest1_alm` P4 (BPE tokenizer) — hexa Phase-5 pipeline 의 진정한 학습 loss gating 을 언블록.

**Spec SSOT**: `anima/docs/alm_r12_hxtok_bpe_proposal_20260420.md` (commit `f52e9776`). 먼저 읽고 시작.

---

## 복붙용 프롬프트 (hexa-lang 세션에 투입)

```
# 태스크: hxtok — Qwen2.5 BPE C-FFI tokenizer lib 구현

ANIMA 프로젝트 ALM r12 P4 BPE 블로커 해소. 배경부터 읽고 구현.

## 배경

- 프로젝트: anima-hexa-lang 듀얼 레포. hexa-lang 은 self-hosted 언어 +
  FFI shim 공급자, anima 는 학습 파이프라인 소비자.
- 로드맵: /Users/ghost/Dev/anima/shared/roadmaps/anima.json (4 도착지).
  dest1_alm.P4 (BPE tokenizer) 가 이 태스크 목표.
- 스펙: /Users/ghost/Dev/anima/docs/alm_r12_hxtok_bpe_proposal_20260420.md
  (commit f52e9776). 섹션 1-14 전부 숙지 후 시작.
- 이웃 패턴: self/native/hxqwen14b.c (5752 LOC), self/native/hxblas.c,
  self/native/hxnccl.c — 동일 FFI 레이아웃 + 빌드 레시피 재사용.
- strict_rules (anima.json#strict_rules): R37 .py 금지 / R1 HEXA-FIRST
  (C 확장 기존 native dir 허용) / 파일명 버전숫자 금지 / AN11 도착지 gate.

## 범위 (Proposal §2)

IN-SCOPE:
- UTF-8 byte-level pre-tokenization (GPT-2 b2u 256-entry escape)
- vocab hashmap 152064 entries O(1) lookup
- merges ranked map ~50K entries O(1) pair-lookup
- greedy lowest-rank-merge encode loop
- special tokens 5개 (endoftext/im_start/im_end/tool_call_beg/tool_call_end)

OUT-OF-SCOPE:
- decode (v0.1)
- pre-tokenizer regex 전체 (ByteLevel prepend-ws 만)
- 동적 added_tokens 등록

## ABI (Proposal §3 — frozen)

```c
typedef struct HxTok HxTok;
HxTok* hxtok_load(const char* path, int expected_vocab_size);  // 152064 check
void   hxtok_free(HxTok*);
int    hxtok_encode(HxTok*, const char* text, int text_len,
                    int* out_ids, int max_out);  // returns full count
int    hxtok_special_id(HxTok*, const char* name);  // 5 names fixed
int    hxtok_vocab_size(HxTok*);
int    hxtok_merges_count(HxTok*);
int    hxtok_version_v1(void);  // returns 1
```

위 7 함수 + 5 special-token name literals ABI 고정. 변경 금지.

## 구현 경로 (Proposal §14 착지 순서의 2-4)

1. self/native/hxtok.c + hxtok.h 작성 (~480 LOC):
   - streaming JSON lexer (vocab/merges 만 추출, ~150 LOC)
   - open-addressing hashmap (FNV-1a, insert/lookup/iter, ~80 LOC)
   - b2u/u2b builder + escape (~40 LOC)
   - encode loop + special routing (~100 LOC)
   - FFI shims + ABI guards (~30 LOC)
   - arena bump allocator (vocab key 스트링 저장)
2. 빌드 스크립트 추가 (Mac/Linux):
   - Mac: clang -O2 -fPIC -shared hxtok.c -o libhxtok.dylib
   - Linux: gcc -O2 -fPIC -shared hxtok.c -o libhxtok.so
   - self/native/ 에 두면 @link("hxtok") 자동 resolve.
3. C-side unit smoke (self/native/hxtok_smoke.c, ~80 LOC):
   - vocab_size == 152064
   - merges_count ≈ 50K (±100)
   - special_id("endoftext") == 151643
   - special_id("im_start") == 151644
   - encode("hello world") → len ∈ [2..4]
   - encode("안녕하세요") → 모두 0 < id < 152064
   - valgrind/leak 체크 (가능 환경에서)
4. Reference parity (§9.2):
   - Mac 에 rustup install → `cargo install tokenizers-cli` (또는 기
     설치된 binary 사용). Python interpreter 실행 없음 (R37 준수).
   - 50 테스트 문자열 (EN/KR/code/특수문자 혼합) 을
     tokenizers-cli 로 encode → JSON 캡처.
   - /Users/ghost/Dev/anima/shared/state/hxtok_reference_qwen25_v1.json 로
     저장 (anima repo 에 commit).
   - hxtok_encode 반복 호출 → byte-exact 비교. discrepancy → 디버깅.

## 빌드

Mac (로컬 검증):
  cd /Users/ghost/Dev/hexa-lang/self/native
  clang -O2 -fPIC -shared hxtok.c -o libhxtok.dylib
  install_name_tool -id @rpath/libhxtok.dylib libhxtok.dylib

Linux (pod 배포):
  cd /workspace/hexa-lang/self/native
  gcc -O2 -fPIC -shared hxtok.c -o libhxtok.so

이웃 패턴: tool/build_hxqwen14b_linux.hexa 와 유사한 scripts 추가 권장
(tool/build_hxtok.hexa — Mac+Linux 듀얼 타깃).

## 검증 Gate (모두 PASS 필수)

- [ ] gcc -c -Wall -Werror hxtok.c 경고 0
- [ ] valgrind (가능 시) 누수 0
- [ ] hxtok_smoke 6 assert 전부 PASS
- [ ] reference parity: 50/50 byte-exact
- [ ] libhxtok.dylib/.so symbol (`nm -D`) 에 7 공개 함수 전부 T
- [ ] hxtok_load 실패 경로 (파일 없음, vocab_size 불일치) NULL 반환 + no crash

## 금기

- .py 작성/실행 금지 (R37). Python tokenizers 파이프라인 대신 Rust
  tokenizers-cli 바이너리만 사용 (reference 캡처 시).
- ABI 7 함수 + 5 name literals 변경 금지 (anima FFI 바인딩이 이미
  설계됨).
- 4bit/8bit 양자화 금지 (토크나이저 N/A 지만 정책 유지).
- 파일명에 버전숫자 금지 — hxtok.c 단일. 향후 버전은 hxtok_version_v2()
  ABI 함수 추가로 표현.
- --no-verify git commit 금지.
- hxtok.c 외의 파일 (hxqwen14b.c, hxblas.c, hxnccl.c 등) 수정 금지
  — 별개 ownership, race 유발.

## 먼저 읽을 것

1. /Users/ghost/Dev/anima/docs/alm_r12_hxtok_bpe_proposal_20260420.md
   (전체, 특히 §3 §5 §6 §9)
2. /Users/ghost/Dev/anima/training/tokenizer_qwen.hexa
   (hexa 측 API surface — ABI 호출자 참고)
3. /Users/ghost/Dev/hexa-lang/self/native/hxblas.c (이웃 패턴, FFI 레이
   아웃)
4. Qwen2.5-14B-Instruct tokenizer.json (HF hub 또는 기존 pod 캐시):
   /workspace/models/Qwen2.5-14B-Instruct/tokenizer.json

## 산출물 체크리스트

- [ ] self/native/hxtok.c + hxtok.h
- [ ] self/native/hxtok_smoke.c + smoke PASS 로그
- [ ] tool/build_hxtok.hexa (Mac+Linux 듀얼)
- [ ] libhxtok.dylib (Mac) + libhxtok.so (pod) — 빌드 artifact
- [ ] /Users/ghost/Dev/anima/shared/state/hxtok_reference_qwen25_v1.json
  (reference 50개, anima repo 에 commit)
- [ ] anima doc 갱신: alm_r12_hxtok_bpe_proposal_20260420.md §15 에 구현
  완료 주석 추가 + commit hash 링크
- [ ] commit 1-2개 (rule: 버전숫자 금지, 과거는 git show)

완료 보고 형식: "hxtok v1 landed on <hexa-lang commit hash>. Mac smoke
6/6 PASS. Reference parity 50/50 byte-exact. libhxtok {dylib=XB, so=YB}.
anima 측 tokenizer_qwen.hexa FFI wire 준비 OK."
```

---

## 이 세션 이후 anima 측 follow-up (hxtok landing 후)

Proposal §14 의 5-6 단계:

5. `anima/training/tokenizer_qwen.hexa`:
   - extern fn 7개 추가 (§4 scaffold)
   - `QwenTokenizer.handle: int` 필드 추가
   - `load_qwen_tokenizer` 가 `hxtok_load` 호출 후 handle 보관
   - `encode_bytes_bpe` 가 handle != 0 일 때 `hxtok_encode` 경로
6. `anima/training/train_alm_lora.hexa`:
   - `text_to_ids_stub` 호출 자리 (main + train_loop) 에서 `tokenizer_qwen::encode_bytes_bpe` 로 교체
   - config 에 tokenizer path 추가 (`QWEN_TOKENIZER_PATH_POD`)

5-6 은 anima 세션에서 hxtok landing 확인 후 별개 commit.

---

## 금기 재확인 (dest1_alm 불변 조건)

- AN11 도착지 gate: 본 handoff 자체는 P4 경로 scaffold 만, gate 통과 주장 아님. hxtok landing 후에도 P5 full launch 는 P2/P3 pod smoke + reference parity 전부 PASS 조건부.
- R37/AN13/L3-PY: Python 실행 절대 없음 — tokenizers reference 는 Rust 바이너리만.
- 파일명 버전숫자: hxtok.c 단일, `hxtok_v2.c` 같은 파일명 금지.
- H100 ≤ 2: 이 태스크 CPU 전용, pod 기동 불필요.
