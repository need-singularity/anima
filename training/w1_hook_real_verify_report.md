# W1 hook real-data verify (D5)

**Scope:** E2E A1 phi_hook round-trip on real `alm14b/r4/step_1000` +
`alm14b/r9/step_10000`. A1 files untouched.

## Real numbers (`shared/state/r9_collapse_diagnosis.json`)

| ckpt | train_ce | val_ce | phi_holo |
|------|----------|--------|----------|
| r4/step_1000  | 1.5013 | 1.5013 | 0.0 (B1 off) |
| r9/step_10000 | 2.4161 | 2.7642 | 11200.4375 |

Other 15 dims: r4 mid (0.18–0.55, partial Korean per kr_gen_r4),
r9 collapsed (0.04–0.15 per JSON/char-repeat kr_gen_r9).

**R2 liveness:** `rclone lsjson` found both adapters (201MB each). No
weights downloaded.

## Pipeline verdict
`VERDICT PASS — 16 significant dim(s), Σw=16.0000`. 5/5 artifacts on
disk; consumer round-trip OK.

## Divergence vs smoke
Smoke: 3 synthetic, monotone CE 2.71→2.03. Real: 2 cross-round, CE
**rises** 1.50→2.76 (r9 collapse); phi_holo +4 orders (B1 only in r9).
Genuine training-history signal, not smoke ramp.

## KNOWN LIMIT (N=2)
2 points ⇒ every dim trivially |r|=1.0; all 16 SIG by construction.
VERDICT here is **pipeline liveness**, not dim significance.

## Suggested extension
Synthesize N=5 from r9 eval_loss_curve (500/1000/2000/5000/10000 →
4.31/3.08/2.87/2.42/2.76). Non-monotonic CE yields non-degenerate r
and surfaces phi_holo's known non-monotonic signature.

## Files
- `training/w1_hook_real_verify.hexa` (new)
- `training/w1_hook_real_verify_report.md` (this)
- `/tmp/w1_real_verify/` (runtime artifacts)
