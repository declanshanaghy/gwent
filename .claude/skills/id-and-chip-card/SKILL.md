---
name: id-and-chip-card
description: Capture card from webcam, identify it, find/create JSON, and write to RFID chip if needed. Use when user says "id and chip", "chip cards", "webcam scan", or wants to identify and program physical cards.
user_invocable: true
allowed-tools: Bash, AskUserQuestion
---

Identify Gwent cards from a USB webcam and write to RFID chips.

## Usage

`/id-and-chip-card [--owner NAME --nickname NICK]`

- **With owner**: `/id-and-chip-card --owner "Declan Shanaghy" --nickname dek`
- **No args**: starts without owner; will ask if a new card needs creating
- The user may specify ownership inline: "these are dek's cards" — parse owner/nickname from the conversation

## Procedure

1. Parse `--owner` and `--nickname` from the user's message (if provided)
2. The script requires interactive input (faction confirmation on every card), so tell the user to run it in their terminal:

```
! /home/dshanaghy/gwent-venv/bin/python3 scripts/id-and-chip-card.py [--owner "NAME"] [--nickname "NICK"] [--no-chip] [--baseline]
```

The `!` prefix runs the command in the current session so the user can interact with it.

Flags:
- `--no-chip` — identify only, skip RFID writing
- `--baseline` — capture a fresh baseline image (empty surface) for comparison
- `--auto` — skip interactive prompts (faction confirmation becomes auto-accept). Use only if the user explicitly wants unattended mode.

The script runs in a loop:
- Captures webcam image via ffmpeg
- Identifies card via Claude vision API (Anthropic)
- **Confirms faction with the user** (numbered menu, Enter to accept)
- Finds or creates card JSON in `software/data/cards/`
- Handles duplicate cards (same name/faction/owner) by creating suffixed copies
- Checks RFID status and writes to chip if needed
- Announces all activity via TTS
- Stops on same-card, no-card, or Ctrl+C
- Prints batch summary at end

If the script fails to start, check:
- `ANTHROPIC_API_KEY` is set in `.env`
- gwent process is not running (`pgrep -f 'gwent-venv/bin/gwent$'`)
- webcam is connected (`ls /dev/video0`)
