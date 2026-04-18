# CLM R4 Corpus — R2 Upload Index

## Upload
- start: 2026-04-18T15:42:12Z
- end:   2026-04-18T15:53:01Z
- total: ~10m49s (gz ~4m46s, raw ~10m43s; parallel)
- mac:   /Users/ghost/Dev/anima (rclone r2 remote)

## R2 Paths (bucket: anima-corpus)
| file | r2 key | size | local sha256 | md5 (local==r2) |
|------|--------|------|--------------|------------------|
| gz   | r2:anima-corpus/clm_r4/corpus_clm_r4.txt.gz | 1709490208 (1.592 GiB) | 8dc92c3230f874eefab4eb29b1908e9561ca0930c878c14485b601a1090a5bc2 | 374fe9d5bf1fda309ff48e7f8aefc07c |
| raw  | r2:anima-corpus/clm_r4/corpus_clm_r4.txt    | 5380874900 (5.011 GiB) | a606bd375d78f1ae19f327a62417541a6ac737440e15b97e5a483085a9e757a8 | e9c7f139a0de1e58def231043e584653 |

Size match: local == r2 (exact byte).
MD5 match: local == r2 (both files).
Note: R2/Cloudflare does not expose server-side sha256; MD5 is the supported hash.

## R2 Bucket
- bucket: anima-corpus (note: scaffold reference `anima-corpora` is a typo)
- clm_r4/ size: 6.603 GiB (2 objects)
- bucket total: 20.178 GiB (34 objects)

## Next Fire — Pull Recipe (pod side)
```
# gz (recommended — faster download)
rclone copy r2:anima-corpus/clm_r4/corpus_clm_r4.txt.gz /workspace/ --s3-no-check-bucket
gunzip /workspace/corpus_clm_r4.txt.gz

# or raw (if gunzip slow on pod)
rclone copy r2:anima-corpus/clm_r4/corpus_clm_r4.txt /workspace/ --s3-no-check-bucket
```

Scaffold flag:
```
--corpus-r2 r2:anima-corpus/clm_r4/corpus_clm_r4.txt
```
(or `.gz` variant when launcher supports stream-decompress)

## Local Preservation
Local files untouched (not deleted, not modified):
- /Users/ghost/Dev/anima/training/corpus_clm_r4.txt
- /Users/ghost/Dev/anima/training/corpus_clm_r4.txt.gz
