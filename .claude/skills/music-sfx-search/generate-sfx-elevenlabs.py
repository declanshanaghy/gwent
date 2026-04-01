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

# No scripted speech prefix + common battle atmosphere preamble
SFX_PREFIX = "Realistic foley sound effect, no scripted speech, no text-to-speech, no narration. "
_WAR = "Medieval dark fantasy battlefield ambience with distant war cries and clashing steel in background. "

PROMPTS = {
    "close": [
        # Swords — 3 variants
        ("close_swords_1", SFX_PREFIX + _WAR + "Foreground: two swordsmen trading heavy blows, steel ringing on steel, grunting with effort, parrying and striking, 3 seconds", 3.0),
        ("close_swords_2", SFX_PREFIX + _WAR + "Foreground: duel between champions, slow deliberate heavy sword strikes with deep metallic rings, circling footsteps, then an explosive flurry of blows, 3 seconds", 3.0),
        ("close_swords_3", SFX_PREFIX + _WAR + "Foreground: rapid sword fight, three quick steel-on-steel exchanges, a fierce battle cry mid-swing, the clash of a killing blow, 3 seconds", 3.0),
        # Shields — 3 variants
        ("close_shields_1", SFX_PREFIX + _WAR + "Foreground: shield wall collision, wood and iron crashing together, men roaring as they shove forward, boots scraping dirt, weapons clanging overhead, 3 seconds", 3.0),
        ("close_shields_2", SFX_PREFIX + _WAR + "Foreground: desperate shield bash, heavy wooden shield slamming into an armored opponent, iron rim crunching, the defender stumbling, a war cry, 3 seconds", 3.0),
        ("close_shields_3", SFX_PREFIX + _WAR + "Foreground: infantry pushing through a breach, shields battering, axes hacking at wooden barricades, men grunting and shouting as they pour through, 3 seconds", 3.0),
        # Cavalry — 2 variants
        ("close_cavalry_1", SFX_PREFIX + _WAR + "Foreground: cavalry impact, horses whinnying, lances shattering, riders clashing with swords from horseback, hooves thundering on packed earth, 3 seconds", 3.0),
        ("close_cavalry_2", SFX_PREFIX + _WAR + "Foreground: mounted charge hitting infantry, horses screaming, bodies and shields crunching, lances splintering, chaos of a cavalry breakthrough, 3 seconds", 3.0),
        # Berserker — 2 variants
        ("close_berserker_1", SFX_PREFIX + _WAR + "Foreground: berserker charge with savage war cry, wild axe swings crunching into shield and armor, primal grunts and snarls, brutal and fast, 3 seconds", 3.0),
        ("close_berserker_2", SFX_PREFIX + _WAR + "Foreground: night raid chaos, torches crackling, surprise attack with weapons clashing in darkness, panicked shouts mixing with aggressive battle cries, 3 seconds", 3.0),
    ],
    "ranged": [
        # Volley — 3 variants
        ("ranged_volley_1", SFX_PREFIX + _WAR + "Foreground: massive arrow volley launched on command, hundreds of bowstrings releasing together, arrows whooshing like rain through air, thudding into distant shields, 4 seconds", 4.0),
        ("ranged_volley_2", SFX_PREFIX + _WAR + "Foreground: arrow storm darkening the sky, continuous whistling and whooshing from hundreds of projectiles overhead, impacts like hail on wood and metal, 4 seconds", 4.0),
        ("ranged_volley_3", SFX_PREFIX + _WAR + "Foreground: fire arrows launching, bowstrings twang with crackling flames whooshing through night air, distant fiery impacts and wood catching fire, 4 seconds", 4.0),
        # Crossbow — 3 variants
        ("ranged_crossbow_1", SFX_PREFIX + _WAR + "Foreground: crossbow line firing in disciplined sequence, mechanical clicks and heavy bolts cutting air one after another, distant thuds of impact, reload cranking, 4 seconds", 4.0),
        ("ranged_crossbow_2", SFX_PREFIX + _WAR + "Foreground: defending walls with crossbows, bolts fired downward with heavy twangs, impacts on scaling ladders and attackers below, desperate reload clicks, 4 seconds", 4.0),
        ("ranged_crossbow_3", SFX_PREFIX + _WAR + "Foreground: ballista firing a massive bolt with enormous string twang, heavy projectile cutting air with a deep hum, distant crushing impact, 3 seconds", 3.0),
        # Skirmish — 2 variants
        ("ranged_skirmish_1", SFX_PREFIX + _WAR + "Foreground: skirmish with arrows flying both ways, bows twanging rapidly, bolts whooshing past ears, arrows thudding into nearby cover, shouts between volleys, 3 seconds", 3.0),
        ("ranged_skirmish_2", SFX_PREFIX + _WAR + "Foreground: rapid guerrilla archery from forest cover, quick bow releases from multiple positions, arrows zipping through leaves, surprised shouts from targets, 3 seconds", 3.0),
        # Single shot — 2 variants
        ("ranged_shot_1", SFX_PREFIX + _WAR + "Foreground: single powerful longbow drawn to full tension with a long creak, then released with a deep string snap, heavy arrow cutting air with low whoosh, distant thud, 3 seconds", 3.0),
        ("ranged_shot_2", SFX_PREFIX + _WAR + "Foreground: mounted archer galloping past, horse hooves thundering, quick bow releases while riding, arrows whistling away at speed, hooves fading, 3 seconds", 3.0),
    ],
    "siege": [
        # Catapult — 3 variants
        ("siege_catapult_1", SFX_PREFIX + _WAR + "Foreground: catapult arm snapping forward with wood creaking, boulder whooshing through air, then crashing into castle wall with massive stone impact and rubble, 5 seconds", 5.0),
        ("siege_catapult_2", SFX_PREFIX + _WAR + "Foreground: flaming pitch barrel launched from catapult, fire crackling in flight, fiery explosion on impact with roaring flames and shattering timber, 5 seconds", 5.0),
        ("siege_catapult_3", SFX_PREFIX + _WAR + "Foreground: multiple siege engines firing in sequence, three heavy mechanical releases, distant cascading impacts and rumbling explosions, ground trembling, 5 seconds", 5.0),
        # Trebuchet — 2 variants
        ("siege_trebuchet_1", SFX_PREFIX + _WAR + "Foreground: trebuchet counterweight dropping with chains, arm swinging with deep whoosh, boulder arcing then smashing into fortification with thunderous explosion, 5 seconds", 5.0),
        ("siege_trebuchet_2", SFX_PREFIX + _WAR + "Foreground: mining tunnel collapsing under a tower, deep underground rumble building, ground cracking open, stone structure imploding with massive dust and debris, 5 seconds", 5.0),
        # Ram — 2 variants
        ("siege_ram_1", SFX_PREFIX + _WAR + "Foreground: battering ram slamming into castle gate, massive boom of wood on wood, iron hinges groaning, soldiers chanting heave, gate splintering, 5 seconds", 5.0),
        ("siege_ram_2", SFX_PREFIX + _WAR + "Foreground: siege tower reaching the wall, heavy wooden bridge dropping with a crash, armored soldiers pouring across with war cries, weapons immediately clashing, 5 seconds", 5.0),
        # Destruction — 3 variants
        ("siege_destruction_1", SFX_PREFIX + _WAR + "Foreground: castle wall section collapsing, deep cracking of masonry, entire section falling in massive avalanche of stone blocks and dust cloud, 5 seconds", 5.0),
        ("siege_destruction_2", SFX_PREFIX + _WAR + "Foreground: boiling oil poured from battlements, liquid sizzling and splashing, screams below, cauldron scraping on stone, defenders shouting, 4 seconds", 4.0),
        ("siege_destruction_3", SFX_PREFIX + _WAR + "Foreground: scaling ladders slamming against walls, wood thudding on stone, soldiers climbing with armor clanking, defenders pushing ladders back, ladder crashing, 4 seconds", 4.0),
    ],
    "commander": [
        ("commander_01", SFX_PREFIX + _WAR + "Foreground: deep war horn playing a powerful descending 4-note melody, reverberating across the field with authority, soldiers stamping weapons in response, 5 seconds", 5.0),
        ("commander_02", SFX_PREFIX + _WAR + "Foreground: urgent battle horn playing a sharp ascending 3-note rally call, piercing and bright, the final note sustained as troops roar in unison, 4 seconds", 4.0),
        ("commander_03", SFX_PREFIX + _WAR + "Foreground: war drums building from slow menacing heartbeat to thunderous rapid charge rhythm, adding layers of percussion, crescendo with cymbal crash, 5 seconds", 5.0),
        ("commander_04", SFX_PREFIX + _WAR + "Foreground: three short sharp horn blasts in ascending pitch, brief pause, then one long sustained rally note, troops responding with a unified battle cry, 4 seconds", 4.0),
        ("commander_05", SFX_PREFIX + _WAR + "Foreground: massive war drum solo with driving cavalry charge rhythm, urgent and relentless, accent hits growing louder, horses hooves joining the beat, 5 seconds", 5.0),
        ("commander_06", SFX_PREFIX + _WAR + "Foreground: long mournful war horn playing a descending 5-note melody, each note fading into the next, solemn and powerful, echoing into silence, 5 seconds", 5.0),
        ("commander_07", SFX_PREFIX + _WAR + "Foreground: twin war horns playing a call-and-response melody, one deep one high, followed by synchronized war drums, an army announcing its presence, 5 seconds", 5.0),
        ("commander_08", SFX_PREFIX + _WAR + "Foreground: retreat signal horn playing urgent descending notes, drums beating double-time, soldiers shouting to fall back, organized chaos of withdrawal, 4 seconds", 4.0),
        ("commander_09", SFX_PREFIX + _WAR + "Foreground: victory fanfare, triumphant ascending horn melody with drums in celebration rhythm, soldiers cheering and clashing weapons on shields in jubilation, 5 seconds", 5.0),
        ("commander_10", SFX_PREFIX + _WAR + "Foreground: dawn battle horn, a single long rising note that breaks the morning silence, answered by distant horns, war drums beginning to beat as an army awakens, 5 seconds", 5.0),
    ],
    "leader": [
        ("leader_01", SFX_PREFIX + _WAR + "Foreground: regal brass fanfare with triumphant ascending melody and snare drum roll, heraldic trumpets announcing a king, soldiers stamping spears in salute, 5 seconds", 5.0),
        ("leader_02", SFX_PREFIX + _WAR + "Foreground: dark imperial war drums in slow menacing march, heavy oppressive rhythm, armored boots marching in lockstep, a low brass horn playing an ominous 3-note theme, 5 seconds", 5.0),
        ("leader_03", SFX_PREFIX + _WAR + "Foreground: ethereal elven horn echoing through ancient forest, haunting melody rising and falling like birdsong, rustle of archers drawing bows, whispered readiness, 5 seconds", 5.0),
        ("leader_04", SFX_PREFIX + _WAR + "Foreground: otherworldly frost horn with alien chromatic melody, ice cracking between notes, spectral howling wind, supernatural dread washing over the battlefield, 5 seconds", 5.0),
        ("leader_05", SFX_PREFIX + _WAR + "Foreground: massive viking war horn from a longship, three bold ascending notes then one long thunderous blast, waves crashing, warriors beating shields with axes, 5 seconds", 5.0),
        ("leader_06", SFX_PREFIX + _WAR + "Foreground: primal monster war drums with inhuman accelerating rhythm, bone on hide, distant creature roars and shrieks between drum fills, terrifying and otherworldly, 5 seconds", 5.0),
        ("leader_07", SFX_PREFIX + _WAR + "Foreground: noble cavalry horn playing a gallant rising melody, followed by thunder of hooves, lances being couched, a disciplined charge beginning with a unified shout, 5 seconds", 5.0),
        ("leader_08", SFX_PREFIX + _WAR + "Foreground: guerrilla ambush signal, a sharp whistle cutting through forest silence, followed by sudden rain of arrows, war cries erupting from hidden positions all around, 4 seconds", 4.0),
        ("leader_09", SFX_PREFIX + _WAR + "Foreground: ancient ceremonial war drums building from silence to a thunderous crescendo, each beat answered by a crowd stamping and chanting, culminating in a deafening roar, 5 seconds", 5.0),
        ("leader_10", SFX_PREFIX + _WAR + "Foreground: fleet of warships arriving, multiple horns sounding from different distances, waves against hulls, oars splashing in rhythm, the sound of an invasion force making landfall, 5 seconds", 5.0),
    ],
    "card": [
        ("card_01", SFX_PREFIX + "Medieval tavern ambience with murmuring patrons and crackling hearth. Foreground: Gwent card slapped confidently onto scarred oak table, crisp paper-on-wood impact, 2 seconds", 2.0),
        ("card_02", SFX_PREFIX + "Medieval tavern ambience with clinking tankards. Foreground: card slid across polished wood and placed down with a firm tap, the sound of a calculated move, 2 seconds", 2.0),
        ("card_03", SFX_PREFIX + "Medieval tavern ambience with distant lute. Foreground: card flipped dramatically face-up with a sharp paper snap, a gasp from onlookers, 2 seconds", 2.0),
        ("card_04", SFX_PREFIX + "Medieval tavern ambience with fire crackling. Foreground: heavy card or token thumped down with authority, the thud reverberating through the table, a decisive play, 2 seconds", 2.0),
        ("card_05", SFX_PREFIX + "Medieval tavern ambience with murmuring crowd. Foreground: deck of cards riffle shuffled with crisp paper sounds, then cut and placed down, ready for the next round, 2 seconds", 2.0),
        ("card_06", SFX_PREFIX + "Medieval tavern ambience with wooden chairs creaking. Foreground: multiple cards laid down in rapid succession, tap tap tap on wood, the sound of a devastating combo play, 2 seconds", 2.0),
        ("card_07", SFX_PREFIX + "Medieval tavern ambience with ale being poured. Foreground: single card drawn slowly from a hand with paper friction, then inspected with a thoughtful pause before placement, 2 seconds", 2.0),
        ("card_08", SFX_PREFIX + "Medieval tavern ambience with hushed crowd. Foreground: a trump card slammed down with force, table rattling, tankards jumping, crowd erupting in reaction, 2 seconds", 2.0),
        ("card_09", SFX_PREFIX + "Medieval tavern ambience with wind outside. Foreground: cards being gathered up from the table, paper sliding on wood, stacking neatly, end of a round, 2 seconds", 2.0),
        ("card_10", SFX_PREFIX + "Medieval tavern ambience with dice rolling nearby. Foreground: two players simultaneously slamming their cards down in a showdown, double impact, crowd holding breath, 2 seconds", 2.0),
    ],
    "weather": [
        # Frost (Biting Frost) — 3 variants
        ("weather_frost_1", SFX_PREFIX + _WAR + "Foreground: supernatural biting frost creeping across the battlefield, ice crackling on armor and weapons, crystalline spreading sounds, temperature audibly dropping, soldiers shivering, 4 seconds", 4.0),
        ("weather_frost_2", SFX_PREFIX + _WAR + "Foreground: white frost from another world, alien ice crackling with otherworldly resonance, spectral wind howling, reality itself seeming to freeze and crack, 4 seconds", 4.0),
        ("weather_frost_3", SFX_PREFIX + _WAR + "Foreground: blizzard descending rapidly, wind screaming, snow and ice pelting armor, visibility zero, soldiers shouting but voices swallowed by the frost storm, 4 seconds", 4.0),
        # Fog (Impenetrable Fog) — 3 variants
        ("weather_fog_1", SFX_PREFIX + _WAR + "Foreground: impenetrable fog rolling in like a living thing, sounds becoming muffled and distant, eerie low-frequency resonance, dripping moisture, lost voices calling out, 4 seconds", 4.0),
        ("weather_fog_2", SFX_PREFIX + _WAR + "Foreground: dense swamp fog with bubbling marsh sounds, distant creature calls, will-o-wisps with ethereal tinkling, oppressive humidity and dripping water, eerie, 4 seconds", 4.0),
        ("weather_fog_3", SFX_PREFIX + _WAR + "Foreground: battlefield fog descending, visibility vanishing, muffled shouts of confusion, footsteps stumbling, weapons clanging blindly, an eerie silence between, 4 seconds", 4.0),
        # Rain (Torrential Rain) — 3 variants
        ("weather_rain_1", SFX_PREFIX + _WAR + "Foreground: torrential rain hammering the battlefield, thunder cracking overhead, mud splashing under boots, soldiers cursing the deluge, armor dripping, 4 seconds", 4.0),
        ("weather_rain_2", SFX_PREFIX + _WAR + "Foreground: howling storm with supernatural fury, wind tearing at banners and tents, lightning strikes with deafening thunder, rain lashing horizontally, 4 seconds", 4.0),
        ("weather_rain_3", SFX_PREFIX + _WAR + "Foreground: storm rolling in from the sea, massive waves crashing against cliffs, howling arctic wind carrying sea spray, creaking ship timbers straining, 4 seconds", 4.0),
        # Clear Weather — 1 variant
        ("weather_clear_1", SFX_PREFIX + _WAR + "Foreground: weather clearing dramatically, clouds parting with a rush of wind, sunlight breaking through with warm tones, birds suddenly singing, a collective sigh of relief, 4 seconds", 4.0),
    ],
    "special": [
        # Scorch — 3 variants
        ("special_scorch_1", SFX_PREFIX + _WAR + "Foreground: scorch spell erupting, intense dragon-fire blast roaring across the field, everything in its path crackling and burning, the heat audible, 3 seconds", 3.0),
        ("special_scorch_2", SFX_PREFIX + _WAR + "Foreground: wall of flame sweeping across the battlefield, air superheating with a deep roar, wood and cloth igniting instantly, crackling inferno, 3 seconds", 3.0),
        ("special_scorch_3", SFX_PREFIX + _WAR + "Foreground: fire raining from above, multiple impacts of flaming projectiles, ground erupting in fire, roaring blaze consuming the strongest units, 3 seconds", 3.0),
        # Spy — 3 variants
        ("special_spy_1", SFX_PREFIX + _WAR + "Foreground: spy infiltrating, careful footsteps on cobblestone, a lock picking with delicate clicks, parchment unfolding, shadows shifting, a coded whistle, 3 seconds", 3.0),
        ("special_spy_2", SFX_PREFIX + _WAR + "Foreground: cloaked figure dropping from a wall, soft thud on cobblestone, quick footsteps darting between shadows, coins clinking as a bribe is passed, 3 seconds", 3.0),
        ("special_spy_3", SFX_PREFIX + _WAR + "Foreground: double agent revealed, a gasp of surprise, weapons drawn in response, the tension of betrayal, documents rustling as secrets change hands, 3 seconds", 3.0),
        # Medic — 3 variants
        ("special_medic_1", SFX_PREFIX + _WAR + "Foreground: healing magic activating, warm ethereal chimes ascending, shimmering golden energy sound, wounds closing with a soft organic tone, a breath of relief, 3 seconds", 3.0),
        ("special_medic_2", SFX_PREFIX + _WAR + "Foreground: resurrection magic, deep reverberating bass note building, bones reassembling with grinding sounds, a gasp of life returning, ethereal energy dissipating, 4 seconds", 4.0),
        ("special_medic_3", SFX_PREFIX + _WAR + "Foreground: battlefield medic's magic, soft glowing hum building in intensity, broken armor mending with metallic clicks, a heartbeat returning strong, 3 seconds", 3.0),
        # Muster — 3 variants
        ("special_muster_1", SFX_PREFIX + _WAR + "Foreground: muster horn sounding an urgent triple blast echoing across mountains, answering horns from multiple directions, the thunder of reinforcements arriving, 4 seconds", 4.0),
        ("special_muster_2", SFX_PREFIX + _WAR + "Foreground: rally drums beating urgent call to arms, distant running footsteps growing louder, weapons being drawn, shields raised, an army assembling rapidly, 4 seconds", 4.0),
        ("special_muster_3", SFX_PREFIX + _WAR + "Foreground: clan call echoing through valleys, multiple war horns answering from different directions, the rumble of many warriors converging on the battlefield, 4 seconds", 4.0),
        # Decoy — 2 variants
        ("special_decoy_1", SFX_PREFIX + _WAR + "Foreground: decoy being placed, hollow wooden thunk of a dummy on the field, rope creaking, cloth rustling in the wind, a subtle deception deployed, 3 seconds", 3.0),
        ("special_decoy_2", SFX_PREFIX + _WAR + "Foreground: tactical retreat sound, a card being snatched back quickly, the rustle of a swap, wooden decoy thudding into position, a trick well played, 3 seconds", 3.0),
        # Morale — 2 variants
        ("special_morale_1", SFX_PREFIX + _WAR + "Foreground: morale boost, an inspiring horn call followed by soldiers cheering with renewed vigor, weapons raised, stamping feet, turning the tide, 4 seconds", 4.0),
        ("special_morale_2", SFX_PREFIX + _WAR + "Foreground: troops rallying, a commander's horn playing a triumphant note, men roaring with determination, the sound of courage returning to the ranks, 4 seconds", 4.0),
        # Bond — 2 variants
        ("special_bond_1", SFX_PREFIX + _WAR + "Foreground: bond ability activating, two identical weapons drawn simultaneously with a metallic ring, supernatural harmonic resonance between them, power doubling, 3 seconds", 3.0),
        ("special_bond_2", SFX_PREFIX + _WAR + "Foreground: tight bond forming, matching war horns sounding in perfect unison, synchronized shield locks, the strength of brothers in arms, 3 seconds", 3.0),
        # Berserker Transform — 2 variants
        ("special_transform_1", SFX_PREFIX + _WAR + "Foreground: transformation magic, bones cracking and reshaping, a guttural growl becoming a monstrous roar, the sound of a berserker becoming something far worse, 4 seconds", 4.0),
        ("special_transform_2", SFX_PREFIX + _WAR + "Foreground: berserker rage triggering, heavy breathing becoming animalistic snarling, armor bursting apart, a terrifying inhuman war cry erupting, 4 seconds", 4.0),
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
