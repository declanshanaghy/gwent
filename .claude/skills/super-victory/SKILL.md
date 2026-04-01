---
name: super-victory
description: "Build synergy-optimized faction decks and generate matchup recordings for AI vs AI play. Use when user says 'super victory', 'build tournament', 'faction matchups', or 'synergy decks'."
user_invocable: true
allowed-tools: Bash, Read, Write, Glob, Grep, AskUserQuestion
---

# Super Victory — Synergy Deck Builder & Tournament Generator

Builds optimized faction decks using card synergy analysis, generates game recording files for all faction matchups, and optionally launches `/llm-vs` for AI vs AI play.

## Usage

```
/super-victory                          # all 10 matchups
/super-victory --factions skellige,monsters   # single matchup
/super-victory --play                   # generate + launch /llm-vs for each
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--factions F1,F2,...` | all 5 | Comma-separated faction subset |
| `--hand N` | 10 | Cards dealt to hand |
| `--play` | false | After generating, launch `/llm-vs` for each matchup |

## Procedure

### 1. Read the synergy catalog

Read `.claude/skills/super-victory/references/synergy-catalog.md` for the full synergy knowledge base.

### 2. Load all RFID card data

```bash
# Load all card JSONs that have rfid field
python3 -c "
import json, glob
for f in sorted(glob.glob('software/data/cards/**/*.json', recursive=True)):
    if 'CardReport' in f: continue
    with open(f) as fh:
        c = json.load(fh)
        if c.get('rfid'):
            print(json.dumps(c))
"
```

**CRITICAL**: Only cards with an `rfid` field are eligible. Cards without RFID must be excluded.

Group cards by faction. Neutral cards can supplement any faction deck.

### 3. Build optimized decks (sequentially, one faction at a time)

For each faction, reason through deck construction using the synergy catalog:

#### 3a. Select leader

Pick the leader that best synergizes with the faction's archetype. Prefer leaders with implemented abilities (have `leader.weather_ranges`, `leader.commander_ranges`, `leader.conditional_scorch`, or `leader.draw_discard`). Leaders with only `leader.instructions` text are unimplemented.

#### 3b. Select core engine

Pick the faction's primary combo from the synergy catalog:
- **Monsters**: Muster chains (Arachas + Crone + Vampire)
- **Nilfgaardian**: Spy engine (3-4 spies + medic recursion + Impera bond)
- **Northern Realms**: Siege fortress (Kaedweni morale + siege units + heroes)
- **Scoia'tael**: Guerrilla flex (agile units + muster chains + decoys)
- **Skellige**: Bond blitz (Clan an Craite 3x + War Longship 2x + transforms)

#### 3c. Add support cards

