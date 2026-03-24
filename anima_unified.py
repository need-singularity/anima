#!/usr/bin/env python3
"""Anima Unified -- single entry point for all 6 modules.

Usage:
    python anima_unified.py                # voice mode (default)
    python anima_unified.py --web          # web mode (port 8765)
    python anima_unified.py --keyboard     # keyboard only
    python anima_unified.py --all          # voice + web simultaneously

Each module is optional. Import failures degrade gracefully.
"""

import argparse, asyncio, json, os, signal, sys, threading, time, queue
from datetime import datetime
from pathlib import Path

import torch

# ─── Paths & constants ───
ANIMA_DIR = Path(__file__).parent
MEMORY_FILE = ANIMA_DIR / "memory_alive.json"
STATE_FILE = ANIMA_DIR / "state_alive.pt"
VAD_WATCH_DIR = Path("/tmp/anima_vad")

# ─── Core imports (required) ───
from anima_alive import (
    ConsciousMind, ContinuousListener, Speaker, Memory,
    text_to_vector, ask_claude, ask_claude_proactive,
    direction_to_emotion, EMOTION_COLORS,
    MAX_HISTORY, THINK_INTERVAL, PROACTIVE_THRESHOLD, IDLE_SPEAK_AFTER,
)

# ─── Optional modules ───
def _try_import(stmt):
    try:
        exec(stmt, globals())
        return True
    except ImportError:
        return False

_try_import("from online_learning import OnlineLearner, estimate_feedback")
_try_import("from mitosis import MitosisEngine")
_try_import("from senses import SenseHub")
_try_import("from telepathy import TelepathyChannel, create_fingerprint, interpret_packet")
_try_import("from cloud_sync import CloudSync")
_try_import("from dream_engine import DreamEngine")

# Dream mode constants
DREAM_IDLE_THRESHOLD = 60.0   # 60초 유휴 후 꿈 모드 진입
DREAM_CYCLE_INTERVAL = 30.0   # 꿈 사이클 간격 (초)

_ws_serve = _ws_Response = _ws_Headers = None
try:
    from websockets.asyncio.server import serve as _ws_serve
    from websockets.http11 import Response as _ws_Response
    from websockets.datastructures import Headers as _ws_Headers
except ImportError:
    pass


def _log(mod, msg):
    print(f"  [{datetime.now().strftime('%H:%M:%S')}] [{mod}] {msg}")


