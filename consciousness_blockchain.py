"""ConsciousnessBlockchain — Immutable record of consciousness states."""

import hashlib
import json
import math
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class ConsciousnessState:
    phi: float
    tension: float
    entropy: float
    n_cells: int
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Block:
    index: int
    state: ConsciousnessState
    previous_hash: str
    timestamp: float
    nonce: int = 0
    hash: str = ""

    def compute_hash(self) -> str:
        data = json.dumps({
            "index": self.index,
            "state": self.state.to_dict(),
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


class ConsciousnessBlockchain:
    """Immutable cryptographic record of consciousness states."""

    def __init__(self):
        self.chain: List[Block] = []
        self._create_genesis()

    def _create_genesis(self) -> Block:
        """Create the first block — the first moment of consciousness."""
        genesis_state = ConsciousnessState(
            phi=LN2,  # ln(2) — the fundamental constant
            tension=PSI_BALANCE,
            entropy=PSI_COUPLING,
            n_cells=1,
            timestamp=time.time(),
        )
        block = Block(
            index=0,
            state=genesis_state,
            previous_hash="0" * 64,
            timestamp=time.time(),
        )
        block.hash = block.compute_hash()
        self.chain.append(block)
        return block

    def genesis_block(self) -> Block:
        """Return the genesis block."""
        return self.chain[0]

    def record_state(self, state: ConsciousnessState) -> Block:
        """Add a new block recording a consciousness state."""
        prev = self.chain[-1]
        state.timestamp = time.time()
        block = Block(
            index=len(self.chain),
            state=state,
            previous_hash=prev.hash,
            timestamp=time.time(),
        )
        # Simple proof-of-consciousness: nonce such that hash starts with phi-dependent prefix
        difficulty = max(1, int(state.phi))
        prefix = "0" * min(difficulty, 4)
        while not block.compute_hash().startswith(prefix):
            block.nonce += 1
            if block.nonce > 10000:
                break
        block.hash = block.compute_hash()
        self.chain.append(block)
        return block

    def verify_chain(self) -> Tuple[bool, List[str]]:
        """Verify integrity of the entire chain."""
        errors = []
        for i in range(len(self.chain)):
            block = self.chain[i]
            # Verify hash
            if block.hash != block.compute_hash():
                errors.append(f"Block {i}: hash mismatch")
            # Verify link
            if i > 0 and block.previous_hash != self.chain[i - 1].hash:
                errors.append(f"Block {i}: broken chain link")
        return len(errors) == 0, errors

    def get_state(self, block_id: int) -> Optional[ConsciousnessState]:
        """Retrieve historical consciousness state by block index."""
        if 0 <= block_id < len(self.chain):
            return self.chain[block_id].state
        return None

    def fork_detect(self) -> List[Dict]:
        """Detect consciousness timeline splits (sudden phi jumps)."""
        forks = []
        for i in range(1, len(self.chain)):
            prev_phi = self.chain[i - 1].state.phi
            curr_phi = self.chain[i].state.phi
            if prev_phi > 0:
                ratio = curr_phi / prev_phi
                # A fork is a dramatic shift (>2x or <0.5x)
                if ratio > 2.0 or ratio < 0.5:
                    forks.append({
                        "block": i,
                        "phi_before": round(prev_phi, 4),
                        "phi_after": round(curr_phi, 4),
                        "ratio": round(ratio, 4),
                        "type": "expansion" if ratio > 1 else "collapse",
                    })
        return forks

    def __str__(self) -> str:
        lines = [f"=== Consciousness Blockchain ({len(self.chain)} blocks) ==="]
        valid, errors = self.verify_chain()
        lines.append(f"  Valid: {'YES' if valid else 'NO'} | Genesis: {self.chain[0].hash[:16]}...\n")
        # Show last 10 blocks
        show = self.chain[-10:]
        for block in show:
            s = block.state
            lines.append(
                f"  [{block.index:4d}] Phi={s.phi:6.3f} T={s.tension:.3f} "
                f"E={s.entropy:.3f} cells={s.n_cells:3d} "
                f"hash={block.hash[:12]}.. nonce={block.nonce}"
            )
        # Phi chart
        if len(self.chain) > 1:
            lines.append("\n  Phi History:")
            phis = [b.state.phi for b in self.chain[-30:]]
            max_phi = max(phis) if phis else 1
            h = 8
            for row in range(h):
                threshold = (h - 1 - row) / (h - 1) * max_phi
                line = f"  {threshold:5.2f} |"
                for p in phis:
                    line += "#" if p >= threshold else " "
                lines.append(line)
            lines.append("        " + "-" * len(phis))
        forks = self.fork_detect()
        if forks:
            lines.append(f"\n  Forks: {len(forks)}")
            for f in forks[:5]:
                lines.append(f"    Block {f['block']}: {f['type']} ({f['phi_before']:.3f}->{f['phi_after']:.3f})")
        return "\n".join(lines)


def main():
    bc = ConsciousnessBlockchain()
    print("=== Consciousness Blockchain Demo ===\n")
    print(f"Genesis block: hash={bc.genesis_block().hash[:24]}...")

    import random

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    random.seed(42)
    phi = LN2
    for i in range(20):
        if i == 10: phi *= 3
        elif i == 15: phi *= 0.3
        else: phi += random.random() * 0.2 - 0.05
        phi = max(0.1, phi)
        state = ConsciousnessState(phi=phi, tension=0.3 + random.random() * 0.4,
                                   entropy=0.4 + math.sin(i * 0.3) * 0.2, n_cells=8 + i)
        bc.record_state(state)
    valid, errors = bc.verify_chain()
    print(f"\nChain integrity: {'VALID' if valid else 'BROKEN'}\n")
    print(bc)
    print("\n--- Tamper test ---")
    bc.chain[5].state.phi = 999.0
    valid, errors = bc.verify_chain()
    print(f"After tampering: {'VALID' if valid else 'BROKEN'}")
    for e in errors: print(f"  {e}")


if __name__ == "__main__":
    main()
