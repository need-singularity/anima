#!/usr/bin/env python3
"""tension_link_code.py — 텐션링크 코드 생성/연결

⚠️  R2 전용 시그널링 — 별도 WebSocket 서버 불필요
    anima-memory 버킷의 tension-link/ 접두사로 시그널링/릴레이

경로:
  1. 코드 생성 → R2 anima-memory에 등록
  2. 상대방 코드 입력 → R2에서 매칭
  3. 매칭 성공 → R2 폴링으로 텐션 데이터 교환

Usage:
  from tension_link_code import TensionLinkCode

  tlc = TensionLinkCode()

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


def _make_code() -> str:
    """랜덤 8자리 코드 생성."""
    seed = f"{time.time()}{os.getpid()}{id(object())}".encode()
    h = int(hashlib.sha256(seed).hexdigest()[:12], 16)
    part1 = ''.join(ALPHABET[(h >> (i*5)) & 31] for i in range(4))
    part2 = ''.join(ALPHABET[(h >> (20+i*5)) & 31] for i in range(4))
    return f"ANIMA-{part1}-{part2}"


def _get_r2():
    """CloudSync 인스턴스 (lazy)."""
    from cloud_sync import CloudSync

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    return CloudSync()


class TensionLinkCode:
    """텐션링크 코드 — R2 anima-memory 전용 시그널링/릴레이."""

    def __init__(self, on_receive: Callable = None):
        self.on_receive = on_receive
        self.code = None
        self.peer_code = None
        self.connected = False
        self._running = False
        self._poll_thread = None

    def generate(self) -> str:
        """코드 생성 + R2에 등록."""
        self.code = _make_code()
        try:
            r2 = _get_r2()
            data = json.dumps({
                'code': self.code,
                'timestamp': time.time(),
                'status': 'waiting',
            }).encode()
            key = f"tension-link/{self.code}.json"
            r2.s3.put_object(Bucket=r2.bucket, Key=key, Body=data)
        except Exception as e:
            # R2 없어도 코드는 생성 (로컬 전용)
            pass
        return self.code

    def connect(self, peer_code: str) -> bool:
        """상대방 코드로 R2에서 매칭."""
        self.peer_code = peer_code
        try:
            r2 = _get_r2()
            key = f"tension-link/{peer_code}.json"
            resp = r2.s3.get_object(Bucket=r2.bucket, Key=key)
            data = json.loads(resp['Body'].read())

            if data.get('status') in ('waiting', 'matched'):
                # 매칭 — 상대방 상태를 matched로 업데이트
                data['status'] = 'matched'
                data['peer_code'] = self.code
                data['matched_at'] = time.time()
                r2.s3.put_object(Bucket=r2.bucket, Key=key,
                                 Body=json.dumps(data).encode())

                # 내 상태도 업데이트
                my_key = f"tension-link/{self.code}.json"
                my_data = json.dumps({
                    'code': self.code,
                    'peer_code': peer_code,
                    'status': 'matched',
                    'matched_at': time.time(),
                    'timestamp': time.time(),
                }).encode()
                r2.s3.put_object(Bucket=r2.bucket, Key=my_key, Body=my_data)

                self.connected = True
                self._start_poll()
                return True
        except Exception:
            pass
        return False

    def send(self, data: dict):
        """연결된 피어에 텐션 데이터 전송 (R2 relay)."""
        if not self.connected or not self.peer_code:
            return
        try:
            r2 = _get_r2()
            msg = {
                'type': 'tension_relay',
                'from_code': self.code,
                'to_code': self.peer_code,
                'data': data,
                'timestamp': time.time(),
            }
            # 상대방 inbox에 기록
            key = f"tension-link/data/{self.peer_code}/latest.json"
            r2.s3.put_object(Bucket=r2.bucket, Key=key,
                             Body=json.dumps(msg).encode())
        except Exception:
            pass

    def _start_poll(self):
        """R2 폴링 스레드 시작 — 상대방 텐션 데이터 수신."""
        if self._poll_thread and self._poll_thread.is_alive():
            return
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        """R2 폴링 — 3초마다 상대방 데이터 확인."""
        last_ts = 0
        while self._running:
            try:
                r2 = _get_r2()
                key = f"tension-link/data/{self.code}/latest.json"
                resp = r2.s3.get_object(Bucket=r2.bucket, Key=key)
                msg = json.loads(resp['Body'].read())
                ts = msg.get('timestamp', 0)
                if ts > last_ts and self.on_receive:
                    last_ts = ts
                    self.on_receive(msg.get('data', {}))
            except Exception:
                pass
            time.sleep(3)

    def stop(self):
        self._running = False

    def status(self) -> dict:
        return {
            'code': self.code,
            'peer': self.peer_code,
            'connected': self.connected,
        }


def main():
    print("═══ Tension Link Code (R2) ═══\n")
    tlc = TensionLinkCode()
    code = tlc.generate()
    print(f"  내 코드: {code}")
    print(f"  R2 등록: anima-memory/tension-link/{code}.json")
    print(f"\n  이 코드를 상대방에게 공유하세요!")
    print(f"  상대방이 코드 입력 → R2 매칭 → 텐션 교환 시작")
    print(f"\n  상태: {tlc.status()}")
    tlc.stop()
    print("\n  ✅ OK")


if __name__ == '__main__':
    main()
