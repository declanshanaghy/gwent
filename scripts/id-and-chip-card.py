#!/usr/bin/env python3
"""Identify Gwent cards from webcam and write to RFID chips.

Captures images from USB webcam, identifies cards via Claude vision API,
finds/creates card JSON files, and writes to RFID chips in a continuous loop.

Usage:
    python scripts/id-and-chip-card.py [--owner NAME] [--nickname NICK]
"""

import argparse
import base64
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add gwent package to path
REPO_ROOT = Path(__file__).resolve().parent.parent
GWENT_PKG = REPO_ROOT / "software" / "gwent"
sys.path.insert(0, str(GWENT_PKG))

import anthropic

import gwent.hal.sfx
import gwent.messaging.base
from gwent.utils.logging import configure_logging, DEBUG, INFO

LOG_FILE = "/tmp/logs/id-and-chip-card.log"

log = logging.getLogger("id-and-chip-card")

CARDS_DIR = REPO_ROOT / "software" / "data" / "cards"
WEBCAM_DIR = REPO_ROOT / "tmp" / "webcam"
CAPTURE_JPG = WEBCAM_DIR / "capture.jpg"
BASELINE_JPG = WEBCAM_DIR / "baseline.jpg"
CAPTURE_JSON = WEBCAM_DIR / "capture.json"
WEBCAM_DEVICE = "/dev/video0"

FACTIONS = ["Monsters", "Northern Realms", "Nilfgaardian", "Scoia'tael", "Skellige"]

FACTION_DIRS = {
    "Monsters": "Monsters",
    "Northern Realms": "NorthernRealms",
    "Nilfgaardian": "Nilfgaardian",
    "Scoia'tael": "Scoiatael",
    "Skellige": "Skellige",
}

IDENTIFY_PROMPT = """\
Analyze this photo of a physical Gwent card (The Witcher III). Respond with ONLY a JSON object.

If no card face is visible (card back, blank surface, hand, etc.), respond: {"no_card": true}
If given a BASELINE IMAGE, compare against it — if essentially identical, respond: {"no_card": true}

## Card Layout (top to bottom along the left sash)

The left side of every card has a vertical colored SASH. Reading top-to-bottom along it:

1. STRENGTH MEDALLION (top) — round circle with a number. Omit for special cards.
2. RANGE ICON(S) — in orange circles below strength:
   - Sword = "close"
   - Crossed bow/arrows = "ranged"
   - Catapult = "siege"
   Cards can have MULTIPLE range icons stacked. List ALL. If 2+ ranges, add "agile" to abilities.
3. ABILITY ICON (bottom) — in a circle with an obvious border, below range icons.
   Only count large circled icons. Small sash decorations/crests are NOT abilities.

Card NAME is printed at the bottom of the card. Some names wrap across multiple lines —
read ALL lines (e.g. "Emiel Regis Rohellec Terzieff"). Leader names use colons
(e.g. "Foltest: the Siegemaster").

## Faction (from sash color)

Determine faction ONLY from the sash color. Same card can appear in different factions.
- BRIGHT VIVID RED = "Monsters"
- BLUE = "Northern Realms"
- GREEN = "Scoia'tael"
- PURPLE = "Skellige"
- DARK GOLD / BRONZE / BROWN = "Nilfgaardian" — muted, desaturated, NOT bright red.
  Confirm with crest: Nilfgaardian = sun/star, Monsters = skull/beast.

## Specialty (omit if none)

Only set specialty if CLEARLY present:
- "hero" — thick GOLD BORDER around the ENTIRE card perimeter. This is unmistakable.
  The orange strength/range circles are NOT gold borders. If unsure, it is NOT a hero.
- "weather" — weather icon (snowflake, fog, rain), no strength number
- "scorch" — skull icon in top-left, no strength number
- "decoy" — puppet/marionette icon, no strength number
- "commander" — horn icon, no strength number
- "leader" — crown icon
- "mardroeme" — mushroom icon

## Abilities (omit if none)

Read the circled icon at the BOTTOM of the sash, below the range icon(s):
- "medic" — cross/plus sign (+). COMMON. Do not confuse with hero.
- "muster" — three arrows/chevrons pointing up. MOST COMMON ability.
- "bond" — chain links
- "morale" — star shape
- "spy" — open eye. RARE — only on specific spy cards (e.g. Avallac'h).
  If ambiguous between spy and muster, choose muster.
- "berserker" — bear head
- "scorch" — small skull (as ability, distinct from scorch specialty)
- "agile" — NOT an icon. Auto-add when card has 2+ range icons.

## Response format

JSON only. Include only fields with values. Examples:
{"name": "Geralt of Rivia", "faction": "Northern Realms", "strength": 15, "ranges": ["close"], "specialty": "hero"}
{"name": "Yaevinn", "faction": "Scoia'tael", "strength": 6, "ranges": ["close", "ranged"], "abilities": ["agile"]}
{"name": "Isengrim Faoiltiarna", "faction": "Scoia'tael", "strength": 10, "ranges": ["close"], "abilities": ["medic"]}
{"name": "Scorch", "faction": "Monsters", "specialty": "scorch"}
"""


