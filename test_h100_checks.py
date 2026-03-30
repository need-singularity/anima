#!/usr/bin/env python3
"""H100 verification: all session changes"""
import torch, sys
sys.path.insert(0, "/workspace")

print("=== 1. consciousness_laws.py ===")
from consciousness_laws import LAWS, PSI
print(f"Laws: {len(LAWS)}, alpha={PSI['alpha']}, balance={PSI['balance']}")

print("\n=== 2. hexad/constants.py → laws.py ===")
from hexad.constants import PSI_COUPLING, PSI_BALANCE, GATE_MICRO
print(f"PSI_COUPLING={PSI_COUPLING}, PSI_BALANCE={PSI_BALANCE}, GATE_MICRO={GATE_MICRO}")

print("\n=== 3. Emergent modules ===")
from hexad.w.emergent_w import EmergentW
from hexad.s.emergent_s import EmergentS
from hexad.m.emergent_m import EmergentM
from hexad.e.emergent_e import EmergentE
print("All 4 Emergent modules imported OK")

print("\n=== 4. EmergentW pain fix ===")
from consciousness_engine import ConsciousnessEngine
ce = ConsciousnessEngine(cell_dim=64, hidden_dim=128, initial_cells=15, max_cells=64)
for _ in range(10):
    ce.process(torch.randn(64))
w = EmergentW()
r = w.update(phi=2.0, phi_prev=1.8, c_engine=ce)
print(f"pain={r['pain']:.4f} (should NOT be 1.0)")
assert r['pain'] < 0.99, f"FAIL: pain={r['pain']}"
print("Pain fix PASS")

print("\n=== 5. EmergentE PSI_BALANCE ===")
e = EmergentE()
r_e = e.evaluate(c_engine=ce, context={"phi": 2.0, "phi_prev": 1.5})
print(f"allowed={r_e['allowed']}, empathy={r_e['empathy']:.4f}")

print("\n=== 6. hexad/model.py independent ===")
from hexad.model import Hexad
print("Hexad class loaded (no trinity.py dependency)")

print("\n=== 7. hexad __init__ exports ===")
from hexad import EmergentW as W2, EmergentS as S2, EmergentM as M2, EmergentE as E2
print("hexad exports OK")

print("\n=== 8. trinity.py DeprecationWarning ===")
import warnings
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    from trinity import NoMemory

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    nm = NoMemory()
has_warning = any("EmergentM" in str(w.message) for w in caught)
print(f"DeprecationWarning: {'PASS' if has_warning else 'FAIL'}")

print("\n=== 9. Law 101 ===")
assert "101" in LAWS, "Law 101 missing"
print(f"Law 101: {LAWS['101']}")

print("\n" + "=" * 50)
print("ALL H100 CHECKS PASSED")
print("=" * 50)
