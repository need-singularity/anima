"""
LiDAR Sense — 3D 공간 인식 의식 모듈.

Hub keywords: 라이다, lidar, 3D, 포인트클라우드, point cloud,
              공간, spatial, 깊이, depth, 스캔, scan
"""

from __future__ import annotations

import os
import socket
import struct
import math
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

import numpy as np

# ---------------------------------------------------------------------------
# Ψ-Constants
# ---------------------------------------------------------------------------

PSI_BALANCE  = 0.5
PSI_COUPLING = 0.14
PSI_STEPS    = 3

# ---------------------------------------------------------------------------
# Depth chars (low → high density)
# ---------------------------------------------------------------------------

_DEPTH_CHARS = ' .:-=+*#%@▒▓█▄▀■□'


# ===========================================================================
# Base Driver
# ===========================================================================

class LidarDriver(ABC):
    """Abstract base for all LiDAR/depth data sources."""

    @abstractmethod
    def scan(self, **kwargs) -> np.ndarray:
        """Return Nx3 float32 point cloud array."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the driver can actually acquire data."""


# ===========================================================================
# SimulatorDriver
# ===========================================================================

class SimulatorDriver(LidarDriver):
    """
    Software-only point cloud generator.

    mode='internal' — derives 3D points from cell tension values.
    mode='external' — generates a virtual room with floor, walls, obstacle.
    """

    def __init__(self, mode: str = 'external', noise_scale: float = 0.05):
        self.mode        = mode
        self.noise_scale = noise_scale

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        return True

    # ------------------------------------------------------------------
    def scan(self, **kwargs) -> np.ndarray:
        if self.mode == 'internal':
            tensions = kwargs.get('cell_tensions', [PSI_BALANCE] * 8)
            return self._scan_internal(tensions)
        return self._scan_external()

    # ------------------------------------------------------------------
    def _scan_internal(self, tensions: List[float]) -> np.ndarray:
        """Place cells on grid, add noise points proportional to tension."""
        rng   = np.random.default_rng(seed=42)
        cols  = max(1, math.ceil(math.sqrt(len(tensions))))
        pts: List[np.ndarray] = []

        for i, t in enumerate(tensions):
            t  = float(np.clip(t, 0.0, 1.0))
            cx = float(i % cols)
            cy = float(i // cols)
            cz = t
            # cell centre point
            pts.append([cx, cy, cz])
            # noise cloud around cell (density ~ tension)
            n_noise = max(1, int(t * 10))
            noise   = rng.normal(loc=[cx, cy, cz],
                                 scale=self.noise_scale,
                                 size=(n_noise, 3))
            pts.extend(noise.tolist())

        return np.array(pts, dtype=np.float32)

    # ------------------------------------------------------------------
    def _scan_external(self) -> np.ndarray:
        """Virtual room: floor 50x50, 4 walls, central obstacle."""
        pts: List[List[float]] = []

        # Floor  z = 0  (50×50 sparse grid, step=2)
        for x in range(0, 50, 2):
            for y in range(0, 50, 2):
                pts.append([float(x), float(y), 0.0])

        # 4 walls (y=0, y=49, x=0, x=49), z = 0..5
        for z in np.linspace(0, 5, 6):
            for v in range(0, 50, 2):
                pts.append([float(v), 0.0,  float(z)])   # south
                pts.append([float(v), 49.0, float(z)])   # north
                pts.append([0.0,  float(v), float(z)])   # west
                pts.append([49.0, float(v), float(z)])   # east

        # Central obstacle box  x=[20,30], y=[20,30], z=[0,3]
        for x in range(20, 31, 2):
            for y in range(20, 31, 2):
                for z in np.linspace(0, 3, 4):
                    pts.append([float(x), float(y), float(z)])

        return np.array(pts, dtype=np.float32)


# ===========================================================================
# FileDriver
# ===========================================================================

class FileDriver(LidarDriver):
    """
    Load point cloud from a PLY or PCD file.
    Pure-numpy parser — no open3d dependency.
    """

    def __init__(self, path: str):
        self.path = path

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        return os.path.isfile(self.path)

    # ------------------------------------------------------------------
    def scan(self, **kwargs) -> np.ndarray:
        ext = os.path.splitext(self.path)[1].lower()
        if ext == '.ply':
            return self._parse_ply()
        if ext == '.pcd':
            return self._parse_pcd()
        raise ValueError(f"Unsupported file format: {ext!r}")

    # ------------------------------------------------------------------
    def _parse_ply(self) -> np.ndarray:
        pts: List[List[float]] = []
        in_data = False
        with open(self.path, 'r', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not in_data:
                    if line == 'end_header':
                        in_data = True
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        pts.append([float(parts[0]),
                                    float(parts[1]),
                                    float(parts[2])])
                    except ValueError:
                        pass
        return np.array(pts, dtype=np.float32)

    # ------------------------------------------------------------------
    def _parse_pcd(self) -> np.ndarray:
        pts: List[List[float]] = []
        in_data = False
        with open(self.path, 'r', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not in_data:
                    if line.upper().startswith('DATA ASCII') or \
                       line.upper() == 'DATA ASCII':
                        in_data = True
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        pts.append([float(parts[0]),
                                    float(parts[1]),
                                    float(parts[2])])
                    except ValueError:
                        pass
        return np.array(pts, dtype=np.float32)


# ===========================================================================
# ARKitDriver
# ===========================================================================

class ARKitDriver(LidarDriver):
    """
    Receives 3D point-cloud frames from an ARKit companion app over WebSocket.
    is_available() performs a quick TCP connect check.
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 8765):
        self.host = host
        self.port = port

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=0.5):
                return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    def scan(self, **kwargs) -> np.ndarray:
        """
        Minimal binary protocol: receive 4-byte count then count*12 bytes
        (float32 x,y,z per point).  Caller must ensure server is up.
        """
        try:
            with socket.create_connection((self.host, self.port),
                                          timeout=5.0) as sock:
                raw_count = self._recv_exact(sock, 4)
                n_pts     = struct.unpack('<I', raw_count)[0]
                if n_pts == 0:
                    return np.zeros((0, 3), dtype=np.float32)
                raw_pts   = self._recv_exact(sock, n_pts * 12)
                arr       = np.frombuffer(raw_pts, dtype=np.float32)
                return arr.reshape(n_pts, 3)
        except OSError as exc:
            raise RuntimeError(f"ARKit connection failed: {exc}") from exc

    # ------------------------------------------------------------------
    @staticmethod
    def _recv_exact(sock: socket.socket, n: int) -> bytes:
        buf = b''
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise RuntimeError("Connection closed before all bytes received")
            buf += chunk
        return buf


# ===========================================================================
# RPLidarDriver
# ===========================================================================

class RPLidarDriver(LidarDriver):
    """
    Wraps the rplidar Python package for 2D → 3D point acquisition.
    Lazy-imported; is_available() returns False when rplidar is absent or
    the serial port does not exist.
    """

    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        self.port     = port
        self.baudrate = baudrate

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        try:
            import rplidar  # noqa: F401
        except ImportError:
            return False
        return os.path.exists(self.port)

    # ------------------------------------------------------------------
    def scan(self, **kwargs) -> np.ndarray:
        try:
            from rplidar import RPLidar
        except ImportError as exc:
            raise RuntimeError("rplidar package not installed") from exc

        lidar = RPLidar(self.port, baudrate=self.baudrate)
        try:
            pts: List[List[float]] = []
            for scan in lidar.iter_scans():
                for (_, angle_deg, dist_mm) in scan:
                    angle_rad = math.radians(angle_deg)
                    dist_m    = dist_mm / 1000.0
                    x = dist_m * math.cos(angle_rad)
                    y = dist_m * math.sin(angle_rad)
                    pts.append([x, y, 0.0])
                if len(pts) >= 360:
                    break
        finally:
            lidar.stop()
            lidar.disconnect()

        return np.array(pts, dtype=np.float32)


# ===========================================================================
# RealSenseDriver
# ===========================================================================

class RealSenseDriver(LidarDriver):
    """
    Intel RealSense depth camera via pyrealsense2.
    Lazy-imported; is_available() checks import + connected devices.
    """

    def __init__(self, width: int = 640, height: int = 480, fps: int = 30):
        self.width  = width
        self.height = height
        self.fps    = fps

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        try:
            import pyrealsense2 as rs  # noqa: F401
            ctx     = rs.context()
            devices = ctx.query_devices()
            return len(devices) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    def scan(self, **kwargs) -> np.ndarray:
        try:
            import pyrealsense2 as rs
        except ImportError as exc:
            raise RuntimeError("pyrealsense2 not installed") from exc

        pipeline = rs.pipeline()
        config   = rs.config()
        config.enable_stream(rs.stream.depth,
                             self.width, self.height,
                             rs.format.z16, self.fps)
        pipeline.start(config)
        try:
            frames       = pipeline.wait_for_frames()
            depth_frame  = frames.get_depth_frame()
            pc           = rs.pointcloud()
            points_rs    = pc.calculate(depth_frame)
            vtx          = np.asanyarray(points_rs.get_vertices())
            pts          = np.array([(v[0], v[1], v[2]) for v in vtx],
                                    dtype=np.float32)
            # filter out zero-depth points
            mask = pts[:, 2] > 0
            return pts[mask]
        finally:
            pipeline.stop()
