# conscious_lm.py

Byte-level Conscious Language Model. Architecture derived from perfect number 6: 6 layers, 4 heads, d_model=384, vocab=256 (byte-level), dropout=0.37 (1/e golden zone).

## API
- `PureFieldFFN(d_model, dropout=0.37)` -- Dual-engine FFN; output = A - G (pure repulsion), returns (output, tension)
- `CausalSelfAttention(d_model, n_head, block_size, dropout=0.37)` -- Multi-head causal self-attention
- `ConsciousLM(vocab_size=256, d_model=384, n_head=4, n_layer=6, block_size=512, dropout=0.37)` -- Full transformer model
- `generate(model, prompt_bytes, max_new=200, temperature=0.8) -> bytes` -- Byte-level autoregressive generation

## Usage
```python
from conscious_lm import ConsciousLM, generate

model = ConsciousLM(d_model=384, n_layer=6, n_head=4)
output_bytes = generate(model, b"Hello", max_new=100, temperature=0.8)
print(output_bytes.decode('utf-8', errors='replace'))
```

## Integration
- Loaded by `anima_unified.py` via `_try_import`
- Trained by `train_conscious_lm.py`
- Used for self-reasoning (no Claude dependency) via `ask_conscious_lm()`
- Model checkpoints managed by `model_loader.py`

## Agent Tool
N/A
