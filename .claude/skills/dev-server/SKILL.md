---
name: dev-server
description: Launch the gwent dev server in the background with file logging and auto-rotation
allowed-tools: Bash
---

Manage gwent dev services using the dev-server.sh script.

## Usage

```
bash scripts/dev-server.sh <service> <action>
```

- **service**: `gwent` | `glory-gate` | `all`
- **action**: `start` | `stop` | `restart` | `status`

## Mapping user arguments to commands

The user invokes this skill as `/dev-server <service> <action>`. Pass the arguments directly through.

If the user omits the action, default to `status`. If the user omits both, default to `all status`.

## Running

**IMPORTANT**: glory-gate (react-scripts) requires the parent shell to stay alive.
When the action involves **starting glory-gate** (`glory-gate start`, `glory-gate restart`, `all start`, `all restart`),
run the command with `run_in_background: true` on the Bash tool.

For **stop** and **status** actions, run normally (not in background).

After launching a background start, wait ~60 seconds, then run `bash scripts/dev-server.sh all status` to get the summary (the start command blocks and won't return).

## Summary output

After the status command completes, present a **single markdown table** combining all services. Parse the script's summary output and render it like this:

| Service | Status | PID | URLs | Log |
|---------|--------|-----|------|-----|
| gwent | running | 12345 | — | `tail -f /tmp/logs/gwent.log` |
| glory-gate | running | 67890 | http://localhost:8080 | `tail -f /tmp/logs/glory-gate.log` |
| | | | http://gwent:8080 | |
| | | | http://192.168.1.219:8080 | |

Rules:
- All URLs from the script output get their own row (continuation rows with empty Service/Status/PID/Log cells).
- The Log column should contain a copyable `tail -f <path>` command.
- If gwent is running, add a note below the table: "Save state: `kill -USR1 <pid>`".
