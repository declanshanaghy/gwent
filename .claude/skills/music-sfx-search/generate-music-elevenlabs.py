#!/usr/bin/env python3
"""Generate background music using ElevenLabs Eleven Music API.

Reads prompts from the embedded PROMPTS dict, generates instrumental tracks,
saves as MP3 files with sidecar JSON metadata to tmp/resources/music/.

Usage:
    python3 generate-music-elevenlabs.py [--category tavern|battle|ambient]
    python3 generate-music-elevenlabs.py  # generates all categories
"""

import argparse
import json
import logging
import os
import sys
import time

import requests

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
STAGING = os.path.join(REPO_ROOT, 'tmp', 'resources', 'music')

# ---------------------------------------------------------------------------
# Logging — both stdout and file
# ---------------------------------------------------------------------------

LOG_DIR = os.path.join(REPO_ROOT, 'tmp', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'generate-music-elevenlabs.log')

log = logging.getLogger('generate-music-elevenlabs')
log.setLevel(logging.DEBUG)
_fmt = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s', datefmt='%H:%M:%S')
_sh = logging.StreamHandler(sys.stdout)
_sh.setLevel(logging.INFO)
_sh.setFormatter(_fmt)
log.addHandler(_sh)
_fh = logging.FileHandler(LOG_FILE)
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_fmt)
log.addHandler(_fh)

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------

def _load_env():
    env_path = os.path.join(REPO_ROOT, '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, val = line.partition('=')
                    val = val.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), val)

_load_env()

API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
if not API_KEY:
    log.error("ELEVENLABS_API_KEY not set (check .env)")
    sys.exit(1)

API_URL = "https://api.elevenlabs.io/v1/music"
MODEL_ID = "music_v1"

# ---------------------------------------------------------------------------
# Witcher-themed music prompts — all instrumental, no vocals
# ---------------------------------------------------------------------------

PROMPTS = {
    "tavern": [
        ("tavern_kingfisher_lute", "Medieval tavern folk music with lute and fiddle, warm and lively atmosphere, patrons clinking tankards, crackling fireplace ambience", 120000),
        ("tavern_chameleon_cabaret", "Gentle medieval lute melody with soft percussion, intimate cabaret atmosphere, relaxed and inviting mood", 120000),
        ("tavern_skellige_mead_hall", "Upbeat Celtic drinking song with bodhran drums, tin whistle and fiddle, stomping feet rhythm, hearty and joyful", 120000),
    ],
    "battle": [
        ("battle_northern_realms", "Epic medieval battle orchestral theme with war drums, brass fanfare, mounting tension and heroic triumph, full orchestra", 180000),
        ("battle_nilfgaard_march", "Dark imperial military march with heavy percussion, ominous strings, choir chanting, menacing and relentless", 180000),
        ("battle_wild_hunt", "Slavic-inspired fantasy battle theme with driving drums, throat singing, hurdy-gurdy, intense destiny-charged energy", 180000),
    ],
    "ambient": [
        ("ambient_witcher_keep", "Peaceful evening ambient with soft strings echoing through ancient stone halls, distant wolves howling, contemplative and bittersweet", 180000),
        ("ambient_dark_swamp", "Mysterious dark swamp ambient with will-o-wisps flickering sounds, fog and cricket sounds, uneasy cello, eerie and unsettling", 180000),
        ("ambient_academy_dusk", "Scholarly ambient with warm golden hour strings, distant fountain splashing, quill scratching sounds, peaceful and intellectual", 180000),
    ],
}


def generate_one(name, prompt, category, duration_ms):
    """Generate one music track from a prompt. Returns True, 'skip', or False."""
    os.makedirs(STAGING, exist_ok=True)
    outpath = os.path.join(STAGING, f"{name}.mp3")
    jsonpath = os.path.join(STAGING, f"{name}.json")

    # Skip if already generated
    if os.path.exists(outpath) and os.path.getsize(outpath) > 0:
        log.info(f"SKIP {name}.mp3 (already exists)")
        return "skip"

    for attempt in range(5):
        try:
            log.debug(f"API call: {name} ({duration_ms/1000:.0f}s)")
            resp = requests.post(
                API_URL,
                headers={
                    "xi-api-key": API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "prompt": prompt,
                    "music_length_ms": duration_ms,
                    "model_id": MODEL_ID,
                    "force_instrumental": True,
                    "output_format": "mp3_44100_128",
                },
                timeout=300,  # music generation can take a while
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                log.info(f"rate limited (429), waiting {retry_after}s then retrying...")
                time.sleep(retry_after)
                continue

            if resp.status_code == 422:
                log.error(f"FAIL {name}: validation error: {resp.text}")
                return False

            resp.raise_for_status()

            # Response is raw MP3 bytes
            with open(outpath, "wb") as f:
                f.write(resp.content)

            # Sidecar JSON
            meta = {
                "type": "music",
                "use_for": category,
                "title": name.replace("_", " ").title(),
                "source": "elevenlabs",
                "prompt": prompt,
                "duration_ms": duration_ms,
                "model": MODEL_ID,
                "license": "ElevenLabs subscription (commercial use cleared)",
            }
            with open(jsonpath, "w") as f:
                json.dump(meta, f, indent=2)
                f.write("\n")

            size = os.path.getsize(outpath)
            log.info(f"OK  {name}.mp3 ({size:,} bytes, {duration_ms/1000:.0f}s)")
            return True

        except Exception as e:
            log.error(f"ERROR {name}: {e}", exc_info=True)
            return False

    log.error(f"FAIL {name}: exceeded retry attempts")
    return False


def main():
    parser = argparse.ArgumentParser(description="Generate music via ElevenLabs")
    parser.add_argument("--category", "-c",
                        choices=list(PROMPTS.keys()),
                        help="Generate only this category (default: all)")
    args = parser.parse_args()

    categories = [args.category] if args.category else list(PROMPTS.keys())
    total = sum(len(PROMPTS[c]) for c in categories)
    skips = 0
    done = 0
    errors = 0

    log.info(f"Generating {total} music tracks via ElevenLabs Eleven Music")
    log.info(f"Staging: {STAGING}")
    log.info(f"Log file: {LOG_FILE}")

    for category in categories:
        log.info(f"=== {category.upper()} ===")
        for name, prompt, duration_ms in PROMPTS[category]:
            done += 1
            log.info(f"[{done}/{total}] {name} ({duration_ms/1000:.0f}s)")
            ok = generate_one(name, prompt, category, duration_ms)
            if ok == "skip":
                skips += 1
            elif not ok:
                errors += 1
            # Small delay between requests
            if ok != "skip" and done < total:
                time.sleep(2)

    log.info(f"Done: {done - errors - skips}/{total} generated, {skips} skipped, {errors} errors")
    log.info(f"Files in: {STAGING}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
