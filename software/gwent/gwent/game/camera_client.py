"""CameraClient — game-server-side bridge to the gwent-camera service.

The camera is owned by the standalone gwent-camera service
(scripts/camera-server.py); this component only talks MQTT:

    out: gwent/camera/ctrl   {"action": on|off|record-start|record-stop|
                              save|discard|evict-saved, ...}
    in:  gwent/camera/state  retained status (camera_on, recording,
                              recordings list w/ sizes + URL paths, budget)

Responsibilities:
    - main-menu Camera toggle backend (camera_on / camera_off)
    - start a recording when a game deals (try_start_recording) — silent
      auto-eviction of unconfirmed recordings happens in the camera service;
      when only SAVED recordings block the 1.5 GiB headroom, prompt the user
      (with download URLs) before deleting any of them
    - stop the recording at Game Over and save/discard on the user's answer

EVERYTHING here is fail-soft: the camera service being down must never block
or break a game. Payloads are free-form JSON, so subscriptions use the raw
pubsub client (same pattern as ServerCommandHandler).
"""

import json
import secrets
import time
from datetime import datetime
from typing import Optional

import paho.mqtt.client as mqtt

from gwent.game import (
    CH_CAMERA_CTRL,
    CH_CAMERA_STATE,
    CH_SEP,
    MAIN_CHANNEL,
    PubSubComponent,
)

# Transient TUI banner (same topic the LLMPlayerManager uses)
_CH_TOAST = CH_SEP.join((MAIN_CHANNEL, 'toast'))

# How long an eviction prompt stays answerable before we assume the user
# moved on (avoids y/n crosstalk with later prompts, e.g. Game Over's).
_EVICT_PROMPT_TTL_SECS = 120


