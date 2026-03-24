"""멀티모델 로더 — ConsciousLM, GGUF(llama.cpp), 향후 확장 가능

사용법:
    python anima_unified.py --model mistral-7b
    python anima_unified.py --model conscious-lm
    python anima_unified.py --model llama-8b
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

    raise ValueError(f"알 수 없는 모델: {model_name}\n"
                     f"사용 가능: {', '.join(['conscious-lm'] + list(GGUF_REGISTRY.keys()))}")


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

    # GGUF 모델들
    for name, filename in GGUF_REGISTRY.items():
        path = MODELS_DIR / filename
        exists = path.exists() or _find_gguf_elsewhere(filename) is not None
        models.append((name, filename, exists))

    return models
