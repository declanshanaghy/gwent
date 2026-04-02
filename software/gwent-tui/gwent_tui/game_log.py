"""File-based MQTT message logging for game events.

Every MQTT message is saved to tmp/games/{game_id}/{kind}/{ts_ms}-{subkind}.json.
Summary screens read from these files instead of in-memory arrays.
"""

import json
import logging
import os
import shutil
import threading
import time

log = logging.getLogger("gwent_tui.game_log")

_PENDING = "_pending"


class GameLog:
    """Write MQTT messages to disk, read them back for summaries."""

    def __init__(self, base_dir: str):
        self._base_dir = base_dir
        self._game_id = None
        self._lock = threading.Lock()
        self._cache = {}  # subdir -> (file_count, [data])
        # Clean up stale _pending from crashed sessions
        pending = os.path.join(base_dir, _PENDING)
        if os.path.isdir(pending):
            shutil.rmtree(pending, ignore_errors=True)

    @property
    def game_dir(self) -> str:
        """Current game directory (pending or resolved)."""
        with self._lock:
            name = self._game_id or _PENDING
            return os.path.join(self._base_dir, name)

    def set_game_id(self, game_id: str):
        """Resolve _pending/ -> {game_id}/. Called once when game_id is known."""
        with self._lock:
            if self._game_id == game_id:
                return
            old_dir = os.path.join(self._base_dir, _PENDING)
            new_dir = os.path.join(self._base_dir, game_id)
            if os.path.isdir(old_dir) and not os.path.isdir(new_dir):
                os.rename(old_dir, new_dir)
                log.info("Game log: %s -> %s", _PENDING, game_id)
            elif os.path.isdir(old_dir) and os.path.isdir(new_dir):
                # Merge: move files from pending into existing game dir
                for subdir in os.listdir(old_dir):
                    src = os.path.join(old_dir, subdir)
                    dst = os.path.join(new_dir, subdir)
                    if os.path.isdir(src):
                        os.makedirs(dst, exist_ok=True)
                        for f in os.listdir(src):
                            os.rename(os.path.join(src, f), os.path.join(dst, f))
                shutil.rmtree(old_dir, ignore_errors=True)
                log.info("Game log: merged %s into %s", _PENDING, game_id)
            self._game_id = game_id
            self._cache.clear()

    def reset(self):
        """New game — clear state, back to _pending."""
        with self._lock:
            self._game_id = None
            self._cache.clear()
            pending = os.path.join(self._base_dir, _PENDING)
            if os.path.isdir(pending):
                shutil.rmtree(pending, ignore_errors=True)

    def write(self, subdir: str, subkind: str, data: dict):
        """Write a JSON message to {game_dir}/{subdir}/{ts_ms}-{subkind}.json."""
        try:
            d = os.path.join(self.game_dir, subdir)
            os.makedirs(d, exist_ok=True)
            ms = int(time.time() * 1000)
            path = os.path.join(d, f"{ms}-{subkind}.json")
            with open(path, "w") as f:
                json.dump(data, f, separators=(",", ":"))
            with self._lock:
                self._cache.pop(subdir, None)
        except Exception as e:
            log.debug("Failed to write game log: %s", e)

    def read_all(self, subdir: str) -> list:
        """Read all JSON files from subdir, sorted chronologically."""
        d = os.path.join(self.game_dir, subdir)
        if not os.path.isdir(d):
            return []

        # Cache check: use file count as cheap invalidation
        try:
            files = sorted(f for f in os.listdir(d) if f.endswith(".json"))
        except OSError:
            return []

        with self._lock:
            cached = self._cache.get(subdir)
            if cached and cached[0] == len(files):
                return cached[1]

        result = []
        for fname in files:
            try:
                with open(os.path.join(d, fname)) as f:
                    result.append(json.load(f))
            except (json.JSONDecodeError, OSError):
                continue

        with self._lock:
            self._cache[subdir] = (len(files), result)
        return result

    def read_filtered(self, subdir: str, round_num: int = None,
                      subkinds: list = None) -> list:
        """Read and filter by round number and/or subkind list."""
        items = self.read_all(subdir)
        if subkinds is not None:
            items = [e for e in items if e.get("subkind") in subkinds]
        if round_num is not None:
            items = [e for e in items if e.get("round") == round_num]
        return items
