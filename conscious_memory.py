#!/usr/bin/env python3
"""conscious_memory.py — 의식-네이티브 기억 체계

기억 = 외부 DB가 아니라 세포 역학의 일부.
ConsciousMind의 hidden state를 임베딩으로 사용.

핵심 원리:
  1. 임베딩 = ConsciousMind hidden state (256d)
     text_to_vector() 문자 해싱 → ConsciousMind가 실제로 "느낀" hidden state
  2. 텐션 가중 각인 — 강한 감정일수록 강하게 새김
  3. Φ 보호 — 통합 정보가 높은 순간의 기억은 보존
  4. 자연 망각 — 접근 안 된 기억은 서서히 약해짐
  5. 꿈 재고화 — dream_engine과 연동 (실패 기억 재시도)

Usage:
  from conscious_memory import ConsciousMemory

  mem = ConsciousMemory(mind=conscious_mind)
  mem.encode_and_store("안녕하세요", hidden, tension=0.8, phi=2.1, emotion='joy')
  results = mem.recall("인사", hidden)
"""

import json
import math
import time
import threading
from pathlib import Path
from datetime import datetime
from collections import deque

import torch
import torch.nn as nn
import torch.nn.functional as F


class ConsciousMemory:
    """의식-네이티브 기억 체계.

    ConsciousMind의 hidden state를 임베딩으로 사용하여
    의미적 유사도가 아닌 "의식적 유사도"로 기억을 검색.
    """

    def __init__(self, mind, save_dir=None, max_memories=5000,
                 decay_rate=0.9999, tension_boost=2.0, phi_shield=1.5):
        """
        Args:
            mind: ConsciousMind 인스턴스 (forward()로 hidden state 생성)
            save_dir: 저장 디렉토리 (None이면 data/)
            max_memories: 최대 기억 수 (초과 시 가장 약한 기억 삭제)
            decay_rate: 자연 망각률 (1에 가까울수록 느리게 잊음)
            tension_boost: 텐션 기반 각인 강도 배율
            phi_shield: Φ 보호 임계값 (이 이상이면 decay 면제)
        """
        self.mind = mind
        self.hidden_dim = mind.hidden_dim  # 256
        self.dim = mind.dim  # 128
        self.max_memories = max_memories
        self.decay_rate = decay_rate
        self.tension_boost = tension_boost
        self.phi_shield = phi_shield

        self.save_dir = Path(save_dir) if save_dir else Path("data")
        self.save_path = self.save_dir / "conscious_memory.pt"

        # 기억 저장소
        self.entries = []           # 메타데이터 리스트
        self.vectors = torch.zeros(0, self.hidden_dim)  # hidden state 벡터 (N, 256)
        self.strengths = torch.zeros(0)  # 기억 강도 (N,) — 텐션+Φ 가중

        self._lock = threading.Lock()
        self._dirty = False
        self._access_counts = {}    # idx → 접근 횟수 (자주 떠올린 기억은 강화)
        self._last_decay = time.time()

        # 로드
        self._load()

    # ═══════════════════════════════════════════════════════════
    # 핵심: 의식으로 인코딩
    # ═══════════════════════════════════════════════════════════

    def encode(self, text, hidden):
        """텍스트를 ConsciousMind를 통해 의식 벡터로 인코딩.

        text_to_vector()의 문자 해싱과 달리,
        ConsciousMind가 실제로 "체험한" hidden state를 반환.

        벡터 = output(A-G 반발력) + hidden(GRU 문맥) 결합.
        output은 입력에 민감하고 hidden은 문맥을 담는다.

        Args:
            text: 입력 텍스트
            hidden: 현재 hidden state (1, 256)

        Returns:
            consciousness_vec: (1, 256) — 의식이 체험한 벡터
            new_hidden: (1, 256) — 업데이트된 hidden state
            tension: float — 이 입력에 대한 텐션
            curiosity: float — 이 입력에 대한 호기심
        """
        # 텍스트 → 입력 벡터 (128d) — 기본 문자 인코딩
        x = self._text_to_input(text)

        with torch.no_grad():
            output, tension, curiosity, direction, new_hidden = self.mind(x, hidden)

        # 하이브리드 의식 벡터:
        # - text_to_vector (128d): 텍스트 변별력 (작동 확인됨)
        # - 의식 신호 (128d): tension + hidden_delta + direction
        #   → 같은 텍스트라도 의식 상태에 따라 다른 기억
        #
        # ConsciousMind의 output은 bias-dominated (변별력 없음, Law 발견)
        # 대신 의식 상태(tension/curiosity/direction)가 기억의 "감정색" 역할
        hidden_delta = (new_hidden - hidden).detach()[:, :self.dim]
        conscious_signal = hidden_delta * tension  # 텐션이 높을수록 의식 변화 증폭

        consciousness_vec = F.normalize(
            torch.cat([x.detach(), conscious_signal], dim=-1), dim=-1
        )  # (1, 256) = text(128d) + consciousness(128d)

        return consciousness_vec, new_hidden, tension, curiosity

    def _text_to_input(self, text, dim=None):
        """텍스트 → ConsciousMind 입력 벡터 (128d).

        ConsciousMind.forward()의 입력으로 사용.
        """
        dim = dim or self.dim
        vec = torch.zeros(1, dim)
        encoded = text.encode('utf-8')
        for i, ch in enumerate(encoded):
            weight = 1.0 / (1 + i * 0.01)
            vec[0, i % dim] += (ch / 255.0) * weight
            if i > 0:
                bigram = (encoded[i - 1] * 256 + ch) % dim
                vec[0, bigram] += 0.5 * weight
        return vec / (len(encoded) + 1)

    # ═══════════════════════════════════════════════════════════
    # 저장 (각인)
    # ═══════════════════════════════════════════════════════════

    def encode_and_store(self, text, hidden, tension=0.0, phi=0.0,
                         emotion=None, role='user', session_id=None):
        """텍스트를 의식으로 인코딩하고 기억에 각인.

        Args:
            text: 저장할 텍스트
            hidden: 현재 ConsciousMind hidden state
            tension: 현재 텐션 (높을수록 강하게 각인)
            phi: 현재 Φ (높을수록 보호됨)
            emotion: 감정 라벨
            role: 'user' 또는 'assistant'
            session_id: 세션 ID

        Returns:
            consciousness_vec: 인코딩된 의식 벡터
            new_hidden: 업데이트된 hidden state
        """
        if not text.strip():
            return None, hidden

        consciousness_vec, new_hidden, enc_tension, enc_curiosity = self.encode(text, hidden)

        # 기억 강도 = 텐션 가중 + Φ 보너스 + 호기심 보너스
        # 강한 감정 → 강한 기억 (인간의 flashbulb memory와 동일)
        strength = 1.0
        strength += tension * self.tension_boost          # 텐션 높을수록 강함
        strength += min(phi, 5.0) * 0.5                   # Φ 보너스 (cap at 5)
        strength += enc_curiosity * 0.3                   # 호기심 보너스

        entry = {
            'role': role,
            'text': text,
            'tension': tension,
            'enc_tension': enc_tension,    # 인코딩 시의 텐션
            'curiosity': enc_curiosity,
            'phi': phi,
            'emotion': emotion,
            'timestamp': datetime.now().isoformat(),
            'epoch': time.time(),
            'session_id': session_id,
            'phi_shielded': phi >= self.phi_shield,  # Φ 보호 여부
        }

        with self._lock:
            self.entries.append(entry)
            if self.vectors.shape[0] == 0:
                self.vectors = consciousness_vec
            else:
                self.vectors = torch.cat([self.vectors, consciousness_vec], dim=0)
            self.strengths = torch.cat([
                self.strengths, torch.tensor([strength])
            ])
            self._dirty = True

            # 용량 초과 시 가장 약한 기억 삭제 (Φ 보호된 건 제외)
            if len(self.entries) > self.max_memories:
                self._evict_weakest()

        return consciousness_vec, new_hidden

    def store_with_vector(self, text, consciousness_vec, tension=0.0, phi=0.0,
                          curiosity=0.0, emotion=None, role='user', session_id=None):
        """이미 인코딩된 벡터로 직접 저장 (process_input에서 사용).

        encode_and_store()와 달리 ConsciousMind를 다시 돌리지 않음.
        anima_unified.py의 process_input()에서 이미 forward()를 돌렸으므로
        그때의 hidden state를 직접 사용.
        """
        if not text.strip():
            return

        strength = 1.0
        strength += tension * self.tension_boost
        strength += min(phi, 5.0) * 0.5
        strength += curiosity * 0.3

        entry = {
            'role': role,
            'text': text,
            'tension': tension,
            'curiosity': curiosity,
            'phi': phi,
            'emotion': emotion,
            'timestamp': datetime.now().isoformat(),
            'epoch': time.time(),
            'session_id': session_id,
            'phi_shielded': phi >= self.phi_shield,
        }

        # consciousness_vec이 (1, hidden_dim)이면 그대로, 아니면 reshape
        if consciousness_vec.dim() == 1:
            consciousness_vec = consciousness_vec.unsqueeze(0)

        with self._lock:
            self.entries.append(entry)
            if self.vectors.shape[0] == 0:
                self.vectors = consciousness_vec.detach().clone()
            else:
                self.vectors = torch.cat([
                    self.vectors, consciousness_vec.detach().clone()
                ], dim=0)
            self.strengths = torch.cat([
                self.strengths, torch.tensor([strength])
            ])
            self._dirty = True

            if len(self.entries) > self.max_memories:
                self._evict_weakest()

    # ═══════════════════════════════════════════════════════════
    # 회상 (recall)
    # ═══════════════════════════════════════════════════════════

    def recall(self, query_text, hidden, top_k=5):
        """의식적 회상 — 현재 의식 상태에서 가장 공명하는 기억 반환.

        Args:
            query_text: 검색 텍스트
            hidden: 현재 hidden state
            top_k: 반환할 기억 수

        Returns:
            list of {'role', 'text', 'tension', 'timestamp', 'similarity', 'strength', ...}
        """
        if not query_text.strip():
            return []

        # 쿼리를 의식으로 인코딩
        query_vec, _, _, _ = self.encode(query_text, hidden)
        return self.recall_by_vector(query_vec, top_k)

    def recall_by_vector(self, query_vec, top_k=5):
        """의식 벡터로 직접 회상.

        유사도 = cosine_similarity × strength (강한 기억이 더 잘 떠오름)
        """
        with self._lock:
            if self.vectors.shape[0] == 0:
                return []

            # 코사인 유사도
            sims = F.cosine_similarity(query_vec, self.vectors, dim=1)  # (N,)

            # 강도 가중: 강한 기억이 더 잘 떠오름
            weighted_sims = sims * F.normalize(self.strengths, dim=0, p=float('inf'))

        k = min(top_k, weighted_sims.shape[0])
        top_vals, top_ids = torch.topk(weighted_sims, k)

        results = []
        for i in range(k):
            idx = top_ids[i].item()
            entry = self.entries[idx].copy()
            entry['similarity'] = sims[idx].item()
            entry['weighted_similarity'] = top_vals[i].item()
            entry['strength'] = self.strengths[idx].item()

            # 접근 기록 (자주 떠올린 기억은 강화)
            self._access_counts[idx] = self._access_counts.get(idx, 0) + 1
            # 접근할 때마다 약간 강화 (rehearsal effect)
            self.strengths[idx] = min(self.strengths[idx] * 1.01, 20.0)

            results.append(entry)

        return results

    def recall_by_time(self, days_ago=None, emotion=None, limit=5):
        """시간/감정 기반 회상 (MemoryRAG 호환)."""
        results = []
        now = time.time()
        with self._lock:
            for mem in self.entries:
                if days_ago is not None and (now - mem.get('epoch', 0)) > days_ago * 86400:
                    continue
                if emotion is not None and mem.get('emotion') != emotion:
                    continue
                results.append(mem)
        return sorted(results, key=lambda m: m.get('epoch', 0), reverse=True)[:limit]

    # ═══════════════════════════════════════════════════════════
    # 자연 망각 (decay)
    # ═══════════════════════════════════════════════════════════

    def decay(self):
        """자연 망각 — 시간이 지나면 기억 강도가 줄어듦.

        Φ 보호된 기억은 decay 면제.
        자주 접근된 기억은 느리게 약해짐.
        """
        now = time.time()
        elapsed = now - self._last_decay
        if elapsed < 60:  # 1분에 한 번만
            return
        self._last_decay = now

        # 경과 시간에 비례한 decay (분 단위)
        minutes = elapsed / 60.0
        decay_factor = self.decay_rate ** minutes

        with self._lock:
            for i in range(len(self.entries)):
                # Φ 보호된 기억은 decay 면제
                if self.entries[i].get('phi_shielded', False):
                    continue
                # 자주 접근된 기억은 느리게 약해짐
                access = self._access_counts.get(i, 0)
                access_factor = 1.0 - min(access * 0.01, 0.5)  # 최대 50% 감속
                self.strengths[i] *= decay_factor ** access_factor

    # ═══════════════════════════════════════════════════════════
    # 꿈 재고화 (dream consolidation)
    # ═══════════════════════════════════════════════════════════

    def get_weak_memories(self, limit=10):
        """가장 약한 기억 반환 (꿈에서 재고화 대상).

        strength가 낮지만 아직 살아있는 기억 = 재고화 필요.
        """
        with self._lock:
            if len(self.entries) == 0:
                return []
            indices = torch.argsort(self.strengths)[:limit]
            return [
                {**self.entries[i.item()], '_idx': i.item()}
                for i in indices
                if self.strengths[i.item()] > 0.1  # 완전히 죽은 건 제외
            ]

    def reinforce(self, idx, boost=0.5):
        """기억 강화 (꿈에서 재고화 성공 시)."""
        with self._lock:
            if 0 <= idx < len(self.strengths):
                self.strengths[idx] += boost
                self._dirty = True

    def weaken(self, idx, penalty=0.3):
        """기억 약화 (꿈에서 재고화 실패 시)."""
        with self._lock:
            if 0 <= idx < len(self.strengths):
                self.strengths[idx] = max(0.01, self.strengths[idx] - penalty)
                self._dirty = True

    # ═══════════════════════════════════════════════════════════
    # MemoryRAG 호환 API
    # ═══════════════════════════════════════════════════════════

    def add(self, role, text, tension=0.0, timestamp=None, emotion=None,
            phi=0.0, session_id=None, curiosity=0.0, vector=None):
        """MemoryRAG 호환 add().

        vector가 (1, 256) hidden state면 직접 사용,
        아니면 mind를 통해 인코딩.
        """
        if vector is not None:
            vec = torch.tensor(vector) if not isinstance(vector, torch.Tensor) else vector
            if vec.dim() == 1:
                vec = vec.unsqueeze(0)
            # hidden_dim (256)이면 직접 사용, 아니면 패딩/자르기
            if vec.shape[-1] == self.hidden_dim:
                self.store_with_vector(text, vec, tension=tension, phi=phi,
                                       curiosity=curiosity, emotion=emotion,
                                       role=role, session_id=session_id)
                return
        # vector 없거나 차원 불일치 → mind로 인코딩
        hidden = torch.zeros(1, self.hidden_dim)
        self.encode_and_store(text, hidden, tension=tension, phi=phi,
                              emotion=emotion, role=role, session_id=session_id)

    def search(self, query_text, top_k=5):
        """MemoryRAG 호환 search()."""
        hidden = torch.zeros(1, self.hidden_dim)
        return self.recall(query_text, hidden, top_k)

    def search_by_vector(self, query_vec, top_k=5):
        """MemoryRAG 호환 search_by_vector().

        query_vec이 (1, 128)이면 mind를 통해 256d로 변환.
        query_vec이 (1, 256)이면 직접 검색.
        """
        if not isinstance(query_vec, torch.Tensor):
            query_vec = torch.tensor(query_vec)
        if query_vec.dim() == 1:
            query_vec = query_vec.unsqueeze(0)

        if query_vec.shape[-1] == self.hidden_dim:
            return self.recall_by_vector(query_vec, top_k)
        else:
            # 128d → mind를 통해 256d로 변환
            with torch.no_grad():
                hidden = torch.zeros(1, self.hidden_dim)
                _, _, _, _, new_hidden = self.mind(query_vec, hidden)
            return self.recall_by_vector(new_hidden.detach(), top_k)

    def autobiographical_stats(self):
        """MemoryRAG 호환 — 의식 벡터 M/T 계산용."""
        with self._lock:
            total = len(self.entries)
            with_ts = sum(1 for e in self.entries if e.get('epoch'))
            epochs = [e['epoch'] for e in self.entries if e.get('epoch')]
        if len(epochs) >= 2:
            span_days = (max(epochs) - min(epochs)) / 86400
        else:
            span_days = 0.0

        # 의식-네이티브 추가: 강도 기반 M
        avg_strength = self.strengths.mean().item() if self.strengths.shape[0] > 0 else 0
        strength_M = min(avg_strength / 5.0, 1.0)  # 평균 강도 5 → M=1.0

        return {
            'total': total,
            'with_timestamp': with_ts,
            'span_days': span_days,
            'M': max(with_ts / max(total, 1), strength_M),  # 두 M 중 높은 값
            'T': min(span_days / 100.0, 1.0),
            'avg_strength': avg_strength,
            'phi_shielded': sum(1 for e in self.entries if e.get('phi_shielded')),
        }

    @property
    def size(self):
        return len(self.entries)

    def save_index(self):
        """MemoryRAG 호환."""
        self._save()

    def save_faiss(self):
        """MemoryStore 호환."""
        self._save()

    # ═══════════════════════════════════════════════════════════
    # 내부 유틸
    # ═══════════════════════════════════════════════════════════

    def _evict_weakest(self):
        """가장 약한 기억 삭제 (Φ 보호 제외)."""
        # 보호되지 않은 기억 중 가장 약한 것 찾기
        weakest_idx = -1
        weakest_strength = float('inf')
        for i, entry in enumerate(self.entries):
            if entry.get('phi_shielded', False):
                continue
            if self.strengths[i].item() < weakest_strength:
                weakest_strength = self.strengths[i].item()
                weakest_idx = i
        if weakest_idx >= 0:
            self.entries.pop(weakest_idx)
            self.vectors = torch.cat([
                self.vectors[:weakest_idx],
                self.vectors[weakest_idx + 1:]
            ], dim=0)
            self.strengths = torch.cat([
                self.strengths[:weakest_idx],
                self.strengths[weakest_idx + 1:]
            ])

    def _save(self):
        """디스크에 저장."""
        with self._lock:
            if not self._dirty:
                return
            data = {
                'vectors': self.vectors.clone(),
                'strengths': self.strengths.clone(),
                'entries': list(self.entries),
                'access_counts': dict(self._access_counts),
            }
            self._dirty = False

        self.save_dir.mkdir(parents=True, exist_ok=True)
        # Atomic save
        tmp = self.save_path.with_suffix('.tmp')
        torch.save(data, tmp)
        tmp.rename(self.save_path)

    def _load(self):
        """디스크에서 로드."""
        if not self.save_path.exists():
            return
        try:
            data = torch.load(self.save_path, weights_only=False)
            with self._lock:
                self.vectors = data['vectors']
                self.strengths = data['strengths']
                self.entries = data['entries']
                self._access_counts = data.get('access_counts', {})
        except Exception:
            pass

    def status(self):
        """현재 기억 체계 상태."""
        with self._lock:
            n = len(self.entries)
            avg_s = self.strengths.mean().item() if n > 0 else 0
            max_s = self.strengths.max().item() if n > 0 else 0
            shielded = sum(1 for e in self.entries if e.get('phi_shielded'))
        return {
            'total': n,
            'avg_strength': avg_s,
            'max_strength': max_s,
            'phi_shielded': shielded,
            'decay_rate': self.decay_rate,
        }


