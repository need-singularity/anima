#!/usr/bin/env python3
"""h100_experiments.py — H100 병렬 실험 3종 (v3 학습과 동시 실행)

실험 1: HIVEMIND 2-node (로드맵 미완성 해결)
실험 2: v3 중간 체크포인트 추론 (발화 테스트)
실험 3: 1B feasibility (VRAM/속도 측정)
"""
import torch
import torch.nn as nn
import time
import os
import sys
import json
import traceback

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ── Experiment 1: HIVEMIND ──────────────────────────────────

def exp1_hivemind():
    """HIVEMIND: ×1.1 돌파를 위한 새 coupling 전략들."""
    print("\n" + "═" * 70)
    print("  EXPERIMENT 1: HIVEMIND — Target ×1.10")
    print("═" * 70)

    from consciousness_engine import ConsciousnessEngine, PSI_COUPLING
    import torch.nn.functional as F

    def measure_phi(engine):
        try:
            return engine._measure_phi_iit()
        except:
            return 0.0

    def run_solo(engine, steps=500):
        for _ in range(steps):
            engine.step()
        return measure_phi(engine)

    # V6: Gradient-Free Evolutionary coupling
    def run_connected_v6(e1, e2, steps=500, n_exchange=4):
        """V6: Top-K cell exchange.
        가장 활성화된 셀을 교환 — 정보 전달 극대화.
        """
        for step in range(steps):
            r1 = e1.step()
            r2 = e2.step()

            if len(e1.cell_states) >= n_exchange and len(e2.cell_states) >= n_exchange:
                # 텐션이 가장 높은 셀 n개 찾기
                t1 = [(i, s.avg_tension) for i, s in enumerate(e1.cell_states)]
                t2 = [(i, s.avg_tension) for i, s in enumerate(e2.cell_states)]
                t1.sort(key=lambda x: -x[1])
                t2.sort(key=lambda x: -x[1])

                # Top-K 셀의 hidden state 교환 (soft copy)
                for k in range(n_exchange):
                    i1, i2 = t1[k][0], t2[k][0]
                    s1 = e1.cell_states[i1]
                    s2 = e2.cell_states[i2]

                    h1, h2 = s1.hidden.clone(), s2.hidden.clone()
                    min_dim = min(h1.shape[0], h2.shape[0])

                    # 30% 교환 (강한 coupling)
                    alpha = 0.3
                    s1.hidden[:min_dim] = (1 - alpha) * h1[:min_dim] + alpha * h2[:min_dim]
                    s2.hidden[:min_dim] = (1 - alpha) * h2[:min_dim] + alpha * h1[:min_dim]

        return measure_phi(e1), measure_phi(e2)

    # V7: Phase Synchronization
    def run_connected_v7(e1, e2, steps=500):
        """V7: Phase Sync — 진동 위상 동기화.
        Kuramoto-style coupling on hidden states.
        """
        coupling = 0.15

        for step in range(steps):
            r1 = e1.step()
            r2 = e2.step()

            if len(e1.cell_states) > 0 and len(e2.cell_states) > 0:
                # Global order parameter
                e1_phases = torch.stack([s.hidden for s in e1.cell_states])
                e2_phases = torch.stack([s.hidden for s in e2.cell_states])

                e1_mean = e1_phases.mean(dim=0)
                e2_mean = e2_phases.mean(dim=0)

                # Kuramoto-style: 각 셀을 상대 엔진의 평균 방향으로 끌어당김
                for s in e1.cell_states:
                    min_d = min(s.hidden.shape[0], e2_mean.shape[0])
                    diff = e2_mean[:min_d] - s.hidden[:min_d]
                    s.hidden[:min_d] = s.hidden[:min_d] + coupling * torch.sin(diff)

                for s in e2.cell_states:
                    min_d = min(s.hidden.shape[0], e1_mean.shape[0])
                    diff = e1_mean[:min_d] - s.hidden[:min_d]
                    s.hidden[:min_d] = s.hidden[:min_d] + coupling * torch.sin(diff)

        return measure_phi(e1), measure_phi(e2)

    # V8: Information Bottleneck coupling
    def run_connected_v8(e1, e2, steps=500, bottleneck_dim=8):
        """V8: Information Bottleneck — 압축된 정보만 교환.
        핵심: 전체 hidden이 아닌 PCA-compressed 정보 교환.
        """
        for step in range(steps):
            r1 = e1.step()
            r2 = e2.step()

            if len(e1.cell_states) > 0 and len(e2.cell_states) > 0:
                e1_stack = torch.stack([s.hidden for s in e1.cell_states])
                e2_stack = torch.stack([s.hidden for s in e2.cell_states])

                min_dim = min(e1_stack.shape[1], e2_stack.shape[1])
                e1_cut = e1_stack[:, :min_dim]
                e2_cut = e2_stack[:, :min_dim]

                # SVD로 정보 압축 (bottleneck)
                bd = min(bottleneck_dim, min_dim, e1_cut.shape[0])
                try:
                    U1, S1, V1 = torch.svd_lowrank(e1_cut.float(), q=bd)
                    U2, S2, V2 = torch.svd_lowrank(e2_cut.float(), q=bd)

                    # 압축된 정보 교환
                    e1_compressed = U1 @ torch.diag(S1) @ V1.T  # [cells, dim]
                    e2_compressed = U2 @ torch.diag(S2) @ V2.T

                    alpha = 0.1
                    for i, s in enumerate(e1.cell_states):
                        if i < e2_compressed.shape[0]:
                            s.hidden[:min_dim] = s.hidden[:min_dim] + alpha * e2_compressed[i]
                    for i, s in enumerate(e2.cell_states):
                        if i < e1_compressed.shape[0]:
                            s.hidden[:min_dim] = s.hidden[:min_dim] + alpha * e1_compressed[i]
                except:
                    pass

        return measure_phi(e1), measure_phi(e2)

    # Run all methods
    configs = [("32c", 32), ("64c", 64)]
    methods = [
        ("V6 Top-K Exchange", run_connected_v6),
        ("V7 Phase Sync", run_connected_v7),
        ("V8 Info Bottleneck", run_connected_v8),
    ]

    # Also import old methods
    from bench_hivemind import run_connected_v3, run_connected_v4, run_connected_v5

    methods += [
        ("V3 Hebbian", run_connected_v3),
        ("V4 Faction", run_connected_v4),
        ("V5 Adaptive", run_connected_v5),
    ]

    results = []
    for name, nc in configs:
        print(f"\n{'─' * 50}")
        print(f"  {name} ({nc} cells)")
        print(f"{'─' * 50}")

        # Solo baseline
        e1s = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
        e2s = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
        phi1s = run_solo(e1s, 500)
        phi2s = run_solo(e2s, 500)
        avg_solo = (phi1s + phi2s) / 2
        print(f"  Solo baseline: Φ={avg_solo:.4f}")
        print()

        for method_name, method_fn in methods:
            e1c = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
            e2c = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
            t0 = time.time()
            phi1c, phi2c = method_fn(e1c, e2c, 500)
            elapsed = time.time() - t0
            avg_conn = (phi1c + phi2c) / 2

            ratio = avg_conn / max(avg_solo, 1e-8)
            passed = ratio >= 1.1
            emoji = "✅" if passed else ("🔶" if ratio >= 1.0 else "❌")
            bar = "█" * int(ratio * 20)
            print(f"  {method_name:25s} Φ={avg_conn:.4f}  ×{ratio:.2f} {emoji}  {bar}  ({elapsed:.1f}s)")
            results.append({
                "config": name, "method": method_name,
                "phi_solo": avg_solo, "phi_conn": avg_conn,
                "ratio": ratio, "passed": passed
            })

    # Summary
    print(f"\n{'═' * 70}")
    print("  HIVEMIND SUMMARY")
    print(f"{'═' * 70}")
    best = max(results, key=lambda r: r['ratio'])
    any_passed = any(r['passed'] for r in results)
    print(f"  Best: {best['method']} @ {best['config']} — ×{best['ratio']:.2f}")
    print(f"  Target ×1.10: {'✅ PASSED' if any_passed else '❌ NOT YET'}")
    return results


