# PRD-003: Game State Machine

## Overview

The game followed a stage-based state machine that governed the complete lifecycle from main menu through gameplay to winner display. The Controller routed incoming MQTT messages to the currently active stage, and each stage defined its own message handling and transition logic.

## Requirements

### Functional Requirements

- FR-1: The game progressed through ordered stages: MainMenu, RegisterLeaders, RegisterDecks, DealCards, PlayRound, RoundEnd, GameOver, DisplayWinner.
- FR-2: The Controller maintained a reference to the active stage and delegated all incoming MQTT messages to it.
- FR-3: Stage transitions were triggered by stage-internal logic (e.g., both players registered triggers transition to next stage).
- FR-4: RoundKeeper tracked gems (2 per player at game start; 1 lost per round loss, both lose 1 on draw).
- FR-5: PlayRound managed card plays, pass/play decisions, row placement, and turn alternation.
- FR-6: Scoring calculated total strength per row with modifiers: tight bond (multiply matching cards), morale boost (+1 to row-mates), commander's horn (double row), weather effects (reduce to 1).
- FR-7: When both players passed, the round ended and RoundEnd compared total scores to award/remove gems.
- FR-8: GameOver triggered when any player reached 0 gems, or after 3 rounds maximum.
- FR-9: No cards were re-dealt between rounds; players kept their remaining hand cards.
- FR-10: Faction passive abilities applied automatically (e.g., Monsters keep a random card on round loss, Nilfgaard wins on draw).

### Non-Functional Requirements

- NFR-1: Stage transitions were atomic; no messages were processed during a transition.
- NFR-2: The state machine was deterministic given the same sequence of inputs.

## Dependencies

- MQTT messaging (PRD-001) for input routing
- Card data system (PRD-007) for card attributes

## Related Documents

- [Game Stages](GwentGameStages.md)
- [Gwent Rules](GwentRules.md)
- [Card Mechanics](GwentCardMechanics.md)
