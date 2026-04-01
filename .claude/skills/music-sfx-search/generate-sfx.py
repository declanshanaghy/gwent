#!/usr/bin/env python3
"""Generate SFX audio files using Gemini TTS API.

Reads prompts from the embedded PROMPTS dict, generates audio via Gemini TTS,
saves as WAV files with sidecar JSON metadata to tmp/resources/sfx/{category}/.

Usage:
    python3 generate-sfx.py [--category close|ranged|siege|commander|card|weather|special]
    python3 generate-sfx.py  # generates all categories
"""

import argparse
import base64
import json
import logging
import os
import sys
import time
import wave

import requests

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
STAGING = os.path.join(REPO_ROOT, 'tmp', 'resources', 'sfx')

# ---------------------------------------------------------------------------
# Logging — both stdout and file
# ---------------------------------------------------------------------------

LOG_DIR = os.path.join(REPO_ROOT, 'tmp', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'generate-sfx.log')

log = logging.getLogger('generate-sfx')
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

API_KEY = os.environ.get('GEMINI_API_KEY', '')
if not API_KEY:
    log.error("GEMINI_API_KEY not set (check .env)")
    sys.exit(1)

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={API_KEY}"

# Free tier: 3 requests/minute. Space requests 21s apart to stay under limit.
# If we still hit the limit, the retry logic parses the exact wait from the error.
REQUEST_INTERVAL = 21

# ---------------------------------------------------------------------------
# Witcher-themed generation prompts
# ---------------------------------------------------------------------------

# IMPORTANT: No speech, no voices, no character names. Pure sound effects only.
# The game already has TTS for speech. These are environmental/mechanical SFX.
SFX_PREFIX = "Realistic foley sound effect, no scripted speech, no text-to-speech, no narration. "

