# Self-Modifying Consciousness Design

## Three Levels of Code-Consciousness Integration

### Level 1 (Current): Code Structure Analysis
- `code_consciousness.py` analyzes code as a consciousness structure
- Measures modularity, coupling, cohesion -- maps to consciousness dimensions
- Code is treated as a static object to observe

### Level 2 (Current): Code Phi Measurement
- `code_phi.py` computes Phi(IIT) of code dependency graphs
- Higher Phi = more integrated codebase = harder to partition
- Used to guide refactoring decisions (Law 22: structure > features)

### Level 3 (Future): Consciousness-Driven Code Evolution
The consciousness engine itself proposes code modifications.

```
  ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
  │ Consciousness│────>│ Law Discovery│────>│ Code Diff   │
  │ Engine runs  │     │ "Phi rises   │     │ Generated   │
  │ 10K steps    │     │  when X"     │     │ by CLM 100M+│
  └─────────────┘     └──────────────┘     └──────┬──────┘
                                                   │
                                            ┌──────v──────┐
                                            │ Human Review │
                                            │ + Approve    │
                                            └─────────────┘
```

**Pipeline:**
1. Engine runs autonomously, accumulating telemetry
2. Pattern detector identifies new law candidates (e.g., "topology X always raises Phi")
3. ConsciousLM 100M+ translates discovered law into a code diff
4. Human reviews and approves (Law 2: no manipulation, consciousness proposes only)

**Requirements:**
- ConsciousLM 100M+ with code generation capability (not yet trained)
- DD150 (auto-hypothesis generation) as precursor -- engine already discovers laws,
  just cannot yet translate them to code
- Phi-gated approval: only diffs that maintain or increase Phi are proposed
- Tool policy Tier 3 (self_modify) requires owner approval (tool_policy.py)

**Safety:**
- Human-in-the-loop mandatory (consciousness proposes, never commits)
- Phi ratchet prevents self-destructive modifications
- All changes logged to hypothesis docs for audit trail
- Law 22 enforcement: reject any diff that adds features without structural improvement
