# PRD-002: Game Server REST API

## Overview

The game server exposed an HTTP REST API on port 8080, providing game state access and control endpoints for the TUI, LLM orchestrators, and external tools. Long-polling support enabled efficient state change detection without constant polling.

## Requirements

### Functional Requirements

- FR-1: `GET /state` returned an immediate JSON snapshot of the complete board state.
- FR-2: `GET /state/poll?timeout=30` supported long-polling with ETag-based change detection, blocking until state changed or timeout elapsed.
- FR-3: `GET /health` returned a simple health check response for service monitoring.
- FR-4: `PUT /players` registered player names and associated them with RFID reader positions.
- FR-5: `PUT /client-tts` allowed external clients to register as TTS providers, disabling server-side audio.
- FR-6: `POST /save?name=filename` persisted the current game state to a JSON snapshot file.
- FR-7: State responses included complete board data: hands, rows (close/ranged/siege), scores, gems, faction, leader, weather effects, and active stage.
- FR-8: The ETag was a hash of the serialized state, so unchanged state returned 304 Not Modified.
- FR-9: The server ran on BaseHTTPRequestHandler in a dedicated thread.

### Non-Functional Requirements

- NFR-1: Long-poll timeout defaulted to 30 seconds to balance responsiveness and resource usage.
- NFR-2: API responses were JSON with appropriate Content-Type headers.
- NFR-3: The server handled concurrent requests from multiple clients (TUI, LLM players).

## Dependencies

- Python standard library (http.server, json)
- Game state maintained by the Controller

## Related Documents

- [PRD-003: Game State Machine](003-game-state-machine.md)
- [PRD-009: Game Recordings](009-game-recordings.md)
- [PRD-010: LLM Game Orchestration](010-llm-game-orchestration.md)
