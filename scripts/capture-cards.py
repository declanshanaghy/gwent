#!/usr/bin/env python3
"""Capture, crop, identify, and catalog Gwent card photos.

Captures images from USB webcam, crops/deskews the card, identifies it via
Claude vision API, confirms faction with the user, and saves the image to
the correct faction directory with the card name.

Usage:
    python scripts/capture-cards.py [--owner NAME] [--baseline] [--tts PROVIDER]
"""

import argparse
import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ExifTags

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
GWENT_PKG = REPO_ROOT / "software" / "gwent"
GWENT_SHARED_PKG = REPO_ROOT / "software" / "gwent-shared"
sys.path.insert(0, str(GWENT_PKG))
sys.path.insert(0, str(GWENT_SHARED_PKG))

CARDS_DIR = REPO_ROOT / "software" / "data" / "cards"
IMAGES_DIR = REPO_ROOT / "software" / "data" / "images"
WEBCAM_DIR = REPO_ROOT / "tmp" / "webcam"
CAPTURE_JPG = WEBCAM_DIR / "capture.jpg"
BASELINE_JPG = WEBCAM_DIR / "baseline.jpg"
WEBCAM_DEVICE = "/dev/video0"

LOG_FILE = "/tmp/logs/capture-cards.log"

log = logging.getLogger("capture-cards")

# ---------------------------------------------------------------------------
# Factions
# ---------------------------------------------------------------------------
FACTIONS = ["Monsters", "Northern Realms", "Nilfgaardian", "Scoia'tael", "Skellige"]

FACTION_DIRS = {
    "Monsters": "Monsters",
    "Northern Realms": "NorthernRealms",
    "Nilfgaardian": "Nilfgaardian",
    "Scoia'tael": "Scoiatael",
    "Skellige": "Skellige",
}

# ---------------------------------------------------------------------------
# Card identification prompt  (shared with id-and-chip-card.py)
# ---------------------------------------------------------------------------
IDENTIFY_PROMPT = """\
Analyze this photo of a physical Gwent card (The Witcher III). Respond with ONLY a JSON object.

If no card face is clearly visible, respond: {"no_card": true}
This includes: card back, blank surface, hand/fingers in the way, blurry/out of focus image,
card being placed or removed (partially visible), or if you are unsure about the identification.
If given a BASELINE IMAGE, compare against it — if essentially identical, respond: {"no_card": true}

## Card Layout

There are TWO card layouts:

### Regular cards (top to bottom along the left sash)

The left side has a vertical colored SASH. Reading top-to-bottom along it:

1. STRENGTH MEDALLION (top) — round circle with a number. Omit for special cards.
2. RANGE ICON(S) — in orange circles below strength:
   - Sword = "close"
   - Crossed bow/arrows = "ranged"
   - Catapult = "siege"
   Cards can have MULTIPLE range icons stacked. List ALL. If 2+ ranges, add "agile" to abilities.
3. ABILITY ICON (bottom) — in a circle with an obvious border, below range icons.
   Only count large circled icons. Small sash decorations/crests are NOT abilities.

### Leader cards (different layout — NO sash, NO strength, NO ranges)

Leader cards have NO vertical sash and NO strength number. Instead:
- A FACTION EMBLEM / CROWN at the top-left corner (ornate circular medallion)
- Full-bleed artwork covering most of the card
- Card NAME in large text below the art
- LEADER ABILITY TEXT below the name describing the leader's power
- Faction determined by the emblem color/style and card border tint

Leader cards MUST have: "specialty": "leader"
Leader cards do NOT have: strength, ranges, or abilities.
Include the leader ability text in "card_text".

Card NAME is printed at the bottom of the card. Some names wrap across multiple lines —
read ALL lines (e.g. "Emiel Regis Rohellec Terzieff").

LEADER NAMES have TWO lines: the character name on the first line and a SUBTITLE on the
second line in smaller text. Combine them with a colon separator:
  "Francesca Findabair" + "Daisy of the Valley" = "Francesca Findabair: Daisy of the Valley"
  "Foltest" + "the Siegemaster" = "Foltest: the Siegemaster"
  "Eredin" + "Bringer of Death" = "Eredin: Bringer of Death"
Plain leader names with no subtitle are also valid (e.g. "Crach an Craite").

## Faction (from sash color)

Determine faction ONLY from the sash color. Same card can appear in different factions.
- BRIGHT VIVID RED = "Monsters"
- BLUE = "Northern Realms"
- GREEN = "Scoia'tael"
- PURPLE / VIOLET = "Skellige"
- DARK GOLD / BRONZE / BROWN / TAN = "Nilfgaardian" — often looks muted, desaturated,
  or even greyish under poor lighting. If the sash looks brownish, tan, khaki, or warm grey,
  it is Nilfgaardian. Confirm with crest: Nilfgaardian = sun/star, Monsters = skull/beast.
IMPORTANT: Webcam lighting can wash out colors. A Nilfgaardian dark gold sash may appear
grey or brown. Look at the CREST at the bottom of the sash for confirmation:
- Sun/star crest = Nilfgaardian
- Skull/beast crest = Monsters
- Fleur-de-lis crest = Northern Realms
- Arrow/leaf crest = Scoia'tael
- Shield/axe crest = Skellige

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

## Card text

Read any flavour or ability text printed below the card name (usually in italics).
Include it in the "card_text" field. Omit if none.

## Response format

JSON only. Include only fields with values. Examples:
{"name": "Geralt of Rivia", "faction": "Northern Realms", "strength": 15, "ranges": ["close"], "specialty": "hero", "card_text": "If that's what it takes to save the world, it's better to let that world die."}
{"name": "Yaevinn", "faction": "Scoia'tael", "strength": 6, "ranges": ["close", "ranged"], "abilities": ["agile"]}
{"name": "Isengrim Faoiltiarna", "faction": "Scoia'tael", "strength": 10, "ranges": ["close"], "abilities": ["medic"]}
{"name": "Scorch", "faction": "Monsters", "specialty": "scorch", "card_text": "Pillars of flame turn the mightiest to ash. All others tremble in shock and awe."}
{"name": "Crach an Craite", "faction": "Skellige", "specialty": "leader", "card_text": "Shuffle all cards from each player's graveyard back into their decks."}
"""

# ---------------------------------------------------------------------------
# Card aspect ratio for crop
# ---------------------------------------------------------------------------
CARD_ASPECT = 63.0 / 88.0
CARD_OUTPUT_HEIGHT = 1200
CARD_OUTPUT_WIDTH = int(CARD_OUTPUT_HEIGHT * CARD_ASPECT)

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def load_dotenv():
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), value)


def configure_logging():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stderr),
        ],
    )
    logging.getLogger().setLevel(logging.WARNING)
    log.setLevel(logging.DEBUG)


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

_tts = None
_tts_counter = 0


def init_tts(provider_name="gtts"):
    """Initialize the TTS provider."""
    global _tts
    try:
        from gwent_shared.tts import get_provider
        _tts = get_provider(provider_name)
        log.info("TTS initialized: %s", provider_name)
    except Exception as e:
        log.warning("Could not init TTS (%s): %s", provider_name, e)
        print(f"WARNING: TTS init failed ({provider_name}): {e}")
        _tts = None


