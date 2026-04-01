# ADR 003: MQTT as Central Messaging Backbone

## Status

Accepted

## Context

The Gwent Companion has multiple independent subsystems — game server, RFID hardware, LED matrices, SFX engine, TUI dashboard, and external LLM orchestrators — that need to communicate without tight coupling. A direct function-call architecture would create circular dependencies and prevent components from being developed or tested independently.

## Decision

- Use an MQTT broker (Mosquitto) as the central message bus via `paho.mqtt.client`.
- Define a topic hierarchy under `gwent/` with structured subtopics:
  - `gwent/ctrl` — game control commands (start, reset, stage transitions)
  - `gwent/cards/raw/read` — raw RFID card scan events from hardware
  - `gwent/cards/raw/write` — RFID write commands
  - `gwent/cards/play/+` — card play events (per-player wildcard)
  - `gwent/mfd/present` — display content pushed to OLED
  - `gwent/mfd/choose` — user selection from rotary encoder menus
  - `gwent/sfx` — sound effect triggers; `gwent/sfx/complete` — playback done
- All messages are JSON with a `kind` field for type discrimination, validated by `gwent.messaging` classes.
- Components extend `PubSubComponent` base class which wraps subscribe/unsubscribe/publish with QoS 1.
- The `make_channel()` helper constructs topic paths from segments.

## Consequences

### Positive
- Any component can subscribe independently — TUI observes without affecting game.
- LLM orchestrators publish card plays on the same topics as physical RFID scans.
- Adding new subscribers (web UI, logging) requires zero server changes.
- Integration tests can inject messages directly onto the bus.

### Negative
- Requires a running Mosquitto broker on the Pi (additional service dependency).
- JSON parsing overhead on every message (acceptable at game-event rates).

### Risks
- Broker crash halts all communication; mitigated by systemd restart policy.
- Topic naming changes require coordinated updates across packages.

## Related
- [PubSub Architecture](../GwentPubSub.md)
- [ADR 004: Game Stage State Machine](004-game-stage-state-machine.md)
- [ADR 010: LLM Orchestration](010-llm-orchestration-architecture.md)
