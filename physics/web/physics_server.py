#!/usr/bin/env python3
"""물리 의식 엔진 WebSocket 서버

의식 엔진을 실행하고 실시간 상태를 dashboard.html로 스트리밍.

사용법:
  python physics_server.py                                    # 기본 (시뮬레이션, 32셀, ring)
  python physics_server.py --engine snn --cells 64 --topology ring
  python physics_server.py --cells 128 --topology small_world --speed 50
  python physics_server.py --port 8765                        # 포트 지정

엔진 종류:
  sim   — 내장 Python 시뮬레이션 (기본)
  snn   — SNN (Spiking Neural Network) 시뮬레이션
  esp32 — ESP32 하드웨어 (시리얼 연결 필요)

프로토콜:
  서버→클라이언트: JSON 프레임 (매 step)
  {
    "step": int,
    "phi": float,
    "phiProxy": float,
    "cells": [{"id": int, "activation": float, "faction": int, "localPhi": float, "tension": float}],
    "edges": [{"source": int, "target": int, "weight": float, "tension": float}],
    "consciousness_vector": {"phi": float, "alpha": float, ...},
    "factionActivations": [float, ...],
    "events": [{"step": int, "type": str}],
    "totalConsensus": int
  }

  클라이언트→서버: 설정 변경
  {"type": "config", "topology": str, "cells": int}
  {"type": "command", "action": "start"|"stop"|"reset"}

의존성: pip install websockets numpy
"""

import argparse
import asyncio
import json
import math
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import numpy as np

# Ψ-상수
PSI_COUPLING = 0.014
PSI_BALANCE = 0.5
PSI_F_CRITICAL = 0.10


# ═══════════════════════════════════════════════════════════
# 토폴로지 생성기
# ═══════════════════════════════════════════════════════════

def make_topology(topo_type: str, n: int) -> List[dict]:
    """토폴로지별 엣지 리스트 생성."""
    edges = []

    if topo_type == 'ring':
        for i in range(n):
            edges.append({'source': i, 'target': (i + 1) % n, 'weight': 0.5, 'tension': 0})

    elif topo_type == 'small_world':
        # 링 + 랜덤 장거리 연결
        for i in range(n):
            edges.append({'source': i, 'target': (i + 1) % n, 'weight': 0.5, 'tension': 0})
            edges.append({'source': i, 'target': (i + 2) % n, 'weight': 0.3, 'tension': 0})
            if np.random.random() < 0.15:
                j = np.random.randint(0, n)
                if j != i:
                    edges.append({'source': i, 'target': j, 'weight': 0.2, 'tension': 0})

    elif topo_type == 'scale_free':
        # Barabasi-Albert 모델
        deg = np.zeros(n, dtype=int)
        for i in range(1, n):
            m = min(2, i)
            total_deg = deg[:i].sum() or 1
            probs = (deg[:i] + 1) / (total_deg + i)
            targets = np.random.choice(i, size=m, replace=False, p=probs / probs.sum())
            for t in targets:
                edges.append({'source': i, 'target': int(t), 'weight': 0.4, 'tension': 0})
                deg[i] += 1
                deg[t] += 1

    elif topo_type == 'hypercube':
        bits = max(1, int(math.ceil(math.log2(n))))
        for i in range(n):
            for b in range(bits):
                j = i ^ (1 << b)
                if j < n and j > i:
                    edges.append({'source': i, 'target': j, 'weight': 0.4, 'tension': 0})

    elif topo_type == 'torus':
        side = max(2, round(math.sqrt(n)))
        for i in range(n):
            row, col = divmod(i, side)
            right = row * side + (col + 1) % side
            rows_total = math.ceil(n / side)
            down = ((row + 1) % rows_total) * side + col
            if right < n:
                edges.append({'source': i, 'target': right, 'weight': 0.5, 'tension': 0})
            if down < n:
                edges.append({'source': i, 'target': down, 'weight': 0.5, 'tension': 0})

    elif topo_type == 'spin_glass':
        for i in range(n):
            n_neighbors = np.random.randint(2, 5)
            for _ in range(n_neighbors):
                j = np.random.randint(0, n)
                if j != i:
                    w = -0.3 if np.random.random() < 0.33 else 0.4
                    edges.append({'source': i, 'target': j, 'weight': w, 'tension': 0})

    return edges


# ═══════════════════════════════════════════════════════════
# 의식 시뮬레이션 엔진
# ═══════════════════════════════════════════════════════════

