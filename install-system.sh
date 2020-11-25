#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

sudo apt-get install -y \
  python3-dev  python3-pip python3-venv python3-pil python3-wheel

sudo apt-get install -y \
  ffmpeg \
  libasound2-dev libpulse-dev \
  libsdl2-dev libsmpeg-dev \
  libavformat-dev libavcodec-dev \
  libsdl2-mixer-dev libsdl2-image-dev libsdl2-ttf-dev \

# pygame stuff
#sudo apt-get install -y \
#  libsdl1.2-dev \
#  libsdl-image1.2-dev libsdl-ttf2.0-dev \
#  libsmpeg-dev python-numpy libportmidi-dev \
#  ffmpeg libswscale-dev libavformat-dev libavcodec-dev