def say(text, faction=None):
    """Speak text using the configured TTS provider. Non-blocking not needed here."""
    global _tts_counter
    if _tts is None:
        return
    _tts_counter += 1
    tmp_dir = Path("/tmp/capture-cards-tts")
    tmp_dir.mkdir(exist_ok=True)

    ext = ".wav" if _tts.native_wav else ".mp3"
    audio_file = tmp_dir / f"speech_{_tts_counter}{ext}"
    try:
        _tts.synthesize(text, faction, str(audio_file))
        if ext == ".wav":
            subprocess.run(["aplay", "-q", str(audio_file)],
                           capture_output=True, timeout=15)
        else:
            subprocess.run(["mpg123", "-q", str(audio_file)],
                           capture_output=True, timeout=15)
    except Exception as e:
        log.debug("TTS playback failed: %s", e)
    finally:
        audio_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Webcam capture
# ---------------------------------------------------------------------------

def capture_image(output_path=None):
    """Capture a single frame from the webcam using fswebcam."""
    if output_path is None:
        output_path = CAPTURE_JPG
    WEBCAM_DIR.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["fswebcam", "-r", "1920x1080", "--no-banner", "-S", "20",
         str(output_path)],
        capture_output=True, text=True, timeout=15,
    )
    if not output_path.exists() or output_path.stat().st_size < 1000:
        log.error("Capture failed")
        print("ERROR: Failed to capture image from webcam")
        return False
    log.info("Captured %s (%d bytes)", output_path.name, output_path.stat().st_size)
    _play_capture_sound()
    return True


CAPTURE_WAV = REPO_ROOT / "software" / "gwent" / "gwent" / "hal" / "effects" / "card_read.wav"


def _play_capture_sound():
    """Play the card_read.wav sound on capture."""
    if CAPTURE_WAV.exists():
        subprocess.Popen(
            ["aplay", "-q", str(CAPTURE_WAV)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


# ---------------------------------------------------------------------------
# Card identification via Claude
# ---------------------------------------------------------------------------

def identify_card(client, image_path, baseline_b64=None):
    """Send image to Claude for identification. Returns dict or None."""
    image_data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")

    content = []
    if baseline_b64:
        content.append({"type": "text", "text": "BASELINE IMAGE (empty surface, no card):"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": baseline_b64},
        })
        content.append({"type": "text", "text": "CURRENT IMAGE (identify the card):"})

    content.append({
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data},
    })
    content.append({"type": "text", "text": IDENTIFY_PROMPT})

    import anthropic
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": content}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.error("Could not parse Claude response: %s", text)
        print(f"ERROR: Could not parse: {text}")
        return None


# ---------------------------------------------------------------------------
# Faction confirmation
# ---------------------------------------------------------------------------

def confirm_faction(detected_faction):
    """Confirm or correct the detected faction via stdin."""
    print(f"\n  Detected faction: {detected_faction}")
    print("  Factions:")
    for i, f in enumerate(FACTIONS, 1):
        marker = " <<" if f == detected_faction else ""
        print(f"    {i}. {f}{marker}")
    print(f"  Press Enter to accept '{detected_faction}', or enter number: ", end="", flush=True)
    try:
        choice = input().strip()
    except EOFError:
        return detected_faction
    if not choice:
        return detected_faction
    try:
        idx = int(choice)
        if 1 <= idx <= len(FACTIONS):
            return FACTIONS[idx - 1]
    except ValueError:
        pass
    return detected_faction


# ---------------------------------------------------------------------------
# Crop / deskew
# ---------------------------------------------------------------------------

def apply_exif_orientation(pil_img):
    """Rotate image according to EXIF orientation tag."""
    try:
        exif = pil_img._getexif()
        if not exif:
            return pil_img
        orient_key = next(k for k, v in ExifTags.TAGS.items() if v == "Orientation")
        orient = exif.get(orient_key)
        if orient == 3:
            return pil_img.rotate(180, expand=True)
        elif orient == 6:
            return pil_img.rotate(270, expand=True)
        elif orient == 8:
            return pil_img.rotate(90, expand=True)
    except (StopIteration, AttributeError, KeyError):
        pass
    return pil_img


def order_points(pts):
    """Order 4 points as: top-left, top-right, bottom-right, bottom-left.

    Uses Y-coordinate sorting (top pair vs bottom pair) for robustness
    with rotated rectangles from minAreaRect.
    """
    sorted_by_y = pts[np.argsort(pts[:, 1])]
    top2 = sorted_by_y[:2]
    bot2 = sorted_by_y[2:]
    tl = top2[np.argmin(top2[:, 0])]
    tr = top2[np.argmax(top2[:, 0])]
    bl = bot2[np.argmin(bot2[:, 0])]
    br = bot2[np.argmax(bot2[:, 0])]
    return np.array([tl, tr, br, bl], dtype="float32")


def _find_card_rect(contours, small_area, scale):
    """Find the best card-shaped contour via minAreaRect.

    Uses minAreaRect for a tight rotated bounding box that properly
    captures the card angle for deskewing. Shrinks 2% inward to
    trim edge bleed from the background.
    """
    for c in contours[:10]:
        area = cv2.contourArea(c)
        ratio = area / small_area
        if ratio < 0.05 or ratio > 0.8:
            continue

        rect = cv2.minAreaRect(c)
        w, h = rect[1]
        if w == 0 or h == 0:
            continue

        aspect = min(w, h) / max(w, h)
        fill = area / (w * h) if w * h > 0 else 0

        # Card aspect ~0.716; accept 0.5-0.9 range; fill > 0.5
        if 0.5 < aspect < 0.9 and fill > 0.5:
            box = cv2.boxPoints(rect)
            corners = (box / scale).astype("float32")
            # Shrink 2% inward from center to trim background bleed
            center = corners.mean(axis=0)
            corners = center + (corners - center) * 0.98
            return corners

    return None


# Global baseline image for diff-based detection
_baseline_cv = None


def set_baseline(image_path):
    """Load a baseline image for diff-based card detection."""
    global _baseline_cv
    _baseline_cv = cv2.imread(str(image_path))
    if _baseline_cv is not None:
        log.info("Baseline loaded: %s (%s)", image_path, _baseline_cv.shape)


def find_card_contour(cv_img):
    """Find the card rectangle.

    If a baseline is available, diffs against it, uses Otsu threshold
    and convex hull for a clean card outline. Falls back to edge detection.
    """
    img_area = cv_img.shape[0] * cv_img.shape[1]

    # Strategy 1: Baseline diff + Otsu + convex hull (most reliable)
    if _baseline_cv is not None:
        bl = cv2.resize(_baseline_cv, (cv_img.shape[1], cv_img.shape[0]))
        diff = cv2.absdiff(bl, cv_img)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray_diff, (11, 11), 0)
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Large close kernel to bridge gaps where light card text
        # blends with the background in the diff
        close_k = cv2.getStructuringElement(cv2.MORPH_RECT, (60, 60))
        closed = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, close_k)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        for c in contours[:5]:
            area = cv2.contourArea(c)
            if area / img_area < 0.05:
                continue
            hull = cv2.convexHull(c)
            result = _find_card_rect([hull], img_area, 1.0)
            if result is not None:
                return result

    # Strategy 2: Edge detection fallback
    scale = 0.5
    small = cv2.resize(cv_img, (0, 0), fx=scale, fy=scale)
    small_area = small.shape[0] * small.shape[1]
    filtered = cv2.bilateralFilter(small, 9, 75, 75)
    gray = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.dilate(edges, kernel, iterations=2)
    edges = cv2.erode(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    return _find_card_rect(contours, small_area, scale)


def crop_card(image_path):
    """Crop and deskew a card photo. Returns cropped cv2 image or None."""
    pil_img = Image.open(image_path)
    pil_img = apply_exif_orientation(pil_img)
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    corners = find_card_contour(cv_img)
    if corners is None:
        return None

    ordered = order_points(corners)
    tl, tr, br, bl = ordered
    avg_w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    avg_h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2

    if avg_w > avg_h:
        out_w, out_h = CARD_OUTPUT_HEIGHT, CARD_OUTPUT_WIDTH
    else:
        out_w, out_h = CARD_OUTPUT_WIDTH, CARD_OUTPUT_HEIGHT

    dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
                   dtype="float32")
    M = cv2.getPerspectiveTransform(ordered, dst)
    warped = cv2.warpPerspective(cv_img, M, (out_w, out_h))

    if avg_w > avg_h:
        warped = cv2.rotate(warped, cv2.ROTATE_90_COUNTERCLOCKWISE)

    return warped


