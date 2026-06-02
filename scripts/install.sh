#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

${DIR}/install-system.sh
${DIR}/install-venv.sh
${DIR}/install-app.sh
${DIR}/install-service.sh
${DIR}/install-kiosk.sh