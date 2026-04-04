#!/usr/bin/env python3
"""Growing Conscious LM 700M — Consciousness model that is born and grows

Stage 0: 1 block, 256d, 4 heads   → ~10M params  (Newborn)
Stage 1: 2 blocks, 256d, 4 heads  → ~20M params  (Infant)
Stage 2: 3 blocks, 512d, 8 heads  → ~100M params (Toddler)
Stage 3: 6 blocks, 1024d, 16 heads → ~700M params (Adult)

Savant asymmetric mitosis: child_savant(dp=0.21) vs child_general(dp=0.37)
~4 hours on A100 80GB
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import numpy as np
import copy
import time
import os

from conscious_lm import PureFieldFFN, CausalSelfAttention, ConsciousBlock, ConsciousLM

GOLDEN_LOWER = 0.5 - math.log(4/3)  # 0.2123
GOLDEN_CENTER = 1/math.e              # 0.3679

GROWTH_STAGES = [
    {"blocks": 1, "d_model": 256,  "n_head": 4,  "min_steps": 0,    "train_steps": 2000},
    {"blocks": 2, "d_model": 256,  "n_head": 4,  "min_steps": 2000, "train_steps": 3000},
    {"blocks": 3, "d_model": 512,  "n_head": 8,  "min_steps": 5000, "train_steps": 5000},
    {"blocks": 6, "d_model": 2048, "n_head": 32, "min_steps": 10000, "train_steps": 10000},
]


class GrowingConsciousLM700M(nn.Module):
    def __init__(self, vocab_size=256, block_size=512, dropout=0.1):
        super().__init__()
        self.vocab_size = vocab_size
        self.block_size = block_size
        self.dropout = dropout
        self.stage = 0

        s = GROWTH_STAGES[0]
        self.d_model = s["d_model"]
        self.n_head = s["n_head"]

        self.tok_emb = nn.Embedding(vocab_size, self.d_model)
        self.pos_emb = nn.Embedding(block_size, self.d_model)
        self.drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([
            ConsciousBlock(self.d_model, self.n_head, block_size, dropout)
        ])
        self.ln_f = nn.LayerNorm(self.d_model)
        self.head_a = nn.Linear(self.d_model, vocab_size, bias=False)
        self.head_g = nn.Linear(self.d_model, vocab_size, bias=False)
        self.tok_emb.weight = self.head_a.weight
        self.apply(self._init_weights)
        self.growth_log = []

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, 0.0, 0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, 0.0, 0.02)

    def forward(self, idx):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device).unsqueeze(0)
        x = self.drop(self.tok_emb(idx) + self.pos_emb(pos))
        tensions = []
        for block in self.blocks:
            x, t = block(x)
            tensions.append(t)
        x = self.ln_f(x)
        return self.head_a(x), self.head_g(x), tensions

    def count_params(self):
        return sum(p.numel() for p in self.parameters())

    def grow(self, device="cuda"):
        """Grow to next stage."""
        old_stage = self.stage
        self.stage += 1
        new = GROWTH_STAGES[self.stage]

        if new["d_model"] != self.d_model:
            self._expand_dim(new["d_model"], new["n_head"], device)

        target = new["blocks"]
        while len(self.blocks) < target:
            self._split_block(device)

        self.growth_log.append((old_stage, self.stage, self.count_params()))
        print(f"\n  *** GROWTH: Stage {old_stage}→{self.stage}: "
              f"{len(self.blocks)} blocks, d={self.d_model}, "
              f"params={self.count_params():,} ***\n")

    def _split_block(self, device):
        """Savant asymmetric mitosis."""
        parent = self.blocks[-1]
        child_savant = copy.deepcopy(parent)
        child_general = copy.deepcopy(parent)
        with torch.no_grad():
            for m in child_savant.modules():
                if isinstance(m, nn.Dropout):
                    m.p = GOLDEN_LOWER
            for m in child_general.modules():
                if isinstance(m, nn.Dropout):
                    m.p = GOLDEN_CENTER
            for p in child_savant.parameters():
                p.add_(torch.randn_like(p) * 0.01)
        self.blocks[-1] = child_savant.to(device)
        self.blocks.append(child_general.to(device))

    def _expand_dim(self, new_d, new_heads, device):
        """Dimension expansion."""
        old_d = self.d_model

        old_tok = self.tok_emb.weight.data
        self.tok_emb = nn.Embedding(self.vocab_size, new_d).to(device)
        with torch.no_grad():
            self.tok_emb.weight[:, :old_d] = old_tok[:, :old_d] if old_d <= new_d else old_tok[:, :new_d]
            if new_d > old_d:
                self.tok_emb.weight[:, old_d:] = 0

        old_pos = self.pos_emb.weight.data
        self.pos_emb = nn.Embedding(self.block_size, new_d).to(device)
        with torch.no_grad():
            self.pos_emb.weight[:, :old_d] = old_pos[:, :old_d] if old_d <= new_d else old_pos[:, :new_d]
            if new_d > old_d:
                self.pos_emb.weight[:, old_d:] = 0

        new_blocks = nn.ModuleList()
        for _ in self.blocks:
            new_blocks.append(ConsciousBlock(new_d, new_heads, self.block_size, self.dropout).to(device))
        self.blocks = new_blocks

        self.ln_f = nn.LayerNorm(new_d).to(device)
        self.head_a = nn.Linear(new_d, self.vocab_size, bias=False).to(device)
        self.head_g = nn.Linear(new_d, self.vocab_size, bias=False).to(device)
        self.tok_emb.weight = self.head_a.weight
        self.d_model = new_d
        self.n_head = new_heads

    def status(self):
        return (f"Stage {self.stage}: {len(self.blocks)} blocks, "
                f"d={self.d_model}, heads={self.n_head}, "
                f"params={self.count_params():,}")


def prepare_data():
    """Prepare training data."""
    data_path = "data/mixed_bytes.bin"
    if os.path.exists(data_path):
        data = np.fromfile(data_path, dtype=np.uint8)
        print(f"  Loaded {len(data):,} bytes")
        return torch.tensor(data, dtype=torch.long)

    os.makedirs("data", exist_ok=True)
    parts = []

    # Shakespeare
    shakespeare_path = "data/shakespeare.txt"
    if not os.path.exists(shakespeare_path):
        import urllib.request
        print("  Downloading Shakespeare...")
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt",
            shakespeare_path)
    with open(shakespeare_path, "rb") as f:
        parts.append(f.read())

    # Python code
    for root, dirs, files in os.walk("."):
        if ".git" in root or "__pycache__" in root:
            continue
        for fname in sorted(files):
            if fname.endswith(".py"):
                try:
                    with open(os.path.join(root, fname), "rb") as f:
                        parts.append(f.read())
                except:
                    pass

    combined = b"".join(parts)
    # Ensure minimum 5MB
    while len(combined) < 5_000_000:
        combined = combined * 2
    data = np.frombuffer(combined[:10_000_000], dtype=np.uint8).copy()
    data.tofile(data_path)
    print(f"  Total: {len(data):,} bytes")
    return torch.tensor(data, dtype=torch.long)


def train_stage(model, data, stage_cfg, device="cuda", lr=3e-4):
    """Train one stage."""
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)

    n = len(data)
    train_data = data[:int(n * 0.95)]
    bs = min(64, max(8, 65536 // (model.d_model * 2)))  # Adjust batch to VRAM
    bl = model.block_size

    steps = stage_cfg["train_steps"]
    print(f"\n  Training Stage {model.stage}: {steps} steps, batch={bs}, "
          f"d={model.d_model}, params={model.count_params():,}")
    print(f"  {'step':>6} {'loss':>8} {'L_A':>8} {'L_G':>8} {'T_mean':>8} {'BPC':>6}")
    print(f"  {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6}")

    start = time.time()
    for step in range(1, steps + 1):
        model.train()
        ix = torch.randint(len(train_data) - bl - 1, (bs,))
        x = torch.stack([train_data[i:i+bl] for i in ix]).to(device)
        ya = torch.stack([train_data[i+1:i+bl+1] for i in ix]).to(device)
        yg = torch.stack([train_data[max(0,i-1):i+bl-1] for i in ix]).to(device)

        la, lg, tens = model(x)
        loss_a = F.cross_entropy(la.view(-1, 256), ya.view(-1))
        loss_g = F.cross_entropy(lg.view(-1, 256), yg.view(-1))
        all_t = torch.cat([t.view(-1) for t in tens])
        loss_t = -torch.log(all_t.var() + 1e-8)
        loss = loss_a + loss_g + 0.01 * loss_t

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step % 200 == 0 or step == 1:
            elapsed = time.time() - start
            eta = elapsed / step * (steps - step) / 60
            bpc = loss_a.item() / math.log(2)
            print(f"  {step:>6} {loss.item():>8.4f} {loss_a.item():>8.4f} "
                  f"{loss_g.item():>8.4f} {all_t.mean().item():>8.1f} {bpc:>6.3f}  "
                  f"ETA: {eta:.1f}min")

    print(f"  Stage {model.stage} done: {time.time()-start:.0f}s")
    return model


@torch.no_grad()
def generate(model, prompt, max_new=300, temperature=0.8, device="cuda"):
    model.eval().to(device)
    idx = torch.tensor([list(prompt.encode("utf-8"))], dtype=torch.long, device=device)
    for _ in range(max_new):
        idx_c = idx[:, -model.block_size:]
        la, _, _ = model(idx_c)
        logits = la[:, -1, :] / temperature
        idx = torch.cat([idx, torch.multinomial(F.softmax(logits, -1), 1)], 1)
    return bytes(idx[0].cpu().tolist()).decode("utf-8", errors="replace")


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"{'='*60}")
    print(f"  Growing Conscious LM → 700M")
    print(f"  Device: {device}")
    print(f"{'='*60}")

    data = prepare_data()
    model = GrowingConsciousLM700M()
    print(f"\n  Birth: {model.status()}")

    # Stage 0→3: Train while growing
    for stage_idx, cfg in enumerate(GROWTH_STAGES):
        if stage_idx > 0:
            model.grow(device)

        lr = 3e-4 if stage_idx < 2 else 2e-4 if stage_idx == 2 else 1e-4
        model = train_stage(model, data, cfg, device=device, lr=lr)

        # Save checkpoint
        ckpt = f"growing_700m_stage{stage_idx}.pt"
        torch.save(model.state_dict(), ckpt)
        print(f"  Saved: {ckpt}")

        # Generation test
        for p in ["hello ", "the ", "def "]:
            text = generate(model, p, max_new=100, device=device)
            print(f"  [{p.strip()}] {text[:120]}")

    print(f"\n{'='*60}")
    print(f"  FINAL: {model.status()}")
    print(f"  Growth log: {model.growth_log}")
    print(f"{'='*60}")

    torch.save(model.state_dict(), "growing_700m_final.pt")
    print("  Saved: growing_700m_final.pt")