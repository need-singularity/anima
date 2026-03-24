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
