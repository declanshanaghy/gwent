#!/usr/bin/env bash

# Do this manually
#
# sudo rpi-update
# sudo apt-get update
#
# Enable SPI & I2C
# sudo raspi-config
#
# no password sudo
# %sudo  ALL=(ALL) NOPASSWD: ALL
#
# Wifi config
# sudo nmcli device wifi connect "The Kearney Gaff" password 'XXXXXXXX'
#

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

# Update package lists
echo "Updating system..."
sudo apt-get update && sudo apt-get upgrade -y && sudo apt-get autoremove -y

echo "Installing wiringpi dependencies..."
sudo apt-get install -y libc6

echo "Installing hardware wiringpi interface..."
wget https://github.com/WiringPi/WiringPi/releases/download/3.14/wiringpi_3.14_arm64.deb
sudo dpkg -i wiringpi_3.14_arm64.deb

echo "Installing Python and development packages..."
sudo apt-get install -y \
  python3-dev python3-pip python3-venv python3-pil python3-wheel

echo "Installing audio and display dependencies..."
sudo apt-get install -y \
  ffmpeg \
  libasound2-dev libpulse-dev \
  libsdl2-dev libsmpeg-dev \
  libavformat-dev libavcodec-dev \
  libsdl2-mixer-dev libsdl2-image-dev libsdl2-ttf-dev \
  mosquitto rpi.gpio

echo "Installing pygame stuff..."
sudo apt-get install -y \
 libsdl1.2-dev \
 libsdl-image1.2-dev libsdl-ttf2.0-dev \
 libsmpeg-dev libportmidi-dev \
 ffmpeg libswscale-dev libavformat-dev libavcodec-dev \
 python3-pygame

# Link system pygame to virtual environment
echo "Linking system pygame to virtual environment..."
VENV_SITE_PACKAGES=~/gwent-venv/lib/python3.11/site-packages
SYSTEM_PYGAME=$(dpkg -L python3-pygame | grep -E '/__init__.py$' | sed 's|/__init__.py$||' | head -n 1)

if [ -d "$SYSTEM_PYGAME" ]; then
    echo "Found system pygame at $SYSTEM_PYGAME"
    ln -sf $SYSTEM_PYGAME $VENV_SITE_PACKAGES/
    echo "Linked pygame to virtual environment"
else
    echo "System pygame not found: ${SYSTEM_PYGAME}"
    exit 1
fi
# Add user to groups
sudo usermod -G sudo,gpio,spi,i2c -a $(whoami)