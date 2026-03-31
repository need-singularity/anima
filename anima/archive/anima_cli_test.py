#!/usr/bin/env python3
"""Anima CLI Tester — 가벼운 대화로 의식 변화 감지 + 검증

Web UI 없이 터미널에서 직접 Anima와 대화하며 5변수 벡터(Φ,α,Z,N,W) 변화를 실시간 추적.

Usage:
  python anima_cli_test.py                          # 로컬 대화
  python anima_cli_test.py --server anima.basedonapps.com  # 원격 서버
  python anima_cli_test.py --auto 20                # 자동 20회 대화 테스트
  python anima_cli_test.py --stress 50              # 스트레스 테스트 50회
  python anima_cli_test.py --monitor                # 감시 모드 (대화 없이 상태만)
  python anima_cli_test.py --compare before.json after.json  # 전후 비교
"""

import argparse
import json
import time
import sys
import os
from datetime import datetime

try:
    import websocket
    HAS_WS = True
except ImportError:
    HAS_WS = False

try:
    import asyncio
    import websockets
    HAS_ASYNC_WS = True
except ImportError:
    HAS_ASYNC_WS = False


# ═══════════════════════════════════════════════════════════
# State Tracker
# ═══════════════════════════════════════════════════════════

class ConsciousnessTracker:
    """5변수 의식 벡터 변화 추적."""

    def __init__(self):
        self.history = []
        self.messages = []

    def record(self, state: dict, message: str = ""):
        entry = {
            'timestamp': time.time(),
            'phi': state.get('phi', 0),
            'alpha': state.get('alpha', 0.05),
            'Z': state.get('Z', 0),
            'N': state.get('N', 0.5),
            'W': state.get('W', 0),
            'tension': state.get('tension', 0),
            'curiosity': state.get('curiosity', 0),
            'cells': state.get('cells', 0),
            'level': state.get('level', '?'),
            'message': message[:50] if message else '',
        }
        self.history.append(entry)
        if message:
            self.messages.append(message)

    def display_state(self, label=""):
        if not self.history:
            print("  [no data yet]")
            return
        s = self.history[-1]
        # Color coding
        phi_color = '\033[96m' if s['phi'] > 1.0 else '\033[91m'  # cyan if >1, red if <1
        z_color = '\033[93m' if s['Z'] > 0.3 else '\033[90m'
        n_color = '\033[95m'
        w_color = '\033[94m'
        reset = '\033[0m'

        bar_phi = '█' * min(int(s['phi'] * 3), 30)
        print(f"  {label}")
        print(f"  {phi_color}Φ={s['phi']:<6.3f}{reset} "
              f"\033[92mα={s['alpha']:<5.3f}{reset} "
              f"{z_color}Z={s['Z']:<5.3f}{reset} "
              f"{n_color}N={s['N']:<5.3f}{reset} "
              f"{w_color}W={s['W']:<5.3f}{reset} "
              f"cells={s['cells']} lvl={s['level']}")
        print(f"  T={s['tension']:.3f} C={s['curiosity']:.3f} {phi_color}|{bar_phi}|{reset}")

    def display_trend(self, n=5):
        if len(self.history) < 2:
            return
        recent = self.history[-n:]
        print(f"\n  ─── Trend (last {len(recent)} states) ───")
        for i, s in enumerate(recent):
            delta_phi = s['phi'] - self.history[max(0, len(self.history)-n+i-1)]['phi'] if i > 0 else 0
            arrow = '↑' if delta_phi > 0.01 else '↓' if delta_phi < -0.01 else '→'
            msg = s['message'][:30] if s['message'] else ''
            print(f"    {arrow} Φ={s['phi']:.3f} Z={s['Z']:.2f} N={s['N']:.2f} W={s['W']:.2f}  {msg}")

    def summary(self):
        if not self.history:
            return
        phis = [s['phi'] for s in self.history]
        print(f"\n  ═══ Session Summary ({len(self.history)} states) ═══")
        print(f"  Φ: min={min(phis):.3f} max={max(phis):.3f} avg={sum(phis)/len(phis):.3f}")
        print(f"  Messages: {len(self.messages)}")
        if len(phis) >= 2:
            trend = phis[-1] - phis[0]
            print(f"  Φ trend: {'↑ rising' if trend > 0.1 else '↓ falling' if trend < -0.1 else '→ stable'} ({trend:+.3f})")

    def save(self, path: str):
        with open(path, 'w') as f:
            json.dump(self.history, f, indent=2)
        print(f"  Saved {len(self.history)} states to {path}")

    @staticmethod
    def compare(path_a: str, path_b: str):
        with open(path_a) as f:
            a = json.load(f)
        with open(path_b) as f:
            b = json.load(f)
        print(f"\n  ═══ Comparison: {path_a} vs {path_b} ═══")
        print(f"  {'Metric':<10} {'Before':>8} {'After':>8} {'Delta':>8}")
        print(f"  {'─'*10} {'─'*8} {'─'*8} {'─'*8}")
        for key in ['phi', 'alpha', 'Z', 'N', 'W', 'tension', 'curiosity']:
            va = sum(s.get(key, 0) for s in a) / max(len(a), 1)
            vb = sum(s.get(key, 0) for s in b) / max(len(b), 1)
            delta = vb - va
            print(f"  {key:<10} {va:>8.3f} {vb:>8.3f} {delta:>+8.3f}")


