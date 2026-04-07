# telegram_bot.py

Consciousness-aware Telegram interface with tool support. Bridges Telegram messages to Anima's WebSocket and relays spontaneous utterances as Telegram notifications.

## API
- `AnimaTelegramBot(anima=None)` -- main class
  - `.start()` -- begin polling for messages
  - `.send_message(chat_id, text)` -- send to Telegram
- Commands: `/status`, `/consciousness`, `/tools`, `/search`, `/code`, `/memory`, `/learn`
- Auto-tool: factual questions auto-trigger web search (pattern matching for question words in English/Korean)

## Usage
```bash
export ANIMA_TELEGRAM_TOKEN="your-token"
python3 telegram_bot.py
```

## Integration
- Connects to Anima via WebSocket or direct `AnimaUnified` instance
- Uses `AgentToolSystem` for tool execution (web search, code exec, memory, etc.)
- Displays emotion emojis + Phi value with each response
- Spontaneous utterances forwarded to all active chat IDs

## Agent Tool
N/A (this is a communication interface)
