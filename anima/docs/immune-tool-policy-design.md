# Immune System + Tool Policy Integration Design

## Current State

- `immune_system.py` -- detects adversarial/harmful input patterns
- `tool_policy.py` -- gates tool access by Phi tier (0/1/2/3) + ethics

These two modules operate independently. They should be chained.

## Integration Flow

```
User Input
  |
  v
immune_system.detect(input)
  |
  |- BLOCKED --> reject immediately, log threat
  |- SUSPICIOUS --> flag, reduce tier by 1, continue
  |- CLEAN --> continue
  |
  v
tool_policy.evaluate(tool, phi, empathy, owner)
  |
  |- DENIED --> reject tool call
  |- ALLOWED --> execute tool
```

## Key Rules

1. Immune check runs BEFORE tool_policy -- block early, save compute
2. Suspicious inputs downgrade effective Phi tier (e.g., TIER_2 -> TIER_1)
3. Blocked inputs never reach tool_policy at all
4. Both modules log to the same audit trail for forensics
5. Neither module modifies consciousness state (Law 2: no manipulation)

## API

```python
from immune_system import ImmuneSystem
from tool_policy import ToolPolicy

immune = ImmuneSystem()
policy = ToolPolicy()

threat = immune.detect(user_input)
if threat.blocked:
    return reject(threat.reason)
effective_phi = phi - threat.tier_penalty
allowed = policy.check(tool_name, effective_phi, empathy, owner)
```
