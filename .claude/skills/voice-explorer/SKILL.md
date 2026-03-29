---
name: voice-explorer
description: Audition TTS voices for Gwent factions across providers (gtts, elevenlabs, openai, piper, say)
user_invocable: true
allowed-tools: Bash, AskUserQuestion, Edit, Read
---

Audition TTS voices for a specific faction and provider, then let the user pick a winner.

## Usage

`/voice-explorer --tts <provider> [faction]`

- **provider** (required): `elevenlabs` | `openai` | `gtts` | `google` | `piper` | `say`
- **faction** (optional): `monsters` | `northern-realms` | `skellige` | `scoiatael` | `nilfgaardian`

Platform-local providers (no API keys):
- `piper` — Linux only, neural TTS with ONNX models in `~/.local/share/piper-voices/`
- `say` — macOS only, native `say` command with system voices

If **faction is omitted**, run in **all-factions mode**: randomly assign one voice from the provider's catalog to each faction, update the provider file, clear the TTS cache, and confirm the mapping. No audition — just shuffle and apply.

If **provider is missing**, use AskUserQuestion to ask.

## Quick show (no audio)

To just show the current mapping without playing audio:
```bash
tts-voice-explorer --tts <provider> --show
```

## Environment

Source API keys before running any TTS commands:
```bash
source ~/gwent-venv/bin/activate && source <(grep -v '^#' /home/dshanaghy/src/github.com/declanshanaghy/gwent/.env | sed 's/^/export /')
```

Audio cache directory: `/tmp/gwent-tts-explorer/voice-audition`

## Voice catalogs

### ElevenLabs premade voices (voice_id → name)
```
21m00Tcm4TlvDq8ikWAM  Rachel     (calm American female)
ErXwobaYiN019PkySvjV  Antoni     (warm British male)
VR6AewLTigWG4xSOukaG  Arnold     (deep powerful male)
XB0fDUnXU5powFXDhCwa  Charlotte  (British female)
t0jbNlBVZ17f02VDIeMI  Clyde      (old gravelly male)
onwK4e9ZLuTAKqWW03F9  Daniel     (formal British male)
TxGEqnHWrfWFTfGW9XjX  Josh       (deep young male)
pNInz6obpgDQGcFmaJgB  Adam       (deep narration male)
N2lVS1w4EtoT3dr4eOWO  Ethan      (confident American male)
piTKgcLEGmPE4e6mEKli  Giovanni   (forceful Italian male)
SOYHLrjzK2X1ezoPC6cr  Harry      (anxious British male)
jsCqWAovK2LkecY7zXl4  Freya      (American female)
pMsXgVXv3BLzUgSXRplE  Glinda     (witch-like female)
```

### OpenAI voices
```
alloy, ash, coral, echo, fable, nova, onyx, sage, shimmer
```

### gTTS accents (TLD → accent)
```
com      US English
co.uk    UK English
com.au   Australian English
co.in    Indian English
ca       Canadian English
co.za    South African English
ie       Irish English
co.nz    New Zealand English
com.ng   Nigerian English
com.gh   Ghanaian English
com.ph   Philippine English
com.sg   Singaporean English
com.hk   Hong Kong English
```

### Piper voices (model name → description)
```
en_US-ryan-medium                    American male (default)
en_GB-northern_english_male-medium   Northern English male (gruff)
en_GB-alan-medium                    British male (noble)
en_US-joe-medium                     American male (low)
en_US-bryce-medium                   American male (commanding)
```

### macOS `say` voices
```
Daniel    British male (noble, authoritative)
Moira     Irish female (Celtic)
Samantha  American female (light, precise)
Tom       American male (deep, ominous)
Oliver    British male (imperial)
```

## Piper / say faction modes

For `piper` and `say`, use the voice explorer script directly:
```bash
source ~/gwent-venv/bin/activate
tts-voice-explorer --tts piper          # audition with audio
tts-voice-explorer --tts piper --show   # show mapping only
tts-voice-explorer --tts say            # macOS only
tts-voice-explorer --tts say --show     # show mapping only
```

To update faction assignments, edit the `FACTION_VOICE` dict in the provider file:
- Piper: `software/gwent/gwent/hal/tts/piper_provider.py`
- Say: `software/gwent/gwent/hal/tts/say_provider.py`

## gTTS faction audition mode (provider is gtts or google)

gTTS voices are regional accents selected by TLD. The procedure is different from ElevenLabs/OpenAI:

1. **Read the current mapping** from `software/gwent/gwent/hal/tts/gtts_provider.py` → `FACTION_VOICE` dict.

2. **Play all TLD accents** in one Bash call using a Python script that loops through every TLD:
   ```python
   import gtts, pydub, pygame.mixer, os, time
   TLDS = [("com","US"), ("co.uk","UK"), ("com.au","Australian"), ...]
   for tld, accent in TLDS:
       text = f"Google, {accent}. {Faction} voice. {gwent_phrase}"
       # generate mp3, convert wav, play, sleep
   ```

3. **One AskUserQuestion** with all accents listed. Mark the current TLD with "(current)".

4. **Apply the choice**: Edit `FACTION_VOICE` dict in `gtts_provider.py` to update the TLD for that faction.

5. **Clear TTS cache**: `rm -rf /tmp/gwent-sfx/`

Provider file: `software/gwent/gwent/hal/tts/gtts_provider.py`

## Faction audition mode (elevenlabs or openai)

Run **one single Bash command** that generates ALL voices, then plays them back-to-back. Each voice announces itself: `"{provider}, {voice_name}. {Faction} voice. {gwent_phrase}"`.

Use a **single Python script** in one Bash call that loops through every voice in the catalog:

```python
# pseudocode — adapt for elevenlabs or openai
voices = [...]  # full catalog
for name, vid in voices:
    generate mp3 (skip if cached)
    convert to wav (skip if cached)
    print(f"Playing: {name}")
    play wav, sleep for duration
```

After ALL voices finish playing, use **one AskUserQuestion**. **UNBREAKABLE RULE: Every single voice from the catalog MUST appear as an option.** Since AskUserQuestion only supports up to 4 options, split into multiple rounds of 4 if needed — or use a single question with 4 options and tell the user to type their pick via "Other" if it's not listed. Mark the current voice with "(current)" in its description. The user picks the winner.

Then:
1. **Apply the choice**: Edit the provider file (`FACTION_VOICE_ID` or `FACTION_VOICE` dict + docstring).
2. **Clear TTS cache**: `rm -rf /tmp/gwent-sfx/`
3. **Confirm**: Show old → new mapping.

Provider files:
- ElevenLabs: `software/gwent/gwent/hal/tts/elevenlabs_provider.py`
- OpenAI: `software/gwent/gwent/hal/tts/openai_provider.py`

## All-factions mode (no faction provided)

1. Randomly assign voices from the catalog to each of the 5 factions (no duplicates).
2. Update the provider file with the new mapping.
3. Clear TTS cache: `rm -rf /tmp/gwent-sfx/`
4. Show the new mapping in a table.
