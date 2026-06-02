#!/usr/bin/env bash
# Kiosk runner — launched by greetd → cage → kitty -e <this script>.
# Runs `just tui --tts elevenlabs` forever. On exit (crash or clean), prints
# the error, waits for Enter, then restarts. Ctrl+C at the prompt drops to
# an interactive bash so we can do maintenance (touch test, etc.).

set -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REPO="$( cd "${DIR}/.." && pwd )"
cd "${REPO}"

drop_to_shell() {
    echo
    echo "Dropping to bash. Type 'exit' to resume the kiosk."
    exec bash -l
}

while true; do
    # Reset trap each iteration so it covers the read below.
    trap - INT
    just tui --tts elevenlabs
    rc=$?
    echo
    echo "================================================================"
    echo "  gwent-tui exited (code ${rc}) at $(date -Iseconds)"
    echo "  Press Enter to restart, Ctrl+C for a shell"
    echo "================================================================"
    trap drop_to_shell INT
    read -r || drop_to_shell
done
