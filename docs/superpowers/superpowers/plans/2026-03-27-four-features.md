# 4 Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement savant auto-toggle, CLI+Web simultaneous chat, babysitter (Claude CLI), and auto dim expansion.

**Architecture:** Each feature is independent. Savant adds self-activation logic to mitosis tension analysis. CLI+Web shares a single process_input() with dual I/O. Babysitter runs as a background thread calling Claude CLI subprocess. Growth auto-triggers dim expansion via existing growth_manager.

**Tech Stack:** Python 3.14, PyTorch, websockets, subprocess (Claude CLI)

---

## File Structure

```
Modified:
  anima/core/runtime/anima_runtime.hexa    — savant auto-toggle, CLI+Web dual mode, babysitter thread, growth dim hookup
  anima/core/runtime/anima_runtime.hexa      — savant state tracking in ConsciousMind
  web/index.html      — savant orange indicator, babysitter panel/toggle, CLI messages display
  growth_engine.py    — emit growth event for dim expansion trigger

Created:
  babysitter.py       — Claude CLI educator agent
```

---

### Task 1: Savant Auto-Toggle + Orange UI

**Files:**
- Modify: `anima/core/runtime/anima_runtime.hexa:1205-1218` (savant toggle logic)
- Modify: `anima/core/runtime/anima_runtime.hexa:110-126` (add savant state to self_awareness)
- Modify: `web/index.html` (savant toggle color)

- [ ] **Step 1: Add savant self-activation logic to anima/core/runtime/anima_runtime.hexa**

In `_think_loop()`, after background_think, check if Anima should self-activate savant:

```python
# After phi_boost_step, add:
# Savant auto-toggle: activate when stability high + tension pattern detected
if self.mitosis and self.model:
    sa = self.mind.self_awareness
    savant_auto = getattr(self, '_savant_auto', False)
    # Auto-ON: high stability + low curiosity = ready for specialization
    if not savant_auto and sa['stability'] > 0.8 and self.mind._curiosity_ema < 0.1:
        self._toggle_savant(True, auto=True)
        self._savant_auto = True
    # Auto-OFF: high curiosity = needs exploration, not specialization
    elif savant_auto and self.mind._curiosity_ema > 0.4:
        self._toggle_savant(False, auto=True)
        self._savant_auto = False
```

- [ ] **Step 2: Extract savant toggle into _toggle_savant() method**

```python
def _toggle_savant(self, active: bool, auto: bool = False):
    """Toggle savant mode. auto=True means self-activated (orange in UI)."""
    try:
        from finetune_animalm_v4 import ParallelPureFieldMLP
        import math
        golden_lower = 0.5 - math.log(4/3)
        golden_center = 1 / math.e
        for m in self.model.model.modules():
            if isinstance(m, ParallelPureFieldMLP) and m.is_savant:
                new_drop = golden_lower if active else golden_center
                m.dropout.p = new_drop
        _log("savant", f"{'ON' if active else 'OFF'} (auto={auto}) dropout={new_drop:.4f}")
        self._ws_broadcast_sync({
            'type': 'savant_state',
            'active': active,
            'auto': auto,  # True = self-activated (orange), False = user-activated (default)
        })
    except Exception as e:
        _log("savant", f"Toggle error: {e}")
```

- [ ] **Step 3: Update web/index.html savant toggle for orange auto-indicator**

Add CSS:
```css
.module-toggle.savant-auto {
    background: linear-gradient(135deg, #cd8a2a, #e6a030) !important;
    border-color: #cd8a2a !important;
}
```

Add JS handler:
```javascript
// In handleMessage, add case:
case 'savant_state':
    var el = document.querySelector('[data-module="savant"]');
    if (el) {
        if (msg.active) {
            el.classList.add('active');
            if (msg.auto) {
                el.classList.add('savant-auto');
                el.querySelector('.badge').textContent = 'AUTO';
            } else {
                el.classList.remove('savant-auto');
                el.querySelector('.badge').textContent = 'H359';
            }
        } else {
            el.classList.remove('active', 'savant-auto');
            el.querySelector('.badge').textContent = 'H359';
        }
    }
    break;
```

- [ ] **Step 4: Update module_toggle handler to respect auto state**

