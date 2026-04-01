# ADR 010: LLM Game Orchestration via HTTP API and MQTT

## Status

Accepted

## Context

We want AI-vs-AI Gwent games for automated testing, entertainment, and balance analysis. The game server should not need to know about LLMs — it should enforce rules the same way regardless of whether a human or AI is playing. Multiple LLM providers (Anthropic, OpenAI, Google Gemini, Ollama) should be supported.

## Decision

- An external Python script (`game-loop.py`) acts as the LLM orchestrator, running outside the game server process.
- The orchestrator polls game state via `GET /state/poll` (long-polling with ETag).
- When it's a player's turn, the orchestrator sends the board state to the LLM and asks for a move.
- Moves are published as MQTT messages on `gwent/cards/raw/read` — the exact same topic as physical RFID scans.
- Supported providers via model prefix: `anthropic/`, `openai/`, `gemini/`, `ollama/` with alias shortcuts (e.g., `anthropic/sonnet`).
- Each player can use a different model (`--model-p1`, `--model-p2`).
- The orchestrator never injects strategy hints — it only relays the current state and asks for a card choice.
- Game rules are enforced entirely by the server; invalid moves are rejected.

## Consequences

### Positive
- Server is LLM-agnostic — same code path for human and AI play.
- Any new LLM provider just needs an API adapter in the orchestrator.
- Games can be recorded and replayed using the standard trace system.
- Multiple model matchups enable automated balance testing.

### Negative
- Orchestrator must parse game state JSON to construct meaningful prompts.
- LLM API latency (1-10s per move) makes games slow compared to human play.

### Risks
- LLM may produce invalid moves requiring retry logic and turn timeouts.
- API costs for cloud models can accumulate during extended test runs.

## Related
- `.claude/skills/llm-vs/scripts/game-loop.py`
- [ADR 005: REST API Long-Polling](005-rest-api-long-polling.md)
- [ADR 003: MQTT PubSub](003-mqtt-pubsub-backbone.md)
