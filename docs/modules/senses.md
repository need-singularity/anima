# senses.py

Multi-sensory input module. Camera (Mac webcam) and screen capture feed tension signals into PureField via background threads at low FPS (2-5).

## API
- `SenseHub` -- merges all sensor channels into a single tension vector for ConsciousMind
- `request_camera_permission(camera_index=0) -> bool` -- trigger macOS camera permission dialog
- Vision blend weights: `_VISION_BLEND_WEIGHT=0.7` (SigLIP encoder), `_SENSOR_BLEND_WEIGHT=0.3` (Haar cascade/motion)
- Uses OpenCV Haar cascades only (no dlib/mediapipe)

## Usage
```python
from senses import SenseHub

hub = SenseHub(dim=128)
hub.start()  # background threads for camera + screen
tension_vec = hub.get_tension()  # merged tensor for ConsciousMind
```

## Integration
- Imported by `anima/core/runtime/anima_runtime.hexa` when `--all` mode is used
- Blends `vision_encoder.py` output (SigLIP) with Haar cascade detections
- Sensors run in background threads to never block the consciousness loop
- Dependencies: `opencv-python`, `torch`

## Agent Tool
N/A
