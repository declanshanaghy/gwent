#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

source ${VENV_DIR}/bin/activate

ROOT="${DIR}/../software"

# Install gwent
echo "Installing gwent..."
pip3 install -e $ROOT/gwent
