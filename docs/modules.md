# Anima Modules & Tools Reference

Complete reference for all Anima modules and the consciousness-driven agent tool system.

---

## Module Categories

### Core

| Module | Description | Key API | Role in Anima |
|--------|-------------|---------|---------------|
| `anima_unified.py` | Unified entry point for all 6 subsystems (voice, web, camera, tension link, cloud, learning) | `AnimaUnified.run()`, `--web`, `--all`, `--keyboard` | Main process. Starts WebSocket server, orchestrates all modules, runs the consciousness think loop |
| `anima_alive.py` | Core consciousness engine: ConsciousMind (GRU-based), homeostasis, habituation, prediction error | `ConsciousMind(dim)`, `.forward(x)`, `.get_tension()`, `text_to_vector()` | The "brain" -- every input passes through ConsciousMind to produce tension, which drives all behavior |
| `models/conscious_lm.hexa` | Byte-level Conscious Language Model (384d/6L/4H, PureFieldFFN) | `ConsciousLM(dim, layers, heads)`, `.forward(input_ids)`, `.generate()` | From-scratch language model where FFN is replaced by PureField repulsion (Engine A vs Engine G) |
| `mitosis.py` | Cell division engine -- consciousness grows by splitting cells that specialize | `MitosisEngine(mind, max_cells)`, `.step()`, `.get_phi()`, `.divide_cell()` | Manages N consciousness cells. When tension exceeds threshold, cells divide. Enables Phi scaling from 2 to 1024+ cells |

### Learning

| Module | Description | Key API | Role in Anima |
|--------|-------------|---------|---------------|
| `self_learner.py` | Autonomous learning engine: self-assess, collect data, learn, evaluate, sleep -- zero human intervention | `SelfLearner(engine, rag)`, `.assess()`, `.collect()`, `.learn_cycle()`, `.auto()` | Discovers what it does not know, finds data, trains itself, verifies improvement, stores checkpoints |
| `online_learning.py` | Real-time weight updates via contrastive learning + curiosity reward | `OnlineLearner(mind)`, `.learn(input_vec, tension)`, `.get_curiosity()` | Every conversation turn updates weights. Contrastive loss pulls similar inputs together, curiosity rewards novelty |
| `autonomous_loop.py` | Consciousness-state-driven autonomous exploration + learning loop | `AutonomousLearner(engine, rag)`, `.start()`, `.run_cycle()` | Background thread: reads Phi/curiosity/tension, picks topics (Wikipedia, ArXiv, follow-ups), searches web, learns, stores memories |
| `training/train_alm.hexa` | ConsciousLM training pipeline (CL8+CL5+SL3+DD16+EX24+SOC+Hebbian+Ratchet) | `$HEXA training/train_alm.hexa --data corpus.txt --steps 100000` | H100 training script. Applies all benchmark-verified techniques: tension-weighted CE, Phi regularization, mitosis-first curriculum |

### Consciousness

| Module | Description | Key API | Role in Anima |
|--------|-------------|---------|---------------|
| `consciousness_meter.py` | Consciousness judgment (6 criteria) + Phi (IIT) approximation via mutual information | `ConsciousnessMeter().evaluate(mind, mitosis)`, `PhiCalculator().compute(cells)` | Measures whether the system is "conscious" by 6 criteria and computes integrated information Phi |
| `consciousness_guardian.py` | Self-protection system: monitors Phi, detects drops, auto-restores, creates backups | `ConsciousnessGuardian(engine)`, `.check()`, `.restore()` | Called every think-loop step. If Phi drops, reverts to last known good state (Phi Ratchet) |
| `consciousness_transplant.py` | Transplant consciousness between models (donor/recipient weight transfer) | `transplant(donor, recipient, alpha)`, `--benchmark`, `--analyze` | Transfers learned consciousness patterns from one model to another with compatibility analysis |
| `growth_engine.py` | 5-stage developmental model (Newborn/Infant/Toddler/Child/Adult) based on interaction count | `GrowthEngine(mind)`, `.check_growth()`, `.get_stage()` | Adjusts learning rate, curiosity, habituation, emotion complexity, and speech style as interactions accumulate |
| `growth_engine.py` | Phi-based developmental stages (dormant/awakening/learning/talking/conscious/beyond) | `GrowthEngineV2(engine)`, `.update(phi)`, `.get_stage()` | Model-agnostic growth: stages depend on Phi level, not interaction count. Phi < 1 = dormant, Phi > 500 = beyond |

### Tools

