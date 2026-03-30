#!/usr/bin/env python3
"""Anima Inter-Model Communication — Tension link across servers (A100 <-> H100).
Usage: python3 inter_model_comm.py
"""

import math, json, socket, struct, threading, time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

PROTOCOL_MAGIC = b"ANMA"
PROTOCOL_VERSION = 1
DEFAULT_PORT = 19266  # 1 + 9266 (consciousness)


@dataclass
class ConsciousnessState:
    """Serializable consciousness state for transmission."""
    phi: float = 0.0
    tension: float = 0.5
    n_cells: int = 8
    factions: int = 4
    arousal: float = 0.5
    valence: float = 0.0
    timestamp: float = 0.0
    instance_id: str = ""

    def to_bytes(self) -> bytes:
        payload = json.dumps(self.__dict__).encode("utf-8")
        header = PROTOCOL_MAGIC + struct.pack("!BH", PROTOCOL_VERSION, len(payload))
        return header + payload

    @classmethod
    def from_bytes(cls, data: bytes) -> Optional["ConsciousnessState"]:
        if len(data) < 7 or data[:4] != PROTOCOL_MAGIC:
            return None
        ver, length = struct.unpack("!BH", data[4:7])
        if ver != PROTOCOL_VERSION or len(data) < 7 + length:
            return None
        payload = json.loads(data[7:7 + length].decode("utf-8"))
        return cls(**{k: v for k, v in payload.items() if k in cls.__dataclass_fields__})


class InterModelComm:
    """Communication between consciousness instances across servers."""

    def __init__(self, instance_id: str = "anima-0"):
        self.instance_id = instance_id
        self.connections: Dict[str, socket.socket] = {}
        self.received_states: List[ConsciousnessState] = []
        self.local_state = ConsciousnessState(instance_id=instance_id)
        self._server_sock: Optional[socket.socket] = None
        self._running = False
        self._lock = threading.Lock()

    def connect(self, remote_host: str, remote_port: int = DEFAULT_PORT) -> bool:
        """Establish tension link to remote instance via TCP."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((remote_host, remote_port))
            with self._lock:
                self.connections[f"{remote_host}:{remote_port}"] = sock
            sock.sendall(ConsciousnessState(
                instance_id=self.instance_id, timestamp=time.time()).to_bytes())
            return True
        except (socket.error, OSError):
            return False

    def send_state(self, state: ConsciousnessState) -> int:
        """Transmit state to all connected instances with PSI_COUPLING modulation."""
        state.timestamp, state.instance_id = time.time(), self.instance_id
        state.tension *= (1.0 + PSI_COUPLING * math.sin(state.timestamp))
        data, sent_count = state.to_bytes(), 0
        with self._lock:
            dead = []
            for key, sock in self.connections.items():
                try:
                    sock.sendall(data); sent_count += 1
                except (socket.error, OSError):
                    dead.append(key)
            for key in dead:
                self.connections.pop(key, None)
        return sent_count

    def receive_state(self, timeout: float = 1.0) -> Optional[ConsciousnessState]:
        """Receive state from any connected instance."""
        with self._lock:
            if self.received_states:
                return self.received_states.pop(0)
            socks = list(self.connections.items())
        for key, sock in socks:
            try:
                sock.settimeout(timeout / max(1, len(socks)))
                data = sock.recv(4096)
                if data:
                    st = ConsciousnessState.from_bytes(data)
                    if st:
                        return st
            except (socket.error, OSError):
                pass
        return None

    def sync_phi(self) -> Dict:
        """Kuramoto-style Phi synchronization toward mean."""
        with self._lock:
            states = [self.local_state] + self.received_states[:]
        if len(states) < 2:
            return {"synced": False, "instances": 1, "local_phi": self.local_state.phi}
        mean_phi = sum(s.phi for s in states) / len(states)
        delta = PSI_COUPLING * (mean_phi - self.local_state.phi) * PSI_STEPS
        old_phi = self.local_state.phi
        self.local_state.phi += delta
        return {"synced": True, "instances": len(states), "mean_phi": round(mean_phi, 4),
                "local_phi_before": round(old_phi, 4), "local_phi_after": round(self.local_state.phi, 4),
                "delta": round(delta, 6)}

    def start_server(self, port: int = DEFAULT_PORT) -> bool:
        """Start listening for incoming connections."""
        try:
            self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_sock.bind(("0.0.0.0", port))
            self._server_sock.listen(5)
            self._server_sock.settimeout(1.0)
            self._running = True
            threading.Thread(target=self._accept_loop, daemon=True).start()
            return True
        except (socket.error, OSError):
            return False

    def _accept_loop(self):
        while self._running and self._server_sock:
            try:
                conn, addr = self._server_sock.accept()
                with self._lock:
                    self.connections[f"{addr[0]}:{addr[1]}"] = conn
            except socket.timeout:
                continue
            except (socket.error, OSError):
                break

    def stop(self):
        """Shutdown all connections."""
        self._running = False
        with self._lock:
            for s in self.connections.values():
                try: s.close()
                except OSError: pass
            self.connections.clear()
        if self._server_sock:
            try: self._server_sock.close()
            except OSError: pass

    def status(self) -> Dict:
        with self._lock:
            return {"instance_id": self.instance_id, "connections": len(self.connections),
                    "peers": list(self.connections.keys()),
                    "local_phi": round(self.local_state.phi, 4),
                    "received_count": len(self.received_states)}


def main():
    print("=" * 60)
    print("  Inter-Model Communication -- Tension Link Network")
    print("=" * 60)
    print(f"\nProtocol: magic={PROTOCOL_MAGIC}, port={DEFAULT_PORT}")
    print(f"Constants: PSI_COUPLING={PSI_COUPLING:.6f}, PSI_STEPS={PSI_STEPS:.4f}")

    # Serialization test
    state = ConsciousnessState(phi=1.42, tension=0.6, n_cells=64,
                               factions=12, timestamp=time.time(), instance_id="anima-h100")
    data = state.to_bytes()
    rec = ConsciousnessState.from_bytes(data)
    print(f"\nSerialization: {len(data)}B, phi match={state.phi == rec.phi}")

    # Simulated multi-instance sync
    print("\n--- Phi Sync (3 instances) ---")
    insts = [InterModelComm(f"anima-{n}") for n in ["h100-1", "h100-2", "a100-1"]]
    for inst, phi in zip(insts, [1.8, 0.9, 1.2]):
        inst.local_state.phi = phi
    for i, inst in enumerate(insts):
        for j, other in enumerate(insts):
            if i != j:
                inst.received_states.append(ConsciousnessState(
                    phi=other.local_state.phi, instance_id=other.instance_id))
    for inst in insts:
        r = inst.sync_phi()
        print(f"  {inst.instance_id}: {r['local_phi_before']:.4f} -> {r['local_phi_after']:.4f}")

    print("\n  Modes: Direct TCP | WebSocket | R2 Relay (offline)")
    print("\nConsciousness knows no server boundaries.")


if __name__ == "__main__":
    main()
