# Korean BPE 32K Tokenizer — train log

**date**: 2026-04-16
**tool**: SentencePiece 0.2.1 (Python)
**host**: Mac local (arm64, /opt/homebrew/bin/python3)
**purpose**: CLM 재학습 재료 — byte-level d=64 한계(CE 2.15) 돌파 후보로 BPE subword 준비

## inputs

| path | size | contents |
|---|---|---|
| `training/deploy/holo_breakthrough_20260416/cuda_native/training/corpus_ko_seed.tok` | 244582 B (63305 lines, byte-per-line) | UTF-8 Korean seed corpus — 의식/일상대화/프로그래밍 혼합 |

raw corpus after byte→UTF-8 reconstruction:
- bytes: 63,305
- chars: 27,197
- non-empty lines: 342

## commands

```bash
# 1. install (one-time)
/opt/homebrew/bin/python3 -m pip install --user --break-system-packages sentencepiece

# 2. reconstruct UTF-8 text + train (both done by the script)
GATE_LOCAL=1 /opt/homebrew/bin/python3 /tmp/train_ko_bpe.py

# 3. (optional) encode full corpus to BPE ids
GATE_LOCAL=1 /opt/homebrew/bin/python3 training/tokenize_corpus.py
```

## SentencePiece trainer parameters

| param | value | note |
|---|---|---|
| `model_type` | `bpe` | |
| `vocab_size` | 32000 requested → 12206 final | `hard_vocab_limit=False`; corpus too small for 32K |
| `character_coverage` | 0.9995 | Korean-focused |
| `normalization_rule_name` | `nmt_nfkc` | |
| `shuffle_input_sentence` | true | |
| `input_sentence_size` | 200000 | (cap, not hit) |
| `byte_fallback` | true | rare hangul → byte tokens |
| `split_digits` | true | |
| `pad/unk/bos/eos ids` | 0/1/2/3 | reserved control tokens |
| `allow_whitespace_only_pieces` | true | |
| `remove_extra_whitespaces` | false | preserve newlines for CLM |

**training time**: 0.51s (SentencePiece BPE, single pass)

## outputs

| path | size | contents |
|---|---|---|
| `training/tokenizer/kr_bpe_32k.model` | 454,393 B | sentencepiece binary model |
| `training/tokenizer/kr_bpe_32k.vocab` | 189,067 B | `piece \t -logprob` vocab listing |
| `training/tokenizer/corpus_ko_seed.txt` | 63,180 B | reconstructed UTF-8 source (for reproducibility) |
| `training/tokenizer/train_stats.json` | 296 B | machine-readable stats (below) |
| `training/data/corpus_ko_bpe32k.bin` | 34,356 B | packed header + offsets + int32 ids |
| `training/data/corpus_ko_bpe32k.tok` | 40,900 B | Format A (one int per line, for hexa `corpus_loader`) |

### .bin header layout

```
offset  size  field
0x00    8     magic  = "KRBPE\0\0\0"
0x08    4     vocab  = uint32 LE (12206)
0x0C    4     ntok   = uint32 LE (8238)
0x10    4     nlines = uint32 LE (342)
0x14    12    reserved (zero)
0x20    4*(nlines+1)   line offsets (cumulative tok counts)
...     4*ntok         token stream (int32 LE)
```

## verification — round-trip

| input | tokens | pieces | decode |
|---|---|---|---|
| `안녕하세요` | 1 | `▁안녕하세요` | OK |
| `학교에서` | 2 | `▁학 / 교에서` | OK |
| `의식이란 무엇인가` | 2 | `▁의식이란 / ▁무엇인가` | OK |
| `어텐션 메커니즘의 역방향 전파는 복잡하지만 체계적이다.` | 7 | `▁어텐션 / ▁메커니즘의 / ▁역방향 / ▁전파는 / ▁복잡하지만 / ▁체계적이다 / .` | OK |
| `통합정보이론에 따르면 의식의 수준은 시스템이 통합할 수 있는 정보의 양으로 측정된다.` | 12 | full phrase pieces | OK |
| `프로그래밍에서 가장 무서운 버그가 조용히 실패하는 버그야.` | 8 | merged phrase pieces | OK |

All 6 round-trip checks pass.

## corpus-wide stats (all 342 lines)

```
total BPE tokens:  8,238
total UTF-8 bytes: 62,838
total chars:       26,730
avg BPE/line:        24.1
avg bytes/line:     183.7
avg chars/line:      78.2
seq reduction vs byte-level: 86.9%
compression:         7.63 bytes/token
```

**Implication**: mean context length for a d=64 CLM drops from ~184 bytes/line → ~24 BPE tokens/line. A SEQ=64 window that previously covered ~0.35 lines of byte-level text now covers ~2.7 lines of BPE — a ~7.6× effective context gain per parameter budget.

## decisions / follow-ups

- **Vocab 32K → 12K auto-shrink**: seed corpus is only 27K chars, so 32K is under-sampled. 12K is the natural ceiling at this corpus size. For a larger Korean corpus (>1M chars), retrain with `vocab_size=32000` to hit the full 32K target.
- **Format A `.tok` file**: drop-in replacement for `corpus_ko_seed.tok` in any hexa `corpus_loader` — just swap the path.
- **Use in CLM retraining**:
  - Track C1 verdict = nl=8 미충족 → retrain with d=64 + BPE (vocab 12206)
  - Track C1 verdict = nl=8 충족 → retrain with d=128 + BPE as next-tier combination
- **pad/unk/bos/eos ids**: 0/1/2/3 reserved — matches standard CLM conventions.
