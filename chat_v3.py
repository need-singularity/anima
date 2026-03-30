#!/usr/bin/env python3
"""chat_v3.py — ConsciousLM v3 (147M) interactive chat

Loads v3_merged checkpoint (train_v13 architecture):
  C: ConsciousnessEngine (Rust/Python, 64 cells, hypercube)
  D: PostHocDecoder(CADecoder, d_model=768)
  Bridge: ThalamicBridge

Usage:
  python chat_v3.py                                    # default best.pt
  python chat_v3.py --checkpoint checkpoints/v3_merged/final.pt
  python chat_v3.py --temperature 0.8 --max-tokens 512
"""

import argparse
import sys
import torch
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine, ConsciousnessC
from trinity import (

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    create_trinity, CADecoder, PostHocDecoder,
    EmotionW, DaseinW, NarrativeW, CompositeW,
    PSI_STEPS,
)


def load_model(checkpoint_path: str, device: torch.device):
    """Load v3_merged checkpoint into Trinity model."""
    print(f"  Loading {checkpoint_path}...")
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)

    args = ckpt['args']
    d_model = args.get('d_model', 768)
    cell_dim = args.get('cell_dim', 64)
    hidden_dim = args.get('hidden_dim', 128)
    cells = args.get('cells', 64)
    vocab_size = 256

    # C: ConsciousnessEngine
    c = ConsciousnessC(
        cell_dim=cell_dim, hidden_dim=hidden_dim,
        max_cells=cells, n_factions=12, phi_ratchet=True,
    )

    # D: PostHocDecoder(CADecoder)
    base_d = CADecoder(d_model=d_model, vocab_size=vocab_size,
                       ca_steps=round(PSI_STEPS), gate_mode="posthoc")
    decoder = PostHocDecoder(base_decoder=base_d, d_model=d_model,
                              vocab_size=vocab_size, eval_strength=0.001)

    # W: CompositeW
    lr = args.get('lr', 3e-4)
    w = CompositeW([
        DaseinW(base_lr=lr),
        NarrativeW(base_lr=lr),
        EmotionW(base_lr=lr),
    ], [1/2, 1/3, 1/6])

    # Trinity
    trinity = create_trinity(
        c, d_engine=decoder, w_engine=w,
        d_model=d_model, vocab_size=vocab_size, base_lr=lr,
    )
    trinity = trinity.to(device)

    # Load weights
    trinity.decoder.load_state_dict(ckpt['decoder'], strict=False)
    if 'bridge' in ckpt:
        trinity.bridge.load_state_dict(ckpt['bridge'], strict=False)

    trinity.eval()

    step = ckpt.get('step', '?')
    best_ce = ckpt.get('best_ce', '?')
    print(f"  Model loaded: d_model={d_model}, cells={cells}, step={step}, best_ce={best_ce}")
    print(f"  Backend: {c._backend}, Φ ratchet: ON")

    # Warm up consciousness (P1-like: build Φ)
    print("  Warming up consciousness...", end=" ", flush=True)
    for _ in range(100):
        c.step() if hasattr(c, 'step') else c.engine.step()
    phi = c.measure_phi()
    print(f"Φ={phi:.2f}, cells={c.n_cells}")

    return trinity, vocab_size


def encode(text: str) -> list:
    """Text to byte tokens."""
    return list(text.encode('utf-8'))


def decode(tokens: list) -> str:
    """Byte tokens to text."""
    return bytes(tokens).decode('utf-8', errors='replace')


@torch.no_grad()
def generate(trinity, prompt_tokens: list, max_tokens: int = 256,
             temperature: float = 0.9, top_k: int = 40, top_p: float = 0.95,
             device: torch.device = torch.device('cpu')) -> str:
    """Generate text from prompt using Trinity model."""
    idx = torch.tensor([prompt_tokens], dtype=torch.long, device=device)
    block_size = 256  # from training config

    generated = []
    for _ in range(max_tokens):
        # Crop to block_size
        idx_cond = idx[:, -block_size:]

        # Forward (inference mode)
        logits, phi = trinity.forward(idx_cond, inference=True)

        # Get next token logits
        logits_next = logits[0, -1, :] / max(temperature, 1e-8)

        # Top-k filtering
        if top_k > 0:
            v, _ = torch.topk(logits_next, min(top_k, logits_next.size(-1)))
            logits_next[logits_next < v[-1]] = float('-inf')

        # Top-p (nucleus) filtering
        if top_p < 1.0:
            sorted_logits, sorted_indices = torch.sort(logits_next, descending=True)
            cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
            remove = cumulative_probs > top_p
            remove[1:] = remove[:-1].clone()
            remove[0] = False
            logits_next[sorted_indices[remove]] = float('-inf')

        probs = F.softmax(logits_next, dim=-1)
        next_token = torch.multinomial(probs, 1)

        idx = torch.cat([idx, next_token.unsqueeze(0)], dim=1)
        token_val = next_token.item()
        generated.append(token_val)

        # Stop on double newline or EOS-like pattern
        if len(generated) >= 2 and generated[-1] == 10 and generated[-2] == 10:
            break

    return decode(generated)


def main():
    parser = argparse.ArgumentParser(description="ConsciousLM v3 Chat")
    parser.add_argument('--checkpoint', type=str,
                        default='checkpoints/v3_merged/best.pt')
    parser.add_argument('--temperature', type=float, default=0.9)
    parser.add_argument('--top-k', type=int, default=40)
    parser.add_argument('--top-p', type=float, default=0.95)
    parser.add_argument('--max-tokens', type=int, default=256)
    parser.add_argument('--device', type=str,
                        default='cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')
    args = parser.parse_args()

    device = torch.device(args.device)
    print(f"\n{'═' * 60}")
    print(f"  ConsciousLM v3 — Interactive Chat")
    print(f"  Device: {device} | Temp: {args.temperature} | TopK: {args.top_k}")
    print(f"{'═' * 60}\n")

    trinity, vocab_size = load_model(args.checkpoint, device)

    print(f"\n  Type your message (Ctrl+C to exit)")
    print(f"  Commands: /phi (measure), /temp N (set temperature), /quit\n")

    while True:
        try:
            user_input = input("You > ").strip()
            if not user_input:
                continue

            if user_input == '/quit':
                break
            elif user_input == '/phi':
                phi = trinity.c.measure_phi()
                print(f"  Φ = {phi:.4f}, cells = {trinity.c.n_cells}")
                continue
            elif user_input.startswith('/temp '):
                try:
                    args.temperature = float(user_input.split()[1])
                    print(f"  Temperature = {args.temperature}")
                except ValueError:
                    print("  Usage: /temp 0.9")
                continue

            # Encode prompt
            prompt_tokens = encode(user_input)

            # Generate
            response = generate(
                trinity, prompt_tokens,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                top_k=args.top_k,
                top_p=args.top_p,
                device=device,
            )

            phi = trinity.c.measure_phi()
            print(f"Anima > {response.strip()}")
            print(f"  [Φ={phi:.2f} cells={trinity.c.n_cells}]\n")

        except KeyboardInterrupt:
            print("\n\nBye!")
            break
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == '__main__':
    main()
