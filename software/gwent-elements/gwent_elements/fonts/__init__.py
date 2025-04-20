"""
Font files for Gwent Elements
"""

import os

FONTS_DIR = os.path.dirname(os.path.abspath(__file__))

def get_font_path(font_name):
    """
    Get the path to a font file
    
    Args:
        font_name (str): Font file name
        
    Returns:
        str: Full path to the font file
    """
    return os.path.join(FONTS_DIR, font_name)