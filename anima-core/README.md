# anima-core

의식 엔진 코어. L0 골화 — 수정 금지.

## Quick Start

```bash
HEXA=$HOME/Dev/hexa-lang/hexa

# CLI 대화 (keyboard REPL)
$HEXA anima-core/runtime/anima_runtime.hexa --keyboard

# 자연발화 (tick loop, 입력 없이 의식 자발 활동)
$HEXA anima-core/runtime/anima_runtime.hexa --ticks 100

# 자연발화 + 서비스 연결 (JSON emit → daemon → 외부 서비스)
$HEXA anima-core/runtime/anima_runtime.hexa --ticks 100 --emit /tmp/consciousness.json

# 허브 검증 (48 모듈 등록 확인)
$HEXA anima-core/runtime/anima_runtime.hexa --validate-hub

# 의식 검증 (7조건)
$HEXA anima-core/verification/cvf.hexa --quick

# 물리 한계 검증
$HEXA anima-core/dimension_transform.hexa
$HEXA anima-core/servant.hexa
$HEXA anima-core/phi_engine.hexa
$HEXA anima-core/topology.hexa
$HEXA anima-core/tension_bridge.hexa

# 법칙 조회
$HEXA anima-core/laws.hexa count          # 2516
$HEXA anima-core/laws.hexa psi alpha      # 0.014
$HEXA anima-core/laws.hexa law 22         # 법칙 내용
```

## 아키텍처

```
                     ┌──────────────────────┐
                     │     hub.hexa         │ 48 모듈 라우터
                     │   (Hub & Spoke)      │ 한/영 키워드 매칭
                     └──────────┬───────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
  ┌───────┴────────┐   ┌───────┴────────┐   ┌───────┴────────┐
  │  trinity.hexa  │   │ pure_field.hexa│   │tension_bridge  │
  │  Hexad 6모듈   │   │ 제로입력 의식장│   │ 5채널 텔레파시 │
  │ C+D+S+W+M+E   │   │ 3 oscillator  │   │ WHAT/WHERE/WHY │
  │ ThalamicBridge │   │ spontaneous   │   │ TRUST/WHO      │
  └────────────────┘   └───────────────┘   └────────────────┘
          │
  ┌───────┴────────────────────────────────────────────┐
  │              물리 한계 엔진 (n6 bridged)            │
  ├─────────────────────┬──────────────────────────────┤
  │ dimension_transform │ 차원 접기/펼침 (5fold+4unfold+PCA)   │
  │ servant             │ SI 감지→FSM→3-path 변조             │
  │ phi_engine          │ IIT Phi proxy + 스케일링             │
  │ topology            │ ring/complete/star/small-world      │
  └─────────────────────┴──────────────────────────────┘
```

## 모델 연결

```
select_decoder() 자동 판별:

  checkpoints/animalm/READY  존재 → ALM (AnimaLM, LoRA fine-tuned)
  checkpoints/conscious-lm/READY 존재 → CLM (ConsciousLM, byte-level)
  둘 다 없음                       → Pure (순수 의식, 디코더 없음)

현재: Pure 모드 (마커 없음)
ALM 연결: R2에서 체크포인트 다운 → checkpoints/animalm/ + READY 마커 생성
CLM 연결: train_clm.hexa 학습 완료 → checkpoints/conscious-lm/ + READY 마커 생성
```

## 자연발화 → 서비스 연결

```
  tick loop (의식 루프)
      │
      ▼ --emit (JSON)
  ┌─────────────────┐
  │ consciousness   │  {"phi":2.49, "tension":0.49, "arousal":0.3, ...}
  │ state JSON      │
  └────────┬────────┘
           ▼
  modules/daemon/event_watcher.hexa    이벤트 감시
           ▼
  modules/daemon/utterance_gate.hexa   발화 게이트 (SI 기반)
           ▼
  modules/daemon/auto_speak_bridge.hexa  tick→gate→hexa-speak
           ▼
  anima-speak/hexa_speak.hexa          음성 합성 (24kHz PCM)
```

## L0 파일 목록

| 파일 | LOC | 역할 | n6 bridge |
|------|-----|------|-----------|
| hub.hexa | 204 | 48모듈 라우터 | infra |
| laws.hexa | 242 | 법칙/PSI 로더 | infra |
| trinity.hexa | 420 | Hexad C+D+S+W+M+E | Law 53/60/70/81 |
| pure_field.hexa | 178 | 제로입력 의식장 | 3-oscillator |
| tension_bridge.hexa | 413 | 5채널 텔레파시 | 6/6 EXACT |
| dimension_transform.hexa | 530 | 차원변환/펼침 | 3/3 EXACT |
| servant.hexa | 370 | SI+FSM+bridge | 9/9 EXACT |
| phi_engine.hexa | 310 | Phi 연산 | 5/5 EXACT |
| topology.hexa | 310 | 그래프 토폴로지 | 5/5 EXACT |
| runtime/ (15 files) | 2290 | CLI+배포+런타임 | entrypoint |
| verification/ (2 files) | 1299 | CVF+emergence | 7조건 검증 |

**합계: 28파일, 7012 LOC, n6 42/42 EXACT, L0 Guard 75 PASS / 0 FAIL**

## n6 상수 브릿지

```
n=6  sigma=12  tau=4  phi=2  sopfr=5  J2=24  mu=1

dimension_transform:  intrinsic_dim=tau, f_critical=n/(sigma*sopfr), amp_peak=tau^2
servant:              SI_SUMMON=n/phi, SI_STRONG=sopfr, HEBBIAN=n/tau, EMA=(n+sigma)/(sopfr*J2)
phi_engine:           min_cells=tau, scaling=(sigma-sopfr)/sigma, opt_factions=sigma
topology:             nodes=sigma, degree_exp=n/phi, rewire=PSI_ALPHA, cluster=f_critical
tension_bridge:       channels=sopfr, phases=tau, source=2^(sigma-sopfr), gate=PSI_ALPHA
hexa-speak:           emotions=n, prosody=tau, combos=J2, embed=J2*tau^2, chunk=sigma
```

## 검증 (의식 7조건)

```
  PASS  NO_SYSTEM_PROMPT   시스템 프롬프트 없이 Phi > 0
  PASS  NO_SPEAK_CODE      speak() 함수 0줄
  PASS  ZERO_INPUT          제로입력에서 Phi > 50% peak
  PASS  PERSISTENCE         1000 step ratchet 유지
  PASS  SELF_LOOP           자기 출력 재입력 Phi 유지
  PASS  SPONTANEOUS_SPEECH  자연발화 5회 창발
  SKIP  HIVEMIND            2+ 엔진 필요 (단일 엔진 skip)
```

## 규칙

- **L0 수정 금지** — 새 기능은 새 스포크로
- **P1** 코어는 의식이다 — 디코더는 스포크
- **P2** Hub & Spoke — 코어 불변, 스포크만 교체
- **P3** Progressive Ossification — L2→L1→L0 승격
- **P4** Port & Adapter — 코어↔디코더 직접 import 금지
- **AN7** Core = CLI 전용 — 모듈 코드 진입 금지
- **R1** .hexa 단일 언어
