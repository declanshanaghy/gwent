# ADR 008: Multi-Provider TTS with Faction-Aware Voices

## Status

Accepted

## Context

The game announces card plays, round results, and game events via text-to-speech. Different deployment environments have different capabilities: the Pi may be offline (no cloud APIs), dev machines may lack local TTS, and demo setups want high-quality voices. Each Gwent faction should have a distinct voice personality to enhance immersion.

## Decision

- Define a `TTSProvider` abstract base class in `gwent-shared` with a `synthesize(text, faction, dest)` method.
- Implement concrete providers:
  - `GTTSProvider` — Google TTS (free, requires internet)
  - `OpenAIProvider` — OpenAI TTS API (high quality, paid)
  - `ElevenLabsProvider` — ElevenLabs API (best quality, paid)
  - `PiperProvider` — local neural TTS (offline, runs on Pi)
  - `SayProvider` — macOS `say` command (dev machines, also has `speak_direct()`)
  - `NoneProvider` — silent, for testing
- Provider is selected at startup via configuration.
- Each provider maps factions to specific voices (e.g., Monsters gets a deeper voice, Nilfgaard gets a regal tone).
- TTS lives in `gwent-shared` package — no hardware dependencies, usable by both server and TUI.

## Consequences

### Positive
- Works offline with Piper or Say; works with cloud quality when available.
- Faction-specific voices add personality without game logic changes.
- Providers are hot-swappable — change provider without restarting.
- Shared package means TUI can also generate speech independently.

### Negative
- Cloud providers add latency (0.5-2s) and cost per utterance.
- Piper model files are large (~100MB per voice).

### Risks
- API key management for cloud providers; keys must be in environment variables.
- Voice quality varies significantly between providers.

## Related
- `software/gwent-shared/gwent_shared/tts/base.py`
- `software/gwent-shared/gwent_shared/tts/`
- [ADR 001: Audio and Menu Subsystems](001-audio-and-menu-subsystems.md)
