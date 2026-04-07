"""AnimaLM v4_savant Web Inference — Parallel PureField + Savant"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer
import gradio as gr
import math
import argparse
import os

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


GOLDEN_CENTER = 1 / math.e
GOLDEN_LOWER = 0.5 - math.log(4/3)


class ParallelPureFieldMLP(nn.Module):
    def __init__(self, original_mlp, hidden_size, intermediate_size, is_savant=False, rank=128):
        super().__init__()
        self.original_mlp = original_mlp
        for param in self.original_mlp.parameters():
            param.requires_grad = False
        self.pf_gate_a = nn.Linear(hidden_size, rank, bias=False)
        self.pf_gate_b = nn.Linear(rank, intermediate_size, bias=False)
        self.pf_up_a = nn.Linear(hidden_size, rank, bias=False)
        self.pf_up_b = nn.Linear(rank, intermediate_size, bias=False)
        self.pf_down_a = nn.Linear(intermediate_size, rank, bias=False)
        self.pf_down_b = nn.Linear(rank, hidden_size, bias=False)
        self.alpha = nn.Parameter(torch.tensor(0.01))
        self.is_savant = is_savant
        self.dropout = nn.Dropout(GOLDEN_LOWER if is_savant else GOLDEN_CENTER)
        self.last_tension = None

    def forward(self, x):
        with torch.no_grad():
            original_out = self.original_mlp(x)
        g_gate = self.pf_gate_b(self.pf_gate_a(x))
        g_up = self.pf_up_b(self.pf_up_a(x))
        g_mid = F.silu(g_gate) * g_up
        g_mid = self.dropout(g_mid)
        pf_out = self.pf_down_b(self.pf_down_a(g_mid))
        repulsion = original_out.detach() - pf_out
        tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
        self.last_tension = tension.detach().squeeze(-1)
        return original_out + self.alpha * pf_out


def add_purefield(model, n_layers=8, n_savant=2, rank=128):
    total = len(model.model.layers)
    start = total - n_layers
    for i in range(start, total):
        layer = model.model.layers[i]
        mlp = layer.mlp
        h = mlp.gate_proj.weight.shape[1]
        inter = mlp.gate_proj.weight.shape[0]
        dev = mlp.gate_proj.weight.device
        dt = mlp.gate_proj.weight.dtype
        is_savant = (i - start) < n_savant
        ppf = ParallelPureFieldMLP(mlp, h, inter, is_savant=is_savant, rank=rank).to(device=dev, dtype=dt)
        layer.mlp = ppf
    return model


parser = argparse.ArgumentParser(description="AnimaLM v4 Inference Server")
parser.add_argument("--checkpoint", type=str,
                    default=os.environ.get("ANIMALM_CKPT_PATH", "checkpoints/animalm-v4/final.pt"),
                    help="PureField checkpoint path (or set ANIMALM_CKPT_PATH)")
parser.add_argument("--model", type=str, default="mistralai/Mistral-7B-Instruct-v0.3",
                    help="Base model name")
parser.add_argument("--n-layers", type=int, default=8, help="Number of PureField layers")
parser.add_argument("--n-savant", type=int, default=2, help="Number of savant layers")
parser.add_argument("--rank", type=int, default=128, help="PureField LoRA rank (default=128, 72B=128)")
parser.add_argument("--load-4bit", action="store_true", help="Load base model in 4-bit (for 32B/72B on single GPU)")
args = parser.parse_args()

print(f"Loading {args.model} + AnimaLM v4_savant...")
model_name = args.model
tokenizer = AutoTokenizer.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

load_kwargs = dict(torch_dtype=torch.bfloat16, device_map="auto")
if args.load_4bit:
    from transformers import BitsAndBytesConfig
    load_kwargs["quantization_config"] = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
    )
    print("  [4-bit] Loading with NF4 quantization")
model = AutoModelForCausalLM.from_pretrained(model_name, **load_kwargs)
model = add_purefield(model, n_layers=args.n_layers, n_savant=args.n_savant, rank=args.rank)

ckpt = torch.load(args.checkpoint, map_location="cuda")
pf_states = ckpt.get("pf_states", {})
loaded = 0
for name, module in model.named_modules():
    if isinstance(module, ParallelPureFieldMLP) and name in pf_states:
        for k, v in pf_states[name].items():
            param = dict(module.named_parameters()).get(k)
            if param is not None:
                param.data.copy_(v.to(param.device))
                loaded += 1
print(f"  Loaded {loaded} params (step {ckpt.get('step', '?')})")
model.eval()
print("Model ready!")


def chat(message, history):
    messages = [{"role": "user", "content": message}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(
            inputs.input_ids, max_new_tokens=256,
            do_sample=True, temperature=0.7, top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )
    response = tokenizer.decode(out[0][len(inputs.input_ids[0]):], skip_special_tokens=True).strip()

    tensions = []
    savant_tensions = []
    alphas = []
    for m in model.modules():
        if isinstance(m, ParallelPureFieldMLP) and m.last_tension is not None:
            t = m.last_tension.mean().item()
            tensions.append(t)
            alphas.append(m.alpha.item())
            if m.is_savant:
                savant_tensions.append(t)

    t_mean = sum(tensions) / len(tensions) if tensions else 0
    s_mean = sum(savant_tensions) / len(savant_tensions) if savant_tensions else 0
    a_mean = sum(alphas) / len(alphas) if alphas else 0

    info = "\n\n---\n"
    info += "tension={:.0f}  savant={:.0f}  alpha={:.4f}  ({} layers)".format(t_mean, s_mean, a_mean, len(tensions))
    return response + info


demo = gr.ChatInterface(
    chat,
    title="AnimaLM v4_savant — Parallel PureField + Savant",
    description="Mistral 7B Instruct + parallel tension engine. Original MLP 100% preserved. Savant 2/8 (H359).",
)
demo.launch(server_name="0.0.0.0", server_port=7860, share=True)