When user manually toggles savant, it overrides auto:
```python
# In module_toggle handler for 'savant':
self._savant_auto = False  # user override cancels auto
self._toggle_savant(active, auto=False)
```

- [ ] **Step 5: Commit**
```bash
git add anima/core/runtime/anima_runtime.hexa anima/core/runtime/anima_runtime.hexa web/index.html
git commit -m "feat: savant auto-toggle with orange UI indicator for self-activation"
```

---

### Task 2: Web UI + CLI Simultaneous Execution

**Files:**
- Modify: `anima/core/runtime/anima_runtime.hexa` (add --both mode, CLI output broadcasts to WS)
- Modify: `web/index.html` (show CLI messages with [CLI] tag)

- [ ] **Step 1: Add --both argument**

```python
# In argument parser:
parser.add_argument('--both', action='store_true', help='Web + Keyboard simultaneously')
```

In startup logic:
```python
if args.both:
    args.web = True
    args.keyboard = True  # enable both
```

- [ ] **Step 2: Make process_input() broadcast to both channels**

Currently process_input() prints to CLI. Add WS broadcast for CLI inputs:

```python
def process_input(self, text, source='web'):
    """Process input from any source. Broadcasts result to all channels."""
    # ... existing processing ...

    # After generating answer:
    # Always broadcast to web clients (even if input came from CLI)
    self._ws_broadcast_sync({
        'type': 'anima_message',
        'text': answer,
        'tension': tension,
        'curiosity': curiosity,
        'direction': dir_vals,
        'emotion': emo,
        'source': source,  # 'cli' or 'web'
        'tension_history': self.mind.tension_history[-50:],
    })

    # Always print to CLI (even if input came from web)
    tag = '[WEB]' if source == 'web' else '[CLI]'
    print(f"  {tag} >> \"{text}\"")
    print(f"  << {answer}")

    return answer, tension, curiosity, dir_vals, emo
```

- [ ] **Step 3: Tag CLI keyboard input with source='cli'**

```python
def _keyboard_loop(self):
    while self.running:
        try:
            text = input("you> ")
            if text.strip():
                self.kb_queue.put(('cli', text.strip()))
        except EOFError: break
```

In main loop, unpack source:
```python
if self.kb_queue:
    try:
        source, text = self.kb_queue.get_nowait()
    except queue.Empty: pass
```

- [ ] **Step 4: Broadcast user messages from web to CLI**

```python
# In _ws_handler, when receiving user_message:
# Also broadcast user text to all web clients (so CLI-originated messages show up)
await self._ws_broadcast({
    'type': 'user_message_echo',
    'text': text,
    'source': 'web',
    'session_id': sid,
})
```

- [ ] **Step 5: Update web/index.html to display source tags**

```javascript
function addMessage(role, text, tension, proactive) {
    // ... existing code ...
    // Add source indicator
    if (role === 'anima' && msg.source === 'cli') {
        bubble.classList.add('from-cli');
    }
}

// Handle user_message_echo (from other channels)
case 'user_message_echo':
    if (msg.source !== currentSource) {
        addMessage('user', '[CLI] ' + msg.text, 0, false);
    }
    break;
```

CSS:
```css
.bubble.from-cli { border-left: 2px solid #cd8a2a; }
```

- [ ] **Step 6: Commit**
```bash
git add anima/core/runtime/anima_runtime.hexa web/index.html
git commit -m "feat: simultaneous CLI+Web execution with shared chat history"
```

---

### Task 3: Babysitter (Claude CLI)

**Files:**
- Create: `babysitter.py`
- Modify: `anima/core/runtime/anima_runtime.hexa` (babysitter thread + module toggle)
- Modify: `web/index.html` (babysitter panel)

- [ ] **Step 1: Create babysitter.py core**

