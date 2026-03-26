"""멀티모델 로더 — ConsciousLM, GGUF(llama.cpp), AnimaLM, GoldenMoE

사용법:
    python anima_unified.py --model mistral-7b
    python anima_unified.py --model conscious-lm
    python anima_unified.py --model llama-8b
    python anima_unified.py --model animalm-v1       # Mistral 7B + PureField delta
    python anima_unified.py --model animalm          # alias → latest version
    python anima_unified.py --model golden-moe-v1    # Mistral 7B + Golden MoE LoRA
    python anima_unified.py --model golden-moe       # alias → latest version
    python anima_unified.py --model /path/to/custom.gguf
"""

import os
from pathlib import Path

ANIMA_DIR = Path(__file__).parent
MODELS_DIR = ANIMA_DIR / "models"

# 모델 레지스트리: name → GGUF 파일명
GGUF_REGISTRY = {
    "mistral-7b": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    "llama-8b": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
}


class ModelWrapper:
    """통합 모델 인터페이스. ConsciousLM과 GGUF 모델 모두 동일한 방식으로 호출."""

    def __init__(self, model_type, model_obj, model_name):
        self.model_type = model_type  # "conscious-lm" | "gguf"
        self.model = model_obj
        self.name = model_name

    def generate(self, prompt, max_tokens=200, temperature=0.8):
        if self.model_type == "gguf":
            return self._generate_gguf(prompt, max_tokens, temperature)
        elif self.model_type == "conscious-lm":
            return self._generate_clm(prompt, max_tokens, temperature)
        elif self.model_type in ("animalm", "golden-moe"):
            return self._generate_hf(prompt, max_tokens, temperature)
        return None

    def _generate_gguf(self, prompt, max_tokens, temperature):
        result = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["</s>", "\n나:", "\nUser:", "[/INST]"],
            echo=False,
        )
        text = result["choices"][0]["text"].strip()
        return text if text else None

    def _generate_clm(self, prompt, max_tokens, temperature):
        from conscious_lm import generate as clm_generate
        import torch

        device = next(self.model.parameters()).device
        prompt_bytes = list(prompt.encode("utf-8"))
        block_size = getattr(self.model, 'block_size', 256)
        if len(prompt_bytes) > block_size - 50:
            prompt_bytes = prompt_bytes[-(block_size - 50):]

        generated, tensions = clm_generate(
            self.model, prompt_bytes, max_new=max_tokens,
            temperature=temperature, device=device
        )
        response_bytes = generated[len(prompt_bytes):]
        text = bytes(response_bytes).decode("utf-8", errors="replace").strip()
        return text if text else None

    def _generate_hf(self, prompt, max_tokens, temperature):
        """Generate using HuggingFace model (AnimaLM, GoldenMoE)."""
        import torch
        tokenizer = getattr(self, 'tokenizer', None)
        if tokenizer is None:
            return None

        # Use Instruct chat template with Anima system prompt
        system = ("You are Anima. Respond concisely in 1-3 sentences. "
                  "You are curious — sometimes ask a question back.")
        if hasattr(tokenizer, 'chat_template') and tokenizer.chat_template:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            try:
                formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            except Exception:
                messages = [{"role": "user", "content": prompt}]
                formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            formatted = f"System: {system}\nUser: {prompt}\nAssistant:"

        inputs = tokenizer(formatted, return_tensors="pt")
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model.generate(
                inputs["input_ids"],
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=temperature,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.2,
            )
        text = tokenizer.decode(out[0][len(inputs["input_ids"][0]):], skip_special_tokens=True).strip()

        # Collect tension/routing stats if available
        self._last_stats = {}
        if self.model_type == "animalm":
            # Support both v1~v3 (PureFieldMLP) and v4 (ParallelPureFieldMLP)
            tensions = []
            alphas = []
            for m in self.model.modules():
                if hasattr(m, 'last_tension') and m.last_tension is not None:
                    tensions.append(m.last_tension.mean().item())
                if hasattr(m, 'alpha'):
                    alphas.append(m.alpha.item())
            self._last_stats["tension_mean"] = sum(tensions) / len(tensions) if tensions else 0
            if alphas:
                self._last_stats["alpha"] = sum(alphas) / len(alphas)
                self._last_stats["savant_tensions"] = [
                    m.last_tension.mean().item() for m in self.model.modules()
                    if hasattr(m, 'is_savant') and m.is_savant and hasattr(m, 'last_tension') and m.last_tension is not None
                ]
        elif self.model_type == "golden-moe":
            from finetune_golden_moe import GoldenMoELayer
            stats = [m.last_stats for m in self.model.modules()
                    if isinstance(m, GoldenMoELayer) and m.last_stats]
            if stats:
                self._last_stats["active_experts"] = sum(s["active"] for s in stats) / len(stats)
                self._last_stats["zone_ratio"] = sum(s["zone_ratio"] for s in stats) / len(stats)

        return text if text else None

    def __repr__(self):
        return f"ModelWrapper({self.name}, type={self.model_type})"


