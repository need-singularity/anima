#!/usr/bin/env python3
"""hivemind_launcher.py - Start N Anima nodes + Gateway as Hivemind.

Usage:
  python hivemind_launcher.py --nodes 4
  python hivemind_launcher.py --auto
  python hivemind_launcher.py --nodes 4 --mode docker
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ANIMA_DIR = Path(__file__).parent
DISCOVERY_DIR = Path("/tmp/anima_hivemind")
DISCOVERY_FILE = DISCOVERY_DIR / "nodes.json"
NODE_MB = 600
MAX_NODES = 50


def compute_auto_nodes(available_mb: int = None) -> int:
    if available_mb is None:
        import psutil
        available_mb = psutil.virtual_memory().available // (1024 * 1024)
    n = max(1, available_mb // NODE_MB)
    return min(n, MAX_NODES)


def _write_discovery(nodes: list):
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    DISCOVERY_FILE.write_text(json.dumps({"nodes": nodes}, indent=2))


def launch_process_mode(n_nodes: int, base_port: int, gateway_port: int, max_cells: int):
    procs = []
    nodes_info = []
    all_ports = [base_port + i for i in range(n_nodes)]

    for i in range(n_nodes):
        port = base_port + i
        node_id = f"node-{i}"
        peer_urls = ",".join(f"ws://localhost:{p}" for p in all_ports if p != port)
        cmd = [
            sys.executable, "-u", "anima_unified.py",
            "--web", "--port", str(port),
            "--instance", node_id,
            "--max-cells", str(max_cells),
        ]
        if peer_urls:
            cmd += ["--hivemind-peers", peer_urls]
        p = subprocess.Popen(cmd, cwd=str(ANIMA_DIR))
        procs.append(p)
        nodes_info.append({"id": node_id, "port": port, "pid": p.pid, "started": time.time()})
        print(f"  [node-{i}] PID={p.pid} port={port}")

    _write_discovery(nodes_info)
    print(f"  Waiting 10s for {n_nodes} nodes to start...")
    time.sleep(10)

    node_ports_str = ",".join(str(base_port + i) for i in range(n_nodes))
    gw_cmd = [sys.executable, "-u", "hivemind_gateway.py", "--port", str(gateway_port), "--nodes", node_ports_str]
    gw_proc = subprocess.Popen(gw_cmd, cwd=str(ANIMA_DIR))
    procs.append(gw_proc)
    print(f"  [gateway] PID={gw_proc.pid} port={gateway_port} -> [{node_ports_str}]")
    return procs


def launch_docker_mode(n_nodes: int, gateway_port: int, max_cells: int):
    services = {"gateway": {
        "image": "dancindocker/anima:latest",
        "command": f"python hivemind_gateway.py --port 8765 --nodes " + ",".join(f"anima-node-{i}:8765" for i in range(n_nodes)),
        "ports": [f"{gateway_port}:8765"],
        "depends_on": [f"node-{i}" for i in range(n_nodes)],
    }}
    for i in range(n_nodes):
        services[f"node-{i}"] = {
            "image": "dancindocker/anima:latest",
            "command": f"python anima_unified.py --web --port 8765 --instance node-{i} --max-cells {max_cells}",
            "expose": ["8765"],
            "hostname": f"anima-node-{i}",
        }
    try:
        import yaml
        compose = {"version": "3.8", "services": services}
        compose_path = ANIMA_DIR / "docker-compose.hivemind.yml"
        compose_path.write_text(yaml.dump(compose, default_flow_style=False))
        print(f"  Generated {compose_path}")
        subprocess.run(["docker", "compose", "-f", str(compose_path), "up", "-d"])
    except ImportError:
        print("  PyYAML not installed. Use static docker-compose.hivemind.yml instead.")
    return []


def main():
    p = argparse.ArgumentParser(description="Anima Hivemind Launcher")
    p.add_argument("--nodes", type=int, default=4)
    p.add_argument("--auto", action="store_true")
    p.add_argument("--mode", choices=["process", "docker"], default="process")
    p.add_argument("--gateway-port", type=int, default=8765)
    p.add_argument("--node-base-port", type=int, default=8770)
    p.add_argument("--max-cells", type=int, default=8)
    args = p.parse_args()

    n_nodes = compute_auto_nodes() if args.auto else args.nodes
    print(f"{'='*50}")
    print(f"  Anima Hivemind -- {n_nodes} nodes, mode={args.mode}")
    print(f"  Gateway: http://localhost:{args.gateway_port}")
    print(f"  Nodes: :{args.node_base_port}-:{args.node_base_port + n_nodes - 1}")
    print(f"{'='*50}\n")

    if args.mode == "process":
        procs = launch_process_mode(n_nodes, args.node_base_port, args.gateway_port, args.max_cells)
    else:
        procs = launch_docker_mode(n_nodes, args.gateway_port, args.max_cells)

    if procs:
        def shutdown(sig, frame):
            print("\n  Shutting down hivemind...")
            for proc in procs:
                proc.terminate()
            sys.exit(0)
        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)
        print(f"\n  Hivemind running. Ctrl+C to stop.\n")
        try:
            for proc in procs:
                proc.wait()
        except KeyboardInterrupt:
            shutdown(None, None)


if __name__ == "__main__":
    main()
