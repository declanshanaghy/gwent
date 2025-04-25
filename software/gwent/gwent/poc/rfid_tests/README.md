# RFID Tests

This directory contains scripts for testing and debugging RFID functionality used in the Gwent project.

## Scripts

### rfid.py

A test script for RFID card scanning using the gwent.hal.rfid module.

#### Features:
- Continuously scans for RFID cards
- Prints the ID and text content when a card is detected
- Handles errors gracefully with helpful messages
- Properly cleans up GPIO resources on exit

#### Usage:
```bash
python rfid.py
```

When running the script:
1. Place an RFID card near the reader
2. The script will display the card's ID and any available properties (name, faction, strength, etc.)
3. Press Ctrl+C to exit

## Relationship to Main Codebase

The RFID functionality tested in this script is implemented in the main codebase in:
- `gwent/hal/rfid.py`: Hardware abstraction layer for RFID
- `gwent/game/poc.py`: Contains `CardReaderUtil` and `CardWriterUtil` classes for reading and writing cards

## Troubleshooting

If you encounter issues with the RFID reader:

1. Check that SPI is enabled on your Raspberry Pi
   - Run `sudo raspi-config > Interface Options > SPI > Enable`

2. Verify the connections to your MFRC522 RFID reader
   - SPI connections: MOSI, MISO, SCLK, CS
   - Power connections: 3.3V, GND

3. Check for GPIO pin conflicts using the `gpio_check.py` script in the diagnostic_tools directory

4. If the reader is not detecting cards:
   - Ensure the card is compatible with the MFRC522 reader (13.56 MHz)
   - Try placing the card directly on the reader
   - Try different cards to rule out a faulty card