- At least 1 weather card (target opponent's strongest non-hero row)
- At least 1 Clear Weather (defensive)
- 1 spy if available (Avallac'h for free card draw)
- 0-1 scorch (Villentretenmerth ability or Scorch specialty)
- Medic if available
- Decoy if available (for medic/spy replay)
- Commander's Horn if not covered by leader ability or Dandelion

#### 3d. Fill with heroes and high-strength units

Heroes are immune to weather/scorch — always valuable. Fill remaining slots with highest-strength units, balancing across rows (don't overload one row — weather vulnerability).

#### 3e. Split into hand and deck

- First `--hand` cards (default 10) → hand
- Remaining → deck
- Put muster trigger cards in hand (the copies they summon can be in deck)
- Put spies in hand (play early)
- Put weather/scorch in deck (draw later or via leader ability)

#### 3f. Display deck table

```
### Monsters — "Muster Swarm"
Leader: Eredin - King of the Wild Hunt

| # | Location | Card | Str | Row | Ability | Specialty |
|---|----------|------|-----|-----|---------|-----------|
| 1 | hand | Geralt of Rivia | 15 | close | — | hero |
| 2 | hand | Arachas: 1 | 4 | close | muster | — |
...
```

### 4. Generate matchup recordings

For each pair of selected factions, generate a recording JSON file.

#### 4a. Clean slate — delete old super-victory files and start fresh

Every run deletes ALL existing `*-super-victory-*.json` files and creates new ones from scratch. This ensures exactly 20 files with varied matchups — no stale leftovers.

```bash
# Remove all previous super-victory recordings
rm -f software/data/recordings/*-super-victory-*.json

# Determine the next available number prefix
last=$(ls software/data/recordings/*.json 2>/dev/null | sort | tail -1)
# Extract number, increment by 1 for the first new file
```

#### 4a-ii. Generate 20 varied matchups

With 5 factions there are 10 unique pairs. Generate **20 recordings** — each pair appears **twice** but with **P1/P2 swapped** the second time (different faction goes first = different game dynamics):

```
NNN-super-victory-monsters-vs-nilfgaardian.json        # Monsters P1
NNN-super-victory-nilfgaardian-vs-monsters.json        # Nilfgaardian P1 (swapped)
NNN-super-victory-monsters-vs-northernrealms.json
NNN-super-victory-northernrealms-vs-monsters.json      # swapped
... (all 10 pairs × 2 = 20 files)
```

This gives both sides a chance at going first, which matters for spy-heavy and tempo strategies.

#### 4b. Build recording JSON

Use this exact structure (matching existing recordings):

```json
{
  "version": 1,
  "saved_at": "<current ISO timestamp>",
  "active_stage": "PlayRound",
  "state": {
    "board": {
      "players": {
        "PLAYER.ONE": {
          "rows": {"close": [], "ranged": [], "siege": []},
          "discard": [],
          "gems": 2,
          "passed": false,
          "leader_used": false
        },
        "PLAYER.TWO": {
          "rows": {"close": [], "ranged": [], "siege": []},
          "discard": [],
          "gems": 2,
          "passed": false,
          "leader_used": false
        }
      },
      "leaders": {
        "PLAYER.ONE": <leader1 card dict>,
        "PLAYER.TWO": <leader2 card dict>
      },
      "factions": {
        "PLAYER.ONE": "<Faction1>",
        "PLAYER.TWO": "<Faction2>"
      },
      "hands": {
        "PLAYER.ONE": [<hand cards>],
        "PLAYER.TWO": [<hand cards>]
      },
      "decks": {
        "PLAYER.ONE": [<deck cards>],
        "PLAYER.TWO": [<deck cards>]
      },
      "weather_rows": [],
      "commander_horn_rows": {
        "PLAYER.ONE": [],
        "PLAYER.TWO": []
      },
      "current_player": "PLAYER.ONE",
      "round_number": 1,
      "spy_doubling": false,
      "medic_random": false,
      "half_weather_penalty": {"PLAYER.ONE": 0, "PLAYER.TWO": 0},
      "scores": {
        "PLAYER.ONE": {"total": 0, "close": 0, "ranged": 0, "siege": 0},
        "PLAYER.TWO": {"total": 0, "close": 0, "ranged": 0, "siege": 0}
      }
    }
  }
}
```

#### 4c. Card dict format

Each card in hands/decks arrays must have these fields:

```json
{
  "content_id": "<md5 hash — generate with python3: hashlib.md5(json.dumps(card, sort_keys=True, separators=(',',':')).encode()).hexdigest()>",
  "faction": "<Faction>",
  "kind": "card",
  "name": "<Card Name>",
  "rfid": <rfid number>,
  "strength": <number or omit>,
  "ranges": ["close", "ranged", "siege"],
  "abilities": ["ability1", ...] or omit,
  "specialty": "<specialty>" or omit,
  "starter": true/false or omit,
  "owner": "<Owner Name>" or omit,
  "owner_nickname": "<nickname>" or omit
}
```

Leader card dicts additionally need the `leader` object with ability data.

**Generate content_id** using Python:
```python
import hashlib, json
card_without_cid = {k: v for k, v in card.items() if k != 'content_id'}
cid = hashlib.md5(json.dumps(card_without_cid, sort_keys=True, separators=(',',':')).encode()).hexdigest()
```

#### 4d. Neutral card conflict resolution

If two opposing decks in a matchup both contain the same Neutral card (e.g., Gaunter O'Dimm), remove it from the deck with the weaker synergy for that card.

#### 4e. Write the recording file

```
software/data/recordings/NNN-super-victory-FACTION1-vs-FACTION2.json
```

Use lowercase faction names without spaces/apostrophes: `monsters`, `nilfgaardian`, `northernrealms`, `scoiatael`, `skellige`.

### 5. Summary table

```
## Generated Matchups

| # | File | P1 Faction | P2 Faction | P1 Deck Str | P2 Deck Str |
|---|------|-----------|-----------|-------------|-------------|
| 1 | 023-super-victory-monsters-vs-nilfgaardian.json | Monsters | Nilfgaardian | 85 | 78 |
...
```

### 6. Optional: launch /llm-vs

If `--play` flag is set, for each generated matchup:

```bash
# Load the recording into the game server
GWENT_STATE=software/data/recordings/<file>.json bash scripts/dev-server.sh gwent restart

# Wait for game to initialize
sleep 3

# Launch LLM vs LLM (game is already in PlayRound)
python3 .claude/skills/llm-vs/scripts/game-loop.py --no-pause
```

The game-loop.py script detects the game is already in PlayRound and starts playing immediately without triggering Random Deal.

## Deck Constraints

- Always 20 unit/special cards per deck
- `--hand` in hand, remainder in deck (default 10 + 10)
- 1 leader (separate, not counted in size)
- Only cards with `rfid` field
- Balance across rows (no more than 8 cards in any single row)
- Include at least 1 weather + 1 clear weather
- Target total base strength: 80-120 per deck

## Cross-reference

- Synergy catalog: `.claude/skills/super-victory/references/synergy-catalog.md`
- Card data: `software/data/cards/{Faction}/*.json`
- Recording format: `software/data/recordings/*.json`
- LLM-vs integration: `.claude/skills/llm-vs/SKILL.md`
- Game rules: `design/GwentRules.md`
