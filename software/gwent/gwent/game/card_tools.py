#!/usr/bin/env python3

"""
Card Tools Module for Gwent
This module provides tools for reading and writing RFID cards.
"""

import json
import sys
import time
from ..hal.rfid import RFIDReader

def read_card():
    """
    Command-line tool to read a Gwent card.
    """
    print("=== Gwent Card Reader ===")
    print("Place a card on the RFID reader...")
    
    reader = RFIDReader()
    
    try:
        card_id, text = reader.read()
        
        if card_id is None:
            print("Error: Failed to read card.")
            return 1
        
        print(f"Card ID: {card_id}")
        
        try:
            # Try to parse the text as JSON
            card_data = json.loads(text)
            print("\nCard Data:")
            print(json.dumps(card_data, indent=2))
        except json.JSONDecodeError:
            # If not JSON, just print the raw text
            print(f"\nCard Text: {text}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        reader.cleanup()

def write_card():
    """
    Command-line tool to write a Gwent card.
    """
    print("=== Gwent Card Writer ===")
    
    # Check if a file was provided
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], 'r') as f:
                card_data = json.load(f)
            card_text = json.dumps(card_data)
        except Exception as e:
            print(f"Error reading card data from file: {e}")
            return 1
    else:
        # Interactive mode
        print("Enter card data (JSON format):")
        print("Example: {\"name\": \"Geralt of Rivia\", \"strength\": 10, \"ability\": \"hero\"}")
        
        try:
            card_text = input("> ")
            # Validate JSON
            json.loads(card_text)
        except json.JSONDecodeError:
            print("Error: Invalid JSON format.")
            return 1
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return 1
    
    print("\nPlace a card on the RFID reader to write data...")
    
    reader = RFIDReader()
    
    try:
        success = reader.write(card_text)
        
        if success:
            print("Card written successfully!")
            
            # Read back the card to verify
            print("\nVerifying card data...")
            time.sleep(1)  # Give some time before reading
            
            card_id, text = reader.read()
            
            if card_id is None:
                print("Warning: Could not verify card data.")
            else:
                print(f"Card ID: {card_id}")
                print(f"Card Data: {text}")
                
                if text == card_text:
                    print("Verification successful!")
                else:
                    print("Warning: Card data does not match what was written.")
            
            return 0
        else:
            print("Error: Failed to write card.")
            return 1
        
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        reader.cleanup()

if __name__ == "__main__":
    # This allows the module to be run directly
    if "read" in sys.argv[0]:
        sys.exit(read_card())
    else:
        sys.exit(write_card())