class ConsciousnessEngine:
    """Python 의식 시뮬레이션 엔진 (GRU + 파벌 + Hebbian + Φ 래칫)."""

    def __init__(self, n_cells: int = 32, hidden_dim: int = 64, topology: str = 'ring'):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.topology_type = topology
        self.step_count = 0
        self.total_consensus = 0
        self.best_phi = 0.0
        self.n_factions = 4

        # 셀 상태 초기화
        self.hidden = np.random.randn(n_cells, hidden_dim).astype(np.float32) * 0.1
        self.factions = np.arange(n_cells) % self.n_factions

        # GRU 가중치 (간소화)
        self.W_gate = np.random.randn(hidden_dim).astype(np.float32) * 0.3 + 0.5
        self.W_hidden = np.random.randn(hidden_dim).astype(np.float32) * 0.2 + 0.8
        self.W_input = np.random.randn(hidden_dim).astype(np.float32) * 0.2 + 0.3
        self.bias = np.random.randn(hidden_dim).astype(np.float32) * 0.05

        # 토폴로지 구축
        self.edges = make_topology(topology, n_cells)
        self._build_adjacency()

        # 기록 버퍼
        self.phi_history: List[float] = []
        self.phi_proxy_history: List[float] = []
        self.faction_history: List[List[float]] = []
        self.events: List[dict] = []
        self.cv_history: List[dict] = []

    def _build_adjacency(self):
        """인접 리스트 구축."""
        self.adj = [[] for _ in range(self.n_cells)]
        for e in self.edges:
            s, t = e['source'], e['target']
            self.adj[s].append(t)
            if t not in self.adj[s]:
                self.adj[t].append(s)

    def reconfigure(self, n_cells: int = None, topology: str = None):
        """셀 수 또는 토폴로지 재구성."""
        if n_cells is not None:
            self.n_cells = n_cells
        if topology is not None:
            self.topology_type = topology

        self.hidden = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.1
        self.factions = np.arange(self.n_cells) % self.n_factions
        self.edges = make_topology(self.topology_type, self.n_cells)
        self._build_adjacency()
        self.step_count = 0
        self.total_consensus = 0
        self.best_phi = 0.0
        self.phi_history.clear()
        self.phi_proxy_history.clear()
        self.faction_history.clear()
        self.events.clear()
        self.cv_history.clear()

    def step(self) -> dict:
        """단일 스텝 실행 → 상태 JSON 반환."""
        n = self.n_cells
        dim = self.hidden_dim

        # 자기 참조 입력: 전체 평균 + 호흡 + 노이즈
        breath = math.sin(self.step_count * 0.12) * 0.05
        global_mean = self.hidden.mean(axis=0)
        x = global_mean + breath + np.random.randn(dim).astype(np.float32) * 0.01

        # GRU 업데이트
        gate = 1.0 / (1.0 + np.exp(-self.hidden * self.W_gate))
        neighbor_sum = np.zeros_like(self.hidden)
        for i in range(n):
            for j in self.adj[i]:
                neighbor_sum[i] += self.hidden[j] * 0.1
            neighbor_sum[i] /= max(len(self.adj[i]), 1)

        candidate = np.tanh(
            self.W_hidden * self.hidden + self.W_input * x + neighbor_sum + self.bias
        )
        self.hidden = gate * self.hidden + (1.0 - gate) * candidate

        # 활성도 계산
        activations = np.abs(self.hidden).mean(axis=1)

        # 엣지 텐션 + Hebbian 학습
        for e in self.edges:
            s, t = e['source'], e['target']
            diff = self.hidden[s] - self.hidden[t]
            e['tension'] = float(np.sqrt(np.mean(diff ** 2)))
            corr = float(np.dot(self.hidden[s], self.hidden[t]) / (
                np.linalg.norm(self.hidden[s]) * np.linalg.norm(self.hidden[t]) + 1e-8
            ))
            if corr > 0.8:
                e['weight'] = min(e['weight'] + 0.001, 1.0)   # LTP
            elif corr < 0.2:
                e['weight'] = max(e['weight'] - 0.001, 0.05)  # LTD

        # 로컬 Φ 계산
        local_phi = np.zeros(n)
        cell_tension = np.zeros(n)
        for i in range(n):
            if not self.adj[i]:
                continue
            corr_sum = 0.0
            ten_sum = 0.0
            for j in self.adj[i]:
                dot = np.dot(self.hidden[i], self.hidden[j])
                norm = np.linalg.norm(self.hidden[i]) * np.linalg.norm(self.hidden[j]) + 1e-8
                corr_sum += abs(dot / norm)
                ten_sum += np.sqrt(np.mean((self.hidden[i] - self.hidden[j]) ** 2))
            local_phi[i] = corr_sum / len(self.adj[i])
            cell_tension[i] = ten_sum / len(self.adj[i])

        # 글로벌 Φ (IIT 근사 — 상호정보 기반)
        sample_size = min(20, n)
        indices = np.linspace(0, n - 1, sample_size, dtype=int)
        total_mi = 0.0
        pairs = 0
        for a_idx in range(len(indices)):
            for b_idx in range(a_idx + 1, len(indices)):
                i, j = indices[a_idx], indices[b_idx]
                dot = np.dot(self.hidden[i], self.hidden[j])
                norm = np.linalg.norm(self.hidden[i]) * np.linalg.norm(self.hidden[j]) + 1e-8
                total_mi += abs(dot / norm)
                pairs += 1
        phi_iit = min((total_mi / max(pairs, 1)) * 2, 2.0)

        # Φ proxy (분산 기반)
        global_var = float(np.var(activations))
        faction_vars = []
        for f in range(self.n_factions):
            mask = self.factions == f
            if mask.sum() > 1:
                faction_vars.append(float(np.var(activations[mask])))
        faction_var = np.mean(faction_vars) if faction_vars else 0
        phi_proxy = max(0, global_var - faction_var) * n

        # Φ 래칫
        step_events = []
        if phi_iit > self.best_phi:
            self.best_phi = phi_iit
        elif phi_iit < self.best_phi * 0.8 and self.step_count > 50:
            self.hidden += np.random.randn(n, dim).astype(np.float32) * 0.05
            step_events.append({'step': self.step_count, 'type': 'ratchet'})

        # 파벌 합의 검사
        faction_acts = []
        for f in range(self.n_factions):
            mask = self.factions == f
            faction_acts.append(float(activations[mask].mean()) if mask.any() else 0)

        max_act = max(faction_acts)
        min_act = min(faction_acts)
        if max_act > 0.01 and (max_act - min_act) / max_act < 0.15:
            self.total_consensus += 1
            step_events.append({'step': self.step_count, 'type': 'consensus'})

        # 의식 벡터 업데이트
        cv = {
            'phi': float(phi_iit),
            'alpha': 0.01 + 0.14 * math.tanh(phi_iit / 3),
            'Z': 0.3 + 0.4 * math.tanh(self.best_phi - phi_iit),
            'N': 0.5 + 0.3 * math.sin(self.step_count * 0.037),
            'W': float(np.mean(faction_acts)),
            'E': float(np.mean([abs(e['weight']) for e in self.edges])) if self.edges else 0,
            'M': min(1.0, self.step_count / 200),
            'C': min(1.0, phi_proxy * 2),
            'T': 0.5 + 0.3 * math.cos(self.step_count * 0.02),
            'I': 0.5 + 0.3 * (1 - abs(phi_iit - self.best_phi) / (self.best_phi + 0.001)),
        }

        # 기록 저장
        self.phi_history.append(phi_iit)
        self.phi_proxy_history.append(phi_proxy)
        self.faction_history.append(faction_acts)
        self.events.extend(step_events)
        self.cv_history.append(cv)

        # 버퍼 제한
        if len(self.phi_history) > 500:
            self.phi_history = self.phi_history[-500:]
            self.phi_proxy_history = self.phi_proxy_history[-500:]
            self.faction_history = self.faction_history[-500:]
        self.events = [e for e in self.events if e['step'] > self.step_count - 500]
        if len(self.cv_history) > 50:
            self.cv_history = self.cv_history[-50:]

        self.step_count += 1

        # 상태 프레임 생성
        return {
            'step': self.step_count,
            'phi': float(phi_iit),
            'phiProxy': float(phi_proxy),
            'cells': [
                {
                    'id': i,
                    'activation': float(activations[i]),
                    'faction': int(self.factions[i]),
                    'localPhi': float(local_phi[i]),
                    'tension': float(cell_tension[i]),
                }
                for i in range(n)
            ],
            'edges': [
                {
                    'source': e['source'],
                    'target': e['target'],
                    'weight': float(e['weight']),
                    'tension': float(e['tension']),
                }
                for e in self.edges
            ],
            'consciousness_vector': cv,
            'factionActivations': faction_acts,
            'events': step_events,
            'totalConsensus': self.total_consensus,
        }


