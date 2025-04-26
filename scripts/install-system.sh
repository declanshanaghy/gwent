#!/usr/bin/env bash

#############################################################################
#
# Perform all the following steps before running `make install-system`
#
#############################################################################
#
# sudo apt-get update
# sudo rpi-update
#
# Enable SPI & I2C
# sudo raspi-config
#
# sudo usermod -G sudo,gpio,spi,i2c -a ${USER}
#
# Install ssh pub key in ~/.ssh/authorized_keys
#
# no password sudo
# %sudo  ALL=(ALL) NOPASSWD: ALL
#
# Create mosquitto user with password "gwent" (hardcoded)
# sudo mosquitto_passwd -c /etc/mosquitto/passwd geralt
#
#############################################################################

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

# Install WiringPi if the package exists
if [ -f "${DIR}/../software/wiringpi-latest.deb" ]; then
  echo "Installing WiringPi from package..."
  sudo dpkg -i "${DIR}/../software/wiringpi-latest.deb" || {
    echo "Warning: Failed to install WiringPi package. Attempting to fix broken packages..."
    sudo apt --fix-broken install -y
  }
else
  echo "WiringPi package not found. Skipping installation."
  echo "If WiringPi is required, please install it manually."
fi

# Update package lists
echo "Updating package lists..."
sudo apt-get update

echo "Installing Python and development packages..."
sudo apt-get install -y \
  python3-dev python3-pip python3-venv python3-pil python3-wheel

echo "Installing audio and display dependencies..."
sudo apt-get install -y \
  ffmpeg mpg123 \
  libasound2-dev libpulse-dev \
  libsdl2-dev libsmpeg-dev \
  libavformat-dev libavcodec-dev \
  libsdl2-mixer-dev libsdl2-image-dev libsdl2-ttf-dev \
  mosquitto

echo "Installing GPIO libraries for rotary encoder support..."
sudo apt-get install -y \
  pigpio python3-pigpio \
  python3-gpiozero
  
# Enable and start the pigpio daemon
echo "Enabling and starting pigpio daemon..."
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Configure mosquitto only if the config file doesn't exist
MOSQUITTO_CONF="/etc/mosquitto/conf.d/50-listen-mqtt.conf"
if [ ! -f "$MOSQUITTO_CONF" ]; then
    echo "Configuring mosquitto..."
    sudo cp ${DIR}/50-listen-mqtt.conf $MOSQUITTO_CONF
    echo "Restarting mosquitto service..."
    sudo systemctl restart mosquitto
else
    echo "Mosquitto already configured, skipping configuration."
fi