# ---------------------------------------------------------------------------
# Card JSON helpers (from id-and-chip-card.py)
# ---------------------------------------------------------------------------

def card_filename_base(name):
    """Convert card name to PascalCase filename base."""
    import re
    words = name.split()
    words = [w[0].upper() + w[1:] for w in words if w]
    s = " ".join(words)
    s = s.replace("'", "").replace(":", "").replace(",", "")
    return re.sub(r'[^a-zA-Z0-9]', '', s.replace(" ", ""))


def _base_name(name):
    if ":" in name:
        before, _, after = name.rpartition(":")
        if after.strip().isdigit():
            return before.strip()
    return name.strip()


def _edit_distance(a, b):
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
    if detected == stored:
        return True
    det_base = _base_name(detected).lower()
    sto_base = _base_name(stored).lower()
    if det_base == sto_base:
        return True
    if len(det_base) >= 8 and len(sto_base) >= 8:
        shorter, longer = (det_base, sto_base) if len(det_base) <= len(sto_base) else (sto_base, det_base)
        if longer.startswith(shorter) and len(shorter) >= len(longer) * 0.35:
            return True
    if len(det_base) >= 8 and len(sto_base) >= 8:
        if _edit_distance(det_base, sto_base) <= 2:
            return True
    return False


def find_card_json(name, faction):
    """Find a card JSON matching the name in the faction directory."""
    faction_dir = FACTION_DIRS.get(faction)
    if not faction_dir:
        return None
    search_dir = CARDS_DIR / faction_dir
    if not search_dir.exists():
        return None

    for f in search_dir.iterdir():
        if f.suffix != ".json":
            continue
        try:
            data = json.loads(f.read_text())
            if _names_match(name, data.get("name", "")):
                return f
        except (json.JSONDecodeError, OSError):
            continue
    return None


def update_card_json(card_json_path, image_rel_path, card_text=None):
    """Update 'image' and optionally 'card_text' in a card JSON file."""
    data = json.loads(card_json_path.read_text())
    data["image"] = image_rel_path
    if card_text:
        data["card_text"] = card_text
    card_json_path.write_text(json.dumps(data, indent=4) + "\n")


# ---------------------------------------------------------------------------
# Bounding box persistence
# ---------------------------------------------------------------------------

BBOX_FILE = WEBCAM_DIR / "cc.json"

# Default bounding box [x, y, w, h] in pixels (1920x1080 webcam)
DEFAULT_BBOX = [480, 30, 500, 900]
MOVE_STEP = 10   # pixels per arrow key press
RESIZE_STEP = 10  # pixels per shift+arrow press


def load_bbox():
    """Load saved bounding box or return default."""
    if BBOX_FILE.exists():
        try:
            data = json.loads(BBOX_FILE.read_text())
            if len(data) == 4:
                return list(data)
        except (json.JSONDecodeError, OSError):
            pass
    return list(DEFAULT_BBOX)


def estimate_bbox_from_image(image_path):
    """Use the CV card detection algorithm to estimate a bounding box."""
    img = cv2.imread(str(image_path))
    if img is None:
        return None
    corners = find_card_contour(img)
    if corners is None:
        return None
    # Convert 4 corners to axis-aligned bounding box [x, y, w, h]
    x_min = int(corners[:, 0].min())
    y_min = int(corners[:, 1].min())
    x_max = int(corners[:, 0].max())
    y_max = int(corners[:, 1].max())
    return [x_min, y_min, x_max - x_min, y_max - y_min]


def save_bbox(bbox):
    """Save bounding box to disk."""
    WEBCAM_DIR.mkdir(parents=True, exist_ok=True)
    BBOX_FILE.write_text(json.dumps(bbox))


