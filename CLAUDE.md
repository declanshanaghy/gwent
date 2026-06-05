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
- `software/gwent-tui/` — terminal dashboard (`gwent-tui`); runs as the 7" touchscreen kiosk (greetd→cage→kitty→gwent-tui)
- `software/data/cards/` — card JSON definitions by faction
- `software/data/decks/` — saved player decks
- `design/` — architecture docs, ADRs, diagrams
- `scripts/` — dev tooling (dev-server.sh, install scripts) + the standalone `gwent-camera` service (camera-server.py, camera.sh, nginx-camera.conf)

## Development

- Python virtualenv: `/home/dshanaghy/gwent-venv/`
- Run locally: `bash scripts/dev-server.sh gwent start`
- Game state dump: `mosquitto_sub -h localhost -u geralt -P gwent -t gwent/server/state -C 1` (retained snapshot — no HTTP API; MQTT is full command-and-control)
- Games always start from freshly generated decks — there are no game-state snapshots/replay. ("Recordings" now means camera VIDEO of the table, owned by gwent-camera — a separate concern.)
- The server always has a game in progress (auto-deals a random game at startup, after Game Over, and on in-game Quit) — there is no main menu

## Important Conventions

- Always use SIGTERM for graceful shutdown (never SIGKILL/kill -9) — hardware cleanup required
- Card data lives in `software/data/cards/{Faction}/CardName.json`
- Starter cards have `"starter": true` and no `"owner"` field
- Leaders are stored separately from hand/deck in `board.leaders`
- No cards are re-dealt between rounds; players keep remaining hand cards
