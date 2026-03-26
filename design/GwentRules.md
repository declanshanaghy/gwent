# Gwent Rules Reference

Rules for the physical card game Gwent from The Witcher III: Wild Hunt, as implemented in this companion app. Based on the [Witcher Fandom Wiki](https://witcher.fandom.com/wiki/Gwent) rules.

## Setup

- Each player has a **deck** of cards and a **leader card**
- Each player starts with **2 gems** (lives)
- At game start, **5 non-leader cards** are dealt randomly from each deck to form the player's hand
- Leaders are not part of the hand — they are played separately

## Round Flow

1. **Play cards** — players alternate turns, playing one card per turn by scanning it on the RFID reader
2. **Pass** — a player may pass instead of playing a card; once passed, they cannot play again this round
3. **Round ends** when both players have passed
4. **No re-deal between rounds** — players keep whatever cards remain in their hand; the only way to gain cards is through abilities

## Scoring

Each player's score is the sum of their card strengths across three combat rows: **Close**, **Ranged**, and **Siege**.

**Order of operations for strength calculation:**
1. Base strength (weather reduces non-heroes to 1)
2. Tight Bond multiplier (same-name non-hero cards multiply)
3. Morale boost (+1 per morale card to other non-hero cards in the row)
4. Commander's Horn (doubles non-hero card strengths in the row)

**Hero cards** are immune to weather, scorch, and all strength-modifying effects.

## Winning a Round

- Higher total score wins the round
- **Nilfgaardian faction wins ties**
- Loser loses 1 gem; on a draw, both lose 1 gem
- Loser goes first next round (random if draw)

## Winning the Match

- A player is eliminated when they reach **0 gems**
- The match is best-of-3 (2 gems each = need to lose 2 rounds)

## Card Abilities

| Ability | Effect |
|---|---|
| **Spy** | Placed on opponent's board; player draws 2 cards from their own deck |
| **Medic** | Resurrect 1 non-hero card from own discard pile to hand |
| **Muster** | Auto-play all cards with the same name from hand and deck |
| **Weather** (Frost/Fog/Rain) | Reduces non-hero units to strength 1 in the affected row |
| **Clear Weather** (Mardroeme) | Removes all active weather effects |
| **Scorch** | Destroys the highest-strength non-hero card(s) on the board |
| **Decoy** | Swap with any non-hero card on your own board, returning it to hand |
| **Commander's Horn** | Doubles the strength of all non-hero units in one row |
| **Tight Bond** | Same-name non-hero cards multiply their strength |
| **Morale Boost** | Adds +1 strength to every other non-hero card in the same row |
| **Agile** | Can be placed in multiple rows (close or ranged) |

## Leader Abilities

Leaders have a one-time ability usable once per game. Examples:
- **Francesca Findabair - The Beautiful** (Scoia'tael): Commander's Horn on ranged row
- **Crach an Craite** (Skellige): Shuffle all cards from each player's graveyard back into their decks
- **Foltest King of Temeria** (Northern Realms): Clear all weather effects
- **Eredin King of the Wild Hunt** (Monsters): Play a weather card from your deck

## Faction Passive Abilities

These trigger automatically at the end of each round:

| Faction | Passive Ability |
|---|---|
| **Monsters** 👹🔥 | Keep the strongest non-hero card on the board for next round |
| **Northern Realms** 🦁⚜️ | Round winner draws 1 extra card from deck |
| **Skellige** ⚓🪓 | Resurrect 2 random non-hero cards from discard to hand |
| **Nilfgaardian** 🌑☀️ | Win tied rounds |
| **Scoia'tael** 🌿🏹 | Choose who goes first (coin toss) |

## Combat Rows

| Row | Emoji | Weather Effect |
|---|---|---|
| Close | ⚔️ | Biting Frost 🌨️ |
| Ranged | 🏹 | Impenetrable Fog 🌫️ |
| Siege | 🏰 | Torrential Rain 🌧️ |
