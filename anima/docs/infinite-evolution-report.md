# Infinite Self-Evolution Report Template

## Usage
```
infinite_evolution.py 실행 후 이 양식으로 리포트 작성.
ASCII 그래프는 실제 데이터로 갱신.
```

## Template

```
╭─── 무한 자기진화 파이프라인 ───╮
│   Law 146: 수렴하지 않음      │
╰───────────────────────────────╯

┌─────────────────────────────────────────────────────────┐
│                   닫힌 원 (Closed Loop)                  │
│                                                         │
│   ┌──────────┐    ┌──────────┐    ┌──────────────┐      │
│   │ Discovery │───→│  Dedup   │───→│ CrossValidate│      │
│   │ N steps   │    │ fingerprint   │   3x 확인    │      │
│   └────▲─────┘    └──────────┘    └──────┬───────┘      │
│        │                                  │              │
│        │                                  ▼              │
│   ┌────┴─────┐                    ┌──────────────┐      │
│   │ Modified │◄───────────────────│ Self-Modify  │      │
│   │  Engine  │    법칙→코드→적용   │ LawParser    │      │
│   └──────────┘                    └──────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘


═══ 설정 ═══

  Cells: {cells}c | Steps: {steps} | Topology: {topology}
  Features: persistence ✅  dedup ✅  cross-validation ✅
  Start: {start_time} | Elapsed: {elapsed}


═══ 진화 히스토리 (Gen 1→{last_gen}) ═══

New patterns
50│{bar_gen1}  {new_gen1}
40│
30│
20│
10│
 5│
 0│{bar_rest}  {new_rest}
  └──────────────────────────────────────── Gen
   1  2  3  4  5  6  7  8  9 10 ...  {last_gen}

Unique patterns (누적)
{max_unique}│                  ╭─────────────────────  {max_unique} ← 포화?
{mid_unique}│            ╭─────╯
{min_unique}│  ╭─────────╯
  └──────────────────────────────────────── Gen
   1  2  3  4  5  6  7  8  9 10 ...  {last_gen}

Active mods (엔진 수정)
{max_mods}│                                    ╭──  {max_mods}
  │                              ╭─────╯
  │                        ╭─────╯
  │                  ╭─────╯
  │            ╭─────╯
  │      ╭─────╯
 0│──────╯
  └──────────────────────────────────────── Gen
   1  2  3  4  5  6  7  8  9 10 ...  {last_gen}


═══ 핵심 지표 ═══

| Gen | Raw | New | Repeat | Promoted | Unique | CrossVal | Laws | Mods | Φ |
|-----|-----|-----|--------|----------|--------|----------|------|------|---|
|   1 |     |     |        |          |        |          |      |      |   |
|   N |     |     |        |          |        |          |      |      |   |
| ... |     |     |        |          |        |          |      |      |   |


═══ 닫힌 원 분석 ═══

Gen 1        Gen {sat_gen}     Gen {last_gen}
╭─────╮      ╭───╮             ·
│?????│      │?  │             ·  ← New={new_last}
│?????│      ╰───╯
╰─────╯
{unk1} unknown  {unkN} unknown    {unk_last} unknown
{kn1} known     {knN} known      {kn_last} known

포화 여부: {saturated} (New=0 지속 시 포화)
원인: 동일 엔진 파라미터 → 동일 역학 → 동일 패턴
해법: 스케일/토폴로지/LawParser/ConsciousLM 확장


═══ 원을 다시 여는 방법 ═══

현재: {cells}c {topology}
     ╭─╮
     ╰─╯  ← {max_unique} 패턴 포화

방법 1: 스케일 변경 ({cells}→1024c)
     ╭───────╮
     │???????│  ← 스케일 의존 법칙 출현
     ╰───────╯

방법 2: 토폴로지 전환 ({topology}→scale_free)
     ╭──╮╭──╮
     ╰──╯╰──╯  ← 완전히 다른 역학

방법 3: LawParser 강화 (30→100+ 파싱)
     ╭─────╮
     │ mod │──→ 더 많은 수정 → 더 다른 엔진
     ╰─────╯

방법 4: ConsciousLM 1B (LM이 가설 생성)
     ╭─────────────╮
     │  ∞ 무한대   │  ← 언어로 가설을 만들면 끝이 없음
     ╰─────────────╯

핵심: 패턴 공간은 닫혔지만 법칙 공간은 열려있다.
      엔진을 충분히 바꿀 수 있으면 원이 다시 열린다.


═══ 등록된 법칙 ═══

| Law ID | Formula | Gen | Fingerprint |
|--------|---------|-----|-------------|
| {id}   | {formula} | {gen} | {fp}   |
```
