"""Shared fixtures and helpers for leader integration tests.

Tests require a running gwent game loaded with a recording:
    GWENT_STATE=<recording> bash scripts/dev-server.sh gwent start

Run with:
    pytest software/gwent/integration-tests/ --recording <path>
"""

import hashlib
import json
import time
import urllib.request

import paho.mqtt.client as mqtt
import pytest

MQTT_HOST = "localhost"
MQTT_USER = "geralt"
MQTT_PASS = "gwent"
STATE_URL = "http://localhost:8080/state"

TOPIC_CARD_READ = "gwent/cards/raw/read"
TOPIC_MFD_CHOOSE = "gwent/mfd/choose"


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
    """Helper for interacting with the running gwent game."""

    def __init__(self, mqtt_client):
        self._mqtt = mqtt_client

    def get_state(self):
        """Fetch current game state from HTTP API."""
        req = urllib.request.Request(STATE_URL)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())

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
        """Poll /state until the ETag changes or timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                req = urllib.request.Request(STATE_URL)
                req.add_header("If-None-Match", pre_etag)
                remaining = max(1, deadline - time.time())
                with urllib.request.urlopen(
                    req, timeout=min(5, remaining)
                ) as resp:
                    data = json.loads(resp.read())
                    new_etag = resp.headers.get("ETag", "")
                    if new_etag != pre_etag:
                        return data
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    time.sleep(0.5)
                    continue
                raise
            except Exception:
                time.sleep(0.5)
        raise TimeoutError(f"State did not change within {timeout}s")

    def wait_for_current_player(self, expected_player, timeout=20):
        """Poll until current_player matches expected value."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            board = self.get_board()
            if board["current_player"] == expected_player:
                return board
            time.sleep(1)
        raise TimeoutError(
            f"current_player did not become {expected_player} within {timeout}s"
        )


@pytest.fixture(scope="session")
def game(mqtt_client):
    return GameAPI(mqtt_client)


def card_names(cards):
    """Extract card names from a list of card dicts."""
    return [c.get("name", "?") for c in cards]
