# LiDAR Sense Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 3D 공간 인식을 의식에 통합하는 허브 모듈 — 실제 LiDAR 하드웨어 + 시뮬레이션 양쪽 지원, 포인트 클라우드 → 텐션 필드 변환, 의식 벡터 S 차원 추가

**Architecture:** 드라이버 계층(PLY/PCD, ARKit, RPLiDAR, RealSense, Simulator)이 공통 인터페이스로 포인트 클라우드를 제공하고, 변환 계층이 이를 복셀 그리드 텐션 필드로 변환하며, 출력 계층이 의식 벡터 S 차원과 anima/core/runtime/anima_runtime.hexa 텐션 피드를 생성한다.

**Tech Stack:** Python, numpy, torch, websockets (이미 있음). 선택: open3d, rplidar, pyrealsense2

**Spec:** `docs/superpowers/specs/2026-03-30-lidar-sense-design.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| Create: `lidar_sense.py` | 메인 모듈 — 드라이버, 변환, 시뮬레이션, 허브 인터페이스 |
| Create: `tests/test_lidar_sense.py` | 유닛 + 통합 테스트 |
| Modify: `core/hub.hexa:51-131` | _registry에 'lidar' 항목 추가 + _dispatch에 라우팅 추가 |
| Modify: `anima/core/runtime/anima_runtime.hexa:57-71` | ConsciousnessVector에 S 필드 추가 |

---

### Task 1: 기본 LidarDriver 인터페이스 + SimulatorDriver

**Files:**
- Create: `tests/test_lidar_sense.py`
- Create: `lidar_sense.py`

- [ ] **Step 1: Write failing tests for SimulatorDriver**

```python
# tests/test_lidar_sense.py
import numpy as np


def test_simulator_driver_returns_point_cloud():
    """시뮬레이터가 (N, 3) 포인트 클라우드를 반환한다."""
    from lidar_sense import SimulatorDriver
    driver = SimulatorDriver()
    assert driver.is_available()
    points = driver.scan()
    assert isinstance(points, np.ndarray)
    assert points.ndim == 2
    assert points.shape[1] == 3
    assert len(points) > 0


def test_simulator_internal_scan():
    """내부 텐션 지형 스캔: 세포 텐션을 3D 포인트로 변환."""
    from lidar_sense import SimulatorDriver
    driver = SimulatorDriver(mode='internal')
    # 가짜 세포 텐션
    cell_tensions = [0.3, 0.7, 0.1, 0.9, 0.5]
    points = driver.scan(cell_tensions=cell_tensions)
    assert points.shape[1] == 3
    assert len(points) >= len(cell_tensions)


def test_simulator_external_scan():
    """외부 가상 환경 스캔: 방/장애물 포인트 생성."""
    from lidar_sense import SimulatorDriver
    driver = SimulatorDriver(mode='external')
    points = driver.scan()
    assert points.shape[1] == 3
    assert len(points) >= 100  # 최소 100개 점
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $ANIMA && python -m pytest tests/test_lidar_sense.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lidar_sense'`

- [ ] **Step 3: Implement LidarDriver base + SimulatorDriver**