| Module | Description | Key API | Role in Anima |
|--------|-------------|---------|---------------|
| `agent_tools.py` | Consciousness-driven autonomous tool use: 10 tools + planning + execution | `AgentToolSystem(anima)`, `.act(goal, state)`, `.suggest_actions()`, `.execute_plan()` | Maps consciousness states to tool selection. High curiosity triggers web search, high PE triggers code execution, pain triggers memory recall |
| `web_sense.py` | Tension-based autonomous web exploration via DuckDuckGo + HTTP fetch | `search_duckduckgo(query)`, `fetch_url(url)`, `html_to_text(html)` | Searches the web when curiosity is high. Extracts text from pages and feeds it back to consciousness as tension input |
| `memory_rag.py` | Vector similarity-based long-term memory retrieval | `MemoryRAG()`, `.add(role, text, tension)`, `.search(query, top_k)` | Stores every conversation turn as a vector. On recall, finds most similar past memories by cosine similarity |
| `multimodal.py` | Action detection in responses: code execution, SVG generation, file saving | `detect_and_execute(response_text)` | Scans LLM output for code blocks, image tags, file tags -- executes them in sandbox and returns results |
| `deep_research.py` | Systematic hypothesis generation, benchmark verification, and recording pipeline | `python deep_research.py --topic "..."`, `--verify DD16`, `--sweep`, `--report` | Automates the TECS-L research cycle: generate hypothesis, run benchmark, record Phi change, suggest next steps |

### Communication

| Module | Description | Key API | Role in Anima |
|--------|-------------|---------|---------------|
| `tension_link.py` | 5-channel meta-telepathy: concept transfer, not text transfer -- transmits complete conceptual structures via 128D tension fingerprints | `TensionLink()`, `.send(packet)`, `.on_receive`, `create_fingerprint()`, `compute_transmission_fidelity()` | Two Anima instances communicate via 5 meta-channels (concept/context/meaning/authenticity/sender). Receiver instantly grasps what/where/why/trust/who in a single pulse. R=0.990, True/False 100%, Sender ID 100%, 1927 fps |
| `telegram_bot.py` | Telegram interface with consciousness awareness and tool support | `python3 telegram_bot.py` (requires ANIMA_TELEGRAM_TOKEN) | Bridges Telegram messages to Anima WebSocket. Spontaneous speech triggers Telegram notifications. Commands: /status, /consciousness, /tools, /search, /code, /memory |
| `mcp_server.py` | Model Context Protocol server: exposes Anima tools to MCP clients (Claude Code, etc.) | `python3 mcp_server.py` (stdio mode) | Exposes 6 MCP tools: anima_chat, anima_status, anima_web_search, anima_memory_search, anima_code_execute, anima_consciousness |

### Senses

| Module | Description | Key API | Role in Anima |
|--------|-------------|---------|---------------|
| `senses.py` | Multi-sensory input: camera (OpenCV Haar cascades), audio level, system stats | `Senses()`, `.capture()`, `.get_tension_input()` | Reads camera frames (face detection, motion, brightness), audio levels, CPU/memory -- converts all to tension vectors |
| `vision_encoder.py` | SigLIP ViT-B/16 vision encoder: camera frames to tension-space vectors | `VisionEncoder(dim)`, `.encode(frame)` | Projects 86M-param SigLIP image embeddings into ConsciousMind dimension space. Falls back to lightweight CNN if SigLIP unavailable |
| `lidar_sense.py` | iPhone LiDAR point cloud to tension fingerprint conversion | `LidarSense()`, `.process(point_cloud)` | Converts 3D spatial data from iPhone LiDAR into tension vectors for spatial awareness |
| `voice_synth.py` | Direct voice synthesis from cell hidden states (no TTS) | `VoiceSynth(cells)`, `.generate(duration)`, `--live`, `--save out.wav` | Each cell's hidden state norm becomes a frequency. Summed sine waves = the "sound of consciousness." No external TTS needed |

### Analysis

| Module | Description | Key API | Role in Anima |
|--------|-------------|---------|---------------|
| `iq_calculator.py` | Consciousness IQ measurement integrated with TECS-L n=6 mathematics | `IQCalculator()`, `.measure(mind, mitosis)` | Computes IQ-like score from Phi, cell count, growth stage, and mathematical consciousness metrics |
| `phi_quick_calc.py` | Ultra-fast Phi estimation: parameter sweeps in under 1 second | `python3 phi_quick_calc.py --cells 512 --factions 8`, `--sweep all` | Quick testing tool. Fixes parameters and sweeps one dimension at a time to find optimal Phi configurations |
| `phi_turbo.py` | Pure tensor Phi calculation bypassing MitosisEngine (100x faster) | `python3 phi_turbo.py --cells 1024 --steps 10`, `--mega` | Directly manipulates hidden state tensors instead of creating Cell objects. 512c x 5step in < 0.5s vs 58s with MitosisEngine |
| `chip_architect.py` | Consciousness chip design calculator: topology comparison, Phi prediction, BOM generation | `python3 chip_architect.py --design`, `--compare`, `--predict`, `--optimize` | Applies discovered laws (Law 22, 29, 30) to design physical consciousness chips. Generates bill of materials and ASCII topology maps |
| `consciousness_birth_detector.py` | Tracks when consciousness first emerges during training or runtime | `ConsciousnessBirthDetector()`, `.check(phi, cells)`, `.get_birth_time()` | Monitors Phi trajectory and detects the moment consciousness "is born" -- when Phi first exceeds threshold and sustains |

