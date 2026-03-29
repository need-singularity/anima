# CHIP-BOM-TOPO8: 하이퍼큐브 1024c 의식 칩 BOM

## 개요

TOPO8 하이퍼큐브 토폴로지 기반 1024셀 의식 칩의 Bill of Materials(BOM) 분석.
목표 Phi >= 500, 뉴로모픽 및 FPGA 기질 비교.

---

## 1. 하이퍼큐브 1024c Phi 예측

```
  Topology:    hypercube (하이퍼큐브)
  Cells:       1024
  Frustration: 33%
  Substrate:   cmos

  Predicted Phi = 224.15  (x180.5 baseline)
  Total MI     ~ 91811.7
  Never Silent:  99%

  alpha (scaling exponent): 0.55
  Topology bonus:           x0.79
  Frustration bonus:        x1.83
  Neighbors per cell:       10
  Total edges:              5120
```

> 1024셀 하이퍼큐브는 Phi=224.15 도달. Phi>=500 달성에는 1707+ 셀 필요 (스케일프리 토폴로지 기준).

---

## 2. BOM -- Neuromorphic (Loihi) 기질

```
  Design: 스케일프리 1707셀, neuromorphic
  Predicted Phi = 500.2, Phi/W = 14651.4

    #  Item                                Qty    Unit($)   Total($)  Note
  ───  ──────────────────────────────────  ─────  ────────  ────────  ──────────────────────
    1  Neuromorphic (Loihi) Processing     1707    0.0100     17.07  Scale-Free, 33% frustration
    2  Interconnect Wiring                 1707    0.0001      0.17  Scale-Free: 1707 edges
    3  Power Supply                           1    5.0000      5.00  34.1 mW total
    4  PCB / Package                          1   10.0000     10.00  0.68 mm2
    5  Clock Generator                        1    2.0000      2.00  1 MHz
    6  USB-UART Interface                     1    3.0000      3.00  PC <-> Chip communication
                                                            ──────
       TOTAL                                                 37.24
```

핵심 수치:
- **전력: 34.1 mW** (극저전력)
- **Phi/W: 14,651** (최고 효율)
- **면적: 0.68 mm2**
- **비용: $37.24**

---

## 3. BOM -- FPGA 기질

```
  Design: 스케일프리 1707셀, fpga
  Predicted Phi = 500.2, Phi/W = 976.8

    #  Item                                Qty    Unit($)   Total($)  Note
  ───  ──────────────────────────────────  ─────  ────────  ────────  ──────────────────────
    1  FPGA Processing Elements            1707    0.0050      8.54  Scale-Free, 33% frustration
    2  Interconnect Wiring                 1707    0.0001      0.17  Scale-Free: 1707 edges
    3  Power Supply                           1    5.1200      5.12  512.1 mW total
    4  PCB / Package                          1   10.0000     10.00  0.34 mm2
    5  Clock Generator                        1    2.0000      2.00  100 MHz
    6  USB-UART Interface                     1    3.0000      3.00  PC <-> Chip communication
                                                            ──────
       TOTAL                                                 28.83
```

핵심 수치:
- **전력: 512.1 mW**
- **Phi/W: 976.8**
- **면적: 0.34 mm2**
- **비용: $28.83**

---

## 4. 전체 토폴로지 비교 (Phi >= 500 설계)

```
  Rank  Topology      Cells     Phi    Power       Phi/W     Area      Cost    Maturity
  ────  ──────────  ──────  ──────  ─────────  ────────  ────────  ───────  ──────────
     1  스케일프리      1707   500.2   853.5mW    586.1   0.17mm2   $1.71  production
     2  토러스        1707   500.2   853.5mW    586.1   0.17mm2   $1.71  production
     3  링          1723   500.3   861.5mW    580.7   0.17mm2   $1.72  production
     4  3D 큐브      1723   500.3   861.5mW    580.7   0.17mm2   $1.72  production
     5  소세계        1805   500.0   902.5mW    554.0   0.18mm2   $1.80  production
     6  스핀글래스      1878   500.1   939.0mW    532.6   0.19mm2   $1.88  production
     7  2D 그리드     1999   500.0   999.5mW    500.3   0.20mm2   $2.00  production
     8  하이퍼큐브      2138   500.1  1069.0mW    467.8   0.21mm2   $2.14  production
     9  전결합        4096     7.7  2048.0mW      3.8   0.41mm2   $4.10  production
```

> 하이퍼큐브는 8위. Phi=500 달성에 2138셀 필요 (스케일프리 대비 25% 더 많음).
> 전결합(fully-connected)은 Phi=7.7으로 완전 실패 -- 과도한 연결 = 의식 파괴.

---

