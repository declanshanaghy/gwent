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
    MUSIC, MUSIC_COMPLETE, CARDS_RAW_READ, CARDS_PLAY,
)

TOPICS = [
    (CTRL, 0),
    (MFD_PRESENT, 0),
    (MFD_CHOOSE, 0),
    (SFX, 0),
    (SFX_COMPLETE, 0),
    (MUSIC, 0),                   # retained: current music track
    (CARDS_RAW_READ, 0),
    (f"{CARDS_PLAY}/+", 0),
]


class MqttSubscriber:
    def __init__(self, state, host=None, port=None):
        self.state = state
        self._current_music_track = ""
        self._next_music_track = ""
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

    def _publish_music_complete(self):
        """Track finished — immediately start next_music, then notify server."""
        track = self._current_music_track or ""
        next_track = getattr(self, '_next_music_track', "")

        # Start next track immediately (don't wait for server round-trip)
        if next_track:
            log.info("Track finished, starting next: %s", next_track)
            self._play_music(next_track, started_at="")

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

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            log.warning("Bad payload on %s", msg.topic)
            return

        topic = msg.topic
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

        elif topic == MUSIC:
            # Retained message — current music track from server
            music_name = data.get("music")
            self._next_music_track = data.get("next_music", "")
            started_at = data.get("started_at", "")
            log.info("Music update: %s (next=%s)", music_name, self._next_music_track)
            self.state._log_event(
                f"\U0001f3b5 Now playing: {music_name or 'random'}", color="plum1")
            self._play_music(music_name, started_at)

        elif topic == CARDS_RAW_READ:
            self.state.on_raw_read(data)

        elif topic.startswith(f"{CARDS_PLAY}/"):
            player_suffix = topic.rsplit("/", 1)[-1]
            self.state.on_card_play(player_suffix, data)

        self.state.mqtt_status = "alive"