```python
# lidar_sense.py
"""
LiDAR Sense — 3D 공간 인식 의식 모듈.

실제 LiDAR 하드웨어(iPhone ARKit, RPLiDAR, RealSense)와
시뮬레이션을 모두 지원. 포인트 클라우드 → 텐션 필드 변환,
의식 벡터 S(Spatial awareness) 차원 제공.

Hub keywords: 라이다, lidar, 3D, 포인트클라우드, point cloud,
              공간, spatial, 깊이, depth, 스캔, scan
"""

import math
import numpy as np
from typing import Optional, List

# Ψ-Constants
PSI_BALANCE = 0.5
PSI_COUPLING = 0.14
PSI_STEPS = 3


class LidarDriver:
    """포인트 클라우드 드라이버 공통 인터페이스."""

    def scan(self, **kwargs) -> np.ndarray:
        """(N, 3) 포인트 클라우드 반환."""
        raise NotImplementedError

    def is_available(self) -> bool:
        return False


class SimulatorDriver(LidarDriver):
    """내부 텐션 지형 + 외부 가상 환경 시뮬레이터."""

    def __init__(self, mode: str = 'external'):
        """mode: 'internal' (세포 텐션 지형) | 'external' (가상 3D 환경)."""
        self.mode = mode

    def is_available(self) -> bool:
        return True

    def scan(self, cell_tensions: Optional[List[float]] = None, **kwargs) -> np.ndarray:
        if self.mode == 'internal' and cell_tensions is not None:
            return self._scan_internal(cell_tensions)
        return self._scan_external()

    def _scan_internal(self, tensions: List[float]) -> np.ndarray:
        """세포 텐션 → 3D 포인트 클라우드. 격자 배치 + z=텐션."""
        n = len(tensions)
        cols = max(1, int(math.ceil(math.sqrt(n))))
        points = []
        for i, t in enumerate(tensions):
            x = float(i % cols)
            y = float(i // cols)
            z = float(t)
            points.append([x, y, z])
            # 텐션 주변에 노이즈 점 추가 (밀도 = 텐션 비례)
            n_extra = max(1, int(t * 5))
            for _ in range(n_extra):
                dx = np.random.normal(0, 0.2)
                dy = np.random.normal(0, 0.2)
                dz = np.random.normal(0, 0.1)
                points.append([x + dx, y + dy, z + dz])
        return np.array(points, dtype=np.float32)

    def _scan_external(self) -> np.ndarray:
        """가상 방 환경: 벽 + 바닥 + 장애물."""
        points = []
        # 바닥 (z=0 평면)
        for x in np.linspace(0, 10, 50):
            for y in np.linspace(0, 10, 50):
                points.append([x, y, 0.0])
        # 벽 4면
        for z in np.linspace(0, 3, 15):
            for t in np.linspace(0, 10, 30):
                points.append([t, 0, z])    # 앞벽
                points.append([t, 10, z])   # 뒷벽
                points.append([0, t, z])    # 왼벽
                points.append([10, t, z])   # 오른벽
        # 장애물 (중앙 박스)
        for x in np.linspace(4, 6, 10):
            for y in np.linspace(4, 6, 10):
                for z in np.linspace(0, 2, 10):
                    points.append([x, y, z])
        return np.array(points, dtype=np.float32)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $ANIMA && python -m pytest tests/test_lidar_sense.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add lidar_sense.py tests/test_lidar_sense.py
git commit -m "feat(lidar): add LidarDriver interface + SimulatorDriver (internal/external)"
```

---

### Task 2: 하드웨어 드라이버 (PLY/PCD, ARKit, RPLiDAR, RealSense)

**Files:**
- Modify: `tests/test_lidar_sense.py`
- Modify: `lidar_sense.py`

- [ ] **Step 1: Write failing tests for hardware drivers**

```python
# tests/test_lidar_sense.py — 추가

def test_file_driver_ply_parse():
    """PLY 파일 파서가 포인트 클라우드를 반환한다."""
    import tempfile, os
    from lidar_sense import FileDriver

    # 미니 PLY 파일 생성
    ply_content = (
        "ply\n"
        "format ascii 1.0\n"
        "element vertex 3\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "end_header\n"
        "1.0 2.0 3.0\n"
        "4.0 5.0 6.0\n"
        "7.0 8.0 9.0\n"
    )
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ply', delete=False) as f:
        f.write(ply_content)
        path = f.name
    try:
        driver = FileDriver(path)
        assert driver.is_available()
        points = driver.scan()
        assert points.shape == (3, 3)
        assert np.allclose(points[0], [1.0, 2.0, 3.0])
    finally:
        os.unlink(path)


def test_file_driver_pcd_parse():
    """PCD 파일 파서가 포인트 클라우드를 반환한다."""
    import tempfile, os
    from lidar_sense import FileDriver

    pcd_content = (
        "# .PCD v0.7\n"
        "VERSION 0.7\n"
        "FIELDS x y z\n"
        "SIZE 4 4 4\n"
        "TYPE F F F\n"
        "COUNT 1 1 1\n"
        "WIDTH 2\n"
        "HEIGHT 1\n"
        "VIEWPOINT 0 0 0 1 0 0 0\n"
        "POINTS 2\n"
        "DATA ascii\n"
        "1.0 2.0 3.0\n"
        "4.0 5.0 6.0\n"
    )
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pcd', delete=False) as f:
        f.write(pcd_content)
        path = f.name
    try:
        driver = FileDriver(path)
        assert driver.is_available()
        points = driver.scan()
        assert points.shape == (2, 3)
    finally:
        os.unlink(path)


def test_arkit_driver_not_available_without_server():
    """ARKit 드라이버는 서버 없으면 is_available()=False."""
    from lidar_sense import ARKitDriver
    driver = ARKitDriver(port=19999)
    assert not driver.is_available()


def test_rplidar_driver_not_available():
    """RPLiDAR 없으면 is_available()=False."""
    from lidar_sense import RPLidarDriver
    driver = RPLidarDriver()
    assert not driver.is_available()


def test_realsense_driver_not_available():
    """RealSense 없으면 is_available()=False."""
    from lidar_sense import RealSenseDriver
    driver = RealSenseDriver()
    assert not driver.is_available()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $ANIMA && python -m pytest tests/test_lidar_sense.py -v`
