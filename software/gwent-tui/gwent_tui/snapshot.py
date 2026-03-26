"""Load game state from the gwent HTTP API."""

import json
import logging
import urllib.request
import urllib.error

log = logging.getLogger("gwent_tui.snapshot")

# Module-level URL, set from CLI arg in app.py
gwent_state_url = "http://localhost:8080/state"


def load_snapshot(state):
    """Fetch game state via HTTP and load into state.

    Returns True if snapshot was loaded, False otherwise.
    """
    try:
        req = urllib.request.Request(gwent_state_url)
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        state.load_snapshot(data)
        state.http_ok = True
        log.debug("Snapshot loaded from %s", gwent_state_url)
        return True
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        state.http_ok = False
        log.debug("Snapshot fetch failed: %s", e)
        return False
