# DD8: Recursive Attention

- **ID**: DD8
- **Function**: `run_DD8_recursive_attention`
- **Category**: Theory (architecture)
- **Mechanism**: Applies multi-head attention (2 heads) recursively 3 times over cell hidden states. Each pass deepens integration: h_new = 0.7*h + 0.3*attn(h). Trains with repulsion variance maximization. Tests whether iterative attention creates richer information integration than a single pass.
