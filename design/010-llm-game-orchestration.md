# PRD-010: LLM Game Orchestration

## Overview

The LLM orchestration system enabled AI-vs-AI gameplay by connecting language model providers to the game server. Each LLM player polled the HTTP API for state, reasoned about the board, and published moves via MQTT. Multiple provider backends were supported for comparative play.

## Requirements

### Functional Requirements

- FR-1: Supported LLM providers: Anthropic (Claude), OpenAI (GPT), Google (Gemini), and Ollama (local models).
- FR-2: Model aliases simplified provider selection (e.g., `anthropic/sonnet`, `openai/gpt-4o`, `ollama/deepseek`).
- FR-3: Each LLM player polled `GET /state/poll` for board state updates and detected its turn via `current_player`.
- FR-4: Moves were published as MQTT card_play messages to the appropriate player topic.
- FR-5: The turn loop followed: check stage, fetch board state, wait for current_player match, build prompt, call model, extract and execute action.
- FR-6: SIGUSR1 toggled pause/step mode for debugging; SIGUSR2 resumed unattended play.
- FR-7: Prompts included round history and faction passive ability context for informed decision-making.
- FR-8: LLM conversation history was reset at the start of each round to manage context length.
- FR-9: The orchestrator never injected strategy hints; it only relayed game state and errors.
- FR-10: Pass actions were supported alongside card play actions.

### Non-Functional Requirements

- NFR-1: The orchestrator tolerated LLM API errors and retried with exponential backoff.
- NFR-2: Invalid moves (malformed responses, illegal plays) were caught and re-prompted.
- NFR-3: Each turn had a timeout to prevent indefinite hangs on unresponsive models.

## Dependencies

- Game server REST API (PRD-002) for state polling
- MQTT messaging (PRD-001) for move publication
- Provider API keys configured in environment

## Related Documents

- [PRD-002: Game Server REST API](002-game-server-rest-api.md)
- [PRD-003: Game State Machine](003-game-state-machine.md)
- [PRD-001: MQTT PubSub Messaging](001-mqtt-pubsub-messaging.md)
