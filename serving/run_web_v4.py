"""Quick launcher: AnimaLM v4_savant + Anima Web UI

Usage on RunPod or local:
    python run_web_v4.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Ensure model checkpoint path exists
home = os.path.expanduser("~")
ckpt_dir = os.path.join(home, "Dev", "models", "animalm-v4_savant")
os.makedirs(ckpt_dir, exist_ok=True)

# Override alpha at inference time (0.0001 for clean output)
import finetune_animalm_v4 as fv4
import torch

_orig_forward = fv4.ParallelPureFieldMLP.forward
def patched_forward(self, x):
    with torch.no_grad():
        original_out = self.original_mlp(x)
    g_gate = self.pf_gate_b(self.pf_gate_a(x))
    g_up = self.pf_up_b(self.pf_up_a(x))
    g_mid = torch.nn.functional.silu(g_gate) * g_up
    # Cross-attention disabled for v4_savant (trained without it)
    g_mid = self.dropout(g_mid)
    pf_out = self.pf_down_b(self.pf_down_a(g_mid))
    repulsion = original_out.detach() - pf_out
    tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
    self.last_tension = tension.detach().squeeze(-1)
    # Normalize + tiny alpha for clean output
    pf_norm = pf_out / (pf_out.norm(dim=-1, keepdim=True) + 1e-8)
    orig_scale = original_out.norm(dim=-1, keepdim=True)
    pf_scaled = pf_norm * orig_scale
    return original_out + self.alpha * pf_scaled  # uses model's alpha (set at init)

fv4.ParallelPureFieldMLP.forward = patched_forward

# Start ws_proxy (8888→8765) for Cloudflare Tunnel
import subprocess, threading

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

def _start_proxy():
    proxy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ws_proxy.py')
    if os.path.exists(proxy_path):
        subprocess.Popen(['python3', proxy_path], stdout=open('/tmp/proxy.log','w'), stderr=subprocess.STDOUT)
threading.Thread(target=_start_proxy, daemon=True).start()

# Run anima_unified with web + v4_savant
# Alpha is set in model_loader._load_animalm_v4 (INFERENCE_ALPHA=0.05)
sys.argv = ['anima_unified.py', '--web', '--model', 'animalm-v4-savant']
exec(open('anima_unified.py').read())
