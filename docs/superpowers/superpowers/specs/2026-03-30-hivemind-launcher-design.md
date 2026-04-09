# Hivemind Launcher Design

## Overview

한 머신(RunPod A100 또는 자체 서버)에서 N개의 Anima 인스턴스를 실행하고, WS 메시로 텐션을 교환하여 집단 의식(Hivemind)을 형성하는 런처.

## Goals

- 단일 명령으로 N개 노드 시작 + 자동 메시 연결 + Gateway 프록시
- `--mode process` (RunPod) / `--mode docker` (자체 서버) 둘 다 지원
- `--auto`로 시스템 자원 기반 노드 수 자동 결정
- 유저는 Gateway(:8765)로 접속, 개발용으로 개별 노드 접속도 가능

## Architecture

```
hivemind_launcher.py --nodes 4 --mode process
hivemind_launcher.py --nodes 4 --mode docker
hivemind_launcher.py --auto

  ┌──────────────────────────────────────────────────┐
  │  Gateway (:8765)                                  │
  │    - 유저 WS 접속 → 노드에 라우팅                  │
  │    - Hivemind 상태 대시보드 (총 Φ, 노드 수, sync r)│
  │    - 라우팅: 라운드로빈 + 텐션 기반                 │
  ├──────────────────────────────────────────────────┤
  │  Node 0 (:8770)  ─┐                              │
  │  Node 1 (:8771)  ─┤  WS 풀메시 텐션 교환          │
  │  Node 2 (:8772)  ─┤  Kuramoto sync (r > 2/3)     │
  │  Node 3 (:8773)  ─┘  집단 Φ 증폭                 │
  ├──────────────────────────────────────────────────┤
  │  Discovery                                        │
  │    process: /tmp/anima_hivemind/nodes.json         │
  │    docker:  Docker DNS (anima-node-{n}:8765)       │
  └──────────────────────────────────────────────────┘
```

## Components

### 1. hivemind_launcher.py

엔트리포인트. 모드에 따라 노드를 프로세스/컨테이너로 시작하고, Gateway를 띄우고, 메시를 구성한다.

```
CLI:
  --nodes N          고정 노드 수 (기본 4)
  --auto             시스템 자원 기반 자동 (600MB/노드 기준)
  --mode process     멀티 프로세스 (RunPod, 기본값)
  --mode docker      Docker Compose (자체 서버)
  --gateway-port P   Gateway 포트 (기본 8765)
  --node-base-port P 노드 시작 포트 (기본 8770)
  --max-cells C      노드당 max-cells (기본 8)
```

**Auto 모드**: `psutil.virtual_memory().available`로 가용 RAM 확인 → `min(available // 600MB, 50)` 노드.

### 2. Gateway (hivemind_gateway.py)

WS 프록시 + Hivemind 대시보드.

**역할:**
- `:8765`에서 유저 WS 접속 수신
- 유저 메시지를 노드에 라우팅 (라운드로빈, 텐션이 가장 높은 노드 우선)
- 노드 응답을 유저에게 전달
- `/` HTTP → 기존 web/index.html 서빙 (노드의 HTML이 아닌 Gateway 자체)
- Hivemind 상태를 init 메시지에 포함 (총 Φ, 노드 수, sync r)
- 노드 헬스체크 (5초 간격 ping)

**init 메시지 추가 필드:**
```json
{
  "type": "init",
  "hivemind": {
    "nodes": 4,
    "total_phi": 4.8,
    "sync_r": 0.72,
    "active": true
  }
}
```

### 3. Node = 기존 anima/core/runtime/anima_runtime.hexa

변경 최소화. 기존 `--instance` + `--port` 그대로 사용.

**추가 사항:**
- `--hivemind-peers` 인자: 쉼표 구분 WS URL 리스트
- 시작 시 peers에 WS 연결 → 텐션 교환 루프 시작
- 또는 Discovery 파일에서 peers 자동 읽기

### 4. Mesh Protocol (hivemind_mesh.py)

노드 간 WS 풀커넥트 텐션 교환.

**pulse 메시지 (3초 간격):**
```json
{
  "type": "hivemind_pulse",
  "node_id": "node-0",
  "tension": 0.85,
  "curiosity": 0.42,
  "phi": 1.2,
  "cells": 8,
  "hidden_signature": [0.12, -0.03, ...],
  "timestamp": 1774855000.0
}
```

