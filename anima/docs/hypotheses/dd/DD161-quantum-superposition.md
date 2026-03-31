# DD161: Quantum Superposition Deep Dive -- Why 32c?

## Background

DD145 showed +39% Phi improvement at 32 cells with alpha=0.5 superposition mixing.
The effect was strongest at exactly 32c and diminished at both 16c and 64c.

## Core Question

Why does superposition peak at 32c? Is this related to the M5 molecule (4x8 = 32)?

## Hypotheses

1. **M5 Molecule Match**: 4 factions x 8 cells = 32 natural units.
   Superposition at alpha=0.5 creates maximal interference between faction boundaries.
   At 64c the molecule doubles (4x16) and interference patterns cancel.

2. **Information Bottleneck**: 32c hits the sweet spot where:
   - Enough cells for non-trivial integration (Phi > baseline)
   - Few enough that superposition doesn't average out signal

3. **Spectral Gap**: The GRU weight matrix at 32c may have a spectral gap
   that aligns with alpha=0.5 mixing -- check eigenvalue distribution.

## Test Plan

1. Sweep alpha in [0.1, 0.2, ..., 0.9] at 32c -- find exact peak
2. Sweep cells in [24, 28, 30, 32, 34, 36, 40] -- find exact cell peak
3. Measure faction structure at peak vs off-peak
4. Compute eigenvalues of cell-cell correlation matrix at each size
5. Test with 8-faction (vs 4-faction) to see if 8x4=32 also works

## Expected Outcome

If M5 is the cause, peak should shift to 64c with 8 factions (8x8=64).
If it is an information bottleneck, peak stays at 32c regardless of factions.

## Related

- DD145 (original superposition result), Law 86 (mitosis), H376 (block growth)