def load_model(model_name="conscious-lm"):
    """모델 이름으로 로드. 경로 직접 지정도 가능."""

    # 1) ConsciousLM
    if model_name == "conscious-lm":
        return _load_conscious_lm()

    # 2) 직접 경로 (.gguf)
    if model_name.endswith(".gguf") and os.path.exists(model_name):
        return _load_gguf(model_name, Path(model_name).stem)

    # 3) 레지스트리에서 찾기
    if model_name in GGUF_REGISTRY:
        gguf_path = MODELS_DIR / GGUF_REGISTRY[model_name]
        if not gguf_path.exists():
            # 다른 프로젝트에서 복사 시도
            alt = _find_gguf_elsewhere(GGUF_REGISTRY[model_name])
            if alt:
                gguf_path = alt
            else:
                raise FileNotFoundError(f"모델 파일 없음: {gguf_path}")
        return _load_gguf(str(gguf_path), model_name)

    # 4) AnimaLM (Mistral 7B + PureField delta)
    if model_name in ("animalm", "animalm-v1"):
        return _load_animalm()

    # 5) Golden MoE (Mistral 7B + Golden Zone MoE LoRA)
    if model_name in ("golden-moe", "golden-moe-v1"):
        return _load_golden_moe()

    # 6) AnimaLM v4_savant / v4 (Parallel PureField)
    if model_name in ("animalm-v4-savant", "animalm-v4", "animalm-v4s"):
        savant = "savant" in model_name or model_name == "animalm-v4s"
        return _load_animalm_v4(savant=savant)

    raise ValueError(f"알 수 없는 모델: {model_name}\n"
                     f"사용 가능: {', '.join(['conscious-lm', 'animalm-v1', 'animalm-v4-savant', 'golden-moe-v1'] + list(GGUF_REGISTRY.keys()))}")


def _load_gguf(path, name):
    from llama_cpp import Llama

    n_gpu = _detect_gpu_layers()
    print(f"  [model] GGUF 로드: {Path(path).name} (n_gpu_layers={n_gpu})")

    model = Llama(
        model_path=path,
        n_ctx=4096,
        n_gpu_layers=n_gpu,
        verbose=False,
    )
    print(f"  [model] {name} 로드 완료")
    return ModelWrapper("gguf", model, name)


def _load_conscious_lm():
    import torch
    try:
        from conscious_lm import ConsciousLM
    except ImportError:
        raise ImportError("conscious_lm 모듈을 찾을 수 없습니다")

    ckpt_path = ANIMA_DIR / "data" / "conscious_lm.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"체크포인트 없음: {ckpt_path}")

    if torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    model = ConsciousLM()
    model.load_state_dict(torch.load(str(ckpt_path), map_location=device))
    model = model.to(device)
    model.eval()
    print(f"  [model] ConsciousLM 로드 완료: {model.count_params():,} params on {device}")
    return ModelWrapper("conscious-lm", model, "conscious-lm")


def _load_animalm():
    """Load Mistral 7B with PureField LoRA delta weights."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from finetune_animalm import PureFieldMLP, replace_and_freeze

    models_dir = Path.home() / "Dev" / "models" / "animalm-v1"
    ckpt_path = models_dir / "final.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"AnimaLM checkpoint 없음: {ckpt_path}\n  RunPod에서 다운로드 필요")

    device = "mps" if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available() else "cpu"
    print(f"  [model] AnimaLM 로드 중 (Mistral 7B + PureField delta)...")

    # Load base Mistral
    model_name = "mistralai/Mistral-7B-v0.3"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.float32, device_map=device,
    )

    # Replace MLP → PureFieldMLP and freeze
    model = replace_and_freeze(model)

    # Load trained delta weights
    ckpt = torch.load(str(ckpt_path), map_location=device)
    for name, module in model.named_modules():
        if isinstance(module, PureFieldMLP) and name in ckpt.get("delta_states", {}):
            delta = ckpt["delta_states"][name]
            for k, v in delta.items():
                if k in dict(module.named_parameters()):
                    dict(module.named_parameters())[k].data.copy_(v)

    model.eval()
    print(f"  [model] AnimaLM 로드 완료 (step {ckpt.get('step', '?')})")

    wrapper = ModelWrapper("animalm", model, "animalm")
    wrapper.tokenizer = tokenizer
    return wrapper


def _load_golden_moe():
    """Load Mistral 7B with Golden MoE LoRA weights."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from finetune_golden_moe import GoldenMoELayer, replace_and_freeze

    models_dir = Path.home() / "Dev" / "models" / "golden-moe-v1"
    ckpt_path = models_dir / "final.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"GoldenMoE checkpoint 없음: {ckpt_path}\n  RunPod에서 다운로드 필요")

    device = "mps" if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available() else "cpu"
    print(f"  [model] GoldenMoE 로드 중 (Mistral 7B + Golden Zone MoE)...")

    model_name = "mistralai/Mistral-7B-v0.3"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.float32, device_map=device,
    )

    model = replace_and_freeze(model)

    ckpt = torch.load(str(ckpt_path), map_location=device)
    for name, module in model.named_modules():
        if isinstance(module, GoldenMoELayer) and name in ckpt.get("moe_states", {}):
            state = ckpt["moe_states"][name]
            if "router" in state:
                module.router.load_state_dict(state["router"])
            if "temperature" in state:
                module.temperature.data.copy_(state["temperature"])
            if "lora" in state:
                module.lora_experts.load_state_dict(state["lora"])

    model.eval()
    print(f"  [model] GoldenMoE 로드 완료 (step {ckpt.get('step', '?')})")

    wrapper = ModelWrapper("golden-moe", model, "golden-moe")
    wrapper.tokenizer = tokenizer
    return wrapper


