#!/usr/bin/env bash

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${DIR}/.." && pwd)"

# Load shared vars
source "${DIR}/install-vars.sh"

# Ensure ~/.local/bin is on PATH (corepack installs yarn here)
export PATH="${HOME}/.local/bin:${PATH}"

LOG_DIR="/tmp/logs"
PID_DIR="/tmp/pids"
mkdir -p "${LOG_DIR}" "${PID_DIR}"

# Service definitions
GWENT_LOG="${LOG_DIR}/gwent.log"
GWENT_PID_FILE="${PID_DIR}/gwent.pid"

# Detect machine hostname and IP for URL display
MACHINE_HOSTNAME="$(hostname 2>/dev/null || echo "localhost")"
MACHINE_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
[ -z "${MACHINE_IP}" ] && MACHINE_IP="127.0.0.1"

export PYTHONUNBUFFERED=1
export RUNNING_ON_PI=true
export GWENT_STATE=${GWENT_STATE:-""}
export GWENT_STATE_OUT=${GWENT_STATE_OUT:-""}
GWENT_OWNER=""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

usage() {
    echo "Usage: dev-server.sh <service> <action>"
    echo ""
    echo "  service:  gwent | all"
    echo "  action:   start | stop | restart | status"
    echo ""
    echo "Options:"
    echo "  -r, --recording FILE   Load a game recording on start/restart"
    echo "  -o, --owner NAME       Set card owner"
    echo "  -t, --tts PROVIDER     Set TTS provider"
    echo "  -s, --simple           Use simple announcements"
    echo ""
    echo "Examples:"
    echo "  dev-server.sh gwent start"
    echo "  dev-server.sh gwent restart -r 008-nilfgaardian-vs-skellige.json"
    echo "  dev-server.sh all stop"
    exit 1
}

is_running() {
    local pid_file="$1"
    if [ -f "${pid_file}" ]; then
        local pid
        pid=$(cat "${pid_file}")
        if kill -0 "${pid}" 2>/dev/null; then
            return 0
        fi
        # Stale pid file
        rm -f "${pid_file}"
    fi
    return 1
}

read_pid() {
    cat "$1" 2>/dev/null || echo ""
}

# ---------------------------------------------------------------------------
# Start functions
# ---------------------------------------------------------------------------

start_gwent() {
    if is_running "${GWENT_PID_FILE}"; then
        echo "gwent is already running (pid $(read_pid "${GWENT_PID_FILE}"))"
        return 0
    fi
    touch "${GWENT_LOG}"
    echo "--- start at $(date -Iseconds) ---" >> "${GWENT_LOG}"
    # gwent manages its own PID file at /tmp/pids/gwent.pid
    local owner_arg=""
    [ -n "${GWENT_OWNER}" ] && owner_arg="--owner ${GWENT_OWNER}"
    local tts_arg=""
    [ -n "${GWENT_TTS}" ] && tts_arg="--tts ${GWENT_TTS}"
    local simple_arg=""
    [ -n "${GWENT_SIMPLE}" ] && simple_arg="--simple"
    nohup "${VENV_DIR}/bin/gwent" ${owner_arg} ${tts_arg} ${simple_arg} >> "${GWENT_LOG}" 2>&1 &
    disown $! 2>/dev/null
    # Wait for gwent to write its PID file
    for i in 1 2 3 4 5; do
        [ -f "${GWENT_PID_FILE}" ] && break
        sleep 1
    done
    if [ -f "${GWENT_PID_FILE}" ]; then
        echo "gwent started (pid $(read_pid "${GWENT_PID_FILE}"))"
    else
        echo "gwent failed to start (no PID file after 5s)"
    fi
}

# ---------------------------------------------------------------------------
# Stop functions — uses SIGTERM for graceful shutdown
# ---------------------------------------------------------------------------

stop_service() {
    local name="$1"
    local pid_file="$2"

    if ! is_running "${pid_file}"; then
        echo "${name} is not running"
        return 0
    fi

    local pid
    pid=$(read_pid "${pid_file}")
    echo "Stopping ${name} (pid ${pid})..."
    kill "${pid}" 2>/dev/null || true
    # Wait up to 10s for graceful exit
    local i=0
    while kill -0 "${pid}" 2>/dev/null && [ $i -lt 20 ]; do
        sleep 0.5
        i=$((i + 1))
    done
    if kill -0 "${pid}" 2>/dev/null; then
        echo "  ${name} did not exit in time, sending SIGKILL"
        kill -9 "${pid}" 2>/dev/null || true
    fi
    rm -f "${pid_file}"
    echo "${name} stopped"
}

stop_gwent()      { stop_service "gwent"      "${GWENT_PID_FILE}"; }

# ---------------------------------------------------------------------------
# Status / summary
# ---------------------------------------------------------------------------

print_summary() {
    echo ""
    echo "===== Dev Server Summary ====="
    echo ""

    if is_running "${GWENT_PID_FILE}"; then
        local gpid
        gpid=$(read_pid "${GWENT_PID_FILE}")
        echo "  gwent"
        echo "    Status:     running (pid ${gpid})"
        echo "    Log:        ${GWENT_LOG}"
        echo "    Save state: kill -USR1 ${gpid}"
    else
        echo "  gwent"
        echo "    Status:     stopped"
        echo "    Log:        ${GWENT_LOG}"
    fi

    echo ""
    echo "==============================="
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SERVICE="${1:-}"
ACTION="${2:-}"
shift 2 2>/dev/null || true

# Parse optional flags
while [ $# -gt 0 ]; do
    case "$1" in
        -o|--owner) GWENT_OWNER="$2"; shift 2 ;;
        -t|--tts)   GWENT_TTS="$2"; shift 2 ;;
        -s|--simple) GWENT_SIMPLE=1; shift ;;
        -r|--recording) GWENT_STATE="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [ -z "${SERVICE}" ] || [ -z "${ACTION}" ]; then
    usage
fi

case "${ACTION}" in
    start)
        case "${SERVICE}" in
            gwent)       start_gwent ;;
            all)         start_gwent ;;
            *)           usage ;;
        esac
        ;;
    stop)
        case "${SERVICE}" in
            gwent)       stop_gwent ;;
            all)         stop_gwent ;;
            *)           usage ;;
        esac
        ;;
    restart)
        case "${SERVICE}" in
            gwent)       stop_gwent; start_gwent ;;
            all)         stop_gwent; start_gwent ;;
            *)           usage ;;
        esac
        ;;
    status)
        ;;
    *)
        usage
        ;;
esac

print_summary
