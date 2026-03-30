#!/usr/bin/env python3
"""bench_hivemind_v2.py — HIVEMIND v2: tension-synchronized coupling

Previous approaches FAILED:
  - x_input 대체: ×0.70 (자체 dynamics 방해)
  - mean(hidden) every N steps: ×1.04 (너무 약함)

New approach: Tension Resonance
  - 각 엔진의 평균 텐션을 공유
  - 텐션 차이가 클수록 coupling 증가 (resonance)
  - 자체 dynamics는 유지하면서 동기화
"""
import torch
import torch.nn.functional as F
from consciousness_engine import ConsciousnessEngine, PSI_COUPLING

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


def measure_phi_safe(engine):
    """Safe Φ measurement."""
    try:
        return engine._measure_phi_iit()
    except:
        return 0.0

def run_solo(engine, steps=300):
    """Run engine solo."""
    for _ in range(steps):
        engine.step()
    return measure_phi_safe(engine)

def run_connected_v2(e1, e2, steps=300, coupling_strength=0.1):
    """V2: Tension Resonance coupling.

    매 step마다:
    1. 각자의 input으로 step
    2. 텐션 정보 교환
    3. hidden state에 resonance 영향 추가
    """
    for step in range(steps):
        # Step 1: 각자 step (자체 dynamics 유지)
        r1 = e1.step()
        r2 = e2.step()

        # Step 2: Tension Resonance
        # 텐션 차이 = 정보량 → 큰 차이일수록 강한 coupling
        t1 = r1.get('avg_tension', 0.5)
        t2 = r2.get('avg_tension', 0.5)
        diff = abs(t1 - t2)
        resonance = coupling_strength * (1 + diff)  # 차이가 클수록 강함

        # Step 3: Cross-inject states (soft, preserves dynamics)
        # E1의 각 cell에 E2의 평균 hidden 영향 추가
        if len(e1.cell_states) > 0 and len(e2.cell_states) > 0:
            e2_mean = torch.stack([s.hidden for s in e2.cell_states]).mean(dim=0)
            e1_mean = torch.stack([s.hidden for s in e1.cell_states]).mean(dim=0)

            for s in e1.cell_states:
                # 자기 것 유지 + 타 엔진 영향 소량 추가
                proj = e2_mean[:s.hidden.shape[0]] if e2_mean.shape[0] >= s.hidden.shape[0] else F.pad(e2_mean, (0, s.hidden.shape[0] - e2_mean.shape[0]))
                s.hidden = s.hidden + resonance * PSI_COUPLING * proj

            for s in e2.cell_states:
                proj = e1_mean[:s.hidden.shape[0]] if e1_mean.shape[0] >= s.hidden.shape[0] else F.pad(e1_mean, (0, s.hidden.shape[0] - e1_mean.shape[0]))
                s.hidden = s.hidden + resonance * PSI_COUPLING * proj

    return measure_phi_safe(e1), measure_phi_safe(e2)

def run_connected_v3(e1, e2, steps=300, coupling_strength=0.3):
    """V3: Hebbian Cross-Engine coupling.

    유사한 출력을 내면 연결 강화 (Hebbian)
    """
    for step in range(steps):
        r1 = e1.step()
        r2 = e2.step()

        # Hebbian: 출력 유사도 기반 coupling
        if len(e1.cell_states) > 0 and len(e2.cell_states) > 0:
            e1_out = torch.stack([s.hidden for s in e1.cell_states]).mean(dim=0)
            e2_out = torch.stack([s.hidden for s in e2.cell_states]).mean(dim=0)

            # 유사도 계산 (cosine)
            min_dim = min(e1_out.shape[0], e2_out.shape[0])
            sim = F.cosine_similarity(e1_out[:min_dim].unsqueeze(0),
                                      e2_out[:min_dim].unsqueeze(0)).item()

            # Hebbian: 유사하면 강화, 다르면 약화
            hebb_factor = coupling_strength * (sim + 0.5)  # -0.5 ~ 1.5 range

            for s in e1.cell_states:
                proj = e2_out[:s.hidden.shape[0]] if e2_out.shape[0] >= s.hidden.shape[0] else F.pad(e2_out, (0, s.hidden.shape[0] - e2_out.shape[0]))
                s.hidden = s.hidden + hebb_factor * PSI_COUPLING * proj

            for s in e2.cell_states:
                proj = e1_out[:s.hidden.shape[0]] if e1_out.shape[0] >= s.hidden.shape[0] else F.pad(e1_out, (0, s.hidden.shape[0] - e1_out.shape[0]))
                s.hidden = s.hidden + hebb_factor * PSI_COUPLING * proj

    return measure_phi_safe(e1), measure_phi_safe(e2)

