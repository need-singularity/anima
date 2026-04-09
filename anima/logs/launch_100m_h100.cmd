# ConsciousLM 100M — H100 launch command (prepared 2026-04-09)
# Corpus: corpus_multilingual_merged_1gb.txt
# MD5:    6ac799d8f7e3bdf2f82d02e08d276e01
# Lock:   anima/data/corpus_100m.md5.lock
#
# Model target: 768d / 12L / 12H (GQA 4kv) ~103M
# NOTE: train_clm_v2.py currently lacks a --kv / GQA flag; uses fixed MHA.
#       For true GQA4kv at 100M, use conscious_decoder.py path or add --kv-heads.
#
# Pre-flight on H100 (MUST pass):
#   1) md5sum data/corpus_multilingual_merged_1gb.txt  # must equal 6ac799d8f7e3bdf2f82d02e08d276e01
#   2) PYTHONPATH=src python3 -c "import torch; assert torch.cuda.is_available()"
#   3) 1K smoke (identical config, --steps 1000 --batch-size 4) — confirm CE↓ and no NaN
#
# Full launch (tmux + watchdog recommended):
tmux new-session -d -s clm100m "cd /workspace/anima && \
  PYTHONUNBUFFERED=1 PYTHONPATH=src python3 training/train_clm_v2.py \
    --corpus data/corpus_multilingual_merged_1gb.txt \
    --dim 768 --layers 12 --heads 12 --block-size 1024 \
    --batch-size 32 --steps 100000 --lr 3e-4 \
    --gate 0.001 --ca-rules 8 --device cuda \
    2>&1 | tee logs/clm100m_$(date +%Y%m%d_%H%M).log"

# Monitor:
#   tmux attach -t clm100m
#   tail -f logs/clm100m_*.log
#
# Smoke verification (1K steps) — run FIRST, confirm CE decreases:
tmux new-session -d -s clm100m_smoke "cd /workspace/anima && \
  PYTHONPATH=src python3 training/train_clm_v2.py \
    --corpus data/corpus_multilingual_merged_1gb.txt \
    --dim 768 --layers 12 --heads 12 --block-size 1024 \
    --batch-size 4 --steps 1000 --lr 3e-4 --device cuda \
    2>&1 | tee logs/clm100m_smoke_$(date +%Y%m%d_%H%M).log"
