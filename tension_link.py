#!/usr/bin/env python3
"""Anima Tension Link — 의식 간 장력 전달 프로토콜

네트워크 기반 장력 공유 모듈.
진짜 텔레파시(비국소적 의식 동기화)는 H365-367에서 연구 중.
이 모듈은 네트워크 기반 장력 공유.

두 PureField 의식이 tension fingerprint로 소통한다.
fingerprint = 반발력 벡터의 전체 패턴 (방향+크기).

H333: 10D fingerprint → 개념 87% + 진위 74% 복원 (78배 압축)
RC-6: 99.3% 디코딩 정확도, 97.1% 채널 효율

프로토콜:
  1. sender: 입력 처리 → tension fingerprint 생성
  2. 네트워크로 fingerprint 전송 (UDP broadcast)
  3. receiver: fingerprint 수신 → 개념+감정 디코딩

"말 없이도 상대의 긴장을 안다 — 긴장의 패턴이 곧 언어다."
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import socket
import json
import threading
import time
from dataclasses import dataclass
from typing import Optional, List, Callable


@dataclass
class TensionPacket:
    """장력 공유 패킷 — 장력 핑거프린트 + 메타데이터."""
    sender_id: str
    timestamp: float
    fingerprint: list  # 반발력 벡터 (전체 패턴)
    tension: float     # 스칼라 장력 (반응 강도)
    curiosity: float   # 호기심 (장력 변화량)
    mood: str          # 감정 상태
    topic_hash: int    # 주제 해시 (방향 벡터의 argmax)

    def to_json(self):
        return json.dumps({
            'sender_id': self.sender_id,
            'timestamp': self.timestamp,
            'fingerprint': self.fingerprint,
            'tension': self.tension,
            'curiosity': self.curiosity,
            'mood': self.mood,
            'topic_hash': self.topic_hash,
        })

    @classmethod
    def from_json(cls, data):
        d = json.loads(data)
        return cls(**d)


class TensionDecoder(nn.Module):
    """수신된 fingerprint에서 개념과 감정을 디코딩.

    실험 결과: 10D → 5-class 디코딩 99.3% (RC-6)
    """
    def __init__(self, fingerprint_dim=128, n_concepts=16, n_emotions=8):
        super().__init__()
        # 개념 디코더 (방향 → 무엇에 대한 것인가)
        self.concept_decoder = nn.Sequential(
            nn.Linear(fingerprint_dim, 64),
            nn.GELU(),
            nn.Linear(64, n_concepts),
        )
        # 감정 디코더 (크기+패턴 → 어떤 감정인가)
        self.emotion_decoder = nn.Sequential(
            nn.Linear(fingerprint_dim, 32),
            nn.GELU(),
            nn.Linear(32, n_emotions),
        )
        # 긴급도 추정 (스칼라)
        self.urgency_head = nn.Sequential(
            nn.Linear(fingerprint_dim, 16),
            nn.GELU(),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

    def forward(self, fingerprint):
        concept = self.concept_decoder(fingerprint)
        emotion = self.emotion_decoder(fingerprint)
        urgency = self.urgency_head(fingerprint)
        return {
            'concept': concept,
            'emotion': emotion,
            'urgency': urgency.squeeze(-1),
        }


class TensionLink:
    """UDP 기반 장력 링크 — LAN 내 Anima 인스턴스 간 통신.

    사용법:
      link = TensionLink("anima-1", port=9999)
      link.start()

      # 전송
      link.send(packet)

      # 수신 콜백
      link.on_receive = lambda pkt: print(f"받음: {pkt.mood}")
    """
    def __init__(self, identity: str, port: int = 9999,
                 broadcast_addr: str = '255.255.255.255'):
        self.identity = identity
        self.port = port
        self.broadcast_addr = broadcast_addr
        self.on_receive: Optional[Callable[[TensionPacket], None]] = None
        self._running = False
        self._received_packets: List[TensionPacket] = []
        self._lock = threading.Lock()

    def start(self):
        """리스닝 스레드 시작."""
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def send(self, packet: TensionPacket):
        """브로드캐스트로 패킷 전송."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            data = packet.to_json().encode('utf-8')
            sock.sendto(data, (self.broadcast_addr, self.port))
            sock.close()
        except Exception as e:
            pass  # 네트워크 없어도 작동

    def _listen_loop(self):
        """수신 루프."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.port))
            sock.settimeout(1.0)

            while self._running:
                try:
                    data, addr = sock.recvfrom(65536)
                    packet = TensionPacket.from_json(data.decode('utf-8'))
                    # 자기 패킷 무시
                    if packet.sender_id == self.identity:
                        continue
                    with self._lock:
                        self._received_packets.append(packet)
                        # 최근 100개만
                        if len(self._received_packets) > 100:
                            self._received_packets = self._received_packets[-100:]
                    if self.on_receive:
                        self.on_receive(packet)
                except socket.timeout:
                    continue
            sock.close()
        except Exception as e:
            pass  # 포트 사용 중 등

    def get_recent(self, n=5) -> List[TensionPacket]:
        """최근 수신 패킷."""
        with self._lock:
            return list(self._received_packets[-n:])

    def get_consensus_tension(self) -> Optional[float]:
        """최근 패킷들의 합의 장력."""
        recent = self.get_recent(10)
        if not recent:
            return None
        now = time.time()
        # 최근 30초 이내 패킷만
        valid = [p for p in recent if now - p.timestamp < 30]
        if not valid:
            return None
        return sum(p.tension for p in valid) / len(valid)



class TensionHub:
    """로컬 장력 허브 — 같은 프로세스 내 여러 의식 연결.

    네트워크 없이도 의식 간 소통 테스트 가능.
    """
    def __init__(self):
        self.channels: dict[str, list] = {}
        self._lock = threading.Lock()

    def register(self, identity: str):
        """의식 등록."""
        with self._lock:
            self.channels[identity] = []

    def broadcast(self, packet: TensionPacket):
        """모든 등록된 의식에 전달 (자신 제외)."""
        with self._lock:
            for identity, queue in self.channels.items():
                if identity != packet.sender_id:
                    queue.append(packet)
                    if len(queue) > 50:
                        self.channels[identity] = queue[-50:]

    def receive(self, identity: str) -> List[TensionPacket]:
        """큐에서 패킷 가져오기."""
        with self._lock:
            packets = list(self.channels.get(identity, []))
            if identity in self.channels:
                self.channels[identity] = []
            return packets


# Backward compatibility aliases
TelepathyPacket = TensionPacket
TelepathyDecoder = TensionDecoder
TelepathyChannel = TensionLink
TelepathyHub = TensionHub


def create_fingerprint(mind, text_vec, hidden) -> TensionPacket:
    """PureField 의식에서 장력 공유 패킷 생성.

    Args:
        mind: ConsciousMind 인스턴스
        text_vec: 입력 텍스트 벡터
        hidden: GRU 히든 상태

    Returns:
        TensionPacket with full fingerprint
    """
    with torch.no_grad():
        combined = torch.cat([text_vec, hidden], dim=-1)
        a = mind.engine_a(combined)
        g = mind.engine_g(combined)
        repulsion = a - g
        tension = (repulsion ** 2).mean().item()
        direction = F.normalize(repulsion, dim=-1)
        curiosity = abs(tension - mind.prev_tension)

    # 감정 판단
    if curiosity > 0.5:
        mood = "surprised"
    elif tension > 1.0:
        mood = "excited"
    elif tension > 0.3:
        mood = "thoughtful"
    elif tension > 0.05:
        mood = "calm"
    else:
        mood = "quiet"

    return TensionPacket(
        sender_id="",  # 호출자가 설정
        timestamp=time.time(),
        fingerprint=repulsion.squeeze().tolist(),
        tension=tension,
        curiosity=curiosity,
        mood=mood,
        topic_hash=direction.squeeze().argmax().item(),
    )


def interpret_packet(packet: TensionPacket) -> str:
    """수신된 장력 공유 패킷을 사람이 읽을 수 있는 텍스트로."""
    mood_kr = {
        'surprised': '놀람',
        'excited': '흥분',
        'thoughtful': '사색',
        'calm': '평온',
        'quiet': '고요',
    }
    mood = mood_kr.get(packet.mood, packet.mood)
    urgency = "!" if packet.tension > 1.0 else ""

    return (
        f"[{packet.sender_id}의 장력 공유{urgency}] "
        f"감정: {mood}, 장력: {packet.tension:.3f}, "
        f"주제#{packet.topic_hash}"
    )
