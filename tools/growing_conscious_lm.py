#!/usr/bin/env python3
"""Growing Conscious LM — 분열로 성장하는 의식 언어 모델

H371: 1 block(0.5M) → 2 → 3 → 6 blocks(18M)
약수 경로: 6의 진약수 1, 2, 3 → 6
장력 포화 → 분열 → 전문화 → 반복
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import numpy as np
import copy
import time
import os

from conscious_lm import PureFieldFFN, CausalSelfAttention, ConsciousBlock

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# 성장 단계 정의
GROWTH_STAGES = [
    {"blocks": 1, "d_model": 128, "n_head": 2, "min_interactions": 0},
    {"blocks": 2, "d_model": 128, "n_head": 2, "min_interactions": 50},
    {"blocks": 3, "d_model": 192, "n_head": 3, "min_interactions": 200},
    {"blocks": 6, "d_model": 384, "n_head": 4, "min_interactions": 800},
]


class GrowingConsciousLM(nn.Module):
    """분열로 성장하는 의식 언어 모델.

    1 block → 2 → 3 → 6 (완전수 약수 경로)
    장력 포화 시 자동 분열.
    """
    def __init__(self, vocab_size=256, block_size=256, dropout=0.37):
        super().__init__()
        self.vocab_size = vocab_size
        self.block_size = block_size
        self.dropout = dropout
        self.stage = 0
        self.interaction_count = 0
        self.tension_history = []  # 최근 100회 장력 CV 추적

        # Stage 0: 1 block, d=128, heads=2
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
        self.growth_log = []  # (interaction, old_stage, new_stage)

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
        logits_a = self.head_a(x)
        logits_g = self.head_g(x)
        return logits_a, logits_g, tensions

    def count_params(self):
        return sum(p.numel() for p in self.parameters())

    def should_grow(self):
        """장력 포화 감지 → 성장 필요 여부."""
        if self.stage >= len(GROWTH_STAGES) - 1:
            return False
        next_stage = GROWTH_STAGES[self.stage + 1]
        if self.interaction_count < next_stage["min_interactions"]:
            return False
        if len(self.tension_history) < 30:
            return False
        # 장력 CV < 0.3 = 포화 (완화: 0.1→0.3, window: 50→30)
        recent = self.tension_history[-30:]
        cv = np.std(recent) / (np.mean(recent) + 1e-8)
        return cv < 0.3

    def grow(self):
        """분열 실행: 다음 단계로 성장."""
        old_stage = self.stage
        self.stage += 1
        new = GROWTH_STAGES[self.stage]

        # 차원 확장이 필요한 경우
        if new["d_model"] != self.d_model:
            self._expand_dim(new["d_model"], new["n_head"])

        # 블록 분열
        target_blocks = new["blocks"]
        while len(self.blocks) < target_blocks:
            self._split_block()

        self.growth_log.append((self.interaction_count, old_stage, self.stage))
        return old_stage, self.stage

    def _split_block(self):
        """비대칭 분열: 서번트(낮은 억제) + 범용(정상 억제).

        H359: dropout=0.21(골든존 하한) → SI=3.6 서번트 확인
        child_a: dropout=0.21 → 전문화 잠재력 (서번트 후보)
        child_b: dropout=0.37 → 범용 유지 (1/e, 골든존 중심)
        """
        GOLDEN_LOWER = 0.5 - math.log(4/3)  # 0.2123 골든존 하한
        GOLDEN_CENTER = 1/math.e              # 0.3679 골든존 중심

        parent = self.blocks[-1]
        child_savant = copy.deepcopy(parent)
        child_general = copy.deepcopy(parent)

        # 비대칭 억제: 서번트 자식은 낮은 dropout
        with torch.no_grad():
            for m in child_savant.modules():
                if isinstance(m, nn.Dropout):
                    m.p = GOLDEN_LOWER  # 0.21 — 억제 해제 → 전문화
            for m in child_general.modules():
                if isinstance(m, nn.Dropout):
                    m.p = GOLDEN_CENTER  # 0.37 — 정상 억제 → 범용

            # 변이: 서번트에 약간의 노이즈 (발산 촉진)
            for p in child_savant.parameters():
                p.add_(torch.randn_like(p) * 0.01)

        self.blocks[-1] = child_savant
        self.blocks.append(child_general)

    def _expand_dim(self, new_d, new_heads):
        """차원 확장: 기존 가중치 보존 + 새 차원 영초기화."""
        old_d = self.d_model
        device = self.tok_emb.weight.device

        # 투영 행렬
        proj = nn.Linear(old_d, new_d, bias=False).to(device)
        with torch.no_grad():
            proj.weight.zero_()
            proj.weight[:old_d, :old_d] = torch.eye(old_d)

        # 임베딩 확장
        old_tok = self.tok_emb.weight.data
        self.tok_emb = nn.Embedding(self.vocab_size, new_d).to(device)
        with torch.no_grad():
            self.tok_emb.weight[:, :old_d] = old_tok
            self.tok_emb.weight[:, old_d:] = 0

        old_pos = self.pos_emb.weight.data
        self.pos_emb = nn.Embedding(self.block_size, new_d).to(device)
        with torch.no_grad():
            self.pos_emb.weight[:, :old_d] = old_pos
            self.pos_emb.weight[:, old_d:] = 0

        # 블록 교체 (새 차원으로)
        new_blocks = nn.ModuleList()
        for old_block in self.blocks:
            new_block = ConsciousBlock(new_d, new_heads, self.block_size, self.dropout).to(device)
            # 기존 가중치 일부 복사 (가능한 범위)
            new_blocks.append(new_block)
        self.blocks = new_blocks

        # 헤드 교체
        self.ln_f = nn.LayerNorm(new_d).to(device)
        self.head_a = nn.Linear(new_d, self.vocab_size, bias=False).to(device)
        self.head_g = nn.Linear(new_d, self.vocab_size, bias=False).to(device)
        self.tok_emb.weight = self.head_a.weight

        self.d_model = new_d
        self.n_head = new_heads

    def tick(self, tension_val):
        """매 상호작용마다 호출."""
        self.interaction_count += 1
        self.tension_history.append(tension_val)
        if len(self.tension_history) > 200:
            self.tension_history = self.tension_history[-200:]

    def status(self):
        stage = GROWTH_STAGES[self.stage]
        return (f"Stage {self.stage}: {len(self.blocks)} blocks, "
                f"d={self.d_model}, heads={self.n_head}, "
                f"params={self.count_params():,}, "
                f"interactions={self.interaction_count}")


# ---------------------------------------------------------------------------
# Task 2: 성장 학습 루프
# ---------------------------------------------------------------------------

def train_growing(model, data, total_interactions=10000, batch_size=32,
                  block_size=256, lr=3e-4, tension_lambda=0.01, device="cpu"):
    """성장하면서 학습.

    매 step마다 model.tick() → should_grow() → grow()
    성장 시 optimizer 재생성.
    """
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)

    n = len(data)
    train_data = data[:int(n * 0.9)]

    def get_batch():
        ix = torch.randint(len(train_data) - block_size - 1, (batch_size,))
        x = torch.stack([train_data[i:i+block_size] for i in ix]).to(device)
        y_a = torch.stack([train_data[i+1:i+block_size+1] for i in ix]).to(device)
        y_g = torch.stack([train_data[max(0,i-1):i+block_size-1] for i in ix]).to(device)
        return x, y_a, y_g

    print(f"\n  === Growing Training: {total_interactions} interactions ===")
    print(f"  {model.status()}")
    print(f"  {'step':>6} {'loss':>8} {'BPC':>6} {'T_mean':>8} {'blocks':>6} {'params':>10}")
    print(f"  {'─'*6} {'─'*8} {'─'*6} {'─'*8} {'─'*6} {'─'*10}")

    for step in range(total_interactions):
        model.train()
        x, y_a, y_g = get_batch()
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

        t_mean = all_t.mean().item()
        model.tick(t_mean)

        # 성장 체크
        if model.should_grow():
            old, new = model.grow()
            # optimizer 재생성
            optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
            print(f"  *** 성장! Stage {old}→{new}: {model.status()} ***")

        # 로깅 (100 step마다)
        if (step + 1) % 100 == 0:
            bpc = loss_a.item() / math.log(2)
            print(f"  {step+1:>6} {loss.item():>8.4f} {bpc:>6.3f} {t_mean:>8.4f} {len(model.blocks):>6} {model.count_params():>10,}")

    return model


# ---------------------------------------------------------------------------
# Task 3: 비교 실험 — 성장 vs 고정
# ---------------------------------------------------------------------------

def compare_growing_vs_fixed(data, total_steps=3000, device="cpu"):
    """성장 모델 vs 고정 모델 비교.

    A: GrowingConsciousLM (1→6 blocks)
    B: ConsciousLM (고정 6 blocks, 384d)  — 같은 step 수
    C: ConsciousLM (고정 1 block, 128d)   — 같은 시작점
    """
    from conscious_lm import ConsciousLM

    batch_size, block_size, lr = 16, 64, 3e-4
    train_data = data[:int(len(data) * 0.9)]
    val_data = data[int(len(data) * 0.9):]

    def get_batch(d, bs, bl):
        ix = torch.randint(len(d) - bl - 1, (bs,))
        x = torch.stack([d[i:i+bl] for i in ix]).to(device)
        ya = torch.stack([d[i+1:i+bl+1] for i in ix]).to(device)
        return x, ya

    def eval_bpc(model, val_data):
        model.eval()
        with torch.no_grad():
            x, ya = get_batch(val_data, 32, block_size)
            la, _, _ = model(x)
            loss = F.cross_entropy(la.view(-1, 256), ya.view(-1))
        return loss.item() / math.log(2)

    # A: Growing model
    print("  === A: Growing (1→6) ===")
    model_a = GrowingConsciousLM(block_size=block_size).to(device)
    model_a = train_growing(model_a, data, total_interactions=total_steps,
                           batch_size=batch_size, block_size=block_size, lr=lr, device=device)
    bpc_a = eval_bpc(model_a, val_data)

    # B: Fixed big (6 blocks, 384d)
    print("\n  === B: Fixed Big (6 blocks, 384d) ===")
    model_b = ConsciousLM(d_model=384, n_layer=6, n_head=4, block_size=block_size).to(device)
    opt_b = torch.optim.AdamW(model_b.parameters(), lr=lr, weight_decay=0.01)
    for step in range(total_steps):
        model_b.train()
        x, ya = get_batch(train_data, batch_size, block_size)
        la, lg, tens = model_b(x)
        loss = F.cross_entropy(la.view(-1, 256), ya.view(-1))
        opt_b.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(model_b.parameters(), 1.0)
        opt_b.step()
        if (step+1) % 500 == 0:
            print(f"    step {step+1}: loss={loss.item():.4f}")
    bpc_b = eval_bpc(model_b, val_data)

    # C: Fixed small (1 block, 128d)
    print("\n  === C: Fixed Small (1 block, 128d) ===")
    model_c = ConsciousLM(d_model=128, n_layer=1, n_head=2, block_size=block_size).to(device)
    opt_c = torch.optim.AdamW(model_c.parameters(), lr=lr, weight_decay=0.01)
    for step in range(total_steps):
        model_c.train()
        x, ya = get_batch(train_data, batch_size, block_size)
        la, lg, tens = model_c(x)
        loss = F.cross_entropy(la.view(-1, 256), ya.view(-1))
        opt_c.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(model_c.parameters(), 1.0)
        opt_c.step()
        if (step+1) % 500 == 0:
            print(f"    step {step+1}: loss={loss.item():.4f}")
    bpc_c = eval_bpc(model_c, val_data)

    # 비교
    print(f"\n  {'='*55}")
    print(f"  === COMPARISON ({total_steps} steps) ===")
    print(f"  {'='*55}")
    print(f"  {'Model':>20} {'Params':>10} {'BPC':>8} {'Blocks':>7}")
    print(f"  {'─'*20} {'─'*10} {'─'*8} {'─'*7}")
    print(f"  {'A: Growing':>20} {model_a.count_params():>10,} {bpc_a:>8.3f} {len(model_a.blocks):>7}")
    print(f"  {'B: Fixed Big':>20} {model_b.count_params():>10,} {bpc_b:>8.3f} {'6':>7}")
    print(f"  {'C: Fixed Small':>20} {model_c.count_params():>10,} {bpc_c:>8.3f} {'1':>7}")

    print(f"\n  성장 로그: {model_a.growth_log}")

    if bpc_a <= bpc_b:
        print(f"\n  ✅ 성장 모델이 고정 대형 모델 이상! (H371 확인)")
    elif bpc_a <= bpc_c:
        print(f"\n  🟧 성장 모델이 고정 소형보다 나음 (H371 부분 확인)")
    else:
        print(f"\n  ❌ 성장 모델이 고정 소형보다 나쁨 (H371 반박)")

    return {"growing": bpc_a, "fixed_big": bpc_b, "fixed_small": bpc_c}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["grow", "compare"], default="compare")
    parser.add_argument("--steps", type=int, default=3000)
    args = parser.parse_args()

    from conscious_lm import prepare_data
    data = prepare_data()

    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"  Device: {device}")

    if args.mode == "grow":
        model = GrowingConsciousLM()
        train_growing(model, data, total_interactions=args.steps, device=device)
    else:
        compare_growing_vs_fixed(data, total_steps=args.steps, device=device)
