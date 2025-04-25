#!/usr/bin/env python3
"""
Logging configuration for the Gwent application.
"""

import logging
import logging.config
import os
import json
from pathlib import Path

def setup(level='info'):
    """
    Set up logging for the Gwent application.
    
    Args:
        level: The logging level (debug, info, warning, error, critical)
    """
    # Convert level string to logging level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    # Check if there's a logging.json file
    config_path = Path(__file__).parent / 'logging.json'
    if config_path.exists():
        # Load logging configuration from file
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Override the root logger level with the provided level
        config['loggers']['']['level'] = level.upper()
        
        # Configure logging
        logging.config.dictConfig(config)
    else:
        # Basic configuration
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Create a logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at level {level.upper()}")
    
    return logger