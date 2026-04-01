# Music & SFX Search / Generate

Find or generate sound effects and music for the Gwent card game companion.

## Arguments
- `generate elevenlabs` — generate SFX using ElevenLabs Sound Effects V2 (recommended)
- `generate gemini` — generate SFX using Gemini TTS API (slow, 3 req/min free tier)
- `generate music` — generate music using Lyria 3 API
- `generate` — generate SFX with ElevenLabs (default provider)
- `search sfx` — search and download SFX from Mixkit
- `search music` — search and download music from Mixkit
- `search` — search both
- (no args) — default to `generate elevenlabs`

---

## Mode 1: GENERATE (AI-generated audio)

### SFX Generation: ElevenLabs Sound Effects V2 (Recommended)

**Model:** `eleven_text_to_sound_v2`
**API:** `https://api.elevenlabs.io/v1/sound-generation`
**Auth:** `ELEVENLABS_API_KEY` from `.env`
**Output:** MP3 → converted to WAV 44100Hz stereo during install
**Rate limit:** Generous (subscription-based, no 3 req/min nonsense)
**Quality:** 48kHz, up to 30s clips, purpose-built for SFX

**Script:** `.claude/skills/music-sfx-search/generate-sfx-elevenlabs.py`
```bash
python3 .claude/skills/music-sfx-search/generate-sfx-elevenlabs.py           # all categories
python3 .claude/skills/music-sfx-search/generate-sfx-elevenlabs.py -c close  # one category
```

### SFX Generation: Gemini TTS (Slow alternative)

**Model:** `gemini-2.5-flash-preview-tts`
**API:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent`
**Auth:** `GEMINI_API_KEY` from `.env`
**Output:** PCM 24kHz 16-bit mono → convert to WAV 44100Hz stereo

```bash
# Generate SFX from prompt
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=$GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "contents": [{"parts": [{"text": "PROMPT_HERE"}]}],
    "generationConfig": {
      "responseModalities": ["AUDIO"],
      "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}}
    }
  }' | python3 -c "
import sys, json, base64, wave
data = json.load(sys.stdin)
audio = base64.b64decode(data['candidates'][0]['content']['parts'][0]['inlineData']['data'])
with wave.open('OUTPUT.wav', 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(audio)
"
# Then convert: ffmpeg -i OUTPUT.wav -ar 44100 -ac 2 FINAL.wav
```

### Music Generation: Lyria 3

**Model:** `lyria-3-clip-preview`
**API:** Vertex AI interactions endpoint
**Auth:** `gcloud auth print-access-token` (requires gcloud CLI)
**Output:** audio/mpeg (MP3)

```bash
# Generate music from prompt
curl -s -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://aiplatform.googleapis.com/v1beta1/projects/PROJECT_ID/locations/global/interactions" \
  -d '{
    "inputs": [{"type": "text", "text": "PROMPT_HERE"}]
  }' | python3 -c "
import sys, json, base64
data = json.load(sys.stdin)
for output in data.get('outputs', []):
    if output.get('mime_type') == 'audio/mpeg':
        with open('OUTPUT.mp3', 'wb') as f:
            f.write(base64.b64decode(output['data']))
        break
