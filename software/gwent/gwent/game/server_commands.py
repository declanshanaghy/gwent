"""ServerCommandHandler — handles client→server commands over MQTT.

Subscribes to the `gwent/ctrl/*` command topics:

  gwent/ctrl/players      {"PLAYER.ONE": {"name","pronoun"} | "<name>", ...}
  gwent/ctrl/client-tts   {"client_id": "...", "provider": "..."}

Payloads are free-form JSON (not the gwent.messaging envelope), so this
subscribes via the raw MQTT client rather than PubSubComponent.subscribe.
Writes go through the shared apply_* helpers and then notify state_condition to
trigger a StatePublisher republish.
"""

import json

import paho.mqtt.client as mqtt

from gwent.game import PubSubComponent
from gwent.game.session_config import (
    SessionConfig,
    apply_client_tts,
    apply_player_names,
)
from gwent_shared.topics import CTRL_CLIENT_TTS, CTRL_PLAYERS


class ServerCommandHandler(PubSubComponent):
    """Owns the gwent/ctrl/* command topics."""

    def __init__(self, pubsub: mqtt.Client, controller, session_config: SessionConfig):
        super().__init__(pubsub)
        self._controller = controller
        self._cfg = session_config
        self._raw_topics = (CTRL_PLAYERS, CTRL_CLIENT_TTS)

    def init(self):
        super().init()
        # Raw subscriptions (free-form JSON, not the messaging envelope).
        self._pubsub.subscribe(CTRL_PLAYERS, self._on_set_players)
        self._pubsub.subscribe(CTRL_CLIENT_TTS, self._on_set_client_tts)
        self._log.info("ServerCommandHandler initialized")

    def shutdown(self):
        for topic in self._raw_topics:
            try:
                self._pubsub.unsubscribe(topic)
            except Exception as e:
                self._log.debug("unsubscribe %s failed: %s", topic, e)
        super().shutdown()

    def _notify_state_changed(self):
        """Wake the StatePublisher so it republishes the snapshot."""
        cond = getattr(self._pubsub, 'state_condition', None)
        if cond:
            with cond:
                cond.notify_all()

    def _on_set_players(self, topic, payload):
        try:
            data = json.loads(payload)
            apply_player_names(self._cfg, data)
            self._notify_state_changed()
        except Exception as e:
            self._log.error("Error handling %s: %s", CTRL_PLAYERS, e, exc_info=True)

    def _on_set_client_tts(self, topic, payload):
        try:
            data = json.loads(payload)
            client_id = data.get("client_id", "gwent-tui")
            provider = data.get("provider", "none")
            apply_client_tts(self._cfg, client_id, provider)
            self._notify_state_changed()
        except Exception as e:
            self._log.error("Error handling %s: %s", CTRL_CLIENT_TTS, e, exc_info=True)