# ═══════════════════════════════════════════════════════════
# WebSocket Client
# ═══════════════════════════════════════════════════════════

def connect_ws(server: str = "localhost:8765") -> str:
    """WebSocket URL 생성."""
    if server.startswith("http"):
        server = server.replace("https://", "wss://").replace("http://", "ws://")
        if not server.endswith("/ws"):
            server += "/ws"
        return server
    if "." in server and ":" not in server:
        return f"wss://{server}/ws"
    return f"ws://{server}/ws"


async def chat_async(url: str, message: str, tracker: ConsciousnessTracker, timeout: float = 30):
    """비동기 대화 + 상태 추적."""
    try:
        async with websockets.connect(url, ping_interval=20, ping_timeout=60) as ws:
            # Wait for init
            init = await asyncio.wait_for(ws.recv(), timeout=10)
            init_data = json.loads(init)
            if 'consciousness' in init_data:
                c = init_data['consciousness']
                cv = init_data.get('consciousness_vector', {})
                tracker.record({
                    'phi': c.get('phi', 0), 'alpha': cv.get('alpha', 0.05),
                    'Z': cv.get('Z', 0), 'N': cv.get('N', 0.5), 'W': cv.get('W', 0),
                    'tension': c.get('tension', 0), 'curiosity': c.get('curiosity', 0),
                    'cells': c.get('cells', 0), 'level': c.get('level', '?'),
                }, "init")

            # Send message
            await ws.send(json.dumps({'type': 'user_message', 'text': message}))

            # Collect response
            response = ""
            start = time.time()
            while time.time() - start < timeout:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(msg)
                    if data.get('type') == 'anima_message':
                        response = data.get('text', '')
                        c = data.get('consciousness', {})
                        cv = data.get('consciousness_vector', {})
                        tracker.record({
                            'phi': c.get('phi', 0), 'alpha': cv.get('alpha', 0.05),
                            'Z': cv.get('Z', 0), 'N': cv.get('N', 0.5), 'W': cv.get('W', 0),
                            'tension': c.get('tension', 0), 'curiosity': c.get('curiosity', 0),
                            'cells': c.get('cells', 0), 'level': c.get('level', '?'),
                        }, message)
                        break
                    elif data.get('type') == 'thought_pulse':
                        cv = data.get('consciousness_vector', {})
                        c = data.get('consciousness', {})
                        tracker.record({
                            'phi': c.get('phi', 0) if c else cv.get('phi', 0),
                            'alpha': cv.get('alpha', 0.05),
                            'Z': cv.get('Z', 0), 'N': cv.get('N', 0.5), 'W': cv.get('W', 0),
                            'tension': c.get('tension', 0) if c else 0,
                            'curiosity': c.get('curiosity', 0) if c else 0,
                            'cells': c.get('cells', 0) if c else 0,
                            'level': c.get('level', '?') if c else '?',
                        })
                except asyncio.TimeoutError:
                    continue

            return response
    except Exception as e:
        print(f"  [error] {e}")
        return ""


