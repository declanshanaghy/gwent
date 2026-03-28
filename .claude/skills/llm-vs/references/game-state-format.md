# Game State Format for LLMs

## What goes where

| Info | Location | When |
|------|----------|------|
| Rules, card mechanics, faction passives, strategy | System prompt | Once at game start |
| Player's faction, leader, full deck card list | System prompt (section 7) | Once at game start |
| Opponent's faction, leader | System prompt (section 7) | Once at game start |
| Current hand, board rows, scores, gems, weather | User message (conversation) | Every turn |
| Leader available targets (discard choices) | User message (conversation) | Every turn |

## Fetching state from the game server

```bash
curl -s http://localhost:8080/state
```

Returns JSON with structure:
```json
{
  "active_stage": "PlayRound",
  "state": {
    "board": {
      "current_player": "PLAYER.ONE",
      "round_number": 1,
      "players": {
        "PLAYER.ONE": { "gems": 2, "passed": false, "leader_used": false, "rows": {...}, "discard": [...] },
        "PLAYER.TWO": { ... }
      },
      "leaders": { "PLAYER.ONE": { card... }, "PLAYER.TWO": { card... } },
      "factions": { "PLAYER.ONE": "Nilfgaardian", "PLAYER.TWO": "Scoia'tael" },
      "hands": { "PLAYER.ONE": [ card... ], "PLAYER.TWO": [ card... ] },
      "decks": { "PLAYER.ONE": [ card... ], "PLAYER.TWO": [ card... ] },
      "weather_rows": ["close"],
      "commander_horn_rows": { "PLAYER.ONE": [], "PLAYER.TWO": [] },
      "scores": {
        "PLAYER.ONE": { "total": 15, "close": 5, "ranged": 10, "siege": 0 },
        "PLAYER.TWO": { "total": 22, "close": 12, "ranged": 5, "siege": 5 }
      },
      "spy_doubling": false,
      "medic_random": false
    }
  }
}
```

## Building the LLM state message

For the current player, build this JSON and send as the `user` message:

```json
{
  "round": <board.round_number>,
  "your_gems": <player.gems>,
  "opponent_gems": <opponent.gems>,
  "your_score": <scores[player].total>,
  "opponent_score": <scores[opponent].total>,
  "your_hand": [
    {"name": "Card Name", "strength": 5, "row": "close", "abilities": ["spy"], "specialty": "hero"}
  ],
  "your_board": {
    "close": [{"name": "...", "strength": 5}],
    "ranged": [],
    "siege": []
  },
  "opponent_board": { same format },
  "your_discard": [{"name": "...", "strength": 5}],
  "weather_active": ["close"],
  "your_leader": {
    "name": "Leader Name",
    "instructions": "ability description",
    "used": false
  },
  "your_deck_size": <len(decks[player])>,
  "opponent_hand_size": <len(hands[opponent])>,
  "opponent_passed": <opponent.passed>
}
```

## Card summary format

For each card in the hand, include:
- `name`: exact card name (string)
- `strength`: integer (0 for spells)
- `row`: first row from ranges (string)
- `rows`: array of all valid rows (only if card has 2+ ranges / is agile)
- `abilities`: array of ability strings (only if present)
- `specialty`: string (only if present: "hero", "weather", "scorch", "decoy", "mardroeme", "commander")

## Leader target enrichment

For leaders with choice-based abilities, add `available_targets` to the leader info so the LLM can make an informed pick:

**draw_opponent_discard**:
```json
"choose_from": "opponent_discard",
"available_targets": [{"name": "...", "strength": 5}, ...]
```

**draw_own_discard** (non-hero cards only):
```json
"choose_from": "your_discard",
"available_targets": [{"name": "...", "strength": 5}, ...]
```

**weather_ranges** (weather cards in deck matching allowed rows):
```json
"choose_from": "weather_in_deck",
"available_targets": [{"name": "Biting Frost: 1", "row": "close"}, ...]
```

**discard_and_draw**:
```json
"discard_count": 2, "draw_count": 1
```

## Player mapping

- `PLAYER.ONE` = P1 (always listed first in the game state)
- `PLAYER.TWO` = P2
- `current_player` tells whose turn it is