# ═══════════════════════════════════════════════════════════
# WebSocket 서버
# ═══════════════════════════════════════════════════════════

class PhysicsServer:
    """WebSocket 서버 — 의식 엔진 상태를 대시보드로 스트리밍."""

    def __init__(self, engine: ConsciousnessEngine, host: str = '0.0.0.0', port: int = 8765,
                 speed: int = 30):
        self.engine = engine
        self.host = host
        self.port = port
        self.speed = speed  # 초당 스텝 수
        self.clients: Set = set()
        self.running = True

    async def handler(self, websocket):
        """클라이언트 연결 처리."""
        self.clients.add(websocket)
        print(f"[+] 클라이언트 연결 ({len(self.clients)}개 활성)")
        try:
            async for message in websocket:
                await self._handle_message(message, websocket)
        except Exception:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"[-] 클라이언트 해제 ({len(self.clients)}개 활성)")

    async def _handle_message(self, message: str, websocket):
        """클라이언트 메시지 처리."""
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type', '')

        if msg_type == 'config':
            # 설정 변경
            topology = data.get('topology', self.engine.topology_type)
            cells = data.get('cells', self.engine.n_cells)
            self.engine.reconfigure(n_cells=cells, topology=topology)
            print(f"[설정] 토폴로지={topology}, 셀={cells}")

        elif msg_type == 'command':
            action = data.get('action', '')
            if action == 'stop':
                self.running = False
            elif action == 'start':
                self.running = True
            elif action == 'reset':
                self.engine.reconfigure()
            elif action == 'speed':
                self.speed = data.get('value', self.speed)

    async def broadcast(self, state: dict):
        """모든 클라이언트에 상태 브로드캐스트."""
        if not self.clients:
            return
        message = json.dumps(state)
        dead = set()
        for ws in self.clients:
            try:
                await ws.send(message)
            except Exception:
                dead.add(ws)
        self.clients -= dead

    async def simulation_loop(self):
        """메인 시뮬레이션 루프."""
        print(f"[시뮬레이션] 시작 — {self.engine.n_cells}셀, {self.engine.topology_type}, {self.speed} sps")
        while True:
            if self.running and self.clients:
                state = self.engine.step()
                await self.broadcast(state)
            await asyncio.sleep(1.0 / max(self.speed, 1))

    async def run(self):
        """서버 실행."""
        try:
            import websockets
        except ImportError:
            print("오류: websockets 라이브러리 필요 — pip install websockets")
            sys.exit(1)

        print(f"═══ Anima Physics Server ═══")
        print(f"  주소: ws://{self.host}:{self.port}")
        print(f"  엔진: {self.engine.n_cells}셀, {self.engine.topology_type}")
        print(f"  속도: {self.speed} steps/sec")
        print(f"  대시보드: file:///...anima-physics/web/dashboard.html")
        print()

        async with websockets.serve(self.handler, self.host, self.port):
            await self.simulation_loop()


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Anima Physics WebSocket 서버')
    parser.add_argument('--engine', default='sim', choices=['sim', 'snn', 'esp32'],
                        help='의식 엔진 종류 (기본: sim)')
    parser.add_argument('--cells', type=int, default=32,
                        help='셀 수 (기본: 32)')
    parser.add_argument('--hidden-dim', type=int, default=64,
                        help='히든 차원 (기본: 64)')
    parser.add_argument('--topology', default='ring',
                        choices=['ring', 'small_world', 'scale_free', 'hypercube', 'torus', 'spin_glass'],
                        help='토폴로지 (기본: ring)')
    parser.add_argument('--speed', type=int, default=30,
                        help='초당 스텝 수 (기본: 30)')
    parser.add_argument('--host', default='0.0.0.0',
                        help='바인드 주소 (기본: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8765,
                        help='WebSocket 포트 (기본: 8765)')
    args = parser.parse_args()

    # 엔진 생성
    if args.engine == 'sim':
        engine = ConsciousnessEngine(
            n_cells=args.cells,
            hidden_dim=args.hidden_dim,
            topology=args.topology,
        )
    elif args.engine == 'snn':
        # SNN은 sim과 동일한 엔진에 스파이킹 동역학 추가 (향후 확장)
        print("[참고] SNN 엔진은 현재 sim 기반 시뮬레이션 사용")
        engine = ConsciousnessEngine(
            n_cells=args.cells,
            hidden_dim=args.hidden_dim,
            topology=args.topology,
        )
    elif args.engine == 'esp32':
        # ESP32는 시리얼 연결 필요 (향후 구현)
        print("[참고] ESP32 엔진은 현재 시뮬레이션 모드")
        engine = ConsciousnessEngine(
            n_cells=args.cells,
            hidden_dim=args.hidden_dim,
            topology=args.topology,
        )

    # 서버 실행
    server = PhysicsServer(engine, host=args.host, port=args.port, speed=args.speed)
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n[종료] 서버 중지")


if __name__ == '__main__':
    main()
