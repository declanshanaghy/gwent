#!/usr/bin/env python3

"""
Test script for the logging system.
This script tests the logging to file functionality.
"""

from __future__ import annotations

import os
import pytest
import logging
import tempfile
import re
from typing import Optional
from gwent.utils.logging import configure_logging

def test_file_logging() -> None:
    """Test that logging to a file works correctly."""
    # Create a temporary log file
    with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as temp_file:
        log_path = temp_file.name
    
    try:
        # Configure logging to write to the temporary file
        configure_logging(log_file=log_path)
        
        # Get a logger and write some test messages
        logger = logging.getLogger("test_logger")
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        
        # Verify that the log file contains the messages
        with open(log_path, 'r') as f:
            log_content = f.read()
            
        assert "Test info message" in log_content
        assert "Test warning message" in log_content
        assert "Test error message" in log_content
        assert "test_logger" in log_content
    finally:
        # Clean up the temporary file
        if os.path.exists(log_path):
            os.remove(log_path)

def test_timestamp_format() -> None:
    """Test that the timestamp in the log file is correctly formatted."""
    # Create a temporary log file
    with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as temp_file:
        log_path = temp_file.name
    
    try:
        # Configure logging to write to the temporary file
        configure_logging(log_file=log_path)
        
        # Get a logger and write a test message
        logger = logging.getLogger("test_logger")
        logger.info("Test timestamp message")
        
        # Verify that the log file contains a properly formatted timestamp
        with open(log_path, 'r') as f:
            log_content = f.read()
            
        # Check for ISO format timestamp (YYYY-MM-DDTHH:MM:SS)
        timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        assert re.search(timestamp_pattern, log_content) is not None
    finally:
        # Clean up the temporary file
        if os.path.exists(log_path):
            os.remove(log_path)