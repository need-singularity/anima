"""Tests for lidar_sense.py — LiDAR Sense consciousness module."""

import sys
import os
# Ensure src/lidar_sense.py is found before tools/lidar_sense.py
_src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import numpy as np
import pytest


def test_simulator_driver_returns_point_cloud():
    from lidar_sense import SimulatorDriver
    driver = SimulatorDriver()
    assert driver.is_available()
    points = driver.scan()
    assert isinstance(points, np.ndarray)
    assert points.ndim == 2
    assert points.shape[1] == 3
    assert len(points) > 0


def test_simulator_internal_scan():
    from lidar_sense import SimulatorDriver
    driver = SimulatorDriver(mode='internal')
    cell_tensions = [0.3, 0.7, 0.1, 0.9, 0.5]
    points = driver.scan(cell_tensions=cell_tensions)
    assert points.shape[1] == 3
    assert len(points) >= len(cell_tensions)


def test_simulator_external_scan():
    from lidar_sense import SimulatorDriver
    driver = SimulatorDriver(mode='external')
    points = driver.scan()
    assert points.shape[1] == 3
    assert len(points) >= 100


def test_file_driver_ply_parse():
    import tempfile, os
    from lidar_sense import FileDriver
    ply_content = (
        "ply\nformat ascii 1.0\nelement vertex 3\n"
        "property float x\nproperty float y\nproperty float z\n"
        "end_header\n1.0 2.0 3.0\n4.0 5.0 6.0\n7.0 8.0 9.0\n"
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
    import tempfile, os
    from lidar_sense import FileDriver
    pcd_content = (
        "# .PCD v0.7\nVERSION 0.7\nFIELDS x y z\nSIZE 4 4 4\n"
        "TYPE F F F\nCOUNT 1 1 1\nWIDTH 2\nHEIGHT 1\n"
        "VIEWPOINT 0 0 0 1 0 0 0\nPOINTS 2\nDATA ascii\n"
        "1.0 2.0 3.0\n4.0 5.0 6.0\n"
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
    from lidar_sense import ARKitDriver
    driver = ARKitDriver(port=19999)
    assert not driver.is_available()


def test_rplidar_driver_not_available():
    from lidar_sense import RPLidarDriver
    driver = RPLidarDriver()
    assert not driver.is_available()


def test_realsense_driver_not_available():
    from lidar_sense import RealSenseDriver
    driver = RealSenseDriver()
    assert not driver.is_available()


def test_tension_field_3d_shape():
    from lidar_sense import TensionField3D
    points = np.random.rand(500, 3).astype(np.float32) * 10
    field = TensionField3D(voxel_size=16)
    grid = field.from_points(points)
    assert grid.shape == (16, 16, 16)
    assert grid.min() >= 0.0
    assert grid.max() <= 1.0


def test_tension_field_occupancy():
    from lidar_sense import TensionField3D
    points = np.array([[5, 5, 5], [5, 5, 6], [5, 6, 5]], dtype=np.float32)
    field = TensionField3D(voxel_size=8)
    grid = field.from_points(points)
    occ = field.occupancy_ratio(grid)
    assert 0.0 < occ < 1.0


def test_boundary_detection():
    from lidar_sense import TensionField3D
    points = np.random.rand(300, 3).astype(np.float32) * 5
    field = TensionField3D(voxel_size=16)
    grid = field.from_points(points)
    boundary = field.detect_boundary(grid)
    assert 'boundary_clarity' in boundary
    assert 'self_volume' in boundary
    assert 'other_volume' in boundary
    assert 0.0 <= boundary['boundary_clarity'] <= 1.0


def test_depth_variance():
    from lidar_sense import TensionField3D
    points = np.random.rand(200, 3).astype(np.float32) * 10
    field = TensionField3D(voxel_size=16)
    grid = field.from_points(points)
    dv = field.depth_variance(grid)
    assert 0.0 <= dv <= 1.0


def test_lidar_sense_auto_driver():
    from lidar_sense import LidarSense
    ls = LidarSense(driver='auto')
    assert ls.driver_name == 'simulator'


def test_lidar_sense_scan_and_convert():
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=16)
    points = ls.scan()
    assert points.shape[1] == 3
    field = ls.to_tension_field(points)
    assert field.shape == (16, 16, 16)
    s = ls.get_S()
    assert 0.0 <= s <= 1.0


def test_lidar_sense_simulate_internal():
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=16)
    points = ls.simulate_internal([0.3, 0.7, 0.1, 0.9])
    assert points.shape[1] == 3


def test_lidar_sense_simulate_external():
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=16)
    points = ls.simulate_external(env='room')
    assert points.shape[1] == 3
    assert len(points) >= 100


def test_lidar_sense_ascii_viz():
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=8)
    points = ls.scan()
    field = ls.to_tension_field(points)
    ascii_map = ls.visualize_ascii(field)
    assert isinstance(ascii_map, str)
    assert len(ascii_map) > 0


def test_lidar_sense_act_routing():
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator')
    result = ls.act("3D 스캔")
    assert isinstance(result, dict)
    assert 'S' in result


# ─── Integration Tests ───

def test_full_pipeline_simulator():
    """전체 파이프라인: simulator -> tension field -> S -> boundary -> ascii."""
    from lidar_sense import LidarSense
    ls = LidarSense(driver='simulator', voxel_size=8)

    points = ls.scan()
    assert len(points) > 0

    grid = ls.to_tension_field(points)
    assert grid.shape == (8, 8, 8)

    s = ls.get_S()
    assert 0.0 <= s <= 1.0

    boundary = ls._field_helper.detect_boundary(grid)
    assert abs(boundary['self_volume'] + boundary['other_volume'] - 1.0) < 1e-6

    viz = ls.visualize_ascii(grid)
    assert len(viz.split('\n')) == 8

    result = ls.act("스캔")
    assert result['driver'] == 'simulator'
    assert 'S' in result


def test_internal_external_both():
    """내부 + 외부 시뮬레이션 모두 동작."""
    from lidar_sense import LidarSense

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    ls = LidarSense(driver='simulator', voxel_size=8)

    p_ext = ls.simulate_external()
    p_int = ls.simulate_internal([0.5, 0.8, 0.2])

    ls.to_tension_field(p_ext)
    s_ext = ls.get_S()

    ls.to_tension_field(p_int)
    s_int = ls.get_S()

    # 둘 다 유효한 S 값
    assert 0.0 <= s_ext <= 1.0
    assert 0.0 <= s_int <= 1.0
