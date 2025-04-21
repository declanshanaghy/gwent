#!/usr/bin/env python3

"""
Font utilities for Gwent
"""

import os
from pathlib import Path

def get_font_path(name):
    """
    Get the path to a font file
    
    Args:
        name (str): Font name
        
    Returns:
        str: Path to the font file
    """
    # Get the directory where this file is located
    font_dir = Path(__file__).resolve().parent
    
    # Return the path to the font file
    return str(font_dir.joinpath(name))