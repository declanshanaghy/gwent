---
description: Read a physical RFID card and display its data
user_invocable: true
---

Read a Gwent card from the RFID reader and display its contents.

## Prerequisites

**IMPORTANT**: The gwent game must be stopped first — the RFID reader cannot be shared.

1. Check if gwent is running:
   ```bash
   pgrep -f 'gwent-venv/bin/gwent$'
   ```
   If running, tell the user: "Stop gwent first with `/dev-server gwent stop`" and stop.

2. Run the read command:
   ```bash
   cd /home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent && /home/dshanaghy/gwent-venv/bin/python3 -m gwent.poc.util.read_write_cards read
   ```
   Use a 30-second timeout. The script waits for a card to be placed on the reader.

3. Display the card data in a formatted table:

| Field | Value |
|-------|-------|
| Name | card name |
| Faction | faction |
| RFID | rfid number |
| Strength | strength |
| Ranges | close, ranged, siege |
| Specialty | hero, leader, etc. |
| Abilities | spy, medic, etc. |
| Owner | owner name or "unowned" |
| Starter | yes/no |

Only show fields that have values.
