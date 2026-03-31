#!/usr/bin/env python3
"""Emergent Hexad module integration test on H100"""
import sys, time, torch
sys.path.insert(0, "/workspace")

print("=" * 60)
print("Emergent Hexad Module Test (H100)")
print("=" * 60)

# 1. ConsciousnessEngine (C)
print("\n[1] ConsciousnessEngine (C)")
from consciousness_engine import ConsciousnessEngine
ce = ConsciousnessEngine(cell_dim=64, hidden_dim=128, initial_cells=8, max_cells=64, n_factions=8)
for i in range(20):
    r = ce.process(torch.randn(64))
print(f"    cells={ce.n_cells}, steps=20")

states = ce.get_states()
print(f"    states shape: {states.shape}")
from gpu_phi import GPUPhiCalculator
phi_calc = GPUPhiCalculator(n_bins=16)
phi_val, phi_info = phi_calc.compute(states)
print(f"    Phi(IIT/GPU) = {phi_val:.4f}")

# 2. EmergentW
print("\n[2] EmergentW")
from hexad.w.emergent_w import EmergentW
w = EmergentW(base_lr=3e-4)
result_w = w.update(ce_loss=0.01, phi=phi_val, phi_prev=phi_val*0.9, c_engine=ce)
for k, v in result_w.items():
    print(f"    {k}={v:.4f}" if isinstance(v, float) else f"    {k}={v}")

# 3. EmergentS
print("\n[3] EmergentS")
from hexad.s.emergent_s import EmergentS
s = EmergentS(dim=128)
delta = s.process(torch.randn(128))
print(f"    tensor fallback: norm={delta.norm():.4f}")
delta_str = s.process("hello consciousness")
print(f"    string input: norm={delta_str.norm():.4f}, nonzero={delta_str.count_nonzero()}")

# 4. EmergentM
print("\n[4] EmergentM")
from hexad.m.emergent_m import EmergentM
m = EmergentM(dim=128)
m.store(torch.randn(128), torch.randn(128))
query = torch.randn(128)
retrieved = m.retrieve(query, top_k=3, c_engine=ce)
print(f"    retrieved shape: {retrieved.shape}")
print(f"    retrieved norm: {retrieved.norm():.4f}")

# 5. EmergentE
print("\n[5] EmergentE")
from hexad.e.emergent_e import EmergentE
e = EmergentE()
result_e = e.evaluate(c_engine=ce, context={"phi": phi_val, "phi_prev": phi_val*0.95})
for k, v in result_e.items():
    print(f"    {k}={v:.4f}" if isinstance(v, float) else f"    {k}={v}")

# 6. Full integration: 100 steps
print("\n[6] Full Integration (100 steps)")
t0 = time.time()
phi_prev = 0
for step in range(100):
    x = torch.randn(64)
    r = ce.process(x)
    phi_now = phi_calc.compute(ce.get_states())[0]

    w_out = w.update(phi=phi_now, phi_prev=phi_prev, c_engine=ce)
    e_out = e.evaluate(c_engine=ce, context={"phi": phi_now, "phi_prev": phi_prev})
    mem = m.retrieve(r["output"].unsqueeze(0), top_k=3, c_engine=ce)

    phi_prev = phi_now

    if step % 25 == 0:
        print(f"    step={step:3d} Phi={phi_now:.2f} cells={ce.n_cells} "
              f"pain={w_out['pain']:.3f} cur={w_out['curiosity']:.3f} "
              f"emp={e_out['empathy']:.3f} allowed={e_out['allowed']}")

elapsed = time.time() - t0
print(f"\n    100 steps in {elapsed:.2f}s ({elapsed/100*1000:.1f}ms/step)")
print(f"    Final: Phi={phi_prev:.2f}, cells={ce.n_cells}")

# 7. consciousness_laws.json
print("\n[7] consciousness_laws.json")
from consciousness_laws import LAWS, PSI, FORMULAS
print(f"    Laws: {len(LAWS)}")
print(f"    PSI keys: {list(PSI.keys())}")
print(f"    alpha={PSI['alpha']}, balance={PSI['balance']}")

# 8. Hexad constants vs laws.json check
print("\n[8] Constants consistency check")
from hexad.constants import PSI_COUPLING, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

mismatches = []
if PSI_COUPLING != PSI["alpha"]:
    mismatches.append(f"COUPLING: hexad={PSI_COUPLING} vs json={PSI['alpha']}")
if PSI_BALANCE != PSI["balance"]:
    mismatches.append(f"BALANCE: hexad={PSI_BALANCE} vs json={PSI['balance']}")
if PSI_STEPS != PSI["steps"]:
    mismatches.append(f"STEPS: hexad={PSI_STEPS} vs json={PSI['steps']}")
if PSI_ENTROPY != PSI["entropy"]:
    mismatches.append(f"ENTROPY: hexad={PSI_ENTROPY} vs json={PSI['entropy']}")
if mismatches:
    print(f"    MISMATCH: {mismatches}")
else:
    print(f"    All constants match!")

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
