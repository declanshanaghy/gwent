#!/usr/bin/env python3

"""
RFID Reader Module for Gwent
This module provides an interface to the MFRC522 RFID reader.
"""

import time
import threading
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

class RFIDReader:
    """
    Class to handle RFID card reading and writing.
    Uses the MFRC522 RFID reader connected via SPI.
    """
    
    def __init__(self, callback=None):
        """
        Initialize the RFID reader.
        
        Args:
            callback (callable, optional): Function to call when a card is detected.
                The callback will receive the card ID and text as arguments.
        """
        self.reader = SimpleMFRC522()
        self.callback = callback
        self.running = False
        self.thread = None
    
    def read(self, timeout=None):
        """
        Read a card and return its ID and text.
        This is a blocking call that waits for a card to be presented.
        
        Args:
            timeout (float, optional): Maximum time to wait for a card in seconds.
                If None, wait indefinitely.
        
        Returns:
            tuple: (card_id, text) if a card is read, or (None, None) on timeout.
        """
        try:
            # Set a timeout if specified
            if timeout is not None:
                start_time = time.time()
                while time.time() - start_time < timeout:
                    # Check if a card is present
                    try:
                        id, text = self.reader.read_no_block()
                        if id is not None:
                            return id, text
                        time.sleep(0.1)
                    except Exception:
                        time.sleep(0.1)
                return None, None
            else:
                # No timeout, block until a card is read
                return self.reader.read()
        except Exception as e:
            print(f"Error reading RFID card: {e}")
            return None, None
    
    def write(self, text):
        """
        Write text to a card.
        This is a blocking call that waits for a card to be presented.
        
        Args:
            text (str): Text to write to the card.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self.reader.write(text)
            return True
        except Exception as e:
            print(f"Error writing to RFID card: {e}")
            return False
    
    def start_monitoring(self):
        """
        Start a background thread to monitor for cards.
        When a card is detected, the callback function is called.
        """
        if self.thread is not None and self.thread.is_alive():
            return  # Already running
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_thread)
        self.thread.daemon = True
        self.thread.start()
    
    def stop_monitoring(self):
        """
        Stop the background monitoring thread.
        """
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
    
    def _monitor_thread(self):
        """
        Background thread function to monitor for cards.
        """
        last_id = None
        
        while self.running:
            try:
                # Non-blocking read
                id, text = self.reader.read_no_block()
                
                if id is not None and id != last_id:
                    last_id = id
                    if self.callback is not None:
                        self.callback(id, text)
                
                # Small delay to prevent CPU hogging
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in RFID monitoring thread: {e}")
                time.sleep(0.5)  # Longer delay on error
    
    def cleanup(self):
        """
        Clean up GPIO resources.
        """
        self.stop_monitoring()
        # No need to call GPIO.cleanup() as SimpleMFRC522 handles this