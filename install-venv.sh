#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

# Setup venv if it doesn't exist
if [ -d ${VENV_DIR} ]; then
  echo "venv exists in ${VENV_DIR}"
else
  echo "Setting up new venv in ${VENV_DIR}"
  python3 -m venv ${VENV_DIR}
fi