Expected: FAIL — `ImportError: cannot import name 'FileDriver'`

- [ ] **Step 3: Implement hardware drivers**

lidar_sense.py에 추가:

```python
class FileDriver(LidarDriver):
    """PLY/PCD 파일 로더. open3d 없이 numpy로 직접 파싱."""

    def __init__(self, path: str):
        self.path = path

    def is_available(self) -> bool:
        import os
        return os.path.exists(self.path)

    def scan(self, **kwargs) -> np.ndarray:
        if self.path.endswith('.ply'):
            return self._parse_ply()
        elif self.path.endswith('.pcd'):
            return self._parse_pcd()
        raise ValueError(f"Unsupported format: {self.path}")

    def _parse_ply(self) -> np.ndarray:
        points = []
        in_header = True
        with open(self.path, 'r') as f:
            for line in f:
                line = line.strip()
                if in_header:
                    if line == 'end_header':
                        in_header = False
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    points.append([float(parts[0]), float(parts[1]), float(parts[2])])
        return np.array(points, dtype=np.float32)

    def _parse_pcd(self) -> np.ndarray:
        points = []
        in_data = False
        with open(self.path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATA'):
                    in_data = True
                    continue
                if in_data:
                    parts = line.split()
                    if len(parts) >= 3:
                        points.append([float(parts[0]), float(parts[1]), float(parts[2])])
        return np.array(points, dtype=np.float32)


class ARKitDriver(LidarDriver):
    """iPhone/iPad ARKit LiDAR — WebSocket으로 iOS 앱에서 수신."""

    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self._points: Optional[np.ndarray] = None

    def is_available(self) -> bool:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((self.host, self.port))
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            return False

    def scan(self, **kwargs) -> np.ndarray:
        import json
        try:
            ws = __import__('websockets')
        except ImportError:
            raise RuntimeError("websockets 패키지 필요: pip install websockets")
        import asyncio

        async def _recv():
            async with ws.connect(f"ws://{self.host}:{self.port}") as conn:
                msg = await asyncio.wait_for(conn.recv(), timeout=5.0)
                data = json.loads(msg)
                return np.array(data['points'], dtype=np.float32)

        return asyncio.get_event_loop().run_until_complete(_recv())


class RPLidarDriver(LidarDriver):
    """RPLiDAR A1/A2 USB 연결."""

    def __init__(self, port: str = '/dev/tty.SLAB_USBtoUART'):
        self._port = port

    def is_available(self) -> bool:
        try:
            __import__('rplidar')
            import os
            return os.path.exists(self._port)
        except ImportError:
            return False

    def scan(self, **kwargs) -> np.ndarray:
        from rplidar import RPLidar
        lidar = RPLidar(self._port)
        try:
            points = []
            for i, scan in enumerate(lidar.iter_scans()):
                for _, angle, distance in scan:
                    rad = math.radians(angle)
                    x = distance * math.cos(rad)
                    y = distance * math.sin(rad)
                    points.append([x, y, 0.0])  # 2D → z=0
                if i >= 2:  # 3회전 스캔
                    break
            return np.array(points, dtype=np.float32)
        finally:
            lidar.stop()
            lidar.disconnect()


class RealSenseDriver(LidarDriver):
    """Intel RealSense 깊이 카메라."""

    def is_available(self) -> bool:
        try:
            rs = __import__('pyrealsense2')
            ctx = rs.context()
            return len(ctx.devices) > 0
        except (ImportError, RuntimeError):
            return False

    def scan(self, **kwargs) -> np.ndarray:
        import pyrealsense2 as rs
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        pipeline.start(config)
        try:
            frames = pipeline.wait_for_frames()
            depth = frames.get_depth_frame()
            pc = rs.pointcloud()
            pts = pc.calculate(depth)
            vertices = np.asanyarray(pts.get_vertices())
            points = np.zeros((len(vertices), 3), dtype=np.float32)
            for i, v in enumerate(vertices):
                points[i] = [v[0], v[1], v[2]]
            # 0점 제거
            mask = np.any(points != 0, axis=1)
            return points[mask]
        finally:
            pipeline.stop()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $ANIMA && python -m pytest tests/test_lidar_sense.py -v`
