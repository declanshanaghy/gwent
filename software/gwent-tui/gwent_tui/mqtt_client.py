"""MQTT subscriber that routes messages to GameState."""

import json
import logging

import paho.mqtt.client as mqtt

from gwent_tui import tts

log = logging.getLogger("gwent_tui.mqtt")


BROKER_HOST = "localhost"
BROKER_PORT = 1883
BROKER_USER = "geralt"
BROKER_PASS = "gwent"

from gwent_shared.topics import (
    CTRL, MFD_PRESENT, MFD_CHOOSE, SFX, SFX_COMPLETE,
    MUSIC, MUSIC_COMPLETE, MUSIC_CTRL, CARDS_RAW_READ, CARDS_PLAY,
    PRESENCE, MAIN,
    MENU_PRESENT_PREFIX, MENU_PRESENT_WILDCARD, MENU_CHOOSE,
)

# Per-side retained controller state — Phase 3.
PLAYERS_CONTROLLER_PREFIX = f"{MAIN}/players/controller"
PLAYERS_CONTROLLER_WILDCARD = f"{PLAYERS_CONTROLLER_PREFIX}/+"
# Transient TUI banner topic — Phase 3.
TOAST = f"{MAIN}/toast"

TOPICS = [
    (CTRL, 0),
    (MFD_PRESENT, 0),
    (MFD_CHOOSE, 0),
    (SFX, 0),
    (SFX_COMPLETE, 0),
    (MUSIC, 0),                   # retained: current music track
    (PRESENCE, 0),                # retained: server online/offline
    (CARDS_RAW_READ, 0),
    (f"{CARDS_PLAY}/+", 0),
    (MENU_PRESENT_WILDCARD, 0),   # retained: TUI menu mirror (per menu_id)
    (PLAYERS_CONTROLLER_WILDCARD, 0),  # retained: which controller drives each side
    (TOAST, 0),                   # transient: failover / status banners
]


