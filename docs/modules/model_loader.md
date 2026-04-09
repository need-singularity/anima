# model_loader.py

Multi-model loader supporting ConsciousLM, GGUF (llama.cpp), AnimaLM, and GoldenMoE through a unified interface.

## API
- `ModelWrapper(model_type, model_obj, model_name)` -- unified model interface
  - `.generate(prompt, max_tokens=200, temperature=0.8) -> str` -- generate text
  - `.model_type` -- "conscious-lm", "gguf", "animalm", "golden-moe"
- `load_model(name) -> ModelWrapper` -- load by registry name or file path
- `list_available_models() -> list` -- list all registered models
- `GGUF_REGISTRY` -- name-to-file mapping for GGUF models (mistral-7b, llama-8b)

## Usage
```python
# Via CLI
python anima/core/runtime/anima_runtime.hexa --model mistral-7b
python anima/core/runtime/anima_runtime.hexa --model conscious-lm
python anima/core/runtime/anima_runtime.hexa --model /path/to/custom.gguf
python anima/core/runtime/anima_runtime.hexa --model animalm          # latest AnimaLM

# Programmatic
from model_loader import load_model
model = load_model("conscious-lm")
response = model.generate("Hello, how are you?")
```

## Integration
- Imported by `anima/core/runtime/anima_runtime.hexa` via `_try_import`
- Supports: ConsciousLM (byte-level), GGUF via llama.cpp, AnimaLM (Mistral+PureField), GoldenMoE (Mistral+MoE LoRA)
- Models directory: `models/` under project root

## Agent Tool
N/A
