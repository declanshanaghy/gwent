---
name: id-and-chip-card
description: Capture card from webcam, identify it, find/create JSON, and write to RFID chip if needed. Use when user says "id and chip", "chip cards", "webcam scan", or wants to identify and program physical cards.
user_invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill
---

Capture Gwent cards from a USB webcam, identify them visually, find or create their JSON files, and write to RFID chips if needed. Runs as a batch loop — place cards under the webcam one at a time.

## Usage

`/id-and-chip-card [--owner NAME --nickname NICK]`

- **With owner**: `/id-and-chip-card --owner "Declan Shanaghy" --nickname dek`
- **No args**: starts without owner; will ask if a new card needs creating
- The user may specify ownership inline: "these are dek's cards" — parse owner/nickname from the conversation

Owner/nickname are **session-sticky** — they apply to all cards in this batch until changed. The user can change mid-session by saying e.g. "now these are Dylan's cards".

## Critical Rules

- **Trust the faction from the image** — every card has a **vertical colored sash on the left side**. This is the primary faction indicator.
  - **Northern Realms**: BLUE sash
  - **Scoia'tael**: GREEN sash
  - **Monsters**: RED sash
  - **Skellige**: PURPLE sash
  - **Nilfgaardian**: GRAY sash
- Cards like Villentretenmerth and Cirilla appear in multiple faction decks with different sash colors. The sash determines which deck this physical copy belongs to.
- **There is no Neutral faction deck.** The `Neutral` directory is a holding area for unassigned cards. When scanning a physical card, it ALWAYS has a faction sash — read it. Never create cards as Neutral from photo scans.
- **Do NOT guess** — if you can't read a field clearly from the image, use **AskUserQuestion** showing what you see so the user can clarify.
- **Process sequentially** — do NOT use sub-agents (they OOM on the Pi).

## Batch Loop Procedure

### 0. Parse arguments

Extract from the user's message:
- **Owner** (optional): full name for `"owner"` field
- **Nickname** (optional): short name for `"owner_nickname"` field

Keep these in session for all cards in the batch.

### 1. Capture webcam image

```bash
ffmpeg -y -f v4l2 -input_format mjpeg -video_size 1280x720 -i /dev/video0 -frames:v 1 -update 1 tmp/webcam/capture.jpg 2>&1
```

### 2. Identify card from image

Use the **Read** tool to view `tmp/webcam/capture.jpg`. Extract ALL fields from visual content:

| Field | How to identify |
|-------|----------------|
| **name** | Text at bottom of card |
| **faction** | Vertical colored sash on left side: BLUE = Northern Realms, GREEN = Scoia'tael, RED = Monsters, PURPLE = Skellige, GRAY = Nilfgaardian. Crest at bottom of sash confirms. |
| **strength** | Number in top-left medallion (absent for weather/special/leader) |
| **ranges** | Sword icon = close, bow = ranged, catapult = siege |
| **specialty** | Gold border = hero, weather icon = weather, skull = scorch, puppet = decoy, horn = commander, crown = leader, mushroom = mardroeme |
| **abilities** | Ability icons are large, circled with obvious borders — do NOT confuse with small sash decorations/crests. Chains = bond, triple arrows = muster, star = morale, eye = spy, cross = medic, bear = berserker, small skull = scorch ability. If no large circled icon is present, the card has no abilities. |

**Stop conditions** — check BEFORE proceeding:
- **No card detected**: if the image shows no card (blank surface, hand, etc.), stop the batch: "No card detected, stopping batch."
- **Same card as previous**: read `tmp/webcam/capture.json` (if it exists) and compare the `name` and `faction` fields to the current card. If both match, stop the batch: "Same card detected (`{name}`), stopping batch."

If ambiguous, use `AskUserQuestion` to clarify.

**After identification**, write the extracted data to `tmp/webcam/capture.json` so it can be compared on the next iteration:
```json
{
    "name": "Card Name",
    "faction": "Faction",
    "strength": 5,
    "ranges": ["close"],
    "specialty": "hero",
    "abilities": ["spy"],
    "captured_at": "2026-03-28T17:00:00"
}
```
Only include fields that were identified (omit nulls). This file is overwritten each iteration.

### 3. Find or create card JSON

Search `software/data/cards/{FactionDir}/` for the card name using Grep/Glob.

**Faction directory mapping:**
```
Monsters       → Monsters
Northern Realms → NorthernRealms
Nilfgaardian   → Nilfgaardian
Scoia'tael     → Scoiatael
Skellige       → Skellige
```

**If JSON exists:** Read it, proceed to Step 4.

**If JSON does NOT exist:**
1. Present the extracted attributes to the user via `AskUserQuestion` for confirmation
2. On confirmation, create the card JSON at `software/data/cards/{FactionDir}/{CardName}.json`
   - **Filename**: Remove spaces, apostrophes, colons, commas from name. TitleCase. Example: `DwarvenSkirmisher4.json`
   - Include: `kind` (always `"card"`), `faction` (proper display name e.g. `"Scoia'tael"`), `name`, `strength`, `ranges`, `abilities`, `specialty` — as identified from the image
   - Omit `strength` for weather/special/leader cards
   - Omit `specialty` unless card is: hero, weather, scorch, decoy, commander, mardroeme, leader
   - Omit `abilities` unless card has abilities
   - Include `owner`/`owner_nickname` from session args (if set). If not set and creating a new card, ask the user.
   - Set `last_updated` to current ISO timestamp
   - Do NOT include `rfid`, `rfid_written_at`, `content_id`, or `starter`
3. Proceed to Step 4

### 4. Determine if chipping is needed

Read the card JSON and check:

- **Needs chipping** if: `rfid` field is absent, OR `last_updated > rfid_written_at`
- **Already current** if: `rfid` is present AND `rfid_written_at >= last_updated`

If already current: report "Card `{name}` is already chipped and current -- skipping." and go to Step 6.

### 5. Write to RFID

Invoke the write-card skill:

```
/write-card <path-to-card-json>
```

This handles: gwent process check, user confirmation, hardware write, updating `rfid` and `rfid_written_at` fields.

### 6. Record result and loop

Record the card's result for the summary table, then go back to Step 1 to capture the next card.

### 7. Batch summary

When the loop ends (no card or same card detected), print a summary table:

```
| # | Card Name | Faction | Status |
|---|-----------|---------|--------|
| 1 | Dwarven Skirmisher: 4 | Scoia'tael | CREATED + CHIPPED |
| 2 | Iorveth | Scoia'tael | EXISTS — CHIPPED |
| 3 | Geralt of Rivia | Northern Realms | EXISTS — already current |
```

Status values:
- `CREATED + CHIPPED` — new JSON created and RFID written
- `EXISTS — CHIPPED` — existing JSON, RFID written/rewritten
- `EXISTS — already current` — no action needed
- `CREATED — chip skipped` — JSON created, user declined RFID write
- `ERROR` — could not identify or process

## Cross-reference sources

For ambiguous readings, check:
- Existing cards: `software/data/cards/`
- Rowan-Paul database: `/tmp/GWENTcards/public/`
- asundr/gwent-classic cards.js (if cloned)
