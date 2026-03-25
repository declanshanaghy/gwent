---
name: playback-trace
description: Start the gwent game by replaying one or more trace files to jump to a saved game state
allowed-tools: Bash, Glob
---

Replay one or more MQTT trace recordings to jump to a saved game state.

The argument is one or more trace filenames (comma-separated, without .jsonl extension). If no argument is given, list available recordings and ask the user to pick.

## Steps

1. If no argument given, list available recordings:
   ```bash
   ls software/gwent/gwent/game/recordings/*.jsonl
   ```
   Then ask the user which one(s) to replay.

2. Resolve filenames to full paths under `software/gwent/gwent/game/recordings/`. Add `.jsonl` if not present.

3. Kill any running gwent processes:
   ```bash
   kill -9 $(pgrep -f 'bin/gwent') 2>/dev/null; sleep 2
   ```

4. Start gwent with `GWENT_REPLAY` set to the comma-separated list of full paths. Tracing is disabled (no `GWENT_TRACE`):
   ```bash
   source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_REPLAY=<paths> GWENT_TRACE=none gwent >> /tmp/logs/gwent.log 2>&1 &
   ```
   Note: Setting GWENT_TRACE=none causes the input prompt to be skipped and tracing stays disabled.

5. Wait for startup, confirm the process is running, and check logs for "Replay complete" messages.

6. Tell the user which state the game should be in based on the trace filename(s).
