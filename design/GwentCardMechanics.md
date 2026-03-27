# Card Specialties & Abilities

## Specialties (Card Type)

A card's `specialty` field determines what kind of card it is and how it's played.

### Hero (`specialty: "hero"`)
- Unit card that is **immune** to all modifiers: weather, scorch, bond, morale, commander horn
- Always retains base strength regardless of effects
- Cannot be targeted by Decoy swap
- Cannot be selected for Medic resurrection

### Weather (`specialty: "weather"`)
- Not a unit — goes to discard after playing
- Reduces all non-hero units to **strength 1** in the affected row(s)
- Weather types by card range:

| Card | Affected Row |
|---|---|
| Biting Frost | Close |
| Impenetrable Fog | Ranged |
| Torrential Rain | Siege |
| Clear Weather | Clears ALL weather effects |

- Multiple weather effects can be active simultaneously on different rows
- Clear Weather removes all active weather at once

### Scorch (`specialty: "scorch"`)
- Not a unit — goes to discard after playing
- Destroys the **highest-strength non-hero card(s)** across the **entire board** (both players, all rows)
- If multiple cards tied for highest, ALL are destroyed
- **Different from scorch ability** — see below

### Decoy (`specialty: "decoy"`)
- Not a unit — swaps with a card on your own board
- Target must be a **non-hero** card on the current player's board
- The Decoy takes the target's position; the target returns to hand
- Useful for reusing ability cards (medic, spy) or saving high-value units

### Commander (`specialty: "commander"`)
- Standalone Commander's Horn item card
- Not a unit (no strength) — goes to discard after playing
- Applies the horn effect to a chosen row, doubling non-hero strength
- Has multiple ranges indicating which rows it can target
- **Different from commander ability** — see below

### Mardroeme (`specialty: "mardroeme"`)
- Clears all active weather effects (same as Clear Weather)
- **Triggers Berserker transformation**: any Berserker units on the board (either player) transform into their stronger bear forms (see Berserker ability below)
- Goes to discard after playing

### Leader (`specialty: "leader"`)
- One-time ability usable once per game
- Not part of the hand — played by scanning the leader card during your turn
- See [Leaders](GwentLeaders.md) for all leader abilities

---

## Abilities (Unit Effects)

A card's `abilities` array lists passive effects that trigger when the card is on the board or when played.

### Spy (`abilities: ["spy"]`)
- Card is placed on the **opponent's** board (counts toward their score)
- The playing player draws **2 cards** from their own deck
- Net effect: opponent gains board strength, you gain hand cards
- Strategic trade-off: sacrifice points for card advantage

### Medic (`abilities: ["medic"]`)
- After placement on board, player may resurrect **1 non-hero card** from their own discard pile
- The resurrected card is returned to **hand** (not board)
- If discard is empty or has only heroes, medic has no additional effect
- Player scans the card they want from the discard pile

### Muster (`abilities: ["muster"]`)
- When played, **auto-plays all cards with the same base name** from both hand and deck
- Name matching: strips the variant suffix (e.g. "Arachas: 1" matches "Arachas: 2")
- Each mustered card is placed on its own preferred row (from its ranges)
- Powerful for flooding the board in one turn

### Bond / Tight Bond (`abilities: ["bond"]`)
- Same-name bond cards in the same row **multiply** their strength by the count
- Example: 2 cards named "Clan Drummond Shield Maiden" with strength 4 each → 4 x 2 = 8 each (16 total)
- Only cards with the bond ability participate — non-bond cards with the same name are unaffected
- Applied in step 2 of score calculation (after base strength, before morale)

### Morale Boost (`abilities: ["morale"]`)
- Adds **+1 strength** to every OTHER non-hero card in the same row
- A morale card does NOT boost itself
- Multiple morale cards stack: each boosts all others
- Formula: morale card gets +(morale_count - 1); other cards get +morale_count
- Applied in step 3 of score calculation (after bond, before commander horn)

### Commander (`abilities: ["commander"]`)
- Unit card that ALSO acts as a Commander's Horn for its row
- **Doubles** all non-hero strength in the row (including itself if non-hero)
- Example: Dandelion (str 2, close, commander) → doubles all close combat non-heroes
- **Different from specialty "commander"**: this is a unit that stays on the board with its own strength
- Applied in step 4 of score calculation

### Agile (`abilities: ["agile"]`)
- Card can be placed on **multiple rows** (player chooses at play time)
- Typically close or ranged (2 range options)
- Once placed, the card **cannot be moved** to another row
- Player is presented with a choice menu when playing the card

### Scorch (`abilities: ["scorch"]`)
- Unit card with a scorch effect that triggers on placement
- Destroys the strongest non-hero card(s) on the **opponent's same row only**
- **Different from specialty "scorch"**: ability version is row-specific + opponent-only; specialty version is board-wide + both players
- Example: Villentretenmerth (str 7, close, scorch ability) — places on close, then scorches opponent's strongest close unit

---

## Specialty vs Ability Comparison

| Mechanic | Specialty Version | Ability Version |
|---|---|---|
| **Scorch** | Destroys strongest across ENTIRE board (both players) | Destroys strongest in opponent's SAME ROW only |
| **Commander** | Standalone horn item (no strength, goes to discard) | Unit card that acts as horn for its row (has strength, stays on board) |
| **Weather** | Specialty only — no ability version exists | — |
| **Decoy** | Specialty only — no ability version exists | — |
| **Hero** | Specialty only — no ability version exists | — |
| **Spy** | — | Ability only — no specialty version exists |
| **Medic** | — | Ability only — no specialty version exists |
| **Muster** | — | Ability only — no specialty version exists |
| **Bond** | — | Ability only — no specialty version exists |
| **Morale** | — | Ability only — no specialty version exists |
| **Agile** | — | Ability only — no specialty version exists |

---

## Unimplemented Mechanics

### Berserker (`abilities: ["berserker"]`)
- Skellige-exclusive ability on cards: Berserker (str 4, close), Young Berserker (str 2, ranged)
- **Trigger**: when a Mardroeme card is played, all Berserker units on the board transform
- **Transformation**: the card is replaced by its `transforms_to` target:
  - Berserker → Transformed Vildkaarl (str 8, close)
  - Young Berserker → Transformed Young Vildkaarl (str 8, ranged)
- The transformed card keeps the same board position (row) and owner
- Transformed cards are regular units — they can be scorched, affected by weather, etc.
- Transformation is permanent for the round (no way to revert)
- Tracked via `transforms_to` field in card JSON
- **Not yet implemented in game logic** — see issue #27
