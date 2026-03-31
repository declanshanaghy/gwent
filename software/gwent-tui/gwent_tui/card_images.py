"""Resolve card image paths from card name and faction."""

import re
from pathlib import Path

# Images live relative to the gwent-tui package
_IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "images"
_CARDS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cards"

FACTION_DIRS = {
    "Monsters": "Monsters",
    "Northern Realms": "NorthernRealms",
    "Nilfgaardian": "Nilfgaardian",
    "Scoia'tael": "Scoiatael",
    "Skellige": "Skellige",
    "Neutral": "Neutral",
}


def _to_filename(name: str) -> str:
    """Convert card name to PascalCase filename (no extension)."""
    words = name.split()
    words = [w[0].upper() + w[1:] for w in words if w]
    s = " ".join(words)
    s = s.replace("'", "").replace(":", "").replace(",", "")
    return re.sub(r'[^a-zA-Z0-9]', '', s.replace(" ", ""))


def resolve_card_image(card: dict) -> str | None:
    """Find the image file for a card. Returns absolute path or None.

    Tries in order:
    1. The card's `image` field (relative path from card JSON)
    2. Name-based lookup in the faction image directory
    3. Suffix-stripped fallback for duplicate cards
    """
    name = card.get("name", "")
    faction = card.get("faction", "")
    image_field = card.get("image")

    # Try the image field first — it's a relative path from the card JSON dir
    if image_field:
        faction_dir = FACTION_DIRS.get(faction, "")
        if faction_dir:
            candidate = (_CARDS_DIR / faction_dir / image_field).resolve()
            if candidate.exists():
                return str(candidate)

    faction_dir = FACTION_DIRS.get(faction)
    if not faction_dir:
        return None

    img_dir = _IMAGES_DIR / faction_dir
    if not img_dir.is_dir():
        return None

    # Try exact name match
    fname = _to_filename(name)
    candidate = img_dir / f"{fname}.jpg"
    if candidate.exists():
        return str(candidate)

    # Strip ": N" suffix for duplicates (e.g. "Arachas: 2" -> "Arachas")
    if ":" in name:
        before, _, after = name.rpartition(":")
        if after.strip().isdigit():
            base_name = before.strip()
            base_fname = _to_filename(base_name)
            # Try suffixed: Arachas2.jpg
            suffixed = img_dir / f"{base_fname}{after.strip()}.jpg"
            if suffixed.exists():
                return str(suffixed)
            # Try base: Arachas.jpg
            base = img_dir / f"{base_fname}.jpg"
            if base.exists():
                return str(base)

    return None
