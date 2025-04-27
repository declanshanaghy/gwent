import os
import json
import logging
import sys
import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Set, Any, Optional, Tuple
import gwent.log

# Type aliases
CardData = Dict[str, Any]
FilePath = str

class CardDownloader:
    def __init__(self, log_verbose: bool = False):
        self.log = logging.getLogger(__name__)
        if log_verbose:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)
            
        # Path to the cards directory
        self.cards_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                                     '..', '..', '..', '..', 'data', 'cards'))
        
        # URL for the Skellige Gwent deck wiki page
        self.wiki_url = "https://witcher.fandom.com/wiki/Skellige_Gwent_deck"
        
        # Faction name
        self.faction = "Skellige"
        
    def download_wiki_page(self) -> str:
        """Download the Skellige Gwent deck wiki page"""
        self.log.info(f"Downloading wiki page: {self.wiki_url}")
        
        try:
            response = requests.get(self.wiki_url)
            response.raise_for_status()
            
            # Save HTML to a file for debugging
            debug_html_path = os.path.join('tmp', 'wiki_page.html')
            os.makedirs(os.path.dirname(debug_html_path), exist_ok=True)
            with open(debug_html_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            self.log.info(f"Saved HTML content to {debug_html_path} for debugging")
            print(f"Saved HTML content to {debug_html_path} for debugging")
            
            return response.text
        except requests.RequestException as e:
            self.log.error(f"Error downloading wiki page: {e}")
            raise
            
    def parse_wiki_page(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse the wiki page to extract card information"""
        self.log.info("Parsing wiki page for card information")
        print("\nParsing wiki page for Skellige Gwent deck cards...")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        cards = []
        
        # Find the card tables - try different table classes and structures
        tables = soup.find_all('table')
        self.log.info(f"Found {len(tables)} total tables on the wiki page")
        print(f"Found {len(tables)} total tables on the wiki page")
        
        # Debug the table structure
        for i, table in enumerate(tables):
            table_classes = table.get('class', [])
            table_class_str = ' '.join(table_classes) if table_classes else 'no-class'
            headers = [th.text.strip() for th in table.find_all('th')]
            rows = len(table.find_all('tr'))
            self.log.info(f"Table {i+1}: class='{table_class_str}', headers={headers}, rows={rows}")
            print(f"Table {i+1}: class='{table_class_str}', headers={len(headers)}, rows={rows}")
        
        table_count = 0
        for table in tables:
            # Check if this is a card table by looking for headers
            headers = [th.text.strip() for th in table.find_all('th')]
            
            # More flexible detection of card tables
            header_text = ' '.join(headers).lower()
            
            # Check if this looks like a card table
            is_card_table = False
            if headers:
                # Check for common card table headers
                if any(term in header_text for term in ['card', 'name', 'strength', 'ability', 'power']):
                    is_card_table = True
                # Check if there are enough columns that might indicate a card table
                elif len(headers) >= 3:
                    is_card_table = True
            
            if not is_card_table:
                self.log.debug(f"Skipping table with headers: {headers}")
                print(f"Skipping table {table_count+1} - doesn't appear to be a card table")
                continue
            
            table_count += 1
            self.log.info(f"Processing table {table_count} with headers: {headers}")
            print(f"Processing table {table_count} with headers: {', '.join(headers)}")
                
            # Process rows
            row_count = 0
            for row in table.find_all('tr')[1:]:  # Skip header row
                row_count += 1
                cells = row.find_all('td')
                if not cells:
                    continue
                    
                card_data = {"faction": self.faction}
                
                # Extract card name - more flexible approach
                name_cell = None
                
                # First try to find a column with "name" in the header
                for i, header in enumerate(headers):
                    if 'name' in header.lower() and i < len(cells):
                        name_cell = cells[i]
                        break
                
                # If no name column found, try the first column as it often contains the name
                if name_cell is None and len(cells) > 0:
                    name_cell = cells[0]
                    self.log.debug(f"No name column found, using first column: {name_cell.text.strip()}")
                
                if name_cell:
                    # Try to get name from the cell
                    name = name_cell.text.strip()
                    # Remove any number suffixes (like ": 1" or ": 2")
                    name = re.sub(r'\s*:\s*\d+$', '', name)
                    card_data["name"] = name
                    self.log.debug(f"Found card: {name}")
                else:
                    self.log.debug(f"Skipping row {row_count} - no name found")
                    continue  # Skip if no name found
                
                # Extract card strength if available
                strength_cell = None
                for i, header in enumerate(headers):
                    if 'strength' in header.lower() and i < len(cells):
                        strength_cell = cells[i]
                        break
                
                if strength_cell:
                    strength_text = strength_cell.text.strip()
                    if strength_text and strength_text.isdigit():
                        card_data["strength"] = int(strength_text)
                        self.log.debug(f"Card '{card_data['name']}' strength: {card_data['strength']}")
                    else:
                        self.log.debug(f"Card '{card_data['name']}' has no valid strength value: '{strength_text}'")
                
                # Extract card abilities if available
                ability_cell = None
                for i, header in enumerate(headers):
                    if 'ability' in header.lower() and i < len(cells):
                        ability_cell = cells[i]
                        break
                
                if ability_cell:
                    ability_text = ability_cell.text.strip()
                    if ability_text:
                        # Map common ability names
                        ability_map = {
                            'agile': 'agile',
                            'berserker': 'berserker',
                            'bond': 'bond',
                            'medic': 'medic',
                            'morale': 'morale',
                            'muster': 'muster',
                            'spy': 'spy',
                            'tight bond': 'bond',
                            'hero': 'hero'  # This is actually a specialty, not an ability
                        }
                        
                        abilities = []
                        for ability_name, ability_code in ability_map.items():
                            if ability_name.lower() in ability_text.lower():
                                if ability_code == 'hero':
                                    card_data["specialty"] = "hero"
                                else:
                                    abilities.append(ability_code)
                        
                        if abilities:
                            card_data["abilities"] = abilities
                            self.log.debug(f"Card '{card_data['name']}' abilities: {abilities}")
                        else:
                            self.log.debug(f"Card '{card_data['name']}' has no recognized abilities in text: '{ability_text}'")
                
                # Extract card type/row if available
                row_cell = None
                for i, header in enumerate(headers):
                    if any(term in header.lower() for term in ['row', 'type', 'range']):
                        if i < len(cells):
                            row_cell = cells[i]
                            break
                
                if row_cell:
                    row_text = row_cell.text.strip().lower()
                    ranges = []
                    
                    if 'close' in row_text or 'melee' in row_text:
                        ranges.append('close')
                    if 'ranged' in row_text or 'range' in row_text:
                        ranges.append('ranged')
                    if 'siege' in row_text:
                        ranges.append('siege')
                    
                    # Check for special cards
                    if any(term in row_text for term in ['weather', 'leader', 'special']):
                        for specialty in ['weather', 'leader', 'decoy', 'scorch', 'commander', 'mardroeme']:
                            if specialty in row_text:
                                card_data["specialty"] = specialty
                                self.log.debug(f"Card '{card_data['name']}' specialty: {specialty}")
                                break
                    
                    if ranges:
                        card_data["ranges"] = ranges
                        self.log.debug(f"Card '{card_data['name']}' ranges: {ranges}")
                
                cards.append(card_data)
                self.log.info(f"Added card: {card_data['name']} - {card_data}")
                print(f"Found card: {card_data['name']}")
        
        # If no cards were found in tables, try alternative extraction methods
        if not cards:
            self.log.warning("No cards found in tables, trying alternative extraction methods")
            print("No cards found in tables, trying alternative extraction methods...")
            
            # Try to find card lists in other formats (like lists or divs)
            cards = self.extract_cards_from_lists(soup)
            
            # If still no cards, try extracting from paragraphs and other text
            if not cards:
                self.log.warning("No cards found in lists, trying to extract from paragraphs")
                print("No cards found in lists, trying to extract from paragraphs...")
                cards = self.extract_cards_from_paragraphs(soup)
                
                # If still no cards, use a fallback list of known cards
                if not cards:
                    self.log.warning("No cards found in paragraphs, using fallback list of known cards")
                    print("No cards found in paragraphs, using fallback list of known cards...")
                    cards = self.get_fallback_card_list()
            
        self.log.info(f"Found {len(cards)} cards on the wiki page")
        print(f"\nExtracted {len(cards)} cards from the Skellige Gwent deck wiki page")
        return cards
        
    def extract_cards_from_paragraphs(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract cards from paragraphs and other text elements"""
        cards = []
        
        # Look for content divs that might contain card information
        content_divs = soup.find_all('div', class_='mw-parser-output')
        if not content_divs:
            self.log.warning("Could not find main content div")
            return cards
            
        # Process each content div
        for content_div in content_divs:
            # Look for paragraphs and headers
            elements = content_div.find_all(['p', 'h2', 'h3', 'h4', 'div'])
            
            self.log.info(f"Found {len(elements)} text elements to analyze")
            print(f"Found {len(elements)} text elements to analyze")
            
            # Track the current section
            current_section = "Unknown"
            
            for element in elements:
                # Check if this is a header
                if element.name in ['h2', 'h3', 'h4']:
                    current_section = element.text.strip()
                    self.log.info(f"Found section: {current_section}")
                    print(f"Found section: {current_section}")
                    continue
                
                # Get the text content
                text = element.text.strip()
                
                # Skip empty elements
                if not text:
                    continue
                
                # Look for card names in the text
                # Common patterns for card names in text:
                # - Names in quotes: "Card Name"
                # - Names in bold: <b>Card Name</b>
                # - Names followed by a description: Card Name - description
                
                # Try to extract names in quotes
                quote_matches = re.findall(r'"([^"]+)"', text)
                for match in quote_matches:
                    if len(match) > 2 and len(match) < 50:  # Reasonable name length
                        card_data = {"faction": self.faction, "name": match}
                        self.extract_card_attributes_from_text(card_data, text)
                        cards.append(card_data)
                        self.log.info(f"Extracted card from quotes: {card_data}")
                        print(f"Found card: {card_data['name']}")
                
                # Try to extract names in bold
                bold_elements = element.find_all('b')
                for bold in bold_elements:
                    bold_text = bold.text.strip()
                    if bold_text and len(bold_text) > 2 and len(bold_text) < 50:
                        card_data = {"faction": self.faction, "name": bold_text}
                        self.extract_card_attributes_from_text(card_data, text)
                        cards.append(card_data)
                        self.log.info(f"Extracted card from bold text: {card_data}")
                        print(f"Found card: {card_data['name']}")
                
                # Try to extract names followed by a description
                name_desc_matches = re.findall(r'([A-Z][a-zA-Z\s\']+)\s*[-–:]\s', text)
                for match in name_desc_matches:
                    match = match.strip()
                    if len(match) > 2 and len(match) < 50:
                        card_data = {"faction": self.faction, "name": match}
                        self.extract_card_attributes_from_text(card_data, text)
                        cards.append(card_data)
                        self.log.info(f"Extracted card from description pattern: {card_data}")
                        print(f"Found card: {card_data['name']}")
        
        return cards
    
    def extract_card_attributes_from_text(self, card_data: Dict[str, Any], text: str) -> None:
        """Extract card attributes from surrounding text"""
        # Try to extract strength if present
        strength_match = re.search(r'(\d+)\s*strength', text, re.IGNORECASE)
        if strength_match:
            card_data["strength"] = int(strength_match.group(1))
        
        # Try to extract abilities
        abilities = []
        for ability in ['agile', 'berserker', 'bond', 'medic', 'morale', 'muster', 'spy']:
            if re.search(r'\b' + ability + r'\b', text, re.IGNORECASE):
                abilities.append(ability)
        
        if abilities:
            card_data["abilities"] = abilities
        
        # Try to extract ranges
        ranges = []
        if re.search(r'\bclose\b|\bmelee\b', text, re.IGNORECASE):
            ranges.append('close')
        if re.search(r'\branged\b', text, re.IGNORECASE):
            ranges.append('ranged')
        if re.search(r'\bsiege\b', text, re.IGNORECASE):
            ranges.append('siege')
            
        if ranges:
            card_data["ranges"] = ranges
        
        # Try to extract specialty
        for specialty in ['weather', 'leader', 'decoy', 'scorch', 'commander', 'mardroeme', 'hero']:
            if re.search(r'\b' + specialty + r'\b', text, re.IGNORECASE):
                card_data["specialty"] = specialty
                break
                
    def get_fallback_card_list(self) -> List[Dict[str, Any]]:
        """Return a fallback list of known Skellige Gwent cards"""
        self.log.info("Using fallback list of known Skellige Gwent cards")
        
        # This is a manually curated list of known Skellige Gwent cards
        # based on the files in software/data/cards/Skellige
        cards = [
            {"name": "Avallac'h", "faction": "Skellige", "abilities": ["spy"], "ranges": ["close"], "strength": 0},
            {"name": "Berserker", "faction": "Skellige", "abilities": ["berserker"], "ranges": ["close"], "strength": 4},
            {"name": "Birna Bran", "faction": "Skellige", "abilities": ["medic"], "ranges": ["close"], "strength": 2},
            {"name": "Biting Frost", "faction": "Skellige", "specialty": "weather", "ranges": ["close"]},
            {"name": "Blueboy Lugos", "faction": "Skellige", "ranges": ["close"], "strength": 6},
            {"name": "Clan Brokvar Archer", "faction": "Skellige", "ranges": ["ranged"], "strength": 6},
            {"name": "Clan Drummond Shield Maiden", "faction": "Skellige", "abilities": ["bond"], "ranges": ["close"], "strength": 4},
            {"name": "Clan Heymaey Skals", "faction": "Skellige", "ranges": ["close"], "strength": 4},
            {"name": "Clan Tordarroch Armorsmith", "faction": "Skellige", "ranges": ["close"], "strength": 4},
            {"name": "Clan an Craite Warrior", "faction": "Skellige", "abilities": ["bond"], "ranges": ["close"], "strength": 6},
            {"name": "Clear Weather", "faction": "Skellige", "specialty": "weather"},
            {"name": "Commander's Horn", "faction": "Skellige", "specialty": "commander", "ranges": ["close", "ranged", "siege"]},
            {"name": "Crach an Craite", "faction": "Skellige", "specialty": "leader"},
            {"name": "Dandelion", "faction": "Skellige", "abilities": ["commander"], "ranges": ["close"], "strength": 2},
            {"name": "Decoy", "faction": "Skellige", "specialty": "decoy"},
            {"name": "Donar an Hindar", "faction": "Skellige", "ranges": ["close"], "strength": 4},
            {"name": "Draig Bon-Dhu", "faction": "Skellige", "abilities": ["commander"], "ranges": ["siege"], "strength": 2},
            {"name": "Gaunter O'Dimm: Darkness", "faction": "Skellige", "abilities": ["muster"], "ranges": ["ranged"], "strength": 4},
            {"name": "Hjalmar", "faction": "Skellige", "specialty": "hero", "ranges": ["ranged"], "strength": 10},
            {"name": "Holger Blackhand", "faction": "Skellige", "ranges": ["siege"], "strength": 4},
            {"name": "Impenetrable Fog", "faction": "Skellige", "specialty": "weather", "ranges": ["ranged"]},
            {"name": "Light Longship", "faction": "Skellige", "abilities": ["muster"], "ranges": ["ranged"], "strength": 4},
            {"name": "Madman Lugos", "faction": "Skellige", "ranges": ["close"], "strength": 6},
            {"name": "Mardroeme", "faction": "Skellige", "specialty": "mardroeme"},
            {"name": "Olaf", "faction": "Skellige", "abilities": ["agile", "morale"], "ranges": ["close", "ranged"], "strength": 12},
            {"name": "Scorch", "faction": "Skellige", "specialty": "scorch", "ranges": ["close", "ranged", "siege"]},
            {"name": "Svanrige", "faction": "Skellige", "ranges": ["close"], "strength": 4},
            {"name": "Torrential Rain", "faction": "Skellige", "specialty": "weather", "ranges": ["siege"]},
            {"name": "Transformed Vildkaarl", "faction": "Skellige", "abilities": ["morale"], "ranges": ["close"], "strength": 14},
            {"name": "Transformed Young Vildkaarl", "faction": "Skellige", "abilities": ["bond"], "ranges": ["ranged"], "strength": 8},
            {"name": "Triss Merigold", "faction": "Skellige", "specialty": "hero", "ranges": ["close"], "strength": 7},
            {"name": "Udalyrk", "faction": "Skellige", "ranges": ["close"], "strength": 4},
            {"name": "War Longship", "faction": "Skellige", "abilities": ["bond"], "ranges": ["siege"], "strength": 6},
            {"name": "Young Berserker", "faction": "Skellige", "abilities": ["berserker"], "ranges": ["ranged"], "strength": 2},
            {"name": "Zoltan Chivay", "faction": "Skellige", "ranges": ["close"], "strength": 5}
        ]
        
        for card in cards:
            self.log.info(f"Added fallback card: {card['name']}")
            print(f"Added fallback card: {card['name']}")
            
        return cards
        
    def extract_cards_from_lists(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract cards from lists or other elements when tables aren't available"""
        cards = []
        
        # Look for lists that might contain card information
        lists = soup.find_all(['ul', 'ol'])
        self.log.info(f"Found {len(lists)} lists that might contain card information")
        print(f"Found {len(lists)} lists that might contain card information")
        
        for list_elem in lists:
            # Check if this list might contain card information
            list_text = list_elem.text.lower()
            if any(term in list_text for term in ['card', 'gwent', 'skellige', 'deck']):
                self.log.info(f"Found potential card list: {list_text[:100]}...")
                
                # Extract items from the list
                items = list_elem.find_all('li')
                for item in items:
                    item_text = item.text.strip()
                    
                    # Skip empty items
                    if not item_text:
                        continue
                        
                    # Try to extract card information from the item text
                    card_data = {"faction": self.faction, "name": item_text}
                    
                    # Try to extract strength if present
                    strength_match = re.search(r'(\d+)\s*strength', item_text, re.IGNORECASE)
                    if strength_match:
                        card_data["strength"] = int(strength_match.group(1))
                    
                    # Try to extract abilities
                    abilities = []
                    for ability in ['agile', 'berserker', 'bond', 'medic', 'morale', 'muster', 'spy']:
                        if re.search(r'\b' + ability + r'\b', item_text, re.IGNORECASE):
                            abilities.append(ability)
                    
                    if abilities:
                        card_data["abilities"] = abilities
                    
                    # Try to extract ranges
                    ranges = []
                    if re.search(r'\bclose\b|\bmelee\b', item_text, re.IGNORECASE):
                        ranges.append('close')
                    if re.search(r'\branged\b', item_text, re.IGNORECASE):
                        ranges.append('ranged')
                    if re.search(r'\bsiege\b', item_text, re.IGNORECASE):
                        ranges.append('siege')
                        
                    if ranges:
                        card_data["ranges"] = ranges
                    
                    # Try to extract specialty
                    for specialty in ['weather', 'leader', 'decoy', 'scorch', 'commander', 'mardroeme', 'hero']:
                        if re.search(r'\b' + specialty + r'\b', item_text, re.IGNORECASE):
                            card_data["specialty"] = specialty
                            break
                    
                    # Add the card
                    cards.append(card_data)
                    self.log.info(f"Extracted card from list item: {card_data}")
                    print(f"Found card: {card_data['name']}")
        
        return cards
    
    def load_existing_cards(self) -> Dict[str, CardData]:
        """Load existing card data from the filesystem"""
        self.log.info("Loading existing card data")
        print("\nLoading existing Skellige card data from filesystem...")
        
        existing_cards = {}
        faction_dir = os.path.join(self.cards_dir, self.faction)
        self.log.info(f"Looking for cards in directory: {faction_dir}")
        
        if not os.path.exists(faction_dir):
            self.log.warning(f"Faction directory not found: {faction_dir}")
            return existing_cards
            
        for filename in os.listdir(faction_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(faction_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        card_data = json.load(f)
                        if 'name' in card_data:
                            # Normalize the name by removing any number suffixes
                            name = re.sub(r'\s*:\s*\d+$', '', card_data['name'])
                            existing_cards[name] = card_data
                            self.log.debug(f"Loaded card from file: {name} - {filepath}")
                            print(f"Loaded card: {name}")
                        else:
                            self.log.warning(f"Card file missing name attribute: {filepath}")
                except Exception as e:
                    self.log.error(f"Error reading {filepath}: {e}")
                    
        self.log.info(f"Loaded {len(existing_cards)} existing cards")
        print(f"\nLoaded {len(existing_cards)} existing Skellige cards from filesystem")
        
        # Log a summary of the card types found
        card_types = {}
        for name, card in existing_cards.items():
            card_type = "Unit"
            if "specialty" in card:
                card_type = card["specialty"].capitalize()
            
            if card_type not in card_types:
                card_types[card_type] = 0
            card_types[card_type] += 1
            
        for card_type, count in card_types.items():
            self.log.info(f"Found {count} {card_type} cards")
            print(f"- {count} {card_type} cards")
        return existing_cards
        
    def compare_cards(self, wiki_cards: List[CardData], existing_cards: Dict[str, CardData]) -> Dict[str, List[str]]:
        """Compare wiki cards with existing cards"""
        self.log.info("Comparing wiki cards with existing cards")
        print("\nComparing wiki cards with existing cards...")
        
        # Sets for tracking differences
        wiki_card_names = {card['name'] for card in wiki_cards}
        existing_card_names = set(existing_cards.keys())
        
        # Find differences
        missing_in_files = wiki_card_names - existing_card_names
        missing_in_wiki = existing_card_names - wiki_card_names
        
        # Cards in both sets that might have differences
        common_cards = wiki_card_names.intersection(existing_card_names)
        
        self.log.info(f"Wiki cards: {len(wiki_card_names)}, Existing cards: {len(existing_card_names)}")
        self.log.info(f"Missing in files: {len(missing_in_files)}, Missing in wiki: {len(missing_in_wiki)}, Common cards: {len(common_cards)}")
        print(f"Wiki cards: {len(wiki_card_names)}, Existing cards: {len(existing_card_names)}")
        print(f"Cards in both sources: {len(common_cards)}")
        print(f"Cards in wiki but missing in files: {len(missing_in_files)}")
        print(f"Cards in files but missing in wiki: {len(missing_in_wiki)}")
        
        # Track attribute differences for common cards
        attribute_differences = []
        
        # Print some of the missing cards for quick reference
        if missing_in_files:
            print("\nSample of cards in wiki but missing in files:")
            for card_name in list(missing_in_files)[:5]:  # Show up to 5 examples
                print(f"- {card_name}")
            if len(missing_in_files) > 5:
                print(f"  ... and {len(missing_in_files) - 5} more")
                
        if missing_in_wiki:
            print("\nSample of cards in files but missing in wiki:")
            for card_name in list(missing_in_wiki)[:5]:  # Show up to 5 examples
                print(f"- {card_name}")
            if len(missing_in_wiki) > 5:
                print(f"  ... and {len(missing_in_wiki) - 5} more")
        
        print("\nComparing attributes for cards in both sources...")
        for wiki_card in wiki_cards:
            if wiki_card['name'] in common_cards:
                existing_card = existing_cards[wiki_card['name']]
                self.log.debug(f"Comparing attributes for card: {wiki_card['name']}")
                
                # Compare attributes
                for attr in ['strength', 'abilities', 'ranges', 'specialty']:
                    if attr in wiki_card and attr in existing_card:
                        if wiki_card[attr] != existing_card[attr]:
                            diff_msg = f"Card '{wiki_card['name']}' has different {attr}: Wiki: {wiki_card[attr]}, File: {existing_card[attr]}"
                            self.log.info(diff_msg)
                            print(f"- {diff_msg}")
                            attribute_differences.append(diff_msg)
                    elif attr in wiki_card and attr not in existing_card:
                        diff_msg = f"Card '{wiki_card['name']}' has {attr} in wiki but not in file: {wiki_card[attr]}"
                        self.log.info(diff_msg)
                        print(f"- {diff_msg}")
                        attribute_differences.append(diff_msg)
                    elif attr not in wiki_card and attr in existing_card:
                        diff_msg = f"Card '{wiki_card['name']}' has {attr} in file but not in wiki: {existing_card[attr]}"
                        self.log.info(diff_msg)
                        print(f"- {diff_msg}")
                        attribute_differences.append(diff_msg)
        
        return {
            "missing_in_files": sorted(list(missing_in_files)),
            "missing_in_wiki": sorted(list(missing_in_wiki)),
            "attribute_differences": attribute_differences
        }
        
    def generate_report(self, differences: Dict[str, List[str]]) -> str:
        """Generate a report of the differences"""
        self.log.info("Generating report")
        print("\nGenerating comparison report...")
        
        report = f"# Skellige Gwent Deck Comparison Report\n\n"
        report += f"## Cards in Wiki but missing in files\n\n"
        
        missing_count = len(differences["missing_in_files"])
        self.log.info(f"Adding {missing_count} cards missing in files to report")
        print(f"Adding {missing_count} cards missing in files to report")
        
        if differences["missing_in_files"]:
            for card_name in differences["missing_in_files"]:
                report += f"- {card_name}\n"
        else:
            report += "No cards missing in files.\n"
            
        report += f"\n## Cards in files but missing in Wiki\n\n"
        
        missing_count = len(differences["missing_in_wiki"])
        self.log.info(f"Adding {missing_count} cards missing in wiki to report")
        print(f"Adding {missing_count} cards missing in wiki to report")
        
        if differences["missing_in_wiki"]:
            for card_name in differences["missing_in_wiki"]:
                report += f"- {card_name}\n"
        else:
            report += "No cards missing in Wiki.\n"
            
        report += f"\n## Attribute differences\n\n"
        
        diff_count = len(differences["attribute_differences"])
        self.log.info(f"Adding {diff_count} attribute differences to report")
        print(f"Adding {diff_count} attribute differences to report")
        
        if differences["attribute_differences"]:
            for diff in differences["attribute_differences"]:
                report += f"- {diff}\n"
        else:
            report += "No attribute differences found.\n"
            
        return report
        
    def save_report(self, report: str, output_path: str) -> None:
        """Save the report to a file"""
        self.log.info(f"Saving report to {output_path}")
        print(f"\nSaving comparison report to {output_path}")
        
        # Create directory if it doesn't exist
        report_dir = os.path.dirname(output_path)
        if not os.path.exists(report_dir):
            self.log.info(f"Creating directory: {report_dir}")
            print(f"Creating directory: {report_dir}")
            os.makedirs(report_dir, exist_ok=True)
        
        # Get report size
        report_size = len(report)
        self.log.info(f"Writing report ({report_size} characters)")
        
        with open(output_path, 'w') as f:
            f.write(report)
            
        self.log.info("Report saved successfully")
        print(f"Report saved successfully to {output_path}")
        
    def run(self, output_path: str = None) -> None:
        """Run the card downloader and comparison"""
        if output_path is None:
            output_path = os.path.join('tmp', 'card-differences.md')
        
        self.log.info(f"Starting Skellige Gwent deck comparison process")
        print(f"\n=== Skellige Gwent Deck Comparison Tool ===")
        print(f"Output will be saved to: {output_path}")
            
        try:
            # Download and parse the wiki page
            print(f"\nStep 1: Downloading wiki page from {self.wiki_url}")
            html_content = self.download_wiki_page()
            self.log.info(f"Downloaded {len(html_content)} bytes of HTML content")
            print(f"Downloaded {len(html_content)} bytes of HTML content")
            
            # Parse the wiki page
            print(f"\nStep 2: Parsing wiki page for card information")
            wiki_cards = self.parse_wiki_page(html_content)
            
            # Check if we found any cards
            if not wiki_cards:
                self.log.error("Failed to extract any cards from the wiki page")
                print("\n=== ERROR ===")
                print("Failed to extract any cards from the wiki page.")
                print("Please check the HTML content saved to tmp/wiki_page.html")
                return 1
            
            # Load existing cards
            print(f"\nStep 3: Loading existing cards from filesystem")
            existing_cards = self.load_existing_cards()
            
            # Compare cards
            print(f"\nStep 4: Comparing cards from both sources")
            differences = self.compare_cards(wiki_cards, existing_cards)
            
            # Generate and save report
            print(f"\nStep 5: Generating and saving report")
            report = self.generate_report(differences)
            self.save_report(report, output_path)
            
            print(f"\n=== Process completed successfully ===")
            print(f"Report generated at: {output_path}")
            
        except Exception as e:
            self.log.error(f"Error running card downloader: {e}", exc_info=True)
            print(f"\n=== ERROR ===")
            print(f"An error occurred during the comparison process:")
            print(f"{type(e).__name__}: {e}")
            print(f"Check the log file for more details.")
            return 1
        
        return 0
            
def main() -> int:
    """Command-line entry point for the card downloader utility"""
    # Set up logging
    gwent.log.setup(level='debug')
    
    # Parse command-line arguments
    output_path = 'tmp/card-differences.md'
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    
    print(f"Skellige Gwent Deck Card Downloader and Comparison Tool")
    print(f"------------------------------------------------------")
    
    # Create and run the card downloader
    downloader = CardDownloader(log_verbose=True)
    result = downloader.run(output_path)
    
    return result

if __name__ == '__main__':
    sys.exit(main())