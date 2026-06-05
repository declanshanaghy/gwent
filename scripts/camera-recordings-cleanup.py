#!/usr/bin/env python3
"""Cron janitor for gwent camera recordings.

Enforces the 10 GiB budget by deleting the oldest UNCONFIRMED recordings
until usage is back under the cap. Never touches saved/ — those are deleted
only via the user-confirmed evict-saved flow in camera-server.py.

Runs hourly from /etc/cron.d/gwent-camera. Pure filesystem janitor — no MQTT,
so it works even when the broker or camera service is down.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_recordings  # noqa: E402

LOG_DIR = camera_recordings.REPO_ROOT / "tmp" / "logs"
LOG_FILE = LOG_DIR / "camera-recordings-cleanup.log"


class ISOFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created).astimezone().isoformat(
            timespec="seconds"
        )


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("camera-recordings-cleanup")
    for handler in (logging.StreamHandler(sys.stdout),
                    logging.FileHandler(LOG_FILE)):
        handler.setFormatter(
            ISOFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    camera_recordings.ensure_dirs()
    used = camera_recordings.bytes_used()
    logger.info("recordings usage: %.2f GB of %.2f GB budget",
                used / 1e9, camera_recordings.BUDGET_BYTES / 1e9)

    if used <= camera_recordings.BUDGET_BYTES:
        logger.info("under budget — nothing to do")
        return

    # Over cap: delete oldest unconfirmed until back under (target_free=0).
    freed, deleted = camera_recordings.evict_unconfirmed(logger, target_free=0)
    if deleted:
        logger.info("freed %.2f GB by deleting %d unconfirmed recording(s)",
                    freed / 1e9, len(deleted))
    over = camera_recordings.bytes_used() - camera_recordings.BUDGET_BYTES
    if over > 0:
        logger.warning(
            "still %.2f GB over budget — only saved/ recordings remain; "
            "they require user-confirmed eviction", over / 1e9)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
