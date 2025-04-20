#!/usr/bin/env python3

"""
Mock RFID Reader Module for Gwent
This module provides a mock implementation of the RFID reader for development on non-Raspberry Pi systems.
"""

import time
import threading

class MockRFIDReader:
    """
    Mock class to simulate RFID card reading and writing.
    """
    
    def __init__(self, callback=None):
        """
        Initialize the mock RFID reader.
        
        Args:
            callback (callable, optional): Function to call when a card is detected.
                The callback will receive the card ID and text as arguments.
        """
        self.callback = callback
        self.running = False
        self.thread = None
    
    def read(self, timeout=None):
        """
        Simulate reading a card.
        
        Args:
            timeout (float, optional): Maximum time to wait for a card in seconds.
                If None, wait indefinitely.
        
        Returns:
            tuple: (card_id, text) if a card is read, or (None, None) on timeout.
        """
        print("Mock RFID: Simulating card read")
        return 12345, '{"name": "Mock Card", "strength": 5}'
    
    def write(self, text):
        """
        Simulate writing text to a card.
        
        Args:
            text (str): Text to write to the card.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        print(f"Mock RFID: Simulating card write with text: {text}")
        return True
    
    def start_monitoring(self):
        """
        Start a background thread to simulate monitoring for cards.
        """
        if self.thread is not None and self.thread.is_alive():
            return  # Already running
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_thread)
        self.thread.daemon = True
        self.thread.start()
        print("Mock RFID: Started monitoring")
    
    def stop_monitoring(self):
        """
        Stop the background monitoring thread.
        """
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
        print("Mock RFID: Stopped monitoring")
    
    def _monitor_thread(self):
        """
        Background thread function to simulate monitoring for cards.
        """
        print("Mock RFID: Monitoring thread started")
        
        while self.running:
            time.sleep(0.1)  # Just sleep, no actual monitoring
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.stop_monitoring()
        print("Mock RFID: Cleaned up")