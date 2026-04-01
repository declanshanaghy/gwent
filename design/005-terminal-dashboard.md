# PRD-005: Terminal Dashboard (gwent-tui)

## Overview

The gwent-tui package provided a Rich/Textual-based terminal dashboard that visualized the complete game state in real time. It subscribed to MQTT topics and rendered widgets for hands, board rows, scores, weather, and game stage information.

## Requirements

### Functional Requirements

- FR-1: The TUI subscribed to MQTT topics: ctrl, sfx, card reads, and card_play events.
- FR-2: Hand widgets displayed each player's cards with strength, range icons, and ability indicators.
- FR-3: The board widget showed 3 rows per player (close, ranged, siege) with placed cards and row totals.
- FR-4: Discard pile and deck count widgets tracked card attrition through the game.
- FR-5: A header widget showed player names, total scores, gem counts, and the current game stage.
- FR-6: Weather effects were displayed with visual indicators showing which rows were affected.
- FR-7: Stage-specific views adapted the layout for MainMenu, RegisterLeaders, PlayRound, and RoundEnd.
- FR-8: Card image overlays displayed card artwork when cards were played or scanned.
- FR-9: Emoji-based faction indicators identified each player's faction at a glance.
- FR-10: TTS announcement completion callbacks synchronized audio with visual updates.
- FR-11: Timer widgets showed elapsed time for rounds and total game duration.

### Non-Functional Requirements

- NFR-1: The TUI updated within 200ms of receiving MQTT state changes.
- NFR-2: Terminal color rendering accounted for Alacritty/tmux color mapping (blue renders as purple; dodger_blue2 used for true blue).
- NFR-3: The variation selector emoji character (U+FE0F) was stripped to avoid rendering issues.

## Dependencies

- Rich and Textual Python libraries
- MQTT broker (PRD-001)
- Game server REST API (PRD-002) for initial state fetch

## Related Documents

- [PRD-001: MQTT PubSub Messaging](001-mqtt-pubsub-messaging.md)
- [PRD-002: Game Server REST API](002-game-server-rest-api.md)
