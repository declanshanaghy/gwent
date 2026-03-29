# CLAUDE.md

## Project Overview

Gwent Companion — a Raspberry Pi-based digital companion for the physical card game Gwent from The Witcher III. Players use RFID-tagged physical cards; the companion tracks scores, manages game state, and guides players through the game.

## Key References

- [Gwent Rules](design/GwentRules.md) — canonical game rules as implemented
- [Game Stages](design/GwentGameStages.md) — state machine and flow diagrams
- [PubSub Architecture](design/GwentPubSub.md) — messaging system design
- [Product Requirements](design/000-product-requirements.md) — PRD

## Project Structure

- `software/gwent/` — Python game server (`gwent` system service)
- `software/gwent-shared/` — shared utilities (TTS providers, no hardware deps)
- `software/gwent-tui/` — terminal dashboard (`gwent-tui`)
- `software/data/cards/` — card JSON definitions by faction
- `software/data/decks/` — saved player decks
- `design/` — architecture docs, ADRs, diagrams
- `scripts/` — dev tooling (dev-server.sh, install scripts)

## Development

- Python virtualenv: `/home/dshanaghy/gwent-venv/`
- Run locally: `bash scripts/dev-server.sh gwent start`
- Game state dump: `kill -USR1 $(pgrep -f gwent-venv/bin/gwent)`
- Game recordings: `software/gwent/gwent/game/recordings/`

## Important Conventions

- Always use SIGTERM for graceful shutdown (never SIGKILL/kill -9) — hardware cleanup required
- Card data lives in `software/data/cards/{Faction}/CardName.json`
- Starter cards have `"starter": true` and no `"owner"` field
- Leaders are stored separately from hand/deck in `board.leaders`
- No cards are re-dealt between rounds; players keep remaining hand cards
