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
