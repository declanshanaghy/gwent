# ADR 009: Per-Card JSON Files with Ownership Model

## Status

Accepted

## Context

The game needs to know which physical cards exist, which faction they belong to, their abilities and stats, and which player owns them. We also need a way to distinguish shared starter cards from player-owned cards. The RFID chip on each physical card stores an identifier that must map to card data.

## Decision

- Each card is a JSON file at `software/data/cards/{Faction}/{CardName}.json`.
- Card JSON includes: `name`, `faction`, `kind`, `strength`, `ranges` (close/ranged/siege), `abilities`, `starter`, `owner`, `rfid`, `image`, `card_text`, `pronoun`.
- `"starter": true` marks cards available to both players (no `owner` field).
- `"owner": "PlayerName"` assigns a card to a specific player's collection.
- A player's deck is derived at runtime by filtering: all starter cards for the faction plus all cards owned by that player.
- The `rfid` field stores the RFID chip UID, written during the card chipping pipeline.
- `rfid_written_at` and `last_updated` track when the physical chip was programmed.
- Leaders are a subset (`kind` or separate handling) stored in `board.leaders`, not in the hand/deck.

## Consequences

### Positive
- No separate deck configuration files — decks are computed from card ownership.
- Adding a new card means creating one JSON file; the game discovers it automatically.
- RFID UID maps directly to a card JSON — scan card, look up file, get all metadata.
- Easy to reassign cards between players by changing the `owner` field.

### Negative
- Deck composition depends on file-system state — no version-controlled deck lists.
- Scanning the cards directory at startup adds a few hundred milliseconds.

### Risks
- Duplicate RFID UIDs across cards would cause lookup ambiguity; mitigated by unique chip programming.
- Card JSON schema changes require migration of all existing files.

## Related
- `software/data/cards/` (card JSON files)
- [ADR 012: RFID Card Capture Pipeline](012-rfid-card-capture-pipeline.md)
- [Gwent Rules](../GwentRules.md)
