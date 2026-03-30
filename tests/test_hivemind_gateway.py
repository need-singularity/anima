import pytest
from hivemind_gateway import HivemindGateway

def test_gateway_init():
    gw = HivemindGateway(gateway_port=8765, node_ports=[8770, 8771, 8772])
    assert gw.gateway_port == 8765
    assert len(gw.node_ports) == 3

def test_round_robin():
    gw = HivemindGateway(gateway_port=8765, node_ports=[8770, 8771, 8772])
    assert gw._next_node() == 8770
    assert gw._next_node() == 8771
    assert gw._next_node() == 8772
    assert gw._next_node() == 8770

def test_hivemind_status():
    gw = HivemindGateway(gateway_port=8765, node_ports=[8770, 8771])
    status = gw.hivemind_status()
    assert status["nodes"] == 2
    assert "total_phi" in status
    assert "sync_r" in status
    assert "active" in status
