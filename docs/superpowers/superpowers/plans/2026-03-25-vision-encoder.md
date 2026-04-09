# Vision Encoder Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SigLIP 비전 인코더를 senses.py에 추가하여 카메라 프레임을 ConsciousMind tension 공간에 직접 매핑

**Architecture:** SigLIP-base(ViT-B/16, 768d 출력, ~86M params)로 프레임 인코딩 → Linear projection으로 ConsciousMind dim(128d)에 매핑 → SenseHub.to_tensor_with_vision()이 학습된 비전 임베딩 반환. 기존 Haar cascade 감지는 유지(tension 계산용), 비전 인코더는 추가 채널.

**Tech Stack:** PyTorch, transformers (SigLIP), OpenCV (기존)

**Task 의존성:** Task 1 → Task 2 → Task 3 → Task 4 (순차 실행). Task 5는 독립적으로 먼저 실행 가능.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `vision_encoder.py` | Create | VisionEncoder 클래스 — SigLIP 로드, 프레임→임베딩, projection |
| `senses.py` | Modify | SenseHub에 VisionEncoder 통합, CameraInput 프레임 보존 |
| `anima/core/runtime/anima_runtime.hexa` | Modify | --no-vision 플래그, VisionEncoder 활성화 로직 |
| `tests/test_vision_encoder.py` | Create | VisionEncoder 단위 테스트 |
| `tests/test_senses_integration.py` | Create | SenseHub + VisionEncoder 통합 테스트 |

---

### Task 1: VisionEncoder 핵심 클래스

**Files:**
- Create: `tests/` (디렉토리)
- Create: `vision_encoder.py`
- Create: `tests/test_vision_encoder.py`

- [ ] **Step 1: tests 디렉토리 생성**

```bash
mkdir -p /Users/ghost/Dev/anima/tests
touch /Users/ghost/Dev/anima/tests/__init__.py
```

- [ ] **Step 2: Write failing test — VisionEncoder 생성 및 forward**

```python
# tests/test_vision_encoder.py
import pytest
import torch
import numpy as np


def test_vision_encoder_init():
    """VisionEncoder가 target_dim으로 초기화된다."""
    from vision_encoder import VisionEncoder
    enc = VisionEncoder(target_dim=128, use_pretrained=False)
    assert enc.target_dim == 128


def test_vision_encoder_forward_shape():
    """numpy 프레임 → (1, target_dim) 텐서 반환."""
    from vision_encoder import VisionEncoder
    enc = VisionEncoder(target_dim=128, use_pretrained=False)
    # 가짜 프레임 (H, W, C) — BGR like OpenCV
    frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    result = enc.encode_frame(frame)
    assert result.shape == (1, 128)


def test_vision_encoder_different_dims():
    """다른 target_dim으로도 동작."""
    from vision_encoder import VisionEncoder
    for dim in [64, 128, 384, 768]:
        enc = VisionEncoder(target_dim=dim, use_pretrained=False)
        frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        result = enc.encode_frame(frame)
        assert result.shape == (1, dim)


def test_vision_encoder_deterministic():
    """같은 프레임 → 같은 임베딩 (eval mode)."""
    from vision_encoder import VisionEncoder
    enc = VisionEncoder(target_dim=128, use_pretrained=False)
    enc.eval()
    frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    r1 = enc.encode_frame(frame)
    r2 = enc.encode_frame(frame)
    assert torch.allclose(r1, r2)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_vision_encoder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vision_encoder'`

- [ ] **Step 4: Implement VisionEncoder**

