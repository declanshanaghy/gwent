# ADR 007: Rich/Textual Terminal Dashboard

## Status

Accepted

## Context

During development and demos, we need real-time visibility into game state without requiring a web browser or the physical hardware displays. The Pi runs headless most of the time, accessed via SSH. A terminal-based dashboard that updates live would serve both development debugging and spectator observation.

## Decision

- Build `gwent-tui` as a separate Python package using the Textual framework (built on Rich).
- The TUI subscribes to MQTT topics to receive game events in real-time via `mqtt_client.py`.
- Additionally, a `SnapshotPoller` background thread long-polls `GET /state/poll` for full state snapshots.
- Stage-specific widget layouts show board state, player hands, scores, round status, and event logs.
- The TUI is read-only — it observes but does not send game commands.
- Installed as a separate entry point (`gwent-tui`) independent of the game server.

## Consequences

### Positive
- Zero-dependency observation — works over SSH on any terminal.
- MQTT subscription provides instant event updates without polling overhead.
- Separate package means TUI changes don't affect the game server.
- Useful for debugging stage transitions and card ability resolution.

### Negative
- Terminal color support varies — Alacritty/tmux remap some colors (blue renders as purple).
- Textual framework is a significant dependency for a display-only tool.

### Risks
- MQTT and HTTP polling run in parallel; state could briefly be inconsistent between the two sources.

## Related
- [ADR 003: MQTT PubSub](003-mqtt-pubsub-backbone.md)
- [ADR 005: REST API Long-Polling](005-rest-api-long-polling.md)
- `software/gwent-tui/`