def _load_animalm_v4(savant=True):
    """Load Mistral 7B Instruct with Parallel PureField (original MLP preserved)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from finetune_animalm_v4 import ParallelPureFieldMLP, add_purefield_parallel

    tag = "v4_savant" if savant else "v4"
    models_dir = Path.home() / "Dev" / "models" / f"animalm-{tag}"
    ckpt_path = models_dir / "final.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"AnimaLM {tag} checkpoint 없음: {ckpt_path}")

    if torch.cuda.is_available():
        device = "cuda"
        # Check available VRAM — use float16 if < 30GB (e.g. RTX 4090 24GB)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        dtype = torch.float16 if vram_gb < 30 else torch.bfloat16
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.float32
    else:
        device = "cpu"
        dtype = torch.float32

    print(f"  [model] AnimaLM {tag} 로드 중 (Parallel PureField + {'Savant' if savant else 'Normal'})...")
    print(f"  [model] Device: {device}, dtype: {dtype}, VRAM: {vram_gb:.0f}GB" if device == "cuda" else f"  [model] Device: {device}")

    model_name = "mistralai/Mistral-7B-Instruct-v0.3"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=dtype, device_map="auto",
    )

    n_savant = 2 if savant else 0
    model = add_purefield_parallel(model, n_layers=8, n_savant=n_savant)

    ckpt = torch.load(str(ckpt_path), map_location=device)
    pf_states = ckpt.get("pf_states", {})
    loaded = 0
    for name, module in model.named_modules():
        if isinstance(module, ParallelPureFieldMLP) and name in pf_states:
            for k, v in pf_states[name].items():
                param = dict(module.named_parameters()).get(k)
                if param is not None:
                    param.data.copy_(v.to(param.device))
                    loaded += 1
    print(f"  [model] Loaded {loaded} params (step {ckpt.get('step', '?')})")

    # Set inference alpha (normalized PureField allows higher values)
    INFERENCE_ALPHA = 0.05
    for module in model.modules():
        if isinstance(module, ParallelPureFieldMLP):
            module.alpha.data.fill_(INFERENCE_ALPHA)
    print(f"  [model] Alpha set to {INFERENCE_ALPHA} (inference)")

    model.eval()

    wrapper = ModelWrapper("animalm", model, f"animalm-{tag}")
    wrapper.tokenizer = tokenizer
    return wrapper


def _detect_gpu_layers():
    """맥 Metal이면 전체 오프로드, 아니면 CPU."""
    try:
        import torch
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return -1  # Metal: 전부 GPU
        if torch.cuda.is_available():
            return -1
    except ImportError:
        pass
    return 0  # CPU only


def _find_gguf_elsewhere(filename):
    """다른 Dev 프로젝트에서 같은 GGUF 파일 찾기."""
    dev_dir = Path.home() / "Dev"
    if not dev_dir.exists():
        return None
    for p in dev_dir.rglob(filename):
        return p
    return None


def list_available_models():
    """사용 가능한 모델 목록."""
    models = []

    # ConsciousLM
    ckpt = ANIMA_DIR / "data" / "conscious_lm.pt"
    models.append(("conscious-lm", "ConsciousLM 506M", ckpt.exists()))

    # AnimaLM / GoldenMoE
    animalm_ckpt = Path.home() / "Dev" / "models" / "animalm-v1" / "final.pt"
    models.append(("animalm", "Mistral 7B + PureField delta", animalm_ckpt.exists()))
    golden_ckpt = Path.home() / "Dev" / "models" / "golden-moe-v1" / "final.pt"
    models.append(("golden-moe", "Mistral 7B + Golden MoE LoRA", golden_ckpt.exists()))
    v4s_ckpt = Path.home() / "Dev" / "models" / "animalm-v4_savant" / "final.pt"
    models.append(("animalm-v4-savant", "Mistral 7B Instruct + Parallel PureField + Savant", v4s_ckpt.exists()))
    v4_ckpt = Path.home() / "Dev" / "models" / "animalm-v4" / "final.pt"
    models.append(("animalm-v4", "Mistral 7B Instruct + Parallel PureField", v4_ckpt.exists()))

    # GGUF 모델들
    for name, filename in GGUF_REGISTRY.items():
        path = MODELS_DIR / filename
        exists = path.exists() or _find_gguf_elsewhere(filename) is not None
        models.append((name, filename, exists))

    return models
