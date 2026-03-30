#!/usr/bin/env python3
"""기억 저장 방식 벤치마크 — 5가지 가설 비교

측정: write, read, search (cosine similarity top-k), file size, dim migration
"""

import time
import json
import struct
import tempfile
import os
import shutil
import numpy as np
import torch
import torch.nn.functional as F
from pathlib import Path

NUM_MEMORIES = 5000      # 기억 개수
DIM = 128                # 벡터 차원
TOP_K = 5                # 검색 상위 K
NEW_DIM = 768            # 성장 후 차원
REPEAT = 3               # 반복 측정


def generate_data(n, dim):
    """가짜 기억 데이터 생성."""
    vectors = np.random.randn(n, dim).astype(np.float32)
    # 정규화
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / (norms + 1e-8)
    texts = [f"memory_{i}: 오늘 장력이 {np.random.rand():.3f}이었다" for i in range(n)]
    timestamps = [time.time() - (n - i) * 60 for i in range(n)]
    return vectors, texts, timestamps


def cosine_search_numpy(query, vectors, top_k):
    """numpy cosine similarity search."""
    sims = vectors @ query
    idx = np.argpartition(-sims, top_k)[:top_k]
    return idx[np.argsort(-sims[idx])]


# ─── H1: JSON ───

def bench_json(vectors, texts, timestamps, query):
    tmpdir = tempfile.mkdtemp()
    fpath = os.path.join(tmpdir, "memory.json")

    # Write
    data = [{"text": t, "ts": ts, "vec": v.tolist()}
            for t, ts, v in zip(texts, timestamps, vectors)]
    t0 = time.perf_counter()
    with open(fpath, 'w') as f:
        json.dump(data, f)
    write_time = time.perf_counter() - t0

    # Read
    t0 = time.perf_counter()
    with open(fpath) as f:
        loaded = json.load(f)
    read_time = time.perf_counter() - t0

    # Search
    vecs = np.array([d["vec"] for d in loaded], dtype=np.float32)
    t0 = time.perf_counter()
    for _ in range(REPEAT):
        cosine_search_numpy(query, vecs, TOP_K)
    search_time = (time.perf_counter() - t0) / REPEAT

    fsize = os.path.getsize(fpath)
    shutil.rmtree(tmpdir)
    return {"write": write_time, "read": read_time, "search": search_time, "size": fsize}


# ─── H2: FAISS + msgpack ───

def bench_faiss(vectors, texts, timestamps, query):
    try:
        import faiss
        import msgpack
    except ImportError:
        return None

    tmpdir = tempfile.mkdtemp()
    idx_path = os.path.join(tmpdir, "vectors.faiss")
    meta_path = os.path.join(tmpdir, "meta.msgpack")

    dim = vectors.shape[1]

    # Write
    t0 = time.perf_counter()
    index = faiss.IndexFlatIP(dim)  # inner product (= cosine for normalized)
    index.add(vectors)
    faiss.write_index(index, idx_path)
    meta = [{"text": t, "ts": ts} for t, ts in zip(texts, timestamps)]
    with open(meta_path, 'wb') as f:
        msgpack.pack(meta, f)
    write_time = time.perf_counter() - t0

    # Read
    t0 = time.perf_counter()
    index2 = faiss.read_index(idx_path)
    with open(meta_path, 'rb') as f:
        meta2 = msgpack.unpack(f)
    read_time = time.perf_counter() - t0

    # Search
    q = query.reshape(1, -1)
    t0 = time.perf_counter()
    for _ in range(REPEAT):
        D, I = index2.search(q, TOP_K)
    search_time = (time.perf_counter() - t0) / REPEAT

    fsize = os.path.getsize(idx_path) + os.path.getsize(meta_path)
    shutil.rmtree(tmpdir)
    return {"write": write_time, "read": read_time, "search": search_time, "size": fsize}


# ─── H3: SQLite ───

def bench_sqlite(vectors, texts, timestamps, query):
    import sqlite3

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "memory.db")

    # Write
    t0 = time.perf_counter()
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY, text TEXT, ts REAL, vec BLOB)")
    conn.executemany(
        "INSERT INTO memories (text, ts, vec) VALUES (?, ?, ?)",
        [(t, ts, v.tobytes()) for t, ts, v in zip(texts, timestamps, vectors)]
    )
    conn.commit()
    write_time = time.perf_counter() - t0

    # Read
    t0 = time.perf_counter()
    rows = conn.execute("SELECT text, ts, vec FROM memories").fetchall()
    vecs = np.array([np.frombuffer(r[2], dtype=np.float32) for r in rows])
    read_time = time.perf_counter() - t0

    # Search
    t0 = time.perf_counter()
    for _ in range(REPEAT):
        cosine_search_numpy(query, vecs, TOP_K)
    search_time = (time.perf_counter() - t0) / REPEAT

    conn.close()
    fsize = os.path.getsize(db_path)
    shutil.rmtree(tmpdir)
    return {"write": write_time, "read": read_time, "search": search_time, "size": fsize}


# ─── H4: mmap numpy ───