class MqttSubscriber:
    def __init__(self, state, host=None, port=None):
        self.state = state
        self._current_music_track = ""
        self._next_music_track = ""
        self.music_enabled = True
        self._server_online = True   # assume online until presence says otherwise
        self.host = host or BROKER_HOST
        self.port = port or BROKER_PORT
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="gwent-tui",
            clean_session=True,
        )
        self.client.username_pw_set(BROKER_USER, BROKER_PASS)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def connect(self):
        """Connect and start background loop."""
        try:
            log.info("Connecting to MQTT broker %s:%d", self.host, self.port)
            self.client.connect(self.host, self.port, keepalive=60)
            self.client.loop_start()
            # Wire TTS completion to publish announcement_complete
            tts.set_on_complete(self._publish_announcement_complete)
            tts.set_on_music_complete(self._publish_music_complete)
        except Exception as e:
            log.error("MQTT connect failed: %s", e)
            self.state.mqtt_status = "error"

    def _publish_announcement_complete(self, content_id):
        """Publish announcement_complete with original content_id."""
        try:
            payload = json.dumps({
                "kind": "sfx",
                "subkind": "announcement_complete",
                "original_content_id": content_id,
                "source": "gwent-tui",
            })
            self.client.publish(SFX_COMPLETE, payload)
        except Exception as e:
            log.debug("Failed to publish announcement_complete: %s", e)

    def publish_music_toggle(self):
        """Publish music toggle command to server and toggle local playback."""
        self.music_enabled = not self.music_enabled
        log.info("Music %s", "enabled" if self.music_enabled else "disabled")
        if not self.music_enabled:
            tts.stop_music()
        try:
            payload = json.dumps({
                "kind": "music",
                "subkind": "control",
                "action": "toggle",
                "source": "gwent-tui",
            })
            self.client.publish(MUSIC_CTRL, payload)
            log.info("Published music toggle")
        except Exception as e:
            log.debug("Failed to publish music toggle: %s", e)

    def _publish_music_complete(self):
        """Track finished — immediately start next_music, then notify server."""
        track = self._current_music_track or ""
        next_track = getattr(self, '_next_music_track', "")

        # Start next track immediately (don't wait for server round-trip).
        # Skip auto-advance if the server is offline — otherwise music would
        # loop forever after the server stops.
        if next_track and self._server_online:
            log.info("Track finished, starting next: %s", next_track)
            self._play_music(next_track, started_at="")
        elif next_track:
            log.info("Track finished; server offline, skipping auto-advance")

        # Notify server so it can update the retained message
        try:
            payload = json.dumps({
                "kind": "music",
                "subkind": "complete",
                "music": track,
                "source": "gwent-tui",
            })
            self.client.publish(MUSIC_COMPLETE, payload)
            log.info("Published music complete for: %s", track)
        except Exception as e:
            log.debug("Failed to publish music complete: %s", e)

    def _play_music(self, music_name, started_at=0):
        """Resolve a music track and play it, seeking to current position."""
        import time as _time
        import random as _random
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        music_dir = repo_root / "data" / "music"

        if not music_name:
            files = list(music_dir.glob("*.mp3"))
            if files:
                path = str(_random.choice(files))
            else:
                log.debug("No music files found in %s", music_dir)
                return
        else:
            path = str(music_dir / f"{music_name}.mp3")

        import os
        if not os.path.exists(path):
            log.debug("Music file not found: %s", path)
            return

        # Calculate seek offset from server's started_at ISO 8601 timestamp
        seek_seconds = 0
        if started_at:
            try:
                from datetime import datetime
                start = datetime.fromisoformat(started_at)
                now = datetime.now().astimezone()
                seek_seconds = max(0, (now - start).total_seconds())
                if seek_seconds > 1:
                    log.info("Music seek: %.0fs into track", seek_seconds)
            except (ValueError, TypeError):
                pass

        self._current_music_track = music_name or os.path.splitext(os.path.basename(path))[0]
        tts.play_music(path, seek_seconds=seek_seconds)

    def disconnect(self):
        """Stop loop and disconnect."""
        tts.stop()
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        log.info("MQTT connected (rc=%s)", reason_code)
        self.state.mqtt_status = "alive"
        client.subscribe(TOPICS)
        self.state._log_event("MQTT connected")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        log.warning("MQTT disconnected (rc=%s)", reason_code)
        self.state.mqtt_status = "error"
        self.state._log_event("MQTT disconnected")

    def publish_choose(self, menu_id: str, choice_id: str) -> None:
        """Publish a `gwent/menu/choose` selection. Profuse logging per
        feedback_profuse_logging — every selection should be inspectable
        post-hoc."""
        payload = json.dumps({
            "kind": "menu",
            "menu_id": menu_id,
            "id": choice_id,
        })
        log.info("publish_choose menu_id=%s id=%s", menu_id, choice_id)
        try:
            result = self.client.publish(MENU_CHOOSE, payload, qos=1)
            log.debug("publish_choose result rc=%s mid=%s", result.rc, result.mid)
        except Exception as e:
            log.exception("publish_choose failed: %s", e)

    def publish_card_scan(self, card: dict) -> None:
        """Publish a card to `gwent/cards/raw/read`, simulating an RFID scan.

        The server controller subscribes to this topic and routes the card to
        the active stage's process_card() — identical to a physical scan. Used
        by the hand-detail overlay's [Play] button. Profuse logging per
        feedback_profuse_logging.
        """
        payload = dict(card)
        payload["kind"] = "card"
        # Drop the server-injected content id so the server recomputes it.
        payload.pop("content_id", None)
        data = json.dumps(payload)
        log.info("publish_card_scan name=%s rfid=%s",
                 card.get("name"), card.get("rfid"))
        try:
            result = self.client.publish(CARDS_RAW_READ, data, qos=1)
            log.debug("publish_card_scan result rc=%s mid=%s",
                      result.rc, result.mid)
        except Exception as e:
            log.exception("publish_card_scan failed: %s", e)

    def _announce_matchup(self, data: dict) -> None:
        """Speak a Witcher-style matchup line when the New Game wizard is shown
        or re-rolled. Fires once per distinct wizard payload (content_id)."""
        summary = (data or {}).get("summary") or {}
        if summary.get("error"):
            return
        p1 = (summary.get("p1") or {}).get("faction")
        p2 = (summary.get("p2") or {}).get("faction")
        if not p1 or not p2:
            return
        cid = data.get("content_id")
        if cid and cid == getattr(self, "_last_wizard_cid", None):
            return  # already announced this exact matchup
        self._last_wizard_cid = cid
        try:
            from gwent_tui import matchup_announcer
            line = matchup_announcer.announce_matchup(p1, p2)
            log.info("matchup announcement: %s", line)
            # Drop any queued matchup line so a fast re-roll speaks the latest.
            tts.clear_pending()
            tts.speak(line, faction=None)
        except Exception as e:
            log.error("matchup announcement failed: %s", e, exc_info=True)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic

        # Retained menu present — topic is `gwent/menu/present/{menu_id}`.
        # An EMPTY payload means the retained slot was cleared.
        if topic.startswith(MENU_PRESENT_PREFIX + "/"):
            menu_id = topic[len(MENU_PRESENT_PREFIX) + 1:]
            if not msg.payload:
                log.info("menu present CLEARED menu_id=%s", menu_id)
                self.state.on_menu(menu_id, None)
                return
            try:
                data = json.loads(msg.payload.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                log.warning("Bad menu payload on %s", topic)
                return
            log.info("menu present menu_id=%s choices=%d",
                     menu_id, len(data.get("choices", [])))
            self.state.on_menu(menu_id, data)
            if menu_id == "wizard":
                self._announce_matchup(data)
            return

        # Per-side controller state — Phase 3.
        if topic.startswith(PLAYERS_CONTROLLER_PREFIX + "/"):
            player_id = topic[len(PLAYERS_CONTROLLER_PREFIX) + 1:]
            if not msg.payload:
                log.info("controller CLEARED player=%s", player_id)
                self.state.on_controller(player_id, "human")
                return
            try:
                data = json.loads(msg.payload.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                log.warning("Bad controller payload on %s", topic)
                return
            self.state.on_controller(player_id, data.get("controller", "human"),
                                       data.get("label"))
            return

        # Transient toast — Phase 3.
        if topic == TOAST:
            try:
                data = json.loads(msg.payload.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                log.warning("Bad toast payload")
                return
            self.state.on_toast(data)
            return

        # Presence is a plain-text payload ("online"/"offline"), not JSON —
        # handle it before the JSON parse to avoid the bad-payload early-return.
        if topic == PRESENCE:
            status = msg.payload.decode("utf-8", errors="replace").strip()
            was_online = self._server_online
            self._server_online = (status == "online")
            log.info("Server presence: %s", status)
            if was_online and not self._server_online:
                self.state._log_event("\U0001f4f4 Server offline — stopping music", color="plum1")
                tts.stop_music()
            elif not was_online and self._server_online:
                self.state._log_event("\U0001f7e2 Server online", color="plum1")
            return

        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            log.warning("Bad payload on %s", msg.topic)
            return

        kind = data.get("kind", "")
        subkind = data.get("subkind", "")
        log.debug("MQTT msg topic=%s kind=%s subkind=%s", topic, kind, subkind)
        self.state.mqtt_status = "processing"

        if topic == CTRL:
            self.state.on_ctrl(data)

        elif topic == MFD_PRESENT:
            self.state.on_mfd(data)

        elif topic == MFD_CHOOSE:
            self.state.on_choice(data)

        elif topic == SFX:
            self.state.on_sfx(data)
            if data.get("subkind") == "announcement":
                tts.speak(data.get("announcement", ""),
                          faction=data.get("faction"),
                          content_id=data.get("content_id"))
            # SFX effects are triggered by the card overlay when shown

        elif topic == MUSIC:
            # Retained message — current music track from server
            self.state.game_log.write("music", data.get("subkind", "play"), data)
            music_name = data.get("music")
            self._next_music_track = data.get("next_music", "")
            started_at = data.get("started_at", "")
            log.info("Music update: %s (next=%s)", music_name, self._next_music_track)
            self.state._log_event(
                f"\U0001f3b5 Now playing: {music_name or 'random'}", color="plum1")
            if self.music_enabled:
                self._play_music(music_name, started_at)

        elif topic == CARDS_RAW_READ:
            self.state.on_raw_read(data)

        elif topic.startswith(f"{CARDS_PLAY}/"):
            player_suffix = topic.rsplit("/", 1)[-1]
            self.state.on_card_play(player_suffix, data)

        self.state.mqtt_status = "alive"
