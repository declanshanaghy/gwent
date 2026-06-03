"""Per-session server config: player metadata + connected-client TTS state.

Holds the mutable bits that used to live on the HTTP server (`_GwentHTTPServer`)
so they have a single owner shared by every transport — the StatePublisher reads
them into the snapshot, and the MQTT command handlers (and, during the HTTP→MQTT
transition, the dormant HTTP PUT handlers) write to them through the apply_*
helpers below.
"""

from dataclasses import dataclass, field

import gwent.game
from gwent.utils.logging import get_logger

log = get_logger("gwent.game.session_config")


@dataclass
class SessionConfig:
    player_names: dict = field(
        default_factory=lambda: {"PLAYER.ONE": "Player 1", "PLAYER.TWO": "Player 2"})
    player_pronouns: dict = field(
        default_factory=lambda: {"PLAYER.ONE": "he", "PLAYER.TWO": "he"})
    client_tts: dict = field(default_factory=dict)  # {client_id: provider_name}


def apply_player_names(cfg: SessionConfig, data: dict):
    """Apply a players command/PUT body to cfg.

    Accepts either a bare name string or an extended
    {"name": "...", "pronoun": "he|she"} dict per player key.
    """
    for key in ("PLAYER.ONE", "PLAYER.TWO"):
        if key not in data:
            continue
        val = data[key]
        if isinstance(val, dict):
            cfg.player_names[key] = str(val.get("name", key))
            if "pronoun" in val:
                cfg.player_pronouns[key] = str(val["pronoun"])
        else:
            cfg.player_names[key] = str(val)
    log.info("Player names updated: %s, pronouns: %s",
             cfg.player_names, cfg.player_pronouns)


def apply_client_tts(cfg: SessionConfig, client_id: str, provider: str):
    """Register a client's TTS provider and hand audio over to that client.

    Sets the server-wide flags so the server stops doing local TTS/music, and
    stops any in-flight pygame music stream once, so the client becomes the sole
    audio source (mirrors the old PUT /client-tts behaviour).
    """
    cfg.client_tts[client_id] = provider
    log.info("Client TTS registered: %s=%s", client_id, provider)

    # Tell server SFX to skip local music AND TTS — the client handles both.
    already_handled = gwent.game.PubSubComponent._client_handles_music
    gwent.game.PubSubComponent._client_handles_music = True
    gwent.game.PubSubComponent._client_handles_tts = True

    # If the server was already playing music when the client registered, the
    # existing pygame stream keeps running forever (subsequent plays are
    # skipped). Stop it now so the client's stream is the only source.
    if not already_handled:
        try:
            from gwent_shared.audio import get_mixer
            mixer = get_mixer()
            log.info("Client took over music — disabling local server playback")
            mixer.disable_music()
        except Exception as e:
            log.warning("failed to disable local music on client takeover: %s", e)
