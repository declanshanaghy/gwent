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

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt
from rich.prompt import Confirm
from rich.prompt import IntPrompt
from rich.prompt import PromptBase
from rich.theme import Theme
from rich.style import Style
from rich.highlighter import Highlighter
from rich.prompt import PromptBase
from rich.console import RenderableType
from rich.prompt import Prompt
from rich.prompt import PromptBase
from rich.console import Console
from rich.console import RenderableType
from rich.style import Style
from rich.text import Text
from rich.theme import Theme
import readchar

import gwent.log
import gwent.game
import gwent.messaging.base
import gwent.cards.all
import gwent.messaging.card
from gwent.messaging.card import NAME, FACTION, RFID  # Import constants
import gwent.cards.util
import gwent.hal.rfid
import RPi.GPIO as GPIO  # Import GPIO library to suppress warnings

# Type aliases
CardData = Dict[str, Any]
FilePath = str

class CardManager(gwent.game.BaseComponent):
    def __init__(self, log_verbose: bool = True):  # Default to verbose logging
        super().__init__(log_verbose=log_verbose)
        self._stop_event = threading.Event()
        self.cards_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                     '..', '..', '..', '..', 'data', 'cards'))
        # Suppress GPIO warnings
        GPIO.setwarnings(False)
        # No longer initializing RFID reader as a class member
        self._log.info({
            'action': 'card_manager_initialized',
            'log_verbose': log_verbose,
            'cards_dir': self.cards_dir
        })
        
        # Initialize Rich console
        self.console = Console()
        
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful exit"""
        def signal_handler(sig: int, frame: Any) -> None:
            self._log.info(f'Received exit signal {signal.Signals(sig).name}...')
            self._stop_event.set()
            
        for s in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                  signal.SIGQUIT, signal.SIGTERM):
            signal.signal(s, signal_handler)

    def cleanup(self) -> None:
        """Clean up resources"""
        # No longer need to clean up RFID reader as it's now created locally when needed
        pass

    def format_box_line(self, label: str, value: str, box_width: int = 48) -> str:
        """Format a line for the box with proper padding
        
        Args:
            label: Label for the line (e.g., "Name: ")
            value: Value to display
            box_width: Total width of the box interior (default: 48)
            
        Returns:
            Formatted line with proper padding for consistent right border
        """
        # Calculate the total available space for content (excluding borders and initial spacing)
        available_space = box_width - 4  # -4 for "║  " and " ║"
        
        # Combine label and value
        content = f"{label}{value}"
        
        # If content is too long, truncate it
        if len(content) > available_space:
            # Special handling for important fields
            if label == "CARD READ: " or label == "CARD FOUND: " or label == "Name:    ":
                max_value_length = available_space - len(label)
                if len(value) > max_value_length:
                    value = value[:max_value_length-3] + "..."
                content = f"{label}{value}"
            else:
                # For other fields, simple truncation
                content = content[:available_space-3] + "..."
        
        # Calculate exact padding to ensure consistent right border
        padding = available_space - len(content)
        
        # Return the formatted line with exact padding
        return f"║  {content}" + " " * padding + "║"
    
    def format_card_display(self, card_data: Union[gwent.messaging.card.Message, CardData],
                           header_text: str = "CARD READ",
                           file_path: Optional[str] = None,
                           show_additional_info: bool = False) -> Panel:
        """Format card data for display using Rich Panel
        
        Args:
            card_data: Card data to display (either Message object or dictionary)
            header_text: Text to display in the header (e.g., "CARD READ" or "CARD FOUND")
            file_path: Path to the card file (optional)
            show_additional_info: Whether to show additional information section
            
        Returns:
            Rich Panel object for display
        """
        if card_data is None:
            return Panel("No card data available")
        
        # Determine if we're dealing with a Message object or a dictionary
        is_message = isinstance(card_data, gwent.messaging.card.Message)
        
        # Check if this is a blank card
        is_blank_card = False
        if is_message:
            # A card is blank if it has an RFID but no name attribute or the name is not in the instance
            # OR if the name starts with "Blank Card" (indicating it was auto-generated)
            is_blank_card = (hasattr(card_data, 'rfid') and
                            (not (hasattr(card_data, 'name') and NAME in card_data.instance) or
                             (hasattr(card_data, 'name') and card_data.name.startswith("Blank Card"))))
        else:
            # For dictionary data, check if it has RFID but no name or name starts with "Blank Card"
            is_blank_card = ('rfid' in card_data and
                            ('name' not in card_data or
                             not card_data['name'] or
                             (isinstance(card_data.get('name'), str) and card_data['name'].startswith("Blank Card"))))
        
        # Get card properties based on the type
        if is_message:
            name = card_data.name if hasattr(card_data, 'name') and NAME in card_data.instance else f"Blank Card {card_data.rfid}" if hasattr(card_data, 'rfid') else 'Unknown'
            faction = card_data.faction if hasattr(card_data, 'faction') and FACTION in card_data.instance else 'Unknown'
            rfid = str(card_data.rfid) if hasattr(card_data, 'rfid') else 'Unknown'
            instance = card_data.instance if hasattr(card_data, 'instance') else {}
        else:
            name = card_data.get('name', f"Blank Card {card_data.get('rfid', 'Unknown')}" if 'rfid' in card_data else 'Unknown')
            faction = card_data.get('faction', 'Unknown')
            rfid = str(card_data.get('rfid', 'Unknown'))
            instance = card_data  # The dictionary itself contains the attributes
        
        # Create a Text object for the card information
        card_text = Text()
        
        # Basic information
        card_text.append("Basic Information:\n", style="bold cyan")
        card_text.append("Name:    ", style="cyan")
        card_text.append(f"{name}\n", style="green")
        card_text.append("Faction: ", style="cyan")
        card_text.append(f"{faction}\n", style="green")
        
        if not show_additional_info:
            card_text.append("RFID:    ", style="cyan")
            card_text.append(f"{rfid}\n", style="green")
        
        # Card attributes
        card_text.append("\nCard Attributes:\n", style="bold cyan")
        
        # Strength
        strength = instance.get('strength') if is_message else card_data.get('strength')
        card_text.append("Strength: ", style="cyan")
        if strength is not None:
            card_text.append(f"{strength}\n", style="green")
        else:
            card_text.append("N/A\n", style="green")
            
        # Ranges
        ranges = instance.get('ranges') if is_message else card_data.get('ranges')
        card_text.append("Ranges:   ", style="cyan")
        if ranges:
            ranges_str = ', '.join(ranges)
            card_text.append(f"{ranges_str}\n", style="green")
        else:
            card_text.append("N/A\n", style="green")
            
        # Specialty
        specialty = instance.get('specialty') if is_message else card_data.get('specialty')
        card_text.append("Specialty: ", style="cyan")
        if specialty:
            card_text.append(f"{specialty}\n", style="green")
        else:
            card_text.append("None\n", style="green")
            
        # Abilities
        abilities = instance.get('abilities') if is_message else card_data.get('abilities')
        card_text.append("Abilities: ", style="cyan")
        if abilities:
            abilities_str = ', '.join(abilities)
            card_text.append(f"{abilities_str}\n", style="green")
        else:
            card_text.append("None\n", style="green")
        
        # Additional information (for database cards)
        if show_additional_info:
            card_text.append("\nAdditional Information:\n", style="bold cyan")
            
            # Owner
            owner = card_data.get('owner')
            card_text.append("Owner:       ", style="cyan")
            if owner:
                card_text.append(f"{owner}\n", style="green")
            else:
                card_text.append("None\n", style="green")
                
            # Starter card
            starter = card_data.get('starter', False)
            card_text.append("Starter card: ", style="cyan")
            if starter:
                card_text.append("Yes\n", style="green")
            else:
                card_text.append("No\n", style="green")
            
            # RFID
            card_text.append("RFID:         ", style="cyan")
            if 'rfid' in card_data:
                card_text.append(f"{card_data['rfid']}\n", style="green")
            else:
                card_text.append("Not assigned\n", style="green")
                
            # Content ID
            content_id = card_data.get('content_id')
            if content_id:
                card_text.append("Content ID:   ", style="cyan")
                card_text.append(f"{content_id}\n", style="green")
            
            # File information
            if file_path:
                card_text.append("\nFile: ", style="cyan")
                card_text.append(f"{file_path}\n", style="green")
        
        # Create a panel with the card information
        try:
            panel = Panel(
                card_text,
                title=f"[bold yellow]{header_text}: {name}[/bold yellow]",
                border_style="bright_blue",
                box=box.DOUBLE,
                width=80,
                expand=False
            )
        except Exception as e:
            self._log.error(f"Error creating panel: {e}", exc_info=True)
            # Create a simple panel as fallback
            panel = Panel(
                f"Card: {name}\nFaction: {faction}\nRFID: {rfid}",
                title=f"[bold yellow]{header_text}[/bold yellow]",
                border_style="bright_blue"
            )
        
        return panel
    
    def pretty_print_card(self, card: gwent.messaging.card.Message) -> None:
        """Pretty print a card to the console"""
        if card is None:
            return
        
        # Format the card display
        display = self.format_card_display(card, "CARD READ")
        
        # Print the formatted display
        self.console.print(display)
        
        # Add debug log to verify the method is being called
        self._log.info("Pretty printed card to console")

    def read_rfid_card(self) -> Optional[gwent.messaging.card.Message]:
        """Read a card using the RFID reader"""
        self.console.print("\n[bold cyan]===== CARD READING PROCESS =====[/bold cyan]")
        self.console.print("[bold cyan]STEP 1:[/bold cyan] Place your card on the reader")
        self.console.print("[bold cyan]STEP 2:[/bold cyan] Press Enter when the card is in position")
        self.console.print("[bold cyan]STEP 3:[/bold cyan] Keep the card on the reader until the process completes")
        
        # Wait for the user to place the card and press Enter
        self.console.print("\n[bold green]Please place your card on the reader and press Enter when ready (or ESC/Ctrl+C to cancel)...[/bold green]")
        try:
            key = readchar.readkey()
            if key == readchar.key.ESC:
                self._log.info("User pressed ESC to cancel card reading")
                self.console.print("\n[yellow]Card reading cancelled.[/yellow]")
                return None
        except KeyboardInterrupt:
            self._log.info("User pressed Ctrl+C to cancel card reading")
            self.console.print("\n[yellow]Card reading cancelled.[/yellow]")
            return None
        
        self._log.info("User confirmed card is placed on reader")
        self.console.print("[bold cyan]Reading card...[/bold cyan]")
        
        # First check if a card is physically present by reading its ID
        rfid_reader = gwent.hal.rfid.instance()
        id, _ = rfid_reader._rfid.read_id(attempts=3)
        if id is None:
            self._log.warning("No card detected on reader")
            self.console.print("\n[bold red]ERROR: No card detected on reader![/bold red]")
            self.console.print("[yellow]Please make sure a card is placed on the reader and try again.[/yellow]")
            return None
            
        self._log.info(f"Card detected with ID: {id}")
        self.console.print(f"[green]Card detected with ID: {id}[/green]")
        
        # Log the start time of the read operation
        start_time = time.time()
        self._log.info(f"Starting card data read at timestamp: {start_time}")
        
        # Now try to read the card data
        card: Optional[gwent.messaging.card.Message] = None
        max_attempts = 2  # Limit attempts to avoid excessive retries
        attempts = 0
        
        # Simple loop to try reading the card
        while card is None and not self._stop_event.is_set() and attempts < max_attempts:
            attempts += 1
            self._log.debug(f"Card data read attempt #{attempts}")
            
            # Try to read the card
            rfid_reader = gwent.hal.rfid.instance()
            card = rfid_reader.read_card()
            
            # If we got a card (even a blank one), we're done
            if card is not None:
                self._log.info(f"Card read successfully on attempt {attempts}")
                break
                
            # If this isn't the last attempt, provide feedback and try again
            if attempts < max_attempts:
                self.console.print(f"[yellow]Attempt {attempts}/{max_attempts}: No card data read. Trying again...[/yellow]")
                # Small delay between attempts
                time.sleep(0.5)
        
        # If we still couldn't read card data but we have an ID, it's likely a blank card
        if card is None and id is not None:
            self._log.info(f"Card with ID {id} appears to be blank or uninitialized")
            self.console.print("\n[bold yellow]Card detected but appears to be blank or uninitialized.[/bold yellow]")
            
            # Create a minimal card object with just the RFID
            # This will allow the handle_read_card method to recognize it as a blank card
            # that needs initialization rather than a completely missing card
            card = gwent.messaging.card.Message.from_properties(rfid=id)
        
        # Log the end time and duration of the read operation
        end_time = time.time()
        duration = end_time - start_time
        self._log.info(f"Card read completed at timestamp: {end_time}, duration: {duration:.2f}s, attempts: {attempts}")
        
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
            
            # Pretty print the card immediately after reading
            self.pretty_print_card(card)
            
            # Add a longer delay after successful read to allow the RFID reader to reset
            time.sleep(1.0)
            self._log.info("Added 1.0s delay after successful card read to allow reader to reset")

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
                        self._log.error(f"Error reading {json_file}: {e}", exc_info=True)
        
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
                    self._log.error(f"Error reading {json_file}: {e}", exc_info=True)
        
        self._log.info("Card not found in database by name and faction")
        return None, None

    # content_id is no longer used in the card files

    def prompt_for_card_details(self, default_name: Optional[str] = None, default_faction: Optional[str] = None) -> CardData:
        """Prompt the user for card details"""
        self._log.info("Prompting user for card details")
        print("\nEnter card details:")
        
        # Required fields
        name_prompt = f"Name (required) [{default_name}]: " if default_name else "Name (required): "
        self._log.info(f"Prompting for card name with default: {default_name}")
        name = input(name_prompt)
        self._log.info(f"User input for card name: '{name}'")
        
        if not name and default_name:
            name = default_name
            self._log.info(f"Using default name: {name}")
        
        while not name:
            self._log.info("Name is required, prompting again")
            print("Name is required.")
            name = input("Name (required): ")
            self._log.info(f"User input for card name (retry): '{name}'")
        
        # Prompt for faction with validation
        valid_factions: List[str] = ["Northern Realms", "Monsters", "Nilfgaardian", "Scoia'tael", "Skellige"]
        faction_prompt = f"Faction (required) [{default_faction}]: " if default_faction else f"Faction (required) - Choose from {', '.join(valid_factions)}: "
        self._log.info(f"Prompting for card faction with default: {default_faction}")
        faction = input(faction_prompt)
        self._log.info(f"User input for card faction: '{faction}'")
        
        if not faction and default_faction:
            faction = default_faction
            self._log.info(f"Using default faction: {faction}")
        
        while faction not in valid_factions:
            self._log.info(f"Invalid faction '{faction}', prompting again")
            print(f"Invalid faction. Please choose from: {', '.join(valid_factions)}")
            faction = input("Faction (required): ")
            self._log.info(f"User input for card faction (retry): '{faction}'")
        
        # Optional fields
        self._log.info("Prompting for card owner")
        owner = input("Owner (optional): ")
        self._log.info(f"User input for card owner: '{owner}'")
        
        # Ranges
        valid_ranges: List[str] = ["close", "ranged", "siege"]
        print(f"Valid ranges: {', '.join(valid_ranges)}")
        self._log.info("Prompting for card ranges")
        ranges_input = input("Ranges (comma-separated, optional): ")
        self._log.info(f"User input for card ranges: '{ranges_input}'")
        
        ranges: List[str] = [r.strip() for r in ranges_input.split(',')] if ranges_input else []
        # Validate ranges
        ranges = [r for r in ranges if r in valid_ranges]
        self._log.info(f"Validated card ranges: {ranges}")
        
        # Strength
        self._log.info("Prompting for card strength")
        strength_input = input("Strength (0-15, optional): ")
        self._log.info(f"User input for card strength: '{strength_input}'")
        
        strength = None
        if strength_input:
            try:
                strength = int(strength_input)
                if strength < 0 or strength > 15:
                    self._log.info(f"Invalid strength value {strength}, setting to 0")
                    print("Strength must be between 0 and 15. Setting to 0.")
                    strength = 0
            except ValueError:
                self._log.info(f"Invalid strength value '{strength_input}', setting to 0")
                print("Invalid strength value. Setting to 0.")
                strength = 0
        
        # Abilities
        valid_abilities: List[str] = ["agile", "berserker", "commander", "morale", "medic", "muster", "scorch", "spy", "summon", "bond"]
        print(f"Valid abilities: {', '.join(valid_abilities)}")
        self._log.info("Prompting for card abilities")
        abilities_input = input("Abilities (comma-separated, optional): ")
        self._log.info(f"User input for card abilities: '{abilities_input}'")
        
        abilities: List[str] = [a.strip() for a in abilities_input.split(',')] if abilities_input else []
        # Validate abilities
        abilities = [a for a in abilities if a in valid_abilities]
        self._log.info(f"Validated card abilities: {abilities}")
        
        # Specialty
        valid_specialties: List[str] = ["commander", "decoy", "leader", "scorch", "weather", "hero", "mardroeme"]
        print(f"Valid specialties: {', '.join(valid_specialties)}")
        self._log.info("Prompting for card specialty")
        specialty = input("Specialty (optional): ")
        self._log.info(f"User input for card specialty: '{specialty}'")
        
        if specialty and specialty not in valid_specialties:
            self._log.info(f"Invalid specialty '{specialty}', setting to None")
            print(f"Invalid specialty. Setting to None.")
            specialty = None
        
        # Starter
        self._log.info("Prompting for starter card status")
        starter_input = input("Starter card? (yes/no, default: no): ")
        self._log.info(f"User input for starter card: '{starter_input}'")
        
        starter = starter_input.lower() in ['yes', 'y', 'true']
        self._log.info(f"Starter card status: {starter}")
        
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
        """Write a card to an RFID tag
        
        IMPORTANT: This method does NOT check if the card already has data.
        Use write_card_to_rfid_safely instead to ensure the card is blank.
        """
        self._log.warning("write_card_to_rfid called directly - this method does not check for existing data")
        self._log.info("Redirecting to write_card_to_rfid_safely for safety")
        
        # Always use the safe version that checks for existing data
        return self.write_card_to_rfid_safely(card_data)
        
    def write_card_to_rfid_safely(self, card_data: CardData) -> Optional[int]:
        """Write a card to an RFID tag, but only if the tag is blank"""
        # Clear instructions for the user
        self.console.print("\n[bold cyan]===== CARD WRITING PROCESS =====[/bold cyan]")
        self.console.print("[bold cyan]STEP 1:[/bold cyan] Place your RFID chip on the writer")
        self.console.print("[bold cyan]STEP 2:[/bold cyan] Press Enter when the chip is in position")
        self.console.print("[bold cyan]STEP 3:[/bold cyan] Keep the chip on the writer until the process completes")
        self.console.print("[bold yellow]WARNING:[/bold yellow] If the chip already contains data, the write will be aborted to prevent data loss.")
        
        # Wait for the user to place the card and press Enter
        self.console.print("\n[bold green]Please place your RFID chip on the writer and press Enter when ready (or ESC/Ctrl+C to cancel)...[/bold green]")
        try:
            key = readchar.readkey()
            if key == readchar.key.ESC:
                self._log.info("User pressed ESC to cancel card writing")
                self.console.print("\n[yellow]Card writing cancelled.[/yellow]")
                return None
        except KeyboardInterrupt:
            self._log.info("User pressed Ctrl+C to cancel card writing")
            self.console.print("\n[yellow]Card writing cancelled.[/yellow]")
            return None
        
        self.console.print("[bold cyan]Checking for RFID chip...[/bold cyan]")
        
        # Try to read the card to see if it already has data
        try:
            # First try to get just the ID of the card with multiple attempts
            self._log.info("Checking if RFID chip is present...")
            self.console.print("\n[bold cyan]Detecting RFID chip...[/bold cyan]")
            
            # Try multiple times with feedback
            max_attempts = 5
            for attempt in range(1, max_attempts + 1):
                self._log.info(f"Attempt {attempt}/{max_attempts} to detect RFID chip")
                rfid_reader = gwent.hal.rfid.instance()
                id, _ = rfid_reader._rfid.read_id(attempts=2)
                
                if id is not None:
                    break
                    
                if attempt < max_attempts:
                    self.console.print(f"[yellow]Attempt {attempt}/{max_attempts}: No chip detected. Please adjust position...[/yellow]")
                    time.sleep(0.1)  # Give user time to adjust
            
            if id is None:
                self._log.warning("No RFID chip detected after multiple attempts")
                self.console.print("\n[bold red]ERROR: No RFID chip detected after multiple attempts![/bold red]")
                self.console.print("[yellow]Please make sure the chip is placed directly on the writer and try again.[/yellow]")
                self.console.print("[yellow]Tips: Try moving the chip slightly, or use a different chip.[/yellow]")
                return None
                
            self._log.info(f"RFID chip detected with ID: {id}")
            self.console.print(f"\n[bold green]RFID chip detected with ID: {id}[/bold green]")
            
            # Now check if the card has data
            self._log.info("Checking if RFID chip has existing data...")
            self.console.print("[bold cyan]Checking if chip already contains data...[/bold cyan]")
            rfid_reader = gwent.hal.rfid.instance()
            existing_card = rfid_reader.read_card()
            
            # Check if the card has data
            if existing_card is not None:
                # Card has some data
                card_info = {}
                if hasattr(existing_card, 'name') and existing_card.name:
                    card_info['name'] = existing_card.name
                if hasattr(existing_card, 'faction') and existing_card.faction:
                    card_info['faction'] = existing_card.faction
                if hasattr(existing_card, 'rfid') and existing_card.rfid:
                    card_info['rfid'] = existing_card.rfid
                
                if card_info:
                    # Card has meaningful data
                    self._log.warning(f"RFID chip already contains data: {card_info}")
                    
                    # Create a detailed error panel using a single Text.from_markup call
                    error_message = f"This RFID chip already contains card data:\n\n"
                    
                    if 'name' in card_info:
                        error_message += f"[bold]Name:[/bold] {card_info['name']}\n"
                    if 'faction' in card_info:
                        error_message += f"[bold]Faction:[/bold] {card_info['faction']}\n"
                    if 'rfid' in card_info:
                        error_message += f"[bold]RFID:[/bold] {card_info['rfid']}\n"
                    
                    error_message += "\n[bold red]Writing to this card would overwrite existing data.[/bold red]\n"
                    error_message += "Please use a blank RFID chip or explicitly choose to overwrite."
                    
                    error_text = Text.from_markup(error_message)
                    
                    error_panel = Panel(
                        error_text,
                        title="[bold red]ERROR: RFID CHIP ALREADY HAS DATA[/bold red]",
                        border_style="red",
                        box=box.DOUBLE
                    )
                    self.console.print("\n")
                    self.console.print(error_panel)
                    
                    # Ask if the user wants to overwrite
                    self.console.print("\n[bold cyan]Do you want to overwrite the existing data? This cannot be undone! (y/n or ESC/Ctrl+C to cancel)[/bold cyan]")
                    try:
                        key = readchar.readkey()
                        if key == readchar.key.ESC:
                            self._log.info("User pressed ESC to cancel overwriting existing card data")
                            self.console.print("\n[bold green]Operation cancelled.[/bold green]")
                            return None
                        
                        overwrite = key.lower() in ['y']
                        if overwrite:
                            self._log.warning("User chose to overwrite existing card data")
                            self.console.print("\n[bold yellow]Proceeding with overwrite...[/bold yellow]")
                        else:
                            self._log.info("User chose not to overwrite existing card data")
                            self.console.print("\n[bold green]Operation cancelled.[/bold green]")
                            return None
                    except KeyboardInterrupt:
                        self._log.info("User pressed Ctrl+C to cancel overwriting existing card data")
                        self.console.print("\n[bold green]Operation cancelled.[/bold green]")
                        return None
            
            # If we get here, either the card is blank or the user has chosen to overwrite
            self._log.info("RFID chip is blank or user has chosen to overwrite. Proceeding with write...")
            
            if existing_card is None:
                self.console.print("\n[bold green]✓ Chip is blank and ready for writing[/bold green]")
            else:
                self.console.print("\n[bold yellow]⚠ Proceeding with overwrite as confirmed[/bold yellow]")
            
            # Show card details that will be written
            self.console.print(f"\n[bold cyan]Writing card data:[/bold cyan]")
            self.console.print(f"[cyan]Name:[/cyan] [green]{card_data.get('name', 'Unknown')}[/green]")
            self.console.print(f"[cyan]Faction:[/cyan] [green]{card_data.get('faction', 'Unknown')}[/green]")
            
            self.console.print("\n[bold cyan]IMPORTANT: Keep the chip on the writer until writing is complete![/bold cyan]")
            
            # Convert card data to a Message object
            card: gwent.messaging.card.Message = gwent.messaging.card.Message.from_properties(card_data)
            
            self._log.info({
                'action': 'Hold the tag steady while writing data',
                'name': card.name,
                'faction': card.faction,
            })
            
            # Use the class member RFID reader instance
            rfid: Optional[int] = None
            attempts = 0
            max_attempts = 5
            
            while rfid is None and not self._stop_event.is_set() and attempts < max_attempts:
                attempts += 1
                self._log.info(f"Write attempt #{attempts}")
                
                rfid_reader = gwent.hal.rfid.instance()
                rfid = rfid_reader.write_card(card)
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
                
                self.console.print("\n[bold green]✓ SUCCESS: Card data written successfully![/bold green]")
                self.console.print(f"[green]Card ID: {rfid}[/green]")
                self.console.print("[cyan]You can now remove the card from the writer.[/cyan]")
                
                return rfid
            else:
                self._log.error("Failed to write card after multiple attempts")
                self.console.print("\n[bold red]✗ ERROR: Failed to write card after multiple attempts.[/bold red]")
                self.console.print("[yellow]Possible causes:[/yellow]")
                self.console.print("  [yellow]- Card was removed during writing[/yellow]")
                self.console.print("  [yellow]- Card is write-protected[/yellow]")
                self.console.print("  [yellow]- Card is damaged or incompatible[/yellow]")
                self.console.print("  [yellow]- RFID reader hardware issue[/yellow]")
                self.console.print("\n[cyan]Please try again with the same or different card.[/cyan]")
                return None
            
        except Exception as e:
            # If there's an error reading the card, log it and abort
            self._log.error(f"Error checking or writing to RFID chip: {e}", exc_info=True)
            self.console.print(f"\n[bold red]Error: {e}[/bold red]")
            self.console.print("[bold red]Card writing aborted for safety.[/bold red]")
            return None

    def interactive_menu(self, title: str, options: List[str], exit_option: str = "Back") -> int:
        """Display an interactive menu with keyboard navigation and scrolling
        
        Args:
            title: The title of the menu
            options: List of menu options
            exit_option: Text for the exit/back option
            
        Returns:
            Index of the selected option (-1 for exit)
        """
        # Add the exit option
        all_options = options + [exit_option]
        
        # Initial selection
        selected = 0
        
        # Scrolling parameters
        max_visible_items = 15  # Maximum number of items to show at once
        scroll_offset = 0       # Current scroll position
        
        try:
            while True:
                # Clear the screen
                self.console.clear()
                
                # Create the menu panel
                menu_text = Text()
                menu_text.append(f"Use ↑/↓ arrows to navigate, Enter to select, Ctrl+C to exit\n\n", style="bold white")
                
                # Calculate visible range
                total_items = len(all_options)
                
                # Adjust scroll_offset if needed to keep selected item visible
                if selected < scroll_offset:
                    scroll_offset = selected
                elif selected >= scroll_offset + max_visible_items:
                    scroll_offset = selected - max_visible_items + 1
                
                # Ensure scroll_offset is within bounds
                scroll_offset = max(0, min(scroll_offset, total_items - max_visible_items))
                
                # Show scroll indicator if there are items above the visible area
                if scroll_offset > 0:
                    menu_text.append("  ↑ More options above ↑\n", style="bold yellow")
                
                # Display visible items
                visible_end = min(scroll_offset + max_visible_items, total_items)
                for i in range(scroll_offset, visible_end):
                    option = all_options[i]
                    if i == selected:
                        # Highlight the selected option
                        menu_text.append(f"▶ {option}\n", style="bold green")
                    else:
                        style = "bold red" if i == len(all_options) - 1 else "cyan"
                        menu_text.append(f"  {option}\n", style=style)
                
                # Show scroll indicator if there are items below the visible area
                if visible_end < total_items:
                    menu_text.append("  ↓ More options below ↓\n", style="bold yellow")
                
                # Add scrolling instructions if the list is scrollable
                if total_items > max_visible_items:
                    menu_text.append(f"\nShowing {visible_end - scroll_offset} of {total_items} options", style="dim")
                
                panel = Panel(
                    menu_text,
                    title=f"[bold yellow]{title}[/bold yellow]",
                    border_style="bright_blue",
                    box=box.DOUBLE
                )
                
                # Print the panel
                self.console.print(panel)
                
                try:
                    # Get key press with exception handling
                    key = readchar.readkey()
                    
                    # Handle key press
                    if key == readchar.key.UP or key == 'k':
                        selected = max(0, selected - 1)
                    elif key == readchar.key.DOWN or key == 'j':
                        selected = min(len(all_options) - 1, selected + 1)
                    elif key == readchar.key.PAGE_UP:
                        # Jump up by max_visible_items
                        selected = max(0, selected - max_visible_items)
                    elif key == readchar.key.PAGE_DOWN:
                        # Jump down by max_visible_items
                        selected = min(len(all_options) - 1, selected + max_visible_items)
                    elif key == readchar.key.HOME:
                        # Jump to the first item
                        selected = 0
                    elif key == readchar.key.END:
                        # Jump to the last item
                        selected = len(all_options) - 1
                    elif key == readchar.key.ENTER:
                        # Return -1 for exit option
                        if selected == len(all_options) - 1:
                            self._log.info(f"User selected: {exit_option} from menu '{title}'")
                            return -1
                        
                        selected_option = all_options[selected]
                        self._log.info(f"User selected: '{selected_option}' from menu '{title}'")
                        return selected
                    elif key == readchar.key.CTRL_C or key == readchar.key.ESC:
                        # ESC key now acts like selecting the "Back" option
                        self._log.info(f"User pressed ESC to go back from menu '{title}'")
                        return -1
                except KeyboardInterrupt:
                    # Handle Ctrl+C - now acts like selecting the "Back" option
                    self._log.info(f"User pressed Ctrl+C to go back from menu '{title}'")
                    return -1
        except Exception as e:
            self._log.error(f"Error in interactive menu: {e}", exc_info=True)
            self._stop_event.set()  # Set the stop event to exit gracefully
            return -1
    
    def display_menu(self) -> str:
        """Display the main menu and get user selection"""
        options = ["Read card", "Write card"]
        
        self._log.info("Displaying main menu")
        selected = self.interactive_menu("CARD MANAGER MENU", options, "Exit")
        
        if selected == -1:
            # This could be from selecting "Exit" or pressing ESC/Ctrl+C
            self._log.info("User selected to exit the application")
            return '0'  # Exit
        else:
            choice = str(selected + 1)  # 1-based indexing for compatibility
            self._log.info(f"User selected main menu option: {options[selected]} (choice {choice})")
            return choice
    
    def handle_read_card(self) -> None:
        """Handle the 'Read card' option"""
        self._log.info("=== Starting handle_read_card() ===")
        
        # Read the RFID card with additional logging
        self._log.info("Calling read_rfid_card()")
        self.console.print("\n[bold cyan]Please place a card on the reader...[/bold cyan]")
        
        try:
            card: Optional[gwent.messaging.card.Message] = self.read_rfid_card()
        except Exception as e:
            self._log.error(f"Exception during card read: {e}", exc_info=True)
            self.console.print(f"\n[bold red]Error reading card: {e}[/bold red]")
            self.console.print("[yellow]Please try again or use a different card.[/yellow]")
            self._log.info("=== Ending handle_read_card() - exception during read ===")
            return
        
        # Check if a card was detected
        if card is None:
            # No card detected at all
            self._log.error("No card detected or operation was cancelled")
            self.console.print("\n[bold red]No card detected or operation was cancelled.[/bold red]")
            self.console.print("[yellow]Please make sure the card is properly positioned on the reader.[/yellow]")
            self._log.info("=== Ending handle_read_card() - no card detected ===")
            return
        
        # Check if this is a blank card (has RFID but no other data)
        is_blank_card = hasattr(card, 'rfid') and card.rfid and not (hasattr(card, 'name') and hasattr(card, 'faction'))
        
        if is_blank_card:
            # This is a blank card with just an RFID
            id = card.rfid
            self._log.info(f"Detected blank or uninitialized card with ID: {id}")
            self.console.print("\n[bold yellow]Blank or uninitialized card detected.[/bold yellow]")
            self.console.print(f"Card ID: {id}")
            
            # Ask if the user wants to initialize this card
            self.console.print("\n[bold cyan]Would you like to initialize this card? (y/n or ESC/Ctrl+C to cancel)[/bold cyan]")
            try:
                key = readchar.readkey()
                if key == readchar.key.ESC:
                    self._log.info("User pressed ESC to cancel card initialization")
                    self.console.print("[yellow]Card initialization cancelled.[/yellow]")
                    return
                
                initialize = key.lower() in ['y']
                if initialize:
                    self._log.info("User chose to initialize blank card")
                else:
                    self._log.info("User chose not to initialize blank card")
                    self.console.print("[yellow]Card initialization cancelled.[/yellow]")
                    return
            except KeyboardInterrupt:
                self._log.info("User pressed Ctrl+C to cancel card initialization")
                self.console.print("[yellow]Card initialization cancelled.[/yellow]")
                return
                
            if True:  # This block was previously inside the Confirm.ask() condition
                
                # Ask how they want to initialize the card
                self.console.print("\n[bold cyan]How would you like to initialize this card?[/bold cyan]")
                options = ["Select an existing card from database", "Manually enter card details"]
                selected = self.interactive_menu("CARD INITIALIZATION", options, "Cancel initialization")
                
                if selected == -1:
                    self._log.info("User cancelled card initialization")
                    self.console.print("\n[yellow]Card initialization cancelled.[/yellow]")
                    return
                
                card_data = None
                
                if selected == 0:  # Select existing card
                    self._log.info("User chose to select an existing card from database")
                    
                    # Select faction
                    faction_dir = self.select_faction()
                    if faction_dir is None:
                        self._log.info("User cancelled faction selection")
                        self.console.print("\n[yellow]Card initialization cancelled.[/yellow]")
                        return
                    
                    # Select card file, including those with RFID (we'll just copy the data)
                    card_file = self.select_card_file(faction_dir, exclude_with_rfid=False)
                    if card_file is None:
                        self._log.info("User cancelled card selection")
                        self.console.print("\n[yellow]Card initialization cancelled.[/yellow]")
                        return
                    
                    # Read card data from file
                    try:
                        with open(card_file, 'r') as f:
                            card_data = json.load(f)
                            
                        # Create a copy of the card data without the RFID
                        if 'rfid' in card_data:
                            self._log.info(f"Removing existing RFID {card_data['rfid']} from template card")
                            del card_data['rfid']
                            
                        self._log.info(f"Using card template: {card_data.get('name', 'Unknown')}")
                        self.console.print(f"\n[bold green]Using card template: {card_data.get('name', 'Unknown')}[/bold green]")
                    except Exception as e:
                        self._log.error(f"Error reading card file: {e}", exc_info=True)
                        self.console.print(f"\n[bold red]Error reading card file: {e}[/bold red]")
                        return
                else:  # Manually enter details
                    self._log.info("User chose to manually enter card details")
                    # Prompt for card details
                    card_data = self.prompt_for_card_details()
                
                if card_data:
                    # Add RFID to the card data
                    card_data['rfid'] = id
                    
                    # Write the card to the database
                    file_path = self.write_card_to_database(card_data)
                    self._log.info(f"Card written to {file_path}")
                    
                    # Write the card to the RFID chip
                    rfid = self.write_card_to_rfid_safely(card_data)
                    if rfid is not None:
                        self.console.print(f"\n[bold green]Card successfully initialized with ID: {rfid}[/bold green]")
                        self._log.info(f"Card initialized with ID: {rfid}")
                    else:
                        self.console.print("\n[bold red]Failed to initialize card.[/bold red]")
                        self._log.error("Failed to initialize card")
            
            self._log.info("=== Ending handle_read_card() - blank card handling complete ===")
            return
        # Try to find the card in the database
        card_data: Optional[CardData] = None
        card_file: Optional[FilePath] = None
    
        try:
            # First try by RFID if available
            if hasattr(card, 'rfid') and card.rfid:
                card_data, card_file = self.find_card_in_database(card.rfid)
            
            # Try by name and faction if available and card is not blank
            if card_data is None and not is_blank_card and hasattr(card, 'name') and hasattr(card, 'faction'):
                # For weather cards, strip any number suffix
                name = card.name
                if hasattr(card, 'instance') and card.instance.get('specialty') == 'weather':
                    # Strip number suffix from weather card names
                    name = re.sub(r': \d+$', '', name)
                    self._log.info(f"Searching for weather card with normalized name: {name}")
                
                self._log.info(f"Trying to find card by name and faction: {name}, {card.faction}")
                card_data, card_file = self.find_card_by_name_and_faction(name, card.faction)
        except Exception as e:
            self._log.error(f"Error finding card: {e}", exc_info=True)
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
                
                # Write the updated card data back to the file
                if card_file:
                    try:
                        with open(card_file, 'w') as f:
                            json.dump(card_data, f, indent=4)
                        self._log.info(f"Updated card file: {card_file}")
                    except Exception as e:
                        self._log.error(f"Error updating card file: {e}", exc_info=True)
            
            # Display the card details from the database
            try:
                display = self.format_card_display(
                    card_data,
                    header_text="CARD FOUND",
                    file_path=card_file,
                    show_additional_info=True
                )
                # Ensure we're printing the panel correctly
                self.console.print(display)
                self._log.info("Pretty printed card details to console")
            except Exception as e:
                self._log.error(f"Error displaying card details: {e}", exc_info=True)
                # Fallback display method
                self.console.print(f"\n[bold green]Card found: {card_data.get('name', 'Unknown')}[/bold green]")
                self.console.print(f"[cyan]Faction:[/cyan] {card_data.get('faction', 'Unknown')}")
                self.console.print(f"[cyan]RFID:[/cyan] {card_data.get('rfid', 'Unknown')}")
            
            # If the card was updated, inform the user
            if updated:
                self.console.print("\n[bold green]Card database entry updated with RFID.[/bold green]")
        else:
            # Card not found in database
            self._log.info("Card not found in database")
            self.console.print("\n[bold yellow]Card not found in database.[/bold yellow]")
                    
        # Prompt user to press Enter to return to the menu
        self._log.info("Prompting user to press Enter to return to the menu")
        self.console.print("\n[bold cyan]Press Enter to return to the menu (or ESC/Ctrl+C)...[/bold cyan]")
        try:
            # Check if a key is pressed without blocking
            key = readchar.readkey()
            if key == readchar.key.ESC:
                self._log.info("User pressed ESC to return to the menu")
                self.console.print("\n[yellow]Returning to menu...[/yellow]")
            else:
                self._log.info("User pressed a key to return to the menu")
        except KeyboardInterrupt:
            self._log.info("User interrupted the prompt with Ctrl+C")
            self.console.print("\n[yellow]Returning to menu...[/yellow]")
        
        # Add a delay before returning to the menu to allow the RFID reader to reset
        self._log.info("Adding 0.1s delay before returning to menu")
        time.sleep(0.1)
        self._log.info("=== Ending handle_read_card() ===")
    
    def select_faction(self) -> Optional[str]:
        """Display a list of factions and let the user select one"""
        # Get a list of faction directories
        factions = []
        for faction_dir in os.listdir(self.cards_dir):
            faction_path = os.path.join(self.cards_dir, faction_dir)
            if os.path.isdir(faction_path):
                factions.append(faction_dir)
        
        self._log.info(f"Found {len(factions)} factions: {', '.join(factions)}")
        
        if not factions:
            self._log.warning("No faction directories found")
            self.console.print("[bold red]No faction directories found.[/bold red]")
            return None
        
        # Display interactive menu
        self._log.info("Displaying faction selection menu")
        selected = self.interactive_menu("SELECT FACTION", factions, "Back to main menu")
        
        if selected == -1:
            self._log.info("User cancelled faction selection")
            return None
        else:
            selected_faction = factions[selected]
            self._log.info(f"User selected faction: {selected_faction}")
            return selected_faction
    
    def select_card_file(self, faction_dir: str, exclude_with_rfid: bool = False) -> Optional[str]:
        """Display a list of card files in the faction directory and let the user select one
        
        Args:
            faction_dir: The faction directory to list cards from
            exclude_with_rfid: If True, exclude cards that already have an RFID assigned
        """
        # Get a list of card files
        faction_path = os.path.join(self.cards_dir, faction_dir)
        card_files_dict = {}  # Dictionary to map card names to file paths
        excluded_count = 0
        
        self._log.info(f"Searching for cards in faction: {faction_dir}")
        self._log.info(f"Exclude cards with RFID: {exclude_with_rfid}")
        
        for json_file in glob.glob(os.path.join(faction_path, "*.json")):
            # If we need to exclude cards with RFID, check the file content
            if exclude_with_rfid:
                try:
                    with open(json_file, 'r') as f:
                        card_data = json.load(f)
                        # Skip this card if it already has an RFID
                        if 'rfid' in card_data:
                            excluded_count += 1
                            continue
                except Exception as e:
                    self._log.error(f"Error reading {json_file}: {e}", exc_info=True)
                    # If there's an error reading the file, skip it
                    continue
            
            # Extract the card name from the file path
            card_name = os.path.basename(json_file).replace('.json', '')
            card_files_dict[card_name] = json_file
        
        self._log.info(f"Found {len(card_files_dict)} cards in faction {faction_dir}")
        if exclude_with_rfid:
            self._log.info(f"Excluded {excluded_count} cards that already have RFID")
        
        if not card_files_dict:
            if exclude_with_rfid:
                self._log.warning(f"No cards without RFID found in {faction_path}")
                self.console.print(f"[bold red]No cards without RFID found in {faction_path}.[/bold red]")
            else:
                self._log.warning(f"No card files found in {faction_path}")
                self.console.print(f"[bold red]No card files found in {faction_path}.[/bold red]")
            return None
        
        # Sort card names alphabetically
        sorted_card_names = sorted(card_files_dict.keys())
        
        # Display interactive menu
        self._log.info(f"Displaying card selection menu for faction {faction_dir}")
        selected = self.interactive_menu(f"SELECT CARD - {faction_dir}", sorted_card_names, "Back to faction selection")
        
        if selected == -1:
            self._log.info("User cancelled card selection")
            return None
        else:
            selected_card_name = sorted_card_names[selected]
            selected_card_file = card_files_dict[selected_card_name]
            self._log.info(f"User selected card: {selected_card_name} ({selected_card_file})")
            return selected_card_file
    
    def handle_write_card(self) -> None:
        """Handle the 'Write card' option"""
        # Select faction
        faction_dir = self.select_faction()
        if faction_dir is None:
            return
        
        # Continuously select cards for writing until 0 is selected
        while True:
            # Select card file, excluding those that already have an RFID
            card_file = self.select_card_file(faction_dir, exclude_with_rfid=True)
            if card_file is None:
                # User selected 0 to go back
                break
            
            # Read card data from file
            try:
                with open(card_file, 'r') as f:
                    card_data = json.load(f)
            except Exception as e:
                self._log.error(f"Error reading card file: {e}", exc_info=True)
                print(f"Error reading card file: {e}")
                continue
            
            # Display card information
            display = self.format_card_display(
                card_data,
                "SELECTED CARD",
                file_path=card_file,
                show_additional_info=True
            )
            self.console.print(display)
            
            # Confirm with user
            self._log.info(f"Prompting user to confirm writing card: {card_data.get('name', 'Unknown')}")
            self.console.print("\n[bold cyan]Write this card to an RFID chip? (y/n or ESC/Ctrl+C to cancel):[/bold cyan]")
            try:
                key = readchar.readkey()
                if key == readchar.key.ESC:
                    self._log.info(f"User pressed ESC to cancel writing card: {card_data.get('name', 'Unknown')}")
                    self.console.print("[bold yellow]Operation cancelled.[/bold yellow]")
                    continue
                confirm = key
                self._log.info(f"User input for write confirmation: '{confirm}'")
                
                if confirm.lower() not in ['y', 'yes']:
                    self._log.info(f"User cancelled writing card: {card_data.get('name', 'Unknown')}")
                    self.console.print("[bold yellow]Operation cancelled.[/bold yellow]")
                    continue
            except KeyboardInterrupt:
                self._log.info(f"User pressed Ctrl+C to cancel writing card: {card_data.get('name', 'Unknown')}")
                self.console.print("[bold yellow]Operation cancelled.[/bold yellow]")
                continue
            
            self._log.info(f"User confirmed writing card: {card_data.get('name', 'Unknown')} to RFID chip")
            
            # Write card to RFID tag - we'll check if it's blank during the write process
            
            # Create a modified version of write_card_to_rfid that checks for existing data
            rfid = self.write_card_to_rfid_safely(card_data)
            
            if rfid:
                # Update the card data with the RFID
                card_data['rfid'] = rfid
                
                # Write the updated card data to the file
                try:
                    with open(card_file, 'w') as f:
                        json.dump(card_data, f, indent=4)
                    self.console.print(f"\n[bold green]Card successfully written to RFID chip with ID: {rfid}[/bold green]")
                    self.console.print(f"[green]Card file updated with RFID: {card_file}[/green]")
                except Exception as e:
                    self._log.error(f"Error updating card file with RFID: {e}", exc_info=True)
                    self.console.print(f"[bold red]Error updating card file with RFID: {e}[/bold red]")
            else:
                self.console.print("\n[bold red]Failed to write card to RFID chip[/bold red]")
            
            # Ask if the user wants to write another card
            self._log.info("Prompting user to write another card")
            self.console.print("\n[bold cyan]Write another card? (y/n or ESC/Ctrl+C to cancel):[/bold cyan]")
            try:
                key = readchar.readkey()
                if key == readchar.key.ESC:
                    self._log.info("User pressed ESC to cancel writing more cards")
                    self.console.print("[yellow]Returning to main menu...[/yellow]")
                    break
                another = key
                self._log.info(f"User input for write another card: '{another}'")
                
                if another.lower() not in ['y', 'yes']:
                    self._log.info("User chose not to write another card")
                    break
            except KeyboardInterrupt:
                self._log.info("User pressed Ctrl+C to cancel writing more cards")
                self.console.print("[yellow]Returning to main menu...[/yellow]")
                break
            
            self._log.info("User chose to write another card")
    
    def run(self) -> None:
        """Run the card manager utility"""
        self.setup_signal_handlers()
        
        self.console.print("\n[bold blue]Card Manager Utility[/bold blue]")
        self.console.print("[dim]Press Ctrl+C to exit[/dim]\n")
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Display menu and get user choice
                    choice = self.display_menu()
                    
                    if choice == '1':
                        # Read card
                        self.handle_read_card()
                    elif choice == '2':
                        # Write card
                        self.handle_write_card()
                    elif choice == '0':
                        # Exit
                        self.console.print("[bold yellow]Exiting...[/bold yellow]")
                        break
                    else:
                        self.console.print("[bold red]Invalid choice. Please enter 0, 1, or 2.[/bold red]")
                except KeyboardInterrupt:
                    # Handle Ctrl+C gracefully - treat as "Exit" selection
                    self._log.info("User pressed Ctrl+C at main menu")
                    self.console.print("\n[bold yellow]Exiting...[/bold yellow]")
                    break
                except Exception as e:
                    self._log.error(f"Error during card processing: {e}", exc_info=True)
                    self.console.print(f"\n[bold red]Error: {e}[/bold red]")
                    self.console.print("[yellow]Continuing...[/yellow]")
                    time.sleep(0.1)
        finally:
            # Ensure cleanup happens regardless of how we exit the loop
            self.cleanup()


def setup_logging():
    """Set up logging to file"""
    # Create tmp directory if it doesn't exist
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'tmp'))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set up log file path
    log_file = os.path.join(log_dir, 'card-manager.log')
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers to avoid duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    root_logger.addHandler(file_handler)
    
    # Log startup message
    logging.info(f"Card Manager started with DEBUG logging enabled. Logging to {log_file}")
    
    return log_file

def main() -> int:
    """Command-line entry point for the card manager utility"""
    # Set up logging to file
    log_file = setup_logging()
    
    # Display startup message
    console = Console()
    console.print(f"\n[bold blue]Card Manager Utility[/bold blue]")
    console.print(f"[dim]Logging to {log_file}[/dim]")
    
    # Create and run the card manager utility with verbose logging enabled
    manager = CardManager(log_verbose=True)
    manager.run()
    
    # Ensure we catch any exceptions at the top level
    try:
        return 0
    except Exception as e:
        logging.error(f"Unhandled exception in main: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())