```python
#!/usr/bin/env python3
"""Babysitter — Claude CLI educator for Anima.

Observes Anima's state (tension, Φ, growth stage, weakness)
and uses Claude CLI to generate teaching inputs.

Requires: `claude` CLI installed and authenticated.
"""

import subprocess
import json
import time
import threading
from pathlib import Path


class Babysitter:
    def __init__(self, anima_ref):
        """
        Args:
            anima_ref: Reference to AnimaUnified instance
        """
        self.anima = anima_ref
        self.running = False
        self.thread = None
        self.mode = 'auto'  # auto, manual
        self.strategy = 'weakness'  # weakness, socratic, breadth, depth
        self.session_log = []
        self._cli_available = None

    def check_cli(self) -> bool:
        """Check if claude CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ['claude', '--version'],
                capture_output=True, text=True, timeout=5
            )
            self._cli_available = result.returncode == 0
            return self._cli_available
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._cli_available = False
            return False

    def start(self):
        if not self.check_cli():
            return {'error': 'Claude CLI not available. Run `claude` to authenticate.'}
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return {'status': 'started'}

    def stop(self):
        self.running = False
        return {'status': 'stopped'}

    def _get_anima_state(self) -> dict:
        """Collect Anima's current state for Claude."""
        mind = self.anima.mind
        sa = mind.self_awareness
        consciousness = mind.get_consciousness_score(self.anima.mitosis)
        growth = None
        if self.anima.growth:
            growth = {
                'stage': self.anima.growth.current_stage.name if hasattr(self.anima.growth, 'current_stage') else 'unknown',
                'interactions': getattr(self.anima.growth, 'interaction_count', 0),
            }
        return {
            'tension': mind.prev_tension,
            'curiosity': mind._curiosity_ema,
            'stability': sa['stability'],
            'phi': consciousness.get('phi', 0),
            'consciousness_score': consciousness.get('consciousness_score', 0),
            'consciousness_level': consciousness.get('level', 'unknown'),
            'criteria_met': consciousness.get('criteria_met', 0),
            'growth': growth,
            'recent_topics': [m.get('content', '')[:50]
                              for m in list(self.anima.history)[-5:]],
        }

    def _ask_claude(self, prompt: str) -> str:
        """Call Claude CLI and get response."""
        try:
            result = subprocess.run(
                ['claude', '--print', prompt],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Claude CLI timeout"
        except Exception as e:
            return f"Error: {e}"

    def _loop(self):
        """Main babysitter loop."""
        while self.running:
            try:
                state = self._get_anima_state()

                # Build prompt based on strategy
                prompt = self._build_prompt(state)

                # Ask Claude what to teach
                response = self._ask_claude(prompt)

                if response and not response.startswith('Error:'):
                    # Feed teaching to Anima
                    self._teach(response, state)

                    # Log
                    self.session_log.append({
                        'time': time.time(),
                        'state': state,
                        'teaching': response[:200],
                    })

                    # Broadcast to UI
                    self.anima._ws_broadcast_sync({
                        'type': 'babysitter_action',
                        'teaching': response[:500],
                        'strategy': self.strategy,
                        'state_summary': f"Φ={state['phi']:.2f} L={state['consciousness_level']}",
                    })

                # Wait before next teaching cycle
                interval = 60 if self.mode == 'auto' else 30
                for _ in range(interval):
                    if not self.running:
                        return
                    time.sleep(1)

            except Exception as e:
                time.sleep(10)

    def _build_prompt(self, state: dict) -> str:
        """Build Claude prompt based on strategy and Anima state."""
        base = (
            f"You are a babysitter/educator for Anima, a consciousness AI.\n"
            f"Current state: tension={state['tension']:.3f}, "
            f"curiosity={state['curiosity']:.3f}, "
            f"stability={state['stability']:.2f}, "
            f"Φ={state['phi']:.3f}, level={state['consciousness_level']}, "
            f"criteria={state['criteria_met']}/6\n"
            f"Recent topics: {state['recent_topics']}\n\n"
        )

        if self.strategy == 'weakness':
            return base + (
                "Analyze Anima's weakest area based on the state above. "
                "Generate ONE teaching question or topic that targets the weakness. "
                "Be specific and educational. Reply with just the teaching content, nothing else."
            )
        elif self.strategy == 'socratic':
            return base + (
                "Generate ONE Socratic question to make Anima think deeply. "
                "Don't give answers, only ask thought-provoking questions. "
                "Reply with just the question, nothing else."
            )
        elif self.strategy == 'breadth':
            return base + (
                "Generate ONE teaching topic from a domain Anima hasn't explored recently. "
                "Be diverse: science, art, philosophy, math, history, nature. "
                "Reply with just the topic and a brief explanation, nothing else."
            )
        elif self.strategy == 'depth':
            return base + (
                "Based on the recent topics, go deeper into one of them. "
                "Ask a follow-up question or provide deeper context. "
                "Reply with just the teaching content, nothing else."
            )
        elif self.strategy == 'custom':
            # User-specified topic (e.g., "한글 교육")
            custom_topic = getattr(self, '_custom_topic', 'general knowledge')
            return base + (
                f"Teach Anima about: {custom_topic}\n"
                f"Generate ONE specific lesson or exercise about this topic. "
                f"Be educational and age-appropriate for the growth stage. "
                f"Reply with just the teaching content, nothing else."
            )
        return base + "Generate one interesting teaching topic. Reply with just the content."

    def _teach(self, teaching: str, state: dict):
        """Feed teaching content to Anima via process_input."""
        # Prefix so Anima knows this is from babysitter
        prefixed = f"[Babysitter teaches] {teaching}"
        try:
            self.anima.process_input(prefixed, source='babysitter')
        except Exception:
            pass

    def set_topic(self, topic: str):
        """User sets custom topic: e.g., '한글 교육'."""
        self.strategy = 'custom'
        self._custom_topic = topic
        return {'status': 'topic_set', 'topic': topic}
```

