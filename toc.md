# Gwent Companion Documentation

Welcome to the documentation for the Gwent Companion project, a Raspberry Pi-based digital companion for the physical card game Gwent from The Witcher III.

## Project Overview

- [README.md](README.md): Project overview, architecture diagram, and quick-start
- [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md): Hardware and environment setup

## Architecture

- [GwentArchitecture.md](design/GwentArchitecture.md): Comprehensive system architecture (server, TUI, game-loop, hardware, MQTT)
- [GwentGameStages.md](design/GwentGameStages.md): Game stage state machine and transitions
- [GwentPubSub.md](design/GwentPubSub.md): MQTT pub/sub messaging architecture
- [ThreadModel.md](design/ThreadModel.md): Threading model

## Game Design

- [GwentRules.md](design/GwentRules.md): Canonical game rules as implemented
- [GwentCardMechanics.md](design/GwentCardMechanics.md): Card abilities and mechanics
- [GwentFactions.md](design/GwentFactions.md): Faction descriptions and passive abilities
- [GwentLeaders.md](design/GwentLeaders.md): Leader cards and abilities

## Product Requirements

- [PRD-000](design/000-product-requirements.md): Product overview and core requirements
- [PRD-001](design/001-mqtt-pubsub-messaging.md): MQTT pub/sub messaging
- [PRD-002](design/002-game-server-rest-api.md): Game server REST API
- [PRD-003](design/003-game-state-machine.md): Game state machine
- [PRD-004](design/004-hardware-abstraction-layer.md): Hardware abstraction layer
- [PRD-005](design/005-terminal-dashboard.md): Terminal dashboard (gwent-tui)
- [PRD-006](design/006-audio-tts-system.md): Audio and TTS system
- [PRD-007](design/007-card-data-system.md): Card data system
- [PRD-008](design/008-deck-management.md): Deck management
- [PRD-009](design/009-game-recordings.md): Game recordings and replay
- [PRD-010](design/010-llm-game-orchestration.md): LLM game orchestration
- [PRD-011](design/011-card-capture-rfid.md): Card capture and RFID programming

## Architecture Decision Records

- [ADR-001](design/ADR/001-audio-and-menu-subsystems.md): Audio and menu subsystems
- [ADR-002](design/ADR/002-physical-interface-implementation.md): Physical interface (rotary encoder, OLED)
- [ADR-003](design/ADR/003-mqtt-pubsub-backbone.md): MQTT as messaging backbone
- [ADR-004](design/ADR/004-game-stage-state-machine.md): Stage-based state machine
- [ADR-005](design/ADR/005-rest-api-long-polling.md): REST API long-polling with ETag
- [ADR-006](design/ADR/006-hardware-abstraction-layer.md): Hardware abstraction layer
- [ADR-007](design/ADR/007-tui-rich-textual-dashboard.md): Rich/Textual TUI dashboard
- [ADR-008](design/ADR/008-multi-provider-tts.md): Multi-provider TTS with faction voices
- [ADR-009](design/ADR/009-card-json-ownership-model.md): Card JSON ownership model
- [ADR-010](design/ADR/010-llm-orchestration-architecture.md): LLM orchestration via HTTP + MQTT
- [ADR-011](design/ADR/011-game-recordings-replay.md): Game recordings and replay
- [ADR-012](design/ADR/012-rfid-card-capture-pipeline.md): RFID card capture pipeline

## Style Guidelines

- [DesignDocumentationStyleGuide.md](design/DesignDocumentationStyleGuide.md): Design documentation style
- [MermaidStyleGuide.md](design/MermaidStyleGuide.md): Mermaid diagram styling

## Software

- [Gwent Core](software/gwent/README.md): Game server package
- [Gwent TUI](software/gwent-tui/): Terminal dashboard
- [Gwent Shared](software/gwent-shared/): Shared utilities (TTS providers)
- [Menu System](software/gwent/docs/menu_system.md): Interactive menu system

### Proof of Concept

- [POC Overview](software/gwent/gwent/poc/README.md): Proof-of-concept scripts
  - [Diagnostic Tools](software/gwent/gwent/poc/diagnostic_tools/README.md)
  - [Display Tests](software/gwent/gwent/poc/display_tests/README.md)
  - [Input Tests](software/gwent/gwent/poc/input_tests/README.md)
  - [RFID Tests](software/gwent/gwent/poc/rfid_tests/README.md)

## Development

- [Scripts](scripts/README.md): Development scripts and utilities
- [MFRC522 Python](software/MFRC522-python/README.md): RFID reader library
