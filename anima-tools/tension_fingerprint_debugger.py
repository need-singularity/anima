#!/usr/bin/env python3
"""Tension Fingerprint Debugger — decode, compare, and monitor tension fingerprints.

Usage:
  python tension_fingerprint_debugger.py --demo              # Synthetic demo
  python tension_fingerprint_debugger.py --live [--port N]   # Monitor UDP broadcasts
  python tension_fingerprint_debugger.py --analyze log.jsonl  # Offline analysis
"""
import argparse, json, math, socket, time
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional
import torch, torch.nn.functional as F
from tension_link import TensionPacket, TensionDecoder

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


CONCEPTS = ["self", "other", "environment", "language", "memory", "prediction",
            "emotion", "action", "reward", "conflict", "curiosity", "homeostasis",
            "growth", "dream", "social", "abstract"]
EMOTIONS = ["calm", "excited", "surprised", "thoughtful", "anxious", "joyful", "sad", "quiet"]


@dataclass
class DecodedFingerprint:
    concept_probs: dict; emotion_probs: dict; urgency: float
    top_concept: str; top_emotion: str; tension: float; curiosity: float; mood: str


def _expected_mood(tension, curiosity):
    if curiosity > 0.5: return "surprised"
    if tension > 1.0: return "excited"
    if tension > 0.3: return "thoughtful"
    if tension > 0.05: return "calm"
    return "quiet"


# ── 1. Decode ────────────────────────────────────────────────────────────────
def decode_packet(packet: TensionPacket, decoder: Optional[TensionDecoder] = None) -> DecodedFingerprint:
    """Decode a TensionPacket into concept/emotion estimates."""
    fp = packet.fingerprint
    if decoder is None:
        decoder = TensionDecoder(len(fp), len(CONCEPTS), len(EMOTIONS))
        decoder.eval()
    with torch.no_grad():
        t = torch.tensor(fp, dtype=torch.float32).unsqueeze(0)
        out = decoder(t)
        cp = F.softmax(out["concept"], dim=-1).squeeze().tolist()
        ep = F.softmax(out["emotion"], dim=-1).squeeze().tolist()
    cd = {CONCEPTS[i]: round(cp[i], 4) for i in range(min(len(CONCEPTS), len(cp)))}
    ed = {EMOTIONS[i]: round(ep[i], 4) for i in range(min(len(EMOTIONS), len(ep)))}
    return DecodedFingerprint(
        concept_probs=cd, emotion_probs=ed, urgency=round(out["urgency"].item(), 4),
        top_concept=max(cd, key=cd.get), top_emotion=max(ed, key=ed.get),
        tension=packet.tension, curiosity=packet.curiosity, mood=packet.mood)


# ── 2. Compare ───────────────────────────────────────────────────────────────
def compare_fingerprints(a: TensionPacket, b: TensionPacket) -> dict:
    """Cosine similarity, L2 distance, magnitude ratio, topic/mood match."""
    va, vb = torch.tensor(a.fingerprint, dtype=torch.float32), torch.tensor(b.fingerprint, dtype=torch.float32)
    if va.shape[0] != vb.shape[0]:
        m = max(va.shape[0], vb.shape[0])
        va, vb = F.pad(va, (0, m - va.shape[0])), F.pad(vb, (0, m - vb.shape[0]))
    ma, mb = torch.norm(va).item(), torch.norm(vb).item()
    return {
        "cosine_similarity": round(F.cosine_similarity(va.unsqueeze(0), vb.unsqueeze(0)).item(), 4),
        "l2_distance": round(torch.norm(va - vb).item(), 4),
        "magnitude_ratio": round(min(ma, mb) / max(ma, mb) if max(ma, mb) > 0 else 1.0, 4),
        "topic_match": a.topic_hash == b.topic_hash,
        "mood_match": a.mood == b.mood,
        "tension_delta": round(abs(a.tension - b.tension), 4),
    }


