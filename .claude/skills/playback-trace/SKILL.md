---
name: playback-trace
description: Start the gwent game by replaying trace files to jump to a saved game state. Accepts a playback JSON file or individual trace filenames.
allowed-tools: Bash, Glob
---

Replay MQTT trace recordings to jump to a saved game state.

The argument can be:
- A `.json` playback file (e.g., `000-happy.json`) from `playbacks/`
- One or more `.jsonl` trace filenames (comma-separated) from `recordings/`

If no argument is given, list available playbacks and recordings and ask the user to pick.

**IMPORTANT:** All file paths must be resolved to absolute paths before passing to gwent. The base directories are:
- Playbacks: `/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent/gwent/game/playbacks/`
- Recordings: `/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent/gwent/game/recordings/`

## Steps

1. If no argument given, list available options:
   ```bash
   echo "=== Playbacks ===" && ls software/gwent/gwent/game/playbacks/*.json 2>/dev/null
   echo "=== Recordings ===" && ls software/gwent/gwent/game/recordings/*.jsonl 2>/dev/null
   ```
   Then ask the user which to replay.

2. Resolve the argument to an absolute path:
   - If it ends in `.json`, resolve under `software/gwent/gwent/game/playbacks/`
   - If it ends in `.jsonl`, resolve under `software/gwent/gwent/game/recordings/`
   - Use `realpath` or prepend the full repo path to get absolute paths

3. Kill any running gwent processes:
   ```bash
   kill -9 $(pgrep -f 'bin/gwent') 2>/dev/null; sleep 2
   ```

4. Start gwent with the absolute path:
   - For a playback JSON file, use `GWENT_PLAYBACK`:
     ```bash
     source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_PLAYBACK=<absolute-path> GWENT_TRACE=off gwent >> /tmp/logs/gwent.log 2>&1 &
     ```
   - For individual traces, use `GWENT_REPLAY` with comma-separated absolute paths:
     ```bash
     source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_REPLAY=<absolute-paths> GWENT_TRACE=off gwent >> /tmp/logs/gwent.log 2>&1 &
     ```

5. Wait for startup, confirm the process is running, and check logs for "Playback complete" or "Replay complete" messages.

6. Tell the user which state the game should be in based on the playback/trace name(s).
