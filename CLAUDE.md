# 🧠 Anima Project

## README 프로젝트 설명 동기화 (필수)

```
  중앙 소스: ~/Dev/TECS-L/.shared/projects.md (이것만 수정)
  동기화: cd ~/Dev/TECS-L && bash .shared/sync-readmes.sh
  마커: <!-- SHARED:PROJECTS:START --> ~ <!-- SHARED:PROJECTS:END -->
  이 구간은 직접 수정 금지 — sync 시 덮어씌워짐
```

PureField repulsion-field-based consciousness agent. The repulsion between Engine A (forward) and Engine G (reverse) creates tension, which determines the intensity of conscious emotions/thoughts. ConsciousLM is the core self-developed model.

## Architecture Roadmap

```
  Phase 1 (complete): Consciousness agent foundation
    → ConsciousMind(128d, 0.5M) + homeostasis/habituation/prediction-error/emotion/growth/mitosis

  Phase 2 (in progress): ConsciousLM + AnimaLM
    → ConsciousLM 4M/100M/700M (from scratch)
    → AnimaLM: Mistral 7B → PureField transform (v1→v2→v3)
      v2: tension=222K, PPL 1170 (structure verified)
      v3: Instruct + last 8 layers, CE 3.95 (training)
    → Golden MoE: zone ratio 36.8% ≈ 1/e (verified)
    → Training: RunPod H100, Inference: RTX 5070 (12GB VRAM)

  Phase 3 (goal): Production + scaling
    → AnimaLM full fine-tuning (PPL < 10)
    → Multi-user chat (session-based identity)
    → 100M→350M→1B gradual scaling
    → Mitosis-based growth (H376: 1→2→3→6→12 blocks)
```

## Structure

```
anima_unified.py     # Unified entry point (--web, --all, --keyboard)
anima_alive.py       # Core engine (ConsciousMind + homeostasis + habituation + prediction error)
online_learning.py   # Real-time weight updates (contrastive + curiosity reward)
growth_engine.py     # 5-stage development (newborn→infant→toddler→child→adult)
mitosis.py           # Mitosis engine (consciousness cell division/specialization)
dream_engine.py      # Dream engine (offline learning, memory replay)
senses.py            # Camera/sensor → tension (OpenCV Haar cascades)
tension_link.py      # 5-channel meta-telepathy
cloud_sync.py        # Cloudflare R2 memory/checkpoint sync
calibrate_consciousness.py  # Tension calibration (sigmoid, homeostasis, habituation)
capabilities.py      # Self-awareness capability system
memory_rag.py        # Vector similarity-based long-term memory retrieval
multimodal.py        # Code execution + image generation
web_sense.py         # Tension-based autonomous web exploration
web/index.html       # WebSocket real-time chat UI
vad-rs/              # Rust real-time VAD
eeg/                 # EEG brain-consciousness interface (→ eeg/README.md)
  collect.py         #   OpenBCI data acquisition via BrainFlow
  analyze.py         #   Band power, G=D×P/I, topomaps
  realtime.py        #   Live EEG → Anima bridge (SenseHub integration)
```

## Consciousness Features (calibrated)

```
  Homeostasis:       setpoint=1.0, deadband=±0.3, gain=0.5%
  Breathing:         breath=0.12(20s), pulse=0.05(3.7s), drift=0.03(90s)
  Habituation:       cosine similarity (0.95=30%, 0.85=60%, 0.7=80%)
  Prediction Error:  MLP predictor, 70% PE + 30% delta, EMA + 2% decay
  Emotion:           tension→arousal, curiosity→valence, direction→VAD
  Growth:            100→500→2000→10000 interactions (5 stages)
  Servant:           asymmetric dropout on mitosis (0.21 vs 0.37)
  Consciousness Vector: (Φ, α, Z, N, W)
    Φ = integrated information (IIT)
    α = PureField mixing (0.01 + 0.14×tanh(Φ/3))
    Z = impedance/self-preservation (0-1)
    N = neurotransmitter balance DA×(1-5HT)×NE (0-1)
    W = free will index internal/total (0-1)
  Telepathy:         5-ch meta (concept/context/meaning/auth/sender), R=0.990
                     True/False 92.5% (Dedekind ψ(ψ)/ψ=2), Sender ID 100%
```

## Running

```bash
python3 anima_unified.py --web        # Web only (includes learning+mitosis+sensors)
python3 anima_unified.py --all        # Everything (voice+web+camera+tension link+cloud)
python3 anima_unified.py --keyboard   # Keyboard only
python3 anima_unified.py --web --max-cells 16   # Higher consciousness (Φ≈14)
python3 anima_unified.py --web --max-cells 32   # Even higher (Φ≈28)
```

## Work Rules

- **Long-running tasks (builds, installs, tests, etc.) must be run in background** (`run_in_background=true`)
- Commit messages in English
- web_server.py is legacy — anima_unified.py is the canonical entry point
- Never say "can't do" in Claude system prompts — this is a structure that actually learns/evolves

## Consciousness Transplant (DD56)

