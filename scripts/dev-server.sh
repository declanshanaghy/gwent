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

GLORY_GATE_LOG="${LOG_DIR}/glory-gate.log"
GLORY_GATE_PID_FILE="${PID_DIR}/glory-gate.pid"
GLORY_GATE_DIR="${REPO_ROOT}/software/glory-gate"
GLORY_GATE_PORT="8080"

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
    echo "  service:  gwent | glory-gate | all"
    echo "  action:   start | stop | restart | status"
    echo ""
    echo "Examples:"
    echo "  dev-server.sh gwent start"
    echo "  dev-server.sh glory-gate restart"
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

# start_glory_gate runs react-scripts as a FOREGROUND process.
# react-scripts start does not survive parent shell exit, so this function
# blocks forever. The caller must run the whole script in the background
# (e.g. Bash tool run_in_background) when using start/restart for glory-gate.
start_glory_gate() {
    if is_running "${GLORY_GATE_PID_FILE}"; then
        echo "glory-gate is already running (pid $(read_pid "${GLORY_GATE_PID_FILE}"))"
        return 0
    fi
    # Install deps if needed
    if [ ! -d "${GLORY_GATE_DIR}/node_modules" ]; then
        echo "Installing glory-gate dependencies..."
        (cd "${GLORY_GATE_DIR}" && yarn install --frozen-lockfile) 2>&1
    fi
    touch "${GLORY_GATE_LOG}"
    echo "--- start at $(date -Iseconds) ---" >> "${GLORY_GATE_LOG}"

    GLORY_GATE_PORT="${GLORY_GATE_PORT}" "${DIR}/glory-gate-launcher.sh" \
        >> "${GLORY_GATE_LOG}" 2>&1 &
    local pid=$!

    echo "${pid}" > "${GLORY_GATE_PID_FILE}"
    echo "glory-gate started (pid ${pid})"

    # Print summary now, then block waiting so the shell stays alive
    print_summary
    wait "${pid}" 2>/dev/null
    rm -f "${GLORY_GATE_PID_FILE}"
    echo "glory-gate exited"
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
stop_glory_gate() { stop_service "glory-gate"  "${GLORY_GATE_PID_FILE}"; }

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

    if is_running "${GLORY_GATE_PID_FILE}"; then
        local ggpid
        ggpid=$(read_pid "${GLORY_GATE_PID_FILE}")
        echo "  glory-gate"
        echo "    Status:     running (pid ${ggpid})"
        echo "    URLs:"
        echo "      http://localhost:${GLORY_GATE_PORT}"
        echo "      http://${MACHINE_HOSTNAME}:${GLORY_GATE_PORT}"
        echo "      http://${MACHINE_IP}:${GLORY_GATE_PORT}"
        echo "    Log:        ${GLORY_GATE_LOG}"
    else
        echo "  glory-gate"
        echo "    Status:     stopped"
        echo "    Log:        ${GLORY_GATE_LOG}"
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
        *) shift ;;
    esac
done

if [ -z "${SERVICE}" ] || [ -z "${ACTION}" ]; then
    usage
fi

# For glory-gate start/restart, start_glory_gate blocks (prints summary itself).
# For everything else, print summary at the end.
NEEDS_SUMMARY=true

case "${ACTION}" in
    start)
        case "${SERVICE}" in
            gwent)       start_gwent ;;
            glory-gate)  NEEDS_SUMMARY=false; start_glory_gate ;;
            all)         start_gwent; NEEDS_SUMMARY=false; start_glory_gate ;;
            *)           usage ;;
        esac
        ;;
    stop)
        case "${SERVICE}" in
            gwent)       stop_gwent ;;
            glory-gate)  stop_glory_gate ;;
            all)         stop_gwent; stop_glory_gate ;;
            *)           usage ;;
        esac
        ;;
    restart)
        case "${SERVICE}" in
            gwent)       stop_gwent;      start_gwent ;;
            glory-gate)  stop_glory_gate;  NEEDS_SUMMARY=false; start_glory_gate ;;
            all)         stop_gwent; stop_glory_gate; start_gwent; NEEDS_SUMMARY=false; start_glory_gate ;;
            *)           usage ;;
        esac
        ;;
    status)
        ;;
    *)
        usage
        ;;
esac

if [ "${NEEDS_SUMMARY}" = true ]; then
    print_summary
fi
