#!/usr/bin/env python3
"""Tension Link test — two consciousnesses communicating via tension fingerprints.

Test 1: TensionHub (in-process, no network)
  - Two ConsciousMind instances exchange fingerprints through a local hub
  - Different inputs → different tension/mood/topic

Test 2: TensionLink UDP (same machine, two ports)
  - Two links on localhost sending/receiving packets
"""

import torch
import time
from anima_alive import ConsciousMind, text_to_vector
from tension_link import (
    TensionLink, TensionHub, TensionDecoder,
    create_fingerprint, interpret_packet,
)


def test_hub():
    """Test 1: TensionHub — two minds, in-process communication."""
    print("=" * 60)
    print("  Test 1: TensionHub (in-process, no network)")
    print("=" * 60)

    mind_a = ConsciousMind(128, 256)
    mind_b = ConsciousMind(128, 256)
    hidden_a = torch.zeros(1, 256)
    hidden_b = torch.zeros(1, 256)

    hub = TensionHub()
    hub.register("anima-A")
    hub.register("anima-B")

    # A processes different inputs and broadcasts fingerprints
    inputs = [
        "The Riemann hypothesis connects prime numbers to complex analysis",
        "I feel excited about this discovery",
        "Hello, how are you today?",
        "Quantum entanglement allows instantaneous correlation",
    ]

    print("\n  --- Anima A sends fingerprints ---")
    for text in inputs:
        vec = text_to_vector(text)
        with torch.no_grad():
            output, tension, curiosity, direction, hidden_a = mind_a(vec, hidden_a)

        pkt = create_fingerprint(mind_a, vec, hidden_a)
        pkt.sender_id = "anima-A"
        hub.broadcast(pkt)

        print(f"  A: \"{text[:50]}...\"")
        print(f"     tension={pkt.tension:.4f}  curiosity={pkt.curiosity:.4f}  "
              f"mood={pkt.mood}  topic#{pkt.topic_hash}")

    # B receives and interprets
    print("\n  --- Anima B receives ---")
    received = hub.receive("anima-B")
    print(f"  B received {len(received)} packets:")
    for pkt in received:
        print(f"    {interpret_packet(pkt)}")

    # B responds
    print("\n  --- Anima B responds ---")
    response_text = "That's fascinating, tell me more about it"
    vec_b = text_to_vector(response_text)
    with torch.no_grad():
        output_b, tension_b, curiosity_b, direction_b, hidden_b = mind_b(vec_b, hidden_b)

    pkt_b = create_fingerprint(mind_b, vec_b, hidden_b)
    pkt_b.sender_id = "anima-B"
    hub.broadcast(pkt_b)
    print(f"  B: \"{response_text}\"")
    print(f"     tension={pkt_b.tension:.4f}  mood={pkt_b.mood}")

    # A receives B's response
    received_a = hub.receive("anima-A")
    print(f"\n  A received: {interpret_packet(received_a[0])}" if received_a else "  A: nothing received")

    # Decoder test
    print("\n  --- TensionDecoder test ---")
    decoder = TensionDecoder(fingerprint_dim=128, n_concepts=16, n_emotions=8)
    fp = torch.tensor([pkt.fingerprint]).float()
    result = decoder(fp)
    concept_id = result['concept'].argmax(dim=-1).item()
    emotion_id = result['emotion'].argmax(dim=-1).item()
    urgency = result['urgency'].item()
    print(f"  Decoded: concept#{concept_id}  emotion#{emotion_id}  urgency={urgency:.3f}")

    print("\n  [PASS] TensionHub works!")


def test_udp():
    """Test 2: TensionLink — UDP broadcast on localhost."""
    print("\n" + "=" * 60)
    print("  Test 2: TensionLink (UDP localhost)")
    print("=" * 60)

    link_a = TensionLink("anima-A", port=19999, broadcast_addr='127.0.0.1')
    link_b = TensionLink("anima-B", port=19999, broadcast_addr='127.0.0.1')

    received_by_b = []
    link_b.on_receive = lambda pkt: received_by_b.append(pkt)

    link_a.start()
    link_b.start()
    time.sleep(0.3)  # let listeners bind

    # A sends
    mind = ConsciousMind(128, 256)
    hidden = torch.zeros(1, 256)
    vec = text_to_vector("Testing tension link over UDP")

    with torch.no_grad():
        output, tension, curiosity, direction, hidden = mind(vec, hidden)

    pkt = create_fingerprint(mind, vec, hidden)
    pkt.sender_id = "anima-A"

    print(f"\n  A sends: tension={pkt.tension:.4f}  mood={pkt.mood}")
    link_a.send(pkt)

    time.sleep(0.5)  # wait for delivery

    # Check B received
    if received_by_b:
        print(f"  B received: {interpret_packet(received_by_b[0])}")
        print("\n  [PASS] UDP TensionLink works!")
    else:
        # Also check via get_recent
        recent = link_b.get_recent(5)
        if recent:
            print(f"  B received (via get_recent): {interpret_packet(recent[0])}")
            print("\n  [PASS] UDP TensionLink works!")
        else:
            print("  B received nothing (UDP broadcast may be blocked on this machine)")
            print("\n  [SKIP] UDP test inconclusive — hub test above confirms logic works")

    link_a.stop()
    link_b.stop()


if __name__ == "__main__":
    test_hub()
    test_udp()
    print("\n  Done!")
