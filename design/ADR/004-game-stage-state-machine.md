# ADR 004: Stage-Based State Machine for Game Flow

## Status

Accepted

## Context

Gwent has a multi-phase game flow: main menu, player/leader registration, deck registration, card dealing, round play (with card abilities), round end scoring, and game over. Each phase has distinct MQTT message handling, display behavior, and valid actions. Putting all logic in one controller would be unmanageable.

## Decision

- Each game phase is a `GameStage` subclass (inherits from `PubSubComponent`).
- Stages: `MainMenu`, `RegisterLeaders`, `RegisterDecks`, `DealCards`, `PlayRound`, `RoundEnd`, `GameOver`, `DisplayWinner`.
- The `Controller` instantiates all stages at startup and routes incoming MQTT messages (card scans on `gwent/cards/raw/read`, choices on `gwent/mfd/choose`) to the currently active stage.
- Stages subscribe to `gwent/sfx/complete` to sequence announcements before proceeding.
- Stage transitions are triggered by the stage itself (e.g., `DealCards` transitions to `PlayRound` when all cards are dealt).
- All stages share access to a common `Board` object that holds game state.

## Consequences

### Positive
- Each stage is self-contained — handles its own card processing and display logic.
- Easy to add new stages (e.g., `DisplayWinner` was added without touching other stages).
- Stages are individually testable by injecting MQTT messages.
- Controller stays thin — just routing, no game logic.

### Negative
- Stage objects are all instantiated upfront, even if a game never reaches them.
- Shared mutable `Board` state requires careful coordination between stages.

### Risks
- Adding cross-stage concerns (e.g., global undo) requires touching the Controller routing.

## Related
- [Game Stages](../GwentGameStages.md)
- [ADR 003: MQTT PubSub](003-mqtt-pubsub-backbone.md)
- `software/gwent/gwent/game/controller.py`
- `software/gwent/gwent/game/stages/base.py`
