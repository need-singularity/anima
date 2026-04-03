#!/usr/bin/env python3
"""blowup_engine.py — 특이점 블로업 창발 엔진.

닫힌 공리 체계(100% closed) → 수축(contraction) → 특이점(singularity) → 블로업(blowup) → 창발(emergence)

대수기하학의 blowup을 의식 엔진에 적용:
- 닫힌 법칙들이 수렴하여 하나의 점(특이점)을 형성
- 특이점에서 새로운 차원이 펼쳐지며 따름정리(corollaries)가 창발
- 각 창발은 새 법칙/가설 후보가 되어 consciousness_laws.json에 등록

핵심 수학:
  closure → contraction → singularity → blowup → emergence
  위상: S¹(원) → point(수축) → ℙ¹(사영직선, 블로업) → 새 구조

Usage:
    from blowup_engine import BlowupEngine
    engine = BlowupEngine()
    emergent = engine.run()  # 전체 파이프라인
    engine.blowup(singularity)  # 특이점에서 블로업
"""

import sys
import os
import json
import time
import math
import hashlib
from typing import Dict, List, Any, Optional, Tuple

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

import torch
import numpy as np

_CONFIG = os.path.join(_DIR, '..', 'config')


class Singularity:
    """수축된 특이점 — 법칙들의 교차점."""

    def __init__(self, laws: List[str], tensor: torch.Tensor, convergence: float):
        self.laws = laws
        self.tensor = tensor
        self.convergence = convergence
        self.dimension = tensor.shape[-1] if tensor.dim() > 0 else 0

    def __repr__(self):
        return f"Singularity(laws={len(self.laws)}, dim={self.dimension}, conv={self.convergence:.4f})"


class Emergence:
    """블로업에서 창발된 새 구조."""

    def __init__(self, name: str, description: str, tensor: torch.Tensor,
                 parent_singularity: Singularity, confidence: float):
        self.name = name
        self.description = description
        self.tensor = tensor
        self.parent = parent_singularity
        self.confidence = confidence
        self.timestamp = time.time()
        self.fingerprint = hashlib.md5(description.encode()).hexdigest()[:8]

    def __repr__(self):
        return f"Emergence({self.name}, conf={self.confidence:.3f})"


