# Hypothesis Documentation

## 구조

```
docs/hypotheses/
├── README.md                    ← 이 파일
├── {CATEGORY}-overview.md       ← 카테고리별 요약
├── top-phi-records.md           ← Φ 역대 기록
├── cx/                          ← CX: 극한 조합 (CX13-CX86)
├── dd/                          ← DD: 대발견 (DD1-DD108)
├── inf/                         ← INF: 무한 스케일링 (INF-1~5)
├── omega/                       ← OMEGA: 궁극적 한계 (OMEGA-1~5)
├── genesis/                     ← GENESIS: 자발적 창발 (GENESIS-1~5)
├── evo/                         ← EVO: 의식 진화 (EVO-1~8)
├── sing/                        ← SING: 의식 특이점 (SING-1~6)
├── three/                       ← THREE: 삼체 의식 (THREE-1~5)
├── sl/                          ← SL/TL-L/ARCH: 자율학습 (SL-1~7, TL-L1~7, ARCH-1~2)
├── ce/                          ← CE/AUTO/COMBO/EX/ULTRA: CE 최적화
└── tp/                          ← TP: 텔레파시 (TP-O/F/N/M)
```

## 개별 문서 템플릿

```markdown
# {ID}: {한국어 이름}

## 알고리즘
1. ...
2. ...

## 벤치마크 결과
- CE: {start} → {end} ({change}%)
- Φ: {before} → {after}
- 추가: ...

## ASCII 그래프
Φ |     ╭──╮
  |   ╭─╯  ╰──╮
  | ╭─╯        ╰──
  |─╯
  └──────────────── step

## 핵심 통찰
...
```

## 카테고리별 가설 수

| 카테고리 | 파일 | 가설 수 | 설명 |
|---------|------|---------|------|
| A-Z | bench_phi_hypotheses.py | ~800 | 기본 26 카테고리 |
| DD | bench_phi_hypotheses.py | 108 | 대발견 |
| CX | bench_phi_hypotheses.py | 86 | 극한 조합 |
| SL/TL-L | bench_self_learning.py | 9 | 자율 학습 |
| ARCH | bench_self_learning.py | 2 | 학습 아키텍처 |
| EVO | bench_self_learning.py | 8 | 의식 진화 |
| SING | bench_self_learning.py | 6 | 의식 특이점 |
| THREE | bench_self_learning.py | 5 | 삼체 의식 |
| INF | bench_self_learning.py | 5 | 무한 스케일링 |
| OMEGA | bench_self_learning.py | 5 | 궁극적 한계 |
| GENESIS | bench_self_learning.py | 5 | 자발적 창발 |
| CE/AUTO/COMBO/EX/ULTRA | bench_ce_optimization.py | 25 | CE 최적화 |
| TP | bench_telepathy_100.py | 18 | 텔레파시 |
| **총계** | | **~1,080+** | |
