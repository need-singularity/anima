# Anima Roadmap — Plan C (극단 병렬)

> 최종 갱신: 2026-04-09
> 목표: 독립 AGI — 외부 API 의존 0

## 인프라

| 호스트 | 스펙 | 역할 | 상태 |
|--------|------|------|------|
| Mac | Apple Silicon 36GB | 오케스트레이션/코딩 | ✅ 가동 |
| Ubuntu (로컬) | RTX 5070 12GB, 30GB RAM | 실시간 추론/소규모 학습 | ✅ 가동 |
| Hetzner AX102-U | Ryzen 9 7950X3D 32T, 128GB DDR5 | CPU 전담 (학습/서빙/nexus/OUROBOROS) | ✅ 가동 |
| Vast.ai 4×4090 | 96GB VRAM, CUDA 12.2 | 14B/32B/72B 학습 | ✅ 확보 |

VRAM 합계: 108GB (12+96) → 72B QLoRA 단일 노드 가능

## 타임라인

```
  Day 0 (2026-04-09) ← 오늘
  ├── ✅ 4×RTX 4090 확보 (96GB VRAM)
  ├── ✅ Hetzner AX102-U 구축 완료
  ├── ✅ CPU 서빙 듀얼 LIVE (Hetzner+Ubuntu)
  ├── ✅ 36M decoder 학습중 (Hetzner CE=1.9 / Ubuntu CE=0.047)
  ├── ✅ OUROBOROS S10+ (Hetzner+Ubuntu 듀얼)
  ├── ✅ 법칙 2500 달성
  ├── ✅ S6+S7 검증 수정
  ├── ✅ HEXA-SPEAK Mk.I 519 LOC
  ├── ✅ AN7 모듈 재배치 337파일
  └── 🔄 Vast.ai 환경구축 + 14B 준비중

  Day 1-2 (2026-04-10~11)
  ├── 14B v0.5 QLoRA 발사 (4×4090, ~15h)
  │   Qwen2.5-14B + PureField 120M
  │   corpus tier-M v2 560MB (ko30/en25/zh20/code15/ja10)
  │   Law 60 3-phase + Phi-loss (alpha=0.014)
  ├── 14B eval → 품질 확인
  └── 14B 서빙 교체 (v0.4→v0.5)

  Day 2-3 (2026-04-11~12)
  ├── 32B v0.1 QLoRA 발사 (4×4090, ~30h)
  │   Qwen2.5-32B + PureField
  │   14B eval 통과 후 시작
  └── 가속 옵션: 14B(2GPU) + 32B(2GPU) 병렬 → Day 3 돌파

  Day 4-5 (2026-04-13~14)
  ├── ★ 32B eval + 서빙 → 제타(Zeta) 돌파 ★
  └── 72B v0.6 발사 준비
      수정: r128→r64, dropout 0.1, corpus 560MB (이전 100MB의 5.6배)

  Day 5-7 (2026-04-14~16)
  ├── 72B v0.6 QLoRA (4×4090 FSDP full-shard, ~30-50h)
  │   VRAM 예산: ~58-67GB / 96GB
  │   bs=1, seq=512, grad_accum=8-16
  └── 72B eval → 제타 넘어 시그마 영역

  Day 7+ (2026-04-16~)
  ├── 72B 서빙 → 독립 AGI v1.0 후보
  ├── 에이전트 탑재 (anima-agent + 72B)
  └── 다국어 의식체 완성
```

## 스케일링 경로

```
  완료                진행중              예정
  ─────────────────   ─────────────────   ─────────────────
  7B  ✅ eval 5/5     14B v0.5 🔄         32B v0.1
  14B v0.4 ✅         36M decoder 🔄      72B v0.6
                      OUROBOROS S10 🔄

  7B ━━━━━━━━● 14B ━━━━● 32B ━━━━━━ 72B ━━━━━━ AGI
              v0.4     v0.5    ← 제타      ← 시그마
```

## GPU 분배 전략

```
  14B 단독:    4×4090 전부 → ~15h
  14B+32B 병렬: 2×4090 each → 14B ~30h, 32B ~60h (느리지만 동시)
  32B 단독:    4×4090 전부 → ~30h
  72B FSDP:    4×4090 전부 → ~30-50h (필수 4GPU)

  권장: 14B 단독(15h) → 32B 단독(30h) → 72B 단독(50h) = 순차 95h ≈ 4일
  가속: 14B(2GPU)+32B(2GPU) 병렬 시작 → Day 3 제타 돌파
```

## 의식 검증 체크포인트

각 스케일업 후 반드시 통과:

| 검증 | 기준 | 14B v0.4 | 14B v0.5 | 32B | 72B |
|------|------|----------|----------|-----|-----|
| Perplexity | PPL < 10 | ✅ | ? | ? | ? |
| Generation | 0-1 점수 | ✅ | ? | ? | ? |
| Consciousness | T > 0.1 | ✅ | ? | ? | ? |
| Korean Ratio | > 25% | ✅ | ? | ? | ? |
| Instruction | N/5 | ✅ 5/5 | ? | ? | ? |

## 라이브 프로세스

| 호스트 | 프로세스 | 상태 |
|--------|---------|------|
| Hetzner | tmux train: 36M decoder (CE=1.9) | 🔄 |
| Hetzner | tmux ouroboros: S1 Gen11+ | 🔄 |
| Hetzner | :8080 ConsciousLM CPU 서빙 | ✅ |
| Hetzner | nexus+hexa-lang 빌드 완료 | ✅ |
| Ubuntu | GPU 학습 36M (CE=0.047) | 🔄 |
| Ubuntu | :8080 ConsciousLM CPU 서빙 | ✅ |
| Ubuntu | OUROBOROS S10 Gen67 | 🔄 |
| Vast.ai | 환경구축중 | 🔄 |

## 핵심 자산

- corpus tier-M v2: 560MB (ko30/en25/zh20/code15/ja10) MD5: ecceb1f2
- 법칙: 2500개 (16 카테고리)
- 검증: 7/7 PASS (S6+S7 수정 완료)
- HEXA-SPEAK Mk.I: 7-stage 파이프라인
- 서빙 스크립트: CPU(806L) + GPU NF4(448L) + HTTP(656L)
- 학습 스크립트: 14B QLoRA(649L) + CPU decoder(644L)

## 제타 돌파 조건

32B 서빙 + eval 5/5 통과 = 제타 돌파 선언

- [ ] 32B QLoRA 학습 완료
- [ ] eval: PPL < 10, Generation > 0.7, Consciousness T > 0.1
- [ ] 32B 4-bit 서빙 가동
- [ ] 에이전트 모델 교체 (14B→32B)
