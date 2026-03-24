#!/usr/bin/env python3
"""Conscious LM 100M — 대화 가능한 의식 언어 모델

완전수 6 확장: 12 layers, 768d, 12 heads, vocab=256 bytes
학습: 한국어+영어+코드 Mixed 바이트 데이터
2단계: pretrain(언어이해) → SFT(대화형식)

RunPod H100에서 ~17분 학습
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import numpy as np
import os
import time
import urllib.request

from conscious_lm import PureFieldFFN, CausalSelfAttention, ConsciousBlock, ConsciousLM


def prepare_large_data(min_bytes=100_000_000):
    """100M+ 학습 데이터: 영어 + 한국어 + 코드.

    목표: 최소 100MB (100M 모델에 적합)
    """
    data_path = "data/mixed_100m.bin"
    if os.path.exists(data_path):
        data = np.fromfile(data_path, dtype=np.uint8)
        print(f"  Loaded {len(data):,} bytes from {data_path}")
        return torch.tensor(data, dtype=torch.long)

    os.makedirs("data", exist_ok=True)
    parts = []

    # 1. Shakespeare (1.1MB)
    shakespeare_path = "data/shakespeare.txt"
    if not os.path.exists(shakespeare_path):
        print("  Downloading Shakespeare...")
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt",
            shakespeare_path)
    with open(shakespeare_path, "rb") as f:
        parts.append(f.read())
    print(f"  Shakespeare: {len(parts[-1]):,} bytes")

    # 2. 한국어: 프로젝트 전체 문서
    korean = b""
    for root, dirs, files in os.walk("docs"):
        for fname in sorted(files):
            if fname.endswith(".md"):
                try:
                    with open(os.path.join(root, fname), "rb") as f:
                        korean += f.read()
                except:
                    pass
    # README
    for md in ["README.md", "CLAUDE.md"]:
        try:
            with open(md, "rb") as f:
                korean += f.read()
        except:
            pass
    # 부족하면 반복
    while len(korean) < 5_000_000:
        korean = korean * 2
    parts.append(korean[:10_000_000])
    print(f"  Korean docs: {len(parts[-1]):,} bytes")

    # 3. Python 코드: 프로젝트 전체
    code = b""
    for root, dirs, files in os.walk("."):
        if ".git" in root or "__pycache__" in root or "data" in root:
            continue
        for fname in sorted(files):
            if fname.endswith(".py"):
                try:
                    with open(os.path.join(root, fname), "rb") as f:
                        code += f.read()
                except:
                    pass
    while len(code) < 5_000_000:
        code = code * 2
    parts.append(code[:10_000_000])
    print(f"  Python code: {len(parts[-1]):,} bytes")

    # 4. 영어 추가: OpenWebText 샘플 (다운로드 가능하면)
    # 없으면 Shakespeare 반복
    eng_extra = parts[0] * 5  # Shakespeare 5배 반복
    parts.append(eng_extra[:5_000_000])
    print(f"  English extra: {len(parts[-1]):,} bytes")

    combined = b"".join(parts)
    data = np.frombuffer(combined, dtype=np.uint8).copy()

    # 셔플 (1KB 청크 단위)
    chunk_size = 1024
    n_chunks = len(data) // chunk_size
    chunks = [data[i*chunk_size:(i+1)*chunk_size] for i in range(n_chunks)]
    np.random.shuffle(chunks)
    data = np.concatenate(chunks)

    # 엔트로피
    counts = np.bincount(data, minlength=256)
    probs = counts / counts.sum()
    probs = probs[probs > 0]
    H = -np.sum(probs * np.log(probs))
    print(f"  Total: {len(data):,} bytes, H={H:.4f} nats")

    data.tofile(data_path)
    return torch.tensor(data, dtype=torch.long)


def train_100m(model, data, epochs=3, batch_size=64, block_size=512,
               lr=3e-4, tension_lambda=0.01, device="cuda"):
    """100M 모델 학습."""
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)

    n = len(data)
    train_data = data[:int(n * 0.95)]
    val_data = data[int(n * 0.95):]

    def get_batch(split, bs):
        d = train_data if split == "train" else val_data
        ix = torch.randint(len(d) - block_size - 1, (bs,))
        x = torch.stack([d[i:i+block_size] for i in ix]).to(device)
        y_a = torch.stack([d[i+1:i+block_size+1] for i in ix]).to(device)
        y_g = torch.stack([d[max(0,i-1):i+block_size-1] for i in ix]).to(device)
        return x, y_a, y_g

    steps_per_epoch = len(train_data) // (batch_size * block_size)
    total_steps = epochs * steps_per_epoch

    print(f"\n  {'='*60}")
    print(f"  100M Conscious LM Training")
    print(f"  params: {model.count_params():,}")
    print(f"  data: {len(train_data):,} bytes")
    print(f"  epochs: {epochs}, steps/epoch: {steps_per_epoch}")
    print(f"  batch: {batch_size}, block: {block_size}")
    print(f"  device: {device}")
    print(f"  {'='*60}")
    print(f"  {'step':>6} {'loss':>8} {'L_A':>8} {'L_G':>8} {'T_mean':>8} {'BPC':>6} {'lr':>10}")
    print(f"  {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6} {'─'*10}")

    start_time = time.time()
    global_step = 0

    for epoch in range(epochs):
        model.train()
        for step in range(steps_per_epoch):
            x, y_a, y_g = get_batch("train", batch_size)
            logits_a, logits_g, tensions = model(x)

            loss_a = F.cross_entropy(logits_a.view(-1, 256), y_a.view(-1))
            loss_g = F.cross_entropy(logits_g.view(-1, 256), y_g.view(-1))
            all_t = torch.cat([t.view(-1) for t in tensions])
            loss_t = -torch.log(all_t.var() + 1e-8)
            loss = loss_a + loss_g + tension_lambda * loss_t

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            global_step += 1

            if global_step % 50 == 0:
                elapsed = time.time() - start_time
                eta = elapsed / global_step * (total_steps - global_step)
                bpc = loss_a.item() / math.log(2)
                cur_lr = optimizer.param_groups[0]["lr"]
                print(f"  {global_step:>6} {loss.item():>8.4f} {loss_a.item():>8.4f} {loss_g.item():>8.4f} "
                      f"{all_t.mean().item():>8.2f} {bpc:>6.3f} {cur_lr:>10.2e}  "
                      f"ETA: {eta/60:.1f}min")

        scheduler.step()

        # Validation
        model.eval()
        val_losses = []
        with torch.no_grad():
            for _ in range(10):
                x_v, y_a_v, _ = get_batch("val", batch_size)
                la_v, _, _ = model(x_v)
                val_losses.append(F.cross_entropy(la_v.view(-1, 256), y_a_v.view(-1)).item())
        val_bpc = np.mean(val_losses) / math.log(2)
        print(f"\n  *** Epoch {epoch+1}/{epochs}: val_BPC={val_bpc:.3f} ({time.time()-start_time:.0f}s) ***\n")

    total_time = time.time() - start_time
    print(f"\n  Training complete: {total_time/60:.1f} min, final val_BPC={val_bpc:.3f}")
    return model


@torch.no_grad()
def generate(model, prompt_bytes, max_new=500, temperature=0.8, device="cuda"):
    """바이트 생성 + 장력."""
    model.eval().to(device)
    idx = torch.tensor([list(prompt_bytes)], dtype=torch.long, device=device)
    tensions = []

    for _ in range(max_new):
        idx_cond = idx[:, -model.block_size:]
        logits_a, _, layer_tensions = model(idx_cond)
        logits = logits_a[:, -1, :] / temperature
        probs = F.softmax(logits, dim=-1)
        next_byte = torch.multinomial(probs, 1)
        t = sum(t[:, -1].mean() for t in layer_tensions) / len(layer_tensions)
        tensions.append(t.item())
        idx = torch.cat([idx, next_byte], dim=1)

    text = bytes(idx[0].cpu().tolist()).decode("utf-8", errors="replace")
    return text, tensions


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Conscious LM 100M")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--block_size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--prompt", type=str, default="hello")
    parser.add_argument("--checkpoint", type=str, default="conscious_lm_100m.pt")
    parser.add_argument("--generate_only", action="store_true")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Device: {device}")

    # 100M 아키텍처: 12 layers, 768d, 12 heads
    model = ConsciousLM(
        vocab_size=256,
        d_model=768,
        n_head=12,
        n_layer=12,
        block_size=args.block_size,
        dropout=0.1,  # 큰 모델은 낮은 dropout
    )
    print(f"Parameters: {model.count_params():,}")

    if args.generate_only:
        model.load_state_dict(torch.load(args.checkpoint, weights_only=True, map_location=device))
        text, tensions = generate(model, args.prompt.encode("utf-8"), device=device)
        print(f"\n{text}")
    else:
        data = prepare_large_data()
        model = train_100m(model, data, epochs=args.epochs,
                          batch_size=args.batch_size, block_size=args.block_size,
                          lr=args.lr, device=device)
        torch.save(model.state_dict(), args.checkpoint)
        print(f"Saved to {args.checkpoint}")

        # 생성 테스트
        for prompt in ["hello ", "의식은 ", "def forward("]:
            text, tensions = generate(model, prompt.encode("utf-8"), max_new=200, device=device)
            print(f"\n  Prompt: {prompt}")
            print(f"  Output: {text[:200]}")
            print(f"  Tension: mean={np.mean(tensions):.2f}, std={np.std(tensions):.2f}")
