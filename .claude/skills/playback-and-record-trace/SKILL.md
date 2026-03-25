---
name: playback-and-record-trace
description: Load a saved game state, then save a new state snapshot when the user reaches the next point
allowed-tools: Bash, Glob
---

Load a saved game state to jump to a point in the game, then save a new state snapshot when the user is ready.

Arguments: `<input-state> <output-state-name>`
- `<input-state>`: a state .json file to load from `recordings/`
- `<output-state-name>`: filename for the new state snapshot (without .json, always the last argument)

If arguments are missing, list available state files and ask the user.

**State files are stored at:**
`/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent/gwent/game/recordings/`

## Steps

1. If arguments are missing, list available state files:
   ```bash
   ls software/gwent/gwent/game/recordings/*.json 2>/dev/null
   ```
   Ask the user which state to load and what to name the new snapshot.

2. Resolve the input state to an absolute path under `recordings/`. Add `.json` if not present.

3. Kill any running gwent processes:
   ```bash
   kill -9 $(pgrep -f 'bin/gwent') 2>/dev/null; sleep 2
   ```

4. Start gwent with both `GWENT_STATE` (load) and `GWENT_STATE_OUT` (save name):
   ```bash
   source ~/gwent-venv/bin/activate && RUNNING_ON_PI=true PYTHONUNBUFFERED=1 GWENT_STATE=<absolute-input-path> GWENT_STATE_OUT=<output-name> gwent >> /tmp/logs/gwent.log 2>&1 &
   ```

5. Wait for startup, confirm the process is running, and check logs for "Loading game state" and "now at stage" messages.

6. Tell the user:
   - State loaded, game is at the target stage
   - Play through to the next desired point, then tell Claude to save
   - When they say save, send SIGUSR1: `kill -USR1 $(pgrep -f 'bin/gwent' | head -1)`
   - State will be saved to `recordings/<output-name>.json`
   - Logs at `tail -f /tmp/logs/gwent.log`
