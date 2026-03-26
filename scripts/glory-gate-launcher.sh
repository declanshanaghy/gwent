#!/usr/bin/env bash
# Standalone launcher for glory-gate. Designed to be invoked via setsid/nohup
# so it runs fully detached from the calling shell.
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLORY_GATE_DIR="${DIR}/../software/glory-gate"

export PATH="${HOME}/.local/bin:${PATH}"

cd "${GLORY_GATE_DIR}"
exec env \
    HOST=0.0.0.0 \
    PORT="${GLORY_GATE_PORT:-8080}" \
    NODE_OPTIONS=--openssl-legacy-provider \
    BROWSER=none \
    node node_modules/.bin/react-scripts start
