# ADR 001: Audio and Menu Subsystems Implementation

## Status

Accepted

## Context

The Gwent Companion project requires a user interface that allows players to interact with the device through physical controls and provides audio feedback during gameplay. Previously, audio functionality was controlled through an environment variable (`GWENT_AUDIO_ENABLED`), which was inflexible and required system configuration changes to modify at runtime.

Additionally, the project needed a structured way for users to navigate through options and settings using the physical interface (rotary encoder and buttons). This required a menu system that could:
- Display hierarchical options on the OLED display
- Process input from the rotary encoder for navigation
- Execute actions when menu items are selected
- Provide a consistent user experience across different parts of the application

The previous approach lacked:
- Dynamic control of audio settings during runtime
- A centralized way to manage audio state across the application
- A structured menu system for user interaction
- Integration between physical controls and on-screen options

## Decision

We have implemented an integrated audio management system and menu system with the following components:

### 1. Audio State Management

- **AudioStateManager**: A singleton class that centralizes audio state management across the application
  - Provides methods to enable/disable audio
  - Tracks the current audio state
  - Replaces the previous environment variable approach
  - Integrates with AudioPlayer for actual audio playback

- **Audio Control API**:
  - Simple functions to check audio state: `is_audio_enabled()`
  - Methods to enable/disable audio: `enable_audio()`, `disable_audio()`
  - Functions to control music and sound playback

### 2. Menu System

- **MenuItem Class**: Represents individual menu options
  - Contains text to display
  - Stores an action (function) to execute when selected
  - Tracks enabled/disabled state

- **MenuSystem Class**: Manages the collection of menu items
  - Handles navigation between items
  - Processes selection events
  - Renders the menu on the display
  - Manages the menu's lifecycle (start/stop)

- **Integration Features**:
  - Display integration with methods for rendering menus
  - Rotary encoder integration for navigation and selection
  - Datetime display capabilities
  - Support for hierarchical (nested) menus

### 3. Implementation Details

- Removed `GWENT_AUDIO_ENABLED` environment variable from service file and scripts
- Updated main.py to use the new AudioStateManager instead of environment variable
- Added comprehensive menu documentation in software/gwent/docs/menu_system.md
- Created test scripts to verify functionality:
  - test_audio_state_manager.py - Tests basic functionality
  - test_audio_playback.py - Tests integration with AudioPlayer
  - test_integrated_audio.py - Tests the full integrated audio system
- Added logging utilities to improve debugging and monitoring

## Consequences

### Positive

1. **Improved User Experience**: The menu system provides an intuitive interface for users to navigate through options and settings using the physical controls.

2. **Dynamic Audio Control**: Audio settings can be changed during runtime without requiring system configuration changes or application restarts.

3. **Centralized State Management**: The AudioStateManager provides a single source of truth for audio state across the application, making it easier to maintain consistency.

4. **Flexible Menu Structure**: The menu system supports hierarchical navigation, allowing for complex menu structures while maintaining a simple user interface.

5. **Better Integration**: Physical controls (rotary encoder and buttons) are now tightly integrated with the on-screen display, creating a cohesive user experience.

6. **Improved Testability**: The modular design of both systems makes them easier to test in isolation and as integrated components.

7. **Enhanced Debugging**: Added logging utilities improve the ability to debug and monitor the system during operation.

### Negative

1. **Increased Complexity**: The new systems add more complexity to the codebase, requiring developers to understand the singleton pattern and menu system architecture.

2. **Memory Usage**: The menu system requires additional memory to store menu items and state, which could be a concern on resource-constrained devices.

3. **Threading Considerations**: The menu system uses threading for datetime updates, which requires careful management to avoid race conditions.

4. **Learning Curve**: Developers will need to learn the new APIs for audio state management and menu creation/navigation.

5. **Potential Performance Impact**: Rendering menus and processing input events adds computational overhead, which could affect performance in resource-intensive scenarios.

## References

1. [Menu System Documentation](../software/gwent/docs/menu_system.md) - Comprehensive documentation of the menu system
2. [AudioStateManager Test](../test_audio_state_manager.py) - Test script for the AudioStateManager
3. [Audio Playback Test](../test_audio_playback.py) - Test script for audio playback integration
4. [Integrated Audio Test](../test_integrated_audio.py) - Test script for the full integrated audio system