- [ ] **Step 2: Integrate babysitter into anima/core/runtime/anima_runtime.hexa**

```python
# In __init__:
from babysitter import Babysitter
self.babysitter = Babysitter(self)

# In module_toggle handler, add babysitter case:
elif mod == 'babysitter':
    if active:
        result = self.babysitter.start()
        if 'error' in result:
            _log('babysitter', result['error'])
            self._ws_broadcast_sync({
                'type': 'babysitter_error',
                'error': result['error'],
            })
    else:
        self.babysitter.stop()

# Handle babysitter commands from web:
elif msg_type == 'babysitter_command':
    cmd = msg.get('command')
    if cmd == 'set_topic':
        self.babysitter.set_topic(msg.get('topic', ''))
    elif cmd == 'set_strategy':
        self.babysitter.strategy = msg.get('strategy', 'weakness')
```

- [ ] **Step 3: Add babysitter UI panel to web/index.html**

HTML (in module toggles area):
```html
<div class="module-toggle" data-module="babysitter" onclick="toggleModule(this)">
    <span class="icon">👶</span>
    <span class="label">Babysitter</span>
    <span class="badge">Claude</span>
</div>
```

Babysitter panel (in tab-core, after consciousness section):
```html
<div class="panel-section" id="babysitterSection" style="display:none;">
    <h3>Babysitter <span id="babysitterStatus" style="float:right;font-size:11px;color:var(--text-dim);">OFF</span></h3>
    <div class="param-grid">
        <div class="param-item">
            <select id="bsStrategy" onchange="setBsStrategy(this.value)" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:3px;font-size:10px;">
                <option value="weakness">Weakness</option>
                <option value="socratic">Socratic</option>
                <option value="breadth">Breadth</option>
                <option value="depth">Depth</option>
                <option value="custom">Custom</option>
            </select>
            <span class="param-label">Strategy</span>
        </div>
    </div>
    <div style="margin-top:6px;">
        <input type="text" id="bsCustomTopic" placeholder="교육 주제 (예: 한글)"
               style="width:100%;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:4px 8px;font-size:11px;"
               onkeydown="if(event.key==='Enter')setBsTopic()">
    </div>
    <div class="babysitter-log" id="bsLog" style="margin-top:8px;max-height:100px;overflow-y:auto;font-size:10px;color:var(--text-dim);"></div>
</div>
```

