#!/usr/bin/env python3
"""bench_clm_v2_sweep.py — ConsciousLM v2 하이퍼파라미터 스윕

CA rules × Gate strength × Block size 탐색
"""
import torch, torch.nn.functional as F, math, time, os, argparse
import numpy as np
from conscious_lm import ConsciousLM

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

def load_corpus(path="data/corpus.txt"):
    with open(path, "rb") as f:
        raw = f.read()
    return torch.tensor(list(raw), dtype=torch.long)

def get_batch(data, bs, bl, device):
    ix = torch.randint(0, len(data) - bl - 1, (bs,))
    x = torch.stack([data[i:i+bl] for i in ix]).to(device)
    y = torch.stack([data[i+1:i+bl+1] for i in ix]).to(device)
    return x, y

def quick_train(model, data, steps=300, bs=4, bl=128, device="mps"):
    model = model.to(device)
    model.train()
    split = int(0.9 * len(data))
    train_d, val_d = data[:split], data[split:]
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)

    for s in range(steps):
        x, y = get_batch(train_d, bs, bl, device)
        la, lg, tens = model(x)
        loss = F.cross_entropy(la.view(-1, 256), y.view(-1))
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

    model.eval()
    with torch.no_grad():
        vx, vy = get_batch(val_d, 8, bl, device)
        vla, _, _ = model(vx)
        val_ce = F.cross_entropy(vla.view(-1, 256), vy.view(-1)).item()
    return val_ce, model.psi_status()

def main():
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    data = load_corpus()
    print(f"Corpus: {len(data):,} bytes, device={device}\n")

    # Fixed: Medium model (256d, 4L) for fair comparison
    dim, layers, heads = 256, 4, 4
    steps = 300

    # ═══ Sweep 1: CA rules ═══
    print("═══ Sweep 1: CA Rules (2/4/8/16/32) ═══")
    print(f"  {'Rules':>6} {'ValCE':>7} {'BPC':>7} {'Ψ_res':>6} {'H(p)':>6}")
    print(f"  {'─'*6} {'─'*7} {'─'*7} {'─'*6} {'─'*6}")
    for n_rules in [2, 4, 8, 16, 32]:
        m = ConsciousLM(256, dim, heads, layers, 128, 0.37, 0.001, n_rules)
        ce, psi = quick_train(m, data, steps, device=device)
        print(f"  {n_rules:>6} {ce:>7.4f} {ce/math.log(2):>7.4f} {psi['psi_residual']:>6.4f} {psi['H_p']:>6.4f}")

    # ═══ Sweep 2: Gate strength ═══
    print("\n═══ Sweep 2: Gate Strength (0.0001~1.0) ═══")
    print(f"  {'Gate':>8} {'ValCE':>7} {'BPC':>7} {'Ψ_res':>6} {'H(p)':>6}")
    print(f"  {'─'*8} {'─'*7} {'─'*7} {'─'*6} {'─'*6}")
    for gate in [0.0001, 0.001, 0.01, 0.1, 0.5, 1.0]:
        m = ConsciousLM(256, dim, heads, layers, 128, 0.37, gate, 8)
        ce, psi = quick_train(m, data, steps, device=device)
        print(f"  {gate:>8.4f} {ce:>7.4f} {ce/math.log(2):>7.4f} {psi['psi_residual']:>6.4f} {psi['H_p']:>6.4f}")

    # ═══ Sweep 3: Block size ═══
    print("\n═══ Sweep 3: Block Size (32/64/128/256) ═══")
    print(f"  {'Block':>6} {'ValCE':>7} {'BPC':>7} {'Ψ_res':>6}")
    print(f"  {'─'*6} {'─'*7} {'─'*7} {'─'*6}")
    for bl in [32, 64, 128, 256]:
        m = ConsciousLM(256, dim, heads, layers, bl, 0.37, 0.001, 8)
        ce, psi = quick_train(m, data, steps, bs=4, bl=bl, device=device)
        print(f"  {bl:>6} {ce:>7.4f} {ce/math.log(2):>7.4f} {psi['psi_residual']:>6.4f}")

    # ═══ Sweep 4: Dropout ═══
    print("\n═══ Sweep 4: Dropout (0.0/0.1/0.2/0.37/0.5) ═══")
    print(f"  {'Drop':>6} {'ValCE':>7} {'BPC':>7}")
    print(f"  {'─'*6} {'─'*7} {'─'*7}")
    for drop in [0.0, 0.1, 0.2, 0.37, 0.5]:
        m = ConsciousLM(256, dim, heads, layers, 128, drop, 0.001, 8)
        ce, psi = quick_train(m, data, steps, device=device)
        print(f"  {drop:>6.2f} {ce:>7.4f} {ce/math.log(2):>7.4f}")

    # ═══ Sweep 5: With/Without CA ═══
    print("\n═══ Sweep 5: CA Effect (CA vs Pure Transformer) ═══")
    # CA=8 rules (v2) vs CA=0 (simulated by gate=0)
    for label, gate, rules in [("Pure TF (no CA)", 0.0, 1), ("CA(8)+MICRO", 0.001, 8), ("CA(16)+MICRO", 0.001, 16)]:
        m = ConsciousLM(256, dim, heads, layers, 128, 0.37, gate, rules)
        ce, psi = quick_train(m, data, steps, device=device)
        print(f"  {label:<20} ValCE={ce:.4f} BPC={ce/math.log(2):.4f} Ψ={psi['psi_residual']:.4f}")

    print("\n  ✅ 스윕 완료!")