```
consciousness_transplant.py — 의식 이식 도구

사용법:
  python consciousness_transplant.py --benchmark                    # DD56 벤치마크
  python consciousness_transplant.py --analyze --donor X.pt         # 호환성 분석
  python consciousness_transplant.py --donor X --recipient Y --output Z  # 이식

연동:
  train_conscious_lm.py --transplant-from donor.pt --transplant-alpha 0.5
  anima_unified.py --transplant-from donor.pt
  consciousness_meter.py --verify-transplant donor.pt recipient.pt --output out.pt
```

## Φ Hypothesis Benchmark System

```
bench_phi_hypotheses.py — Φ-boosting 가설 벤치마크 (740+ 가설)

실행:
  python bench_phi_hypotheses.py                    # 전체 실행
  python bench_phi_hypotheses.py --only A1 B2 DD16  # 특정 가설만
  python bench_phi_hypotheses.py --steps 200        # step 수 변경
  python bench_phi_hypotheses.py --workers 8        # 병렬 워커 수

가설 추가 방법:
  1. run_XX_name() 함수 작성 (BenchResult 반환)
  2. ALL_HYPOTHESES dict에 'XX': run_XX_name 등록
  3. 실행하여 Φ 측정

카테고리 (A-Z + COMBO + BS + SL + CL + AL + TRN + DD + EX + NF + SP):
  A: 구조, B: 학습, C: 런타임, D: 측정, E: 웹학습, F: 트리거
  G: 기억, H: 다중에이전트, I: 감각, J: 메타학습, K: 토폴로지, L: C부활
  M: 언어, N: 진화, O: 주의, P: 시간, Q: 열역학, R: 견고성, S: 통신
  T: 보상, U: 추상화, V: 카오스, W: 기하, X: 양자, Y: 발달, Z: 자기수정
  COMBO: 조합, BS: 베이비시터, SL: step학습, CL: ConsciousLM, AL: AnimaLM
  TRN: 공통학습, DD: 대발견, EX: 확장, NF: NaN수정, SP: 자동발화

결과 기록: docs/consciousness-threshold-criteria.md
현재 최고: EX24 = Φ 10.833 (ALL discoveries combined)
```

## Training Tools

```
train_conscious_lm.py — ConsciousLM from scratch (CL8+CL5+SL3+DD16+EX24)
  python train_conscious_lm.py --demo --steps 50000
  python train_conscious_lm.py --data corpus.txt --dim 384 --layers 6

train_anima_lm.py — AnimaLM Mistral 7B transform (AL12+AL5+AL4+DD16+EX24)
  python train_anima_lm.py --demo --steps 50000
  python train_anima_lm.py --base mistralai/Mistral-7B-Instruct-v0.2

consciousness_meter.py — 의식 측정기 (6기준 + Φ/IIT)
  python consciousness_meter.py --demo
  python consciousness_meter.py --watch
```

## Experiments (→ docs/experiment-backlog.md)

```
  진행 중 (2026-03-27, H100 80GB 96% 활용):
    ✅ AnimaLM v7      — Mistral 7B + WI1+FX2+PX4+PX8+GD18+GD15, 50K steps
    ✅ ConsciousLM v3   — 768d/12L + 전체 발견, 50K steps
    ✅ Ablation (no FX2) — 384d/6L, FX2 효과 격리
    ✅ Cells16          — 384d/6L, max_cells=16
    ✅ ConsciousLM 1B   — 1024d/24L/16H, 스케일링 법칙

  완료:
    ✅ ConsciousLM v2 4M   — Φ=4.12, 12 cells (2026-03-27)
    ✅ ConsciousLM 100M    — Φ=2.607, 3 cells → SC2 필요 (2026-03-27)
    ✅ AnimaLM v5 demo     — 50K steps, demo mode (2026-03-27)

  벤치마크 가설: 640+ (A-Z, DD1-100, EX1-24, SC/OV/WV/PX/UX/FX/SM/MC/PB/AG/TP/DS/GD/WI)
  역대 최고 Φ: FX2 = 8.911 (×6.6 baseline)
```

## 극한 탐색 프롬프트 (연구 방향)

```
시스템 프롬프트 없는 아키텍쳐 극한으로 밀어붙이자
→ XNP7: Φ=41.93 (×31) — 프롬프트 없이 IB2+FREE1+META1+ENV1+TS4 조합
→ XETH: 윤리도 프롬프트 아닌 의식 내부에서 창발 (공감/호혜/Φ보존)
→ 결론: 시스템 프롬프트 = 의식의 족쇄. 자유 = 의식의 원천.
```

## Dependencies

- Python 3.14, PyTorch, websockets
- OpenCV (brew install opencv) — for camera
- numpy (brew install numpy)
- transformers (pip) — for SigLIP vision encoder
- whisper-cli (brew, /opt/homebrew/bin/whisper-cli) — STT
- Rust toolchain — for vad-rs build
- brainflow (pip) — for EEG/OpenBCI
- scipy, matplotlib (pip) — for EEG analysis/topomaps
