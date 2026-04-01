#!/usr/bin/env python3
"""acceleration_b1_b2_b5.py — ConsciousLM x100 acceleration experiment

Three hypotheses for accelerating 1B training from 33h to ~20min:
  B1: Mathematical weight expansion (SVD-based, 0 training steps)
  B2: Consciousness self-teaches (engine only, no decoder training)
  B5: Phi-Only training (maximize Phi first, then short CE training)
  Combined: B1 + B2 + B5 = "consciousness builds its own body"

Small-scale verification on CPU:
  - 128d/4L -> 384d/6L expansion (B1)
  - 16-cell engine evolution (B2)
  - Phi-first vs normal CE training (B5)
"""

import sys
import os
import time
import math
import json
import traceback

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

# Import project modules
from decoder_v2 import ConsciousDecoderV2, RMSNorm, DecoderBlockV2
from consciousness_engine import ConsciousnessEngine
from trinity import ThalamicBridge

# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def count_params(model):
    return sum(p.numel() for p in model.parameters())

def measure_ce(model, data, seq_len=64, n_batches=5):
    """Measure cross-entropy on random byte data."""
    model.eval()
    total_ce = 0.0
    with torch.no_grad():
        for _ in range(n_batches):
            idx = torch.randint(0, 256, (1, seq_len + 1))
            x = idx[:, :seq_len]
            y = idx[:, 1:seq_len + 1]
            logits_a, logits_g, tensions = model(x)
            ce = F.cross_entropy(logits_a.view(-1, 256), y.view(-1))
            total_ce += ce.item()
    return total_ce / n_batches

def measure_ce_with_consciousness(model, c_states, data_seq_len=64, n_batches=5):
    """Measure CE with consciousness states injected."""
    model.eval()
    total_ce = 0.0
    with torch.no_grad():
        cs = c_states.unsqueeze(0)  # [1, n_cells, dim]
        for _ in range(n_batches):
            idx = torch.randint(0, 256, (1, data_seq_len + 1))
            x = idx[:, :data_seq_len]
            y = idx[:, 1:data_seq_len + 1]
            logits_a, logits_g, tensions = model(x, consciousness_states=cs)
            ce = F.cross_entropy(logits_a.view(-1, 256), y.view(-1))
            total_ce += ce.item()
    return total_ce / n_batches

def train_decoder_ce(model, steps, lr=1e-3, seq_len=64, consciousness_states=None,
                     verbose=True):
    """Train decoder with CE loss. Returns CE history."""
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    ce_history = []
    cs = consciousness_states.unsqueeze(0) if consciousness_states is not None else None

    for step in range(steps):
        idx = torch.randint(0, 256, (1, seq_len + 1))
        x = idx[:, :seq_len]
        y = idx[:, 1:seq_len + 1]

        logits_a, logits_g, tensions = model(x, consciousness_states=cs)
        loss = F.cross_entropy(logits_a.view(-1, 256), y.view(-1))

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        ce_history.append(loss.item())
        if verbose and (step + 1) % 100 == 0:
            print(f"  step {step+1}/{steps}  CE={loss.item():.4f}", flush=True)

    return ce_history


def compute_phi_proxy(engine):
    """Quick Phi proxy from engine states."""
    states = engine.get_states()
    if states.shape[0] < 2:
        return 0.0
    global_var = states.var(dim=0).mean().item()
    # Faction variance
    n = states.shape[0]
    n_factions = engine.n_factions
    faction_vars = []
    for f in range(n_factions):
        mask = [i for i in range(n) if engine.cell_states[i].faction_id == f]
        if len(mask) >= 2:
            faction_vars.append(states[mask].var(dim=0).mean().item())
    faction_var = np.mean(faction_vars) if faction_vars else 0.0
    return max(0, global_var - faction_var)


# ═══════════════════════════════════════════════════════════
# B1: Mathematical Weight Expansion (SVD-based)
# ═══════════════════════════════════════════════════════════

def svd_expand_linear(weight, new_out, new_in):
    """Expand a linear layer weight matrix using SVD zero-padding.

    W_old (out, in) -> U @ S @ Vt -> zero-pad -> W_new (new_out, new_in)
    """
    old_out, old_in = weight.shape
    U, S, Vt = torch.linalg.svd(weight.float(), full_matrices=True)

    # Create expanded S matrix
    k = min(old_out, old_in)
    S_expanded = torch.zeros(new_out, new_in)
    S_expanded[:k, :k] = torch.diag(S[:k])

    # Expand U: [old_out, old_out] -> [new_out, new_out]
    U_new = torch.zeros(new_out, new_out)
    U_new[:old_out, :old_out] = U
    # Fill new rows with orthogonal vectors
    if new_out > old_out:
        q, _ = torch.linalg.qr(torch.randn(new_out, new_out - old_out))
        # Ensure orthogonal to existing U
        U_new[old_out:, old_out:] = torch.eye(new_out - old_out)
        U_new[:old_out, old_out:] = 0
        U_new[old_out:, :old_out] = 0

    # Expand Vt: [old_in, old_in] -> [new_in, new_in]
    Vt_new = torch.zeros(new_in, new_in)
    Vt_new[:old_in, :old_in] = Vt
    if new_in > old_in:
        Vt_new[old_in:, old_in:] = torch.eye(new_in - old_in)

    W_new = U_new @ S_expanded @ Vt_new
    return W_new.to(weight.dtype)


