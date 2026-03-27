"""Load game state from the gwent HTTP API.

SnapshotPoller runs in a background thread, fetching state at a regular
interval and pushing snapshots onto a queue. The UI thread drains the
queue to update GameState. If the queue fills up (UI not consuming fast
enough), the poller backs off.
"""

import json
import logging
import queue
import threading
import time
import urllib.request
import urllib.error

log = logging.getLogger("gwent_tui.snapshot")

# Module-level URL, set from CLI arg in app.py
gwent_state_url = "http://localhost:8080/state"

# Max snapshots buffered before poller backs off
MAX_QUEUE_SIZE = 3


def fetch_snapshot():
    """Fetch game state JSON from the HTTP API.

    Returns the parsed dict on success, None on failure.
    """
    try:
        req = urllib.request.Request(gwent_state_url)
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        log.debug("Snapshot fetch failed: %s", e)
        return None


def load_snapshot(state):
    """Fetch and apply a snapshot directly (used for initial load).

    Returns True if snapshot was loaded, False otherwise.
    """
    data = fetch_snapshot()
    if data is not None:
        state.load_snapshot(data)
        state.http_ok = True
        log.debug("Snapshot loaded from %s", gwent_state_url)
        return True
    state.http_ok = False
    return False


class SnapshotPoller:
    """Background thread that polls /state and pushes snapshots onto a queue."""

    def __init__(self, interval=5.0):
        self.interval = interval
        self.queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self.data_ready = threading.Event()  # signaled when new data is available
        self._running = False
        self._thread = None
        self._backoff = 1.0

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._run, name="snapshot-poller", daemon=True)
        self._thread.start()
        log.info("Snapshot poller started (interval=%.1fs)", self.interval)

    def stop(self):
        self._running = False

    def drain(self, state):
        """Apply all pending snapshots to state. Returns number applied."""
        count = 0
        while True:
            try:
                data = self.queue.get_nowait()
                state.load_snapshot(data)
                state.http_ok = True
                count += 1
            except queue.Empty:
                break
        return count

    def _run(self):
        while self._running:
            # Check queue pressure — back off if full
            if self.queue.full():
                backoff = min(self._backoff * 2, self.interval * 4)
                if backoff != self._backoff:
                    log.warning("Queue full, backing off to %.1fs", backoff)
                self._backoff = backoff
                time.sleep(self._backoff)
                continue

            # Reset backoff when queue has room
            if self._backoff > 1.0:
                log.debug("Queue drained, resetting backoff")
                self._backoff = 1.0

            data = fetch_snapshot()
            if data is not None:
                try:
                    self.queue.put_nowait(data)
                    self.data_ready.set()  # wake up the UI thread
                except queue.Full:
                    pass  # drop it, will back off next iteration
            else:
                # Mark HTTP as down — UI can check state.http_ok
                pass

            time.sleep(self.interval)
