#!/bin/bash
set -e

# Make sure we're on the menu-integration branch
git checkout menu-integration

# Soft reset to origin/master to unstage all changes
git reset --soft origin/master

# Create a new commit with all the changes
git commit -m "feat: implement menu system with audio state management

This commit implements a new integrated audio management system and menu system:

- Implemented menu system with hierarchical navigation and rotary encoder support
- Added comprehensive menu documentation in software/gwent/docs/menu_system.md
- Removed GWENT_AUDIO_ENABLED environment variable from service file and scripts
- Implemented AudioStateManager as a singleton class to manage audio state across the application
- Integrated AudioStateManager with AudioPlayer for actual audio playback
- Added methods to enable/disable audio and control music/sound playback
- Updated main.py to use the new AudioStateManager instead of environment variable
- Added test scripts to verify AudioStateManager functionality:
  * test_audio_state_manager.py - Tests basic functionality
  * test_audio_playback.py - Tests integration with AudioPlayer
  * test_integrated_audio.py - Tests the full integrated audio system
- Added logging utilities to improve debugging and monitoring

This change improves the system by:
1. Centralizing audio state management in a single class
2. Providing a cleaner API for audio control
3. Eliminating the need for environment variable configuration
4. Making audio state changes dynamic during runtime
5. Adding a comprehensive menu system for user interaction"

echo "Rebase and squash completed successfully!"