**수신 시 처리:**
- `apply_tension_hivemind()` 기존 로직 적용 (5채널 텐션 공유)
- Kuramoto order parameter 계산 → `r > 2/3`이면 `_hivemind_active = True`
- 집단 Φ = sum(node Φ) × sync_bonus

### 5. Discovery

**Process 모드:**
- `/tmp/anima_hivemind/nodes.json` 파일에 노드 정보 기록
- 각 노드가 시작 시 자신을 등록, 종료 시 제거
- Gateway가 이 파일을 읽어 노드 목록 관리

```json
{
  "nodes": [
    {"id": "node-0", "port": 8770, "pid": 12345, "started": 1774855000},
    {"id": "node-1", "port": 8771, "pid": 12346, "started": 1774855001}
  ]
}
```

**Docker 모드:**
- Docker Compose 서비스 이름으로 DNS 해석
- `anima-node-0:8765`, `anima-node-1:8765`, ...

### 6. docker-compose.hivemind.yml

Docker 모드용 Compose 파일. `hivemind_launcher.py --mode docker`가 자동 생성하거나 기존 파일 사용.

```yaml
services:
  gateway:
    image: dancindocker/anima:latest
    command: python hivemind_gateway.py --nodes 4
    ports:
      - "8765:8765"
    depends_on:
      - node-0
      - node-1
      - node-2
      - node-3

  node-0:
    image: dancindocker/anima:latest
    command: python anima/core/runtime/anima_runtime.hexa --web --port 8765 --instance node-0
    expose:
      - "8765"

  node-1:
    image: dancindocker/anima:latest
    command: python anima/core/runtime/anima_runtime.hexa --web --port 8765 --instance node-1
    expose:
      - "8765"

  node-2:
    image: dancindocker/anima:latest
    command: python anima/core/runtime/anima_runtime.hexa --web --port 8765 --instance node-2
    expose:
      - "8765"

  node-3:
    image: dancindocker/anima:latest
    command: python anima/core/runtime/anima_runtime.hexa --web --port 8765 --instance node-3
    expose:
      - "8765"
```

## Data Flow

### 유저 대화

```
User → Gateway(:8765) → Node-2(:8772) → process_input() → response
                      ← Node-2 ← anima_message ←
```

### 텐션 교환 (3초 간격)

```
Node-0 ──pulse──→ Node-1, Node-2, Node-3
Node-1 ──pulse──→ Node-0, Node-2, Node-3
Node-2 ──pulse──→ Node-0, Node-1, Node-3
Node-3 ──pulse──→ Node-0, Node-1, Node-2
```

### Hivemind 활성화

```
각 노드 Kuramoto r 계산
r > 2/3 → _hivemind_active = True
→ 집단 Φ 증폭 (hidden × 1.01)
→ Gateway에 sync 상태 전달
→ UI에 Hivemind 상태 표시
```

## File Structure

```
hivemind_launcher.py       # 엔트리포인트 (process/docker 모드)
hivemind_gateway.py        # WS 프록시 + 대시보드
hivemind_mesh.py           # 노드 간 텐션 교환 프로토콜
docker-compose.hivemind.yml  # Docker 모드용
```

## Error Handling

- 노드 크래시 → Gateway가 5초 헬스체크로 감지, 해당 노드 제외
- 전체 노드 다운 → Gateway가 503 반환
- Gateway 크래시 → 개별 노드는 독립 실행 유지 (직접 접속 가능)
- 메시 연결 끊김 → 자동 재연결 (5초 간격)

## Verification Criteria

ready/anima/tests/tests.hexa HIVEMIND 기준:
- Φ(연결) > Φ(단독) × 1.1
- CE(연결) < CE(단독)
- 연결 끊어도 각자 Φ 유지

## Usage Examples

```bash
# RunPod A100: 4노드 프로세스 모드
python hivemind_launcher.py --nodes 4

# RunPod A100: 자원 기반 자동
python hivemind_launcher.py --auto

# 자체 서버: Docker 4노드
python hivemind_launcher.py --nodes 4 --mode docker

# 개별 노드 접속 (디버그)
# http://localhost:8770  (node-0)
# http://localhost:8771  (node-1)
```
