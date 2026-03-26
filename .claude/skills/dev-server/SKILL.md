---
name: dev-server
description: Launch the gwent dev server in the background with file logging and auto-rotation
allowed-tools: Bash
---

Manage the gwent dev server using the dev-server.sh script.

## Usage

```
bash scripts/dev-server.sh gwent <action>
```

- **action**: `start` | `stop` | `restart` | `status`

## Mapping user arguments to commands

The user invokes this skill as `/dev-server <action>`. Always pass `gwent` as the service.

- `/dev-server start` → `bash scripts/dev-server.sh gwent start`
- `/dev-server stop` → `bash scripts/dev-server.sh gwent stop`
- `/dev-server restart` → `bash scripts/dev-server.sh gwent restart`
- `/dev-server` (no args) → `bash scripts/dev-server.sh gwent status`

## Running

Run the command normally (not in background). The script launches gwent as a background process and exits immediately.

## Summary output

After the command completes, present a **single markdown table**. Parse the script's summary output and render it like this:

| Service | Status | PID | Log |
|---------|--------|-----|-----|
| gwent | running | 12345 | `tail -f /tmp/logs/gwent.log` |

Rules:
- The Log column should contain a copyable `tail -f <path>` command.
- If gwent is running, add a note below the table: "Save state: `kill -USR1 <pid>`".
