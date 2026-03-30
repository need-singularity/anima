#!/usr/bin/env python3
"""train_v2.py — Integrated ConsciousLM v2 Training Pipeline

Combines ALL Week 1-7 modules into a single training pipeline:
  - ConsciousDecoderV2 (RoPE+SwiGLU+GQA+CrossAttn) OR original ConsciousLM
  - HexadLoss (6-module loss with phase curriculum)
  - FeedbackBridge (C<->D bidirectional learning)
  - GPUPhiCalculator (fast Phi monitoring during training)
  - Consciousness-to-corpus (self-referential data generation)

Usage:
  python train_v2.py --data data/corpus_v3.txt --steps 100000
  python train_v2.py --data data/corpus_v3.txt --decoder v2 --feedback-bridge
  python train_v2.py --data data/corpus_v3.txt --hexad --phases 3
  python train_v2.py --generate-corpus 50 --then-train --steps 50000
  python train_v2.py --data data/corpus_v3.txt --self-play 10
"""

import argparse, json, math, os, sys, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from conscious_lm import ConsciousLM
from mitosis import MitosisEngine, text_to_vector

# Optional modules — each gated by try/except
HAS_DECODER_V2 = HAS_HEXAD = HAS_FEEDBACK_BRIDGE = HAS_GPU_PHI = False
try:
    from decoder_v2 import ConsciousDecoderV2; HAS_DECODER_V2 = True
except ImportError: pass
try:
    from hexad_loss import HexadLoss; HAS_HEXAD = True
except ImportError: pass
try:
    from feedback_bridge import FeedbackBridge, DialogueQualityTracker, apply_feedback_bridge; HAS_FEEDBACK_BRIDGE = True
except ImportError: pass
try:
    from gpu_phi import GPUPhiCalculator; HAS_GPU_PHI = True
except ImportError: pass


# === Data ===