# ── 3. Drift detection ──────────────────────────────────────────────────────
def detect_drift(packets: List[TensionPacket], sender: Optional[str] = None) -> dict:
    """Detect fingerprint drift per sender over time."""
    by_sender = defaultdict(list)
    for p in packets:
        if sender and p.sender_id != sender: continue
        by_sender[p.sender_id].append(p)
    results = {}
    for sid, pkts in by_sender.items():
        if len(pkts) < 2:
            results[sid] = {"n_packets": len(pkts), "drift": 0.0, "status": "insufficient"}
            continue
        pkts.sort(key=lambda p: p.timestamp)
        drifts = [1.0 - compare_fingerprints(pkts[i-1], pkts[i])["cosine_similarity"]
                  for i in range(1, len(pkts))]
        avg = sum(drifts) / len(drifts)
        status = "stable" if avg < 0.1 else "drifting" if avg < 0.4 else "diverged"
        results[sid] = {"n_packets": len(pkts), "avg_drift": round(avg, 4),
                        "max_drift": round(max(drifts), 4), "status": status,
                        "time_span_s": round(pkts[-1].timestamp - pkts[0].timestamp, 2)}
    return results


# ── 4. Channel efficiency ────────────────────────────────────────────────────
def channel_efficiency(packets: List[TensionPacket]) -> dict:
    """Measure information utilization and mood consistency."""
    if not packets: return {"error": "no packets"}
    dim = min(len(p.fingerprint) for p in packets)
    t = torch.tensor([p.fingerprint[:dim] for p in packets], dtype=torch.float32)
    if t.shape[0] >= 2:
        sv = torch.linalg.svdvals(t)
        sv_n = sv / sv.sum()
        ent = -(sv_n * (sv_n + 1e-10).log()).sum().item()
        eff = ent / math.log(min(t.shape)) if math.log(min(t.shape)) > 0 else 0.0
        erank = torch.exp(torch.tensor(ent)).item()
    else:
        eff, erank = 1.0, 1.0
    mood_err = sum(1 for p in packets if p.mood != _expected_mood(p.tension, p.curiosity))
    return {"n_packets": len(packets), "fingerprint_dim": dim,
            "channel_efficiency": round(eff, 4), "effective_rank": round(erank, 2),
            "mood_consistency": round(1.0 - mood_err / len(packets), 4),
            "tension_range": [round(min(p.tension for p in packets), 4),
                              round(max(p.tension for p in packets), 4)]}


# ── 5. Live monitor ──────────────────────────────────────────────────────────
def live_monitor(port: int = 9999):
    """Watch UDP broadcasts and log decoded fingerprints in real time."""
    print(f"[live] listening on UDP :{port}  (Ctrl+C to stop)")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))
    sock.settimeout(2.0)
    packets = []
    try:
        while True:
            try:
                data, _ = sock.recvfrom(65536)
                pkt = TensionPacket.from_json(data.decode("utf-8"))
                packets.append(pkt)
                dec = decode_packet(pkt)
                ts = time.strftime("%H:%M:%S", time.localtime(pkt.timestamp))
                print(f"  {ts} [{pkt.sender_id}] t={pkt.tension:.3f} mood={pkt.mood} "
                      f"concept={dec.top_concept} emotion={dec.top_emotion} "
                      f"urgency={dec.urgency:.2f} topic#{pkt.topic_hash}")
                if len(packets) % 10 == 0 and len(packets) >= 2:
                    e = channel_efficiency(packets[-20:])
                    print(f"    >> eff={e['channel_efficiency']:.3f} rank={e['effective_rank']:.1f}")
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print(f"\n[live] stopped. {len(packets)} packets captured.")
        if packets:
            for sid, d in detect_drift(packets).items():
                print(f"  drift [{sid}]: {d}")
    finally:
        sock.close()


