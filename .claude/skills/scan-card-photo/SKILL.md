---
name: scan-card-photo
description: Extract Gwent card data from photos and generate JSON files. Use when the user says "scan card", "photo of card", "card photo", "extract card", or provides card images to process.
user_invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

Extract Gwent card data from photos of physical cards, match against existing database, and generate missing JSON files.

## Usage

`/scan-card-photo <path> [--owner NAME --nickname NICK] [--force]`

- **Directory**: `/scan-card-photo /tmp/cards/` (all images in dir)
- **Single image**: `/scan-card-photo /tmp/cards/IMG_1234.jpg`
- **Glob**: `/scan-card-photo /tmp/cards/*.jpg`
- **With owner**: `/scan-card-photo /tmp/cards/ --owner "Declan Shanaghy" --nickname dek`
- **Re-process**: `/scan-card-photo /tmp/cards/ --force` (ignore sidecar files, re-scan all)
- No argument: ask user for path

The user may also specify ownership inline: "these are all dek's cards" — parse owner/nickname from the conversation.

Supports: `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`

## Critical Rules

- **Do NOT rely on filenames** for card identification. Filenames will be random timestamps (IMG_1234.jpg, 2026-03-28_14.30.22.heic). ALL data comes from the image.
- **Trust the faction from the image** — every card has a **vertical colored sash on the left side**. This is the primary faction indicator. Read the sash color, NOT borders (there are no borders). The faction crest at the bottom of the sash is a secondary confirmation.
  - **Northern Realms**: BLUE sash
  - **Scoia'tael**: GREEN sash
  - **Monsters**: RED sash
  - **Skellige**: PURPLE sash
  - **Nilfgaardian**: GRAY sash
- Cards like Villentretenmerth and Cirilla appear in multiple faction decks with different sash colors. The sash determines which deck this physical copy belongs to.
- **There is no Neutral faction deck.** The `Neutral` directory is a holding area for unassigned cards. When scanning a physical card, it ALWAYS has a faction sash — read it. Never create cards as Neutral from photo scans.
- **Do NOT guess** — if you can't read a field clearly from the image, use **AskUserQuestion** showing the source filename so the user can check.
- **Always show source filename** in questions and logs so the user can cross-reference which physical photo you're asking about.

## Procedure

### 1. Parse arguments

Extract from the user's message:
- **Path**: directory, file, or glob
- **Owner** (optional): full name for `"owner"` field
- **Nickname** (optional): short name for `"owner_nickname"` field

If owner/nickname provided, ALL cards in this batch get these fields.

### 2. Find images

```bash
find <path> -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.webp" \) ! -name "._*" | sort
```

Report count: "Found N card images to process."

### 3. Check sidecar files (skip already-processed)

For each image, check if a **sidecar file** exists: `{filename}.json` in the same directory.

Example: `IMG_1234.jpg` → `IMG_1234.jpg.json`

If the sidecar exists, the image was already processed. Read it and report:
- `"status"`: "created", "exists", "mismatch_fixed", "skipped"
- `"card_name"`: the card that was identified
- `"card_json_path"`: path to the generated/matched JSON file
- `"processed_at"`: when it was scanned

**Skip** images that have a sidecar with `"status"` != `"error"`. Report them as "already processed" in the summary.

To **re-process** an already-scanned image, the user can delete the sidecar file or pass `--force`.

### 4. Process each unprocessed image

Process images **one at a time, sequentially**. Do NOT use sub-agents — they OOM on the Pi.

For each image:

#### 4a. Read the image

Use the **Read** tool to view the image. Extract ALL fields from visual content:

| Field | How to identify |
|-------|----------------|
| **name** | Text at bottom of card |
| **faction** | Vertical colored sash on left side: BLUE = Northern Realms, GREEN = Scoia'tael, RED = Monsters, PURPLE = Skellige, GRAY = Nilfgaardian. Crest at bottom of sash confirms. |
| **strength** | Number in top-left medallion (absent for weather/special/leader) |
| **ranges** | Sword icon = close, bow = ranged, catapult = siege |
| **specialty** | Gold border = hero, weather icon = weather, skull = scorch, puppet = decoy, horn = commander, crown = leader, mushroom = mardroeme |
| **abilities** | Chains = bond, triple arrows = muster, star = morale, eye = spy, cross = medic, bear = berserker, small skull = scorch ability |

#### 4b. Search for existing match

Use Grep to search `software/data/cards/` for the card name.

#### 4c. Determine status

- **NEW** — no matching card in database
- **EXISTS_COMPLETE** — match found with RFID
- **EXISTS_NO_RFID** — match found without RFID
- **MISMATCH** — match found but fields differ
- **UNCLEAR** — could not read a field (use AskUserQuestion)

#### 4d. Write card JSON + sidecar immediately

