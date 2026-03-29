#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

source ${VENV_DIR}/bin/activate

ROOT="${DIR}/../software"

# Install MFRC522-python
if ! pip3 show mfrc522 > /dev/null 2>&1; then
    echo "Installing MFRC522-python from local sources..."
    pip3 install -e $ROOT/MFRC522-python
else
    echo "MFRC522-python is already installed."
fi

# Install gwent-shared (TTS providers, shared utilities — no hardware deps)
echo "Installing gwent-shared..."
pip3 install -e $ROOT/gwent-shared

# Install gwent
echo "Installing gwent..."
if [ "$(uname)" = "Darwin" ]; then
    # macOS: skip hardware deps that won't build (lgpio, pigpio, etc.)
    pip3 install --no-deps -e $ROOT/gwent
    # Install non-hardware deps only
    pip3 install paho-mqtt pydub pygame beautifulsoup4 gtts flask requests audioop-lts 2>/dev/null || true
else
    pip3 install -e $ROOT/gwent
fi

# Install gwent-tui
echo "Installing gwent-tui..."
pip3 install -e $ROOT/gwent-tui
