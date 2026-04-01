---
name: record-trace
description: Start the gwent game, optionally loading a saved state, then save a new state snapshot on SIGUSR1
allowed-tools: Bash
---

Start the gwent game and save a state snapshot when requested.

The argument is the output state filename (without .json extension). If no argument is given, ask the user for one.

Optionally, a second argument can specify a state to load first (to resume from a saved point).

**State files are stored at:**
`/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/data/recordings/<name>.json`

## Steps

1. Kill any running gwent processes:
   ```bash
   kill -9 $(pgrep -f 'bin/gwent') 2>/dev/null; sleep 2
   ```

2. Start gwent with `GWENT_STATE_OUT` set to the output filename. If loading a state, also set `GWENT_STATE`:
   ```bash
   source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_STATE_OUT=<output-name> gwent >> /tmp/logs/gwent.log 2>&1 &
   ```

3. Wait a few seconds, confirm the process is running, and tell the user:
   - The game is running
   - When they reach the desired state, tell Claude to save (sends SIGUSR1)
   - State will be saved to `recordings/<output-name>.json`
   - Logs at `tail -f /tmp/logs/gwent.log`

4. When the user says to save, send SIGUSR1:
   ```bash
   kill -USR1 $(pgrep -f 'bin/gwent' | head -1)
   ```
   Then confirm the state file was written.