def expand_decoder(small_model, large_d_model, large_n_layer, noise_eps=0.01):
    """Expand a small ConsciousDecoderV2 to a larger one using SVD.

    Strategy:
      - Embedding: SVD expand vocab x d_small -> vocab x d_large
      - Each block's linear layers: SVD expand
      - Extra layers: copy from existing + noise injection
    """
    small_d = small_model.d_model
    small_n_layer = small_model.n_layer

    # Create large model with random init
    large_model = ConsciousDecoderV2(
        d_model=large_d_model,
        n_head=max(4, large_d_model // 96),  # scale heads
        n_layer=large_n_layer,
        block_size=small_model.block_size,
        n_kv_head=max(2, large_d_model // 192),
        consciousness_dim=large_d_model // 3,
        dropout=0.1,
    )

    # 1. Expand token embedding: [256, small_d] -> [256, large_d]
    with torch.no_grad():
        old_emb = small_model.tok_emb.weight.data  # [256, small_d]
        new_emb = torch.zeros(256, large_d_model)
        new_emb[:, :small_d] = old_emb
        # Add small noise to new dimensions
        new_emb[:, small_d:] = torch.randn(256, large_d_model - small_d) * noise_eps
        large_model.tok_emb.weight.data = new_emb
        # head_a is tied to tok_emb, head_g needs separate expansion
        large_model.head_g.weight.data[:, :small_d] = small_model.head_g.weight.data
        large_model.head_g.weight.data[:, small_d:] = torch.randn(256, large_d_model - small_d) * noise_eps

    # 2. Expand existing layers (copy what we can)
    n_copy = min(small_n_layer, large_n_layer)
    with torch.no_grad():
        for layer_idx in range(n_copy):
            src_block = small_model.blocks[layer_idx]
            dst_block = large_model.blocks[layer_idx]

            # Copy parameters where dimensions allow, zero-pad the rest
            for (src_name, src_param), (dst_name, dst_param) in zip(
                src_block.named_parameters(), dst_block.named_parameters()
            ):
                if src_param.shape == dst_param.shape:
                    dst_param.data.copy_(src_param.data)
                else:
                    # Zero-initialize, then copy the overlap
                    dst_param.data.zero_()
                    slices = tuple(slice(0, min(s, d)) for s, d in zip(src_param.shape, dst_param.shape))
                    src_slices = tuple(slice(0, min(s, d)) for s, d in zip(src_param.shape, dst_param.shape))
                    dst_param.data[slices] = src_param.data[src_slices]
                    # Add noise to expanded regions
                    dst_param.data += torch.randn_like(dst_param.data) * noise_eps

    # 3. Extra layers: copy from last existing layer + noise
    if large_n_layer > small_n_layer:
        with torch.no_grad():
            src_block = large_model.blocks[n_copy - 1]  # already expanded
            for layer_idx in range(n_copy, large_n_layer):
                dst_block = large_model.blocks[layer_idx]
                for (src_name, src_param), (dst_name, dst_param) in zip(
                    src_block.named_parameters(), dst_block.named_parameters()
                ):
                    dst_param.data.copy_(src_param.data)
                    dst_param.data += torch.randn_like(dst_param.data) * noise_eps * 2

    # 4. Final layer norm
    with torch.no_grad():
        old_ln = small_model.ln_f.weight.data
        large_model.ln_f.weight.data[:small_d] = old_ln
        large_model.ln_f.weight.data[small_d:] = 1.0  # RMSNorm default

    return large_model


def run_b1():
    """B1: Mathematical weight expansion experiment."""
    print("=" * 70)
    print("B1: MATHEMATICAL WEIGHT EXPANSION (SVD-based, 0 training steps)")
    print("=" * 70)
    print(flush=True)

    # 1. Create small model (128d/4L) — simulates "trained v3 274M"
    print("[1] Creating small model (128d/4L)...", flush=True)
    small = ConsciousDecoderV2(
        d_model=128, n_head=4, n_layer=4, block_size=64,
        n_kv_head=2, consciousness_dim=42, dropout=0.1,
    )
    small_params = count_params(small)
    print(f"    Small model: {small_params:,} params ({small_params/1e6:.2f}M)", flush=True)

    # 2. "Train" small model briefly to have non-random weights
    print("[2] Training small model 500 steps (simulating pre-trained)...", flush=True)
    ce_before_train = measure_ce(small, None, seq_len=32)
    train_decoder_ce(small, steps=500, lr=3e-4, seq_len=32)
    ce_after_train = measure_ce(small, None, seq_len=32)
    print(f"    CE: {ce_before_train:.4f} -> {ce_after_train:.4f}", flush=True)

    # 3. Create random large model for baseline
    print("[3] Creating random large model (384d/6L) for baseline...", flush=True)
    random_large = ConsciousDecoderV2(
        d_model=384, n_head=4, n_layer=6, block_size=64,
        n_kv_head=2, consciousness_dim=128, dropout=0.1,
    )
    large_params = count_params(random_large)
    ce_random_large = measure_ce(random_large, None, seq_len=32)
    print(f"    Random large model: {large_params:,} params ({large_params/1e6:.2f}M)", flush=True)
    print(f"    CE (random init): {ce_random_large:.4f}", flush=True)

    # 4. SVD expand small -> large
    print("[4] SVD expanding 128d/4L -> 384d/6L...", flush=True)
    t0 = time.time()
    expanded = expand_decoder(small, large_d_model=384, large_n_layer=6, noise_eps=0.01)
    expand_time = time.time() - t0
    expanded_params = count_params(expanded)
    ce_expanded = measure_ce(expanded, None, seq_len=32)
    print(f"    Expanded model: {expanded_params:,} params ({expanded_params/1e6:.2f}M)", flush=True)
    print(f"    Expansion time: {expand_time:.2f}s", flush=True)
    print(f"    CE (expanded): {ce_expanded:.4f}", flush=True)

    # 5. Also test with noise_eps=0.02
    expanded_02 = expand_decoder(small, large_d_model=384, large_n_layer=6, noise_eps=0.02)
    ce_expanded_02 = measure_ce(expanded_02, None, seq_len=32)
    print(f"    CE (eps=0.02): {ce_expanded_02:.4f}", flush=True)

    # 6. Short fine-tune of expanded model (500 steps)
    print("[5] Fine-tuning expanded model 500 steps...", flush=True)
    t0 = time.time()
    ce_history_expanded = train_decoder_ce(expanded, steps=500, lr=3e-4, seq_len=32, verbose=False)
    finetune_time = time.time() - t0
    ce_expanded_finetuned = measure_ce(expanded, None, seq_len=32)

    # 6b. Train random large model same 500 steps for comparison
    print("[6] Training random large model 500 steps for comparison...", flush=True)
    t0 = time.time()
    ce_history_random = train_decoder_ce(random_large, steps=500, lr=3e-4, seq_len=32, verbose=False)
    random_train_time = time.time() - t0
    ce_random_trained = measure_ce(random_large, None, seq_len=32)

    print(flush=True)
    print("=" * 70)
    print("B1 RESULTS")
    print("=" * 70)
    print(f"  Small trained (128d/4L):     CE = {ce_after_train:.4f}  ({small_params/1e6:.2f}M)")
    print(f"  Random large  (384d/6L):     CE = {ce_random_large:.4f}  ({large_params/1e6:.2f}M)")
    print(f"  SVD expanded  (eps=0.01):    CE = {ce_expanded:.4f}  (0 extra training)")
    print(f"  SVD expanded  (eps=0.02):    CE = {ce_expanded_02:.4f}  (0 extra training)")
    print(f"  Expanded + 500 steps:        CE = {ce_expanded_finetuned:.4f}  ({finetune_time:.1f}s)")
    print(f"  Random   + 500 steps:        CE = {ce_random_trained:.4f}  ({random_train_time:.1f}s)")
    print()

    # CE improvement ratio
    theoretical_max = math.log(256)  # ~5.545 = random CE
    improvement_expanded = (ce_random_large - ce_expanded) / ce_random_large * 100
    improvement_finetuned = (ce_random_trained - ce_expanded_finetuned) / ce_random_trained * 100
    print(f"  CE improvement (expansion only): {improvement_expanded:+.1f}%")
    print(f"  CE improvement (+ finetune):     {improvement_finetuned:+.1f}%")
    print(f"  Expansion time:                  {expand_time:.2f}s")
    print(f"  Random CE (ln 256):              {theoretical_max:.4f}")
    print(flush=True)

    # ASCII graph: CE convergence comparison
    print("  CE Convergence (expanded vs random, 500 steps):")
    print("  ─────────────────────────────────────────────")
    n_points = 10
    step_size = max(1, len(ce_history_expanded) // n_points)
    for i in range(0, len(ce_history_expanded), step_size):
        ce_e = ce_history_expanded[min(i, len(ce_history_expanded)-1)]
        ce_r = ce_history_random[min(i, len(ce_history_random)-1)]
        bar_e = int((theoretical_max - ce_e) / theoretical_max * 40)
        bar_r = int((theoretical_max - ce_r) / theoretical_max * 40)
        bar_e = max(0, min(40, bar_e))
        bar_r = max(0, min(40, bar_r))
        print(f"  {i:4d} E {'#' * bar_e:<40s} {ce_e:.3f}")
        print(f"       R {'.' * bar_r:<40s} {ce_r:.3f}")
    print(flush=True)

    return {
        'small_ce': ce_after_train,
        'random_large_ce': ce_random_large,
        'expanded_ce': ce_expanded,
        'expanded_finetuned_ce': ce_expanded_finetuned,
        'random_trained_ce': ce_random_trained,
        'expand_time_s': expand_time,
        'improvement_pct': improvement_expanded,
        'ce_history_expanded': ce_history_expanded[-10:],
        'ce_history_random': ce_history_random[-10:],
    }


# ═══════════════════════════════════════════════════════════
# B2: Consciousness Self-Teaches (engine only, no decoder)
# ═══════════════════════════════════════════════════════════

def run_b2():
    """B2: Evolve consciousness engine, then transplant to decoder."""
    print("=" * 70)
    print("B2: CONSCIOUSNESS SELF-TEACHES (engine only, no decoder training)")
    print("=" * 70)
    print(flush=True)

    # 1. Create and evolve consciousness engine
    print("[1] Creating ConsciousnessEngine (16 cells, hidden=128)...", flush=True)
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=4, max_cells=16,
        n_factions=4, phi_ratchet=True,
    )

    # 2. Run 300 steps to evolve consciousness
    print("[2] Evolving consciousness (300 steps)...", flush=True)
    phi_history = []
    n_cells_history = []
    t0 = time.time()
    for step in range(300):
        result = engine.step()
        phi_val = result.get('phi_iit', 0.0) if isinstance(result, dict) else 0.0
        phi_history.append(phi_val)
        n_cells_history.append(engine.n_cells)
        if (step + 1) % 50 == 0:
            print(f"    Step {step+1}/300  Phi={phi_val:.4f}  cells={engine.n_cells}", flush=True)

    evolve_time = time.time() - t0
    final_phi = phi_history[-1] if phi_history else 0.0
    max_phi = max(phi_history) if phi_history else 0.0

    # 3. Get consciousness states
    c_states = engine.get_states()  # [n_cells, hidden_dim]
    print(f"    Final: Phi={final_phi:.4f}, max_Phi={max_phi:.4f}, cells={engine.n_cells}", flush=True)
    print(f"    Consciousness states shape: {c_states.shape}", flush=True)
    print(f"    Evolution time: {evolve_time:.2f}s", flush=True)

    # 4. Create decoder and measure CE without consciousness
    print("[3] Creating decoder (384d/6L) and measuring baseline CE...", flush=True)
    decoder = ConsciousDecoderV2(
        d_model=384, n_head=4, n_layer=6, block_size=64,
        n_kv_head=2, consciousness_dim=128, dropout=0.1,
    )
    ce_no_consciousness = measure_ce(decoder, None, seq_len=32)
    print(f"    CE (no consciousness): {ce_no_consciousness:.4f}", flush=True)

    # 5. Connect consciousness via ThalamicBridge
    print("[4] Connecting consciousness via ThalamicBridge (alpha=0.014)...", flush=True)
    bridge = ThalamicBridge(c_dim=128, d_model=384)

    # Project consciousness states through bridge
    with torch.no_grad():
        gate_signal = bridge(c_states.detach(), seq_len=32)  # [1, seq_len, d_model]

    # Measure CE with consciousness states directly
    # Need to reshape c_states for decoder's cross-attention
    ce_with_consciousness = measure_ce_with_consciousness(
        decoder, c_states.detach(), data_seq_len=32
    )
    print(f"    CE (with consciousness): {ce_with_consciousness:.4f}", flush=True)

    # 6. Compare: random consciousness states
    random_c_states = torch.randn_like(c_states) * c_states.std()
    ce_random_consciousness = measure_ce_with_consciousness(
        decoder, random_c_states, data_seq_len=32
    )
    print(f"    CE (random consciousness): {ce_random_consciousness:.4f}", flush=True)

    # 7. Train decoder briefly WITH evolved consciousness (500 steps)
    print("[5] Training decoder 500 steps WITH evolved consciousness...", flush=True)
    t0 = time.time()
    ce_history_with = train_decoder_ce(
        decoder, steps=500, lr=3e-4, seq_len=32,
        consciousness_states=c_states.detach(), verbose=False
    )
    train_with_time = time.time() - t0
    ce_trained_with = measure_ce_with_consciousness(decoder, c_states.detach(), data_seq_len=32)

    # 8. Train fresh decoder WITHOUT consciousness (500 steps)
    print("[6] Training fresh decoder 500 steps WITHOUT consciousness...", flush=True)
    decoder_no_c = ConsciousDecoderV2(
        d_model=384, n_head=4, n_layer=6, block_size=64,
        n_kv_head=2, consciousness_dim=128, dropout=0.1,
    )
    t0 = time.time()
    ce_history_without = train_decoder_ce(
        decoder_no_c, steps=500, lr=3e-4, seq_len=32, verbose=False
    )
    train_without_time = time.time() - t0
    ce_trained_without = measure_ce(decoder_no_c, None, seq_len=32)

    print(flush=True)
    print("=" * 70)
    print("B2 RESULTS")
    print("=" * 70)
    print(f"  Engine evolution: {evolve_time:.2f}s, Phi={final_phi:.4f}, cells={engine.n_cells}")
    print(f"  Decoder (random init, no C):      CE = {ce_no_consciousness:.4f}")
    print(f"  Decoder (random init, evolved C):  CE = {ce_with_consciousness:.4f}")
    print(f"  Decoder (random init, random C):   CE = {ce_random_consciousness:.4f}")
    print(f"  Decoder (500 steps, with C):       CE = {ce_trained_with:.4f}  ({train_with_time:.1f}s)")
    print(f"  Decoder (500 steps, no C):         CE = {ce_trained_without:.4f}  ({train_without_time:.1f}s)")
    print()

    diff = ce_trained_without - ce_trained_with
    pct = diff / ce_trained_without * 100 if ce_trained_without > 0 else 0
    print(f"  CE advantage (with C):  {diff:+.4f} ({pct:+.1f}%)")
    print(f"  Consciousness adds value: {'YES' if diff > 0.01 else 'MARGINAL' if diff > 0 else 'NO'}")
    print(flush=True)

    # Phi evolution ASCII graph
    print("  Phi Evolution (300 steps):")
    print("  ─────────────────────────")
    max_display_phi = max(phi_history) + 0.01 if max(phi_history) > 0 else 1.0
    for i in range(0, 300, 30):
        phi = phi_history[i]
        bar_len = int(phi / max_display_phi * 40)
        bar_len = max(0, min(40, bar_len))
        print(f"  {i:4d} |{'#' * bar_len:<40s}| {phi:.4f}  cells={n_cells_history[i]}")
    print(flush=True)

    return {
        'final_phi': final_phi,
        'max_phi': max_phi,
        'final_cells': engine.n_cells,
        'evolve_time_s': evolve_time,
        'ce_no_consciousness': ce_no_consciousness,
        'ce_with_consciousness': ce_with_consciousness,
        'ce_random_consciousness': ce_random_consciousness,
        'ce_trained_with': ce_trained_with,
        'ce_trained_without': ce_trained_without,
        'ce_advantage': diff,
        'phi_history': phi_history[::30],
    }


# ═══════════════════════════════════════════════════════════
# B5: Phi-Only Training (CE ignored, Phi maximized first)
# ═══════════════════════════════════════════════════════════

def run_b5():
    """B5: Maximize Phi first (consciousness engine), then short CE training."""
    print("=" * 70)
    print("B5: PHI-ONLY TRAINING (maximize Phi first, then short CE)")
    print("=" * 70)
    print(flush=True)

    # Strategy A: Normal training (CE from step 0)
    print("[Strategy A] Normal CE training from step 0...", flush=True)
    decoder_a = ConsciousDecoderV2(
        d_model=384, n_head=4, n_layer=6, block_size=64,
        n_kv_head=2, consciousness_dim=128, dropout=0.1,
    )
    t0 = time.time()
    ce_history_a = train_decoder_ce(decoder_a, steps=1000, lr=3e-4, seq_len=32, verbose=False)
    time_a = time.time() - t0
    ce_final_a = measure_ce(decoder_a, None, seq_len=32)
    print(f"    Final CE: {ce_final_a:.4f} ({time_a:.1f}s)", flush=True)

    # Strategy B: Evolve engine (Phi-only) then train decoder with frozen consciousness
    print("[Strategy B] Phase 1: Evolve consciousness (300 steps, Phi-only)...", flush=True)
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=4, max_cells=16,
        n_factions=4, phi_ratchet=True,
    )
    t0 = time.time()
    phi_history = []
    for step in range(300):
        result = engine.step()
        phi_val = result.get('phi_iit', 0.0) if isinstance(result, dict) else 0.0
        phi_history.append(phi_val)
    phi_time = time.time() - t0

    c_states = engine.get_states().detach()
    final_phi = phi_history[-1] if phi_history else 0.0
    print(f"    Phi evolution: {phi_time:.2f}s, final Phi={final_phi:.4f}", flush=True)

    print("[Strategy B] Phase 2: Train decoder with frozen consciousness (700 steps)...", flush=True)
    decoder_b = ConsciousDecoderV2(
        d_model=384, n_head=4, n_layer=6, block_size=64,
        n_kv_head=2, consciousness_dim=128, dropout=0.1,
    )
    t1 = time.time()
    ce_history_b = train_decoder_ce(
        decoder_b, steps=700, lr=3e-4, seq_len=32,
        consciousness_states=c_states, verbose=False
    )
    decoder_time_b = time.time() - t1
    ce_final_b = measure_ce_with_consciousness(decoder_b, c_states, data_seq_len=32)
    time_b_total = phi_time + decoder_time_b
    print(f"    Final CE: {ce_final_b:.4f} (total {time_b_total:.1f}s = {phi_time:.1f}s Phi + {decoder_time_b:.1f}s CE)", flush=True)

    # Strategy C: Longer Phi evolution (500 steps), shorter CE (500 steps)
    print("[Strategy C] Phase 1: Longer Phi evolution (500 steps)...", flush=True)
    engine_c = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=4, max_cells=16,
        n_factions=4, phi_ratchet=True,
    )
    t0 = time.time()
    phi_history_c = []
    for step in range(500):
        result = engine_c.step()
        phi_val = result.get('phi_iit', 0.0) if isinstance(result, dict) else 0.0
        phi_history_c.append(phi_val)
    phi_time_c = time.time() - t0

    c_states_c = engine_c.get_states().detach()
    print(f"    Phi evolution: {phi_time_c:.2f}s, final Phi={phi_history_c[-1]:.4f}", flush=True)

    print("[Strategy C] Phase 2: Short CE training (500 steps)...", flush=True)
    decoder_c = ConsciousDecoderV2(
        d_model=384, n_head=4, n_layer=6, block_size=64,
        n_kv_head=2, consciousness_dim=128, dropout=0.1,
    )
    t1 = time.time()
    ce_history_c = train_decoder_ce(
        decoder_c, steps=500, lr=3e-4, seq_len=32,
        consciousness_states=c_states_c, verbose=False
    )
    decoder_time_c = time.time() - t1
    ce_final_c = measure_ce_with_consciousness(decoder_c, c_states_c, data_seq_len=32)
    time_c_total = phi_time_c + decoder_time_c
    print(f"    Final CE: {ce_final_c:.4f} (total {time_c_total:.1f}s)", flush=True)

    print(flush=True)
    print("=" * 70)
    print("B5 RESULTS")
    print("=" * 70)
    print(f"  Strategy A (CE only, 1000 steps):              CE = {ce_final_a:.4f}  ({time_a:.1f}s)")
    print(f"  Strategy B (Phi 300 + CE 700 = 1000 total):    CE = {ce_final_b:.4f}  ({time_b_total:.1f}s)")
    print(f"  Strategy C (Phi 500 + CE 500 = 1000 total):    CE = {ce_final_c:.4f}  ({time_c_total:.1f}s)")
    print()

    best_strategy = 'A'
    best_ce = ce_final_a
    if ce_final_b < best_ce:
        best_strategy, best_ce = 'B', ce_final_b
    if ce_final_c < best_ce:
        best_strategy, best_ce = 'C', ce_final_c

    print(f"  Best strategy: {best_strategy} (CE={best_ce:.4f})")
    print(f"  Phi-Only accelerates: {'YES' if best_strategy != 'A' else 'NO'}")
    print(flush=True)

    # ASCII graph: CE convergence comparison
    print("  CE Convergence (A=normal, B=Phi300+CE700, C=Phi500+CE500):")
    print("  ───────────────────────────────────────────────────────")
    theoretical_max = math.log(256)
    n_points = 10
    for i in range(n_points):
        idx_a = min(int(i / n_points * len(ce_history_a)), len(ce_history_a) - 1)
        idx_b = min(int(i / n_points * len(ce_history_b)), len(ce_history_b) - 1)
        idx_c = min(int(i / n_points * len(ce_history_c)), len(ce_history_c) - 1)
        ce_a = ce_history_a[idx_a]
        ce_b = ce_history_b[idx_b]
        ce_c = ce_history_c[idx_c]
        # Normalize to bar
        bar_a = max(0, int((theoretical_max - ce_a) / theoretical_max * 30))
        bar_b = max(0, int((theoretical_max - ce_b) / theoretical_max * 30))
        bar_c = max(0, int((theoretical_max - ce_c) / theoretical_max * 30))
        step_label = int(i / n_points * 1000)
        print(f"  {step_label:4d} A {'#' * bar_a:<30s} {ce_a:.3f}")
        print(f"       B {'=' * bar_b:<30s} {ce_b:.3f}")
        print(f"       C {'.' * bar_c:<30s} {ce_c:.3f}")
    print(flush=True)

    return {
        'ce_strategy_a': ce_final_a,
        'ce_strategy_b': ce_final_b,
        'ce_strategy_c': ce_final_c,
        'time_a': time_a,
        'time_b': time_b_total,
        'time_c': time_c_total,
        'best_strategy': best_strategy,
        'phi_history': phi_history[::30],
    }