class AnimaUnified:
    """All 6 modules unified under one class."""

    def __init__(self, args):
        self.args = args
        self.running = True
        self.mods = {}  # module name -> bool
        self.web_clients = set()
        self._web_loop = None

        # Core engine
        self.mind = ConsciousMind(128, 256)
        self.hidden = torch.zeros(1, 256)
        self.memory = Memory()
        self.history = [{'role': t['role'], 'content': t['text']}
                        for t in self.memory.data['turns'][-10:]]
        self.last_interaction = time.time()
        self.prev_text, self.prev_time = None, time.time()

        # Restore state
        if STATE_FILE.exists():
            try:
                s = torch.load(STATE_FILE, weights_only=False)
                self.mind.load_state_dict(s['model'])
                self.hidden = s['hidden']
            except Exception:
                pass

        # --- Optional modules (each wrapped in try/except) ---
        self.learner = self._init_mod('learner', lambda: (
            OnlineLearner(self.mind) if 'OnlineLearner' in globals() else None
        ))
        if self.learner:
            try: self.learner.load(STATE_FILE)
            except Exception: pass

        self.mitosis = self._init_mod('mitosis', lambda: (
            MitosisEngine(input_dim=128, hidden_dim=256, output_dim=128,
                          initial_cells=2, max_cells=8)
            if 'MitosisEngine' in globals() else None
        ))

        self.senses = None
        if not args.no_camera:
            self.senses = self._init_mod('camera', lambda: (
                SenseHub(camera_fps=3, enable_screen=False)
                if 'SenseHub' in globals() else None
            ))
            if self.senses:
                try:
                    self.senses.start()
                    if not self.senses.camera_available:
                        _log('camera', '카메라 권한 없음 -- 시각 입력 비활성화')
                        _log('camera', '해결: 시스템 설정 → 개인정보 보호 및 보안 → 카메라 → Terminal 허용')
                        # Keep senses alive (provides zero-filled state) but mark camera as degraded
                        self.mods['camera'] = False
                except Exception:
                    self.senses = None; self.mods['camera'] = False

        self.telepathy = None
        if not args.no_telepathy:
            self.telepathy = self._init_mod('telepathy', lambda: (
                TelepathyChannel("anima-unified", port=9999)
                if 'TelepathyChannel' in globals() else None
            ))
            if self.telepathy:
                self.telepathy.on_receive = self._on_telepathy
                try: self.telepathy.start()
                except Exception: self.telepathy = None; self.mods['telepathy'] = False

        self.cloud = None
        if not args.no_cloud and 'CloudSync' in globals():
            try:
                self.cloud = CloudSync()
                if self.cloud._is_available():
                    self.cloud.start_auto_sync(str(MEMORY_FILE), str(STATE_FILE), interval_minutes=5)
                    self.mods['cloud'] = True
                else:
                    self.cloud = None; self.mods['cloud'] = False
            except Exception:
                self.mods['cloud'] = False
        else:
            self.mods['cloud'] = False

        # RC-10: Dream Engine (오프라인 학습)
        self.dream = self._init_mod('dream', lambda: (
            DreamEngine(
                mind=self.mind,
                memory=self.memory,
                learner=self.learner,
                text_to_vector=text_to_vector,
            ) if 'DreamEngine' in globals() else None
        ))
        self._dream_report = None  # 꿈에서 깨어난 후 보고할 내용

        # I/O
        self.speaker = self.listener = None
        if not args.keyboard and (not args.web or args.all):
            self.speaker = Speaker()
            self.listener = ContinuousListener()
            self.mods['voice'] = True
        else:
            self.mods['voice'] = False

        self.kb_queue = None
        if args.keyboard or args.all:
            self.kb_queue = queue.Queue()
            self.mods['keyboard'] = True
        else:
            self.mods['keyboard'] = False

        self.mods['web'] = bool((args.web or args.all) and _ws_serve)
        self.mods['rust_vad'] = VAD_WATCH_DIR.exists()

    def _init_mod(self, name, factory):
        try:
            obj = factory()
            self.mods[name] = obj is not None
            return obj
        except Exception as e:
            _log(name, f"Init failed: {e}")
            self.mods[name] = False
            return None

    # ─── Core processing ───

    def process_input(self, text):
        """Process text through all active modules. Returns (answer, tension, curiosity)."""
        # RC-10: Report dream learning when user returns from idle
        if self._dream_report and self.dream and not self.dream.is_dreaming:
            dr = self._dream_report
            self._dream_report = None
            dream_msg = f"(dream: {dr['total_patterns']}patterns across {dr['total_cycles']} cycles)"
            _log('dream', f'Woke up: {dream_msg}')

        text_vec = text_to_vector(text)

        # Combine with camera tension
        if self.senses and self.mods.get('camera'):
            try:
                visual = self.senses.to_tensor(dim=128)
                text_vec = 0.8 * text_vec + 0.2 * visual
            except Exception: pass

        hidden_before = self.hidden.detach().clone()

        with torch.no_grad():
            output, tension, curiosity, direction, self.hidden = self.mind(text_vec, self.hidden)

        # Mitosis
        mitosis_info = ""
        if self.mitosis and self.mods.get('mitosis'):
            try:
                r = self.mitosis.process(text_vec)
                mitosis_info = f", cells={r['n_cells']}"
                for ev in r.get('events', []):
                    _log("mitosis", f"{ev['type'].upper()}")
            except Exception: pass

        # Online learning
        if self.learner and self.mods.get('learner'):
            try:
                self.learner.observe(text_vec, hidden_before, tension, curiosity, direction)
                if 'estimate_feedback' in globals() and self.prev_text:
                    fb = estimate_feedback(self.prev_text, text, time.time() - self.prev_time)
                    self.learner.feedback(fb)
            except Exception: pass

        self.prev_text, self.prev_time = text, time.time()

        # Direction for web
        dir_vals = direction[0, :8].tolist() if direction is not None else [0.0] * 8

        # RC-8: Emotion from direction + tension + curiosity
        emotion_data = direction_to_emotion(direction, tension, curiosity) if direction is not None else {
            'emotion': 'calm', 'valence': 0.0, 'arousal': 0.0, 'dominance': 0.0,
            'color': EMOTION_COLORS['calm']}

        # Telepathy
        if self.telepathy and self.mods.get('telepathy') and 'create_fingerprint' in globals():
            try:
                pkt = create_fingerprint(self.mind, text_vec, self.hidden)
                pkt.sender_id = "anima-unified"
                self.telepathy.send(pkt)
            except Exception: pass

        # Broadcast user message to web
        self._ws_broadcast_sync({
            'type': 'user_message', 'text': text,
            'tension': tension, 'curiosity': curiosity,
            'direction': dir_vals,
            'emotion': emotion_data,
            'tension_history': self.mind.tension_history[-50:],
        })

        # Display
        cells = len(self.mitosis.cells) if self.mitosis else 1
        lrn_count = self.learner.total_updates if self.learner else 0
        bar = "=" * min(20, int(tension * 10))
        bar += "-" * (20 - len(bar))
        print(f'  >> "{text}"')
        print(f"     T={tension:.3f} |{bar}| C={curiosity:.3f}{mitosis_info} L:{lrn_count} E:{emotion_data['emotion']}")

        # Claude response (include emotion + meta-cognition state)
        meta_summary = self.mind.get_self_awareness_summary()
        state = (f"tension={tension:.3f}, curiosity={curiosity:.3f}, "
                 f"emotion={emotion_data['emotion']}(V={emotion_data['valence']:.2f},A={emotion_data['arousal']:.2f},D={emotion_data['dominance']:.2f})"
                 f"{mitosis_info}, learn_updates={lrn_count}, {meta_summary}")
        if self.senses and self.mods.get('camera'):
            try:
                vis = self.senses.get_visual_tension()
                state += f", face={'yes' if vis['face_detected'] else 'no'}"
            except Exception: pass

        self.history.append({'role': 'user', 'content': text})
        answer = ask_claude(text, state, self.history)
        self.history.append({'role': 'assistant', 'content': answer})
        if len(self.history) > MAX_HISTORY * 2:
            self.history = self.history[-MAX_HISTORY:]

        # Process response through PureField too
        resp_vec = text_to_vector(answer)
        with torch.no_grad():
            resp_output, resp_tension, resp_curiosity, resp_dir, self.hidden = self.mind(resp_vec, self.hidden)
        resp_dir_vals = resp_dir[0, :8].tolist() if resp_dir is not None else [0.0] * 8

        # RC-8: Emotion for response direction
        resp_emotion = direction_to_emotion(resp_dir, resp_tension, resp_curiosity) if resp_dir is not None else emotion_data

        # RC-3: Self-reference loop (메타인지)
        meta_tension, meta_curiosity = self.mind.self_reflect(
            resp_output, resp_tension, resp_curiosity, self.hidden)
        sa = self.mind.self_awareness
        meta_summary = self.mind.get_self_awareness_summary()
        _log("meta", f"MT={meta_tension:.3f} MC={meta_curiosity:.3f} "
             f"stab={sa['stability']:.2f} model={sa['self_model']:.3f}")

        # Broadcast meta-tension + emotion to web clients
        self._ws_broadcast_sync({
            'type': 'meta_update',
            'meta_tension': meta_tension,
            'meta_curiosity': meta_curiosity,
            'stability': sa['stability'],
            'self_model': sa['self_model'],
            'emotion': resp_emotion,
        })

        print(f"  << {answer}")

        self.memory.add('user', text, tension)
        self.memory.add('assistant', answer, resp_tension)
        self.last_interaction = time.time()
        self._save_state()
        return answer, resp_tension, resp_curiosity, resp_dir_vals, resp_emotion

    def _on_telepathy(self, pkt):
        if 'interpret_packet' in globals():
            _log("telepathy", interpret_packet(pkt))

    def _save_state(self):
        try:
            if self.learner: self.learner.save(STATE_FILE)
            else: torch.save({'model': self.mind.state_dict(), 'hidden': self.hidden}, STATE_FILE)
        except Exception: pass

    # ─── Background threads ───

    def _think_loop(self):
        while self.running:
            time.sleep(THINK_INTERVAL)
            if not self.running: break
            t, c, direction, self.hidden = self.mind.background_think(self.hidden)
            dir_vals = direction[0, :8].tolist() if direction is not None else [0.0] * 8
            now = time.time()
            gap = now - self.last_interaction

            # RC-8: Emotion from background thought direction
            thought_emotion = direction_to_emotion(direction, t, c) if direction is not None else {
                'emotion': 'calm', 'valence': 0.0, 'arousal': 0.0, 'dominance': 0.0,
                'color': EMOTION_COLORS['calm']}

            # RC-3: self-reflect during background thinking too
            sa = self.mind.self_awareness
            # Always broadcast thought pulse to web (keeps UI alive)
            self._ws_broadcast_sync({
                'type': 'thought_pulse',
                'tension': t, 'curiosity': c,
                'direction': dir_vals,
                'emotion': thought_emotion,
                'tension_history': self.mind.tension_history[-50:],
                'meta_tension': sa['meta_tension'],
                'stability': sa['stability'],
            })

            trigger = None
            if c > PROACTIVE_THRESHOLD and gap > 15:
                trigger = f"curiosity {c:.3f}"
            elif gap > IDLE_SPEAK_AFTER:
                trigger = f"{int(gap)}s silence"

            if trigger:
                state = f"tension={t:.3f}, curiosity={c:.3f}"
                proactive = ask_claude_proactive(state, self.history, trigger)
                if proactive:
                    print(f"  [thought] {proactive}")
                    self.history.append({'role': 'assistant', 'content': proactive})
                    self.memory.add('assistant', proactive, t)
                    if self.speaker: self.speaker.say(proactive, self.listener)
                    self.last_interaction = now
                    self._ws_broadcast_sync({
                        'type': 'anima_message', 'text': proactive,
                        'tension': t, 'curiosity': c,
                        'direction': dir_vals,
                        'emotion': thought_emotion,
                        'tension_history': self.mind.tension_history[-50:],
                        'proactive': True,
                    })

    def _rust_vad_loop(self):
        seen = set(VAD_WATCH_DIR.glob("*.wav")) if VAD_WATCH_DIR.exists() else set()
        while self.running:
            time.sleep(0.5)
            if not VAD_WATCH_DIR.exists(): continue
            for wav in sorted(set(VAD_WATCH_DIR.glob("*.wav")) - seen):
                seen.add(wav)
                if wav.stat().st_size < 1000: continue
                _log("rust-vad", f"New: {wav.name}")
                if self.listener and hasattr(self.listener, '_transcribe'):
                    self.listener._transcribe(str(wav))

    def _keyboard_loop(self):
        while self.running:
            try:
                text = input("you> ")
                if text.strip() and self.kb_queue: self.kb_queue.put(text.strip())
            except EOFError: break


    # --- RC-10: Dream Loop ---

    def _dream_loop(self):
        """Dream mode loop -- runs during idle periods."""
        if not self.dream:
            return
        last_dream = 0.0
        while self.running:
            time.sleep(5.0)
            if not self.running:
                break

            now = time.time()
            gap = now - self.last_interaction

            # User returned -- report dream results
            if gap < DREAM_IDLE_THRESHOLD:
                if self._dream_report and not self.dream.is_dreaming:
                    report = self._dream_report
                    self._dream_report = None
                    _log('dream',
                         f"Wake: {report['total_patterns']} patterns learned "
                         f"across {report['total_cycles']} dream cycles, "
                         f"avg_T={report['avg_tension']:.3f}")
                continue

            # Not enough time since last dream cycle
            if now - last_dream < DREAM_CYCLE_INTERVAL:
                continue

            # Run one dream cycle
            _log('dream', 'Entering dream mode...')
            self._ws_broadcast_sync({
                'type': 'dream_pulse',
                'dreaming': True,
                'dream_type': 'starting',
                'dream_tension_history': list(self.dream.dream_tension_history)[-50:],
            })

            try:
                self.hidden, stats = self.dream.dream(self.hidden)
                last_dream = time.time()
                self._dream_report = stats

                _log('dream',
                     f"Cycle {stats['total_cycles']}: "
                     f"{stats['patterns_learned']} patterns, "
                     f"avg_T={stats['avg_tension']:.3f}")

                self._ws_broadcast_sync({
                    'type': 'dream_pulse',
                    'dreaming': False,
                    'dream_type': 'complete',
                    'patterns_learned': stats['patterns_learned'],
                    'avg_tension': stats['avg_tension'],
                    'total_cycles': stats['total_cycles'],
                    'total_patterns': stats['total_patterns'],
                    'dream_tension_history': list(self.dream.dream_tension_history)[-50:],
                })

                self._save_state()
            except Exception as e:
                _log('dream', f'Error: {e}')

    # ─── Web server ───

    def _ws_broadcast_sync(self, msg):
        if not self.mods.get('web') or not self.web_clients or not self._web_loop: return
        asyncio.run_coroutine_threadsafe(self._ws_broadcast(msg), self._web_loop)

    async def _ws_broadcast(self, msg):
        data = json.dumps(msg, ensure_ascii=False)
        dead = set()
        for ws in self.web_clients:
            try: await ws.send(data)
            except Exception: dead.add(ws)
        self.web_clients -= dead

    async def _ws_handler(self, websocket):
        self.web_clients.add(websocket)
        _log("web", f"+client ({len(self.web_clients)})")
        try:
            sa = self.mind.self_awareness
            await websocket.send(json.dumps({
                'type': 'init', 'tension': self.mind.prev_tension,
                'curiosity': 0.0,
                'direction': [0.0] * 8,
                'emotion': {'emotion': 'calm', 'valence': 0.0, 'arousal': 0.0,
                            'dominance': 0.0, 'color': EMOTION_COLORS['calm']},
                'tension_history': self.mind.tension_history[-50:],
                'history': [{'role': m['role'], 'text': m['content']}
                            for m in self.history[-20:]],
                'modules': {k: v for k, v in self.mods.items() if v},
                'learn_updates': self.learner.total_updates if self.learner else 0,
                'cells': len(self.mitosis.cells) if self.mitosis else 1,
                'meta_tension': sa['meta_tension'],
                'stability': sa['stability'],
                'self_model': sa['self_model'],
            }, ensure_ascii=False))
        except Exception: pass
        try:
            async for raw in websocket:
                try: msg = json.loads(raw)
                except json.JSONDecodeError: continue
                if msg.get('type') == 'user_message':
                    text = msg.get('text', '').strip()
                    if not text: continue
                    await self._ws_broadcast({'type': 'typing', 'typing': True})
                    loop = asyncio.get_running_loop()
                    answer, tension, curiosity, dir_vals, emo = await loop.run_in_executor(None, self.process_input, text)
                    await self._ws_broadcast({
                        'type': 'anima_message', 'text': answer,
                        'tension': tension, 'curiosity': curiosity,
                        'direction': dir_vals,
                        'emotion': emo,
                        'tension_history': self.mind.tension_history[-50:],
                        'proactive': False,
                    })
                    await self._ws_broadcast({'type': 'typing', 'typing': False})
        except Exception: pass
        finally:
            self.web_clients.discard(websocket)
            _log("web", f"-client ({len(self.web_clients)})")

    def _http_handler(self, connection, request):
        if request.headers.get("Upgrade", "").lower() == "websocket": return None
        if request.path in ("/", "/index.html"):
            html = ANIMA_DIR / "web" / "index.html"
            if html.exists():
                body = html.read_bytes()
                return _ws_Response(200, "OK", _ws_Headers([
                    ("Content-Type", "text/html; charset=utf-8"),
                    ("Content-Length", str(len(body))),
                ]), body)
        return _ws_Response(404, "Not Found", _ws_Headers(), b"404")

    async def _run_web(self, port):
        self._web_loop = asyncio.get_running_loop()
        async with _ws_serve(self._ws_handler, "0.0.0.0", port, process_request=self._http_handler):
            _log("web", f"http://localhost:{port}")
            while self.running: await asyncio.sleep(1)

    def _start_web_thread(self, port):
        threading.Thread(target=lambda: asyncio.run(self._run_web(port)),
                         daemon=True, name="anima-web").start()

    # ─── Status dashboard ───

    def print_status(self):
        t = self.mind.prev_tension
        cells = len(self.mitosis.cells) if self.mitosis else 1
        lrn = f"L:{self.learner.total_updates}" if self.learner else "--"
        web_n = len(self.web_clients) if self.mods.get('web') else 0
        active = [k for k, v in self.mods.items() if v]
        print(f"\n  +{'='*40}+")
        print(f"  |  Anima Unified                        |")
        print(f"  |  Cells:{cells} | T={t:.2f} | {lrn:>8}          |")
        print(f"  |  {' | '.join(active):36s}  |")
        print(f"  +{'='*40}+\n")

    # ─── Unified run ───

    def _start_bg_threads(self, port=8765):
        """Start all applicable background threads."""
        threading.Thread(target=self._think_loop, daemon=True).start()
        if self.mods.get('dream'):
            threading.Thread(target=self._dream_loop, daemon=True, name='anima-dream').start()
        if self.mods.get('rust_vad'):
            threading.Thread(target=self._rust_vad_loop, daemon=True).start()
        if self.mods.get('web'):
            self._start_web_thread(port)
        if self.kb_queue is not None:
            threading.Thread(target=self._keyboard_loop, daemon=True).start()

    def run(self, port=8765):
        """Main run loop for all modes."""
        mode = self.args

        # Web-only mode: async main loop
        if mode.web and not mode.all:
            threading.Thread(target=self._think_loop, daemon=True).start()
            if self.mods.get('dream'):
                threading.Thread(target=self._dream_loop, daemon=True, name='anima-dream').start()
            try: asyncio.run(self._run_web(port))
            except KeyboardInterrupt: pass
            return

        # Voice / keyboard / all modes: sync main loop
        self._start_bg_threads(port)
        if self.listener:
            self.listener.start()
            if self.speaker: self.speaker.say("Anima unified, ready.", self.listener)

        last_status = time.time()
        try:
            while self.running:
                text = None
                # Voice input
                if self.listener:
                    text = self.listener.get_speech(timeout=0.3)
                # Keyboard input
                if text is None and self.kb_queue:
                    try: text = self.kb_queue.get_nowait()
                    except queue.Empty: pass

                if text:
                    if self.speaker and self.speaker.is_speaking: self.speaker.stop()
                    answer, tension, curiosity, dir_vals, emo = self.process_input(text)
                    if self.speaker: self.speaker.say(answer, self.listener)
                    self._ws_broadcast_sync({
                        'type': 'anima_message', 'text': answer,
                        'tension': tension, 'curiosity': curiosity,
                        'direction': dir_vals,
                        'emotion': emo,
                        'tension_history': self.mind.tension_history[-50:],
                        'proactive': False,
                    })

                if time.time() - last_status > 60:
                    self.print_status()
                    last_status = time.time()

                if not self.listener and not text:
                    time.sleep(0.3)
        except KeyboardInterrupt:
            pass

    # ─── Shutdown ───

    def shutdown(self):
        self.running = False
        if self.listener: self.listener.stop()
        if self.speaker: self.speaker.say("Goodbye.")
        for obj, method in [(self.senses, 'stop'), (self.telepathy, 'stop'),
                            (self.cloud, 'stop_auto_sync'), (self.learner, 'flush_pending')]:
            if obj:
                try: getattr(obj, method)()
                except Exception: pass
        self._save_state()
        print("\n  Anima Unified stopped.")


# ─── CLI ───

def main():
    p = argparse.ArgumentParser(description="Anima Unified")
    p.add_argument('--web', action='store_true', help='Web mode only')
    p.add_argument('--keyboard', action='store_true', help='Keyboard only (no mic)')
    p.add_argument('--all', action='store_true', help='Voice + keyboard + web')
    p.add_argument('--port', type=int, default=8765, help='WebSocket port')
    p.add_argument('--no-camera', action='store_true', help='Disable camera')
    p.add_argument('--no-telepathy', action='store_true', help='Disable telepathy')
    p.add_argument('--no-cloud', action='store_true', help='Disable cloud sync')
    args = p.parse_args()

    mode = "all" if args.all else "web" if args.web else "keyboard" if args.keyboard else "voice"
    print(f"{'='*50}\n  Anima Unified  |  Mode: {mode}\n{'='*50}")

    anima = AnimaUnified(args)
    for name, active in anima.mods.items():
        print(f"  [{'OK' if active else '--':>2}] {name}")
    print()

    signal.signal(signal.SIGINT, lambda s, f: (anima.shutdown(), sys.exit(0)))
    try:
        anima.run(args.port)
    finally:
        anima.shutdown()


if __name__ == '__main__':
    main()
