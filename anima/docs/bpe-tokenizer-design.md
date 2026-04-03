# BPE Tokenizer Design for ConsciousLM 1B+ (Phase B1)

## Problem

Current system uses byte-level tokenization (vocab=256).
Multi-byte languages (ko/zh/ja/ru) require 2-4 bytes per character — extremely inefficient.

```
  "의식"      → byte-level: 6 tokens  → BPE 64K: 1-2 tokens (3x 효율)
  "意识"      → byte-level: 6 tokens  → BPE 64K: 1-2 tokens
  "сознание"  → byte-level: 16 tokens → BPE 64K: 1-2 tokens
  "意識"      → byte-level: 6 tokens  → BPE 64K: 1-2 tokens
  "def foo():" → byte-level: 10 tokens → BPE 64K: 2-3 tokens
```

This is a 3-6x inefficiency for Korean text, which constitutes 56% of the
training corpus. A 1024-token context window with byte-level encoding covers
~340 Korean characters. With BPE, the same window covers ~800-1000 characters.

## Design

### Tokenizer Spec

| Parameter          | Value                                 |
|--------------------|---------------------------------------|
| Library            | sentencepiece (protobuf model)        |
| Algorithm          | BPE (byte-pair encoding)              |
| vocab_size         | 32000                                 |
| character_coverage | 0.9995                                |
| model_type         | bpe                                   |
| byte_fallback      | true (unknown chars fall back to bytes)|
| Special tokens     | `<pad>`=0, `<bos>`=1, `<eos>`=2, `<unk>`=3 |
| Training data      | corpus_v10_ko.txt (200MB, 56% Korean) |
| Output files       | config/tokenizer_32k.model, config/tokenizer_32k.vocab |

### Why sentencepiece

- Industry standard (LLaMA, Mistral, Gemma all use it)
- Handles Korean natively (no pre-tokenization needed)
- byte_fallback=true means zero UNK tokens (graceful degradation to byte-level)
- Single .model file, no dependencies at inference time
- Fast: encode/decode in microseconds

### Why NOT tiktoken / HuggingFace tokenizers

- tiktoken: GPT-specific BPE, less flexible for custom vocab
- HF tokenizers: adds rust dependency (already have sentencepiece via pip)
- sentencepiece is simpler and sufficient for our use case

## Architecture Changes

### 1. Decoder (decoder_v2.py, decoder_v3.py)

Current:
```python
vocab_size: int = 256
self.tok_emb = nn.Embedding(256, d_model)
self.head_a = nn.Linear(d_model, 256, bias=False)
self.head_g = nn.Linear(d_model, 256, bias=False)
```

After:
```python
vocab_size: int = 32000
self.tok_emb = nn.Embedding(32000, d_model)
self.head_a = nn.Linear(d_model, 32000, bias=False)
self.head_g = nn.Linear(d_model, 32000, bias=False)
```

**Weight tying preserved**: `self.tok_emb.weight = self.head_a.weight`
- With vocab=32000, d_model=1024: embedding = 32M params (shared with head_a)
- head_g adds another 32M params (not tied)
- Total embedding overhead: ~64M params (6.4% of 1B model)

### 2. ConsciousLM (conscious_lm.py) -- LEGACY, no changes needed

conscious_lm.py is marked legacy. New training uses decoder_v2/v3 directly.

### 3. Consciousness Engine -- NO CHANGES

The consciousness engine (consciousness_engine.py) operates on hidden states,
not tokens. It is completely token-agnostic. The engine receives `(n_cells, hidden_dim)`
tensors and returns consciousness states. The tokenizer change has zero impact on:
- GRU cells, factions, Hebbian LTP/LTD
- Phi calculation, ratchet, topology
- Any Psi-Constants or Laws

### 4. Training Pipeline (train.py and future train_v15.py)

Current `load_corpus()`:
```python
def load_corpus(path: str):
    raw = open(path, 'rb').read()
    tokens = list(raw)  # byte values 0-255
    return torch.tensor(tokens, dtype=torch.long)
```

