#!/usr/bin/env bash

set -e

# Load environment variables from .env file if it exists
if [ -f "${DIR}/../.env" ]; then
    echo "Loading environment variables from .env file"
    # Only export lines that don't start with # and strip comments
    export $(grep -v '^#' "${DIR}/../.env" | sed 's/\s*#.*$//' | xargs)
fi

export VENV_NAME="gwent-venv"
export VENV_DIR="${HOME}/${VENV_NAME}"

# Export Raspberry Pi configuration for use in other scripts
export RASPBERRY_PI_IP=${RASPBERRY_PI_IP:-"192.168.1.225"}
echo "Using Raspberry Pi IP: ${RASPBERRY_PI_IP}"
