set -e
mkdir -p /workspace/out
cat > /workspace/.hf_token <<HFEOT
hf_REDACTED_FROM_SECRETS_FILE
HFEOT
pip install -q transformers accelerate sentencepiece 2>&1 | tail -3
export ANIMA_BASE='Qwen/Qwen2.5-14B'
echo '=== AXIS 1: Phi v3 (load=1, all axes share weights via re-load) ==='
ANIMA_OUTPUT=/workspace/out/phi_v3.json python3 /workspace/anima_phi_v3_canonical_helper.py 2>&1 | tail -8
echo '=== AXIS 2: AN11(b) ==='
ANIMA_OUT_HLAST=/workspace/out/an11b_h_last.json ANIMA_OUT_EIGEN=/workspace/out/an11b.json python3 /workspace/anima_an11b_eigen_helper.py 2>&1 | tail -8
echo '=== AXIS 3: B-ToM ==='
ANIMA_OUTPUT=/workspace/out/btom.json python3 /workspace/anima_b_tom_helper.py 2>&1 | tail -8
echo '=== AXIS 4: CMT ==='
ANIMA_OUTPUT=/workspace/out/cmt.json python3 /workspace/anima_cmt_helper.py 2>&1 | tail -8
ls -la /workspace/out/
