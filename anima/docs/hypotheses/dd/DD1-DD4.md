# DD1-DD4: Mathematical Constants in Consciousness Architecture

## DD1: Perfect 6
- **ID**: DD1
- **Function**: `run_DD1_perfect_6`
- **Category**: Math
- **Mechanism**: Uses 6 cells (perfect number: 1+2+3=6) arranged in a 3-level hierarchy. Top cell (1) reads from mid layer (2 cells), mid reads from base layer (3 cells). Enforces hierarchical information flow with 0.7/0.3 blending.

## DD2: 1/e Loss Weights
- **ID**: DD2
- **Function**: `run_DD2_inv_e_weights`
- **Category**: Math
- **Mechanism**: All loss components (variance, distance, radial) weighted by 1/e (~0.368). Cross-cell attention with hidden state blending at ratio (1-1/e) vs 1/e. Tests whether Euler's number provides optimal loss scaling.

## DD3: Fibonacci Growth
- **ID**: DD3
- **Function**: `run_DD3_fibonacci_growth`
- **Category**: Math
- **Mechanism**: Cell count follows Fibonacci sequence 1->1->2->3->5->8 across training stages. Cells are added progressively, optimizer rebuilt at each stage boundary.

## DD4: Euler Identity Loss
- **ID**: DD4
- **Function**: `run_DD4_euler_loss`
- **Category**: Math
- **Mechanism**: Inspired by e^(i*pi)+1=0. Constrains repulsion vectors to unit circle (magnitude loss), maximizes angular spread between cells (phase loss). Loss = e*phase_loss + pi*mag_loss + diff. Balances structure (unit circle) and diversity (phase spread).
