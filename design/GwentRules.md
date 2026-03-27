# Gwent Rules Reference

Rules for the physical card game Gwent from The Witcher III: Wild Hunt, as implemented in this companion app. Based on the [Witcher Fandom Wiki](https://witcher.fandom.com/wiki/Gwent) rules.

## Setup

- Each player has a **deck** of cards and a **leader card**
- Each player starts with **2 gems** (lives)
- At game start, **5 non-leader cards** are dealt randomly from each deck to form the player's hand
- Leaders are not part of the hand — they are played separately
- Owned cards are dealt first; starters fill remaining slots
- If a deck has no leader, a random starter leader is assigned

## Round Flow

1. **Play cards** — players alternate turns, playing one card per turn by scanning it on the RFID reader
2. **Pass** — a player may pass instead of playing a card; once passed, they cannot play again this round
3. **Round ends** when both players have passed
4. **No re-deal between rounds** — players keep whatever cards remain in their hand; the only way to gain cards is through abilities

## Scoring

Each player's score is the sum of their card strengths across three combat rows: **Close**, **Ranged**, and **Siege**.

**Order of operations for strength calculation (per row):**

1. **Base strength** — weather reduces non-heroes to 1; heroes keep their full strength
2. **Tight Bond** — cards with the `bond` ability that share the same name multiply their strength by the count of same-name bond cards in the row
3. **Morale Boost** — each card with the `morale` ability adds +1 to every OTHER non-hero card in the row (morale cards boost each other but not themselves)
4. **Commander's Horn** — doubles all non-hero card strengths in the row (from horn flag OR a unit card with the `commander` ability)

**Hero cards** are immune to weather, scorch, and all strength-modifying effects.

## Winning a Round

- Higher total score wins the round
- **Nilfgaardian faction wins ties**
- Loser loses 1 gem; on a draw, both lose 1 gem
- Loser goes first next round (random if draw)

## Winning the Match

- A player is eliminated when they reach **0 gems**
- The match is best-of-3 (2 gems each = need to lose 2 rounds)
- Winner determined by gem count, not board score

## Card Types: Specialties vs Abilities

Cards have two different systems for special effects:

- **Specialty** = what the card IS (determines how it's played — unit, special item, weather, etc.)
- **Ability** = what extra effects a unit card HAS (applied after placement on the board)

A card can have one specialty and multiple abilities. See [Card Specialties & Abilities](GwentCardMechanics.md) for full details.

## Combat Rows

| Row | Emoji | Weather Effect |
|---|---|---|
| Close | ⚔️ | Biting Frost 🌨️ |
| Ranged | 🏹 | Impenetrable Fog 🌫️ |
| Siege | 🏰 | Torrential Rain 🌧️ |

## Sub-Pages

- [Card Specialties & Abilities](GwentCardMechanics.md) — detailed mechanics for every card type
- [Leaders](GwentLeaders.md) — all leader abilities and implementation status
- [Faction Passives](GwentFactions.md) — end-of-round faction abilities
