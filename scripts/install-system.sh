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

echo "Updating rpi firmware..."
sudo rpi-update

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
 ffmpeg libswscale-dev libavformat-dev libavcodec-dev

echo "Configuring groups..."
# Create groups if they don't exist
getent group gpio > /dev/null || sudo groupadd gpio
getent group i2c > /dev/null || sudo groupadd i2c
# Add user to groups
sudo usermod -G sudo,gpio,spi,i2c -a $(whoami)