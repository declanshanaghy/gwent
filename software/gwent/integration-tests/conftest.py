"""Shared fixtures and helpers for leader integration tests.

Tests require a running gwent game loaded with a recording:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start

Run with:
    pytest software/gwent/integration-tests/ --recording <path>
"""

import hashlib
import json
import threading
import time

import paho.mqtt.client as mqtt
import pytest

MQTT_HOST = "localhost"
MQTT_USER = "geralt"
MQTT_PASS = "gwent"

TOPIC_CARD_READ = "gwent/cards/raw/read"
TOPIC_MFD_CHOOSE = "gwent/mfd/choose"
TOPIC_SERVER_STATE = "gwent/server/state"


def pytest_addoption(parser):
    parser.addoption(
        "--recording", required=True,
        help="Path to game recording JSON file",
    )


@pytest.fixture(scope="session")
def recording_path(request):
    return request.config.getoption("--recording")


@pytest.fixture(scope="session")
def recording(recording_path):
    with open(recording_path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_HOST, 1883, 60)
    client.loop_start()
    yield client
    client.loop_stop()
    client.disconnect()


class GameAPI:
    """Helper for interacting with the running gwent game over MQTT.

    Game state comes from the retained `gwent/server/state` topic (delivered
    instantly on subscribe and republished on every change); commands are
    injected by publishing to the card/choice topics.
    """

    def __init__(self, mqtt_client):
        self._mqtt = mqtt_client
        self._lock = threading.Lock()
        self._snapshot = None
        self._event = threading.Event()
        mqtt_client.on_message = self._on_message
        mqtt_client.subscribe(TOPIC_SERVER_STATE, qos=1)

    def _on_message(self, client, userdata, msg):
        if msg.topic != TOPIC_SERVER_STATE or not msg.payload:
            return
        try:
            d = json.loads(msg.payload)
        except Exception:
            return
        with self._lock:
            self._snapshot = d
        self._event.set()

    def get_state(self, timeout=10):
        """Return the latest game-state snapshot, waiting for the first one."""
        deadline = time.time() + timeout
        while True:
            with self._lock:
                if self._snapshot is not None:
                    return self._snapshot
            if time.time() >= deadline:
                raise TimeoutError("no gwent/server/state received")
            self._event.wait(timeout=0.2)

    def get_board(self):
        """Fetch just the board dict."""
        return self.get_state()["state"]["board"]

    @staticmethod
    def compute_etag(snapshot):
        stable = dict(snapshot)
        stable.pop("saved_at", None)
        raw = json.dumps(stable, sort_keys=True).encode("utf-8")
        return hashlib.md5(raw).hexdigest()

    def inject_card(self, card_json):
        """Inject a card scan via MQTT."""
        payload = dict(card_json)
        payload["kind"] = "card"
        result = self._mqtt.publish(
            TOPIC_CARD_READ, json.dumps(payload), qos=1)
        result.wait_for_publish(timeout=5)

    def inject_choice(self, choice_id, text=""):
        """Inject an MFD choice via MQTT."""
        result = self._mqtt.publish(
            TOPIC_MFD_CHOOSE,
            json.dumps({"kind": "choice", "id": choice_id, "text": text}),
            qos=1,
        )
        result.wait_for_publish(timeout=5)

    def inject_card_and_wait(self, card_json, timeout=20):
        """Inject a card and wait for the game state to change."""
        pre_state = self.get_state()
        pre_etag = self.compute_etag(pre_state)
        self.inject_card(card_json)
        time.sleep(2)
        return self.wait_for_state_change(pre_etag, timeout=timeout)

    def wait_for_state_change(self, pre_etag, timeout=20):
        """Wait until the snapshot hash changes from pre_etag or timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._event.clear()
            data = self.get_state()
            if self.compute_etag(data) != pre_etag:
                return data
            self._event.wait(timeout=min(0.5, max(0.0, deadline - time.time())))
        raise TimeoutError(f"State did not change within {timeout}s")

    def wait_for_current_player(self, expected_player, timeout=20):
        """Wait until current_player matches expected value."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._event.clear()
            board = self.get_board()
            if board["current_player"] == expected_player:
                return board
            self._event.wait(timeout=min(0.5, max(0.0, deadline - time.time())))
        raise TimeoutError(
            f"current_player did not become {expected_player} within {timeout}s"
        )


@pytest.fixture(scope="session")
def game(mqtt_client):
    return GameAPI(mqtt_client)


def card_names(cards):
    """Extract card names from a list of card dicts."""
    return [c.get("name", "?") for c in cards]
