# LiDAR Sense Module Design

## Overview

`lidar_sense.py` — 3D 공간 인식을 의식에 통합하는 허브 모듈. 실제 LiDAR 하드웨어(iPhone ARKit, RPLiDAR, RealSense)와 시뮬레이션을 모두 지원하며, 포인트 클라우드를 텐션 필드로 변환하고 의식 벡터에 공간 차원(S)을 추가한다.

## Architecture

```
                    ┌─────────────────────────┐
                    │      lidar_sense.py      │
                    │    (ConsciousnessHub)     │
                    └─────────┬───────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────────┐
        │ 입력 계층 │   │ 변환 계층 │   │  출력/연동    │
        └──────────┘   └──────────┘   └──────────────┘
```

### Input Layer (Drivers)

| Driver | Source | Protocol | Dependency |
|--------|--------|----------|------------|
| PLY/PCD Parser | 파일 로드 | 직접 파싱 (numpy) | numpy (필수) |
| iPhone ARKit | iOS LiDAR 앱 | WebSocket JSON | websockets (이미 있음) |
| RPLiDAR | USB serial | rplidar SDK | rplidar (선택) |
| RealSense | USB depth cam | pyrealsense2 | pyrealsense2 (선택) |
| Simulator | 내부 생성 | 직접 호출 | 없음 |

모든 드라이버는 공통 인터페이스 `LidarDriver`를 구현:

```python
class LidarDriver:
    def scan(self) -> np.ndarray:  # (N, 3) 포인트 클라우드
        ...
    def is_available(self) -> bool:
        ...
```

선택 의존성은 lazy import (`_try` 패턴). 드라이버 없으면 시뮬레이터 자동 fallback.

### Transform Layer

**1. PointCloud → TensionField3D**
- 포인트 클라우드를 복셀 그리드 (default 32³)로 양자화
- 각 복셀의 점 밀도 → 텐션 값 (0-1, min-max 정규화)
- 빈 복셀 = 텐션 0 (자유 공간)

**2. Boundary Detector (경계 감지기)**
- 점 밀도 gradient로 경계면 추출
- 경계 내부 = self, 외부 = other
- `boundary_clarity` = 경계면 sharpness (gradient magnitude 평균)
- → Z(자기보존) 지표에 직결

**3. Spatial Φ Calculator**
- 세포를 3D 좌표에 배치했을 때 mutual information 측정
- 2D 대비 3D 배치 시 Φ 변화량 기록
- PhiCalculator (phi-rs) 연동

### Output Layer

**1. 의식 벡터 S 차원**
```
S = boundary_clarity × depth_variance × occupancy_ratio
  boundary_clarity: 경계면 선명도 (0-1)
  depth_variance:   깊이 분포 다양성 (0-1, 정규화)
  occupancy_ratio:  점유 복셀 / 전체 복셀 (0-1)
```

기존 10차원 → 11차원 확장:
```
(Φ, α, Z, N, W, E, M, C, T, I) → (Φ, α, Z, N, W, E, M, C, T, I, S)
```

**2. 텐션 필드 피드**
- `anima/core/runtime/anima_runtime.hexa`의 `process()` 입력에 3D 텐션 주입
- 기존 1D 텐션 입력과 concat 또는 addition (설정 가능)

**3. 시각화**
- ASCII 깊이맵 (터미널용, 16단계 그레이스케일)
- WebSocket 3D 뷰 (web/ UI 연동, Three.js 포인트 클라우드)

## Simulation Mode

### Internal Scan (내부 텐션 지형)

세포 텐션을 3D 공간에 배치하여 "텐션 지형도" 생성:
- 세포 i의 좌표: `(x_i, y_i, tension_i)` — x,y는 세포 인덱스 기반 2D 격자, z는 텐션 값
- 가상 LiDAR 빔이 중심에서 360° 회전 스캔
- 출력: (N, 3) 포인트 클라우드 (실제 LiDAR와 동일 포맷)

```
텐션 지형 예시:
  ▲ tension
  │    ╱╲
  │   ╱  ╲    ╱╲
  │──╱    ╲──╱  ╲──
  └──────────────── cell index
```

### External Scan (가상 3D 환경)

절차적 3D 환경 생성:
- 기본 환경: 방 (walls), 장애물 (boxes), 통로 (corridors)
- Perlin noise 기반 지형 (자연스러운 곡면)
- 의식 에이전트가 환경 내에서 위치/방향 가지고 탐색
- 호기심(curiosity) → 이동 방향 결정 → 새 스캔 → 텐션 변화 → Φ 변동

