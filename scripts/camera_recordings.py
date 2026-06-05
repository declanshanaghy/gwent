"""Disk-budget manager for gwent camera recordings. Stdlib only.

Layout:
    tmp/recordings/unconfirmed/   recordings not yet saved at Game Over —
                                  fair game for automatic eviction
    tmp/recordings/saved/         user-confirmed keepers — deleted only after
                                  explicit user confirmation (evict_saved)

Policy (user-decided):
    - BUDGET: recordings may never use more than 10 GiB total
    - HEADROOM: a new game needs 1.5 GiB free in the budget (one long game)
    - No time-based TTL — keep recordings as long as possible, evict oldest
      first and only under space pressure

Used by scripts/camera-server.py (live eviction at record-start) and
scripts/camera-recordings-cleanup.py (hourly cron cap enforcement).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REC_ROOT = REPO_ROOT / "tmp" / "recordings"
UNCONFIRMED_DIR = REC_ROOT / "unconfirmed"
SAVED_DIR = REC_ROOT / "saved"

BUDGET_BYTES = 10 * 1024**3          # 10 GiB hard cap for all recordings
HEADROOM_BYTES = int(1.5 * 1024**3)  # required free budget before recording

# H.264 @ 3 Mbps ≈ 22.5 MB/min ≈ 0.68 GB per 30-min game
BITRATE = 3_000_000


def ensure_dirs():
    """Create the recordings tree, world-readable so nginx can serve it."""
    for d in (REC_ROOT, UNCONFIRMED_DIR, SAVED_DIR):
        d.mkdir(parents=True, exist_ok=True)
        d.chmod(0o755)


def recording_path(game_id):
    """Where a new recording for game_id lands (always unconfirmed first)."""
    return UNCONFIRMED_DIR / f"{game_id}.mp4"


def list_recordings():
    """All recordings oldest-first: [{path, file, size, saved, mtime}]."""
    recs = []
    for d, saved in ((UNCONFIRMED_DIR, False), (SAVED_DIR, True)):
        if not d.is_dir():
            continue
        for p in d.iterdir():
            if p.is_file():
                st = p.stat()
                recs.append({
                    "path": p,
                    "file": p.name,
                    "size": st.st_size,
                    "saved": saved,
                    "mtime": st.st_mtime,
                })
    recs.sort(key=lambda r: r["mtime"])
    return recs


def bytes_used():
    return sum(r["size"] for r in list_recordings())


def budget_free():
    """Bytes left in the budget (negative when over cap)."""
    return BUDGET_BYTES - bytes_used()


def headroom_ok():
    return budget_free() >= HEADROOM_BYTES


def evict_unconfirmed(logger, target_free=HEADROOM_BYTES, exclude=None):
    """Delete oldest unconfirmed recordings until budget_free() >= target_free.

    exclude: set of filenames never to delete (e.g. the in-progress recording).
    Never touches saved/. Returns (freed_bytes, deleted_names).
    """
    exclude = exclude or set()
    freed = 0
    deleted = []
    for rec in [r for r in list_recordings() if not r["saved"]]:
        if budget_free() >= target_free:
            break
        if rec["file"] in exclude:
            continue
        rec["path"].unlink()
        freed += rec["size"]
        deleted.append(rec["file"])
        logger.info(
            "evicted unconfirmed %s (%.1f MB) — budget free now %.2f GB",
            rec["file"], rec["size"] / 1e6, budget_free() / 1e9)
    return freed, deleted


def oldest_saved_until(bytes_needed):
    """Oldest saved recordings whose cumulative size covers bytes_needed."""
    out = []
    acc = 0
    for rec in [r for r in list_recordings() if r["saved"]]:
        out.append(rec)
        acc += rec["size"]
        if acc >= bytes_needed:
            break
    return out


def evict_saved(logger, bytes_needed):
    """Delete oldest saved recordings to free >= bytes_needed.

    Only called after the user has explicitly confirmed (they get download
    URLs first). Returns (freed_bytes, deleted_names).
    """
    freed = 0
    deleted = []
    for rec in oldest_saved_until(bytes_needed):
        rec["path"].unlink()
        freed += rec["size"]
        deleted.append(rec["file"])
        logger.info(
            "evicted SAVED %s (%.1f MB) on user confirmation — freed %.2f GB",
            rec["file"], rec["size"] / 1e6, freed / 1e9)
    return freed, deleted


def move_to_saved(filename, logger):
    """Promote an unconfirmed recording to saved/. Returns new path or None."""
    src = UNCONFIRMED_DIR / filename
    if not src.is_file():
        logger.error("move_to_saved: %s not found in unconfirmed/", filename)
        return None
    dst = SAVED_DIR / filename
    src.rename(dst)
    logger.info("saved recording %s (%.1f MB)", filename, dst.stat().st_size / 1e6)
    return dst
