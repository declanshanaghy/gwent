---
name: llm-vs
description: Two LLM models play Gwent against each other via the live game server. Use when the user says "llm vs", "ollama vs", "models play gwent", "AI vs AI", or specifies model names to play.
user_invocable: true
allowed-tools: Bash, Read, Grep, Glob, AskUserQuestion
---

Orchestrate two LLM models playing Gwent against each other through the live game server.

## Usage

`/llm-vs [--model-p1 MODEL] [--model-p2 MODEL]`

- Models use a provider prefix: `anthropic/`, `openai/`, or `ollama/`
- Default model: `anthropic/claude-haiku-4-5-20251001`
- P2 defaults to P1's model if `--model-p2` not specified
- Default Ollama URL: `http://hal-9005.lan:11434`
- API keys loaded from `.env` (OPENAI_API_KEY, ANTHROPIC_API_KEY)

## Help (--help)

When the user passes `--help`, display this help text verbatim and do NOT launch a game:

````
## /llm-vs — LLM vs LLM Gwent Match

Two AI models play Gwent against each other through the live game server.

### Usage

  /llm-vs [--model-p1 MODEL] [--model-p2 MODEL] [options]

### Prerequisites

  The game server must be running and in PlayRound stage before launching.
  Use /dev-server to start the server and deal cards first.

### Quick Start

  /llm-vs                                                   # claude-haiku vs claude-haiku
  /llm-vs --model-p1 anthropic/claude-sonnet-4-6            # sonnet mirror match
  /llm-vs --model-p1 openai/gpt-4o                          # GPT-4o mirror match
  /llm-vs --model-p1 ollama/deepseek-r1:14b                 # Ollama local model
  /llm-vs --model-p1 anthropic/claude-haiku-4-5-20251001 \
          --model-p2 openai/gpt-4o                          # cross-provider matchup