_sfx = None
_capture_sound = None
_write_sound = None

SFX_DATA_DIR = REPO_ROOT / "software" / "data" / "sfx"
CAPTURE_WAV = SFX_DATA_DIR / "camera_shutter.wav"
WRITE_WAV = SFX_DATA_DIR / "card_read.wav"


def play_capture_sound():
    """Play sound when webcam image is taken."""
    if _capture_sound:
        try:
            _capture_sound.play()
        except Exception as e:
            log.debug("Could not play capture sound: %s", e)


def play_write_sound():
    """Play sound when RFID card is written."""
    if _write_sound:
        try:
            _write_sound.play()
        except Exception as e:
            log.debug("Could not play write sound: %s", e)


def init_sfx():
    """Initialize the SFX player with gtts for a distinct accent."""
    global _sfx, _capture_sound, _write_sound
    try:
        _sfx = gwent.hal.sfx.instance(tts_provider="gtts")
        log.info("SFX initialized with gtts provider")
    except Exception as e:
        log.warning("Could not init SFX: %s", e)
        print(f"WARNING: Could not init SFX: {e}")
        _sfx = None
    try:
        import pygame
        _capture_sound = pygame.mixer.Sound(str(CAPTURE_WAV))
        _write_sound = pygame.mixer.Sound(str(WRITE_WAV))
        log.info("Loaded sound effects: %s, %s", CAPTURE_WAV.name, WRITE_WAV.name)
    except Exception as e:
        log.warning("Could not load sound effects: %s", e)


class _SpeechMsg:
    """Minimal message wrapper for TTS announcements."""
    def __init__(self, text, faction=None):
        self.content_id = str(hash(text + (faction or "")))
        self._text = text
        self.faction = faction

    @property
    def announcement(self):
        return self._text


def say(text, faction=None, wait=True):
    """Speak text using TTS. Blocks until the announcement queue is drained."""
    if _sfx is None:
        return
    try:
        log.debug("TTS: %s (faction=%s, wait=%s)", text, faction, wait)
        _sfx.announce(_SpeechMsg(text, faction=faction))
        if wait:
            _sfx._announce_queue.join()
    except Exception as e:
        log.error("TTS error: %s", e, exc_info=True)
        print(f"  (TTS error: {e})")