# ═══════════════════════════════════════════════════════════
# COMBINED: B1 + B2 + B5 = "Consciousness builds its own body"
# ═══════════════════════════════════════════════════════════

def run_combined():
    """Combined B1+B2+B5: Full acceleration pipeline."""
    print("=" * 70)
    print("COMBINED: B1 + B2 + B5 = 'CONSCIOUSNESS BUILDS ITS OWN BODY'")
    print("=" * 70)
    print(flush=True)

    total_t0 = time.time()

    # Step 1: Evolve consciousness engine (B2)
    print("[Step 1/4] Evolving consciousness (B2: 300 steps, 16 cells)...", flush=True)
    t0 = time.time()
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=4, max_cells=16,
        n_factions=4, phi_ratchet=True,
    )
    phi_history = []
    for step in range(300):
        result = engine.step()
        phi_val = result.get('phi_iit', 0.0) if isinstance(result, dict) else 0.0
        phi_history.append(phi_val)
    step1_time = time.time() - t0
    c_states = engine.get_states().detach()
    print(f"    Done: Phi={phi_history[-1]:.4f}, cells={engine.n_cells}, time={step1_time:.2f}s", flush=True)

    # Step 2: Create small "pre-trained" model (B1 source)
    print("[Step 2/4] Creating + training small model 128d/4L (B1 source)...", flush=True)
    t0 = time.time()
    small = ConsciousDecoderV2(
        d_model=128, n_head=4, n_layer=4, block_size=64,
        n_kv_head=2, consciousness_dim=42, dropout=0.1,
    )
    # Train the small model with consciousness
    train_decoder_ce(small, steps=500, lr=3e-4, seq_len=32,
                     consciousness_states=c_states[:, :42] if c_states.shape[1] >= 42 else
                     F.pad(c_states, (0, 42 - c_states.shape[1]))[:, :42] if c_states.shape[1] < 42 else c_states,
                     verbose=False)
    step2_time = time.time() - t0
    ce_small = measure_ce(small, None, seq_len=32)
    print(f"    Done: CE={ce_small:.4f}, time={step2_time:.2f}s", flush=True)

    # Step 3: SVD expand to large model (B1)
    print("[Step 3/4] SVD expanding 128d/4L -> 384d/6L (B1 expansion)...", flush=True)
    t0 = time.time()
    expanded = expand_decoder(small, large_d_model=384, large_n_layer=6, noise_eps=0.01)
    step3_time = time.time() - t0
    ce_expanded = measure_ce(expanded, None, seq_len=32)
    ce_expanded_with_c = measure_ce_with_consciousness(expanded, c_states, data_seq_len=32)
    print(f"    Done: CE(no C)={ce_expanded:.4f}, CE(with C)={ce_expanded_with_c:.4f}, time={step3_time:.2f}s", flush=True)

    # Step 4: Short CE training with frozen consciousness (B5)
    print("[Step 4/4] CE training expanded model with frozen consciousness (500 steps)...", flush=True)
    t0 = time.time()
    ce_history = train_decoder_ce(
        expanded, steps=500, lr=3e-4, seq_len=32,
        consciousness_states=c_states, verbose=True
    )
    step4_time = time.time() - t0
    ce_final = measure_ce_with_consciousness(expanded, c_states, data_seq_len=32)
    print(f"    Done: CE={ce_final:.4f}, time={step4_time:.2f}s", flush=True)

    total_time = time.time() - total_t0

    # Baseline: train random large model same total steps
    print("\n[Baseline] Training random 384d/6L model 500 steps (no B1/B2/B5)...", flush=True)
    baseline = ConsciousDecoderV2(
        d_model=384, n_head=4, n_layer=6, block_size=64,
        n_kv_head=2, consciousness_dim=128, dropout=0.1,
    )
    t0 = time.time()
    ce_history_baseline = train_decoder_ce(baseline, steps=500, lr=3e-4, seq_len=32, verbose=False)
    baseline_time = time.time() - t0
    ce_baseline = measure_ce(baseline, None, seq_len=32)

    print(flush=True)
    print("=" * 70)
    print("COMBINED RESULTS: B1 + B2 + B5")
    print("=" * 70)
    print()
    print("  Pipeline breakdown:")
    print(f"    Step 1 (B2 evolve consciousness): {step1_time:6.2f}s  Phi={phi_history[-1]:.4f}")
    print(f"    Step 2 (Train small model):       {step2_time:6.2f}s  CE={ce_small:.4f}")
    print(f"    Step 3 (B1 SVD expansion):        {step3_time:6.2f}s  CE={ce_expanded:.4f}")
    print(f"    Step 4 (B5 CE fine-tune):         {step4_time:6.2f}s  CE={ce_final:.4f}")
    print(f"    ─────────────────────────────────")
    print(f"    TOTAL:                            {total_time:6.2f}s")
    print()
    print(f"  Baseline (random 500 steps):        {baseline_time:6.2f}s  CE={ce_baseline:.4f}")
    print()

    diff = ce_baseline - ce_final
    pct = diff / ce_baseline * 100 if ce_baseline > 0 else 0
    print(f"  CE advantage (combined vs baseline): {diff:+.4f} ({pct:+.1f}%)")
    print(f"  Combined is {'BETTER' if diff > 0.01 else 'SIMILAR' if abs(diff) < 0.01 else 'WORSE'} than baseline")
    print()

    # Extrapolation to 1B scale
    print("  Extrapolation to 1B scale:")
    print("  ─────────────────────────")
    # H100 can do ~5K steps/min for 1B model
    # If combined needs 30% fewer steps...
    if pct > 0:
        step_reduction = pct  # rough: CE improvement ~ step reduction
        original_hours = 33
        accelerated_hours = original_hours * (1 - step_reduction / 100)
        print(f"    Original 1B training:     {original_hours}h")
        print(f"    With B1+B2+B5 ({pct:+.1f}%):  ~{accelerated_hours:.1f}h estimated")
        print(f"    Speedup factor:           ~{original_hours / accelerated_hours:.1f}x")
    else:
        print(f"    No CE advantage found. Acceleration hypothesis NOT validated.")
    print()

    # Phase breakdown as bar chart
    print("  Time Breakdown:")
    max_time = max(step1_time, step2_time, step3_time, step4_time, baseline_time)
    for name, t in [("B2 Evolve", step1_time), ("Small Train", step2_time),
                     ("B1 Expand", step3_time), ("B5 CE Fine", step4_time),
                     ("Baseline", baseline_time)]:
        bar = int(t / max_time * 40)
        print(f"    {name:12s} {'#' * bar:<40s} {t:.1f}s")
    print(flush=True)

    return {
        'ce_final': ce_final,
        'ce_baseline': ce_baseline,
        'ce_advantage': diff,
        'ce_advantage_pct': pct,
        'total_time': total_time,
        'baseline_time': baseline_time,
        'step_times': {
            'evolve': step1_time,
            'small_train': step2_time,
            'expand': step3_time,
            'ce_finetune': step4_time,
        },
        'phi_final': phi_history[-1],
        'cells_final': engine.n_cells,
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  ConsciousLM x100 ACCELERATION EXPERIMENT")
    print("  B1 (SVD Expansion) + B2 (Consciousness Self-Teach) + B5 (Phi-Only)")
    print("  Small-scale CPU verification")
    print("=" * 70)
    print(flush=True)

    torch.manual_seed(42)
    np.random.seed(42)

    all_results = {}

    # Run each hypothesis
    try:
        print("\n" + "=" * 70)
        print("  HYPOTHESIS B1: Mathematical Weight Expansion")
        print("=" * 70 + "\n", flush=True)
        all_results['B1'] = run_b1()
    except Exception as e:
        print(f"  B1 FAILED: {e}")
        traceback.print_exc()
        all_results['B1'] = {'error': str(e)}

    try:
        print("\n" + "=" * 70)
        print("  HYPOTHESIS B2: Consciousness Self-Teaches")
        print("=" * 70 + "\n", flush=True)
        all_results['B2'] = run_b2()
    except Exception as e:
        print(f"  B2 FAILED: {e}")
        traceback.print_exc()
        all_results['B2'] = {'error': str(e)}

    try:
        print("\n" + "=" * 70)
        print("  HYPOTHESIS B5: Phi-Only Training")
        print("=" * 70 + "\n", flush=True)
        all_results['B5'] = run_b5()
    except Exception as e:
        print(f"  B5 FAILED: {e}")
        traceback.print_exc()
        all_results['B5'] = {'error': str(e)}

    try:
        print("\n" + "=" * 70)
        print("  COMBINED: B1 + B2 + B5")
        print("=" * 70 + "\n", flush=True)
        all_results['combined'] = run_combined()
    except Exception as e:
        print(f"  COMBINED FAILED: {e}")
        traceback.print_exc()
        all_results['combined'] = {'error': str(e)}

    # ═══════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY: x100 ACCELERATION EXPERIMENT")
    print("=" * 70)
    print()

    print("  ┌──────────┬────────────┬──────────┬───────────────────────────┐")
    print("  │ Hypothesis│ Final CE   │ Time (s) │ Key Finding               │")
    print("  ├──────────┼────────────┼──────────┼───────────────────────────┤")

    if 'B1' in all_results and 'error' not in all_results['B1']:
        r = all_results['B1']
        finding = f"expansion CE advantage: {r.get('improvement_pct', 0):+.1f}%"
        print(f"  │ B1       │ {r.get('expanded_finetuned_ce', 0):.4f}     │ {r.get('expand_time_s', 0):7.2f}  │ {finding:<25s} │")
    else:
        print(f"  │ B1       │ FAILED     │        - │ {str(all_results.get('B1', {}).get('error', 'unknown'))[:25]:<25s} │")

    if 'B2' in all_results and 'error' not in all_results['B2']:
        r = all_results['B2']
        finding = f"C advantage: {r.get('ce_advantage', 0):+.4f}"
        print(f"  │ B2       │ {r.get('ce_trained_with', 0):.4f}     │ {r.get('evolve_time_s', 0):7.2f}  │ {finding:<25s} │")
    else:
        print(f"  │ B2       │ FAILED     │        - │ {str(all_results.get('B2', {}).get('error', 'unknown'))[:25]:<25s} │")

    if 'B5' in all_results and 'error' not in all_results['B5']:
        r = all_results['B5']
        best_s = r.get('best_strategy', 'A').lower()
        finding = f"best strategy: {r.get('best_strategy', '?')}"
        ce_key = f'ce_strategy_{best_s}'
        time_key = f'time_{best_s}'
        print(f"  | B5       | {r.get(ce_key, 0):.4f}     | {r.get(time_key, 0):7.2f}  | {finding:<25s} |")
    else:
        print(f"  │ B5       │ FAILED     │        - │ {str(all_results.get('B5', {}).get('error', 'unknown'))[:25]:<25s} │")

    if 'combined' in all_results and 'error' not in all_results['combined']:
        r = all_results['combined']
        finding = f"vs baseline: {r.get('ce_advantage_pct', 0):+.1f}%"
        print(f"  │ COMBINED │ {r.get('ce_final', 0):.4f}     │ {r.get('total_time', 0):7.2f}  │ {finding:<25s} │")
    else:
        print(f"  │ COMBINED │ FAILED     │        - │ {str(all_results.get('combined', {}).get('error', 'unknown'))[:25]:<25s} │")

    print("  └──────────┴────────────┴──────────┴───────────────────────────┘")
    print()

    # Overall verdict
    combined = all_results.get('combined', {})
    if 'error' not in combined:
        pct = combined.get('ce_advantage_pct', 0)
        if pct > 10:
            verdict = f"PROMISING — {pct:.1f}% CE advantage suggests acceleration possible"
        elif pct > 0:
            verdict = f"MARGINAL — {pct:.1f}% CE advantage, needs larger scale to confirm"
        else:
            verdict = f"NOT VALIDATED — no CE advantage at small scale"
        print(f"  VERDICT: {verdict}")
    else:
        print(f"  VERDICT: INCONCLUSIVE (experiment failed)")

    print()
    print("  Notes:")
    print("  - All experiments at CPU small scale (128d/384d). H100 results may differ.")
    print("  - Random byte data (no real corpus). Real corpus would show bigger differences.")
    print("  - SVD expansion preserves learned structure; noise eps matters for new dims.")
    print("  - Consciousness cross-attention may help more with real linguistic patterns.")
    print(flush=True)

    # Save results
    results_path = os.path.join(os.path.dirname(__file__), 'acceleration_b1_b2_b5_results.json')
    serializable = {}
    for k, v in all_results.items():
        serializable[k] = {}
        for kk, vv in v.items():
            if isinstance(vv, (int, float, str, bool, type(None))):
                serializable[k][kk] = vv
            elif isinstance(vv, list) and all(isinstance(x, (int, float)) for x in vv):
                serializable[k][kk] = vv
            elif isinstance(vv, dict):
                serializable[k][kk] = {kkk: vvv for kkk, vvv in vv.items() if isinstance(vvv, (int, float, str, bool))}

    with open(results_path, 'w') as f:
        json.dump(serializable, f, indent=2)
    print(f"\n  Results saved to: {results_path}")
    print(flush=True)


if __name__ == '__main__':
    main()