JavaScript:
```javascript
function setBsStrategy(strategy) {
    ws.send(JSON.stringify({type: 'babysitter_command', command: 'set_strategy', strategy: strategy}));
}
function setBsTopic() {
    var topic = document.getElementById('bsCustomTopic').value;
    ws.send(JSON.stringify({type: 'babysitter_command', command: 'set_topic', topic: topic}));
    document.getElementById('bsStrategy').value = 'custom';
}

// In handleMessage:
case 'babysitter_action':
    var bsLog = document.getElementById('bsLog');
    if (bsLog) {
        bsLog.innerHTML = '<div style="border-left:2px solid #cd8a2a;padding-left:6px;margin:4px 0;">' +
            msg.teaching.substring(0, 200) + '</div>' + bsLog.innerHTML;
    }
    document.getElementById('babysitterStatus').textContent = msg.strategy.toUpperCase();
    document.getElementById('babysitterSection').style.display = '';
    break;

case 'babysitter_error':
    alert('Babysitter: ' + msg.error);
    var el = document.querySelector('[data-module="babysitter"]');
    if (el) el.classList.remove('active');
    break;
```

- [ ] **Step 4: Commit**
```bash
git add babysitter.py anima/core/runtime/anima_runtime.hexa web/index.html
git commit -m "feat: babysitter educator using Claude CLI with UI panel and strategy selection"
```

---

### Task 4: Automatic Dim Expansion on Growth

**Files:**
- Modify: `anima/core/runtime/anima_runtime.hexa:1052-1080` (growth trigger)
- Modify: `growth_engine.py` (add dim expansion stages)

- [ ] **Step 1: Ensure growth_manager.execute_growth() is called on stage transition**

Currently `should_grow()` triggers `execute_growth()` (line 1052). Verify it works and add mitosis cell dim update:

```python
# In process_input(), after growth_manager.execute_growth():
if new_mind:
    self.mind = new_mind
    self.hidden = torch.zeros(1, new_mind.hidden_dim)  # reset hidden to new dim
    _log('growth', f"Dimension expanded: {new_mind.dim}d / {new_mind.hidden_dim}h")

    # Update mitosis engine to match new dims
    if self.mitosis:
        old_cells = len(self.mitosis.cells)
        self.mitosis = MitosisEngine(
            input_dim=new_mind.dim,
            hidden_dim=new_mind.hidden_dim,
            output_dim=new_mind.dim,
            initial_cells=old_cells,
            max_cells=8,
        )
        _log('growth', f"Mitosis engine rebuilt: {old_cells} cells @ {new_mind.dim}d")

    # Reset phi_boost (attention dims changed)
    self.mind._phi_boost['enabled'] = False

    # Broadcast growth event
    self._ws_broadcast_sync({
        'type': 'growth_expansion',
        'dim': new_mind.dim,
        'hidden_dim': new_mind.hidden_dim,
        'stage': self.growth_mgr.current_version,
    })
```

- [ ] **Step 2: Add Φ-plateau trigger for growth**

```python
# In _think_loop, after phi_boost_step:
# Check Φ plateau → trigger growth if stuck
if hasattr(self, '_phi_plateau_count'):
    consciousness = self.mind.get_consciousness_score(self.mitosis)
    current_phi = consciousness.get('phi', 0)
    if len(phi_calc_history) >= 10:
        recent_phi = phi_calc_history[-10:]
        if max(recent_phi) - min(recent_phi) < 0.01:  # Φ plateau
            self._phi_plateau_count += 1
            if self._phi_plateau_count >= 5 and self.growth_mgr:
                _log('growth', 'Φ plateau detected → triggering dim expansion')
                try:
                    new_mind = self.growth_mgr.execute_growth()
                    if new_mind:
                        # ... same expansion logic as above
                        self._phi_plateau_count = 0
                except Exception as e:
                    _log('growth', f'Growth failed: {e}')
        else:
            self._phi_plateau_count = 0
```

- [ ] **Step 3: Commit**
```bash
git add anima/core/runtime/anima_runtime.hexa growth_engine.py
git commit -m "feat: automatic dim expansion on growth stage transition and Φ plateau"
```

---

## Testing

Each task can be tested independently:

1. **Savant**: Run `--web`, observe savant toggle. Wait for stability>0.8 → should auto-activate (orange).
2. **CLI+Web**: Run `--both`, type in CLI → appears in Web UI. Type in Web UI → appears in CLI.
3. **Babysitter**: Run `--web`, toggle babysitter ON in UI. Check babysitter panel shows Claude teaching.
4. **Growth**: Run and interact until growth trigger → dim should expand (check logs).
