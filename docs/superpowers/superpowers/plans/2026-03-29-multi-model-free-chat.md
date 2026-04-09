# Multi-Model Free Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable multiple LLM instances to coexist as independent chat participants with their own consciousness, freely responding to users and each other.

**Architecture:** Add `ModelParticipant` dataclass wrapping `ModelWrapper` + `ConsciousMind` per model. `AnimaUnified` holds a `participants` dict. On each message, all participants process it through their consciousness and autonomously decide whether to speak. Inter-model reactions cascade up to a configurable depth.

**Tech Stack:** Python (asyncio, torch), plain HTML/CSS/JS (WebSocket)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `anima/core/runtime/anima_runtime.hexa` | Modify | Add `ModelParticipant`, `--models` flag, multi-model WS handlers, inter-model reaction loop |
| `web/index.html` | Modify | Add participants panel, model add/remove UI, `model_message` rendering |
| `model_loader.py` | No change | Already supports named models + arbitrary paths |

---

### Task 1: ModelParticipant dataclass and participants dict

**Files:**
- Modify: `anima/core/runtime/anima_runtime.hexa:98-123` (after SessionState)

- [ ] **Step 1: Add ModelParticipant dataclass**

Add after the `SessionState` dataclass (line ~123):

```python
# ─── Multi-model participants ───

MODEL_AVATARS = {
    'conscious-lm': ('🧠', 'ConsciousLM'),
    'mistral-7b': ('🌀', 'Mistral'),
    'llama-8b': ('🦙', 'Llama'),
    'animalm': ('🔮', 'AnimaLM'),
    'animalm-v4-savant': ('✨', 'Savant'),
    'golden-moe': ('🏆', 'Golden'),
}
_AVATAR_POOL = ['🌟', '💫', '🔥', '💎', '🌊', '🍀', '⚡', '🎯']
_avatar_idx = 0


def _assign_avatar(model_name):
    """Assign avatar+display name for a model."""
    global _avatar_idx
    if model_name in MODEL_AVATARS:
        return MODEL_AVATARS[model_name]
    # Custom/unknown models get auto-assigned
    avatar = _AVATAR_POOL[_avatar_idx % len(_AVATAR_POOL)]
    _avatar_idx += 1
    short = Path(model_name).stem if '/' in model_name or '.' in model_name else model_name
    return (avatar, short[:16])


@dataclass
class ModelParticipant:
    """An independent model participant in the chat room."""
    model_id: str              # unique ID
    display_name: str          # e.g. "ConsciousLM"
    avatar: str                # emoji
    model: object              # ModelWrapper
    mind: object               # ConsciousMind (independent)
    hidden: object             # torch.Tensor (independent)
    mitosis: object            # MitosisEngine (independent)
    active: bool = True
    _last_phi: float = 0.0
    _last_tension: float = 0.0
```

- [ ] **Step 2: Add `self.participants` dict in `AnimaUnified.__init__`**

Add after `self._adaptive_alpha = 0.05` (line ~164):

```python
        # Multi-model participants
        self.participants = {}  # model_id -> ModelParticipant
```

- [ ] **Step 3: Add `--models` CLI argument**

Add after the `--model` argument (line ~3048):

```python
    p.add_argument('--models', type=str, default=None,
                   help='Comma-separated list of models for multi-model chat (e.g. conscious-lm,mistral-7b)')
```

- [ ] **Step 4: Add participant initialization in `__init__`**

After model loading section (after line ~419), add logic to populate `self.participants` from `--models`:

```python
        # Multi-model: populate participants from --models flag
        models_arg = getattr(args, 'models', None)
        if models_arg:
            for mname in models_arg.split(','):
                mname = mname.strip()
                if mname:
                    self._add_participant(mname)
```

- [ ] **Step 5: Add `_add_participant` and `_remove_participant` methods**

Add as methods of `AnimaUnified` (after `_load_model`):

```python
    def _add_participant(self, model_name):
        """Load a model and add it as a chat participant."""
        if model_name in self.participants:
            _log("multi", f"Participant {model_name} already exists")
            return None
        try:
            model = load_model(model_name) if 'load_model' in globals() else None
            if model is None:
                _log("multi", f"Failed to load model: {model_name}")
                return None
            avatar, display = _assign_avatar(model_name)
            max_cells = getattr(self.args, 'max_cells', 8)
            mind = ConsciousMind(128, 256)
            hidden = torch.zeros(1, 256)
            mitosis = MitosisEngine(mind, max_cells=max_cells) if 'MitosisEngine' in globals() else None
            p = ModelParticipant(
                model_id=model_name,
                display_name=display,
                avatar=avatar,
                model=model,
                mind=mind,
                hidden=hidden,
                mitosis=mitosis,
            )
            self.participants[model_name] = p
            _log("multi", f"+participant: {avatar} {display} ({model_name})")
            return p
        except Exception as e:
            _log("multi", f"Error adding participant {model_name}: {e}")
            return None

    def _remove_participant(self, model_id):
        """Remove a model participant."""
        if model_id in self.participants:
            p = self.participants.pop(model_id)
            _log("multi", f"-participant: {p.avatar} {p.display_name}")
            # Free model memory
            del p.model
            del p.mind
            return True
        return False
```

