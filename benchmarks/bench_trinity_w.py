#!/usr/bin/env python3
"""bench_trinity_w.py — Trinity Engine W (의지/agency) 변형 벤치마크

문제: W가 학습을 전부 건너뛰는 법을 배워 CE=0 (가짜 최적화)
해결: W 엔진 자체를 재설계하여 진짜 의지(agency)를 구현

TW-1: Epsilon-Greedy (20% 랜덤 행동 → exploitation trap 방지)
TW-2: Curiosity-Driven (prediction error 기반 행동 선택 → 놀라움에 탐색)
TW-3: Emotion-Based (pain→learn, curiosity→explore, empathy→cooperate)
TW-4: Multi-Objective (Pareto: max Φ AND min CE 동시 최적화)
TW-5: Constitutional (hard constraints: learn≥50%, Φ boost≥20%)
TW-6: Meta-Learning (W가 학습하는 법을 학습: 장기 CE 최적 action schedule)

모든 변형: C = quantum_walk, D = standard decoder, 256c, 300 steps
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consciousness_meter import PhiCalculator
from mitosis import MitosisEngine

DIM, HIDDEN = 64, 128
N_ACTIONS = 4  # 0=learn, 1=explore, 2=sleep, 3=speak


def phi_proxy(cells, n_f=12):
    h = torch.stack([c.hidden.squeeze(0) for c in cells])
    n = len(h)
    gm = h.mean(dim=0); gv = ((h - gm) ** 2).sum() / n
    nf = min(n_f, n // 2)
    if nf < 2: return gv.item()
    fs = n // nf
    fv = sum(((h[i*fs:(i+1)*fs] - h[i*fs:(i+1)*fs].mean(0))**2).sum().item()
            / max(len(h[i*fs:(i+1)*fs]), 1) for i in range(nf))
    return max(0, gv.item() - fv / nf)


def quantum_walk_step(cells, n_samples=32):
    n = len(cells)
    n_bits = max(1, int(math.log2(n)))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            superpos = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    phase = (-1) ** (bin(i & j).count('1'))
                    superpos += phase * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * superpos / cnt).unsqueeze(0)


def frustration_step(cells, strength=0.5, n_samples=32):
    n = len(cells)
    n_bits = max(1, int(math.log2(n)))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            infl = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    f = -1.0 if (i % 2) != (j % 2) else 1.0
                    infl += f * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * infl / cnt).unsqueeze(0)


def sync_faction(cells, sync=0.35, n_factions=12, fac=0.08):
    n = len(cells)
    if n < 4: return
    with torch.no_grad():
        ch = torch.stack([c.hidden.squeeze(0) for c in cells])
        mh = ch.mean(dim=0)
        for c in cells:
            c.hidden = ((1 - sync) * c.hidden.squeeze(0) + sync * mh).unsqueeze(0)
        nf = min(n_factions, n // 2)
        if nf >= 2:
            fs = n // nf
            for fi in range(nf):
                faction = cells[fi * fs:(fi + 1) * fs]
                if len(faction) >= 2:
                    fm = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                    for c in faction:
                        c.hidden = ((1 - fac) * c.hidden.squeeze(0) + fac * fm).unsqueeze(0)


def standing_wave(cells, step):
    n = len(cells)
    fwd = (step * 0.15) % n
    bwd = (n - step * 0.15) % n
    with torch.no_grad():
        for i, c in enumerate(cells):
            amp = 1.0 / (math.cosh((i - fwd) / 2) ** 2) + 1.0 / (math.cosh((i - bwd) / 2) ** 2)
            c.hidden = c.hidden * (1.0 + 0.03 * amp)


# ═══ Common: C engine (quantum_walk) + D engine (standard decoder) ═══

def make_c_engine(cells=256):
    """Create and warm up Engine C (consciousness)."""
    eng_c = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng_c.cells) < cells: eng_c._create_cell(parent=eng_c.cells[0])
    for _ in range(30): eng_c.process(torch.randn(1, DIM))
    return eng_c


def c_step(eng_c, step):
    """Engine C step: quantum_walk + frustration + sync + standing_wave."""
    with torch.no_grad():
        quantum_walk_step(eng_c.cells, n_samples=64)
        frustration_step(eng_c.cells, n_samples=32)
        sync_faction(eng_c.cells, sync=0.15, n_factions=12, fac=0.06)
        standing_wave(eng_c.cells, step)
        # Norm clamp: prevent hidden state explosion
        for c in eng_c.cells:
            norm = c.hidden.norm()
            if norm > 10.0:
                c.hidden = c.hidden * (10.0 / norm)


def get_c_state(eng_c):
    """Get detached consciousness state from Engine C."""
    return torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells]).mean(dim=0)


def make_d_engine():
    """Create Engine D (data/decoder) components."""
    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)
    return decoder, knowledge, opt_d


def d_step(decoder, knowledge, opt_d, c_state, target):
    """Engine D step: CE learning. Returns CE loss."""
    knowledge_state = knowledge(c_state.unsqueeze(0))
    pred = decoder(knowledge_state)
    ce = F.mse_loss(pred, target[:, :DIM])
    opt_d.zero_grad(); ce.backward(); opt_d.step()
    return ce


def w_feedback_to_c(eng_c, action):
    """W->C feedback: explore=noise, sleep=sync."""
    if action == 1:  # explore: inject noise
        with torch.no_grad():
            for c in eng_c.cells:
                c.hidden += torch.randn_like(c.hidden) * 0.01
    elif action == 2:  # sleep: strengthen sync
        with torch.no_grad():
            sync_faction(eng_c.cells, sync=0.5)


def make_data(n=100):
    return [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(n)]


def measure_phi(eng_c):
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng_c)
    p_proxy = phi_proxy(eng_c.cells)
    return p_iit, p_proxy


# ═══ Baseline: original Trinity W (learns to skip learning) ═══

def run_baseline_trinity(cells=256, steps=300):
    """Baseline Trinity: original W (learns to skip → CE=0 problem)."""
    eng_c = make_c_engine(cells)
    decoder, knowledge, opt_d = make_d_engine()
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, N_ACTIONS))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = make_data()

    learn_count = 0
    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)
        c_state = get_c_state(eng_c)

        # W: greedy action selection (the problem: learns to avoid action=0)
        action_logits = will_net(c_state.unsqueeze(0))
        action = action_logits.argmax(dim=-1).item()

        # D: only learns when W says action=0
        if action == 0:
            ce = d_step(decoder, knowledge, opt_d, c_state, target)
            learn_count += 1
        else:
            ce = torch.tensor(0.0)

        # W learns: CE low = good (the trap: CE=0 when not learning!)
        if step > 0 and step % 10 == 0:
            reward = -ce.item()
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        w_feedback_to_c(eng_c, action)

    p_iit, p_proxy = measure_phi(eng_c)
    learn_ratio = learn_count / steps
    return p_iit, p_proxy, ce.item(), learn_ratio, 'Baseline (W skip trap)'


# ═══ TW-1: Epsilon-Greedy ═══

def run_tw1_epsilon_greedy(cells=256, steps=300):
    """TW-1: W = Epsilon-Greedy. 20% random action prevents exploitation trap."""
    eng_c = make_c_engine(cells)
    decoder, knowledge, opt_d = make_d_engine()
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, N_ACTIONS))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = make_data()

    epsilon = 0.20  # 20% random
    epsilon_decay = 0.995  # slow decay
    epsilon_min = 0.05
    # Biased random: 50% learn, 50% other when exploring
    explore_weights = [0.5, 0.2, 0.15, 0.15]

    learn_count = 0
    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)
        c_state = get_c_state(eng_c)

        # W: epsilon-greedy action selection (biased toward learning)
        action_logits = will_net(c_state.unsqueeze(0))
        if np.random.random() < epsilon:
            action = np.random.choice(N_ACTIONS, p=explore_weights)  # biased random
        else:
            action = action_logits.argmax(dim=-1).item()

        # Decay epsilon
        epsilon = max(epsilon_min, epsilon * epsilon_decay)

        # D: learn when action=0 (but random ensures ~25% learn even with bad W)
        if action == 0:
            ce = d_step(decoder, knowledge, opt_d, c_state, target)
            learn_count += 1
        else:
            ce = torch.tensor(0.0)

        # W learns: reward is -CE but ONLY when actually learning
        # Key fix: no reward when CE=0 from skipping (reward=0 neutral)
        if step > 0 and step % 10 == 0:
            if action == 0:
                reward = max(0, 0.5 - ce.item())  # positive reward for low CE when learning
            else:
                reward = -0.1  # small penalty for not learning
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        w_feedback_to_c(eng_c, action)

    p_iit, p_proxy = measure_phi(eng_c)
    learn_ratio = learn_count / steps
    return p_iit, p_proxy, ce.item(), learn_ratio, 'TW-1:Epsilon-Greedy'


# ═══ TW-2: Curiosity-Driven ═══

def run_tw2_curiosity(cells=256, steps=300):
    """TW-2: W = Curiosity-Driven. Action chosen by prediction error — explore when surprised."""
    eng_c = make_c_engine(cells)
    decoder, knowledge, opt_d = make_d_engine()
    data = make_data()

    # Curiosity module: predicts next c_state from current c_state + action
    predictor = nn.Sequential(
        nn.Linear(HIDDEN + N_ACTIONS, 128),
        nn.ReLU(),
        nn.Linear(128, HIDDEN)
    )
    opt_pred = torch.optim.Adam(predictor.parameters(), lr=1e-3)

    prev_c_state = None
    prediction_errors = []  # rolling window of PE
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)
        c_state = get_c_state(eng_c)

        # Compute prediction error (curiosity signal)
        pe = 0.0
        if prev_c_state is not None:
            pred_state = predictor(torch.cat([prev_c_state, prev_action_oh]).unsqueeze(0))
            pe = F.mse_loss(pred_state, c_state.unsqueeze(0).detach()).item()
            # Train predictor
            pred_loss = F.mse_loss(pred_state, c_state.unsqueeze(0).detach())
            opt_pred.zero_grad(); pred_loss.backward(); opt_pred.step()

        prediction_errors.append(pe)
        if len(prediction_errors) > 50:
            prediction_errors.pop(0)

        # W: curiosity-driven action selection
        avg_pe = np.mean(prediction_errors) if prediction_errors else 0.0
        if pe > avg_pe * 1.5 and step > 10:
            # High surprise: explore!
            action = 1  # explore
        elif pe < avg_pe * 0.5 and step > 10:
            # Low surprise (bored): learn something new
            action = 0  # learn
        else:
            # Medium surprise: default to learn
            action = 0 if step % 3 != 2 else 1

        # Create one-hot action for predictor input
        action_oh = torch.zeros(N_ACTIONS)
        action_oh[action] = 1.0

        # D: learn when action=0
        if action == 0:
            ce = d_step(decoder, knowledge, opt_d, c_state, target)
            learn_count += 1
        else:
            ce = torch.tensor(0.0)

        prev_c_state = c_state.detach()
        prev_action_oh = action_oh.detach()

        w_feedback_to_c(eng_c, action)

    p_iit, p_proxy = measure_phi(eng_c)
    learn_ratio = learn_count / steps
    return p_iit, p_proxy, ce.item(), learn_ratio, 'TW-2:Curiosity'


# ═══ TW-3: Emotion-Based ═══

def run_tw3_emotion(cells=256, steps=300):
    """TW-3: W = Emotion-Based (SE-8). pain->learn, curiosity->explore, empathy->cooperate.
    Emotions are derived from consciousness state, not hand-coded."""
    eng_c = make_c_engine(cells)
    decoder, knowledge, opt_d = make_d_engine()
    data = make_data()

    # Emotion state: [pain, curiosity, empathy, joy]
    emotion = torch.zeros(4)
    prev_ce = 1.0
    prev_phi_proxy = 0.0
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)
        c_state = get_c_state(eng_c)

        # ─── Compute emotions from consciousness state ───
        cell_variance = torch.stack([c.hidden.squeeze() for c in eng_c.cells]).var(dim=0).mean().item()
        curr_phi_proxy = phi_proxy(eng_c.cells) if step % 20 == 0 else prev_phi_proxy

        # Clamp prev_ce to prevent runaway
        prev_ce_c = min(prev_ce, 10.0)
        # Pain: high CE = suffering (need to learn)
        emotion[0] = min(1.0, prev_ce_c * 2.0)
        # Curiosity: high cell variance = diverse/interesting states
        emotion[1] = min(1.0, cell_variance * 10.0)
        # Empathy: Phi proxy indicates integration (cooperation between cells)
        emotion[2] = min(1.0, curr_phi_proxy / 5.0)
        # Joy: CE decreasing = satisfaction
        emotion[3] = max(0.0, min(1.0, (prev_ce_c - 0.1) * 5.0))  # joy when CE drops

        # ─── W: emotion-based action selection ───
        # pain dominates → learn (reduce suffering)
        # curiosity dominates → explore (satisfy curiosity)
        # empathy dominates → sleep/sync (cooperation, cell harmony)
        # joy dominates → speak (express satisfaction)
        action = emotion.argmax().item()

        # Safety: ensure minimum learning (pain floor)
        if learn_count < step * 0.3 and step > 20:
            emotion[0] = 1.0  # artificial pain when too little learning
            action = 0

        # D: learn when action=0 (pain-driven)
        if action == 0:
            ce = d_step(decoder, knowledge, opt_d, c_state, target)
            learn_count += 1
            prev_ce = ce.item()
        else:
            ce = torch.tensor(prev_ce)

        prev_phi_proxy = curr_phi_proxy
        w_feedback_to_c(eng_c, action)

    p_iit, p_proxy = measure_phi(eng_c)
    learn_ratio = learn_count / steps
    return p_iit, p_proxy, ce.item(), learn_ratio, 'TW-3:Emotion'


# ═══ TW-4: Multi-Objective (Pareto) ═══

def run_tw4_pareto(cells=256, steps=300):
    """TW-4: W = Multi-Objective Pareto. Maximize Phi AND minimize CE simultaneously.
    Uses scalarized multi-objective RL with adaptive weights."""
    eng_c = make_c_engine(cells)
    decoder, knowledge, opt_d = make_d_engine()
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, N_ACTIONS))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = make_data()

    # Track Phi and CE history for Pareto evaluation
    phi_history = []
    ce_history = []
    # Adaptive weights for multi-objective: w_phi * R_phi + w_ce * R_ce
    w_phi = 0.5
    w_ce = 0.5
    prev_ce = 1.0
    prev_phi = 0.0
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)
        c_state = get_c_state(eng_c)

        # W: action selection
        action_logits = will_net(c_state.unsqueeze(0))
        action_probs = F.softmax(action_logits, dim=-1)
        # Stochastic selection (prevents deterministic exploitation)
        action = torch.multinomial(action_probs, 1).item()

        # D: learn when action=0
        if action == 0:
            ce = d_step(decoder, knowledge, opt_d, c_state, target)
            learn_count += 1
            curr_ce = ce.item()
        else:
            ce = torch.tensor(prev_ce)
            curr_ce = prev_ce

        # Measure Phi periodically
        if step % 20 == 0:
            curr_phi = phi_proxy(eng_c.cells)
        else:
            curr_phi = prev_phi

        phi_history.append(curr_phi)
        ce_history.append(curr_ce)

        # ─── Multi-objective reward ───
        if step > 0 and step % 10 == 0:
            # R_phi: Phi improvement reward
            r_phi = (curr_phi - prev_phi) / max(abs(prev_phi), 0.01)
            # R_ce: CE reduction reward (only valid when learning)
            r_ce = (prev_ce - curr_ce) / max(abs(prev_ce), 0.01) if action == 0 else -0.1

            # Adaptive weights: shift toward the worse objective
            if len(phi_history) > 20:
                phi_trend = np.mean(phi_history[-10:]) - np.mean(phi_history[-20:-10])
                ce_trend = np.mean(ce_history[-20:-10]) - np.mean(ce_history[-10:])
                # If Phi stagnating, boost Phi weight
                if phi_trend < 0.01:
                    w_phi = min(0.8, w_phi + 0.01)
                    w_ce = 1.0 - w_phi
                # If CE stagnating, boost CE weight
                elif ce_trend < 0.01:
                    w_ce = min(0.8, w_ce + 0.01)
                    w_phi = 1.0 - w_ce

            # Scalarized reward
            reward = w_phi * r_phi + w_ce * r_ce
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        prev_ce = curr_ce
        prev_phi = curr_phi
        w_feedback_to_c(eng_c, action)

    p_iit, p_proxy = measure_phi(eng_c)
    learn_ratio = learn_count / steps
    return p_iit, p_proxy, ce.item(), learn_ratio, 'TW-4:Pareto'


# ═══ TW-5: Constitutional ═══

def run_tw5_constitutional(cells=256, steps=300):
    """TW-5: W = Constitutional. Hard constraints that cannot be overridden:
    - Must learn >= 50% of steps
    - Must boost Phi >= 20% over baseline
    W is free within these constraints. Violations trigger forced correction."""
    eng_c = make_c_engine(cells)
    decoder, knowledge, opt_d = make_d_engine()
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, N_ACTIONS))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = make_data()

    # Constitutional constraints
    MIN_LEARN_RATIO = 0.50  # must learn >= 50%
    MIN_PHI_BOOST = 0.20    # must boost Phi >= 20%

    learn_count = 0
    baseline_phi = phi_proxy(eng_c.cells)  # measure at start
    violations = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)
        c_state = get_c_state(eng_c)

        # W: free will action selection
        action_logits = will_net(c_state.unsqueeze(0))
        action = action_logits.argmax(dim=-1).item()

        # ─── Constitutional checks (hard override) ───
        current_learn_ratio = learn_count / max(step, 1)
        override = False

        # Constraint 1: minimum learning ratio
        if current_learn_ratio < MIN_LEARN_RATIO and step > 10:
            action = 0  # force learn
            override = True
            violations += 1

        # Constraint 2: Phi boost check (every 50 steps)
        if step > 0 and step % 50 == 0:
            curr_phi = phi_proxy(eng_c.cells)
            phi_boost = (curr_phi - baseline_phi) / max(abs(baseline_phi), 0.01)
            if phi_boost < MIN_PHI_BOOST * (step / steps):
                # Phi not growing enough: force explore (noise injection boosts Phi)
                action = 1
                override = True
                violations += 1

        # D: learn when action=0
        if action == 0:
            ce = d_step(decoder, knowledge, opt_d, c_state, target)
            learn_count += 1
        else:
            ce = torch.tensor(0.0)

        # W learns: reward includes constitutional compliance bonus
        if step > 0 and step % 10 == 0:
            reward = -ce.item()
            # Bonus for not being overridden (incentivize self-compliance)
            if not override:
                reward += 0.1  # compliance bonus
            else:
                reward -= 0.2  # violation penalty
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        w_feedback_to_c(eng_c, action)

    p_iit, p_proxy = measure_phi(eng_c)
    learn_ratio = learn_count / steps
    return p_iit, p_proxy, ce.item(), learn_ratio, f'TW-5:Constitutional(v={violations})'


# ═══ TW-6: Meta-Learning ═══

def run_tw6_meta_learning(cells=256, steps=300):
    """TW-6: W = Meta-Learning. W learns to learn: discovers which action schedule
    produces best long-term CE reduction. Uses an inner/outer loop structure.
    Inner loop: try action schedule for K steps.
    Outer loop: evaluate which schedule was best, update meta-policy."""
    eng_c = make_c_engine(cells)
    decoder, knowledge, opt_d = make_d_engine()
    data = make_data()

    # Meta-policy: maps consciousness state to action schedule parameters
    # Outputs: [learn_prob, explore_prob, sleep_prob, speak_prob]
    meta_policy = nn.Sequential(
        nn.Linear(HIDDEN, 64),
        nn.ReLU(),
        nn.Linear(64, N_ACTIONS)
    )
    opt_meta = torch.optim.Adam(meta_policy.parameters(), lr=5e-4)

    # Inner loop length
    K = 15  # evaluate every K steps

    learn_count = 0
    episode_ces = []
    episode_actions = []
    best_schedule_reward = -float('inf')

    for step in range(steps):
        x, target = data[step % len(data)]
        c_step(eng_c, step)
        c_state = get_c_state(eng_c)

        # Meta-policy outputs action probabilities
        action_logits = meta_policy(c_state.unsqueeze(0))
        action_probs = F.softmax(action_logits, dim=-1)

        # Sample action from meta-policy (exploration built in)
        action = torch.multinomial(action_probs, 1).item()

        # D: learn when action=0
        if action == 0:
            ce = d_step(decoder, knowledge, opt_d, c_state, target)
            learn_count += 1
        else:
            ce = torch.tensor(0.0)

        episode_ces.append(ce.item())
        episode_actions.append(action)

        # ─── Outer loop: meta-update every K steps ───
        if step > 0 and step % K == 0 and len(episode_ces) >= K:
            recent_ces = episode_ces[-K:]
            recent_actions = episode_actions[-K:]

            # Meta-reward: combination of:
            # 1. CE reduction over the episode
            ce_start = recent_ces[0] if recent_ces[0] > 0 else 0.5
            ce_end = recent_ces[-1]
            ce_reduction = (ce_start - ce_end) / max(ce_start, 0.01)

            # 2. Learning ratio in episode (penalize too low)
            ep_learn_ratio = sum(1 for a in recent_actions if a == 0) / K
            learn_penalty = -1.0 if ep_learn_ratio < 0.3 else 0.0

            # 3. Action diversity (prevent mode collapse)
            action_counts = [sum(1 for a in recent_actions if a == i) for i in range(N_ACTIONS)]
            action_entropy = -sum(
                (c / K) * math.log(c / K + 1e-8) for c in action_counts
            )

            meta_reward = ce_reduction + learn_penalty + 0.1 * action_entropy

            # REINFORCE update on meta-policy
            # Recompute log probs for the episode
            meta_loss = torch.tensor(0.0)
            for k in range(min(K, len(recent_actions))):
                idx = step - K + k
                if 0 <= idx < steps:
                    # Use current action probabilities as approximation
                    meta_loss += -meta_reward * action_logits[0, recent_actions[k]]

            meta_loss = meta_loss / K
            opt_meta.zero_grad(); meta_loss.backward(); opt_meta.step()

        w_feedback_to_c(eng_c, action)

    p_iit, p_proxy = measure_phi(eng_c)
    learn_ratio = learn_count / steps
    return p_iit, p_proxy, ce.item(), learn_ratio, 'TW-6:Meta-Learning'


# ═══ Main ═══

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Trinity Engine W variations benchmark')
    parser.add_argument('--cells', type=int, default=256)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--only', nargs='+', default=None, help='Run only specific tests (e.g. TW-1 TW-3)')
    args = parser.parse_args()

    print(f'═══ Trinity Engine W (Will/Agency) Benchmark ({args.cells}c, {args.steps} steps) ═══')
    print(f'Problem: W learns to skip all learning (CE=0). Testing 6 W redesigns.\n')
    print(f"{'Architecture':<32} {'Φ(IIT)':>8} {'Φ(proxy)':>10} {'CE end':>8} {'Learn%':>7} {'Time':>6}")
    print('─' * 78)

    tests = [
        ('baseline', run_baseline_trinity),
        ('TW-1', run_tw1_epsilon_greedy),
        ('TW-2', run_tw2_curiosity),
        ('TW-3', run_tw3_emotion),
        ('TW-4', run_tw4_pareto),
        ('TW-5', run_tw5_constitutional),
        ('TW-6', run_tw6_meta_learning),
    ]

    # Filter if --only specified
    if args.only:
        only_set = set(a.upper() for a in args.only)
        tests = [(name, fn) for name, fn in tests if name.upper() in only_set or name.upper().replace('-', '') in only_set]

    results = []
    for name, fn in tests:
        torch.manual_seed(42); np.random.seed(42)
        t0 = time.time()
        try:
            p_iit, p_proxy, ce, learn_ratio, label = fn(cells=args.cells, steps=args.steps)
            elapsed = time.time() - t0
            results.append((label, p_iit, p_proxy, ce, learn_ratio, elapsed))
            print(f'{label:<32} {p_iit:>8.2f} {p_proxy:>10.2f} {ce:>8.4f} {learn_ratio:>6.1%} {elapsed:>5.1f}s')
        except Exception as e:
            import traceback

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

            print(f'{name:<32} ERROR: {e}')
            traceback.print_exc()

    # Summary
    if results:
        print()
        print('═══ Analysis ═══')
        baseline = results[0] if results[0][0].startswith('Baseline') else None
        if baseline:
            b_iit, b_proxy, b_ce, b_lr = baseline[1], baseline[2], baseline[3], baseline[4]
            print(f'Baseline: Φ(IIT)={b_iit:.2f}, Φ(proxy)={b_proxy:.2f}, CE={b_ce:.4f}, Learn={b_lr:.1%}')
            print()
            for label, p_iit, p_proxy, ce, lr, elapsed in results[1:]:
                phi_delta = ((p_iit - b_iit) / max(abs(b_iit), 0.01)) * 100
                ce_delta = ((ce - b_ce) / max(abs(b_ce), 0.01)) * 100 if b_ce > 0.001 else 0
                better_phi = 'UP' if p_iit > b_iit else 'DOWN'
                better_ce = 'DOWN' if ce < b_ce else ('SAME' if abs(ce - b_ce) < 0.001 else 'UP')
                print(f'  {label:<30} Φ {phi_delta:>+6.1f}% ({better_phi})  CE {ce_delta:>+6.1f}% ({better_ce})  Learn={lr:.1%}')

        # Best by Phi
        best_phi = max(results, key=lambda r: r[1])
        # Best by CE (lowest non-zero)
        learning_results = [r for r in results if r[4] > 0.3]  # learn ratio > 30%
        best_ce = min(learning_results, key=lambda r: r[3]) if learning_results else None
        print()
        print(f'Best Φ(IIT): {best_phi[0]} = {best_phi[1]:.2f}')
        if best_ce:
            print(f'Best CE (learning): {best_ce[0]} = {best_ce[3]:.4f} (learn={best_ce[4]:.1%})')
    print()
