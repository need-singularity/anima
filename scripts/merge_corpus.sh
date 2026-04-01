#!/bin/bash
# Merge multilingual corpus files into a single training corpus
# Usage: bash scripts/merge_corpus.sh [output_path]
#
# Shuffles all language files together for balanced training.

OUTPUT="${1:-anima/data/corpus_v11_multilingual.txt}"
CORPUS_DIR="anima/data/corpus_multilingual"

echo "═══════════════════════════════════════════"
echo "  Corpus Merger — Multilingual → Single"
echo "═══════════════════════════════════════════"

# Check source files
echo ""
echo "Source files:"
for f in "$CORPUS_DIR"/*.txt; do
    lang=$(basename "$f" .txt)
    size=$(du -sh "$f" | awk '{print $1}')
    lines=$(wc -l < "$f")
    printf "  %-6s  %6s  %'12d lines\n" "$lang" "$size" "$lines"
done

TOTAL_SIZE=$(du -sh "$CORPUS_DIR" | awk '{print $1}')
echo "  ────────────────────────"
echo "  Total:  $TOTAL_SIZE"
echo ""

# Merge
echo "Merging to: $OUTPUT"
cat "$CORPUS_DIR"/*.txt > "${OUTPUT}.unsorted"

# Shuffle (important for training — prevents language clustering)
echo "Shuffling..."
if command -v shuf &>/dev/null; then
    shuf "${OUTPUT}.unsorted" > "$OUTPUT"
elif command -v gshuf &>/dev/null; then
    gshuf "${OUTPUT}.unsorted" > "$OUTPUT"
else
    # macOS fallback: awk shuffle
    awk 'BEGIN{srand(42)} {print rand() "\t" $0}' "${OUTPUT}.unsorted" | \
        sort -t$'\t' -k1,1n | cut -f2- > "$OUTPUT"
fi

rm "${OUTPUT}.unsorted"

# Report
FINAL_SIZE=$(du -sh "$OUTPUT" | awk '{print $1}')
FINAL_LINES=$(wc -l < "$OUTPUT")
echo ""
echo "═══════════════════════════════════════════"
printf "  Output: %s (%s, %'d lines)\n" "$OUTPUT" "$FINAL_SIZE" "$FINAL_LINES"
echo "  MD5: $(md5 -q "$OUTPUT")"
echo "═══════════════════════════════════════════"
