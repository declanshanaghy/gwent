#!/usr/bin/env bash

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${DIR}/.." && pwd)"

# Load shared vars
source "${DIR}/install-vars.sh"

LOG_DIR="/tmp/logs"
LOG_FILE="${LOG_DIR}/gwent.log"

mkdir -p "${LOG_DIR}"
touch "${LOG_FILE}"

export PYTHONUNBUFFERED=1
export RUNNING_ON_PI=true
export GWENT_PLAYBACK=${GWENT_PLAYBACK:-""}
export GWENT_REPLAY=${GWENT_REPLAY:-""}
export GWENT_TRACE=${GWENT_TRACE:-""}

cleanup() {
    echo ""
    echo "Shutting down gwent..."
    [ -n "${GWENT_PID}" ] && kill "${GWENT_PID}" 2>/dev/null
    wait "${GWENT_PID}" 2>/dev/null
    echo "Stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "Starting gwent dev server"
echo "  Logs: ${LOG_FILE}"
if [ -n "${GWENT_REPLAY}" ]; then
    echo "  Replay: ${GWENT_REPLAY}"
fi
echo "  Trace: /tmp/logs/gwent-trace.jsonl"
echo "  Press Ctrl+C to stop"
echo ""

echo "--- start at $(date -Iseconds) ---" >> "${LOG_FILE}"
"${VENV_DIR}/bin/gwent" >> "${LOG_FILE}" 2>&1 &
GWENT_PID=$!

echo "gwent started (pid ${GWENT_PID})"
echo "  tail -f ${LOG_FILE}"

wait "${GWENT_PID}"