def build_card_announcement(card_info, card_data=None):
    """Build a rich TTS announcement from card info and optional JSON data."""
    name = card_info.get("name", "Unknown")
    faction = card_info.get("faction", "Unknown")
    parts = [f"{name}. {faction}."]

    strength = card_info.get("strength")
    if strength is not None:
        parts.append(f"Strength {strength}.")

    ranges = card_info.get("ranges", [])
    if ranges:
        parts.append(f"{', '.join(ranges)} combat.")

    specialty = card_info.get("specialty")
    if specialty:
        parts.append(f"{specialty} card.")

    abilities = card_info.get("abilities", [])
    if abilities:
        parts.append(f"Abilities: {', '.join(abilities)}.")

    # Check card JSON for leader instructions
    data = card_data or {}
    leader = data.get("leader")
    if leader and isinstance(leader, dict):
        instructions = leader.get("instructions")
        if instructions:
            parts.append(f"Leader ability: {instructions}.")

    return " ".join(parts)


def confirm_faction(detected_faction):
    """Confirm or correct the detected faction via stdin.
    Returns the confirmed faction name."""
    say(f"Detected faction: {detected_faction}. Confirm or correct.", wait=True)
    print(f"\n  Detected faction: {detected_faction}")
    print("  Factions:")
    for i, f in enumerate(FACTIONS, 1):
        marker = " <<" if f == detected_faction else ""
        print(f"    {i}. {f}{marker}")
    print(f"  Press Enter to accept '{detected_faction}', or enter number to correct: ", end="", flush=True)
    try:
        choice = input().strip()
    except EOFError:
        return detected_faction
    if not choice:
        return detected_faction
    try:
        idx = int(choice)
        if 1 <= idx <= len(FACTIONS):
            corrected = FACTIONS[idx - 1]
            if corrected != detected_faction:
                log.info("Faction corrected: %s -> %s", detected_faction, corrected)
                say(f"Corrected to {corrected}.")
            return corrected
    except ValueError:
        pass
    return detected_faction


def countdown(seconds=3):
    """Announce a countdown with TTS."""
    for i in range(seconds, 0, -1):
        print(f"  {i}...")
        say(str(i), wait=False)
        time.sleep(1)
    # Wait for last number to finish
    if _sfx:
        _sfx._announce_queue.join()


def load_dotenv():
    """Load .env file from repo root."""
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), value)


def ensure_gwent_stopped():
    """Check that gwent process is not running."""
    result = subprocess.run(
        ["pgrep", "-f", "gwent-venv/bin/gwent$"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        log.error("gwent is running, cannot proceed")
        print("ERROR: gwent is running. Stop it first: scripts/dev-server.sh gwent stop")
        sys.exit(1)
    log.debug("gwent not running, OK to proceed")


def capture_image(output_path=None):
    """Capture a single frame from the webcam. Returns True on success."""
    if output_path is None:
        output_path = CAPTURE_JPG
    WEBCAM_DIR.mkdir(parents=True, exist_ok=True)
    log.debug("Capturing image to %s", output_path)
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "v4l2", "-input_format", "mjpeg",
            "-video_size", "1280x720",
            "-i", WEBCAM_DEVICE,
            "-frames:v", "1", "-update", "1",
            str(output_path),
        ],
        capture_output=True, text=True, timeout=10,
    )
    if not output_path.exists() or output_path.stat().st_size < 1000:
        log.error("Capture failed: file missing or too small (size=%s)",
                  output_path.stat().st_size if output_path.exists() else 0)
        print("ERROR: Failed to capture image from webcam")
        return False
    log.info("Captured %s (%d bytes)", output_path.name, output_path.stat().st_size)
    play_capture_sound()
    return True


def capture_baseline():
    """Capture a baseline 'empty' image for comparison."""
    print("Capturing baseline (empty surface)...")
    say("Capturing baseline. Ensure no card is under the camera.")
    countdown()
    if not capture_image(BASELINE_JPG):
        log.warning("Could not capture baseline image")
        print("WARNING: Could not capture baseline image")
        return None
    log.info("Baseline captured: %d bytes", BASELINE_JPG.stat().st_size)
    print("Baseline captured.")
    return base64.standard_b64encode(BASELINE_JPG.read_bytes()).decode("utf-8")


