# PRD-008: Deck Management

## Overview

Decks were dynamically derived from card JSON ownership rather than maintained as separate deck files. A player's deck consisted of all faction cards where the owner matched the player's name or the card was marked as a starter. This eliminated synchronization issues between deck lists and card definitions.

## Requirements

### Functional Requirements

- FR-1: A player's deck was the set of faction cards where `owner` matched the player's slugified name OR `starter` was true.
- FR-2: No separate deck files were maintained; card JSON ownership was the single source of truth.
- FR-3: Player names were slugified (lowercased, spaces replaced with hyphens) for filesystem-safe matching.
- FR-4: Decks were shuffled at game start to randomize draw order.
- FR-5: Faction canonical names mapped display names to directory names (e.g., "Scoia'tael" to "Scoiatael").
- FR-6: Leaders were stored separately from the deck in `board.leaders` and were not part of the drawable card pool.
- FR-7: Deck counts were tracked and displayed in the TUI for both players.
- FR-8: Saved deck configurations in `software/data/decks/` provided pre-built deck definitions for testing.

### Non-Functional Requirements

- NFR-1: Deck derivation completed in under 100ms at startup.
- NFR-2: Adding a card to a player's deck required only setting the `owner` field in the card JSON.

## Dependencies

- Card data system (PRD-007) for card JSON files
- Faction directory structure

## Related Documents

- [PRD-007: Card Data System](007-card-data-system.md)
- [PRD-003: Game State Machine](003-game-state-machine.md)
- [Factions](GwentFactions.md)
