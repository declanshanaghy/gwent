#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

source ${VENV_DIR}/bin/activate

ROOT="${DIR}/../software"

# Install MFRC522-python from GitHub if not already installed
if ! pip3 show mfrc522 > /dev/null 2>&1; then
    echo "Installing MFRC522-python from GitHub..."
    sudo pip3 install --break-system-packages git+https://github.com/pimylifeup/MFRC522-python.git
else
    echo "MFRC522-python is already installed."
fi

# Install gwent
echo "Installing gwent..."
sudo pip3 install --break-system-packages -e $ROOT/gwent