### Model Providers

  anthropic/MODEL   Anthropic API (needs ANTHROPIC_API_KEY in .env)
  openai/MODEL      OpenAI API (needs OPENAI_API_KEY in .env)
  ollama/MODEL      Ollama local (default: http://hal-9005.lan:11434)

### Options

  --model-p1 MODEL   Model for P1 (default: claude-haiku)
  --model-p2 MODEL   Model for P2 (default: same as --model-p1)
  --no-commentary    Disable MQTT turn commentary announcements
  --help             Show this help

### Turn Control

  The game pauses after each turn. You choose:
  • Continue           Play one more turn
  • Run uninterrupted  Let both AIs play freely until game over
  • Order P1/P2        Inject strategic orders into the next AI move
  • Stop               End the match (SIGTERM)

### Examples — Mirror Matches

  /llm-vs                                                       # haiku vs haiku (default)
  /llm-vs --model-p1 anthropic/claude-sonnet-4-6                # sonnet vs sonnet
  /llm-vs --model-p1 openai/gpt-4o                              # GPT-4o vs GPT-4o
  /llm-vs --model-p1 ollama/deepseek-r1:14b                     # deepseek vs deepseek
  /llm-vs --model-p1 ollama/llama3.2:3b                         # llama vs llama
  /llm-vs --model-p1 ollama/qwen2.5:7b                           # qwen vs qwen

### Examples — Cross-Model Matchups

  /llm-vs --model-p1 anthropic/claude-haiku-4-5-20251001 --model-p2 openai/gpt-4o
  /llm-vs --model-p1 anthropic/claude-sonnet-4-6 --model-p2 ollama/deepseek-r1:14b
  /llm-vs --model-p1 openai/gpt-4o --model-p2 ollama/llama3.2:3b
  /llm-vs --model-p1 ollama/deepseek-r1:14b --model-p2 ollama/qwen2.5:7b
````

## Running

The game-loop.py script handles everything: prerequisite checks, system prompt generation, and the full turn loop with audio-synced long-polling. The game server must already be running and in PlayRound.

```bash
python3 .claude/skills/llm-vs/scripts/game-loop.py \
  --model-p1 MODEL \
  [--model-p2 MODEL] \
  [--no-pause] \
  [--json] \
  [--ollama-url URL] \
  [--host HOST] \
  [--max-turns N]
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--model-p1` | `anthropic/claude-haiku-4-5-20251001` | Model for P1 (and P2 if --model-p2 not set) |
| `--model-p2` | same as `--model-p1` | Different model for P2 |
| `--no-pause` | off | Run continuously without pausing between turns |
| `--no-commentary` | off | Disable MQTT announcements for LLM turn commentary |
| `--json` | off | Also emit structured JSON events per turn |
| `--ollama-url` | `http://hal-9005.lan:11434` | Ollama API URL |
| `--host` | `localhost` | Gwent MQTT broker host (state + commands over MQTT) |
| `--max-turns` | 60 | Safety limit |

### Pause behavior (DEFAULT — no flag needed)

The script **pauses by default** — it starts paused and pauses again after every turn, writing status to `/tmp/llm-vs-status.json` and blocking until SIGUSR1 is received. This enables turn-by-turn orchestration from the skill. Use `--no-pause` to disable this.

**IMPORTANT**: The script starts in a paused state. After launching, you MUST send `kill -USR1 <pid>` to begin the first turn.

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

1. **Check if game-loop.py is already running**: read PID from `/tmp/pids/game-loop.pid`
2. **Validate the PID is actually alive**: `kill -0 <pid> 2>/dev/null`
   - If PID file exists but `kill -0` fails, the process is dead/stale — treat as "not running"
3. **If running** and user says "unpause", "continue", "next turn", "just unpause":
   - Read PID from `/tmp/pids/game-loop.pid`
   - Send `kill -USR1 <pid>` to unpause
   - Do NOT launch a new process
4. **If NOT running**: check current game state via `mosquitto_sub -h localhost -u geralt -P gwent -t gwent/server/state -C 1 -W 3 | python3 -c "import json,sys; print(json.load(sys.stdin).get('active_stage',''))"`:
   - If stage is `PlayRound` → launch the game loop
   - If stage is anything else, or server is down → tell the user to start the server and deal cards first (use `/dev-server`)
5. **Model mapping**: `/llm-vs --model-p1 ollama/deepseek-r1:14b` → `--model-p1 ollama/deepseek-r1:14b`
6. **Unattended**: only pass `--no-pause` when user says "auto-play", "run unattended"
8. **IMPORTANT**: After launching, send `kill -USR1 <pid>` to start the first turn (script starts paused)

## Turn-by-Turn Orchestration

The script pauses by default (no flag needed). Use this loop:

### 1. Launch in background

```bash
source ~/gwent-venv/bin/activate && \
source <(grep -v '^#' .env | sed 's/^/export /') && \
python3 .claude/skills/llm-vs/scripts/game-loop.py \
  --model-p1 MODEL [--model-p2 MODEL] &
```

Capture the PID. The script starts **paused** — send `kill -USR1 <pid>` to begin the first turn. After each turn it pauses again.

### 2. Wait for pause and read status

After each turn, the script writes `/tmp/llm-vs-status.json`:
```json
{"turn": 3, "current_player": "PLAYER.ONE", "round": 1, "scores": {...}, "pid": 12345}
```

Read the script's stdout for the turn summary, board state, and reasoning.

Then fetch the **full game state** for the rich summary:
```bash
mosquitto_sub -h localhost -u geralt -P gwent -t gwent/server/state -C 1 -W 3 | /home/dshanaghy/gwent-venv/bin/python3 -c "
import json, sys
s = json.load(sys.stdin)
b = s['state']['board']
print(json.dumps({
    'factions': b.get('factions'),
    'leaders': {p: v.get('name') for p, v in b.get('leaders', {}).items()},
    'hand_sizes': {p: len(v) for p, v in b.get('hands', {}).items()},
    'deck_sizes': {p: len(v) for p, v in b.get('decks', {}).items()},
    'scores': b.get('scores'),
    'weather': b.get('weather_rows', []),
    'horns': b.get('commander_horn_rows', {}),
    'current_player': b.get('current_player'),
    'round': b.get('round_number'),
}, indent=2))
"
```

Use this data to render the rich game state summary (see step 3).

### 3. Present game state summary and AskUserQuestion

After each turn completes, fetch the full game state from `mosquitto_sub -h localhost -u geralt -P gwent -t gwent/server/state -C 1 -W 3` and present a rich, emoji-laden markdown summary **before** the AskUserQuestion. Use this template:

```
## ⚔️ Round {round} — Turn {turn}

### 🏰 {P1 Faction Emoji} {P1 Faction} vs {P2 Faction Emoji} {P2 Faction}

| | {P1 Faction Emoji} {P1 Faction} | {P2 Faction Emoji} {P2 Faction} |
|---|---|---|
| 👑 Leader | {P1 leader name} | {P2 leader name} |
| 🃏 Hand | {P1 hand size} cards | {P2 hand size} cards |
| 📚 Deck | {P1 deck size} remaining | {P2 deck size} remaining |

### 📊 Scoreboard

| Row | {P1 Faction Emoji} {P1 Faction} | {P2 Faction Emoji} {P2 Faction} |
|---|---|---|
| ⚔️ Close | {p1_close} | {p2_close} |
| 🏹 Ranged | {p1_ranged} | {p2_ranged} |
| 🔥 Siege | {p1_siege} | {p2_siege} |
| **🏆 Total** | **{p1_total}** | **{p2_total}** |

{weather_line}
{horn_line}

### 🎯 Next up: {Current Player Faction Emoji} {Current Player Faction}
```

**Faction emojis:**
| Faction | Emoji |
|---------|-------|
| Monsters | 👹 |
| Nilfgaardian | 🦅 |
| Northern Realms | 🏰 |
| Scoia'tael | 🌿 |
| Skellige | ⚓ |

**Conditional lines:**
- `{weather_line}`: If `weather_rows` is non-empty, show `🌨️ **Weather:** {comma-separated weather effects}`. Omit if empty.
- `{horn_line}`: If any player has commander horns, show `📯 **Commander Horns:** {details}`. Omit if empty.
- Show score cells with leading emoji when non-zero: e.g. `⚔️ 27` vs just `0`
- If a player is winning, add 👑 next to their total

After the summary, present **AskUserQuestion** with these options:

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
