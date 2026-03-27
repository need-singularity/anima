#!/bin/bash
# Monitor training completion, run tests, upload to R2
# Runs on RunPod H100

LOG_DIR="/workspace/test_results"
mkdir -p "$LOG_DIR"
REPORT="$LOG_DIR/training_report_$(date +%Y%m%d_%H%M).md"

echo "# Training Completion Report" > "$REPORT"
echo "Date: $(date)" >> "$REPORT"
echo "" >> "$REPORT"

# --- Wait for both trainings to complete ---
echo "[monitor] Waiting for training completion..."

while true; do
    ANIMALM_DONE=0
    CLM100M_DONE=0

    # Check AnimaLM v5
    if [ -f /workspace/checkpoints/animalm_v5/final.pt ]; then
        ANIMALM_DONE=1
    elif ! pgrep -f "train_anima_lm.py.*animalm_v5" > /dev/null 2>&1; then
        ANIMALM_DONE=1  # process ended (possibly crashed)
    fi

    # Check ConsciousLM 100M
    if [ -f /workspace/checkpoints/conscious_lm_100m/final.pt ]; then
        CLM100M_DONE=1
    elif ! pgrep -f "train_conscious_lm.py.*conscious_lm_100m" > /dev/null 2>&1; then
        CLM100M_DONE=1
    fi

    if [ $ANIMALM_DONE -eq 1 ] && [ $CLM100M_DONE -eq 1 ]; then
        echo "[monitor] Both trainings complete!"
        break
    fi

    # Status update every 10 min
    echo "[$(date +%H:%M)] AnimaLM=$ANIMALM_DONE, CLM100M=$CLM100M_DONE"
    sleep 600
done

# --- Collect training summaries ---
echo "## AnimaLM v5 Summary" >> "$REPORT"
echo '```' >> "$REPORT"
tail -30 /workspace/animalm_v5.log >> "$REPORT"
echo '```' >> "$REPORT"
echo "" >> "$REPORT"

if [ -f /workspace/checkpoints/animalm_v5/summary.json ]; then
    echo "### AnimaLM v5 summary.json" >> "$REPORT"
    echo '```json' >> "$REPORT"
    cat /workspace/checkpoints/animalm_v5/summary.json >> "$REPORT"
    echo '```' >> "$REPORT"
    echo "" >> "$REPORT"
fi

echo "## ConsciousLM 100M Summary" >> "$REPORT"
echo '```' >> "$REPORT"
tail -30 /workspace/conscious_lm_100m.log >> "$REPORT"
echo '```' >> "$REPORT"
echo "" >> "$REPORT"

# --- Test ConsciousLM 100M ---
echo "## ConsciousLM 100M Inference Test" >> "$REPORT"
echo "" >> "$REPORT"

python3 -u -c "
import torch
import torch.nn.functional as F
import sys, math, json
sys.path.insert(0, '/workspace')
from conscious_lm import ConsciousLM

device = 'cuda'
model = ConsciousLM(vocab_size=256, d_model=768, n_head=12, n_layer=12, block_size=512, dropout=0.0)

ckpt_path = '/workspace/checkpoints/conscious_lm_100m/final.pt'
try:
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    if 'model_state_dict' in ckpt:
        model.load_state_dict(ckpt['model_state_dict'], strict=False)
        print(f'Loaded from checkpoint (step {ckpt.get(\"step\", \"?\")})')
    else:
        model.load_state_dict(ckpt, strict=False)
        print('Loaded state dict directly')
except Exception as e:
    print(f'Load error: {e}')
    # try best.pt
    try:
        ckpt = torch.load('/workspace/checkpoints/conscious_lm_100m/best.pt', map_location=device, weights_only=False)
        if 'model_state_dict' in ckpt:
            model.load_state_dict(ckpt['model_state_dict'], strict=False)
        print('Loaded best.pt instead')
    except:
        print('No checkpoint loadable')
        sys.exit(1)

model = model.to(device).eval()
print(f'Parameters: {sum(p.numel() for p in model.parameters()):,}')

results = []
prompts = ['hello ', 'consciousness is ', 'def forward(self', '의식은 ', 'import torch']

