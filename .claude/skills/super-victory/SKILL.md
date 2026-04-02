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

### 1. Run the deck builder script

```bash
# All 20 matchups (10 pairs x 2 swapped)
python3 .claude/skills/super-victory/scripts/build-decks.py

# Specific factions only
python3 .claude/skills/super-victory/scripts/build-decks.py --factions skellige,monsters

# Custom hand size
python3 .claude/skills/super-victory/scripts/build-decks.py --hand 10
```

The script:
1. Loads all cards with BOTH `rfid` AND `image` fields
2. Builds synergy-optimized 20-card decks per faction (max 2 spies each)
3. Deletes old `*-super-victory-*.json` recordings
4. Generates 20 new matchup recordings (10 pairs x 2 P1/P2 swapped)

### 2. Optional: launch /llm-vs

If `--play` flag is set, for each generated matchup:

```bash
# Load the recording into the game server
GWENT_STATE=software/data/recordings/<file>.json bash scripts/dev-server.sh gwent restart

# Wait for game to initialize
sleep 3

# Launch LLM vs LLM (game is already in PlayRound)
python3 .claude/skills/llm-vs/scripts/game-loop.py --no-pause
```

## Deck Constraints

- Always 20 unit/special cards per deck
- `--hand` in hand, remainder in deck (default 10 + 10)
- 1 leader (separate, not counted in size)
- **Only cards with BOTH `rfid` AND `image` fields** — cards without images cannot be displayed in the TUI card overlay
- **Maximum 2 spies per deck** (hand + deck combined) — more than 2 unbalances games
- Balance across rows (no more than 8 cards in any single row)
- Include at least 1 weather + 1 clear weather
- Target total base strength: 80-120 per deck

## Cross-reference

- Synergy catalog: `.claude/skills/super-victory/references/synergy-catalog.md`
- Card data: `software/data/cards/{Faction}/*.json`
- Recording format: `software/data/recordings/*.json`
- LLM-vs integration: `.claude/skills/llm-vs/SKILL.md`
- Game rules: `design/GwentRules.md`