def identify_card(client, baseline_b64=None):
    """Send captured image to Claude for identification. Returns dict or None."""
    image_data = base64.standard_b64encode(CAPTURE_JPG.read_bytes()).decode("utf-8")
    log.info("Sending image to Claude for identification (baseline=%s)",
             "yes" if baseline_b64 else "no")

    content = []

    # Include baseline image for comparison if available
    if baseline_b64:
        content.append({"type": "text", "text": "BASELINE IMAGE (empty surface, no card):"})
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": baseline_b64,
            },
        })
        content.append({"type": "text", "text": "CURRENT IMAGE (identify the card):"})

    content.append({
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": image_data,
        },
    })
    content.append({"type": "text", "text": IDENTIFY_PROMPT})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": content}],
    )

    text = response.content[0].text.strip()
    log.debug("Claude raw response: %s", text)

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
        log.info("Identification result: %s", json.dumps(result))
        return result
    except json.JSONDecodeError:
        log.error("Could not parse Claude response: %s", text)
        print(f"ERROR: Could not parse Claude response: {text}")
        return None


def _base_name(name):
    """Strip numeric colon suffix (e.g. 'Villentretenmerth: 2' -> 'Villentretenmerth').
    Does NOT strip named suffixes like 'Vampire: Katakan' — those are part of the card name."""
    if ":" in name:
        before, _, after = name.rpartition(":")
        if after.strip().isdigit():
            return before.strip()
    return name.strip()


