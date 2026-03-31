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

## Card text

Read any flavour or ability text printed below the card name (usually in italics).
Include it in the "card_text" field. Omit if none.

## Response format

JSON only. Include only fields with values. Examples:
{"name": "Geralt of Rivia", "faction": "Northern Realms", "strength": 15, "ranges": ["close"], "specialty": "hero", "card_text": "If that's what it takes to save the world, it's better to let that world die."}
{"name": "Yaevinn", "faction": "Scoia'tael", "strength": 6, "ranges": ["close", "ranged"], "abilities": ["agile"]}
{"name": "Isengrim Faoiltiarna", "faction": "Scoia'tael", "strength": 10, "ranges": ["close"], "abilities": ["medic"]}
{"name": "Scorch", "faction": "Monsters", "specialty": "scorch", "card_text": "Pillars of flame turn the mightiest to ash. All others tremble in shock and awe."}
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
    return True


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
    captures the card angle for deskewing. Shrinks 5% inward to
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
            # Shrink 5% inward from center to trim background bleed
            center = corners.mean(axis=0)
            corners = center + (corners - center) * 0.95
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
        close_k = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 30))
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
    """Create a tiny blank JPEG for placeholder images."""
    WEBCAM_DIR.mkdir(parents=True, exist_ok=True)
    if not _BLANK_IMG.exists():
        blank = np.zeros((100, 72, 3), dtype=np.uint8) + 40
        cv2.imwrite(str(_BLANK_IMG), blank)


