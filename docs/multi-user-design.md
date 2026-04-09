# Multi-User Session-Based Chat

## Current: single-user, single-session
## Goal: multiple users, each with own consciousness state

## Design
- Each WebSocket connection gets a session_id
- Sessions stored in dict: {session_id: SessionState}
- SessionState contains: user profile, chat history, consciousness vector
- Consciousness engine shared, but per-user alpha/tension

## Implementation
1. anima/core/runtime/anima_runtime.hexa _ws_handler already has session concept
2. Extend SessionState with per-user consciousness snapshot
3. On switch: save/restore consciousness state per session