PROMPTS = {
    "close": [
        ("close_sword_clash_heavy", SFX_PREFIX + "Heavy steel sword clashing against another blade, metal on metal impact with sparks, 2 seconds"),
        ("close_axe_shield_splinter", SFX_PREFIX + "Battle axe smashing into a wooden shield, splintering crack and wood breaking, 2 seconds"),
        ("close_rapid_swordfight", SFX_PREFIX + "Two swords trading rapid blows in quick succession, steel ringing repeatedly, 3 seconds"),
        ("close_mace_iron_shield", SFX_PREFIX + "Heavy mace crushing against an iron shield, deep resonant metallic thud, 2 seconds"),
        ("close_blade_scrape_shield", SFX_PREFIX + "Sword blade scraping across a metal shield boss, grinding metallic screech, 2 seconds"),
        ("close_dagger_parry", SFX_PREFIX + "Quick dagger strike parried by a shield, sharp metallic scrape and deflection, 1 second"),
        ("close_heavy_cleave_armor", SFX_PREFIX + "Massive blade cleaving through plate armor, metal tearing and breaking, 2 seconds"),
    ],
    "ranged": [
        ("ranged_longbow_release", SFX_PREFIX + "Arrow released from a longbow, string twang and whoosh through air, 2 seconds"),
        ("ranged_crossbow_fire", SFX_PREFIX + "Crossbow bolt firing with mechanical click and string release, projectile flight, 2 seconds"),
        ("ranged_arrow_volley", SFX_PREFIX + "Volley of many arrows whooshing overhead, multiple projectiles cutting through air, 3 seconds"),
        ("ranged_arrow_shield_thud", SFX_PREFIX + "Arrow thudding into a wooden shield, sharp impact and vibration, 1 second"),
        ("ranged_arrow_whistle", SFX_PREFIX + "Single arrow whistling past at close range, fast whoosh with doppler effect, 1 second"),
        ("ranged_crossbow_reload", SFX_PREFIX + "Crossbow being cranked and reloaded, mechanical clicking and tension, 2 seconds"),
        ("ranged_bolt_stone_ricochet", SFX_PREFIX + "Crossbow bolt ricocheting off stone wall, sharp metallic ping and stone chip, 1 second"),
    ],
    "siege": [
        ("siege_catapult_launch", SFX_PREFIX + "Catapult arm swinging and launching a boulder, wood creaking under tension then snapping forward, 3 seconds"),
        ("siege_trebuchet_fire", SFX_PREFIX + "Trebuchet counterweight dropping and arm swinging, heavy mechanical release with distant boulder impact, 4 seconds"),
        ("siege_wall_crumble", SFX_PREFIX + "Stone castle wall crumbling from impact, rocks falling and dust cascading, 3 seconds"),
        ("siege_battering_ram", SFX_PREFIX + "Battering ram slamming into heavy wooden gate, massive rhythmic thud with wood straining, 2 seconds"),
        ("siege_ballista_bolt", SFX_PREFIX + "Ballista launching a massive bolt, enormous string twang and heavy projectile cutting air, 2 seconds"),
        ("siege_engine_grinding", SFX_PREFIX + "Heavy siege engine wheels grinding forward on dirt, wood and metal creaking under strain, 3 seconds"),
        ("siege_flaming_impact", SFX_PREFIX + "Flaming projectile impacting stone fortification, explosion with fire crackling and debris, 3 seconds"),
    ],
    "commander": [
        ("commander_war_horn_deep", SFX_PREFIX + "Deep ancient war horn blast echoing across a battlefield, reverberating low tone, 3 seconds"),
        ("commander_war_horn_high", SFX_PREFIX + "High-pitched battle horn signal, piercing and urgent, calling to attention, 2 seconds"),
        ("commander_war_drums_slow", SFX_PREFIX + "War drums beating a slow menacing rhythm, deep booming percussion building tension, 4 seconds"),
        ("commander_war_drums_fast", SFX_PREFIX + "War drums beating rapidly, urgent driving rhythm signaling a charge, 3 seconds"),
        ("commander_horn_triple", SFX_PREFIX + "Three short sharp horn blasts in succession, urgent rally signal, 3 seconds"),
        ("commander_drums_crescendo", SFX_PREFIX + "War drums building from slow to fast crescendo, culminating in a cymbal crash, 4 seconds"),
        ("commander_horn_long", SFX_PREFIX + "Long sustained war horn blast fading into the distance, mournful and powerful, 4 seconds"),
    ],
    "card": [
        ("card_slam_table", SFX_PREFIX + "Playing card slapped firmly on a wooden tavern table, crisp impact, 1 second"),
        ("card_flip", SFX_PREFIX + "Single card flipped over with a crisp paper snap, 1 second"),
        ("card_slide_place", SFX_PREFIX + "Card sliding across a wooden surface and placed down firmly, 1 second"),
        ("card_heavy_thud", SFX_PREFIX + "Heavy card or token placed on a game board with a satisfying deep thud, 1 second"),
        ("card_shuffle_riffle", SFX_PREFIX + "Deck of cards riffle shuffled once, quick crisp paper sounds, 2 seconds"),
    ],
    "weather": [
        ("weather_frost_crackle", SFX_PREFIX + "Ice forming and crackling, frost spreading across metal surfaces, cold crystalline sounds, 3 seconds"),
        ("weather_fog_eerie", SFX_PREFIX + "Thick fog rolling in, distant muffled sounds, eerie low-frequency wind, 4 seconds"),
        ("weather_rain_thunder", SFX_PREFIX + "Torrential rain hammering muddy ground with a crack of thunder, 4 seconds"),
        ("weather_storm_wind", SFX_PREFIX + "Howling storm wind with crashing waves against rocky cliffs, 4 seconds"),
        ("weather_clear_birds", SFX_PREFIX + "Clear weather breaking through, birds singing cheerfully, gentle warm breeze rustling leaves, 3 seconds"),
    ],
    "special": [
        ("special_heal_chimes", SFX_PREFIX + "Magical healing spell with ethereal chimes, warm shimmering glow sound rising, 3 seconds"),
        ("special_scorch_fire", SFX_PREFIX + "Intense fire blast erupting, roaring flames consuming everything briefly, 3 seconds"),
        ("special_muster_horn", SFX_PREFIX + "Urgent rally horn with three rapid blasts, echoing across a mountainous landscape, 3 seconds"),
        ("special_spy_footsteps", SFX_PREFIX + "Sneaky footsteps on cobblestone, careful and quiet, with a shadow-like ambient, 3 seconds"),
        ("special_decoy_thunk", SFX_PREFIX + "Hollow wooden object placed on the ground with a thunk, followed by a subtle creak, 2 seconds"),
    ],
}


