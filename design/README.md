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
- [ADR-001](ADR/001-audio-and-menu-subsystems.md): Audio and Menu Subsystems Implementation
- [ADR-002](ADR/002-physical-interface-implementation.md): Physical Interface Implementation with Rotary Encoder and OLED Display

## Design Documentation

The following documents provide additional design specifications:

### PDF Documents
- [GwentPubSub.pdf](GwentPubSub.pdf): Describes the publish-subscribe architecture used for communication between components
- [GwentGameStages.pdf](GwentGameStages.pdf): Details the game stages and state transitions in the Gwent Companion system

### Mermaid Diagrams
- [GwentPubSub.md](GwentPubSub.md): Interactive Mermaid diagram of the publish-subscribe architecture with component descriptions
- [MermaidStyleGuide.md](MermaidStyleGuide.md): Standard styling guide for all mermaid diagrams in the project

### Project Branding
- [logo/](logo/): Contains the Gwent Companion logo in various formats
  - [logo_generator.html](logo/logo_generator.html): Interactive logo generator with download functionality
  - [logo_generator_simple.html](logo/logo_generator_simple.html): Simplified logo generator with SVG export option
  - [logo_README.md](logo/logo_README.md): Documentation for using and customizing the logo

## Style Guidelines

All design documentation in this project follows the [Design Documentation Style Guide](DesignDocumentationStyleGuide.md). This guide outlines the visual style, component representation, layout organization, and documentation structure for creating consistent and readable design documentation.

All mermaid diagrams must follow the standardized styling defined in the [Mermaid Style Guide](MermaidStyleGuide.md) to ensure visual consistency across all project documentation.

The project logo and branding materials in the [logo/](logo/) directory follow these style guidelines, using the same color scheme (#6d1a36 burgundy and #d4af37 gold) and visual elements (cards, RFID technology, Raspberry Pi) to maintain a consistent brand identity.