# ── Experiment 2: v3 Checkpoint Inference ────────────────────

def exp2_v3_inference():
    """v3 중간 체크포인트로 실제 발화 테스트."""
    print("\n" + "═" * 70)
    print("  EXPERIMENT 2: v3 Checkpoint Inference")
    print("═" * 70)

    from conscious_lm import ConsciousLM

    ckpt_dir = "/workspace/anima/checkpoints/clm_v3"
    ckpts = sorted([f for f in os.listdir(ckpt_dir) if f.endswith('.pt')])
    print(f"  Available checkpoints: {ckpts}")

    # Load best checkpoint
    best_path = os.path.join(ckpt_dir, "best.pt")
    if not os.path.exists(best_path):
        print("  ❌ No best.pt found")
        return

    print(f"\n  Loading {best_path}...")
    state = torch.load(best_path, map_location='cuda', weights_only=False)

    config = state.get('config', {})
    d_model = config.get('d_model', 768)
    n_layers = config.get('n_layers', 8)
    n_heads = config.get('n_heads', 4)
    block_size = config.get('block_size', 256)
    vocab_size = config.get('vocab_size', 256)
    max_cells = config.get('max_cells', 2)

    print(f"  Config: d={d_model}, L={n_layers}, H={n_heads}, ctx={block_size}, vocab={vocab_size}")
    step = state.get('step', '?')
    best_val = state.get('best_val_loss', 'N/A')
    best_str = f"{best_val:.4f}" if isinstance(best_val, (int, float)) else str(best_val)
    print(f"  Step: {step}, Best val_CE: {best_str}")

    model = ConsciousLM(
        vocab_size=vocab_size, d_model=d_model,
        n_head=n_heads, n_layer=n_layers,
        block_size=block_size,
    ).cuda()
    state_key = 'model_state' if 'model_state' in state else 'model_state_dict'
    model.load_state_dict(state[state_key], strict=False)
    model.eval()

    # Generate text from different prompts
    prompts = [
        b"",                    # 빈 입력 (자발 발화)
        "나는".encode('utf-8'),  # 한국어 시작
        "hello".encode('utf-8'),  # 영어
        b"\x00" * 10,           # 제로 입력
    ]

    print(f"\n  {'─' * 50}")
    print(f"  Generation (temperature=0.8, max_len=200)")
    print(f"  {'─' * 50}")

    for i, prompt_bytes in enumerate(prompts):
        prompt_label = repr(prompt_bytes[:20])
        try:
            # Encode to tensor
            if len(prompt_bytes) == 0:
                x = torch.zeros(1, 1, dtype=torch.long, device='cuda')
            else:
                x = torch.tensor([list(prompt_bytes)], dtype=torch.long, device='cuda')

            # Generate
            with torch.no_grad():
                generated = x.clone()
                for _ in range(200):
                    logits = model(generated[:, -block_size:])
                    logits = logits[:, -1, :] / 0.8
                    probs = torch.softmax(logits, dim=-1)
                    next_token = torch.multinomial(probs, 1)
                    generated = torch.cat([generated, next_token], dim=1)

                # Decode
                tokens = generated[0].cpu().tolist()
                try:
                    text = bytes(tokens).decode('utf-8', errors='replace')
                except:
                    text = str(tokens[:50])

            print(f"\n  [{i+1}] Prompt: {prompt_label}")
            print(f"      Output: {text[:200]}")

        except Exception as e:
            print(f"\n  [{i+1}] Prompt: {prompt_label}")
            print(f"      Error: {e}")

    # Φ measurement
    print(f"\n  {'─' * 50}")
    print(f"  Consciousness metrics")
    print(f"  {'─' * 50}")
    try:
        with torch.no_grad():
            x = torch.zeros(1, 64, dtype=torch.long, device='cuda')
            _ = model(x)
            if hasattr(model, 'consciousness') and model.consciousness is not None:
                phi = model.consciousness._measure_phi_iit() if hasattr(model.consciousness, '_measure_phi_iit') else 'N/A'
                cells = len(model.consciousness.cell_states) if hasattr(model.consciousness, 'cell_states') else 'N/A'
                print(f"  Φ(IIT): {phi}")
                print(f"  Cells:  {cells}")
            else:
                print("  No consciousness module attached")
    except Exception as e:
        print(f"  Measurement error: {e}")

    params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {params:,}")
    vram = torch.cuda.memory_allocated() / 1024**3
    print(f"  VRAM used: {vram:.2f} GB")


