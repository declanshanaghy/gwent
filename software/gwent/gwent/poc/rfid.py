#!/usr/bin/env python3
"""
Simple test script for RFID card scanning using the MFRC522 module.
This script will continuously scan for RFID cards and print the ID and text content
when a card is detected.
"""

import time
import signal
import sys
import os
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

# Global variables
reader = None
running = True
gpio_initialized = False

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully"""
    global running, gpio_initialized, reader
    print("\nExiting RFID scanner...")
    running = False
    if reader:
        # Ensure the reader is properly closed
        try:
            reader._mfrc522.Close_MFRC522()
        except:
            pass
    if gpio_initialized:
        try:
            GPIO.cleanup()
        except:
            pass
    sys.exit(0)

def run():
    """Run the RFID scanner"""
    global reader, running, gpio_initialized
    
    print("Starting RFID scanner...")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Set GPIO mode before initializing the reader
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        
        # Initialize the RFID reader
        reader = SimpleMFRC522()
        gpio_initialized = True
        
        print("RFID reader initialized successfully")
        print("Place an RFID card near the reader")
        print("Press Ctrl+C to exit")
        print("Waiting for cards...")
        
        # Main loop
        while running:
            try:
                # Read card
                id, text = reader.read()
                
                # Print the results
                print("-" * 50)
                print(f"Card detected!")
                print(f"ID: {id}")
                print(f"Text: {text.strip()}")
                print("-" * 50)
                
                # Wait a bit before scanning again
                time.sleep(1)
                
            except Exception as e:
                print(f"Error reading card: {e}")
                time.sleep(0.5)
                
    except Exception as e:
        print(f"Error initializing RFID reader: {e}")
        print(f"Details: {str(e)}")
        if "No such file or directory" in str(e):
            print("This may be because the MFRC522 hardware is not connected")
            print("or the SPI interface is not enabled on your Raspberry Pi.")
            print("To enable SPI: sudo raspi-config > Interface Options > SPI > Enable")
        running = False
        sys.exit(1)
    finally:
        if reader:
            # Ensure the reader is properly closed
            try:
                reader._mfrc522.Close_MFRC522()
            except:
                pass
        if gpio_initialized:
            try:
                GPIO.cleanup()
            except:
                pass

if __name__ == "__main__":
    run()