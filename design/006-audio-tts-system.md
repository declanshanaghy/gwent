# PRD-006: Audio and TTS System

## Overview

The audio system provided text-to-speech announcements and sound effects to enhance gameplay. Multiple TTS providers were supported with faction-aware voice selection. A background worker thread handled async synthesis and playback to avoid blocking the game loop.

## Requirements

### Functional Requirements

- FR-1: TTS providers included GTTS (Google), OpenAI, ElevenLabs, Piper (local/offline), and Say (macOS/Linux espeak).
- FR-2: Each faction was assigned a distinct voice to differentiate player announcements.
- FR-3: SFX playback selected a random WAV file from categorized subdirectories under sfx/.
- FR-4: Background music played random MP3 files from the music/ directory.
- FR-5: An announcement worker thread queued TTS requests and handled async synthesis followed by playback.
- FR-6: pygame mixer managed audio channels: channel 0 for SFX, channel 1 for TTS.
- FR-7: TTS audio was cached to disk to avoid re-synthesizing repeated phrases.
- FR-8: External clients could register as TTS providers via `PUT /client-tts`, disabling server-side audio.
- FR-9: Announcement completion callbacks notified the game when speech finished.

### Non-Functional Requirements

- NFR-1: Piper provided offline TTS capability when network providers were unavailable.
- NFR-2: TTS synthesis and playback did not block the main game thread.
- NFR-3: Audio gracefully degraded (logged warnings, continued without sound) if pygame or audio hardware was unavailable.

## Dependencies

- pygame mixer
- Provider-specific libraries/APIs (gtts, openai, elevenlabs, piper-tts)
- MQTT for sfx trigger messages (PRD-001)

## Related Documents

- [PRD-001: MQTT PubSub Messaging](001-mqtt-pubsub-messaging.md)
- [PRD-004: Hardware Abstraction Layer](004-hardware-abstraction-layer.md)
