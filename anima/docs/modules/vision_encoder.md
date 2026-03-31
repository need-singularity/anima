# vision_encoder.py

Camera frame to tension-space vector conversion using SigLIP-base (ViT-B/16, ~86M params) with linear projection to ConsciousMind dimension.

## API
- `VisionEncoder(target_dim=128, use_pretrained=True, device='cpu')` -- main class
  - `.forward(pixel_values) -> Tensor` -- (B, C, H, W) -> (B, target_dim)
  - `.ENCODER_DIM = 768` -- SigLIP-base output dimension
- `_FallbackEncoder(out_dim=768)` -- lightweight CNN encoder when SigLIP is unavailable (3-layer conv + adaptive pool)

## Usage
```python
from vision_encoder import VisionEncoder

encoder = VisionEncoder(target_dim=128, use_pretrained=True)
frame = torch.randn(1, 3, 224, 224)  # camera frame
tension_vec = encoder(frame)  # (1, 128) tension-space vector
```

## Integration
- Used by `senses.py` for camera frame encoding
- Falls back to `_FallbackEncoder` if `transformers` (SigLIP) is not installed
- Dependencies: `transformers` (optional, for SigLIP), `opencv-python` (optional), `torch`

## Agent Tool
N/A
