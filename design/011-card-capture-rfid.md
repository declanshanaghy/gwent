# PRD-011: Card Capture and RFID Programming

## Overview

The card capture workflow bridged physical cards and the digital system. Two scripts handled the pipeline: capturing card images via webcam for Claude vision API identification, and writing card data to RFID chips. This enabled batch programming of physical card decks.

## Requirements

### Functional Requirements

- FR-1: `capture-cards.py` captured images from a webcam, sent them to the Claude vision API for card identification, and saved cropped card images.
- FR-2: `id-and-chip-card.py` provided a continuous workflow: capture image, identify card, find or create the card JSON, and write data to the RFID chip.
- FR-3: RFID writing used sectors 1-15 of Mifare Classic cards, with 16 bytes per sector, storing serialized card identity data.
- FR-4: CRC validation ensured data integrity when reading back written RFID data.
- FR-5: Faction directory normalization handled spelling variants (e.g., "Scoiatael" vs "Scoia'tael").
- FR-6: The `--owner` flag assigned card ownership during the chipping process.
- FR-7: The `--nickname` flag allowed associating a player nickname with programmed cards.
- FR-8: Auto mode in capture-cards.py provided continuous webcam capture with automatic card detection.
- FR-9: Bounding box cropping isolated the card from the webcam frame for cleaner identification.
- FR-10: Faction lock mode restricted identification to a specific faction for batch processing.

### Non-Functional Requirements

- NFR-1: Card identification via Claude vision API processed images sequentially to avoid OOM on the Raspberry Pi.
- NFR-2: RFID write operations verified data by reading back and comparing with CRC.
- NFR-3: KeyboardInterrupt was caught silently for clean exit from continuous capture loops.

## Dependencies

- MFRC522 RFID hardware and library
- Claude API (Anthropic) for vision-based card identification
- OpenCV for webcam capture
- Card data system (PRD-007) for JSON storage

## Related Documents

- [PRD-007: Card Data System](007-card-data-system.md)
- [PRD-004: Hardware Abstraction Layer](004-hardware-abstraction-layer.md)
