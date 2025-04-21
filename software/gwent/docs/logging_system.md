# Gwent Logging System

This document describes the logging system implemented in the Gwent project using the python-json-logger library.

## Overview

The Gwent project uses a structured JSON logging system that provides:

- Consistent log format across all components
- Configurable log levels for individual components
- Support for standard log levels (ERROR, WARNING, INFO, DEBUG) plus a custom VERBOSE level
- Environment variable configuration for log levels
- JSON configuration file for persistent log level settings
- Dynamic log level updates without application restart
- JSON-formatted logs for easier parsing and analysis

## Log Levels

The logging system supports the following log levels, in order of decreasing severity:

1. **ERROR** - Critical errors that prevent functionality
2. **WARNING** - Issues that don't prevent functionality but are concerning
3. **INFO** - Important state changes and operational information
4. **DEBUG** - Detailed information useful during development
5. **VERBOSE** - Very detailed, high-frequency logs

## Using the Logger

### Getting a Logger

To use the logging system in your code, import the logging module and get a logger for your component:

```python
from gwent.utils.logging import get_logger, INFO, DEBUG, WARNING, ERROR, VERBOSE

# Get a logger for your component
logger = get_logger("gwent.your.component")
```

### Logging Messages

Use the appropriate log level method to log messages:

```python
# Error messages for critical issues
logger.error("Failed to initialize hardware")

# Warning messages for concerning issues
logger.warning("Font file not found, using default font")

# Info messages for important state changes
logger.info("Game started")

# Debug messages for detailed information
logger.debug("Processing input event")

# Verbose messages for very detailed information
logger.verbose("Calculated pixel coordinates: x=120, y=45")
```

## Configuring Log Levels

### Environment Variables

Log levels can be configured using environment variables:

- `GWENT_LOG_LEVEL` - Sets the global log level for all components
- `GWENT_LOG_LEVEL_COMPONENT_NAME` - Sets the log level for a specific component

For example:
```bash
# Set global log level to DEBUG
export GWENT_LOG_LEVEL=DEBUG

# Set log level for display component to VERBOSE
export GWENT_LOG_LEVEL_GWENT_HAL_DISPLAY=VERBOSE
```

Note that component names in environment variables use underscores instead of dots and are uppercase.

### JSON Configuration File

Log levels can be configured using a JSON configuration file located at `software/gwent/logging.json`. This file is monitored for changes, allowing log levels to be updated without restarting the application.

The configuration file has the following structure:

```json
{
  "global": {
    "level": "INFO"
  },
  "components": {
    "gwent.game.main": {
      "level": "INFO"
    },
    "gwent.hal.display": {
      "level": "INFO"
    },
    "gwent.hal.rotary": {
      "level": "VERBOSE"
    },
    "gwent.logical.menu": {
      "level": "DEBUG"
    }
  }
}
```

The `global` section sets the default log level for all components. The `components` section allows you to set specific log levels for individual components.

To change a log level at runtime, simply edit the JSON file. The logging system will detect the change and update the log levels automatically.

### Programmatic Configuration

Log levels can also be configured programmatically:

```python
from gwent.utils.logging import set_log_level, set_global_log_level, DEBUG, VERBOSE

# Set log level for a specific component
set_log_level("gwent.hal.display", VERBOSE)

# Set global log level
set_global_log_level(DEBUG)
```

## Log Format

Logs are formatted as JSON objects with the following fields:

- `timestamp` - The time the log was created
- `level` - The log level (ERROR, WARNING, INFO, DEBUG, VERBOSE)
- `component` - The component that generated the log
- `message` - The log message
- `file` - The file that generated the log
- `line` - The line number in the file
- `thread` - The thread that generated the log
- `process` - The process that generated the log

Example log entry:
```json
{
  "timestamp": "2025-04-20 02:10:26,123",
  "level": "INFO",
  "component": "gwent.game.main",
  "message": "Starting Gwent Companion...",
  "file": "/Users/user/gwent/software/gwent/gwent/game/main.py",
  "line": 251,
  "thread": "MainThread",
  "process": "MainProcess"
}
```

## Best Practices

1. **Use the appropriate log level** - Choose the log level that matches the importance of your message.
2. **Include relevant context** - Include enough information in your log messages to understand what happened.
3. **Be consistent** - Use similar log messages for similar events.
4. **Don't log sensitive information** - Avoid logging passwords, API keys, or other sensitive information.
5. **Use structured data** - When logging complex data, consider using structured formats.

## Implementation Details

The logging system is implemented in `gwent/utils/logging.py` and provides the following key functions:

- `get_logger(component_name)` - Get a logger for a specific component
- `set_log_level(component_name, level)` - Set the log level for a specific component
- `set_global_log_level(level)` - Set the log level for all components
- `configure_logging(level=None)` - Configure the root logger with JSON formatting
- `_load_config_from_file()` - Load logging configuration from the JSON file
- `_apply_config(config)` - Apply the logging configuration
- `_start_file_watcher()` - Start watching the configuration file for changes
- `stop_file_watcher()` - Stop watching the configuration file for changes

The system automatically configures logging when the module is imported, including:
1. Setting up the JSON formatter
2. Loading configuration from the JSON file
3. Starting the file watcher to monitor for changes to the configuration file
4. Registering an atexit handler to stop the file watcher when the application exits

## Configuration Priority

When determining the log level for a component, the system checks the following sources in order:

1. Component-specific log level in the JSON configuration file
2. Global log level in the JSON configuration file
3. Component-specific log level from environment variables
4. Global log level from environment variables
5. Default log level (INFO)

This allows for flexible configuration while maintaining a clear precedence order.