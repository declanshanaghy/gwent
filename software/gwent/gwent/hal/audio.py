#!/usr/bin/env python3

"""
Audio Module for Gwent
This module provides audio playback functionality for the Gwent game.
"""

from __future__ import annotations

import os
import threading
import time
import pygame
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union, TypedDict

# Import the logging module
from ..utils.logging import get_logger, INFO, DEBUG, WARNING, ERROR, VERBOSE

# Get a logger for this module
logger = get_logger("gwent.hal.audio")

class FileInfo(TypedDict):
    path: str
    size: int
    format: str
    filename: str

class PerformanceMeasurement(TypedDict):
    time: float
    cpu: float
    memory: float
    playing: bool

class AudioPlayer:
    """
    Audio player class for Gwent.
    Uses pygame for audio playback in a separate thread.
    """
    
    def __init__(self) -> None:
        """
        Initialize the audio player.
        """
        self.initialized = False
        self.playing = False
        self.current_thread = None
        
        # Initialize pygame mixer with optimized settings for Raspberry Pi
        try:
            # Use a larger buffer size (4096) to reduce CPU load and prevent stuttering
            # Set frequency to 44100Hz for better quality
            # Use 16-bit audio (-16) and stereo (2 channels)
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            self.initialized = True
            logger.info("Audio system initialized successfully with optimized buffer settings")
        except Exception as e:
            logger.error(f"Error initializing audio system: {e}")
    
    def play_music(self, music_file: str, volume: float = 0.8, loop: bool = False) -> None:
        """
        Play a music file in a separate thread.
        
        Args:
            music_file (str): Path to the music file
            volume (float): Volume level (0.0 to 1.0)
            loop (bool): Whether to loop the music
        """
        if not self.initialized:
            logger.warning("Audio system not initialized")
            return
            
        # Stop any currently playing music
        self.stop_music()
        
        # Start a new thread to play the music
        self.current_thread = threading.Thread(
            target=self._play_music_thread,
            args=(music_file, volume, loop),
            daemon=True
        )
        self.current_thread.start()
    
    def _check_audio_file(self, file_path: str) -> Tuple[bool, str, Optional[FileInfo]]:
        """
        Check if an audio file is valid and get its format information.
        
        Args:
            file_path (str): Path to the audio file
            
        Returns:
            tuple: (is_valid, file_path, file_info)
        """
        # Check if file exists
        if not os.path.exists(file_path):
            # Try to find the file relative to the module
            module_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(module_dir, file_path)
            
            if not os.path.exists(file_path):
                logger.error(f"Audio file not found: {file_path}")
                return False, file_path, None
        
        # Check file size to ensure it's not empty
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.error(f"Audio file is empty: {file_path}")
            return False, file_path, None
            
        # Get file extension to check format
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Check if file format is supported
        supported_formats = ['.mp3', '.wav', '.ogg']
        if file_ext not in supported_formats:
            logger.warning(f"Audio file format {file_ext} may not be optimal. Supported formats: {supported_formats}")
        
        file_info = {
            'path': file_path,
            'size': file_size,
            'format': file_ext,
            'filename': os.path.basename(file_path)
        }
        
        return True, file_path, file_info
    
    def _play_music_thread(self, music_file: str, volume: float, loop: bool) -> None:
        """
        Thread function to play music.
        
        Args:
            music_file (str): Path to the music file
            volume (float): Volume level (0.0 to 1.0)
            loop (bool): Whether to loop the music
        """
        try:
            # Check if file is valid
            is_valid, music_file, file_info = self._check_audio_file(music_file)
            if not is_valid:
                return
            
            logger.info(f"Loading music file: {music_file}")
            logger.debug(f"Music file size: {file_info['size']} bytes, format: {file_info['format']}")
            
            # Load and play the music
            try:
                pygame.mixer.music.load(music_file)
                logger.debug(f"Successfully loaded music file")
            except pygame.error as pe:
                logger.error(f"Pygame error loading music file: {pe}")
                return
                
            pygame.mixer.music.set_volume(volume)
            logger.debug(f"Set volume to {volume}")
            
            loop_count = -1 if loop else 0  # -1 means infinite loop
            pygame.mixer.music.play(loop_count)
            logger.info(f"Started music playback with loop={loop}")
            
            self.playing = True
            
            # Keep the thread alive while music is playing
            # Use a shorter sleep interval (0.05s) for more responsive playback
            # This helps prevent stuttering by checking the playback state more frequently
            while pygame.mixer.music.get_busy() and self.playing:
                time.sleep(0.05)
                
        except Exception as e:
            logger.error(f"Error playing music: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            self.playing = False
    
    def play_sound(self, sound_file: str, volume: float = 1.0) -> None:
        """
        Play a sound effect.
        
        Args:
            sound_file (str): Path to the sound file
            volume (float): Volume level (0.0 to 1.0)
        """
        if not self.initialized:
            logger.warning("Audio system not initialized")
            return
            
        try:
            # Check if file is valid
            is_valid, sound_file, file_info = self._check_audio_file(sound_file)
            if not is_valid:
                return
            
            # Load and play the sound
            sound = pygame.mixer.Sound(sound_file)
            sound.set_volume(volume)
            
            # Set buffer size for sound playback
            # This can help reduce stuttering for sound effects
            if hasattr(sound, 'set_buffer'):
                sound.set_buffer(4096)
                
            sound.play()
            logger.debug(f"Playing sound: {file_info['filename']} (Volume: {volume})")
        except Exception as e:
            logger.error(f"Error playing sound: {e}")
    
    def stop_music(self) -> None:
        """
        Stop any currently playing music.
        """
        if not self.initialized:
            return
            
        if self.playing:
            pygame.mixer.music.stop()
            self.playing = False
            
            # Wait for the thread to finish
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread.join(timeout=1.0)
                self.current_thread = None
    
    def is_music_playing(self) -> bool:
        """
        Check if music is currently playing.
        
        Returns:
            bool: True if music is playing, False otherwise
        """
        if not self.initialized:
            return False
            
        return self.playing and pygame.mixer.music.get_busy()
    
    def monitor_performance(self, duration: int = 5) -> Optional[Dict[str, Any]]:
        """
        Monitor CPU usage during audio playback.
        This is useful for diagnosing stuttering issues.
        
        Args:
            duration (int): Duration to monitor in seconds
            
        Returns:
            dict: Performance metrics
        """
        try:
            import psutil
            process = psutil.Process(os.getpid())
            
            # Start monitoring
            logger.info(f"Monitoring audio performance for {duration} seconds...")
            
            # Take measurements
            measurements: List[PerformanceMeasurement] = []
            start_time = time.time()
            end_time = start_time + duration
            
            while time.time() < end_time:
                cpu_percent = process.cpu_percent()
                memory_mb = process.memory_info().rss / (1024 * 1024)
                
                measurements.append({
                    'time': time.time() - start_time,
                    'cpu': cpu_percent,
                    'memory': memory_mb,
                    'playing': pygame.mixer.music.get_busy() if self.initialized else False
                })
                
                time.sleep(0.5)
            
            # Calculate averages
            avg_cpu = sum(m['cpu'] for m in measurements) / len(measurements)
            avg_memory = sum(m['memory'] for m in measurements) / len(measurements)
            
            results = {
                'avg_cpu': avg_cpu,
                'avg_memory': avg_memory,
                'measurements': measurements,
                'mixer_settings': pygame.mixer.get_init() if self.initialized else None
            }
            
            logger.info(f"Audio performance: Avg CPU: {avg_cpu:.1f}%, Avg Memory: {avg_memory:.1f}MB")
            return results
            
        except ImportError:
            logger.warning("psutil not available, cannot monitor performance")
            return None
    
    def cleanup(self) -> None:
        """
        Clean up the audio player.
        """
        self.stop_music()
        
        if self.initialized:
            pygame.mixer.quit()
            self.initialized = False