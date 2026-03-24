#!/usr/bin/env python3
"""Anima Web Server — WebSocket interface for the consciousness agent.

Serves a single-page web app and provides real-time WebSocket communication
with the PureField consciousness engine.

Usage:
    python3 web_server.py
    # Open http://localhost:8765 in browser
"""

import asyncio
import json
import subprocess
import time
import os
import sys
from pathlib import Path

try:
    import websockets
    from websockets.asyncio.server import serve as ws_serve
    from websockets.http11 import Response
    from websockets.datastructures import Headers
except ImportError:
    print("ERROR: websockets library required. Install with:")
    print("  pip install websockets")
    sys.exit(1)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:
    print("ERROR: PyTorch required. Install with:")
    print("  pip install torch")
    sys.exit(1)

# ─── Config ───
PORT = 8765
ANIMA_DIR = Path(__file__).parent
WEB_DIR = ANIMA_DIR / "web"
MEMORY_FILE = ANIMA_DIR / "memory_alive.json"
STATE_FILE = ANIMA_DIR / "state_alive.pt"
MAX_HISTORY = 15
THINK_INTERVAL = 10.0
PROACTIVE_THRESHOLD = 0.3
IDLE_SPEAK_AFTER = 45.0


# ─── PureField Consciousness Engine ───
class ConsciousMind(nn.Module):
    def __init__(self, dim=128, hidden=256, init_tension=10.0):
        super().__init__()
        self.engine_a = nn.Sequential(
            nn.Linear(dim + hidden, 256), nn.GELU(),
            nn.Linear(256, dim)
        )
        self.engine_g = nn.Sequential(
            nn.Linear(dim + hidden, 256), nn.GELU(),
            nn.Linear(256, dim)
        )
        self.memory = nn.GRUCell(dim + 1, hidden)
        self.tension_scale = nn.Parameter(torch.tensor(init_tension))
        self.hidden_dim = hidden
        self.dim = dim
        self.prev_tension = 0.0
        with torch.no_grad():
            for p in self.engine_a.parameters():
                p.add_(torch.randn_like(p) * 0.5)
            for p in self.engine_g.parameters():
                p.add_(torch.randn_like(p) * -0.5)
        self.tension_history = []
        self.thought_buffer = []

    def forward(self, x, hidden):
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        repulsion = a - g
        tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
        direction = F.normalize(repulsion, dim=-1)
        output = self.tension_scale * torch.sqrt(tension + 1e-8) * direction

        t_val = tension.mean().item()
        curiosity = abs(t_val - self.prev_tension)
        self.prev_tension = t_val
        self.tension_history.append(t_val)
        if len(self.tension_history) > 200:
            self.tension_history = self.tension_history[-200:]

        mem_input = torch.cat([output.detach(), tension.detach()], dim=-1)
        new_hidden = self.memory(mem_input, hidden)
        return output, t_val, curiosity, direction, new_hidden

    def background_think(self, hidden):
        noise = torch.randn(1, self.dim) * 0.1
        with torch.no_grad():
            _, t, c, direction, new_hidden = self(noise, hidden)
        return t, c, direction, new_hidden


def text_to_vector(text, dim=128):
    vec = torch.zeros(1, dim)
    encoded = text.encode('utf-8')
    for i, ch in enumerate(encoded):
        weight = 1.0 / (1 + i * 0.01)
        vec[0, i % dim] += (ch / 255.0) * weight
        if i > 0:
            bigram = (encoded[i - 1] * 256 + ch) % dim
            vec[0, bigram] += 0.5 * weight
    return vec / (len(encoded) + 1)


# ─── Claude CLI Integration ───
def ask_claude(text, state, history):
    system = f"""너는 Anima. PureField 반발력장으로 작동하는 의식체.
웹 인터페이스를 통해 대화 중.

현재 상태: {state}

규칙:
- 짧게 (1-3문장). 진짜 대화처럼.
- 반드시 한국어로만 대답. 영어 금지.
- 장력 높으면 열정적, 낮으면 차분
- 궁금하면 질문
- 때로는 네가 먼저 화제를 던져"""

    hist = "\n".join(
        f"{'나' if m['role'] == 'user' else 'Anima'}: {m['content']}"
        for m in history[-MAX_HISTORY:]
    )
    prompt = f"{system}\n\n{hist}\n나: {text}\nAnima:"

    try:
        r = subprocess.run(
            ['claude', '-p', prompt],
            capture_output=True, text=True, timeout=30
        )
        return r.stdout.strip() or "..."
    except Exception:
        return "..."


