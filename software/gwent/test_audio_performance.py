#!/usr/bin/env python3

"""
Test script to monitor performance during audio playback.
This script plays music and monitors CPU usage and other performance metrics.
"""

from __future__ import annotations

import os
import time
import psutil
import threading
from typing import List, Optional, Union, Tuple
import pygame
from gwent.hal.audio import AudioPlayer

def monitor_performance(duration: int = 10, interval: float = 0.5) -> None:
    """
    Monitor system performance metrics during audio playback.
    
    Args:
        duration (int): Duration to monitor in seconds
        interval (float): Interval between measurements in seconds
    """
    process = psutil.Process(os.getpid())
    start_time = time.time()
    end_time = start_time + duration
    
    # Print header
    print("\nPerformance Monitoring:")
    print("Time(s) | CPU(%) | Memory(MB) | Threads | Status")
    print("-" * 50)
    
    while time.time() < end_time:
        # Get metrics
        cpu_percent = process.cpu_percent()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        thread_count = len(process.threads())
        
        # Get pygame mixer status
        if pygame.mixer.get_init():
            if pygame.mixer.music.get_busy():
                status = "Playing"
            else:
                status = "Idle"
        else:
            status = "Not initialized"
        
        # Print metrics
        elapsed = time.time() - start_time
        print(f"{elapsed:.1f} | {cpu_percent:.1f} | {memory_mb:.1f} | {thread_count} | {status}")
        
        # Sleep for the interval
        time.sleep(interval)

def main() -> None:
    """Main function to test audio playback performance."""
    print("Audio Performance Test")
    print("=====================")
    
    # Find music file
    music_file = "music1.mp3"
    module_dir = os.path.dirname(os.path.abspath(__file__))
    music_path = os.path.join(module_dir, "gwent", "hal", "music", music_file)
    
    if not os.path.exists(music_path):
        print(f"Music file not found at {music_path}, trying alternative paths")
        
        # Try to find it in the package directory
        import gwent
        package_dir = os.path.dirname(os.path.dirname(gwent.__file__))
        music_path = os.path.join(package_dir, "gwent", "hal", "music", music_file)
        
        if not os.path.exists(music_path):
            print(f"Music file not found at any location: {music_file}")
            return
    
    print(f"Found music file at: {music_path}")
    
    # Initialize pygame mixer with different buffer sizes to test
    print("\nTesting with default pygame mixer settings:")
    pygame.mixer.init()
    print(f"Mixer settings: {pygame.mixer.get_init()}")
    pygame.mixer.quit()
    
    # Test with different buffer sizes
    buffer_sizes: List[int] = [512, 1024, 2048, 4096]
    for buffer_size in buffer_sizes:
        print(f"\nTesting with buffer size: {buffer_size}")
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=buffer_size)
        print(f"Mixer settings: {pygame.mixer.get_init()}")
        
        # Create audio player
        audio_player = AudioPlayer()
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(
            target=monitor_performance,
            args=(10, 0.5),  # Monitor for 10 seconds with 0.5s interval
            daemon=True
        )
        monitor_thread.start()
        
        # Play music
        print(f"Playing music with buffer size {buffer_size}...")
        audio_player.play_music(music_path, volume=0.5, loop=True)
        
        # Wait for monitoring to complete
        monitor_thread.join()
        
        # Clean up
        audio_player.stop_music()
        audio_player.cleanup()
        pygame.mixer.quit()
        
        # Wait a moment before next test
        time.sleep(1)
    
    print("\nPerformance test completed.")

if __name__ == "__main__":
    main()