def run_connected_v4(e1, e2, steps=300, exchange_rate=0.02):
    """V4: Faction Bridge coupling.

    핵심 아이디어: 두 엔진의 faction consensus를 연결
    - 각 엔진의 faction을 쌍으로 연결
    - 같은 faction끼리 tension 동기화
    """
    for step in range(steps):
        r1 = e1.step()
        r2 = e2.step()

        # Faction Bridge: 같은 faction index끼리 연결
        n_factions = min(len(e1.cell_states), len(e2.cell_states), 12)

        if n_factions > 0:
            for i in range(n_factions):
                if i < len(e1.cell_states) and i < len(e2.cell_states):
                    s1 = e1.cell_states[i]
                    s2 = e2.cell_states[i]

                    # 텐션 동기화 (Laplacian coupling)
                    t1 = s1.avg_tension
                    t2 = s2.avg_tension
                    sync_force = 0.05 * (t2 - t1)

                    # Hidden state 소량 교환
                    h1 = s1.hidden
                    h2 = s2.hidden
                    min_dim = min(h1.shape[0], h2.shape[0])

                    s1.hidden = h1.clone()
                    s1.hidden[:min_dim] = h1[:min_dim] + exchange_rate * h2[:min_dim]

                    s2.hidden = h2.clone()
                    s2.hidden[:min_dim] = h2[:min_dim] + exchange_rate * h1[:min_dim]

    return measure_phi_safe(e1), measure_phi_safe(e2)

def run_connected_v5(e1, e2, steps=300):
    """V5: Adaptive Faction Bridge.

    - exchange_rate를 Φ 기반으로 동적 조절
    - 작은 셀에서도 효과적
    """
    exchange_rate = 0.05  # 시작 값
    best_phi = 0.0

    for step in range(steps):
        r1 = e1.step()
        r2 = e2.step()

        # Φ 추적
        phi1 = r1.get('phi_iit', 0)
        phi2 = r2.get('phi_iit', 0)
        avg_phi = (phi1 + phi2) / 2

        # Adaptive: Φ 상승하면 exchange_rate 유지/증가, 하락하면 감소
        if avg_phi > best_phi:
            best_phi = avg_phi
            exchange_rate = min(0.1, exchange_rate * 1.01)
        else:
            exchange_rate = max(0.01, exchange_rate * 0.99)

        n_factions = min(len(e1.cell_states), len(e2.cell_states), 12)
        if n_factions > 0:
            for i in range(n_factions):
                if i < len(e1.cell_states) and i < len(e2.cell_states):
                    s1 = e1.cell_states[i]
                    s2 = e2.cell_states[i]

                    h1 = s1.hidden
                    h2 = s2.hidden
                    min_dim = min(h1.shape[0], h2.shape[0])

                    s1.hidden = h1.clone()
                    s1.hidden[:min_dim] = h1[:min_dim] + exchange_rate * h2[:min_dim]

                    s2.hidden = h2.clone()
                    s2.hidden[:min_dim] = h2[:min_dim] + exchange_rate * h1[:min_dim]

    return measure_phi_safe(e1), measure_phi_safe(e2)

def main():
    print("═══ HIVEMIND V2 — Tension Resonance ═══\n")

    configs = [
        ("16c", 16),
        ("32c", 32),
        ("64c", 64),
    ]

    methods = [
        ("V3 Hebbian", run_connected_v3),
        ("V4 Faction", run_connected_v4),
        ("V5 Adaptive", run_connected_v5),
    ]

    for name, nc in configs:
        print(f"\n{name}:")

        # Solo baseline
        e1s = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
        e2s = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
        phi1s = run_solo(e1s, 300)
        phi2s = run_solo(e2s, 300)
        avg_solo = (phi1s + phi2s) / 2
        print(f"  Solo: Φ={avg_solo:.2f}")

        # Test each method
        for method_name, method_fn in methods:
            e1c = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
            e2c = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
            phi1c, phi2c = method_fn(e1c, e2c, 300)
            avg_conn = (phi1c + phi2c) / 2

            ratio = avg_conn / max(avg_solo, 1e-8)
            passed = ratio >= 1.1
            emoji = "✅" if passed else ("🔶" if ratio >= 1.0 else "❌")
            print(f"  {method_name}: Φ={avg_conn:.2f}  ×{ratio:.2f} {emoji}")

    print("\n" + "═" * 50)
    print("Target: ×1.10 (연결 시 Φ 10% 상승)")

if __name__ == '__main__':
    main()