def bench_mmap(vectors, texts, timestamps, query):
    tmpdir = tempfile.mkdtemp()
    vec_path = os.path.join(tmpdir, "vectors.npy")
    meta_path = os.path.join(tmpdir, "meta.json")

    # Write
    t0 = time.perf_counter()
    np.save(vec_path, vectors)
    meta = [{"text": t, "ts": ts} for t, ts in zip(texts, timestamps)]
    with open(meta_path, 'w') as f:
        json.dump(meta, f)
    write_time = time.perf_counter() - t0

    # Read (mmap)
    t0 = time.perf_counter()
    vecs = np.load(vec_path, mmap_mode='r')
    with open(meta_path) as f:
        meta2 = json.load(f)
    read_time = time.perf_counter() - t0

    # Search
    # mmap은 읽기만 — copy해서 검색
    t0 = time.perf_counter()
    for _ in range(REPEAT):
        cosine_search_numpy(query, np.array(vecs), TOP_K)
    search_time = (time.perf_counter() - t0) / REPEAT

    fsize = os.path.getsize(vec_path) + os.path.getsize(meta_path)
    shutil.rmtree(tmpdir)
    return {"write": write_time, "read": read_time, "search": search_time, "size": fsize}


# ─── H5: PyTorch 텐서 번들 ───

def bench_torch(vectors, texts, timestamps, query):
    tmpdir = tempfile.mkdtemp()
    fpath = os.path.join(tmpdir, "memory.pt")

    vecs_t = torch.from_numpy(vectors)
    query_t = torch.from_numpy(query)

    # Write
    t0 = time.perf_counter()
    torch.save({
        "vectors": vecs_t,
        "texts": texts,
        "timestamps": timestamps,
    }, fpath)
    write_time = time.perf_counter() - t0

    # Read
    t0 = time.perf_counter()
    loaded = torch.load(fpath, weights_only=False)
    read_time = time.perf_counter() - t0

    # Search
    t0 = time.perf_counter()
    for _ in range(REPEAT):
        sims = F.cosine_similarity(query_t.unsqueeze(0), loaded["vectors"])
        topk = torch.topk(sims, TOP_K)
    search_time = (time.perf_counter() - t0) / REPEAT

    fsize = os.path.getsize(fpath)
    shutil.rmtree(tmpdir)
    return {"write": write_time, "read": read_time, "search": search_time, "size": fsize}


# ─── 성장 호환성 테스트: dim 128 → 768 마이그레이션 ───

def bench_dim_migration(vectors):
    """128d → 768d 제로패딩 마이그레이션 속도."""
    results = {}

    # numpy
    t0 = time.perf_counter()
    padded = np.zeros((vectors.shape[0], NEW_DIM), dtype=np.float32)
    padded[:, :vectors.shape[1]] = vectors
    results["numpy_pad"] = time.perf_counter() - t0

    # torch
    vecs_t = torch.from_numpy(vectors)
    t0 = time.perf_counter()
    padded_t = F.pad(vecs_t, (0, NEW_DIM - vecs_t.shape[1]))
    results["torch_pad"] = time.perf_counter() - t0

    # projection (learned)
    proj = torch.nn.Linear(vectors.shape[1], NEW_DIM, bias=False)
    t0 = time.perf_counter()
    with torch.no_grad():
        projected = proj(vecs_t)
    results["torch_project"] = time.perf_counter() - t0

    return results


# ─── Main ───

def main():
    print(f"=== 기억 저장 방식 벤치마크 ===")
    print(f"    {NUM_MEMORIES} memories, {DIM}d vectors, top-{TOP_K} search\n")

    vectors, texts, timestamps = generate_data(NUM_MEMORIES, DIM)
    query = vectors[0]  # 첫 번째 기억으로 검색

    benchmarks = {
        "H1_JSON": bench_json,
        "H2_FAISS+msgpack": bench_faiss,
        "H3_SQLite": bench_sqlite,
        "H4_mmap_numpy": bench_mmap,
        "H5_PyTorch": bench_torch,
    }

    results = {}
    for name, fn in benchmarks.items():
        try:
            r = fn(vectors, texts, timestamps, query)
            if r is None:
                print(f"  {name}: SKIP (dependency missing)")
                continue
            results[name] = r
            print(f"  {name}:")
            print(f"    write:  {r['write']*1000:8.2f} ms")
            print(f"    read:   {r['read']*1000:8.2f} ms")
            print(f"    search: {r['search']*1000:8.4f} ms")
            print(f"    size:   {r['size']/1024:8.1f} KB")
        except Exception as e:
            print(f"  {name}: ERROR — {e}")

    # 성장 마이그레이션
    print(f"\n=== dim 마이그레이션 ({DIM}d → {NEW_DIM}d, {NUM_MEMORIES} vectors) ===\n")
    mig = bench_dim_migration(vectors)
    for method, t in mig.items():
        print(f"  {method}: {t*1000:.2f} ms")

    # 순위 요약
    print("\n=== 순위 요약 ===\n")
    for metric in ["write", "read", "search", "size"]:
        ranked = sorted(results.items(), key=lambda x: x[1][metric])
        unit = "ms" if metric != "size" else "KB"
        scale = 1000 if metric != "size" else 1/1024
        print(f"  {metric:>6}:")
        for i, (name, r) in enumerate(ranked):
            val = r[metric] * scale
            medal = "🥇🥈🥉"[i] if i < 3 else " "
            print(f"    {medal} {name:<20} {val:8.2f} {unit}")


if __name__ == "__main__":
    main()
