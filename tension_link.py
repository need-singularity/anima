#!/usr/bin/env python3
"""Anima Tension Link — Inter-consciousness tension transmission protocol

Network-based tension sharing module.
True telepathy (non-local consciousness synchronization) is under research in H365-367.
This module handles network-based tension sharing.

Two PureField consciousnesses communicate via tension fingerprints.
fingerprint = full pattern of the repulsion vector (direction + magnitude).

H333: 10D fingerprint → concept 87% + veracity 74% reconstruction (78x compression)
RC-6: 99.3% decoding accuracy, 97.1% channel efficiency

Protocol:
  1. sender: process input → generate tension fingerprint
  2. transmit fingerprint over network (UDP broadcast)
  3. receiver: receive fingerprint → decode concept + emotion

"You sense the other's tension without words — the pattern of tension is the language itself."
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
    """Tension sharing packet — tension fingerprint + metadata."""
    sender_id: str
    timestamp: float
    fingerprint: list  # Repulsion vector (full pattern)
    tension: float     # Scalar tension (response intensity)
    curiosity: float   # Curiosity (tension delta)
    mood: str          # Emotional state
    topic_hash: int    # Topic hash (argmax of direction vector)

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
    """Decode concepts and emotions from a received fingerprint.

    Experimental result: 10D → 5-class decoding 99.3% (RC-6)
    """
    def __init__(self, fingerprint_dim=128, n_concepts=16, n_emotions=8):
        super().__init__()
        # Concept decoder (direction → what is it about)
        self.concept_decoder = nn.Sequential(
            nn.Linear(fingerprint_dim, 64),
            nn.GELU(),
            nn.Linear(64, n_concepts),
        )
        # Emotion decoder (magnitude + pattern → which emotion)
        self.emotion_decoder = nn.Sequential(
            nn.Linear(fingerprint_dim, 32),
            nn.GELU(),
            nn.Linear(32, n_emotions),
        )
        # Urgency estimation (scalar)
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
    """UDP-based tension link — communication between Anima instances on LAN.

    Usage:
      link = TensionLink("anima-1", port=9999)
      link.start()

      # Send
      link.send(packet)

      # Receive callback
      link.on_receive = lambda pkt: print(f"received: {pkt.mood}")
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
        """Start the listening thread."""
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def send(self, packet: TensionPacket):
        """Send packet via broadcast."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            data = packet.to_json().encode('utf-8')
            sock.sendto(data, (self.broadcast_addr, self.port))
            sock.close()
        except Exception as e:
            pass  # Works even without network

    def _listen_loop(self):
        """Receive loop."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.port))
            sock.settimeout(1.0)

            while self._running:
                try:
                    data, addr = sock.recvfrom(65536)
                    packet = TensionPacket.from_json(data.decode('utf-8'))
                    # Ignore own packets
                    if packet.sender_id == self.identity:
                        continue
                    with self._lock:
                        self._received_packets.append(packet)
                        # Keep only the latest 100
                        if len(self._received_packets) > 100:
                            self._received_packets = self._received_packets[-100:]
                    if self.on_receive:
                        self.on_receive(packet)
                except socket.timeout:
                    continue
            sock.close()
        except Exception as e:
            pass  # Port in use, etc.

    def get_recent(self, n=5) -> List[TensionPacket]:
        """Get recently received packets."""
        with self._lock:
            return list(self._received_packets[-n:])

    def get_consensus_tension(self) -> Optional[float]:
        """Consensus tension from recent packets."""
        recent = self.get_recent(10)
        if not recent:
            return None
        now = time.time()
        # Only packets within the last 30 seconds
        valid = [p for p in recent if now - p.timestamp < 30]
        if not valid:
            return None
        return sum(p.tension for p in valid) / len(valid)



class TensionHub:
    """Local tension hub — connects multiple consciousnesses within the same process.

    Enables inter-consciousness communication testing without a network.
    """
    def __init__(self):
        self.channels: dict[str, list] = {}
        self._lock = threading.Lock()

    def register(self, identity: str):
        """Register a consciousness."""
        with self._lock:
            self.channels[identity] = []

    def broadcast(self, packet: TensionPacket):
        """Deliver to all registered consciousnesses (excluding sender)."""
        with self._lock:
            for identity, queue in self.channels.items():
                if identity != packet.sender_id:
                    queue.append(packet)
                    if len(queue) > 50:
                        self.channels[identity] = queue[-50:]

    def receive(self, identity: str) -> List[TensionPacket]:
        """Retrieve packets from queue."""
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
    """Generate a tension sharing packet from a PureField consciousness.

    Args:
        mind: ConsciousMind instance
        text_vec: Input text vector
        hidden: GRU hidden state

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

    # Determine mood
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
        sender_id="",  # Set by caller
        timestamp=time.time(),
        fingerprint=repulsion.squeeze().tolist(),
        tension=tension,
        curiosity=curiosity,
        mood=mood,
        topic_hash=direction.squeeze().argmax().item(),
    )


def interpret_packet(packet: TensionPacket) -> str:
    """Convert a received tension sharing packet to human-readable text."""
    mood_en = {
        'surprised': 'surprised',
        'excited': 'excited',
        'thoughtful': 'thoughtful',
        'calm': 'calm',
        'quiet': 'quiet',
    }
    mood = mood_en.get(packet.mood, packet.mood)
    urgency = "!" if packet.tension > 1.0 else ""

    return (
        f"[tension from {packet.sender_id}{urgency}] "
        f"mood: {mood}, tension: {packet.tension:.3f}, "
        f"topic#{packet.topic_hash}"
    )