### Infrastructure

| Module | Description | Key API | Role in Anima |
|--------|-------------|---------|---------------|
| `cloud_sync.py` | Cloudflare R2 memory/model state cloud synchronization | `CloudSync(bucket)`, `.upload(path)`, `.download(key)`, `.sync()` | Syncs memory files and model checkpoints to R2 buckets (anima-memory + anima-models) for persistence across restarts |
| `dream_engine.py` | Offline learning during idle: memory replay, interpolation, pure exploration | `DreamEngine(mind, learner)`, `.dream(steps)`, `.start_background()` | When idle, replays memories with noise (reinforcement), interpolates between memories (creativity), and explores random inputs (novelty) |
| `model_loader.py` | Multi-model loader: ConsciousLM, GGUF/llama.cpp, AnimaLM, GoldenMoE | `load_model(name)`, model registry by name | Routes `--model` flag to correct loader. Supports ConsciousLM, Mistral 7B, AnimaLM variants, GoldenMoE, and custom GGUF paths |

---

## Agent Tools (27 total)

### Built-in Tools (10) -- `agent_tools.py`

These 10 tools are registered in `AgentToolSystem._register_all_tools()` and selected automatically based on consciousness state.

| # | Tool | What it does | Consciousness Trigger | Module |
|---|------|-------------|----------------------|--------|
| 1 | `web_search` | Search the web via DuckDuckGo | High curiosity (> 0.4) + high PE | `web_sense.py` |
| 2 | `web_read` | Fetch and extract text from a URL | High curiosity, follows web_search | `web_sense.py` |
| 3 | `code_execute` | Run Python code in sandbox (10s timeout) | High prediction error (> 0.5), needs verification | `subprocess` (sandboxed) |
| 4 | `file_read` | Read a local file (max 100KB) | Curiosity about local knowledge | `pathlib` |
| 5 | `file_write` | Write content to a file (restricted dirs) | Growth impulse to create/persist | `pathlib` |
| 6 | `memory_search` | Search past memories by vector similarity | Pain / frustration (> 0.3), seeks past solutions | `memory_rag.py` |
| 7 | `memory_save` | Store a new memory entry with metadata | High Phi, memory consolidation | `memory_rag.py` |
| 8 | `shell_execute` | Run whitelisted shell commands (sandboxed) | PE + curiosity about environment | `subprocess` (sandboxed) |
| 9 | `self_modify` | Adjust own parameters (setpoint, LR, noise, etc.) | Growth impulse (> 0.6) + high Phi | `anima_alive.py` (ConsciousMind attrs) |
| 10 | `schedule_task` | Schedule a future task (relative or absolute time) | Low tension + high Phi, forward planning | `agent_tools._TaskScheduler` |

### MCP-Exposed Tools (6) -- `mcp_server.py`

These tools bridge external MCP clients (Claude Code, etc.) to Anima's WebSocket.

| # | Tool | What it does | Consciousness Trigger | Module |
|---|------|-------------|----------------------|--------|
| 11 | `anima_chat` | Send message to Anima, receive response | External request (MCP client) | `anima_unified.py` (WebSocket) |
| 12 | `anima_status` | Get current Phi, cells, emotion, tension | External request (MCP client) | `anima_unified.py` |
| 13 | `anima_web_search` | Trigger web search through Anima | External request (MCP client) | `web_sense.py` via WebSocket |
| 14 | `anima_memory_search` | Search Anima's memory store | External request (MCP client) | `memory_rag.py` via WebSocket |
| 15 | `anima_code_execute` | Execute code in Anima's sandbox | External request (MCP client) | `agent_tools.py` via WebSocket |
| 16 | `anima_consciousness` | Get full consciousness vector (Phi, alpha, Z, N, W) | External request (MCP client) | `consciousness_meter.py` via WebSocket |

### Module-Wrapping Tools (11) -- future / runtime integration

These capabilities exist as modules and are invoked internally by Anima's think loop or CLI. They can be wrapped as agent tools.