"
```

### Generation Prompts

All SFX prompts are prefixed with "Sound effect only, no speech, no voices, no words, no narration."
No character names in SFX. Pure environmental/mechanical sound effects.
Prompts are defined in `generate-sfx.py` — see PROMPTS dict.

**Categories and counts:**
- Close combat: 7 (swords, shields, axes, maces, daggers, armor)
- Ranged: 7 (longbow, crossbow, arrow volleys, impacts, ricochets)
- Siege: 7 (catapult, trebuchet, ballista, battering ram, wall crumble, fire)
- Commander: 7 (war horns deep/high, war drums slow/fast, horn signals)
- Leader: 10 (faction-themed war cries — 2 per faction: Northern Realms, Nilfgaard, Scoia'tael, Monsters, Skellige)
- Card play: 5 (slam, flip, slide, thud, shuffle)
- Weather: 5 (frost, fog, rain/thunder, storm, clear skies)
- Special: 5 (heal chimes, scorch fire, muster horn, spy footsteps, decoy thunk)

#### Music - Tavern
1. "Priscilla singing at the Kingfisher Inn in Novigrad, lute and fiddle accompaniment, patrons clinking tankards, warm tavern atmosphere, 2 minutes"
2. "Dandelion performing at the Chameleon cabaret, gentle lute melody with crackling fireplace, Zoltan ordering another round in the background, 2 minutes"
3. "Upbeat Skellige drinking song at Kaer Trolde's mead hall, Celtic jig with bodhran drums, warriors stomping feet and singing, 2 minutes"

#### Music - Battle
1. "Epic Northern Realms battle theme as Foltest leads the charge at La Valette, war drums, Temerian brass fanfare and mounting tension, 3 minutes"
2. "Dark Nilfgaardian imperial march as Emhyr's Black Ones advance on Cintra, heavy percussion, ominous strings and choir chanting Alba, 3 minutes"
3. "Slavic-inspired Witcher battle theme for Geralt fighting the Wild Hunt at Kaer Morhen, driving drums, throat singing, hurdy-gurdy and destiny-charged energy, 3 minutes"

#### Music - Ambient
1. "Peaceful evening at Kaer Morhen, soft strings echoing through ancient witcher halls, distant wolves howling, contemplative and bittersweet, 3 minutes"
2. "Mysterious Velen swamp ambient, will-o-wisps flickering, distant crone cackling, fog and cricket sounds with uneasy cello, 3 minutes"
3. "Oxenfurt Academy courtyard at dusk, scholars debating in distance, fountain splashing, quill scratching parchment, warm golden hour strings, 3 minutes"

### Generation Scripts

SFX and music generation are implemented as Python scripts in this skill directory:

- **SFX (ElevenLabs, recommended):** `.claude/skills/music-sfx-search/generate-sfx-elevenlabs.py`
- **SFX (Gemini TTS, slow):** `.claude/skills/music-sfx-search/generate-sfx.py`
- **Music:** `.claude/skills/music-sfx-search/generate-music.py` (TODO: requires gcloud setup for Lyria 3)

All scripts: load `.env` automatically, log to `tmp/logs/`, skip existing files, handle rate limits.

### Generation Workflow

**Phase 1: Generate to tmp**
1. Clear staging: `rm -rf tmp/resources && mkdir -p tmp/resources/sfx/{close,ranged,siege,commander,card,weather,special} tmp/resources/music`
2. Run the generation script:
   ```bash
   # ElevenLabs (fast, high quality, recommended)
   python3 .claude/skills/music-sfx-search/generate-sfx-elevenlabs.py           # all SFX
   python3 .claude/skills/music-sfx-search/generate-sfx-elevenlabs.py -c close  # one category

   # Gemini TTS (slow, 3 req/min free tier)
   python3 .claude/skills/music-sfx-search/generate-sfx.py
   ```

**Phase 2: User Review**
4. Tell user: "Generated files are in tmp/resources/. Listen and remove any you don't want, then tell me to continue."
5. STOP and wait

**Phase 3: Install**
6. SFX: ensure WAV 44100Hz stereo, move to `software/data/sfx/{category}/`
7. Music: move MP3s to `software/data/music/`
8. Move sidecar JSONs alongside
9. Clean up: `rm -rf tmp/resources/`

---

## Mode 2: SEARCH (Mixkit web download)

### CRITICAL: Only No-Auth Sources

**ONLY use Mixkit** — direct, no-auth download URLs.

- **SFX pattern:** `https://assets.mixkit.co/active_storage/sfx/{ID}/{ID}-preview.mp3`
- **Music pattern:** `https://assets.mixkit.co/music/{ID}/{ID}.mp3`

