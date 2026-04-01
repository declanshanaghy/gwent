# PRD-009: Game Recordings

## Overview

The recording system captured game state snapshots and message traces for debugging, replay, and testing. State snapshots preserved the full board at a point in time, while JSONL trace files recorded every MQTT message for faithful replay.

## Requirements

### Functional Requirements

- FR-1: JSON snapshots included: version, saved_at timestamp, active_stage name, and full state (board, hands, decks, leaders, scores, gems).
- FR-2: JSONL trace files recorded each MQTT message with its topic, payload, and timestamp.
- FR-3: Replay mode re-published trace messages with original inter-message timing, capped at 20 seconds maximum delay.
- FR-4: Game IDs were timestamp-based for chronological ordering and uniqueness.
- FR-5: The HTTP `POST /save?name=filename` endpoint created snapshots on demand.
- FR-6: State snapshots could be loaded at startup to resume or replay from a specific game state.
- FR-7: The recording format was backward-compatible; missing fields defaulted gracefully to avoid errors on older snapshots.
- FR-8: Recordings were stored in `software/data/recordings/` with descriptive filenames.
- FR-9: SIGUSR1 signal to the running server triggered a state snapshot for debugging.

### Non-Functional Requirements

- NFR-1: Snapshot serialization completed within 500ms to avoid blocking gameplay.
- NFR-2: Trace files were append-only for crash resilience.
- NFR-3: Recording files were human-readable JSON/JSONL for manual inspection.

## Dependencies

- Game server state (PRD-003)
- REST API (PRD-002) for save endpoint
- MQTT messaging (PRD-001) for trace capture

## Related Documents

- [PRD-002: Game Server REST API](002-game-server-rest-api.md)
- [PRD-003: Game State Machine](003-game-state-machine.md)
- [PRD-010: LLM Game Orchestration](010-llm-game-orchestration.md)
