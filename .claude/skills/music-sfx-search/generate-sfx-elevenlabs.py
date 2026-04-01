#!/usr/bin/env python3
"""Generate SFX audio files using ElevenLabs Sound Effects V2 API.

Reads prompts from the embedded PROMPTS dict, generates audio via ElevenLabs,
saves as WAV files with sidecar JSON metadata to tmp/resources/sfx/{category}/.

Usage:
    python3 generate-sfx-elevenlabs.py [--category close|ranged|siege|commander|card|weather|special]
    python3 generate-sfx-elevenlabs.py  # generates all categories
"""

import argparse
import json
import logging
import os
import sys
import time

import pydub
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
LOG_FILE = os.path.join(LOG_DIR, 'generate-sfx-elevenlabs.log')

log = logging.getLogger('generate-sfx-elevenlabs')
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

API_URL = "https://api.elevenlabs.io/v1/sound-generation"
MODEL_ID = "eleven_text_to_sound_v2"

# ---------------------------------------------------------------------------
# Witcher-themed generation prompts
# No speech, no voices, no character names. Pure sound effects only.
# ---------------------------------------------------------------------------

SFX_PREFIX = "Realistic foley sound effect, no scripted speech, no text-to-speech, no narration. "

PROMPTS = {
    "close": [
        ("close_sword_clash_heavy", SFX_PREFIX + "Two heavy steel longswords clashing with a deep resonant metallic clang, like real swords hitting in a medieval duel, low-pitched metal ring, 2 seconds", 2.0),
        ("close_axe_shield_splinter", SFX_PREFIX + "Heavy iron axe chopping into a thick wooden shield, deep cracking wood with metal edge biting in, splinters flying, 2 seconds", 2.0),
        ("close_rapid_swordfight", SFX_PREFIX + "Realistic sword fight with three quick steel-on-steel blade exchanges, each clang distinct and metallic, a warrior grunts with effort between strikes, 3 seconds", 3.0),
        ("close_mace_shield_thud", SFX_PREFIX + "Iron mace smashing into a metal-banded wooden shield, deep heavy thud with wood cracking and metal denting, low bass impact, 2 seconds", 2.0),
        ("close_blade_scrape_shield", SFX_PREFIX + "Steel sword edge dragging across a round metal shield boss, harsh grinding scrape of metal on metal, 2 seconds", 2.0),
        ("close_shield_bash", SFX_PREFIX + "Soldier bashing with a heavy wooden shield, impact of wood and iron rim hitting armor, a grunt of exertion on impact, 2 seconds", 2.0),
        ("close_heavy_cleave_armor", SFX_PREFIX + "Massive two-handed greatsword chopping into plate armor, deep metallic crunch of steel buckling, 2 seconds", 2.0),
    ],
    "ranged": [
        ("ranged_longbow_release", SFX_PREFIX + "Arrow released from a longbow, string twang and whoosh through air, 2 seconds", 2.0),
        ("ranged_crossbow_fire", SFX_PREFIX + "Crossbow bolt firing with mechanical click and string release, projectile flight, 2 seconds", 2.0),
        ("ranged_arrow_volley", SFX_PREFIX + "Volley of many arrows whooshing overhead, multiple projectiles cutting through air, 3 seconds", 3.0),
        ("ranged_arrow_shield_thud", SFX_PREFIX + "Arrow thudding into a wooden shield, sharp impact and vibration, 1 second", 1.5),
        ("ranged_arrow_whistle", SFX_PREFIX + "Single arrow whistling past at close range, fast whoosh with doppler effect, 1 second", 1.5),
        ("ranged_crossbow_reload", SFX_PREFIX + "Crossbow being cranked and reloaded, mechanical clicking and tension, 2 seconds", 2.0),
        ("ranged_bolt_stone_ricochet", SFX_PREFIX + "Crossbow bolt ricocheting off stone wall, sharp metallic ping and stone chip, 1 second", 1.5),
    ],
    "siege": [
        ("siege_catapult_boulder", SFX_PREFIX + "Catapult arm snapping forward with wood creaking, boulder whooshing through air, then massive stone impact crashing into a wall with rubble falling, 4 seconds", 4.0),
        ("siege_trebuchet_explosion", SFX_PREFIX + "Trebuchet counterweight dropping with heavy chains, arm swinging with a deep whoosh, boulder arcing then smashing into fortification with a thunderous explosion and stone debris, 5 seconds", 5.0),
        ("siege_ballista_wall_hit", SFX_PREFIX + "Ballista firing with enormous string twang, massive bolt cutting through air with a deep hum, then punching through stone wall with cracking impact and dust, 4 seconds", 4.0),
        ("siege_battering_ram_gate", SFX_PREFIX + "Battering ram rolling forward on creaking wheels, then slamming into heavy wooden gate with a thunderous boom, wood splintering and iron hinges groaning, 4 seconds", 4.0),
        ("siege_flaming_catapult", SFX_PREFIX + "Catapult launching a flaming pitch barrel, fire crackling in flight, then fiery explosion on impact with roaring flames and shattering timber, 5 seconds", 5.0),
        ("siege_trebuchet_volley", SFX_PREFIX + "Multiple trebuchets firing in sequence, three heavy mechanical releases followed by distant cascading impacts and rumbling explosions, 5 seconds", 5.0),
        ("siege_wall_collapse", SFX_PREFIX + "Castle wall taking a final hit, deep cracking of masonry, then entire section collapsing in a massive avalanche of stone blocks and dust cloud, 4 seconds", 4.0),
    ],
    "commander": [
        ("commander_war_horn_deep", SFX_PREFIX + "Deep ancient war horn blast echoing across a battlefield, reverberating low tone, 3 seconds", 3.0),
        ("commander_war_horn_high", SFX_PREFIX + "High-pitched battle horn signal, piercing and urgent, calling to attention, 2 seconds", 2.0),
        ("commander_war_drums_slow", SFX_PREFIX + "War drums beating a slow menacing rhythm, deep booming percussion building tension, 4 seconds", 4.0),
        ("commander_war_drums_fast", SFX_PREFIX + "War drums beating rapidly, urgent driving rhythm signaling a charge, 3 seconds", 3.0),
        ("commander_horn_triple", SFX_PREFIX + "Three short sharp horn blasts in succession, urgent rally signal, 3 seconds", 3.0),
        ("commander_drums_crescendo", SFX_PREFIX + "War drums building from slow to fast crescendo, culminating in a cymbal crash, 4 seconds", 4.0),
        ("commander_horn_long", SFX_PREFIX + "Long sustained war horn blast fading into the distance, mournful and powerful, 4 seconds", 4.0),
    ],
    "card": [
        ("card_slam_table", SFX_PREFIX + "Playing card slapped firmly on a wooden tavern table, crisp impact, 1 second", 1.0),
        ("card_flip", SFX_PREFIX + "Single card flipped over with a crisp paper snap, 1 second", 1.0),
        ("card_slide_place", SFX_PREFIX + "Card sliding across a wooden surface and placed down firmly, 1 second", 1.5),
        ("card_heavy_thud", SFX_PREFIX + "Heavy card or token placed on a game board with a satisfying deep thud, 1 second", 1.0),
        ("card_shuffle_riffle", SFX_PREFIX + "Deck of cards riffle shuffled once, quick crisp paper sounds, 2 seconds", 2.0),
    ],
    "weather": [
        ("weather_frost_crackle", SFX_PREFIX + "Ice forming and crackling, frost spreading across metal surfaces, cold crystalline sounds, 3 seconds", 3.0),
        ("weather_fog_eerie", SFX_PREFIX + "Thick fog rolling in, distant muffled sounds, eerie low-frequency wind, 4 seconds", 4.0),
        ("weather_rain_thunder", SFX_PREFIX + "Torrential rain hammering muddy ground with a crack of thunder, 4 seconds", 4.0),
        ("weather_storm_wind", SFX_PREFIX + "Howling storm wind with crashing waves against rocky cliffs, 4 seconds", 4.0),
        ("weather_clear_birds", SFX_PREFIX + "Clear weather breaking through, birds singing cheerfully, gentle warm breeze rustling leaves, 3 seconds", 3.0),
    ],
    "special": [
        ("special_heal_chimes", SFX_PREFIX + "Magical healing spell with ethereal chimes, warm shimmering glow sound rising, 3 seconds", 3.0),
        ("special_scorch_fire", SFX_PREFIX + "Intense fire blast erupting, roaring flames consuming everything briefly, 3 seconds", 3.0),
        ("special_muster_horn", SFX_PREFIX + "Urgent rally horn with three rapid blasts, echoing across a mountainous landscape, 3 seconds", 3.0),
        ("special_spy_footsteps", SFX_PREFIX + "Sneaky footsteps on cobblestone, careful and quiet, with a shadow-like ambient, 3 seconds", 3.0),
        ("special_decoy_thunk", SFX_PREFIX + "Hollow wooden object placed on the ground with a thunk, followed by a subtle creak, 2 seconds", 2.0),
    ],
}