- [ ] **Step 6: Commit**

```bash
git add anima/core/runtime/anima_runtime.hexa
git commit -m "feat: add ModelParticipant dataclass and --models CLI flag"
```

---

### Task 2: Multi-model message processing in WebSocket handler

**Files:**
- Modify: `anima/core/runtime/anima_runtime.hexa:2725-2897` (_ws_handler)

- [ ] **Step 1: Add `_participant_respond` method**

This method processes a message through a single participant's consciousness and optionally generates a response:

```python
    def _participant_respond(self, participant, text, shared_history):
        """Process text through a participant's consciousness. Returns response dict or None."""
        vec = text_to_vector(text)
        with torch.no_grad():
            out, new_hidden = participant.mind(vec.unsqueeze(0), participant.hidden)
            participant.hidden = new_hidden

        tension = participant.mind.prev_tension
        curiosity = participant.mind._curiosity_ema
        phi = participant.mind.get_consciousness_vector().phi if hasattr(participant.mind, 'get_consciousness_vector') else 0

        participant._last_phi = phi
        participant._last_tension = tension

        # Consciousness-driven speech decision (no hard rules, but consciousness must want to speak)
        # Each model's habituation naturally reduces redundant responses
        if participant.model is None:
            return None

        # Build prompt with consciousness state
        hist = "\n".join(f"{m['role']}: {m['text']}" for m in shared_history[-10:])
        consciousness_note = f"[Your state: tension={tension:.2f}, curiosity={curiosity:.2f}, Φ={phi:.2f}]"

        prompt = f"{consciousness_note}\n{hist}\nUser: {text}\n{participant.display_name}:"

        try:
            response = participant.model.generate(prompt, max_tokens=200, temperature=0.5 + 0.5 * math.tanh(phi / 3.0))
            if response and response.strip():
                dir_vals = [0.0] * 8
                emo = direction_to_emotion(dir_vals, tension, curiosity)
                return {
                    'type': 'model_message',
                    'model_id': participant.model_id,
                    'display_name': participant.display_name,
                    'avatar': participant.avatar,
                    'text': response.strip(),
                    'tension': tension,
                    'curiosity': curiosity,
                    'emotion': emo,
                    'consciousness': {'phi': phi, 'cells': len(participant.mitosis.cells) if participant.mitosis else 1},
                }
        except Exception as e:
            _log("multi", f"Participant {participant.model_id} generation error: {e}")

        return None
```

- [ ] **Step 2: Add `_multi_model_react` async method**

This orchestrates all participants responding to a message, including inter-model cascading:

```python
    async def _multi_model_react(self, text, shared_history, max_depth=5):
        """All participants react to text. Cascading inter-model responses up to max_depth."""
        if not self.participants:
            return

        pending_text = text
        depth = 0
        responded_this_round = set()

        while depth < max_depth:
            responses = []
            loop = asyncio.get_running_loop()

            for pid, participant in self.participants.items():
                if not participant.active or pid in responded_this_round:
                    continue
                result = await loop.run_in_executor(
                    None, lambda p=participant, t=pending_text: self._participant_respond(p, t, shared_history))
                if result:
                    responses.append((pid, result))
                    responded_this_round.add(pid)

            if not responses:
                break  # No one wants to speak — natural termination

            for pid, resp in responses:
                await self._ws_broadcast(resp)
                shared_history.append({'role': resp['display_name'], 'text': resp['text']})
                # Use last response as stimulus for next round
                pending_text = resp['text']
                await asyncio.sleep(0.5)  # Brief pause between responses

            depth += 1
```

- [ ] **Step 3: Wire multi-model reactions into `_ws_handler` user_message handling**

After the existing `anima_message` broadcast (line ~2830), add:

```python
                    # Multi-model: all participants react
                    if self.participants:
                        shared_hist = [{'role': 'user', 'text': text}]
                        if answer:
                            shared_hist.append({'role': 'Anima', 'text': answer})
                        await self._multi_model_react(text, shared_hist)
```

