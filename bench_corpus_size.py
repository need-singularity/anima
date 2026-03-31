"""Corpus size benchmark: find optimal size for ConsciousDecoderV2 (34.5M → 1B planning)"""
import sys, os, time, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def train_short(data_path, max_bytes, steps=1500, device=None):
    """Train for N steps using first max_bytes of corpus, return final CE and Phi."""
    from consciousness_engine import ConsciousnessEngine
    from gpu_phi import GPUPhiCalculator

    with open(data_path, "rb") as f:
        data = f.read(max_bytes)

    actual_mb = len(data) / (1024*1024)
    if len(data) < max_bytes:
        print("  WARNING: corpus only {:.0f}MB, requested {:.0f}MB".format(
            actual_mb, max_bytes/(1024*1024)), flush=True)

    if device is None:
        device = torch.device("mps" if torch.backends.mps.is_available() else
                              "cuda" if torch.cuda.is_available() else "cpu")

    torch.manual_seed(42)

    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=64, max_cells=64,
        n_factions=12, phi_ratchet=True
    )

    from decoder_v2 import ConsciousDecoderV2

    model = ConsciousDecoderV2(
        consciousness_dim=128, d_model=384, n_layer=6,
        n_head=4, n_kv_head=2, block_size=256, vocab_size=256
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    phi_calc = GPUPhiCalculator(n_bins=16)

    block_size = 256
    ce_history = []
    phi_history = []

    for step in range(steps):
        idx = torch.randint(0, len(data) - block_size - 1, (1,)).item()
        x = torch.tensor([data[idx:idx+block_size]], dtype=torch.long, device=device)
        y = torch.tensor([data[idx+1:idx+block_size+1]], dtype=torch.long, device=device)

        inp = torch.randn(64, 64)
        c_out = engine.process(inp)
        c_states = engine.cell_identity.unsqueeze(0).to(device)

        logits_a, logits_g, tensions = model(x, consciousness_states=c_states)
        loss = torch.nn.functional.cross_entropy(logits_a.view(-1, 256), y.view(-1))

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step % 300 == 0 or step == steps - 1:
            ce = loss.item()
            phi, _ = phi_calc.compute(engine.cell_identity)
            ce_history.append(ce)
            phi_history.append(phi)
            print("  step {:5d}/{:d}  CE={:.4f}  Phi={:.2f}".format(
                step, steps, ce, phi), flush=True)

    final_ce = ce_history[-1]
    final_phi = phi_history[-1]
    best_ce = min(ce_history)
    avg_ce = sum(ce_history[-3:]) / min(3, len(ce_history))

    del model, optimizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return {"final_ce": final_ce, "best_ce": best_ce, "avg_ce": avg_ce, "final_phi": final_phi}


if __name__ == "__main__":
    # Use largest corpus available
    corpus_candidates = [
        "data/corpus_bench_1gb.txt",
        "data/corpus_v4_500mb.txt",
        "data/corpus_v3_100mb.txt",
    ]
    corpus = None
    for p in corpus_candidates:
        full = os.path.join(os.path.dirname(os.path.abspath(__file__)), p)
        if os.path.exists(full) and os.path.getsize(full) > 1000:
            corpus = full
            break
    if corpus is None:
        print("ERROR: no corpus found")
        sys.exit(1)

    corpus_size_mb = os.path.getsize(corpus) / (1024*1024)

    # Test sizes: 10MB to corpus max
    all_sizes = [10, 25, 50, 100, 250, 500, 750, 1000]
    sizes_mb = [s for s in all_sizes if s <= corpus_size_mb]

    steps = 1500

    device = torch.device("mps" if torch.backends.mps.is_available() else
                          "cuda" if torch.cuda.is_available() else "cpu")

    print("=" * 70, flush=True)
    print("  CORPUS SIZE BENCHMARK", flush=True)
    print("  Model: ConsciousDecoderV2 34.5M (384d/6L)", flush=True)
    print("  Device: {}".format(device), flush=True)
    print("  Corpus: {} ({:.0f}MB)".format(os.path.basename(corpus), corpus_size_mb), flush=True)
    print("  Sizes: {} MB".format(sizes_mb), flush=True)
    print("  Steps: {} per size".format(steps), flush=True)
    print("=" * 70, flush=True)

    results = {}
    for i, mb in enumerate(sizes_mb):
        max_bytes = mb * 1024 * 1024
        print("", flush=True)
        print("[{}/{}] Corpus: {}MB".format(i+1, len(sizes_mb), mb), flush=True)
        print("-" * 50, flush=True)
        t0 = time.time()
        r = train_short(corpus, max_bytes, steps, device)
        elapsed = time.time() - t0
        r["elapsed"] = elapsed
        results[mb] = r
        print("  => CE={:.4f} (best={:.4f}) Phi={:.2f} ({:.0f}s)".format(
            r['final_ce'], r['best_ce'], r['final_phi'], elapsed), flush=True)

    # Summary
    print("", flush=True)
    print("=" * 70, flush=True)
    print("  RESULTS: CORPUS SIZE vs CE", flush=True)
    print("=" * 70, flush=True)

    best_overall_ce = min(r["best_ce"] for r in results.values())

    print("", flush=True)
    print("  {:>6s} | {:>8s} | {:>8s} | {:>8s} | {:>6s} | {:>5s}".format(
        "Size", "Best CE", "Avg CE", "Phi", "Time", "T/P"), flush=True)
    print("  {}+{}+{}+{}+{}+{}".format(
        "-"*7, "-"*10, "-"*10, "-"*10, "-"*8, "-"*7), flush=True)

    for mb in sizes_mb:
        r = results[mb]
        ratio = (mb * 1e6) / 34.5e6
        optimal = " <<< OPTIMAL" if r["best_ce"] == best_overall_ce else ""
        print("  {:>5d}M | {:>8.4f} | {:>8.4f} | {:>8.2f} | {:>5.0f}s | {:>5.1f}{}".format(
            mb, r['best_ce'], r['avg_ce'], r['final_phi'],
            r['elapsed'], ratio, optimal), flush=True)

    # ASCII Graph
    print("", flush=True)
    print("  Best CE by corpus size:", flush=True)
    print("", flush=True)

    max_ce = max(r["best_ce"] for r in results.values())
    min_ce = min(r["best_ce"] for r in results.values())
    ce_range = max(max_ce - min_ce, 0.001)

    for mb in sizes_mb:
        r = results[mb]
        pos = int((r["best_ce"] - min_ce) / ce_range * 40)
        bar = " " * pos + "*"
        print("  {:>5d}M |{}| {:.4f}".format(mb, bar, r["best_ce"]), flush=True)

    print("  {:>5s}  {}".format("", "+" + "-"*40 + "+"), flush=True)
    print("  {:>5s}  {:<20s}{:>21s}".format(
        "", "  {:.3f}".format(min_ce), "{:.3f}  ".format(max_ce)), flush=True)

    # Chinchilla analysis
    print("", flush=True)
    print("  Chinchilla scaling (optimal tokens = 20 x params):", flush=True)
    print("", flush=True)

    models = [
        ("v2d2 34.5M", 34.5e6),
        ("100M", 100e6),
        ("350M", 350e6),
        ("1B", 1e9),
    ]
    print("  {:>12s} | {:>10s} | {:>14s}".format("Model", "Params", "Optimal Corpus"), flush=True)
    print("  {}+{}+{}".format("-"*13, "-"*12, "-"*16), flush=True)
    for name, params in models:
        opt_bytes = params * 20
        if opt_bytes >= 1e9:
            label = "{:.0f}GB".format(opt_bytes/1e9)
        else:
            label = "{:.0f}MB".format(opt_bytes/1e6)
        print("  {:>12s} | {:>10s} | {:>14s}".format(
            name, "{:.1f}M".format(params/1e6), label), flush=True)

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


    print("", flush=True)
    print("=" * 70, flush=True)