def generate_one(name, prompt, category, duration):
    """Generate one SFX file from a prompt. Returns True, 'skip', or False."""
    import re as _re
    outdir = os.path.join(STAGING, category)
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f"{name}.wav")
    jsonpath = os.path.join(outdir, f"{name}.json")

    # Skip if already generated
    if os.path.exists(outpath) and os.path.getsize(outpath) > 0:
        log.info(f"SKIP {category}/{name}.wav (already exists)")
        return "skip"

    mp3_tmp = os.path.join(outdir, f"{name}.mp3")

    for attempt in range(5):
        try:
            resp = requests.post(
                API_URL,
                headers={
                    "xi-api-key": API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "text": prompt,
                    "duration_seconds": duration,
                    "prompt_influence": 0.5,
                    "model_id": MODEL_ID,
                },
                timeout=60,
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                log.info(f"rate limited (429), waiting {retry_after}s then retrying...")
                time.sleep(retry_after)
                continue

            if resp.status_code == 422:
                log.error(f"FAIL {category}/{name}: validation error: {resp.text}")
                return False

            resp.raise_for_status()

            # Response is raw audio bytes (MP3 by default)
            with open(mp3_tmp, "wb") as f:
                f.write(resp.content)

            # Convert MP3 → WAV 44100Hz stereo
            audio = pydub.AudioSegment.from_mp3(mp3_tmp)
            audio = audio.set_frame_rate(44100).set_channels(2)
            audio.export(outpath, format="wav")
            os.remove(mp3_tmp)

            # Sidecar JSON
            meta = {
                "type": "sfx",
                "use_for": category,
                "title": name.replace("_", " ").title(),
                "source": "elevenlabs",
                "prompt": prompt,
                "duration_seconds": duration,
                "model": MODEL_ID,
                "license": "ElevenLabs subscription",
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

    log.error(f"FAIL {category}/{name}: exceeded retry attempts")
    return False


def main():
    parser = argparse.ArgumentParser(description="Generate SFX via ElevenLabs")
    parser.add_argument("--category", "-c",
                        choices=list(PROMPTS.keys()),
                        help="Generate only this category (default: all)")
    args = parser.parse_args()

    categories = [args.category] if args.category else list(PROMPTS.keys())
    total = sum(len(PROMPTS[c]) for c in categories)
    skips = 0
    done = 0
    errors = 0

    log.info(f"Generating {total} SFX files via ElevenLabs Sound Effects V2")
    log.info(f"Staging: {STAGING}")
    log.info(f"Log file: {LOG_FILE}")

    for category in categories:
        log.info(f"=== {category.upper()} ===")
        for name, prompt, duration in PROMPTS[category]:
            done += 1
            log.info(f"[{done}/{total}] {category}/{name}")
            ok = generate_one(name, prompt, category, duration)
            if ok == "skip":
                skips += 1
            elif not ok:
                errors += 1
            # Small delay between requests (ElevenLabs is much more generous than Gemini free tier)
            if ok != "skip" and done < total:
                time.sleep(1)

    log.info(f"Done: {done - errors - skips}/{total} generated, {skips} skipped, {errors} errors")
    log.info(f"Files in: {STAGING}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