def draw_bbox_on_image(src_path, dst_path, bbox):
    """Draw the bounding box on an image and save."""
    img = cv2.imread(str(src_path))
    if img is None:
        return
    x, y, w, h = bbox
    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)
    # Corner labels
    for label, px, py in [("TL", x, y - 8), ("BR", x + w - 40, y + h + 22)]:
        cv2.putText(img, label, (px, py), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    # Size label
    cv2.putText(img, f"{w}x{h}", (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.imwrite(str(dst_path), img, [cv2.IMWRITE_JPEG_QUALITY, 90])


def crop_with_bbox(src_path, bbox):
    """Crop image using the bounding box. Returns cv2 image."""
    img = cv2.imread(str(src_path))
    if img is None:
        return None
    ih, iw = img.shape[:2]
    x, y, w, h = bbox
    x1 = max(0, min(x, iw - 1))
    y1 = max(0, min(y, ih - 1))
    x2 = max(0, min(x + w, iw))
    y2 = max(0, min(y + h, ih))
    cropped = img[y1:y2, x1:x2]
    # Resize to standard card dimensions
    return cv2.resize(cropped, (CARD_OUTPUT_WIDTH, CARD_OUTPUT_HEIGHT))


# ---------------------------------------------------------------------------
# Textual TUI App
# ---------------------------------------------------------------------------

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Header
from textual.worker import get_current_worker
from textual_image.widget import TGPImage

_BLANK_IMG = WEBCAM_DIR / "blank.jpg"


def _ensure_blank():
    WEBCAM_DIR.mkdir(parents=True, exist_ok=True)
    if not _BLANK_IMG.exists():
        blank = np.zeros((100, 72, 3), dtype=np.uint8) + 40
        cv2.imwrite(str(_BLANK_IMG), blank)


FACTION_STYLES = {
    "Monsters": "bold red",
    "Northern Realms": "bold dodger_blue2",
    "Nilfgaardian": "bold dark_goldenrod",
    "Scoia'tael": "bold green",
    "Skellige": "bold medium_purple",
}

STATE_READY = "ready"
STATE_BUSY = "busy"
STATE_BBOX = "bbox"         # adjusting bounding box
STATE_PICK_FACTION = "pick_faction"  # select faction before auto starts
STATE_AUTO = "auto"         # auto-capture loop
STATE_CONFIRM = "confirm"   # confirming faction before save
STATE_OVERWRITE = "overwrite"
STATE_FIX = "fix"           # fix last auto-saved card (wrong faction)
STATE_SAME_CARD = "same_card"  # same card detected again — save another or rescan?

AUTO_DELAY = 3  # seconds between auto captures


class CardInfoPanel(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._info = {}

    def set_info(self, info: dict):
        self._info = info
        self.refresh()

    def render(self):
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        info = self._info
        if not info:
            return Panel("[dim]No card scanned yet[/]", title="Card Data",
                         border_style="bright_cyan")
        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), expand=True)
        t.add_column("Field", style="bold bright_cyan", width=12)
        t.add_column("Value")
        name = info.get("name", "???")
        faction = info.get("faction", "???")
        style = FACTION_STYLES.get(faction, "")
        t.add_row("Name", f"[bold bright_white]{name}[/]")
        t.add_row("Faction", f"[{style}]{faction}[/]")
        if info.get("strength") is not None:
            t.add_row("Strength", str(info["strength"]))
        if info.get("ranges"):
            t.add_row("Ranges", ", ".join(info["ranges"]))
        if info.get("specialty"):
            t.add_row("Specialty", info["specialty"])
        if info.get("abilities"):
            t.add_row("Abilities", ", ".join(info["abilities"]))
        if info.get("card_text"):
            t.add_row("Text", f"[italic]{info['card_text']}[/]")
        status = info.get("_status", "")
        if status:
            t.add_row("", status)
        return Panel(t, title="Card Data", border_style="bright_cyan")


class FactionSelector(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._index = 0
        self._active = False

    @property
    def selected(self):
        return FACTIONS[self._index]

    def set_faction(self, faction: str):
        try:
            self._index = FACTIONS.index(faction)
        except ValueError:
            self._index = 0
        self.refresh()

    def set_active(self, active: bool):
        self._active = active
        self.refresh()

    def move_up(self):
        self._index = (self._index - 1) % len(FACTIONS)
        self.refresh()

    def move_down(self):
        self._index = (self._index + 1) % len(FACTIONS)
        self.refresh()

    def render(self):
        from rich.panel import Panel
        lines = []
        for i, f in enumerate(FACTIONS):
            style = FACTION_STYLES.get(f, "")
            if i == self._index:
                lines.append(f"  [{style}]> {f}[/]")
            else:
                lines.append(f"  [dim]  {f}[/]")
        border = "bright_yellow" if self._active else "dim"
        hint = " [dim](arrows + Enter)[/]" if self._active else ""
        return Panel("\n".join(lines), title=f"Faction{hint}", border_style=border)


class StatusBar(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._text = ""

    def set_text(self, text: str):
        self._text = text
        self.refresh()

    def render(self):
        return self._text


class ResultsPanel(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._results = []

    def add_result(self, name, faction, status):
        self._results.append({"name": name, "faction": faction, "status": status})
        self.refresh()

    def render(self):
        from rich.panel import Panel
        from rich.table import Table
        from rich import box
        if not self._results:
            return Panel("[dim]No cards captured yet[/]", title="Results", border_style="dim")
        t = Table(box=box.SIMPLE, show_header=True, padding=(0, 1), expand=True)
        t.add_column("#", width=3)
        t.add_column("Card", ratio=2)
        t.add_column("Faction", ratio=1)
        t.add_column("Status", ratio=1)
        for i, r in enumerate(self._results, 1):
            style = "green" if r["status"] == "OK" else "yellow"
            t.add_row(str(i), r["name"], r["faction"], f"[{style}]{r['status']}[/]")
        return Panel(t, title=f"Results ({len(self._results)} cards)", border_style="bright_green")


class CaptureCardsApp(App):
    """Gwent Card Capture — bounding box crop workflow.

    First capture: shows image with bounding box overlay.
    Arrow keys move, Shift+arrows resize. Enter confirms bbox.
    Subsequent captures use the saved bbox automatically.
    B = re-adjust bbox on next capture.
    """

    TITLE = "Gwent Card Capture"

    CSS = """
    Screen { layout: vertical; }
    #main { height: 1fr; }
    #image-pane { width: 2fr; height: 1fr; border: solid ansi_bright_cyan; border-title-color: ansi_bright_cyan; align: center middle; overflow: hidden; }
    #card-img { max-height: 100%; max-width: 100%; }
    #sidebar { width: 1fr; height: 1fr; }
    #faction-sel { height: auto; max-height: 10; }
    #card-info { height: 1fr; }
    #results { height: auto; max-height: 15; overflow-y: auto; }
    #status-bar { height: 1; content-align: center middle; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def __init__(self, owner=None, tts_provider="gtts", force_baseline=False, auto_variation=False):
        super().__init__()
        self._owner = owner
        self._tts_provider = tts_provider
        self._force_baseline = force_baseline
        self._auto_variation = auto_variation
        self._client = None
        self._baseline_b64 = None
        self._card_info = None
        self._cropped_cv = None
        self._state = STATE_READY
        self._bbox = load_bbox()
        self._bbox_confirmed = BBOX_FILE.exists()
        self._need_bbox_adjust = not self._bbox_confirmed
        self._auto_mode = False
        self._auto_timer = None
        self._auto_faction = None          # locked faction for auto mode
        self._last_saved_path = None       # path to last auto-saved image
        self._last_saved_sidecar = None    # path to last auto-saved sidecar
        self._last_saved_card_json = None  # card JSON that was updated
        self._last_saved_old_image = None  # previous image value in card JSON

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            pane = Vertical(id="image-pane")
            pane.border_title = "Card"
            with pane:
                yield TGPImage(str(_BLANK_IMG), id="card-img")
            with Vertical(id="sidebar"):
                yield FactionSelector(id="faction-sel")
                yield CardInfoPanel(id="card-info")
                yield ResultsPanel(id="results")
        yield StatusBar(id="status-bar")

    def on_mount(self):
        load_dotenv()
        configure_logging()
        init_tts(self._tts_provider)

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            self._status("[bold red]ANTHROPIC_API_KEY not set. Check .env[/]")
            return

        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

        if BASELINE_JPG.exists() and not self._force_baseline:
            set_baseline(BASELINE_JPG)
            self._load_baseline_b64()

        if self._auto_mode and self._bbox_confirmed:
            self._start_auto()
        else:
            self._set_ready()

    def _load_baseline_b64(self):
        """Load baseline image, crop it with the current bbox, and encode for API."""
        if not BASELINE_JPG.exists():
            self._baseline_b64 = None
            return
        if self._bbox_confirmed:
            # Crop baseline with same bbox so the model compares like-for-like
            cropped = crop_with_bbox(BASELINE_JPG, self._bbox)
            if cropped is not None:
                baseline_cropped = WEBCAM_DIR / "baseline_cropped.jpg"
                cv2.imwrite(str(baseline_cropped), cropped, [cv2.IMWRITE_JPEG_QUALITY, 90])
                self._baseline_b64 = base64.standard_b64encode(
                    baseline_cropped.read_bytes()).decode("utf-8")
                return
        # Fallback: use full baseline
        self._baseline_b64 = base64.standard_b64encode(
            BASELINE_JPG.read_bytes()).decode("utf-8")

    def _status(self, text: str):
        try:
            self.query_one("#status-bar", StatusBar).set_text(text)
        except Exception:
            pass

    def _update_image(self, path):
        try:
            self.query_one("#card-img", TGPImage).image = str(path)
        except Exception:
            pass

    def _set_ready(self, prefix=""):
        self._state = STATE_READY
        self._stop_auto_timer()
        msg = f"{prefix} " if prefix else ""
        if self._auto_mode and self._bbox_confirmed:
            # Resume auto mode
            self._start_auto()
            return
        bbox_hint = " [dim](bbox not set)[/]" if self._need_bbox_adjust else ""
        auto_hint = " · [bold]A[/] auto" if not self._auto_mode else ""
        self._status(f"{msg}[bold]Enter[/] capture · [bold]B[/] bbox · [bold]A[/] auto · [bold]Ctrl+C[/] quit{bbox_hint}{auto_hint}")

    def _start_auto(self):
        """Start auto-capture loop — pick faction first if not set."""
        if self._auto_faction is None:
            self._state = STATE_PICK_FACTION
            sel = self.query_one("#faction-sel", FactionSelector)
            sel.set_active(True)
            self._status(
                "[bold]Up/Down[/] select faction · [bold]Enter[/] start auto · [bold]Esc[/] cancel"
            )
            say("Select faction for auto mode.")
            return
        self._state = STATE_AUTO
        faction_style = FACTION_STYLES.get(self._auto_faction, "")
        self._status(
            f"[bold green]AUTO[/] [{faction_style}]{self._auto_faction}[/] — "
            f"[bold]Enter/A[/] stop · [bold]F[/] change faction"
        )
        self._stop_auto_timer()
        self._auto_timer = self.set_timer(AUTO_DELAY, self._auto_capture_tick)

    def _stop_auto_timer(self):
        if self._auto_timer is not None:
            self._auto_timer.stop()
            self._auto_timer = None

    def _auto_capture_tick(self):
        """Timer callback: trigger a capture in auto mode."""
        if self._state != STATE_AUTO:
            return
        self._state = STATE_BUSY
        self._status("[bold yellow]Auto-capturing...[/]")
        self.run_worker(self._worker_auto_capture, thread=True)

    def _stop_auto_and_fix(self):
        """Stop auto mode. Show last card info for review."""
        self._auto_mode = False
        self._stop_auto_timer()
        if self._last_saved_path and self._card_info:
            self._state = STATE_FIX
            info = self._card_info
            info["_status"] = (
                f"[bold yellow]PAUSED[/] — Last: {self._last_saved_path.name}\n"
                "[bold]Up/Down[/] fix faction · [bold]Enter[/] re-save · [bold]Esc[/] delete"
            )
            self.query_one("#card-info", CardInfoPanel).set_info(info)
            sel = self.query_one("#faction-sel", FactionSelector)
            sel.set_faction(info.get("faction", FACTIONS[0]))
            sel.set_active(True)
            self._status(
                "[bold yellow]PAUSED[/] [bold]Up/Down[/] faction · "
                "[bold]Enter[/] re-save · [bold]Esc[/] delete · [bold]A[/] resume"
            )
        else:
            self._set_ready("Auto stopped.")

    def _stop_auto_and_fix_faction(self):
        """Pause auto to change faction. Also lets user fix last saved card."""
        self._stop_auto_timer()
        self._state = STATE_FIX
        sel = self.query_one("#faction-sel", FactionSelector)
        sel.set_faction(self._auto_faction or FACTIONS[0])
        sel.set_active(True)

        if self._last_saved_path and self._card_info:
            info = self._card_info
            info["_status"] = (
                f"[bold yellow]FIX FACTION[/] — Last: {self._last_saved_path.name}\n"
                "[bold]Up/Down[/] change · [bold]Enter[/] set faction & fix last card"
            )
            self.query_one("#card-info", CardInfoPanel).set_info(info)
            say("Fix faction.")
            self._status(
                "[bold yellow]FIX FACTION[/] [bold]Up/Down[/] change · "
                "[bold]Enter[/] set & fix last · [bold]Esc[/] set only · [bold]A[/] resume"
            )
        else:
            say("Change faction.")
            self._status(
                "[bold yellow]CHANGE FACTION[/] [bold]Up/Down[/] select · "
                "[bold]Enter[/] confirm · [bold]Esc[/] cancel"
            )

    def _show_bbox_overlay(self):
        """Draw bbox on current capture and display it."""
        overlay_path = WEBCAM_DIR / "bbox_overlay.jpg"
        draw_bbox_on_image(CAPTURE_JPG, overlay_path, self._bbox)
        self._update_image(overlay_path)

    def _enter_bbox_mode(self):
        self._state = STATE_BBOX
        self._show_bbox_overlay()
        x, y, w, h = self._bbox
        self._status(
            f"[bold]Arrows[/] move · [bold]Shift+Arrows[/] resize · "
            f"[bold]Enter[/] confirm · box: {x},{y} {w}x{h}"
        )

    # --- Key handling ---

    def on_key(self, event):
        # --- Auto mode: only Enter, A, and F are handled ---
        if self._state == STATE_AUTO:
            if event.key in ("enter", "a"):
                event.prevent_default()
                self._stop_auto_and_fix()
            elif event.key == "f":
                event.prevent_default()
                self._stop_auto_and_fix_faction()
            elif event.key == "p":
                event.prevent_default()
                self._stop_auto_timer()
                self._auto_mode = False
                self._state = STATE_READY
                self._status("[bold yellow]PAUSED[/] — [bold]A[/] resume auto · [bold]Enter[/] manual capture")
            return

        if event.key == "enter":
            event.prevent_default()
            if self._state == STATE_READY:
                self._do_start_capture()
            elif self._state == STATE_BBOX:
                self._confirm_bbox()
            elif self._state == STATE_PICK_FACTION:
                sel = self.query_one("#faction-sel", FactionSelector)
                self._auto_faction = sel.selected
                sel.set_active(False)
                say(f"{self._auto_faction}.")
                # Now actually start the auto loop
                self._state = STATE_AUTO
                faction_style = FACTION_STYLES.get(self._auto_faction, "")
                self._status(
                    f"[bold green]AUTO[/] [{faction_style}]{self._auto_faction}[/] — "
                    f"[bold]Enter/A[/] stop · [bold]F[/] change faction"
                )
                self._stop_auto_timer()
                self._auto_timer = self.set_timer(AUTO_DELAY, self._auto_capture_tick)
            elif self._state == STATE_CONFIRM:
                self._do_save()
            elif self._state == STATE_OVERWRITE:
                self._do_write_image(overwrite=True)
            elif self._state == STATE_FIX:
                self._do_fix_save()
            elif self._state == STATE_SAME_CARD:
                # Save another copy
                self._card_info = self._pending_same_card_info
                self._pending_same_card_info = None
                self._on_id_success_auto(self._card_info)

        elif event.key == "escape":
            event.prevent_default()
            if self._state == STATE_BBOX:
                self._set_ready("Bbox unchanged.")
            elif self._state == STATE_PICK_FACTION:
                self.query_one("#faction-sel", FactionSelector).set_active(False)
                self._auto_mode = False
                self._set_ready("Auto cancelled.")
            elif self._state == STATE_CONFIRM:
                self._card_info = None
                self.query_one("#faction-sel", FactionSelector).set_active(False)
                self._set_ready("Discarded.")
            elif self._state == STATE_OVERWRITE:
                self._card_info = None
                self._set_ready("Cancelled.")
            elif self._state == STATE_FIX:
                # In fix mode, Esc = set faction without fixing last card, resume auto
                sel = self.query_one("#faction-sel", FactionSelector)
                self._auto_faction = sel.selected
                sel.set_active(False)
                self._auto_mode = True
                self._start_auto()
            elif self._state == STATE_SAME_CARD:
                # Skip — resume auto to rescan
                self._pending_same_card_info = None
                self._state = STATE_AUTO
                self._start_auto()

        elif event.key == "a" and self._state in (STATE_READY, STATE_FIX):
            event.prevent_default()
            self._auto_mode = True
            self.query_one("#faction-sel", FactionSelector).set_active(False)
            self._auto_faction = None  # Force faction re-selection
            self._start_auto()

        elif event.key == "b" and self._state in (STATE_READY, STATE_FIX):
            event.prevent_default()
            self._auto_mode = False
            self._need_bbox_adjust = True
            self._status("Bbox adjust enabled. Press [bold]Enter[/] to capture and adjust.")

        elif event.key == "v" and self._state == STATE_OVERWRITE:
            event.prevent_default()
            self._do_write_image(overwrite=False)

        # --- BBOX arrow keys ---
        elif self._state == STATE_BBOX:
            event.prevent_default()
            x, y, w, h = self._bbox
            if event.key == "up":
                y -= MOVE_STEP
            elif event.key == "down":
                y += MOVE_STEP
            elif event.key == "left":
                x -= MOVE_STEP
            elif event.key == "right":
                x += MOVE_STEP
            elif event.key == "shift+up":
                h -= RESIZE_STEP
            elif event.key == "shift+down":
                h += RESIZE_STEP
            elif event.key == "shift+left":
                w -= RESIZE_STEP
            elif event.key == "shift+right":
                w += RESIZE_STEP
            else:
                return
            w = max(50, w)
            h = max(50, h)
            x = max(0, x)
            y = max(0, y)
            self._bbox = [x, y, w, h]
            self._show_bbox_overlay()
            self._status(
                f"[bold]Arrows[/] move · [bold]Shift+Arrows[/] resize · "
                f"[bold]Enter[/] confirm · box: {x},{y} {w}x{h}"
            )

        # --- CONFIRM / FIX / PICK faction arrows ---
        elif event.key == "up" and self._state in (STATE_CONFIRM, STATE_FIX, STATE_PICK_FACTION):
            event.prevent_default()
            sel = self.query_one("#faction-sel", FactionSelector)
            sel.move_up()
            if self._card_info:
                self._card_info["faction"] = sel.selected
                self.query_one("#card-info", CardInfoPanel).set_info(self._card_info)
        elif event.key == "down" and self._state in (STATE_CONFIRM, STATE_FIX, STATE_PICK_FACTION):
            event.prevent_default()
            sel = self.query_one("#faction-sel", FactionSelector)
            sel.move_down()
            if self._card_info:
                self._card_info["faction"] = sel.selected
                self.query_one("#card-info", CardInfoPanel).set_info(self._card_info)

    def _do_fix_save(self):
        """Re-save last card with corrected faction.

        If faction changed, moves the image and sidecar to the correct
        faction directory and updates the card JSON.
        Also updates _auto_faction for subsequent auto captures.
        """
        if not self._card_info:
            return

        sel = self.query_one("#faction-sel", FactionSelector)
        new_faction = sel.selected
        old_faction = self._card_info.get("faction", "???")
        self._card_info["faction"] = new_faction
        sel.set_active(False)

        name = self._card_info.get("name", "???")
        card_text = self._card_info.get("card_text")
        new_faction_dir = FACTION_DIRS.get(new_faction)
        if not new_faction_dir:
            self._set_ready(f"Unknown faction: {new_faction}")
            return

        new_img_dir = IMAGES_DIR / new_faction_dir
        new_img_dir.mkdir(parents=True, exist_ok=True)
        base = card_filename_base(name)
        new_dest = new_img_dir / f"{base}.jpg"

        if new_faction != old_faction and self._last_saved_path and self._last_saved_path.exists():
            # Move image to new faction dir
            if new_dest.exists():
                # Find next available variation
                for i in range(2, 100):
                    candidate = new_img_dir / f"{base}{i}.jpg"
                    if not candidate.exists():
                        new_dest = candidate
                        break

            shutil.move(str(self._last_saved_path), str(new_dest))
            log.info("Moved image: %s -> %s", self._last_saved_path, new_dest)

            # Move sidecar
            new_sidecar = new_dest.with_suffix(".jpg.json")
            if self._last_saved_sidecar and self._last_saved_sidecar.exists():
                # Update faction in sidecar before moving
                sc_data = json.loads(self._last_saved_sidecar.read_text())
                sc_data["faction"] = new_faction
                self._last_saved_sidecar.write_text(json.dumps(sc_data, indent=4) + "\n")
                shutil.move(str(self._last_saved_sidecar), str(new_sidecar))
                log.info("Moved sidecar: %s -> %s", self._last_saved_sidecar, new_sidecar)

            # Revert old card JSON image field
            if self._last_saved_card_json and self._last_saved_old_image is not None:
                old_data = json.loads(self._last_saved_card_json.read_text())
                old_data["image"] = self._last_saved_old_image
                self._last_saved_card_json.write_text(json.dumps(old_data, indent=4) + "\n")

            # Update new card JSON
            card_json = find_card_json(name, new_faction)
            if card_json:
                rel_image = f"../../images/{new_faction_dir}/{new_dest.name}"
                update_card_json(card_json, rel_image, card_text=card_text)

            # Update sidecar card_json_path
            if new_sidecar.exists() and card_json:
                sc_data = json.loads(new_sidecar.read_text())
                sc_data["card_json_path"] = str(card_json.relative_to(REPO_ROOT))
                new_sidecar.write_text(json.dumps(sc_data, indent=4) + "\n")

            self._last_saved_path = new_dest
            self._last_saved_sidecar = new_sidecar
            self._last_saved_card_json = card_json

            results_panel = self.query_one("#results", ResultsPanel)
            results_panel.add_result(name, new_faction, "FIXED")
            self._card_info["_status"] = f"[bold green]Moved to {new_faction}[/]"
            self.query_one("#card-info", CardInfoPanel).set_info(self._card_info)
            say(f"{name} moved to {new_faction}.", faction=new_faction)
        else:
            # Same faction — just re-save in place
            self._card_info["_status"] = "[bold green]Confirmed[/]"
            self.query_one("#card-info", CardInfoPanel).set_info(self._card_info)

        # Update auto faction and resume auto
        self._auto_faction = new_faction
        self._card_info = None
        self._auto_mode = True
        self._set_ready(f"Fixed {name}.")

    def _confirm_bbox(self):
        """Lock in the bounding box and proceed to crop + identify."""
        save_bbox(self._bbox)
        self._bbox_confirmed = True
        self._need_bbox_adjust = False
        self._load_baseline_b64()  # re-crop baseline with new bbox
        self._status("[bold yellow]Cropping & identifying...[/]")
        self.run_worker(self._worker_crop_and_identify, thread=True)

    # --- Capture ---

    def _do_start_capture(self):
        if not self._client:
            self._status("[bold red]No API key[/]")
            return
        self._state = STATE_BUSY
        self._status("[bold yellow]Capturing...[/]")
        self.run_worker(self._worker_capture, thread=True)

    def _worker_capture(self):
        if not capture_image():
            self.call_from_thread(self._status, "[bold red]Capture failed[/]")
            self._state = STATE_READY
            return

        if self._need_bbox_adjust:
            # Only auto-detect on first ever capture (no saved bbox)
            if not self._bbox_confirmed:
                estimated = estimate_bbox_from_image(CAPTURE_JPG)
                if estimated:
                    self._bbox = estimated
                    log.info("Estimated bbox from CV: %s", estimated)
            # Show capture with bbox overlay for adjustment
            self.call_from_thread(self._enter_bbox_mode)
        else:
            # Use saved bbox directly
            self.call_from_thread(self._status, "[bold yellow]Cropping & identifying...[/]")
            self._worker_crop_and_identify()

    def _worker_auto_capture(self):
        """Auto mode: capture, crop, identify, save — all automatic."""
        if not capture_image():
            self.call_from_thread(self._status, "[bold red]Capture failed — retrying...[/]")
            self._state = STATE_AUTO
            self.call_from_thread(self._start_auto)
            return

        cropped = crop_with_bbox(CAPTURE_JPG, self._bbox)
        if cropped is None:
            self.call_from_thread(self._status, "[bold red]Crop failed — retrying...[/]")
            self._state = STATE_AUTO
            self.call_from_thread(self._start_auto)
            return

        self._cropped_cv = cropped
        cropped_path = WEBCAM_DIR / "cropped.jpg"
        cv2.imwrite(str(cropped_path), cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
        self.call_from_thread(self._update_image, str(cropped_path))
        self.call_from_thread(self._status, "[bold yellow]Identifying...[/]")

        card_info = identify_card(self._client, cropped_path, self._baseline_b64)
        if card_info is None or card_info.get("no_card"):
            # No card — just loop again
            self.call_from_thread(self._status, "[dim]No card detected — waiting...[/]")
            self._state = STATE_AUTO
            self.call_from_thread(self._start_auto)
            return

        # Check if same card as last saved
        if (self._last_saved_path and self._card_info
                and card_info.get("name") == self._card_info.get("name")
                and card_info.get("faction") == self._card_info.get("faction")):
            self._pending_same_card_info = card_info
            self.call_from_thread(self._prompt_same_card, card_info)
            return

        self._card_info = card_info
        self.call_from_thread(self._on_id_success_auto, card_info)

        name = card_info.get("name", "???")
        faction = card_info.get("faction", "???")
        parts = [f"{name}.", f"{faction}."]
        if card_info.get("strength") is not None:
            parts.append(f"Strength {card_info['strength']}.")
        say(" ".join(parts), faction=faction)

    def _prompt_same_card(self, card_info):
        """Same card detected — prompt to save another copy or rescan."""
        self._stop_auto_timer()
        self._state = STATE_SAME_CARD
        name = card_info.get("name", "???")
        info = dict(card_info)
        info["_status"] = (
            f"[bold yellow]Same card: {name}[/]\n"
            "[bold]Enter[/]=Save another copy  [bold]Esc[/]=Skip & rescan"
        )
        self.query_one("#card-info", CardInfoPanel).set_info(info)
        self._status(
            f"[bold yellow]Same card: {name}[/] — "
            "[bold]Enter[/] save copy · [bold]Esc[/] skip & rescan"
        )
        say(f"Same card. {name}. Save another or rescan?")

    def _on_id_success_auto(self, info):
        """Auto mode: show info with locked faction, then save after a short delay."""
        # Override detected faction with the user-selected auto faction
        if self._auto_faction:
            info["faction"] = self._auto_faction
        info["_status"] = "[bold yellow]Saving...[/]"
        self.query_one("#card-info", CardInfoPanel).set_info(info)
        sel = self.query_one("#faction-sel", FactionSelector)
        sel.set_faction(info.get("faction", FACTIONS[0]))
        self._status(f"[bold green]Identified:[/] {info.get('name', '???')} — saving...")
        self._do_auto_save(info)

    def _do_auto_save(self, info):
        """Save card image and JSON automatically using locked auto faction."""
        name = info.get("name", "???")
        # Use the user-selected faction, not the detected one
        faction = self._auto_faction or info.get("faction", "???")
        info["faction"] = faction
        card_text = info.get("card_text")
        faction_dir = FACTION_DIRS.get(faction)

        if not faction_dir:
            self._start_auto()
            return

        img_dir = IMAGES_DIR / faction_dir
        img_dir.mkdir(parents=True, exist_ok=True)
        base = card_filename_base(name)
        dest_path = img_dir / f"{base}.jpg"

        # If image exists: auto-variation (default in auto mode) or prompt
        if dest_path.exists():
            if self._auto_variation or self._auto_mode:
                # Auto-create variation
                for i in range(2, 100):
                    candidate = img_dir / f"{base}{i}.jpg"
                    if not candidate.exists():
                        dest_path = candidate
                        say(f"Variation. {name}.")
                        break
            else:
                # Pause auto and prompt
                self._stop_auto_timer()
                self._pending_dest = dest_path
                self._state = STATE_OVERWRITE
                info["_status"] = (
                    f"[bold yellow]{dest_path.name} exists![/]\n"
                    "[bold]Enter[/]=Overwrite  [bold]V[/]=Variation  [bold]Esc[/]=Skip"
                )
                self.query_one("#card-info", CardInfoPanel).set_info(info)
                self._status(
                    f"[bold yellow]{dest_path.name} exists[/] — "
                    "[bold]Enter[/] overwrite · [bold]V[/] variation · [bold]Esc[/] skip"
                )
                say(f"{name} already exists. Overwrite or variation?")
                return

        self._pending_dest = dest_path
        if self._cropped_cv is not None:
            cv2.imwrite(str(dest_path), self._cropped_cv, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            shutil.copy2(WEBCAM_DIR / "cropped.jpg", dest_path)

        # Save sidecar
        sidecar_path = dest_path.with_suffix(".jpg.json")
        sidecar = {"name": name, "faction": faction}
        if info.get("strength") is not None:
            sidecar["strength"] = info["strength"]
        if info.get("ranges"):
            sidecar["ranges"] = info["ranges"]
        if info.get("specialty"):
            sidecar["specialty"] = info["specialty"]
        if info.get("abilities"):
            sidecar["abilities"] = info["abilities"]
        if info.get("card_text"):
            sidecar["card_text"] = info["card_text"]
        sidecar["processed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        sidecar["source_image"] = dest_path.name

        # Update card JSON
        card_json = find_card_json(name, faction)
        old_image = None
        if card_json:
            old_data = json.loads(card_json.read_text())
            old_image = old_data.get("image")
            rel_image = f"../../images/{faction_dir}/{dest_path.name}"
            update_card_json(card_json, rel_image, card_text=card_text)
            sidecar["card_json_path"] = str(card_json.relative_to(REPO_ROOT))

        sidecar_path.write_text(json.dumps(sidecar, indent=4) + "\n")

        # Track for undo
        self._last_saved_path = dest_path
        self._last_saved_sidecar = sidecar_path
        self._last_saved_card_json = card_json
        self._last_saved_old_image = old_image

        results_panel = self.query_one("#results", ResultsPanel)
        results_panel.add_result(name, faction, "OK")
        info["_status"] = f"[bold green]Saved[/]"
        self.query_one("#card-info", CardInfoPanel).set_info(info)

        # Continue auto loop
        self._state = STATE_AUTO
        self._start_auto()

    def _undo_last_save(self):
        """Remove last auto-saved image, sidecar, and revert card JSON."""
        if self._last_saved_path and self._last_saved_path.exists():
            self._last_saved_path.unlink()
            log.info("Deleted: %s", self._last_saved_path)
        if self._last_saved_sidecar and self._last_saved_sidecar.exists():
            self._last_saved_sidecar.unlink()
            log.info("Deleted sidecar: %s", self._last_saved_sidecar)
        if self._last_saved_card_json and self._last_saved_old_image is not None:
            data = json.loads(self._last_saved_card_json.read_text())
            data["image"] = self._last_saved_old_image
            self._last_saved_card_json.write_text(json.dumps(data, indent=4) + "\n")
            log.info("Reverted card JSON image: %s", self._last_saved_card_json)
        self._last_saved_path = None
        self._last_saved_sidecar = None
        self._last_saved_card_json = None
        self._last_saved_old_image = None

    def _worker_crop_and_identify(self):
        # Crop using bbox
        cropped = crop_with_bbox(CAPTURE_JPG, self._bbox)
        if cropped is None:
            self.call_from_thread(self._set_ready, "Crop failed.")
            return

        self._cropped_cv = cropped
        cropped_path = WEBCAM_DIR / "cropped.jpg"
        cv2.imwrite(str(cropped_path), cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # Show cropped image
        self.call_from_thread(self._update_image, str(cropped_path))
        self.call_from_thread(self._status, "[bold yellow]Identifying...[/]")

        # Identify
        card_info = identify_card(self._client, cropped_path, self._baseline_b64)
        if card_info is None:
            self.call_from_thread(self._on_id_error, "Could not identify card")
            say("Could not identify card.")
            return

        if card_info.get("no_card"):
            self.call_from_thread(self._on_id_error, "No card detected")
            say("No card detected.")
            return

        self._card_info = card_info
        self.call_from_thread(self._on_id_success, card_info)

        name = card_info.get("name", "???")
        faction = card_info.get("faction", "???")
        parts = [f"{name}.", f"{faction}."]
        if card_info.get("strength") is not None:
            parts.append(f"Strength {card_info['strength']}.")
        if card_info.get("ranges"):
            parts.append(f"{', '.join(card_info['ranges'])} combat.")
        say(" ".join(parts), faction=faction)

    def _on_id_success(self, info):
        info["_status"] = "[bold yellow]Confirm faction, then Enter to save[/]"
        self.query_one("#card-info", CardInfoPanel).set_info(info)
        sel = self.query_one("#faction-sel", FactionSelector)
        sel.set_faction(info.get("faction", FACTIONS[0]))
        self._state = STATE_CONFIRM
        sel.set_active(True)
        self._status("[bold]Up/Down[/] faction · [bold]Enter[/] save · [bold]Esc[/] discard")

    def _on_id_error(self, msg):
        self.query_one("#card-info", CardInfoPanel).set_info(
            {"name": "???", "_status": f"[bold red]{msg}[/]"})
        self._set_ready(msg + ".")

    # --- Save ---

    def _do_save(self):
        if not self._card_info:
            return

        info = self._card_info
        sel = self.query_one("#faction-sel", FactionSelector)
        info["faction"] = sel.selected
        sel.set_active(False)

        name = info.get("name", "???")
        faction = info.get("faction", "???")
        faction_dir = FACTION_DIRS.get(faction)

        if not faction_dir:
            self._set_ready(f"Unknown faction: {faction}")
            return

        img_dir = IMAGES_DIR / faction_dir
        base = card_filename_base(name)
        dest_path = img_dir / f"{base}.jpg"

        if dest_path.exists():
            self._state = STATE_OVERWRITE
            self._pending_dest = dest_path
            info["_status"] = (
                f"[bold yellow]{dest_path.name} exists![/]\n"
                "[bold]Enter[/]=Overwrite  [bold]V[/]=Variation  [bold]Esc[/]=Cancel"
            )
            self.query_one("#card-info", CardInfoPanel).set_info(info)
            self._status(
                f"[bold yellow]{dest_path.name} exists[/] — "
                "[bold]Enter[/] overwrite · [bold]V[/] variation · [bold]Esc[/] cancel"
            )
            return

        self._pending_dest = dest_path
        self._do_write_image(overwrite=True)

    def _do_write_image(self, overwrite=True):
        info = self._card_info
        if not info:
            return

        name = info.get("name", "???")
        faction = info.get("faction", "???")
        card_text = info.get("card_text")
        faction_dir = FACTION_DIRS.get(faction)
        img_dir = IMAGES_DIR / faction_dir
        img_dir.mkdir(parents=True, exist_ok=True)
        base = card_filename_base(name)

        if overwrite:
            dest_path = self._pending_dest
        else:
            for i in range(2, 100):
                candidate = img_dir / f"{base}{i}.jpg"
                if not candidate.exists():
                    dest_path = candidate
                    break
            else:
                self._set_ready("Too many variations!")
                return

        if self._cropped_cv is not None:
            cv2.imwrite(str(dest_path), self._cropped_cv, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            shutil.copy2(WEBCAM_DIR / "cropped.jpg", dest_path)

        # Save sidecar JSON with all identified info
        sidecar_path = dest_path.with_suffix(".jpg.json")
        sidecar = {
            "name": name,
            "faction": faction,
        }
        if info.get("strength") is not None:
            sidecar["strength"] = info["strength"]
        if info.get("ranges"):
            sidecar["ranges"] = info["ranges"]
        if info.get("specialty"):
            sidecar["specialty"] = info["specialty"]
        if info.get("abilities"):
            sidecar["abilities"] = info["abilities"]
        if info.get("card_text"):
            sidecar["card_text"] = info["card_text"]
        sidecar["card_json_path"] = ""  # filled below if found
        sidecar["processed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        sidecar["source_image"] = dest_path.name

        card_name_for_json = name
        if not overwrite:
            suffix = dest_path.stem[len(base):]
            if suffix.isdigit():
                card_name_for_json = f"{name}: {suffix}"

        card_json = find_card_json(name, faction)
        if not overwrite and card_json:
            variation_json = find_card_json(card_name_for_json, faction)
            if variation_json:
                card_json = variation_json

        results_panel = self.query_one("#results", ResultsPanel)
        if card_json:
            rel_image = f"../../images/{faction_dir}/{dest_path.name}"
            update_card_json(card_json, rel_image, card_text=card_text)
            sidecar["card_json_path"] = str(card_json.relative_to(REPO_ROOT))
            results_panel.add_result(name, faction, "OK")
            info["_status"] = f"[bold green]{'Overwritten' if overwrite else 'Variation saved'}[/]"
        else:
            results_panel.add_result(name, faction, "NO JSON")
            info["_status"] = "[bold yellow]Image saved, no card JSON[/]"
            say(f"Warning. No card JSON found for {name}.")

        sidecar_path.write_text(json.dumps(sidecar, indent=4) + "\n")

        self.query_one("#card-info", CardInfoPanel).set_info(info)
        self._card_info = None
        self._pending_dest = None
        self._set_ready(f"Saved {name}.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Capture, crop, and catalog Gwent card photos")
    parser.add_argument("--owner", help="Card owner name (for finding correct JSON)")
    parser.add_argument("--baseline", action="store_true", help="Force recapture of baseline image")
    parser.add_argument("-v", "--variation", action="store_true",
                        help="Auto-create variations instead of prompting on duplicates")
    parser.add_argument("--tts", default="gtts",
                        help="TTS provider (gtts, piper, elevenlabs, openai, say, none)")
    args = parser.parse_args()

    _ensure_blank()
    app = CaptureCardsApp(
        owner=args.owner,
        tts_provider=args.tts,
        force_baseline=args.baseline,
        auto_variation=args.variation,
    )
    app.run()


if __name__ == "__main__":
    main()
