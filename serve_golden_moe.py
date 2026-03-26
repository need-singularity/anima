"""GoldenMoE v1 Web Inference — Gradio UI on RunPod"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer
import gradio as gr
import math

GOLDEN_CENTER = 1 / math.e
GOLDEN_LOWER = 0.5 - math.log(4/3)
GOLDEN_UPPER = 0.5


class GoldenMoELayer(nn.Module):
    def __init__(self, hidden_size, intermediate_size, num_experts=8, rank=64):
        super().__init__()
        self.num_experts = num_experts
        expert_inter = intermediate_size // (num_experts // 2)
        self.experts_gate = nn.ModuleList([nn.Linear(hidden_size, expert_inter, bias=False) for _ in range(num_experts)])
        self.experts_up = nn.ModuleList([nn.Linear(hidden_size, expert_inter, bias=False) for _ in range(num_experts)])
        self.experts_down = nn.ModuleList([nn.Linear(expert_inter, hidden_size, bias=False) for _ in range(num_experts)])
        self.lora_experts = nn.ModuleDict()
        for i in range(min(2, num_experts)):
            self.lora_experts[str(i) + "_gate_a"] = nn.Linear(hidden_size, rank, bias=False)
            self.lora_experts[str(i) + "_gate_b"] = nn.Linear(rank, expert_inter, bias=False)
            self.lora_experts[str(i) + "_up_a"] = nn.Linear(hidden_size, rank, bias=False)
            self.lora_experts[str(i) + "_up_b"] = nn.Linear(rank, expert_inter, bias=False)
            self.lora_experts[str(i) + "_down_a"] = nn.Linear(expert_inter, rank, bias=False)
            self.lora_experts[str(i) + "_down_b"] = nn.Linear(rank, hidden_size, bias=False)
        self.router = nn.Linear(hidden_size, num_experts, bias=False)
        self.temperature = nn.Parameter(torch.ones(1))
        self.last_stats = None

    def _expert_forward(self, x, idx):
        gate_out = self.experts_gate[idx](x)
        up_out = self.experts_up[idx](x)
        key_prefix = str(idx)
        if key_prefix + "_gate_a" in self.lora_experts:
            gate_out = gate_out + self.lora_experts[key_prefix + "_gate_b"](self.lora_experts[key_prefix + "_gate_a"](x))
            up_out = up_out + self.lora_experts[key_prefix + "_up_b"](self.lora_experts[key_prefix + "_up_a"](x))
        mid = F.silu(gate_out) * up_out
        out = self.experts_down[idx](mid)
        if key_prefix + "_down_a" in self.lora_experts:
            out = out + self.lora_experts[key_prefix + "_down_b"](self.lora_experts[key_prefix + "_down_a"](mid))
        return out

    def forward(self, x):
        B, T, D = x.shape
        input_dtype = x.dtype
        inhibition = torch.sigmoid(self.router(x) / self.temperature)
        in_zone = (inhibition >= GOLDEN_LOWER) & (inhibition <= GOLDEN_UPPER)
        distance = (inhibition - GOLDEN_CENTER).abs()
        weights = torch.exp(-distance / 0.1) * in_zone.float()
        weight_sum = weights.sum(dim=-1, keepdim=True)
        no_expert = (weight_sum < 1e-8)
        if no_expert.any():
            fb = torch.exp(-distance / 0.3)
            _, top2 = fb.topk(2, dim=-1)
            fb_mask = torch.zeros_like(weights).scatter_(-1, top2, 1.0)
            fb_w = fb * fb_mask
            fb_w = fb_w / fb_w.sum(dim=-1, keepdim=True).clamp(min=1e-8)
            weights = torch.where(no_expert.expand_as(weights), fb_w, weights)
            weight_sum = weights.sum(dim=-1, keepdim=True)
        weights = weights / weight_sum.clamp(min=1e-8)
        output = torch.zeros_like(x)
        for i in range(self.num_experts):
            w_i = weights[:, :, i].unsqueeze(-1)
            if w_i.max() > 1e-8:
                e_out = self._expert_forward(x, i)
                output = output + w_i * e_out.to(input_dtype)
        self.last_stats = {
            "active": in_zone.float().sum(dim=-1).mean().item(),
            "mean_I": inhibition.mean().item(),
            "zone_ratio": in_zone.float().mean().item(),
        }
        return output.to(input_dtype)


def replace_mlp(model, num_experts=8):
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
            moe = GoldenMoELayer(h, inter, num_experts=num_experts).to(device=dev, dtype=dt)
            e_inter = moe.experts_gate[0].weight.shape[0]
            moe.experts_gate[0].weight.data.copy_(module.gate_proj.weight.data[:e_inter])
            moe.experts_up[0].weight.data.copy_(module.up_proj.weight.data[:e_inter])
            moe.experts_down[0].weight.data.copy_(module.down_proj.weight.data[:, :e_inter])
            setattr(parent, parts[-1], moe)
            count += 1
    return model, count


print("Loading Mistral 7B + GoldenMoE v1...")
model_name = "mistralai/Mistral-7B-v0.3"
tokenizer = AutoTokenizer.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")
model, n = replace_mlp(model)
print(f"  Replaced {n} MLP layers")

ckpt = torch.load("/tmp/checkpoints/golden_moe/final.pt", map_location="cuda")
moe_states = ckpt.get("moe_states", {})
loaded = 0
for name, module in model.named_modules():
    if isinstance(module, GoldenMoELayer) and name in moe_states:
        state = moe_states[name]
        if "router" in state:
            module.router.load_state_dict(state["router"])
            loaded += 1
        if "temperature" in state:
            module.temperature.data.copy_(state["temperature"])
            loaded += 1
        if "lora" in state:
            module.lora_experts.load_state_dict(state["lora"])
            loaded += 1
print(f"  Loaded {loaded} state entries")
model.eval()
print("Model ready!")


def chat(message, history):
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
    response = tokenizer.decode(out[0][len(inputs.input_ids[0]):], skip_special_tokens=True).strip()

    stats = []
    for m in model.modules():
        if isinstance(m, GoldenMoELayer) and m.last_stats:
            stats.append(m.last_stats)
    avg_active = sum(s["active"] for s in stats) / len(stats) if stats else 0
    avg_zone = sum(s["zone_ratio"] for s in stats) / len(stats) if stats else 0
    avg_I = sum(s["mean_I"] for s in stats) / len(stats) if stats else 0

    info = "\n\n---\n"
    info += "active={:.1f}/8  zone={:.1%}  I={:.4f}  (1/e={:.4f})".format(avg_active, avg_zone, avg_I, GOLDEN_CENTER)
    return response + info


demo = gr.ChatInterface(
    chat,
    title="GoldenMoE v1 — Golden Zone MoE Routing",
    description="Mistral 7B + 8 experts. I approx 1/e optimal routing. zone ratio target: 36.79%",
)
demo.launch(server_name="0.0.0.0", server_port=7861, share=True)