def generate_one(name, prompt, category):
    """Generate one SFX file from a prompt. Returns True on success."""
    import re as _re
    outdir = os.path.join(STAGING, category)
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f"{name}.wav")
    jsonpath = os.path.join(outdir, f"{name}.json")

    # Skip if already generated
    if os.path.exists(outpath) and os.path.getsize(outpath) > 0:
        log.info(f"SKIP {category}/{name}.wav (already exists)")
        return "skip"

    for attempt in range(6):
        try:
            resp = requests.post(API_URL, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {"voiceName": "Kore"}
                        }
                    }
                }
            }, timeout=60)

            data = resp.json()
            if "error" in data:
                msg = data['error'].get('message', '')
                match = _re.search(r'retry in ([\d.]+)s', msg)
                if match and attempt < 5:
                    wait = float(match.group(1)) + 2
                    log.info(f"rate limited, waiting {wait:.0f}s then retrying...")
                    time.sleep(wait)
                    continue
                log.error(f"FAIL {category}/{name}: {msg}")
                return False

            audio = base64.b64decode(
                data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
            with wave.open(outpath, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(audio)

            meta = {
                "type": "sfx",
                "use_for": category,
                "title": name.replace("_", " ").title(),
                "source": "gemini-tts",
                "prompt": prompt,
                "model": "gemini-2.5-flash-preview-tts",
                "license": "Generated",
            }
            with open(jsonpath, "w") as f:
                json.dump(meta, f, indent=2)
                f.write("\n")

            size = os.path.getsize(outpath)
            log.info(f"OK  {category}/{name}.wav ({size:,} bytes)")
            return True

        except Exception as e:
            log.error(f"ERROR {category}/{name}: {e}", exc_info=True)
            return False

    return False


def main():
    parser = argparse.ArgumentParser(description="Generate SFX via Gemini TTS")
    parser.add_argument("--category", "-c",
                        choices=list(PROMPTS.keys()),
                        help="Generate only this category (default: all)")
    args = parser.parse_args()

    categories = [args.category] if args.category else list(PROMPTS.keys())
    total = sum(len(PROMPTS[c]) for c in categories)
    skips = 0
    done = 0
    errors = 0
    eta_mins = (total * REQUEST_INTERVAL) / 60

    log.info(f"Generating {total} SFX files via Gemini TTS")
    log.info(f"Rate limit: {REQUEST_INTERVAL}s between requests (~{eta_mins:.0f} min total)")
    log.info(f"Staging: {STAGING}")
    log.info(f"Log file: {LOG_FILE}")

    for category in categories:
        log.info(f"=== {category.upper()} ===")
        for name, prompt in PROMPTS[category]:
            done += 1
            log.info(f"[{done}/{total}] {category}/{name}")
            ok = generate_one(name, prompt, category)
            if ok == "skip":
                skips += 1
            elif not ok:
                errors += 1
            # Rate limit: wait between API calls (not for skips)
            if ok != "skip" and done < total:
                remaining = total - done
                eta = (remaining * REQUEST_INTERVAL) / 60
                log.info(f"  ({remaining} remaining, ~{eta:.0f} min)")
                time.sleep(REQUEST_INTERVAL)

    log.info(f"Done: {done - errors - skips}/{total} generated, {skips} skipped, {errors} errors")
    log.info(f"Files in: {STAGING}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
