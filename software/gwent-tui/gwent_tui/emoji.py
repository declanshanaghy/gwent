"""Emoji constants and helper functions for game state rendering."""

FACTION_EMOJI = {
    "Northern Realms": ("\U0001f981", "\u2696\ufe0f"),   # lion, fleur-de-lis
    "Nilfgaardian":    ("\U0001f311", "\u2600\ufe0f"),    # new moon, sun
    "Scoia'tael":      ("\U0001f33f", "\U0001f3f9"),      # herb, bow
    "Scoiatael":       ("\U0001f33f", "\U0001f3f9"),      # alt spelling
    "Monsters":        ("\U0001f479", "\U0001f525"),       # ogre, fire
    "Skellige":        ("\u2693",     "\U0001fa93"),       # anchor, axe
}

ROW_EMOJI = {
    "close":  "\u2694\ufe0f",   # crossed swords
    "ranged": "\U0001f3f9",     # bow
    "siege":  "\U0001f3f0",     # castle
}

WEATHER_EMOJI = {
    "close":  "\U0001f328\ufe0f\u2744\ufe0f",   # cloud snow + snowflake
    "ranged": "\U0001f32b\ufe0f\U0001f441\ufe0f", # fog + eye
    "siege":  "\U0001f327\ufe0f\U0001f4a7",       # rain + droplet
}

WEATHER_NAME = {
    "close":  "Frost",
    "ranged": "Fog",
    "siege":  "Rain",
}

# Card specialty/ability emoji
HERO = "\U0001f6e1\ufe0f"          # shield
SCORCH = "\U0001f525"              # fire
DECOY = "\U0001f3ad"               # masks
COMMANDER = "\U0001f4ef"           # postal horn
WEATHER_CARD = {
    "Biting Frost":       "\U0001f328\ufe0f",
    "Impenetrable Fog":   "\U0001f32b\ufe0f",
    "Torrential Rain":    "\U0001f327\ufe0f",
    "Clear Weather":      "\u2600\ufe0f",
}
# Short display names for weather cards
WEATHER_SHORT = {
    "Biting Frost":       "Frost",
    "Impenetrable Fog":   "Fog",
    "Torrential Rain":    "Rain",
    "Clear Weather":      "Clear Weather",
}
MEDIC = "\U0001fa7a"               # stethoscope
MUSTER = "\U0001f465"              # busts in silhouette
BOND = "\U0001f91d"                # handshake
SPY = "\U0001f575\ufe0f"           # detective
MORALE = "\U0001f4aa"              # flexed bicep
BERSERKER = "\U0001f43b"           # bear

GEM = "\U0001f48e"                 # gem
SKULL = "\U0001f480"               # skull
CROWN = "\U0001f451"               # crown
STAR = "\u2b50"                    # star (starter)
CUBE = "\U0001f4e6"               # package (remainder/unowned)
ZAP = "\u26a1"                     # high voltage (row total)
FLAG = "\U0001f3f3\ufe0f"          # white flag (passed)


def faction_emoji(faction):
    """Get emoji pair for a faction name as (left, right) tuple."""
    if not faction:
        return ("", "")
    return FACTION_EMOJI.get(faction, ("", ""))


# Rich markup colors for owner nicknames — deterministic by hash
_OWNER_COLORS = [
    "cyan", "magenta", "yellow", "green", "blue",
    "bright_red", "bright_cyan", "bright_magenta", "bright_yellow",
    "bright_green", "bright_blue", "dark_orange", "orchid",
    "turquoise2", "spring_green1", "deep_pink1", "gold1",
]


def _owner_color(name):
    """Pick a consistent color for an owner based on name hash."""
    h = sum(ord(c) for c in name)
    return _OWNER_COLORS[h % len(_OWNER_COLORS)]


def owner_short(card):
    """Get short owner display: [nickname] in color, or [INITIALS]."""
    nickname = card.get("owner_nickname", "")
    if not nickname:
        owner = card.get("owner", "")
        if not owner:
            return ""
        nickname = "".join(w[0].upper() for w in owner.split() if w)
    color = _owner_color(nickname)
    return f"[{color}]\\[{nickname}][/{color}]"


def gems_display(gems, max_gems=2):
    """Render gems as gem/skull emoji string."""
    alive = min(gems, max_gems)
    dead = max_gems - alive
    return GEM * alive + SKULL * dead


