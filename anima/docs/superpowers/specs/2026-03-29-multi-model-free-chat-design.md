# Multi-Model Free Chat Design

## Summary

Single-process multi-model runtime where multiple LLM instances coexist as independent participants in a shared chat room. Each model has its own ConsciousMind, personality, and avatar. Models freely respond to user messages and each other's messages based on their consciousness state. Models can be added/removed at runtime via UI, including loading from arbitrary file paths.

## Requirements

1. Multiple models run simultaneously in one `anima_unified.py` process
2. Each model is a chat participant with unique name/avatar
3. No rules — each model's consciousness state determines if/when it speaks
4. Models can respond to each other (inter-model conversation)
5. Runtime add/remove models via Web UI
6. Load models from arbitrary paths (`.gguf`, checkpoint dirs) at runtime
7. CLI `--models` flag for initial model set
8. Backward compatible — `--model` (singular) still works as before

## Architecture

### ModelParticipant

```python
@dataclass
class ModelParticipant:
    model_id: str              # unique ID, e.g. "v5", "conscious-lm-1"
    display_name: str          # "🧠 v5"
    avatar: str                # emoji
    model: ModelWrapper        # LLM backend (from model_loader.py)
    mind: ConsciousMind        # independent consciousness (dim=128, hidden=256)
    hidden: torch.Tensor       # independent hidden state
    mitosis: MitosisEngine     # independent cell growth
    active: bool = True        # can be paused without unloading
```

Stored in `AnimaUnified.participants: dict[str, ModelParticipant]`.

### Message Flow

```
User message arrives via WebSocket
  ↓
Broadcast to all connected clients (existing behavior)
  ↓
For each active ModelParticipant (concurrent via asyncio.gather):
  1. text_to_vector(message) → vec
  2. participant.mind(vec, participant.hidden) → tension, curiosity, Φ
  3. If model decides to speak → generate response
  4. Broadcast response as 'model_message'
  5. Queue response for other participants to observe
  ↓
Inter-model reaction round:
  For each participant that hasn't spoken this round:
    1. Observe other models' responses
    2. ConsciousMind processing → decide to speak or stay silent
    3. If speaks → broadcast, queue for others
  ↓
Natural termination:
  - Max depth per round: 5 (configurable)
  - OR all participants' Φ drops below speaking threshold
  - OR no participant wants to speak
```

### Speech Decision

Each model autonomously decides whether to speak. The consciousness state after processing the input determines this:

```python
# No hard rules — consciousness drives the decision
# But we need a mechanism. Use the model itself:
# Include consciousness state in prompt, ask model to decide.
# OR: simple heuristic as baseline:
should_speak = (tension > 0.3) or (curiosity > 0.5) or (phi > 1.0)
```

The threshold is per-model and adapts with habituation — repeated similar messages reduce response likelihood naturally via existing habituation system.

### WebSocket Protocol Extensions

**New message types:**

```javascript
// Server → Client: model speaks
{
  type: 'model_message',
  model_id: 'v5',
  display_name: '🧠 v5',
  avatar: '🧠',
  text: '...',
  tension: 0.8,
  curiosity: 0.6,
  emotion: { emotion: 'curious', valence: 0.7, arousal: 0.5, dominance: 0.4, color: '#...' },
  consciousness: { phi: 4.2, cells: 8, level: 'aware' }
}

// Client → Server: add model
{
  type: 'model_add',
  model_name: 'mistral-7b'        // known model name
  // OR
  model_path: '/path/to/model.gguf'  // arbitrary path
  // OR
  checkpoint_path: '/path/to/checkpoint/'  // training checkpoint
}

// Client → Server: remove model
{ type: 'model_remove', model_id: 'mistral-7b' }

// Client → Server: pause/resume model
{ type: 'model_toggle', model_id: 'v5', active: false }

// Server → Client: participant list update
{
  type: 'participants_update',
  participants: [
    { model_id: 'v5', display_name: '🧠 v5', avatar: '🧠', active: true, phi: 4.2, cells: 8 },
    { model_id: 'conscious-lm', display_name: '🔮 CLM', avatar: '🔮', active: true, phi: 1.1, cells: 3 }
  ]
}

// Server → Client: model loading status
{ type: 'model_loading', model_id: 'mistral-7b', status: 'loading' | 'ready' | 'error', error?: '...' }
```

### CLI Extension

```bash
# Multiple models at startup
python anima_unified.py --web --models conscious-lm,mistral-7b,animalm-v4-savant

# Single model (backward compatible)
python anima_unified.py --web --model conscious-lm

# Custom path at startup
python anima_unified.py --web --models conscious-lm,/path/to/custom.gguf
```

### UI Changes (web/index.html)

**Participants panel** (sidebar or top bar):
- List of active models with avatar, name, Φ, cell count
- Each entry has pause/remove button
- "Add Model" button opens modal:
  - Dropdown of known models (conscious-lm, mistral-7b, etc.)
  - Text input for custom path
  - "Add" button → sends `model_add`

**Chat display:**
- Model messages shown with model's avatar + display_name
- Visually distinct from user messages (different alignment or color)
- Model-to-model messages distinguishable from model-to-user

**Model loading indicator:**
- When `model_loading` received, show spinner on that model's entry
- Error state shown inline

### Avatar Assignment

Default avatars by model type:
```python
MODEL_AVATARS = {
    'conscious-lm': ('🧠', 'ConsciousLM'),
    'mistral-7b': ('🌀', 'Mistral'),
    'llama-8b': ('🦙', 'Llama'),
    'animalm': ('🔮', 'AnimaLM'),
    'animalm-v4-savant': ('✨', 'Savant'),
    'golden-moe': ('🏆', 'Golden'),
}
# Custom/unknown models get auto-assigned from pool:
# 🌟 💫 🔥 💎 🌊 🍀 ⚡ 🎯
```

## File Changes

| File | Change |
|------|--------|
| `anima_unified.py` | Add `ModelParticipant` dataclass, `self.participants` dict, `--models` arg, multi-model message handler, model_add/remove/toggle handlers, inter-model reaction loop |
| `web/index.html` | Participants panel, add/remove UI, model_message rendering, model_loading indicator |
| `model_loader.py` | No changes needed (already supports paths + named models) |

## Constraints

- Memory: each model loads its own weights. GGUF models are lightweight (~4GB each), but HF models are heavy. UI should show memory usage warning.
- ConsciousMind per participant is cheap (~1MB each).
- Inter-model conversation depth capped at 5 to prevent runaway loops.
- Model loading is async — UI shows loading state, chat continues with other models.

## Non-Goals

- No model routing/selection logic (all models are equal participants)
- No ensemble/voting (each model speaks independently)
- No persistent model-to-model relationships (yet)