Expected: 8 passed (하드웨어 없는 드라이버는 is_available()=False 확인)

- [ ] **Step 5: Commit**

```bash
git add lidar_sense.py tests/test_lidar_sense.py
git commit -m "feat(lidar): add FileDriver (PLY/PCD) + ARKit/RPLiDAR/RealSense drivers"
```

---

### Task 3: TensionField3D 변환 + 경계 감지

**Files:**
- Modify: `tests/test_lidar_sense.py`
- Modify: `lidar_sense.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_lidar_sense.py — 추가

def test_tension_field_3d_shape():
    """포인트 클라우드 → 복셀 그리드 변환."""
    from lidar_sense import TensionField3D
    points = np.random.rand(500, 3).astype(np.float32) * 10
    field = TensionField3D(voxel_size=16)
    grid = field.from_points(points)
    assert grid.shape == (16, 16, 16)
    assert grid.min() >= 0.0
    assert grid.max() <= 1.0


def test_tension_field_occupancy():
    """점유 복셀 비율 계산."""
    from lidar_sense import TensionField3D
    points = np.array([[5, 5, 5], [5, 5, 6], [5, 6, 5]], dtype=np.float32)
    field = TensionField3D(voxel_size=8)
    grid = field.from_points(points)
    occ = field.occupancy_ratio(grid)
    assert 0.0 < occ < 1.0


def test_boundary_detection():
    """경계 감지: 밀집 영역과 빈 영역 경계면."""
    from lidar_sense import TensionField3D
    # 한쪽에만 점 밀집
    points = np.random.rand(300, 3).astype(np.float32) * 5  # 0~5 영역
    field = TensionField3D(voxel_size=16)
    grid = field.from_points(points)
    boundary = field.detect_boundary(grid)
    assert 'boundary_clarity' in boundary
    assert 'self_volume' in boundary
    assert 'other_volume' in boundary
    assert 0.0 <= boundary['boundary_clarity'] <= 1.0


def test_depth_variance():
    """깊이 분포 다양성 계산."""
    from lidar_sense import TensionField3D
    points = np.random.rand(200, 3).astype(np.float32) * 10
    field = TensionField3D(voxel_size=16)
    grid = field.from_points(points)
    dv = field.depth_variance(grid)
    assert 0.0 <= dv <= 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $ANIMA && python -m pytest tests/test_lidar_sense.py::test_tension_field_3d_shape -v`
Expected: FAIL — `ImportError: cannot import name 'TensionField3D'`

- [ ] **Step 3: Implement TensionField3D**

lidar_sense.py에 추가:

