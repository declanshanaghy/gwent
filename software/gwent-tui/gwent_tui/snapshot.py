"""Load game state from the gwent HTTP API via long-polling.

SnapshotPoller runs in a background thread, using the /state/poll
long-poll endpoint. The server blocks until state changes or timeout,
so the poller gets near-instant updates without busy-polling.

Falls back to regular /state polling if long-poll is unavailable.
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

# Max snapshots buffered before poller drops
MAX_QUEUE_SIZE = 3

# Long-poll settings
POLL_TIMEOUT = 300      # server-side wait (seconds) — 5 minutes
CLIENT_TIMEOUT = 305    # client-side urllib timeout (slightly longer than POLL_TIMEOUT)
RETRY_DELAY = 2         # seconds between retries on error


class SnapshotPoller:
    """Background thread that long-polls /state/poll for state changes."""

    def __init__(self, state=None):
        self.queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self.data_ready = threading.Event()
        self.data_ready_callback = None  # called from poller thread on new data
        self._running = False
        self._thread = None
        self._etag = None  # tracks last seen state
        self._state = state  # for http_status updates

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._run, name="snapshot-poller", daemon=True)
        self._thread.start()
        log.info("Snapshot long-poller started")

    def stop(self):
        self._running = False

    def _set_status(self, status):
        if self._state:
            self._state.http_status = status

    def drain(self, state):
        """Apply all pending snapshots to state. Returns number applied."""
        count = 0
        while True:
            try:
                data = self.queue.get_nowait()
                self._set_status("processing")
                state.load_snapshot(data)
                count += 1
            except queue.Empty:
                break
        if count > 0:
            self._set_status("polling")
        return count

    def _run(self):
        poll_url = gwent_state_url
        log.info("Poller thread started, url=%s", poll_url)

        while self._running:
            self._set_status("polling")
            try:
                log.debug("Polling %s (etag=%s, timeout=%d)", poll_url, self._etag or "(none)", POLL_TIMEOUT)
                url = f"{poll_url}?timeout={POLL_TIMEOUT}"
                req = urllib.request.Request(url)
                req.add_header("Connection", "close")
                if self._etag:
                    req.add_header("If-None-Match", self._etag)

                with urllib.request.urlopen(req, timeout=CLIENT_TIMEOUT) as resp:
                    log.debug("Response status=%d", resp.status)
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        self._etag = resp.headers.get("ETag", "")
                        log.debug("Got snapshot: stage=%s etag=%s", data.get("active_stage"), self._etag)
                        try:
                            self.queue.put_nowait(data)
                            self.data_ready.set()
                            if self.data_ready_callback:
                                self.data_ready_callback()
                        except queue.Full:
                            pass  # drop oldest, UI will catch up
                    # 304 = no change, loop immediately to re-poll

            except urllib.error.HTTPError as e:
                if e.code == 304:
                    log.debug("304 no change, re-polling")
                    continue
                log.debug("Long-poll HTTP error %d: %s", e.code, e)
                self._set_status("error")
                self._error_backoff()

            except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
                log.debug("Long-poll failed: %s", e)
                self._set_status("error")
                self._error_backoff()

            except Exception as e:
                log.error("Poller unexpected error: %s", e, exc_info=True)
                self._set_status("error")
                self._error_backoff()

        log.info("Poller thread exiting")
        self._set_status("off")

    def _error_backoff(self):
        """Sleep on error, but check _running flag to allow quick exit."""
        for _ in range(int(RETRY_DELAY / 0.2)):
            if not self._running:
                return
            time.sleep(0.2)
