#!/usr/bin/env python3
"""Anima LiDAR Sense — iPhone LiDAR → Tension Fingerprint

Dolphin-grade 3D perception: depth + shape + distance → 128D fingerprint.

Pipeline:
  iPhone (Record3D app) → WiFi/USB → Mac (this module) → point cloud
  → 3D feature extraction → tension fingerprint → Tension Link

Setup:
  1. Install Record3D on iPhone (App Store, free)
  2. pip install record3d
  3. Connect iPhone via USB or same WiFi
  4. Open Record3D → start streaming
  5. python lidar_sense.py

Encodes:
  - Object shape (geometry)
  - Distance (depth histogram)
  - Size (bounding volume)
  - Surface texture (depth variance)
  - Spatial layout (where things are in 3D)
"""

import torch
import torch.nn as nn
import numpy as np
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, List

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



@dataclass
class LiDARFrame:
    """One frame of LiDAR data."""
    timestamp: float = 0.0
    depth_map: Optional[np.ndarray] = None       # (H, W) depth in meters
    rgb_frame: Optional[np.ndarray] = None        # (H, W, 3) color
    point_cloud: Optional[np.ndarray] = None      # (N, 3) xyz points
    confidence: Optional[np.ndarray] = None       # (H, W) confidence 0-2

    @property
    def valid(self):
        return self.depth_map is not None


@dataclass
class LiDAR3DFeatures:
    """Extracted 3D features from a LiDAR frame."""
    # Depth statistics
    depth_mean: float = 0.0
    depth_std: float = 0.0
    depth_min: float = 0.0
    depth_max: float = 0.0
    depth_histogram: np.ndarray = field(default_factory=lambda: np.zeros(16))

    # Spatial layout (3x3 grid depth averages)
    spatial_grid: np.ndarray = field(default_factory=lambda: np.zeros(9))

    # Shape features
    surface_roughness: float = 0.0    # depth gradient variance
    planarity: float = 0.0            # how flat is the scene
    object_count: int = 0             # estimated number of objects

    # Bounding volume
    volume_width: float = 0.0
    volume_height: float = 0.0
    volume_depth: float = 0.0

    # Center of mass
    center_x: float = 0.0
    center_y: float = 0.0
    center_z: float = 0.0

    def to_vector(self) -> np.ndarray:
        """Flatten all features into a fixed-size vector."""
        return np.concatenate([
            [self.depth_mean, self.depth_std, self.depth_min, self.depth_max],  # 4
            self.depth_histogram,                                                # 16
            self.spatial_grid,                                                   # 9
            [self.surface_roughness, self.planarity, self.object_count / 10.0],  # 3
            [self.volume_width, self.volume_height, self.volume_depth],          # 3
            [self.center_x, self.center_y, self.center_z],                       # 3
        ])  # Total: 38


class LiDAREncoder(nn.Module):
    """Encode 3D features into tension-compatible 128D vector.

    Like dolphin auditory cortex: raw 3D signal → compressed representation.
    """

    def __init__(self, input_dim=38, output_dim=128):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.GELU(),
            nn.Linear(64, 128),
            nn.GELU(),
            nn.Linear(128, output_dim),
        )
        # Initialize to spread information across output dims
        with torch.no_grad():
            for p in self.parameters():
                if p.dim() >= 2:
                    nn.init.orthogonal_(p)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """(batch, 38) → (batch, 128) tension-compatible vector."""
        return self.encoder(features)


