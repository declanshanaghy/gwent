---
name: playback-trace
description: Start the gwent game by loading a saved state file to jump to a specific game state
allowed-tools: Bash, Glob
---

Load a saved game state to jump to a specific point in the game.

The argument is a state filename (with or without .json extension) from the recordings directory.

If no argument is given, list available state files and ask the user to pick.

**State files are stored at:**
`/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/gwent/gwent/game/recordings/`

## Steps

1. If no argument given, list available state files:
   ```bash
   ls software/gwent/gwent/game/recordings/*.json 2>/dev/null
   ```
   Then ask the user which one to load.

2. Resolve the filename to the absolute path under the recordings directory. Add `.json` if not present.

3. Stop gwent via dev-server (handles PID tracking and cleanup):
   ```bash
   bash scripts/dev-server.sh gwent stop
   ```

4. Start gwent via dev-server with `GWENT_STATE` set to the absolute path:
   ```bash
   GWENT_STATE=<absolute-path> bash scripts/dev-server.sh gwent start
   ```

5. Wait a few seconds, then check logs for "Loading game state" and "now at stage" messages:
   ```bash
   sleep 3 && grep -a -E "Loading game state|now at stage" /tmp/logs/gwent.log | tail -3
   ```

6. Tell the user which stage the game is at based on the log output.