def _iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class CameraClient(PubSubComponent):
    """Thin MQTT bridge to gwent-camera. Never raises into game flow."""

    def __init__(self, pubsub: mqtt.Client):
        super().__init__(pubsub)
        self._state: Optional[dict] = None
        self._recording_game_id: Optional[str] = None
        # Pending saved-eviction prompt: (bytes_needed, deadline_monotonic)
        self._pending_evict: Optional[tuple] = None

    # ------------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------------

    def init(self):
        super().init()
        # Raw subscription — camera state is free-form JSON, not the envelope.
        self._pubsub.subscribe(CH_CAMERA_STATE, self._on_state)
        self._log.info("CameraClient initialized (waiting for retained state)")

    def shutdown(self):
        try:
            self._pubsub.unsubscribe(CH_CAMERA_STATE)
        except Exception as e:
            self._log.debug(f"unsubscribe {CH_CAMERA_STATE} failed: {e}")
        super().shutdown()

    # ------------------------------------------------------------------------
    # Inbound state
    # ------------------------------------------------------------------------

    def _on_state(self, topic, payload):
        try:
            if not payload:
                self._state = None
                self._log.warning("camera state cleared (empty retained payload)")
                return
            data = json.loads(payload)
            self._state = data
            self._log.info(
                "camera state: online=%s camera_on=%s live_view=%s "
                "recording=%s recordings=%d used=%.2fGB",
                data.get("online"), data.get("camera_on"),
                data.get("live_view"), data.get("recording"),
                len(data.get("recordings", [])),
                data.get("bytes_used", 0) / 1e9)
        except Exception as e:
            self._log.error(f"Error handling {topic}: {e}", exc_info=True)

    # ------------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return bool(self._state and self._state.get("online"))

    @property
    def camera_on(self) -> bool:
        return bool(self.available and self._state.get("camera_on"))

    @property
    def live_view(self) -> bool:
        return bool(self.available and self._state.get("live_view"))

    @property
    def recording_game_id(self) -> Optional[str]:
        return self._recording_game_id

    def _saved_bytes(self) -> int:
        if not self._state:
            return 0
        return sum(r.get("size", 0) for r in self._state.get("recordings", [])
                   if r.get("saved"))

    # ------------------------------------------------------------------------
    # Outbound control
    # ------------------------------------------------------------------------

    def _ctrl(self, action: str, **kw):
        payload = json.dumps({"action": action, "timestamp": _iso_now(), **kw})
        self._log.info(f"camera ctrl -> {payload}")
        self._pubsub.publish(CH_CAMERA_CTRL, payload, qos=1, retain=False)

    def _toast(self, text: str, level: str = "warn"):
        payload = json.dumps({
            "kind": "toast", "level": level, "text": text, "ts": time.time(),
        })
        self._pubsub.publish(_CH_TOAST, payload, qos=0, retain=False)
        self._log.info(f"toast ({level}): {text}")

    def camera_turn_on(self):
        self._ctrl("on")

    def camera_turn_off(self):
        self._ctrl("off")

    def live_view_show(self):
        self._ctrl("view-on")

    def live_view_hide(self):
        self._ctrl("view-off")

    # ------------------------------------------------------------------------
    # Recording lifecycle
    # ------------------------------------------------------------------------

    @staticmethod
    def _new_game_id() -> str:
        stamp = datetime.now().astimezone().strftime("%Y-%m-%dT%H-%M-%S")
        return f"{stamp}-{secrets.token_hex(2)}"

    def try_start_recording(self) -> Optional[str]:
        """Start recording the game that is about to deal. Fail-soft.

        The camera service auto-evicts oldest UNCONFIRMED recordings to make
        headroom. When saved/ recordings alone block the headroom, prompt the
        user (with download URLs); confirm deletes them — the answer is
        consumed by process_choice via the controller's MFD choose routing.
        Either way the game itself always proceeds.
        """
        try:
            if not self.camera_on:
                self._log.info("camera off/unavailable — game not recorded")
                return None

            st = self._state or {}
            budget = st.get("bytes_budget", 0)
            headroom = st.get("headroom_bytes", 0)
            # Unconfirmed recordings are auto-evictable, so the binding
            # constraint is saved/ alone exceeding budget - headroom.
            free_after_eviction = budget - self._saved_bytes()
            if free_after_eviction >= headroom:
                game_id = self._new_game_id()
                self._recording_game_id = game_id
                self._ctrl("record-start", game_id=game_id)
                self._log.info(f"recording requested for game {game_id}")
                return game_id

            # Saved recordings block the headroom — ask before deleting.
            need = headroom - free_after_eviction
            victims = []
            acc = 0
            for r in st.get("recordings", []):  # already oldest-first
                if not r.get("saved"):
                    continue
                victims.append(r)
                acc += r.get("size", 0)
                if acc >= need:
                    break
            lines = "\n".join(
                f"  {r['file']} ({r.get('size', 0) / 1e6:.0f} MB) — "
                f"http://gwent{r.get('url_path', '')}" for r in victims)
            self._pending_evict = (need, time.monotonic() + _EVICT_PROMPT_TTL_SECS)
            self.publish_prompt(
                "Recordings storage is full of saved games. Delete the oldest "
                f"{len(victims)} to record new games?\n"
                f"Download them first:\n{lines}",
                ok=True, cancel=True, clear_choices=True,
                ok_text="Delete & Record")
            self._log.warning(
                f"saved recordings block headroom (need {need / 1e9:.2f} GB) — "
                f"prompted user; this game will NOT be recorded")
            return None
        except Exception as e:
            self._log.error(f"try_start_recording failed (non-fatal): {e}",
                            exc_info=True)
            return None

    def process_choice(self, choice) -> bool:
        """Handle a y/n MFD choice for a pending eviction prompt.

        Called from the controller's CH_MFD_CHOOSE routing. Returns True when
        the choice was consumed by the eviction flow.
        """
        try:
            if self._pending_evict is None:
                return False
            need, deadline = self._pending_evict
            if time.monotonic() > deadline:
                self._log.info("eviction prompt expired — ignoring choice")
                self._pending_evict = None
                return False
            if choice.id == 'y':
                self._pending_evict = None
                self._ctrl("evict-saved", bytes_needed=need)
                self._toast("Old saved recordings deleted — "
                            "the next game will be recorded", level="info")
                return True
            if choice.id == 'n':
                self._pending_evict = None
                self._toast("Recording skipped — storage full. Download & "
                            "delete saved games at /camera/recordings/")
                return True
            return False
        except Exception as e:
            self._log.error(f"eviction choice handling failed: {e}",
                            exc_info=True)
            self._pending_evict = None
            return False

    def finish_recording(self) -> Optional[str]:
        """Stop the in-flight recording at Game Over. Returns its game_id
        (for the save/discard prompt) or None when nothing was recorded."""
        try:
            game_id = self._recording_game_id
            if game_id is None:
                return None
            self._ctrl("record-stop", game_id=game_id)
            self._log.info(f"recording stopped for game {game_id}")
            return game_id
        except Exception as e:
            self._log.error(f"finish_recording failed (non-fatal): {e}",
                            exc_info=True)
            return None

    def save_recording(self, game_id: str):
        """User confirmed at Game Over — promote to saved/."""
        try:
            self._ctrl("save", game_id=game_id)
            self._recording_game_id = None
            self._toast(f"Recording saved — download at "
                        f"/camera/recordings/saved/{game_id}.mp4", level="info")
        except Exception as e:
            self._log.error(f"save_recording failed: {e}", exc_info=True)

    def discard_recording(self, game_id: str):
        """User declined — leave in unconfirmed/ (evicted under pressure)."""
        try:
            self._ctrl("discard", game_id=game_id)
            self._recording_game_id = None
        except Exception as e:
            self._log.error(f"discard_recording failed: {e}", exc_info=True)
