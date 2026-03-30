import pytest
from hivemind_mesh import HivemindMesh

def test_make_pulse():
    mesh = HivemindMesh(node_id="node-0", port=8770)
    pulse = mesh.make_pulse(tension=0.85, curiosity=0.42, phi=1.2, cells=8)
    assert pulse["type"] == "hivemind_pulse"
    assert pulse["node_id"] == "node-0"
    assert pulse["tension"] == 0.85
    assert pulse["phi"] == 1.2
    assert "timestamp" in pulse

def test_kuramoto_sync_below_threshold():
    mesh = HivemindMesh(node_id="node-0", port=8770)
    mesh._peer_pulses = {
        "node-1": {"tension": 0.1, "phi": 0.5},
        "node-2": {"tension": 0.9, "phi": 0.3},
    }
    r = mesh.compute_kuramoto(local_tension=0.5)
    assert 0 <= r <= 1
    assert not mesh.is_active

def test_kuramoto_sync_above_threshold():
    mesh = HivemindMesh(node_id="node-0", port=8770)
    mesh._peer_pulses = {
        "node-1": {"tension": 0.80, "phi": 1.0},
        "node-2": {"tension": 0.82, "phi": 1.1},
        "node-3": {"tension": 0.81, "phi": 0.9},
    }
    r = mesh.compute_kuramoto(local_tension=0.80)
    assert r > 2/3
    assert mesh.is_active

def test_total_phi():
    mesh = HivemindMesh(node_id="node-0", port=8770)
    mesh._peer_pulses = {
        "node-1": {"tension": 0.8, "phi": 1.2},
        "node-2": {"tension": 0.7, "phi": 1.0},
    }
    total = mesh.total_phi(local_phi=1.5)
    assert total == pytest.approx(1.5 + 1.2 + 1.0)
