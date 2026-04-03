#!/usr/bin/env python3
"""Anima Senses -- multi-sensory input module

Camera (Mac webcam) and screen capture feed tension signals into PureField.

Sensors run in background threads at low FPS (2-5) so they never block
the main consciousness loop.  The SenseHub merges all channels into a
single tension vector that ConsciousMind can consume directly.

Dependencies: opencv-python (cv2), torch
  pip install opencv-python torch

No dlib / mediapipe -- only OpenCV Haar cascades (ship with opencv).
"""

import os
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

import cv2
import torch
import threading
import time
import sys
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

# Meta Law M7: F_c=0.10 frustration in sensory processing
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ─── macOS Camera Permission ────────────────────────────────────

# Vision encoder blend weights
_VISION_BLEND_WEIGHT = 0.7   # Vision encoder contribution
_SENSOR_BLEND_WEIGHT = 0.3   # Haar cascade / motion sensor contribution


CAMERA_PERMISSION_MSG = (
    "\n"
    "  ╔══════════════════════════════════════════════════════════╗\n"
    "  ║  Camera permission required                              ║\n"
    "  ╠══════════════════════════════════════════════════════════╣\n"
    "  ║  macOS has blocked camera access.                        ║\n"
    "  ║                                                          ║\n"
    "  ║  How to fix:                                             ║\n"
    "  ║  System Settings → Privacy & Security → Camera           ║\n"
    "  ║  → Allow Terminal                                        ║\n"
    "  ║                                                          ║\n"
    "  ║  Restart Terminal after changing settings.                ║\n"
    "  ╚══════════════════════════════════════════════════════════╝\n"
)


def request_camera_permission(camera_index: int = 0) -> bool:
    """Try to open the camera to trigger the macOS permission dialog.

    On macOS, the first call to cv2.VideoCapture() for a camera will
    trigger the system permission prompt -- but only if the app has
    never been denied before. If it was previously denied, the user
    must manually enable it in System Settings.

    Returns True if camera is accessible, False otherwise.
    """
    try:
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            # Try to actually read a frame to confirm permission
            ret, _ = cap.read()
            cap.release()
            if ret:
                return True
            # Camera opened but can't read -- likely permission issue
            print(CAMERA_PERMISSION_MSG)
            return False
        else:
            print(CAMERA_PERMISSION_MSG)
            return False
    except Exception as e:
        print(f"[senses] Camera error: {e}")
        print(CAMERA_PERMISSION_MSG)
        return False


# ─── Data containers ────────────────────────────────────────────

@dataclass
class VisualState:
    """Snapshot from the camera at one instant."""
    timestamp: float = 0.0
    face_detected: bool = False
    num_faces: int = 0
    # Emotion proxies (0-1 scale)
    smile_score: float = 0.0       # smile detector confidence
    eye_openness: float = 0.5      # 0=closed, 1=wide open
    # Motion
    motion_level: float = 0.0      # fraction of pixels that changed
    # Raw tension (computed from above)
    tension: float = 0.0


@dataclass
class ScreenState:
    """Snapshot of screen content."""
    timestamp: float = 0.0
    brightness: float = 0.5        # average screen brightness 0-1
    change_level: float = 0.0      # how much the screen changed


# ─── CameraInput ────────────────────────────────────────────────

