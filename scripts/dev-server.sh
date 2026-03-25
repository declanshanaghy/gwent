#!/usr/bin/env bash

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${DIR}/.." && pwd)"

# Load shared vars
source "${DIR}/install-vars.sh"

LOG_DIR="/tmp/logs"
LOG_FILE="${LOG_DIR}/gwent.log"

mkdir -p "${LOG_DIR}"

export PYTHONUNBUFFERED=1
export RUNNING_ON_PI=true

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
echo "  Press Ctrl+C to stop"
echo ""

echo "--- start at $(date -Iseconds) ---" >> "${LOG_FILE}"
"${VENV_DIR}/bin/gwent" >> "${LOG_FILE}" 2>&1 &
GWENT_PID=$!

echo "gwent started (pid ${GWENT_PID})"
echo "  tail -f ${LOG_FILE}"

wait "${GWENT_PID}"
