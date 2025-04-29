import json
import os
import signal
import sys
import time
import threading
import hashlib
import glob
import re
import argparse
import select
from typing import Dict, List, Tuple, Optional, Any, Union, Callable

# Import gwent logging utilities
from gwent.utils.logging import configure_logging, get_logger

# Rich library imports
from rich.console import Console, RenderableType
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt, Confirm, IntPrompt, PromptBase
from rich.theme import Theme
from rich.style import Style
from rich.highlighter import Highlighter
import readchar

# Import gwent modules
import gwent.game
import gwent.messaging.base
import gwent.cards.all
import gwent.messaging.card
from gwent.messaging.card import NAME, FACTION, RFID, BlankCardMessage  # Import constants
import gwent.cards.util
import gwent.hal.rfid
import RPi.GPIO as GPIO  # Import GPIO library to suppress warnings

# Type aliases
CardData = Dict[str, Any]
FilePath = str

# Menu entry type definition
MenuEntry = Dict[str, Any]

class CardManager(gwent.game.BaseComponent):
    def __init__(self):
        super().__init__()
        # Get a logger for this component
        self._log = get_logger("gwent.poc.util.card_manager")
        self._stop_event = threading.Event()
        self.cards_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                       '..', '..', '..', '..', 'data', 'cards'))
        # Suppress GPIO warnings
        GPIO.setwarnings(False)
        # No longer initializing RFID reader as a class member
        self._log.info({
            'action': 'card_manager_initialized',
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
        
    def get_user_confirmation(self, prompt_text: str, default_yes: bool = True) -> bool:
        """Get confirmation from the user with a consistent interface
        
        Args:
            prompt_text: The text to display to the user
            default_yes: Whether the default answer is Yes
            
        Returns:
            True if confirmed, False otherwise
        """
        self.console.print(f"\n[bold cyan]{prompt_text} (y/n or Enter to confirm, ESC to cancel):[/bold cyan]")
        key = readchar.readkey()
        if key == readchar.key.ESC:
            self._log.info("User pressed ESC to cancel")
            self.console.print("[bold yellow]Operation cancelled.[/bold yellow]")
            return False
            
        # Accept 'y', 'yes', or Enter (CR or LF) as confirmation
        if default_yes:
            confirmed = key.lower() not in ['n', 'no']
        else:
            confirmed = key.lower() in ['y', 'yes', '\r', '\n', readchar.key.ENTER]
            
        # Log what key was used for confirmation
        if key.lower() in ['\r', '\n', readchar.key.ENTER]:
            self._log.info("User pressed Enter")
        else:
            self._log.info(f"User pressed '{key}'")
            
        if confirmed:
            self._log.info("User confirmed")
        else:
            self._log.info("User declined")
            self.console.print("[bold yellow]Operation cancelled.[/bold yellow]")
            
        return confirmed
        # CTRL-C will now exit the program as we're not catching KeyboardInterrupt

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
    
    def format_card_display(self, card_data: gwent.messaging.card.Message,
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
        
        # Check if this is a blank card
        is_blank_card = isinstance(card_data, BlankCardMessage)
        
        # Get card properties
        name = card_data.name
        faction = card_data.faction
        rfid = str(card_data.rfid)
        
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
        strength = card_data.strength
        card_text.append("Strength: ", style="cyan")
        if strength is not None:
            card_text.append(f"{strength}\n", style="green")
        else:
            card_text.append("N/A\n", style="green")
            
        # Ranges
        ranges = card_data.ranges
        card_text.append("Ranges:   ", style="cyan")
        if ranges:
            ranges_str = ', '.join(ranges)
            card_text.append(f"{ranges_str}\n", style="green")
        else:
            card_text.append("N/A\n", style="green")
            
        # Specialty
        specialty = card_data.specialty
        card_text.append("Specialty: ", style="cyan")
        if specialty:
            card_text.append(f"{specialty}\n", style="green")
        else:
            card_text.append("None\n", style="green")
            
        # Abilities
        abilities = card_data.abilities
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
            owner = card_data.owner
            card_text.append("Owner:       ", style="cyan")
            if owner:
                card_text.append(f"{owner}\n", style="green")
            else:
                card_text.append("None\n", style="green")
                
            # Starter card
            starter = card_data.is_starter
            card_text.append("Starter card: ", style="cyan")
            if starter:
                card_text.append("Yes\n", style="green")
            else:
                card_text.append("No\n", style="green")
            
            # RFID
            card_text.append("RFID:         ", style="cyan")
            if hasattr(card_data, 'rfid') and card_data.rfid:
                card_text.append(f"{card_data.rfid}\n", style="green")
            else:
                card_text.append("Not assigned\n", style="green")
                
            # Content ID
            content_id = card_data.content_id
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
    
    def pretty_print_card(self, card: gwent.messaging.card.Message, 
                          header_text="RFID CARD", 
                          file_path: Optional[str] = None,
                          show_additional_info: bool = False) -> None:
        """Pretty print a card to the console"""
        if card is None:
            return
        
        # Format the card display
        display = self.format_card_display(card, header_text, 
                                           file_path=file_path,
                                           show_additional_info=show_additional_info)
        
        # Print the formatted display
        self.console.print(display)
        
        # Add debug log to verify the method is being called
        self._log.info("Pretty printed card to console")

    def read_rfid_card(self, non_blocking: bool = False) -> Optional[gwent.messaging.card.Message]:
        """Read a card using the RFID reader
        
        Args:
            non_blocking: If True, don't wait for user input and return immediately if no card is found
        """
        if not non_blocking:
            # Original interactive behavior
            self.console.print("\n[bold cyan]===== CARD READING PROCESS =====[/bold cyan]")
            self.console.print("[bold cyan]STEP 1:[/bold cyan] Place your card on the reader")
            self.console.print("[bold cyan]STEP 2:[/bold cyan] Press Enter when the card is in position")
            self.console.print("[bold cyan]STEP 3:[/bold cyan] Keep the card on the reader until the process completes")
            
            # Wait for the user to place the card and press Enter
            self.console.print("\n[bold green]Please place your card on the reader and press Enter when ready (or ESC/Ctrl+C to cancel)...[/bold green]")
            key = readchar.readkey()
            if key == readchar.key.ESC:
                self._log.info("User pressed ESC to cancel card reading")
                self.console.print("\n[yellow]Card reading cancelled.[/yellow]")
                return None
            # Remove KeyboardInterrupt handling to allow CTRL-C to exit the program
            
            self._log.info("User confirmed card is placed on reader")
            self.console.print("[bold cyan]Reading card...[/bold cyan]")
        
        # First check if a card is physically present by reading its ID
        rfid_reader = gwent.hal.rfid.instance()
        id, _ = rfid_reader._rfid.read_id(attempts=1 if non_blocking else 3)
        if id is None:
            if not non_blocking:
                self._log.warning("No card detected on reader")
                self.console.print("\n[bold red]ERROR: No card detected on reader![/bold red]")
                self.console.print("[yellow]Please make sure a card is placed on the reader and try again.[/yellow]")
            return None
            
        if not non_blocking:
            self._log.info(f"Card detected with ID: {id}")
            self.console.print(f"[green]Card detected with ID: {id}[/green]")
        
        # Log the start time of the read operation
        start_time = time.time()
        self._log.info(f"Starting card data read at timestamp: {start_time}")
        
        # Now try to read the card data
        card: Optional[gwent.messaging.card.Message] = None
        max_attempts = 1 if non_blocking else 2  # Limit attempts to avoid excessive retries
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
            if attempts < max_attempts and not non_blocking:
                self.console.print(f"[yellow]Attempt {attempts}/{max_attempts}: No card data read. Trying again...[/yellow]")
                # Small delay between attempts
                time.sleep(0.5)
        
        # If we still couldn't read card data but we have an ID, it's likely a blank card
        if card is None and id is not None:
            self._log.info(f"Card with ID {id} appears to be blank or uninitialized")
            if not non_blocking:
                self.console.print("\n[bold yellow]Card detected but appears to be blank or uninitialized.[/bold yellow]")
            
            # Create a minimal card object with just the RFID
            # This will allow the handle_read_card method to recognize it as a blank card
            # that needs initialization rather than a completely missing card
            card = gwent.messaging.card.Message.from_properties(rfid=id)
        
        # Log the end time and duration of the read operation
        end_time = time.time()
        duration = end_time - start_time
        self._log.info(f"Card read completed at timestamp: {end_time}, duration: {duration:.2f}s, attempts: {attempts}")
            
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
        self.console.print("\n[bold green]Please place your RFID chip on the writer and press Enter when ready (or ESC to cancel)...[/bold green]")
        key = readchar.readkey()
        if key == readchar.key.ESC:
            self._log.info("User pressed ESC to cancel card writing")
            self.console.print("\n[yellow]Card writing cancelled.[/yellow]")
            return None
        # CTRL-C will now exit the program as we're not catching KeyboardInterrupt
        
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
            if existing_card is not None and not isinstance(existing_card, BlankCardMessage):
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
                    if not self.get_user_confirmation("Do you want to overwrite the existing data? This cannot be undone!"):
                        self.console.print("\n[bold green]Operation cancelled.[/bold green]")
                        return None
                        
                    self._log.warning("User chose to overwrite existing card data")
                    self.console.print("\n[bold yellow]Proceeding with overwrite...[/bold yellow]")
            
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

    def create_menu_structure(self):
        """Create the menu structure with handlers
        
        Returns:
            Dictionary of menus with their options and handlers
        """
        # Define the main menu with all necessary information
        main_menu = [
            {
                "id": "1",
                "label": "Read card",
                "handler": self.handle_read_card,
                "description": "Read and display card information"
            },
            {
                "id": "2",
                "label": "Write card",
                "handler": self.handle_write_card,
                "args": {"show_rfid_cards": True},
                "description": "Write card data to an RFID chip"
            }
        ]
        
        return {
            "main": main_menu
        }
    
    def interactive_menu(self, title: str, menu_entries: List[Union[MenuEntry, str]], exit_option: str = "Back") -> Optional[MenuEntry]:
        """Display an interactive menu with keyboard navigation and scrolling
        
        Args:
            title: The title of the menu
            menu_entries: List of menu entries (dicts with 'label', etc.) or strings
            exit_option: Text for the exit/back option
            
        Returns:
            Selected menu entry or None for exit
        """
        # Extract just the labels for display
        options = []
        for entry in menu_entries:
            if isinstance(entry, dict):
                # If it's a dict with 'label' and optional 'id'
                if 'id' in entry and entry['id']:
                    options.append(f"{entry['id']} - {entry['label']}")
                else:
                    options.append(entry["label"])
            else:
                # If it's just a string
                options.append(entry)
        
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
                
                # Get key press - no exception handling to allow CTRL-C to exit the program
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
                    # Return None for exit option
                    if selected == len(all_options) - 1:
                        self._log.info(f"User selected: {exit_option} from menu '{title}'")
                        return None
                    
                    selected_option = all_options[selected]
                    self._log.info(f"User selected: '{selected_option}' from menu '{title}'")
                    
                    # Return the selected entry or create one if it was a string
                    if isinstance(menu_entries[selected], dict):
                        return menu_entries[selected]
                    else:
                        return {"label": menu_entries[selected]}
                elif key == readchar.key.ESC:
                    # ESC key acts like selecting the "Back" option
                    self._log.info(f"User pressed ESC to go back from menu '{title}'")
                    return None
                # CTRL-C will now exit the program as we're not catching KeyboardInterrupt
        except Exception as e:
            self._log.error(f"Error in interactive menu: {e}", exc_info=True)
            self._stop_event.set()  # Set the stop event to exit gracefully
            return None
    
    def display_menu(self) -> dict:
        """Display the main menu and get user selection
        
        Returns:
            Selected menu entry or None if exit was chosen
        """
        # Get the menu structure
        menus = self.create_menu_structure()
        main_menu = menus["main"]
        
        self._log.info("Displaying main menu")
        handler = self.interactive_menu("CARD MANAGER MENU", main_menu, "Exit")
        
        if handler is None:
            # This could be from selecting "Exit" or pressing ESC/Ctrl+C
            self._log.info("User selected to exit the application")
            return None  # Exit
        else:
            self._log.info(f"User selected main menu option: {handler['label']} (id {handler['id']})")
            return handler
    
    def handle_read_card(self, cooldown_period: float = 2.0) -> None:
        """Handle the 'Read card' option with continuous scanning
        
        Args:
            cooldown_period: Seconds to wait before reading the same card again
        """
        self._log.info("=== Starting handle_read_card() with continuous scanning ===")
        
        # Clear the screen and show instructions
        self.console.clear()
        self.console.print("\n[bold cyan]===== CONTINUOUS CARD SCANNING MODE =====[/bold cyan]")
        self.console.print("[bold green]Place cards on the reader to scan them[/bold green]")
        self.console.print("[bold yellow]Press ENTER or ESC at any time to return to the main menu[/bold yellow]")
        
        # Keep track of the last card ID to avoid duplicate readings
        last_card_id = None
        last_read_time = 0
        
        try:
            # Main scanning loop
            while not self._stop_event.is_set():
                # Check for key presses (non-blocking)
                rlist, _, _ = select.select([sys.stdin], [], [], 0.001)
                if rlist:
                    key = readchar.readkey()
                    if key == readchar.key.ESC or key == readchar.key.ENTER:
                        self._log.info(f"User pressed {'ESC' if key == readchar.key.ESC else 'ENTER'} to exit continuous scanning mode")
                        self.console.print("\n[yellow]Exiting scanning mode...[/yellow]")
                        break
                
                # Try to read a card without blocking
                try:
                    card = self.read_rfid_card(non_blocking=True)
                    
                    # Process the card if one was detected
                    if card is not None and hasattr(card, 'rfid'):
                        self._log.info(f"Card detected with ID: {card.rfid}")
                            
                        # Display basic information that we've detected a card
                        card_text = Text()
                        card_text.append("Card present:\t", style="bold cyan")
                        card_text.append(f"{card.rfid}", style="green")
                        panel = Panel(
                            card_text,
                            title=f"[bold yellow]RFID Activity[/bold yellow]",
                            border_style="bright_blue",
                            box=box.DOUBLE,
                            width=80,
                            expand=False
                        )                          
                        self.console.print(panel)                    

                        self._process_scanned_card(card)
                        
                        # After processing a card, check for key press immediately
                        # This helps ensure we don't miss a key press right after displaying a card
                        rlist, _, _ = select.select([sys.stdin], [], [], 0.001)
                        if rlist:
                            key = readchar.readkey()
                            if key == readchar.key.ESC or key == readchar.key.ENTER:
                                self._log.info(f"User pressed {'ESC' if key == readchar.key.ESC else 'ENTER'} to exit continuous scanning mode")
                                self.console.print("\n[yellow]Exiting scanning mode...[/yellow]")
                                break

                        message = f"Waiting {cooldown_period} seconds before scanning next card\n"
                        self._log.info(message)
                        self.console.print(f"[dim]{message}[/dim]")
                        time.sleep(cooldown_period)

                        self.console.print("[green]Place another card to scan or press ENTER/ESC to return to main menu[/green]")

                except Exception as e:
                    # Log the error but don't display it to the user
                    self._log.error(f"Error during continuous card scanning: {e}", exc_info=True)
                
                # Small delay to prevent CPU hogging
                time.sleep(0.1)
                
        except Exception as e:
            self._log.error(f"Exception in continuous scanning mode: {e}", exc_info=True)
        finally:
            self._log.info("=== Ending handle_read_card() continuous scanning ===")
            
    def _process_scanned_card(self, card) -> None:
        """Process a scanned card and display its information
        
        Args:
            card: The card object from the RFID reader
        """

        # Display the card from the scanner
        self._log.info(f"Displaying scanned card: {card.name, 'Unknown'}")

        # Use the pretty_print_card method to display the card
        # Clear any previous output to ensure the card is visible
        self.pretty_print_card(card, header_text="RFID CARD")

        # Check if this is a blank card
        is_blank_card = not (hasattr(card, 'name') and hasattr(card, 'faction'))
        
        if is_blank_card:
            # This is a blank card with just an RFID
            self.console.print("\n[bold yellow]Blank or uninitialized card detected[/bold yellow]")
            self.console.print(f"[yellow]Card ID: {card.rfid}[/yellow]")
            return
            
        # Try to find the card in the database
        card_data = None
        card_file = None
        
        try:
            # First try by RFID
            card_data, card_file = self.find_card_in_database(card.rfid)
            
            # Try by name and faction if needed
            if card_data is None and hasattr(card, 'name') and hasattr(card, 'faction'):
                # For weather cards, strip any number suffix
                name = card.name
                if hasattr(card, 'instance') and card.instance.get('specialty') == 'weather':
                    name = re.sub(r': \d+$', '', name)
                
                card_data, card_file = self.find_card_by_name_and_faction(name, card.faction)
        except Exception as e:
            self._log.error(f"Error finding card: {e}", exc_info=True)
        
        # Display card information
        if card_data:
            # Display the card from the database - ensure this is always shown
            self._log.info(f"Displaying card: {card_data.get('name', 'Unknown')}")

            try:
                # Convert dictionary to Message object
                card_obj = gwent.messaging.card.Message.from_properties(card_data)
                
                # Use the pretty_print_card method to display the card
                self.pretty_print_card(card_obj, header_text="DATABASE CARD",
                                      file_path=card_file,
                                      show_additional_info=True)
            except Exception as e:
                # If there's an error displaying the card (e.g., validation error),
                # display a simplified version of the card data
                self._log.error(f"Error displaying card: {e}", exc_info=True)
                
                # Create a simplified display of the card data
                self.console.print(f"\n[bold yellow]Card found in database but has validation errors:[/bold yellow]")
                self.console.print(f"[bold green]Name: {card_data.get('name', 'Unknown')}[/bold green]")
                self.console.print(f"[green]Faction: {card_data.get('faction', 'Unknown')}[/green]")
                self.console.print(f"[green]RFID: {card_data.get('rfid', 'Unknown')}[/green]")
                
                # Display the validation error
                self.console.print(f"[bold red]Error: {str(e)}[/bold red]")

            # Update the card data with the RFID if needed
            if 'rfid' not in card_data or card_data['rfid'] != card.rfid:
                card_data['rfid'] = card.rfid
                if card_file:
                    try:
                        with open(card_file, 'w') as f:
                            json.dump(card_data, f, indent=4)
                        self._log.info(f"Updated card file with RFID: {card_file}")
                    except Exception as e:
                        self._log.error(f"Error updating card file: {e}", exc_info=True)
    
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
        
        # Create menu entries for each faction
        faction_menu = [{"label": faction, "id": str(i+1)} for i, faction in enumerate(factions)]
        
        # Display interactive menu
        self._log.info("Displaying faction selection menu")
        selected = self.interactive_menu("SELECT FACTION", faction_menu, "Back to main menu")
        
        if selected is None:
            self._log.info("User cancelled faction selection")
            return None
        else:
            selected_faction = selected["label"]
            self._log.info(f"User selected faction: {selected_faction}")
            return selected_faction
    
    def select_card_file(self, faction_dir: str, exclude_with_rfid: bool = False, show_rfid_info: bool = False) -> Optional[str]:
        """Display a list of card files in the faction directory and let the user select one
        
        Args:
            faction_dir: The faction directory to list cards from
            exclude_with_rfid: If True, exclude cards that already have an RFID assigned
            show_rfid_info: If True, show RFID information for cards that have it
        """
        # Get a list of card files
        faction_path = os.path.join(self.cards_dir, faction_dir)
        card_files = []  # List to store card menu entries
        excluded_count = 0
        rfid_count = 0
        
        self._log.info(f"Searching for cards in faction: {faction_dir}")
        self._log.info(f"Exclude cards with RFID: {exclude_with_rfid}")
        self._log.info(f"Show RFID info: {show_rfid_info}")
        
        for json_file in glob.glob(os.path.join(faction_path, "*.json")):
            try:
                with open(json_file, 'r') as f:
                    card_data = json.load(f)
                    has_rfid = 'rfid' in card_data and card_data['rfid'] is not None
                    
                    # Skip this card if it already has an RFID and we're excluding those
                    if exclude_with_rfid and has_rfid:
                        excluded_count += 1
                        continue
                    
                    if has_rfid:
                        rfid_count += 1
                    
                    # Extract the card name from the file path
                    original_name = os.path.basename(json_file).replace('.json', '')
                    
                    # Create display name - if the card has an RFID and we're showing RFID info, add it to the display name
                    display_name = original_name
                    if has_rfid and show_rfid_info:
                        display_name = f"{original_name} (RFID: {card_data['rfid']})"
                    
                    # Create a menu entry for this card
                    card_files.append({
                        "label": display_name,
                        "id": str(len(card_files) + 1),
                        "file_path": json_file,
                        "original_name": original_name
                    })
            except Exception as e:
                self._log.error(f"Error reading {json_file}: {e}", exc_info=True)
                # If there's an error reading the file, skip it
                continue
        
        self._log.info(f"Found {len(card_files)} cards in faction {faction_dir}")
        if exclude_with_rfid:
            self._log.info(f"Excluded {excluded_count} cards that already have RFID")
        if show_rfid_info:
            self._log.info(f"Found {rfid_count} cards with RFID values")
        
        if not card_files:
            if exclude_with_rfid:
                self._log.warning(f"No cards without RFID found in {faction_path}")
                self.console.print(f"[bold red]No cards without RFID found in {faction_path}.[/bold red]")
            else:
                self._log.warning(f"No card files found in {faction_path}")
                self.console.print(f"[bold red]No card files found in {faction_path}.[/bold red]")
            return None
        
        # Sort card entries alphabetically by label
        card_files.sort(key=lambda x: x["label"])
        
        # Display interactive menu
        self._log.info(f"Displaying card selection menu for faction {faction_dir}")
        selected = self.interactive_menu(f"SELECT CARD - {faction_dir}", card_files, "Back to faction selection")
        
        if selected is None:
            self._log.info("User cancelled card selection")
            return None
        else:
            selected_card_file = selected["file_path"]
            original_name = selected["original_name"]
            self._log.info(f"User selected card: {original_name} ({selected_card_file})")
            return selected_card_file
    
    def handle_write_card(self, show_rfid_cards: bool = False) -> None:
        """Handle the 'Write card' option
        
        Args:
            show_rfid_cards: If True, show RFID information for cards that have it
        """
        # Select faction
        faction_dir = self.select_faction()
        if faction_dir is None:
            return
        
        # Continuously select cards for writing until user chooses to exit
        while True:
            # Select a card file based on the show_rfid_cards setting
            if show_rfid_cards:
                self.console.print("\n[bold cyan]Select a card to write to an RFID chip[/bold cyan]")
                self.console.print("[bold yellow]Note: Cards with RFID values are shown with their RFID IDs[/bold yellow]")
                card_file = self.select_card_file(faction_dir, exclude_with_rfid=False, show_rfid_info=True)
            else:
                # Default behavior: exclude cards that already have an RFID
                card_file = self.select_card_file(faction_dir, exclude_with_rfid=True)
                
            if card_file is None:
                # User selected to go back
                break
            
            # Read card data from file
            try:
                with open(card_file, 'r') as f:
                    card_data = json.load(f)
            except Exception as e:
                self._log.error(f"Error reading card file: {e}", exc_info=True)
                self.console.print(f"[bold red]Error reading card file: {e}[/bold red]")
                continue
            
            # Display card information
            card = gwent.messaging.card.Message.from_properties(card_data)
            display = self.format_card_display(
                card,
                "SELECTED CARD",
                file_path=card_file,
                show_additional_info=True
            )
            self.console.print(display)
            
            # Confirm with user
            card_name = card_data.get('name', 'Unknown')
            self._log.info(f"Prompting user to confirm writing card: {card_name}")
            if not self.get_user_confirmation(f"Write this card to an RFID chip?"):
                continue
            
            self._log.info(f"User confirmed writing card: {card_name} to RFID chip")
            
            # Write card to RFID tag
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
            if not self.get_user_confirmation("Write another card?"):
                self.console.print("[yellow]Returning to main menu...[/yellow]")
                break
    
    
    def run(self, show_rfid_cards: bool = True) -> None:
        """Run the card manager utility
        
        Args:
            show_rfid_cards: If True, show RFID information for cards that have it when writing
        """
        self.setup_signal_handlers()
        
        self.console.print("\n[bold blue]Card Manager Utility[/bold blue]")
        self.console.print("[dim]Press Ctrl+C to exit[/dim]\n")
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Display menu and get user selection
                    menu_entry = self.display_menu()
                    
                    if menu_entry is None:
                        # Exit
                        self.console.print("[bold yellow]Exiting...[/bold yellow]")
                        break
                    
                    # Execute the selected handler with any provided arguments
                    handler = menu_entry["handler"]
                    args = menu_entry.get("args", {})
                    
                    if args:
                        handler(**args)
                    else:
                        handler()
                # Remove KeyboardInterrupt handling to allow CTRL-C to exit the program
                except Exception as e:
                    self._log.error(f"Error during card processing: {e}", exc_info=True)
                    self.console.print(f"\n[bold red]Error: {e}[/bold red]")
                    self.console.print("[yellow]Continuing...[/yellow]")
                    time.sleep(0.1)
        finally:
            # Ensure cleanup happens regardless of how we exit the loop
            self.cleanup()


def main() -> int:
    """Command-line entry point for the card manager utility"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Card Manager Utility')
    parser.add_argument('--show-rfid-cards', action='store_true', default=True,
                        help='Show RFID information for cards that have it when writing (default: True)')
    parser.add_argument('--no-show-rfid-cards', action='store_false', dest='show_rfid_cards',
                        help='Only show cards without RFID values when writing')
    args = parser.parse_args()
    
    # Set up logging using the gwent logging system
    # This will use the logging.json configuration file
    configure_logging(log_file='tmp/card-manager.log.ndjson')
    
    # Get a logger for this module
    logger = get_logger("gwent.poc.util.card_manager.main")
    
    # Display startup message
    console = Console()
    console.print(f"\n[bold blue]Card Manager Utility[/bold blue]")
    console.print(f"[dim]Logging configured from logging.json[/dim]")
    
    # Log the command-line arguments
    logger.info(f"Command-line arguments: show_rfid_cards={args.show_rfid_cards}")
    
    # Create and run the card manager utility
    manager = CardManager()
    manager.run(show_rfid_cards=args.show_rfid_cards)
    
    # Ensure we catch any exceptions at the top level
    try:
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())