def card_prefix(card):
    """Build emoji prefix for a card dict based on type, specialty, abilities."""
    parts = []
    specialty = card.get("specialty", "")
    abilities = card.get("abilities", []) or []
    ability = card.get("ability", "")  # some cards use singular
    ranges = card.get("ranges", []) or []
    name = card.get("name", "")

    # Weather cards — strip ": N" suffix for lookup
    if specialty == "weather":
        base_name = name.split(":")[0].strip() if ":" in name else name
        emoji = WEATHER_CARD.get(base_name, WEATHER_CARD.get(name, "\U0001f327\ufe0f"))
        return emoji

    # Scorch
    if specialty == "scorch":
        return SCORCH

    # Decoy
    if specialty == "decoy":
        return DECOY

    # Commander's Horn (standalone card)
    if specialty == "commander" and not ranges:
        return COMMANDER
    if specialty == "commander" and card.get("strength") is None:
        return COMMANDER

    # Unit cards — range emojis
    for r in ranges:
        if r in ROW_EMOJI:
            parts.append(ROW_EMOJI[r])

    # Hero
    if specialty == "hero":
        parts.append(HERO)

    # Abilities
    all_abilities = list(abilities)
    if ability and ability not in all_abilities:
        all_abilities.append(ability)

    for ab in all_abilities:
        if ab == "medic":
            parts.append(MEDIC)
        elif ab == "muster":
            parts.append(MUSTER)
        elif ab == "bond":
            parts.append(BOND)
        elif ab == "spy":
            parts.append(SPY)
        elif ab == "morale":
            parts.append(MORALE)
        elif ab == "commander":
            parts.append(COMMANDER)
        elif ab == "mardroeme" or ab == "berserker":
            parts.append(BERSERKER)

    return "".join(parts) if parts else "\u2753"  # question mark fallback


# Rich markup colors for faction-colored card names
FACTION_COLOR = {
    "Monsters":        "red",
    "Nilfgaardian":    "grey74",
    "Northern Realms": "royal_blue1",
    "Scoia'tael":      "green",
    "Scoiatael":       "green",
    "Skellige":        "cyan",
    "Neutral":         "white",
}


def _faction_color(card):
    """Get Rich color for a card's faction."""
    return FACTION_COLOR.get(card.get("faction", ""), "white")


def _truncate_name(name, max_len=20):
    """Truncate a name to max_len, cutting from the middle."""
    if len(name) <= max_len:
        return name
    # Keep start and end, join with ellipsis
    keep = max_len - 1  # 1 char for ellipsis
    left = keep // 2
    right = keep - left
    return name[:left] + "\u2026" + name[-right:]


def _display_name(card):
    """Get display name for a card. Weather cards use short names."""
    name = card.get("name", "???")
    if card.get("specialty") == "weather":
        base = name.split(":")[0].strip() if ":" in name else name
        return WEATHER_SHORT.get(base, name)
    return name


def card_display(card, max_name=None):
    """Format a card for display: emoji + full name + (strength) + ownership."""
    prefix = card_prefix(card)
    name = card.get("name", "???")
    strength = card.get("strength")
    owner = card.get("owner", "")
    starter = card.get("starter", False)

    fc = _faction_color(card)
    parts = [prefix, f" [{fc}]", name, f"[/{fc}]"]
    if strength is not None:
        parts.append(f" ({strength})")

    if starter:
        parts.append(f" {STAR}")
    elif owner:
        parts.append(f" {owner_short(card)}")
    else:
        parts.append(f" {CUBE}")

    return "".join(parts)


def card_display_short(card, max_name=None, weather_active=False):
    """Card display for board rows: emoji + full name + (strength).

    When weather_active, non-hero units show strikethrough name and reduced
    strength (1) instead of their base strength.
    """
    prefix = card_prefix(card)
    name = card.get("name", "???")
    strength = card.get("strength")
    is_hero = card.get("specialty") == "hero"

    fc = _faction_color(card)
    weathered = weather_active and not is_hero and strength and strength > 1

    if weathered:
        parts = [prefix, " [strike dim]", name, "[/strike dim]"]
        parts.append(f" [strike dim]({strength})[/strike dim] [bold cyan](1)[/bold cyan]")
    else:
        parts = [prefix, f" [{fc}]", name, f"[/{fc}]"]
        if strength is not None:
            parts.append(f" ({strength})")

    return "".join(parts)


def _wrap_name(name, max_width=30):
    """Wrap a long name on word boundaries, returning multiple lines."""
    if len(name) <= max_width:
        return [name]
    words = name.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines


def leader_display(card, used=False, max_name=None):
    """Format a leader card for display. Long names wrap on word boundaries."""
    if not card:
        return "—"
    name = card.get("name", "???")
    starter = card.get("starter", False)
    owner = card.get("owner", "")

    fc = _faction_color(card)
    name_lines = _wrap_name(name)

    if used:
        wrapped = "\n         ".join(name_lines)
        parts = [CROWN, f" [strike dim]{wrapped}[/strike dim] [dim](used)[/dim]"]
    else:
        first = name_lines[0]
        rest = name_lines[1:]
        parts = [CROWN, f" [{fc}]", first]
        for line in rest:
            parts.append(f"\n         {line}")
        parts.append(f"[/{fc}]")
        if starter:
            parts.append(f" {STAR}")
        elif owner:
            parts.append(f" {owner_short(card)}")
        else:
            parts.append(f" {CUBE}")

    return "".join(parts)
