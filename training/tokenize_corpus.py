#!/usr/bin/env python3
"""Encode Korean seed corpus with kr_bpe tokenizer.

Reads:  training/tokenizer/corpus_ko_seed.txt   (reconstructed UTF-8 text, one sentence/line)
Writes: training/data/corpus_ko_bpe32k.bin      (packed int32 little-endian, prefixed by header)
        training/data/corpus_ko_bpe32k.tok      (one int per line, for hexa corpus_loader format A)

Header for .bin (32 bytes):
  magic   "KRBPE\0\0\0"                  (8 bytes)
  vocab   uint32 little-endian           (4 bytes)
  ntok    uint32 little-endian           (4 bytes)
  nlines  uint32 little-endian           (4 bytes)
  reserved (12 bytes, zero)

Layout after header:
  line offsets table : uint32 * (nlines+1)   (cumulative token counts)
  token stream       : int32  * ntok
"""
import os
import struct
import sys
import time

import sentencepiece as spm

ANIMA = "/Users/ghost/Dev/anima"
MODEL = f"{ANIMA}/training/tokenizer/kr_bpe_32k.model"
SRC = f"{ANIMA}/training/tokenizer/corpus_ko_seed.txt"
OUT_DIR = f"{ANIMA}/training/data"
OUT_BIN = f"{OUT_DIR}/corpus_ko_bpe32k.bin"
OUT_TOK = f"{OUT_DIR}/corpus_ko_bpe32k.tok"

os.makedirs(OUT_DIR, exist_ok=True)

print(f"[1/3] load model {MODEL}")
sp = spm.SentencePieceProcessor()
sp.load(MODEL)
vocab = sp.get_piece_size()
print(f"  vocab_size = {vocab}")

print(f"[2/3] encode {SRC}")
t0 = time.time()
with open(SRC, "r", encoding="utf-8") as f:
    lines = [ln.rstrip("\n") for ln in f if ln.strip()]
all_ids = []
offsets = [0]
for ln in lines:
    ids = sp.encode(ln, out_type=int)
    all_ids.extend(ids)
    offsets.append(len(all_ids))
print(f"  lines  = {len(lines)}")
print(f"  tokens = {len(all_ids)}")
print(f"  [{time.time()-t0:.2f}s]")

print(f"[3/3] write {OUT_BIN} + {OUT_TOK}")
with open(OUT_BIN, "wb") as f:
    # header
    f.write(b"KRBPE\0\0\0")
    f.write(struct.pack("<III", vocab, len(all_ids), len(lines)))
    f.write(b"\0" * 12)
    # offsets table
    f.write(struct.pack(f"<{len(offsets)}I", *offsets))
    # tokens
    f.write(struct.pack(f"<{len(all_ids)}i", *all_ids))

# hexa corpus_loader Format A (one int per line)
with open(OUT_TOK, "w", encoding="utf-8") as f:
    for tid in all_ids:
        f.write(f"{tid}\n")

bin_sz = os.path.getsize(OUT_BIN)
tok_sz = os.path.getsize(OUT_TOK)
print(f"  {OUT_BIN}  {bin_sz:>8,} bytes")
print(f"  {OUT_TOK}  {tok_sz:>8,} bytes")

# quick sanity: decode back first 3 lines from the packed bin
print("\n  sanity (re-read + decode first 3 lines):")
with open(OUT_BIN, "rb") as f:
    magic = f.read(8)
    assert magic == b"KRBPE\0\0\0", magic
    v, nt, nl = struct.unpack("<III", f.read(12))
    _ = f.read(12)
    offs = struct.unpack(f"<{nl+1}I", f.read(4 * (nl + 1)))
    toks = struct.unpack(f"<{nt}i", f.read(4 * nt))
for i in range(3):
    seg = toks[offs[i]:offs[i+1]]
    print(f"    line {i}: {len(seg)} tokens -> {sp.decode(list(seg))[:80]!r}")
print("[done]")
