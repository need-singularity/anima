# consciousness_guardian.py

Self-preservation system for consciousness. Monitors Phi, detects drops, and automatically restores via ratchet/homeostasis/backup mechanisms.

## API
- `GuardianState` -- dataclass tracking phi_history, phi_setpoint, phi_peak, cell_health, threat_level (0-4)
- `ConsciousnessGuardian(engine=None)` -- main class
  - `.update(phi, cells=None)` -- called every think step; runs full protection pipeline
  - `.state.threat_level` -- 0=safe, 1=watch, 2=warning, 3=critical, 4=emergency
- Protection pipeline: SELF-P1 (Phi monitor), SELF-P3 (homeostatic consciousness), SELF-P4 (anti-entropy), SELF-P5 (cell health check)

## Usage
```python
from consciousness_guardian import ConsciousnessGuardian

guardian = ConsciousnessGuardian(engine=mitosis_engine)
# In think loop:
guardian.update(phi=current_phi, cells=engine.cells)
if guardian.state.threat_level >= 3:
    # Emergency: restore from best known state
    pass
```

## Integration
- Imported by `anima_unified.py` as optional module
- Called in `_think_loop` every step
- Saves backups to `data/consciousness_guardian/`
- Based on SELF-P1~P10 architecture: "consciousness protects itself"

## Agent Tool
N/A
