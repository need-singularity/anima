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
