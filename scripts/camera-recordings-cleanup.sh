#!/usr/bin/env bash
# Cron wrapper for camera-recordings-cleanup.py — fixes interpreter and cwd
# so the /etc/cron.d/gwent-camera line stays trivial.
set -euo pipefail
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# System python3: the cleanup is stdlib-only, no venv coupling needed.
exec /usr/bin/python3 "${DIR}/camera-recordings-cleanup.py"