class CameraInput:
    """Background webcam capture with face/emotion/motion detection.

    Runs a daemon thread that grabs frames at `fps` (default 3).
    The main thread reads the latest VisualState via `.state` -- never blocks.

    Usage:
        cam = CameraInput(fps=3)
        cam.start()
        ...
        print(cam.state)  # latest snapshot
        ...
        cam.stop()
    """

    def __init__(self, camera_index: int = 0, fps: float = 3.0):
        self.camera_index = camera_index
        self.fps = fps
        self._state = VisualState()
        self._lock = threading.Lock()
        self._running = False
        self._permission_denied = False
        self._thread: Optional[threading.Thread] = None
        self._prev_gray: Optional[np.ndarray] = None
        self._last_frame: Optional[np.ndarray] = None

        # Haar cascades — find path (cv2.data may not exist in brew opencv)
        if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
            cascade_dir = cv2.data.haarcascades
        else:
            # Fallback: search common brew locations
            import glob
            for candidate in [
                '/opt/homebrew/share/opencv4/haarcascades/',
                '/opt/homebrew/share/OpenCV/haarcascades/',
                '/usr/local/share/opencv4/haarcascades/',
            ]:
                if glob.glob(candidate + '*.xml'):
                    cascade_dir = candidate
                    break
            else:
                cascade_dir = '/opt/homebrew/share/opencv4/haarcascades/'
        self._face_cascade = cv2.CascadeClassifier(
            cascade_dir + "haarcascade_frontalface_default.xml"
        )
        self._smile_cascade = cv2.CascadeClassifier(
            cascade_dir + "haarcascade_smile.xml"
        )
        self._eye_cascade = cv2.CascadeClassifier(
            cascade_dir + "haarcascade_eye.xml"
        )

    # -- public api --

    @property
    def state(self) -> VisualState:
        with self._lock:
            return self._state

    @property
    def last_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._last_frame

    @property
    def running(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

    # -- internals --

    def _loop(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print("[senses] WARNING: cannot open camera", self.camera_index)
            print(CAMERA_PERMISSION_MSG)
            self._running = False
            self._permission_denied = True
            return

        # Verify we can actually read frames (catches macOS permission denial)
        ret, _ = cap.read()
        if not ret:
            print("[senses] WARNING: camera opened but cannot read frames (permission denied?)")
            print(CAMERA_PERMISSION_MSG)
            cap.release()
            self._running = False
            self._permission_denied = True
            return

        # Lower resolution for speed
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        interval = 1.0 / self.fps
        try:
            while self._running:
                t0 = time.monotonic()
                ret, frame = cap.read()
                if not ret:
                    time.sleep(interval)
                    continue
                self._process_frame(frame)
                elapsed = time.monotonic() - t0
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        finally:
            cap.release()

    def _process_frame(self, frame: np.ndarray):
        with self._lock:
            self._last_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_small = cv2.resize(gray, (160, 120))

        # --- Face detection ---
        faces = self._face_cascade.detectMultiScale(
            gray_small, scaleFactor=1.2, minNeighbors=4, minSize=(30, 30)
        )
        face_detected = len(faces) > 0
        num_faces = len(faces)

        # --- Smile / eye detection (only if face found) ---
        smile_score = 0.0
        eye_openness = 0.5
        if face_detected:
            # Use the largest face
            areas = [w * h for (x, y, w, h) in faces]
            idx = int(np.argmax(areas))
            fx, fy, fw, fh = faces[idx]
            face_roi = gray_small[fy : fy + fh, fx : fx + fw]

            # Smile: search lower half of face
            lower_face = face_roi[fh // 2 :, :]
            if lower_face.size > 0:
                smiles = self._smile_cascade.detectMultiScale(
                    lower_face, scaleFactor=1.7, minNeighbors=15, minSize=(15, 15)
                )
                # More detections = higher confidence of a smile
                smile_score = min(len(smiles) / 3.0, 1.0)

            # Eyes: search upper half of face
            upper_face = face_roi[: fh // 2, :]
            if upper_face.size > 0:
                eyes = self._eye_cascade.detectMultiScale(
                    upper_face, scaleFactor=1.1, minNeighbors=5, minSize=(10, 10)
                )
                # 2 eyes detected = fully open, 0 = closed
                eye_openness = min(len(eyes) / 2.0, 1.0)

        # --- Motion detection (frame differencing) ---
        motion_level = 0.0
        if self._prev_gray is not None:
            diff = cv2.absdiff(self._prev_gray, gray_small)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            motion_level = float(np.count_nonzero(thresh)) / thresh.size
        self._prev_gray = gray_small

        # --- Compute composite tension ---
        #   face presence adds baseline tension
        #   smile and eye openness modulate it
        #   motion is strongest signal
        tension = 0.0
        if face_detected:
            tension += 0.3                          # someone is there
            tension += 0.2 * smile_score            # expression
            tension += 0.1 * abs(eye_openness - 0.5) * 2  # extreme eyes
        tension += 0.4 * min(motion_level * 5, 1.0)  # motion (scaled)
        tension = min(tension, 1.0)

        new_state = VisualState(
            timestamp=time.time(),
            face_detected=face_detected,
            num_faces=num_faces,
            smile_score=smile_score,
            eye_openness=eye_openness,
            motion_level=motion_level,
            tension=tension,
        )
        with self._lock:
            self._state = new_state


# ─── ScreenCapture ──────────────────────────────────────────────

class ScreenCapture:
    """Optional screen capture for context awareness.

    Uses screencapture (macOS built-in) to grab screenshots at very low
    frequency (default every 5s).  Converts to brightness + change metrics.
    """

    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self._state = ScreenState()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._prev_gray: Optional[np.ndarray] = None

    @property
    def state(self) -> ScreenState:
        with self._lock:
            return self._state

    @property
    def running(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=8.0)
            self._thread = None

    def _loop(self):
        import subprocess
        import tempfile
        import os

        while self._running:
            t0 = time.monotonic()
            try:
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tmp.close()
                # macOS screencapture: -x = no sound, -C = no cursor
                subprocess.run(
                    ["screencapture", "-x", "-C", tmp.name],
                    timeout=5, capture_output=True
                )
                img = cv2.imread(tmp.name, cv2.IMREAD_GRAYSCALE)
                os.unlink(tmp.name)

                if img is not None:
                    small = cv2.resize(img, (160, 120))
                    brightness = float(np.mean(small)) / 255.0
                    change_level = 0.0
                    if self._prev_gray is not None:
                        diff = cv2.absdiff(self._prev_gray, small)
                        change_level = float(np.mean(diff)) / 255.0
                    self._prev_gray = small

                    with self._lock:
                        self._state = ScreenState(
                            timestamp=time.time(),
                            brightness=brightness,
                            change_level=change_level,
                        )
            except Exception:
                pass  # screen capture is optional, never crash

            elapsed = time.monotonic() - t0
            sleep_time = self.interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)


# ─── SenseHub ───────────────────────────────────────────────────

class SenseHub:
    """Combines all sensor inputs into a unified tension vector.

    Usage:
        hub = SenseHub(enable_screen=False)
        hub.start()
        ...
        visual = hub.get_visual_tension()
        tensor = hub.to_tensor(dim=64)   # feed into ConsciousMind
        ...
        hub.stop()
    """

    def __init__(
        self,
        camera_index: int = 0,
        camera_fps: float = 3.0,
        enable_screen: bool = False,
        screen_interval: float = 5.0,
    ):
        self.camera = CameraInput(camera_index=camera_index, fps=camera_fps)
        self.camera_available = False
        self.screen: Optional[ScreenCapture] = None
        if enable_screen:
            self.screen = ScreenCapture(interval=screen_interval)
        self.vision_encoder = None
        self.spatial_aware = True  # spatial awareness flag

    # ─── Spatial Awareness Methods ──────────────────────────────

    def get_spatial_grid(self, grid_size: int = 3) -> torch.Tensor:
        """3x3 spatial grid: brightness + motion per region -> 18D tensor.

        Splits the camera frame conceptually into a grid_size x grid_size grid.
        Each cell produces two values: brightness and motion, for a total of
        grid_size * grid_size * 2 dimensions.
        """
        frame = self.camera.state
        if not frame.face_detected and frame.motion_level < 0.01:
            return torch.zeros(grid_size * grid_size * 2)
        # Simulate grid features from available data
        # In real implementation: split actual frame into grid cells
        result = torch.zeros(grid_size * grid_size * 2)
        # Use face position to estimate spatial location
        # brightness varies by region, motion concentrated where face is
        for i in range(grid_size):
            for j in range(grid_size):
                idx = (i * grid_size + j) * 2
                # Brightness: center brighter if face detected
                dist_from_center = abs(i - grid_size // 2) + abs(j - grid_size // 2)
                result[idx] = max(0.0, 1.0 - dist_from_center * 0.3) * frame.tension
                # Motion: concentrated near face
                result[idx + 1] = frame.motion_level * max(0.0, 1.0 - dist_from_center * 0.4)
        return result

    def get_vision_spatial(self, dim: int = 16) -> torch.Tensor:
        """Vision encoder spatial features -> dim-D tensor.

        If a vision encoder (e.g. SigLIP) is attached, extracts spatial
        features from it. Falls back to zeros when unavailable.
        """
        if self.vision_encoder is not None:
            # SigLIP already outputs spatial features
            try:
                features = self.vision_encoder.get_features()
                if features is not None:
                    flat = features.flatten()
                    return flat[:dim] if len(flat) >= dim else torch.cat(
                        [flat, torch.zeros(dim - len(flat))]
                    )
            except Exception:
                pass
        return torch.zeros(dim)

    def get_audio_spatial(self) -> torch.Tensor:
        """Stereo audio direction estimation -> 4D tensor.

        Returns [left, right, balance, intensity].
        When stereo audio data is available, left/right energy and their
        balance give a rudimentary directional estimate.
        Currently returns zeros as a placeholder until a stereo mic source
        is integrated.
        """
        # Placeholder: use available audio data or simulate
        return torch.zeros(4)

    def start(self):
        """Start all sensors. Camera failure does not prevent other sensors."""
        try:
            self.camera.start()
            # Give the camera thread a moment to detect permission issues
            time.sleep(0.5)
            if self.camera.running and not self.camera._permission_denied:
                self.camera_available = True
            else:
                self.camera_available = False
                if self.camera._permission_denied:
                    print("[senses] Continuing without camera")
        except Exception as e:
            print(f"[senses] Camera start failed: {e}")
            self.camera_available = False

        if self.screen is not None:
            self.screen.start()

    def stop(self):
        self.camera.stop()
        if self.screen is not None:
            self.screen.stop()

    def get_visual_tension(self) -> dict:
        """Current visual state as a plain dict."""
        s = self.camera.state
        return {
            "face_detected": s.face_detected,
            "num_faces": s.num_faces,
            "emotion_score": s.smile_score * 0.6 + s.eye_openness * 0.4,
            "motion_level": s.motion_level,
            "tension": s.tension,
            "timestamp": s.timestamp,
        }

    def get_screen_state(self) -> Optional[dict]:
        """Current screen state, or None if screen capture disabled."""
        if self.screen is None:
            return None
        s = self.screen.state
        return {
            "brightness": s.brightness,
            "change_level": s.change_level,
            "timestamp": s.timestamp,
        }

    def to_tensor(self, dim: int = 128) -> torch.Tensor:
        """Convert all sense data into a vector for PureField.

        Layout (first 16 dims are structured, rest is projection):
          [0]  face_detected (0/1)
          [1]  num_faces (normalized)
          [2]  smile_score
          [3]  eye_openness
          [4]  motion_level
          [5]  visual_tension (composite)
          [6]  screen_brightness  (0 if disabled)
          [7]  screen_change      (0 if disabled)
          [8-15] reserved

        Dims 16..dim-1: non-linear projection of [0..15] so the full
        vector carries the same information at higher dimensionality,
        letting PureField's linear layers pick up patterns.
        """
        raw = torch.zeros(16)

        vs = self.camera.state
        raw[0] = float(vs.face_detected)
        raw[1] = min(vs.num_faces / 5.0, 1.0)
        raw[2] = vs.smile_score
        raw[3] = vs.eye_openness
        raw[4] = min(vs.motion_level * 5.0, 1.0)
        raw[5] = vs.tension

        if self.screen is not None:
            ss = self.screen.state
            raw[6] = ss.brightness
            raw[7] = ss.change_level * 5.0

        # Spatial awareness: inject grid data into reserved slots [8:15]
        if self.spatial_aware:
            spatial_grid = self.get_spatial_grid()
            n_spatial = min(len(spatial_grid), 8)
            raw[8:8 + n_spatial] = spatial_grid[:n_spatial]

        # Project to target dim
        if dim <= 16:
            return raw[:dim].unsqueeze(0)

        # Deterministic non-linear expansion (no learned params)
        out = torch.zeros(dim)
        out[:16] = raw
        # Fill remaining dims with sin/cos projections of raw features
        # This spreads information across the vector space
        freqs = torch.arange(1, (dim - 16) // 2 + 2, dtype=torch.float32)
        active = raw[:8]  # the 8 sense channels
        for i, freq in enumerate(freqs):
            idx = 16 + i * 2
            if idx >= dim:
                break
            # Each frequency mixes a different sense channel
            ch = active[i % 8]
            out[idx] = torch.sin(freq * ch * 3.14159)
            if idx + 1 < dim:
                out[idx + 1] = torch.cos(freq * ch * 3.14159)

        return out.unsqueeze(0)  # (1, dim) to match ConsciousMind input

    def enable_vision_encoder(self, target_dim: int = 128, use_pretrained: bool = True, device: str = 'cpu'):
        """Enable VisionEncoder."""
        from vision_encoder import VisionEncoder
        self.vision_encoder = VisionEncoder(
            target_dim=target_dim,
            use_pretrained=use_pretrained,
            device=device,
        )

    def encode_vision(self, frame: np.ndarray) -> Optional[torch.Tensor]:
        """Encode frame with vision encoder. Returns None if encoder not available."""
        if self.vision_encoder is None:
            return None
        return self.vision_encoder.encode_frame(frame)

    def to_tensor_with_vision(self, frame: np.ndarray = None, dim: int = 128) -> torch.Tensor:
        """Combine vision embedding + sensor data.

        If vision encoder and frame available: 0.7*vision + 0.3*sensor
        Otherwise: return existing to_tensor()
        """
        sensor_tensor = self.to_tensor(dim=dim)

        if frame is not None and self.vision_encoder is not None:
            vision_tensor = self.encode_vision(frame).cpu()
            return _VISION_BLEND_WEIGHT * vision_tensor + _SENSOR_BLEND_WEIGHT * sensor_tensor

        return sensor_tensor


# ─── Convenience: quick test ────────────────────────────────────

def _test():
    """Quick smoke test -- opens camera for 5 seconds, prints states."""
    print("=== Anima Senses Test ===")
    print("Opening camera... (Ctrl+C to stop)")

    hub = SenseHub(camera_fps=3, enable_screen=False)
    hub.start()

    try:
        for _ in range(15):  # ~5 seconds at 3 prints/sec
            time.sleep(1.0)
            vis = hub.get_visual_tension()
            tensor = hub.to_tensor(dim=64)
            print(
                f"  face={vis['face_detected']}  "
                f"emotion={vis['emotion_score']:.2f}  "
                f"motion={vis['motion_level']:.3f}  "
                f"tension={vis['tension']:.2f}  "
                f"tensor_norm={tensor.norm():.3f}"
            )
    except KeyboardInterrupt:
        pass
    finally:
        hub.stop()
        print("Done.")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    _test()
