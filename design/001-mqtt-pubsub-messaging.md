# PRD-001: MQTT PubSub Messaging

## Overview

MQTT serves as the messaging backbone for the Gwent Companion, enabling decoupled communication between the game server, hardware drivers, TUI dashboard, and auxiliary tools. All messages are JSON-Schema-validated and published to well-defined topics.

## Requirements

### Functional Requirements

- FR-1: The system used an MQTT broker (Mosquitto) for all inter-component messaging.
- FR-2: Messages were JSON-Schema-validated against defined types: `ctrl`, `card_play`, `sfx`, `card`, `mfd`, `choice`.
- FR-3: Control messages (`gwent/ctrl`) carried game flow commands (start, pass, new_round, etc.).
- FR-4: Sound effect triggers were published to `gwent/sfx` with category and optional text.
- FR-5: OLED display content was published to `gwent/mfd/present` for the hardware display driver.
- FR-6: Card play events used per-player topics (`gwent/cards/play/+`) so each player's card reads were routed independently.
- FR-7: Card read events from RFID hardware were published to `gwent/card` with UID and card data.
- FR-8: Choice prompts (play/pass decisions) were published to `gwent/choice` for rotary encoder input.
- FR-9: Messages included metadata (timestamp, source) for tracing and replay.

### Non-Functional Requirements

- NFR-1: Message delivery was near-real-time (sub-100ms on local network).
- NFR-2: The broker ran locally on the Raspberry Pi to avoid network dependency.
- NFR-3: QoS level 0 was sufficient for local-only communication.

## Dependencies

- Mosquitto MQTT broker installed on the Raspberry Pi
- paho-mqtt Python client library

## Related Documents

- [PubSub Architecture](GwentPubSub.md)
- [Game Stages](GwentGameStages.md)
- [PRD-003: Game State Machine](003-game-state-machine.md)