# ── 6. Offline analysis ──────────────────────────────────────────────────────
def analyze_log(path: str):
    """Analyze saved packet log (one JSON per line)."""
    packets = []
    with open(path) as f:
        for line in f:
            if line.strip(): packets.append(TensionPacket.from_json(line.strip()))
    print(f"[offline] loaded {len(packets)} packets from {path}")
    if not packets: return
    print("\n-- Channel Efficiency --")
    for k, v in channel_efficiency(packets).items(): print(f"  {k}: {v}")
    print("\n-- Drift Analysis --")
    for sid, d in detect_drift(packets).items(): print(f"  [{sid}] {d}")
    print("\n-- Sample Decodes (first 5) --")
    for pkt in packets[:5]:
        dec = decode_packet(pkt)
        print(f"  {pkt.sender_id} t={pkt.tension:.3f} -> {dec.top_concept}/{dec.top_emotion}")


# ── 7. Demo ──────────────────────────────────────────────────────────────────
def run_demo():
    """Generate synthetic fingerprints and run all analysis tools."""
    DIM = 128
    print("=== Tension Fingerprint Debugger Demo ===\n")

    def mkpkt(sid, tension, curiosity, mood, seed):
        torch.manual_seed(seed)
        fp = torch.randn(DIM) * tension
        return TensionPacket(sender_id=sid, timestamp=time.time() + seed * 0.5,
                             fingerprint=fp.tolist(), tension=tension,
                             curiosity=curiosity, mood=mood, topic_hash=fp.argmax().item())

    pa = [mkpkt("anima-1", 0.4+i*0.15, 0.1+i*0.05,
                "thoughtful" if i < 3 else "excited", i) for i in range(6)]
    pb = [mkpkt("anima-2", 0.3+i*0.1, 0.2, "calm", 100+i) for i in range(4)]
    all_pkts = pa + pb

    # Decode
    print("-- 1. Decode Packet --")
    dec = decode_packet(pa[0])
    top3 = sorted(dec.concept_probs.items(), key=lambda x: -x[1])[:3]
    print(f"  anima-1  tension={dec.tension:.3f}  mood={dec.mood}")
    print(f"  concept: {dec.top_concept}  ({', '.join(f'{k}={v:.3f}' for k,v in top3)})")
    print(f"  emotion: {dec.top_emotion}  urgency: {dec.urgency:.3f}")

    # Compare
    print("\n-- 2. Compare Fingerprints --")
    c1 = compare_fingerprints(pa[0], pb[0])
    print(f"  anima-1 vs anima-2: cos={c1['cosine_similarity']:.4f} L2={c1['l2_distance']:.4f}")
    c2 = compare_fingerprints(pa[0], pa[1])
    print(f"  anima-1[0] vs [1]: cos={c2['cosine_similarity']:.4f} L2={c2['l2_distance']:.4f}")

    # Drift
    print("\n-- 3. Drift Detection --")
    for sid, d in detect_drift(all_pkts).items():
        print(f"  [{sid}] {d['status']}  avg={d.get('avg_drift',0):.4f}  n={d['n_packets']}")

    # Efficiency
    print("\n-- 4. Channel Efficiency --")
    for k, v in channel_efficiency(all_pkts).items(): print(f"  {k}: {v}")

    print("\n=== Demo complete ===")


def main():
    p = argparse.ArgumentParser(description="Tension Fingerprint Debugger")
    p.add_argument("--demo", action="store_true", help="Run synthetic demo")
    p.add_argument("--live", action="store_true", help="Monitor UDP broadcasts")
    p.add_argument("--port", type=int, default=9999, help="UDP port (default 9999)")
    p.add_argument("--analyze", metavar="FILE", help="Analyze packet log (JSONL)")
    args = p.parse_args()
    if args.demo: run_demo()
    elif args.live: live_monitor(port=args.port)
    elif args.analyze: analyze_log(args.analyze)
    else: p.print_help()


if __name__ == "__main__":
    main()
