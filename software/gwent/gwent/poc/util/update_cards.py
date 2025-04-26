#!/usr/bin/env python3
import json
import os
import re
import glob

def update_card_files():
    """
    Update all card JSON files:
    1. Remove the number suffix from weather card names
    2. Remove the content_id field from all cards
    """
    # Get the base directory for cards
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                          '..', '..', '..', '..', 'data', 'cards'))
    
    # Regular expressions for weather card names
    patterns = [
        (r'Biting Frost: \d+', 'Biting Frost'),
        (r'Torrential Rain: \d+', 'Torrential Rain'),
        (r'Impenetrable Fog: \d+', 'Impenetrable Fog'),
        (r'Clear Weather: \d+', 'Clear Weather')
    ]
    
    # Count of updated files
    updated_count = 0
    
    # Walk through all faction directories
    for faction_dir in os.listdir(base_dir):
        faction_path = os.path.join(base_dir, faction_dir)
        if os.path.isdir(faction_path):
            # Process all JSON files in the faction directory
            for json_file in glob.glob(os.path.join(faction_path, "*.json")):
                try:
                    # Read the card data
                    with open(json_file, 'r') as f:
                        card_data = json.load(f)
                    
                    # Track if we need to update this file
                    updated = False
                    
                    # Remove content_id if present
                    if 'content_id' in card_data:
                        del card_data['content_id']
                        updated = True
                    
                    # Update weather card names
                    if 'name' in card_data:
                        original_name = card_data['name']
                        for pattern, replacement in patterns:
                            if re.match(pattern, original_name):
                                card_data['name'] = replacement
                                updated = True
                                break
                    
                    # Write the updated data back if changes were made
                    if updated:
                        with open(json_file, 'w') as f:
                            json.dump(card_data, f, indent=4)
                        updated_count += 1
                        print(f"Updated {json_file}")
                
                except Exception as e:
                    print(f"Error processing {json_file}: {e}")
    
    print(f"Updated {updated_count} card files")

if __name__ == "__main__":
    update_card_files()