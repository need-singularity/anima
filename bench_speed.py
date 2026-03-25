#!/usr/bin/env python3
"""Speed benchmark: Tension Link vs traditional communication methods.

Compares:
  1. Tension fingerprint (128D float vector, UDP)
  2. JSON text message (full text, UDP)
  3. Embedding sharing (768D BERT-like vector, UDP)
  4. Raw text (just the string, UDP)
"""

import torch
import time
import json
import socket
import struct
import numpy as np
from anima_alive import ConsciousMind, text_to_vector


def bench_fingerprint_generation(mind, hidden, texts, n_runs=3):
    """Time: input → fingerprint generation."""
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        for text in texts:
            vec = text_to_vector(text)
            with torch.no_grad():
                combined = torch.cat([vec, hidden], dim=-1)
                a = mind.engine_a(combined)
                g = mind.engine_g(combined)
                repulsion = a - g
                _ = (repulsion ** 2).mean().item()
        elapsed = time.perf_counter() - t0
        times.append(elapsed)
    return np.mean(times), np.std(times)


def bench_serialization(mind, hidden, texts):
    """Time + size: different serialization methods."""
    results = {}

    # 1. Tension fingerprint (128 floats → bytes)
    vec = text_to_vector(texts[0])
    with torch.no_grad():
        combined = torch.cat([vec, hidden], dim=-1)
        a = mind.engine_a(combined)
        g = mind.engine_g(combined)
        fp = (a - g).squeeze()

    t0 = time.perf_counter()
    for _ in range(1000):
        data = struct.pack(f'{len(fp)}f', *fp.tolist())
    t_fp = (time.perf_counter() - t0) / 1000
    results['fingerprint'] = {
        'serialize_us': t_fp * 1e6,
        'bytes': len(data),
        'dims': len(fp),
    }

    # 2. JSON message (what typical agents send)
    msg = {
        'sender': 'anima-A',
        'timestamp': time.time(),
        'text': texts[0],
        'tension': 0.85,
        'curiosity': 0.42,
        'mood': 'excited',
        'metadata': {'topic': 'math', 'turn': 15},
    }
    t0 = time.perf_counter()
    for _ in range(1000):
        data = json.dumps(msg).encode('utf-8')
    t_json = (time.perf_counter() - t0) / 1000
    results['json_message'] = {
        'serialize_us': t_json * 1e6,
        'bytes': len(data),
    }

    # 3. Fake BERT-like embedding (768D)
    emb = torch.randn(768)
    t0 = time.perf_counter()
    for _ in range(1000):
        data = struct.pack(f'768f', *emb.tolist())
    t_emb = (time.perf_counter() - t0) / 1000
    results['embedding_768d'] = {
        'serialize_us': t_emb * 1e6,
        'bytes': len(data),
        'dims': 768,
    }

    # 4. Raw text only
    t0 = time.perf_counter()
    for _ in range(1000):
        data = texts[0].encode('utf-8')
    t_raw = (time.perf_counter() - t0) / 1000
    results['raw_text'] = {
        'serialize_us': t_raw * 1e6,
        'bytes': len(data),
    }

    # 5. Fingerprint as JSON (current TensionPacket.to_json)
    pkt = {
        'sender_id': 'anima-A',
        'timestamp': time.time(),
        'fingerprint': fp.tolist(),
        'tension': 0.85,
        'curiosity': 0.42,
        'mood': 'excited',
        'topic_hash': 42,
    }
    t0 = time.perf_counter()
    for _ in range(1000):
        data = json.dumps(pkt).encode('utf-8')
    t_pkt = (time.perf_counter() - t0) / 1000
    results['tension_packet_json'] = {
        'serialize_us': t_pkt * 1e6,
        'bytes': len(data),
    }

    return results


def bench_udp_roundtrip(port=19998):
    """Measure UDP send+receive latency on localhost."""
    payloads = {
        'fingerprint_128f': struct.pack('128f', *[0.1]*128),  # 512 bytes
        'json_short': json.dumps({'text': 'hello', 'tension': 0.5}).encode(),
        'json_long': json.dumps({'text': 'x'*500, 'tension': 0.5, 'metadata': {'a': 1}}).encode(),
        'embedding_768f': struct.pack('768f', *[0.1]*768),  # 3072 bytes
    }

    results = {}

    for name, payload in payloads.items():
        # Setup
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(('127.0.0.1', port))
        recv_sock.settimeout(1.0)

        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        times = []
        n = 500
        for _ in range(n):
            t0 = time.perf_counter()
            send_sock.sendto(payload, ('127.0.0.1', port))
            try:
                recv_sock.recvfrom(65536)
            except socket.timeout:
                continue
            times.append(time.perf_counter() - t0)

        recv_sock.close()
        send_sock.close()

        if times:
            results[name] = {
                'avg_us': np.mean(times) * 1e6,
                'p50_us': np.median(times) * 1e6,
                'p99_us': np.percentile(times, 99) * 1e6,
                'bytes': len(payload),
                'success_rate': len(times) / n * 100,
            }
        port += 1

    return results