def _crop_center(src_path, dst_path, target_w=960, target_h=1080):
    """Crop the center region of a webcam image at full resolution."""
    img = cv2.imread(str(src_path))
    if img is None:
        return
    h, w = img.shape[:2]
    x1 = max(0, (w - target_w) // 2)
    y1 = max(0, (h - target_h) // 2)
    x2 = min(w, x1 + target_w)
    y2 = min(h, y1 + target_h)
    cropped = img[y1:y2, x1:x2]
    cv2.imwrite(str(dst_path), cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])


FACTION_STYLES = {
    "Monsters": "bold red",
    "Northern Realms": "bold dodger_blue2",
    "Nilfgaardian": "bold dark_goldenrod",
    "Scoia'tael": "bold green",
    "Skellige": "bold medium_purple",
}


# App states — Enter progresses through: READY -> CAPTURING -> CONFIRM -> SAVING -> READY
STATE_READY = "ready"
STATE_BUSY = "busy"
STATE_CONFIRM = "confirm"
STATE_OVERWRITE = "overwrite"


class CardInfoPanel(Static):
    """Displays identified card attributes."""

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
    """Arrow-key navigable faction selector."""

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
        return Panel("\n".join(lines), title=f"Faction{hint}",
                     border_style=border)


class StatusBar(Static):
    """Bottom status/instructions bar."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._text = ""

    def set_text(self, text: str):
        self._text = text
        self.refresh()

    def render(self):
        return self._text


class ResultsPanel(Static):
    """Displays capture results summary."""

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
            return Panel("[dim]No cards captured yet[/]", title="Results",
                         border_style="dim")
        t = Table(box=box.SIMPLE, show_header=True, padding=(0, 1), expand=True)
        t.add_column("#", width=3)
        t.add_column("Card", ratio=2)
        t.add_column("Faction", ratio=1)
        t.add_column("Status", ratio=1)
        for i, r in enumerate(self._results, 1):
            style = "green" if r["status"] == "OK" else "yellow"
            t.add_row(str(i), r["name"], r["faction"], f"[{style}]{r['status']}[/]")
        return Panel(t, title=f"Results ({len(self._results)} cards)",
                     border_style="bright_green")


class CaptureCardsApp(App):
    """Gwent Card Photo Capture — Textual TUI.

    Enter-driven flow:
      READY  -> Enter -> capture + crop + identify -> CONFIRM
      CONFIRM -> arrows to pick faction, Enter -> save -> READY
    """

    TITLE = "Gwent Card Capture"

    CSS = """
    Screen { layout: vertical; }
    #top { height: 1fr; }
    #left-pane { width: 1fr; height: 1fr; border: solid ansi_bright_cyan; border-title-color: ansi_bright_cyan; }
    #original-img { width: 1fr; height: 1fr; }
    #right-pane { width: 2fr; height: 1fr; }
    #cropped-pane { width: 1fr; height: 1fr; border: solid ansi_bright_green; border-title-color: ansi_bright_green; }
    #cropped-img { width: 1fr; height: 1fr; }
    #info-col { width: 1fr; height: 1fr; overflow-y: auto; }
    #faction-sel { height: auto; }
    #card-info { height: auto; min-height: 10; }
    #results { height: auto; }
    #status-bar { height: 1; content-align: center middle; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("b", "baseline", "New Baseline", show=False),
    ]

    def __init__(self, owner=None, tts_provider="gtts", force_baseline=False):
        super().__init__()
        self._owner = owner
        self._tts_provider = tts_provider
        self._force_baseline = force_baseline
        self._client = None
        self._baseline_b64 = None
        self._card_info = None
        self._cropped_cv = None
        self._state = STATE_READY

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top"):
            left = Vertical(id="left-pane")
            left.border_title = "Original"
            with left:
                yield TGPImage(str(_BLANK_IMG), id="original-img")
            with Horizontal(id="right-pane"):
                cropped_pane = Vertical(id="cropped-pane")
                cropped_pane.border_title = "Cropped"
                with cropped_pane:
                    yield TGPImage(str(_BLANK_IMG), id="cropped-img")
                with Vertical(id="info-col"):
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
            self._baseline_b64 = base64.standard_b64encode(
                BASELINE_JPG.read_bytes()).decode("utf-8")
            self._set_ready("Baseline loaded.")
        else:
            self._status("No baseline. Press [bold]B[/] for baseline, or [bold]Enter[/] to capture.")


    def _status(self, text: str):
        try:
            self.query_one("#status-bar", StatusBar).set_text(text)
        except Exception:
            pass

    def _set_ready(self, prefix=""):
        self._state = STATE_READY
        msg = f"{prefix} " if prefix else ""
        self._status(f"{msg}Press [bold]Enter[/] to capture · [bold]B[/] baseline · [bold]Ctrl+C[/] quit")

    def _set_confirm(self):
        self._state = STATE_CONFIRM
        self.query_one("#faction-sel", FactionSelector).set_active(True)
        self._status("[bold]Up/Down[/] faction · [bold]Enter[/] save · [bold]Esc[/] discard")

    # --- Key handling ---

    def on_key(self, event):
        if event.key == "enter":
            event.prevent_default()
            if self._state == STATE_READY:
                self._do_start_capture()
            elif self._state == STATE_CONFIRM:
                self._do_save()
            elif self._state == STATE_OVERWRITE:
                self._do_write_image(overwrite=True)
        elif event.key == "escape":
            event.prevent_default()
            if self._state == STATE_CONFIRM:
                self._card_info = None
                self.query_one("#faction-sel", FactionSelector).set_active(False)
                self._set_ready("Discarded.")
            elif self._state == STATE_OVERWRITE:
                self._card_info = None
                self._set_ready("Cancelled.")
        elif event.key == "v" and self._state == STATE_OVERWRITE:
            event.prevent_default()
            self._do_write_image(overwrite=False)
        elif event.key == "up" and self._state == STATE_CONFIRM:
            event.prevent_default()
            sel = self.query_one("#faction-sel", FactionSelector)
            sel.move_up()
            if self._card_info:
                self._card_info["faction"] = sel.selected
                self.query_one("#card-info", CardInfoPanel).set_info(self._card_info)
        elif event.key == "down" and self._state == STATE_CONFIRM:
            event.prevent_default()
            sel = self.query_one("#faction-sel", FactionSelector)
            sel.move_down()
            if self._card_info:
                self._card_info["faction"] = sel.selected
                self.query_one("#card-info", CardInfoPanel).set_info(self._card_info)

    # --- Capture ---

    def _do_start_capture(self):
        if not self._client:
            self._status("[bold red]No API key[/]")
            return
        self._state = STATE_BUSY
        self._status("[bold yellow]Capturing...[/]")
        self.run_worker(self._worker_capture, thread=True)

    def _worker_capture(self):
        # Step 1: Capture
        if not capture_image():
            self.call_from_thread(self._status, "[bold red]Capture failed[/]")
            self._state = STATE_READY
            return

        # Show center-cropped original at full resolution
        center_path = WEBCAM_DIR / "center.jpg"
        _crop_center(CAPTURE_JPG, center_path)
        self.call_from_thread(self._update_image, "original-img", str(center_path))
        self.call_from_thread(self._status, "[bold yellow]Cropping...[/]")

        # Step 2: Crop/deskew
        cropped = crop_card(CAPTURE_JPG)
        cropped_path = WEBCAM_DIR / "cropped.jpg"
        if cropped is not None:
            cv2.imwrite(str(cropped_path), cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
            self._cropped_cv = cropped
        else:
            shutil.copy2(CAPTURE_JPG, cropped_path)
            self._cropped_cv = None

        self.call_from_thread(self._update_image, "cropped-img", str(cropped_path))
        self.call_from_thread(self._status, "[bold yellow]Identifying...[/]")

        # Step 3: Identify
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

        # Announce
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
        self._set_confirm()

    def _on_id_error(self, msg):
        self.query_one("#card-info", CardInfoPanel).set_info(
            {"name": "???", "_status": f"[bold red]{msg}[/]"})
        self._set_ready(msg + ".")

    def _update_image(self, widget_id, path):
        try:
            self.query_one(f"#{widget_id}", TGPImage).image = path
        except Exception:
            pass

    # --- Baseline ---

    def action_baseline(self):
        if self._state != STATE_READY:
            return
        self._state = STATE_BUSY
        self._status("[bold yellow]Capturing baseline... remove all cards[/]")
        say("Remove all cards. Capturing baseline.")
        self.run_worker(self._worker_baseline, thread=True)

    def _worker_baseline(self):
        time.sleep(1)
        if capture_image(BASELINE_JPG):
            set_baseline(BASELINE_JPG)
            self._baseline_b64 = base64.standard_b64encode(
                BASELINE_JPG.read_bytes()).decode("utf-8")
            self.call_from_thread(self._set_ready, "Baseline captured.")
            say("Baseline captured.")
        else:
            self.call_from_thread(self._set_ready, "Baseline failed.")

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
            # Image exists — ask whether to overwrite or create variation
            self._state = STATE_OVERWRITE
            self._pending_dest = dest_path
            info["_status"] = (
                f"[bold yellow]{dest_path.name} already exists![/]\n"
                "[bold]Enter[/]=Overwrite  [bold]V[/]=New variation  [bold]Esc[/]=Cancel"
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
        """Write the image and update card JSON."""
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
            # Find next available suffix: CardName2.jpg, CardName3.jpg, ...
            for i in range(2, 100):
                candidate = img_dir / f"{base}{i}.jpg"
                if not candidate.exists():
                    dest_path = candidate
                    break
            else:
                self._set_ready("Too many variations!")
                return

        # Write the image file
        if self._cropped_cv is not None:
            cv2.imwrite(str(dest_path), self._cropped_cv, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            shutil.copy2(WEBCAM_DIR / "cropped.jpg", dest_path)

        # For variations, the card name gets ": N" suffix in JSON
        card_name_for_json = name
        if not overwrite:
            suffix = dest_path.stem[len(base):]
            if suffix.isdigit():
                card_name_for_json = f"{name}: {suffix}"

        # Update card JSON — find by original name, or by variation name
        card_json = find_card_json(name, faction)
        if not overwrite and card_json:
            # For a new variation, look for the specific suffixed JSON instead
            variation_json = find_card_json(card_name_for_json, faction)
            if variation_json:
                card_json = variation_json
            # If no variation JSON exists yet, we still update the base card
            # (the user may need to create a new card JSON for the variation)

        results_panel = self.query_one("#results", ResultsPanel)
        if card_json:
            rel_image = f"../../images/{faction_dir}/{dest_path.name}"
            update_card_json(card_json, rel_image, card_text=card_text)
            action = "Overwritten" if overwrite else "Variation saved"
            results_panel.add_result(name, faction, "OK")
            info["_status"] = f"[bold green]{action}[/]"
            say(f"{name} saved.", faction=faction)
        else:
            results_panel.add_result(name, faction, "NO JSON")
            info["_status"] = "[bold yellow]Image saved, no card JSON[/]"
            say(f"{name} saved, no card JSON found.")

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
    parser.add_argument("--tts", default="gtts",
                        help="TTS provider (gtts, piper, elevenlabs, openai, say, none)")
    args = parser.parse_args()

    _ensure_blank()
    app = CaptureCardsApp(
        owner=args.owner,
        tts_provider=args.tts,
        force_baseline=args.baseline,
    )
    app.run()


if __name__ == "__main__":
    main()