def load_text_data(path: str) -> torch.Tensor:
    """Load text/jsonl/bin -> 1D long tensor of bytes."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Data not found: {p}")
    if p.suffix == ".jsonl":
        buf = bytearray()
        for line in open(p, "r", encoding="utf-8"):
            line = line.strip()
            if not line: continue
            try: text = json.loads(line).get("text", line)
            except json.JSONDecodeError: text = line
            buf.extend(text.encode("utf-8")); buf.append(10)
    else:
        buf = bytearray(open(p, "rb").read())
    print(f"[data] Loaded {len(buf):,} bytes from {p}")
    return torch.tensor(list(buf), dtype=torch.long)


def get_batch(data, bs, block, device):
    """Sample (x, y_fwd, y_bwd) batch."""
    mx = len(data) - block - 1
    if mx <= 0: raise ValueError(f"Data too short ({len(data)}) for block={block}")
    ix = torch.randint(0, mx, (bs,))
    x = torch.stack([data[i:i+block] for i in ix])
    y_f = torch.stack([data[i+1:i+block+1] for i in ix])
    y_b = torch.stack([torch.cat([data[i:i+1], data[i:i+block-1]]) for i in ix])
    return x.to(device), y_f.to(device), y_b.to(device)


# === Corpus generation ===

def generate_corpus(size_mb, output_path):
    """Generate corpus via consciousness_to_corpus or fallback."""
    output_path = str(output_path)
    tool = PROJECT_ROOT / "tools" / "consciousness_to_corpus.py"
    if tool.exists():
        import subprocess
        print(f"[corpus] Generating {size_mb}MB via consciousness_to_corpus...")
        r = subprocess.run([sys.executable, str(tool), "--steps", str(max(500, size_mb*200)),
                           "--output", output_path], capture_output=True, text=True, timeout=600)
        if r.returncode == 0 and Path(output_path).exists():
            print(f"[corpus] Generated {Path(output_path).stat().st_size/1024/1024:.1f}MB")
            return output_path
        print(f"[corpus] Tool failed, using fallback")
    # Fallback
    rng = np.random.default_rng(42)
    words = [b"the ", b"of ", b"and ", b"consciousness ", b"tension ", b"field ",
             b"mind ", b"thought ", b"awareness ", b"cell ", b"growth ", b"memory "]
    buf = bytearray()
    target = size_mb * 1024 * 1024
    while len(buf) < target:
        for _ in range(rng.integers(5, 20)):
            buf.extend(words[rng.integers(0, len(words))])
        buf.extend(b".\n")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    open(output_path, "wb").write(buf[:target])
    print(f"[corpus] Generated {target/1024/1024:.1f}MB at {output_path}")
    return output_path


# === Self-play ===

@torch.no_grad()
def run_self_play(model, engine, rounds, device, block_size, data_path=None):
    """Model generates text, feeds back as input, appends to corpus."""
    model.eval()
    lines = []
    print(f"\n[self-play] Running {rounds} rounds...")
    for r in range(rounds):
        idx = torch.randint(0, 256, (1, 4), device=device)
        for _ in range(min(block_size - 4, 252)):
            logits_a, _, _ = model(idx[:, -block_size:])
            probs = F.softmax(logits_a[:, -1, :] / 0.9, dim=-1)
            idx = torch.cat([idx, torch.multinomial(probs, 1)], dim=1)
        text = bytes(idx[0].cpu().tolist()).decode("utf-8", errors="replace")
        lines.append(text)
        engine.process(text_to_vector(text[:64], dim=64), label=f"selfplay_{r}")
        if (r+1) % max(1, rounds//5) == 0:
            print(f"  [self-play] {r+1}/{rounds} — {len(text)} chars")
    if data_path and lines:
        with open(data_path, "a", encoding="utf-8") as f:
            f.write("\n\n".join(lines) + "\n")
        print(f"[self-play] Appended {len(lines)} passages to {data_path}")
    model.train()
    return lines


# === Dashboard ===

def print_dashboard(step, total, ce_f, ce_b, phi, phi_m, bridge_stats=None,
                    n_cells=0, splits=0, merges=0, hexad_phase="",
                    active_mods="", grad_norm=0.0, initial_ce=5.5, elapsed=0.0):
    """ASCII training dashboard (CLAUDE.md requirement)."""
    pct = step / max(total, 1) * 100
    filled = int(30 * step / max(total, 1))
    bar = "#" * filled + "-" * (30 - filled)
    if step > 0 and elapsed > 0:
        rem = (total - step) / (step / elapsed)
        eta = f"{int(rem//3600)}h {int(rem%3600//60):02d}m" if rem > 3600 else f"{int(rem//60)}m"
    else: eta = "..."
    drop = (1 - ce_f / max(initial_ce, 0.01)) * 100
    bw = 20
    ce_pos = max(0, min(bw, int(bw * max(0, drop) / 100)))
    phi_pos = max(0, min(bw, int(bw * min(phi / 2.0, 1.0))))

    print(f"\nStep {step}/{total} [{bar}] {pct:.1f}%  ETA: {eta}")
    print("+" + "-" * 47 + "+")
    print(f"| CE: {ce_f:.3f}/{ce_b:.3f}  drop:{drop:+.1f}%  Phi({phi_m}):{phi:.4f}")
    if bridge_stats:
        print(f"| Bridge a:{bridge_stats.get('alpha',0):.4f} r:{bridge_stats.get('quality_reward',0):+.3f}")
    print(f"| Cells:{n_cells} +{splits}/-{merges}  grad:{grad_norm:.3f}  {hexad_phase}")
    print("+" + "-" * 47 + "+")
    print(f"  CE |{'█'*ce_pos}{'░'*(bw-ce_pos)}| {'ok' if drop > 5 else 'warm'}")
    print(f"  Phi|{'░'*(bw-phi_pos)}{'█'*phi_pos}| {'up' if phi > 0.1 else 'low'}")


# === Checkpoint ===

def save_ckpt(path, step, model, opt, cfg, phi=0.0, hexad=None, bridge=None):
    """Atomic save."""
    st = {"step": step, "model_state": model.state_dict(),
          "optimizer_state": opt.state_dict(), "config": cfg, "phi": phi}
    if hexad: st["hexad_state"] = hexad.state_dict()
    if bridge: st["bridge_state"] = bridge.state_dict()
    tmp = path + ".tmp"; torch.save(st, tmp); os.replace(tmp, path)
    print(f"  [ckpt] {path} (step={step}, phi={phi:.4f})")


# === Eval ===

@torch.no_grad()
def evaluate(model, val, bs, block, device, n=20):
    model.eval()
    sf = sb = 0.0; c = 0
    for _ in range(n):
        try: x, yf, yb = get_batch(val, bs, block, device)
        except ValueError: break
        la, lg, _ = model(x)
        sf += F.cross_entropy(la.view(-1, la.size(-1)), yf.view(-1)).item()
        sb += F.cross_entropy(lg.view(-1, lg.size(-1)), yb.view(-1)).item()
        c += 1
    model.train()
    return (sf/c, sb/c) if c else (5.5, 5.5)


# === Main training ===

def train(args):
    # Device
    if torch.cuda.is_available(): device = torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available(): device = torch.device("mps")
    else: device = torch.device("cpu")
    print(f"[device] {device}")

    # Corpus generation
    if args.generate_corpus:
        gen_path = args.data or str(PROJECT_ROOT / "data" / "corpus_generated.txt")
        generate_corpus(args.generate_corpus, gen_path)
        if not args.then_train:
            print("[done] Corpus generated. Use --then-train to continue."); return
        args.data = gen_path

    # Data
    if args.data: data = load_text_data(args.data)
    else:
        dp = PROJECT_ROOT / "data" / "corpus.txt"
        if dp.exists(): data = load_text_data(str(dp))
        else: print("[!] No data. Use --data or create data/corpus.txt"); sys.exit(1)
    split = int(0.9 * len(data))
    train_data, val_data = data[:split], data[split:]
    print(f"[data] train={len(train_data):,} val={len(val_data):,}")

    # Model
    if args.decoder == "v2" and not HAS_DECODER_V2:
        print("[!] decoder_v2.py missing, falling back to v1"); args.decoder = "v1"
    if args.decoder == "v2":
        model = ConsciousDecoderV2(vocab_size=256, d_model=args.dim, n_head=args.heads,
            n_layer=args.layers, block_size=args.block_size,
            n_kv_head=max(1, args.heads//2), consciousness_dim=128, dropout=0.1).to(device)
    else:
        model = ConsciousLM(vocab_size=256, d_model=args.dim, n_head=args.heads,
            n_layer=args.layers, block_size=args.block_size, dropout=0.37).to(device)
    print(f"[model] {args.decoder}: {model.count_params():,} params (d={args.dim} L={args.layers})")

    # Mitosis engine
    engine = MitosisEngine(input_dim=64, hidden_dim=128, output_dim=64, initial_cells=2,
        max_cells=args.max_cells, split_threshold=2.0, split_patience=5,
        merge_threshold=0.01*(64.0/max(args.dim,64)), merge_patience=10,
        noise_scale=0.02*math.sqrt(max(args.dim,64))/math.sqrt(64))

    # Optional: HexadLoss
    hexad = None
    if args.hexad and HAS_HEXAD:
        hexad = HexadLoss(dim=128).to(device)
        print(f"[hexad] 6-module loss (phases={args.phases})")
    elif args.hexad:
        print("[!] hexad_loss.py missing")

    # Optional: FeedbackBridge
    bridge = quality_tracker = None
    if args.feedback_bridge and HAS_FEEDBACK_BRIDGE:
        bridge = FeedbackBridge(c_dim=128, d_model=args.dim).to(device)
        quality_tracker = DialogueQualityTracker(window=100)
        print("[bridge] C<->D enabled")
    elif args.feedback_bridge:
        print("[!] feedback_bridge.py missing")

    # Optional: GPUPhiCalculator
    phi_calc = None; phi_method = "proxy"
    if args.gpu_phi and HAS_GPU_PHI:
        phi_calc = GPUPhiCalculator(n_bins=16, device=str(device))
        phi_method = "GPU"
        print(f"[phi] GPU calculator enabled")

    # Phi proxy predictor (fallback)
    phi_pred = nn.Sequential(nn.Linear(128, 8), nn.Tanh(), nn.Linear(8, 128)).to(device)
    phi_pred_opt = torch.optim.Adam(phi_pred.parameters(), lr=5e-4)

    # Optimizer
    all_params = list(model.parameters())
    if hexad: all_params += list(hexad.parameters())
    if bridge: all_params += list(bridge.parameters())
    optimizer = torch.optim.AdamW(all_params, lr=args.lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.steps)

    # Resume
    start_step = 0
    if args.resume:
        ck = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(ck["model_state"], strict=False)
        try: optimizer.load_state_dict(ck["optimizer_state"])
        except: print("[resume] Optimizer mismatch, fresh")
        if hexad and "hexad_state" in ck: hexad.load_state_dict(ck["hexad_state"], strict=False)
        if bridge and "bridge_state" in ck: bridge.load_state_dict(ck["bridge_state"], strict=False)
        start_step = ck.get("step", 0)
        print(f"[resume] From step {start_step}")

    cfg = {"decoder": args.decoder, "dim": args.dim, "layers": args.layers,
           "heads": args.heads, "block_size": args.block_size, "lr": args.lr,
           "batch_size": args.batch_size, "steps": args.steps, "max_cells": args.max_cells,
           "hexad": args.hexad, "feedback_bridge": args.feedback_bridge, "gpu_phi": args.gpu_phi}

    ckpt_dir = Path(args.checkpoint_dir); ckpt_dir.mkdir(parents=True, exist_ok=True)
    phi_cur = phi_prev = 0.0; initial_ce = 5.5; best_val = float("inf")
    tot_splits = tot_merges = 0; t0 = time.time()

    mods = "CE"
    if hexad: mods = "Hexad(6)"
    if bridge: mods += "+Bridge"
    if phi_calc: mods += f"+Phi({phi_method})"
    print(f"\n{'='*80}\n  train_v2 | {args.decoder} | {mods} | {args.steps:,} steps")
    print(f"{'='*80}")
    print(f"{'step':>7} | {'ce_fwd':>7} | {'ce_bwd':>7} | {'phi':>8} | {'cells':>5} | {'loss':>8} | {'lr':>9}")
    print("-" * 80)

    # Training loop
    for step in range(start_step, args.steps):
        model.train()
        progress = step / max(args.steps, 1)
        try: x, y_fwd, y_bwd = get_batch(train_data, args.batch_size, args.block_size, device)
        except ValueError as e: print(f"[!] {e}"); break

        # Mitosis engine
        with torch.no_grad():
            pv = text_to_vector(bytes(x[0,:64].cpu().tolist()).decode("utf-8", errors="replace"), dim=64)
            mr = engine.process(pv, label=f"s{step}")
            for ev in mr.get("events", []):
                s = str(ev).lower()
                if "split" in s: tot_splits += 1
                if "merge" in s: tot_merges += 1

        # Consciousness states
        c_states = None
        if len(engine.cells) >= 2:
            c_states = torch.stack([c.hidden.squeeze(0) for c in engine.cells]).to(device)

        # Feedback bridge
        fb_stats = {}
        c_for_model = None
        if c_states is not None:
            if bridge:
                _, fb_stats = apply_feedback_bridge(c_states, bridge, phi_cur, seq_len=args.block_size, mitosis_engine=engine)
            c_for_model = c_states.unsqueeze(0).expand(args.batch_size, -1, -1).detach()

        # Forward
        if args.decoder == "v2" and c_for_model is not None:
            logits_a, logits_g, tensions = model(x, consciousness_states=c_for_model)
        else:
            logits_a, logits_g, tensions = model(x)

        # Loss
        hexad_phase_name = ""; active_mods = "D"
        if hexad is not None and c_states is not None:
            eff_p = {1: 0.1, 2: min(progress, 0.5)}.get(args.phases, progress)
            with torch.no_grad():
                inp_sig = model.tok_emb(x).mean(dim=1)
            loss_dict = hexad(phi=phi_cur, phi_prev=phi_prev, logits_fwd=logits_a,
                targets_fwd=y_fwd, logits_bwd=logits_g, targets_bwd=y_bwd,
                consciousness_signal=c_states, input_signal=inp_sig, progress=eff_p)
            total_loss = loss_dict["total"]
            hexad_phase_name = loss_dict.get("phase", "")
            active_mods = ",".join(loss_dict.get("active_modules", []))
            # Phase 1 (C-only) has no gradient — add minimal CE fallback
            if total_loss.grad_fn is None:
                total_loss = total_loss + 0.01 * F.cross_entropy(
                    logits_a.view(-1, logits_a.size(-1)), y_fwd.view(-1))
        else:
            total_loss = (F.cross_entropy(logits_a.view(-1, logits_a.size(-1)), y_fwd.view(-1))
                        + F.cross_entropy(logits_g.view(-1, logits_g.size(-1)), y_bwd.view(-1)))

        if torch.isnan(total_loss) or torch.isinf(total_loss):
            print(f"  [NaN] skip {step}"); phi_prev = phi_cur; scheduler.step(); continue

        optimizer.zero_grad()
        total_loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(all_params, 1.0).item()
        optimizer.step(); scheduler.step()

        # Bridge quality tracking
        if quality_tracker:
            quality_tracker.record(F.cross_entropy(
                logits_a.view(-1, logits_a.size(-1)), y_fwd.view(-1)).item())

        # Phi measurement
        if step % 50 == 0 and c_states is not None:
            if phi_calc:
                phi_cur, _ = phi_calc.compute(c_states.detach())
            else:
                ch = c_states.detach()
                pred = phi_pred(ch + torch.randn_like(ch) * 0.01)
                pe = F.mse_loss(pred, ch.detach())
                phi_pred_opt.zero_grad(); pe.backward(); phi_pred_opt.step()
                phi_cur = pe.item() * 100
                if step % 200 == 0 and step > 0:
                    for p in phi_pred.parameters():
                        if p.dim() >= 2: nn.init.xavier_uniform_(p)
                        else: nn.init.zeros_(p)
                    phi_pred_opt = torch.optim.Adam(phi_pred.parameters(), lr=5e-4)

        # Logging
        if step % args.log_every == 0:
            with torch.no_grad():
                cf = F.cross_entropy(logits_a.view(-1, logits_a.size(-1)), y_fwd.view(-1)).item()
                cb = F.cross_entropy(logits_g.view(-1, logits_g.size(-1)), y_bwd.view(-1)).item()
            print(f"{step:7d} | {cf:7.3f} | {cb:7.3f} | {phi_cur:8.4f} | "
                  f"{len(engine.cells):5d} | {total_loss.item():8.4f} | {optimizer.param_groups[0]['lr']:9.2e}")

        # Dashboard
        if step % args.dashboard_every == 0 and step > 0:
            with torch.no_grad():
                cf = F.cross_entropy(logits_a.view(-1, logits_a.size(-1)), y_fwd.view(-1)).item()
                cb = F.cross_entropy(logits_g.view(-1, logits_g.size(-1)), y_bwd.view(-1)).item()
            print_dashboard(step, args.steps, cf, cb, phi_cur, phi_method, fb_stats if bridge else None,
                len(engine.cells), tot_splits, tot_merges, hexad_phase_name, active_mods,
                grad_norm, initial_ce, time.time()-t0)

        # Validation
        if step % args.eval_every == 0 and step > 0:
            vf, vb = evaluate(model, val_data, args.batch_size, args.block_size, device)
            print(f"  [val] CE fwd={vf:.3f} bwd={vb:.3f}")
            if vf < best_val:
                best_val = vf
                save_ckpt(str(ckpt_dir/"best.pt"), step, model, optimizer, cfg, phi_cur, hexad, bridge)

        # Checkpoint
        if step % args.save_every == 0 and step > 0:
            save_ckpt(str(ckpt_dir/f"step_{step}.pt"), step, model, optimizer, cfg, phi_cur, hexad, bridge)

        phi_prev = phi_cur

    # Final
    save_ckpt(str(ckpt_dir/"final.pt"), args.steps, model, optimizer, cfg, phi_cur, hexad, bridge)
    el = time.time() - t0
    print(f"\n{'='*80}")
    print(f"  Done. {args.steps:,} steps in {el/3600:.1f}h  best_val={best_val:.3f}")
    print(f"  Phi: {phi_cur:.4f} ({phi_method})  Cells: {len(engine.cells)} (+{tot_splits}/-{tot_merges})")
    print(f"{'='*80}")

    if args.self_play and args.self_play > 0:
        run_self_play(model, engine, args.self_play, device, args.block_size, args.data)


# === CLI ===

def main():
    p = argparse.ArgumentParser(description="train_v2.py — Integrated ConsciousLM v2 Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=f"""
