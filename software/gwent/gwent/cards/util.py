#!/usr/bin/env python3
"""
Utility functions for working with Gwent cards.
"""

import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_card_data(card_id):
    """
    Load card data from a JSON file.
    
    Args:
        card_id: The ID of the card to load
        
    Returns:
        dict: The card data, or None if the card doesn't exist
    """
    # Try to find the card in the data directory
    data_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'cards'
    
    # Log the search path
    logger.debug(f"Searching for card {card_id} in {data_dir}")
    
    # Search for the card in all faction directories
    for faction_dir in data_dir.glob('*'):
        if not faction_dir.is_dir():
            continue
            
        # Check if the card exists in this faction
        card_path = faction_dir / f"{card_id}.json"
        if card_path.exists():
            logger.debug(f"Found card {card_id} at {card_path}")
            with open(card_path, 'r') as f:
                return json.load(f)
    
    logger.warning(f"Card {card_id} not found")
    return None

def save_card_data(card_id, data, faction='Neutral'):
    """
    Save card data to a JSON file.
    
    Args:
        card_id: The ID of the card to save
        data: The card data to save
        faction: The faction the card belongs to
        
    Returns:
        bool: True if the card was saved successfully, False otherwise
    """
    # Get the data directory
    data_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'cards' / faction
    
    # Create the directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the card data
    card_path = data_dir / f"{card_id}.json"
    try:
        with open(card_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Saved card {card_id} to {card_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving card {card_id}: {e}")
        return False

def list_cards(faction=None):
    """
    List all available cards.
    
    Args:
        faction: The faction to list cards for, or None for all factions
        
    Returns:
        list: A list of card IDs
    """
    # Get the data directory
    data_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'cards'
    
    cards = []
    
    # Get all factions or just the specified one
    factions = [faction] if faction else [f.name for f in data_dir.glob('*') if f.is_dir()]
    
    # Get all cards in each faction
    for faction_name in factions:
        faction_dir = data_dir / faction_name
        if not faction_dir.exists() or not faction_dir.is_dir():
            continue
            
        # Get all JSON files in the faction directory
        for card_path in faction_dir.glob('*.json'):
            card_id = card_path.stem
            cards.append(card_id)
    
    return cards