After extracting and confirming data for each card, write the card JSON file and sidecar file **right away** (don't batch). This way, if the process is interrupted, already-processed cards have sidecars and will be skipped on retry.

For NEW cards, write the JSON per step 7 rules. For EXISTS/MISMATCH, handle per step 7 rules. Then write the sidecar per step 8 rules.

#### 4e. Report progress inline

After each card, print a one-line status: `[N/TOTAL] CardName (Faction) — STATUS`

After all images are processed, proceed to the summary table (step 5).

### 5. Build summary table

After processing ALL images, show results:

```
| # | Source File | Card Name | Faction | Str | Row | Abilities | Specialty | Action |
|---|------------|-----------|---------|-----|-----|-----------|-----------|--------|
| 1 | IMG_1234.jpg | Dwarven Skirmisher: 4 | Scoia'tael | 3 | close | muster | — | NEW |
| 2 | IMG_1235.jpg | Iorveth | Scoia'tael | 10 | ranged | — | hero | EXISTS (no RFID) |
| 3 | IMG_1236.jpg | Geralt of Rivia | Neutral | 15 | close | — | hero | EXISTS (complete) |
| 4 | IMG_1237.jpg | Elven Skirmisher | Scoia'tael | 2 | close | muster | — | MISMATCH (JSON=ranged) |
| 5 | IMG_1238.jpg | Unknown Card | ??? | ? | ? | ? | ? | ASK USER |
```

### 6. JSON file rules

Cards are written immediately during step 4d. The rules below govern how to write them.

Write to: `software/data/cards/{FactionDir}/{CardName}.json`

**Faction directory mapping:**
```
Monsters       → Monsters
Northern Realms → NorthernRealms
Nilfgaardian   → Nilfgaardian
Scoia'tael     → Scoiatael
Skellige       → Skellige
Neutral        → Neutral
```

**Filename**: Remove apostrophes, colons, commas. Apply `.title()` to capitalize the first letter of EVERY word (including "of", "the", "and", "in", "an"). Then remove all spaces. ALL words must be capitalized — no exceptions. Examples: `YenneferOfVengerberg.json`, `GeraltOfRivia.json`, `EredinKingOfTheWildHunt.json`, `DwarvenSkirmisher4.json`

**JSON structure:**
```json
{
    "kind": "card",
    "faction": "Scoia'tael",
    "name": "Dwarven Skirmisher: 4",
    "strength": 3,
    "ranges": ["close"],
    "abilities": ["muster"],
    "owner": "Declan Shanaghy",
    "owner_nickname": "dek",
    "last_updated": "2026-03-28T15:30:00"
}
```

**Field rules:**
- `kind`: always `"card"`
- `faction`: use the proper display name (e.g. `"Scoia'tael"` not `"Scoiatael"`)
- `strength`: omit for weather/special/leader
- `ranges`: omit for Clear Weather (no specific row). Weather cards get the row they affect
- `specialty`: only include if card is: hero, weather, scorch, decoy, commander, mardroeme, leader
- `abilities`: only include if card has abilities
- `leader`: object with `"instructions"` for leader cards
- `owner` / `owner_nickname`: include if provided in batch args, omit otherwise
- Do NOT include `rfid`, `starter`, `content_id` — those are set separately

**Timestamps:**
- `last_updated`: ISO timestamp — set on EVERY write (new card or mismatch update)
- `rfid_written_at`: ISO timestamp — set ONLY by `/write-card` when chip is programmed
- A card **needs (re)writing** if: `last_updated > rfid_written_at` or `rfid_written_at` is absent
- When updating a card due to mismatch, set `last_updated` but do NOT clear `rfid` or `rfid_written_at` — the old chip still works, it just has stale data

**When updating an existing card (mismatch fix):**
- Preserve all existing fields (`rfid`, `content_id`, `owner`, `starter`, etc.)
- Only update the mismatched fields + set `last_updated`
- Use `Edit` tool, not `Write`, to avoid clobbering other fields

### 7. Sidecar file rules

Sidecars are written immediately during step 4d alongside the card JSON. The rules below govern their format.

Write a sidecar JSON file next to the source image:

**Path**: same directory as image, named `{filename}.json`
- `IMG_1234.jpg` → `IMG_1234.jpg.json`

**Sidecar content:**
```json
{
    "status": "created",
    "card_name": "Dwarven Skirmisher: 4",
    "faction": "Scoia'tael",
    "card_json_path": "software/data/cards/Scoiatael/DwarvenSkirmisher4.json",
    "processed_at": "2026-03-28T16:00:00",
    "source_image": "IMG_1234.jpg"
}
```

**Status values:**
- `"created"` — new JSON file written
- `"exists"` — matched existing card (with or without RFID)
- `"mismatch_fixed"` — existing card updated to match photo
- `"skipped"` — user chose to skip
- `"error"` — could not read card from image (re-processable)

Sidecar files are gitignored (`.gitignore` has `software/data/images/**/.*.json`).

### 8. Final report

After writing, show:
- How many new cards created
- How many existing cards found (with/without RFID)
- How many mismatches found and resolved (JSON updated)
- How many chips need (re)writing: `last_updated > rfid_written_at` or no `rfid_written_at`
- How many unreadable/skipped
- File paths of all created or updated JSONs

**Stale chip summary** — list all cards that need chip writing/rewriting:
```
Cards needing RFID (re)write:
  software/data/cards/Scoiatael/DwarvenSkirmisher4.json — NEW (no RFID)
  software/data/cards/Scoiatael/ElvenSkirmisher1.json — STALE (data updated after last write)
```

## Cross-reference sources

For ambiguous readings, check:
- Existing cards: `software/data/cards/`
- Rowan-Paul database: `/tmp/GWENTcards/public/`
- asundr/gwent-classic cards.js (if cloned)
