---
name: playback-and-record-trace
description: Replay trace files to reach a game state, then start recording a new trace from that point
allowed-tools: Bash, Glob
---

Replay existing trace recordings to jump to a game state, then start recording a new trace segment from that point forward.

Arguments: `<replay-files> <new-trace-name>`
- `<replay-files>`: comma-separated trace filenames to replay (without .jsonl)
- `<new-trace-name>`: filename for the new recording (without .jsonl)

If arguments are missing, list available recordings and ask the user for both the replay file(s) and the new trace name.

## Steps

1. If arguments are missing, list available recordings:
   ```bash
   ls software/gwent/gwent/game/recordings/*.jsonl
   ```
   Ask the user which to replay and what to name the new recording.

2. Resolve replay filenames to full paths under `software/gwent/gwent/game/recordings/`. Add `.jsonl` if not present.

3. Kill any running gwent processes:
   ```bash
   kill -9 $(pgrep -f 'bin/gwent') 2>/dev/null; sleep 2
   ```

4. Start gwent with both `GWENT_REPLAY` and `GWENT_TRACE`:
   ```bash
   source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_REPLAY=<replay-paths> GWENT_TRACE=<new-trace-name> gwent >> /tmp/logs/gwent.log 2>&1 &
   ```

5. Wait for startup, confirm the process is running, and check logs for "Replay complete" and "Recording trace" messages.

6. Tell the user:
   - Replay is complete, game is at the target state
   - New actions are being recorded to `software/gwent/gwent/game/recordings/<new-trace-name>.jsonl`
   - Play through the next segment, then tell Claude to stop
   - To replay both segments later: `GWENT_REPLAY=<first>,<second>`
   - Logs at `tail -f /tmp/logs/gwent.log`
