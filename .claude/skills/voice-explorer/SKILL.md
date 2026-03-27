---
name: voice-explorer
description: Audition TTS voices for Gwent factions across providers (gtts, elevenlabs, openai)
user_invocable: true
allowed-tools: Bash, AskUserQuestion, Edit, Read
---

Audition TTS voices for a specific faction and provider, then let the user pick a winner.

## Usage

`/voice-explorer <provider> [faction]`

- **provider** (required): `elevenlabs` | `openai`
- **faction** (optional): `monsters` | `northern-realms` | `skellige` | `scoiatael` | `nilfgaardian`

If **faction is omitted**, run in **all-factions mode**: randomly assign one voice from the provider's catalog to each faction, update the provider file, clear the TTS cache, and confirm the mapping. No audition — just shuffle and apply.

If **provider is missing**, use AskUserQuestion to ask.

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

## Faction audition mode (faction provided)

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
