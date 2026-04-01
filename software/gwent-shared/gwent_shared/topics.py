"""MQTT topic definitions — shared between server, TUI, and game-loop.

All MQTT topics used in the gwent system are defined here.
Import from gwent_shared.topics to avoid hardcoded topic strings.
"""

# Base
MAIN = 'gwent'

# Control
CTRL = f'{MAIN}/ctrl'

# Multi-Function Display
MFD = f'{MAIN}/mfd'
MFD_PRESENT = f'{MFD}/present'
MFD_CHOOSE = f'{MFD}/choose'

# Sound effects (announcements + effects)
SFX = f'{MAIN}/sfx'
SFX_COMPLETE = f'{SFX}/complete'

# Music (separate from SFX, retained)
MUSIC = f'{MAIN}/music'
MUSIC_COMPLETE = f'{MUSIC}/complete'

# Card events
CARDS_RAW_READ = f'{MAIN}/cards/raw/read'
CARDS_PLAY = f'{MAIN}/cards/play'  # + /PLAYER.ONE or /PLAYER.TWO