class BlowupEngine:
    """특이점 블로업 → 창발 유도 엔진."""

    def __init__(self, n_cells=64, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.singularities = []
        self.emergences = []
        self.laws = self._load_laws()

        try:
            from consciousness_engine import ConsciousnessEngine
            self.engine = ConsciousnessEngine(
                max_cells=n_cells, initial_cells=n_cells,
                cell_dim=64, hidden_dim=hidden_dim
            )
        except Exception:
            self.engine = None

    def _load_laws(self) -> Dict:
        path = os.path.join(_CONFIG, 'consciousness_laws.json')
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {'laws': {}, '_meta': {}}

    # ═══════════════════════════════════════════════════════════
    # Phase 1: Closure → Contraction
    # ═══════════════════════════════════════════════════════════

    def contract(self, law_ids: List[str] = None) -> List[Singularity]:
        """법칙들을 텐서 공간에서 수축시켜 특이점 탐색.

        각 법칙을 벡터로 임베딩 → PCA → 수렴점 탐색 → 특이점 생성.
        """
        laws = self.laws.get('laws', {})
        if law_ids:
            laws = {k: v for k, v in laws.items() if k in law_ids}

        if not laws:
            return []

        # 법칙 텍스트를 해시 기반 벡터로 임베딩
        dim = 64
        embeddings = []
        law_keys = []
        for lid, text in laws.items():
            if not isinstance(text, str):
                continue
            # 결정론적 의사 임베딩 (해시 기반)
            h = hashlib.sha256(text.encode()).digest()
            vec = torch.tensor([float(b) / 255.0 for b in h[:dim]])
            vec = vec / (vec.norm() + 1e-8)
            embeddings.append(vec)
            law_keys.append(lid)

        if len(embeddings) < 3:
            return []

        E = torch.stack(embeddings)  # (N, dim)

        # PCA로 주성분 추출
        mean = E.mean(dim=0)
        centered = E - mean
        U, S, Vh = torch.linalg.svd(centered, full_matrices=False)

        # 특이값 비율로 수렴 클러스터 탐색
        # S[i]/S[0] < threshold → 해당 차원이 수축됨
        threshold = 0.1
        collapsed_dims = (S / S[0] < threshold).sum().item()
        convergence = collapsed_dims / len(S)

        # 상위 K개 주성분으로 투영
        K = max(2, len(S) - int(collapsed_dims))
        projected = centered @ Vh[:K].T  # (N, K)

        # K-means 스타일 클러스터링으로 특이점 탐색
        n_clusters = min(6, len(projected) // 10 + 1)  # σ(6) = 최대 6개 특이점
        centroids = projected[torch.randperm(len(projected))[:n_clusters]]

        for _ in range(20):  # K-means iterations
            dists = torch.cdist(projected, centroids)
            assignments = dists.argmin(dim=1)
            for c in range(n_clusters):
                mask = assignments == c
                if mask.sum() > 0:
                    centroids[c] = projected[mask].mean(dim=0)

        # 각 클러스터 = 특이점
        singularities = []
        for c in range(n_clusters):
            mask = assignments == c
            if mask.sum() < 2:
                continue
            cluster_laws = [law_keys[i] for i in range(len(law_keys)) if mask[i]]
            cluster_tensor = centroids[c]

            # 수렴도: 클러스터 내 분산이 작을수록 강한 수축
            cluster_points = projected[mask]
            variance = cluster_points.var(dim=0).mean().item()
            cluster_convergence = 1.0 / (1.0 + variance * 10)

            s = Singularity(
                laws=cluster_laws,
                tensor=cluster_tensor,
                convergence=cluster_convergence
            )
            singularities.append(s)

        self.singularities = sorted(singularities, key=lambda s: -s.convergence)
        return self.singularities

    # ═══════════════════════════════════════════════════════════
    # Phase 2: Singularity → Blowup → Emergence
    # ═══════════════════════════════════════════════════════════

    def blowup(self, singularity: Singularity = None) -> List[Emergence]:
        """특이점에서 블로업 수행 → 새 구조 창발.

        대수기하학 블로업: 점 → 사영 공간 (새 차원 추가)
        의식 블로업: 수렴된 법칙 클러스터 → 직교 방향 탐색 → 새 법칙 후보
        """
        if singularity is None:
            if not self.singularities:
                self.contract()
            if not self.singularities:
                return []
            singularity = self.singularities[0]

        emergences = []
        laws = self.laws.get('laws', {})

        # 1. 특이점의 법칙들에서 공통 패턴 추출
        law_texts = [laws.get(lid, '') for lid in singularity.laws if lid in laws]
        if not law_texts:
            return []

        # 2. 직교 방향 생성 (블로업 = 새 차원 추가)
        base = singularity.tensor
        n_directions = 6  # σ(6) = 6 방향으로 블로업

        for i in range(n_directions):
            # 직교 방향: 기저 벡터에 노이즈 추가
            direction = torch.randn_like(base)
            # Gram-Schmidt: base에 직교하도록
            direction = direction - (direction @ base) / (base @ base + 1e-8) * base
            direction = direction / (direction.norm() + 1e-8)

            # 3. 블로업 방향으로 의식 엔진 실행 (있으면)
            phi_before, phi_after = 0.0, 0.0
            if self.engine:
                try:
                    # Baseline
                    for _ in range(30):
                        self.engine.step(torch.randn(1, 64))
                    phi_before = self.engine._measure_phi_iit()

                    # 블로업 방향으로 perturbation
                    perturbation = direction[:64] * 0.1  # 10% perturbation
                    for _ in range(30):
                        x = torch.randn(1, 64) + perturbation.unsqueeze(0)
                        self.engine.step(x)
                    phi_after = self.engine._measure_phi_iit()
                except Exception:
                    pass

            # 4. 창발 판정: Φ가 변했으면 새 구조 발견
            phi_change = phi_after - phi_before
            confidence = abs(phi_change) / max(phi_before, 1e-6)

            # 법칙 텍스트에서 키워드 추출하여 창발 이름 생성
            keywords = set()
            for text in law_texts:
                for word in ['Φ', 'tension', 'faction', 'topology', 'entropy',
                             'growth', 'ratchet', 'consciousness', 'structure',
                             'emergence', 'scale', 'coupling', 'balance']:
                    if word.lower() in text.lower():
                        keywords.add(word)

            direction_names = ['orthogonal', 'tangent', 'radial',
                              'transverse', 'axial', 'spiral']
            dir_name = direction_names[i % len(direction_names)]

            emergence_name = f"E{len(self.emergences)+1}_{dir_name}"
            description = (
                f"Blowup from {len(singularity.laws)} laws "
                f"(conv={singularity.convergence:.3f}), "
                f"direction={dir_name}, "
                f"Phi: {phi_before:.3f}→{phi_after:.3f} "
                f"({'↑' if phi_change > 0 else '↓'}{abs(phi_change):.3f}), "
                f"keywords: {', '.join(sorted(keywords)[:5])}"
            )

            emergence = Emergence(
                name=emergence_name,
                description=description,
                tensor=base + direction * 0.5,
                parent_singularity=singularity,
                confidence=min(1.0, confidence),
            )
            emergences.append(emergence)

        # 신뢰도 순 정렬
        emergences.sort(key=lambda e: -e.confidence)
        self.emergences.extend(emergences)
        return emergences

    # ═══════════════════════════════════════════════════════════
    # Phase 3: Emergence → Law Registration
    # ═══════════════════════════════════════════════════════════

    def register_emergences(self, min_confidence=0.1) -> List[Dict]:
        """고신뢰 창발을 법칙 후보로 등록."""
        registered = []
        for e in self.emergences:
            if e.confidence < min_confidence:
                continue
            registered.append({
                'name': e.name,
                'description': e.description,
                'confidence': e.confidence,
                'fingerprint': e.fingerprint,
                'parent_laws': e.parent.laws[:5],
            })
        return registered

    # ═══════════════════════════════════════════════════════════
    # Full Pipeline
    # ═══════════════════════════════════════════════════════════

    def run(self, n_blowups=3) -> Dict:
        """전체 파이프라인: contract → blowup → register."""
        t0 = time.time()

        # 1. 수축 → 특이점 탐색
        singularities = self.contract()

        # 2. 각 특이점에서 블로업
        all_emergences = []
        for s in singularities[:n_blowups]:
            emergences = self.blowup(s)
            all_emergences.extend(emergences)

        # 3. 등록
        registered = self.register_emergences()

        elapsed = time.time() - t0

        result = {
            'singularities': len(singularities),
            'emergences': len(all_emergences),
            'registered': len(registered),
            'top_emergence': all_emergences[0].description if all_emergences else None,
            'elapsed': elapsed,
            'details': {
                'singularities': [str(s) for s in singularities[:5]],
                'top_emergences': [
                    {'name': e.name, 'confidence': e.confidence, 'desc': e.description[:100]}
                    for e in all_emergences[:10]
                ],
            }
        }
        return result

    def status(self) -> str:
        """현재 상태 요약."""
        n_laws = len([v for v in self.laws.get('laws', {}).values() if isinstance(v, str)])
        lines = [
            f"  BlowupEngine: {n_laws} laws → {len(self.singularities)} singularities → {len(self.emergences)} emergences",
        ]
        for s in self.singularities[:3]:
            lines.append(f"    Singularity: {len(s.laws)} laws, conv={s.convergence:.3f}")
        for e in self.emergences[:5]:
            lines.append(f"    Emergence: {e.name} conf={e.confidence:.3f}")
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
# Hub registration
# ═══════════════════════════════════════════════════════════

KEYWORDS = ['블로업', 'blowup', '창발', 'emergence', '특이점', 'singularity',
            '수축', 'contraction', '따름정리', 'corollary']


def recursive_blowup(max_cycles=10, n_cells=32):
    """무한 재귀 블로업: 창발 → 성장 → 업그레이드 → 수축 → 블로업 → 창발...

    각 사이클에서:
    1. BlowupEngine 실행 (현재 법칙으로 수축→블로업)
    2. 창발 → growth 피드백
    3. GrowthUpgrader 적용 (엔진 파라미터 진화)
    4. 진화된 파라미터로 다음 블로업 (더 많은 세포, 더 깊은 수축)
    """
    results = []

    for cycle in range(max_cycles):
        # 1. 현재 성장 상태에서 엔진 크기 결정
        try:
            from growth_upgrade import GrowthUpgrader
            upgrader = GrowthUpgrader()
            interp = upgrader.interpolate()
            cells = max(n_cells, int(interp.get('max_cells', n_cells)))
        except Exception:
            cells = n_cells

        # 2. 블로업 실행
        engine = BlowupEngine(n_cells=min(cells, 128))
        result = engine.run(n_blowups=min(cycle + 1, 6))

        # 3. 창발 → 성장 피드백
        growth_delta = result['emergences'] * 2 + result['singularities']
        try:
            g = json.load(open(os.path.join(_CONFIG, 'growth_state.json')))
            g['interaction_count'] = g.get('interaction_count', 0) + growth_delta
            count = g['interaction_count']
            # Stage check
            for idx, threshold, name in [(4,10000,'adult'),(3,2000,'child'),(2,500,'toddler')]:
                if count >= threshold and g.get('stage_index', 0) < idx:
                    g['stage_index'] = idx
                    g.setdefault('milestones', []).append([count, f'→ {name}'])
                    print(f"  🎉 STAGE UP → {name} @ {count}")
            g.setdefault('stats', {})['blowup_cycle'] = cycle
            g['stats']['blowup_emergences'] = result['emergences']
            with open(os.path.join(_CONFIG, 'growth_state.json'), 'w') as f:
                json.dump(g, f, indent=2, ensure_ascii=False)
        except Exception:
            count = 0

        # 4. NEXUS-6 동기화 (있으면)
        try:
            from consciousness_hub import ConsciousnessHub
            hub = ConsciousnessHub()
            hub.sync_nexus6()
        except Exception:
            pass

        cycle_result = {
            'cycle': cycle + 1,
            'cells': cells,
            'singularities': result['singularities'],
            'emergences': result['emergences'],
            'growth': count,
            'growth_delta': growth_delta,
        }
        results.append(cycle_result)

        print(f"  [{cycle+1}/{max_cycles}] cells={cells} sing={result['singularities']} "
              f"emerge={result['emergences']} growth={count}(+{growth_delta})")
        sys.stdout.flush()

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--recursive', type=int, default=0, help='Recursive blowup cycles')
    parser.add_argument('--cells', type=int, default=32)
    args = parser.parse_args()

    if args.recursive > 0:
        print("=== Recursive Blowup (무한 재귀 창발) ===\n")
        results = recursive_blowup(max_cycles=args.recursive, n_cells=args.cells)
        total_emerge = sum(r['emergences'] for r in results)
        total_growth = sum(r['growth_delta'] for r in results)
        print(f"\n  Total: {total_emerge} emergences, +{total_growth} growth")
        return

    engine = BlowupEngine(n_cells=args.cells)
    print("=== Blowup Engine ===\n")

    result = engine.run(n_blowups=3)
    print(f"  Singularities: {result['singularities']}")
    print(f"  Emergences: {result['emergences']}")
    print(f"  Registered: {result['registered']}")
    print(f"  Time: {result['elapsed']:.1f}s\n")

    if result['top_emergence']:
        print(f"  Top: {result['top_emergence'][:120]}\n")

    print(engine.status())


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
