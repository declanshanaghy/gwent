#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

source ${VENV_DIR}/bin/activate

ROOT="${DIR}/../software"

# Install MFRC522-python from local submodule if not already installed
echo "Installing MFRC522-python from local submodule..."
pip3 install -e $ROOT/MFRC522-python

# Install gwent
echo "Installing gwent..."
pip3 install -e $ROOT/gwent
