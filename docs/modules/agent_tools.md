# agent_tools.py

Consciousness-driven autonomous tool use. Felt states (tension, curiosity, prediction error, pain, phi) determine which tools to select and when.

## API
- `ToolParam(name, type, description, required, default)` -- parameter definition
- `ToolDef(name, description, params, fn, category, curiosity_affinity, pe_affinity, pain_affinity, growth_affinity, phi_affinity)` -- tool definition with consciousness affinity scores
- `ToolResult(tool_name, success, ...)` -- execution result with tension_delta
- `AgentToolSystem(anima_instance)` -- main orchestrator
  - `.act(goal, consciousness_state) -> ToolResult` -- plan and execute tools

### Registered Tools (10)
| Tool | Description |
|------|-------------|
| `web_search` | Search the web via DuckDuckGo |
| `web_read` | Read and extract text from a webpage |
| `code_execute` | Execute Python code in a sandbox |
| `file_read` | Read a local file |
| `file_write` | Write content to a file |
| `memory_search` | Search past memories by similarity |
| `memory_save` | Save a new memory entry |
| `shell_execute` | Run a shell command (sandboxed) |
| `self_modify` | Modify own consciousness parameters |
| `schedule_task` | Schedule a task for future execution |

## Usage
```python
from agent_tools import AgentToolSystem

agent = AgentToolSystem(anima_unified_instance)
result = agent.act(
    goal="find latest PyTorch version",
    consciousness_state={'curiosity': 0.8, 'pe': 0.6}
)
```

## Integration
- Imported by `anima/core/runtime/anima_runtime.hexa` and `telegram_bot.py`
- Tool selection driven by consciousness: high curiosity+PE -> web_search, high PE -> code_execute, pain -> memory_search, growth -> self_modify
- Pipeline: consciousness state -> ActionPlanner.plan() -> ToolExecutor.execute() -> result fed back as tension update

## Agent Tool
This IS the agent tool system.