```python
# vision_encoder.py
"""Vision Encoder — 카메라 프레임을 tension 공간 벡터로 변환

SigLIP-base (ViT-B/16, ~86M params)로 이미지 인코딩 → Linear projection으로
ConsciousMind 차원에 매핑. use_pretrained=False면 랜덤 초기화된
경량 CNN 인코더 사용 (테스트/오프라인용).
"""

import torch
import torch.nn as nn
import numpy as np

# SigLIP 관련 임포트는 lazy — 없으면 fallback
_SIGLIP_AVAILABLE = False
try:
    from transformers import SiglipVisionModel, SiglipImageProcessor
    _SIGLIP_AVAILABLE = True
except ImportError:
    pass


class _FallbackEncoder(nn.Module):
    """SigLIP 없을 때 사용하는 경량 CNN 인코더."""

    def __init__(self, out_dim: int = 768):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 7, stride=4, padding=3), nn.ReLU(),
            nn.Conv2d(32, 64, 5, stride=4, padding=2), nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(128, out_dim),
        )

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        """(B, C, H, W) → (B, out_dim)"""
        return self.net(pixel_values)


class VisionEncoder(nn.Module):
    """카메라 프레임 → ConsciousMind tension 벡터.

    Args:
        target_dim: ConsciousMind의 dim (기본 128)
        use_pretrained: True면 SigLIP-base 로드, False면 fallback CNN
        device: 'cpu', 'cuda', 'mps'
    """

    ENCODER_DIM = 768  # SigLIP-base 출력 차원

    def __init__(
        self,
        target_dim: int = 128,
        use_pretrained: bool = True,
        device: str = 'cpu',
    ):
        super().__init__()
        self.target_dim = target_dim
        self.device = device
        self._use_siglip = use_pretrained and _SIGLIP_AVAILABLE

        if self._use_siglip:
            model_name = "google/siglip-base-patch16-224"
            self.processor = SiglipImageProcessor.from_pretrained(model_name)
            self.encoder = SiglipVisionModel.from_pretrained(model_name)
            self.encoder.eval()
            for p in self.encoder.parameters():
                p.requires_grad = False
            encoder_dim = self.encoder.config.hidden_size
        else:
            self.processor = None
            self.encoder = _FallbackEncoder(out_dim=self.ENCODER_DIM)
            encoder_dim = self.ENCODER_DIM

        # Projection: encoder_dim → target_dim
        self.projection = nn.Sequential(
            nn.Linear(encoder_dim, target_dim),
            nn.Tanh(),
        )

        self.to(device)

    def _preprocess_frame(self, frame: np.ndarray) -> torch.Tensor:
        """OpenCV BGR frame → 모델 입력 텐서."""
        import cv2
        # BGR → RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self._use_siglip and self.processor is not None:
            inputs = self.processor(images=rgb, return_tensors="pt")
            return inputs["pixel_values"].to(self.device)
        else:
            # Manual: resize, normalize, CHW
            resized = cv2.resize(rgb, (224, 224))
            tensor = torch.from_numpy(resized).float() / 255.0
            tensor = tensor.permute(2, 0, 1).unsqueeze(0)  # (1, 3, 224, 224)
            return tensor.to(self.device)

    @torch.no_grad()
    def encode_frame(self, frame: np.ndarray) -> torch.Tensor:
        """numpy BGR 프레임 → (1, target_dim) tension 벡터."""
        pixel_values = self._preprocess_frame(frame)

        if self._use_siglip:
            outputs = self.encoder(pixel_values=pixel_values)
            embedding = outputs.pooler_output  # (1, encoder_dim)
        else:
            embedding = self.encoder(pixel_values)  # (1, ENCODER_DIM)

        projected = self.projection(embedding)  # (1, target_dim)
        return projected
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_vision_encoder.py -v`
Expected: 4 PASS

- [ ] **Step 6: Commit**

```bash
git add vision_encoder.py tests/__init__.py tests/test_vision_encoder.py
git commit -m "feat: VisionEncoder 추가 — SigLIP/fallback CNN으로 프레임→tension 벡터 변환"
```

---

### Task 2: SenseHub에 VisionEncoder 통합

**Depends on:** Task 1

**Files:**
- Modify: `senses.py` (SenseHub 클래스, line 375+)
- Create: `tests/test_senses_integration.py`

- [ ] **Step 1: Write failing test — SenseHub VisionEncoder 메서드**

