#!/usr/bin/env python3

"""
Logging Module for Gwent
This module provides a standardized logging configuration using python-json-logger.
"""

from __future__ import annotations

import os
import sys
import time
import threading
import logging
import json
import pathlib
from typing import Dict, Optional, Any, Union
from pythonjsonlogger import jsonlogger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Define log levels
VERBOSE = 5  # Custom level for very detailed logs
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR

# Register the VERBOSE level
logging.addLevelName(VERBOSE, "VERBOSE")

# Default log level
DEFAULT_LOG_LEVEL = INFO

# Component log levels dictionary
# This will store individual log level settings for each component
_component_log_levels = {}

# Environment variable prefix for log level configuration
ENV_PREFIX = "GWENT_LOG_LEVEL"

# Path to the logging configuration file
CONFIG_FILE_PATH = pathlib.Path(__file__).parent.parent.parent / "logging.json"

# Observer for file changes
_observer = None
_last_modified_time = 0

def _str_to_log_level(level_str: str) -> int:
    """
    Convert a string log level to its corresponding integer value.
    
    Args:
        level_str (str): The log level as a string
        
    Returns:
        int: The log level as an integer
    """
    level_str = level_str.upper()
    if level_str == "VERBOSE":
        return VERBOSE
    elif level_str == "DEBUG":
        return DEBUG
    elif level_str == "INFO":
        return INFO
    elif level_str == "WARNING":
        return WARNING
    elif level_str == "ERROR":
        return ERROR
    else:
        return DEFAULT_LOG_LEVEL

def _load_config_from_file() -> Dict[str, Any]:
    """
    Load logging configuration from the JSON file.
    
    Returns:
        dict: The configuration dictionary
    """
    try:
        if CONFIG_FILE_PATH.exists():
            with open(CONFIG_FILE_PATH, 'r') as f:
                config = json.load(f)
                return config
    except Exception as e:
        print(f"Error loading logging configuration: {e}")
    
    # Return a default configuration if the file doesn't exist or there's an error
    return {
        "global": {
            "level": "INFO"
        },
        "components": {}
    }

def _apply_config(config: Dict[str, Any]) -> None:
    """
    Apply the logging configuration.
    
    Args:
        config (dict): The configuration dictionary
    """
    # Set the global log level
    if "global" in config and "level" in config["global"]:
        global_level = _str_to_log_level(config["global"]["level"])
        set_global_log_level(global_level)
    
    # Set component-specific log levels
    if "components" in config:
        for component_name, component_config in config["components"].items():
            if "level" in component_config:
                level = _str_to_log_level(component_config["level"])
                set_log_level(component_name, level)

class ConfigFileHandler(FileSystemEventHandler):
    """
    Handler for file system events on the logging configuration file.
    """
    
    def on_modified(self, event: Any) -> None:
        """
        Called when the configuration file is modified.
        
        Args:
            event: The file system event
        """
        if event.src_path == str(CONFIG_FILE_PATH):
            # Load and apply the new configuration
            config = _load_config_from_file()
            _apply_config(config)
            print(f"Logging configuration reloaded from {CONFIG_FILE_PATH}")

def _start_file_watcher() -> None:
    """
    Start watching the configuration file for changes.
    """
    global _observer
    
    if _observer is not None:
        return
    
    # Create the observer
    _observer = Observer()
    
    # Create the event handler
    event_handler = ConfigFileHandler()
    
    # Schedule the observer to watch the parent directory of the config file
    _observer.schedule(event_handler, str(CONFIG_FILE_PATH.parent), recursive=False)
    
    # Start the observer
    _observer.start()


class GwentJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for Gwent logs.
    Adds timestamp, log level, and component name to each log entry.
    """
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord,
                  message_dict: Dict[str, Any]) -> None:
        """
        Add custom fields to the log record.
        
        Args:
            log_record (dict): The log record being built
            record (LogRecord): The original log record
            message_dict (dict): The message dictionary
        """
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = self.formatTime(record)
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add component name
        log_record['component'] = record.name
        
        # Add file and line information
        log_record['file'] = record.pathname
        log_record['line'] = record.lineno
        
        # Add thread information
        log_record['thread'] = record.threadName
        
        # Add process information
        log_record['process'] = record.processName


def _verbose(self, message: str, *args: Any, **kwargs: Any) -> None:
    """
    Log a message with VERBOSE level.
    
    Args:
        message: The message to log
        args: Additional positional arguments
        kwargs: Additional keyword arguments
    """
    if self.isEnabledFor(VERBOSE):
        self._log(VERBOSE, message, args, **kwargs)


# Add the verbose method to the Logger class
logging.Logger.verbose = _verbose


def get_log_level_from_env(component_name: str) -> int:
    """
    Get log level from environment variables or configuration file.
    
    Args:
        component_name (str): The name of the component
        
    Returns:
        int: The log level
    """
    # First, check the configuration file
    config = _load_config_from_file()
    
    # Check for component-specific log level in the config file
    if "components" in config and component_name in config["components"] and "level" in config["components"][component_name]:
        level_str = config["components"][component_name]["level"]
        return _str_to_log_level(level_str)
    
    # Check for global log level in the config file
    if "global" in config and "level" in config["global"]:
        level_str = config["global"]["level"]
        return _str_to_log_level(level_str)
    
    # If not found in the config file, check environment variables
    # Check for component-specific log level
    component_env_var = f"{ENV_PREFIX}_{component_name.upper().replace('.', '_')}"
    level_str = os.environ.get(component_env_var)
    
    # Check for global log level if component-specific not found
    if level_str is None:
        level_str = os.environ.get(ENV_PREFIX)
    
    # Return the appropriate log level
    if level_str:
        return _str_to_log_level(level_str)
    
    # Return the default log level if not found
    return DEFAULT_LOG_LEVEL


def configure_logging(level: Optional[int] = None, log_file: Optional[str] = None) -> None:
    """
    Configure the root logger with JSON formatting.
    
    Args:
        level (int, optional): The log level for the root logger
        log_file (str, optional): Path to a log file to write logs to
    """
    # Set up the root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create a handler that writes to stderr
    console_handler = logging.StreamHandler(sys.stderr)
    
    # Create a formatter
    formatter = GwentJsonFormatter('%(timestamp)s %(level)s %(component)s %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add the handler to the root logger
    root_logger.addHandler(console_handler)
    
    # If a log file is specified, add a file handler
    if log_file:
        # Ensure the directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        # Create a file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set the log level
    if level is None:
        level = get_log_level_from_env("root")
    
    root_logger.setLevel(level)
    
    # Load and apply configuration from file
    config = _load_config_from_file()
    _apply_config(config)
    
    # Start the file watcher
    _start_file_watcher()


def get_logger(component_name: str) -> logging.Logger:
    """
    Get a logger for a specific component.
    
    Args:
        component_name (str): The name of the component
        
    Returns:
        logging.Logger: The logger for the component
    """
    # Get the logger for the component
    logger = logging.getLogger(component_name)
    
    # Check if we have a stored log level for this component
    if component_name in _component_log_levels:
        level = _component_log_levels[component_name]
    else:
        # Get the log level from environment variables
        level = get_log_level_from_env(component_name)
        # Store the log level for future reference
        _component_log_levels[component_name] = level
    
    # Set the log level
    logger.setLevel(level)
    
    return logger


def set_log_level(component_name: str, level: int) -> None:
    """
    Set the log level for a specific component.
    
    Args:
        component_name (str): The name of the component
        level (int): The log level
    """
    # Store the log level
    _component_log_levels[component_name] = level
    
    # Get the logger and set its level
    logger = logging.getLogger(component_name)
    logger.setLevel(level)


def set_global_log_level(level: int) -> None:
    """
    Set the log level for all loggers.
    
    Args:
        level (int): The log level
    """
    # Set the root logger level
    logging.getLogger().setLevel(level)
    
    # Update the default log level
    global DEFAULT_LOG_LEVEL
    DEFAULT_LOG_LEVEL = level


def stop_file_watcher() -> None:
    """
    Stop watching the configuration file for changes.
    This should be called when the application exits.
    """
    global _observer
    
    if _observer is not None and _observer.is_alive():
        _observer.stop()
        _observer.join()
        _observer = None


# Configure logging when the module is imported
configure_logging()

# Register an atexit handler to stop the file watcher
import atexit
atexit.register(stop_file_watcher)