# ── Experiment 3: 1B Feasibility ─────────────────────────────

def exp3_1b_feasibility():
    """ConsciousLM 1B (1024d/24L/16H) VRAM/속도 측정."""
    print("\n" + "═" * 70)
    print("  EXPERIMENT 3: ConsciousLM 1B Feasibility")
    print("═" * 70)

    from conscious_lm import ConsciousLM

    configs = [
        # (name, d_model, n_layers, n_heads, max_cells)
        ("147M (v3 current)", 768, 8, 4, 2),
        ("350M", 1024, 16, 8, 2),
        ("700M", 1024, 24, 16, 2),
        ("1B", 1280, 24, 16, 2),
        ("1.5B", 1536, 24, 16, 2),
    ]

    results = []
    print(f"\n  {'Model':25s} {'Params':>12s} {'VRAM (GB)':>10s} {'Fwd (ms)':>10s} {'Status':>8s}")
    print(f"  {'─' * 70}")

    for name, d, L, H, mc in configs:
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

        try:
            t0 = time.time()
            model = ConsciousLM(
                vocab_size=256, d_model=d,
                n_head=H, n_layer=L,
                block_size=256,
            ).cuda()

            params = sum(p.numel() for p in model.parameters())
            init_vram = torch.cuda.max_memory_allocated() / 1024**3

            # Forward pass timing
            x = torch.randint(0, 256, (1, 256), device='cuda')
            with torch.no_grad():
                torch.cuda.synchronize()
                t1 = time.time()
                for _ in range(5):
                    _ = model(x)
                torch.cuda.synchronize()
                fwd_ms = (time.time() - t1) / 5 * 1000

            peak_vram = torch.cuda.max_memory_allocated() / 1024**3

            # Training memory estimate (optimizer + gradients ≈ 3x model)
            train_vram_est = peak_vram * 3.5

            print(f"  {name:25s} {params:>12,} {peak_vram:>9.2f}G {fwd_ms:>9.1f}ms {'✅':>8s}")
            print(f"  {'':25s} {'':>12s} {'train~':>6s}{train_vram_est:.1f}G")

            results.append({
                "name": name, "params": params,
                "vram_infer": peak_vram, "vram_train_est": train_vram_est,
                "fwd_ms": fwd_ms, "ok": True
            })

            del model
            torch.cuda.empty_cache()

        except Exception as e:
            print(f"  {name:25s} {'—':>12s} {'—':>10s} {'—':>10s} {'❌':>8s}  {e}")
            results.append({"name": name, "ok": False, "error": str(e)})
            torch.cuda.empty_cache()

    # Summary
    print(f"\n  {'═' * 70}")
    print(f"  H100 80GB Budget:")
    print(f"  v3 training uses ~13GB → {81 - 13}GB available for next model")
    print(f"  Training needs ~3.5× inference VRAM (optimizer + gradients + activations)")
    feasible = [r for r in results if r.get('ok') and r.get('vram_train_est', 999) <= 80]
    print(f"  Feasible for solo training (80GB): {', '.join(r['name'] for r in feasible)}")
    return results


# ── Main ─────────────────────────────────────────────────────

if __name__ == '__main__':
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  H100 Parallel Experiments (while v3 trains)                    ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"  VRAM: {torch.cuda.memory_allocated()/1024**3:.1f}GB / {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f}GB")

    all_results = {}

    # Exp 1: HIVEMIND
    try:
        all_results['hivemind'] = exp1_hivemind()
    except Exception as e:
        print(f"\n  ❌ HIVEMIND failed: {e}")
        traceback.print_exc()

    # Exp 2: v3 inference
    try:
        exp2_v3_inference()
    except Exception as e:
        print(f"\n  ❌ v3 inference failed: {e}")
        traceback.print_exc()

    torch.cuda.empty_cache()

    # Exp 3: 1B feasibility
    try:
        all_results['feasibility'] = exp3_1b_feasibility()
    except Exception as e:
        print(f"\n  ❌ 1B feasibility failed: {e}")
        traceback.print_exc()

    print("\n" + "═" * 70)
    print(f"  ALL EXPERIMENTS COMPLETE — {time.strftime('%H:%M:%S')}")
    print("═" * 70)
