# Gwent Companion Design Documentation

This directory contains the design documentation for the Gwent Companion project, a physical-digital hybrid gaming system that enhances the traditional Gwent card game experience by combining physical RFID-enabled cards with a digital companion device.

## Directory Structure

- [ADR/](ADR/): Architecture Decision Records documenting significant architectural decisions
- [tasks/](tasks/): Detailed task specifications for implementing the Gwent Companion system

## Tasks

The [tasks/](tasks/) directory contains detailed specifications for each implementation task, organized in a structured format with consistent sections for description, priority, status, dependencies, details, and test strategy.

See the [tasks/000-index.md](tasks/000-index.md) file for an overview of all tasks, their dependencies, and implementation phases.

## Architecture Decision Records (ADRs)

The [ADR/](ADR/) directory contains Architecture Decision Records that document significant architectural decisions made during the project. Each ADR explains the context, decision, and consequences of a particular architectural choice.

Current ADRs include:
- [ADR-000](ADR/000-task-master-roo-code.md): Task Master Integration for AI-Driven Development
- [ADR-001](ADR/001-audio-and-menu-subsystems.md): Audio and Menu Subsystems Implementation
- [ADR-002](ADR/002-physical-interface-implementation.md): Physical Interface Implementation with Rotary Encoder and OLED Display

## PDF Documentation

The following PDF documents provide additional design specifications:

- [GwentPubSub.pdf](GwentPubSub.pdf): Describes the publish-subscribe architecture used for communication between components
- [GwentGameStages.pdf](GwentGameStages.pdf): Details the game stages and state transitions in the Gwent Companion system
