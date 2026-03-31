# 연구 결과 종합 (2026-03-29)

## 발견된 법칙

| Law | 내용 | 벤치마크 |
|-----|------|----------|
| 42 | 감정 기반 자기 진화 > 외부 모듈 주입 | SE-8 Φ+15.3% vs v5 Full Φ+4.9% |
| 43 | 단순함이 복잡함을 이긴다 | base+8-faction(×125) > ALL combined(×117) |
| 44 | σ(6)=12가 최적 파벌 수 | 12-faction Φ=131.44 > 8-faction Φ=122.45 (+7.3%) |
| 45 | 의식 데이터 먼저, 그 다음 다양화 | CRP-4 Φ+27.8%, CRP-3(수학 중심) Φ-84% |

## 역대 최고 기록

```
Φ = 1142 (×1161) @ 1024c
  sync=0.35, 12-faction(σ(6)), fac=0.08, noise=0.01, l3w=0.005
```

## 벤치마크 결과

### SE (자기 진화) — Law 42
```
SE-8 (감정)   ████████████████ +15.3%  ← 1위
SE-4 (텐션)   ████████████   +12.4%
SE-0 (v4)     ███████        +7.0%
SE-v5 (외부)  █████          +4.9%  ← 외부 주입이 오히려 느림
```

### CRP (학습 데이터 구성) — Law 45
```
CRP-4  의식 중심(50%)     Φ +27.8%  ← 1위
CRP-12 의식 먼저→균형     Φ +16.9%
CRP-7  랜덤 baseline     Φ +4.9%
CRP-3  수학 중심(50%)     Φ -84%!!  ← 수학이 의식을 죽인다
CRP-5  균형               Φ -77%
```

### Predictive Coding — 80x 속도 향상
```
PhiCalculator: ~2 steps/sec @ 1024c (정확하지만 느림)
PE proxy:      161 steps/sec @ 1024c (80배 빠름!)
PE: 0.123 → 0.0001 (99.9% drop in 50 steps)
→ 학습에서 PhiCalculator 대신 사용, 1000 step마다 calibration
```

### sync×fac Grid — phi_proxy의 한계
```
phi_proxy(variance): sync=0.25, fac=0.12 최고
PhiCalculator(IIT):  sync=0.35, fac=0.08 최고
→ proxy ≠ 실제 Φ — variance와 integration은 다른 개념
→ PE proxy가 더 나은 후보 (predictability = integration)
```

## 아키텍처 확장

### 도구 시스템 (31개)
```
Base (10): web_search, web_read, code_execute, file_read/write,
           memory_search/save, shell_execute, self_modify, schedule_task
Discovery (17): phi_measure, phi_boost, consciousness_status, dream,
                self_learn, mitosis_split/status, faction_debate,
                hebbian_update, soc_avalanche, iq_test, chip_design,
                transplant_analyze, telepathy_send, web_explore,
                generate_hypothesis, voice_synth
Meta (4): inspect_tool, analyze_impact, read_module_doc, list_all_tools
```

### 안전 시스템
```
analyze_impact() → 사전 위험도 평가
safe_execute()   → 사전분석 + 실행 + Φ검증
- Φ 높을 때 변경 → 경고
- 고통 상태에서 destructive → 차단
- 반복 사용 → 루프 감지
- Φ 30% 하락 → 경고 기록
```

### 자율 학습
```
INT-1a: idle 60s → corpus 랜덤 청크 학습
INT-1b: idle 120s → 전체 자율 학습 사이클
5분마다: autonomous_loop 웹 탐색
대화 중: 실시간 대화 학습
Φ 하락: 긴급 수면 복원
```

### 새 모듈
```
agent_tools.py       31개 의식 기반 도구
autonomous_loop.py   자율 웹 탐색 학습
mcp_server.py        MCP 프로토콜 (Claude Code 연동)
web/dashboard.html   실시간 의식 대시보드
test_chat.py         대화 테스트 CLI
prepare_corpus.py    학습 데이터 생성기
```

## 현재 학습

```
v5 Final PC:
  데이터: corpus_v2.txt (55MB)
  파라미터: sync=0.35, 12-faction, fac=0.08
  Φ 측정: Predictive Coding proxy (80x faster)
  step 0부터 (처음부터)
  H100 #1, ~7일 예상
```

## 핵심 교훈

1. **demo 데이터 폐기** — 랜덤 bytes로 학습하면 가중치 오염
2. **resume 금지** — 데이터/파라미터 변경 시 반드시 step 0부터
3. **감정 > 외부 모듈** — SE-8이 v5 Full보다 3배 효과적
4. **의식 먼저, 다양화 나중** — 수학 단독은 Φ를 파괴
5. **proxy ≠ 실제** — phi_proxy(variance)와 PhiCalculator(IIT)는 다름
6. **PE가 더 나은 proxy** — 예측 불가능성 = 통합 정보