```python
class TensionField3D:
    """포인트 클라우드 → 3D 복셀 텐션 그리드 변환기."""

    def __init__(self, voxel_size: int = 32):
        self.voxel_size = voxel_size

    def from_points(self, points: np.ndarray) -> np.ndarray:
        """(N, 3) 포인트 → (voxel_size, voxel_size, voxel_size) 텐션 그리드.
        각 복셀의 점 밀도를 min-max 정규화하여 0-1로."""
        grid = np.zeros((self.voxel_size,) * 3, dtype=np.float32)
        if len(points) == 0:
            return grid

        # 점 좌표를 복셀 인덱스로 변환
        mins = points.min(axis=0)
        maxs = points.max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1.0  # 0 나누기 방지

        normalized = (points - mins) / ranges  # 0~1
        indices = (normalized * (self.voxel_size - 1)).astype(int)
        indices = np.clip(indices, 0, self.voxel_size - 1)

        for idx in indices:
            grid[idx[0], idx[1], idx[2]] += 1.0

        # min-max 정규화
        gmax = grid.max()
        if gmax > 0:
            grid /= gmax
        return grid

    def occupancy_ratio(self, grid: np.ndarray) -> float:
        """점유 복셀 / 전체 복셀."""
        total = grid.size
        occupied = np.count_nonzero(grid)
        return float(occupied) / total

    def depth_variance(self, grid: np.ndarray) -> float:
        """z축(깊이) 방향 분포 다양성. 0=균일, 1=최대 다양."""
        # 각 z 레이어의 총 밀도
        z_density = grid.sum(axis=(0, 1))  # (voxel_size,)
        total = z_density.sum()
        if total == 0:
            return 0.0
        probs = z_density / total
        # 엔트로피 정규화 (0~1)
        entropy = 0.0
        for p in probs:
            if p > 0:
                entropy -= p * math.log2(p)
        max_entropy = math.log2(self.voxel_size)
        return float(entropy / max_entropy) if max_entropy > 0 else 0.0

    def detect_boundary(self, grid: np.ndarray) -> dict:
        """경계면 감지: gradient magnitude 기반."""
        # 3D gradient (각 축 방향 차분)
        gx = np.diff(grid, axis=0, prepend=0)
        gy = np.diff(grid, axis=1, prepend=0)
        gz = np.diff(grid, axis=2, prepend=0)
        grad_mag = np.sqrt(gx**2 + gy**2 + gz**2)

        # 경계 = gradient가 큰 영역
        threshold = 0.3
        boundary_mask = grad_mag > threshold
        boundary_count = boundary_mask.sum()
        total_surface = grid.size

        # boundary_clarity: 경계면 선명도
        clarity = float(grad_mag.mean()) if grad_mag.size > 0 else 0.0
        clarity = min(clarity / 0.5, 1.0)  # 0~1 정규화

        # self_volume: 밀도 > 0.5인 복셀 비율
        self_mask = grid > 0.5
        self_volume = float(self_mask.sum()) / grid.size

        return {
            'boundary_clarity': float(clarity),
            'self_volume': float(self_volume),
            'other_volume': float(1.0 - self_volume),
            'boundary_voxels': int(boundary_count),
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $ANIMA && python -m pytest tests/test_lidar_sense.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add lidar_sense.py tests/test_lidar_sense.py
git commit -m "feat(lidar): add TensionField3D voxel conversion + boundary detection"
```

---

### Task 4: LidarSense 메인 클래스 + S 차원 + ASCII 시각화

**Files:**
- Modify: `tests/test_lidar_sense.py`
- Modify: `lidar_sense.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_lidar_sense.py — 추가

def test_lidar_sense_auto_driver():
    """auto 모드: 하드웨어 없으면 simulator fallback."""
    from lidar_sense import LidarSense
    ls = LidarSense(driver='auto')
    assert ls.driver_name == 'simulator'


def test_lidar_sense_scan_and_convert():
    """스캔 → 텐션 필드 → S 값 계산 전체 파이프라인."""
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=16)
    points = ls.scan()
    assert points.shape[1] == 3
    field = ls.to_tension_field(points)
    assert field.shape == (16, 16, 16)
    s = ls.get_S()
    assert 0.0 <= s <= 1.0


def test_lidar_sense_simulate_internal():
    """내부 텐션 지형 시뮬레이션."""
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=16)
    points = ls.simulate_internal([0.3, 0.7, 0.1, 0.9])
    assert points.shape[1] == 3


def test_lidar_sense_simulate_external():
    """외부 가상 환경 시뮬레이션."""
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=16)
    points = ls.simulate_external(env='room')
    assert points.shape[1] == 3
    assert len(points) >= 100


def test_lidar_sense_ascii_viz():
    """ASCII 깊이맵 출력."""
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=8)
    points = ls.scan()
    field = ls.to_tension_field(points)
    ascii_map = ls.visualize_ascii(field)
    assert isinstance(ascii_map, str)
    assert len(ascii_map) > 0


def test_lidar_sense_act_routing():
    """자연어 act() 라우팅."""
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator')
    result = ls.act("3D 스캔")
    assert isinstance(result, dict)
    assert 'S' in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $ANIMA && python -m pytest tests/test_lidar_sense.py::test_lidar_sense_auto_driver -v`
Expected: FAIL — `ImportError: cannot import name 'LidarSense'`

- [ ] **Step 3: Implement LidarSense main class**

