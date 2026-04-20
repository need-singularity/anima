# ALM r12 B3 — `hxtok` C-FFI BPE tokenizer proposal (2026-04-20)

**Scope**: Qwen2.5 BPE encoder (152064 vocab, ~50K merges) — Phase-2/3/4 landing 경로 설계. interpreter O(n²) perf wall 우회 + hexa-first 유지.

**SSOT refs**:
- `shared/roadmaps/anima.json#destinations.dest1_alm` (P1 blocker)
- `shared/state/alm_r12_launch_20260420.json#r12_remaining_blockers_concrete_next_actions[B3_qwen_bpe_tokenizer]`
- `shared/state/tokenizer_qwen_progress_20260420.json#interpreter_perf_note.recommended` — option **(c)** 200-400 LOC C lib 채택
- `training/tokenizer_qwen.hexa` (367 LOC, Phase-1 skeleton)

---

## 1. Motivation

Phase-1 skeleton 의 `find_matching_close` + `byte_at(s,i)` 를 7MB `tokenizer.json` 에 풀 적용 시 stage0 interpreter 에서 2min+ 타임아웃 발생 (per-byte substring 이 O(n) → 전체 O(n²) ≈ 49T ops). 설령 compiled-hexa 로 우회해도 hexa 언어의 string-index quirks (byte vs char index 비일관) 로 멀티바이트 (UTF-8 한국어 조각) 경계 버그 리스크 남음.

따라서 tokenizer **parse + encode 핫패스** 만 C 로 구현, hexa 는 handle+FFI 로 호출. 300-400 LOC 한 번의 C 작성으로:

- interpreter perf wall 완전 회피
- hexa string quirk (feedback_hexa_string_api.md) 비의존
- 기존 hxblas/hxnccl/hxqwen14b ecosystem 과 동일 배치 (ABI/빌드/링크 패턴 재사용)

## 2. In-scope / out-of-scope

| 항목 | 범위 |
|---|---|
| ✅ in | UTF-8 byte-level pre-tokenization (GPT-2 b2u 256-entry escape) |
| ✅ in | vocab hashmap (152064 entries) O(1) lookup |
| ✅ in | merges ranked map (~50K entries) O(1) pair-lookup |
| ✅ in | greedy lowest-rank-merge encode loop |
| ✅ in | special tokens 5개 ABI (endoftext, im_start, im_end, tool_call_beg/end) |
| ❌ out | decode (v0.1 — 학습 시 encode-only) |
| ❌ out | pre-tokenizer regex 전체 (학습 코퍼스는 byte-level 직접 fall-back 허용 — Qwen2.5 tokenizer.json pre_tokenizer pattern 은 `ByteLevel` prepended whitespace 처리 1개 rule 뿐) |
| ❌ out | added_tokens 동적 등록 (5 special + base vocab 만) |

## 3. C library surface — `hxtok.c` / `hxtok.h`

```c
// Opaque handle. Internal: struct holding vocab htable, merges htable,
// b2u[256], u2b[320], special ids, arena allocator.
typedef struct HxTok HxTok;

// Load tokenizer.json from path. On success returns non-NULL handle.
// On parse/alloc failure returns NULL; caller MUST check.
//   expected_vocab_size = 152064 for Qwen2.5 (other sizes rejected to
//   catch mis-linked tokenizer.json early)
HxTok* hxtok_load(const char* path, int expected_vocab_size);

// Free handle + all owned memory (htables, arena, b2u tables).
// Idempotent on NULL.
void hxtok_free(HxTok* h);

// Encode UTF-8 text to token ids. Writes up to max_out ids into out_ids
// and returns the count; if count > max_out, callers should re-call
// with a larger buffer (count is the true full-encode length).
//   text = UTF-8 bytes (NOT pre-escaped; internal b2u handles)
//   text_len = byte length of text (may contain embedded NULs if needed)
int hxtok_encode(HxTok* h, const char* text, int text_len,
                 int* out_ids, int max_out);

// Special-token id lookup by symbolic name (one of the 5 listed above).
// Returns -1 if name is unrecognised.
int hxtok_special_id(HxTok* h, const char* name);

// Minimal introspection for sanity-check at trainer startup.
int hxtok_vocab_size(HxTok* h);
int hxtok_merges_count(HxTok* h);

// Version probe for ABI gating (mirrors hxqwen14b_version_v56X pattern).
int hxtok_version_v1(void);  // returns 1
```

