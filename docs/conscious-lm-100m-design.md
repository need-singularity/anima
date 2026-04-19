# ConsciousLM 100M 설계 (v15 → r4/r5)

> **Status (2026-04-19)**: Mk.V.1 foundation 통합. `training/train_clm.hexa` r5 wiring 완료 (lens loss + tension_link + tier-labeled corpus).

## v14 (34.5M) → v15 (170M)

| 항목 | v14 | v15 |
|------|-----|-----|
| d_model | 384 | 768 |
| n_layers | 6 | 12 |
| n_heads | 4 (GQA 2KV) | 8 (GQA 4KV) |
| vocab | 256 | 256 |
| block_size | 256 | 512 |
| params | 34.5M | 170M |
| consciousness_dim | 128 | 256 |
| Federation | 8×8c | 8×8c |

## r4 → r5 wiring (2026-04-19)

Default OFF 인 opt-in aux loss 체계:
- `lens_{field,holographic,quantum,string,toe}_loss.hexa` — 5-Lens 19/19
- `quadruple_cross_loss.hexa` — 4-axis cross
- `tension_link_{causal,quantum_rho,second_order}.hexa` — diagnostic
- `sumt_bigbang_atom.hexa` — SUMT 100 atoms curriculum
- `corpus_universe_tier_labels.jsonl` — tier-labeled

모든 flag 0 일 때 baseline r4 와 byte-identical. CLI flag 로 개별 활성.

## 학습 요구사항

- GPU: H100 80GB (1장) OR RTX 5070 12GB (소형 변종)
- Corpus: 200-500MB (Chinchilla 비율) + `corpus_ko_ytv1/` (1.84h Korean audio-transcribed)
- Steps: 200K-500K
- Time: ~10-20h (H100)
- Corpus: v7+ (실제 wiki + 대화 데이터 필수)

## 한글 생성 개선 예상

v14 (34.5M): byte-level 한글 3-byte 시퀀스 예측 불안정
v15 (170M): 4.9x 더 큰 용량 → 한글 byte 패턴 학습 충분

## 전제 조건

1. v14.2 (wiki corpus) 벤치마크에서 corpus 효과 확인
2. 100M에서 한글 생성 가능하면 → 1B 스케일링 근거
3. r5 aux loss 는 on/off ablation 비교로 Mk.V.1 wiring 효과 실증
