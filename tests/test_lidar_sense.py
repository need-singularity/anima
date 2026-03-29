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
