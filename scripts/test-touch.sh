#!/usr/bin/env bash
# Touch verification — runs scripts/test-touch.py inside a fresh kitty so it
# exercises the real DSI → libinput → cage → kitty → Textual pipeline. Logs
# to tmp/logs/test-touch.log; exits non-zero if no click events were captured.

set -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REPO="$( cd "${DIR}/.." && pwd )"
VENV_PY="${HOME}/gwent-venv/bin/python"
LOG="${REPO}/tmp/logs/test-touch.log"

mkdir -p "$(dirname "${LOG}")"

echo "=== test-touch ==="
echo "log: ${LOG}"

# Informational: list touch-capable input devices.
if command -v libinput > /dev/null; then
    echo
    echo "Detected input devices (libinput):"
    sudo libinput list-devices 2>/dev/null | awk '
        /^Device:/ { dev = $0 }
        /Capabilities:.*touch/ { print "  " dev " " $0 }
    ' || echo "  (libinput list-devices needs root; skipping)"
fi

# Sanity checks.
if [ ! -x "${VENV_PY}" ]; then
    echo "FAIL: ${VENV_PY} not executable. Run scripts/install-venv.sh first." >&2
    exit 1
fi
if ! command -v kitty > /dev/null; then
    echo "FAIL: kitty not installed. Run scripts/install-system.sh first." >&2
    exit 1
fi

echo
echo "Tap the screen; press q to quit."
echo

# If we're already inside a kitty session (e.g. invoked from the kiosk
# wrapper after Ctrl+C drops to bash), run the test in this kitty so it
# uses the existing cage/kitty/Textual pipeline. Otherwise, spawn a fresh
# kitty (useful from an SSH session that has a graphical seat available).
if [ -n "${KITTY_WINDOW_ID:-}" ]; then
    "${VENV_PY}" "${DIR}/test-touch.py"
    rc=$?
else
    kitty --hold --override "shell_integration=disabled" \
        "${VENV_PY}" "${DIR}/test-touch.py"
    rc=$?
fi

echo
echo "kitty exited (code ${rc})."
echo
echo "=== last 30 lines of ${LOG} ==="
tail -n 30 "${LOG}" 2>/dev/null
echo
echo "Full log: ${LOG}"
exit "${rc}"
