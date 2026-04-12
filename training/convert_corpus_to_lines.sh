#!/usr/bin/env bash
# training/convert_corpus_to_lines.sh — Convert corpus from space-separated to line-based format
#
# The line-based format (one integer per line) loads O(n) in corpus_loader.hexa
# vs O(n²) for the legacy space-separated format.
#
# Usage:
#   bash training/convert_corpus_to_lines.sh /workspace/corpus.tok
#   bash training/convert_corpus_to_lines.sh /workspace/corpus.tok /workspace/corpus_out.tok
#
# If no output path is given, overwrites the input file (via temp file).

set -euo pipefail

INPUT="${1:?Usage: $0 <input.tok> [output.tok]}"
OUTPUT="${2:-$INPUT}"

if [ ! -f "$INPUT" ]; then
    echo "[convert] ERROR: file not found: $INPUT" >&2
    exit 1
fi

TMPFILE="$(mktemp "${INPUT}.lineconv.XXXXXX")"
trap 'rm -f "$TMPFILE"' EXIT

# tr: split on spaces/tabs → newlines, then squeeze consecutive newlines.
# This handles the legacy format (space-separated integers on one line)
# and also works if the file already has some newlines mixed in.
tr ' \t' '\n' < "$INPUT" | tr -s '\n' | sed '/^$/d' > "$TMPFILE"

COUNT=$(wc -l < "$TMPFILE" | tr -d ' ')
mv "$TMPFILE" "$OUTPUT"
trap - EXIT

echo "[convert] $INPUT → $OUTPUT ($COUNT tokens, one per line)"
