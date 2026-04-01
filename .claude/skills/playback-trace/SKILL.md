---
name: playback-trace
description: Start the gwent game by loading a saved state file to jump to a specific game state
allowed-tools: Bash, Glob
---

Load a saved game state to jump to a specific point in the game.

The argument is a state filename (with or without .json extension) from the recordings directory,
followed by optional flags.

If no argument is given, list available state files and ask the user to pick.

**State files are stored at:**
`/home/dshanaghy/src/github.com/declanshanaghy/gwent/software/data/recordings/`

## Supported flags

| Flag | Env var | Description |
|------|---------|-------------|
| `--tts PROVIDER` | `GWENT_TTS` | TTS provider: gtts, piper, elevenlabs, openai, say, none |
| `--owner NAME` | `GWENT_OWNER` | Card owner name for filtering |
| `--simple` | `GWENT_SIMPLE` | Simple mode (reduced hardware) |
| `--state-out NAME` | `GWENT_STATE_OUT` | Name for saving state on SIGUSR1 |

## Steps

1. If no argument given, list available state files:
   ```bash
   ls software/data/recordings/*.json 2>/dev/null
   ```
   Then ask the user which one to load.

2. Parse the arguments:
   - First positional arg = state filename (resolve to absolute path, add `.json` if missing)
   - `--tts PROVIDER` → set `GWENT_TTS=PROVIDER`
   - `--owner NAME` → set `GWENT_OWNER=NAME`
   - `--simple` → set `GWENT_SIMPLE=1`
   - `--state-out NAME` → set `GWENT_STATE_OUT=NAME`

3. Stop gwent via dev-server (handles PID tracking and cleanup):
   ```bash
   bash scripts/dev-server.sh gwent stop
   ```

4. Start gwent via dev-server with environment variables set:
   ```bash
   GWENT_STATE=<absolute-path> [GWENT_TTS=<provider>] [GWENT_OWNER=<name>] [GWENT_SIMPLE=1] [GWENT_STATE_OUT=<name>] bash scripts/dev-server.sh gwent start
   ```

   For `--tts none`, set `GWENT_TTS=none` which disables server-side TTS.

5. Wait a few seconds, then check logs for "Loading game state" and "now at stage" messages:
   ```bash
   sleep 3 && grep -a -E "Loading game state|now at stage" /tmp/logs/gwent.log | tail -3
   ```

6. Tell the user which stage the game is at and which TTS provider is active (if set).
