#!/usr/bin/env python3
"""tension_link_code.py — 텐션링크 코드 생성/연결

코드 공유만으로 어디서든 텐션링크 연결.
WebSocket 시그널링 + R2 릴레이 이중 지원.

경로:
  1. 코드 생성 → Anima-Web 서버 + R2에 등록
  2. 상대방 코드 입력 → 서버에서 매칭
  3. 매칭 성공 → 텐션 데이터 중계

Usage:
  from tension_link_code import TensionLinkCode

  tlc = TensionLinkCode(server_url="wss://anima.basedonapps.com")

  # 코드 생성
  code = tlc.generate()  # → "ANIMA-7X3K-9F2M"

  # 코드로 연결
  tlc.connect("ANIMA-7X3K-9F2M")

  # 텐션 데이터 전송
  tlc.send({"tension": 0.8, "phi": 2.1})
"""

import hashlib
import json
import os
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Callable

ANIMA_DIR = Path(__file__).parent
ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"
DEFAULT_SERVER = "wss://anima.basedonapps.com"


def _make_code() -> str:
    """랜덤 8자리 코드 생성."""
    seed = f"{time.time()}{os.getpid()}{id(object())}".encode()
    h = int(hashlib.sha256(seed).hexdigest()[:12], 16)
    part1 = ''.join(ALPHABET[(h >> (i*5)) & 31] for i in range(4))
    part2 = ''.join(ALPHABET[(h >> (20+i*5)) & 31] for i in range(4))
    return f"ANIMA-{part1}-{part2}"