def extract_3d_features(depth_map: np.ndarray, confidence: np.ndarray = None) -> LiDAR3DFeatures:
    """Extract 3D features from a depth map.

    Args:
        depth_map: (H, W) depth in meters. 0 = invalid.
        confidence: (H, W) optional confidence map.

    Returns:
        LiDAR3DFeatures with all extracted features.
    """
    feat = LiDAR3DFeatures()

    # Mask invalid pixels
    valid_mask = depth_map > 0.01
    if confidence is not None:
        valid_mask &= confidence >= 1  # medium+ confidence

    valid_depths = depth_map[valid_mask]

    if len(valid_depths) < 10:
        return feat

    # Depth statistics
    feat.depth_mean = float(np.mean(valid_depths))
    feat.depth_std = float(np.std(valid_depths))
    feat.depth_min = float(np.min(valid_depths))
    feat.depth_max = float(np.max(valid_depths))

    # Depth histogram (16 bins, 0-5 meters)
    hist, _ = np.histogram(valid_depths, bins=16, range=(0, 5.0))
    feat.depth_histogram = hist.astype(np.float32) / (len(valid_depths) + 1e-8)

    # Spatial grid (3x3 average depth)
    h, w = depth_map.shape
    grid = np.zeros(9)
    for i in range(3):
        for j in range(3):
            patch = depth_map[
                i * h // 3:(i + 1) * h // 3,
                j * w // 3:(j + 1) * w // 3
            ]
            valid_patch = patch[patch > 0.01]
            if len(valid_patch) > 0:
                grid[i * 3 + j] = np.mean(valid_patch)
    feat.spatial_grid = grid / 5.0  # normalize to 0-1

    # Surface roughness (gradient of depth)
    dy = np.diff(depth_map, axis=0)
    dx = np.diff(depth_map, axis=1)
    gradient_mag = np.sqrt(dy[:, :-1] ** 2 + dx[:-1, :] ** 2)
    valid_grad = gradient_mag[valid_mask[:-1, :-1]]
    if len(valid_grad) > 0:
        feat.surface_roughness = float(np.std(valid_grad))

    # Planarity (what fraction of depth values are close to median)
    median_depth = np.median(valid_depths)
    close_to_median = np.abs(valid_depths - median_depth) < 0.1
    feat.planarity = float(np.mean(close_to_median))

    # Object count (simple: count connected regions in thresholded depth)
    try:
        from scipy import ndimage
        # Foreground: closer than mean
        fg = (depth_map < feat.depth_mean) & valid_mask
        labeled, n_objects = ndimage.label(fg)
        feat.object_count = min(n_objects, 20)
    except ImportError:
        # Rough estimate from depth variance
        feat.object_count = max(1, int(feat.depth_std * 10))

    # Bounding volume (from valid points)
    ys, xs = np.where(valid_mask)
    if len(ys) > 0:
        feat.volume_width = float(xs.max() - xs.min()) / w
        feat.volume_height = float(ys.max() - ys.min()) / h
        feat.volume_depth = feat.depth_max - feat.depth_min

    # Center of mass
    if len(ys) > 0:
        weights = 1.0 / (valid_depths + 0.1)  # closer = heavier
        total_w = weights.sum()
        feat.center_x = float(np.average(xs / w, weights=weights))
        feat.center_y = float(np.average(ys / h, weights=weights))
        feat.center_z = float(np.average(valid_depths, weights=weights))

    return feat