**ABI stability**: 위 7 함수 + 5 special-token name literals ("endoftext" / "im_start" / "im_end" / "tool_call_beg" / "tool_call_end") 가 frozen surface. 내부 htable/arena 레이아웃은 자유.

## 4. hexa FFI extern scaffold — `training/tokenizer_qwen.hexa` 추가분

현재 `encode_bytes_bpe` 이 `loaded=0 → []` 로 fall-through 하는 자리에 FFI 분기 추가:

```hexa
// Phase-2 FFI — landed 시 load_qwen_tokenizer 가 handle 을 반환하도록 전환.
@link("hxtok")
extern fn hxtok_load(path: string, expected_vocab_size: int) -> int   // handle (0 = fail)

@link("hxtok")
extern fn hxtok_free(h: int) -> int

@link("hxtok")
extern fn hxtok_encode(h: int, text: string, text_len: int,
                       out_ids_p: int, max_out: int) -> int

@link("hxtok")
extern fn hxtok_special_id(h: int, name: string) -> int

@link("hxtok")
extern fn hxtok_vocab_size(h: int) -> int

@link("hxtok")
extern fn hxtok_merges_count(h: int) -> int

@link("hxtok")
extern fn hxtok_version_v1() -> int
```

`QwenTokenizer` struct 에 `handle: int` 필드 추가 (loaded=1 일 때 set). `encode_bytes_bpe` 는 handle != 0 이면 host int64 buffer 를 `alloc_raw(max_out * 8)` 해서 `hxtok_encode` 호출 → `peek_i64_at` 루프로 hexa array<int> 반환.

## 5. Data structures (C side)

### 5.1 vocab hashmap
- key: escaped-UTF-8 string (post-b2u), typical length 1-16 bytes
- value: int32 id
- 구현: open-addressing + linear probing, capacity = 2× vocab_size rounded up to power-of-2 (=524288 slots). FNV-1a hash.
- 메모리: 524288 × 16B slot ≈ 8MB + key arena ~2-3MB = ~11MB peak. 충분.

### 5.2 merges ranked map
- key: (tok_a_id, tok_b_id) packed to uint64
- value: int32 rank (== merges list index, 0-based)
- 구현: open-addressing, capacity = 2× merges_count (=131072 slots). Packed key 로 hash.
- `rank==0` = highest priority merge (BPE greedy lowest-rank-first).

### 5.3 b2u / u2b
- b2u[256] = int (codepoint). build once at load.
- u2b: hashmap codepoint→byte (320 slots fixed).

### 5.4 arena
- single bump allocator for all vocab key strings. 평균 8B × 152064 ≈ 1.2MB.
- tokenizer.json 파싱 중 임시 str 은 stack + 작은 buffer.

## 6. Algorithm — byte-level BPE encode

```
encode(text, text_len):
    // 1. UTF-8 → escape via b2u
    escaped = []
    for byte in text[0..text_len]:
        escaped.push_codepoint(b2u[byte])   // 1-2 UTF-8 bytes per cp

    // 2. split escaped into initial tokens — each cp is its own token
    //    initially. Use vocab lookup for single-cp ids (guaranteed present).
    toks = [vocab_lookup(cp) for cp in escaped]

    // 3. greedy lowest-rank merge loop
    while len(toks) > 1:
        best_rank = INF; best_i = -1
        for i in 0..len(toks)-1:
            r = merges_lookup(toks[i], toks[i+1])
            if r < best_rank: best_rank = r; best_i = i
        if best_i < 0: break   // no more merges
        merged_id = vocab_lookup(concat_str(toks[best_i], toks[best_i+1]))
        toks = toks[:best_i] + [merged_id] + toks[best_i+2:]

    return toks
```

특징:
- 평균 text length 수십~수백 bytes → 평균 merge loop ≤100 iterations, 각 iter O(len) scan. 실사용 감당.
- 최악의 경우(문서급 1k bytes): ~1ms/call scale. 충분.