def bench_throughput(port=19990):
    """Messages per second for each payload type."""
    payloads = {
        'fingerprint': struct.pack('128f', *[0.1]*128),
        'json_text': json.dumps({'text': 'hello world ' * 10}).encode(),
    }

    results = {}
    for name, payload in payloads.items():
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(('127.0.0.1', port))
        recv_sock.settimeout(0.001)

        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        n = 5000
        t0 = time.perf_counter()
        for _ in range(n):
            send_sock.sendto(payload, ('127.0.0.1', port))
        send_time = time.perf_counter() - t0

        received = 0
        while True:
            try:
                recv_sock.recvfrom(65536)
                received += 1
            except socket.timeout:
                break

        recv_sock.close()
        send_sock.close()

        results[name] = {
            'send_rate': n / send_time,
            'received': received,
            'bytes': len(payload),
            'bandwidth_mbps': (n * len(payload) * 8) / send_time / 1e6,
        }
        port += 1

    return results


def main():
    print("=" * 60)
    print("  Speed Benchmark: Tension Link vs Alternatives")
    print("=" * 60)

    mind = ConsciousMind(128, 256)
    hidden = torch.zeros(1, 256)

    texts = [
        "The Riemann hypothesis connects prime numbers to complex analysis in unexpected ways",
        "I feel deeply moved by the beauty of this mathematical proof",
        "Quantum entanglement allows instantaneous correlation between distant particles",
        "Bach fugues demonstrate perfect counterpoint and harmonic resolution",
        "Neural networks approximate functions through layered nonlinear transformations",
    ] * 20  # 100 texts

    # 1. Fingerprint generation speed
    print("\n[1/4] Fingerprint generation speed (100 texts)...")
    avg, std = bench_fingerprint_generation(mind, hidden, texts)
    per_text = avg / len(texts) * 1e6
    print(f"  Total:    {avg*1000:.1f}ms for {len(texts)} texts")
    print(f"  Per text: {per_text:.1f}µs")
    print(f"  Rate:     {len(texts)/avg:.0f} fingerprints/sec")

    # 2. Serialization comparison
    print("\n[2/4] Serialization speed & size...")
    ser = bench_serialization(mind, hidden, texts)
    print(f"  {'Method':<25} {'Time':>8} {'Size':>8}")
    print(f"  {'─'*25} {'─'*8} {'─'*8}")
    for name, info in ser.items():
        print(f"  {name:<25} {info['serialize_us']:>6.1f}µs {info['bytes']:>6}B")

    # 3. UDP roundtrip
    print("\n[3/4] UDP roundtrip latency (localhost, 500 msgs)...")
    try:
        udp = bench_udp_roundtrip()
        print(f"  {'Payload':<20} {'Avg':>8} {'P50':>8} {'P99':>10} {'Size':>6}")
        print(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*10} {'─'*6}")
        for name, info in udp.items():
            print(f"  {name:<20} {info['avg_us']:>6.0f}µs {info['p50_us']:>6.0f}µs "
                  f"{info['p99_us']:>8.0f}µs {info['bytes']:>5}B")
    except Exception as e:
        print(f"  Skipped (UDP error: {e})")

    # 4. Throughput
    print("\n[4/4] Throughput (5000 msgs burst)...")
    try:
        tp = bench_throughput()
        print(f"  {'Payload':<20} {'Send Rate':>12} {'BW':>10} {'Size':>6}")
        print(f"  {'─'*20} {'─'*12} {'─'*10} {'─'*6}")
        for name, info in tp.items():
            print(f"  {name:<20} {info['send_rate']:>10,.0f}/s "
                  f"{info['bandwidth_mbps']:>7.1f}Mbps {info['bytes']:>5}B")
    except Exception as e:
        print(f"  Skipped (UDP error: {e})")

    # Summary
    fp_ser = ser['fingerprint']['serialize_us']
    json_ser = ser['json_message']['serialize_us']
    fp_size = ser['fingerprint']['bytes']
    json_size = ser['json_message']['bytes']

    print(f"\n{'=' * 60}")
    print(f"  Summary")
    print(f"{'=' * 60}")
    print(f"  Fingerprint generation: {per_text:.0f}µs per input")
    print(f"  Serialization:  fingerprint {fp_ser:.0f}µs vs JSON {json_ser:.0f}µs ({json_ser/fp_ser:.1f}x slower)")
    print(f"  Payload size:   fingerprint {fp_size}B vs JSON {json_size}B ({json_size/fp_size:.1f}x larger)")
    print(f"  Binary packing is {json_ser/fp_ser:.0f}x faster than JSON for same info density")


if __name__ == "__main__":
    main()
