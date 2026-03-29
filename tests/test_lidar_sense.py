"""Tests for lidar_sense.py — LiDAR Sense consciousness module."""

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