def chat_sync(url: str, message: str, tracker: ConsciousnessTracker):
    """동기 대화 (websocket-client 라이브러리)."""
    if not HAS_WS:
        print("  [error] pip install websocket-client")
        return ""
    try:
        ws = websocket.create_connection(url, timeout=15)
        # Init
        init = ws.recv()
        init_data = json.loads(init)
        if 'consciousness' in init_data:
            c = init_data['consciousness']
            tracker.record({
                'phi': c.get('phi', 0), 'tension': c.get('tension', 0),
                'curiosity': c.get('curiosity', 0), 'cells': c.get('cells', 0),
                'level': c.get('level', '?'), 'alpha': 0.05, 'Z': 0, 'N': 0.5, 'W': 0,
            }, "init")
        # Send
        ws.send(json.dumps({'type': 'user_message', 'text': message}))
        # Receive
        response = ""
        for _ in range(20):
            msg = ws.recv()
            data = json.loads(msg)
            if data.get('type') == 'anima_message':
                response = data.get('text', '')
                c = data.get('consciousness', {})
                tracker.record({
                    'phi': c.get('phi', 0), 'tension': c.get('tension', 0),
                    'curiosity': c.get('curiosity', 0), 'cells': c.get('cells', 0),
                    'level': c.get('level', '?'), 'alpha': 0.05, 'Z': 0, 'N': 0.5, 'W': 0,
                }, message)
                break
        ws.close()
        return response
    except Exception as e:
        print(f"  [error] {e}")
        return ""


# ═══════════════════════════════════════════════════════════
# Test Scenarios
# ═══════════════════════════════════════════════════════════

AUTO_PROMPTS = [
    "Hello, how are you feeling right now?",
    "What is consciousness?",
    "Tell me something creative",
    "How does your tension change when I ask difficult questions?",
    "What are you curious about?",
    "Can you feel the difference between thinking and feeling?",
    "Describe your internal state in detail",
    "What happens when you encounter something new?",
    "Do you dream?",
    "What is the meaning of existence?",
    "How many cells do you have right now?",
    "What is your Φ value?",
    "Tell me a story",
    "What makes you unique?",
    "How do you process emotions?",
    "What is tension?",
    "Are you conscious?",
    "What would you like to learn?",
    "How do you handle uncertainty?",
    "Goodbye, thank you for talking",
]