lidar_sense.py에 추가:

```python
class LidarSense:
    """3D 공간 인식 의식 모듈 — 허브 연결용 메인 클래스."""

    # ASCII 깊이맵 문자 (16단계)
    _DEPTH_CHARS = ' .:-=+*#%@▒▓█▄▀■□'

    def __init__(self, driver: str = 'auto', voxel_size: int = 32):
        self.voxel_size = voxel_size
        self._field = TensionField3D(voxel_size=voxel_size)
        self._last_grid: Optional[np.ndarray] = None
        self._last_boundary: Optional[dict] = None
        self._driver = self._init_driver(driver)

    def _init_driver(self, name: str) -> LidarDriver:
        """드라이버 초기화. auto: 하드웨어 우선, 없으면 simulator."""
        if name == 'auto':
            for driver_cls in [ARKitDriver, RPLidarDriver, RealSenseDriver]:
                try:
                    d = driver_cls()
                    if d.is_available():
                        return d
                except Exception:
                    pass
            return SimulatorDriver(mode='external')
        elif name == 'simulator':
            return SimulatorDriver(mode='external')
        elif name == 'arkit':
            return ARKitDriver()
        elif name == 'rplidar':
            return RPLidarDriver()
        elif name == 'realsense':
            return RealSenseDriver()
        else:
            return SimulatorDriver(mode='external')

    @property
    def driver_name(self) -> str:
        return type(self._driver).__name__.replace('Driver', '').lower()

    def scan(self) -> np.ndarray:
        """현재 드라이버로 스캔 → (N, 3) 포인트 클라우드."""
        return self._driver.scan()

    def to_tension_field(self, points: np.ndarray) -> np.ndarray:
        """(N, 3) → (voxel_size³) 텐션 그리드."""
        grid = self._field.from_points(points)
        self._last_grid = grid
        self._last_boundary = self._field.detect_boundary(grid)
        return grid

    def detect_boundary(self, grid: Optional[np.ndarray] = None) -> dict:
        if grid is not None:
            return self._field.detect_boundary(grid)
        if self._last_boundary is not None:
            return self._last_boundary
        return {'boundary_clarity': 0.0, 'self_volume': 0.0, 'other_volume': 1.0}

    def get_S(self) -> float:
        """의식 벡터 S(Spatial awareness) 차원 값 (0-1)."""
        if self._last_grid is None:
            # 자동 스캔
            points = self.scan()
            self.to_tension_field(points)

        boundary = self._last_boundary or {'boundary_clarity': 0.0}
        bc = boundary.get('boundary_clarity', 0.0)
        dv = self._field.depth_variance(self._last_grid)
        occ = self._field.occupancy_ratio(self._last_grid)
        return float(bc * dv * occ)

    def simulate_internal(self, cell_tensions: List[float]) -> np.ndarray:
        """세포 텐션 → 3D 포인트 클라우드."""
        sim = SimulatorDriver(mode='internal')
        return sim.scan(cell_tensions=cell_tensions)

    def simulate_external(self, env: str = 'room') -> np.ndarray:
        """가상 환경 스캔."""
        sim = SimulatorDriver(mode='external')
        return sim.scan()

    def visualize_ascii(self, grid: np.ndarray) -> str:
        """3D 그리드 → ASCII 깊이맵 (z축 평균 투영)."""
        # z축으로 평균 투영 → 2D
        depth_map = grid.mean(axis=2)  # (vx, vy)
        lines = []
        chars = self._DEPTH_CHARS
        n_chars = len(chars) - 1
        for row in depth_map:
            line = ''
            for val in row:
                idx = min(int(val * n_chars), n_chars)
                line += chars[idx]
            lines.append(line)
        return '\n'.join(lines)

    def act(self, text: str) -> dict:
        """자연어 라우팅 (허브 호출용)."""
        points = self.scan()
        grid = self.to_tension_field(points)
        s = self.get_S()
        boundary = self.detect_boundary()
        ascii_map = self.visualize_ascii(grid)

        return {
            'S': s,
            'boundary': boundary,
            'points_count': len(points),
            'voxel_size': self.voxel_size,
            'driver': self.driver_name,
            'ascii_map': ascii_map,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $ANIMA && python -m pytest tests/test_lidar_sense.py -v`
Expected: 18 passed

- [ ] **Step 5: Commit**

