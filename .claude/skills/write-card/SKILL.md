---
description: Write card data from a JSON file to a physical RFID card
user_invocable: true
---

Write a Gwent card's data to a physical RFID tag. Takes a card JSON file path as argument.

## Usage

```
/write-card <path-to-card-json>
```

Example: `/write-card software/data/cards/NorthernRealms/FoltestKingofTemeria.json`

## Prerequisites

**IMPORTANT**: The gwent game must be stopped first — the RFID reader cannot be shared.

1. Check if gwent is running:
   ```bash
   pgrep -f 'gwent-venv/bin/gwent$'
   ```
   If running, tell the user: "Stop gwent first with `/dev-server gwent stop`" and stop.

2. Validate the argument:
   - If no file path provided, tell the user the usage and stop.
   - Resolve the path relative to the repo root (`/home/dshanaghy/src/github.com/declanshanaghy/gwent/`).
   - Read the JSON file and display the card data that will be written.
   - Ask the user to confirm before writing.

3. Run the write command:
   ```bash
   cd /home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent && /home/dshanaghy/gwent-venv/bin/python3 -m gwent.poc.util.read_write_cards write <absolute-path-to-json>
   ```
   Use a 30-second timeout. The script waits for an RFID tag to be placed on the reader, writes the card data, and updates the JSON file with the assigned RFID.

4. After writing, update timestamps and display the result:
   - Read the updated JSON file (the write script adds the RFID)
   - Set `"rfid_written_at"` to the current ISO timestamp in the JSON
   - Show the assigned RFID number
   - Confirm the JSON file was updated
   - Display the final JSON to verify

   The `rfid_written_at` timestamp is compared against `last_updated` by `/scan-card-photo` to detect cards that need re-writing (data changed since last chip write).
