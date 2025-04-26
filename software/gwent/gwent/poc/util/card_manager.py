import json
import logging
import os
import signal
import sys
import time
import threading
import hashlib
import glob
import re
from typing import Dict, List, Tuple, Optional, Any, Union

import gwent.log
import gwent.game
import gwent.messaging.base
import gwent.cards.all
import gwent.messaging.card
import gwent.cards.util
import gwent.hal.rfid

# Type aliases
CardData = Dict[str, Any]
FilePath = str

class CardManager(gwent.game.BaseComponent):
    def __init__(self, log_verbose: bool = False):
        super().__init__(log_verbose=log_verbose)
        self._stop_event = threading.Event()
        self.cards_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                                     '..', '..', '..', '..', 'data', 'cards'))
        
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful exit"""
        def signal_handler(sig: int, frame: Any) -> None:
            self._log.info(f'Received exit signal {signal.Signals(sig).name}...')
            self._stop_event.set()
            
        for s in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                  signal.SIGQUIT, signal.SIGTERM):
            signal.signal(s, signal_handler)

    def read_rfid_card(self) -> Optional[gwent.messaging.card.Message]:
        """Read a card using the RFID reader"""
        print("\nPlease place a card on the reader...")
        self._log.info("Please place a card on the reader...")
        reader = gwent.hal.rfid.instance()

        card: Optional[gwent.messaging.card.Message] = None
        while card is None and not self._stop_event.is_set():
            card = reader.read_card()
            if card is None:
                # Small delay to prevent CPU hogging
                time.sleep(0.1)
        
        if card is not None:
            # Log card information
            card_info: Dict[str, Any] = {'action': 'got card', 'rfid': card.rfid}
            
            # Add name and faction if available
            if hasattr(card, 'name'):
                card_info['name'] = card.name
            if hasattr(card, 'faction'):
                card_info['faction'] = card.faction
            
            # Log content_id if available
            if hasattr(card, 'instance') and 'content_id' in card.instance:
                card_info['content_id'] = card.instance['content_id']
                
            self._log.info(card_info)

        return card

    def find_card_in_database(self, rfid: int) -> Tuple[Optional[CardData], Optional[FilePath]]:
        """Find a card in the database by RFID"""
        self._log.info(f"Searching for card with RFID: {rfid}")
        
        # Search through all faction directories
        for faction_dir in os.listdir(self.cards_dir):
            faction_path = os.path.join(self.cards_dir, faction_dir)
            if os.path.isdir(faction_path):
                # Search through all JSON files in the faction directory
                for json_file in glob.glob(os.path.join(faction_path, "*.json")):
                    try:
                        with open(json_file, 'r') as f:
                            card_data = json.load(f)
                            # Check if this card has the matching RFID
                            if card_data.get('rfid') == rfid:
                                self._log.info(f"Found card in {json_file}")
                                return card_data, json_file
                    except Exception as e:
                        self._log.error(f"Error reading {json_file}: {e}")
        
        self._log.info("Card not found in database by content ID")
        return None, None
        
    def find_card_by_name_and_faction(self, name: str, faction: str) -> Tuple[Optional[CardData], Optional[FilePath]]:
        """Find a card in the database by name and faction"""
        if not name or not faction:
            self._log.info("Name or faction not provided")
            return None, None
            
        self._log.info(f"Searching for card with name: {name} and faction: {faction}")
        
        # Search through all faction directories
        faction_dir = os.path.join(self.cards_dir, gwent.cards.util.fs_safe(faction))
        if os.path.isdir(faction_dir):
            # Search through all JSON files in the faction directory
            for json_file in glob.glob(os.path.join(faction_dir, "*.json")):
                try:
                    with open(json_file, 'r') as f:
                        card_data = json.load(f)
                        # Check if this card has the matching name and faction
                        if card_data.get('name') == name and card_data.get('faction') == faction:
                            self._log.info(f"Found card in {json_file}")
                            return card_data, json_file
                except Exception as e:
                    self._log.error(f"Error reading {json_file}: {e}")
        
        self._log.info("Card not found in database by name and faction")
        return None, None

    # content_id is no longer used in the card files

    def prompt_for_card_details(self, default_name: Optional[str] = None, default_faction: Optional[str] = None) -> CardData:
        """Prompt the user for card details"""
        print("\nEnter card details:")
        
        # Required fields
        name_prompt = f"Name (required) [{default_name}]: " if default_name else "Name (required): "
        name = input(name_prompt)
        if not name and default_name:
            name = default_name
        while not name:
            print("Name is required.")
            name = input("Name (required): ")
        
        # Prompt for faction with validation
        valid_factions: List[str] = ["Northern Realms", "Monsters", "Nilfgaardian", "Scoia'tael", "Skellige"]
        faction_prompt = f"Faction (required) [{default_faction}]: " if default_faction else f"Faction (required) - Choose from {', '.join(valid_factions)}: "
        faction = input(faction_prompt)
        if not faction and default_faction:
            faction = default_faction
        while faction not in valid_factions:
            print(f"Invalid faction. Please choose from: {', '.join(valid_factions)}")
            faction = input("Faction (required): ")
        
        # Optional fields
        owner = input("Owner (optional): ")
        
        # Ranges
        valid_ranges: List[str] = ["close", "ranged", "siege"]
        print(f"Valid ranges: {', '.join(valid_ranges)}")
        ranges_input = input("Ranges (comma-separated, optional): ")
        ranges: List[str] = [r.strip() for r in ranges_input.split(',')] if ranges_input else []
        # Validate ranges
        ranges = [r for r in ranges if r in valid_ranges]
        
        # Strength
        strength_input = input("Strength (0-15, optional): ")
        strength = None
        if strength_input:
            try:
                strength = int(strength_input)
                if strength < 0 or strength > 15:
                    print("Strength must be between 0 and 15. Setting to 0.")
                    strength = 0
            except ValueError:
                print("Invalid strength value. Setting to 0.")
                strength = 0
        
        # Abilities
        valid_abilities: List[str] = ["agile", "berserker", "commander", "morale", "medic", "muster", "scorch", "spy", "summon", "bond"]
        print(f"Valid abilities: {', '.join(valid_abilities)}")
        abilities_input = input("Abilities (comma-separated, optional): ")
        abilities: List[str] = [a.strip() for a in abilities_input.split(',')] if abilities_input else []
        # Validate abilities
        abilities = [a for a in abilities if a in valid_abilities]
        
        # Specialty
        valid_specialties: List[str] = ["commander", "decoy", "leader", "scorch", "weather", "hero", "mardroeme"]
        print(f"Valid specialties: {', '.join(valid_specialties)}")
        specialty = input("Specialty (optional): ")
        if specialty and specialty not in valid_specialties:
            print(f"Invalid specialty. Setting to None.")
            specialty = None
        
        # Starter
        starter_input = input("Starter card? (yes/no, default: no): ")
        starter = starter_input.lower() in ['yes', 'y', 'true']
        
        # Generate a content_id (MD5 hash of name + faction)
        content_id = hashlib.md5(f"{name}{faction}".encode()).hexdigest()
        
        # Create card data
        card_data: CardData = {
            "content_id": content_id,
            "name": name,
            "faction": faction
        }
        
        if owner:
            card_data["owner"] = owner
        
        if ranges:
            card_data["ranges"] = ranges
        
        if strength is not None:
            card_data["strength"] = strength
        
        if abilities:
            card_data["abilities"] = abilities
        
        if specialty:
            card_data["specialty"] = specialty
        
        if starter:
            card_data["starter"] = True
        
        return card_data

    def write_card_to_database(self, card_data: CardData) -> FilePath:
        """Write a card to the database"""
        faction = card_data["faction"]
        name = card_data["name"]
        
        # Create faction directory if it doesn't exist
        faction_dir = os.path.join(self.cards_dir, gwent.cards.util.fs_safe(faction))
        if not os.path.exists(faction_dir):
            os.makedirs(faction_dir)
        
        # Create filename
        filename = f"{gwent.cards.util.fs_safe(name)}.json"
        filepath = os.path.join(faction_dir, filename)
        
        # Write card to file
        with open(filepath, 'w') as f:
            json.dump(card_data, f, indent=4)
        
        self._log.info(f"Card written to {filepath}")
        return filepath

    def write_card_to_rfid(self, card_data: CardData) -> Optional[int]:
        """Write a card to an RFID tag"""
        # Convert card data to a Message object
        card: gwent.messaging.card.Message = gwent.messaging.card.Message.from_properties(card_data)
        
        self._log.info({
            'action': 'Hold a tag near the writer to receive the data',
            'name': card.name,
            'faction': card.faction,
        })

        writer = gwent.hal.rfid.instance()

        rfid: Optional[int] = None
        while rfid is None and not self._stop_event.is_set():
            rfid = writer.write_card(card)
            if rfid is None:
                # Small delay to prevent CPU hogging
                time.sleep(0.1)

        if rfid is not None:
            self._log.info({
                'action': 'card written successfully',
                'id': rfid,
            })
            
            # Update the card data with the RFID
            card_data['rfid'] = rfid
            
            return rfid
        
        return None

    def run(self) -> None:
        """Run the card manager utility"""
        self.setup_signal_handlers()
        
        # Read the RFID card
        card: Optional[gwent.messaging.card.Message] = self.read_rfid_card()
        
        if card is None:
            self._log.error("Failed to read card")
            return
        
        # Try to find the card in the database
        card_data: Optional[CardData] = None
        card_file: Optional[FilePath] = None
        
        try:
            # First try by RFID if available
            if hasattr(card, 'rfid') and card.rfid:
                card_data, card_file = self.find_card_in_database(card.rfid)
            
            # Try by name and faction if available
            if card_data is None and hasattr(card, 'name') and hasattr(card, 'faction'):
                # For weather cards, strip any number suffix
                name = card.name
                if hasattr(card, 'instance') and card.instance.get('specialty') == 'weather':
                    # Strip number suffix from weather card names
                    name = re.sub(r': \d+$', '', name)
                    self._log.info(f"Searching for weather card with normalized name: {name}")
                
                self._log.info(f"Trying to find card by name and faction: {name}, {card.faction}")
                card_data, card_file = self.find_card_by_name_and_faction(name, card.faction)
        except Exception as e:
            self._log.error(f"Error finding card: {e}")
            card_data = None
            card_file = None
        
        if card_data:
            # Check if the card data needs to be updated with the RFID
            updated: bool = False
            if hasattr(card, 'rfid') and card.rfid and ('rfid' not in card_data or card_data['rfid'] != card.rfid):
                # Update the card data with the RFID
                card_data['rfid'] = card.rfid
                updated = True
                self._log.info(f"Updating card with RFID: {card.rfid}")
                
                # Write the updated card data to the file
                if card_file:
                    try:
                        # Make sure the RFID is properly set in the card data
                        rfid_value: int = int(card.rfid)
                        card_data['rfid'] = rfid_value
                        
                        # Write the updated card data to the file
                        with open(card_file, 'w') as f:
                            json.dump(card_data, f, indent=4)
                        self._log.info(f"Card file updated with RFID: {card_file}")
                        
                        # Verify the file was updated correctly
                        with open(card_file, 'r') as f:
                            updated_data: CardData = json.load(f)
                            if 'rfid' in updated_data and updated_data['rfid'] == card.rfid:
                                self._log.info(f"Verified RFID was added to file: {card_file}")
                            else:
                                self._log.error(f"Failed to verify RFID in file: {card_file}")
                    except Exception as e:
                        self._log.error(f"Error updating card file with RFID: {e}")
            
            # Card exists, print information
            print("\n" + "="*50)
            print(f"  CARD FOUND: {card_data.get('name', 'Unknown')}")
            print("="*50)
            
            # Basic information
            print(f"\nBasic Information:")
            print(f"  Name:    {card_data.get('name', 'Unknown')}")
            print(f"  Faction: {card_data.get('faction', 'Unknown')}")
            
            # Card attributes
            print("\nCard Attributes:")
            if 'strength' in card_data:
                print(f"  Strength: {card_data['strength']}")
            else:
                print("  Strength: N/A")
                
            if 'ranges' in card_data:
                print(f"  Ranges:   {', '.join(card_data['ranges'])}")
            else:
                print("  Ranges:   N/A")
                
            if 'specialty' in card_data:
                print(f"  Specialty: {card_data['specialty']}")
            else:
                print("  Specialty: None")
                
            if 'abilities' in card_data:
                print(f"  Abilities: {', '.join(card_data['abilities'])}")
            else:
                print("  Abilities: None")
            
            # Additional information
            print("\nAdditional Information:")
            if 'owner' in card_data:
                print(f"  Owner:       {card_data['owner']}")
            else:
                print("  Owner:       None")
                
            if 'starter' in card_data and card_data['starter']:
                print("  Starter card: Yes")
            else:
                print("  Starter card: No")
            
            if 'rfid' in card_data:
                print(f"  RFID:      {card_data['rfid']}")
            else:
                print("  RFID:      Not assigned")
                
            if 'content_id' in card_data:
                print(f"  Content ID:   {card_data['content_id']}")
            
            # File information
            print(f"\nFile: {card_file}")
            print("="*50)
            
            if updated:
                print("\nCard file updated")
        else:
            try:
                # Card doesn't exist, prompt for details
                print("\nCard not found in database. Creating a new card.")
                
                # Get card name and faction from the RFID card if available
                default_name: Optional[str] = card.name if hasattr(card, 'name') else None
                default_faction: Optional[str] = card.faction if hasattr(card, 'faction') else None
                
                card_data = self.prompt_for_card_details(default_name, default_faction)
                
                # Write card to database
                card_file = self.write_card_to_database(card_data)
                
                # Write card to RFID tag
                rfid: Optional[int] = self.write_card_to_rfid(card_data)
                
                if rfid:
                    # Update the card in the database with the RFID
                    card_data['rfid'] = rfid
                    with open(card_file, 'w') as f:
                        json.dump(card_data, f, indent=4)
                    
                    print(f"\nCard successfully written to RFID tag with ID: {rfid}")
                else:
                    print("\nFailed to write card to RFID tag")
            except Exception as e:
                self._log.error(f"Error creating card: {e}")
                print(f"\nError creating card: {e}")


def main() -> int:
    """Command-line entry point for the card manager utility"""
    # Set up logging
    gwent.log.setup(level='debug')
    
    # Create and run the card manager utility
    manager = CardManager()
    manager.run()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())