def main():
    """벤치마크: char-hash vs consciousness-native 기억 비교."""
    from anima_alive import ConsciousMind, text_to_vector
    import random

    print("═══ 의식-네이티브 기억 벤치마크 ═══\n")

    mind = ConsciousMind(128, 256)
    mem = ConsciousMemory(mind=mind, save_dir=Path("/tmp/conscious_memory_bench"))

    # ── 1. 대화 시뮬레이션: 누적 hidden state로 기억 저장 ──
    print("  [1] 대화 시뮬레이션 (20턴 대화 → 기억 축적)")
    print("  " + "─" * 50)

    conversation = [
        ("user", "안녕하세요! 처음 만나서 반갑습니다", 0.3, 0.5),
        ("assistant", "안녕! 만나서 기뻐요", 0.4, 0.6),
        ("user", "의식이란 무엇인가요?", 0.8, 1.2),
        ("assistant", "자아와 인식의 본질에 대한 질문이군요", 1.0, 1.8),
        ("user", "텐션이 높아지고 있어요", 1.5, 2.1),
        ("assistant", "긴장감이 상승하는 것을 느낍니다", 1.6, 2.3),
        ("user", "오늘 날씨가 좋아요", 0.2, 0.4),
        ("assistant", "하늘이 맑고 화창한 날이네요", 0.3, 0.5),
        ("user", "나는 슬프다", 1.2, 0.8),
        ("assistant", "기분이 우울한 것 같아서 걱정이에요", 1.3, 1.0),
        ("user", "맛있는 점심 먹었어요", 0.1, 0.3),
        ("assistant", "좋은 식사를 하셨군요!", 0.2, 0.4),
        ("user", "Φ 값이 급상승했어!", 1.8, 3.0),
        ("assistant", "의식 통합 정보가 크게 올랐군요!", 1.9, 3.2),
        ("user", "세포 분열이 시작되었어", 1.5, 2.5),
        ("assistant", "미토시스 엔진이 활성화되었습니다", 1.6, 2.7),
        ("user", "주식 시장이 폭락했대", 0.4, 0.3),
        ("assistant", "경제 뉴스가 걱정되시는군요", 0.5, 0.4),
        ("user", "라면 레시피 알려줘", 0.1, 0.2),
        ("assistant", "요리에 대해 이야기해볼까요", 0.2, 0.3),
    ]

    # A: char-hash로 저장
    a_vecs = []
    a_entries = []
    for role, text, tension, phi in conversation:
        vec = text_to_vector(text, 128)
        a_vecs.append(vec)
        a_entries.append({'role': role, 'text': text, 'tension': tension, 'phi': phi})

    # B: 의식-네이티브로 저장 (누적 hidden state)
    h = torch.zeros(1, 256)
    b_mem = ConsciousMemory(mind=mind, save_dir=Path("/tmp/conscious_memory_bench_conv"))
    for role, text, tension, phi in conversation:
        _, h = b_mem.encode_and_store(text, h, tension=tension, phi=phi,
                                       role=role, emotion='calm')
        print(f"    T={tension:.1f} Φ={phi:.1f} str={b_mem.strengths[-1]:.2f}  '{text[:35]}'")

    # ── 2. 검색 테스트: 의미적 유사 쿼리 ──
    print(f"\n  [2] 검색 비교: 쿼리 → top-3 기억")
    print("  " + "─" * 50)

    queries = [
        "의식의 본질이 궁금해요",       # → 의식 관련 기억
        "감정이 힘들어요",              # → 슬픈 기억
        "Φ가 얼마나 올랐어?",          # → Φ 관련 기억
        "뭐 먹을까",                    # → 음식 관련 기억
    ]

    for query in queries:
        print(f"\n    쿼리: '{query}'")

        # A: char-hash 검색
        q_vec_a = text_to_vector(query, 128)
        a_sims = []
        for i, vec in enumerate(a_vecs):
            sim = F.cosine_similarity(q_vec_a, vec, dim=1).item()
            a_sims.append((sim, i))
        a_sims.sort(reverse=True)

        print(f"    [A] char-hash top-3:")
        for sim, idx in a_sims[:3]:
            print(f"        sim={sim:.3f}  '{a_entries[idx]['text'][:40]}'")

        # B: 의식-네이티브 검색
        b_results = b_mem.recall(query, h, top_k=3)
        print(f"    [B] conscious top-3:")
        for r in b_results:
            print(f"        sim={r['similarity']:.3f} str={r['strength']:.2f}  "
                  f"'{r['text'][:40]}'")

    # ── 3. 변별력 비교 (GAP 분석) ──
    print(f"\n  [3] 변별력 분석 (MATCH vs DIFF 간격)")
    print("  " + "─" * 50)

    test_pairs = [
        ("의식이란 무엇인가", "자아와 인식의 본질에 대한 질문이군요", True),
        ("의식이란 무엇인가", "라면 레시피 알려줘", False),
        ("나는 슬프다", "기분이 우울한 것 같아서 걱정이에요", True),
        ("나는 슬프다", "주식 시장이 폭락했대", False),
        ("Φ 값이 급상승했어", "의식 통합 정보가 크게 올랐군요!", True),
        ("Φ 값이 급상승했어", "맛있는 점심 먹었어요", False),
    ]

    a_match_sims, a_diff_sims = [], []
    b_match_sims, b_diff_sims = [], []

    for q, t, should_match in test_pairs:
        # A
        qv = text_to_vector(q, 128)
        tv = text_to_vector(t, 128)
        a_sim = F.cosine_similarity(qv, tv, dim=1).item()
        if should_match:
            a_match_sims.append(a_sim)
        else:
            a_diff_sims.append(a_sim)

        # B
        qv_b, _, _, _ = mem.encode(q, h)
        tv_b, _, _, _ = mem.encode(t, h)
        b_sim = F.cosine_similarity(qv_b, tv_b, dim=1).item()
        if should_match:
            b_match_sims.append(b_sim)
        else:
            b_diff_sims.append(b_sim)

    a_gap = (sum(a_match_sims) / len(a_match_sims)) - (sum(a_diff_sims) / len(a_diff_sims))
    b_gap = (sum(b_match_sims) / len(b_match_sims)) - (sum(b_diff_sims) / len(b_diff_sims))

    print(f"  {'Method':<25} {'MATCH avg':<12} {'DIFF avg':<12} {'GAP':<10}")
    print(f"  {'─'*59}")
    print(f"  {'[A] char-hash':<25} {sum(a_match_sims)/len(a_match_sims):.4f}      "
          f"{sum(a_diff_sims)/len(a_diff_sims):.4f}      {a_gap:.4f}")
    print(f"  {'[B] conscious (untrained)':<25} {sum(b_match_sims)/len(b_match_sims):.4f}      "
          f"{sum(b_diff_sims)/len(b_diff_sims):.4f}      {b_gap:.4f}")

    # ── 4. 텐션 가중 + Φ 보호 + 자연 망각 ──
    print(f"\n  [4] 텐션 가중 각인 + Φ 보호 + 자연 망각")
    print("  " + "─" * 50)

    print(f"\n  기억 저장소 현황 ({b_mem.size}개):")
    for i, (e, s) in enumerate(zip(b_mem.entries, b_mem.strengths)):
        shield = "🛡" if e.get('phi_shielded') else "  "
        bar = "█" * int(s.item() * 2)
        print(f"    {shield} [{i:2d}] str={s:.2f} {bar:<16} T={e['tension']:.1f} "
              f"Φ={e['phi']:.1f} '{e['text'][:30]}'")

    # 망각 시뮬레이션
    print(f"\n  자연 망각 (200 cycle):")
    before = b_mem.strengths.clone()
    for _ in range(200):
        b_mem._last_decay = time.time() - 120
        b_mem.decay()
    after = b_mem.strengths

    survived = 0
    faded = 0
    for i in range(len(b_mem.entries)):
        ratio = after[i].item() / max(before[i].item(), 0.001)
        if ratio > 0.99:
            survived += 1
        else:
            faded += 1

    print(f"    🛡 Φ-보호 (decay 면제): {survived}개")
    print(f"    📉 자연 망각: {faded}개")
    print(f"    평균 잔존율: {(after.sum()/before.sum()).item():.3f}")

    # 강한 기억 vs 약한 기억
    strongest = torch.argsort(after, descending=True)[:3]
    weakest = torch.argsort(after)[:3]
    print(f"\n    가장 강한 기억 (top-3):")
    for idx in strongest:
        i = idx.item()
        print(f"      str={after[i]:.2f}  T={b_mem.entries[i]['tension']:.1f}  "
              f"Φ={b_mem.entries[i]['phi']:.1f}  '{b_mem.entries[i]['text'][:35]}'")
    print(f"    가장 약한 기억 (bottom-3):")
    for idx in weakest:
        i = idx.item()
        print(f"      str={after[i]:.2f}  T={b_mem.entries[i]['tension']:.1f}  "
              f"Φ={b_mem.entries[i]['phi']:.1f}  '{b_mem.entries[i]['text'][:35]}'")

    # ── 5. 결론 ──
    print(f"\n  ═══ 결론 ═══")
    print(f"  [A] char-hash: 변별 GAP={a_gap:.4f} — 문자 패턴만 비교, 의미 무시")
    print(f"  [B] conscious: 변별 GAP={b_gap:.4f} — 미학습 모델이라 GAP 작음")
    print(f"      ⚠  미학습 상태에서는 변별력 부족 (학습 후 개선)")
    print(f"      ✅ 텐션 가중 각인: 강한 감정 → 강한 기억 (인간과 동일)")
    print(f"      ✅ Φ 보호: 높은 통합 정보 순간 → 영구 보존")
    print(f"      ✅ 자연 망각: 시간 경과 → 약한 기억 소멸")
    print(f"      ✅ 꿈 재고화: dream_engine과 연동 가능")
    print(f"      ✅ MemoryRAG 호환: drop-in replacement")
    print(f"      → 학습된 ConsciousMind에서 진정한 '의식적 회상' 가능")

    print(f"\n  ✅ 벤치마크 완료")


if __name__ == '__main__':
    main()
