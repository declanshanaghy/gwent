#!/usr/bin/env python3

"""
Audio Diagnostic Tool for Gwent

This script performs comprehensive diagnostics on the audio system to identify
issues with audio playback. It tests both the older SFX system and the newer
AudioPlayer system, checks for missing files, initialization issues, and
performance problems.
"""

import os
import sys
import time
import logging
import argparse
import traceback
from typing import Dict, Any, Optional, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("audio_diagnostic")

def check_pygame_installation() -> bool:
    """Check if pygame is properly installed and can be imported."""
    logger.info("Checking pygame installation...")
    try:
        import pygame
        logger.info(f"Pygame version: {pygame.version.ver}")
        return True
    except ImportError as e:
        logger.error(f"Failed to import pygame: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error importing pygame: {e}")
        return False

def check_audio_files() -> bool:
    """Check if required audio files exist."""
    logger.info("Checking audio files...")
    
    # Define paths to check
    module_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    paths_to_check = [
        os.path.join(module_dir, "hal", "music", "music1.mp3"),
        os.path.join(module_dir, "hal", "effects")
    ]
    
    all_files_exist = True
    for path in paths_to_check:
        if os.path.isdir(path):
            logger.info(f"Directory exists: {path}")
            # Check if directory has any files
            files = os.listdir(path)
            if not files:
                logger.warning(f"Directory is empty: {path}")
                all_files_exist = False
            else:
                logger.info(f"Found {len(files)} files in {path}")
                # List the first 5 files
                for i, file in enumerate(files[:5]):
                    logger.info(f"  - {file}")
                if len(files) > 5:
                    logger.info(f"  - ... and {len(files) - 5} more")
        elif os.path.exists(path):
            logger.info(f"File exists: {path}")
            # Check file size
            size = os.path.getsize(path)
            logger.info(f"  - Size: {size / 1024:.1f} KB")
        else:
            logger.error(f"Path does not exist: {path}")
            all_files_exist = False
    
    return all_files_exist

def test_pygame_mixer_initialization() -> bool:
    """Test if pygame.mixer can be initialized."""
    logger.info("Testing pygame.mixer initialization...")
    try:
        import pygame
        
        # Try different initialization parameters
        initialization_attempts = [
            {"frequency": 44100, "size": -16, "channels": 2, "buffer": 4096},
            {"frequency": 24000, "size": -16, "channels": 2},
            {"frequency": 22050, "size": -16, "channels": 1, "buffer": 2048},
        ]
        
        success = False
        for i, params in enumerate(initialization_attempts):
            try:
                logger.info(f"Attempt {i+1} with params: {params}")
                pygame.mixer.quit()  # Ensure mixer is not already initialized
                pygame.mixer.init(**params)
                
                # Check if initialization was successful
                if pygame.mixer.get_init():
                    logger.info(f"Mixer initialized successfully with params: {pygame.mixer.get_init()}")
                    success = True
                    break
                else:
                    logger.warning("Mixer initialization returned but get_init() is None")
            except Exception as e:
                logger.error(f"Failed to initialize mixer with params {params}: {e}")
        
        if not success:
            logger.error("All mixer initialization attempts failed")
        
        return success
    except Exception as e:
        logger.error(f"Unexpected error testing mixer: {e}")
        return False

def test_audio_state_manager() -> bool:
    """Test the AudioStateManager."""
    logger.info("Testing AudioStateManager...")
    try:
        from gwent.logical.audio_manager import AudioStateManager, audio_state
        
        # Check if audio is enabled
        logger.info(f"Audio enabled: {audio_state.audio_enabled}")
        
        # Initialize audio player
        audio_state.initialize()
        
        # Check if audio player was initialized
        if audio_state._audio_player and audio_state._audio_player.initialized:
            logger.info("AudioPlayer initialized successfully")
            return True
        else:
            logger.error("AudioPlayer initialization failed")
            return False
    except Exception as e:
        logger.error(f"Error testing AudioStateManager: {e}")
        logger.error(traceback.format_exc())
        return False

def test_audio_playback() -> bool:
    """Test actual audio playback."""
    logger.info("Testing audio playback...")
    try:
        from gwent.logical.audio_manager import audio_state
        
        # Find music file
        module_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        music_path = os.path.join(module_dir, "hal", "music", "music1.mp3")
        
        if not os.path.exists(music_path):
            logger.error(f"Music file not found: {music_path}")
            return False
        
        # Ensure audio is enabled
        audio_state.enable_audio()
        logger.info(f"Audio enabled state: {audio_state.audio_enabled}")
        
        # Play music
        logger.info(f"Attempting to play music: {music_path}")
        audio_state.play_music(music_path, volume=0.7, loop=True)
        
        # Wait a moment for playback to start
        time.sleep(1)
        
        # Check if music is playing
        if audio_state._audio_player and audio_state._audio_player.is_music_playing():
            logger.info("Music is playing successfully")
            
            # Let it play for a few seconds
            logger.info("Letting music play for 3 seconds...")
            time.sleep(3)
            
            # Stop music
            audio_state.stop_music()
            logger.info("Music stopped")
            return True
        else:
            logger.error("Music is not playing")
            
            # Check if pygame mixer is busy
            import pygame
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                logger.info("pygame.mixer.music reports it is busy, but our is_music_playing() returned False")
            else:
                logger.info("pygame.mixer.music reports it is not busy")
            
            return False
    except Exception as e:
        logger.error(f"Error testing audio playback: {e}")
        logger.error(traceback.format_exc())
        return False

