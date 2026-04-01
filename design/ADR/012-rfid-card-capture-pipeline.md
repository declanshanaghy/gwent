# ADR 012: RFID Card Capture and Identification Pipeline

## Status

Accepted

## Context

Onboarding physical Gwent cards requires identifying which card an image shows, creating or updating its JSON metadata, and programming the RFID chip so the game server can recognize it. Doing this manually for hundreds of cards is impractical. We needed an automated pipeline that handles card identification from photos.

## Decision

- **Capture**: `capture-cards.py` captures card photos from a USB webcam using OpenCV, crops and deskews the card region using contour detection (cv2 + numpy + PIL).
- **Identification**: The cropped card image is base64-encoded and sent to the Claude vision API, which identifies the card name and faction from the artwork.
- **JSON creation**: If a matching card JSON doesn't exist in `software/data/cards/{Faction}/`, one is created with the identified metadata (name, faction, strength, abilities, ranges).
- **RFID programming**: `id-and-chip-card.py` writes the card's RFID UID to the card JSON and programs the physical RFID chip with card identification data including CRC.
- **Tracking fields**: `rfid_written_at` and `last_updated` timestamps record when each card was chipped. `image_verified` marks cards whose image has been confirmed.
- Owner and faction can be specified via CLI flags (`--owner`, faction lock in auto mode).

## Consequences

### Positive
- Automated card onboarding — capture, identify, and chip in one workflow.
- Claude vision API handles the hard problem of card art recognition.
- Pipeline produces standard card JSON files — seamless integration with game server.
- Batch mode enables processing an entire deck without manual intervention.

### Negative
- Requires Claude API key and internet access for identification.
- Webcam quality and lighting conditions affect identification accuracy.

### Risks
- Claude vision API may misidentify similar card art (e.g., multiple Arachas variants); user confirmation step mitigates this.
- RFID write failures require physical re-chipping; CRC validation catches corrupted writes.

## Related
- `scripts/capture-cards.py`
- `scripts/id-and-chip-card.py`
- [ADR 009: Card JSON Ownership Model](009-card-json-ownership-model.md)
- `software/data/cards/`
