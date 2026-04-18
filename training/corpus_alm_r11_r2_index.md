# ALM r11 Corpus R2 Index

Generated: 2026-04-18 (asia/seoul)
Pipeline: local jsonl → ubu2 farm (jq+awk+shuf) → Mac pull → R2 upload
Toolchain: jq-1.7, awk, shuf (no `.py`)

## Source

- Original: `/Users/ghost/Dev/anima/training/corpus_alm_70b.jsonl` (93,400,043 B / 93.4 MB)
  - Format: `{role, messages:[{role,content}...], source}` ChatML jsonl
  - Extraction: `jq -r '.messages[]?.content // empty' | awk NF>0 | tr -s whitespace | fold -s -w 800`
- Kowiki source: `/Users/ghost/Dev/anima/training/corpus_auto/kowiki.jsonl` (1.37 GB)
  - First 100 MB of jsonl, `.text` field, same stripping pipeline → 15 MB slice → trimmed to 15% target

## R2 Bucket: `r2:anima-corpus/alm/`

| File | Size (B) | Size (MB) | SHA256 | Branches |
|------|---------:|----------:|--------|----------|
| `corpus_alm_70b_stripped.txt` | 81,131,472 | 77.37 | `b2c9170bb31446eb922474fc37b38b0c5b2d976ec40fdc2a62be1750472a0cb3` | A (32B), C (14B seed-sweep) |
| `corpus_alm_70b_stripped_kowiki15.txt` | 93,301,193 | 88.98 | `04395bf3dd2bdd979c700b505f07974919f6c4bc1ac1ad464186a599813cde8e` | B (14B cont.) |

## Admix composition (branch B)

- Stripped corpus:   81,131,472 B (86.96%)
- Kowiki admix:      12,169,720 B (13.04%  of total,  ≈ 15.00% of stripped base)
- Total merged:      93,301,193 B (117,294 lines, shuf randomized)

Note: 15% spec interpreted as "kowiki = 0.15 × stripped" (kowiki/stripped = 15%).  
Alternate interpretation (kowiki = 0.15 × total) would require ~14.3 MB kowiki.

## Pull recipe (pod side)

```
rclone copy r2:anima-corpus/alm/corpus_alm_70b_stripped.txt /workspace/data/
rclone copy r2:anima-corpus/alm/corpus_alm_70b_stripped_kowiki15.txt /workspace/data/
sha256sum /workspace/data/corpus_alm_70b_stripped*.txt  # verify against table above
```

## Local artifacts (Mac)

- `/Users/ghost/Dev/anima/training/corpus_alm_70b_stripped.txt`
- `/Users/ghost/Dev/anima/training/corpus_alm_70b_stripped_kowiki15.txt`
- original `/Users/ghost/Dev/anima/training/corpus_alm_70b.jsonl` **unchanged**

## Token estimate

stripped ~81 MB → ≈ 41.8 M tokens (design spec match: §4 target)  
admix ~93 MB → ≈ 48.0 M tokens (design B cont. budget)

## Compliance

- R37/AN13/L3-PY: zero `.py` anywhere in pipeline (jq + awk + fold + shuf + scp + rclone only)
- ubu2 /tmp workspace purged after pull
- No commit performed (per task constraint)