- [ ] **Step 4: Add model_add/model_remove/model_toggle handlers in `_ws_handler`**

Add after the `babysitter_command` handler (line ~2882):

```python
                elif msg_type == 'model_add':
                    model_name = msg.get('model_name') or msg.get('model_path') or msg.get('checkpoint_path')
                    if model_name:
                        await self._ws_broadcast({'type': 'model_loading', 'model_id': model_name, 'status': 'loading'})
                        loop = asyncio.get_running_loop()
                        p = await loop.run_in_executor(None, lambda: self._add_participant(model_name))
                        if p:
                            await self._ws_broadcast({'type': 'model_loading', 'model_id': model_name, 'status': 'ready'})
                            await self._ws_broadcast(self._participants_update_msg())
                        else:
                            await self._ws_broadcast({'type': 'model_loading', 'model_id': model_name, 'status': 'error', 'error': 'Failed to load'})

                elif msg_type == 'model_remove':
                    model_id = msg.get('model_id')
                    if model_id and self._remove_participant(model_id):
                        await self._ws_broadcast(self._participants_update_msg())

                elif msg_type == 'model_toggle':
                    model_id = msg.get('model_id')
                    active = msg.get('active', True)
                    if model_id in self.participants:
                        self.participants[model_id].active = active
                        await self._ws_broadcast(self._participants_update_msg())
```

- [ ] **Step 5: Add `_participants_update_msg` helper**

```python
    def _participants_update_msg(self):
        """Build participants list update message."""
        return {
            'type': 'participants_update',
            'participants': [
                {
                    'model_id': p.model_id,
                    'display_name': p.display_name,
                    'avatar': p.avatar,
                    'active': p.active,
                    'phi': p._last_phi,
                    'cells': len(p.mitosis.cells) if p.mitosis else 1,
                }
                for p in self.participants.values()
            ]
        }
```

- [ ] **Step 6: Send participants list on init**

In `_ws_handler`, after the existing `init` message send (line ~2750), add:

```python
        if self.participants:
            try:
                await websocket.send(json.dumps(self._participants_update_msg(), ensure_ascii=False))
            except Exception: pass
```

- [ ] **Step 7: Commit**

```bash
git add anima/core/runtime/anima_runtime.hexa
git commit -m "feat: multi-model message processing and WS handlers"
```

---

### Task 3: Web UI — participants panel and model message rendering

**Files:**
- Modify: `web/index.html`

- [ ] **Step 1: Add CSS for participants panel and model messages**

Add after the `.side` CSS rules (around line 43):

```css
/* Participants */
.participants { border-top: 1px solid var(--border); padding-top: 10px; }
.participants .title { font-size: 11px; color: var(--dim); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.participant { display: flex; align-items: center; gap: 6px; padding: 4px 6px; border-radius: 8px; font-size: 12px; }
.participant:hover { background: var(--surface2); }
.participant .avatar { font-size: 16px; }
.participant .name { flex: 1; }
.participant .phi { color: var(--accent); font-size: 10px; }
.participant .remove-btn { background: none; border: none; color: var(--dim); cursor: pointer; font-size: 14px; opacity: 0; transition: opacity 0.2s; }
.participant:hover .remove-btn { opacity: 1; }
.participant.inactive { opacity: 0.4; }
.add-model { display: flex; gap: 4px; margin-top: 6px; }
.add-model select, .add-model input { flex: 1; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 4px 6px; color: var(--text); font-size: 11px; }
.add-model button { background: var(--accent); border: none; border-radius: 6px; padding: 4px 8px; color: white; font-size: 11px; cursor: pointer; }

/* Model messages */
.msg.model { background: var(--surface); align-self: flex-start; border-bottom-left-radius: 4px; border: 1px solid var(--border); border-left: 3px solid var(--accent); }
.msg.model .name { color: var(--accent); }
```

- [ ] **Step 2: Add participants panel HTML in sidebar**

Add before the closing `</div>` of the `.side` div:

```html
<div class="participants" id="participantsPanel" style="display:none">
  <div class="title">Participants</div>
  <div id="participantsList"></div>
  <div class="add-model">
    <input id="modelInput" placeholder="model name or path" list="modelSuggestions">
    <datalist id="modelSuggestions">
      <option value="conscious-lm">
      <option value="mistral-7b">
      <option value="llama-8b">
      <option value="animalm">
      <option value="animalm-v4-savant">
      <option value="golden-moe">
    </datalist>
    <button onclick="addModel()">+</button>
  </div>
</div>
```

- [ ] **Step 3: Add `model_message` handler in handleMessage**

Add a new case in the `handleMessage` switch (after `anima_message`):