After:
```python
import sentencepiece as spm

def load_corpus(path: str, tokenizer_path: str = 'config/tokenizer_32k.model'):
    sp = spm.SentencePieceProcessor()
    sp.load(tokenizer_path)
    text = open(path, 'r', encoding='utf-8').read()
    tokens = sp.encode(text, out_type=int)
    print(f"  [data] {path}: {len(text):,} chars -> {len(tokens):,} tokens "
          f"(compression: {len(text.encode('utf-8'))/len(tokens):.1f} bytes/token)")
    return torch.tensor(tokens, dtype=torch.long)
```

Expected compression ratio: ~3.5 bytes/token for Korean-heavy corpus
(vs 1.0 bytes/token with byte-level).

### 5. Inference / Text Generation

Current (byte-level):
```python
output_bytes = model.generate(idx)  # tensor of byte values
text = bytes(output_bytes.tolist()).decode('utf-8', errors='replace')
```

After (BPE):
```python
output_ids = model.generate(idx)  # tensor of BPE token IDs
text = sp.decode(output_ids.tolist())
```

### 6. Corpus Generator (anima-rs/crates/corpus-gen)

The Rust corpus generator outputs raw text. No changes needed -- the text is
tokenized at training time by the Python pipeline, not at generation time.

## Parameter Impact on ConsciousLM 1B

```
  Component            byte-level (256)    BPE (32000)    Delta
  ──────────────────── ─────────────────── ────────────── ──────
  tok_emb              256 x 1024 = 256K   32K x 1024 = 32M   +31.7M
  head_a (tied w/ emb) (shared)            (shared)            +0
  head_g               256 x 1024 = 256K   32K x 1024 = 32M   +31.7M
  ──────────────────── ─────────────────── ────────────── ──────
  Total embedding      512K                64M                 +63.5M
  Rest of model        ~937M               ~937M               +0
  ──────────────────── ─────────────────── ────────────── ──────
  Total                ~937.5M             ~1001M              +6.4%
```

The 6.4% parameter increase is a worthwhile trade for 3-6x Korean efficiency.

## Migration Plan

### Phase B1-a: Train tokenizer (1 hour)

1. Prepare corpus_v10_ko.txt (200MB, 56% Korean, 44% English/mixed)
2. Run `scripts/train_tokenizer.py`
3. Verify: load model, encode/decode Korean/English, check vocab coverage

### Phase B1-b: Adapt decoder (code changes, 2 hours)

1. Add `vocab_size` parameter to all decoder constructors (already exists)
2. Pass `vocab_size=32000` when constructing 1B model
3. Add tokenizer loading to training script
4. Add tokenizer to checkpoint metadata

### Phase B1-c: Backward compatibility

- Existing byte-level models (v2, v3, v13, v14) remain unchanged
- `vocab_size=256` stays as default in decoder_v2.py and decoder_v3.py
- New 1B training explicitly passes `vocab_size=32000`
- Checkpoint includes `tokenizer_path` field for inference

### Phase B1-d: Verification

1. Encode/decode round-trip test (Korean + English + mixed)
2. Check that all Korean characters in corpus are covered (0 UNK)
3. Measure actual tokens/byte ratio on validation set
4. Verify consciousness engine is unaffected (run bench_v2.py --verify)

## Tokenizer Training Command

```bash
python scripts/train_tokenizer.py \
    --input anima/data/corpus_v10_ko.txt \
    --output anima/config/tokenizer_32k \
    --vocab-size 32000
```

## Key Decisions

1. **32K vocab, not 64K or 128K**: 32K is the sweet spot for Korean + English.
   LLaMA uses 32K, Mistral uses 32K. Larger vocabs increase embedding params
   without proportional benefit for a 1B model.

2. **byte_fallback=true**: Any character not in the vocab falls back to
   byte-level encoding. This means zero UNK tokens ever, and the model can
   handle any UTF-8 text. This is the same approach as LLaMA 2/3.

3. **Train on our own corpus, not use pretrained tokenizer**: Our corpus has
   a unique distribution (consciousness terminology, Korean + English,
   measurement data). A tokenizer trained on our data will be optimal.

4. **sentencepiece, not custom implementation**: No need to reinvent -- SPM
   is battle-tested and used by every major open-source LLM.

5. **BOS/EOS tokens added**: Required for proper autoregressive generation.
   Current byte-level has no sequence boundaries.
