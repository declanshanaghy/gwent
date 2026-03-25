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
#############################################################################

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/install-vars.sh

# Update package lists
echo "Updating package lists..."
sudo apt-get update

# Download and install WiringPi from GitHub
echo "Downloading WiringPi from GitHub..."
WIRINGPI_URL="https://github.com/WiringPi/WiringPi/releases/download/3.14/wiringpi_3.14_arm64.deb"
WIRINGPI_DEB="/tmp/wiringpi_3.14_arm64.deb"

# Download the package
if command -v wget > /dev/null; then
  wget -q -O "$WIRINGPI_DEB" "$WIRINGPI_URL" || {
    echo "Failed to download WiringPi package using wget. Trying curl..."
    if command -v curl > /dev/null; then
      curl -s -L -o "$WIRINGPI_DEB" "$WIRINGPI_URL" || {
        echo "Error: Failed to download WiringPi package. Please check your internet connection."
        echo "If WiringPi is required, please install it manually."
      }
    else
      echo "Error: Neither wget nor curl is available. Cannot download WiringPi package."
      echo "If WiringPi is required, please install it manually."
    fi
  }
else
  if command -v curl > /dev/null; then
    curl -s -L -o "$WIRINGPI_DEB" "$WIRINGPI_URL" || {
      echo "Error: Failed to download WiringPi package. Please check your internet connection."
      echo "If WiringPi is required, please install it manually."
    }
  else
    echo "Error: Neither wget nor curl is available. Cannot download WiringPi package."
    echo "If WiringPi is required, please install it manually."
  fi
fi

# Install the package if download was successful
if [ -f "$WIRINGPI_DEB" ]; then
  echo "Installing WiringPi from downloaded package..."
  sudo dpkg -i "$WIRINGPI_DEB" || {
    echo "Warning: Failed to install WiringPi package. Attempting to fix broken packages..."
    sudo apt --fix-broken install -y
  }

  # Clean up the downloaded file
  rm -f "$WIRINGPI_DEB"
else
  echo "WiringPi package download failed or file not found."
  echo "If WiringPi is required, please install it manually."
fi

echo "Installing Python and development packages..."
sudo apt-get install -y \
  python3-dev python3-pip python3-venv python3-pil python3-wheel

echo "Installing build tools for native Python extensions..."
sudo apt-get install -y \
  swig i2c-tools liblgpio-dev

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
  pigpio-tools python3-pigpio \
  python3-gpiozero

# Install pigpio daemon from source if pigpiod is not available
# (Debian Trixie dropped the pigpio daemon package)
if ! command -v pigpiod > /dev/null; then
  echo "pigpiod not found in system packages, building from source..."
  PIGPIO_BUILD_DIR="/tmp/pigpio-build"
  rm -rf "$PIGPIO_BUILD_DIR"
  mkdir -p "$PIGPIO_BUILD_DIR"
  cd "$PIGPIO_BUILD_DIR"
  wget -q https://github.com/joan2937/pigpio/archive/master.zip
  unzip -q master.zip
  cd pigpio-master
  make -j$(nproc)
  sudo make install
  cd /
  rm -rf "$PIGPIO_BUILD_DIR"
  echo "pigpiod built and installed from source."
fi

# Create pigpiod systemd service if it doesn't exist
if [ ! -f /etc/systemd/system/pigpiod.service ]; then
  echo "Creating pigpiod systemd service..."
  sudo tee /etc/systemd/system/pigpiod.service > /dev/null << 'EOF'
[Unit]
Description=pigpio daemon
After=local-fs.target network.target

[Service]
Type=forking
ExecStart=/usr/local/bin/pigpiod
ExecStop=/bin/kill -SIGTERM $MAINPID

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
fi

# Enable and start the pigpio daemon
echo "Enabling and starting pigpio daemon..."
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Configure mosquitto
MOSQUITTO_CONF="/etc/mosquitto/conf.d/50-listen-mqtt.conf"
if [ ! -f "$MOSQUITTO_CONF" ]; then
    echo "Configuring mosquitto..."
    sudo cp ${DIR}/50-listen-mqtt.conf $MOSQUITTO_CONF
fi

# Configure mosquitto credentials
MOSQUITTO_PASSWD="/etc/mosquitto/passwd"
if [ ! -f "$MOSQUITTO_PASSWD" ]; then
    echo "Creating mosquitto credentials (user: geralt)..."
    sudo mosquitto_passwd -b -c "$MOSQUITTO_PASSWD" geralt gwent
    sudo chmod 640 "$MOSQUITTO_PASSWD"
    sudo chown root:mosquitto "$MOSQUITTO_PASSWD"
fi

echo "Restarting mosquitto service..."
sudo systemctl restart mosquitto

echo "System installation complete."
echo "  mosquitto: $(systemctl is-active mosquitto)"
echo "  pigpiod:   $(systemctl is-active pigpiod)"