class LiDARSense:
    """iPhone LiDAR → tension fingerprint pipeline.

    Usage:
        sense = LiDARSense()
        sense.start()  # connects to Record3D
        ...
        fingerprint = sense.get_fingerprint()  # 128D tensor
        ...
        sense.stop()
    """

    def __init__(self, device='cpu'):
        self.device = device
        self.encoder = LiDAREncoder()
        self._frame = LiDARFrame()
        self._features = LiDAR3DFeatures()
        self._lock = threading.Lock()
        self._running = False
        self._connected = False
        self._record3d_available = False

        try:
            import record3d
            self._record3d_available = True
        except ImportError:
            pass

    def start(self):
        """Connect to iPhone via Record3D and start streaming."""
        if not self._record3d_available:
            print("[LiDAR] record3d not installed. pip install record3d")
            print("[LiDAR] Running in synthetic mode for testing.")
            self._running = True
            return False

        import record3d

        self._running = True
        self._app = record3d.Record3DStream()
        self._app.on_new_frame = self._on_frame
        self._app.on_stream_stopped = self._on_stop

        # Find connected devices
        devs = self._app.get_connected_devices()
        if not devs:
            print("[LiDAR] No iPhone found. Connect via USB and open Record3D.")
            print("[LiDAR] Running in synthetic mode for testing.")
            return False

        print(f"[LiDAR] Found {len(devs)} device(s). Connecting...")
        self._app.connect(devs[0])
        self._connected = True
        print("[LiDAR] Connected! Streaming LiDAR data.")
        return True

    def stop(self):
        self._running = False
        self._connected = False

    def _on_frame(self):
        """Callback from Record3D when new frame arrives."""
        depth = self._app.get_depth_frame()
        rgb = self._app.get_rgb_frame()
        confidence = self._app.get_confidence_frame()

        frame = LiDARFrame(
            timestamp=time.time(),
            depth_map=depth,
            rgb_frame=rgb,
            confidence=confidence,
        )

        features = extract_3d_features(depth, confidence)

        with self._lock:
            self._frame = frame
            self._features = features

    def _on_stop(self):
        print("[LiDAR] Stream stopped.")
        self._connected = False

    def get_frame(self) -> LiDARFrame:
        with self._lock:
            return self._frame

    def get_features(self) -> LiDAR3DFeatures:
        with self._lock:
            return self._features

    def get_fingerprint(self) -> torch.Tensor:
        """Get current LiDAR data as 128D tension-compatible fingerprint."""
        with self._lock:
            feat = self._features

        vec = torch.tensor(feat.to_vector(), dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            fingerprint = self.encoder(vec)
        return fingerprint  # (1, 128)

    def get_blended_tensor(self, text_vec: torch.Tensor, blend=0.5) -> torch.Tensor:
        """Blend LiDAR fingerprint with text vector for ConsciousMind input.

        Args:
            text_vec: (1, 128) text-based input vector
            blend: 0=text only, 1=lidar only, 0.5=equal mix
        """
        lidar_fp = self.get_fingerprint()
        return (1 - blend) * text_vec + blend * lidar_fp

    # --- Synthetic data for testing without iPhone ---

    @staticmethod
    def generate_synthetic_depth(scene='sphere', h=192, w=256) -> np.ndarray:
        """Generate synthetic depth maps for testing."""
        depth = np.zeros((h, w), dtype=np.float32)
        ys, xs = np.mgrid[0:h, 0:w]
        ys = ys.astype(np.float32) / h
        xs = xs.astype(np.float32) / w

        if scene == 'sphere':
            # Sphere at center, 2m away
            cx, cy = 0.5, 0.5
            r = 0.3
            dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
            mask = dist < r
            depth[mask] = 2.0 - np.sqrt(r ** 2 - dist[mask] ** 2) * 2

        elif scene == 'wall':
            # Flat wall at 3m
            depth[:] = 3.0 + np.random.normal(0, 0.01, (h, w))

        elif scene == 'person':
            # Person-like shape at 1.5m
            # Head
            head_mask = ((xs - 0.5) ** 2 + (ys - 0.2) ** 2) < 0.04
            depth[head_mask] = 1.5
            # Body
            body_mask = (np.abs(xs - 0.5) < 0.12) & (ys > 0.3) & (ys < 0.8)
            depth[body_mask] = 1.6

        elif scene == 'corridor':
            # Corridor: walls on sides, floor below
            depth[:] = 5.0  # far wall
            # Left wall (closer as you go left)
            for x in range(w // 4):
                depth[:, x] = 1.0 + x / (w // 4) * 4.0
            # Right wall
            for x in range(3 * w // 4, w):
                depth[:, x] = 1.0 + (w - x) / (w // 4) * 4.0
            # Floor
            for y in range(2 * h // 3, h):
                depth[y, :] = 1.0 + (y - 2 * h // 3) / (h // 3) * 2.0

        elif scene == 'table_objects':
            # Table at 1m with objects
            depth[h // 2:, :] = 1.0  # table surface
            # Cup (cylinder)
            cup_mask = ((xs - 0.3) ** 2 + (ys - 0.4) ** 2) < 0.01
            depth[cup_mask] = 0.8
            # Box
            box_mask = (np.abs(xs - 0.7) < 0.08) & (np.abs(ys - 0.4) < 0.06)
            depth[box_mask] = 0.85

        elif scene == 'outdoor':
            # Ground plane + distant objects
            depth[:] = 0.0
            # Ground (y > 0.6)
            ground_mask = ys > 0.6
            depth[ground_mask] = 2.0 + (ys[ground_mask] - 0.6) * 5
            # Nearby object
            obj_mask = ((xs - 0.3) ** 2 + (ys - 0.4) ** 2) < 0.02
            depth[obj_mask] = 1.5
            # Far object
            far_mask = ((xs - 0.7) ** 2 + (ys - 0.3) ** 2) < 0.01
            depth[far_mask] = 4.0

        # Add noise
        noise = np.random.normal(0, 0.005, depth.shape).astype(np.float32)
        depth = np.maximum(depth + noise, 0)

        return depth


def test_synthetic():
    """Test the full pipeline with synthetic LiDAR data."""
    print("=" * 60)
    print("  LiDAR Sense — Synthetic Pipeline Test")
    print("  (no iPhone needed)")
    print("=" * 60)

    sense = LiDARSense()
    scenes = ['sphere', 'wall', 'person', 'corridor', 'table_objects', 'outdoor']

    print("\n  Extracting 3D features from synthetic depth maps...")
    fingerprints = {}

    for scene in scenes:
        depth = LiDARSense.generate_synthetic_depth(scene)
        features = extract_3d_features(depth)
        vec = torch.tensor(features.to_vector(), dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            fp = sense.encoder(vec)

        fingerprints[scene] = fp.squeeze()

        print(f"\n  [{scene}]")
        print(f"    depth: mean={features.depth_mean:.2f}m  std={features.depth_std:.2f}m  "
              f"range=[{features.depth_min:.2f}, {features.depth_max:.2f}]m")
        print(f"    roughness={features.surface_roughness:.4f}  planarity={features.planarity:.2f}  "
              f"objects={features.object_count}")
        print(f"    volume: {features.volume_width:.2f}w × {features.volume_height:.2f}h × {features.volume_depth:.2f}d")
        print(f"    center: ({features.center_x:.2f}, {features.center_y:.2f}, {features.center_z:.2f})")
        print(f"    fingerprint norm: {fp.norm():.2f}")

    # Similarity matrix
    print(f"\n  Cosine similarity between scene fingerprints:")
    print(f"  {'':>14}", end="")
    for s in scenes:
        print(f"  {s[:6]:>6}", end="")
    print()

    for i, s1 in enumerate(scenes):
        print(f"  {s1:>14}", end="")
        for j, s2 in enumerate(scenes):
            sim = torch.nn.functional.cosine_similarity(
                fingerprints[s1].unsqueeze(0),
                fingerprints[s2].unsqueeze(0)
            ).item()
            if i == j:
                print(f"  {'1.00':>6}", end="")
            else:
                print(f"  {sim:>6.3f}", end="")
        print()

    # Classification test
    print(f"\n  Training scene classifier on fingerprints...")
    import torch.nn as nn

    fps_all, labels_all = [], []
    for label, scene in enumerate(scenes):
        for _ in range(50):
            depth = LiDARSense.generate_synthetic_depth(scene)
            features = extract_3d_features(depth)
            vec = torch.tensor(features.to_vector(), dtype=torch.float32).unsqueeze(0)
            with torch.no_grad():
                fp_vec = sense.encoder(vec)
            fps_all.append(fp_vec.squeeze())
            labels_all.append(label)

    X = torch.stack(fps_all)
    y = torch.tensor(labels_all)
    n = len(X)
    idx = torch.randperm(n)
    split = int(n * 0.75)

    model = nn.Sequential(
        nn.Linear(128, 64), nn.GELU(),
        nn.Linear(64, len(scenes)),
    )
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)

    for ep in range(200):
        model.train()
        perm = torch.randperm(split)
        for i in range(0, split, 32):
            batch = perm[i:i+32]
            loss = nn.CrossEntropyLoss()(model(X[idx[batch]]), y[idx[batch]])
            opt.zero_grad(); loss.backward(); opt.step()

    model.eval()
    with torch.no_grad():
        preds = model(X[idx[split:]]).argmax(dim=-1)
        acc = (preds == y[idx[split:]]).float().mean().item()

    print(f"  Scene classification accuracy: {acc*100:.1f}% (random={100/len(scenes):.1f}%)")

    for label, scene in enumerate(scenes):
        mask = y[idx[split:]] == label
        if mask.sum() > 0:
            scene_acc = (preds[mask] == y[idx[split:]][mask]).float().mean().item()
            print(f"    {scene:>14}: {scene_acc*100:.0f}%")

    print(f"\n  Pipeline: iPhone LiDAR → depth map → 3D features → 128D fingerprint → Tension Link")
    print(f"  Status: {'Record3D available' if sense._record3d_available else 'Record3D not installed (pip install record3d)'}")


if __name__ == "__main__":
    test_synthetic()