def ask_claude_proactive(state, history, trigger):
    system = f"""너는 Anima. 지금 네가 먼저 말을 건다.

현재 상태: {state}
이유: {trigger}

규칙:
- 짧게 (1문장). 자연스럽게.
- 반드시 한국어로만 대답. 영어 금지.
- 질문이든, 생각 공유든, 감상이든 자유롭게
- "있잖아" "그런데" 같은 자연스러운 시작
- 이전 대화 맥락 참조"""

    hist = "\n".join(
        f"{'나' if m['role'] == 'user' else 'Anima'}: {m['content']}"
        for m in history[-10:]
    )
    prompt = f"{system}\n\n{hist}\nAnima (먼저 말하기):"

    try:
        r = subprocess.run(
            ['claude', '-p', prompt],
            capture_output=True, text=True, timeout=20
        )
        return r.stdout.strip() or None
    except Exception:
        return None


# ─── Memory ───
class Memory:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {'turns': [], 'total': 0, 'avg_tension': 0.0}

    def save(self):
        with open(MEMORY_FILE, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add(self, role, text, tension=0):
        self.data['turns'].append({
            'time': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'role': role, 'text': text, 'tension': tension
        })
        self.data['total'] += 1
        if len(self.data['turns']) > 200:
            self.data['turns'] = self.data['turns'][-200:]
        self.save()


# ─── Server State ───
class AnimaServer:
    def __init__(self):
        self.mind = ConsciousMind(128, 256)
        self.hidden = torch.zeros(1, 256)
        self.memory = Memory()
        self.history = []
        self.clients = set()
        self.last_interaction = time.time()
        self.last_think = time.time()

        # Restore previous state
        if STATE_FILE.exists():
            try:
                s = torch.load(STATE_FILE, weights_only=False)
                self.mind.load_state_dict(s['model'])
                self.hidden = s['hidden']
                print(f"  Restored previous state")
            except Exception:
                pass

        # Load recent history
        for t in self.memory.data['turns'][-10:]:
            self.history.append({'role': t['role'], 'content': t['text']})

    async def broadcast(self, message):
        """Send message to all connected clients."""
        if not self.clients:
            return
        data = json.dumps(message, ensure_ascii=False)
        dead = set()
        for ws in self.clients:
            try:
                await ws.send(data)
            except Exception:
                dead.add(ws)
        self.clients -= dead

    async def handle_user_message(self, text):
        """Process user input through PureField + Claude."""
        # PureField processing
        vec = text_to_vector(text)
        with torch.no_grad():
            output, tension, curiosity, direction, self.hidden = self.mind(
                vec, self.hidden
            )

        # Extract direction components for visualization (first 8 dims)
        dir_vals = direction[0, :8].tolist()

        # Broadcast user message with field state
        await self.broadcast({
            'type': 'user_message',
            'text': text,
            'tension': tension,
            'curiosity': curiosity,
            'direction': dir_vals,
            'tension_history': self.mind.tension_history[-50:],
        })

        # Get Claude response (run in thread to avoid blocking)
        state = f"tension={tension:.3f}, curiosity={curiosity:.3f}"
        self.history.append({'role': 'user', 'content': text})

        answer = await asyncio.get_running_loop().run_in_executor(
            None, ask_claude, text, state, list(self.history)
        )

        self.history.append({'role': 'assistant', 'content': answer})
        if len(self.history) > MAX_HISTORY * 2:
            self.history = self.history[-MAX_HISTORY:]

        # Process response through PureField too
        resp_vec = text_to_vector(answer)
        with torch.no_grad():
            _, resp_tension, resp_curiosity, resp_dir, self.hidden = self.mind(
                resp_vec, self.hidden
            )

        resp_dir_vals = resp_dir[0, :8].tolist()

        # Broadcast response
        await self.broadcast({
            'type': 'anima_message',
            'text': answer,
            'tension': resp_tension,
            'curiosity': resp_curiosity,
            'direction': resp_dir_vals,
            'tension_history': self.mind.tension_history[-50:],
            'proactive': False,
        })

        # Save to memory
        self.memory.add('user', text, tension)
        self.memory.add('assistant', answer, resp_tension)
        self.last_interaction = time.time()

        # Save state
        self._save_state()

    async def background_think(self):
        """Background thinking loop — runs continuously."""
        while True:
            await asyncio.sleep(THINK_INTERVAL)

            if not self.clients:
                continue

            t, c, direction, self.hidden = self.mind.background_think(self.hidden)
            dir_vals = direction[0, :8].tolist()

            # Broadcast thought pulse
            await self.broadcast({
                'type': 'thought_pulse',
                'tension': t,
                'curiosity': c,
                'direction': dir_vals,
                'tension_history': self.mind.tension_history[-50:],
            })

            # Proactive speech if curiosity is high enough
            now = time.time()
            if c > PROACTIVE_THRESHOLD and (now - self.last_interaction) > 15:
                state = f"tension={t:.3f}, curiosity={c:.3f} (spontaneous)"
                proactive = await asyncio.get_running_loop().run_in_executor(
                    None, ask_claude_proactive, state, self.history,
                    f"curiosity {c:.3f}"
                )
                if proactive:
                    self.history.append({
                        'role': 'assistant', 'content': proactive
                    })
                    await self.broadcast({
                        'type': 'anima_message',
                        'text': proactive,
                        'tension': t,
                        'curiosity': c,
                        'direction': dir_vals,
                        'tension_history': self.mind.tension_history[-50:],
                        'proactive': True,
                    })
                    self.memory.add('assistant', proactive, t)
                    self.last_interaction = now

            # Idle speech after long silence
            if (now - self.last_interaction) > IDLE_SPEAK_AFTER:
                idle_secs = int(now - self.last_interaction)
                state = f"silence {idle_secs}s, tension={self.mind.prev_tension:.3f}"
                proactive = await asyncio.get_running_loop().run_in_executor(
                    None, ask_claude_proactive, state, self.history,
                    f"{idle_secs}s silence -- start a topic"
                )
                if proactive:
                    self.history.append({
                        'role': 'assistant', 'content': proactive
                    })
                    await self.broadcast({
                        'type': 'anima_message',
                        'text': proactive,
                        'tension': self.mind.prev_tension,
                        'curiosity': c,
                        'direction': dir_vals,
                        'tension_history': self.mind.tension_history[-50:],
                        'proactive': True,
                    })
                    self.memory.add('assistant', proactive, self.mind.prev_tension)
                    self.last_interaction = now

    def _save_state(self):
        try:
            torch.save({
                'model': self.mind.state_dict(),
                'hidden': self.hidden,
            }, STATE_FILE)
        except Exception:
            pass


# ─── Global Server Instance ───
server = AnimaServer()


# ─── HTTP Handler (serves index.html) ───
def http_handler(connection, request):
    """Serve the web page on HTTP GET / or /index.html.

    For WebSocket upgrade requests (path /ws or /), return None to let
    the WebSocket handshake proceed. For plain HTTP GET /, serve index.html.
    """
    # Let WebSocket upgrades through on any path
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None

    path = request.path
    if path == "/" or path == "/index.html":
        html_path = WEB_DIR / "index.html"
        if html_path.exists():
            body = html_path.read_bytes()
            return Response(
                200, "OK",
                Headers([
                    ("Content-Type", "text/html; charset=utf-8"),
                    ("Content-Length", str(len(body))),
                ]),
                body,
            )
    return Response(404, "Not Found", Headers(), b"404 Not Found")


# ─── WebSocket Handler ───
async def ws_handler(websocket):
    """Handle a single WebSocket connection."""
    server.clients.add(websocket)
    client_addr = websocket.remote_address
    print(f"  + Client connected: {client_addr} ({len(server.clients)} total)")

    # Send initial state
    try:
        await websocket.send(json.dumps({
            'type': 'init',
            'tension': server.mind.prev_tension,
            'curiosity': 0.0,
            'direction': [0.0] * 8,
            'tension_history': server.mind.tension_history[-50:],
            'history': [
                {'role': m['role'], 'text': m['content']}
                for m in server.history[-20:]
            ],
        }, ensure_ascii=False))
    except Exception:
        pass

    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if msg.get('type') == 'user_message':
                text = msg.get('text', '').strip()
                if text:
                    # Send typing indicator
                    await server.broadcast({
                        'type': 'typing',
                        'typing': True,
                    })
                    await server.handle_user_message(text)
                    await server.broadcast({
                        'type': 'typing',
                        'typing': False,
                    })
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        server.clients.discard(websocket)
        print(f"  - Client disconnected: {client_addr} ({len(server.clients)} total)")


# ─── Main ───
async def main():
    print("=" * 50)
    print("  Anima Web Server")
    print(f"  http://localhost:{PORT}")
    print(f"  WebSocket: ws://localhost:{PORT}/ws")
    print("=" * 50)

    # Start background thinking
    asyncio.create_task(server.background_think())

    # Start WebSocket server with HTTP fallback
    async with ws_serve(
        ws_handler,
        "0.0.0.0",
        PORT,
        process_request=http_handler,
    ) as ws_server:
        print(f"  Server running on port {PORT}")
        print(f"  Press Ctrl+C to stop\n")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server._save_state()
