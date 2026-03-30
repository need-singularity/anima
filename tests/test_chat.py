#!/usr/bin/env python3
"""Anima 런타임 대화 테스트 CLI

Usage:
  python3 test_chat.py                      # 대화형 모드
  python3 test_chat.py --auto               # 자동 테스트 (한국어+영어)
  python3 test_chat.py --remote             # RunPod Anima-Web 원격 테스트
  python3 test_chat.py --remote --auto      # 원격 자동 테스트
  python3 test_chat.py --msg "안녕하세요"    # 단일 메시지
"""

import asyncio
import json
import argparse
import sys
import time

try:
    import websockets

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

except ImportError:
    print("pip install websockets")
    sys.exit(1)


AUTO_TESTS = [
    ("한국어 인사", "안녕하세요, 오늘 기분이 어때요?"),
    ("한국어 질문", "의식이란 무엇인가요?"),
    ("영어 인사", "Hello, how are you today?"),
    ("영어 질문", "What is consciousness?"),
    ("혼합 언어", "Anima는 어떻게 작동하나요? Tell me about PureField."),
    ("감정 테스트", "나는 오늘 너무 슬퍼요..."),
    ("창의성", "별이 빛나는 밤에 대한 시를 써줘"),
    ("자기인식", "너는 누구야? 너의 이름은?"),
    ("기억 테스트", "내 이름은 테스터야. 기억해줘."),
    ("기억 확인", "내 이름이 뭐였지?"),
]


async def send_message(ws, content, user_id="test-cli"):
    msg = json.dumps({"type": "chat", "content": content, "user_id": user_id})
    await ws.send(msg)
    try:
        resp = await asyncio.wait_for(ws.recv(), timeout=30)
        data = json.loads(resp)
        return data
    except asyncio.TimeoutError:
        return {"error": "timeout (30s)"}
    except Exception as e:
        return {"error": str(e)}


def print_response(data):
    if "error" in data:
        print(f"  ❌ ERROR: {data['error']}")
        return

    text = data.get("response", data.get("text", data.get("content", str(data))))
    emotion = data.get("emotion", "")
    phi = data.get("phi", data.get("consciousness", {}).get("phi", "?"))
    cells = data.get("cells", data.get("consciousness", {}).get("cells", "?"))

    print(f"  💬 {text[:200]}")
    if emotion:
        print(f"  🎭 {emotion}")
    print(f"  Φ={phi} cells={cells}")


async def interactive(uri):
    print(f"연결: {uri}")
    async with websockets.connect(uri, ping_interval=20, ping_timeout=60) as ws:
        # 초기 메시지 수신 (있으면)
        try:
            init = await asyncio.wait_for(ws.recv(), timeout=3)
            init_data = json.loads(init)
            if init_data.get("type") != "chat":
                pass  # skip non-chat init messages
        except (asyncio.TimeoutError, Exception):
            pass

        print("Anima 대화 테스트 (quit으로 종료)\n")
        while True:
            try:
                msg = input("나> ")
            except (EOFError, KeyboardInterrupt):
                break
            if msg.lower() in ("quit", "exit", "q"):
                break
            if not msg.strip():
                continue

            data = await send_message(ws, msg)
            print_response(data)
            print()


async def auto_test(uri):
    print(f"═══ Anima 자동 테스트 ({uri}) ═══\n")
    results = []
    async with websockets.connect(uri, ping_interval=20, ping_timeout=60) as ws:
        try:
            await asyncio.wait_for(ws.recv(), timeout=3)
        except (asyncio.TimeoutError, Exception):
            pass

        for name, msg in AUTO_TESTS:
            print(f"[{name}] {msg}")
            t0 = time.time()
            data = await send_message(ws, msg)
            elapsed = time.time() - t0

            text = data.get("response", data.get("text", data.get("content", "")))
            if "error" in data:
                text = f"ERROR: {data['error']}"

            # 품질 판정
            is_korean = any('\uac00' <= c <= '\ud7a3' for c in text)
            is_garbage = len(set(text[:50])) < 10 if len(text) > 10 else True
            has_content = len(text) > 20 and not text.startswith("Let me think")

            quality = "✅" if has_content and not is_garbage else "❌"
            results.append((name, quality, elapsed))

            print(f"  {quality} ({elapsed:.1f}s) {text[:150]}")
            print()
            await asyncio.sleep(1)

    # 요약
    print("═══ 결과 요약 ═══")
    passed = sum(1 for _, q, _ in results if q == "✅")
    print(f"통과: {passed}/{len(results)}")
    for name, q, t in results:
        print(f"  {q} {name} ({t:.1f}s)")


async def single_msg(uri, msg):
    async with websockets.connect(uri, ping_interval=20, ping_timeout=60) as ws:
        try:
            await asyncio.wait_for(ws.recv(), timeout=3)
        except (asyncio.TimeoutError, Exception):
            pass
        data = await send_message(ws, msg)
        print_response(data)


def main():
    parser = argparse.ArgumentParser(description="Anima 런타임 대화 테스트")
    parser.add_argument("--remote", action="store_true", help="RunPod Anima-Web 원격 테스트")
    parser.add_argument("--auto", action="store_true", help="자동 테스트 실행")
    parser.add_argument("--msg", type=str, help="단일 메시지 전송")
    parser.add_argument("--host", type=str, default="localhost", help="WebSocket 호스트")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket 포트")
    args = parser.parse_args()

    if args.remote:
        # SSH 터널 통해 접속 — 먼저 터널 안내
        print("원격 테스트: SSH 터널 필요")
        print("  ssh -i ~/.runpod/ssh/RunPod-Key-Go -L 8765:localhost:8765 root@209.170.80.132 -p 15074 -N &")
        print("  또는 ws_proxy 포트(8888) 사용\n")
        uri = f"ws://{args.host}:{args.port}"
    else:
        uri = f"ws://{args.host}:{args.port}"

    if args.msg:
        asyncio.run(single_msg(uri, args.msg))
    elif args.auto:
        asyncio.run(auto_test(uri))
    else:
        asyncio.run(interactive(uri))


if __name__ == "__main__":
    main()