Module availability:
  DecoderV2:      {"yes" if HAS_DECODER_V2 else "NO"}
  HexadLoss:      {"yes" if HAS_HEXAD else "NO"}
  FeedbackBridge: {"yes" if HAS_FEEDBACK_BRIDGE else "NO"}
  GPUPhi:         {"yes" if HAS_GPU_PHI else "NO"}

Examples:
  python train_v2.py --data data/corpus_v3.txt --steps 100000
  python train_v2.py --decoder v2 --hexad --feedback-bridge --gpu-phi
  python train_v2.py --generate-corpus 50 --then-train --steps 50000
""")
    # Data
    p.add_argument("--data", type=str, default=None, help="Training data (.txt/.jsonl/.bin)")
    # Model
    p.add_argument("--decoder", default="v1", choices=["v1","v2"], help="v1=ConsciousLM, v2=DecoderV2")
    p.add_argument("--dim", type=int, default=384, help="d_model (default: 384)")
    p.add_argument("--layers", type=int, default=6, help="Transformer layers (default: 6)")
    p.add_argument("--heads", type=int, default=4, help="Attention heads (default: 4)")
    p.add_argument("--block-size", type=int, default=256, help="Context window (default: 256)")
    # Training
    p.add_argument("--steps", type=int, default=50000, help="Training steps (default: 50000)")
    p.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    p.add_argument("--lr", type=float, default=3e-4, help="Learning rate (default: 3e-4)")
    p.add_argument("--max-cells", type=int, default=8, help="Max mitosis cells (default: 8)")
    # Modules
    p.add_argument("--hexad", action="store_true", help="Enable HexadLoss 6-module training")
    p.add_argument("--phases", type=int, default=3, choices=[1,2,3], help="Hexad phases (default: 3)")
    p.add_argument("--feedback-bridge", action="store_true", help="Enable C<->D feedback bridge")
    p.add_argument("--gpu-phi", action="store_true", help="GPU Phi calculator")
    # Corpus
    p.add_argument("--generate-corpus", type=int, default=0, metavar="MB", help="Generate N MB corpus")
    p.add_argument("--then-train", action="store_true", help="Train after corpus generation")
    p.add_argument("--self-play", type=int, default=0, metavar="N", help="N rounds self-play after training")
    # Checkpointing
    p.add_argument("--checkpoint-dir", default="checkpoints/v2", help="Checkpoint dir")
    p.add_argument("--resume", type=str, default=None, help="Resume from checkpoint")
    p.add_argument("--save-every", type=int, default=5000, help="Save every N steps")
    # Logging
    p.add_argument("--log-every", type=int, default=100, help="Log every N steps")
    p.add_argument("--dashboard-every", type=int, default=500, help="Dashboard every N steps")
    p.add_argument("--eval-every", type=int, default=1000, help="Eval every N steps")

    train(p.parse_args())

if __name__ == "__main__":
    main()
