---
name: record-trace
description: Start the gwent game and record MQTT traffic to a named trace file for later replay
allowed-tools: Bash
---

Record a new MQTT trace of a gwent game session.

The argument is the trace filename (without .jsonl extension). If no argument is given, ask the user for one.

**IMPORTANT:** Traces are recorded to the absolute path:
`/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent/gwent/game/recordings/<filename>.jsonl`

## Steps

1. Kill any running gwent processes:
   ```bash
   kill -9 $(pgrep -f 'bin/gwent') 2>/dev/null; sleep 2
   ```

2. Start gwent with the trace filename set via `GWENT_TRACE` env var. Run in background:
   ```bash
   source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_TRACE=<filename> gwent >> /tmp/logs/gwent.log 2>&1 &
   ```

3. Wait a few seconds, confirm the process is running, and tell the user:
   - The game is recording to `software/gwent/gwent/game/recordings/<filename>.jsonl`
   - They should play through the game to the desired state
   - When done, tell Claude to stop the recording (kill the process)
   - Logs at `tail -f /tmp/logs/gwent.log`
