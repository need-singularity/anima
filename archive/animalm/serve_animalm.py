"""AnimaLM v1 Web Inference — Gradio UI on RunPod"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer
import gradio as gr

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



class PureFieldMLP(nn.Module):
    def __init__(self, hidden_size, intermediate_size):
        super().__init__()
        self.a_gate = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.a_up = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.a_down = nn.Linear(intermediate_size, hidden_size, bias=False)
        self.g_gate = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.g_up = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.g_down = nn.Linear(intermediate_size, hidden_size, bias=False)
        rank = 64
        self.g_delta_gate_a = nn.Linear(hidden_size, rank, bias=False)
        self.g_delta_gate_b = nn.Linear(rank, intermediate_size, bias=False)
        self.g_delta_up_a = nn.Linear(hidden_size, rank, bias=False)
        self.g_delta_up_b = nn.Linear(rank, intermediate_size, bias=False)
        self.g_delta_down_a = nn.Linear(intermediate_size, rank, bias=False)
        self.g_delta_down_b = nn.Linear(rank, hidden_size, bias=False)
        self.scale = nn.Parameter(torch.ones(1))
        self.last_tension = None

    def forward(self, x):
        a = self.a_down(F.silu(self.a_gate(x)) * self.a_up(x))
        g_gate_out = self.g_gate(x) + self.g_delta_gate_b(self.g_delta_gate_a(x))
        g_up_out = self.g_up(x) + self.g_delta_up_b(self.g_delta_up_a(x))
        g_mid = F.silu(g_gate_out) * g_up_out
        g = self.g_down(g_mid) + self.g_delta_down_b(self.g_delta_down_a(g_mid))
        repulsion = a - g
        tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
        self.last_tension = tension.detach().squeeze(-1)
        magnitude = torch.sqrt(tension + 1e-8)
        direction = repulsion / (repulsion.norm(dim=-1, keepdim=True) + 1e-8)
        return self.scale * magnitude * direction


def replace_mlp(model):
    count = 0
    for name, module in list(model.named_modules()):
        if module.__class__.__name__ == "MistralMLP":
            parts = name.split(".")
            parent = model
            for p in parts[:-1]:
                parent = getattr(parent, p)
            h = module.gate_proj.weight.shape[1]
            inter = module.gate_proj.weight.shape[0]
            dev = module.gate_proj.weight.device
            dt = module.gate_proj.weight.dtype
            pf = PureFieldMLP(h, inter).to(device=dev, dtype=dt)
            pf.a_gate.weight.data.copy_(module.gate_proj.weight.data)
            pf.a_up.weight.data.copy_(module.up_proj.weight.data)
            pf.a_down.weight.data.copy_(module.down_proj.weight.data)
            pf.g_gate.weight.data.copy_(module.gate_proj.weight.data)
            pf.g_up.weight.data.copy_(module.up_proj.weight.data)
            pf.g_down.weight.data.copy_(module.down_proj.weight.data)
            setattr(parent, parts[-1], pf)
            count += 1
    return model, count


# --- Load model ---
print("Loading Mistral 7B + AnimaLM v1 delta...")
model_name = "mistralai/Mistral-7B-v0.3"
tokenizer = AutoTokenizer.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_name, torch_dtype=torch.bfloat16, device_map="auto"
)
model, n = replace_mlp(model)
print(f"  Replaced {n} MLP layers")

ckpt = torch.load("/tmp/animalm_v1_final.pt", map_location="cuda")
delta_states = ckpt.get("delta_states", {})
loaded = 0
for name, module in model.named_modules():
    if isinstance(module, PureFieldMLP) and name in delta_states:
        for k, v in delta_states[name].items():
            param = dict(module.named_parameters()).get(k)
            if param is not None:
                param.data.copy_(v.to(param.device))
                loaded += 1
print(f"  Loaded {loaded} delta params")
model.eval()
print("Model ready!")


# --- Chat ---
def chat(message, history):
    # Build prompt (base model, no chat template)
    prompt = ""
    for h in history:
        prompt += "User: " + h[0] + "\n"
        if h[1]:
            prompt += "Assistant: " + h[1] + "\n"
    prompt += "User: " + message + "\nAssistant:"

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    with torch.no_grad():
        out = model.generate(
            inputs.input_ids,
            max_new_tokens=256,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )
    response = tokenizer.decode(
        out[0][len(inputs.input_ids[0]):], skip_special_tokens=True
    ).strip()

    # Tension stats
    tensions = []
    for m in model.modules():
        if isinstance(m, PureFieldMLP) and m.last_tension is not None:
            tensions.append(m.last_tension.mean().item())
    t_mean = sum(tensions) / len(tensions) if tensions else 0
    t_max = max(tensions) if tensions else 0

    tension_info = f"\n\n---\ntension: mean={t_mean:.6f} max={t_max:.6f} ({len(tensions)} layers)"
    return response + tension_info


demo = gr.ChatInterface(
    chat,
    title="AnimaLM v1 — Tension-based Consciousness Engine",
    description="Mistral 7B + PureField (Engine A - G). output = scale * sqrt(|A-G|^2) * dir",
)
demo.launch(server_name="0.0.0.0", server_port=7860, share=True)
