"""StatePublisher — publishes the full game state to MQTT.

Mirrors the snapshot to the retained topic `gwent/server/state` whenever the
state changes, so any client gets the current state instantly on connect (no
request roundtrip) and live updates thereafter.

It waits on `pubsub.state_condition` — the same signal fired on every
`PubSubComponent.publish()` — then debounces (a single game action fans out into
~40 internal publishes) and dedupes by content hash, so a burst coalesces into
at most one retained republish.
"""

import json

import gwent.game
import gwent.game.state as game_state
from gwent_shared.topics import SERVER_STATE

# Settle window: after a state-change signal, wait this long for the burst of
# follow-on publishes to finish before snapshotting once.
DEBOUNCE_SECS = 0.2
# Max time to block waiting for a signal before re-checking the stop flag.
WAIT_TIMEOUT_SECS = 1.0


class StatePublisher(gwent.game.ThreadComponent):
    """Publishes retained snapshots to gwent/server/state, debounced + deduped."""

    def __init__(self, pubsub, controller_getter, session_config):
        super().__init__()
        self._pubsub = pubsub
        self._get_controller = controller_getter
        self._cfg = session_config
        self._last_hash = None

    def _publish_snapshot(self):
        """Snapshot current state and publish if it changed. Returns True if published."""
        controller = self._get_controller()
        if controller is None:
            return False
        snapshot = game_state.snapshot_dict(
            controller,
            player_names=self._cfg.player_names,
            player_pronouns=self._cfg.player_pronouns,
            client_tts=self._cfg.client_tts,
        )
        h = game_state.state_hash(snapshot)
        if h == self._last_hash:
            return False
        self._last_hash = h
        # Publish via the raw MQTT client (NOT PubSubComponent.publish) so we
        # don't re-notify state_condition and wake ourselves.
        self._pubsub.publish(SERVER_STATE, json.dumps(snapshot), qos=1, retain=True)
        self._log.info("Published state snapshot (stage=%s, etag=%s)",
                       snapshot.get("active_stage"), h)
        return True

    def run(self):
        cond = getattr(self._pubsub, 'state_condition', None)
        if cond is None:
            self._log.error("pubsub has no state_condition; StatePublisher idle")
            self._stop_event.wait()
            return

        # Initial publish so a freshly-started broker has retained state.
        try:
            self._publish_snapshot()
        except Exception as e:
            self._log.error("initial state publish failed: %s", e, exc_info=True)

        while not self._stop_event.is_set():
            with cond:
                cond.wait(timeout=WAIT_TIMEOUT_SECS)
            if self._stop_event.is_set():
                break
            # Coalesce the burst of follow-on publishes before snapshotting.
            if self._stop_event.wait(DEBOUNCE_SECS):
                break
            try:
                self._publish_snapshot()
            except Exception as e:
                self._log.error("state publish failed: %s", e, exc_info=True)