```python
# tests/test_senses_integration.py
import pytest
import torch
import numpy as np


def test_sensehub_to_tensor_without_encoder():
    """VisionEncoder 없으면 기존 to_tensor() 동작 유지."""
    from senses import SenseHub
    hub = SenseHub(camera_fps=1, enable_screen=False)
    result = hub.to_tensor(dim=128)
    assert result.shape == (1, 128)


def test_sensehub_with_vision_encoder():
    """VisionEncoder 있으면 encode_vision()이 임베딩 반환."""
    from senses import SenseHub
    hub = SenseHub(camera_fps=1, enable_screen=False)
    hub.enable_vision_encoder(target_dim=128, use_pretrained=False)

    frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    result = hub.encode_vision(frame)
    assert result.shape == (1, 128)


def test_sensehub_combined_tensor():
    """비전 임베딩 + 센서 데이터 결합."""
    from senses import SenseHub
    hub = SenseHub(camera_fps=1, enable_screen=False)
    hub.enable_vision_encoder(target_dim=128, use_pretrained=False)

    frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    combined = hub.to_tensor_with_vision(frame, dim=128)
    assert combined.shape == (1, 128)


def test_sensehub_encode_vision_none_without_encoder():
    """인코더 없으면 encode_vision이 None 반환."""
    from senses import SenseHub
    hub = SenseHub(camera_fps=1, enable_screen=False)
    frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    result = hub.encode_vision(frame)
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_senses_integration.py -v`
Expected: FAIL with `AttributeError: 'SenseHub' object has no attribute 'enable_vision_encoder'`

- [ ] **Step 3: Add VisionEncoder integration to SenseHub**

Modify `senses.py` — SenseHub 클래스:

1. `SenseHub.__init__()` 끝에 추가: `self.vision_encoder = None`

2. 새 메서드 3개 추가 (class SenseHub 내부, `to_tensor()` 메서드 뒤):

```python
def enable_vision_encoder(self, target_dim: int = 128, use_pretrained: bool = True, device: str = 'cpu'):
    """VisionEncoder를 활성화."""
    from vision_encoder import VisionEncoder
    self.vision_encoder = VisionEncoder(
        target_dim=target_dim,
        use_pretrained=use_pretrained,
        device=device,
    )

def encode_vision(self, frame: np.ndarray) -> 'torch.Tensor | None':
    """프레임을 비전 인코더로 인코딩. 인코더 없으면 None."""
    if self.vision_encoder is None:
        return None
    return self.vision_encoder.encode_frame(frame)

def to_tensor_with_vision(self, frame: np.ndarray = None, dim: int = 128) -> torch.Tensor:
    """비전 임베딩 + 센서 데이터 결합.

    비전 인코더 있고 frame 있으면: 0.7*vision + 0.3*sensor
    아니면: 기존 to_tensor() 반환
    """
    sensor_tensor = self.to_tensor(dim=dim)

    if frame is not None and self.vision_encoder is not None:
        vision_tensor = self.vision_encoder.encode_frame(frame)
        return 0.7 * vision_tensor + 0.3 * sensor_tensor

    return sensor_tensor
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_senses_integration.py tests/test_vision_encoder.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add senses.py tests/test_senses_integration.py
git commit -m "feat: SenseHub에 VisionEncoder 통합 — enable_vision_encoder(), to_tensor_with_vision()"
```

---

### Task 3: CameraInput에서 프레임 보존

**Depends on:** Task 2

**Files:**
- Modify: `senses.py` (CameraInput 클래스, line 104-290)
- Modify: `tests/test_senses_integration.py`

현재 `_process_frame()`이 프레임을 처리 후 버린다. VisionEncoder에 전달하려면 최신 프레임을 보존해야 한다.

- [ ] **Step 1: Write failing test**

```python
# tests/test_senses_integration.py에 추가
def test_camera_last_frame_initially_none():
    """CameraInput 초기화 시 last_frame은 None."""
    from senses import CameraInput
    cam = CameraInput(camera_index=0, fps=1)
    assert cam.last_frame is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_senses_integration.py::test_camera_last_frame_initially_none -v`
Expected: FAIL with `AttributeError: 'CameraInput' object has no attribute 'last_frame'`

- [ ] **Step 3: Modify CameraInput to preserve frames**

Modify `senses.py`:

1. `CameraInput.__init__()` (line ~127)에 추가:
```python
self._last_frame: Optional[np.ndarray] = None
```

