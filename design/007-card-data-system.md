# PRD-007: Card Data System

## Overview

Card data was stored as individual JSON files organized by faction. Each card file defined the card's gameplay attributes, RFID mapping, ownership, and visual assets. The system supported the full Witcher III Gwent card set across all factions.

## Requirements

### Functional Requirements

- FR-1: Each card was a JSON file with fields: name, faction, strength, ranges (close/ranged/siege booleans), abilities, rfid, starter, owner, image, pronoun.
- FR-2: Abilities included: muster, medic, spy, agile, tight_bond, morale, hero, scorch, decoy, commander's horn, and weather effects.
- FR-3: Cards were organized by faction directories: Monsters, NorthernRealms, Nilfgaardian, Scoiatael, Skellige, Neutral.
- FR-4: An RFID index mapped rfid values to card dictionaries for fast lookup on card scan.
- FR-5: Starter cards had `"starter": true` and no `"owner"` field; they were available to all players of that faction.
- FR-6: Owned cards had an `"owner"` field matching a player's slugified name.
- FR-7: Card variants (e.g., Arachas1, Arachas2, Arachas3) shared the same base name for tight bond and muster mechanics.
- FR-8: The `image` field referenced a relative path to the card's artwork file.
- FR-9: The `image_verified` field tracked whether the card image had been validated.

### Non-Functional Requirements

- NFR-1: Card JSON files were human-readable and editable for manual corrections.
- NFR-2: The card index was built once at startup and cached in memory.
- NFR-3: Missing or malformed card files were logged as warnings without crashing.

## Dependencies

- Filesystem access to `software/data/cards/{Faction}/` directories

## Related Documents

- [Card Mechanics](GwentCardMechanics.md)
- [Factions](GwentFactions.md)
- [PRD-008: Deck Management](008-deck-management.md)