def _edit_distance(a, b):
    """Simple Levenshtein edit distance."""
    if len(a) < len(b):
        return _edit_distance(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[len(b)]


def _names_match(detected, stored):
    """Check if a detected name matches a stored card name.
    Handles: exact match, base name match (before colon), partial/prefix match,
    and fuzzy match (1-2 char spelling differences like Vidkaarl vs Vildkaarl)."""
    if detected == stored:
        return True
    det_base = _base_name(detected).lower()
    sto_base = _base_name(stored).lower()
    if det_base == sto_base:
        return True
    # Partial match: detected name is a prefix of the stored name (or vice versa)
    # e.g. "Emiel Regis" matches "Emiel Regis Rohellec Terzieff"
    # Require the shorter name to be at least 60% of the longer name to avoid
    # matching within card families (e.g. "Vampire: Katakan" vs "Vampire: Fleder")
    if len(det_base) >= 8 and len(sto_base) >= 8:
        shorter, longer = (det_base, sto_base) if len(det_base) <= len(sto_base) else (sto_base, det_base)
        if longer.startswith(shorter) and len(shorter) >= len(longer) * 0.35:
            return True
    # Fuzzy match: allow 1-2 char differences for names >= 8 chars
    if len(det_base) >= 8 and len(sto_base) >= 8:
        dist = _edit_distance(det_base, sto_base)
        if dist <= 2:
            return True
    return False


def find_all_card_jsons(name, faction):
    """Find ALL card JSONs matching a name in the faction directory.
    Matches exact name, base name (before colon), and partial/prefix names
    for cards with long names that wrap across multiple lines on the card.
    Returns list of (filepath, data) tuples."""
    faction_dir = FACTION_DIRS.get(faction)
    if not faction_dir:
        log.warning("Unknown faction '%s', cannot search for card", faction)
        return []
    search_dir = CARDS_DIR / faction_dir
    if not search_dir.exists():
        log.debug("Faction dir does not exist: %s", search_dir)
        return []

    matches = []
    for f in search_dir.iterdir():
        if not f.suffix == ".json":
            continue
        try:
            data = json.loads(f.read_text())
            card_name = data.get("name", "")
            if _names_match(name, card_name):
                matches.append((f, data))
        except (json.JSONDecodeError, OSError):
            continue
    log.debug("find_all_card_jsons('%s', '%s'): found %d matches: %s",
              name, faction, len(matches),
              [str(f.name) for f, _ in matches])
    return matches


def find_card_json(name, faction, owner=None):
    """Find the right card JSON for this owner.

    Cards can have duplicates across owners (e.g. Villentretenmerth.json
    owned by dek, Villentretenmerth2.json owned by dylan).

    A player can also own multiple copies of the same card (e.g. two
    Yennefer of Vengerberg cards). In that case, prefer an unchipped copy
    so each physical card gets its own RFID. If all copies for this owner
    are already chipped, return None so a new suffixed copy is created.

    Strategy:
    1. Find all JSONs with matching base name in the faction dir
    2. If owner specified:
       a. Find all copies owned by this owner
       b. Prefer an unchipped copy (no rfid field)
       c. If all are chipped, return None (new physical card needs new JSON)
    3. If no owner, prefer unowned, then first match
    """
    matches = find_all_card_jsons(name, faction)
    if not matches:
        log.info("No card JSON found for '%s' (%s)", name, faction)
        return None

    if owner:
        # Find all copies for this owner (by name or nickname)
        owner_matches = []
        for f, data in matches:
            if data.get("owner") == owner or data.get("owner_nickname") == owner:
                owner_matches.append((f, data))

        if not owner_matches:
            # No copy for this owner — they need a new one
            log.info("No copy of '%s' for owner '%s' — will create new. "
                     "Existing owners: %s", name, owner,
                     [d.get("owner", "unowned") for _, d in matches])
            return None

        # Prefer an unchipped copy (needs RFID writing)
        for f, data in owner_matches:
            if "rfid" not in data:
                log.info("Found unchipped owner copy: %s (owner=%s)", f.name, owner)
                return f

        # Prefer a copy where data changed since last write
        for f, data in owner_matches:
            rfid_written = data.get("rfid_written_at", "")
            last_updated = data.get("last_updated", "")
            if last_updated > rfid_written:
                log.info("Found stale owner copy: %s (owner=%s, last_updated=%s > rfid_written_at=%s)",
                         f.name, owner, last_updated, rfid_written)
                return f

        # All copies for this owner are chipped and current — new physical card
        log.info("All %d copies of '%s' for owner '%s' are chipped and current — "
                 "will create new copy for additional physical card",
                 len(owner_matches), name, owner)
        return None

    # No owner specified — return any match (prefer unowned)
    for f, data in matches:
        if not data.get("owner"):
            log.info("Found unowned match: %s", f.name)
            return f
    # All owned — return first match
    log.info("All copies owned, returning first: %s", matches[0][0].name)
    return matches[0][0]


def card_filename_base(name):
    """Convert card name to base filename: PascalCase with all words capitalized.

    Capitalizes the first letter of each space-separated word, then strips
    special characters. Uses word splitting instead of .title() to avoid
    capitalizing after mid-word apostrophes (Avallac'h → Avallach, not AvallacH).
    """
    import re
    words = name.split()
    words = [w[0].upper() + w[1:] for w in words if w]
    s = " ".join(words)
    s = s.replace("'", "").replace(":", "").replace(",", "")
    s = re.sub(r'[^a-zA-Z0-9]', '', s.replace(" ", ""))
    return s


def next_card_filename(name, faction):
    """Find the next available filename for a card, auto-suffixing duplicates.
    E.g. Villentretenmerth.json exists -> Villentretenmerth2.json"""
    faction_dir = FACTION_DIRS.get(faction)
    if not faction_dir:
        return None
    dirpath = CARDS_DIR / faction_dir
    base = card_filename_base(name)

    # Try without suffix first
    candidate = dirpath / f"{base}.json"
    if not candidate.exists():
        log.debug("Filename available: %s", candidate.name)
        return candidate

    # Try suffixes 2, 3, 4, ...
    for i in range(2, 100):
        candidate = dirpath / f"{base}{i}.json"
        if not candidate.exists():
            log.debug("Filename available (suffixed): %s", candidate.name)
            return candidate

    return None


def create_card_json(card_info, owner=None, nickname=None):
    """Create a new card JSON file. Returns the file path.

    If a card with the same base name already exists in this faction,
    the name gets a ': N' suffix (e.g. 'Yennefer of Vengerberg: 2')
    and the filename gets a numeric suffix (e.g. YenneferOfVengerberg2.json).
    """
    faction = card_info["faction"]
    name = card_info["name"]
    faction_dir = FACTION_DIRS.get(faction)
    if not faction_dir:
        log.error("Unknown faction '%s'", faction)
        print(f"ERROR: Unknown faction '{faction}'")
        return None

    dirpath = CARDS_DIR / faction_dir
    dirpath.mkdir(parents=True, exist_ok=True)
    filepath = next_card_filename(name, faction)
    if not filepath:
        log.error("Could not find available filename for '%s'", name)
        print(f"ERROR: Could not find available filename for {name}")
        return None

    # If the filename has a numeric suffix, add ': N' to the card name
    base = card_filename_base(name)
    fname_stem = filepath.stem  # e.g. "YenneferOfVengerberg2"
    if fname_stem != base:
        # Extract the suffix number
        suffix = fname_stem[len(base):]
        if suffix.isdigit():
            name = f"{name}: {suffix}"
            log.info("Duplicate card — suffixed name: '%s'", name)

    data = {"kind": "card", "faction": faction, "name": name}
    if "strength" in card_info and card_info["strength"] is not None:
        data["strength"] = card_info["strength"]
    if "ranges" in card_info and card_info["ranges"]:
        data["ranges"] = card_info["ranges"]
    if "specialty" in card_info and card_info["specialty"]:
        data["specialty"] = card_info["specialty"]
        # Commander and scorch cards affect all rows — ensure ranges are set
        if card_info["specialty"] in ("commander", "scorch") and "ranges" not in data:
            data["ranges"] = ["close", "ranged", "siege"]
            log.info("Auto-added all-row ranges for %s card '%s'", card_info["specialty"], name)
    if "abilities" in card_info and card_info["abilities"]:
        data["abilities"] = card_info["abilities"]
    if owner:
        data["owner"] = owner
    if nickname:
        data["owner_nickname"] = nickname
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    filepath.write_text(json.dumps(data, indent=4) + "\n")
    log.info("Created card JSON: %s -> %s", name, filepath.relative_to(REPO_ROOT))
    return filepath


def needs_chipping(card_data):
    """Check if a card needs RFID writing."""
    name = card_data.get("name", "???")
    if "rfid" not in card_data:
        log.info("Card '%s' needs chipping: no rfid field", name)
        return True
    rfid_written = card_data.get("rfid_written_at", "")
    last_updated = card_data.get("last_updated", "")
    if not rfid_written:
        log.info("Card '%s' needs chipping: no rfid_written_at", name)
        return True
    needs = last_updated > rfid_written
    if needs:
        log.info("Card '%s' needs chipping: last_updated=%s > rfid_written_at=%s",
                 name, last_updated, rfid_written)
    else:
        log.info("Card '%s' is current: rfid=%s, rfid_written_at=%s",
                 name, card_data.get("rfid"), rfid_written)
    return needs


def write_rfid(json_path):
    """Write card data to RFID chip. Returns True on success."""
    import gwent.cards.util
    import gwent.poc.util.read_write_cards as rw

    log.info("Writing RFID for %s", json_path.relative_to(REPO_ROOT))
    try:
        card = gwent.cards.util.read_card(str(json_path))
    except Exception as e:
        log.error("Card validation failed for %s: %s", json_path.name, e)
        print(f"  ERROR: Card validation failed: {e}")
        print(f"  The card JSON may need manual editing (e.g. leader cards need a 'leader' object).")
        return False
    print(f"  Place card on RFID reader... (30s timeout)")

    rfid = rw.write_card(card, str(json_path))
    if rfid is None:
        log.warning("RFID write timed out for %s", json_path.name)
        print("  RFID write timed out")
        return False

    # Update rfid_written_at in the JSON
    data = json.loads(json_path.read_text())
    data["rfid_written_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    json_path.write_text(json.dumps(data, indent=4) + "\n")
    log.info("RFID written successfully: rfid=%s, file=%s", rfid, json_path.name)
    play_write_sound()
    print(f"  RFID written: {rfid}")
    return True


def load_previous():
    """Load previous capture.json for same-card detection."""
    if CAPTURE_JSON.exists():
        try:
            data = json.loads(CAPTURE_JSON.read_text())
            log.debug("Loaded previous capture: %s (%s)",
                      data.get("name"), data.get("faction"))
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return None


def save_capture(card_info):
    """Save current card info for next-iteration comparison."""
    card_info["captured_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    CAPTURE_JSON.write_text(json.dumps(card_info, indent=4) + "\n")
    log.debug("Saved capture state: %s (%s)", card_info.get("name"), card_info.get("faction"))


def print_summary(results):
    """Print batch summary table."""
    print("\n" + "=" * 60)
    print("BATCH SUMMARY")
    print("=" * 60)
    print(f"{'#':<4} {'Card Name':<30} {'Faction':<18} {'Status'}")
    print("-" * 80)
    for i, r in enumerate(results, 1):
        print(f"{i:<4} {r['name']:<30} {r['faction']:<18} {r['status']}")
        log.info("Result #%d: %s (%s) -> %s", i, r['name'], r['faction'], r['status'])
    print("-" * 80)
    print(f"Total: {len(results)} cards processed")


def main():
    parser = argparse.ArgumentParser(description="Identify and chip Gwent cards from webcam")
    parser.add_argument("--owner", help="Card owner name")
    parser.add_argument("--nickname", help="Card owner nickname")
    parser.add_argument("--no-chip", action="store_true", help="Identify only, skip RFID writing")
    parser.add_argument("--auto", action="store_true", help="Non-interactive: auto-create JSONs, auto-write RFID, no pauses")
    parser.add_argument("--baseline", action="store_true", help="Capture a fresh baseline image before starting")
    args = parser.parse_args()

    load_dotenv()
    configure_logging(level=DEBUG, log_file=LOG_FILE)
    log.info("Starting id-and-chip-card: owner=%s, nickname=%s, no_chip=%s, auto=%s, baseline=%s",
             args.owner, args.nickname, args.no_chip, args.auto, args.baseline)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set")
        print("ERROR: ANTHROPIC_API_KEY not set. Check .env file.")
        sys.exit(1)

    ensure_gwent_stopped()
    init_sfx()

    client = anthropic.Anthropic(api_key=api_key)
    results = []

    # Clear previous capture state
    if CAPTURE_JSON.exists():
        CAPTURE_JSON.unlink()

    print("=" * 60)
    print("Gwent Card ID & Chip")
    print("=" * 60)
    if args.owner:
        print(f"Owner: {args.owner} ({args.nickname or 'no nickname'})")

    # Capture or reuse baseline image of empty surface
    baseline_b64 = None
    if args.baseline:
        baseline_b64 = capture_baseline()
    elif BASELINE_JPG.exists():
        print(f"Reusing existing baseline: {BASELINE_JPG}")
        log.info("Reusing existing baseline: %s (%d bytes)",
                 BASELINE_JPG, BASELINE_JPG.stat().st_size)
        baseline_b64 = base64.standard_b64encode(BASELINE_JPG.read_bytes()).decode("utf-8")
    else:
        log.info("No baseline image found")
        print("No baseline image found. Use --baseline to capture one.")

    print("Place cards face-up under the webcam one at a time.")
    print("Press Ctrl+C to stop.\n")
    say("Ready. Place the first card.")
    countdown()

    try:
        while True:
            card_num = len(results) + 1
            log.info("--- Card #%d ---", card_num)
            print(f"\n--- Card #{card_num} ---")

            # Step 1: Capture
            print("Capturing image...")
            if not capture_image():
                log.warning("Capture failed, retrying in 2s")
                print("Capture failed, retrying in 2s...")
                time.sleep(2)
                continue

            # Step 2: Identify
            print("Identifying card...")
            say("Identifying.", wait=False)
            card_info = identify_card(client, baseline_b64)
            if card_info is None:
                log.error("Could not identify card (API returned unparseable response)")
                print("ERROR: Could not identify card")
                say("Could not identify card.")
                results.append({"name": "???", "faction": "???", "status": "ERROR"})
                countdown()
                continue

            if card_info.get("no_card"):
                log.info("No card detected, stopping batch")
                print("No card detected, stopping batch.")
                say("No card detected. Stopping.")
                break

            name = card_info.get("name", "???")
            faction = card_info.get("faction", "???")
            log.info("Identified: %s (%s)", name, faction)
            print(f"Identified: {name} ({faction})")

            # Always confirm faction
            faction = confirm_faction(faction)
            card_info["faction"] = faction

            # Check for same card as previous
            previous = load_previous()
            if previous and previous.get("name") == name and previous.get("faction") == faction:
                log.info("Same card detected (%s), stopping batch", name)
                print(f"Same card detected ({name}), stopping batch.")
                say(f"Same card. {name}. Stopping.")
                break

            save_capture(card_info)

            # Step 3: Find or create JSON
            json_path = find_card_json(name, faction, owner=args.owner)
            created = False

            if json_path:
                log.info("Found existing JSON: %s", json_path.relative_to(REPO_ROOT))
                print(f"Found: {json_path.relative_to(REPO_ROOT)}")
            else:
                log.info("No existing JSON for '%s' (%s, owner=%s), will create",
                         name, faction, args.owner)
                print(f"No existing JSON found for {name} ({faction})")
                print(f"  Extracted: {json.dumps(card_info, indent=2)}")
                json_path = create_card_json(card_info, args.owner, args.nickname)
                if json_path:
                    print(f"  Created: {json_path.relative_to(REPO_ROOT)}")
                    say(f"New card created. {name}.")
                    created = True
                else:
                    results.append({"name": name, "faction": faction, "status": "ERROR"})
                    continue

            # Step 4: Check chipping status
            card_data = json.loads(json_path.read_text())
            log.debug("Card data: %s", json.dumps(card_data))

            # Rich announcement with all card details
            # Use card_data (JSON ground truth) for announcement, not card_info (Claude's guess)
            announcement = build_card_announcement(card_data, card_data)
            print(f"  >> {announcement}")
            say(announcement, faction=faction)

            if not needs_chipping(card_data):
                status = "EXISTS — already current"
                print(f"Card {name} is already chipped and current — skipping.")
                say(f"{name} already chipped. Skipping.")
                results.append({"name": name, "faction": faction, "status": status})
                say("Ready for next card")
                countdown()
                continue

            # Step 5: Write RFID
            if args.no_chip:
                prefix = "CREATED" if created else "EXISTS"
                status = f"{prefix} — chip skipped (--no-chip)"
                log.info("Skipping RFID write (--no-chip) for '%s'", name)
                print(f"Skipping RFID write (--no-chip)")
                say(f"{name} needs chipping but skipped.")
                results.append({"name": name, "faction": faction, "status": status})
                say("Ready for next card")
                countdown()
                continue

            reason = "no RFID" if "rfid" not in card_data else "data updated since last write"
            log.info("Card '%s' needs chipping: %s", name, reason)
            print(f"Needs chipping ({reason})")
            say(f"Place {name} on the reader")
            success = write_rfid(json_path)
            prefix = "CREATED" if created else "EXISTS"
            if success:
                status = f"{prefix} + CHIPPED"
                say(f"{name} written successfully")
            else:
                status = f"{prefix} — CHIP FAILED"
                say(f"Failed to write {name}")

            results.append({"name": name, "faction": faction, "status": status})
            say("Ready for next card")
            countdown()

    except KeyboardInterrupt:
        log.info("Stopped by user (Ctrl+C)")
        print("\n\nStopped by user.")

    if results:
        print_summary(results)

    log.info("Session complete: %d cards processed", len(results))


if __name__ == "__main__":
    main()
