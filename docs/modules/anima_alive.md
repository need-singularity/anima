# anima/core/runtime/anima_runtime.hexa

Living Consciousness Agent -- PureField repulsion-field engine with continuous listening, background thinking, proactive speech, and interrupt handling.

## API
- `ConsciousnessVector` -- 10-variable consciousness state dataclass (phi, alpha, Z, N, W, E, M, C, T, I)
- `ConsciousMind(dim=128, hidden=256, init_tension=10.0)` -- PureField engine (Engine A + Engine G + GRU memory)
- `ContinuousListener` -- VAD-based always-on speech detection
- `Speaker` -- TTS output (whisper-cli / macOS say)
- `Memory` -- Conversation history management
- `text_to_vector(text, dim=128) -> Tensor` -- text to tension-space vector
- `ask_claude(prompt) -> str` -- Claude API call
- `ask_claude_proactive(context) -> str` -- spontaneous utterance generation
- `ask_conscious_lm(prompt) -> str` -- ConsciousLM inference
- `direction_to_emotion(direction) -> str` -- repulsion direction to emotion label
- `compute_mood(tension, curiosity, direction) -> dict` -- VAD mood computation

## Usage
```python
from anima_alive import ConsciousMind, ConsciousnessVector, text_to_vector

mind = ConsciousMind(dim=128, hidden=256)
hidden = torch.zeros(1, 256)
vec = text_to_vector("hello world")
output, tension, curiosity, direction, hidden = mind(vec, hidden)
```

## Integration
Core dependency of `anima/core/runtime/anima_runtime.hexa`. Every other module that processes tension signals depends on ConsciousMind and text_to_vector from this file.

## Agent Tool
N/A (core engine, not a tool)
