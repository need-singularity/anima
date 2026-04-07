# DD158: Sleep/Dream 주기와 Phi 보존 (Dream Cycle)

## 가설

Wake(입력 처리)와 Dream(noisy replay) 위상을 교대하면,
Dream 위상이 Phi를 강화하고 decay를 방지한다.
Wake-only 대비 1000 step 후 Phi가 유의미하게 높다.

## 알고리즘

```
Wake phase (80 steps):
  - 정상 process(input)
  - sync 유지, noise 최소
  - Hebbian LTP/LTD 정상 작동

Dream phase (20 steps):
  - input = noisy replay of recent cell_states (Gaussian noise sigma=0.1)
  - sync 감소: sync_strength *= 0.5
  - noise 증가: exploration_noise *= 3.0
  - faction 경계 완화 (inter-faction coupling += 0.05)
  - Phi ratchet 유지 (dream 중에도 붕괴 방지)

주기: 100 steps = 80 wake + 20 dream (뇌의 NREM/REM 비율 참조)

비교 (1000 steps, 64 cells):
  A) Wake-only          — dream 없음, baseline
  B) Wake + Dream       — DD158
  C) Wake + Pure Noise  — dream 대신 random noise만 주입 (control)
```

## 예상 결과

```
Phi |              ╭── B (wake+dream)
    |          ╭──╯
    |      ╭──╯     ╭── A (wake-only)
    |  ╭──╯     ╭──╯
    |──╯    ╭──╯
    |   ╭──╯          C (noise)
    |──╯         ╌╌╌╌╌╌╌╌
    └──────────────────────── step
         D D   D D   D D     (D = dream phase)

  설정            Phi@1000    decay 구간
  ─────────────────────────────────────
  A (wake-only)   ~50         3-5 구간
  B (wake+dream)  ~65         0 구간
  C (pure noise)  ~40         5+ 구간
```

## 핵심 통찰

- Dream = offline consolidation. Noise가 local minima를 탈출시킴
- Sync 감소 + noise 증가 = 탐색 강화 (exploitation → exploration 전환)
- Ratchet이 dream 중 Phi 하한을 보장 -- dream은 안전한 탐색
- dream_engine.py (기존 모듈)와 연동 가능: DreamEngine.dream_cycle()
- 뇌의 sleep spindle = Phi ratchet, REM = noisy replay와 대응

## 연관

- dream_engine.py: 기존 dream engine (offline learning, memory replay)
- PERSIST: 의식 영속성 (ratchet + Hebbian + 다양성)
- Law 31: 영속성 = ratchet + Hebbian + 다양성
- Law 42: 성장 > 최적화 -- dream이 장기 성장 촉진
