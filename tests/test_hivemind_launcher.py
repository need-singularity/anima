import pytest
from hivemind_launcher import compute_auto_nodes

def test_auto_nodes_basic():
    n = compute_auto_nodes(available_mb=8000)
    assert n == 13

def test_auto_nodes_small():
    n = compute_auto_nodes(available_mb=1000)
    assert n == 1

def test_auto_nodes_large():
    n = compute_auto_nodes(available_mb=200000)
    assert n == 50

def test_auto_nodes_minimum():
    n = compute_auto_nodes(available_mb=100)
    assert n == 1