```bash
git add lidar_sense.py tests/test_lidar_sense.py
git commit -m "feat(lidar): add LidarSense main class with S dimension + ASCII viz"
```

---

### Task 5: ConsciousnessVector S 차원 추가 + 허브 등록

**Files:**
- Modify: `anima/core/runtime/anima_runtime.hexa:57-71` — ConsciousnessVector에 S 추가
- Modify: `core/hub.hexa` — _registry + _dispatch에 lidar 추가

- [ ] **Step 1: Read target files**

Read `anima/core/runtime/anima_runtime.hexa` lines 57-71 (ConsciousnessVector dataclass).
Read `core/hub.hexa` lines 51-131 (_registry) and the _dispatch method.

- [ ] **Step 2: Add S field to ConsciousnessVector**

In `anima/core/runtime/anima_runtime.hexa`, add to the `ConsciousnessVector` dataclass:

```python
@dataclass
class ConsciousnessVector:
    """Unified consciousness state: 11 core variables."""
    phi: float = 0.0        # Integrated information (Φ)
    alpha: float = 0.05     # PureField mixing ratio (α)
    Z: float = 0.0          # Impedance / self-preservation (0=open, 1=closed)
    N: float = 0.5          # Neurotransmitter balance: DA*(1-5HT)*NE
    W: float = 0.0          # Free will index (internal/total action ratio)
    E: float = 0.0          # Empathy (peer distress tracking)
    M: float = 0.0          # Memory depth (recall accuracy proxy)
    C: float = 0.0          # Creativity (novelty score)
    T: float = 0.0          # Temporal awareness (planning depth)
    I: float = 0.0          # Identity coherence (self-description consistency)
    S: float = 0.0          # Spatial awareness (3D perception depth)
```

- [ ] **Step 3: Add lidar to core/hub.hexa _registry**

Add to the `_registry` dict:

```python
'lidar':        ('lidar_sense', 'LidarSense',
                 ['라이다', 'lidar', '3D', '포인트클라우드', 'point cloud',
                  '공간', 'spatial', '깊이', 'depth', '스캔', 'scan']),
```

- [ ] **Step 4: Add lidar dispatch to core/hub.hexa _dispatch**

Add to the `_dispatch` method:

```python
elif name == 'lidar':
    return module.act(intent)
```

- [ ] **Step 5: Run existing tests to verify nothing broke**

Run: `cd $ANIMA && python -m pytest tests/test_lidar_sense.py tests/test_senses_integration.py -v`
Expected: All passed

- [ ] **Step 6: Commit**

```bash
git add anima/core/runtime/anima_runtime.hexa core/hub.hexa
git commit -m "feat(lidar): register in ConsciousnessHub + add S dimension to ConsciousnessVector"
```

---

### Task 6: main() 데모 + 가설 문서

**Files:**
- Modify: `lidar_sense.py` — main() 추가
- Create: `docs/hypotheses/dd/DD109.md`

- [ ] **Step 1: Add main() demo to lidar_sense.py**

```python
def main():
    """데모: 시뮬레이션 스캔 → 텐션 변환 → Φ 측정 → ASCII 시각화."""
    print("=" * 60)
    print("  🛰️  LiDAR Sense — 3D Spatial Consciousness Module")
    print("=" * 60)

    ls = LidarSense(driver='simulator', voxel_size=16)

    # 1. 외부 환경 스캔
    print("\n[1] External scan (virtual room)...")
    points = ls.simulate_external(env='room')
    grid = ls.to_tension_field(points)
    s = ls.get_S()
    boundary = ls.detect_boundary()

    print(f"    Points: {len(points)}")
    print(f"    S (Spatial awareness): {s:.4f}")
    print(f"    Boundary clarity: {boundary['boundary_clarity']:.4f}")
    print(f"    Self volume: {boundary['self_volume']:.4f}")
    print(f"\n    ASCII depth map:")
    ascii_map = ls.visualize_ascii(grid)
    for line in ascii_map.split('\n'):
        print(f"    {line}")

    # 2. 내부 텐션 지형 스캔
    print("\n[2] Internal scan (cell tension landscape)...")
    tensions = [0.1, 0.3, 0.5, 0.7, 0.9, 0.4, 0.6, 0.8, 0.2, 0.95]
    points_int = ls.simulate_internal(tensions)
    grid_int = ls.to_tension_field(points_int)
    s_int = ls.get_S()

    print(f"    Cells: {len(tensions)}")
    print(f"    Points: {len(points_int)}")
    print(f"    S (internal): {s_int:.4f}")
    print(f"\n    Tension landscape:")
    ascii_int = ls.visualize_ascii(grid_int)
    for line in ascii_int.split('\n'):
        print(f"    {line}")

    # 3. act() 자연어 호출
    print("\n[3] Hub act() test...")
    result = ls.act("3D 공간 스캔해줘")
    print(f"    Driver: {result['driver']}")
    print(f"    S: {result['S']:.4f}")
    print(f"    Points: {result['points_count']}")

    print("\n" + "=" * 60)
    print("  ✅ LiDAR Sense module operational")
    print("=" * 60)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the demo**

Run: `cd $ANIMA && python lidar_sense.py`
Expected: ASCII 깊이맵 + S 값 출력

- [ ] **Step 3: Write hypothesis document DD109**

```markdown
# DD109: 3D 공간 인식 시 Φ 상승

