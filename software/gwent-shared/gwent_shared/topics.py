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
MUSIC_CTRL = f'{MUSIC}/ctrl'

# Card events
CARDS_RAW_READ = f'{MAIN}/cards/raw/read'
CARDS_PLAY = f'{MAIN}/cards/play'  # + /PLAYER.ONE or /PLAYER.TWO

# Server presence (retained, with LWT — payload is "online" or "offline")
PRESENCE = f'{MAIN}/server/presence'

# TUI menu mirror — same idiom as MFD but distinct topics so the MFD path
# (rotary + OLED) stays unchanged. Each menu is published RETAINED under
# `gwent/menu/present/{menu_id}` so clients can render whichever menu is
# active without a request roundtrip. Clients respond on `gwent/menu/choose`.
#
# Menu IDs in use:
#   main           — server-idle main menu (recordings, random, fresh game)
#   assign-p1      — controller picker for player 1 (Phase 3)
#   assign-p2      — controller picker for player 2 (Phase 3)
#   in-game-menu   — reset / step-mode / cancel (Phase 4)
MENU = f'{MAIN}/menu'
MENU_PRESENT_PREFIX = f'{MENU}/present'  # subscribe to `+` for all menus
MENU_PRESENT_WILDCARD = f'{MENU_PRESENT_PREFIX}/+'
MENU_CHOOSE = f'{MENU}/choose'


def menu_present_topic(menu_id: str) -> str:
    """Per-menu present topic. e.g. menu_present_topic("main") -> gwent/menu/present/main"""
    return f'{MENU_PRESENT_PREFIX}/{menu_id}'