def test_sfx_system() -> bool:
    """Test the older SFX system."""
    logger.info("Testing SFX system...")
    try:
        import gwent.hal.sfx
        
        # Create SFX instance
        sfx = gwent.hal.sfx.instance()
        logger.info("SFX instance created")
        
        # Create a test message
        import gwent.messaging.sfx
        test_msg = gwent.messaging.sfx.Message.with_effect(gwent.messaging.sfx.EFFECT_CARD_READ)
        
        # Try to play an effect
        try:
            logger.info("Attempting to play effect...")
            duration = sfx.play_effect(test_msg)
            logger.info(f"Effect played, duration: {duration}")
            time.sleep(duration)  # Wait for effect to finish
            return True
        except Exception as e:
            logger.error(f"Error playing effect: {e}")
            return False
    except Exception as e:
        logger.error(f"Error testing SFX system: {e}")
        logger.error(traceback.format_exc())
        return False

def check_system_resources() -> bool:
    """Check system resources that might affect audio playback."""
    logger.info("Checking system resources...")
    try:
        import psutil
        
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        logger.info(f"CPU usage: {cpu_percent}%")
        
        # Get memory usage
        memory = psutil.virtual_memory()
        logger.info(f"Memory usage: {memory.percent}% (Available: {memory.available / (1024*1024):.1f} MB)")
        
        # Check if CPU usage is high
        if cpu_percent > 80:
            logger.warning("CPU usage is very high, which may affect audio playback")
        
        # Check if memory is low
        if memory.available < 100 * 1024 * 1024:  # Less than 100MB
            logger.warning("Available memory is very low, which may affect audio playback")
            
        return True
    except ImportError:
        logger.warning("psutil not available, skipping resource check")
        return True
    except Exception as e:
        logger.error(f"Error checking system resources: {e}")
        return False

def check_audio_conflicts() -> bool:
    """Check for potential conflicts between audio systems."""
    logger.info("Checking for audio system conflicts...")
    
    try:
        # Check if both audio systems are initialized
        import pygame
        
        # First check if pygame is already initialized
        if pygame.mixer.get_init():
            logger.warning("pygame.mixer is already initialized before any of our systems use it")
            logger.info(f"Current mixer settings: {pygame.mixer.get_init()}")
        
        # Initialize the newer system
        from gwent.logical.audio_manager import audio_state
        audio_state.initialize()
        
        # Now try to initialize the older system
        import gwent.hal.sfx
        sfx = gwent.hal.sfx.instance()
        
        # Check mixer settings after both systems are initialized
        if pygame.mixer.get_init():
            logger.info(f"Final mixer settings: {pygame.mixer.get_init()}")
            
            # Compare with expected settings for each system
            newer_settings = (44100, -16, 2, 4096)  # frequency, size, channels, buffer
            older_settings = (24000, -16, 2)  # frequency, size, channels
            
            current_settings = pygame.mixer.get_init()
            
            if current_settings[0] == newer_settings[0]:
                logger.info("Mixer is using the newer system's frequency settings")
            elif current_settings[0] == older_settings[0]:
                logger.info("Mixer is using the older system's frequency settings")
                logger.warning("This may cause issues with the newer audio system")
            
        return True
    except Exception as e:
        logger.error(f"Error checking audio conflicts: {e}")
        logger.error(traceback.format_exc())
        return False

def run_diagnostics(args) -> Dict[str, bool]:
    """Run all diagnostic tests."""
    logger.info("Starting audio diagnostic tests")
    
    results = {
        "pygame_installation": check_pygame_installation(),
        "audio_files": check_audio_files(),
        "system_resources": check_system_resources(),
    }
    
    # Only run these tests if pygame was successfully installed
    if results["pygame_installation"]:
        results["pygame_mixer"] = test_pygame_mixer_initialization()
        results["audio_conflicts"] = check_audio_conflicts()
        
        # Test the newer audio system
        results["audio_state_manager"] = test_audio_state_manager()
        if results["audio_state_manager"]:
            results["audio_playback"] = test_audio_playback()
        
        # Test the older SFX system
        results["sfx_system"] = test_sfx_system()
    
    # Print summary
    logger.info("\n=== DIAGNOSTIC RESULTS ===")
    for test, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test}: {status}")
    
    # Provide recommendations based on results
    logger.info("\n=== RECOMMENDATIONS ===")
    
    if not results.get("pygame_installation", False):
        logger.info("- Reinstall pygame: 'pip install pygame==2.1.2'")
    
    if not results.get("audio_files", False):
        logger.info("- Check that audio files exist in the correct locations")
        logger.info("  - Music files should be in gwent/hal/music/")
        logger.info("  - Effect files should be in gwent/hal/effects/")
    
    if not results.get("pygame_mixer", False):
        logger.info("- Check for issues with audio hardware or drivers")
        logger.info("- Try running with different pygame.mixer initialization parameters")
    
    if not results.get("audio_state_manager", False):
        logger.info("- Check for errors in the AudioStateManager initialization")
        logger.info("- Ensure the audio_state singleton is properly initialized")
    
    if not results.get("audio_playback", False) and results.get("audio_state_manager", False):
        logger.info("- Audio system is initialized but playback failed")
        logger.info("- Check if audio is enabled: audio_state.audio_enabled should be True")
        logger.info("- Check if the music file exists and is valid")
    
    if not results.get("sfx_system", False):
        logger.info("- Check for errors in the SFX system initialization")
        logger.info("- Ensure effect files exist and are valid")
    
    if results.get("audio_conflicts", False) == False:
        logger.info("- There may be conflicts between the older and newer audio systems")
        logger.info("- Consider using only one audio system at a time")
    
    return results

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Audio diagnostic tool for Gwent")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        run_diagnostics(args)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())