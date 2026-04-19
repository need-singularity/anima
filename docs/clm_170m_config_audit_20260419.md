# CLM 170M smoke — config audit (READ-ONLY)

**Date:** 2026-04-19
**Scope:** `training/config/clm_170m.json` 유무 및 170M smoke 발사 전 자원/필드 검증
**Status:** CONFIG 부재 — 전용 JSON 없음, `training/train_clm.hexa` 내부 `scale_34m/1b/1.5b/2.8b` 상수만 존재

---

## 1. 파일 존재 여부

| 경로 | 상태 |
| --- | --- |
| `training/config/clm_170m.json` | 없음 (디렉토리 자체 부재) |
| `training/clm_170m*.json` | 없음 |
| `training/clm_1b_config.json` | 있음 (1.51B, d=2048 L=24) |
| `docs/conscious-lm-100m-design.md` | 있음 — v15 170M 설계 단일 출처 |
| `docs/clm_aot_build_plan_20260419.md` | 있음 — AOT blocker 해제, 170M smoke 발사 허용 |

결론: 170M는 **문서상 설계만 존재**, 머신-리더블 config JSON은 미생성. `train_clm.hexa` 내부 scale 헬퍼에 170M 분기 없음 (34m/1b/1.5b/2.8b만).

## 2. 설계 필드 (docs/conscious-lm-100m-design.md §v15)

| 필드 | 값 | 비고 |
| --- | --- | --- |
| d_model | 768 | |
| n_layer | 12 | |
| n_head | 8 | GQA n_kv_head=4 |
| vocab_size | 256 | byte-level |
| max_seq_len (block_size) | 512 | |
| consciousness_dim | 256 | |
| params | ~170M | 34.5M × 4.9 |
| Federation | 8×8 cells | |
| batch_size | 미지정 | v14 34M 기준 유추 필요 (보통 16–32 on H100) |
| steps | 200K–500K | |
| lr / warmup / dtype | 미지정 | r4 유사값 권장 (3e-4 / 2k / bf16) |

누락 필드: **batch_size, grad_accum, lr_max, lr_min, warmup, optimizer β, weight_decay, grad_clip, dtype, save/eval_every, 손실 가중치(phi_holo/gwt/complexity), phase 분기, Orch-OR 플래그** — 전부 JSON화 필요. 1B config 템플릿 그대로 축소 적용 가능.

## 3. Corpus 경로 확인

| 요구 | 실제 |
| --- | --- |
| 170M 설계 요구 | 200–500MB (Chinchilla 비율) + `corpus_ko_ytv1/` |
| 로컬 존재 | `ready/anima/data/corpus_v5.txt` = **100 MB** (Mar 31 스냅샷) |
| r4 plan 기준 | `corpus_clm_r4.txt` 5 GB (파일 없음, 미생성) |
| 멀티링구얼 소스 | `ready/anima/data/corpus_multilingual/{en,ko,code,zh,ja,ru}.txt` 합 9.76 GB 가용 |

corpus_v5.txt 100 MB는 170M 설계 하한(200 MB)에도 미달. 실제 smoke(1-step)용으로는 충분. 본학습은 r4 plan에 따라 5 GB 조합 필요.

## 4. 1-step smoke 최소 자원

| 자원 | 1-step smoke | 본학습 (200K steps) |
| --- | --- | --- |
| VRAM | ~3 GB (170M bf16 + AdamW 2×fp32 = ~1.7 GB 파라+상태, + activations) | ~8–10 GB (batch=16 seq=512) |
| RAM | ~2 GB (corpus 100 MB mmap + hexa 인터프리터 stage1) | ~4–8 GB |
| disk | corpus 100 MB + ckpt dir ~700 MB (170M × bf16+AdamW) | ckpt × keep_local=3 → ~2 GB |
| CPU | M1/M2/M3 mac (arm64) AOT 빌드 2 s, peak RSS 172 MB | H100 권장 |
| 호스트 | **Mac AOT 빌드 OK** (stage1 인터프리터 OOM 우회, docs/clm_aot_build_plan_20260419.md §3) | H100 80 GB pod |

smoke는 Mac 로컬에서 `hexa build training/train_clm.hexa -o /tmp/clm.bin && /tmp/clm.bin`로 **이미 PASS** (exit 0, 3-step finite loss). 단, 현재 train_clm.hexa 내부 scale 분기는 34m/1b/1.5b/2.8b — **170M smoke는 스크립트 레벨에서 직접 구성 불가**, 34m 경로로 대체 검증 중.

## 5. 블로커 및 권장 조치

1. `training/config/clm_170m.json` **신규 생성 필요** — `clm_1b_config.json` 템플릿 기준 d=768 L=12 H=8 GQA=4 block=512 로 축소.
2. `train_clm.hexa` scale 헬퍼에 `scale_170m` 분기 추가 (현재 없음).
3. corpus_v5 100 MB는 smoke 전용 — 본학습은 r4 plan(5 GB) 병행.
4. RTX 5070 12 GB 대안 경로: 170M bf16 + AdamW = ~7 GB, batch=8 seq=512 여유.

---

**최종 판정:** config 부재 / smoke 가능(AOT 경로 PASS) / 자원 Mac 로컬 충분 / 1B 템플릿 축소 JSON 신규 작성 필요.