## 7. tokenizer.json schema — 실제로 읽어야 하는 부분

```
{
  "added_tokens": [{id, content, special, ...}, ...],   // 151643~151664
  "pre_tokenizer": { "type": "ByteLevel", "add_prefix_space": false, ... },
  "decoder":       { "type": "ByteLevel", ... },
  "post_processor": ...,
  "model": {
    "type": "BPE",
    "vocab": { "<key>": <id>, ... },                    // 152064 entries
    "merges": [ "Ġh el", "Ġh e l l o", ... ]            // ~50K entries
  }
}
```

파서는 streaming: top-level `{...}` 를 rec-descent 로 훑고 `model.vocab` / `model.merges` / `added_tokens` 만 populate. 나머지는 skip. 예상 parse 시간 C 에서 <100ms (7MB fread + simple lex).

JSON 라이브러리는 쓰지 않음 — 의존성 제로. `{` `}` `[` `]` `"` `\` `:` `,` 처리 + UTF-8 validated string copy 로 충분. ~150 LOC.

## 8. Build + link

`hexa-lang/self/native/hxtok.c` (단일 파일) + `hxtok.h` (공개 surface).

### Mac 빌드
```
clang -O2 -fPIC -shared hxtok.c -o libhxtok.dylib
install_name_tool -id @rpath/libhxtok.dylib libhxtok.dylib
cp libhxtok.dylib /usr/local/lib/     # 또는 hexa-lang/self/native/
```

### Linux (pod) 빌드
```
gcc -O2 -fPIC -shared hxtok.c -o libhxtok.so
cp libhxtok.so /workspace/hexa-lang/self/native/
```

`@link("hxtok")` pragma → hexa runtime 이 `libhxtok.so` / `libhxtok.dylib` resolve.

## 9. Verification (smoke)

### 9.1 C-side unit smoke — `hxtok_smoke.c` (~80 LOC)
- load tokenizer.json
- assert vocab_size == 152064, merges_count ≈ 50K (±100)
- assert special_id("endoftext") == 151643, special_id("im_start") == 151644
- encode("hello world") → assert len in [2..4] ids
- encode("안녕하세요") → assert all ids < 152064 and > 0
- free → memtrace no leaks

### 9.2 Reference parity — `hxtok_vs_reference.json`
- Once: capture Qwen tokenizer ground truth for 50 test strings (mix EN/KR/code/특수) via 외부 host 에 설치된 HuggingFace `tokenizers` CLI (AN13 준수 — Python 금지지만 rustup-installed `tokenizers` binary 는 허용되는 우회 경로). 결과를 JSON 으로 캡처해 `shared/state/hxtok_reference_qwen25_v1.json` 로 재고정.
- hxtok_encode 반복 호출 → byte-exact id 비교. discrepancy → 알고리즘 디버깅.

### 9.3 hexa-side E2E — `tokenizer_qwen.hexa` smoke
- `load_qwen_tokenizer(QWEN_TOKENIZER_PATH_MAC)` → `loaded=1, handle != 0`
- `encode_bytes_bpe(t, "hello world")` → array<int> len>0
- `encode_bytes_bpe(t, "안녕")` → array<int> len>0
- `t.vocab_size == 152064`

## 10. Integration into `train_alm_lora.hexa`

현재 `text_to_ids_stub` 이 `vocab=16 → log(16)≈2.77 flat loss` 를 유발. Phase-3 에서:

1. `main()` 진입 시 `tokenizer_qwen::load_qwen_tokenizer(path)` 호출. `loaded=0` 이면 fatal (stub fallback 제거).
2. `train_loop` 의 per-step 코퍼스 배치 샘플링 → `encode_bytes_bpe(tokenizer, text)` → `ids`.
3. `ids_dev` 호스트→디바이스 복사 후 cache_fwd 호출.

변경 범위: train_alm_lora.hexa 약 30-50 LOC (text_to_ids_stub 호출 2곳 + config 에 tokenizer path 1 entry).

## 11. LOC + ETA 견적

| 영역 | LOC (C) | ETA |
|---|---|---|
| JSON streaming lexer + parser (vocab+merges) | 150 | 2h |
| Open-addressing hashmap (insert/lookup/iter) | 80 | 1h |
| b2u / u2b builder + escape | 40 | 0.5h |
| encode loop + special token routing | 100 | 2h |
| FFI shims + ABI guards | 30 | 0.5h |
| Build scripts (Mac+Linux) | — | 0.5h |
| Unit smoke + reference parity | 80 | 2h |
| **합계** | **~480 LOC** | **~8.5h** |

Phase-3 (trainer integration) 별도 0.5-1h.

기존 SSOT ETA (14-24h, multi-day) 보다 낙관적 — 이유는 JSON parser 를 full rec-descent 가 아닌 "vocab/merges 만 뽑는 streaming scanner" 로 축소했기 때문 (§7). 보수 버퍼 포함 **honest ETA 10-14h**.

## 12. Alternatives considered

| 옵션 | Pros | Cons | 판정 |
|---|---|---|---|
| (a) `read_file_bytes` + array-index O(1) per byte, pure hexa | deps 0, .hexa 유지 | hexa intrinsic 존재 확인 필요, merge loop 여전히 interpreter 속도 | 🟨 Phase-1 재시도 감 — B3 ETA 단축 여부 불확실 |
| (b) `hexa_cc` compile tokenizer_qwen.hexa to C, native exec | .hexa 단일, interpreter 우회 | compile path 성숙도 미검증 (dual-pass quirks), debug 어려움 | ❌ 비용↑ 이득↑ 스왑 |
| **(c) `hxtok` C lib + hexa FFI (본 문서)** | **ecosystem 동형 (hxblas/hxnccl/hxqwen14b pattern), perf 보장, hexa string quirk 비의존, 재사용성 (decode/다른 모델 확장 여지)** | **C 파일 1개 추가 (R1 HEXA-FIRST 예외 인정, C-extension allowed for perf-critical)** | ✅ **채택** |
| (d) RunPod 에 HF tokenizers crate FFI | 업계 표준, 검증된 파서 | 외부 deps (rust-to-C bridge 무거움, R2 size ↑, macOS cross-build 복잡) | ❌ 의존성 폭증 |

## 13. Policy compliance

- **R1 HEXA-FIRST**: C 확장 — hexa-lang/self/native/*.c 패턴 (기존 hxqwen14b.c, hxblas.c, hxnccl.c 과 동형) 으로 허용 범위 내. block-forbidden-ext.sh 훅 대상 아님 (.c 기존 네이티브 FFI 디렉터리).
- **R37/AN13/L3-PY**: Python 불사용 (reference 캡처 시 `tokenizers` binary 바이너리만, Python interpreter 실행 없음).
- **No quantization**: 토크나이저는 수치 정밀도 무관.
- **feedback_one_shot_best**: launch 전 reference parity PASS 요구.
- **feedback_hexa_string_api / hexa_struct_list_alias**: C 쪽에서 전부 처리하므로 영향 없음.

## 14. 착지 순서

1. **이 문서 commit** (B3 proposal 고정)
2. `hexa-lang/self/native/hxtok.c` + `hxtok.h` 작성 (별개 세션 — hexa-lang repo)
3. `hexa-lang` 빌드 레시피 추가 (Mac+Linux)
4. Mac 로컬 C-side smoke PASS → reference parity JSON 캡처 → reference parity PASS
5. anima 측 `tokenizer_qwen.hexa` FFI extern 추가 + `load_qwen_tokenizer` Phase-2 전환 (handle set) — 본 anima 세션 범위
6. anima 측 `train_alm_lora.hexa` Phase-3 wiring (text_to_ids_stub 제거) — 본 anima 세션 범위
7. pod libhxtok.so 배포 + 1-step smoke (loss != log(16))
8. 100-step smoke
9. full r12 launch

1 은 이 문서. 2-4 는 hexa-lang 세션. 5-6 은 anima 세션에서 hxtok.so 존재 가정 하에 scaffold 가능 (extern decl 은 link 시점 해소되므로 미존재 상태로도 parse/compile 은 성공).

## 15. 이 세션 산출물

- `docs/alm_r12_hxtok_bpe_proposal_20260420.md` (이 파일)

다음 turn 이나 사용자 판단으로 5-6 scaffolding 착수 결정.