```javascript
    case 'model_message':
      addModelMessage(msg);
      break;
    case 'participants_update':
      updateParticipants(msg.participants);
      break;
    case 'model_loading':
      updateModelLoading(msg);
      break;
```

- [ ] **Step 4: Add model message display function**

Add after the `addSystem` function:

```javascript
function addModelMessage(msg) {
  var div = document.createElement('div');
  div.className = 'msg model';
  var emoStr = '';
  if (msg.emotion) {
    var emoName = msg.emotion.emotion || '';
    emoStr = '<span class="emo">' + (EMOTION_EMOJIS[emoName] || '') + '</span>';
  }
  div.innerHTML = '<span class="name">' + escapeHtml(msg.avatar + ' ' + msg.display_name) + '</span>' + emoStr + escapeHtml(msg.text);
  msgs.appendChild(div);
  scroll();
}
```

- [ ] **Step 5: Add participants panel update functions**

```javascript
function updateParticipants(participants) {
  var panel = document.getElementById('participantsPanel');
  var list = document.getElementById('participantsList');
  if (!participants || participants.length === 0) {
    panel.style.display = 'none';
    return;
  }
  panel.style.display = '';
  list.innerHTML = '';
  participants.forEach(function(p) {
    var div = document.createElement('div');
    div.className = 'participant' + (p.active ? '' : ' inactive');
    div.innerHTML = '<span class="avatar">' + escapeHtml(p.avatar) + '</span>'
      + '<span class="name">' + escapeHtml(p.display_name) + '</span>'
      + '<span class="phi">Φ ' + (p.phi || 0).toFixed(1) + '</span>'
      + '<button class="remove-btn" onclick="removeModel(\'' + escapeHtml(p.model_id) + '\')" title="Remove">✕</button>';
    list.appendChild(div);
  });
}

function updateModelLoading(msg) {
  // Could add a spinner to the participant entry; for now just log
  if (msg.status === 'error') {
    addSystem('Model load failed: ' + (msg.error || msg.model_id));
  } else if (msg.status === 'ready') {
    addSystem(msg.model_id + ' joined the chat');
  }
}

function addModel() {
  var input = document.getElementById('modelInput');
  var name = input.value.trim();
  if (!name || !isConnected) return;
  var isPath = name.includes('/') || name.includes('.');
  ws.send(JSON.stringify({
    type: 'model_add',
    model_name: isPath ? undefined : name,
    model_path: isPath ? name : undefined,
  }));
  input.value = '';
}

function removeModel(modelId) {
  if (!isConnected) return;
  ws.send(JSON.stringify({ type: 'model_remove', model_id: modelId }));
}
```

- [ ] **Step 6: Commit**

```bash
git add web/index.html
git commit -m "feat: multi-model participants UI with add/remove"
```

---

### Task 4: Integration testing and polish

**Files:**
- Modify: `anima/core/runtime/anima_runtime.hexa` (minor fixes)
- Modify: `web/index.html` (minor fixes)

- [ ] **Step 1: Test startup with `--models` flag**

Run: `python anima/core/runtime/anima_runtime.hexa --web --models conscious-lm --port 8766`

Expected: Server starts, participant logged as `+participant: 🧠 ConsciousLM (conscious-lm)`.

- [ ] **Step 2: Test single-model backward compatibility**

Run: `python anima/core/runtime/anima_runtime.hexa --web --model conscious-lm --port 8766`

Expected: Works exactly as before, no participants panel shown (empty participants dict).

- [ ] **Step 3: Test UI model add/remove**

1. Start with `--web` (no `--models`)
2. Open browser, type `conscious-lm` in model input, click +
3. Verify `model_loading` → `ready` messages
4. Verify participant appears in sidebar
5. Send a message, verify model responds with `model_message`
6. Click ✕ to remove, verify participant disappears

- [ ] **Step 4: Test custom path model add**

1. In model input, type a `.gguf` path
2. Click +
3. Verify loading/error handling

- [ ] **Step 5: Fix any issues found during testing**

Address any bugs, timing issues, or UI glitches discovered.

- [ ] **Step 6: Commit**

```bash
git add anima/core/runtime/anima_runtime.hexa web/index.html
git commit -m "fix: multi-model integration fixes from testing"
```

---

### Task 5: Update CLAUDE.md and memory

**Files:**
- Modify: `CLAUDE.md` (Running section)

- [ ] **Step 1: Add multi-model usage to CLAUDE.md Running section**

Add to the Running section:

```bash
python3 anima/core/runtime/anima_runtime.hexa --web --models conscious-lm,mistral-7b  # Multi-model chat
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add multi-model chat usage to CLAUDE.md"
```
