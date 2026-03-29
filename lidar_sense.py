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
