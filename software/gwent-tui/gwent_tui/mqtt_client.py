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

TOPICS = [
    ("gwent/ctrl", 0),
    ("gwent/mfd/present", 0),
    ("gwent/mfd/choose", 0),
    ("gwent/sfx", 0),
    ("gwent/sfx/complete", 0),
    ("gwent/cards/raw/read", 0),
    ("gwent/cards/play/+", 0),
]


class MqttSubscriber:
    def __init__(self, state, host=None, port=None):
        self.state = state
        self.host = host or BROKER_HOST
        self.port = port or BROKER_PORT
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="gwent-tui",
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
            self.client.publish("gwent/sfx/complete", payload)
        except Exception as e:
            log.debug("Failed to publish announcement_complete: %s", e)

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

        if topic == "gwent/ctrl":
            self.state.on_ctrl(data)

        elif topic == "gwent/mfd/present":
            self.state.on_mfd(data)

        elif topic == "gwent/mfd/choose":
            self.state.on_choice(data)

        elif topic == "gwent/sfx":
            self.state.on_sfx(data)
            if data.get("subkind") == "announcement":
                tts.speak(data.get("announcement", ""),
                          faction=data.get("faction"),
                          content_id=data.get("content_id"))

        elif topic == "gwent/cards/raw/read":
            self.state.on_raw_read(data)

        elif topic.startswith("gwent/cards/play/"):
            player_suffix = topic.rsplit("/", 1)[-1]
            self.state.on_card_play(player_suffix, data)

        self.state.mqtt_status = "alive"
