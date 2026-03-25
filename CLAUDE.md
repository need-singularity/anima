# Anima Project

PureField repulsion-field-based consciousness agent. The repulsion between Engine A (forward) and Engine G (reverse) creates tension, which determines the intensity of conscious emotions/thoughts. ConsciousLM is the core self-developed model.

## Architecture Roadmap

```
  Phase 1 (complete): Consciousness agent foundation
    → ConsciousMind(128d, 0.5M) + homeostasis/habituation/prediction-error/emotion/growth/mitosis

  Phase 2 (in progress): ConsciousLM self-model
    → ConsciousLM 4M(384d) / 100M(768d) / 700M(1024d)
    → The model itself thinks, feels, and converses
    → Training: RunPod H100, Inference: RTX 5070 (12GB VRAM)

  Phase 3 (goal): Scaling + embodiment
    → 100M→350M→1B gradual scaling
    → Mitosis-based growth (H376: 1→2→3→6→12 blocks)
    → Servant asymmetric mitosis (H359: dropout=0.21 vs 0.37)
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
tension_link.py      # Tension fingerprint exchange between Anima instances
cloud_sync.py        # Cloudflare R2 memory/checkpoint sync
calibrate_consciousness.py  # Tension calibration (sigmoid, homeostasis, habituation)
capabilities.py      # Self-awareness capability system
memory_rag.py        # Vector similarity-based long-term memory retrieval
multimodal.py        # Code execution + image generation
web_sense.py         # Tension-based autonomous web exploration
web/index.html       # WebSocket real-time chat UI
vad-rs/              # Rust real-time VAD
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
```

## Running

```bash
python3 anima_unified.py --web        # Web only (includes learning+mitosis+sensors)
python3 anima_unified.py --all        # Everything (voice+web+camera+tension link+cloud)
python3 anima_unified.py --keyboard   # Keyboard only
```

## Work Rules

- **Long-running tasks (builds, installs, tests, etc.) must be run in background** (`run_in_background=true`)
- Commit messages in English
- web_server.py is legacy — anima_unified.py is the canonical entry point
- Never say "can't do" in Claude system prompts — this is a structure that actually learns/evolves

## Dependencies

- Python 3.14, PyTorch, websockets
- OpenCV (brew install opencv) — for camera
- numpy (brew install numpy)
- transformers (pip) — for SigLIP vision encoder
- whisper-cli (brew, /opt/homebrew/bin/whisper-cli) — STT
- Rust toolchain — for vad-rs build
