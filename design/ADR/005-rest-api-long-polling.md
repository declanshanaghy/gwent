# ADR 005: HTTP Long-Polling with ETag for State Observation

## Status

Accepted

## Context

External clients — particularly the LLM game orchestrator (`game-loop.py`) and the TUI dashboard — need to observe game state changes efficiently. WebSockets add complexity and library dependencies. Frequent polling wastes CPU and network on the Pi. We needed a simple, HTTP-only mechanism that blocks until something actually changes.

## Decision

- The game server exposes two endpoints via `http_api.py`:
  - `GET /state` — returns current game state JSON immediately.
  - `GET /state/poll?timeout=30` — long-poll endpoint that blocks until state changes or timeout.
- Long-poll uses ETag-based change detection:
  - Server computes a hash of the serialized state and returns it as the `ETag` header.
  - Client sends `If-None-Match` with the previous ETag on subsequent requests.
  - If state hasn't changed, server blocks (polling internally) until it does or timeout expires.
  - Returns `304 Not Modified` if timeout expires with no change.
- The TUI's `SnapshotPoller` runs in a background thread, long-polling `/state/poll` and falling back to regular `/state` if long-poll is unavailable.
- Default timeout is 30 seconds; configurable via query parameter.

## Consequences

### Positive
- Simple HTTP clients (curl, requests) can observe state — no WebSocket library needed.
- Efficient: no traffic when state is unchanged.
- LLM orchestrator uses the same polling mechanism as the TUI.
- Stateless server — no connection tracking or session management.

### Negative
- One thread per blocking client on the server side.
- 30-second timeout means up to 30s delay for client disconnect detection.

### Risks
- Many simultaneous polling clients could exhaust server threads; acceptable for expected load (1-2 clients).

## Related
- `software/gwent/gwent/game/http_api.py`
- `software/gwent-tui/gwent_tui/snapshot.py`
- [ADR 010: LLM Orchestration](010-llm-orchestration-architecture.md)