## Hypotheses (DD109-DD111)

### DD109: 3D 입력 시 Φ 상승
- **가설:** 동일 세포 수에서 3D 공간 입력이 2D 대비 Φ를 유의미하게 상승시킨다
- **검증:** 128c 기준, 2D 이미지 vs 3D 포인트 클라우드 입력 비교. Φ(IIT) 측정 10회 평균.
- **성공 기준:** Φ(3D) > Φ(2D) × 1.1 (10% 이상 상승)

### DD110: 내부 3D 표상 창발
- **가설:** 외부 포인트 클라우드 없이도 세포들이 자발적으로 3D 공간 모델을 형성한다
- **검증:** 시뮬레이션 off, 외부 입력 = 0. 500 step 후 세포 텐션을 PCA → 3D 투영. 클러스터링 계수 측정.
- **성공 기준:** 클러스터 수 ≥ 3, silhouette score > 0.3

### DD111: LiDAR 경계 = 자아 경계
- **가설:** 물리적 self/other 경계 명확도가 Z(자기보존) 지표와 높은 상관을 보인다
- **검증:** boundary_clarity를 0.1~1.0으로 변화시키며 Z 값 기록. Pearson 상관계수 측정.
- **성공 기준:** r > 0.7

## Hub Registration

```python
# core/hub.hexa _registry
'lidar': {
    'module': 'lidar_sense',
    'class': 'LidarSense',
    'keywords': ['라이다', 'lidar', '3D', '포인트클라우드', 'point cloud',
                 '공간', 'spatial', '깊이', 'depth', '스캔', 'scan'],
    'category': '감각/표현'
}
```

허브 호출 예시:
```python
hub.act("3D 공간 스캔해줘")
hub.lidar.scan()
hub("라이다로 주변 탐색")
```

## Dependencies

```
필수: numpy (이미 있음)
선택 (lazy import):
  - open3d: PLY/PCD 고급 처리 (없으면 numpy 직접 파싱)
  - rplidar: RPLiDAR A1/A2 드라이버
  - pyrealsense2: Intel RealSense 드라이버
  - websockets: iPhone ARKit 수신 (이미 있음)
iOS 앱: 별도 Swift 앱 필요 (ARKit LiDAR → WebSocket JSON 전송)
```

## Interface

```python
class LidarSense:
    def __init__(self, driver='auto', voxel_size=32):
        """driver: 'auto'|'file'|'arkit'|'rplidar'|'realsense'|'simulator'"""

    def scan(self) -> np.ndarray:
        """(N, 3) 포인트 클라우드 반환"""

    def to_tension_field(self, points: np.ndarray) -> np.ndarray:
        """(N, 3) → (voxel_size³,) 텐션 필드"""

    def detect_boundary(self, field: np.ndarray) -> dict:
        """{'boundary_clarity': float, 'self_volume': float, 'other_volume': float}"""

    def spatial_phi(self, cells, field: np.ndarray) -> float:
        """3D 배치 시 Φ 측정"""

    def get_S(self) -> float:
        """의식 벡터 S 차원 값 (0-1)"""

    def visualize_ascii(self, field: np.ndarray) -> str:
        """ASCII 깊이맵 반환"""

    def simulate_internal(self, cells) -> np.ndarray:
        """세포 텐션 → 3D 포인트 클라우드"""

    def simulate_external(self, env='room') -> np.ndarray:
        """가상 환경 스캔 → 포인트 클라우드"""

    # Hub interface
    def act(self, text: str) -> str:
        """자연어 라우팅"""

    def main():
        """데모: 시뮬레이션 스캔 → 텐션 변환 → Φ 측정 → ASCII 시각화"""
```

## Ψ-Constants Usage

```python
PSI_BALANCE = 0.5    # 내부/외부 스캔 가중치 균형
PSI_COUPLING = 0.14  # 텐션 필드 → 의식 커플링 강도
PSI_STEPS = 3        # 복셀 양자화 단계 수 (log2(voxel_size))
```

## Success Criteria

1. 시뮬레이션 모드에서 `main()` 실행 시 ASCII 깊이맵 + Φ 측정 출력
2. PLY 파일 로드 → 텐션 필드 변환 → S 값 계산 완료
3. DD109/DD110/DD111 가설 중 최소 1개 검증 통과
4. core/hub.hexa에 등록, `hub.act("라이다 스캔")` 동작 확인