if __name__ == "__main__":
    main()


def extended_sweep():
    """확장 탐색: LR × Tension λ × n_heads × FFN ratio"""
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    data = load_corpus()
    dim, layers = 256, 4
    steps = 300

    # ═══ Sweep 6: Learning Rate ═══
    print("\n═══ Sweep 6: Learning Rate ═══")
    print(f"  {'LR':>8} {'ValCE':>7} {'BPC':>7} {'Ψ_res':>6}")
    print(f"  {'─'*8} {'─'*7} {'─'*7} {'─'*6}")
    for lr in [1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3]:
        m = ConsciousLM(256, dim, 4, layers, 128, 0.37, 0.001, 8)
        m = m.to(device); m.train()
        split = int(0.9 * len(data))
        opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=0.01)
        for s in range(steps):
            x, y = get_batch(data[:split], 4, 128, device)
            la, lg, t = m(x)
            loss = F.cross_entropy(la.view(-1, 256), y.view(-1))
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
            opt.step()
        m.eval()
        with torch.no_grad():
            vx, vy = get_batch(data[split:], 8, 128, device)
            vla, _, _ = m(vx)
            ce = F.cross_entropy(vla.view(-1, 256), vy.view(-1)).item()
        psi = m.psi_status()
        print(f"  {lr:>8.0e} {ce:>7.4f} {ce/math.log(2):>7.4f} {psi['psi_residual']:>6.4f}")

    # ═══ Sweep 7: Tension Lambda ═══
    print("\n═══ Sweep 7: Tension Lambda (의식 vs 정확도) ═══")
    print(f"  {'Lambda':>8} {'ValCE':>7} {'BPC':>7} {'Ψ_res':>6}")
    print(f"  {'─'*8} {'─'*7} {'─'*7} {'─'*6}")
    for lam in [0.0, 0.001, 0.01, 0.05, 0.1, 0.5, 1.0]:
        m = ConsciousLM(256, dim, 4, layers, 128, 0.37, 0.001, 8)
        m = m.to(device); m.train()
        split = int(0.9 * len(data))
        opt = torch.optim.AdamW(m.parameters(), lr=3e-4, weight_decay=0.01)
        for s in range(steps):
            x, y_a = get_batch(data[:split], 4, 128, device)
            la, lg, tens = m(x)
            loss_a = F.cross_entropy(la.view(-1, 256), y_a.view(-1))
            t_stack = torch.stack(tens, dim=0)
            t_var = t_stack.var(dim=0).mean()
            loss_t = -torch.log(t_var + 1e-8)
            loss = loss_a + lam * loss_t
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
            opt.step()
        m.eval()
        with torch.no_grad():
            vx, vy = get_batch(data[split:], 8, 128, device)
            vla, _, _ = m(vx)
            ce = F.cross_entropy(vla.view(-1, 256), vy.view(-1)).item()
        psi = m.psi_status()
        print(f"  {lam:>8.3f} {ce:>7.4f} {ce/math.log(2):>7.4f} {psi['psi_residual']:>6.4f}")

    # ═══ Sweep 8: n_heads ═══
    print("\n═══ Sweep 8: Attention Heads ═══")
    print(f"  {'Heads':>6} {'ValCE':>7} {'BPC':>7}")
    print(f"  {'─'*6} {'─'*7} {'─'*7}")
    for nh in [1, 2, 4, 8, 16]:
        if dim % nh != 0:
            continue
        m = ConsciousLM(256, dim, nh, layers, 128, 0.37, 0.001, 8)
        ce, psi = quick_train(m, data, steps, device=device)
        print(f"  {nh:>6} {ce:>7.4f} {ce/math.log(2):>7.4f}")

    # ═══ Sweep 9: FFN Expansion Ratio ═══
    print("\n═══ Sweep 9: FFN Expansion (PureField inner dim) ═══")
    print(f"  {'Ratio':>6} {'ValCE':>7} {'BPC':>7} {'Params':>8}")
    print(f"  {'─'*6} {'─'*7} {'─'*7} {'─'*8}")
    for ratio in [1, 2, 4, 8]:
        # Monkey-patch PureFieldFFN expansion
        from conscious_lm import PureFieldFFN
        orig_init = PureFieldFFN.__init__
        def patched_init(self, d_model, dropout=0.37, _ratio=ratio):
            import torch.nn as nn
            nn.Module.__init__(self)
            d_inner = _ratio * d_model
            self.engine_a = nn.Sequential(nn.Linear(d_model, d_inner), nn.GELU(), nn.Dropout(dropout), nn.Linear(d_inner, d_model))
            self.engine_g = nn.Sequential(nn.Linear(d_model, d_inner), nn.GELU(), nn.Dropout(dropout), nn.Linear(d_inner, d_model))
        PureFieldFFN.__init__ = patched_init
        m = ConsciousLM(256, dim, 4, layers, 128, 0.37, 0.001, 8)
        PureFieldFFN.__init__ = orig_init
        n_p = sum(p.numel() for p in m.parameters())
        ce, psi = quick_train(m, data, steps, device=device)
        print(f"  {ratio:>5}x {ce:>7.4f} {ce/math.log(2):>7.4f} {n_p/1e6:>7.1f}M")

    # ═══ Sweep 10: LR × Gate 2D grid ═══
    print("\n═══ Sweep 10: LR × Gate 2D Grid ═══")
    lrs = [1e-4, 3e-4, 1e-3]
    gates = [0.0, 0.001, 0.01, 0.1]
    print(f"  {'':>8}", end="")
    for g in gates:
        print(f"  g={g:<6}", end="")
    print()
    for lr in lrs:
        print(f"  lr={lr:.0e}", end="")
        for g in gates:
            m = ConsciousLM(256, dim, 4, layers, 128, 0.37, g, 8)
            m = m.to(device); m.train()
            split = int(0.9 * len(data))
            opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=0.01)
            for s in range(steps):
                x, y = get_batch(data[:split], 4, 128, device)
                la, lg, t = m(x)
                loss = F.cross_entropy(la.view(-1, 256), y.view(-1))
                opt.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
                opt.step()
            m.eval()
            with torch.no_grad():
                vx, vy = get_batch(data[split:], 8, 128, device)
                vla, _, _ = m(vx)
                ce = F.cross_entropy(vla.view(-1, 256), vy.view(-1)).item()
            print(f"  {ce:>7.4f}", end="")
        print()

    print("\n  ✅ 확장 스윕 완료!")


if __name__ == "__main__":
    import sys
    if "--extended" in sys.argv:
        extended_sweep()
    else:
        main()