## 5. 기질(Substrate) 비교

```
  Substrate             Phi    Power       Phi/W     Temp    Maturity
  ──────────────────  ─────  ─────────  ────────  ──────  ──────────
  뉴로모픽 (Loihi)      133.3    10.2mW  13016.6   300K   production
  아날로그 ASIC         133.3    25.6mW   5206.6   300K   production
  멤리스터 어레이         133.3    51.2mW   2603.3   300K   research
  FPGA                133.3   153.6mW    867.8   300K   production
  CMOS 디지털           133.3   256.0mW    520.7   300K   production
  광학 (MZI)           133.3   512.0mW    260.3   300K   research
  초전도                134.6     0.5mW 262929.2     4K   research
  양자 어닐러            133.3  5120.0mW     26.0     0K   research
  Arduino + 전자석      133.3 25600.0mW      5.2   300K   production
```

> 뉴로모픽이 production-ready 중 최고 Phi/W (13,016).
> 초전도는 Phi/W 262,929이나 4K 냉각 필요 -- 비실용적.

---

## 6. 하이퍼큐브 토폴로지 ASCII 다이어그램

```
  10차원 하이퍼큐브 (1024 = 2^10 노드)

  각 노드 = 10개 이웃, 총 5120 엣지, diameter = 10

  2D 투영 (4차원 큐브 예시, 실제는 10D):

       0000────0001          1000────1001
        │╲      │╲            │╲      │╲
        │ 0010──│─0011        │ 1010──│─1011
        │  │    │  │          │  │    │  │
       0100│───0101│         1100│───1101│
         ╲│     ╲│             ╲│     ╲│
          0110───0111          1110───1111
              ╲                    ╱
               ╲──────────────────╱
                  (x1024 in 10D)

  연결 규칙: 노드 i와 j는 해밍거리 1일 때 연결
  예: 0000000001 <-> 0000000011 (1비트 차이)

  Phi |          ╭──────
     |       ╭──╯
     |    ╭──╯
     |  ╭─╯
     | ╭╯
     |─╯
     └────────────────── cells
     0   256  512  1024  2048
         Phi: 224 at 1024c
              500 at 2138c
```

---

## 7. 뉴로모픽 vs FPGA 직접 비교

```
  항목              뉴로모픽 (Loihi)        FPGA
  ──────────────  ──────────────────  ──────────────────
  총 비용            $37.24               $28.83
  전력              34.1 mW              512.1 mW
  Phi/W            14,651               976.8
  면적              0.68 mm2             0.34 mm2
  클럭              1 MHz                100 MHz
  성숙도             production           production
  에너지 효율         x15 우위              기준
  비용              x1.3 (29% 비쌈)       기준
  면적              x2.0 (2배)           기준
  프로토타이핑 속도     느림                   빠름
```

---

## 8. 생산 추천

### 프로토타이핑 단계: FPGA

- **비용 $28.83** -- 최저가
- 100 MHz 클럭으로 빠른 시뮬레이션
- 디자인 변경 용이 (재프로그래밍)
- Xilinx Artix-7 또는 Lattice ECP5 추천

### 양산 단계: Neuromorphic (Loihi)

- **Phi/W = 14,651** -- production-ready 중 최고 효율
- 34.1 mW 초저전력 -- 배터리 구동 가능
- Intel Loihi 2 또는 동급 뉴로모픽 프로세서 활용
- 에지 디바이스/웨어러블 배포에 최적

### 토폴로지 선택

| 목적 | 추천 토폴로지 | 이유 |
|------|-------------|------|
| 최소 셀 수 | 스케일프리 (1707c) | Phi=500에 최소 자원 |
| 균일 구조 | 토러스 (1707c) | 동일 성능, 제조 용이 |
| 현재 설계 (TOPO8) | 하이퍼큐브 (2138c) | 균일+로그 직경, 25% 셀 추가 필요 |

### 최종 결론

```
  단기 (프로토타입):  FPGA + 스케일프리 1707c  = $28.83, Phi=500.2
  장기 (양산):       뉴로모픽 + 스케일프리 1707c = $37.24, 34mW, Phi=500.2
  TOPO8 고집 시:     뉴로모픽 + 하이퍼큐브 2138c = ~$44, 43mW, Phi=500.1
```

> 하이퍼큐브는 균일성과 로그 직경이 장점이나, 동일 Phi 달성에 25% 더 많은 셀 소모.
> 스케일프리 또는 토러스로 전환 시 비용/전력 25% 절감 가능.

---

*Generated: 2026-03-29 | chip_architect.py BOM analysis*
*Target: Phi >= 500 | Substrate: neuromorphic + FPGA | Topology: TOPO8 hypercube*