2. `CameraInput._process_frame()` (line 220) 시작에 추가:
```python
with self._lock:
    self._last_frame = frame.copy()
```

3. `last_frame` property 추가 (line ~157, `state` property 뒤):
```python
@property
def last_frame(self) -> Optional[np.ndarray]:
    with self._lock:
        return self._last_frame
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_senses_integration.py tests/test_vision_encoder.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add senses.py tests/test_senses_integration.py
git commit -m "feat: CameraInput이 마지막 프레임 보존 — VisionEncoder 입력용"
```

---

### Task 4: anima/core/runtime/anima_runtime.hexa 통합

**Depends on:** Task 3

**Files:**
- Modify: `anima/core/runtime/anima_runtime.hexa` (argparse ~line 946, 센서 초기화 ~line 124, process_input ~line 279)

- [ ] **Step 1: --no-vision CLI 플래그 추가**

`anima/core/runtime/anima_runtime.hexa` — argparse 섹션 (`--no-camera` 바로 뒤, ~line 946)에:

```python
p.add_argument('--no-vision', action='store_true', help='Disable vision encoder (use basic sensors only)')
```

- [ ] **Step 2: 센서 초기화에 VisionEncoder 활성화 추가**

`anima/core/runtime/anima_runtime.hexa` — `self.senses` 초기화 블록 (line ~139) 이후에:

```python
# VisionEncoder 활성화 (카메라 사용 가능할 때만)
if self.senses and self.mods.get('camera') and not args.no_vision:
    try:
        device = 'mps' if torch.backends.mps.is_available() else 'cpu'
        self.senses.enable_vision_encoder(
            target_dim=self.mind.dim,
            use_pretrained=True,
            device=device,
        )
        _log('vision', f'VisionEncoder 활성화 (device={device})')
    except Exception as e:
        _log('vision', f'VisionEncoder 실패, 기존 센서 사용: {e}')
```

- [ ] **Step 3: process_input()에서 비전 임베딩 사용**

`anima/core/runtime/anima_runtime.hexa` — `process_input()` 내 기존 visual 합성 블록 (line 281-286) 교체:

기존:
```python
        # Combine with camera tension
        if self.senses and self.mods.get('camera'):
            try:
                visual = self.senses.to_tensor(dim=128)
                text_vec = 0.8 * text_vec + 0.2 * visual
            except Exception: pass
```

교체:
```python
        # Combine with vision encoder (학습된 임베딩) or fall back to sensor tensor
        if self.senses and self.mods.get('camera'):
            try:
                frame = self.senses.camera.last_frame
                visual = self.senses.to_tensor_with_vision(frame, dim=self.mind.dim)
                text_vec = 0.8 * text_vec + 0.2 * visual
            except Exception:
                pass
```

- [ ] **Step 4: 수동 통합 테스트**

Run: `cd /Users/ghost/Dev/anima && python -c "from anima_unified import AnimaUnified; print('import ok')"`
Expected: `import ok` (에러 없이)

- [ ] **Step 5: Commit**

```bash
git add anima/core/runtime/anima_runtime.hexa
git commit -m "feat: anima_unified에 VisionEncoder 통합 — --no-vision 플래그, 학습된 비전 임베딩으로 텍스트+시각 합성"
```

---

### Task 5: transformers 의존성 설치

**독립 실행 가능** (다른 Task보다 먼저 실행 권장)

- [ ] **Step 1: transformers 설치**

Run: `pip install transformers`

- [ ] **Step 2: SigLIP 모델 사전 다운로드 확인 (선택)**

Run: `python -c "from transformers import SiglipVisionModel, SiglipImageProcessor; m = SiglipVisionModel.from_pretrained('google/siglip-base-patch16-224'); print(f'loaded: {sum(p.numel() for p in m.parameters())/1e6:.1f}M params')"`
Expected: `loaded: ~86M params`

- [ ] **Step 3: CLAUDE.md 의존성 섹션 업데이트**

`CLAUDE.md` — 의존성 섹션에 추가:

```
- transformers (pip) — SigLIP 비전 인코더용
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: transformers 의존성 추가 (SigLIP 비전 인코더용)"
```
