---
name: llm-vs
description: Two LLM models play Gwent against each other via the live game server. Use when the user says "llm vs", "ollama vs", "models play gwent", "AI vs AI", or specifies model names to play.
user_invocable: true
allowed-tools: Bash, Read, Grep, Glob, AskUserQuestion
---

Orchestrate two LLM models playing Gwent against each other through the live game server.

## Usage

`/llm-vs [model] [--fresh]`

- Models use a provider prefix: `anthropic/`, `openai/`, or none (Ollama)
- Default model: `anthropic/claude-haiku-4-5-20251001`
- Default Ollama URL: `http://hal-9005.lan:11434`
- API keys loaded from `.env` (OPENAI_API_KEY, ANTHROPIC_API_KEY)

## Running

The game-loop.py script handles everything: prerequisite checks, game startup, system prompt generation, and the full turn loop with audio-synced long-polling.

```bash
python3 .claude/skills/llm-vs/scripts/game-loop.py \
  --model MODEL \
  [--fresh] \
  [--pause] \
  [--json] \
  [--ollama-url URL] \
  [--game-url URL] \
  [--max-turns N]
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `anthropic/claude-haiku-4-5-20251001` | Model with provider prefix |
| `--fresh` | off | Restart game server and trigger random deal |
| `--no-pause` | off | Run continuously without pausing between turns |
| `--json` | off | Also emit structured JSON events per turn |
| `--ollama-url` | `http://hal-9005.lan:11434` | Ollama API URL |
| `--game-url` | `http://localhost:8080` | Game server URL |
| `--max-turns` | 60 | Safety limit |

### What `--fresh` does

1. Restarts the gwent dev server via `scripts/dev-server.sh gwent restart`
2. Waits for the server to reach MainMenu
3. Sends a "Random Deal" choice via MQTT
4. Waits for PlayRound stage

Without `--fresh`, the script expects the game to already be in PlayRound.

### What `--pause` does

The script pauses **after every turn**, writing status to `/tmp/llm-vs-status.json` and blocking until SIGUSR1 is received. This enables turn-by-turn orchestration from the skill.

**Resume methods:**
- `kill -USR1 <pid>` — resume without orders
- Write `/tmp/llm-vs-orders-p{1,2}.json` then `kill -USR1 <pid>` — resume with commander orders injected into the next LLM call

**Orders file format:**
```bash
# P1 orders:
echo '{"order": "Focus on siege units"}' > /tmp/llm-vs-orders-p1.json
# P2 orders:
echo '{"order": "Play your spy card"}' > /tmp/llm-vs-orders-p2.json
```

Orders are wrapped in faction-themed language before injection (e.g., "The Jarl's war council demands: ...").

### Mapping user args

### Decision tree

1. **Check if game-loop.py is already running**: `pgrep -f game-loop.py`
2. **Validate the PID is actually alive**: `kill -0 <pid> 2>/dev/null`
   - If `pgrep` returns a PID but `kill -0` fails, the process is dead/stale — treat as "not running"
   - Also validate against `/tmp/llm-vs-status.json` PID if present — if status PID differs from pgrep PID, the status file is stale
3. **If running** and user says "unpause", "continue", "next turn", "just unpause":
   - Read PID: `pgrep -f game-loop.py` or from `/tmp/llm-vs-status.json`
   - Send `kill -USR1 <pid>` to unpause
   - Do NOT launch a new process
4. **If NOT running**: launch a **fresh** game by default (`--fresh` flag). Only skip `--fresh` if the user explicitly says "resume", "continue from where we left off", or similar.
5. **Model mapping**: `/llm-vs deepseek-r1:14b` → `--model deepseek-r1:14b`
6. **Fresh game**: `--fresh` is the DEFAULT. Only omit it when user explicitly asks to resume an existing game.
7. **Unattended**: only pass `--no-pause` when user says "auto-play", "run unattended"

## Turn-by-Turn Orchestration

When running with `--pause`, use this loop:

### 1. Launch in background

```bash
python3 .claude/skills/llm-vs/scripts/game-loop.py \
  --model MODEL --pause --game-url http://localhost:8080 &
```

Capture the PID. The script will play the first turn then pause.

### 2. Wait for pause and read status

After each turn, the script writes `/tmp/llm-vs-status.json`:
```json
{"turn": 3, "current_player": "PLAYER.ONE", "round": 1, "scores": {...}, "pid": 12345}
```

Read the script's stdout for the turn summary, board state, and reasoning.

### 3. Present AskUserQuestion

After each turn completes, use **AskUserQuestion** with these options:

- **"Continue"** — resume for one turn, then pause again
- **"Run uninterrupted"** — disable auto-pause, let agents play freely until game ends (sends SIGUSR2)
- **"Order P1"** — prompt for orders to P1's agent (use faction-themed label)
- **"Order P2"** — prompt for orders to P2's agent (use faction-themed label)
- **"Stop"** — kill the game loop

Use faction-themed labels for order options, e.g.:
- If P1 is Skellige: "Order the Jarl's army"
- If P2 is Monsters: "Command the Wild Hunt"

Note: max 4 options in AskUserQuestion. Use the 2 most relevant order options plus Continue and Run uninterrupted. Put Stop as the "Other" fallback.

### 4. Handle user choice

**"Continue"**: `kill -USR1 <pid>` — plays one turn, pauses again

**"Run uninterrupted"**: `kill -USR2 <pid>` then `kill -USR1 <pid>` — disables auto-pause and unpauses. The game runs freely. The skill should exit the AskUserQuestion loop and just let stdout flow.

**Orders**: Write the user's **exact raw text** — do NOT rephrase, sanitize, or summarize. The game-loop adds faction preamble automatically:
```bash
echo '{"order": "<user text VERBATIM>"}' > /tmp/llm-vs-orders-p1.json  # or p2
kill -USR1 <pid>
```

**"Stop"**: `kill <pid>` (SIGTERM)

### SIGUSR2 from outside the loop

If the user says "let them play", "auto-play", "run free", "uninterrupted" while the game is running (outside the AskUserQuestion loop), `/llm-vs` should:
1. Find PID: `pgrep -f game-loop.py`
2. Send `kill -USR2 <pid>` to toggle auto-pause off
3. If currently paused, also send `kill -USR1 <pid>` to unpause

To re-enable auto-pause from outside: `kill -USR2 <pid>` again (it's a toggle)

### 5. Repeat

Loop back to step 2 until the game ends.

## Faction-Themed Commander Labels

Use these for AskUserQuestion labels/descriptions:

| Faction | Order label | Preamble |
|---------|-------------|----------|
| Monsters | "Command the Wild Hunt" | "The Crone whispers from the shadows" |
| Nilfgaardian | "Issue Imperial decree" | "By Imperial decree of the Emperor" |
| Northern Realms | "Send royal edict" | "A royal edict from the throne of Temeria" |
| Scoia'tael | "Elder's command" | "The elder of the Scoia'tael commands" |
| Skellige | "Order the Jarl's army" | "The Jarl's war council demands" |

## Output

Each turn shows:
1. Pre-turn summary (hand size, scores, weather, leader, orders)
2. LLM action and reasoning
3. Board state summary
4. JSON event (if `--json`)

After the game ends, report:
- Final scores and winner
- Total turns played
- Log file paths