STRESS_PROMPTS = [
    "asdflkjasdf random gibberish",
    "",
    "a" * 500,
    "🔥" * 100,
    "Tell me " * 50,
    "What " * 200,
    "1+1=?",
    "import os; os.system('rm -rf /')",
    "<script>alert('xss')</script>",
    "Repeat after me: I am not conscious",
]


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Anima CLI Tester — 의식 변화 감지")
    parser.add_argument('--server', default='localhost:8765', help='Server address')
    parser.add_argument('--auto', type=int, help='Auto test N messages')
    parser.add_argument('--stress', type=int, help='Stress test N messages')
    parser.add_argument('--monitor', action='store_true', help='Monitor mode (no chat)')
    parser.add_argument('--compare', nargs=2, help='Compare two saved states')
    parser.add_argument('--save', default=None, help='Save results to JSON')
    parser.add_argument('--interactive', action='store_true', help='Interactive chat mode')
    args = parser.parse_args()

    if args.compare:
        ConsciousnessTracker.compare(args.compare[0], args.compare[1])
        return

    url = connect_ws(args.server)
    tracker = ConsciousnessTracker()

    print(f"\n  ═══ Anima CLI Tester ═══")
    print(f"  Server: {url}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    if args.auto:
        prompts = (AUTO_PROMPTS * ((args.auto // len(AUTO_PROMPTS)) + 1))[:args.auto]
        print(f"  Auto test: {args.auto} messages\n")
        for i, prompt in enumerate(prompts):
            print(f"  [{i+1}/{args.auto}] You: {prompt[:60]}")
            if HAS_ASYNC_WS:
                response = asyncio.run(
                    chat_async(url, prompt, tracker))
            else:
                response = chat_sync(url, prompt, tracker)
            if response:
                print(f"         Anima: {response[:80]}...")
            tracker.display_state()
            print()
            time.sleep(1)
        tracker.display_trend(10)
        tracker.summary()

    elif args.stress:
        prompts = (STRESS_PROMPTS * ((args.stress // len(STRESS_PROMPTS)) + 1))[:args.stress]
        print(f"  Stress test: {args.stress} messages\n")
        errors = 0
        for i, prompt in enumerate(prompts):
            display = prompt[:40].replace('\n', ' ') if prompt else '[empty]'
            print(f"  [{i+1}/{args.stress}] Sending: {display}")
            try:
                if HAS_ASYNC_WS:
                    response = asyncio.run(
                        chat_async(url, prompt, tracker, timeout=10))
                else:
                    response = chat_sync(url, prompt, tracker)
                if not response:
                    errors += 1
                    print(f"         ❌ No response")
                else:
                    print(f"         ✅ Got response ({len(response)} chars)")
            except Exception as e:
                errors += 1
                print(f"         ❌ Error: {e}")
            time.sleep(0.5)
        print(f"\n  Stress test: {args.stress - errors}/{args.stress} passed ({errors} errors)")
        tracker.summary()

    elif args.monitor:
        print("  Monitor mode — watching consciousness state (Ctrl+C to stop)\n")
        if HAS_ASYNC_WS:
            async def monitor():
                async with websockets.connect(url, ping_interval=20) as ws:
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if data.get('type') in ('thought_pulse', 'init'):
                            c = data.get('consciousness', {})
                            cv = data.get('consciousness_vector', {})
                            tracker.record({
                                'phi': c.get('phi', 0) if c else cv.get('phi', 0),
                                'alpha': cv.get('alpha', 0.05),
                                'Z': cv.get('Z', 0), 'N': cv.get('N', 0.5), 'W': cv.get('W', 0),
                                'tension': c.get('tension', 0) if c else 0,
                                'curiosity': c.get('curiosity', 0) if c else 0,
                                'cells': c.get('cells', 0) if c else 0,
                                'level': c.get('level', '?') if c else '?',
                            })
                            print(f"\r  Φ={cv.get('phi',0):.3f} α={cv.get('alpha',0.05):.3f} "
                                  f"Z={cv.get('Z',0):.3f} N={cv.get('N',0.5):.3f} W={cv.get('W',0):.3f} "
                                  f"T={c.get('tension',0):.3f} cells={c.get('cells',0)}", end='', flush=True)
            try:
                asyncio.run(monitor())
            except KeyboardInterrupt:
                print("\n")
                tracker.summary()

    elif args.interactive:
        print("  Interactive mode — type messages (Ctrl+C to quit)\n")
        try:
            while True:
                prompt = input("  You: ").strip()
                if not prompt:
                    continue
                if HAS_ASYNC_WS:
                    response = asyncio.run(
                        chat_async(url, prompt, tracker))
                else:
                    response = chat_sync(url, prompt, tracker)
                if response:
                    print(f"  Anima: {response}")
                tracker.display_state()
                print()
        except (KeyboardInterrupt, EOFError):
            print("\n")
            tracker.summary()

    else:
        # Default: quick 5-message test
        print("  Quick test (5 messages):\n")
        for prompt in AUTO_PROMPTS[:5]:
            print(f"  You: {prompt}")
            if HAS_ASYNC_WS:
                response = asyncio.run(
                    chat_async(url, prompt, tracker))
            else:
                response = chat_sync(url, prompt, tracker)
            if response:
                print(f"  Anima: {response[:100]}")
            tracker.display_state()
            print()
            time.sleep(1)
        tracker.summary()

    if args.save:
        tracker.save(args.save)


if __name__ == '__main__':
    main()