### How to Find Mixkit IDs

1. Use WebFetch on a Mixkit category page (e.g. `https://mixkit.co/free-sound-effects/sword/`)
2. Extract IDs from HTML: `free-sound-effects/download/{ID}` or `active_storage/sfx/{ID}`
3. Verify: `curl -sI "URL"` should return HTTP 200

### Useful Mixkit Category Pages

**SFX:** sword/, medieval-battle/, explosion/, battle/, whoosh/, war/
**Music:** medieval/, cinematic/ (at `mixkit.co/free-stock-music/`)

### Search Workflow

**Phase 1: Search & Download to tmp**
1. Clear staging: `rm -rf tmp/resources && mkdir -p tmp/resources/sfx/{close,ranged,siege,commander,card,weather,special} tmp/resources/music`
2. Search Mixkit pages via WebFetch, extract titles + IDs
3. Verify URLs with `curl -sI`
4. Present numbered list, download approved to tmp
5. Write sidecar JSONs with `"source": "mixkit"`, `"mixkit_id"`, `"source_url"`

**Phase 2: User Review**
6. STOP and wait for user to prune

**Phase 3: Convert & Install**
7. Convert SFX MP3→WAV (44100Hz stereo) via pydub
8. Move WAVs to `software/data/sfx/{category}/`, music MP3s to `software/data/music/`
9. Clean up

### Known Working Mixkit IDs

**Close:** 2160, 1506, 2795, 2776, 2788, 2796, 2166
**Ranged:** 2760, 2767, 2158, 263, 2789
**Siege:** 1687, 2804, 2780, 2781, 2765
**Commander:** 2809, 351, 2171, 2771, 2172, 2175
**Card:** 2768, 2770, 2769
**Music:** 466, 676, 677, 678, 679, 680, 607, 871, 614

---

## Shared Config

### SFX Categories

| Category | use_for | Subdir |
|----------|---------|--------|
| Close combat | `close` | `sfx/close/` |
| Ranged combat | `ranged` | `sfx/ranged/` |
| Siege weapons | `siege` | `sfx/siege/` |
| Commander | `commander` | `sfx/commander/` |
| Card play | `card` | `sfx/card/` |
| Weather | `weather` | `sfx/weather/` |
| Special | `special` | `sfx/special/` |
| UI | `ui` | `sfx/ui/` |

### Music Categories

| Category | use_for |
|----------|---------|
| Tavern | `tavern` |
| Battle | `battle` |
| Ambient | `ambient` |

### Sidecar JSON

**Generated SFX:**
```json
{
  "type": "sfx",
  "use_for": "close",
  "title": "Geralt sword clash",
  "source": "gemini-tts",
  "prompt": "Geralt's silver sword clashing...",
  "model": "gemini-2.5-flash-preview-tts",
  "license": "Generated"
}
```

**Generated Music:**
```json
{
  "type": "music",
  "use_for": "battle",
  "title": "Northern Realms battle theme",
  "source": "lyria-3",
  "prompt": "Epic Northern Realms battle theme...",
  "model": "lyria-3-clip-preview",
  "license": "Generated"
}
```

**Downloaded (Mixkit):**
```json
{
  "type": "sfx",
  "use_for": "close",
  "title": "Sword strikes armor",
  "source": "mixkit",
  "source_url": "https://assets.mixkit.co/active_storage/sfx/2788/2788-preview.mp3",
  "mixkit_id": 2788,
  "license": "Mixkit Free License"
}
```

### Important Rules
- All temp files in `tmp/resources/` relative to repo root (NEVER `/tmp/`)
- Final install: `software/data/sfx/` (WAV) and `software/data/music/` (MP3)
- SFX must be WAV 44100Hz stereo for low-latency pygame playback
- Music stays MP3 (streamed by pygame.mixer.music)
- Always STOP and wait for user to prune before installing
- Always write sidecar JSON metadata
- Log errors to stderr, never swallow silently
