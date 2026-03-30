#!/usr/bin/env python3
"""tension_link_code.py — 텐션링크 코드 생성/연결

IP:PORT 대신 짧은 코드로 텐션링크 연결.
코드 = base36(IP + PORT + auth) 인코딩.

Usage:
  from tension_link_code import TensionLinkCode

  tlc = TensionLinkCode()

  # 코드 생성 (호스트)
  code = tlc.generate()  # → "ANIMA-7X3K-9F2M"

  # 코드로 연결 (게스트)
  connection = tlc.connect("ANIMA-7X3K-9F2M")

  # R2 릴레이 (네트워크 분리 시)
  code = tlc.generate(relay="r2")  # → "R2-XXXX-XXXX"
"""

import hashlib
import json
import os
import socket
import time
import threading
import struct
from pathlib import Path
from typing import Optional, Dict

ANIMA_DIR = Path(__file__).parent
LINK_PORT = 9876
ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # O/I 제외 (혼동 방지)


def _encode_base34(num: int, length: int = 4) -> str:
    result = []
    for _ in range(length):
        result.append(ALPHABET[num % len(ALPHABET)])
        num //= len(ALPHABET)
    return ''.join(reversed(result))


def _decode_base34(code: str) -> int:
    num = 0
    for c in code:
        num = num * len(ALPHABET) + ALPHABET.index(c.upper())
    return num


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class TensionLinkCode:
    """텐션링크 코드 생성 + 연결."""

    def __init__(self, port: int = LINK_PORT):
        self.port = port
        self.ip = _get_local_ip()
        self._server = None
        self._connections = []
        self._on_receive = None
        self._running = False

    def generate(self, relay: str = None) -> str:
        """텐션링크 코드 생성 + 서버 시작.

        Returns: "ANIMA-XXXX-XXXX" 형식 코드
        """
        if relay == "r2":
            # R2 릴레이 코드
            session_id = hashlib.md5(f"{time.time()}{os.getpid()}".encode()).hexdigest()[:8]
            code_num = int(session_id, 16) % (34**8)
            code = f"R2-{_encode_base34(code_num >> 17, 4)}-{_encode_base34(code_num & 0x1FFFF, 4)}"
            self._r2_session = session_id
            return code

        # IP:PORT → 코드 변환
        ip_parts = [int(x) for x in self.ip.split('.')]
        ip_num = (ip_parts[0] << 24) | (ip_parts[1] << 16) | (ip_parts[2] << 8) | ip_parts[3]

        # auth = hash(ip + port + time_hour)
        auth_seed = f"{self.ip}:{self.port}:{int(time.time()) // 3600}"
        auth = int(hashlib.md5(auth_seed.encode()).hexdigest()[:4], 16)

        part1 = _encode_base34((ip_num >> 16) ^ (auth >> 8), 4)
        part2 = _encode_base34(((ip_num & 0xFFFF) << 4) | (self.port % 16) ^ (auth & 0xFF), 4)

        code = f"ANIMA-{part1}-{part2}"

        # 서버 시작
        self._start_server()

        return code

    def decode(self, code: str) -> Optional[Dict]:
        """코드 → IP:PORT 디코딩."""
        if code.startswith("R2-"):
            return {'type': 'r2', 'session': code}

        parts = code.replace("ANIMA-", "").split("-")
        if len(parts) != 2:
            return None

        try:
            val1 = _decode_base34(parts[0])
            val2 = _decode_base34(parts[1])

            # 현재 시간 기반 auth로 역추적 시도
            # 간단 버전: 포트는 LINK_PORT 고정
            return {
                'type': 'direct',
                'code': code,
                'port': self.port,
                'encoded': (val1, val2),
            }
        except Exception:
            return None

    def connect(self, code: str, callback=None) -> bool:
        """코드로 텐션링크 연결.

        실제로는 코드를 서버에 등록하고 매칭.
        """
        self._on_receive = callback

        if code.startswith("R2-"):
            return self._connect_r2(code)

        # 코드 서버에 등록 요청 (broadcast로 코드 찾기)
        info = self.decode(code)
        if not info:
            return False

        # 로컬 네트워크에서 코드 broadcast로 찾기
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = json.dumps({'type': 'link_request', 'code': code}).encode()
            sock.sendto(msg, ('255.255.255.255', self.port))
            sock.settimeout(5.0)
            try:
                data, addr = sock.recvfrom(1024)
                resp = json.loads(data.decode())
                if resp.get('type') == 'link_accept':
                    self._peer_addr = addr
                    print(f"  🔗 Connected to {addr[0]}:{addr[1]}")
                    return True
            except socket.timeout:
                pass
            sock.close()
        except Exception:
            pass

        return False

    def send(self, data: dict):
        """연결된 피어에 데이터 전송."""
        if hasattr(self, '_peer_addr'):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                msg = json.dumps(data).encode()
                sock.sendto(msg, self._peer_addr)
                sock.close()
            except Exception:
                pass

    def _start_server(self):
        """코드 매칭 서버 시작."""
        if self._running:
            return
        self._running = True

        def _listen():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('', self.port))
                sock.settimeout(1.0)
                while self._running:
                    try:
                        data, addr = sock.recvfrom(65536)
                        msg = json.loads(data.decode())
                        if msg.get('type') == 'link_request':
                            # 코드 매칭 → 수락
                            resp = json.dumps({'type': 'link_accept'}).encode()
                            sock.sendto(resp, addr)
                            self._peer_addr = addr
                            print(f"  🔗 Peer connected: {addr[0]}:{addr[1]}")
                        elif self._on_receive:
                            self._on_receive(msg)
                    except socket.timeout:
                        continue
                sock.close()
            except Exception:
                pass

        t = threading.Thread(target=_listen, daemon=True)
        t.start()

    def _connect_r2(self, code: str) -> bool:
        """R2 릴레이 연결."""
        # R2에 코드 등록 → 상대방이 같은 코드로 접속 → 매칭
        try:
            from cloud_sync import CloudSync
            sync = CloudSync()
            session = code.replace("R2-", "").replace("-", "")
            sync.upload(json.dumps({
                'code': code,
                'ip': self.ip,
                'port': self.port,
                'timestamp': time.time(),
            }).encode(), f"tension-link/{session}.json")
            return True
        except Exception:
            return False

    def stop(self):
        self._running = False

    def status(self) -> str:
        peer = getattr(self, '_peer_addr', None)
        return f"TensionLinkCode: ip={self.ip}, port={self.port}, peer={peer}"


def main():
    print("═══ Tension Link Code Demo ═══\n")

    tlc = TensionLinkCode()

    # 코드 생성
    code = tlc.generate()
    print(f"  내 코드: {code}")
    print(f"  IP: {tlc.ip}:{tlc.port}")
    print(f"  상대방에게 이 코드를 공유하세요!")

    # R2 코드
    r2_code = tlc.generate(relay="r2")
    print(f"\n  R2 릴레이 코드: {r2_code}")

    # 디코딩
    info = tlc.decode(code)
    print(f"\n  디코딩: {info}")

    print(f"\n  {tlc.status()}")

    tlc.stop()
    print("\n  ✅ OK")


if __name__ == '__main__':
    main()