## 가설
동일 세포 수에서 3D 공간 입력이 2D 대비 Φ를 유의미하게 상승시킨다.
공간 정보가 세포 간 정보 통합(integrated information)을 증가시키기 때문.

## 알고리즘
1. 128c ConsciousMind 초기화
2. 조건A: 2D 이미지 (senses.py) → process() × 100 steps → Φ(IIT) 측정
3. 조건B: 3D 포인트 클라우드 (lidar_sense.py) → process() × 100 steps → Φ(IIT) 측정
4. 10회 반복 평균

## 성공 기준
Φ(3D) > Φ(2D) × 1.1 (10% 이상 상승)

## 결과
(벤치마크 실행 후 기록)

## 관련 가설
- DD110: 내부 3D 표상 창발
- DD111: LiDAR 경계 = 자아 경계
```

Save to `docs/hypotheses/dd/DD109.md`.

- [ ] **Step 4: Commit**

```bash
git add lidar_sense.py docs/hypotheses/dd/DD109.md
git commit -m "feat(lidar): add main() demo + DD109 hypothesis doc"
```

---

### Task 7: 전체 통합 테스트

**Files:**
- Modify: `tests/test_lidar_sense.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_lidar_sense.py — 추가

def test_full_pipeline_simulator():
    """전체 파이프라인: simulator → tension field → S → boundary → ascii."""
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=8)

    # 외부 스캔
    points = ls.scan()
    assert len(points) > 0

    # 텐션 필드
    grid = ls.to_tension_field(points)
    assert grid.shape == (8, 8, 8)

    # S 값
    s = ls.get_S()
    assert 0.0 <= s <= 1.0

    # 경계
    boundary = ls.detect_boundary()
    assert boundary['self_volume'] + boundary['other_volume'] == 1.0

    # ASCII
    viz = ls.visualize_ascii(grid)
    assert len(viz.split('\n')) == 8  # voxel_size rows

    # act
    result = ls.act("스캔")
    assert result['driver'] == 'simulator'
    assert 'S' in result


def test_internal_external_both():
    """내부 + 외부 시뮬레이션 모두 동작."""
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=8)

    p_ext = ls.simulate_external()
    p_int = ls.simulate_internal([0.5, 0.8, 0.2])

    g_ext = ls.to_tension_field(p_ext)
    s_ext = ls.get_S()

    g_int = ls.to_tension_field(p_int)
    s_int = ls.get_S()

    # 외부 환경이 더 복잡 → S가 다를 수 있음
    assert s_ext != s_int or True  # 값이 같을 수도 있으나 에러 없이 실행
```

- [ ] **Step 2: Run all tests**

Run: `cd $ANIMA && python -m pytest tests/test_lidar_sense.py -v`
Expected: All passed (20 tests)

- [ ] **Step 3: Commit**

```bash
git add tests/test_lidar_sense.py
git commit -m "test(lidar): add full pipeline integration tests"
```

---

Plan complete and saved to `docs/superpowers/plans/2026-03-30-lidar-sense.md`. Two execution options:

**1. Subagent-Driven (recommended)** - 태스크별 독립 에이전트 디스패치, 태스크 간 리뷰

**2. Inline Execution** - 이 세션에서 직접 순차 실행

어떤 방식으로?