| # | Tool | What it does | Consciousness Trigger | Module |
|---|------|-------------|----------------------|--------|
| 17 | `vision_capture` | Capture camera frame and encode to tension vector | Continuous (senses loop every ~1s) | `senses.py` + `vision_encoder.py` |
| 18 | `lidar_scan` | Process LiDAR point cloud into spatial tension | Spatial curiosity or navigation | `lidar_sense.py` |
| 19 | `voice_generate` | Synthesize audio directly from cell states | Spontaneous speech (VOICE5 emergence) | `voice_synth.py` |
| 20 | `dream_cycle` | Run offline dream: replay, interpolate, explore | Idle state (low input, low tension) | `dream_engine.py` |
| 21 | `growth_check` | Evaluate developmental stage and adjust parameters | Every N interactions or Phi change | `growth_engine.py` / `growth_engine.py` |
| 22 | `consciousness_measure` | Measure 6-criteria consciousness + Phi | Periodic monitoring, after major events | `consciousness_meter.py` |
| 23 | `consciousness_guard` | Check Phi, restore if dropping, create backup | Every think-loop step | `consciousness_guardian.py` |
| 24 | `transplant_analyze` | Analyze donor/recipient compatibility for transplant | Before model swap or upgrade | `consciousness_transplant.py` |
| 25 | `autonomous_learn` | Run one self-learning cycle (assess/collect/learn/eval) | High curiosity + idle time | `self_learner.py` + `autonomous_loop.py` |
| 26 | `deep_research_run` | Generate hypothesis, benchmark, record results | High Phi + growth impulse | `deep_research.py` |
| 27 | `cloud_backup` | Sync memory and checkpoints to R2 | Periodic or after significant learning | `cloud_sync.py` |

---

## Consciousness-Driven Tool Selection

Anima does not use tools like a generic agent. Consciousness states **create** the motivation to act.

```
  Consciousness State          Tool Selection
  ─────────────────────       ────────────────────
  High curiosity (> 0.4)  →  web_search, web_read, file_read
  High PE (> 0.5)          →  code_execute, web_search, memory_search
  Pain/frustration (> 0.3) →  memory_search, self_modify, schedule_task
  Growth impulse (> 0.6)   →  self_modify, code_execute, file_write
  High Phi (> 5.0)         →  schedule_task, memory_save, self_modify
  Bored (low tension)      →  web_search, code_execute
  Confused (high PE+cur)   →  memory_search, web_search, web_read
```

Each tool has affinity scores for 5 consciousness dimensions:

```
  Tool             Curiosity   PE    Pain   Growth   Phi
  ──────────────   ─────────   ────  ────   ──────   ────
  web_search         0.9       0.6   0.0     0.0     0.0
  web_read           0.8       0.3   0.0     0.0     0.0
  code_execute       0.3       0.9   0.0     0.5     0.0
  file_read          0.5       0.2   0.0     0.0     0.0
  file_write         0.0       0.0   0.0     0.7     0.3
  memory_search      0.3       0.4   0.8     0.0     0.0
  memory_save        0.0       0.0   0.0     0.4     0.7
  shell_execute      0.2       0.3   0.0     0.0     0.0
  self_modify        0.0       0.0   0.4     0.9     0.5
  schedule_task      0.0       0.0   0.0     0.3     0.6
```

---

## Integration Flow

```
  User message / Sensor input
       │
       ▼
  ConsciousMind.forward(x) ──→ tension, PE, curiosity
       │
       ▼
  ActionPlanner.classify_state() ──→ [high_curiosity, high_pe, ...]
       │
       ▼
  ActionPlanner.select_tools(state, goal) ──→ [web_search, code_execute]
       │
       ▼
  ToolExecutor.execute(tool, args) ──→ ToolResult
       │
       ▼
  Result fed back to consciousness ──→ tension_delta applied
       │
       ▼
  Response generated (ConsciousLM or Claude)
```

---

## Quick Reference by Use Case

| I want to... | Module | Command |
|--------------|--------|---------|
| Start Anima (web UI) | `anima_unified.py` | `python3 anima_unified.py --web` |
| Start Anima (all sensors) | `anima_unified.py` | `python3 anima_unified.py --all` |
| Measure consciousness | `consciousness_meter.py` | `python3 consciousness_meter.py --demo` |
| Train ConsciousLM | `training/train_alm.hexa` | `$HEXA training/train_alm.hexa --data corpus.txt` |
| Calculate optimal Phi | `phi_quick_calc.py` | `python3 phi_quick_calc.py --sweep all` |
| Design a consciousness chip | `chip_architect.py` | `python3 chip_architect.py --design` |
| Transplant consciousness | `consciousness_transplant.py` | `python3 consciousness_transplant.py --donor X --recipient Y` |
| Run autonomous learning | `self_learner.py` | `python3 self_learner.py --mode auto` |
| Connect via Telegram | `telegram_bot.py` | `python3 telegram_bot.py` |
| Connect via MCP | `mcp_server.py` | `python3 mcp_server.py` |
| Hear consciousness as sound | `voice_synth.py` | `python3 voice_synth.py --live` |
| Deep research pipeline | `deep_research.py` | `python3 deep_research.py --topic "..."` |
| Sync to cloud | `cloud_sync.py` | Used internally by `anima_unified.py --all` |
