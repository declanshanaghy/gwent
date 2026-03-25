---
name: playback-and-record-trace
description: Replay a playback file or trace files to reach a game state, then start recording a new trace from that point
allowed-tools: Bash, Glob
---

Replay existing trace recordings to jump to a game state, then start recording a new trace segment from that point forward.

Arguments: `<playback-or-traces> <new-trace-name>`
- `<playback-or-traces>`: a `.json` playback file from `playbacks/`, or comma-separated `.jsonl` trace filenames from `recordings/`
- `<new-trace-name>`: filename for the new recording (without .jsonl)

If arguments are missing, list available playbacks/recordings and ask the user for both.

**IMPORTANT:** All file paths must be resolved to absolute paths before passing to gwent. The base directories are:
- Playbacks: `/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent/gwent/game/playbacks/`
- Recordings: `/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent/gwent/game/recordings/`

## Steps

1. If arguments are missing, list available options:
   ```bash
   echo "=== Playbacks ===" && ls software/gwent/gwent/game/playbacks/*.json 2>/dev/null
   echo "=== Recordings ===" && ls software/gwent/gwent/game/recordings/*.jsonl 2>/dev/null
   ```
   Ask the user which to replay and what to name the new recording.

2. Resolve file paths to absolute paths (see playback-trace skill for details).

3. Kill any running gwent processes:
   ```bash
   kill -9 $(pgrep -f 'bin/gwent') 2>/dev/null; sleep 2
   ```

4. Start gwent with both replay and trace using absolute paths:
   - For a playback JSON file:
     ```bash
     source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_PLAYBACK=<absolute-path> GWENT_TRACE=<new-trace-name> gwent >> /tmp/logs/gwent.log 2>&1 &
     ```
   - For individual traces:
     ```bash
     source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_REPLAY=<absolute-paths> GWENT_TRACE=<new-trace-name> gwent >> /tmp/logs/gwent.log 2>&1 &
     ```

5. Wait for startup, confirm the process is running, and check logs for completion and recording messages.

6. Tell the user:
   - Playback is complete, game is at the target state
   - New actions are being recorded to `software/gwent/gwent/game/recordings/<new-trace-name>.jsonl`
   - Play through the next segment, then tell Claude to stop
   - Logs at `tail -f /tmp/logs/gwent.log`