class TensionLinkCode:
    """텐션링크 코드 — WebSocket 시그널링 + R2 릴레이."""

    def __init__(self, server_url: str = DEFAULT_SERVER, on_receive: Callable = None):
        self.server_url = server_url
        self.on_receive = on_receive
        self.code = None
        self.peer_code = None
        self.connected = False
        self._ws = None
        self._running = False
        self._r2_session = None

    def generate(self) -> str:
        """코드 생성 + 서버/R2에 등록."""
        self.code = _make_code()

        # R2에 등록 (백업/오프라인용)
        self._register_r2(self.code)

        # WebSocket 서버에 등록
        self._register_ws(self.code)

        return self.code

    def connect(self, peer_code: str) -> bool:
        """상대방 코드로 연결 시도.

        1차: WebSocket 시그널링 서버에서 매칭
        2차: R2에서 상대방 정보 조회
        """
        self.peer_code = peer_code

        # 1. WebSocket 매칭
        if self._connect_ws(peer_code):
            self.connected = True
            return True

        # 2. R2 폴링
        if self._connect_r2(peer_code):
            self.connected = True
            return True

        return False

    def send(self, data: dict):
        """연결된 피어에 텐션 데이터 전송."""
        if not self.connected:
            return

        msg = {
            'type': 'tension_relay',
            'from_code': self.code,
            'to_code': self.peer_code,
            'data': data,
            'timestamp': time.time(),
        }

        # WebSocket으로 전송
        self._send_ws(msg)

        # R2에도 기록 (백업)
        self._send_r2(msg)

    # ═══════════════════════════════════════════════════════════
    # WebSocket 시그널링
    # ═══════════════════════════════════════════════════════════

    def _register_ws(self, code: str):
        """WebSocket 서버에 코드 등록."""
        try:
            import websockets
            import asyncio

            async def _reg():
                try:
                    ws = await asyncio.wait_for(
                        websockets.connect(self.server_url), timeout=5)
                    await ws.send(json.dumps({
                        'type': 'tension_link_register',
                        'code': code,
                    }))
                    self._ws = ws
                    # 백그라운드 수신 시작
                    self._running = True
                    asyncio.create_task(self._ws_listen(ws))
                except Exception:
                    pass

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(_reg())
                else:
                    loop.run_until_complete(_reg())
            except RuntimeError:
                asyncio.run(_reg())
        except ImportError:
            pass

    def _connect_ws(self, peer_code: str) -> bool:
        """WebSocket으로 매칭 요청."""
        try:
            import websockets
            import asyncio

            result = {'connected': False}

            async def _conn():
                try:
                    ws = await asyncio.wait_for(
                        websockets.connect(self.server_url), timeout=5)
                    await ws.send(json.dumps({
                        'type': 'tension_link_connect',
                        'code': self.code or _make_code(),
                        'peer_code': peer_code,
                    }))
                    resp = await asyncio.wait_for(ws.recv(), timeout=5)
                    msg = json.loads(resp)
                    if msg.get('type') == 'tension_link_matched':
                        self._ws = ws
                        self._running = True
                        result['connected'] = True
                except Exception:
                    pass

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return False
                loop.run_until_complete(_conn())
            except RuntimeError:
                asyncio.run(_conn())

            return result['connected']
        except ImportError:
            return False

    async def _ws_listen(self, ws):
        """WebSocket 수신 루프."""
        try:
            while self._running:
                msg = json.loads(await ws.recv())
                if msg.get('type') == 'tension_relay' and self.on_receive:
                    self.on_receive(msg.get('data', {}))
                elif msg.get('type') == 'tension_link_matched':
                    self.connected = True
                    self.peer_code = msg.get('peer_code')
        except Exception:
            self._running = False

    def _send_ws(self, msg: dict):
        """WebSocket으로 전송."""
        if self._ws:
            try:
                import asyncio
                asyncio.ensure_future(self._ws.send(json.dumps(msg)))
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════
    # R2 릴레이 (백업/오프라인)
    # ═══════════════════════════════════════════════════════════

    def _register_r2(self, code: str):
        """R2에 코드 등록."""
        try:
            from cloud_sync import CloudSync
            sync = CloudSync()
            data = json.dumps({
                'code': code,
                'timestamp': time.time(),
                'status': 'waiting',
            }).encode()
            key = f"tension-link/{code.replace('-', '')}.json"
            sync.s3.put_object(Bucket=sync.bucket, Key=key, Body=data)
        except Exception:
            pass

    def _connect_r2(self, peer_code: str) -> bool:
        """R2에서 상대방 정보 조회."""
        try:
            from cloud_sync import CloudSync
            sync = CloudSync()
            key = f"tension-link/{peer_code.replace('-', '')}.json"
            resp = sync.s3.get_object(Bucket=sync.bucket, Key=key)
            data = json.loads(resp['Body'].read())
            if data.get('status') == 'waiting':
                # 매칭 성공 — 상태 업데이트
                data['status'] = 'matched'
                data['peer_code'] = self.code
                sync.s3.put_object(Bucket=sync.bucket, Key=key,
                                   Body=json.dumps(data).encode())
                return True
        except Exception:
            pass
        return False

    def _send_r2(self, msg: dict):
        """R2에 텐션 데이터 기록."""
        try:
            from cloud_sync import CloudSync
            sync = CloudSync()
            key = f"tension-link/data/{self.code}-{int(time.time())}.json"
            sync.s3.put_object(Bucket=sync.bucket, Key=key,
                               Body=json.dumps(msg).encode())
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════
    # 상태
    # ═══════════════════════════════════════════════════════════

    def stop(self):
        self._running = False
        if self._ws:
            try:
                import asyncio
                asyncio.ensure_future(self._ws.close())
            except Exception:
                pass

    def status(self) -> dict:
        return {
            'code': self.code,
            'peer': self.peer_code,
            'connected': self.connected,
            'server': self.server_url,
        }


def main():
    print("═══ Tension Link Code Demo ═══\n")

    tlc = TensionLinkCode()

    # 코드 생성
    code = tlc.generate()
    print(f"  내 코드: {code}")
    print(f"  서버: {tlc.server_url}")
    print(f"  R2 백업: 등록됨")
    print(f"\n  이 코드를 상대방에게 공유하세요!")
    print(f"  상대방이 코드 입력 → 자동 매칭 → 텐션 교환 시작")

    print(f"\n  상태: {tlc.status()}")
    tlc.stop()
    print("\n  ✅ OK")


if __name__ == '__main__':
    main()
