#!/usr/bin/env python3
import json
import os
import sys
import glob

def update_card_rfid(card_name, card_faction, rfid_id):
    """
    Update a card file with an RFID ID
    
    Args:
        card_name: The name of the card
        card_faction: The faction of the card
        rfid_id: The RFID ID to add to the card
    
    Returns:
        True if the card was updated, False otherwise
    """
    # Get the base directory for cards
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                          '..', '..', '..', '..', 'data', 'cards'))
    
    # Convert RFID ID to integer
    try:
        rfid_id = int(rfid_id)
    except ValueError:
        print(f"Error: RFID ID must be an integer: {rfid_id}")
        return False
    
    # Find the card file
    faction_dir = os.path.join(base_dir, card_faction)
    if not os.path.isdir(faction_dir):
        print(f"Error: Faction directory not found: {faction_dir}")
        return False
    
    # Search for the card file
    found = False
    for json_file in glob.glob(os.path.join(faction_dir, "*.json")):
        try:
            with open(json_file, 'r') as f:
                card_data = json.load(f)
                if card_data.get('name') == card_name and card_data.get('faction') == card_faction:
                    # Found the card, update it with the RFID ID
                    card_data['rfid'] = rfid_id
                    
                    # Write the updated card data back to the file
                    with open(json_file, 'w') as f:
                        json.dump(card_data, f, indent=4)
                    
                    print(f"Updated card file with RFID ID: {json_file}")
                    found = True
                    
                    # Verify the update
                    with open(json_file, 'r') as f:
                        updated_data = json.load(f)
                        if 'rfid' in updated_data and updated_data['rfid'] == rfid_id:
                            print(f"Verified RFID ID was added to file: {json_file}")
                        else:
                            print(f"Failed to verify RFID ID in file: {json_file}")
                            return False
                    
                    break
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
    
    if not found:
        print(f"Error: Card not found: {card_name} ({card_faction})")
        return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python update_card_rfid.py <card_name> <card_faction> <rfid_id>")
        sys.exit(1)
    
    card_name = sys.argv[1]
    card_faction = sys.argv[2]
    rfid_id = sys.argv[3]
    
    if update_card_rfid(card_name, card_faction, rfid_id):
        print(f"Successfully updated card {card_name} ({card_faction}) with RFID ID {rfid_id}")
        sys.exit(0)
    else:
        print(f"Failed to update card {card_name} ({card_faction}) with RFID ID {rfid_id}")
        sys.exit(1)