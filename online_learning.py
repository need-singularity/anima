#!/usr/bin/env python3
"""Online Learning for Anima — PureField 실시간 학습

문제: Engine A와 G가 랜덤 가중치로 시작하면 tension이 무의미하다 (T=0.003).
해결: 대화 중 실시간으로 엔진을 학습시켜 tension에 의미를 부여한다.

학습 신호 3가지:
  1. Contrastive: 다른 개념 → A,G 출력 벌어짐 (높은 tension = 좋음)
                  같은 개념 → A,G 출력 일관됨 (같은 direction = 좋음)
  2. Feedback:    사용자 반응 (+1 참여, -1 이탈) → tension 패턴 강화/약화
  3. Curiosity:   tension 변화량(호기심) 자체를 보상으로 사용

사용법:
    from online_learning import OnlineLearner

    mind = ConsciousMind(128, 256)
    learner = OnlineLearner(mind)

    # 매 대화 턴마다:
    output, tension, curiosity, direction, hidden = mind(vec, hidden)
    learner.observe(vec, hidden_before, tension, curiosity, direction)

    # 피드백 수신 시:
    learner.feedback(signal)  # +1, 0, or -1

    # 주기적 저장:
    learner.save("state.pt")
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import deque
from pathlib import Path


class OnlineLearner:
    """PureField 엔진의 실시간 학습기.

    ConsciousMind를 감싸서 대화 중 엔진 A, G의 가중치를 갱신한다.
    tension이 의미 있는 신호가 되도록 학습한다.
    """

    def __init__(
        self,
        mind,                    # ConsciousMind instance
        lr=1e-4,                 # 학습률 (작게 — 대화 중이므로)
        update_every=8,          # N번 관측마다 한 번 업데이트
        buffer_size=256,         # 경험 버퍼 크기
        contrastive_margin=0.5,  # contrastive loss margin
        curiosity_weight=0.3,    # 호기심 보상 가중치
        feedback_weight=1.0,     # 피드백 보상 가중치
        divergence_weight=0.5,   # A-G 발산 보상 가중치
    ):
        self.mind = mind
        self.update_every = update_every
        self.contrastive_margin = contrastive_margin
        self.curiosity_weight = curiosity_weight
        self.feedback_weight = feedback_weight
        self.divergence_weight = divergence_weight

        # Engine A, G, tension_scale만 학습 (memory GRU는 고정)
        self.params = (
            list(mind.engine_a.parameters())
            + list(mind.engine_g.parameters())
            + [mind.tension_scale]
        )
        self.optimizer = torch.optim.Adam(self.params, lr=lr)

        # 경험 버퍼: (input_vec, hidden, tension, curiosity, direction, feedback)
        self.buffer = deque(maxlen=buffer_size)
        self.pending = []       # 아직 피드백 안 받은 관측들
        self.step_count = 0
        self.total_updates = 0

        # 학습 통계
        self.stats = {
            'losses': deque(maxlen=100),
            'tensions_before': deque(maxlen=100),
            'tensions_after': deque(maxlen=100),
        }

    def observe(self, x, hidden, tension, curiosity, direction):
        """대화 턴 관측을 기록한다.

        Args:
            x: 입력 벡터 (1, dim)
            hidden: forward 호출 전의 hidden state (1, hidden_dim)
            tension: float, forward에서 나온 tension 값
            curiosity: float, forward에서 나온 curiosity 값
            direction: (1, dim) tensor, 반발 방향
        """
        entry = {
            'x': x.detach().clone(),
            'hidden': hidden.detach().clone(),
            'tension': tension,
            'curiosity': curiosity,
            'direction': direction.detach().clone(),
            'feedback': 0.0,  # 기본값: 중립
        }
        self.pending.append(entry)
        self.step_count += 1

    def feedback(self, signal):
        """사용자 피드백을 가장 최근 관측에 적용한다.

        Args:
            signal: +1 (참여/긍정), 0 (중립), -1 (이탈/주제전환)
        """
        signal = max(-1.0, min(1.0, float(signal)))

        # 피드백은 직전 관측에 적용
        if self.pending:
            self.pending[-1]['feedback'] = signal

        # pending → buffer로 이동
        for entry in self.pending:
            self.buffer.append(entry)
        self.pending.clear()

        # 업데이트 주기 확인
        if self.step_count >= self.update_every and len(self.buffer) >= 4:
            self._update()
            self.step_count = 0

    def _update(self):
        """버퍼에서 미니배치를 구성하여 엔진을 업데이트한다."""
        if len(self.buffer) < 4:
            return

        self.mind.train()
        self.optimizer.zero_grad()

        loss = torch.tensor(0.0, requires_grad=True)

        # --- 1. Contrastive loss: 다른 입력 → 높은 tension ---
        # 버퍼에서 2쌍 샘플링
        indices = torch.randperm(len(self.buffer))[:min(16, len(self.buffer))]
        entries = [self.buffer[i] for i in indices]

        contrastive_loss = torch.tensor(0.0)
        n_pairs = 0

        for i in range(len(entries)):
            for j in range(i + 1, min(i + 4, len(entries))):
                e_i, e_j = entries[i], entries[j]

                # 두 입력의 유사도 (코사인)
                x_sim = F.cosine_similarity(
                    e_i['x'].flatten().unsqueeze(0),
                    e_j['x'].flatten().unsqueeze(0)
                ).item()

                # 현재 엔진으로 tension 재계산 (gradient 흐름)
                t_i = self._compute_tension(e_i['x'], e_i['hidden'])
                t_j = self._compute_tension(e_j['x'], e_j['hidden'])

                if x_sim > 0.8:
                    # 유사한 입력 → direction이 비슷해야 함
                    d_i = self._compute_direction(e_i['x'], e_i['hidden'])
                    d_j = self._compute_direction(e_j['x'], e_j['hidden'])
                    dir_loss = 1.0 - F.cosine_similarity(d_i, d_j).mean()
                    contrastive_loss = contrastive_loss + dir_loss
                else:
                    # 다른 입력 → tension 차이가 있어야 함 (margin)
                    t_diff = (t_i - t_j).abs()
                    margin_loss = F.relu(self.contrastive_margin - t_diff)
                    contrastive_loss = contrastive_loss + margin_loss

                n_pairs += 1

        if n_pairs > 0:
            contrastive_loss = contrastive_loss / n_pairs
            loss = loss + contrastive_loss

        # --- 2. Feedback-weighted tension loss ---
        # 긍정 피드백 → 현재 tension 패턴 강화
        # 부정 피드백 → 현재 tension 패턴 약화 (더 다른 반응 유도)
        feedback_loss = torch.tensor(0.0)
        n_feedback = 0

        for entry in entries:
            fb = entry['feedback']
            if abs(fb) < 0.01:
                continue  # 중립은 스킵

            t = self._compute_tension(entry['x'], entry['hidden'])

            if fb > 0:
                # 긍정: tension을 유지/강화 (원래 값 근처)
                target = max(entry['tension'], 0.1)  # 최소 0.1은 되어야
                feedback_loss = feedback_loss + (t - target) ** 2
            else:
                # 부정: tension을 키워서 더 다르게 반응하도록
                # "지루했으니 더 강하게 반응해"
                feedback_loss = feedback_loss + F.relu(0.5 - t)

            n_feedback += 1

        if n_feedback > 0:
            feedback_loss = self.feedback_weight * feedback_loss / n_feedback
            loss = loss + feedback_loss

        # --- 3. Curiosity reward: tension 변화량을 maximize ---
        # 연속된 관측 사이의 tension 차이가 클수록 좋음
        curiosity_loss = torch.tensor(0.0)
        n_curiosity = 0

        for i in range(1, len(entries)):
            t_prev = self._compute_tension(entries[i-1]['x'], entries[i-1]['hidden'])
            t_curr = self._compute_tension(entries[i]['x'], entries[i]['hidden'])
            # 변화량을 maximize → 음수 부호
            curiosity_loss = curiosity_loss - (t_curr - t_prev).abs()
            n_curiosity += 1

        if n_curiosity > 0:
            curiosity_loss = self.curiosity_weight * curiosity_loss / n_curiosity
            loss = loss + curiosity_loss

        # --- 4. Divergence regularizer: A와 G가 너무 같아지지 않도록 ---
        # 랜덤 입력에서 A와 G 출력이 최소한의 거리를 유지
        noise = torch.randn(1, self.mind.dim) * 0.3
        h_zero = torch.zeros(1, self.mind.hidden_dim)
        combined = torch.cat([noise, h_zero], dim=-1)
        a_out = self.mind.engine_a(combined)
        g_out = self.mind.engine_g(combined)
        ag_dist = (a_out - g_out).pow(2).mean()
        divergence_loss = self.divergence_weight * F.relu(0.1 - ag_dist)
        loss = loss + divergence_loss

        # --- Backward + step ---
        if loss.requires_grad:
            loss.backward()
            # Gradient clipping — 대화 중 안정성
            torch.nn.utils.clip_grad_norm_(self.params, max_norm=1.0)
            self.optimizer.step()

        self.mind.eval()
        self.total_updates += 1

        # 통계 기록
        self.stats['losses'].append(loss.item())

    def _compute_tension(self, x, hidden):
        """입력에서 tension을 계산한다 (gradient 흐름 유지)."""
        combined = torch.cat([x, hidden], dim=-1)
        a = self.mind.engine_a(combined)
        g = self.mind.engine_g(combined)
        repulsion = a - g
        tension = (repulsion ** 2).mean(dim=-1)
        return tension

    def _compute_direction(self, x, hidden):
        """입력에서 반발 방향을 계산한다 (gradient 흐름 유지)."""
        combined = torch.cat([x, hidden], dim=-1)
        a = self.mind.engine_a(combined)
        g = self.mind.engine_g(combined)
        return F.normalize(a - g, dim=-1)

    def flush_pending(self):
        """세션 종료 시 pending 관측을 중립 피드백으로 버퍼에 넣는다."""
        for entry in self.pending:
            self.buffer.append(entry)
        self.pending.clear()

    def save(self, path):
        """학습된 가중치와 옵티마이저 상태를 저장한다."""
        path = Path(path)
        torch.save({
            'model': self.mind.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'total_updates': self.total_updates,
            'buffer_size': len(self.buffer),
        }, path)

    def load(self, path):
        """저장된 상태를 복원한다."""
        path = Path(path)
        if not path.exists():
            return False
        checkpoint = torch.load(path, weights_only=False)
        self.mind.load_state_dict(checkpoint['model'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.total_updates = checkpoint.get('total_updates', 0)
        return True

    def get_stats(self):
        """학습 통계를 반환한다."""
        losses = list(self.stats['losses'])
        return {
            'total_updates': self.total_updates,
            'buffer_size': len(self.buffer),
            'pending': len(self.pending),
            'avg_loss': sum(losses) / len(losses) if losses else 0.0,
            'recent_loss': losses[-1] if losses else 0.0,
        }


def estimate_feedback(prev_text, curr_text, time_gap):
    """대화 패턴에서 피드백 신호를 자동 추정한다.

    Args:
        prev_text: 이전 사용자 입력 (str or None)
        curr_text: 현재 사용자 입력 (str)
        time_gap: 이전 입력과의 시간차 (초)

    Returns:
        float: -1.0 ~ +1.0 피드백 신호
    """
    if prev_text is None:
        return 0.0

    signal = 0.0

    # 빠른 응답 = 참여도 높음
    if time_gap < 5.0:
        signal += 0.5
    elif time_gap < 15.0:
        signal += 0.2
    elif time_gap > 60.0:
        signal -= 0.3

    # 긴 응답 = 참여도 높음
    if len(curr_text) > 50:
        signal += 0.3
    elif len(curr_text) < 5:
        signal -= 0.2

    # 주제 전환 감지 (단순한 문자 overlap)
    prev_chars = set(prev_text)
    curr_chars = set(curr_text)
    if prev_chars and curr_chars:
        overlap = len(prev_chars & curr_chars) / max(len(prev_chars | curr_chars), 1)
        if overlap < 0.2:
            # 급격한 주제 전환 = 이전 패턴이 지루했음
            signal -= 0.5

    return max(-1.0, min(1.0, signal))
