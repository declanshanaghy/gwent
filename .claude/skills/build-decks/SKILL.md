---
name: build-decks
description: Build two opposing test decks as a game recording file for playtesting
user_invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion, Glob
---

Build two opposing faction decks and save as a game recording file for use with `/playback-trace`.

## Usage

`/build-decks <faction1> vs <faction2> [--size N] [--hand N]`

- **faction1/faction2**: `monsters` | `northern-realms` | `nilfgaardian` | `scoiatael` | `skellige`
- **--size**: total deck size (default: 15)
- **--hand**: starting hand size (default: 10, remainder goes to deck)

If args are missing, use AskUserQuestion to ask which factions.

## Card data

All cards are in: `software/data/cards/{FactionDir}/*.json`

Faction directory mapping:
```
Monsters → Monsters
Northern Realms → NorthernRealms
Nilfgaardian → Nilfgaardian
Scoia'tael → Scoiatael
Skellige → Skellige
```

## Procedure

### 1. List available cards

Run a Python script to list all non-leader cards per faction with: name, strength, row, abilities, specialty, owner/starter, RFID status.

**IMPORTANT**: Only include cards that have an RFID (physical card exists). Cards without RFID cannot be scanned during gameplay.

### 2. Pick leaders

For each faction, list all leader cards that have RFIDs. Use AskUserQuestion to let the user pick (or auto-select if only one has an RFID).

### 3. Build decks

Select cards prioritizing:
- **Synergy with the leader ability** (e.g., close combat units for a close horn leader)
- **Combo potential** (bond pairs, muster sets, spy + medic loops)
- **Row balance** — don't put everything on one row unless the leader demands it
- **Mix of abilities** — include at least 1-2 weather, a spy if available, a medic
- **Only cards with RFIDs**

Split into hand (first N cards) and deck (remainder).

### 4. Display deck tables

Show both decks in formatted tables. **Group cards by ownership** within each section (hand/deck), with owned cards first then starters. Use section headers like `HAND — Owned (nickname)` and `HAND — Starter`.

Columns:
```
#  Card                     Str  Row        Ability    RFID
```

Show the leader separately above each table with its RFID. Owner column is implicit from the group header — don't repeat it per row.

### 5. Save recording file

Ask the user for a filename (suggest next sequential number in `software/data/recordings/`).

Save as a game state JSON using this structure (model on existing recordings):

```python
{
    "version": 1,
    "saved_at": "<ISO timestamp>",
    "active_stage": "PlayRound",
    "state": {
        "leader1": <leader1_card_json>,
        "leader2": <leader2_card_json>,
        "player1_deck": <hand1 + deck1>,  # full card list
        "player2_deck": <hand2 + deck2>,
        "board": {
            "players": {
                "PLAYER.ONE": {"gems": 2, "passed": false, "leader_used": false, "rows": {"close":[],"ranged":[],"siege":[]}, "discard": []},
                "PLAYER.TWO": {"gems": 2, "passed": false, "leader_used": false, "rows": {"close":[],"ranged":[],"siege":[]}, "discard": []}
            },
            "leaders": {"PLAYER.ONE": <leader1>, "PLAYER.TWO": <leader2>},
            "factions": {"PLAYER.ONE": "<Faction1>", "PLAYER.TWO": "<Faction2>"},
            "hands": {"PLAYER.ONE": <hand1_cards>, "PLAYER.TWO": <hand2_cards>},
            "decks": {"PLAYER.ONE": <deck1_cards>, "PLAYER.TWO": <deck2_cards>},
            "weather_rows": [],
            "commander_horn_rows": {"PLAYER.ONE": [], "PLAYER.TWO": []},
            "current_player": "PLAYER.ONE",
            "round_number": 1,
            "scores": {"PLAYER.ONE": 0, "PLAYER.TWO": 0}
        }
    }
}
```

### 6. Confirm

Tell the user the file was saved and suggest: `Load with /playback-trace <filename>`
