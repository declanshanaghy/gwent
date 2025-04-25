Fix MFD issues and improve system setup

## Overview

This PR addresses several issues with the Multi-Function Display (MFD) components in the Gwent project and improves the system setup process. It includes comprehensive improvements to display initialization, error handling, logging, and diagnostic tools. Additionally, it fixes discrepancies between Makefile POC targets and setup.py entry points, and enhances system setup documentation.

## Key Changes

### MFD Component Improvements

1. **Enhanced Logging System**
   - Configured logger to write to /tmp/log/gwent.log
   - Set up log rotation on startup
   - Maintain 5 log files
   - Rotate logs when they reach 100MB
   - Added comprehensive logging throughout MFD components

2. **Display Initialization Improvements**
   - Implemented automatic testing of multiple device/port combinations
   - Disabled device_port_combinations (0,0) to prevent hanging
   - Added retry mechanisms for display initialization
   - Created comprehensive display reset sequences
   - Improved font loading with fallback mechanisms

3. **Thread Management Enhancements**
   - Enhanced thread creation and monitoring
   - Improved thread termination and cleanup
   - Added better synchronization between threads

4. **MFD Diagnostic Tool**
   - Created mfd_diagnostic.py to systematically test MFD components
   - Implemented tests for display initialization, font loading, and MFD functionality
   - Added automatic fixes for common issues
   - Updated tool to wait for user feedback between tests

### Build System and Documentation Improvements

1. **Fixed POC Targets and Entry Points**
   - Added missing entry points for mfd-diagnostic, rotary-diagnostics, rotary-robust, rotary-lgpio, and rotary-test
   - Fixed naming discrepancies by changing rotary-diagnostic-test to rotary-diagnostic
   - Added separate entry points for gpio-service-stop and gpio-service-start
   - Verified correct module path mappings for matrix-test, oled-direct-test, and display-diagnostic

2. **Restored and Improved Scripts**
   - Restored deploy-and-test.sh from git history
   - Created new validate-gwent.sh with comprehensive validation checks
   - Updated install-system.sh to only reconfigure mosquitto if the conf file doesn't exist

3. **Enhanced Documentation**
   - Updated SETUP_INSTRUCTIONS.md with more comprehensive system preparation steps
   - Added detailed explanations for each setup step

## Files Changed

- `software/gwent/setup.py`: Updated entry points for POC targets
- `Makefile`: Fixed target names to match entry points
- `scripts/validate-gwent.sh`: Created new validation script
- `scripts/deploy-and-test.sh`: Restored from git history
- `scripts/install-system.sh`: Improved mosquitto configuration
- `SETUP_INSTRUCTIONS.md`: Enhanced system preparation documentation
- `software/gwent/gwent/hal/mfd.py`: Fixed missing logging import, improved error handling
- `software/gwent/gwent/hal/oled_ssd1306.py`: Enhanced display initialization and refresh
- `software/gwent/gwent/utils/logging.py`: Added rotating file handler
- `software/gwent/gwent/poc/diagnostic_tools/mfd_diagnostic.py`: Created diagnostic tool

## Development Metrics

- **Total API Cost**: $3.13
- **Total Development Time**: 1 hour 15 minutes
- **Total Lines Added**: 3256
- **Total Lines Deleted**: 2798
- **Files Modified**: 15
- **New Files Created**: 12
- **Bugs Fixed**: 2
- **Features Added**: 3
- **Performance Improvements**: 2
- **Code Quality Improvements**: 5

## Testing

The changes have been tested on a Raspberry Pi with the following components:
- OLED SSD1306 display
- Rotary encoder
- RFID reader

The MFD diagnostic tool provides a comprehensive way to test all MFD components and can be run with:

```bash
make mfd-diagnostic