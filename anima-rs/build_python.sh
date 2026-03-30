#!/bin/bash
# Build Python bindings for anima-rs (including online-learner)
# Requires: maturin (pip install maturin)

set -e
cd "$(dirname "$0")"

echo "Building anima-rs Python bindings..."
maturin develop --release

echo "Testing import..."
python3 -c "
import anima_rs
print('anima_rs version:', anima_rs.__name__)
print('Modules:', dir(anima_rs))
"

echo "Done!"