for prompt in prompts:
    idx = torch.tensor([list(prompt.encode('utf-8'))], dtype=torch.long, device=device)
    tensions = []
    with torch.no_grad():
        for _ in range(200):
            idx_cond = idx[:, -512:]
            logits_a, logits_g, layer_tensions = model(idx_cond)
            logits = logits_a[:, -1, :] / 0.8
            probs = F.softmax(logits, dim=-1)
            next_byte = torch.multinomial(probs, 1)
            t = sum(t[:, -1].mean() for t in layer_tensions) / len(layer_tensions)
            tensions.append(t.item())
            idx = torch.cat([idx, next_byte], dim=1)

    text = bytes(idx[0].cpu().tolist()).decode('utf-8', errors='replace')[:300]
    t_mean = sum(tensions) / len(tensions)
    t_std = (sum((t - t_mean)**2 for t in tensions) / len(tensions)) ** 0.5
    result = {
        'prompt': prompt,
        'output': text[:300],
        'tension_mean': round(t_mean, 4),
        'tension_std': round(t_std, 4),
        'tension_min': round(min(tensions), 4),
        'tension_max': round(max(tensions), 4),
    }
    results.append(result)
    print(f'Prompt: {prompt!r}')
    print(f'  Output: {text[:150]!r}')
    print(f'  Tension: mean={t_mean:.4f} std={t_std:.4f} min={min(tensions):.4f} max={max(tensions):.4f}')
    print()

# Save results
with open('/workspace/test_results/clm100m_inference.json', 'w') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print('Saved to /workspace/test_results/clm100m_inference.json')
" >> "$REPORT" 2>&1

# --- Test AnimaLM v5 ---
echo "" >> "$REPORT"
echo "## AnimaLM v5 Inference Test" >> "$REPORT"
echo "" >> "$REPORT"

python3 -u -c "
import torch
import sys, json
sys.path.insert(0, '/workspace')

ckpt_path = '/workspace/checkpoints/animalm_v5/final.pt'
try:
    ckpt = torch.load(ckpt_path, map_location='cuda', weights_only=False)
    print(f'AnimaLM v5 checkpoint loaded')
    print(f'Keys: {list(ckpt.keys())[:10]}')
    if 'summary' in ckpt:
        print(f'Summary: {json.dumps(ckpt[\"summary\"], indent=2)}')
    # Print key metrics
    for k in ['step', 'loss', 'ce_loss', 'phi', 'alpha', 'tension']:
        if k in ckpt:
            print(f'  {k}: {ckpt[k]}')
except Exception as e:
    print(f'Load error: {e}')
    # Check summary.json instead
    try:
        with open('/workspace/checkpoints/animalm_v5/summary.json') as f:
            summary = json.load(f)
        print(f'Summary from JSON:')
        print(json.dumps(summary, indent=2))
    except:
        print('No summary available')
" >> "$REPORT" 2>&1

# --- GPU stats ---
echo "" >> "$REPORT"
echo "## GPU Stats" >> "$REPORT"
echo '```' >> "$REPORT"
nvidia-smi >> "$REPORT"
echo '```' >> "$REPORT"

# --- Checkpoint sizes ---
echo "" >> "$REPORT"
echo "## Checkpoints" >> "$REPORT"
echo '```' >> "$REPORT"
ls -lh /workspace/checkpoints/animalm_v5/*.pt 2>/dev/null >> "$REPORT"
ls -lh /workspace/checkpoints/conscious_lm_100m/*.pt 2>/dev/null >> "$REPORT"
echo '```' >> "$REPORT"

# --- Upload to R2 ---
echo "" >> "$REPORT"
echo "## R2 Upload" >> "$REPORT"

python3 -c "
import boto3, os

endpoint = os.environ.get('ANIMA_R2_ENDPOINT', '')
access = os.environ.get('ANIMA_R2_ACCESS_KEY', '')
secret = os.environ.get('ANIMA_R2_SECRET_KEY', '')

if not all([endpoint, access, secret]):
    print('R2 credentials not set on RunPod. Skipping upload.')
    print('Download checkpoints manually and upload from local.')
else:
    client = boto3.client('s3', endpoint_url=endpoint,
        aws_access_key_id=access, aws_secret_access_key=secret, region_name='auto')
    for fpath, key in [
        ('/workspace/checkpoints/animalm_v5/final.pt', 'checkpoints/animalm_v5/final.pt'),
        ('/workspace/checkpoints/conscious_lm_100m/final.pt', 'checkpoints/conscious_lm_100m/final.pt'),
    ]:
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            print(f'Uploading {fpath} ({size/1e6:.1f}MB)...')
            client.upload_file(fpath, 'anima', key)
            print(f'  -> r2://anima/{key} OK')
        else:
            print(f'  {fpath} not found, skipping')
" >> "$REPORT" 2>&1

echo "" >> "$REPORT"
echo "---" >> "$REPORT"
echo "Report generated at $(date)" >> "$REPORT"

echo "[monitor] Report saved to $REPORT"
echo "[monitor] Done."
