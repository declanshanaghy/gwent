---
name: playback-and-record-trace
description: Replay a playback file (.json or .jsonl) to reach a game state, then start recording a new trace (.jsonl) from that point
allowed-tools: Bash, Glob
---

Replay a playback file to jump to a game state, then start recording a new trace segment.

Arguments: `<input-file> <output-trace-name>`
- `<input-file>`: a `.json` playback file from `playbacks/`, OR a `.jsonl` trace file from `recordings/`
- `<output-trace-name>`: filename for the new recording (always .jsonl, last argument)

If arguments are missing, list available files and ask the user.

**IMPORTANT:** All file paths must be resolved to absolute paths before passing to gwent. The base directories are:
- Playbacks: `/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent/gwent/game/playbacks/`
- Recordings: `/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent/gwent/game/recordings/`

## Steps

1. If arguments are missing, list available files:
   ```bash
   echo "=== Playbacks ===" && ls software/gwent/gwent/game/playbacks/*.json 2>/dev/null
   echo "=== Recordings ===" && ls software/gwent/gwent/game/recordings/*.jsonl 2>/dev/null
   ```
   Ask the user which to replay and what to name the new recording.

2. Resolve the input file to an absolute path:
   - `.json` → resolve under `playbacks/`
   - `.jsonl` → resolve under `recordings/`

3. Kill any running gwent processes:
   ```bash
   kill -9 $(pgrep -f 'bin/gwent') 2>/dev/null; sleep 2
   ```

4. Start gwent:
   - If input is `.json`, use `GWENT_PLAYBACK`:
     ```bash
     source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_PLAYBACK=<absolute-path> GWENT_TRACE=<output-name> gwent >> /tmp/logs/gwent.log 2>&1 &
     ```
   - If input is `.jsonl`, use `GWENT_REPLAY`:
     ```bash
     source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_REPLAY=<absolute-path> GWENT_TRACE=<output-name> gwent >> /tmp/logs/gwent.log 2>&1 &
     ```

5. Wait for startup, confirm the process is running, and check logs for completion and recording messages.

6. Tell the user:
   - Playback is complete, game is at the target state
   - New actions are being recorded to `software/gwent/gwent/game/recordings/<output-name>.jsonl`
   - Play through the next segment, then tell Claude to stop
   - Logs at `tail -f /tmp/logs/gwent.log`
