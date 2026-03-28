---
name: llm-vs
description: Two LLM models play Gwent against each other via the live game server. Use when the user says "llm vs", "ollama vs", "models play gwent", "AI vs AI", or specifies model names to play.
user_invocable: true
allowed-tools: Bash, Read, Grep, Glob
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
  [--ollama-url URL] \
  [--game-url URL] \
  [--max-turns N]
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `anthropic/claude-haiku-4-5-20251001` | Model with provider prefix |
| `--fresh` | off | Restart game server and trigger random deal |
| `--ollama-url` | `http://hal-9005.lan:11434` | Ollama API URL |
| `--game-url` | `http://localhost:8080` | Game server URL |
| `--max-turns` | 60 | Safety limit |

### What `--fresh` does

1. Restarts the gwent dev server via `scripts/dev-server.sh gwent restart`
2. Waits for the server to reach MainMenu
3. Sends a "Random Deal" choice via MQTT
4. Waits for PlayRound stage

Without `--fresh`, the script expects the game to already be in PlayRound.

### What the script does

1. Checks Ollama model availability and MQTT connectivity
2. Ensures game is in PlayRound (or starts fresh)
3. Builds per-player system prompts with faction, leader, and full deck info
4. Writes conversation logs to `/tmp/logs/llm-vs-p{1,2}.jsonl`
5. Runs the turn loop: fetch state -> call LLM -> validate -> publish MQTT -> long-poll for turn advance
6. Uses ETag-based long-polling to sync with TTS audio playback (waits for announcements to finish before next turn)
7. Reports each turn as a one-liner with reasoning

### Mapping user args

- `/llm-vs` -> `python3 ... --model llama3.2:3b --fresh`
- `/llm-vs deepseek-r1:14b` -> `python3 ... --model deepseek-r1:14b --fresh`
- No explicit `--fresh` from user -> always pass `--fresh` unless user says "resume" or "continue"

## User intervention

If the user says something during the game loop (interrupts), they may want to:
- Change strategy for a player
- Force a specific action
- Stop the game

Honor their request, then re-launch the script without `--fresh` to continue.

## Output

After the game ends, report:
- Final scores and winner
- Total turns played
- Log file paths
