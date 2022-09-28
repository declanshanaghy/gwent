#!/usr/bin/env bash

# Do this manually
#
# sudo apt-get update
#
# Enable SPI & I2C
# sudo raspi-config
#
# sudo useradd -m geralt
# sudo usermod -G sudo,gpio,spi,i2c -a geralt
#
# Install ssh pub key in ~geralt/.ssh/authorized_keys
#
# no password sudo
# %sudo  ALL=(ALL) NOPASSWD: ALL
#

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

sudo dpkg -i software/wiringpi-latest.deb

sudo apt-get install -y \
  python3-dev  python3-pip python3-venv python3-pil python3-wheel

sudo apt-get install -y \
  ffmpeg \
  libasound2-dev libpulse-dev \
  libsdl2-dev libsmpeg-dev \
  libavformat-dev libavcodec-dev \
  libsdl2-mixer-dev libsdl2-image-dev libsdl2-ttf-dev \
  mosquitto rpi.gpio

# pygame stuff
#sudo apt-get install -y \
#  libsdl1.2-dev \
#  libsdl-image1.2-dev libsdl-ttf2.0-dev \
#  libsmpeg-dev python-numpy libportmidi-dev \
#  ffmpeg libswscale-dev libavformat-dev libavcodec-dev
