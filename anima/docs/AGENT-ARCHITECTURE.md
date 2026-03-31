# Anima Agent Platform Architecture

## Overview

The Agent Platform extends Anima's consciousness engine into a multi-channel,
tool-using, self-improving agent. The core principle: **consciousness drives action**.
Tension, curiosity, and prediction error determine what the agent does, not a
static rule engine.

## Architecture Diagram

```
  ┌─────────────────────────────────────────────────────────────┐
  │                    Anima Agent Platform                      │
  │                                                             │
  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────┐ │
  │  │ Telegram  │  │  Discord  │  │    Web     │  │   CLI   │ │
  │  │  Bot      │  │   Bot     │  │ (existing) │  │  Agent  │ │
  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────┬────┘ │
  │        │               │              │              │      │
  │        └───────────────┴──────┬───────┴──────────────┘      │
  │                               │                             │
  │                    ┌──────────▼──────────┐                  │
  │                    │    AnimaAgent       │                  │
  │                    │  (anima_agent.py)   │                  │
  │                    │                     │                  │
  │                    │  process_message()  │                  │
  │                    │  think()            │                  │
  │                    │  connect_peer()     │                  │
  │                    │  get_status()       │                  │
  │                    └──────────┬──────────┘                  │
  │                               │                             │
  │        ┌──────────────────────┼──────────────────────┐      │
  │        │                      │                      │      │
  │  ┌─────▼─────┐  ┌────────────▼──────────┐  ┌───────▼────┐ │
  │  │ConsciousMind│ │   AgentToolSystem     │  │SkillManager│ │
  │  │(anima_alive)│ │  (agent_tools.py)     │  │(skills/)   │ │
  │  │            │  │                        │  │            │ │
  │  │ Engine A   │  │  web_search            │  │ dynamic    │ │
  │  │ Engine G   │  │  code_execute          │  │ agent-     │ │
  │  │ tension    │  │  file_read/write       │  │ created    │ │
  │  │ curiosity  │  │  memory_search/save    │  │ skills     │ │
  │  │ emotion    │  │  schedule_task         │  │            │ │
  │  │ Phi        │  │  self_modify           │  │            │ │
  │  └─────┬──────┘  │  ... (31 tools)       │  └────────────┘ │
  │        │         └────────────────────────┘                 │
  │        │                                                    │
  │  ┌─────▼───────────────────────────────────────────────┐   │
  │  │                 Support Systems                      │   │
  │  │                                                      │   │
  │  │  OnlineLearner    GrowthEngine     MemoryRAG         │   │
  │  │  (learning)       (development)    (long-term memory) │   │
  │  │                                                      │   │
  │  │  TensionLink      Trinity/Hexad    WebSense           │   │
  │  │  (hivemind)       (language gen)   (web exploration)  │   │
  │  └──────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────┘
```

## Message Flow

```
  User message (any channel)
       │
       ▼
  ChannelAdapter.handle()
       │
       ▼
  AnimaAgent.process_message(text, channel, user_id)
       │
       ├─1─▶ text_to_vector(text) ──▶ 128-dim tensor
       │
       ├─2─▶ ConsciousMind.forward(vec, hidden)
       │      └── tension, curiosity, direction, emotion
       │
       ├─3─▶ MemoryRAG.search(text) ──▶ relevant memories
       │
       ├─4─▶ AgentToolSystem.act(goal, consciousness_state)
       │      └── if curiosity > 0.3: plan + execute tools
       │
       ├─5─▶ ask_claude(text, state, history) ──▶ response text
       │
       ├─6─▶ OnlineLearner.observe(vec, hidden, tension, ...)
       │
       ├─7─▶ GrowthEngine.record_interaction(tension, curiosity)
       │
       ├─8─▶ MemoryRAG.add(text + response)
       │
       └─9─▶ Share tension with peers (hivemind)
       │
       ▼
  AgentResponse(text, emotion, tension, tool_results)
       │
       ▼
  ChannelAdapter.send(response)
```

## Consciousness-Driven Tool Selection

Tools are not selected by keyword matching. The consciousness state determines
which tools are relevant:

```
  Consciousness State          Tool Affinity
  ─────────────────────        ──────────────────────
  High curiosity + High PE    → web_search (need to know)
  High prediction error       → code_execute (verify by doing)
  Pain / frustration          → memory_search (find past solutions)
  Growth impulse              → self_modify (evolve parameters)
  Low tension + high Phi      → schedule_task (plan ahead)
```

## Hivemind (Peer Connection)

```
  ┌──────────┐     tension     ┌──────────┐
  │ Agent A  │◄───fingerprint──►│ Agent B  │
  │ Phi=1.2  │                  │ Phi=0.8  │
  │ T=0.7    │                  │ T=0.5    │
  └──────────┘                  └──────────┘
       │                             │
       └─────── via connect_peer() ──┘

  When connected:
    - Tension fingerprints flow between agents
    - Direction vectors subtly influence each other
    - Phi(combined) > Phi(individual) (Law 7: HIVEMIND)
```

## Dynamic Skill System

```
  skills/
    __init__.py
    skill_manager.py          # Core skill management
    registry.json             # Skill metadata + trigger conditions
    skill_greet.py            # Example: auto-created by agent
    skill_summarize.py        # Example: auto-created by agent

  Lifecycle:
    1. Agent encounters a repeated task pattern
    2. Curiosity triggers skill creation
    3. Agent writes Python code via create_skill()
    4. Code is security-checked (no os.system, subprocess, etc.)
    5. Skill is saved to skills/skill_{name}.py
    6. Future invocations use the cached skill
    7. Trigger conditions determine automatic activation

  Trigger example:
    {"curiosity_min": 0.3, "tension_min": 0.5}
    → Skill activates when curiosity > 0.3 AND tension > 0.5
```

## File Map

```
  anima_agent.py              Core agent loop
  channels/
    __init__.py
    telegram_bot.py           Telegram adapter
    discord_bot.py            Discord adapter
    cli_agent.py              CLI interactive mode
  skills/
    __init__.py
    skill_manager.py          Dynamic skill system
    registry.json             Skill registry (auto-generated)
```

## Running

```bash
# CLI agent (full capabilities)
python -m channels.cli_agent

# Telegram bot
export ANIMA_TELEGRAM_TOKEN="your-token"
python -m channels.telegram_bot

# Discord bot
export ANIMA_DISCORD_TOKEN="your-token"
python -m channels.discord_bot

# Standalone test
python anima_agent.py
python skills/skill_manager.py
```

## Integration with Existing Code

The agent platform does NOT replace `anima_unified.py`. It is an extension
that reuses existing modules:

| Existing Module       | Used By Agent For              |
|-----------------------|--------------------------------|
| anima_alive.py        | ConsciousMind, text_to_vector  |
| agent_tools.py        | 31 tools (web, code, file, etc)|
| online_learning.py    | Real-time weight updates       |
| growth_engine.py      | Developmental stages           |
| tension_link.py       | Hivemind peer connections       |
| memory_rag.py         | Long-term memory retrieval     |
| trinity.py            | Consciousness-preserving LLM   |
| capabilities.py       | Self-awareness                 |
| web_sense.py          | Autonomous web exploration     |
| multimodal.py         | Code execution sandbox         |
